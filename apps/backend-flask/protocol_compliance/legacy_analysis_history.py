"""Legacy detection-result and analysis-history storage helpers."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def _data_dir(base_dir: Path | None = None) -> Path:
    return base_dir or Path(__file__).resolve().parent


def _database_dir(base_dir: Path | None = None) -> Path:
    return _data_dir(base_dir) / "databases"


def _database_path(implementation_name: str, base_dir: Path | None = None) -> Path:
    return _database_dir(base_dir) / f"sqlite_{implementation_name}.db"


def _history_file(base_dir: Path | None = None) -> Path:
    return _data_dir(base_dir) / "query_history.json"


def read_detection_results(
    implementation_name: str,
    *,
    base_dir: Path | None = None,
) -> List[Dict[str, Any]]:
    db_path = _database_path(implementation_name, base_dir)
    if not db_path.exists():
        raise FileNotFoundError(db_path)

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT rule_desc, code_snippet, llm_response
            FROM rule_code_snippet
        """)
        rows = cursor.fetchall()

    items = []
    for idx, row in enumerate(rows):
        llm_response: Dict[str, Any] = {}
        if row["llm_response"]:
            try:
                llm_response = json.loads(row["llm_response"])
            except json.JSONDecodeError:
                llm_response = {"result": "error", "reason": "解析失败"}

        items.append({
            "id": idx + 1,
            "rule_desc": row["rule_desc"],
            "code_snippet": row["code_snippet"],
            "llm_response": llm_response,
        })

    return items


def list_available_implementations(*, base_dir: Path | None = None) -> List[str]:
    db_dir = _database_dir(base_dir)
    if not db_dir.exists():
        return []

    implementations = []
    for path in db_dir.iterdir():
        filename = path.name
        if filename.startswith("sqlite_") and filename.endswith(".db"):
            implementations.append(filename[7:-3])

    return implementations


def read_analysis_history(*, base_dir: Path | None = None) -> Any:
    history_file = _history_file(base_dir)
    if not history_file.exists():
        return []

    with history_file.open("r", encoding="utf-8") as f:
        return json.load(f)


def _detection_statistics(
    implementation_name: str,
    *,
    base_dir: Path | None = None,
) -> Dict[str, int]:
    db_path = _database_path(implementation_name, base_dir)
    statistics = {"total": 0, "violations": 0, "noViolations": 0, "noResult": 0}

    if not db_path.exists():
        return statistics

    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT llm_response FROM rule_code_snippet")
            rows = cursor.fetchall()
    except sqlite3.Error:
        return statistics

    statistics["total"] = len(rows)
    for row in rows:
        if row[0]:
            try:
                response = json.loads(row[0])
                result = response.get("result", "").lower()
                if "no violation" in result:
                    statistics["noViolations"] += 1
                elif "violation" in result:
                    statistics["violations"] += 1
                else:
                    statistics["noResult"] += 1
            except json.JSONDecodeError:
                statistics["noResult"] += 1

    return statistics


def append_analysis_history(
    implementation_name: str,
    protocol_name: str,
    *,
    base_dir: Path | None = None,
) -> None:
    history_file = _history_file(base_dir)
    statistics = _detection_statistics(implementation_name, base_dir=base_dir)

    try:
        history = read_analysis_history(base_dir=base_dir)
    except (json.JSONDecodeError, OSError):
        history = []

    history.insert(0, {
        "id": str(uuid.uuid4()),
        "implementationName": implementation_name,
        "protocolName": protocol_name,
        "statistics": statistics,
        "createdAt": datetime.now().isoformat(),
    })
    history = history[:50]

    with history_file.open("w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
