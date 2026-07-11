from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, cast

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance import violation_history_markers as markers  # noqa: E402


def _dedupe_key(value: object) -> str:
    return " ".join(str(value or "").split()).lower()


def _violation_match_keys(violations: object) -> set[str]:
    if not isinstance(violations, list):
        return set()
    return {
        "|".join(
            [
                _dedupe_key(cast(dict[str, Any], item).get("filename")),
                _dedupe_key(cast(dict[str, Any], item).get("functionName")),
                ",".join(str(line) for line in cast(dict[str, Any], item).get("codeLines", [])),
            ]
        )
        for item in violations
        if isinstance(item, dict)
    }


def test_history_database_name_marker_strips_writable_copy_hash() -> None:
    assert (
        markers._history_database_name_marker(
            "a1b2c3d4e5f6-sqlite_Sol.db",
            dedupe_key=_dedupe_key,
        )
        == "sqlite_sol.db"
    )


def test_delete_markers_include_equivalent_semantic_marker() -> None:
    item = {
        "databaseName": "sqlite_Sol.db",
        "reason": "Target reason",
        "ruleDesc": "Duplicate rule",
        "violations": [
            {
                "codeLines": [7, 8],
                "filename": "/workspace/project/sol/src/server.c",
                "functionName": "read_callback",
            }
        ],
    }

    item_markers = markers._history_item_delete_markers(
        item,
        dedupe_key=_dedupe_key,
        violation_match_keys=_violation_match_keys,
    )

    assert (
        "semantic:sqlite_sol.db:duplicate rule:target reason:"
        "/workspace/project/sol/src/server.c|read_callback|7,8"
    ) in item_markers
