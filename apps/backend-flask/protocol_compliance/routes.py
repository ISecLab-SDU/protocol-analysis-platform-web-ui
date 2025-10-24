"""Flask blueprints for the protocol compliance domain."""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import subprocess
import threading
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, cast

import toml
from flask import Blueprint, make_response, request, send_file
from werkzeug.datastructures import FileStorage

try:
    from ..utils.auth import verify_access_token
    from ..utils.responses import error_response, paginate, success_response, unauthorized
except ImportError:
    from utils.auth import verify_access_token
    from utils.responses import error_response, paginate, success_response, unauthorized
from .analysis import (
    delete_static_analysis_job,
    extract_protocol_version,
    get_static_analysis_job,
    get_static_analysis_result,
    list_static_analysis_history,
    normalize_protocol_name,
    submit_static_analysis_job,
    try_extract_rules_summary,
)
from .assertion import (
    get_assert_generation_job,
    get_assert_generation_result,
    get_assert_generation_zip_path,
    submit_assert_generation_job,
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


def _extract_protocol_metadata_from_config(
    raw: Optional[bytes], source_label: str
) -> tuple[Optional[str], Optional[str]]:
    if not raw:
        LOGGER.debug("Config payload %s is empty; skipping protocol metadata extraction", source_label)
        return None, None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        LOGGER.warning("Failed to decode %s as UTF-8 while extracting protocol metadata: %s", source_label, exc)
        return None, None
    try:
        parsed = toml.loads(text)
    except toml.TomlDecodeError as exc:
        LOGGER.warning("Failed to parse %s as TOML while extracting protocol metadata: %s", source_label, exc)
        return None, None

    project = parsed.get("project")
    if isinstance(project, dict):
        raw_name = project.get("protocol_name") or project.get("protocol")
        raw_version = project.get("protocol_version") or project.get("version")
        name = raw_name.strip() if isinstance(raw_name, str) else None
        version = raw_version.strip() if isinstance(raw_version, str) else None
        return (name or None, version or None)

    LOGGER.debug(
        "Config %s does not define a [project] section when extracting protocol metadata", source_label
    )
    return None, None


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
        return make_response(
            error_response("请上传源码、Builder Dockerfile、协议规则和配置文件"), 400
        )

    uploads_map = {
        "codeArchive": request.files.get("codeArchive"),
        "builderDockerfile": request.files.get("builderDockerfile"),
        "rules": request.files.get("rules"),
        "config": request.files.get("config"),
    }

    missing = [
        key for key, value in uploads_map.items() if not isinstance(value, FileStorage)
    ]
    if missing:
        labels = {
            "codeArchive": "源码压缩包",
            "builderDockerfile": "Builder Dockerfile",
            "rules": "协议规则 JSON",
            "config": "分析配置 TOML",
        }
        readable = "、".join(labels.get(item, item) for item in missing)
        return make_response(
            error_response(f"请上传完整文件：{readable}"), 400
        )

    code_upload = cast(FileStorage, uploads_map["codeArchive"])
    builder_upload = cast(FileStorage, uploads_map["builderDockerfile"])
    rules_upload = cast(FileStorage, uploads_map["rules"])
    config_upload = cast(FileStorage, uploads_map["config"])

    code_name, code_data = _read_upload(code_upload)
    builder_name, builder_data = _read_upload(builder_upload)
    rules_name, rules_data = _read_upload(rules_upload)
    config_name, config_data = _read_upload(config_upload)

    if code_data is None or builder_data is None or config_data is None or rules_data is None:
        return make_response(error_response("上传的文件内容为空，请重新上传"), 400)

    parsed_rules = None
    if rules_data:
        try:
            parsed_rules = json.loads(rules_data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            parsed_rules = None

    config_protocol_name, config_protocol_version = _extract_protocol_metadata_from_config(config_data, config_name)

    rules_protocol_fallback = normalize_protocol_name(parsed_rules, _strip_extension(rules_name))
    protocol_name = config_protocol_name or rules_protocol_fallback
    if config_protocol_name:
        LOGGER.info(
            "Static analysis protocol resolved from config %s: %s",
            config_name,
            config_protocol_name,
        )
    else:
        LOGGER.info(
            "Static analysis protocol falling back to %s (config %s missing protocol_name)",
            rules_protocol_fallback,
            config_name,
        )

    rules_version_fallback = extract_protocol_version(parsed_rules, None)
    protocol_version = config_protocol_version or rules_version_fallback
    if config_protocol_version:
        LOGGER.info(
            "Static analysis protocol version resolved from config %s: %s",
            config_name,
            config_protocol_version,
        )
    elif rules_version_fallback:
        LOGGER.info(
            "Static analysis protocol version falling back to %s (config %s missing protocol_version)",
            rules_version_fallback,
            config_name,
        )
    rules_summary = try_extract_rules_summary(parsed_rules)
    notes = request.form.get("notes")

    snapshot = submit_static_analysis_job(
        code_payload=(code_name, code_data),
        builder_payload=(builder_name, builder_data),
        config_payload=(config_name, config_data),
        rules_payload=(rules_name, rules_data),
        notes=notes,
        protocol_name=protocol_name,
        protocol_version=protocol_version,
        rules_summary=rules_summary,
    )
    return make_response(success_response(snapshot), 202)


@bp.route("/static-analysis/history", methods=["GET"])
def static_analysis_history():
    _, error = _ensure_authenticated()
    if error:
        return error

    limit = _to_int(request.args.get("limit"), 50)
    limit = max(1, min(limit, 200))
    history = list_static_analysis_history(limit=limit)
    payload = success_response({"items": history, "limit": limit, "count": len(history)})
    return make_response(payload, 200)


@bp.route("/static-analysis/history/<job_id>", methods=["DELETE"])
def delete_static_analysis_history(job_id: str):
    """Delete a static analysis job from the history."""
    _, error = _ensure_authenticated()
    if error:
        return error

    if not job_id or not isinstance(job_id, str):
        return make_response(error_response("无效的任务 ID"), 400)

    try:
        deleted = delete_static_analysis_job(job_id)
        if not deleted:
            return make_response(error_response("任务不存在"), 404)
        return make_response(success_response({"jobId": job_id, "deleted": True}), 200)
    except Exception as exc:
        LOGGER.error("Failed to delete static analysis job %s: %s", job_id, exc)
        return make_response(error_response(f"删除失败：{str(exc)}"), 500)


def _expand_path(raw: Optional[str]) -> Optional[Path]:
    if not raw or not isinstance(raw, str):
        return None
    try:
        return Path(raw).expanduser()
    except (OSError, ValueError):
        return None


def _find_sqlite_file(
    database_path: Optional[str],
    workspace_path: Optional[str],
) -> tuple[Optional[Path], list[str]]:
    """Resolve the SQLite database path, collecting warnings."""
    warnings: list[str] = []

    candidate = _expand_path(database_path)
    if candidate and candidate.is_file():
        return candidate, warnings
    if candidate and not candidate.exists():
        warnings.append(f"指定的数据库路径不存在：{candidate}")

    workspace = _expand_path(workspace_path)
    if workspace:
        if workspace.is_dir():
            matches = sorted(workspace.glob("sqlite_*.db"))
            if matches:
                return matches[0], warnings
            warnings.append(
                f"在工作目录 {workspace} 中未找到 sqlite_*.db 文件"
            )
        else:
            warnings.append(f"工作目录不存在或不可访问：{workspace}")

    return None, warnings


def _parse_llm_response(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, str):
        payload = payload.strip()
        if not payload or payload.lower() == "null":
            return {}
        try:
            decoded = json.loads(payload)
        except json.JSONDecodeError:
            return {"raw": payload}
        payload = decoded
    if isinstance(payload, dict):
        return payload
    return {}


def _classify_rule_result(llm_payload: Dict[str, Any]) -> tuple[str, str]:
    result_text = str(llm_payload.get("result") or "").lower()
    if "violation" in result_text and "no violation" not in result_text:
        return "violation_found", "发现违规"
    if "no violation" in result_text:
        return "no_violation", "未发现违规"
    return "unknown", "未判定"


@bp.route("/static-analysis/database-insights", methods=["POST"])
def static_analysis_database_insights():
    _, error = _ensure_authenticated()
    if error:
        return error

    payload = request.get_json(silent=True)
    if payload is None:
        return make_response(
            error_response("请求体必须为 JSON 对象"),
            400,
        )
    if not isinstance(payload, dict):
        return make_response(
            error_response("请求体必须为 JSON 对象"),
            400,
        )

    job_id = payload.get("jobId")
    database_path_raw = cast(Optional[str], payload.get("databasePath"))
    workspace_path_raw = cast(Optional[str], payload.get("workspacePath"))

    LOGGER.info(
        "Static analysis database insights requested",
        extra={
            "jobId": job_id,
            "databasePath": database_path_raw,
            "workspacePath": workspace_path_raw,
        },
    )

    resolved_path, warnings = _find_sqlite_file(database_path_raw, workspace_path_raw)
    if not resolved_path:
        detail = {
            "jobId": job_id,
            "databasePath": database_path_raw,
            "workspacePath": workspace_path_raw,
            "warnings": warnings or None,
        }
        LOGGER.warning(
            "Unable to resolve SQLite database for static analysis insights",
            extra=detail,
        )
        return make_response(
            error_response("未找到静态分析结果数据库文件", detail),
            404,
        )

    LOGGER.info(
        "Resolved static analysis database file",
        extra={
            "jobId": job_id,
            "databasePath": str(resolved_path),
            "workspacePath": workspace_path_raw,
        },
    )

    try:
        conn = sqlite3.connect(resolved_path)
    except sqlite3.Error as exc:
        detail = {
            "jobId": job_id,
            "databasePath": str(resolved_path),
            "exception": exc.__class__.__name__,
            "args": [str(item) for item in exc.args],
        }
        LOGGER.exception(
            "Failed to open SQLite database for static analysis insights",
            extra=detail,
        )
        return make_response(
            error_response("无法打开静态分析结果数据库", detail),
            500,
        )

    conn.row_factory = sqlite3.Row

    query = (
        "SELECT rule_desc, code_snippet, call_graph, llm_response "
        "FROM rule_code_snippet"
    )
    try:
        cursor = conn.execute(query)
        rows = cursor.fetchall()
    except sqlite3.Error as exc:
        detail = {
            "jobId": job_id,
            "databasePath": str(resolved_path),
            "exception": exc.__class__.__name__,
            "args": [str(item) for item in exc.args],
            "query": query,
        }
        LOGGER.exception(
            "Failed to query rule_code_snippet from SQLite database",
            extra=detail,
        )
        conn.close()
        return make_response(
            error_response("读取静态分析规则结果失败", detail),
            500,
        )

    findings: List[Dict[str, Any]] = []
    parsing_warnings: List[str] = []

    for row in rows:
        rule_desc = row["rule_desc"]
        code_snippet = row["code_snippet"]
        call_graph = row["call_graph"]
        raw_llm_response = row["llm_response"]

        llm_payload = _parse_llm_response(raw_llm_response)
        result_status, result_label = _classify_rule_result(llm_payload)

        reason = llm_payload.get("reason")
        if isinstance(reason, str):
            reason = reason.strip()
        elif reason is not None:
            reason = json.dumps(reason, ensure_ascii=False)

        violations_payload = llm_payload.get("violations")
        violations: List[Dict[str, Any]] = []
        if isinstance(violations_payload, list):
            for entry in violations_payload:
                if not isinstance(entry, dict):
                    continue
                code_lines = entry.get("code_lines") or entry.get("codeLines")
                if isinstance(code_lines, list):
                    lines = []
                    for item in code_lines:
                        try:
                            lines.append(int(item))
                        except (TypeError, ValueError):
                            continue
                    code_lines = lines or None
                else:
                    code_lines = None
                violations.append(
                    {
                        "filename": entry.get("filename"),
                        "functionName": entry.get("function_name") or entry.get("functionName"),
                        "codeLines": code_lines,
                    }
                )

        findings.append(
            {
                "ruleDesc": rule_desc,
                "codeSnippet": code_snippet,
                "callGraph": call_graph,
                "llmRaw": raw_llm_response,
                "reason": reason,
                "result": result_status,
                "resultLabel": result_label,
                "violations": violations or None,
            }
        )

        if not llm_payload and raw_llm_response:
            parsing_warnings.append(
                f"规则[{rule_desc}]的 LLM 结果无法解析为 JSON，已返回原始字符串"
            )

    conn.close()

    response_payload: Dict[str, Any] = {
        "databasePath": str(resolved_path),
        "workspacePath": workspace_path_raw,
        "extractedAt": datetime.now(timezone.utc).isoformat(),
        "findings": findings,
    }
    all_warnings = warnings + parsing_warnings
    if all_warnings:
        response_payload["warnings"] = all_warnings

    LOGGER.info(
        "Static analysis database insights resolved",
        extra={
            "jobId": job_id,
            "databasePath": str(resolved_path),
            "findings": len(findings),
            "warnings": all_warnings,
        },
    )

    return make_response(success_response(response_payload), 200)


@bp.route("/static-analysis/<job_id>/progress", methods=["GET"])
def static_analysis_progress(job_id: str):
    _, error = _ensure_authenticated()
    if error:
        return error

    snapshot = get_static_analysis_job(job_id)
    if not snapshot:
        return make_response(error_response("未找到静态分析任务"), 404)
    return make_response(success_response(snapshot), 200)


@bp.route("/static-analysis/<job_id>/result", methods=["GET"])
def static_analysis_result(job_id: str):
    _, error = _ensure_authenticated()
    if error:
        return error

    result = get_static_analysis_result(job_id)
    if result is None:
        snapshot = get_static_analysis_job(job_id)
        if not snapshot:
            return make_response(error_response("未找到静态分析任务"), 404)
        status = snapshot.get("status")
        return make_response(
            error_response("静态分析任务尚未完成", {"status": status}),
            409,
        )
    return make_response(success_response(result), 200)


@bp.route("/assertion-generation", methods=["POST"])
def assertion_generation():
    _, error = _ensure_authenticated()
    if error:
        return error

    if not request.files:
        return make_response(error_response("请上传源码压缩包和违规数据库"), 400)

    uploads_map = {
        "codeArchive": request.files.get("codeArchive"),
        "database": request.files.get("database"),
    }

    missing = [key for key, value in uploads_map.items() if not isinstance(value, FileStorage)]
    if missing:
        labels = {
            "codeArchive": "源码压缩包",
            "database": "违规数据库文件",
        }
        readable = "、".join(labels.get(item, item) for item in missing)
        return make_response(error_response(f"请上传完整文件：{readable}"), 400)

    code_upload = cast(FileStorage, uploads_map["codeArchive"])
    database_upload = cast(FileStorage, uploads_map["database"])

    code_name, code_data = _read_upload(code_upload)
    database_name, database_data = _read_upload(database_upload)

    if not code_data or not database_data:
        return make_response(error_response("上传的文件内容为空，请重新上传"), 400)

    build_instructions_raw = request.form.get("buildInstructions", "")
    notes = request.form.get("notes")

    LOGGER.info(
        "Assertion generation job requested",
        extra={
            "codeArchive": code_name,
            "database": database_name,
            "hasBuildInstructions": bool(build_instructions_raw.strip()),
            "notesLength": len(notes.strip()) if isinstance(notes, str) else 0,
        },
    )

    snapshot = submit_assert_generation_job(
        code_payload=(code_name, code_data),
        database_payload=(database_name, database_data),
        build_instructions=build_instructions_raw,
        notes=notes,
    )
    return make_response(success_response(snapshot), 202)


@bp.route("/assertion-generation/<job_id>/progress", methods=["GET"])
def assertion_generation_progress(job_id: str):
    _, error = _ensure_authenticated()
    if error:
        return error

    snapshot = get_assert_generation_job(job_id)
    if not snapshot:
        return make_response(error_response("未找到断言生成任务"), 404)
    return make_response(success_response(snapshot), 200)


@bp.route("/assertion-generation/<job_id>/result", methods=["GET"])
def assertion_generation_result(job_id: str):
    _, error = _ensure_authenticated()
    if error:
        return error

    result = get_assert_generation_result(job_id)
    if result is None:
        snapshot = get_assert_generation_job(job_id)
        if not snapshot:
            return make_response(error_response("未找到断言生成任务"), 404)
        status = snapshot.get("status")
        return make_response(
            error_response("断言生成任务尚未完成", {"status": status}),
            409,
        )
    return make_response(success_response(result), 200)


@bp.route("/assertion-generation/<job_id>/download", methods=["GET"])
def assertion_generation_download(job_id: str):
    _, error = _ensure_authenticated()
    if error:
        return error

    snapshot = get_assert_generation_job(job_id)
    if not snapshot:
        return make_response(error_response("未找到断言生成任务"), 404)

    if snapshot.get("status") != "completed":
        return make_response(
            error_response("断言生成任务尚未完成", {"status": snapshot.get("status")}),
            409,
        )

    zip_path = get_assert_generation_zip_path(job_id)
    if not zip_path:
        return make_response(error_response("未找到断言生成结果压缩包"), 404)

    download_name = f"assertion-generation-{job_id}.zip"
    return send_file(
        zip_path,
        mimetype="application/zip",
        as_attachment=True,
        download_name=download_name,
        max_age=0,
    )


def _strip_extension(filename: str) -> str:
    if "." not in filename:
        return filename
    return filename.rsplit(".", 1)[0]


# RTSP Protocol Specific Routes ---------------------------------------------

# RTSP协议配置 - 在这里修改路径和命令
RTSP_CONFIG = {
    "script_path": "/home/hhh/下载/AFLNET/commands/run-aflnet.sh",  # 修改为你的脚本文件路径
    "shell_command": "cd /home/hhh/下载/AFLNET/ && docker run -d --privileged -v $(pwd)/output:/home/live555/testProgs/out-live555 -v $(pwd)/commands:/host-commands -p 8554:8554 aflnet-live555",  # 修改为你的启动命令
    "log_file_path": "/home/hhh/下载/AFLNET/output/plot_data"  # 修改为你的日志文件路径
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
    else:
        return make_response(error_response(f"不支持的协议类型: {protocol}"), 400)
    
    try:
        if not os.path.exists(file_path):
            return success_response({
                "content": "",
                "position": last_position,
                "message": "日志文件尚未创建"
            })
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # 移动到上次读取的位置
            f.seek(last_position)
            
            # 读取新内容
            new_content = f.read()
            
            # 获取当前位置
            current_position = f.tell()
        
        return success_response({
            "content": new_content,
            "position": current_position,
            "protocol": protocol,
            "message": f"成功读取{len(new_content)}字符"
        })
        
    except Exception as e:
        return make_response(error_response(f"读取日志文件失败: {str(e)}"), 500)


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
