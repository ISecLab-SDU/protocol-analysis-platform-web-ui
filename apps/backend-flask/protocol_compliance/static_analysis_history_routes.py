"""Static-analysis overview and violation-history request handlers."""

from __future__ import annotations

import json
import logging
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, cast

from flask import make_response, request

from utils.responses import error_response, success_response

LOGGER = logging.getLogger(__name__)


def create_static_analysis_history_handlers(
    ensure_authenticated: Callable[[], tuple[object, object]],
    *,
    build_violation_history_item_id: Callable[..., str],
    dedupe_key: Callable[[Any], str],
    delete_analysis_result_violation_history_from_database: Callable[..., tuple[Optional[Dict[str, Any]], List[str]]],
    delete_violation_history_from_database: Callable[..., tuple[Optional[Dict[str, Any]], List[str]]],
    delete_violation_history_from_payload_sources: Callable[..., tuple[Optional[Dict[str, Any]], List[str]]],
    ensure_writable_violation_history_database: Callable[..., Path],
    find_matching_rule_row: Callable[[list[sqlite3.Row], str], Optional[sqlite3.Row]],
    find_sqlite_file: Callable[..., tuple[Optional[Path], list[str]]],
    forget_deleted_violation_history: Callable[[Dict[str, Any]], None],
    history_database_name_marker: Callable[[Any], str],
    history_database_path_marker: Callable[[Any], str],
    history_item_datetime: Callable[[Dict[str, Any]], Optional[datetime]],
    is_violation_history_deleted: Callable[[Dict[str, Any]], bool],
    iter_static_analysis_database_sources: Callable[..., tuple[List[Dict[str, Any]], List[str]]],
    list_static_analysis_history: Callable[..., List[Dict[str, Any]]],
    merge_rule_status: Callable[[Dict[str, str], str, str], None],
    parse_llm_response: Callable[[Any], Dict[str, Any]],
    read_overview_from_analysis_result: Callable[[Dict[str, Any]], tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]],
    read_overview_from_database: Callable[..., tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], Dict[str, int], List[str]]],
    read_violation_history_from_analysis_result: Callable[[Dict[str, Any]], List[Dict[str, Any]]],
    read_violation_history_from_database: Callable[..., tuple[List[Dict[str, Any]], List[str]]],
    remember_deleted_violation_history: Callable[[Dict[str, Any]], None],
    remember_row_history_display_time: Callable[..., None],
    to_int: Callable[[object, int], int],
    visible_violation_history_limit: int,
) -> dict[str, Callable[..., Any]]:
    def static_analysis_database_overview():
        _, error = ensure_authenticated()
        if error:
            return error

        job_limit = to_int(request.args.get("jobLimit"), 200)
        history_entries = list_static_analysis_history(
            limit=job_limit,
            include_result=True,
        )
        result_backed_job_ids: set[str] = set()
        sources, warnings = iter_static_analysis_database_sources(job_limit)
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
                    merge_rule_status(
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
            item, findings = read_overview_from_analysis_result(entry)
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
            item, findings, table_counts, db_warnings = read_overview_from_database(
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
                dedupe_key(finding.get("implementation")),
                dedupe_key(finding.get("rule")),
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

    def static_analysis_violation_history():
        _, error = ensure_authenticated()
        if error:
            return error

        job_limit = to_int(request.args.get("jobLimit"), 200)
        protocol_filter = dedupe_key(request.args.get("protocol"))
        implementation_filter = dedupe_key(request.args.get("implementation"))
        result_filter = dedupe_key(request.args.get("result"))
        time_range = dedupe_key(request.args.get("timeRange"))
        history_entries = list_static_analysis_history(
            limit=job_limit,
            include_result=True,
        )
        database_backed_job_ids: set[str] = set()
        database_backed_names: set[str] = set()
        database_backed_paths: set[str] = set()
        include_builtin_param = request.args.get("includeBuiltin")
        include_builtin = (
            dedupe_key(include_builtin_param) in {"1", "true", "yes", "on"}
            if include_builtin_param is not None
            else False
        )
        try:
            sources, warnings = iter_static_analysis_database_sources(
                job_limit,
                include_builtin=include_builtin,
            )
        except TypeError:
            sources, warnings = iter_static_analysis_database_sources(job_limit)
            if not include_builtin:
                sources = [
                    source
                    for source in sources
                    if source.get("sourceType") != "builtin"
                ]
        items: List[Dict[str, Any]] = []

        for source in sources:
            db_path = cast(Path, source["path"])
            db_items, db_warnings = read_violation_history_from_database(
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
                database_backed_paths.add(history_database_path_marker(db_path))
                database_backed_names.add(history_database_name_marker(db_path.name))
                if source.get("jobId"):
                    database_backed_job_ids.add(str(source["jobId"]))

        for entry in history_entries:
            if entry.get("status") != "completed":
                continue
            job_id = entry.get("jobId")
            if job_id and str(job_id) in database_backed_job_ids:
                continue
            result_items = read_violation_history_from_analysis_result(entry)
            if result_items:
                items.extend(
                    item
                    for item in result_items
                    if history_database_path_marker(item.get("databasePath"))
                    not in database_backed_paths
                    and history_database_name_marker(item.get("databaseName"))
                    not in database_backed_names
                )

        if not items and not include_builtin and include_builtin_param is None:
            try:
                fallback_sources, fallback_warnings = iter_static_analysis_database_sources(
                    job_limit,
                    include_builtin=True,
                )
            except TypeError:
                fallback_sources, fallback_warnings = iter_static_analysis_database_sources(job_limit)
            warnings.extend(fallback_warnings)
            for source in fallback_sources:
                if source.get("sourceType") != "builtin":
                    continue
                db_path = cast(Path, source["path"])
                db_items, db_warnings = read_violation_history_from_database(
                    db_path,
                    source_type=cast(str, source["sourceType"]),
                    job_id=cast(Optional[str], source.get("jobId")),
                    protocol_name=cast(Optional[str], source.get("protocolName")),
                    created_at=cast(Optional[str], source.get("createdAt")),
                    updated_at=cast(Optional[str], source.get("updatedAt")),
                )
                items.extend(db_items)
                warnings.extend(db_warnings)

        items = [item for item in items if not is_violation_history_deleted(item)]

        if protocol_filter:
            items = [
                item
                for item in items
                if dedupe_key(item.get("protocolName")) == protocol_filter
            ]

        if implementation_filter:
            items = [
                item
                for item in items
                if dedupe_key(item.get("implementationName")) == implementation_filter
            ]

        if result_filter:
            items = [
                item for item in items if dedupe_key(item.get("result")) == result_filter
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
                if (item_time := history_item_datetime(item)) is not None
                and item_time >= cutoff
            ]

        items.sort(key=lambda item: str(item.get("updatedAt") or ""), reverse=True)
        visible_items = items[:visible_violation_history_limit]
        payload: Dict[str, Any] = {
            "items": visible_items,
            "count": len(visible_items),
            "generatedAt": datetime.now(timezone.utc).isoformat(),
        }
        if warnings:
            payload["warnings"] = warnings
        return success_response(payload)

    def delete_static_analysis_violation_history(item_id: str):
        _, error = ensure_authenticated()
        if error:
            return error

        if not isinstance(item_id, str) or not item_id.strip():
            return make_response(error_response("无效的历史记录 ID"), 400)

        job_limit = to_int(request.args.get("jobLimit"), 200)
        delete_payload = request.get_json(silent=True)
        delete_payload = delete_payload if isinstance(delete_payload, dict) else {}
        tombstone_item: Dict[str, Any] = {**delete_payload, "id": item_id}
        if delete_payload and is_violation_history_deleted(tombstone_item):
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
        sources, warnings = iter_static_analysis_database_sources(job_limit)

        try:
            for source in sources:
                db_path = cast(Path, source["path"])
                deleted, db_warnings = delete_violation_history_from_database(
                    db_path,
                    item_id=item_id,
                    job_id=cast(Optional[str], source.get("jobId")),
                    source_type=cast(str, source["sourceType"]),
                )
                warnings.extend(db_warnings)
                if deleted:
                    remember_deleted_violation_history(
                        {**delete_payload, **deleted, "id": item_id}
                    )
                    payload: Dict[str, Any] = {**deleted, "deleted": True}
                    if warnings:
                        payload["warnings"] = warnings
                    return make_response(success_response(payload), 200)

            if delete_payload:
                deleted, payload_warnings = delete_violation_history_from_payload_sources(
                    item_id,
                    payload=delete_payload,
                    sources=sources,
                )
                warnings.extend(payload_warnings)
                if deleted:
                    remember_deleted_violation_history(
                        {**delete_payload, **deleted, "id": item_id}
                    )
                    response_payload = {**deleted, "deleted": True}
                    if warnings:
                        response_payload["warnings"] = warnings
                    return make_response(success_response(response_payload), 200)

            deleted, result_warnings = (
                delete_analysis_result_violation_history_from_database(
                    item_id,
                    job_limit=job_limit,
                )
            )
            warnings.extend(result_warnings)
            if deleted:
                remember_deleted_violation_history(
                    {**delete_payload, **deleted, "id": item_id}
                )
                payload = {**deleted, "deleted": True}
                if warnings:
                    payload["warnings"] = warnings
                return make_response(success_response(payload), 200)

            if delete_payload and delete_payload.get("ruleDesc"):
                remember_deleted_violation_history(tombstone_item)
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

    def upsert_static_analysis_violation_history():
        _, error = ensure_authenticated()
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

        resolved_path, warnings = find_sqlite_file(database_path_raw, workspace_path_raw)
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
            resolved_path = ensure_writable_violation_history_database(
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

        matched = find_matching_rule_row(rows, rule_desc)
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

        llm_payload = parse_llm_response(matched["llm_response"])
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

        remember_row_history_display_time(
            resolved_path,
            call_graph=next_call_graph,
            code_snippet=next_code_snippet,
            rule_desc=matched["rule_desc"],
            timestamp=updated_at,
        )
        forget_deleted_violation_history(
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

        item_id = build_violation_history_item_id(
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

    return {
        "delete_static_analysis_violation_history": delete_static_analysis_violation_history,
        "static_analysis_database_overview": static_analysis_database_overview,
        "static_analysis_violation_history": static_analysis_violation_history,
        "upsert_static_analysis_violation_history": upsert_static_analysis_violation_history,
    }
