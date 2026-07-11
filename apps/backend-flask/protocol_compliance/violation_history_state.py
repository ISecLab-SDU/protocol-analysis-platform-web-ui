"""Persistent state helpers for ProtocolGuard violation-history routes."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

LOGGER = logging.getLogger(__name__)


def _violation_history_timestamp_store_path() -> Path:
    state_dir = Path(
        os.environ.get(
            "PROTOCOLGUARD_STATE_DIR",
            str(Path(__file__).resolve().parent / "_state"),
        )
    ).expanduser()
    return state_dir / "violation_history_timestamps.json"


def _violation_history_writable_database_root() -> Path:
    return _violation_history_timestamp_store_path().parent / "writable-databases"


def _sqlite_path_hash(path: Path) -> str:
    return hashlib.sha1(str(path.expanduser()).encode("utf-8")).hexdigest()[:12]


def _violation_history_writable_database_path(
    source_path: Path,
    *,
    job_id: Optional[str],
) -> Path:
    job_key = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(job_id or "manual")).strip("._")
    if not job_key:
        job_key = "manual"
    return (
        _violation_history_writable_database_root()
        / job_key
        / f"{_sqlite_path_hash(source_path)}-{source_path.name}"
    )


def _load_violation_history_timestamps() -> Dict[str, Any]:
    store_path = _violation_history_timestamp_store_path()
    if not store_path.is_file():
        return {"databases": {}, "deleted": {}, "rows": {}}
    try:
        payload = json.loads(store_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        LOGGER.warning("Failed to read violation history timestamps: %s", exc)
        return {"databases": {}, "deleted": {}, "rows": {}}
    if not isinstance(payload, dict):
        return {"databases": {}, "deleted": {}, "rows": {}}
    databases = payload.get("databases")
    deleted = payload.get("deleted")
    rows = payload.get("rows")
    return {
        "databases": databases if isinstance(databases, dict) else {},
        "deleted": deleted if isinstance(deleted, dict) else {},
        "rows": rows if isinstance(rows, dict) else {},
    }


def _save_violation_history_timestamps(payload: Dict[str, Any]) -> None:
    store_path = _violation_history_timestamp_store_path()
    try:
        store_path.parent.mkdir(parents=True, exist_ok=True)
        store_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    except OSError as exc:
        LOGGER.warning("Failed to write violation history timestamps: %s", exc)
