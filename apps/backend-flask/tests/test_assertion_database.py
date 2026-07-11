from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance import assertion_database  # noqa: E402


def test_resolve_assertion_database_path_falls_back_to_job_database(
    tmp_path: Path,
) -> None:
    job_id = "94944131-c267-4b41-b4b3-f3024c10c7de"
    requested = tmp_path / job_id / "database" / "sqlite_Sol.db"
    fallback = tmp_path / job_id / "database" / "sqlite_mosquitto.db"
    fallback.parent.mkdir(parents=True)
    fallback.write_text("sqlite", encoding="utf-8")

    resolved, warnings = assertion_database._resolve_assertion_database_path(
        requested,
        candidate_sqlite_roots_for_job=lambda _job_id: [fallback.parent],
    )

    assert resolved == fallback
    assert warnings == [f"指定的分析结果数据不存在：{requested}"]


def test_candidate_sqlite_roots_for_job_includes_snapshot_paths(
    monkeypatch,
    tmp_path: Path,
) -> None:
    runtime_root = tmp_path / "runtime"
    monkeypatch.setenv("PG_RUNTIME_ROOT", str(runtime_root))
    output_path = tmp_path / "output"
    workspace_path = tmp_path / "workspace"
    database_path = output_path / "database" / "sqlite_Sol.db"

    roots = assertion_database._candidate_sqlite_roots_for_job(
        "job-1",
        expand_path=lambda raw: Path(raw).expanduser() if raw else None,
        get_static_analysis_job=lambda _job_id: {
            "database_path": str(database_path),
            "output_path": str(output_path),
            "workspace_path": str(workspace_path),
        },
    )

    assert roots == [
        runtime_root / "outputs" / "job-1" / "database",
        runtime_root / "outputs" / "job-1",
        runtime_root / "workspaces" / "job-1" / "database",
        runtime_root / "workspaces" / "job-1",
        output_path / "database",
        output_path,
        workspace_path / "database",
        workspace_path,
    ]
