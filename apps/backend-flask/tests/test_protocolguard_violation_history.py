from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from flask import Flask

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance import routes  # noqa: E402


def _create_rule_database(
    db_path: Path,
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


def _history_entry(db_path: Path, rule_desc: str = "rule from sqlite") -> dict:
    return {
        "jobId": "job-with-database",
        "status": "completed",
        "workspacePath": str(db_path.parent),
        "databasePath": str(db_path),
        "createdAt": "2026-06-09T10:00:00+00:00",
        "updatedAt": "2026-06-09T10:00:00+00:00",
        "completedAt": "2026-06-09T10:00:00+00:00",
        "result": {
            "artifacts": {"database": str(db_path)},
            "modelResponse": {
                "verdicts": [
                    {
                        "compliance": "non_compliant",
                        "explanation": "history reason",
                        "findingId": "finding-1",
                        "relatedRule": {"id": "rule-1", "requirement": rule_desc},
                    }
                ]
            },
        },
    }


def _app(monkeypatch) -> Flask:
    monkeypatch.setattr(routes, "_ensure_authenticated", lambda: (None, None))
    app = Flask(__name__)
    app.register_blueprint(routes.bp)
    return app


def test_violation_history_prefers_database_ids_for_database_backed_jobs(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PROTOCOLGUARD_STATE_DIR", str(tmp_path / "state"))
    db_path = tmp_path / "sqlite_Test.db"
    _create_rule_database(db_path)
    entry = _history_entry(db_path)

    monkeypatch.setattr(
        routes,
        "list_static_analysis_history",
        lambda limit=50, include_result=False: [entry],
    )
    monkeypatch.setattr(
        routes,
        "_iter_static_analysis_database_sources",
        lambda job_limit: (
            [
                {
                    "path": db_path,
                    "sourceType": "job",
                    "jobId": "job-with-database",
                    "protocolName": "MQTT",
                    "createdAt": entry["createdAt"],
                    "updatedAt": entry["updatedAt"],
                }
            ],
            [],
        ),
    )

    response = _app(monkeypatch).test_client().get(
        "/api/protocol-compliance/static-analysis/violation-history"
    )

    assert response.status_code == 200
    payload = response.get_json()
    item = payload["data"]["items"][0]
    assert item["id"] == routes._build_violation_history_item_id(
        db_path=db_path,
        job_id="job-with-database",
        row_id=1,
        row_index=1,
        rule_desc="rule from sqlite",
        source_type="job",
    )
    assert item["codeSnippet"].startswith("Function: parse_packet")
    assert item["reason"] == "sqlite reason"


def test_delete_violation_history_accepts_analysis_result_ids(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PROTOCOLGUARD_STATE_DIR", str(tmp_path / "state"))
    db_path = tmp_path / "sqlite_Test.db"
    _create_rule_database(db_path)
    entry = _history_entry(db_path)
    stale_item_id = routes._read_violation_history_from_analysis_result(entry)[0][
        "id"
    ]

    monkeypatch.setattr(
        routes,
        "list_static_analysis_history",
        lambda limit=50, include_result=False: [entry],
    )
    monkeypatch.setattr(
        routes,
        "_iter_static_analysis_database_sources",
        lambda job_limit: ([], []),
    )

    response = _app(monkeypatch).test_client().delete(
        f"/api/protocol-compliance/static-analysis/violation-history/{stale_item_id}"
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["data"]["deleted"] is True
    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM rule_code_snippet").fetchone()[0]
    assert count == 0


def test_delete_violation_history_accepts_legacy_row_index_after_prior_deletes(
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
        for rule_desc in ("first rule", "second rule", "target rule"):
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
                    "Function: parse_packet\n    7 return 0;",
                    "parse_packet -> validate_packet",
                    '{"result":"violation_found","reason":"sqlite reason"}',
                ),
            )
        conn.execute("DELETE FROM rule_code_snippet WHERE rule_desc = ?", ("first rule",))

    stale_item_id = routes._build_violation_history_item_id(
        db_path=db_path,
        job_id=None,
        row_index=3,
        rule_desc="target rule",
        source_type="builtin",
    )

    deleted, warnings = routes._delete_violation_history_from_database(
        db_path,
        item_id=stale_item_id,
        source_type="builtin",
    )

    assert warnings == []
    assert deleted is not None
    with sqlite3.connect(db_path) as conn:
        remaining_rules = [
            row[0]
            for row in conn.execute(
                "SELECT rule_desc FROM rule_code_snippet ORDER BY rowid"
            )
        ]
    assert remaining_rules == ["second rule"]


def test_physical_delete_payload_can_mark_equivalent_history_deleted(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PROTOCOLGUARD_STATE_DIR", str(tmp_path / "state"))
    db_path = tmp_path / "sqlite_Test.db"
    _create_rule_database(db_path)
    item_id = routes._build_violation_history_item_id(
        db_path=db_path,
        job_id=None,
        row_id=1,
        row_index=1,
        rule_desc="rule from sqlite",
        source_type="builtin",
    )

    deleted, warnings = routes._delete_violation_history_from_database(
        db_path,
        item_id=item_id,
        source_type="builtin",
    )
    assert warnings == []
    assert deleted is not None

    routes._remember_deleted_violation_history(deleted)

    assert routes._is_violation_history_deleted(
        {
            "databaseName": "sqlite_Test.db",
            "id": "alternate-source-id",
            "reason": "sqlite reason",
            "ruleDesc": "rule from sqlite",
            "violations": [],
        }
    )


def test_delete_violation_history_payload_matches_duplicate_rules(
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

    deleted, warnings = routes._delete_violation_history_by_payload(
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
    with sqlite3.connect(db_path) as conn:
        remaining_rows = conn.execute(
            "SELECT code_snippet FROM rule_code_snippet ORDER BY rowid"
        ).fetchall()
    assert remaining_rows == [("Function: read_callback\n    7 first",)]


def test_violation_history_uses_llm_row_timestamp_instead_of_database_mtime(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PROTOCOLGUARD_STATE_DIR", str(tmp_path / "state"))
    db_path = tmp_path / "sqlite_Test.db"
    row_timestamp = "2026-06-09T12:13:19+00:00"
    _create_rule_database(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            UPDATE rule_code_snippet
            SET llm_response = ?
            """,
            (
                (
                    '{"result":"violation_found","reason":"sqlite reason",'
                    f'"updated_at":"{row_timestamp}"}}'
                ),
            ),
        )

    items, warnings = routes._read_violation_history_from_database(
        db_path,
        source_type="builtin",
    )

    assert warnings == []
    assert items[0]["updatedAt"] == row_timestamp
    assert items[0]["createdAt"] == row_timestamp
    assert items[0]["extractedAt"] == row_timestamp


def test_violation_history_prefers_llm_row_timestamp_over_job_timestamp(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PROTOCOLGUARD_STATE_DIR", str(tmp_path / "state"))
    db_path = tmp_path / "sqlite_Test.db"
    row_timestamp = "2026-06-09T21:18:15+00:00"
    _create_rule_database(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            UPDATE rule_code_snippet
            SET llm_response = ?
            """,
            (
                (
                    '{"result":"violation_found","reason":"sqlite reason",'
                    f'"updated_at":"{row_timestamp}"}}'
                ),
            ),
        )

    items, warnings = routes._read_violation_history_from_database(
        db_path,
        source_type="job",
        updated_at="2026-06-09T20:32:36+00:00",
    )

    assert warnings == []
    assert items[0]["updatedAt"] == row_timestamp


def test_violation_history_keeps_cached_time_after_database_delete(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PROTOCOLGUARD_STATE_DIR", str(tmp_path / "state"))
    db_path = tmp_path / "sqlite_Test.db"
    _create_rule_database(db_path)

    first_items, first_warnings = routes._read_violation_history_from_database(
        db_path,
        source_type="builtin",
    )
    with sqlite3.connect(db_path) as conn:
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
                "second rule",
                "Function: parse_packet\n    8 return 1;",
                "parse_packet -> validate_packet",
                '{"result":"violation_found","reason":"second reason"}',
            ),
        )
        conn.execute(
            "DELETE FROM rule_code_snippet WHERE rule_desc = ?",
            ("second rule",),
        )

    second_items, second_warnings = routes._read_violation_history_from_database(
        db_path,
        source_type="builtin",
    )

    assert first_warnings == []
    assert second_warnings == []
    assert second_items[0]["updatedAt"] == first_items[0]["updatedAt"]


def test_deleted_violation_history_marker_hides_equivalent_items(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PROTOCOLGUARD_STATE_DIR", str(tmp_path / "state"))
    deleted_item = {
        "databaseName": "sqlite_Sol.db",
        "id": "stale-id",
        "reason": "target reason",
        "ruleDesc": "duplicate rule",
        "violations": [
            {
                "codeLines": [7, 8],
                "filename": "/workspace/project/sol/src/server.c",
                "functionName": "read_callback",
            }
        ],
    }
    equivalent_item = {
        "databaseName": "sqlite_sol.db",
        "id": "new-id-from-another-source",
        "reason": "target reason",
        "ruleDesc": "duplicate rule",
        "violations": [
            {
                "codeLines": [7, 8],
                "filename": "/workspace/project/sol/src/server.c",
                "functionName": "read_callback",
            }
        ],
    }

    routes._remember_deleted_violation_history(deleted_item)

    assert routes._is_violation_history_deleted(equivalent_item)


def test_upserted_violation_history_clears_deleted_marker(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PROTOCOLGUARD_STATE_DIR", str(tmp_path / "state"))
    deleted_item = {
        "databaseName": "sqlite_sol.db",
        "id": "stale-id",
        "reason": "target reason",
        "ruleDesc": "duplicate rule",
    }
    upserted_item = {
        "databaseName": "sqlite_sol.db",
        "id": "new-id",
        "reason": "target reason",
        "ruleDesc": "duplicate rule",
    }

    routes._remember_deleted_violation_history(deleted_item)
    assert routes._is_violation_history_deleted(upserted_item)

    routes._forget_deleted_violation_history(upserted_item)

    assert not routes._is_violation_history_deleted(upserted_item)


def test_delete_violation_history_soft_deletes_reappeared_result_item(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PROTOCOLGUARD_STATE_DIR", str(tmp_path / "state"))
    db_path = tmp_path / "sqlite_Test.db"
    entry = _history_entry(db_path)
    history_item = routes._read_violation_history_from_analysis_result(entry)[0]

    monkeypatch.setattr(
        routes,
        "list_static_analysis_history",
        lambda limit=50, include_result=False: [entry],
    )
    monkeypatch.setattr(
        routes,
        "_iter_static_analysis_database_sources",
        lambda job_limit: ([], []),
    )

    client = _app(monkeypatch).test_client()
    delete_response = client.delete(
        f"/api/protocol-compliance/static-analysis/violation-history/{history_item['id']}",
        json={
            "databaseName": history_item["databaseName"],
            "databasePath": history_item["databasePath"],
            "reason": history_item["reason"],
            "ruleDesc": history_item["ruleDesc"],
            "violations": history_item["violations"],
        },
    )
    list_response = client.get(
        "/api/protocol-compliance/static-analysis/violation-history"
    )

    assert delete_response.status_code == 200
    assert delete_response.get_json()["data"]["deleted"] is True
    assert list_response.status_code == 200
    assert list_response.get_json()["data"]["items"] == []
