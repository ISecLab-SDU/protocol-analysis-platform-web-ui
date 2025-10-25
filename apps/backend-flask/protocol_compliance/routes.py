"""Flask blueprints for the protocol compliance domain."""

from __future__ import annotations

import contextlib
import logging
import json
import os
import re
import subprocess
import threading
from datetime import datetime
from typing import Iterable, Optional

from flask import Blueprint, make_response, request
from werkzeug.datastructures import FileStorage

try:
    from ..utils.auth import verify_access_token
    from ..utils.responses import error_response, paginate, success_response, unauthorized
except ImportError:
    from utils.auth import verify_access_token
    from utils.responses import error_response, paginate, success_response, unauthorized
from .analysis import (
    AnalysisError,
    AnalysisExecutionError,
    AnalysisNotReadyError,
    extract_protocol_version,
    normalize_protocol_name,
    run_static_analysis,
    try_extract_rules_summary,
)
from .store import STORE, TaskStatus

LOGGER = logging.getLogger(__name__)

bp = Blueprint("protocol_compliance", __name__, url_prefix="/api/protocol-compliance")


# Authentication -------------------------------------------------------------

def _ensure_authenticated():
    user = verify_access_token(request.headers.get("Authorization"))
    if not user:
        return None, unauthorized()
    return user, None


# Helpers -------------------------------------------------------------------

def _to_int(value: Optional[str], fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return parsed if parsed > 0 else fallback


def _normalize_status(raw: Optional[Iterable[str]]) -> Optional[list[TaskStatus]]:
    if not raw:
        return None
    statuses: set[TaskStatus] = set()
    allowed: set[TaskStatus] = {"completed", "failed", "processing", "queued"}

    for item in raw:
        if not item:
            continue
        segments = [segment.strip() for segment in item.split(",")]
        for segment in segments:
            if segment in allowed:
                statuses.add(segment)  # type: ignore[arg-type]

    return list(statuses) if statuses else None


def _parse_tags(raw: Optional[str]) -> Optional[list[str]]:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, list):
        tags = [item for item in parsed if isinstance(item, str)]
        return tags or None
    return None


def _read_upload(upload: FileStorage) -> tuple[str, Optional[bytes]]:
    filename = upload.filename or "upload.bin"
    data = upload.read() if upload else None
    if upload:
        with contextlib.suppress(Exception):
            upload.stream.seek(0)
    return filename, data


def _collect_exception_details(exc: Exception, *, max_logs: int = 40) -> dict:
    details = {"message": str(exc)}
    extra = getattr(exc, "details", None)
    if isinstance(extra, dict) and extra:
        details.update(extra)

    logs = getattr(exc, "logs", None)
    if isinstance(logs, list) and logs:
        details["logs"] = logs[-max_logs:]

    excerpt = getattr(exc, "log_excerpt", None)
    if excerpt and "logExcerpt" not in details:
        details["logExcerpt"] = excerpt

    return details


# Routes --------------------------------------------------------------------


@bp.route("/tasks", methods=["GET"])
def list_tasks():
    _, error = _ensure_authenticated()
    if error:
        return error

    page = _to_int(request.args.get("page"), 1)
    page_size = min(_to_int(request.args.get("pageSize"), 20), 50)
    status = _normalize_status(request.args.getlist("status"))

    tasks = STORE.list_tasks(status=status)
    paged, total = paginate(tasks, page, page_size)

    base_url = request.url_root.rstrip("/")
    items = [STORE.serialize_task(task, base_url) for task in paged]

    if page > 1 and not items and total > 0:
        payload = error_response("Requested page exceeds available data")
        return make_response(payload, 400)

    payload = success_response(
        {
            "items": items,
            "page": page,
            "pageSize": page_size,
            "total": total,
        }
    )
    return payload


@bp.route("/tasks", methods=["POST"])
def create_task():
    _, error = _ensure_authenticated()
    if error:
        return error

    if "file" not in request.files and not request.files:
        payload = error_response("请上传协议文档")
        return make_response(payload, 400)

    document_name: Optional[str] = None
    document_size: Optional[int] = None

    for upload in request.files.values():
        if not isinstance(upload, FileStorage):
            continue
        document_name = upload.filename
        data = upload.read()
        document_size = len(data) if data else None
        upload.stream.seek(0)
        break

    if not document_name:
        payload = error_response("缺少协议文档，请重新上传")
        return make_response(payload, 400)

    description = request.form.get("description", "").strip() or None
    name = (
        request.form.get("name", "").strip()
        or _strip_extension(document_name)
        or "协议任务"
    )
    tags = _parse_tags(request.form.get("tags"))

    task = STORE.create_task(
        name=name,
        document_name=document_name,
        document_size=document_size,
        description=description,
        tags=tags,
    )

    base_url = request.url_root.rstrip("/")
    payload = success_response(STORE.serialize_task(task, base_url))
    return payload


@bp.route("/tasks/<task_id>/result", methods=["GET"])
def download_result(task_id: str):
    _, error = _ensure_authenticated()
    if error:
        return error

    task = STORE.get_task(task_id)
    if not task:
        return make_response(error_response("未找到指定任务"), 404)

    if task.status != "completed" or not task.result_payload:
        return make_response(
            error_response("任务尚未完成，暂不可下载结果"), 409
        )

    content = json.dumps(task.result_payload, ensure_ascii=False, indent=2)
    base_name = re.sub(r"\s+", "-", task.name or task.document_name)
    file_name = f"{base_name}-rules.json"

    response = make_response(content)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    response.headers["Content-Disposition"] = f'attachment; filename="{file_name}"'
    return response


@bp.route("/static-analysis", methods=["POST"])
def static_analysis():
    _, error = _ensure_authenticated()
    if error:
        return error

    if not request.files:
        return make_response(error_response("请上传协议规则和代码片段"), 400)

    rules_upload = request.files.get("rules")
    code_upload = request.files.get("code")

    if not isinstance(rules_upload, FileStorage) or not isinstance(
        code_upload, FileStorage
    ):
        return make_response(error_response("请同时上传协议规则 JSON 和代码片段文件"), 400)

    rules_name, rules_data = _read_upload(rules_upload)
    code_name, _ = _read_upload(code_upload)

    parsed_rules = None
    if rules_data:
        try:
            parsed_rules = json.loads(rules_data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            parsed_rules = None

    protocol_name = normalize_protocol_name(parsed_rules, rules_name)
    protocol_version = extract_protocol_version(parsed_rules, None)
    rules_summary = try_extract_rules_summary(parsed_rules)
    notes = request.form.get("notes")

    try:
        analysis = run_static_analysis(
            code_stream=code_upload.stream,
            code_file_name=code_name,
            rules_stream=rules_upload.stream,
            rules_file_name=rules_name,
            notes=notes,
            protocol_name=protocol_name,
            protocol_version=protocol_version,
            rules_summary=rules_summary,
        )
    except AnalysisNotReadyError as exc:
        LOGGER.warning("ProtocolGuard Docker not ready: %s", exc)
        details = _collect_exception_details(exc)
        return make_response(error_response(f"后端尚未就绪: {exc}", details), 503)
    except AnalysisExecutionError as exc:
        LOGGER.error("ProtocolGuard Docker execution failed: %s", exc)
        details = _collect_exception_details(exc)
        return make_response(
            error_response("静态分析执行失败。请查看日志了解详情。", details),
            502,
        )
    except AnalysisError as exc:
        LOGGER.error("ProtocolGuard Docker integration error: %s", exc)
        details = _collect_exception_details(exc)
        return make_response(
            error_response("静态分析服务出现异常。", details),
            500,
        )

    payload = success_response(analysis)
    return payload


def _strip_extension(filename: str) -> str:
    if "." not in filename:
        return filename
    return filename.rsplit(".", 1)[0]


# Protocol Specific Routes -------------------------------------------------

# RTSP协议配置 - 在这里修改路径和命令
RTSP_CONFIG = {
    "script_path": "/home/hhh/下载/AFLNET/commands/run-aflnet.sh",  # 修改为你的脚本文件路径
    "shell_command": "cd /home/hhh/下载/AFLNET/ && docker run -d --privileged -v $(pwd)/output:/home/live555/testProgs/out-live555 -v $(pwd)/commands:/host-commands -p 8554:8554 aflnet-live555",  # 修改为你的启动命令
    "log_file_path": "/home/hhh/下载/AFLNET/output/plot_data"  # 修改为你的日志文件路径
}

# MQTT协议配置 - MBFuzzer相关路径
MQTT_CONFIG = {
    "log_file_path": os.path.join(os.path.dirname(__file__), "mbfuzzer_logs", "fuzzing_report.txt"),  # MBFuzzer日志文件路径
    "shell_command": "python3 /path/to/mbfuzzer/fuzz.py",  # MBFuzzer启动命令（需要根据实际路径修改）
    "output_dir": os.path.join(os.path.dirname(__file__), "mbfuzzer_logs")  # MBFuzzer输出目录
}

# SNMP协议配置 - SNMP Fuzzer相关路径
SNMP_CONFIG = {
    "log_file_path": os.path.join(os.path.dirname(__file__), "snmpfuzzer_logs", "fuzz_output.txt"),  # SNMP Fuzzer日志文件路径
    "shell_command": "python3 /path/to/snmpfuzzer/fuzz.py",  # SNMP Fuzzer启动命令（需要根据实际路径修改）
    "output_dir": os.path.join(os.path.dirname(__file__), "snmpfuzzer_logs")  # SNMP Fuzzer输出目录
}

@bp.route("/write-script", methods=["POST"])
def write_script():
    """写入脚本文件到指定路径"""
    _, error = _ensure_authenticated()
    if error:
        return error
    
    data = request.get_json()
    if not data:
        return make_response(error_response("请求数据不能为空"), 400)
    
    content = data.get("content")
    protocol = data.get("protocol", "UNKNOWN")
    
    if not content:
        return make_response(error_response("脚本内容不能为空"), 400)
    
    # 根据协议获取配置
    if protocol == "RTSP":
        file_path = RTSP_CONFIG["script_path"]
    elif protocol == "MQTT":
        # MQTT协议暂时不需要脚本文件，直接返回成功
        return success_response({
            "message": f"{protocol}协议不需要脚本文件",
            "filePath": "N/A",
            "size": 0
        })
    else:
        return make_response(error_response(f"不支持的协议类型: {protocol}"), 400)
    
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 写入文件（覆盖模式）
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 如果是shell脚本，设置执行权限
        if file_path.endswith('.sh'):
            os.chmod(file_path, 0o755)
        
        return success_response({
            "message": f"{protocol}脚本文件写入成功",
            "filePath": file_path,
            "size": len(content.encode('utf-8'))
        })
        
    except Exception as e:
        return make_response(error_response(f"写入文件失败: {str(e)}"), 500)


@bp.route("/execute-command", methods=["POST"])
def execute_command():
    """执行shell命令启动程序"""
    _, error = _ensure_authenticated()
    if error:
        return error
    
    data = request.get_json()
    if not data:
        return make_response(error_response("请求数据不能为空"), 400)
    
    protocol = data.get("protocol", "UNKNOWN")
    
    # 根据协议获取配置
    if protocol == "RTSP":
        command = RTSP_CONFIG["shell_command"]
    elif protocol == "MQTT":
        command = MQTT_CONFIG["shell_command"]
    else:
        return make_response(error_response(f"不支持的协议类型: {protocol}"), 400)
    
    try:
        print(f"[DEBUG] 执行命令: {command}")  # 调试日志
        
        # 使用subprocess.run等待命令完成，而不是Popen
        result = subprocess.run(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30  # 30秒超时
        )
        
        print(f"[DEBUG] 命令返回码: {result.returncode}")  # 调试日志
        
        if result.returncode == 0:
            # 命令执行成功
            print(f"[DEBUG] 命令执行成功")
            print(f"[DEBUG] stdout: {result.stdout}")
            
            # 对于docker run -d，成功的话stdout通常包含容器ID
            container_id = result.stdout.strip() if result.stdout.strip() else "unknown"
            
            return success_response({
                "message": f"{protocol}命令执行成功",
                "command": command,
                "container_id": container_id,
                "pid": "docker_container"  # Docker容器没有传统意义的PID
            })
        else:
            # 命令执行失败
            error_msg = result.stderr.strip() if result.stderr.strip() else "未知错误"
            print(f"[DEBUG] 命令执行失败: {error_msg}")
            return make_response(error_response(f"命令执行失败: {error_msg}"), 500)
        
    except subprocess.TimeoutExpired:
        print(f"[DEBUG] 命令执行超时")
        return make_response(error_response("命令执行超时"), 500)
    except Exception as e:
        print(f"[DEBUG] 异常: {str(e)}")  # 调试日志
        return make_response(error_response(f"执行命令失败: {str(e)}"), 500)


@bp.route("/read-log", methods=["POST"])
def read_log():
    """实时读取日志文件内容"""
    _, error = _ensure_authenticated()
    if error:
        return error
    
    data = request.get_json()
    if not data:
        return make_response(error_response("请求数据不能为空"), 400)
    
    protocol = data.get("protocol", "UNKNOWN")
    last_position = data.get("lastPosition", 0)
    
    # 根据协议获取配置
    if protocol == "RTSP":
        file_path = RTSP_CONFIG["log_file_path"]
    elif protocol == "MQTT":
        file_path = MQTT_CONFIG["log_file_path"]
    elif protocol == "SNMP":
        file_path = SNMP_CONFIG["log_file_path"]
    else:
        return make_response(error_response(f"不支持的协议类型: {protocol}"), 400)
    
    try:
        print(f"[DEBUG] 尝试读取{protocol}日志文件: {file_path}")
        print(f"[DEBUG] 上次读取位置: {last_position}")
        
        # 检查目录是否存在
        log_dir = os.path.dirname(file_path)
        if not os.path.exists(log_dir):
            print(f"[DEBUG] 日志目录不存在: {log_dir}")
            return success_response({
                "content": "",
                "position": last_position,
                "message": f"日志目录不存在: {log_dir}"
            })
        
        # 列出目录中的文件
        try:
            files_in_dir = os.listdir(log_dir)
            print(f"[DEBUG] 日志目录中的文件: {files_in_dir}")
        except Exception as e:
            print(f"[DEBUG] 无法列出目录文件: {e}")
        
        if not os.path.exists(file_path):
            print(f"[DEBUG] 日志文件不存在: {file_path}")
            return success_response({
                "content": "",
                "position": last_position,
                "message": f"日志文件尚未创建: {file_path}"
            })
        
        # 获取文件信息
        file_stat = os.stat(file_path)
        file_size = file_stat.st_size
        print(f"[DEBUG] 日志文件大小: {file_size} 字节")
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # 移动到上次读取的位置
            f.seek(last_position)
            
            # 读取新内容
            new_content = f.read()
            
            # 获取当前位置
            current_position = f.tell()
        
        print(f"[DEBUG] 读取到新内容长度: {len(new_content)} 字符")
        print(f"[DEBUG] 新的读取位置: {current_position}")
        
        if new_content:
            print(f"[DEBUG] 新内容预览: {new_content[:200]}...")
        
        return success_response({
            "content": new_content,
            "position": current_position,
            "protocol": protocol,
            "file_size": file_size,
            "message": f"成功读取{len(new_content)}字符，文件大小{file_size}字节"
        })
        
    except Exception as e:
        print(f"[DEBUG] 读取日志文件异常: {e}")
        return make_response(error_response(f"读取日志文件失败: {str(e)}"), 500)


@bp.route("/check-status", methods=["POST"])
def check_status():
    """检查协议测试状态和文件系统"""
    _, error = _ensure_authenticated()
    if error:
        return error
    
    data = request.get_json()
    if not data:
        return make_response(error_response("请求数据不能为空"), 400)
    
    protocol = data.get("protocol", "UNKNOWN")
    
    try:
        status_info = {
            "protocol": protocol,
            "timestamp": datetime.now().isoformat()
        }
        
        if protocol == "RTSP":
            # 检查RTSP相关状态
            log_file_path = RTSP_CONFIG["log_file_path"]
            log_dir = os.path.dirname(log_file_path)
            
            # 检查目录和文件状态
            status_info.update({
                "log_file_path": log_file_path,
                "log_dir": log_dir,
                "log_dir_exists": os.path.exists(log_dir),
                "log_file_exists": os.path.exists(log_file_path)
            })
            
            # 如果目录存在，列出文件
            if os.path.exists(log_dir):
                try:
                    files = os.listdir(log_dir)
                    status_info["files_in_log_dir"] = files
                except Exception as e:
                    status_info["files_in_log_dir"] = f"无法列出文件: {e}"
            
            # 如果日志文件存在，获取文件信息
            if os.path.exists(log_file_path):
                file_stat = os.stat(log_file_path)
                status_info.update({
                    "log_file_size": file_stat.st_size,
                    "log_file_mtime": datetime.fromtimestamp(file_stat.st_mtime).isoformat()
                })
            
            # 检查Docker容器状态
            try:
                result = subprocess.run(
                    "docker ps --format 'table {{.ID}}\\t{{.Image}}\\t{{.Status}}\\t{{.Ports}}'",
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10
                )
                
                if result.returncode == 0:
                    status_info["docker_containers"] = result.stdout
                else:
                    status_info["docker_error"] = result.stderr
                    
            except Exception as e:
                status_info["docker_error"] = str(e)
        
        print(f"[DEBUG] 状态检查结果: {status_info}")
        
        return success_response(status_info)
        
    except Exception as e:
        print(f"[DEBUG] 状态检查异常: {e}")
        return make_response(error_response(f"状态检查失败: {str(e)}"), 500)


@bp.route("/stop-process", methods=["POST"])
def stop_process():
    """停止指定进程"""
    _, error = _ensure_authenticated()
    if error:
        return error
    
    data = request.get_json()
    if not data:
        return make_response(error_response("请求数据不能为空"), 400)
    
    pid = data.get("pid")
    protocol = data.get("protocol", "UNKNOWN")
    
    if not pid:
        return make_response(error_response("进程ID不能为空"), 400)
    
    try:
        if os.name == 'nt':  # Windows
            subprocess.run(['taskkill', '/F', '/PID', str(pid)], check=True)
        else:  # Unix/Linux
            os.killpg(os.getpgid(pid), 9)
        
        return success_response({
            "message": f"{protocol}进程停止成功",
            "pid": pid
        })
        
    except subprocess.CalledProcessError:
        return make_response(error_response(f"进程 {pid} 不存在或已停止"), 404)
    except Exception as e:
        return make_response(error_response(f"停止进程失败: {str(e)}"), 500)


@bp.route("/stop-and-cleanup", methods=["POST"])
def stop_and_cleanup():
    """停止Docker容器并清理输出文件"""
    _, error = _ensure_authenticated()
    if error:
        return error
    
    data = request.get_json()
    if not data:
        return make_response(error_response("请求数据不能为空"), 400)
    
    container_id = data.get("container_id")
    protocol = data.get("protocol", "UNKNOWN")
    
    if not container_id:
        return make_response(error_response("容器ID不能为空"), 400)
    
    cleanup_results = {
        "container_stopped": False,
        "container_removed": False,
        "output_cleaned": False,
        "errors": []
    }
    
    try:
        print(f"[DEBUG] 开始停止和清理{protocol}容器: {container_id}")
        
        # 1. 停止Docker容器
        try:
            stop_result = subprocess.run(
                f"docker stop {container_id}",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30
            )
            
            if stop_result.returncode == 0:
                cleanup_results["container_stopped"] = True
                print(f"[DEBUG] 容器停止成功: {container_id}")
            else:
                error_msg = stop_result.stderr.strip() or "停止容器失败"
                cleanup_results["errors"].append(f"停止容器失败: {error_msg}")
                print(f"[DEBUG] 停止容器失败: {error_msg}")
                
        except subprocess.TimeoutExpired:
            cleanup_results["errors"].append("停止容器超时")
            print(f"[DEBUG] 停止容器超时")
        except Exception as e:
            cleanup_results["errors"].append(f"停止容器异常: {str(e)}")
            print(f"[DEBUG] 停止容器异常: {e}")
        
        # 2. 删除Docker容器
        try:
            remove_result = subprocess.run(
                f"docker rm -f {container_id}",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30
            )
            
            if remove_result.returncode == 0:
                cleanup_results["container_removed"] = True
                print(f"[DEBUG] 容器删除成功: {container_id}")
            else:
                error_msg = remove_result.stderr.strip() or "删除容器失败"
                cleanup_results["errors"].append(f"删除容器失败: {error_msg}")
                print(f"[DEBUG] 删除容器失败: {error_msg}")
                
        except subprocess.TimeoutExpired:
            cleanup_results["errors"].append("删除容器超时")
            print(f"[DEBUG] 删除容器超时")
        except Exception as e:
            cleanup_results["errors"].append(f"删除容器异常: {str(e)}")
            print(f"[DEBUG] 删除容器异常: {e}")
        
        # 3. 清理输出文件夹
        if protocol == "RTSP":
            output_dir = os.path.dirname(RTSP_CONFIG["log_file_path"])  # 从RTSP_CONFIG获取路径
            
            # Linux安全检查：防止删除系统重要目录
            dangerous_paths = ['/', '/home', '/usr', '/var', '/etc', '/bin', '/sbin', '/lib', '/opt']
            if output_dir in dangerous_paths or len(output_dir.strip()) < 5:
                cleanup_results["errors"].append(f"拒绝清理危险路径: {output_dir}")
                print(f"[DEBUG] 安全检查失败，拒绝清理: {output_dir}")
            else:
                try:
                    if os.path.exists(output_dir):
                        import shutil
                        import stat
                        
                        # 删除output目录下的所有文件和子目录，但保留目录本身
                        cleaned_items = []
                        failed_items = []
                        
                        for item in os.listdir(output_dir):
                            item_path = os.path.join(output_dir, item)
                            try:
                                # 处理符号链接
                                if os.path.islink(item_path):
                                    os.unlink(item_path)
                                    cleaned_items.append(f"符号链接: {item}")
                                # 处理普通文件
                                elif os.path.isfile(item_path):
                                    # Linux下处理只读文件
                                    if not os.access(item_path, os.W_OK):
                                        os.chmod(item_path, stat.S_IWRITE | stat.S_IREAD)
                                    os.remove(item_path)
                                    cleaned_items.append(f"文件: {item}")
                                # 处理目录
                                elif os.path.isdir(item_path):
                                    # 递归处理只读目录和文件
                                    def handle_remove_readonly(func, path, exc):
                                        if os.path.exists(path):
                                            os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
                                            func(path)
                                    
                                    shutil.rmtree(item_path, onerror=handle_remove_readonly)
                                    cleaned_items.append(f"目录: {item}")
                            except PermissionError as pe:
                                failed_items.append(f"{item} (权限不足: {pe})")
                            except OSError as oe:
                                failed_items.append(f"{item} (系统错误: {oe})")
                            except Exception as ie:
                                failed_items.append(f"{item} (未知错误: {ie})")
                        
                        # 设置清理结果
                        if len(failed_items) == 0:
                            cleanup_results["output_cleaned"] = True
                            print(f"[DEBUG] 输出目录完全清理成功: {output_dir}")
                            print(f"[DEBUG] 已清理项目: {cleaned_items}")
                        else:
                            cleanup_results["output_cleaned"] = len(cleaned_items) > 0
                            cleanup_results["errors"].append(f"部分文件清理失败: {failed_items}")
                            print(f"[DEBUG] 输出目录部分清理: 成功{len(cleaned_items)}项, 失败{len(failed_items)}项")
                            print(f"[DEBUG] 清理成功: {cleaned_items}")
                            print(f"[DEBUG] 清理失败: {failed_items}")
                    else:
                        cleanup_results["errors"].append(f"输出目录不存在: {output_dir}")
                        print(f"[DEBUG] 输出目录不存在: {output_dir}")
                        
                except Exception as e:
                    cleanup_results["errors"].append(f"清理输出目录失败: {str(e)}")
                    print(f"[DEBUG] 清理输出目录异常: {e}")
        
        # 构建响应消息
        success_count = sum([
            cleanup_results["container_stopped"],
            cleanup_results["container_removed"], 
            cleanup_results["output_cleaned"]
        ])
        
        if success_count == 3:
            message = f"{protocol}容器已完全停止并清理"
        elif success_count > 0:
            message = f"{protocol}容器部分清理完成 ({success_count}/3)"
        else:
            message = f"{protocol}容器清理失败"
        
        return success_response({
            "message": message,
            "container_id": container_id,
            "protocol": protocol,
            "cleanup_results": cleanup_results
        })
        
    except Exception as e:
        print(f"[DEBUG] 清理过程异常: {e}")
        return make_response(error_response(f"清理过程失败: {str(e)}"), 500)
