from __future__ import annotations

import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance.routes import _resolve_assertion_database_path  # noqa: E402


def test_assertion_database_resolution_falls_back_to_output_database(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    job_id = "94944131-c267-4b41-b4b3-f3024c10c7de"
    runtime_root = tmp_path / "runtime"
    monkeypatch.setenv("PG_RUNTIME_ROOT", str(runtime_root))

    requested = runtime_root / "outputs" / job_id / "database" / "sqlite_Sol.db"
    fallback = runtime_root / "outputs" / job_id / "database" / "sqlite_mosquitto.db"
    fallback.parent.mkdir(parents=True)
    fallback.write_text("sqlite", encoding="utf-8")

    resolved, warnings = _resolve_assertion_database_path(requested)

    assert resolved == fallback
    assert warnings == [f"指定的分析结果数据不存在：{requested}"]


def test_assertion_database_resolution_keeps_existing_requested_file(
    tmp_path: Path,
) -> None:
    requested = tmp_path / "sqlite_Sol.db"
    requested.write_text("sqlite", encoding="utf-8")

    resolved, warnings = _resolve_assertion_database_path(requested)

    assert resolved == requested
    assert warnings == []
