"""Reusable checks for ProtocolGuard static-analysis SQLite outputs."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

NO_VIOLATION_RESULT = "no violation found!"
VIOLATION_RESULT = "violation found!"
ALLOWED_RESULTS = {NO_VIOLATION_RESULT, VIOLATION_RESULT}


def normalize_llm_result(value: Any) -> Optional[str]:
    """Return a canonical static-analysis result value if it is recognized."""
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if normalized in ALLOWED_RESULTS:
        return normalized
    return None


def check_static_analysis_database(db_path: str | Path) -> Dict[str, object]:
    """Inspect rule_code_snippet.llm_response and summarize violation status.

    The function intentionally keeps invalid/missing JSON separate from positive
    violations. A database with no ``violation found!`` values still returns
    ``hasViolation=False`` so the caller can skip downstream verification, while
    ``invalidCount`` and ``invalidRows`` preserve diagnostics for UI/logging.
    """
    path = Path(db_path)
    total_count = 0
    no_violation_count = 0
    violation_count = 0
    invalid_rows: List[Dict[str, object]] = []

    with sqlite3.connect(path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT rowid AS rowId, rule_desc, llm_response
            FROM rule_code_snippet
            ORDER BY rowid
            """
        ).fetchall()

    for row in rows:
        total_count += 1
        raw_response = row["llm_response"]
        try:
            payload = json.loads(raw_response) if raw_response else None
        except json.JSONDecodeError as exc:
            invalid_rows.append(
                {
                    "rowId": row["rowId"],
                    "ruleDesc": row["rule_desc"],
                    "reason": f"Invalid llm_response JSON: {exc.msg}",
                }
            )
            continue

        if not isinstance(payload, dict):
            invalid_rows.append(
                {
                    "rowId": row["rowId"],
                    "ruleDesc": row["rule_desc"],
                    "reason": "llm_response JSON is not an object",
                }
            )
            continue

        result = normalize_llm_result(payload.get("result"))
        if result == VIOLATION_RESULT:
            violation_count += 1
        elif result == NO_VIOLATION_RESULT:
            no_violation_count += 1
        else:
            invalid_rows.append(
                {
                    "rowId": row["rowId"],
                    "ruleDesc": row["rule_desc"],
                    "reason": "llm_response.result is missing or unsupported",
                    "result": payload.get("result"),
                }
            )

    all_no_violation = (
        total_count > 0
        and no_violation_count == total_count
        and violation_count == 0
        and not invalid_rows
    )

    return {
        "totalCount": total_count,
        "noViolationCount": no_violation_count,
        "violationCount": violation_count,
        "invalidCount": len(invalid_rows),
        "hasViolation": violation_count > 0,
        "allNoViolation": all_no_violation,
        "shouldSkipDownstream": all_no_violation,
        "invalidRows": invalid_rows,
    }
