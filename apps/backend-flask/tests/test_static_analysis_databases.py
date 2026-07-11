from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance import static_analysis_databases as databases  # noqa: E402
from protocol_compliance import violation_history_state as state  # noqa: E402


def _create_sqlite_database(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE sample (id INTEGER PRIMARY KEY)")


def test_find_sqlite_file_prefers_explicit_database_path(tmp_path: Path) -> None:
    explicit = tmp_path / "explicit.db"
    workspace = tmp_path / "workspace"
    workspace_database = workspace / "sqlite_result.db"
    _create_sqlite_database(explicit)
    _create_sqlite_database(workspace_database)

    resolved, warnings = databases._find_sqlite_file(
        str(explicit),
        str(workspace),
    )

    assert resolved == explicit
    assert warnings == []


def test_find_sqlite_file_resolves_workspace_database(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace_database = workspace / "sqlite_result.db"
    _create_sqlite_database(workspace_database)

    resolved, warnings = databases._find_sqlite_file(
        str(tmp_path / "missing.db"),
        str(workspace),
    )

    assert resolved == workspace_database
    assert warnings == [f"指定的数据库路径不存在：{tmp_path / 'missing.db'}"]


def test_iter_violation_history_writable_database_copies(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("PROTOCOLGUARD_STATE_DIR", str(tmp_path / "state"))

    manual_source = tmp_path / "manual.db"
    job_source = tmp_path / "job.db"
    _create_sqlite_database(manual_source)
    _create_sqlite_database(job_source)

    manual_copy = state._violation_history_writable_database_path(
        manual_source,
        job_id=None,
    )
    job_copy = state._violation_history_writable_database_path(
        job_source,
        job_id="job-1",
    )
    _create_sqlite_database(manual_copy)
    _create_sqlite_database(job_copy)
    _create_sqlite_database(
        state._violation_history_writable_database_root() / "job-1" / "bad-name.db"
    )

    sources = databases._iter_violation_history_writable_database_copies()

    assert sources == [
        {
            "path": job_copy,
            "sourceType": "job",
            "jobId": "job-1",
            "protocolName": None,
            "createdAt": None,
            "updatedAt": None,
            "originalPathHash": state._sqlite_path_hash(job_source),
        },
        {
            "path": manual_copy,
            "sourceType": "builtin",
            "jobId": None,
            "protocolName": None,
            "createdAt": None,
            "updatedAt": None,
            "originalPathHash": state._sqlite_path_hash(manual_source),
        },
    ]
