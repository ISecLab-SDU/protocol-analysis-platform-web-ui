"""Flask blueprints for the protocol compliance domain."""

from __future__ import annotations

import contextlib
import json
import logging
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, cast

import toml
from flask import Blueprint, make_response, request
from werkzeug.datastructures import FileStorage

try:
    from ..utils.auth import verify_access_token
    from ..utils.responses import error_response, paginate, success_response, unauthorized
except ImportError:
    from utils.auth import verify_access_token
    from utils.responses import error_response, paginate, success_response, unauthorized
from .analysis import (
    extract_protocol_version,
    get_static_analysis_job,
    get_static_analysis_result,
    list_static_analysis_history,
    normalize_protocol_name,
    submit_static_analysis_job,
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


def _strip_extension(filename: str) -> str:
    if "." not in filename:
        return filename
    return filename.rsplit(".", 1)[0]
