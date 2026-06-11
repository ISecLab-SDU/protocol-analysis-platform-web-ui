from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance.static_analysis_result_checker import (
    check_static_analysis_database,
)


def _create_database(tmp_path: Path, responses: list[str]) -> Path:
    db_path = tmp_path / "analysis.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE rule_code_snippet (
                rule_desc TEXT PRIMARY KEY,
                code_snippet TEXT NOT NULL,
                call_graph TEXT NOT NULL,
                llm_response TEXT NOT NULL DEFAULT ''
            )
            """
        )
        for index, response in enumerate(responses, start=1):
            conn.execute(
                """
                INSERT INTO rule_code_snippet (
                    rule_desc,
                    code_snippet,
                    call_graph,
                    llm_response
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    f"rule {index}",
                    "int main(void) { return 0; }",
                    "",
                    response,
                ),
            )
    return db_path


def test_check_static_analysis_database_skips_when_all_rows_are_no_violation(
    tmp_path: Path,
) -> None:
    db_path = _create_database(
        tmp_path,
        [
            '{"result":"no violation found!","reason":"ok"}',
            '{"result":"NO VIOLATION FOUND!","reason":"ok"}',
        ],
    )

    summary = check_static_analysis_database(db_path)

    assert summary["totalCount"] == 2
    assert summary["noViolationCount"] == 2
    assert summary["violationCount"] == 0
    assert summary["hasViolation"] is False
    assert summary["allNoViolation"] is True
    assert summary["shouldSkipDownstream"] is True


def test_check_static_analysis_database_continues_when_violation_exists(
    tmp_path: Path,
) -> None:
    db_path = _create_database(
        tmp_path,
        [
            '{"result":"no violation found!","reason":"ok"}',
            '{"result":"violation found!","reason":"bad"}',
        ],
    )

    summary = check_static_analysis_database(db_path)

    assert summary["totalCount"] == 2
    assert summary["violationCount"] == 1
    assert summary["hasViolation"] is True
    assert summary["allNoViolation"] is False
    assert summary["shouldSkipDownstream"] is False


def test_check_static_analysis_database_reports_invalid_rows_without_violation(
    tmp_path: Path,
) -> None:
    db_path = _create_database(
        tmp_path,
        [
            '{"result":"no violation found!","reason":"ok"}',
            '{"result":"maybe","reason":"unknown"}',
            '{broken',
        ],
    )

    summary = check_static_analysis_database(db_path)

    assert summary["totalCount"] == 3
    assert summary["violationCount"] == 0
    assert summary["invalidCount"] == 2
    assert summary["allNoViolation"] is False
    assert summary["shouldSkipDownstream"] is False
