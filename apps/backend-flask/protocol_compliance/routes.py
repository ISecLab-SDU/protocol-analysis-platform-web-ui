"""Flask blueprints for the protocol compliance domain."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
import logging
import os
import re
import shutil
import sqlite3
import subprocess
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

VISIBLE_VIOLATION_HISTORY_LIMIT = 5


# Authentication -------------------------------------------------------------

def _ensure_authenticated():
    user = verify_access_token(request.headers.get("Authorization"))
    if not user:
        return None, unauthorized()
    return user, None


# Helpers -------------------------------------------------------------------

def _to_int(value: Optional[str], fallback: int) -> int:
    if value is None:
        return fallback
    try:
        parsed = int(value)
    except ValueError:
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
                statuses.add(cast(TaskStatus, segment))

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
    *,
    collect_warnings: bool = True,
) -> tuple[Optional[Path], list[str]]:
    """Resolve the SQLite database path, collecting warnings."""
    warnings: list[str] = []

    candidate = _expand_path(database_path)
    if candidate and candidate.is_file():
        return candidate, warnings
    if collect_warnings and candidate and not candidate.exists():
        warnings.append(f"指定的数据库路径不存在：{candidate}")

    workspace = _expand_path(workspace_path)
    if workspace:
        if workspace.is_dir():
            matches = sorted(workspace.glob("sqlite_*.db"))
            if matches:
                return matches[0], warnings
            if collect_warnings:
                warnings.append(
                    f"在工作目录 {workspace} 中未找到 sqlite_*.db 文件"
                )
        else:
            if collect_warnings:
                warnings.append(f"工作目录不存在或不可访问：{workspace}")

    return None, warnings


def _violation_history_timestamp_store_path() -> Path:
    state_dir = Path(
        os.environ.get(
            "PROTOCOLGUARD_STATE_DIR",
            str(Path(__file__).resolve().parent / "_state"),
        )
    ).expanduser()
    return state_dir / "violation_history_timestamps.json"


def _violation_history_writable_database_root() -> Path:
    return _violation_history_timestamp_store_path().parent / "writable-databases"


def _sqlite_path_hash(path: Path) -> str:
    return hashlib.sha1(str(path.expanduser()).encode("utf-8")).hexdigest()[:12]


def _violation_history_writable_database_path(
    source_path: Path,
    *,
    job_id: Optional[str],
) -> Path:
    job_key = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(job_id or "manual")).strip("._")
    if not job_key:
        job_key = "manual"
    return (
        _violation_history_writable_database_root()
        / job_key
        / f"{_sqlite_path_hash(source_path)}-{source_path.name}"
    )


def _is_sqlite_database_writable(db_path: Path) -> bool:
    if not db_path.is_file():
        return False
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute("BEGIN IMMEDIATE")
            conn.execute(
                "CREATE TABLE __protocolguard_write_probe__ "
                "(id INTEGER PRIMARY KEY)"
            )
            conn.execute("DROP TABLE __protocolguard_write_probe__")
            conn.rollback()
        return True
    except sqlite3.Error:
        return False


def _copy_sqlite_database_for_violation_history(
    source_path: Path,
    *,
    job_id: Optional[str],
) -> Path:
    destination = _violation_history_writable_database_path(source_path, job_id=job_id)
    if destination.is_file() and _is_sqlite_database_writable(destination):
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, destination)
    os.chmod(destination, 0o600)
    return destination


def _ensure_writable_violation_history_database(
    db_path: Path,
    *,
    job_id: Optional[str],
    warnings: List[str],
) -> Path:
    if _is_sqlite_database_writable(db_path):
        return db_path

    writable_copy = _copy_sqlite_database_for_violation_history(db_path, job_id=job_id)
    warnings.append(
        f"数据库 {db_path} 不可写，已使用后端状态目录中的可写副本：{writable_copy}"
    )
    return writable_copy


def _iter_violation_history_writable_database_copies() -> List[Dict[str, Any]]:
    copy_root = _violation_history_writable_database_root()
    if not copy_root.is_dir():
        return []

    sources: List[Dict[str, Any]] = []
    for db_path in sorted(copy_root.glob("*/*.db")):
        name = db_path.name
        if "-" not in name:
            continue
        original_hash, _ = name.split("-", 1)
        if not re.fullmatch(r"[0-9a-f]{12}", original_hash):
            continue
        job_id = db_path.parent.name if db_path.parent.name != "manual" else None
        sources.append(
            {
                "path": db_path,
                "sourceType": "job" if job_id else "builtin",
                "jobId": job_id,
                "protocolName": None,
                "createdAt": None,
                "updatedAt": None,
                "originalPathHash": original_hash,
            }
        )
    return sources


def _load_violation_history_timestamps() -> Dict[str, Any]:
    store_path = _violation_history_timestamp_store_path()
    if not store_path.is_file():
        return {"databases": {}, "deleted": {}, "rows": {}}
    try:
        payload = json.loads(store_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        LOGGER.warning("Failed to read violation history timestamps: %s", exc)
        return {"databases": {}, "deleted": {}, "rows": {}}
    if not isinstance(payload, dict):
        return {"databases": {}, "deleted": {}, "rows": {}}
    databases = payload.get("databases")
    deleted = payload.get("deleted")
    rows = payload.get("rows")
    return {
        "databases": databases if isinstance(databases, dict) else {},
        "deleted": deleted if isinstance(deleted, dict) else {},
        "rows": rows if isinstance(rows, dict) else {},
    }


def _save_violation_history_timestamps(payload: Dict[str, Any]) -> None:
    store_path = _violation_history_timestamp_store_path()
    try:
        store_path.parent.mkdir(parents=True, exist_ok=True)
        store_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    except OSError as exc:
        LOGGER.warning("Failed to write violation history timestamps: %s", exc)


def _database_history_time_marker(db_path: Path) -> str:
    return _history_database_path_marker(db_path)


def _row_history_time_marker(
    db_path: Path,
    *,
    call_graph: Any,
    code_snippet: Any,
    rule_desc: Any,
) -> str:
    stable_key = "|".join(
        [
            _database_history_time_marker(db_path),
            _dedupe_key(rule_desc),
            hashlib.sha1(str(code_snippet or "").encode("utf-8")).hexdigest(),
            hashlib.sha1(str(call_graph or "").encode("utf-8")).hexdigest(),
        ]
    )
    return hashlib.sha1(stable_key.encode("utf-8")).hexdigest()


def _candidate_database_history_times(db_path: Path) -> List[str]:
    candidates: List[str] = []
    for candidate in [
        db_path,
        Path(__file__).resolve().parent / "databases" / db_path.name,
        Path.cwd() / "database" / db_path.name,
    ]:
        try:
            if candidate.is_file():
                candidates.append(
                    datetime.fromtimestamp(
                        candidate.stat().st_mtime,
                        timezone.utc,
                    ).isoformat()
                )
        except OSError:
            continue
    return candidates


def _database_history_display_time(
    db_path: Path,
    *,
    persist_if_missing: bool = True,
) -> str:
    marker = _database_history_time_marker(db_path)
    timestamps = _load_violation_history_timestamps()
    databases = cast(Dict[str, Any], timestamps["databases"])
    stored = databases.get(marker)
    if isinstance(stored, str) and stored.strip():
        return stored

    candidate_times = _candidate_database_history_times(db_path)
    display_time = (
        min(candidate_times)
        if candidate_times
        else datetime.now(timezone.utc).isoformat()
    )
    if persist_if_missing:
        databases[marker] = display_time
        _save_violation_history_timestamps(timestamps)
    return display_time


def _row_history_display_time(
    db_path: Path,
    *,
    call_graph: Any,
    code_snippet: Any,
    fallback: str,
    persist_if_missing: bool = True,
    rule_desc: Any,
) -> str:
    marker = _row_history_time_marker(
        db_path,
        call_graph=call_graph,
        code_snippet=code_snippet,
        rule_desc=rule_desc,
    )
    timestamps = _load_violation_history_timestamps()
    rows = cast(Dict[str, Any], timestamps["rows"])
    stored = rows.get(marker)
    if isinstance(stored, str) and stored.strip():
        return stored
    if persist_if_missing:
        rows[marker] = fallback
        _save_violation_history_timestamps(timestamps)
    return fallback


def _remember_row_history_display_time(
    db_path: Path,
    *,
    call_graph: Any,
    code_snippet: Any,
    rule_desc: Any,
    timestamp: str,
) -> None:
    timestamps = _load_violation_history_timestamps()
    marker = _row_history_time_marker(
        db_path,
        call_graph=call_graph,
        code_snippet=code_snippet,
        rule_desc=rule_desc,
    )
    rows = cast(Dict[str, Any], timestamps["rows"])
    rows[marker] = timestamp
    _save_violation_history_timestamps(timestamps)


def _history_delete_marker_payload(value: Any) -> str:
    return hashlib.sha1(str(value or "").encode("utf-8")).hexdigest()


def _history_item_delete_markers(item: Dict[str, Any]) -> set[str]:
    markers: set[str] = set()
    item_id = item.get("id")
    if isinstance(item_id, str) and item_id.strip():
        markers.add(f"id:{item_id.strip()}")

    database_key = _dedupe_key(
        item.get("databaseName")
        or Path(str(item.get("databasePath") or "")).name
    )
    rule_key = _dedupe_key(item.get("ruleDesc"))
    reason_key = _dedupe_key(item.get("reason"))
    code_snippet = str(item.get("codeSnippet") or "")
    call_graph = str(item.get("callGraph") or "")
    code_key = _history_delete_marker_payload(code_snippet) if code_snippet else ""
    call_graph_key = _history_delete_marker_payload(call_graph) if call_graph else ""
    violation_key = ";".join(sorted(_violation_match_keys(item.get("violations"))))

    if database_key and rule_key:
        has_specific_evidence = bool(code_key or call_graph_key or violation_key)
        if violation_key:
            markers.add(f"location:{database_key}:{rule_key}:{violation_key}")
        if reason_key and violation_key:
            markers.add(
                f"semantic:{database_key}:{rule_key}:{reason_key}:{violation_key}"
            )
        if code_key or call_graph_key:
            markers.add(
                f"body:{database_key}:{rule_key}:{code_key}:{call_graph_key}"
            )
        if reason_key and not has_specific_evidence:
            markers.add(f"reason:{database_key}:{rule_key}:{reason_key}")
    return markers


def _deleted_violation_history_markers() -> Dict[str, Any]:
    timestamps = _load_violation_history_timestamps()
    deleted = cast(Dict[str, Any], timestamps["deleted"])
    return deleted


def _is_violation_history_deleted(item: Dict[str, Any]) -> bool:
    deleted = _deleted_violation_history_markers()
    item_markers = _history_item_delete_markers(item)
    return any(marker in deleted for marker in item_markers)


def _remember_deleted_violation_history(item: Dict[str, Any]) -> None:
    markers = _history_item_delete_markers(item)
    if not markers:
        return
    timestamps = _load_violation_history_timestamps()
    deleted = cast(Dict[str, Any], timestamps["deleted"])
    deleted_at = datetime.now(timezone.utc).isoformat()
    for marker in markers:
        deleted[marker] = deleted_at
    _save_violation_history_timestamps(timestamps)


def _forget_deleted_violation_history(item: Dict[str, Any]) -> None:
    markers = _history_item_delete_markers(item)
    if not markers:
        return
    timestamps = _load_violation_history_timestamps()
    deleted = cast(Dict[str, Any], timestamps["deleted"])
    changed = False
    for marker in markers:
        if marker in deleted:
            changed = True
            deleted.pop(marker, None)
    if changed:
        _save_violation_history_timestamps(timestamps)


def _candidate_sqlite_roots_for_job(job_id: str) -> list[Path]:
    runtime_root = Path(os.environ.get("PG_RUNTIME_ROOT", "/tmp/protocolguard")).expanduser()
    output_root = Path(os.environ.get("PG_OUTPUT_ROOT", runtime_root / "outputs")).expanduser()
    workspace_root = Path(os.environ.get("PG_WORKSPACE_ROOT", runtime_root / "workspaces")).expanduser()

    roots = [
        output_root / job_id / "database",
        output_root / job_id,
        workspace_root / job_id / "database",
        workspace_root / job_id,
    ]

    snapshot = get_static_analysis_job(job_id)
    if snapshot:
        for key in ("database_path", "databasePath"):
            raw_database_path = snapshot.get(key)
            database_path = _expand_path(str(raw_database_path)) if raw_database_path else None
            if database_path:
                roots.append(database_path.parent if database_path.suffix else database_path)
        for key in ("output_path", "outputPath"):
            raw_output_path = snapshot.get(key)
            output_path = _expand_path(str(raw_output_path)) if raw_output_path else None
            if output_path:
                roots.extend([output_path / "database", output_path])
        for key in ("workspace_path", "workspacePath"):
            raw_workspace_path = snapshot.get(key)
            workspace_path = _expand_path(str(raw_workspace_path)) if raw_workspace_path else None
            if workspace_path:
                roots.extend([workspace_path / "database", workspace_path])

    unique_roots: list[Path] = []
    seen: set[str] = set()
    for root in roots:
        marker = str(root.resolve(strict=False))
        if marker in seen:
            continue
        seen.add(marker)
        unique_roots.append(root)
    return unique_roots


def _resolve_assertion_database_path(database_path: Path) -> tuple[Optional[Path], list[str]]:
    warnings: list[str] = []
    if database_path.is_file():
        return database_path, warnings

    warnings.append(f"指定的分析结果数据不存在：{database_path}")
    job_id = next(
        (
            part
            for part in database_path.parts
            if re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", part)
        ),
        None,
    )
    if not job_id:
        return None, warnings

    expected_name = database_path.name
    for root in _candidate_sqlite_roots_for_job(job_id):
        if not root.exists() or not root.is_dir():
            continue
        named_candidate = root / expected_name
        if named_candidate.is_file():
            return named_candidate, warnings
        matches = sorted(root.glob("*.db"))
        if matches:
            return matches[0], warnings

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


def _has_structured_violation_payload(llm_payload: Dict[str, Any]) -> bool:
    violations = llm_payload.get("violations")
    if not isinstance(violations, list):
        return False
    return any(isinstance(item, dict) for item in violations)


def _classify_rule_result(llm_payload: Dict[str, Any]) -> tuple[str, str]:
    if _has_structured_violation_payload(llm_payload):
        return "violation_found", "发现违规"

    result_text = str(llm_payload.get("result") or "").lower()
    normalized_result = re.sub(r"[\s_-]+", " ", result_text)
    if "no violation" in normalized_result:
        return "no_violation", "未发现违规"
    if "violation" in normalized_result:
        return "violation_found", "发现违规"
    return "unknown", "未判定"


def _llm_payload_history_time(llm_payload: Dict[str, Any]) -> Optional[str]:
    for key in ("updated_at", "updatedAt", "created_at", "createdAt"):
        value = llm_payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


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


def _preview_text(value: Any, limit: int = 240) -> str:
    if value is None:
        return ""
    return str(value)[:limit].replace("\n", "\\n")


def _log_rule_code_snippet_rows(
    *,
    context: str,
    database_path: Path,
    rows: Iterable[sqlite3.Row],
    columns: Optional[List[str]] = None,
    job_id: Any = None,
) -> None:
    materialized_rows = list(rows)
    LOGGER.warning(
        "*** ProtocolGuard rule_code_snippet %s: jobId=%s db=%s columns=%s row_count=%d ***",
        context,
        job_id,
        database_path,
        columns or [],
        len(materialized_rows),
    )
    for index, row in enumerate(materialized_rows[:10], start=1):
        rule_desc = row["rule_desc"] if "rule_desc" in row.keys() else None
        code_snippet = row["code_snippet"] if "code_snippet" in row.keys() else None
        call_graph = row["call_graph"] if "call_graph" in row.keys() else None
        llm_response = row["llm_response"] if "llm_response" in row.keys() else None
        LOGGER.warning(
            (
                "*** ProtocolGuard rule_code_snippet %s row=%d "
                "rule_len=%d code_snippet_len=%d call_graph_len=%d llm_response_len=%d "
                "rule_preview=%r code_snippet_preview=%r ***"
            ),
            context,
            index,
            len(str(rule_desc or "")),
            len(str(code_snippet or "")),
            len(str(call_graph or "")),
            len(str(llm_response or "")),
            _preview_text(rule_desc, 160),
            _preview_text(code_snippet),
        )


def _iter_static_analysis_database_sources(
    job_limit: int,
) -> tuple[List[Dict[str, Any]], List[str]]:
    db_dir = Path(os.path.dirname(__file__)) / "databases"
    sources: List[Dict[str, Any]] = []
    warnings: List[str] = []
    seen_database_paths: set[str] = set()
    shadowed_database_hashes: set[str] = set()

    for source in _iter_violation_history_writable_database_copies():
        db_path = cast(Path, source["path"])
        resolved = str(db_path.resolve())
        seen_database_paths.add(resolved)
        original_hash = source.get("originalPathHash")
        if isinstance(original_hash, str):
            shadowed_database_hashes.add(original_hash)
        sources.append(source)

    if db_dir.is_dir():
        for db_path in sorted(db_dir.glob("sqlite_*.db")):
            resolved = str(db_path.resolve())
            if _sqlite_path_hash(db_path) in shadowed_database_hashes:
                continue
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
            collect_warnings=False,
        )
        warnings.extend(resolve_warnings)
        if not resolved_path:
            continue
        resolved = str(resolved_path.resolve())
        if (
            resolved in seen_database_paths
            or _sqlite_path_hash(resolved_path) in shadowed_database_hashes
        ):
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
    database_display_time = (
        updated_at
        or created_at
        or _database_history_display_time(db_path)
    )

    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error as exc:
        return items, [f"无法打开数据库 {db_path}: {exc}"]

    conn.row_factory = sqlite3.Row
    query = (
        "SELECT rowid AS __rowid, rule_desc, code_snippet, call_graph, llm_response "
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
            row_id=row["__rowid"],
            row_index=index,
            rule_desc=row["rule_desc"],
            source_type=source_type,
        )
        llm_history_time = _llm_payload_history_time(llm_payload)
        row_display_time = (
            llm_history_time
            or updated_at
            or created_at
            or _row_history_display_time(
                db_path,
                call_graph=row["call_graph"],
                code_snippet=row["code_snippet"],
                fallback=llm_history_time or database_display_time,
                rule_desc=row["rule_desc"],
            )
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
                "createdAt": row_display_time,
                "updatedAt": row_display_time,
                "extractedAt": row_display_time,
            }
        )

    conn.close()
    return items, warnings


def _build_violation_history_item_id(
    *,
    db_path: Path,
    job_id: Optional[str],
    row_id: Optional[int] = None,
    row_index: int,
    rule_desc: Any,
    source_type: str,
) -> str:
    row_key = f"rowid:{row_id}" if row_id is not None else str(row_index)
    stable_key = "|".join(
        [
            source_type,
            job_id or "",
            str(db_path),
            str(rule_desc),
            row_key,
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
        "SELECT rowid AS __rowid, rule_desc, code_snippet, call_graph, llm_response "
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
            row_id=row["__rowid"],
            row_index=index,
            rule_desc=row["rule_desc"],
            source_type=source_type,
        )
        legacy_id = _build_violation_history_item_id(
            db_path=db_path,
            job_id=job_id,
            row_index=index,
            rule_desc=row["rule_desc"],
            source_type=source_type,
        )
        legacy_rowid_index_id = _build_violation_history_item_id(
            db_path=db_path,
            job_id=job_id,
            row_index=row["__rowid"],
            rule_desc=row["rule_desc"],
            source_type=source_type,
        )
        if item_id not in {current_id, legacy_id, legacy_rowid_index_id}:
            continue

        llm_payload = _parse_llm_response(row["llm_response"])
        reason = llm_payload.get("reason")
        if not isinstance(reason, str):
            reason = json.dumps(reason, ensure_ascii=False) if reason else None
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
                "callGraph": row["call_graph"],
                "codeSnippet": row["code_snippet"],
                "id": item_id,
                "reason": reason,
                "ruleDesc": row["rule_desc"],
                "violations": _parse_violation_details(llm_payload),
            },
            warnings,
        )

    conn.close()
    return None, warnings


def _delete_violation_history_by_rule_desc(
    db_path: Path,
    *,
    item_id: str,
    rule_desc: str,
) -> tuple[Optional[Dict[str, Any]], List[str]]:
    warnings: List[str] = []

    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error as exc:
        return None, [f"无法打开数据库 {db_path}: {exc}"]

    conn.row_factory = sqlite3.Row
    query = (
        "SELECT rowid AS __rowid, rule_desc, code_snippet, call_graph, llm_response "
        "FROM rule_code_snippet"
    )
    try:
        rows = conn.execute(query).fetchall()
    except sqlite3.Error as exc:
        conn.close()
        return None, [f"无法读取数据库 {db_path} 的 rule_code_snippet: {exc}"]

    matched = _find_matching_rule_row(rows, rule_desc)
    if not matched:
        conn.close()
        return None, warnings

    llm_payload = _parse_llm_response(matched["llm_response"])
    reason = llm_payload.get("reason")
    if not isinstance(reason, str):
        reason = json.dumps(reason, ensure_ascii=False) if reason else None
    try:
        conn.execute(
            "DELETE FROM rule_code_snippet WHERE rowid = ?",
            (matched["__rowid"],),
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
                "callGraph": matched["call_graph"],
                "codeSnippet": matched["code_snippet"],
                "id": item_id,
                "reason": reason,
                "ruleDesc": matched["rule_desc"],
                "violations": _parse_violation_details(llm_payload),
            },
            warnings,
        )


def _delete_analysis_result_violation_history_from_database(
    item_id: str,
    *,
    job_limit: int,
) -> tuple[Optional[Dict[str, Any]], List[str]]:
    warnings: List[str] = []

    for entry in list_static_analysis_history(limit=job_limit, include_result=True):
        if entry.get("status") != "completed":
            continue
        for item in _read_violation_history_from_analysis_result(entry):
            if item.get("id") != item_id:
                continue

            resolved_path, resolve_warnings = _find_sqlite_file(
                cast(Optional[str], item.get("databasePath")),
                cast(Optional[str], entry.get("workspacePath")),
            )
            warnings.extend(resolve_warnings)
            if not resolved_path:
                return None, warnings

            deleted, db_warnings = _delete_violation_history_by_rule_desc(
                resolved_path,
                item_id=item_id,
                rule_desc=str(item.get("ruleDesc") or ""),
            )
            warnings.extend(db_warnings)
            return deleted, warnings

    return None, warnings


def _normalized_history_match_text(value: Any) -> str:
    return " ".join(str(value or "").split()).lower()


def _violation_match_keys(violations: Any) -> set[str]:
    if not isinstance(violations, list):
        return set()

    keys: set[str] = set()
    for violation in violations:
        if not isinstance(violation, dict):
            continue
        code_lines = violation.get("codeLines") or violation.get("code_lines")
        if isinstance(code_lines, list):
            lines = ",".join(str(item) for item in code_lines)
        else:
            lines = ""
        keys.add(
            "|".join(
                [
                    _dedupe_key(violation.get("filename")),
                    _dedupe_key(
                        violation.get("functionName")
                        or violation.get("function_name"),
                    ),
                    lines,
                ]
            )
        )
    return {key for key in keys if key.strip("|")}


def _score_violation_history_payload_row(
    row: sqlite3.Row,
    payload: Dict[str, Any],
) -> int:
    score = 0
    rule_key = _dedupe_key(payload.get("ruleDesc"))
    row_rule_key = _dedupe_key(row["rule_desc"])
    if rule_key:
        if row_rule_key == rule_key:
            score += 100
        elif rule_key in row_rule_key or row_rule_key in rule_key:
            score += 50
        else:
            return 0

    code_snippet = _normalized_history_match_text(payload.get("codeSnippet"))
    row_code_snippet = _normalized_history_match_text(row["code_snippet"])
    if code_snippet and row_code_snippet:
        if code_snippet == row_code_snippet:
            score += 80
        elif code_snippet in row_code_snippet or row_code_snippet in code_snippet:
            score += 35

    call_graph = _normalized_history_match_text(payload.get("callGraph"))
    row_call_graph = _normalized_history_match_text(row["call_graph"])
    if call_graph and row_call_graph:
        if call_graph == row_call_graph:
            score += 40
        elif call_graph in row_call_graph or row_call_graph in call_graph:
            score += 20

    llm_payload = _parse_llm_response(row["llm_response"])
    reason = _normalized_history_match_text(payload.get("reason"))
    row_reason = _normalized_history_match_text(llm_payload.get("reason"))
    if reason and row_reason:
        if reason == row_reason:
            score += 70
        elif reason in row_reason or row_reason in reason:
            score += 35

    payload_violation_keys = _violation_match_keys(payload.get("violations"))
    row_violation_keys = _violation_match_keys(_parse_violation_details(llm_payload))
    if payload_violation_keys and row_violation_keys:
        score += 50 * len(payload_violation_keys & row_violation_keys)

    return score


def _delete_violation_history_by_payload(
    db_path: Path,
    *,
    item_id: str,
    payload: Dict[str, Any],
) -> tuple[Optional[Dict[str, Any]], List[str]]:
    warnings: List[str] = []

    try:
        conn = sqlite3.connect(db_path)
    except sqlite3.Error as exc:
        return None, [f"无法打开数据库 {db_path}: {exc}"]

    conn.row_factory = sqlite3.Row
    query = (
        "SELECT rowid AS __rowid, rule_desc, code_snippet, call_graph, llm_response "
        "FROM rule_code_snippet"
    )
    try:
        rows = conn.execute(query).fetchall()
    except sqlite3.Error as exc:
        conn.close()
        return None, [f"无法读取数据库 {db_path} 的 rule_code_snippet: {exc}"]

    scored_rows = [
        (_score_violation_history_payload_row(row, payload), row) for row in rows
    ]
    scored_rows = [entry for entry in scored_rows if entry[0] >= 100]
    if not scored_rows:
        conn.close()
        return None, warnings

    scored_rows.sort(key=lambda entry: entry[0], reverse=True)
    matched = scored_rows[0][1]
    llm_payload = _parse_llm_response(matched["llm_response"])
    reason = llm_payload.get("reason")
    if not isinstance(reason, str):
        reason = json.dumps(reason, ensure_ascii=False) if reason else None

    try:
        conn.execute(
            "DELETE FROM rule_code_snippet WHERE rowid = ?",
            (matched["__rowid"],),
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
                "callGraph": matched["call_graph"],
                "codeSnippet": matched["code_snippet"],
                "id": item_id,
                "reason": reason,
                "ruleDesc": matched["rule_desc"],
                "violations": _parse_violation_details(llm_payload),
            },
            warnings,
        )


def _payload_candidate_database_sources(
    payload: Dict[str, Any],
    sources: List[Dict[str, Any]],
) -> tuple[List[Path], List[str]]:
    warnings: List[str] = []
    candidates: List[Path] = []
    seen: set[str] = set()

    def add_candidate(path: Optional[Path]) -> None:
        if not path:
            return
        marker = _history_database_path_marker(path)
        if marker in seen:
            return
        seen.add(marker)
        candidates.append(path)

    resolved_path, resolve_warnings = _find_sqlite_file(
        cast(Optional[str], payload.get("databasePath")),
        cast(Optional[str], payload.get("workspacePath")),
        collect_warnings=False,
    )
    warnings.extend(resolve_warnings)
    add_candidate(resolved_path)

    database_name = _dedupe_key(payload.get("databaseName"))
    for source in sources:
        db_path = cast(Path, source["path"])
        if database_name and _dedupe_key(db_path.name) == database_name:
            add_candidate(db_path)

    for source in sources:
        add_candidate(cast(Path, source["path"]))

    return candidates, warnings


def _delete_violation_history_from_payload_sources(
    item_id: str,
    *,
    payload: Dict[str, Any],
    sources: List[Dict[str, Any]],
) -> tuple[Optional[Dict[str, Any]], List[str]]:
    candidates, warnings = _payload_candidate_database_sources(payload, sources)
    for db_path in candidates:
        deleted, db_warnings = _delete_violation_history_by_payload(
            db_path,
            item_id=item_id,
            payload=payload,
        )
        warnings.extend(db_warnings)
        if deleted:
            return deleted, warnings
    return None, warnings


def _find_matching_rule_row(
    rows: list[sqlite3.Row],
    rule_desc: str,
) -> Optional[sqlite3.Row]:
    rule_key = _dedupe_key(rule_desc)
    if not rule_key:
        return rows[0] if rows else None

    for row in rows:
        if _dedupe_key(row["rule_desc"]) == rule_key:
            return row

    for row in rows:
        row_key = _dedupe_key(row["rule_desc"])
        if rule_key in row_key or row_key in rule_key:
            return row

    return None


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


def _history_database_path_marker(value: Any) -> str:
    if not value:
        return ""
    try:
        return str(Path(str(value)).expanduser().resolve(strict=False))
    except (OSError, RuntimeError, ValueError):
        return str(value)


def _strip_archive_suffix(filename: str) -> str:
    normalized = filename.strip()
    for suffix in (".tar.gz", ".tar.bz2", ".tar.xz", ".zip", ".tgz", ".tbz2", ".txz"):
        if normalized.lower().endswith(suffix):
            return normalized[: -len(suffix)]
    return Path(normalized).stem or normalized


def _get_static_analysis_verdicts(result: Any) -> List[Dict[str, Any]]:
    if not isinstance(result, dict):
        return []
    model_response = result.get("modelResponse")
    if not isinstance(model_response, dict):
        return []
    verdicts = model_response.get("verdicts")
    if not isinstance(verdicts, list):
        return []
    return [item for item in verdicts if isinstance(item, dict)]


def _analysis_result_inputs(result: Any) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    inputs = result.get("inputs")
    return inputs if isinstance(inputs, dict) else {}


def _analysis_result_artifacts(result: Any) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return {}
    artifacts = result.get("artifacts")
    return artifacts if isinstance(artifacts, dict) else {}


def _normalize_implementation_from_analysis_result(
    entry: Dict[str, Any],
    result: Dict[str, Any],
) -> str:
    inputs = _analysis_result_inputs(result)
    raw_name = (
        inputs.get("codeFileName")
        or entry.get("codeFileName")
        or entry.get("databasePath")
        or entry.get("jobId")
        or "analysis-result"
    )
    name = Path(str(raw_name)).name
    return _strip_archive_suffix(name)


def _analysis_result_database_path(
    entry: Dict[str, Any],
    result: Dict[str, Any],
) -> Optional[str]:
    artifacts = _analysis_result_artifacts(result)
    raw_path = artifacts.get("database") or entry.get("databasePath")
    return str(raw_path) if raw_path else None


def _analysis_result_database_name(
    entry: Dict[str, Any],
    result: Dict[str, Any],
) -> str:
    database_path = _analysis_result_database_path(entry, result)
    if database_path:
        return Path(database_path).name
    return "code-locate-consistency"


def _verdict_result_status(verdict: Dict[str, Any]) -> tuple[str, str]:
    compliance = str(verdict.get("compliance") or "").lower()
    if compliance == "non_compliant":
        return "violation_found", "发现违规"
    if compliance == "compliant":
        return "no_violation", "未发现违规"
    return "unknown", "未判定"


def _verdict_rule_desc(verdict: Dict[str, Any]) -> str:
    related_rule = verdict.get("relatedRule")
    if isinstance(related_rule, dict):
        requirement = related_rule.get("requirement")
        if isinstance(requirement, str) and requirement.strip():
            return requirement.strip()
        rule_id = related_rule.get("id")
        if isinstance(rule_id, str) and rule_id.strip():
            return rule_id.strip()
    category = verdict.get("category")
    if isinstance(category, str) and category.strip():
        return category.strip()
    return "未命名规则"


def _verdict_code_lines(verdict: Dict[str, Any]) -> Optional[List[int]]:
    line_range = verdict.get("lineRange")
    if not isinstance(line_range, list) or len(line_range) < 2:
        return None
    try:
        start = int(line_range[0])
        end = int(line_range[1])
    except (TypeError, ValueError):
        return None
    if start <= 0 or end <= 0:
        return None
    if end < start:
        start, end = end, start
    return list(range(start, min(end, start + 199) + 1))


def _verdict_violation_details(
    verdict: Dict[str, Any],
) -> Optional[List[Dict[str, Any]]]:
    location = verdict.get("location")
    location = location if isinstance(location, dict) else {}
    filename = location.get("file")
    function_name = location.get("function")
    code_lines = _verdict_code_lines(verdict)
    if not filename and not function_name and not code_lines:
        return None
    return [
        {
            "filename": filename,
            "functionName": function_name,
            "codeLines": code_lines,
        }
    ]


def _build_analysis_result_history_item_id(
    *,
    entry: Dict[str, Any],
    verdict: Dict[str, Any],
    row_index: int,
) -> str:
    related_rule = verdict.get("relatedRule")
    rule_id = related_rule.get("id") if isinstance(related_rule, dict) else None
    stable_key = "|".join(
        [
            "analysis-result",
            str(entry.get("jobId") or ""),
            str(verdict.get("findingId") or ""),
            str(rule_id or ""),
            _verdict_rule_desc(verdict),
            str(row_index),
        ]
    )
    return hashlib.sha1(stable_key.encode("utf-8")).hexdigest()


def _read_violation_history_from_analysis_result(
    entry: Dict[str, Any],
) -> List[Dict[str, Any]]:
    result = entry.get("result")
    if not isinstance(result, dict):
        return []

    verdicts = _get_static_analysis_verdicts(result)
    if not verdicts:
        return []

    implementation_name = _normalize_implementation_from_analysis_result(entry, result)
    resolved_protocol = _normalize_protocol_name(
        cast(Optional[str], entry.get("protocolName")),
        implementation_name,
    )
    database_path = _analysis_result_database_path(entry, result)
    database_name = _analysis_result_database_name(entry, result)
    extracted_at = (
        entry.get("completedAt")
        or entry.get("updatedAt")
        or datetime.now(timezone.utc).isoformat()
    )

    items: List[Dict[str, Any]] = []
    for index, verdict in enumerate(verdicts, start=1):
        result_status, result_label = _verdict_result_status(verdict)
        reason = verdict.get("explanation")
        if isinstance(reason, str):
            reason = reason.strip()
        elif reason is not None:
            reason = json.dumps(reason, ensure_ascii=False)

        items.append(
            {
                "id": _build_analysis_result_history_item_id(
                    entry=entry,
                    verdict=verdict,
                    row_index=index,
                ),
                "sourceType": "job",
                "jobId": entry.get("jobId"),
                "implementationName": implementation_name,
                "protocolName": resolved_protocol,
                "databaseName": database_name,
                "databasePath": database_path,
                "ruleDesc": _verdict_rule_desc(verdict),
                "result": result_status,
                "resultLabel": result_label,
                "reason": reason,
                "codeSnippet": None,
                "callGraph": None,
                "llmRaw": verdict,
                "violations": _verdict_violation_details(verdict),
                "createdAt": entry.get("createdAt") or extracted_at,
                "updatedAt": entry.get("updatedAt") or extracted_at,
                "extractedAt": extracted_at,
            }
        )

    return items


def _find_static_analysis_history_entry(
    job_id: Any,
    *,
    limit: int = 500,
) -> Optional[Dict[str, Any]]:
    if not job_id:
        return None
    job_key = str(job_id)
    for entry in list_static_analysis_history(limit=limit, include_result=True):
        if str(entry.get("jobId") or "") == job_key:
            return entry
    return None


def _read_database_insights_from_analysis_result(
    entry: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    result = entry.get("result")
    if not isinstance(result, dict):
        return None

    history_items = _read_violation_history_from_analysis_result(entry)
    if not history_items:
        return None

    artifacts = _analysis_result_artifacts(result)
    database_path = _analysis_result_database_path(entry, result)
    workspace_path = artifacts.get("workspace") or entry.get("workspacePath")
    findings = [
        {
            "ruleDesc": item.get("ruleDesc"),
            "codeSnippet": item.get("codeSnippet"),
            "callGraph": item.get("callGraph"),
            "llmRaw": item.get("llmRaw"),
            "reason": item.get("reason"),
            "result": item.get("result"),
            "resultLabel": item.get("resultLabel"),
            "violations": item.get("violations"),
        }
        for item in history_items
    ]
    return {
        "databasePath": database_path,
        "workspacePath": str(workspace_path) if workspace_path else None,
        "extractedAt": (
            entry.get("completedAt")
            or entry.get("updatedAt")
            or datetime.now(timezone.utc).isoformat()
        ),
        "findings": findings,
    }


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


def _read_overview_from_analysis_result(
    entry: Dict[str, Any],
) -> tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    result = entry.get("result")
    if not isinstance(result, dict):
        return None, []

    verdicts = _get_static_analysis_verdicts(result)
    if not verdicts:
        return None, []

    implementation_name = _normalize_implementation_from_analysis_result(entry, result)
    resolved_protocol = _normalize_protocol_name(
        cast(Optional[str], entry.get("protocolName")),
        implementation_name,
    )
    database_name = _analysis_result_database_name(entry, result)

    rule_status_by_key: Dict[str, str] = {}
    code_snippet_rule_keys: set[str] = set()
    violation_location_keys: set[str] = set()
    top_findings: List[Dict[str, Any]] = []

    for verdict in verdicts:
        rule_desc = _verdict_rule_desc(verdict)
        rule_key = _dedupe_key(rule_desc)
        result_status, _ = _verdict_result_status(verdict)
        _merge_rule_status(rule_status_by_key, rule_key, result_status)

        location = verdict.get("location")
        if isinstance(location, dict) and location.get("file"):
            code_snippet_rule_keys.add(rule_key)

        violations = _verdict_violation_details(verdict)
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
                    "rule": _truncate_text(rule_desc, 160),
                    "reason": _truncate_text(verdict.get("explanation"), 220),
                }
            )

    item = {
        "name": implementation_name,
        "protocol": resolved_protocol,
        "database": database_name,
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
    return item, top_findings


@bp.route("/static-analysis/database-overview", methods=["GET"])
def static_analysis_database_overview():
    _, error = _ensure_authenticated()
    if error:
        return error

    job_limit = _to_int(request.args.get("jobLimit"), 200)
    history_entries = list_static_analysis_history(
        limit=job_limit,
        include_result=True,
    )
    result_backed_job_ids: set[str] = set()
    sources, warnings = _iter_static_analysis_database_sources(job_limit)
    summary: Dict[str, int] = defaultdict(int)
    table_totals: Dict[str, int] = defaultdict(int)
    protocol_totals: Dict[str, Dict[str, int]] = {}
    implementation_groups: Dict[tuple[str, str], Dict[str, Any]] = {}
    top_findings: List[Dict[str, Any]] = []

    def absorb_overview_item(
        item: Optional[Dict[str, Any]],
        findings: List[Dict[str, Any]],
        table_counts: Optional[Dict[str, int]] = None,
    ) -> None:
        if item is None:
            return

        top_findings.extend(findings)
        for table, count in (table_counts or {}).items():
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

    for entry in history_entries:
        if entry.get("status") != "completed":
            continue
        item, findings = _read_overview_from_analysis_result(entry)
        if item is None:
            continue
        job_id = entry.get("jobId")
        if job_id:
            result_backed_job_ids.add(str(job_id))
        absorb_overview_item(item, findings)

    for source in sources:
        if (
            source.get("sourceType") == "job"
            and source.get("jobId")
            and str(source.get("jobId")) in result_backed_job_ids
        ):
            continue
        db_path = cast(Path, source["path"])
        item, findings, table_counts, db_warnings = _read_overview_from_database(
            db_path,
            protocol_name=cast(Optional[str], source.get("protocolName")),
        )
        warnings.extend(db_warnings)
        absorb_overview_item(item, findings, table_counts)

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
    history_entries = list_static_analysis_history(
        limit=job_limit,
        include_result=True,
    )
    database_backed_job_ids: set[str] = set()
    database_backed_paths: set[str] = set()
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
        if db_items:
            database_backed_paths.add(_history_database_path_marker(db_path))
            if source.get("sourceType") == "job" and source.get("jobId"):
                database_backed_job_ids.add(str(source["jobId"]))

    for entry in history_entries:
        if entry.get("status") != "completed":
            continue
        job_id = entry.get("jobId")
        if job_id and str(job_id) in database_backed_job_ids:
            continue
        result_items = _read_violation_history_from_analysis_result(entry)
        if result_items:
            items.extend(
                item
                for item in result_items
                if _history_database_path_marker(item.get("databasePath"))
                not in database_backed_paths
            )

    items = [item for item in items if not _is_violation_history_deleted(item)]

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
    visible_items = items[:VISIBLE_VIOLATION_HISTORY_LIMIT]
    payload: Dict[str, Any] = {
        "items": visible_items,
        "count": len(visible_items),
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
    delete_payload = request.get_json(silent=True)
    delete_payload = delete_payload if isinstance(delete_payload, dict) else {}
    tombstone_item: Dict[str, Any] = {**delete_payload, "id": item_id}
    if delete_payload and _is_violation_history_deleted(tombstone_item):
        return make_response(
            success_response(
                {
                    "databaseName": str(
                        delete_payload.get("databaseName") or "",
                    ),
                    "databasePath": delete_payload.get("databasePath"),
                    "deleted": True,
                    "id": item_id,
                }
            ),
            200,
        )
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
                _remember_deleted_violation_history(
                    {**delete_payload, **deleted, "id": item_id}
                )
                payload: Dict[str, Any] = {**deleted, "deleted": True}
                if warnings:
                    payload["warnings"] = warnings
                return make_response(success_response(payload), 200)

        if delete_payload:
            deleted, payload_warnings = _delete_violation_history_from_payload_sources(
                item_id,
                payload=delete_payload,
                sources=sources,
            )
            warnings.extend(payload_warnings)
            if deleted:
                _remember_deleted_violation_history(
                    {**delete_payload, **deleted, "id": item_id}
                )
                response_payload = {**deleted, "deleted": True}
                if warnings:
                    response_payload["warnings"] = warnings
                return make_response(success_response(response_payload), 200)

        deleted, result_warnings = (
            _delete_analysis_result_violation_history_from_database(
                item_id,
                job_limit=job_limit,
            )
        )
        warnings.extend(result_warnings)
        if deleted:
            _remember_deleted_violation_history(
                {**delete_payload, **deleted, "id": item_id}
            )
            payload = {**deleted, "deleted": True}
            if warnings:
                payload["warnings"] = warnings
            return make_response(success_response(payload), 200)

        if delete_payload and delete_payload.get("ruleDesc"):
            _remember_deleted_violation_history(tombstone_item)
            response_payload = {
                "databaseName": str(delete_payload.get("databaseName") or ""),
                "databasePath": delete_payload.get("databasePath"),
                "deleted": True,
                "id": item_id,
            }
            if warnings:
                response_payload["warnings"] = warnings
            return make_response(success_response(response_payload), 200)
    except RuntimeError as exc:
        LOGGER.error("Failed to delete violation history item %s: %s", item_id, exc)
        return make_response(error_response(str(exc)), 500)

    detail: Dict[str, Any] = {"id": item_id}
    if warnings:
        detail["warnings"] = warnings
    return make_response(error_response("历史记录不存在", detail), 404)


@bp.route("/static-analysis/violation-history", methods=["POST"])
def upsert_static_analysis_violation_history():
    _, error = _ensure_authenticated()
    if error:
        return error

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return make_response(error_response("请求体必须为 JSON 对象"), 400)

    database_path_raw = cast(Optional[str], payload.get("databasePath"))
    workspace_path_raw = cast(Optional[str], payload.get("workspacePath"))
    job_id = cast(Optional[str], payload.get("jobId"))
    rule_desc = str(payload.get("ruleDesc") or "").strip()
    reason = str(payload.get("reason") or "工作台结果验证发现违规证据").strip()
    code_snippet = payload.get("codeSnippet")
    call_graph = payload.get("callGraph")
    violations_payload = payload.get("violations")

    resolved_path, warnings = _find_sqlite_file(database_path_raw, workspace_path_raw)
    if not resolved_path:
        return make_response(
            error_response(
                "未找到可写入的静态分析结果数据库",
                {
                    "databasePath": database_path_raw,
                    "jobId": job_id,
                    "warnings": warnings or None,
                    "workspacePath": workspace_path_raw,
                },
            ),
            404,
        )

    try:
        resolved_path = _ensure_writable_violation_history_database(
            resolved_path,
            job_id=job_id,
            warnings=warnings,
        )
    except OSError as exc:
        return make_response(error_response(f"准备可写数据库失败：{exc}"), 500)

    try:
        conn = sqlite3.connect(resolved_path)
    except sqlite3.Error as exc:
        return make_response(error_response(f"无法打开静态分析结果数据库：{exc}"), 500)

    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT rowid AS __rowid, rule_desc, code_snippet, call_graph, llm_response "
            "FROM rule_code_snippet"
        ).fetchall()
    except sqlite3.Error as exc:
        conn.close()
        return make_response(error_response(f"读取静态分析规则结果失败：{exc}"), 500)

    matched = _find_matching_rule_row(rows, rule_desc)
    if matched is None:
        conn.close()
        return make_response(
            error_response(
                "未找到匹配的规则记录，无法写入违规历史",
                {"databasePath": str(resolved_path), "ruleDesc": rule_desc},
            ),
            404,
        )
    matched_index = next(
        (
            index
            for index, row in enumerate(rows, start=1)
            if row["__rowid"] == matched["__rowid"]
        ),
        1,
    )

    llm_payload = _parse_llm_response(matched["llm_response"])
    if not isinstance(llm_payload, dict):
        llm_payload = {}
    updated_at = datetime.now(timezone.utc).isoformat()
    llm_payload.update(
        {
            "reason": reason,
            "result": "violation_found",
            "updated_by": "workbench_result_verification",
            "updated_at": updated_at,
        }
    )
    if isinstance(violations_payload, list) and violations_payload:
        llm_payload["violations"] = violations_payload

    next_code_snippet = (
        code_snippet
        if isinstance(code_snippet, str) and code_snippet.strip()
        else matched["code_snippet"]
    )
    next_call_graph = (
        call_graph
        if isinstance(call_graph, str) and call_graph.strip()
        else matched["call_graph"]
    )

    try:
        conn.execute(
            "UPDATE rule_code_snippet "
            "SET code_snippet = ?, call_graph = ?, llm_response = ? "
            "WHERE rowid = ?",
            (
                next_code_snippet,
                next_call_graph,
                json.dumps(llm_payload, ensure_ascii=False),
                matched["__rowid"],
            ),
        )
        conn.commit()
    except sqlite3.Error as exc:
        conn.close()
        return make_response(error_response(f"写入违规历史失败：{exc}"), 500)

    _remember_row_history_display_time(
        resolved_path,
        call_graph=next_call_graph,
        code_snippet=next_code_snippet,
        rule_desc=matched["rule_desc"],
        timestamp=updated_at,
    )
    _forget_deleted_violation_history(
        {
            "callGraph": next_call_graph,
            "codeSnippet": next_code_snippet,
            "databaseName": resolved_path.name,
            "databasePath": str(resolved_path),
            "reason": reason,
            "ruleDesc": matched["rule_desc"],
            "violations": (
                violations_payload
                if isinstance(violations_payload, list)
                else None
            ),
        }
    )

    item_id = _build_violation_history_item_id(
        db_path=resolved_path,
        job_id=job_id,
        row_id=matched["__rowid"],
        row_index=matched_index,
        rule_desc=matched["rule_desc"],
        source_type="job" if job_id else "builtin",
    )
    conn.close()

    return make_response(
        success_response(
            {
                "databasePath": str(resolved_path),
                "id": item_id,
                "result": "violation_found",
                "resultLabel": "发现违规",
                "ruleDesc": matched["rule_desc"],
                "updated": True,
                "warnings": warnings,
            }
        ),
        200,
    )


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
        history_entry = _find_static_analysis_history_entry(job_id)
        if history_entry:
            result_payload = _read_database_insights_from_analysis_result(history_entry)
            if result_payload:
                LOGGER.warning(
                    (
                        "*** ProtocolGuard rule_code_snippet database-insights fallback: "
                        "SQLite not found, returning history verdicts without code snippets. "
                        "jobId=%s databasePath=%r workspacePath=%r findings=%d warnings=%s ***"
                    ),
                    job_id,
                    database_path_raw,
                    workspace_path_raw,
                    len(result_payload.get("findings") or []),
                    warnings,
                )
                return make_response(success_response(result_payload), 200)

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
        columns = [
            str(row["name"])
            for row in conn.execute("PRAGMA table_info(rule_code_snippet)").fetchall()
        ]
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

    _log_rule_code_snippet_rows(
        context="database-insights",
        database_path=resolved_path,
        rows=rows,
        columns=columns,
        job_id=job_id,
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
        database_path = _expand_path(database_path_requested)
        if database_path is None:
            return make_response(error_response("分析结果数据路径无效"), 400)
        resolved_database_path, database_warnings = _resolve_assertion_database_path(database_path)
        if resolved_database_path is None:
            return make_response(
                error_response(f"分析结果数据不存在：{database_path}"),
                400,
            )
        if database_warnings:
            LOGGER.warning(
                "Resolved assertion analysis data with fallback",
                extra={
                    "requestedDatabasePath": str(database_path),
                    "resolvedDatabasePath": str(resolved_database_path),
                    "warnings": database_warnings,
                },
            )
        database_path = resolved_database_path
        try:
            database_data = database_path.read_bytes()
        except OSError as exc:
            LOGGER.exception("Failed to read assertion analysis data: %s", database_path)
            return make_response(error_response(f"读取分析结果数据失败：{exc}"), 500)
        database_name = database_path.name
        database_source = str(database_path)
    else:
        database_upload_raw = request.files.get("database")
        if not isinstance(database_upload_raw, FileStorage):
            return make_response(error_response("请上传完整文件：分析结果数据文件"), 400)
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
    
    instrumentation_data = cast(Dict[str, object], instrumentation)
    artifacts = instrumentation_data.get("artifacts")
    if not artifacts or not isinstance(artifacts, dict):
        return make_response(error_response("未找到 instrumentation artifacts"), 404)
    
    artifact_data = cast(Dict[str, object], artifacts)
    diff_output = artifact_data.get("diffOutput")
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

    filename = os.environ.get("AFLNET_FALLBACK_LOG_FILE_NAME", "plot_data")
    candidates = [
        _repo_root() / "fuzz-output",
        _repo_root().parent / "fuzz-output",
        Path.cwd() / "fuzz-output",
        Path("/tmp/protocolguard/fuzz-output"),
    ]
    seen: set[Path] = set()
    for candidate in candidates:
        try:
            resolved = candidate.expanduser().resolve()
        except (OSError, RuntimeError):
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if (resolved / filename).exists():
            return resolved

    for candidate in candidates:
        expanded = candidate.expanduser()
        if expanded.exists():
            return expanded

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

    if not content:
        return make_response(error_response("脚本内容不能为空"), 400)

    # 根据协议获取配置
    if protocol == "RTSP":
        # SOL使用ProtocolGuard，不需要脚本文件，直接返回成功
        return success_response({
            "message": "SOL不需要脚本文件，直接启动docker即可生成日志",
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


@bp.route("/execute-command", methods=["POST"])
def execute_command():
    """执行shell命令启动程序"""
    print("[DEBUG] ========== execute-command API被调用 ==========")
    
    _, error = _ensure_authenticated()
    if error:
        print(f"[DEBUG] 认证失败: {error}")
        return error

    data = request.get_json()
    print(f"[DEBUG] 接收到的请求数据: {data}")
    
    if not data:
        print("[DEBUG] 请求数据为空")
        return make_response(error_response("请求数据不能为空"), 400)

    protocol = data.get("protocol", "UNKNOWN")
    protocol_implementations = data.get("protocolImplementations", [])
    
    print(f"[DEBUG] 解析参数 - 协议: {protocol}, 实现: {protocol_implementations}")

    # 根据协议获取配置
    if protocol == "MQTT":
        # MQTT协议支持双引擎配置
        if protocol_implementations and "SOL" in protocol_implementations:
            # SOL使用AFLNET引擎 (原RTSP配置)
            command = cast(str, RTSP_CONFIG["shell_command"])
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
                print("[DEBUG] 命令执行成功")
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
        print("[DEBUG] 命令执行超时")
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
    max_lines = _to_int(str(data.get("maxLines")), 0) if data.get("maxLines") is not None else 0

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
        print(f"[DEBUG] 日志文件大小: {file_size} 字节")
        
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
        
        print(f"[DEBUG] 读取到新内容长度: {len(new_content)} 字符")
        print(f"[DEBUG] 新的读取位置: {current_position}")
        
        if new_content:
            print(f"[DEBUG] 新内容预览: {new_content[:200]}...")
        
        response_data = {
            "content": new_content,
            "position": current_position,
            "protocol": protocol,
            "file_size": file_size,
            "is_eof": current_position >= file_size,
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
    print("[DEBUG] ========== 启动前清理API被调用 ==========")
    
    _, error = _ensure_authenticated()
    if error:
        print(f"[DEBUG] 认证失败: {error}")
        return error
    
    data = request.get_json()
    print(f"[DEBUG] 接收到的请求数据: {data}")
    
    if not data:
        print("[DEBUG] 请求数据为空")
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
                print("[DEBUG] 没有找到运行中的protocolguard容器")
        
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
            "message": "启动前清理完成",
            "cleanup_results": cleanup_results
        })
        
    except Exception as e:
        print(f"[DEBUG] 启动前清理异常: {e}")
        cleanup_results["errors"].append(f"清理过程异常: {str(e)}")
        
        return success_response({
            "message": "启动前清理部分完成",
            "cleanup_results": cleanup_results
        })


@bp.route("/stop-and-cleanup", methods=["POST"])
def stop_and_cleanup():
    """停止Docker容器并清理输出文件"""
    print("[DEBUG] ========== 停止和清理API被调用 ==========")
    
    _, error = _ensure_authenticated()
    if error:
        print(f"[DEBUG] 认证失败: {error}")
        return error
    
    data = request.get_json()
    print(f"[DEBUG] 接收到的请求数据: {data}")
    
    if not data:
        print("[DEBUG] 请求数据为空")
        return make_response(error_response("请求数据不能为空"), 400)
    
    container_id = data.get("container_id")
    protocol = data.get("protocol", "UNKNOWN")
    
    print(f"[DEBUG] 解析参数 - 容器ID: {container_id}, 协议: {protocol}")
    
    if not container_id:
        print("[DEBUG] 容器ID为空")
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
            print("[DEBUG] 容器未在运行或已停止")
        
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
            print("[DEBUG] 停止容器超时")
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
            print("[DEBUG] 删除容器超时")
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
