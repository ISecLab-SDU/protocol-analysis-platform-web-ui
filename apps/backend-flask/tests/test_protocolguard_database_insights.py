from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from flask import Flask

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance import routes  # noqa: E402


def test_database_insights_prefers_sqlite_code_snippets_over_history(
    monkeypatch,
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
                "rule from sqlite",
                "Function: parse_packet\nPath: src/parser.c:7\n    7 return 0;",
                "parse_packet -> validate_packet",
                '{"result":"violation_found","reason":"sqlite reason","violations":[]}',
            ),
        )

    monkeypatch.setattr(routes, "_ensure_authenticated", lambda: (None, None))
    monkeypatch.setattr(
        routes,
        "_find_static_analysis_history_entry",
        lambda job_id: {
            "jobId": job_id,
            "result": {
                "artifacts": {"database": str(db_path)},
                "modelResponse": {
                    "verdicts": [
                        {
                            "compliance": "non_compliant",
                            "explanation": "history reason",
                            "relatedRule": {"requirement": "rule from history"},
                        }
                    ]
                },
            },
        },
    )

    app = Flask(__name__)
    app.register_blueprint(routes.bp)

    response = app.test_client().post(
        "/api/protocol-compliance/static-analysis/database-insights",
        json={
            "databasePath": str(db_path),
            "jobId": "job-with-history",
            "workspacePath": str(tmp_path),
        },
    )

    assert response.status_code == 200
    payload = response.get_json()
    finding = payload["data"]["findings"][0]
    assert finding["ruleDesc"] == "rule from sqlite"
    assert finding["codeSnippet"].startswith("Function: parse_packet")
    assert finding["callGraph"] == "parse_packet -> validate_packet"

