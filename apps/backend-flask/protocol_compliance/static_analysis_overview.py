"""Static-analysis overview readers."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from .static_analysis_models import (
    _analysis_result_database_name,
    _classify_rule_result,
    _dedupe_key,
    _get_static_analysis_verdicts,
    _merge_rule_status,
    _normalize_implementation_from_analysis_result,
    _normalize_implementation_from_db,
    _normalize_protocol_name,
    _parse_llm_response,
    _parse_violation_details,
    _verdict_result_status,
    _verdict_rule_desc,
    _verdict_violation_details,
    _violation_location_key,
)


def _truncate_text(value: Any, limit: int) -> Optional[str]:
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if len(text) <= limit:
        return text
    return f"{text[:limit - 1]}…"


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
