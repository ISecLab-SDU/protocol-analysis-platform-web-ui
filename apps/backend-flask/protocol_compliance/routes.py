"""Flask blueprints for the protocol compliance domain."""

from __future__ import annotations

import contextlib
import logging
import json
import re
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
    
import os  
import sqlite3  
import uuid  
from datetime import datetime  
  
# 新增的路由端点  
  
@bp.route("/detection-results/<implementation_name>", methods=["GET"])  
def get_detection_results(implementation_name: str):  
    """获取指定协议实现的检测结果"""  
    _, error = _ensure_authenticated()  
    if error:  
        return error  
      
    # 数据库文件路径  
    db_path = os.path.join(  
        os.path.dirname(__file__),   
        "databases",   
        f"sqlite_{implementation_name}.db"  
    )  
      
    # 检查文件是否存在  
    if not os.path.exists(db_path):  
        return make_response(  
            error_response(f"未找到协议实现 '{implementation_name}' 的数据库文件"),   
            404  
        )  
      
    try:  
        conn = sqlite3.connect(db_path)  
        conn.row_factory = sqlite3.Row  
        cursor = conn.cursor()  
          
        # 从 rule_code_snippet 表读取数据  
        cursor.execute("""  
            SELECT rule_desc, code_snippet, llm_response   
            FROM rule_code_snippet  
        """)  
          
        rows = cursor.fetchall()  
        items = []  
          
        for idx, row in enumerate(rows):  
            # 解析 JSON 格式的 llm_response  
            llm_response = {}  
            if row['llm_response']:  
                try:  
                    llm_response = json.loads(row['llm_response'])  
                except json.JSONDecodeError:  
                    llm_response = {'result': 'error', 'reason': '解析失败'}  
              
            items.append({  
                'id': idx + 1,  # 使用索引作为 id  
                'rule_desc': row['rule_desc'],  
                'code_snippet': row['code_snippet'],  
                'llm_response': llm_response  
            })  
          
        conn.close()  
        return success_response({'items': items})  
          
    except sqlite3.Error as e:  
        return make_response(  
            error_response(f"数据库读取错误: {str(e)}"),   
            500  
        )  
  
  
@bp.route("/available-implementations", methods=["GET"])  
def list_available_implementations():  
    """获取所有可用的协议实现列表"""  
    _, error = _ensure_authenticated()  
    if error:  
        return error  
      
    db_dir = os.path.join(os.path.dirname(__file__), "databases")  
      
    if not os.path.exists(db_dir):  
        return success_response({'items': []})  
      
    # 扫描目录中的所有 .db 文件  
    implementations = []  
    for filename in os.listdir(db_dir):  
        if filename.startswith("sqlite_") and filename.endswith(".db"):  
            # 提取实现名称（去掉 sqlite_ 前缀和 .db 后缀）  
            impl_name = filename[7:-3]  
            implementations.append(impl_name)  
      
    return success_response({'items': implementations})  
  
  
@bp.route("/analysis-history", methods=["GET"])  
def get_analysis_history():  
    """获取历史记录"""  
    _, error = _ensure_authenticated()  
    if error:  
        return error  
      
    history_file = os.path.join(os.path.dirname(__file__), "query_history.json")  
      
    if not os.path.exists(history_file):  
        return success_response({'items': []})  
      
    try:  
        with open(history_file, 'r', encoding='utf-8') as f:  
            history = json.load(f)  
        return success_response({'items': history})  
    except (json.JSONDecodeError, IOError) as e:  
        return make_response(  
            error_response(f"读取历史记录失败: {str(e)}"),   
            500  
        )  
  
  
@bp.route("/analysis-history", methods=["POST"])  
def add_analysis_history():  
    """添加历史记录"""  
    _, error = _ensure_authenticated()  
    if error:  
        return error  
      
    data = request.get_json()  
    implementation_name = data.get('implementationName')  
    protocol_name = data.get('protocolName')  
      
    if not implementation_name or not protocol_name:  
        return make_response(  
            error_response("缺少必要参数"),   
            400  
        )  
      
    # 读取数据库统计信息  
    db_path = os.path.join(  
        os.path.dirname(__file__),   
        "databases",   
        f"sqlite_{implementation_name}.db"  
    )  
      
    statistics = {'total': 0, 'violations': 0, 'noViolations': 0, 'noResult': 0}  
      
    if os.path.exists(db_path):  
        try:  
            conn = sqlite3.connect(db_path)  
            cursor = conn.cursor()  
              
            # 从 rule_code_snippet 表读取  
            cursor.execute("SELECT llm_response FROM rule_code_snippet")  
            rows = cursor.fetchall()  
              
            statistics['total'] = len(rows)  
            for row in rows:  
                if row[0]:  
                    try:  
                        response = json.loads(row[0])  
                        result = response.get('result', '').lower()  
                        if 'no violation' in result:  
                            statistics['noViolations'] += 1  
                        elif 'violation' in result:  
                            statistics['violations'] += 1  
                        else:  
                            statistics['noResult'] += 1  
                    except json.JSONDecodeError:  
                        statistics['noResult'] += 1  
              
            conn.close()  
        except sqlite3.Error:  
            pass  
      
    # 保存历史记录  
    history_file = os.path.join(os.path.dirname(__file__), "query_history.json")  
    history = []  
      
    if os.path.exists(history_file):  
        try:  
            with open(history_file, 'r', encoding='utf-8') as f:  
                history = json.load(f)  
        except (json.JSONDecodeError, IOError):  
            history = []  
      
    history.insert(0, {  
        'id': str(uuid.uuid4()),  
        'implementationName': implementation_name,  
        'protocolName': protocol_name,  
        'statistics': statistics,  
        'createdAt': datetime.now().isoformat()  
    })  
      
    # 只保留最近 50 条记录  
    history = history[:50]  
      
    try:  
        with open(history_file, 'w', encoding='utf-8') as f:  
            json.dump(history, f, ensure_ascii=False, indent=2)  
    except IOError as e:  
        return make_response(  
            error_response(f"保存历史记录失败: {str(e)}"),   
            500  
        )  
      
    return success_response({'message': '已添加到历史记录'})
