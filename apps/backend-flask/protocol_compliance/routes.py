"""Flask blueprints for the protocol compliance domain."""

from __future__ import annotations

import json
import logging
import os
import re
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
    list_static_analysis_history,
    normalize_protocol_name,
    submit_static_analysis_job,
    try_extract_rules_summary,
)
from .assertion import (
    get_assertion_history_diff_path,
    get_assertion_history_entry,
    list_assertion_history,
)
from .assertion_routes import register_assertion_routes
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
    read_analysis_history as read_analysis_history,
)
from .legacy_analysis_routes import register_legacy_analysis_routes
from .legacy_fuzz_routes import (
    MQTT_CONFIG as MQTT_CONFIG,
    SNMP_CONFIG as SNMP_CONFIG,
    register_legacy_fuzz_routes,
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
from .static_analysis_databases import (
    _copy_sqlite_database_for_violation_history as _copy_sqlite_database_for_violation_history,
    _ensure_writable_violation_history_database,
    _expand_path,
    _find_sqlite_file,
    _is_sqlite_database_writable as _is_sqlite_database_writable,
    _iter_violation_history_writable_database_copies,
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
    _dedupe_key,
    _get_static_analysis_verdicts,
    _has_structured_violation_payload as _has_structured_violation_payload,
    _merge_rule_status,
    _normalize_implementation_from_analysis_result,
    _normalize_protocol_name,
    _parse_llm_response,
    _protocol_for_implementation as _protocol_for_implementation,
    _strip_archive_suffix as _strip_archive_suffix,
    _verdict_code_lines as _verdict_code_lines,
    _verdict_result_status,
    _verdict_rule_desc,
    _verdict_violation_details,
)
from .static_analysis_insights import StaticAnalysisDatabaseInsightsHandler
from .static_analysis_job_routes import register_static_analysis_job_routes
from .static_analysis_overview import (
    _read_overview_from_analysis_result,
    _read_overview_from_database,
    _truncate_text as _truncate_text,
)
from .static_analysis_sources import (
    iter_static_analysis_database_sources,
)
from .violation_history_markers import (
    _candidate_database_history_times as _candidate_database_history_times_impl,
    _database_history_display_time as _database_history_display_time_impl,
    _database_history_time_marker as _database_history_time_marker,
    _deleted_violation_history_markers as _deleted_violation_history_markers,
    _forget_deleted_violation_history as _forget_deleted_violation_history_impl,
    _history_database_name_marker as _history_database_name_marker_impl,
    _history_database_path_marker as _history_database_path_marker_impl,
    _history_delete_marker_payload as _history_delete_marker_payload,
    _history_item_delete_markers as _history_item_delete_markers_impl,
    _is_violation_history_deleted as _is_violation_history_deleted_impl,
    _remember_deleted_violation_history as _remember_deleted_violation_history_impl,
    _remember_row_history_display_time as _remember_row_history_display_time_impl,
    _row_history_display_time as _row_history_display_time_impl,
    _row_history_time_marker as _row_history_time_marker_impl,
)
from .violation_history_records import (
    _build_violation_history_item_id as _build_violation_history_item_id,
    _delete_analysis_result_violation_history_from_database as _delete_analysis_result_violation_history_from_database_impl,
    _delete_violation_history_by_payload as _delete_violation_history_by_payload,
    _delete_violation_history_by_rule_desc as _delete_violation_history_by_rule_desc_impl,
    _delete_violation_history_from_database as _delete_violation_history_from_database_impl,
    _delete_violation_history_from_payload_sources as _delete_violation_history_from_payload_sources_impl,
    _find_matching_rule_row as _find_matching_rule_row,
    _normalized_history_match_text as _normalized_history_match_text,
    _payload_candidate_database_sources as _payload_candidate_database_sources_impl,
    _read_violation_history_from_database as _read_violation_history_from_database_impl,
    _score_violation_history_payload_row as _score_violation_history_payload_row,
    _violation_match_keys as _violation_match_keys,
)
from .violation_history_state import (
    _sqlite_path_hash,
    _violation_history_timestamp_store_path as _violation_history_timestamp_store_path,
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

_static_analysis_job_route_handlers = register_static_analysis_job_routes(
    bp,
    _ensure_authenticated,
)
static_analysis_progress = _static_analysis_job_route_handlers["static_analysis_progress"]
static_analysis_result = _static_analysis_job_route_handlers["static_analysis_result"]
download_static_analysis_database = _static_analysis_job_route_handlers[
    "download_static_analysis_database"
]

_legacy_analysis_route_handlers = register_legacy_analysis_routes(
    bp,
    _ensure_authenticated,
)
get_detection_results = _legacy_analysis_route_handlers["get_detection_results"]
list_available_implementations = _legacy_analysis_route_handlers["list_available_implementations"]
get_analysis_history = _legacy_analysis_route_handlers["get_analysis_history"]
add_analysis_history = _legacy_analysis_route_handlers["add_analysis_history"]

_legacy_fuzz_route_handlers = register_legacy_fuzz_routes(
    bp,
    _ensure_authenticated,
    logger=LOGGER,
    subprocess_module=subprocess,
    to_int=_to_int,
    aflnet_shell_command=_aflnet_shell_command,
    aflnet_result_path_info=_aflnet_result_path_info,
    aflnet_log_file_for_source=_aflnet_log_file_for_source,
    aflnet_output_root=_aflnet_output_root,
    aflnet_fallback_output_root=_aflnet_fallback_output_root,
    resolve_aflnet_output_source=_resolve_aflnet_output_source,
)
write_script = _legacy_fuzz_route_handlers["write_script"]
execute_command = _legacy_fuzz_route_handlers["execute_command"]
read_log = _legacy_fuzz_route_handlers["read_log"]
check_status = _legacy_fuzz_route_handlers["check_status"]
stop_process = _legacy_fuzz_route_handlers["stop_process"]
pre_start_cleanup = _legacy_fuzz_route_handlers["pre_start_cleanup"]
stop_and_cleanup = _legacy_fuzz_route_handlers["stop_and_cleanup"]

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


def _row_history_time_marker(
    db_path: Path,
    *,
    call_graph: Any,
    code_snippet: Any,
    rule_desc: Any,
) -> str:
    return _row_history_time_marker_impl(
        db_path,
        call_graph=call_graph,
        code_snippet=code_snippet,
        dedupe_key=_dedupe_key,
        rule_desc=rule_desc,
    )


def _candidate_database_history_times(db_path: Path) -> List[str]:
    return _candidate_database_history_times_impl(
        db_path,
        package_dir=Path(__file__).resolve().parent,
    )


def _database_history_display_time(
    db_path: Path,
    *,
    persist_if_missing: bool = True,
) -> str:
    return _database_history_display_time_impl(
        db_path,
        package_dir=Path(__file__).resolve().parent,
        persist_if_missing=persist_if_missing,
    )


def _row_history_display_time(
    db_path: Path,
    *,
    call_graph: Any,
    code_snippet: Any,
    fallback: str,
    persist_if_missing: bool = True,
    rule_desc: Any,
) -> str:
    return _row_history_display_time_impl(
        db_path,
        call_graph=call_graph,
        code_snippet=code_snippet,
        dedupe_key=_dedupe_key,
        fallback=fallback,
        persist_if_missing=persist_if_missing,
        rule_desc=rule_desc,
    )


def _remember_row_history_display_time(
    db_path: Path,
    *,
    call_graph: Any,
    code_snippet: Any,
    rule_desc: Any,
    timestamp: str,
) -> None:
    _remember_row_history_display_time_impl(
        db_path,
        call_graph=call_graph,
        code_snippet=code_snippet,
        dedupe_key=_dedupe_key,
        rule_desc=rule_desc,
        timestamp=timestamp,
    )


def _history_item_delete_markers(item: Dict[str, Any]) -> set[str]:
    return _history_item_delete_markers_impl(
        item,
        dedupe_key=_dedupe_key,
        violation_match_keys=_violation_match_keys,
    )


def _is_violation_history_deleted(item: Dict[str, Any]) -> bool:
    return _is_violation_history_deleted_impl(
        item,
        dedupe_key=_dedupe_key,
        violation_match_keys=_violation_match_keys,
    )


def _remember_deleted_violation_history(item: Dict[str, Any]) -> None:
    _remember_deleted_violation_history_impl(
        item,
        dedupe_key=_dedupe_key,
        violation_match_keys=_violation_match_keys,
    )


def _forget_deleted_violation_history(item: Dict[str, Any]) -> None:
    _forget_deleted_violation_history_impl(
        item,
        dedupe_key=_dedupe_key,
        violation_match_keys=_violation_match_keys,
    )


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


_assertion_route_handlers = register_assertion_routes(
    bp,
    _ensure_authenticated,
    _expand_path,
    _read_upload,
    _resolve_assertion_database_path,
)
assertion_generation = _assertion_route_handlers["assertion_generation"]
assertion_generation_progress = _assertion_route_handlers["assertion_generation_progress"]
assertion_generation_result = _assertion_route_handlers["assertion_generation_result"]
assertion_generation_download = _assertion_route_handlers["assertion_generation_download"]
assertion_generation_instrumentation_diff = _assertion_route_handlers[
    "assertion_generation_instrumentation_diff"
]
start_diff_parsing = _assertion_route_handlers["start_diff_parsing"]
diff_parsing_progress = _assertion_route_handlers["diff_parsing_progress"]
diff_parsing_result = _assertion_route_handlers["diff_parsing_result"]


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
    return _read_violation_history_from_database_impl(
        db_path,
        database_history_display_time=_database_history_display_time,
        row_history_display_time=_row_history_display_time,
        source_type=source_type,
        job_id=job_id,
        protocol_name=protocol_name,
        created_at=created_at,
        updated_at=updated_at,
    )


def _delete_violation_history_from_database(
    db_path: Path,
    *,
    item_id: str,
    job_id: Optional[str] = None,
    source_type: str,
) -> tuple[Optional[Dict[str, Any]], List[str]]:
    return _delete_violation_history_from_database_impl(
        db_path,
        item_id=item_id,
        job_id=job_id,
        source_type=source_type,
    )


def _delete_violation_history_by_rule_desc(
    db_path: Path,
    *,
    item_id: str,
    rule_desc: str,
) -> tuple[Optional[Dict[str, Any]], List[str]]:
    return _delete_violation_history_by_rule_desc_impl(
        db_path,
        item_id=item_id,
        rule_desc=rule_desc,
    )


def _delete_analysis_result_violation_history_from_database(
    item_id: str,
    *,
    job_limit: int,
) -> tuple[Optional[Dict[str, Any]], List[str]]:
    return _delete_analysis_result_violation_history_from_database_impl(
        item_id,
        find_sqlite_file=_find_sqlite_file,
        list_static_analysis_history=list_static_analysis_history,
        read_violation_history_from_analysis_result=_read_violation_history_from_analysis_result,
        job_limit=job_limit,
    )


def _payload_candidate_database_sources(
    payload: Dict[str, Any],
    sources: List[Dict[str, Any]],
) -> tuple[List[Path], List[str]]:
    return _payload_candidate_database_sources_impl(
        payload,
        sources,
        find_sqlite_file=_find_sqlite_file,
        history_database_path_marker=_history_database_path_marker,
    )


def _delete_violation_history_from_payload_sources(
    item_id: str,
    *,
    payload: Dict[str, Any],
    sources: List[Dict[str, Any]],
) -> tuple[Optional[Dict[str, Any]], List[str]]:
    return _delete_violation_history_from_payload_sources_impl(
        item_id,
        find_sqlite_file=_find_sqlite_file,
        history_database_path_marker=_history_database_path_marker,
        payload=payload,
        sources=sources,
    )


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
    return _history_database_path_marker_impl(value)


def _history_database_name_marker(value: Any) -> str:
    return _history_database_name_marker_impl(value, dedupe_key=_dedupe_key)


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


def _static_analysis_database_insights_handler() -> StaticAnalysisDatabaseInsightsHandler:
    return StaticAnalysisDatabaseInsightsHandler(
        ensure_authenticated=_ensure_authenticated,
        find_sqlite_file=_find_sqlite_file,
        find_static_analysis_history_entry=_find_static_analysis_history_entry,
        log_rule_code_snippet_rows=_log_rule_code_snippet_rows,
        read_database_insights_from_analysis_result=_read_database_insights_from_analysis_result,
    )


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
    return _static_analysis_database_insights_handler()()
