from __future__ import annotations

import json
from pathlib import Path

from protocol_compliance import violation_history_state as state


def test_violation_history_state_uses_configured_state_dir(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROTOCOLGUARD_STATE_DIR", str(tmp_path / "state"))

    assert state._violation_history_timestamp_store_path() == (
        tmp_path / "state" / "violation_history_timestamps.json"
    )
    assert state._violation_history_writable_database_root() == (
        tmp_path / "state" / "writable-databases"
    )


def test_violation_history_writable_database_path_sanitizes_job_id(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PROTOCOLGUARD_STATE_DIR", str(tmp_path / "state"))

    source = tmp_path / "readonly" / "sqlite_Test.db"
    destination = state._violation_history_writable_database_path(
        source,
        job_id="../../bad job",
    )

    assert destination.parent.name == "bad_job"
    assert destination.name.endswith("-sqlite_Test.db")
    assert destination.name.startswith(f"{state._sqlite_path_hash(source)}-")


def test_violation_history_timestamp_payload_round_trip(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PROTOCOLGUARD_STATE_DIR", str(tmp_path / "state"))
    payload = {
        "databases": {"db": "created"},
        "deleted": {"item": "deleted"},
        "rows": {"row": "seen"},
    }

    state._save_violation_history_timestamps(payload)

    saved = json.loads(state._violation_history_timestamp_store_path().read_text(encoding="utf-8"))
    assert saved == payload
    assert state._load_violation_history_timestamps() == payload


def test_violation_history_timestamp_loader_recovers_from_invalid_json(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PROTOCOLGUARD_STATE_DIR", str(tmp_path / "state"))
    store_path = state._violation_history_timestamp_store_path()
    store_path.parent.mkdir(parents=True)
    store_path.write_text("{invalid", encoding="utf-8")

    assert state._load_violation_history_timestamps() == {
        "databases": {},
        "deleted": {},
        "rows": {},
    }
