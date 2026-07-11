"""Legacy fuzzing request handlers."""

from __future__ import annotations

import os
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict

from flask import make_response, request

from utils.responses import error_response, success_response


# MQTT协议配置 - MBFuzzer相关路径
MQTT_CONFIG = {
    "log_file_path": os.path.join(os.path.dirname(__file__), "mbfuzzer_logs", "fuzzing_report.txt"),  # MBFuzzer日志文件路径
    "shell_command": "echo 'MBFuzzer模拟运行 - 传统MQTT broker模糊测试'",  # MBFuzzer启动命令（临时模拟）
    "output_dir": os.path.join(os.path.dirname(__file__), "mbfuzzer_logs"),  # MBFuzzer输出目录
}

# SNMP协议配置 - SNMP Fuzzer相关路径
SNMP_CONFIG = {
    "log_file_path": os.path.join(os.path.dirname(__file__), "snmpfuzzer_logs", "fuzz_output.txt"),  # SNMP Fuzzer日志文件路径
    "shell_command": "echo 'SNMP Fuzzer模拟运行'",  # SNMP Fuzzer启动命令（临时模拟）
    "output_dir": os.path.join(os.path.dirname(__file__), "snmpfuzzer_logs"),  # SNMP Fuzzer输出目录
}


def create_legacy_fuzz_handlers(
    ensure_authenticated: Callable[[], tuple[object, object]],
    *,
    logger: Any,
    subprocess_module: Any,
    to_int: Callable[[object, int], int],
    aflnet_shell_command: Callable[[], str],
    aflnet_result_path_info: Callable[[str], Dict[str, Any]],
    aflnet_log_file_for_source: Callable[[str], Path],
    aflnet_output_root: Callable[[], Path],
    aflnet_fallback_output_root: Callable[[], Path],
    resolve_aflnet_output_source: Callable[[Dict[str, Any]], str],
) -> Dict[str, Callable[..., object]]:
    def write_script():
        """写入脚本文件到指定路径"""
        _, error = ensure_authenticated()
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
            # SOL使用ProtocolGuard，不需要脚本文件，直接返回成功
            return success_response({
                "message": "SOL不需要脚本文件，直接启动docker即可生成日志",
                "filePath": "N/A",
                "size": 0,
            })
        elif protocol == "MQTT":
            # MQTT协议暂时不需要脚本文件，直接返回成功
            return success_response({
                "message": f"{protocol}协议不需要脚本文件",
                "filePath": "N/A",
                "size": 0,
            })
        else:
            return make_response(error_response(f"不支持的协议类型: {protocol}"), 400)

    def execute_command():
        """执行shell命令启动程序"""
        logger.debug("========== execute-command API被调用 ==========")

        _, error = ensure_authenticated()
        if error:
            logger.debug("认证失败: %s", error)
            return error

        data = request.get_json()
        logger.debug("接收到的请求数据: %s", data)

        if not data:
            logger.debug("请求数据为空")
            return make_response(error_response("请求数据不能为空"), 400)

        protocol = data.get("protocol", "UNKNOWN")
        protocol_implementations = data.get("protocolImplementations", [])

        logger.debug("解析参数 - 协议: %s, 实现: %s", protocol, protocol_implementations)

        # 根据协议获取配置
        if protocol == "MQTT":
            # MQTT协议支持双引擎配置
            if protocol_implementations and "SOL" in protocol_implementations:
                # SOL使用AFLNET引擎 (原RTSP配置)
                command = aflnet_shell_command()
                logger.debug("MQTT协议使用SOL实现(AFLNET引擎): %s", protocol_implementations)
            else:
                # 传统MQTT broker使用MBFuzzer引擎
                command = MQTT_CONFIG["shell_command"]
                logger.debug("MQTT协议使用传统broker实现(MBFuzzer引擎): %s", protocol_implementations)
                # 这里可以根据选择的broker实现来调整MBFuzzer的配置
                # 例如：为不同的broker设置不同的测试参数
                if protocol_implementations:
                    implementations_str = ",".join(protocol_implementations)
                    # 可以将实现信息传递给MBFuzzer作为参数
                    command = f"{command} --brokers={implementations_str}"
        elif protocol == "SNMP":
            command = SNMP_CONFIG["shell_command"]
            # SNMP协议实现信息记录到日志
            if protocol_implementations:
                logger.debug("SNMP协议实现: %s", protocol_implementations)
        else:
            return make_response(error_response(f"不支持的协议类型: {protocol}"), 400)

        try:
            logger.debug("执行命令: %s", command)

            # 对于SOL的ProtocolGuard，使用后台运行方式
            # 检查是否是SOL实现（MQTT协议 + SOL实现 或者 原RTSP协议）
            is_sol_protocol = (
                protocol == "RTSP"
                or (
                    protocol == "MQTT"
                    and protocol_implementations
                    and "SOL" in protocol_implementations
                )
            )

            if is_sol_protocol:
                # ProtocolGuard需要在后台运行，因为它是长时间运行的fuzzing任务
                # 直接执行docker命令并获取容器ID
                try:
                    result = subprocess_module.run(
                        command,
                        shell=True,
                        stdout=subprocess_module.PIPE,
                        stderr=subprocess_module.PIPE,
                        text=True,
                        timeout=30,  # 30秒超时
                    )

                    if result.returncode == 0:
                        container_id = result.stdout.strip()
                        if container_id and len(container_id) >= 12:  # Docker容器ID至少12位
                            protocol_name = "SOL" if protocol == "MQTT" else protocol
                            logger.debug("%s ProtocolGuard启动成功，容器ID: %s", protocol_name, container_id)

                            # 验证容器是否真的在运行
                            time.sleep(2)
                            check_result = subprocess_module.run(
                                f"docker ps -q --filter id={container_id}",
                                shell=True,
                                stdout=subprocess_module.PIPE,
                                stderr=subprocess_module.PIPE,
                                text=True,
                            )

                            if check_result.returncode == 0 and check_result.stdout.strip():
                                response_data = {
                                    "message": f"{protocol_name} ProtocolGuard启动成功，正在后台运行fuzzing任务",
                                    "command": command,
                                    "pid": None,  # Docker容器没有直接的PID
                                    "container_id": container_id,
                                    **aflnet_result_path_info("primary"),
                                }
                                logger.debug("返回成功响应: %s", response_data)
                                return success_response(response_data)
                            else:
                                return make_response(
                                    error_response(
                                        "容器启动后立即停止，已切换到备份 fuzz-output 数据源",
                                        aflnet_result_path_info("fallback"),
                                    ),
                                    500,
                                )
                        else:
                            error_msg = result.stderr.strip() if result.stderr.strip() else "无法获取有效的容器ID"
                            logger.debug("ProtocolGuard启动失败: %s", error_msg)
                            return make_response(error_response(f"ProtocolGuard启动失败: {error_msg}"), 500)
                    else:
                        error_msg = result.stderr.strip() if result.stderr.strip() else "Docker命令执行失败"
                        logger.debug("ProtocolGuard启动失败: %s", error_msg)
                        return make_response(error_response(f"ProtocolGuard启动失败: {error_msg}"), 500)

                except subprocess_module.TimeoutExpired:
                    return make_response(error_response("Docker容器启动超时"), 500)
                except Exception as e:
                    logger.debug("ProtocolGuard启动异常: %s", str(e))
                    return make_response(error_response(f"ProtocolGuard启动异常: {str(e)}"), 500)
            else:
                # 其他协议使用原来的方式
                result = subprocess_module.run(
                    command,
                    shell=True,
                    stdout=subprocess_module.PIPE,
                    stderr=subprocess_module.PIPE,
                    text=True,
                    timeout=30,  # 30秒超时
                )

                logger.debug("命令返回码: %s", result.returncode)

                if result.returncode == 0:
                    # 命令执行成功
                    logger.debug("命令执行成功")
                    logger.debug("stdout: %s", result.stdout)

                    # 对于docker run -d，成功的话stdout通常包含容器ID
                    container_id = result.stdout.strip() if result.stdout.strip() else "unknown"

                    return success_response({
                        "message": f"{protocol}命令执行成功",
                        "command": command,
                        "container_id": container_id,
                        "pid": "docker_container",  # Docker容器没有传统意义的PID
                    })
                else:
                    # 命令执行失败
                    error_msg = result.stderr.strip() if result.stderr.strip() else "未知错误"
                    logger.debug("命令执行失败: %s", error_msg)
                    return make_response(error_response(f"命令执行失败: {error_msg}"), 500)

        except subprocess_module.TimeoutExpired:
            logger.debug("命令执行超时")
            return make_response(error_response("命令执行超时"), 500)
        except Exception as e:
            logger.debug("异常: %s", str(e))
            return make_response(error_response(f"执行命令失败: {str(e)}"), 500)

    def read_log():
        """实时读取日志文件内容"""
        _, error = ensure_authenticated()
        if error:
            return error

        data = request.get_json()
        if not data:
            return make_response(error_response("请求数据不能为空"), 400)

        protocol = data.get("protocol", "UNKNOWN")
        last_position = data.get("lastPosition", 0)
        max_lines = to_int(str(data.get("maxLines")), 0) if data.get("maxLines") is not None else 0

        # 根据协议获取配置
        protocol_implementations = data.get("protocolImplementations", [])
        output_source = resolve_aflnet_output_source(data)
        is_sol_aflnet = (
            protocol == "MQTT"
            and protocol_implementations
            and "SOL" in protocol_implementations
        )

        if protocol == "MQTT":
            # MQTT协议支持双引擎配置
            if protocol_implementations and "SOL" in protocol_implementations:
                # SOL使用AFLNET引擎日志路径 (原RTSP配置)
                file_path = str(aflnet_log_file_for_source(output_source))
                logger.debug("MQTT协议使用SOL实现，读取AFLNET日志(%s): %s", output_source, file_path)
            else:
                # 传统MQTT broker使用MBFuzzer引擎日志路径
                file_path = MQTT_CONFIG["log_file_path"]
                logger.debug("MQTT协议使用传统broker实现，读取MBFuzzer日志: %s", file_path)
        elif protocol == "SNMP":
            file_path = SNMP_CONFIG["log_file_path"]
        else:
            return make_response(error_response(f"不支持的协议类型: {protocol}"), 400)

        try:
            logger.debug("尝试读取%s日志文件: %s", protocol, file_path)
            logger.debug("上次读取位置: %s", last_position)

            # 检查目录是否存在
            log_dir = os.path.dirname(file_path)
            if not os.path.exists(log_dir):
                logger.debug("日志目录不存在: %s", log_dir)
                response_data = {
                    "content": "",
                    "position": last_position,
                    "message": f"日志目录不存在: {log_dir}",
                }
                if is_sol_aflnet:
                    response_data.update(aflnet_result_path_info(output_source))
                    if output_source == "fallback":
                        response_data.update({
                            "is_eof": True,
                            "file_size": 0,
                            "message": (
                                "AFLNET 备份日志目录不存在，请设置 "
                                f"AFLNET_FALLBACK_OUTPUT_ROOT 或创建 {log_dir}"
                            ),
                        })
                return success_response(response_data)

            # 列出目录中的文件
            try:
                files_in_dir = os.listdir(log_dir)
                logger.debug("日志目录中的文件: %s", files_in_dir)
            except Exception as e:
                logger.debug("无法列出目录文件: %s", e)

            if not os.path.exists(file_path):
                logger.debug("日志文件不存在: %s", file_path)
                response_data = {
                    "content": "",
                    "position": last_position,
                    "message": f"日志文件尚未创建: {file_path}",
                }
                if is_sol_aflnet:
                    response_data.update(aflnet_result_path_info(output_source))
                    if output_source == "fallback":
                        response_data.update({
                            "is_eof": True,
                            "file_size": 0,
                            "message": (
                                "AFLNET 备份日志文件不存在，请确认 "
                                f"{file_path} 已生成或设置 AFLNET_FALLBACK_LOG_FILE_NAME"
                            ),
                        })
                return success_response(response_data)

            # 获取文件信息
            file_stat = os.stat(file_path)
            file_size = file_stat.st_size
            logger.debug("日志文件大小: %s 字节", file_size)

            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # 移动到上次读取的位置
                f.seek(last_position)

                # 读取新内容
                if max_lines > 0:
                    content_parts = []
                    for _ in range(max_lines):
                        line = f.readline()
                        if not line:
                            break
                        content_parts.append(line)
                    new_content = ''.join(content_parts)
                else:
                    new_content = f.read()

                # 获取当前位置
                current_position = f.tell()

            logger.debug("读取到新内容长度: %s 字符", len(new_content))
            logger.debug("新的读取位置: %s", current_position)

            if new_content:
                logger.debug("新内容预览: %s...", new_content[:200])

            response_data = {
                "content": new_content,
                "position": current_position,
                "protocol": protocol,
                "file_size": file_size,
                "is_eof": current_position >= file_size,
                "message": f"成功读取{len(new_content)}字符，文件大小{file_size}字节",
            }
            if is_sol_aflnet:
                response_data.update(aflnet_result_path_info(output_source))
            return success_response(response_data)

        except Exception as e:
            logger.debug("读取日志文件异常: %s", e)
            return make_response(error_response(f"读取日志文件失败: {str(e)}"), 500)

    def check_status():
        """检查协议测试状态和文件系统"""
        _, error = ensure_authenticated()
        if error:
            return error

        data = request.get_json()
        if not data:
            return make_response(error_response("请求数据不能为空"), 400)

        protocol = data.get("protocol", "UNKNOWN")

        try:
            status_info = {
                "protocol": protocol,
                "timestamp": datetime.now().isoformat(),
            }

            if protocol == "MQTT":
                # MQTT协议支持双引擎配置，需要检查协议实现
                protocol_implementations = data.get("protocolImplementations", [])

                if protocol_implementations and "SOL" in protocol_implementations:
                    # 检查SOL相关状态 (使用AFLNET引擎)
                    log_file_path = str(aflnet_log_file_for_source("primary"))
                    status_info["engine"] = "AFLNET"
                    status_info["implementation"] = "SOL"
                    status_info.update(aflnet_result_path_info("primary"))
                    fallback_info = aflnet_result_path_info("fallback")
                    fallback_log_path = fallback_info["logFilePath"]
                    fallback_info.update({
                        "logDirExists": os.path.exists(os.path.dirname(fallback_log_path)),
                        "logFileExists": os.path.exists(fallback_log_path),
                    })
                    status_info["fallbackOutput"] = fallback_info
                else:
                    # 检查传统MQTT broker状态 (使用MBFuzzer引擎)
                    log_file_path = MQTT_CONFIG["log_file_path"]
                    status_info["engine"] = "MBFuzzer"
                    status_info["implementation"] = protocol_implementations

                log_dir = os.path.dirname(log_file_path)

                # 检查目录和文件状态
                status_info.update({
                    "log_file_path": log_file_path,
                    "log_dir": log_dir,
                    "log_dir_exists": os.path.exists(log_dir),
                    "log_file_exists": os.path.exists(log_file_path),
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
                        "log_file_mtime": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                    })

                # 检查Docker容器状态
                try:
                    result = subprocess_module.run(
                        "docker ps --format 'table {{.ID}}\\t{{.Image}}\\t{{.Status}}\\t{{.Ports}}'",
                        shell=True,
                        stdout=subprocess_module.PIPE,
                        stderr=subprocess_module.PIPE,
                        text=True,
                        timeout=10,
                    )

                    if result.returncode == 0:
                        status_info["docker_containers"] = result.stdout
                    else:
                        status_info["docker_error"] = result.stderr

                except Exception as e:
                    status_info["docker_error"] = str(e)

            logger.debug("状态检查结果: %s", status_info)

            return success_response(status_info)

        except Exception as e:
            logger.debug("状态检查异常: %s", e)
            return make_response(error_response(f"状态检查失败: {str(e)}"), 500)

    def stop_process():
        """停止指定进程"""
        _, error = ensure_authenticated()
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
                subprocess_module.run(['taskkill', '/F', '/PID', str(pid)], check=True)
            else:  # Unix/Linux
                os.killpg(os.getpgid(pid), 9)

            return success_response({
                "message": f"{protocol}进程停止成功",
                "pid": pid,
            })

        except subprocess_module.CalledProcessError:
            return make_response(error_response(f"进程 {pid} 不存在或已停止"), 404)
        except Exception as e:
            return make_response(error_response(f"停止进程失败: {str(e)}"), 500)

    def pre_start_cleanup():
        """启动前清理：停止现有容器并清理输出文件"""
        logger.debug("========== 启动前清理API被调用 ==========")

        _, error = ensure_authenticated()
        if error:
            logger.debug("认证失败: %s", error)
            return error

        data = request.get_json()
        logger.debug("接收到的请求数据: %s", data)

        if not data:
            logger.debug("请求数据为空")
            return make_response(error_response("请求数据不能为空"), 400)

        protocol = data.get("protocol", "UNKNOWN")

        logger.debug("解析参数 - 协议: %s", protocol)

        cleanup_results = {
            "containers_stopped": 0,
            "containers_removed": 0,
            "output_cleaned": False,
            "errors": [],
        }

        try:
            logger.debug("开始启动前清理 - 协议: %s", protocol)

            # 1. 查找并停止所有相关的Docker容器
            if protocol == "RTSP" or protocol == "MQTT":
                # 查找protocolguard容器
                find_result = subprocess_module.run(
                    "docker ps -q --filter ancestor=protocolguard:latest",
                    shell=True,
                    stdout=subprocess_module.PIPE,
                    stderr=subprocess_module.PIPE,
                    text=True,
                )

                if find_result.returncode == 0 and find_result.stdout.strip():
                    container_ids = find_result.stdout.strip().split('\n')
                    logger.debug("找到 %s 个运行中的protocolguard容器", len(container_ids))

                    for container_id in container_ids:
                        if container_id:
                            try:
                                # 停止容器
                                stop_result = subprocess_module.run(
                                    f"docker stop {container_id}",
                                    shell=True,
                                    stdout=subprocess_module.PIPE,
                                    stderr=subprocess_module.PIPE,
                                    text=True,
                                    timeout=30,
                                )

                                if stop_result.returncode == 0:
                                    cleanup_results["containers_stopped"] += 1
                                    logger.debug("容器停止成功: %s", container_id)

                                    # 删除容器
                                    remove_result = subprocess_module.run(
                                        f"docker rm {container_id}",
                                        shell=True,
                                        stdout=subprocess_module.PIPE,
                                        stderr=subprocess_module.PIPE,
                                        text=True,
                                        timeout=30,
                                    )

                                    if remove_result.returncode == 0:
                                        cleanup_results["containers_removed"] += 1
                                        logger.debug("容器删除成功: %s", container_id)
                                    else:
                                        error_msg = remove_result.stderr.strip() or "删除容器失败"
                                        cleanup_results["errors"].append(f"删除容器失败 {container_id}: {error_msg}")
                                else:
                                    error_msg = stop_result.stderr.strip() or "停止容器失败"
                                    cleanup_results["errors"].append(f"停止容器失败 {container_id}: {error_msg}")

                            except subprocess_module.TimeoutExpired:
                                cleanup_results["errors"].append(f"操作容器超时: {container_id}")
                            except Exception as e:
                                cleanup_results["errors"].append(f"操作容器异常 {container_id}: {str(e)}")
                else:
                    logger.debug("没有找到运行中的protocolguard容器")

            # 2. 清理输出文件夹
            if protocol == "RTSP" or protocol == "MQTT":
                output_dir = str(aflnet_output_root())
                fallback_output_dir = str(aflnet_fallback_output_root().resolve())

                # Linux安全检查：防止删除系统重要目录
                dangerous_paths = ['/', '/home', '/usr', '/var', '/etc', '/bin', '/sbin', '/lib', '/opt']
                if str(Path(output_dir).resolve()) == fallback_output_dir:
                    cleanup_results["errors"].append(f"拒绝清理备份输出目录: {output_dir}")
                    logger.debug("安全检查失败，拒绝清理备份输出目录: %s", output_dir)
                elif output_dir in dangerous_paths or len(output_dir.strip()) < 5:
                    cleanup_results["errors"].append(f"拒绝清理危险路径: {output_dir}")
                    logger.debug("安全检查失败，拒绝清理: %s", output_dir)
                else:
                    try:
                        if os.path.exists(output_dir):
                            # 删除output目录下的所有文件和子目录，但保留目录本身
                            cleaned_items = []
                            failed_items = []

                            for item in os.listdir(output_dir):
                                item_path = os.path.join(output_dir, item)
                                try:
                                    if os.path.isdir(item_path):
                                        shutil.rmtree(item_path)
                                    else:
                                        os.remove(item_path)
                                    cleaned_items.append(item)
                                except Exception as e:
                                    failed_items.append(f"{item}: {str(e)}")

                            if cleaned_items:
                                cleanup_results["output_cleaned"] = True
                                logger.debug("输出目录清理成功，删除了 %s 个项目", len(cleaned_items))

                            if failed_items:
                                cleanup_results["errors"].extend([f"清理失败: {item}" for item in failed_items])
                        else:
                            logger.debug("输出目录不存在: %s", output_dir)
                            cleanup_results["output_cleaned"] = True  # 目录不存在也算清理成功

                    except Exception as e:
                        cleanup_results["errors"].append(f"清理输出目录异常: {str(e)}")
                        logger.debug("清理输出目录异常: %s", e)

            logger.debug("启动前清理完成: %s", cleanup_results)

            return success_response({
                "message": "启动前清理完成",
                "cleanup_results": cleanup_results,
            })

        except Exception as e:
            logger.debug("启动前清理异常: %s", e)
            cleanup_results["errors"].append(f"清理过程异常: {str(e)}")

            return success_response({
                "message": "启动前清理部分完成",
                "cleanup_results": cleanup_results,
            })

    def stop_and_cleanup():
        """停止Docker容器并清理输出文件"""
        logger.debug("========== 停止和清理API被调用 ==========")

        _, error = ensure_authenticated()
        if error:
            logger.debug("认证失败: %s", error)
            return error

        data = request.get_json()
        logger.debug("接收到的请求数据: %s", data)

        if not data:
            logger.debug("请求数据为空")
            return make_response(error_response("请求数据不能为空"), 400)

        container_id = data.get("container_id")
        protocol = data.get("protocol", "UNKNOWN")

        logger.debug("解析参数 - 容器ID: %s, 协议: %s", container_id, protocol)

        if not container_id:
            logger.debug("容器ID为空")
            return make_response(error_response("容器ID不能为空"), 400)

        stop_results = {
            "container_stopped": False,
            "container_removed": False,
            "errors": [],
        }

        try:
            logger.debug("开始停止和清理%s容器: %s", protocol, container_id)

            # 首先检查容器是否存在
            check_result = subprocess_module.run(
                f"docker ps -a -q --filter id={container_id}",
                shell=True,
                stdout=subprocess_module.PIPE,
                stderr=subprocess_module.PIPE,
                text=True,
            )

            if check_result.returncode == 0 and check_result.stdout.strip():
                logger.debug("找到容器: %s", check_result.stdout.strip())
            else:
                logger.debug("容器不存在或查找失败: %s", check_result.stderr)
                stop_results["errors"].append(f"容器不存在: {container_id}")

            # 检查容器是否正在运行
            running_check = subprocess_module.run(
                f"docker ps -q --filter id={container_id}",
                shell=True,
                stdout=subprocess_module.PIPE,
                stderr=subprocess_module.PIPE,
                text=True,
            )

            if running_check.returncode == 0 and running_check.stdout.strip():
                logger.debug("容器正在运行，需要停止: %s", running_check.stdout.strip())
            else:
                logger.debug("容器未在运行或已停止")

            # 1. 停止Docker容器（使用更短的超时时间）
            try:
                stop_result = subprocess_module.run(
                    f"docker stop -t 10 {container_id}",  # 给容器10秒时间优雅停止
                    shell=True,
                    stdout=subprocess_module.PIPE,
                    stderr=subprocess_module.PIPE,
                    text=True,
                    timeout=15,  # 总超时时间15秒
                )

                if stop_result.returncode == 0:
                    stop_results["container_stopped"] = True
                    logger.debug("容器停止成功: %s", container_id)
                else:
                    error_msg = stop_result.stderr.strip() or "停止容器失败"
                    stop_results["errors"].append(f"停止容器失败: {error_msg}")
                    logger.debug("停止容器失败: %s", error_msg)

            except subprocess_module.TimeoutExpired:
                stop_results["errors"].append("停止容器超时")
                logger.debug("停止容器超时")
            except Exception as e:
                stop_results["errors"].append(f"停止容器异常: {str(e)}")
                logger.debug("停止容器异常: %s", e)

            # 2. 删除Docker容器
            try:
                remove_result = subprocess_module.run(
                    f"docker rm -f {container_id}",
                    shell=True,
                    stdout=subprocess_module.PIPE,
                    stderr=subprocess_module.PIPE,
                    text=True,
                    timeout=10,  # 删除操作通常很快
                )

                if remove_result.returncode == 0:
                    stop_results["container_removed"] = True
                    logger.debug("容器删除成功: %s", container_id)
                else:
                    error_msg = remove_result.stderr.strip() or "删除容器失败"
                    stop_results["errors"].append(f"删除容器失败: {error_msg}")
                    logger.debug("删除容器失败: %s", error_msg)

            except subprocess_module.TimeoutExpired:
                stop_results["errors"].append("删除容器超时")
                logger.debug("删除容器超时")
            except Exception as e:
                stop_results["errors"].append(f"删除容器异常: {str(e)}")
                logger.debug("删除容器异常: %s", e)

            logger.debug("容器停止完成: %s", stop_results)

            # 构建响应消息
            success_count = sum([
                stop_results["container_stopped"],
                stop_results["container_removed"],
            ])

            if success_count == 2:
                message = f"{protocol}容器已完全停止，输出文件已保留供查看"
            elif success_count > 0:
                message = f"{protocol}容器部分停止完成 ({success_count}/2)，输出文件已保留"
            else:
                message = f"{protocol}容器停止失败"

            return success_response({
                "message": message,
                "container_id": container_id,
                "protocol": protocol,
                "stop_results": stop_results,
            })

        except Exception as e:
            logger.debug("停止过程异常: %s", e)
            stop_results["errors"].append(f"停止过程异常: {str(e)}")

            return success_response({
                "message": f"{protocol}容器停止部分完成",
                "container_id": container_id,
                "protocol": protocol,
                "stop_results": stop_results,
            })

    return {
        "write_script": write_script,
        "execute_command": execute_command,
        "read_log": read_log,
        "check_status": check_status,
        "stop_process": stop_process,
        "pre_start_cleanup": pre_start_cleanup,
        "stop_and_cleanup": stop_and_cleanup,
    }
