from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance import violation_history_records as records  # noqa: E402


def _create_rule_database(
    db_path: Path,
    *,
    rule_desc: str = "rule from sqlite",
) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE rule_code_snippet (
                rule_desc TEXT,
                code_snippet TEXT,
                call_graph TEXT,
                llm_response TEXT
            )
            """
        )
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
                rule_desc,
                "Function: parse_packet\nPath: src/parser.c:7\n    7 return 0;",
                "parse_packet -> validate_packet",
                '{"result":"violation_found","reason":"sqlite reason","violations":[]}',
            ),
        )


def test_read_violation_history_from_database_builds_database_backed_items(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "sqlite_Test.db"
    _create_rule_database(db_path)

    items, warnings = records._read_violation_history_from_database(
        db_path,
        database_history_display_time=lambda _path: "2026-06-09T10:00:00+00:00",
        row_history_display_time=lambda *args, **kwargs: "2026-06-09T11:00:00+00:00",
        source_type="job",
        job_id="job-1",
        protocol_name="MQTT",
    )

    assert warnings == []
    assert items == [
        {
            "id": records._build_violation_history_item_id(
                db_path=db_path,
                job_id="job-1",
                row_id=1,
                row_index=1,
                rule_desc="rule from sqlite",
                source_type="job",
            ),
            "sourceType": "job",
            "jobId": "job-1",
            "implementationName": "Test",
            "protocolName": "MQTT",
            "databaseName": "sqlite_Test.db",
            "databasePath": str(db_path),
            "ruleDesc": "rule from sqlite",
            "result": "violation_found",
            "resultLabel": "发现违规",
            "reason": "sqlite reason",
            "codeSnippet": "Function: parse_packet\nPath: src/parser.c:7\n    7 return 0;",
            "callGraph": "parse_packet -> validate_packet",
            "llmRaw": '{"result":"violation_found","reason":"sqlite reason","violations":[]}',
            "violations": None,
            "createdAt": "2026-06-09T11:00:00+00:00",
            "updatedAt": "2026-06-09T11:00:00+00:00",
            "extractedAt": "2026-06-09T11:00:00+00:00",
        }
    ]


def test_delete_violation_history_by_payload_selects_best_duplicate_rule(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "sqlite_Test.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE rule_code_snippet (
                rule_desc TEXT,
                code_snippet TEXT,
                call_graph TEXT,
                llm_response TEXT
            )
            """
        )
        for code_snippet, reason in (
            ("Function: read_callback\n    7 first", "first reason"),
            ("Function: process_message\n    9 target", "target reason"),
        ):
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
                    "duplicate rule",
                    code_snippet,
                    "call graph",
                    f'{{"result":"violation_found","reason":"{reason}"}}',
                ),
            )

    deleted, warnings = records._delete_violation_history_by_payload(
        db_path,
        item_id="stale-id",
        payload={
            "codeSnippet": "Function: process_message\n    9 target",
            "reason": "target reason",
            "ruleDesc": "duplicate rule",
        },
    )

    assert warnings == []
    assert deleted is not None
    assert deleted["codeSnippet"] == "Function: process_message\n    9 target"
    with sqlite3.connect(db_path) as conn:
        remaining_rows = conn.execute(
            "SELECT code_snippet FROM rule_code_snippet ORDER BY rowid"
        ).fetchall()
    assert remaining_rows == [("Function: read_callback\n    7 first",)]
