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
