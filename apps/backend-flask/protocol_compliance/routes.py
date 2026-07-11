"""Flask blueprints for the protocol compliance domain."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import sqlite3
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, cast

from flask import Blueprint, make_response, request, send_file
from werkzeug.datastructures import FileStorage

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
from .store import STORE
from .pipeline_runner import (
    PipelineExecutionError,
    PipelineResultNotFoundError,
    run_protocol_pipeline,
)
from .aflnet import (
    RTSP_CONFIG as RTSP_CONFIG,
    _aflnet_fallback_output_root,
    _aflnet_log_file_for_source,
    _aflnet_output_root,
    _aflnet_result_path_info,
    _aflnet_shell_command,
    _resolve_aflnet_output_source,
)
from .aflnet_routes import register_aflnet_routes
from .legacy_analysis_history import (
    append_analysis_history,
    list_available_implementations as list_legacy_available_implementations,
    read_analysis_history,
    read_detection_results,
)
from .route_helpers import (
    _collect_exception_details as _collect_exception_details,
    _extract_protocol_metadata_from_config,
    _normalize_status,
    _parse_tags,
    _read_upload,
    _strip_extension,
    _to_int,
)
from .static_analysis_models import (
    PROTOCOL_ALIASES as PROTOCOL_ALIASES,
    PROTOCOL_BY_IMPLEMENTATION as PROTOCOL_BY_IMPLEMENTATION,
    RULE_RESULT_PRIORITY as RULE_RESULT_PRIORITY,
    _analysis_result_artifacts,
    _analysis_result_database_name,
    _analysis_result_database_path,
    _analysis_result_inputs as _analysis_result_inputs,
    _build_analysis_result_history_item_id,
    _classify_rule_result,
    _dedupe_key,
    _get_static_analysis_verdicts,
    _has_structured_violation_payload as _has_structured_violation_payload,
    _llm_payload_history_time,
    _merge_rule_status,
    _normalize_implementation_from_analysis_result,
    _normalize_implementation_from_db,
    _normalize_protocol_name,
    _parse_llm_response,
    _parse_violation_details,
    _protocol_for_implementation as _protocol_for_implementation,
    _strip_archive_suffix as _strip_archive_suffix,
    _verdict_code_lines as _verdict_code_lines,
    _verdict_result_status,
    _verdict_rule_desc,
    _verdict_violation_details,
    _violation_location_key,
)
from .static_analysis_sources import (
    iter_static_analysis_database_sources,
)
from .violation_history_state import (
    _load_violation_history_timestamps,
    _save_violation_history_timestamps,
    _sqlite_path_hash,
    _violation_history_timestamp_store_path as _violation_history_timestamp_store_path,
    _violation_history_writable_database_path,
    _violation_history_writable_database_root,
)

LOGGER = logging.getLogger(__name__)

bp = Blueprint("protocol_compliance", __name__, url_prefix="/api/protocol-compliance")

VISIBLE_VIOLATION_HISTORY_LIMIT = 5


# Authentication -------------------------------------------------------------

def _ensure_authenticated():
    user = verify_access_token(request.headers.get("Authorization"))
    if not user:
        return None, unauthorized()
    return user, None


_aflnet_route_handlers = register_aflnet_routes(bp, _ensure_authenticated)
download_aflnet_result = _aflnet_route_handlers["download_aflnet_result"]
snapshot_aflnet_result = _aflnet_route_handlers["snapshot_aflnet_result"]
download_aflnet_result_artifact = _aflnet_route_handlers["download_aflnet_result_artifact"]


# Helpers -------------------------------------------------------------------


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
    llm_base_url = (request.form.get("llmBaseUrl") or "").strip()
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
            llm_base_url=llm_base_url,
        )
    except ValueError as exc:
        payload = make_error_payload("参数错误", details=str(exc))
        return make_response(payload, 400)
    except FileNotFoundError as exc:
        LOGGER.exception("Protocol extraction pipeline is not ready")
        payload = make_error_payload("流程未准备就绪", details=str(exc))
        return make_response(payload, 500)
    except PipelineResultNotFoundError as exc:
        LOGGER.exception("Protocol extraction pipeline result file was not found")
        detail = {"message": str(exc)}
        payload = make_error_payload("未找到分析结果文件", details=detail)
        return make_response(payload, 500)
    except PipelineExecutionError as exc:
        LOGGER.exception(
            "Protocol extraction pipeline execution failed. log_path=%s",
            exc.log_path,
        )
        detail = {
            "logPath": exc.log_path,
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
            error_response("请上传源码、协议规则和配置文件"), 400
        )

    uploads_map = {
        "codeArchive": request.files.get("codeArchive"),
        "rules": request.files.get("rules"),
        "config": request.files.get("config"),
    }

    required_missing = [
        key for key, value in uploads_map.items()
        if not isinstance(value, FileStorage)
    ]
    if required_missing:
        labels = {
            "codeArchive": "源码压缩包",
            "rules": "协议规则 JSON",
            "config": "分析配置 TOML",
        }
        readable = "、".join(labels.get(item, item) for item in required_missing)
        return make_response(
            error_response(f"请上传完整文件：{readable}"), 400
        )

    code_upload = cast(FileStorage, uploads_map["codeArchive"])
    rules_upload = cast(FileStorage, uploads_map["rules"])
    config_upload = cast(FileStorage, uploads_map["config"])

    code_name, code_data = _read_upload(code_upload)
    rules_name, rules_data = _read_upload(rules_upload)
    config_name, config_data = _read_upload(config_upload)

    if code_data is None or config_data is None or rules_data is None:
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
        LOGGER.exception("Failed to delete static analysis job %s", job_id)
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
        if reason_key:
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
    LOGGER.debug(
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
        LOGGER.debug(
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
    *,
    include_builtin: bool = True,
) -> tuple[List[Dict[str, Any]], List[str]]:
    db_dir = Path(os.path.dirname(__file__)) / "databases"
    return iter_static_analysis_database_sources(
        db_dir=db_dir,
        find_sqlite_file=lambda database_path, workspace_path: _find_sqlite_file(
            database_path,
            workspace_path,
            collect_warnings=False,
        ),
        include_builtin=include_builtin,
        iter_writable_database_copies=_iter_violation_history_writable_database_copies,
        job_limit=job_limit,
        list_static_analysis_history=list_static_analysis_history,
        sqlite_path_hash=_sqlite_path_hash,
    )


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


def _history_database_name_marker(value: Any) -> str:
    name = Path(str(value or "")).name
    if re.fullmatch(r"[0-9a-f]{12}-.+", name):
        name = name.split("-", 1)[1]
    return _dedupe_key(name)


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
    database_backed_names: set[str] = set()
    database_backed_paths: set[str] = set()
    include_builtin_param = request.args.get("includeBuiltin")
    include_builtin = (
        _dedupe_key(include_builtin_param) in {"1", "true", "yes", "on"}
        if include_builtin_param is not None
        else False
    )
    try:
        sources, warnings = _iter_static_analysis_database_sources(
            job_limit,
            include_builtin=include_builtin,
        )
    except TypeError:
        sources, warnings = _iter_static_analysis_database_sources(job_limit)
        if not include_builtin:
            sources = [
                source
                for source in sources
                if source.get("sourceType") != "builtin"
            ]
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
            database_backed_names.add(_history_database_name_marker(db_path.name))
            if source.get("jobId"):
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
                and _history_database_name_marker(item.get("databaseName"))
                not in database_backed_names
            )

    if not items and not include_builtin and include_builtin_param is None:
        try:
            fallback_sources, fallback_warnings = _iter_static_analysis_database_sources(
                job_limit,
                include_builtin=True,
            )
        except TypeError:
            fallback_sources, fallback_warnings = _iter_static_analysis_database_sources(job_limit)
        warnings.extend(fallback_warnings)
        for source in fallback_sources:
            if source.get("sourceType") != "builtin":
                continue
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
        LOGGER.exception("Failed to prepare writable violation-history database")
        return make_response(error_response(f"准备可写数据库失败：{exc}"), 500)

    try:
        conn = sqlite3.connect(resolved_path)
    except sqlite3.Error as exc:
        LOGGER.exception("Failed to open static analysis result database %s", resolved_path)
        return make_response(error_response(f"无法打开静态分析结果数据库：{exc}"), 500)

    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            "SELECT rowid AS __rowid, rule_desc, code_snippet, call_graph, llm_response "
            "FROM rule_code_snippet"
        ).fetchall()
    except sqlite3.Error as exc:
        conn.close()
        LOGGER.exception("Failed to read static analysis rule results from %s", resolved_path)
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
        LOGGER.exception("Failed to write violation history to %s", resolved_path)
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
            "exceptionArgs": [str(item) for item in exc.args],
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
    LOGGER.info("[下载数据库] 请求下载任务 %s 的数据库文件", job_id)
    _, error = _ensure_authenticated()
    if error:
        LOGGER.warning("[下载数据库] 任务 %s 认证失败", job_id)
        return error

    snapshot = get_static_analysis_job(job_id)
    if not snapshot:
        LOGGER.error("[下载数据库] 任务 %s 未找到", job_id)
        return make_response(error_response("未找到静态分析任务"), 404)

    LOGGER.info("[下载数据库] 任务 %s 找到，状态: %s", job_id, snapshot.get("status"))

    # 优先使用存储的database_path
    database_path = snapshot.get("database_path")
    LOGGER.info("[下载数据库] 任务 %s 的 database_path: %s", job_id, database_path)

    if isinstance(database_path, str) and database_path:
        db_file = Path(database_path)
        if db_file.exists():
            LOGGER.info("[下载数据库] 使用存储的路径: %s", db_file)
            return send_file(
                db_file,
                as_attachment=True,
                download_name=f"analysis-{job_id}.db",
                mimetype="application/octet-stream",
            )

    # 如果database_path为空或文件不存在，尝试从output_path动态查找
    LOGGER.warning("[下载数据库] database_path 无效，尝试从 output_path 查找")
    output_path = snapshot.get("output_path")
    if isinstance(output_path, str) and output_path:
        output_dir = Path(output_path)
        database_dir = output_dir / "database"
        LOGGER.info("[下载数据库] 在 %s 目录查找数据库文件", database_dir)

        if database_dir.exists():
            candidates = list(database_dir.glob("*.db"))
            LOGGER.info("[下载数据库] 找到 %d 个 .db 文件: %s", len(candidates), candidates)
            if candidates:
                db_file = candidates[0]
                LOGGER.info("[下载数据库] 使用 output_path 找到的文件: %s", db_file)
                return send_file(
                    db_file,
                    as_attachment=True,
                    download_name=f"analysis-{job_id}.db",
                    mimetype="application/octet-stream",
                )

    # 最后尝试：直接从环境变量配置的output_root构造路径
    LOGGER.warning("[下载数据库] output_path 也无效，尝试从环境变量构造路径")
    output_root = os.environ.get("PG_OUTPUT_ROOT", "/tmp/protocolguard/outputs")
    constructed_path = Path(output_root) / job_id / "database"
    LOGGER.info("[下载数据库] 尝试构造的路径: %s", constructed_path)

    if constructed_path.exists():
        candidates = list(constructed_path.glob("*.db"))
        LOGGER.info("[下载数据库] 在构造路径找到 %d 个 .db 文件: %s", len(candidates), candidates)
        if candidates:
            db_file = candidates[0]
            LOGGER.info("[下载数据库] 使用构造路径找到的文件: %s", db_file)
            return send_file(
                db_file,
                as_attachment=True,
                download_name=f"analysis-{job_id}.db",
                mimetype="application/octet-stream",
            )

    LOGGER.error("[下载数据库] 所有方法都失败，无法找到数据库文件")
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

    code_name, code_data = _read_upload(code_upload_raw)

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
        database_name, database_data = _read_upload(database_upload_raw)

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


# Protocol Specific Routes -------------------------------------------------

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
    LOGGER.debug("========== execute-command API被调用 ==========")

    _, error = _ensure_authenticated()
    if error:
        LOGGER.debug("认证失败: %s", error)
        return error

    data = request.get_json()
    LOGGER.debug("接收到的请求数据: %s", data)

    if not data:
        LOGGER.debug("请求数据为空")
        return make_response(error_response("请求数据不能为空"), 400)

    protocol = data.get("protocol", "UNKNOWN")
    protocol_implementations = data.get("protocolImplementations", [])

    LOGGER.debug("解析参数 - 协议: %s, 实现: %s", protocol, protocol_implementations)

    # 根据协议获取配置
    if protocol == "MQTT":
        # MQTT协议支持双引擎配置
        if protocol_implementations and "SOL" in protocol_implementations:
            # SOL使用AFLNET引擎 (原RTSP配置)
            command = _aflnet_shell_command()
            LOGGER.debug("MQTT协议使用SOL实现(AFLNET引擎): %s", protocol_implementations)
        else:
            # 传统MQTT broker使用MBFuzzer引擎
            command = MQTT_CONFIG["shell_command"]
            LOGGER.debug("MQTT协议使用传统broker实现(MBFuzzer引擎): %s", protocol_implementations)
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
            LOGGER.debug("SNMP协议实现: %s", protocol_implementations)
    else:
        return make_response(error_response(f"不支持的协议类型: {protocol}"), 400)

    try:
        LOGGER.debug("执行命令: %s", command)

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
                        LOGGER.debug("%s ProtocolGuard启动成功，容器ID: %s", protocol_name, container_id)

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
                            LOGGER.debug("返回成功响应: %s", response_data)
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
                        LOGGER.debug("ProtocolGuard启动失败: %s", error_msg)
                        return make_response(error_response(f"ProtocolGuard启动失败: {error_msg}"), 500)
                else:
                    error_msg = result.stderr.strip() if result.stderr.strip() else "Docker命令执行失败"
                    LOGGER.debug("ProtocolGuard启动失败: %s", error_msg)
                    return make_response(error_response(f"ProtocolGuard启动失败: {error_msg}"), 500)

            except subprocess.TimeoutExpired:
                return make_response(error_response("Docker容器启动超时"), 500)
            except Exception as e:
                LOGGER.debug("ProtocolGuard启动异常: %s", str(e))
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

            LOGGER.debug("命令返回码: %s", result.returncode)

            if result.returncode == 0:
                # 命令执行成功
                LOGGER.debug("命令执行成功")
                LOGGER.debug("stdout: %s", result.stdout)

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
                LOGGER.debug("命令执行失败: %s", error_msg)
                return make_response(error_response(f"命令执行失败: {error_msg}"), 500)

    except subprocess.TimeoutExpired:
        LOGGER.debug("命令执行超时")
        return make_response(error_response("命令执行超时"), 500)
    except Exception as e:
        LOGGER.debug("异常: %s", str(e))
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
            LOGGER.debug("MQTT协议使用SOL实现，读取AFLNET日志(%s): %s", output_source, file_path)
        else:
            # 传统MQTT broker使用MBFuzzer引擎日志路径
            file_path = MQTT_CONFIG["log_file_path"]
            LOGGER.debug("MQTT协议使用传统broker实现，读取MBFuzzer日志: %s", file_path)
    elif protocol == "SNMP":
        file_path = SNMP_CONFIG["log_file_path"]
    else:
        return make_response(error_response(f"不支持的协议类型: {protocol}"), 400)

    try:
        LOGGER.debug("尝试读取%s日志文件: %s", protocol, file_path)
        LOGGER.debug("上次读取位置: %s", last_position)

        # 检查目录是否存在
        log_dir = os.path.dirname(file_path)
        if not os.path.exists(log_dir):
            LOGGER.debug("日志目录不存在: %s", log_dir)
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
            LOGGER.debug("日志目录中的文件: %s", files_in_dir)
        except Exception as e:
            LOGGER.debug("无法列出目录文件: %s", e)

        if not os.path.exists(file_path):
            LOGGER.debug("日志文件不存在: %s", file_path)
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
        LOGGER.debug("日志文件大小: %s 字节", file_size)

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

        LOGGER.debug("读取到新内容长度: %s 字符", len(new_content))
        LOGGER.debug("新的读取位置: %s", current_position)

        if new_content:
            LOGGER.debug("新内容预览: %s...", new_content[:200])

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
        LOGGER.debug("读取日志文件异常: %s", e)
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

        LOGGER.debug("状态检查结果: %s", status_info)

        return success_response(status_info)

    except Exception as e:
        LOGGER.debug("状态检查异常: %s", e)
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
    LOGGER.debug("========== 启动前清理API被调用 ==========")

    _, error = _ensure_authenticated()
    if error:
        LOGGER.debug("认证失败: %s", error)
        return error

    data = request.get_json()
    LOGGER.debug("接收到的请求数据: %s", data)

    if not data:
        LOGGER.debug("请求数据为空")
        return make_response(error_response("请求数据不能为空"), 400)

    protocol = data.get("protocol", "UNKNOWN")

    LOGGER.debug("解析参数 - 协议: %s", protocol)

    cleanup_results = {
        "containers_stopped": 0,
        "containers_removed": 0,
        "output_cleaned": False,
        "errors": []
    }

    try:
        LOGGER.debug("开始启动前清理 - 协议: %s", protocol)

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
                LOGGER.debug("找到 %s 个运行中的protocolguard容器", len(container_ids))

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
                                LOGGER.debug("容器停止成功: %s", container_id)

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
                                    LOGGER.debug("容器删除成功: %s", container_id)
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
                LOGGER.debug("没有找到运行中的protocolguard容器")

        # 2. 清理输出文件夹
        if protocol == "RTSP" or protocol == "MQTT":
            output_dir = str(_aflnet_output_root())
            fallback_output_dir = str(_aflnet_fallback_output_root().resolve())

            # Linux安全检查：防止删除系统重要目录
            dangerous_paths = ['/', '/home', '/usr', '/var', '/etc', '/bin', '/sbin', '/lib', '/opt']
            if str(Path(output_dir).resolve()) == fallback_output_dir:
                cleanup_results["errors"].append(f"拒绝清理备份输出目录: {output_dir}")
                LOGGER.debug("安全检查失败，拒绝清理备份输出目录: %s", output_dir)
            elif output_dir in dangerous_paths or len(output_dir.strip()) < 5:
                cleanup_results["errors"].append(f"拒绝清理危险路径: {output_dir}")
                LOGGER.debug("安全检查失败，拒绝清理: %s", output_dir)
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
                            LOGGER.debug("输出目录清理成功，删除了 %s 个项目", len(cleaned_items))

                        if failed_items:
                            cleanup_results["errors"].extend([f"清理失败: {item}" for item in failed_items])
                    else:
                        LOGGER.debug("输出目录不存在: %s", output_dir)
                        cleanup_results["output_cleaned"] = True  # 目录不存在也算清理成功

                except Exception as e:
                    cleanup_results["errors"].append(f"清理输出目录异常: {str(e)}")
                    LOGGER.debug("清理输出目录异常: %s", e)

        LOGGER.debug("启动前清理完成: %s", cleanup_results)

        return success_response({
            "message": "启动前清理完成",
            "cleanup_results": cleanup_results
        })

    except Exception as e:
        LOGGER.debug("启动前清理异常: %s", e)
        cleanup_results["errors"].append(f"清理过程异常: {str(e)}")

        return success_response({
            "message": "启动前清理部分完成",
            "cleanup_results": cleanup_results
        })


@bp.route("/stop-and-cleanup", methods=["POST"])
def stop_and_cleanup():
    """停止Docker容器并清理输出文件"""
    LOGGER.debug("========== 停止和清理API被调用 ==========")

    _, error = _ensure_authenticated()
    if error:
        LOGGER.debug("认证失败: %s", error)
        return error

    data = request.get_json()
    LOGGER.debug("接收到的请求数据: %s", data)

    if not data:
        LOGGER.debug("请求数据为空")
        return make_response(error_response("请求数据不能为空"), 400)

    container_id = data.get("container_id")
    protocol = data.get("protocol", "UNKNOWN")

    LOGGER.debug("解析参数 - 容器ID: %s, 协议: %s", container_id, protocol)

    if not container_id:
        LOGGER.debug("容器ID为空")
        return make_response(error_response("容器ID不能为空"), 400)

    stop_results = {
        "container_stopped": False,
        "container_removed": False,
        "errors": []
    }

    try:
        LOGGER.debug("开始停止和清理%s容器: %s", protocol, container_id)

        # 首先检查容器是否存在
        check_result = subprocess.run(
            f"docker ps -a -q --filter id={container_id}",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if check_result.returncode == 0 and check_result.stdout.strip():
            LOGGER.debug("找到容器: %s", check_result.stdout.strip())
        else:
            LOGGER.debug("容器不存在或查找失败: %s", check_result.stderr)
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
            LOGGER.debug("容器正在运行，需要停止: %s", running_check.stdout.strip())
        else:
            LOGGER.debug("容器未在运行或已停止")

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
                LOGGER.debug("容器停止成功: %s", container_id)
            else:
                error_msg = stop_result.stderr.strip() or "停止容器失败"
                stop_results["errors"].append(f"停止容器失败: {error_msg}")
                LOGGER.debug("停止容器失败: %s", error_msg)

        except subprocess.TimeoutExpired:
            stop_results["errors"].append("停止容器超时")
            LOGGER.debug("停止容器超时")
        except Exception as e:
            stop_results["errors"].append(f"停止容器异常: {str(e)}")
            LOGGER.debug("停止容器异常: %s", e)

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
                LOGGER.debug("容器删除成功: %s", container_id)
            else:
                error_msg = remove_result.stderr.strip() or "删除容器失败"
                stop_results["errors"].append(f"删除容器失败: {error_msg}")
                LOGGER.debug("删除容器失败: %s", error_msg)

        except subprocess.TimeoutExpired:
            stop_results["errors"].append("删除容器超时")
            LOGGER.debug("删除容器超时")
        except Exception as e:
            stop_results["errors"].append(f"删除容器异常: {str(e)}")
            LOGGER.debug("删除容器异常: %s", e)

        LOGGER.debug("容器停止完成: %s", stop_results)

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
        LOGGER.debug("停止过程异常: %s", e)
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

    try:
        items = read_detection_results(implementation_name)
    except FileNotFoundError:
        return make_response(
            error_response(f"未找到协议实现 '{implementation_name}' 的数据库文件"),
            404
        )
    except sqlite3.Error as e:
        return make_response(
            error_response(f"数据库读取错误: {str(e)}"),
            500
        )

    return success_response({'items': items})


@bp.route("/available-implementations", methods=["GET"])
def list_available_implementations():
    """获取所有可用的协议实现列表"""
    _, error = _ensure_authenticated()
    if error:
        return error

    implementations = list_legacy_available_implementations()
    return success_response({'items': implementations})


@bp.route("/analysis-history", methods=["GET"])
def get_analysis_history():
    """获取历史记录"""
    _, error = _ensure_authenticated()
    if error:
        return error

    try:
        history = read_analysis_history()
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

    try:
        append_analysis_history(implementation_name, protocol_name)
    except IOError as e:
        return make_response(
            error_response(f"保存历史记录失败: {str(e)}"),
            500
        )

    return success_response({'message': '已添加到历史记录'})
