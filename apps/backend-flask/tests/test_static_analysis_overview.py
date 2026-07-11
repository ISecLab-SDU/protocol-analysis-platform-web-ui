from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance import static_analysis_overview as overview  # noqa: E402


def test_read_overview_from_database_counts_rules_and_locations(tmp_path: Path) -> None:
    db_path = tmp_path / "sqlite_Sol.db"
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
                "must validate remaining length",
                "Function: parse_packet\n    7 return 0;",
                "parse_packet -> validate_packet",
                (
                    '{"result":"violation_found","reason":"missing guard",'
                    '"violations":[{"filename":"src/server.c",'
                    '"function_name":"parse_packet","code_lines":[7]}]}'
                ),
            ),
        )

    item, findings, table_counts, warnings = overview._read_overview_from_database(
        db_path,
        protocol_name="MQTT",
    )

    assert warnings == []
    assert table_counts == {"rule_code_snippet": 1}
    assert item is not None
    assert item["name"] == "Sol"
    assert item["protocol"] == "MQTT"
    assert item["violationRules"] == 1
    assert item["violationLocations"] == 1
    assert findings == [
        {
            "implementation": "Sol",
            "protocol": "MQTT",
            "rule": "must validate remaining length",
            "reason": "missing guard",
        }
    ]


def test_read_overview_from_analysis_result_uses_verdict_payload() -> None:
    entry = {
        "codeFileName": "sol.tar.gz",
        "protocolName": "MQTT",
        "result": {
            "artifacts": {"database": "/tmp/sqlite_Sol.db"},
            "modelResponse": {
                "verdicts": [
                    {
                        "compliance": "non_compliant",
                        "explanation": "missing guard",
                        "location": {
                            "file": "src/server.c",
                            "functionName": "parse_packet",
                            "codeLines": [7],
                        },
                        "relatedRule": {
                            "requirement": "must validate remaining length",
                        },
                    }
                ]
            },
        },
    }

    item, findings = overview._read_overview_from_analysis_result(entry)

    assert item is not None
    assert item["name"] == "sol"
    assert item["protocol"] == "MQTT"
    assert item["database"] == "sqlite_Sol.db"
    assert item["violationRules"] == 1
    assert item["codeSnippets"] == 1
    assert findings == [
        {
            "implementation": "sol",
            "protocol": "MQTT",
            "rule": "must validate remaining length",
            "reason": "missing guard",
        }
    ]
