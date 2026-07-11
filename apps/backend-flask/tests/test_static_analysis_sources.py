from __future__ import annotations

from pathlib import Path

from protocol_compliance.static_analysis_sources import (
    iter_static_analysis_database_sources,
)


def test_static_analysis_sources_preserve_order_and_shadow_builtin(tmp_path: Path) -> None:
    db_dir = tmp_path / "databases"
    db_dir.mkdir()
    builtin_db = db_dir / "sqlite_sol.db"
    builtin_db.touch()
    job_db = tmp_path / "jobs" / "sqlite_job.db"
    job_db.parent.mkdir()
    job_db.touch()
    writable_copy = tmp_path / "state" / "manual" / "abc123-sqlite_sol.db"
    writable_copy.parent.mkdir(parents=True)
    writable_copy.touch()

    def path_hash(path: Path) -> str:
        if path == builtin_db:
            return "abc123"
        return path.name

    sources, warnings = iter_static_analysis_database_sources(
        db_dir=db_dir,
        find_sqlite_file=lambda _database_path, _workspace_path: (job_db, []),
        iter_writable_database_copies=lambda: [
            {
                "path": writable_copy,
                "sourceType": "builtin",
                "jobId": None,
                "protocolName": None,
                "createdAt": None,
                "updatedAt": None,
                "originalPathHash": "abc123",
            }
        ],
        job_limit=50,
        list_static_analysis_history=lambda limit: [
            {
                "status": "completed",
                "jobId": "job-1",
                "databasePath": str(job_db),
                "workspacePath": None,
                "protocolName": "MQTT",
                "createdAt": "created",
                "updatedAt": "updated",
            }
        ],
        sqlite_path_hash=path_hash,
    )

    assert warnings == []
    assert sources == [
        {
            "path": writable_copy,
            "sourceType": "builtin",
            "jobId": None,
            "protocolName": None,
            "createdAt": None,
            "updatedAt": None,
            "originalPathHash": "abc123",
        },
        {
            "path": job_db,
            "sourceType": "job",
            "jobId": "job-1",
            "protocolName": "MQTT",
            "createdAt": "created",
            "updatedAt": "updated",
        },
    ]


def test_static_analysis_sources_can_skip_builtin_databases(tmp_path: Path) -> None:
    db_dir = tmp_path / "databases"
    db_dir.mkdir()
    (db_dir / "sqlite_sol.db").touch()

    sources, warnings = iter_static_analysis_database_sources(
        db_dir=db_dir,
        find_sqlite_file=lambda _database_path, _workspace_path: (None, []),
        include_builtin=False,
        iter_writable_database_copies=lambda: [],
        job_limit=50,
        list_static_analysis_history=lambda limit: [],
        sqlite_path_hash=lambda path: path.name,
    )

    assert sources == []
    assert warnings == []
