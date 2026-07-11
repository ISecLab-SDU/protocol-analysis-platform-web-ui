"""Static-analysis database insight service."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from flask import make_response, request

from utils.responses import error_response, success_response

from .static_analysis_models import (
    _classify_rule_result,
    _parse_llm_response,
    _parse_violation_details,
)

LOGGER = logging.getLogger(__name__)


class StaticAnalysisDatabaseInsightsHandler:
    def __init__(
        self,
        *,
        ensure_authenticated: Callable[[], tuple[object, object]],
        find_sqlite_file: Callable[[Optional[str], Optional[str]], tuple[Optional[Path], List[str]]],
        find_static_analysis_history_entry: Callable[[Any], Optional[Dict[str, Any]]],
        log_rule_code_snippet_rows: Callable[..., None],
        read_database_insights_from_analysis_result: Callable[[Dict[str, Any]], Optional[Dict[str, Any]]],
    ) -> None:
        self._ensure_authenticated = ensure_authenticated
        self._find_sqlite_file = find_sqlite_file
        self._find_static_analysis_history_entry = find_static_analysis_history_entry
        self._log_rule_code_snippet_rows = log_rule_code_snippet_rows
        self._read_database_insights_from_analysis_result = read_database_insights_from_analysis_result

    def __call__(self):
        _, error = self._ensure_authenticated()
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
        database_path_raw = payload.get("databasePath")
        database_path_raw = database_path_raw if isinstance(database_path_raw, str) else None
        workspace_path_raw = payload.get("workspacePath")
        workspace_path_raw = workspace_path_raw if isinstance(workspace_path_raw, str) else None

        LOGGER.info(
            "Static analysis database insights requested",
            extra={
                "jobId": job_id,
                "databasePath": database_path_raw,
                "workspacePath": workspace_path_raw,
            },
        )

        resolved_path, warnings = self._find_sqlite_file(database_path_raw, workspace_path_raw)
        if not resolved_path:
            history_entry = self._find_static_analysis_history_entry(job_id)
            if history_entry:
                result_payload = self._read_database_insights_from_analysis_result(history_entry)
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
                "Unable to resolve SQLite database for static analysis insights: "
                "databasePath=%r, workspacePath=%r",
                database_path_raw,
                workspace_path_raw,
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

        self._log_rule_code_snippet_rows(
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

            findings.append(
                {
                    "ruleDesc": rule_desc,
                    "codeSnippet": code_snippet,
                    "callGraph": call_graph,
                    "llmRaw": raw_llm_response,
                    "reason": reason,
                    "result": result_status,
                    "resultLabel": result_label,
                    "violations": _parse_violation_details(llm_payload),
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
