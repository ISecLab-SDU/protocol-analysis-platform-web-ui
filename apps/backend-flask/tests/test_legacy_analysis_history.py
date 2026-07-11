from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance.legacy_analysis_history import (  # noqa: E402
    append_analysis_history,
    list_available_implementations,
    read_analysis_history,
    read_detection_results,
)


def _create_rule_database(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE rule_code_snippet (
                rule_desc TEXT,
                code_snippet TEXT,
                llm_response TEXT
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO rule_code_snippet (rule_desc, code_snippet, llm_response)
            VALUES (?, ?, ?)
            """,
            [
                (
                    "rule one",
                    "line one",
                    json.dumps({"result": "violation found", "reason": "bad"}),
                ),
                (
                    "rule two",
                    "line two",
                    json.dumps({"result": "no violation", "reason": "ok"}),
                ),
                ("rule three", "line three", "{invalid"),
            ],
        )


def test_read_detection_results_preserves_legacy_payload_shape(tmp_path: Path) -> None:
    _create_rule_database(tmp_path / "databases" / "sqlite_sol.db")

    items = read_detection_results("sol", base_dir=tmp_path)

    assert items == [
        {
            "id": 1,
            "rule_desc": "rule one",
            "code_snippet": "line one",
            "llm_response": {"result": "violation found", "reason": "bad"},
        },
        {
            "id": 2,
            "rule_desc": "rule two",
            "code_snippet": "line two",
            "llm_response": {"result": "no violation", "reason": "ok"},
        },
        {
            "id": 3,
            "rule_desc": "rule three",
            "code_snippet": "line three",
            "llm_response": {"result": "error", "reason": "解析失败"},
        },
    ]


def test_analysis_history_append_preserves_statistics_and_limit(tmp_path: Path) -> None:
    _create_rule_database(tmp_path / "databases" / "sqlite_sol.db")
    existing = [
        {"id": str(index), "implementationName": "old", "protocolName": "MQTT"}
        for index in range(55)
    ]
    (tmp_path / "query_history.json").write_text(
        json.dumps(existing, ensure_ascii=False),
        encoding="utf-8",
    )

    append_analysis_history("sol", "MQTT", base_dir=tmp_path)

    history = read_analysis_history(base_dir=tmp_path)
    assert len(history) == 50
    assert history[0]["implementationName"] == "sol"
    assert history[0]["protocolName"] == "MQTT"
    assert history[0]["statistics"] == {
        "total": 3,
        "violations": 1,
        "noViolations": 1,
        "noResult": 1,
    }


def test_list_available_implementations_matches_sqlite_database_names(tmp_path: Path) -> None:
    db_dir = tmp_path / "databases"
    db_dir.mkdir()
    (db_dir / "sqlite_sol.db").touch()
    (db_dir / "sqlite_mosquitto.db").touch()
    (db_dir / "notes.txt").touch()

    assert set(list_available_implementations(base_dir=tmp_path)) == {"sol", "mosquitto"}
