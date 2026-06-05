"""Flask blueprints for the protocol compliance domain."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import logging
import os
import re
import sqlite3
import subprocess
import threading
import uuid
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, cast

import toml
from flask import Blueprint, make_response, request, send_file
from werkzeug.datastructures import FileStorage

try:
    from ..utils.auth import verify_access_token
    from ..utils.responses import (
        error_response,
        make_error_payload,
        paginate,
        success_response,
        unauthorized,
    )
except ImportError:
    from utils.auth import verify_access_token
    from utils.responses import (
        error_response,
        make_error_payload,
        paginate,
        success_response,
        unauthorized,
    )
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
    get_assertion_history_diff_path,
    get_assertion_history_entry,
    get_assert_generation_job,
    get_assert_generation_result,
    get_assert_generation_zip_path,
    submit_assert_generation_job,
    submit_diff_parsing_job,
    get_diff_parsing_job,
    get_diff_parsing_result,
    list_assertion_history,
)
from .store import STORE, TaskStatus
from .pipeline_runner import (
    PipelineExecutionError,
    PipelineResultNotFoundError,
    run_protocol_pipeline,
)

LOGGER = logging.getLogger(__name__)

bp = Blueprint("protocol_compliance", __name__, url_prefix="/api/protocol-compliance")

TEMP_ASSERTION_DATABASE_PATH = Path(
    "/home/lab426_system/protocol-web-ui/violations.db"
)

PROTOCOL_BY_IMPLEMENTATION = {
    "freecoap": "CoAP",
    "libcoap": "CoAP",
    "dhcp": "DHCPv6",
    "dnsmasq": "DHCPv6",
    "ndhs": "DHCPv6",
    "mosquitto": "MQTT",
    "sol": "MQTT",
    "tinymqtt": "MQTT",
    "pure-ftpd": "FTP",
    "uftpd": "FTP",
    "tlse": "TLS",
    "wolfssl": "TLS",
}

PROTOCOL_ALIASES = {
    "coap": "CoAP",
    "dhcp": "DHCPv6",
    "dhcpv6": "DHCPv6",
    "ftp": "FTP",
    "mqtt": "MQTT",
    "mqttv3": "MQTT",
    "mqttv5": "MQTT",
    "snmp": "SNMP",
    "ssl": "TLS",
    "tls": "TLS",
    "tlsv1.3": "TLS",
}

RULE_RESULT_PRIORITY = {
    "unknown": 0,
    "no_violation": 1,
    "violation_found": 2,
}


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


@bp.route("/extract/run", methods=["POST"])
def run_protocol_extract():
    _, error = _ensure_authenticated()
    if error:
        return error

    html_upload = request.files.get("htmlFile")
    if not isinstance(html_upload, FileStorage):
        return make_response(error_response("请上传协议 HTML 文件"), 400)

    api_key = (request.form.get("apiKey") or "").strip()
    protocol = (request.form.get("protocol") or "").strip()
    version = (request.form.get("version") or "").strip()
    filter_flag = (request.form.get("filterHeadings") or "").strip().lower()
    filter_headings = filter_flag in {"1", "true", "yes", "on"}

    try:
        result = run_protocol_pipeline(
            api_key=api_key,
            protocol=protocol,
            version=version,
            html_upload=html_upload,
            filter_headings=filter_headings,
        )
    except ValueError as exc:
        payload = make_error_payload("参数错误", details=str(exc))
        return make_response(payload, 400)
    except FileNotFoundError as exc:
        payload = make_error_payload("流程未准备就绪", details=str(exc))
        return make_response(payload, 500)
    except PipelineResultNotFoundError as exc:
        detail = {"message": str(exc)}
        payload = make_error_payload("未找到分析结果文件", details=detail)
        return make_response(payload, 500)
    except PipelineExecutionError as exc:
        detail = {
            "stdout": (exc.stdout or "").splitlines()[-40:] or None,
            "stderr": (exc.stderr or "").splitlines()[-40:] or None,
        }
        payload = make_error_payload("协议分析执行失败", details=detail)
        return make_response(payload, 500)

    payload = success_response(
        {
            "protocol": result.protocol,
            "version": result.version,
            "ruleCount": len(result.rules),
            "rules": [
                {
                    "rule": item.rule,
                    "req_type": item.req_type,
                    "req_fields": item.req_fields,
                    "res_type": item.res_type,
                    "res_fields": item.res_fields,
                    "group": item.group,
                }
                for item in result.rules
            ],
            "storeDir": str(result.store_dir),
            "resultPath": str(result.result_path),
        }
    )
    return make_response(payload, 200)


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


@bp.route("/assertions/history", methods=["GET"])
def assertion_history():
    _, error = _ensure_authenticated()
    if error:
        return error

    limit = _to_int(request.args.get("limit"), 50)
    limit = max(1, min(limit, 200))
    items = list_assertion_history(limit=limit)
    payload = {"items": items, "limit": limit, "count": len(items)}
    return make_response(success_response(payload), 200)


@bp.route("/assertions/history/<job_id>", methods=["GET"])
def assertion_history_entry(job_id: str):
    _, error = _ensure_authenticated()
    if error:
        return error

    entry = get_assertion_history_entry(job_id)
    if not entry:
        return make_response(error_response("历史记录不存在"), 404)
    return make_response(success_response(entry), 200)


@bp.route("/assertions/history/<job_id>/diff", methods=["GET"])
def download_assertion_diff(job_id: str):
    _, error = _ensure_authenticated()
    if error:
        return error

    diff_path = get_assertion_history_diff_path(job_id)
    if not diff_path:
        return make_response(error_response("Diff 文件不存在"), 404)
    return send_file(diff_path, as_attachment=True, download_name=diff_path.name)


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


def _normalize_implementation_from_db(path: Path) -> str:
    name = path.stem
    return name[7:] if name.startswith("sqlite_") else name


def _protocol_for_implementation(implementation_name: str) -> str:
    return PROTOCOL_BY_IMPLEMENTATION.get(implementation_name.lower(), "Other")


def _normalize_protocol_name(
    protocol_name: Optional[str],
    implementation_name: str,
) -> str:
    if isinstance(protocol_name, str) and protocol_name.strip():
        key = re.sub(r"[\s_-]+", "", protocol_name.strip().lower())
        for prefix, normalized in PROTOCOL_ALIASES.items():
            if key.startswith(prefix.replace(".", "")):
                return normalized
    return _protocol_for_implementation(implementation_name)


def _dedupe_key(value: Any) -> str:
    return " ".join(str(value or "").split()).lower()


def _merge_rule_status(
    status_by_rule: Dict[str, str],
    rule_key: str,
    result_status: str,
) -> None:
    current = status_by_rule.get(rule_key)
    if current is None or (
        RULE_RESULT_PRIORITY.get(result_status, 0)
        > RULE_RESULT_PRIORITY.get(current, 0)
    ):
        status_by_rule[rule_key] = result_status


def _violation_location_key(rule_key: str, violation: Dict[str, Any]) -> str:
    code_lines = violation.get("codeLines")
    if isinstance(code_lines, list):
        lines = ",".join(str(item) for item in code_lines)
    else:
        lines = ""
    return "|".join(
        [
            rule_key,
            _dedupe_key(violation.get("filename")),
            _dedupe_key(violation.get("functionName")),
            lines,
        ]
    )


def _parse_violation_details(payload: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
    violations_payload = payload.get("violations")
    if not isinstance(violations_payload, list):
        return None

    violations: List[Dict[str, Any]] = []
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
    return violations or None


def _iter_static_analysis_database_sources(
    job_limit: int,
) -> tuple[List[Dict[str, Any]], List[str]]:
    db_dir = Path(os.path.dirname(__file__)) / "databases"
    sources: List[Dict[str, Any]] = []
    warnings: List[str] = []
    seen_database_paths: set[str] = set()

    if db_dir.is_dir():
        for db_path in sorted(db_dir.glob("sqlite_*.db")):
            resolved = str(db_path.resolve())
            seen_database_paths.add(resolved)
            sources.append(
                {
                    "path": db_path,
                    "sourceType": "builtin",
                    "jobId": None,
                    "protocolName": None,
                    "createdAt": None,
                    "updatedAt": None,
                }
            )
    else:
        warnings.append(f"数据库目录不存在：{db_dir}")

    for entry in list_static_analysis_history(limit=job_limit):
        if entry.get("status") != "completed":
            continue
        database_path_raw = entry.get("databasePath")
        workspace_path_raw = entry.get("workspacePath")
        resolved_path, resolve_warnings = _find_sqlite_file(
            str(database_path_raw) if database_path_raw else None,
            str(workspace_path_raw) if workspace_path_raw else None,
        )
        warnings.extend(resolve_warnings)
        if not resolved_path:
            continue
        resolved = str(resolved_path.resolve())
        if resolved in seen_database_paths:
            continue
        seen_database_paths.add(resolved)
        sources.append(
            {
                "path": resolved_path,
                "sourceType": "job",
                "jobId": entry.get("jobId"),
                "protocolName": entry.get("protocolName"),
                "createdAt": entry.get("createdAt"),
                "updatedAt": entry.get("updatedAt"),
            }
        )

    return sources, warnings


def _read_violation_history_from_database(
    db_path: Path,
    *,
    source_type: str,
    job_id: Optional[str] = None,
    protocol_name: Optional[str] = None,
    created_at: Optional[str] = None,
    updated_at: Optional[str] = None,
) -> tuple[List[Dict[str, Any]], List[str]]:
    warnings: List[str] = []
    items: List[Dict[str, Any]] = []

    implementation_name = _normalize_implementation_from_db(db_path)
    resolved_protocol = _normalize_protocol_name(protocol_name, implementation_name)
    database_name = db_path.name
    try:
        extracted_at = datetime.fromtimestamp(
            db_path.stat().st_mtime,
            timezone.utc,
        ).isoformat()
    except OSError:
        extracted_at = datetime.now(timezone.utc).isoformat()

    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error as exc:
        return items, [f"无法打开数据库 {db_path}: {exc}"]

    conn.row_factory = sqlite3.Row
    query = (
        "SELECT rule_desc, code_snippet, call_graph, llm_response "
        "FROM rule_code_snippet"
    )
    try:
        rows = conn.execute(query).fetchall()
    except sqlite3.Error as exc:
        conn.close()
        return items, [f"无法读取数据库 {db_path} 的 rule_code_snippet: {exc}"]

    for index, row in enumerate(rows, start=1):
        raw_llm_response = row["llm_response"]
        llm_payload = _parse_llm_response(raw_llm_response)
        result_status, result_label = _classify_rule_result(llm_payload)

        reason = llm_payload.get("reason")
        if isinstance(reason, str):
            reason = reason.strip()
        elif reason is not None:
            reason = json.dumps(reason, ensure_ascii=False)

        item_id = _build_violation_history_item_id(
            db_path=db_path,
            job_id=job_id,
            row_index=index,
            rule_desc=row["rule_desc"],
            source_type=source_type,
        )
        items.append(
            {
                "id": item_id,
                "sourceType": source_type,
                "jobId": job_id,
                "implementationName": implementation_name,
                "protocolName": resolved_protocol,
                "databaseName": database_name,
                "databasePath": str(db_path),
                "ruleDesc": row["rule_desc"],
                "result": result_status,
                "resultLabel": result_label,
                "reason": reason,
                "codeSnippet": row["code_snippet"],
                "callGraph": row["call_graph"],
                "llmRaw": raw_llm_response,
                "violations": _parse_violation_details(llm_payload),
                "createdAt": created_at or extracted_at,
                "updatedAt": updated_at or extracted_at,
                "extractedAt": extracted_at,
            }
        )

    conn.close()
    return items, warnings


def _build_violation_history_item_id(
    *,
    db_path: Path,
    job_id: Optional[str],
    row_index: int,
    rule_desc: Any,
    source_type: str,
) -> str:
    stable_key = "|".join(
        [
            source_type,
            job_id or "",
            str(db_path),
            str(rule_desc),
            str(row_index),
        ]
    )
    return hashlib.sha1(stable_key.encode("utf-8")).hexdigest()


def _delete_violation_history_from_database(
    db_path: Path,
    *,
    item_id: str,
    job_id: Optional[str] = None,
    source_type: str,
) -> tuple[Optional[Dict[str, Any]], List[str]]:
    warnings: List[str] = []

    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error as exc:
        return None, [f"无法打开数据库 {db_path}: {exc}"]

    conn.row_factory = sqlite3.Row
    query = (
        "SELECT rowid AS __rowid, rule_desc, llm_response "
        "FROM rule_code_snippet"
    )
    try:
        rows = conn.execute(query).fetchall()
    except sqlite3.Error as exc:
        conn.close()
        return None, [f"无法读取数据库 {db_path} 的 rule_code_snippet: {exc}"]

    for index, row in enumerate(rows, start=1):
        current_id = _build_violation_history_item_id(
            db_path=db_path,
            job_id=job_id,
            row_index=index,
            rule_desc=row["rule_desc"],
            source_type=source_type,
        )
        if current_id != item_id:
            continue

        try:
            conn.execute(
                "DELETE FROM rule_code_snippet WHERE rowid = ?",
                (row["__rowid"],),
            )
            conn.commit()
        except sqlite3.Error as exc:
            conn.close()
            raise RuntimeError(f"删除数据库记录失败：{exc}") from exc

        conn.close()
        return (
            {
                "databaseName": db_path.name,
                "databasePath": str(db_path),
                "id": item_id,
            },
            warnings,
        )

    conn.close()
    return None, warnings


def _truncate_text(value: Any, limit: int) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return f"{text[:limit - 1]}…"


def _parse_history_datetime(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _history_item_datetime(item: Dict[str, Any]) -> Optional[datetime]:
    return (
        _parse_history_datetime(item.get("updatedAt"))
        or _parse_history_datetime(item.get("extractedAt"))
        or _parse_history_datetime(item.get("createdAt"))
    )


def _read_overview_from_database(
    db_path: Path,
    *,
    protocol_name: Optional[str] = None,
) -> tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int], List[str]]:
    warnings: List[str] = []
    table_counts: Dict[str, int] = {}
    top_findings: List[Dict[str, Any]] = []

    implementation_name = _normalize_implementation_from_db(db_path)
    resolved_protocol = _normalize_protocol_name(protocol_name, implementation_name)

    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error as exc:
        return None, top_findings, table_counts, [f"无法打开数据库 {db_path}: {exc}"]

    conn.row_factory = sqlite3.Row
    try:
        tables = [
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"
            )
        ]
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            table_counts[table] = int(
                conn.execute(f"SELECT COUNT(*) FROM {quoted}").fetchone()[0]
            )
    except sqlite3.Error as exc:
        conn.close()
        return None, top_findings, table_counts, [f"无法统计数据库 {db_path}: {exc}"]

    if "rule_code_snippet" in tables:
        try:
            rule_rows = conn.execute(
                "SELECT rule_desc, code_snippet, llm_response FROM rule_code_snippet"
            ).fetchall()
        except sqlite3.Error as exc:
            conn.close()
            return None, top_findings, table_counts, [
                f"无法读取数据库 {db_path} 的 rule_code_snippet: {exc}"
            ]
    else:
        rule_rows = []

    rule_status_by_key: Dict[str, str] = {}
    code_snippet_rule_keys: set[str] = set()
    violation_location_keys: set[str] = set()
    for row in rule_rows:
        rule_key = _dedupe_key(row["rule_desc"])
        llm_payload = _parse_llm_response(row["llm_response"])
        result_status, _ = _classify_rule_result(llm_payload)
        _merge_rule_status(rule_status_by_key, rule_key, result_status)

        if row["code_snippet"]:
            code_snippet_rule_keys.add(rule_key)

        violations = _parse_violation_details(llm_payload)
        if result_status == "violation_found" and violations:
            for violation in violations:
                violation_location_keys.add(
                    _violation_location_key(rule_key, violation)
                )

        if result_status == "violation_found":
            top_findings.append(
                {
                    "implementation": implementation_name,
                    "protocol": resolved_protocol,
                    "rule": _truncate_text(row["rule_desc"], 160),
                    "reason": _truncate_text(llm_payload.get("reason"), 220),
                }
            )

    conn.close()

    item = {
        "name": implementation_name,
        "protocol": resolved_protocol,
        "database": db_path.name,
        "analysisRecords": len(rule_status_by_key),
        "ruleResults": len(rule_status_by_key),
        "violationRules": list(rule_status_by_key.values()).count("violation_found"),
        "noViolationRules": list(rule_status_by_key.values()).count("no_violation"),
        "unknownRules": list(rule_status_by_key.values()).count("unknown"),
        "violationLocations": len(violation_location_keys),
        "codeSnippets": len(code_snippet_rule_keys),
        "_ruleStatusByKey": rule_status_by_key,
        "_codeSnippetRuleKeys": code_snippet_rule_keys,
        "_violationLocationKeys": violation_location_keys,
    }
    return item, top_findings, table_counts, warnings


@bp.route("/static-analysis/database-overview", methods=["GET"])
def static_analysis_database_overview():
    _, error = _ensure_authenticated()
    if error:
        return error

    job_limit = _to_int(request.args.get("jobLimit"), 200)
    sources, warnings = _iter_static_analysis_database_sources(job_limit)
    summary: Dict[str, int] = defaultdict(int)
    table_totals: Dict[str, int] = defaultdict(int)
    protocol_totals: Dict[str, Dict[str, int]] = {}
    implementation_groups: Dict[tuple[str, str], Dict[str, Any]] = {}
    top_findings: List[Dict[str, Any]] = []

    for source in sources:
        db_path = cast(Path, source["path"])
        item, findings, table_counts, db_warnings = _read_overview_from_database(
            db_path,
            protocol_name=cast(Optional[str], source.get("protocolName")),
        )
        warnings.extend(db_warnings)
        if item is None:
            continue

        top_findings.extend(findings)
        for table, count in table_counts.items():
            table_totals[table] += count

        group_key = (str(item["name"]).lower(), str(item["protocol"]).lower())
        grouped = implementation_groups.get(group_key)
        if grouped is None:
            grouped = {
                **item,
                "databaseNames": [item["database"]],
            }
            implementation_groups[group_key] = grouped
        else:
            databases = grouped.setdefault("databaseNames", [])
            if item["database"] not in databases:
                databases.append(item["database"])
            for rule_key, result_status in cast(
                Dict[str, str],
                item.get("_ruleStatusByKey") or {},
            ).items():
                _merge_rule_status(
                    cast(Dict[str, str], grouped["_ruleStatusByKey"]),
                    rule_key,
                    result_status,
                )
            cast(set[str], grouped["_codeSnippetRuleKeys"]).update(
                cast(set[str], item.get("_codeSnippetRuleKeys") or set())
            )
            cast(set[str], grouped["_violationLocationKeys"]).update(
                cast(set[str], item.get("_violationLocationKeys") or set())
            )

    implementations = list(implementation_groups.values())
    for item in implementations:
        database_names = item.get("databaseNames")
        if isinstance(database_names, list) and database_names:
            item["database"] = ", ".join(str(name) for name in sorted(database_names))
        item.pop("databaseNames", None)

        rule_status_by_key = cast(Dict[str, str], item.pop("_ruleStatusByKey", {}))
        code_snippet_rule_keys = cast(set[str], item.pop("_codeSnippetRuleKeys", set()))
        violation_location_keys = cast(
            set[str],
            item.pop("_violationLocationKeys", set()),
        )
        result_values = list(rule_status_by_key.values())
        item["analysisRecords"] = len(rule_status_by_key)
        item["ruleResults"] = len(rule_status_by_key)
        item["violationRules"] = result_values.count("violation_found")
        item["noViolationRules"] = result_values.count("no_violation")
        item["unknownRules"] = result_values.count("unknown")
        item["violationLocations"] = len(violation_location_keys)
        item["codeSnippets"] = len(code_snippet_rule_keys)

        protocol = str(item["protocol"])
        protocol_bucket = protocol_totals.setdefault(protocol, defaultdict(int))
        for key in (
            "analysisRecords",
            "ruleResults",
            "violationRules",
            "noViolationRules",
            "unknownRules",
            "violationLocations",
            "codeSnippets",
        ):
            value = int(item[key])
            summary[key] += value
            protocol_bucket[key] += value
        protocol_bucket["implementations"] += 1

    implementations.sort(key=lambda item: item["violationRules"], reverse=True)
    unique_top_findings: Dict[tuple[str, str], Dict[str, Any]] = {}
    for finding in top_findings:
        finding_key = (
            _dedupe_key(finding.get("implementation")),
            _dedupe_key(finding.get("rule")),
        )
        unique_top_findings.setdefault(finding_key, finding)
    top_findings = sorted(
        unique_top_findings.values(),
        key=lambda item: (
            str(item.get("protocol") or ""),
            str(item.get("implementation") or "").lower(),
            str(item.get("rule") or ""),
        ),
    )[:6]
    protocols = [
        {"name": name, **dict(values)}
        for name, values in sorted(protocol_totals.items())
    ]

    payload: Dict[str, Any] = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceDirectory": "static-analysis databases",
        "summary": {
            "databaseFiles": len(implementations),
            "implementations": len(implementations),
            **dict(summary),
        },
        "tableTotals": dict(sorted(table_totals.items())),
        "protocols": protocols,
        "implementations": implementations,
        "topFindings": top_findings,
    }
    if warnings:
        payload["warnings"] = warnings
    return success_response(payload)


@bp.route("/static-analysis/violation-history", methods=["GET"])
def static_analysis_violation_history():
    _, error = _ensure_authenticated()
    if error:
        return error

    job_limit = _to_int(request.args.get("jobLimit"), 200)
    protocol_filter = _dedupe_key(request.args.get("protocol"))
    implementation_filter = _dedupe_key(request.args.get("implementation"))
    result_filter = _dedupe_key(request.args.get("result"))
    time_range = _dedupe_key(request.args.get("timeRange"))
    sources, warnings = _iter_static_analysis_database_sources(job_limit)
    items: List[Dict[str, Any]] = []

    for source in sources:
        db_path = cast(Path, source["path"])
        db_items, db_warnings = _read_violation_history_from_database(
            db_path,
            source_type=cast(str, source["sourceType"]),
            job_id=cast(Optional[str], source.get("jobId")),
            protocol_name=cast(Optional[str], source.get("protocolName")),
            created_at=cast(Optional[str], source.get("createdAt")),
            updated_at=cast(Optional[str], source.get("updatedAt")),
        )
        items.extend(db_items)
        warnings.extend(db_warnings)

    if protocol_filter:
        items = [
            item
            for item in items
            if _dedupe_key(item.get("protocolName")) == protocol_filter
        ]

    if implementation_filter:
        items = [
            item
            for item in items
            if _dedupe_key(item.get("implementationName")) == implementation_filter
        ]

    if result_filter:
        items = [
            item for item in items if _dedupe_key(item.get("result")) == result_filter
        ]

    range_days = {
        "week": 7,
        "month": 30,
        "year": 365,
    }.get(time_range)
    if range_days:
        cutoff = datetime.now(timezone.utc) - timedelta(days=range_days)
        items = [
            item
            for item in items
            if (item_time := _history_item_datetime(item)) is not None
            and item_time >= cutoff
        ]

    items.sort(key=lambda item: str(item.get("updatedAt") or ""), reverse=True)
    payload: Dict[str, Any] = {
        "items": items,
        "count": len(items),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    if warnings:
        payload["warnings"] = warnings
    return success_response(payload)


@bp.route("/static-analysis/violation-history/<item_id>", methods=["DELETE"])
def delete_static_analysis_violation_history(item_id: str):
    _, error = _ensure_authenticated()
    if error:
        return error

    if not isinstance(item_id, str) or not item_id.strip():
        return make_response(error_response("无效的历史记录 ID"), 400)

    job_limit = _to_int(request.args.get("jobLimit"), 200)
    sources, warnings = _iter_static_analysis_database_sources(job_limit)

    try:
        for source in sources:
            db_path = cast(Path, source["path"])
            deleted, db_warnings = _delete_violation_history_from_database(
                db_path,
                item_id=item_id,
                job_id=cast(Optional[str], source.get("jobId")),
                source_type=cast(str, source["sourceType"]),
            )
            warnings.extend(db_warnings)
            if deleted:
                payload: Dict[str, Any] = {**deleted, "deleted": True}
                if warnings:
                    payload["warnings"] = warnings
                return make_response(success_response(payload), 200)
    except RuntimeError as exc:
        LOGGER.error("Failed to delete violation history item %s: %s", item_id, exc)
        return make_response(error_response(str(exc)), 500)

    detail: Dict[str, Any] = {"id": item_id}
    if warnings:
        detail["warnings"] = warnings
    return make_response(error_response("历史记录不存在", detail), 404)


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
            f"Unable to resolve SQLite database for static analysis insights: databasePath={database_path_raw!r}, workspacePath={workspace_path_raw!r}",
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

    # Support incremental event fetching via fromEventId query parameter
    from_event_id_raw = request.args.get("fromEventId")
    from_event_id: Optional[int] = None
    if from_event_id_raw is not None:
        try:
            from_event_id = int(from_event_id_raw)
        except (TypeError, ValueError):
            LOGGER.warning(
                "Invalid fromEventId parameter: %s (job_id=%s)",
                from_event_id_raw,
                job_id,
            )
            # Continue with full snapshot if parameter is invalid

    snapshot = get_static_analysis_job(job_id, from_event_id=from_event_id)
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


@bp.route("/static-analysis/<job_id>/artifact/database", methods=["GET"])
def download_static_analysis_database(job_id: str):
    LOGGER.info(f"[下载数据库] 请求下载任务 {job_id} 的数据库文件")
    _, error = _ensure_authenticated()
    if error:
        LOGGER.warning(f"[下载数据库] 任务 {job_id} 认证失败")
        return error

    snapshot = get_static_analysis_job(job_id)
    if not snapshot:
        LOGGER.error(f"[下载数据库] 任务 {job_id} 未找到")
        return make_response(error_response("未找到静态分析任务"), 404)

    LOGGER.info(f"[下载数据库] 任务 {job_id} 找到，状态: {snapshot.get('status')}")

    # 优先使用存储的database_path
    database_path = snapshot.get("database_path")
    LOGGER.info(f"[下载数据库] 任务 {job_id} 的 database_path: {database_path}")

    if database_path:
        db_file = Path(database_path)
        if db_file.exists():
            LOGGER.info(f"[下载数据库] 使用存储的路径: {db_file}")
            return send_file(
                db_file,
                as_attachment=True,
                download_name=f"analysis-{job_id}.db",
                mimetype="application/octet-stream",
            )

    # 如果database_path为空或文件不存在，尝试从output_path动态查找
    LOGGER.warning(f"[下载数据库] database_path 无效，尝试从 output_path 查找")
    output_path = snapshot.get("output_path")
    if output_path:
        output_dir = Path(output_path)
        database_dir = output_dir / "database"
        LOGGER.info(f"[下载数据库] 在 {database_dir} 目录查找数据库文件")

        if database_dir.exists():
            candidates = list(database_dir.glob("*.db"))
            LOGGER.info(f"[下载数据库] 找到 {len(candidates)} 个 .db 文件: {candidates}")
            if candidates:
                db_file = candidates[0]
                LOGGER.info(f"[下载数据库] 使用 output_path 找到的文件: {db_file}")
                return send_file(
                    db_file,
                    as_attachment=True,
                    download_name=f"analysis-{job_id}.db",
                    mimetype="application/octet-stream",
                )

    # 最后尝试：直接从环境变量配置的output_root构造路径
    LOGGER.warning(f"[下载数据库] output_path 也无效，尝试从环境变量构造路径")
    output_root = os.environ.get("PG_OUTPUT_ROOT", "/tmp/protocolguard/outputs")
    constructed_path = Path(output_root) / job_id / "database"
    LOGGER.info(f"[下载数据库] 尝试构造的路径: {constructed_path}")

    if constructed_path.exists():
        candidates = list(constructed_path.glob("*.db"))
        LOGGER.info(f"[下载数据库] 在构造路径找到 {len(candidates)} 个 .db 文件: {candidates}")
        if candidates:
            db_file = candidates[0]
            LOGGER.info(f"[下载数据库] 使用构造路径找到的文件: {db_file}")
            return send_file(
                db_file,
                as_attachment=True,
                download_name=f"analysis-{job_id}.db",
                mimetype="application/octet-stream",
            )

    LOGGER.error(f"[下载数据库] 所有方法都失败，无法找到数据库文件")
    return make_response(error_response("数据库文件不存在"), 404)


@bp.route("/assertion-generation", methods=["POST"])
def assertion_generation():
    _, error = _ensure_authenticated()
    if error:
        return error

    if not request.files:
        return make_response(error_response("请上传源码压缩包"), 400)

    code_upload_raw = request.files.get("codeArchive")
    if not isinstance(code_upload_raw, FileStorage):
        return make_response(error_response("请上传完整文件：源码压缩包"), 400)

    code_upload = cast(FileStorage, code_upload_raw)
    code_name, code_data = _read_upload(code_upload)

    database_path_requested = request.form.get("databasePath")
    database_source = "upload"
    if database_path_requested:
        database_path = TEMP_ASSERTION_DATABASE_PATH
        if not database_path.is_file():
            return make_response(
                error_response(f"固定违规数据库不存在：{database_path}"),
                400,
            )
        try:
            database_data = database_path.read_bytes()
        except OSError as exc:
            LOGGER.exception("Failed to read fixed assertion database: %s", database_path)
            return make_response(error_response(f"读取固定违规数据库失败：{exc}"), 500)
        database_name = database_path.name
        database_source = str(database_path)
    else:
        database_upload_raw = request.files.get("database")
        if not isinstance(database_upload_raw, FileStorage):
            return make_response(error_response("请上传完整文件：违规数据库文件"), 400)
        database_upload = cast(FileStorage, database_upload_raw)
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
            "databaseSource": database_source,
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


@bp.route("/assertion-generation/<job_id>/instrumentation-diff", methods=["GET"])
def assertion_generation_instrumentation_diff(job_id: str):
    """Fetch the instrumentation diff for a completed assertion generation job."""
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
    
    # Extract instrumentation diff from result
    instrumentation = result.get("instrumentation")
    if not instrumentation or not isinstance(instrumentation, dict):
        return make_response(error_response("未找到 instrumentation 数据"), 404)
    
    artifacts = instrumentation.get("artifacts")
    if not artifacts or not isinstance(artifacts, dict):
        return make_response(error_response("未找到 instrumentation artifacts"), 404)
    
    diff_output = artifacts.get("diffOutput")
    if not diff_output or not isinstance(diff_output, dict):
        return make_response(error_response("未找到 instrumentation diff 输出"), 404)
    
    return make_response(success_response(diff_output), 200)


# Diff Parsing Routes -----------------------------------------------------------


@bp.route("/assertion-generation/<assert_job_id>/diff-parsing", methods=["POST"])
def start_diff_parsing(assert_job_id: str):
    """Start diff parsing for a completed assertion generation job."""
    _, error = _ensure_authenticated()
    if error:
        return error

    # Verify the parent assertion generation job exists
    assert_snapshot = get_assert_generation_job(assert_job_id)
    if not assert_snapshot:
        return make_response(error_response("未找到断言生成任务"), 404)

    if assert_snapshot.get("status") != "completed":
        return make_response(
            error_response(
                "断言生成任务尚未完成，无法开始差异解析",
                {"status": assert_snapshot.get("status")},
            ),
            409,
        )

    LOGGER.info(
        "Diff parsing job requested",
        extra={
            "parentJobId": assert_job_id,
        },
    )

    snapshot = submit_diff_parsing_job(assert_job_id)
    return make_response(success_response(snapshot), 202)


@bp.route(
    "/assertion-generation/<assert_job_id>/diff-parsing/<diff_job_id>/progress",
    methods=["GET"],
)
def diff_parsing_progress(assert_job_id: str, diff_job_id: str):
    """Get progress of a diff parsing job."""
    _, error = _ensure_authenticated()
    if error:
        return error

    snapshot = get_diff_parsing_job(diff_job_id)
    if not snapshot:
        return make_response(error_response("未找到差异解析任务"), 404)

    # Verify the parent job ID matches
    if snapshot.get("parentJobId") != assert_job_id:
        return make_response(
            error_response("差异解析任务与指定的断言生成任务不匹配"),
            400,
        )

    return make_response(success_response(snapshot), 200)


@bp.route(
    "/assertion-generation/<assert_job_id>/diff-parsing/<diff_job_id>/result",
    methods=["GET"],
)
def diff_parsing_result(assert_job_id: str, diff_job_id: str):
    """Get result of a completed diff parsing job."""
    _, error = _ensure_authenticated()
    if error:
        return error

    result = get_diff_parsing_result(diff_job_id)
    if result is None:
        snapshot = get_diff_parsing_job(diff_job_id)
        if not snapshot:
            return make_response(error_response("未找到差异解析任务"), 404)

        # Verify the parent job ID matches
        if snapshot.get("parentJobId") != assert_job_id:
            return make_response(
                error_response("差异解析任务与指定的断言生成任务不匹配"),
                400,
            )

        status = snapshot.get("status")
        return make_response(
            error_response("差异解析任务尚未完成", {"status": status}),
            409,
        )

    return make_response(success_response(result), 200)


def _strip_extension(filename: str) -> str:
    if "." not in filename:
        return filename
    return filename.rsplit(".", 1)[0]


# Protocol Specific Routes -------------------------------------------------

# SOL配置 - ProtocolGuard配置
RTSP_CONFIG = {
    "script_path": None,  # 不再需要脚本文件
    "shell_command": "docker run -d --privileged -v /home/lab426_system/ProtocolGuardOutPut:/out/fuzz-output protocolguard:latest fuzz",  # ProtocolGuard启动命令（使用-d后台运行，移除--rm和-it）
    "log_file_path": "/home/lab426_system/ProtocolGuardOutPut/plot_data"  # ProtocolGuard日志文件路径
}

# MQTT协议配置 - MBFuzzer相关路径
MQTT_CONFIG = {
    "log_file_path": os.path.join(os.path.dirname(__file__), "mbfuzzer_logs", "fuzzing_report.txt"),  # MBFuzzer日志文件路径
    "shell_command": "echo 'MBFuzzer模拟运行 - 传统MQTT broker模糊测试'",  # MBFuzzer启动命令（临时模拟）
    "output_dir": os.path.join(os.path.dirname(__file__), "mbfuzzer_logs")  # MBFuzzer输出目录
}

# SNMP协议配置 - SNMP Fuzzer相关路径
SNMP_CONFIG = {
    "log_file_path": os.path.join(os.path.dirname(__file__), "snmpfuzzer_logs", "fuzz_output.txt"),  # SNMP Fuzzer日志文件路径
    "shell_command": "echo 'SNMP Fuzzer模拟运行'",  # SNMP Fuzzer启动命令（临时模拟）
    "output_dir": os.path.join(os.path.dirname(__file__), "snmpfuzzer_logs")  # SNMP Fuzzer输出目录
}


def _is_path_inside(path: Path, allowed_roots: list[Path]) -> bool:
    try:
        resolved = path.expanduser().resolve()
    except (OSError, RuntimeError, ValueError):
        return False

    for root in allowed_roots:
        try:
            resolved.relative_to(root.expanduser().resolve())
            return True
        except (OSError, RuntimeError, ValueError):
            continue
    return False


def _aflnet_output_root() -> Path:
    return Path(os.environ.get("AFLNET_OUTPUT_ROOT") or os.path.dirname(RTSP_CONFIG["log_file_path"]))


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _aflnet_fallback_output_root() -> Path:
    configured = os.environ.get("AFLNET_FALLBACK_OUTPUT_ROOT")
    if configured:
        return Path(configured).expanduser()
    return _repo_root() / "fuzz-output"


def _aflnet_output_root_for_source(source: str = "primary") -> Path:
    if source == "fallback":
        return _aflnet_fallback_output_root()
    return _aflnet_output_root()


def _aflnet_log_file_for_source(source: str = "primary") -> Path:
    if source == "fallback":
        filename = os.environ.get("AFLNET_FALLBACK_LOG_FILE_NAME", "plot_data")
        return _aflnet_fallback_output_root() / filename
    return Path(RTSP_CONFIG["log_file_path"]).expanduser()


def _resolve_aflnet_output_source(data: Optional[Dict[str, Any]] = None) -> str:
    requested = (data or {}).get("outputSource") or (data or {}).get("output_source")
    if requested == "fallback" or (data or {}).get("useFallbackOutput"):
        return "fallback"
    return "primary"


def _resolve_aflnet_archive_source(
    requested_path: Optional[str],
    requested_source: Optional[str],
) -> str:
    if requested_source == "fallback":
        return "fallback"
    if requested_path:
        path = Path(requested_path).expanduser()
        if path.exists() and _is_path_inside(path, [_aflnet_fallback_output_root()]):
            return "fallback"
    return "primary"


def _aflnet_artifact_root() -> Path:
    configured = os.environ.get("AFLNET_ARTIFACT_ROOT")
    if configured:
        return Path(configured).expanduser()
    pg_output_root = Path(os.environ.get("PG_OUTPUT_ROOT", "/tmp/protocolguard/outputs")).expanduser()
    return pg_output_root.parent / "fuzz-artifacts"


def _aflnet_result_path_info(source: str = "primary") -> Dict[str, Any]:
    output_root = _aflnet_output_root_for_source(source).expanduser()
    log_file = _aflnet_log_file_for_source(source).expanduser()
    poc_path = output_root
    for name in ("replayable-crashes", "crashes", "crash", "crash_logs", "queue"):
        candidate = output_root / name
        if candidate.exists():
            poc_path = candidate
            break
    return {
        "isFallbackOutput": source == "fallback",
        "logFilePath": str(log_file),
        "outputSource": source,
        "outputRoot": str(output_root),
        "pocPath": str(poc_path),
    }


def _poc_artifact_candidates(output_root: Path, requested_path: Optional[str]) -> list[Path]:
    allowed_roots = [output_root]
    candidates: list[Path] = []

    if requested_path:
        requested = Path(requested_path).expanduser()
        if requested.exists() and _is_path_inside(requested, allowed_roots):
            candidates.append(requested)

    for name in (
        "replayable-crashes",
        "crashes",
        "crash",
        "crash_logs",
        "queue",
        "hangs",
        "fuzzer_stats",
        "plot_data",
    ):
        candidate = output_root / name
        if candidate.exists():
            candidates.append(candidate)

    if not candidates and output_root.exists():
        candidates.append(output_root)

    deduped: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except (OSError, RuntimeError):
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        deduped.append(candidate)
    return deduped


def _add_path_to_zip(archive: zipfile.ZipFile, path: Path, output_root: Path) -> int:
    if not path.exists() or not _is_path_inside(path, [output_root]):
        return 0

    added = 0
    if path.is_file():
        archive.write(path, path.relative_to(output_root).as_posix())
        return 1

    for child in sorted(path.rglob("*")):
        if not child.is_file() or child.is_symlink():
            continue
        if not _is_path_inside(child, [output_root]):
            continue
        archive.write(child, child.relative_to(output_root).as_posix())
        added += 1
    return added


def _write_aflnet_poc_archive(
    target: Any,
    *,
    artifact_id: Optional[str],
    crash_log_path: Optional[str],
    implementation: str,
    output_root: Path,
    protocol: str,
) -> int:
    candidates = _poc_artifact_candidates(output_root, crash_log_path)
    if not candidates:
        return 0

    manifest = {
        "artifactId": artifact_id,
        "protocol": protocol,
        "implementation": implementation,
        "outputRoot": str(output_root),
        "requestedCrashLogPath": crash_log_path,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }
    added = 0

    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        added += 1
        for candidate in candidates:
            added += _add_path_to_zip(archive, candidate, output_root)

    return added


@bp.route("/fuzzing/aflnet-result/download", methods=["GET"])
def download_aflnet_result():
    """Download AFLNET crash/queue artefacts as a zip bundle."""
    _, error = _ensure_authenticated()
    if error:
        return error

    protocol = request.args.get("protocol") or "MQTT"
    implementation = request.args.get("implementation") or "SOL"
    crash_log_path = request.args.get("crashLogPath")
    output_source = _resolve_aflnet_archive_source(
        crash_log_path,
        request.args.get("outputSource"),
    )

    output_root = _aflnet_output_root_for_source(output_source).expanduser()
    if not output_root.exists() or not output_root.is_dir():
        return make_response(
            error_response(f"AFLNET 输出目录不存在：{output_root}"),
            404,
        )

    buffer = io.BytesIO()
    added = _write_aflnet_poc_archive(
        buffer,
        artifact_id=None,
        crash_log_path=crash_log_path,
        implementation=implementation,
        output_root=output_root,
        protocol=protocol,
    )

    if added <= 1:
        return make_response(error_response("AFLNET 输出目录中没有可打包的 POC 文件"), 404)

    buffer.seek(0)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    safe_impl = re.sub(r"[^A-Za-z0-9_.-]+", "-", implementation).strip("-") or "aflnet"
    return send_file(
        buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"{safe_impl}-aflnet-poc-{timestamp}.zip",
        max_age=0,
    )


@bp.route("/fuzzing/aflnet-result/snapshot", methods=["POST"])
def snapshot_aflnet_result():
    """Persist the current AFLNET POC bundle for history downloads."""
    _, error = _ensure_authenticated()
    if error:
        return error

    data = request.get_json(silent=True) or {}
    protocol = data.get("protocol") or "MQTT"
    implementation = data.get("implementation") or "SOL"
    crash_log_path = data.get("crashLogPath")
    output_source = _resolve_aflnet_archive_source(
        crash_log_path,
        data.get("outputSource") or data.get("output_source"),
    )

    output_root = _aflnet_output_root_for_source(output_source).expanduser()
    if not output_root.exists() or not output_root.is_dir():
        return make_response(
            error_response(f"AFLNET 输出目录不存在：{output_root}"),
            404,
        )

    artifact_id = f"aflnet-{datetime.now().strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    artifact_dir = (_aflnet_artifact_root() / artifact_id).resolve()
    artifact_dir.mkdir(parents=True, exist_ok=False)
    zip_path = artifact_dir / "poc.zip"

    added = _write_aflnet_poc_archive(
        zip_path,
        artifact_id=artifact_id,
        crash_log_path=crash_log_path,
        implementation=implementation,
        output_root=output_root,
        protocol=protocol,
    )

    if added <= 1:
        with contextlib.suppress(OSError):
            zip_path.unlink()
        with contextlib.suppress(OSError):
            artifact_dir.rmdir()
        return make_response(error_response("AFLNET 输出目录中没有可归档的 POC 文件"), 404)

    file_size = zip_path.stat().st_size
    return success_response({
        "artifactId": artifact_id,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "downloadUrl": f"/protocol-compliance/fuzzing/aflnet-result/artifacts/{artifact_id}/download",
        "fileSize": file_size,
    })


@bp.route("/fuzzing/aflnet-result/artifacts/<artifact_id>/download", methods=["GET"])
def download_aflnet_result_artifact(artifact_id: str):
    """Download a persisted AFLNET POC artifact."""
    _, error = _ensure_authenticated()
    if error:
        return error

    if not re.fullmatch(r"[A-Za-z0-9_.-]+", artifact_id):
        return make_response(error_response("POC artifact id 非法"), 400)

    artifact_root = _aflnet_artifact_root().resolve()
    zip_path = (artifact_root / artifact_id / "poc.zip").resolve()
    if not _is_path_inside(zip_path, [artifact_root]) or not zip_path.is_file():
        return make_response(error_response("POC artifact 不存在或已过期"), 404)

    return send_file(
        zip_path,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"{artifact_id}.zip",
        max_age=0,
    )

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
    protocol_implementations = data.get("protocolImplementations", [])

    if not content:
        return make_response(error_response("脚本内容不能为空"), 400)

    # 根据协议获取配置
    if protocol == "RTSP":
        # SOL使用ProtocolGuard，不需要脚本文件，直接返回成功
        return success_response({
            "message": f"SOL不需要脚本文件，直接启动docker即可生成日志",
            "filePath": "N/A",
            "size": 0
        })
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
    print(f"[DEBUG] ========== execute-command API被调用 ==========")
    
    _, error = _ensure_authenticated()
    if error:
        print(f"[DEBUG] 认证失败: {error}")
        return error

    data = request.get_json()
    print(f"[DEBUG] 接收到的请求数据: {data}")
    
    if not data:
        print(f"[DEBUG] 请求数据为空")
        return make_response(error_response("请求数据不能为空"), 400)

    protocol = data.get("protocol", "UNKNOWN")
    protocol_implementations = data.get("protocolImplementations", [])
    
    print(f"[DEBUG] 解析参数 - 协议: {protocol}, 实现: {protocol_implementations}")

    # 根据协议获取配置
    if protocol == "MQTT":
        # MQTT协议支持双引擎配置
        if protocol_implementations and "SOL" in protocol_implementations:
            # SOL使用AFLNET引擎 (原RTSP配置)
            command = RTSP_CONFIG["shell_command"]
            print(f"[DEBUG] MQTT协议使用SOL实现(AFLNET引擎): {protocol_implementations}")
        else:
            # 传统MQTT broker使用MBFuzzer引擎
            command = MQTT_CONFIG["shell_command"]
            print(f"[DEBUG] MQTT协议使用传统broker实现(MBFuzzer引擎): {protocol_implementations}")
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
            print(f"[DEBUG] SNMP协议实现: {protocol_implementations}")
    else:
        return make_response(error_response(f"不支持的协议类型: {protocol}"), 400)

    try:
        print(f"[DEBUG] 执行命令: {command}")  # 调试日志

        # 对于SOL的ProtocolGuard，使用后台运行方式
        # 检查是否是SOL实现（MQTT协议 + SOL实现 或者 原RTSP协议）
        is_sol_protocol = (protocol == "RTSP") or (protocol == "MQTT" and protocol_implementations and "SOL" in protocol_implementations)
        
        if is_sol_protocol:
            # ProtocolGuard需要在后台运行，因为它是长时间运行的fuzzing任务
            # 直接执行docker命令并获取容器ID
            try:
                result = subprocess.run(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=30  # 30秒超时
                )
                
                if result.returncode == 0:
                    container_id = result.stdout.strip()
                    if container_id and len(container_id) >= 12:  # Docker容器ID至少12位
                        protocol_name = "SOL" if protocol == "MQTT" else protocol
                        print(f"[DEBUG] {protocol_name} ProtocolGuard启动成功，容器ID: {container_id}")
                        
                        # 验证容器是否真的在运行
                        import time
                        time.sleep(2)
                        check_result = subprocess.run(
                            f"docker ps -q --filter id={container_id}",
                            shell=True,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )
                        
                        if check_result.returncode == 0 and check_result.stdout.strip():
                            response_data = {
                                "message": f"{protocol_name} ProtocolGuard启动成功，正在后台运行fuzzing任务",
                                "command": command,
                                "pid": None,  # Docker容器没有直接的PID
                                "container_id": container_id,
                                **_aflnet_result_path_info(),
                            }
                            print(f"[DEBUG] 返回成功响应: {response_data}")
                            return success_response(response_data)
                        else:
                            return make_response(
                                error_response(
                                    "容器启动后立即停止，已切换到备份 fuzz-output 数据源",
                                    _aflnet_result_path_info("fallback"),
                                ),
                                500,
                            )
                    else:
                        error_msg = result.stderr.strip() if result.stderr.strip() else "无法获取有效的容器ID"
                        print(f"[DEBUG] ProtocolGuard启动失败: {error_msg}")
                        return make_response(error_response(f"ProtocolGuard启动失败: {error_msg}"), 500)
                else:
                    error_msg = result.stderr.strip() if result.stderr.strip() else "Docker命令执行失败"
                    print(f"[DEBUG] ProtocolGuard启动失败: {error_msg}")
                    return make_response(error_response(f"ProtocolGuard启动失败: {error_msg}"), 500)
                    
            except subprocess.TimeoutExpired:
                return make_response(error_response("Docker容器启动超时"), 500)
            except Exception as e:
                print(f"[DEBUG] ProtocolGuard启动异常: {str(e)}")
                return make_response(error_response(f"ProtocolGuard启动异常: {str(e)}"), 500)
        else:
            # 其他协议使用原来的方式
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
    protocol_implementations = data.get("protocolImplementations", [])
    output_source = _resolve_aflnet_output_source(data)
    is_sol_aflnet = (
        protocol == "MQTT"
        and protocol_implementations
        and "SOL" in protocol_implementations
    )
    
    if protocol == "MQTT":
        # MQTT协议支持双引擎配置
        if protocol_implementations and "SOL" in protocol_implementations:
            # SOL使用AFLNET引擎日志路径 (原RTSP配置)
            file_path = str(_aflnet_log_file_for_source(output_source))
            print(f"[DEBUG] MQTT协议使用SOL实现，读取AFLNET日志({output_source}): {file_path}")
        else:
            # 传统MQTT broker使用MBFuzzer引擎日志路径
            file_path = MQTT_CONFIG["log_file_path"]
            print(f"[DEBUG] MQTT协议使用传统broker实现，读取MBFuzzer日志: {file_path}")
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
            response_data = {
                "content": "",
                "position": last_position,
                "message": f"日志目录不存在: {log_dir}",
            }
            if is_sol_aflnet:
                response_data.update(_aflnet_result_path_info(output_source))
            return success_response(response_data)
        
        # 列出目录中的文件
        try:
            files_in_dir = os.listdir(log_dir)
            print(f"[DEBUG] 日志目录中的文件: {files_in_dir}")
        except Exception as e:
            print(f"[DEBUG] 无法列出目录文件: {e}")
        
        if not os.path.exists(file_path):
            print(f"[DEBUG] 日志文件不存在: {file_path}")
            response_data = {
                "content": "",
                "position": last_position,
                "message": f"日志文件尚未创建: {file_path}",
            }
            if is_sol_aflnet:
                response_data.update(_aflnet_result_path_info(output_source))
            return success_response(response_data)
        
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
        
        response_data = {
            "content": new_content,
            "position": current_position,
            "protocol": protocol,
            "file_size": file_size,
            "message": f"成功读取{len(new_content)}字符，文件大小{file_size}字节",
        }
        if is_sol_aflnet:
            response_data.update(_aflnet_result_path_info(output_source))
        return success_response(response_data)

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
        
        if protocol == "MQTT":
            # MQTT协议支持双引擎配置，需要检查协议实现
            protocol_implementations = data.get("protocolImplementations", [])
            
            if protocol_implementations and "SOL" in protocol_implementations:
                # 检查SOL相关状态 (使用AFLNET引擎)
                log_file_path = str(_aflnet_log_file_for_source())
                status_info["engine"] = "AFLNET"
                status_info["implementation"] = "SOL"
                status_info.update(_aflnet_result_path_info())
                fallback_info = _aflnet_result_path_info("fallback")
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


@bp.route("/pre-start-cleanup", methods=["POST"])
def pre_start_cleanup():
    """启动前清理：停止现有容器并清理输出文件"""
    print(f"[DEBUG] ========== 启动前清理API被调用 ==========")
    
    _, error = _ensure_authenticated()
    if error:
        print(f"[DEBUG] 认证失败: {error}")
        return error
    
    data = request.get_json()
    print(f"[DEBUG] 接收到的请求数据: {data}")
    
    if not data:
        print(f"[DEBUG] 请求数据为空")
        return make_response(error_response("请求数据不能为空"), 400)
    
    protocol = data.get("protocol", "UNKNOWN")
    
    print(f"[DEBUG] 解析参数 - 协议: {protocol}")
    
    cleanup_results = {
        "containers_stopped": 0,
        "containers_removed": 0,
        "output_cleaned": False,
        "errors": []
    }
    
    try:
        print(f"[DEBUG] 开始启动前清理 - 协议: {protocol}")
        
        # 1. 查找并停止所有相关的Docker容器
        if protocol == "RTSP" or protocol == "MQTT":
            # 查找protocolguard容器
            find_result = subprocess.run(
                "docker ps -q --filter ancestor=protocolguard:latest",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if find_result.returncode == 0 and find_result.stdout.strip():
                container_ids = find_result.stdout.strip().split('\n')
                print(f"[DEBUG] 找到 {len(container_ids)} 个运行中的protocolguard容器")
                
                for container_id in container_ids:
                    if container_id:
                        try:
                            # 停止容器
                            stop_result = subprocess.run(
                                f"docker stop {container_id}",
                                shell=True,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True,
                                timeout=30
                            )
                            
                            if stop_result.returncode == 0:
                                cleanup_results["containers_stopped"] += 1
                                print(f"[DEBUG] 容器停止成功: {container_id}")
                                
                                # 删除容器
                                remove_result = subprocess.run(
                                    f"docker rm {container_id}",
                                    shell=True,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    text=True,
                                    timeout=30
                                )
                                
                                if remove_result.returncode == 0:
                                    cleanup_results["containers_removed"] += 1
                                    print(f"[DEBUG] 容器删除成功: {container_id}")
                                else:
                                    error_msg = remove_result.stderr.strip() or "删除容器失败"
                                    cleanup_results["errors"].append(f"删除容器失败 {container_id}: {error_msg}")
                            else:
                                error_msg = stop_result.stderr.strip() or "停止容器失败"
                                cleanup_results["errors"].append(f"停止容器失败 {container_id}: {error_msg}")
                                
                        except subprocess.TimeoutExpired:
                            cleanup_results["errors"].append(f"操作容器超时: {container_id}")
                        except Exception as e:
                            cleanup_results["errors"].append(f"操作容器异常 {container_id}: {str(e)}")
            else:
                print(f"[DEBUG] 没有找到运行中的protocolguard容器")
        
        # 2. 清理输出文件夹
        if protocol == "RTSP" or protocol == "MQTT":
            output_dir = os.path.dirname(RTSP_CONFIG["log_file_path"])
            fallback_output_dir = str(_aflnet_fallback_output_root().resolve())
            
            # Linux安全检查：防止删除系统重要目录
            dangerous_paths = ['/', '/home', '/usr', '/var', '/etc', '/bin', '/sbin', '/lib', '/opt']
            if str(Path(output_dir).resolve()) == fallback_output_dir:
                cleanup_results["errors"].append(f"拒绝清理备份输出目录: {output_dir}")
                print(f"[DEBUG] 安全检查失败，拒绝清理备份输出目录: {output_dir}")
            elif output_dir in dangerous_paths or len(output_dir.strip()) < 5:
                cleanup_results["errors"].append(f"拒绝清理危险路径: {output_dir}")
                print(f"[DEBUG] 安全检查失败，拒绝清理: {output_dir}")
            else:
                try:
                    if os.path.exists(output_dir):
                        import shutil
                        
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
                            print(f"[DEBUG] 输出目录清理成功，删除了 {len(cleaned_items)} 个项目")
                        
                        if failed_items:
                            cleanup_results["errors"].extend([f"清理失败: {item}" for item in failed_items])
                    else:
                        print(f"[DEBUG] 输出目录不存在: {output_dir}")
                        cleanup_results["output_cleaned"] = True  # 目录不存在也算清理成功
                        
                except Exception as e:
                    cleanup_results["errors"].append(f"清理输出目录异常: {str(e)}")
                    print(f"[DEBUG] 清理输出目录异常: {e}")
        
        print(f"[DEBUG] 启动前清理完成: {cleanup_results}")
        
        return success_response({
            "message": f"启动前清理完成",
            "cleanup_results": cleanup_results
        })
        
    except Exception as e:
        print(f"[DEBUG] 启动前清理异常: {e}")
        cleanup_results["errors"].append(f"清理过程异常: {str(e)}")
        
        return success_response({
            "message": f"启动前清理部分完成",
            "cleanup_results": cleanup_results
        })


@bp.route("/stop-and-cleanup", methods=["POST"])
def stop_and_cleanup():
    """停止Docker容器并清理输出文件"""
    print(f"[DEBUG] ========== 停止和清理API被调用 ==========")
    
    _, error = _ensure_authenticated()
    if error:
        print(f"[DEBUG] 认证失败: {error}")
        return error
    
    data = request.get_json()
    print(f"[DEBUG] 接收到的请求数据: {data}")
    
    if not data:
        print(f"[DEBUG] 请求数据为空")
        return make_response(error_response("请求数据不能为空"), 400)
    
    container_id = data.get("container_id")
    protocol = data.get("protocol", "UNKNOWN")
    
    print(f"[DEBUG] 解析参数 - 容器ID: {container_id}, 协议: {protocol}")
    
    if not container_id:
        print(f"[DEBUG] 容器ID为空")
        return make_response(error_response("容器ID不能为空"), 400)
    
    stop_results = {
        "container_stopped": False,
        "container_removed": False,
        "errors": []
    }
    
    try:
        print(f"[DEBUG] 开始停止和清理{protocol}容器: {container_id}")
        
        # 首先检查容器是否存在
        check_result = subprocess.run(
            f"docker ps -a -q --filter id={container_id}",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if check_result.returncode == 0 and check_result.stdout.strip():
            print(f"[DEBUG] 找到容器: {check_result.stdout.strip()}")
        else:
            print(f"[DEBUG] 容器不存在或查找失败: {check_result.stderr}")
            stop_results["errors"].append(f"容器不存在: {container_id}")
        
        # 检查容器是否正在运行
        running_check = subprocess.run(
            f"docker ps -q --filter id={container_id}",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        if running_check.returncode == 0 and running_check.stdout.strip():
            print(f"[DEBUG] 容器正在运行，需要停止: {running_check.stdout.strip()}")
        else:
            print(f"[DEBUG] 容器未在运行或已停止")
        
        # 1. 停止Docker容器（使用更短的超时时间）
        try:
            stop_result = subprocess.run(
                f"docker stop -t 10 {container_id}",  # 给容器10秒时间优雅停止
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15  # 总超时时间15秒
            )
            
            if stop_result.returncode == 0:
                stop_results["container_stopped"] = True
                print(f"[DEBUG] 容器停止成功: {container_id}")
            else:
                error_msg = stop_result.stderr.strip() or "停止容器失败"
                stop_results["errors"].append(f"停止容器失败: {error_msg}")
                print(f"[DEBUG] 停止容器失败: {error_msg}")
                
        except subprocess.TimeoutExpired:
            stop_results["errors"].append("停止容器超时")
            print(f"[DEBUG] 停止容器超时")
        except Exception as e:
            stop_results["errors"].append(f"停止容器异常: {str(e)}")
            print(f"[DEBUG] 停止容器异常: {e}")
        
        # 2. 删除Docker容器
        try:
            remove_result = subprocess.run(
                f"docker rm -f {container_id}",
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10  # 删除操作通常很快
            )
            
            if remove_result.returncode == 0:
                stop_results["container_removed"] = True
                print(f"[DEBUG] 容器删除成功: {container_id}")
            else:
                error_msg = remove_result.stderr.strip() or "删除容器失败"
                stop_results["errors"].append(f"删除容器失败: {error_msg}")
                print(f"[DEBUG] 删除容器失败: {error_msg}")
                
        except subprocess.TimeoutExpired:
            stop_results["errors"].append("删除容器超时")
            print(f"[DEBUG] 删除容器超时")
        except Exception as e:
            stop_results["errors"].append(f"删除容器异常: {str(e)}")
            print(f"[DEBUG] 删除容器异常: {e}")
        
        print(f"[DEBUG] 容器停止完成: {stop_results}")
        
        # 构建响应消息
        success_count = sum([
            stop_results["container_stopped"],
            stop_results["container_removed"]
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
            "stop_results": stop_results
        })
        
    except Exception as e:
        print(f"[DEBUG] 停止过程异常: {e}")
        stop_results["errors"].append(f"停止过程异常: {str(e)}")
        
        return success_response({
            "message": f"{protocol}容器停止部分完成",
            "container_id": container_id,
            "protocol": protocol,
            "stop_results": stop_results
        })


# Detection Results Routes ------------------------------------------------------


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
