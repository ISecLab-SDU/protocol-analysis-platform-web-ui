"""Database-backed violation-history read and delete helpers."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, cast

from .static_analysis_models import (
    _classify_rule_result,
    _dedupe_key,
    _llm_payload_history_time,
    _normalize_implementation_from_db,
    _normalize_protocol_name,
    _parse_llm_response,
    _parse_violation_details,
)


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


def _read_violation_history_from_database(
    db_path: Path,
    *,
    database_history_display_time: Callable[[Path], str],
    row_history_display_time: Callable[..., str],
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
        or database_history_display_time(db_path)
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
            or row_history_display_time(
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
    find_sqlite_file: Callable[..., tuple[Optional[Path], list[str]]],
    list_static_analysis_history: Callable[..., List[Dict[str, Any]]],
    read_violation_history_from_analysis_result: Callable[[Dict[str, Any]], List[Dict[str, Any]]],
    job_limit: int,
) -> tuple[Optional[Dict[str, Any]], List[str]]:
    warnings: List[str] = []

    for entry in list_static_analysis_history(limit=job_limit, include_result=True):
        if entry.get("status") != "completed":
            continue
        for item in read_violation_history_from_analysis_result(entry):
            if item.get("id") != item_id:
                continue

            resolved_path, resolve_warnings = find_sqlite_file(
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
    *,
    find_sqlite_file: Callable[..., tuple[Optional[Path], list[str]]],
    history_database_path_marker: Callable[[Any], str],
) -> tuple[List[Path], List[str]]:
    warnings: List[str] = []
    candidates: List[Path] = []
    seen: set[str] = set()

    def add_candidate(path: Optional[Path]) -> None:
        if not path:
            return
        marker = history_database_path_marker(path)
        if marker in seen:
            return
        seen.add(marker)
        candidates.append(path)

    resolved_path, resolve_warnings = find_sqlite_file(
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
    find_sqlite_file: Callable[..., tuple[Optional[Path], list[str]]],
    history_database_path_marker: Callable[[Any], str],
    payload: Dict[str, Any],
    sources: List[Dict[str, Any]],
) -> tuple[Optional[Dict[str, Any]], List[str]]:
    candidates, warnings = _payload_candidate_database_sources(
        payload,
        sources,
        find_sqlite_file=find_sqlite_file,
        history_database_path_marker=history_database_path_marker,
    )
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
