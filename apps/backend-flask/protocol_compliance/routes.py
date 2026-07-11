"""Flask blueprints for the protocol compliance domain."""

from __future__ import annotations

import json
import logging
import os
import sqlite3
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, cast

from flask import Blueprint, request

from utils.auth import verify_access_token
from utils.responses import (
    unauthorized,
)
from .analysis import (
    get_static_analysis_job,
    list_static_analysis_history,
)
from .assertion_database import (
    _candidate_sqlite_roots_for_job as _candidate_sqlite_roots_for_job_impl,
    _resolve_assertion_database_path as _resolve_assertion_database_path_impl,
)
from .assertion_history_routes import register_assertion_history_routes
from .assertion_routes import register_assertion_routes
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
from .static_analysis_insight_routes import register_static_analysis_insight_routes
from .static_analysis_history_routes import register_static_analysis_history_routes
from .static_analysis_job_routes import register_static_analysis_job_routes
from .static_analysis_overview import (
    _read_overview_from_analysis_result,
    _read_overview_from_database,
    _truncate_text as _truncate_text,
)
from .static_analysis_sources import (
    iter_static_analysis_database_sources,
)
from .static_analysis_submission_routes import register_static_analysis_submission_routes
from .task_routes import register_task_routes
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

_task_route_handlers = register_task_routes(
    bp,
    _ensure_authenticated,
    normalize_status=_normalize_status,
    parse_tags=_parse_tags,
    strip_extension=_strip_extension,
    to_int=_to_int,
)
run_protocol_extract = _task_route_handlers["run_protocol_extract"]
list_tasks = _task_route_handlers["list_tasks"]
create_task = _task_route_handlers["create_task"]
download_result = _task_route_handlers["download_result"]

_assertion_history_route_handlers = register_assertion_history_routes(
    bp,
    _ensure_authenticated,
    to_int=_to_int,
)
assertion_history = _assertion_history_route_handlers["assertion_history"]
assertion_history_entry = _assertion_history_route_handlers["assertion_history_entry"]
download_assertion_diff = _assertion_history_route_handlers["download_assertion_diff"]

_static_analysis_submission_route_handlers = register_static_analysis_submission_routes(
    bp,
    _ensure_authenticated,
    extract_protocol_metadata_from_config=_extract_protocol_metadata_from_config,
    list_static_analysis_history=(
        lambda *args, **kwargs: list_static_analysis_history(*args, **kwargs)
    ),
    read_upload=_read_upload,
    strip_extension=_strip_extension,
    to_int=_to_int,
)
static_analysis = _static_analysis_submission_route_handlers["static_analysis"]
static_analysis_history = _static_analysis_submission_route_handlers[
    "static_analysis_history"
]
delete_static_analysis_history = _static_analysis_submission_route_handlers[
    "delete_static_analysis_history"
]


# Helpers -------------------------------------------------------------------


# Routes --------------------------------------------------------------------


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
    return _candidate_sqlite_roots_for_job_impl(
        job_id,
        expand_path=_expand_path,
        get_static_analysis_job=get_static_analysis_job,
    )


def _resolve_assertion_database_path(database_path: Path) -> tuple[Optional[Path], list[str]]:
    return _resolve_assertion_database_path_impl(
        database_path,
        candidate_sqlite_roots_for_job=_candidate_sqlite_roots_for_job,
    )


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


_static_analysis_history_route_handlers = register_static_analysis_history_routes(
    bp,
    lambda: _ensure_authenticated(),
    build_violation_history_item_id=_build_violation_history_item_id,
    dedupe_key=_dedupe_key,
    delete_analysis_result_violation_history_from_database=(
        lambda *args, **kwargs: _delete_analysis_result_violation_history_from_database(
            *args,
            **kwargs,
        )
    ),
    delete_violation_history_from_database=(
        lambda *args, **kwargs: _delete_violation_history_from_database(
            *args,
            **kwargs,
        )
    ),
    delete_violation_history_from_payload_sources=(
        lambda *args, **kwargs: _delete_violation_history_from_payload_sources(
            *args,
            **kwargs,
        )
    ),
    ensure_writable_violation_history_database=_ensure_writable_violation_history_database,
    find_matching_rule_row=_find_matching_rule_row,
    find_sqlite_file=_find_sqlite_file,
    forget_deleted_violation_history=_forget_deleted_violation_history,
    history_database_name_marker=_history_database_name_marker,
    history_database_path_marker=_history_database_path_marker,
    history_item_datetime=_history_item_datetime,
    is_violation_history_deleted=_is_violation_history_deleted,
    iter_static_analysis_database_sources=(
        lambda *args, **kwargs: _iter_static_analysis_database_sources(
            *args,
            **kwargs,
        )
    ),
    list_static_analysis_history=(
        lambda *args, **kwargs: list_static_analysis_history(*args, **kwargs)
    ),
    merge_rule_status=_merge_rule_status,
    parse_llm_response=_parse_llm_response,
    read_overview_from_analysis_result=_read_overview_from_analysis_result,
    read_overview_from_database=_read_overview_from_database,
    read_violation_history_from_analysis_result=_read_violation_history_from_analysis_result,
    read_violation_history_from_database=_read_violation_history_from_database,
    remember_deleted_violation_history=_remember_deleted_violation_history,
    remember_row_history_display_time=_remember_row_history_display_time,
    to_int=_to_int,
    visible_violation_history_limit=VISIBLE_VIOLATION_HISTORY_LIMIT,
)
static_analysis_database_overview = _static_analysis_history_route_handlers[
    "static_analysis_database_overview"
]
static_analysis_violation_history = _static_analysis_history_route_handlers[
    "static_analysis_violation_history"
]
delete_static_analysis_violation_history = _static_analysis_history_route_handlers[
    "delete_static_analysis_violation_history"
]
upsert_static_analysis_violation_history = _static_analysis_history_route_handlers[
    "upsert_static_analysis_violation_history"
]

_static_analysis_insight_route_handlers = register_static_analysis_insight_routes(
    bp,
    _static_analysis_database_insights_handler,
)
static_analysis_database_insights = _static_analysis_insight_route_handlers[
    "static_analysis_database_insights"
]
