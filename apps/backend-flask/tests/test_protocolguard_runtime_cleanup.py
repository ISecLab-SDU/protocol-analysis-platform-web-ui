from __future__ import annotations

import os
import sys
import time
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance._docker_runner.config import ProtocolGuardDockerSettings
from protocol_compliance._docker_runner.runner import ProtocolGuardDockerRunner
from protocol_compliance._docker_runner.job import JobPaths


def _settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ProtocolGuardDockerSettings:
    monkeypatch.setenv("PG_RUNTIME_ROOT", str(tmp_path / "runtime"))
    return ProtocolGuardDockerSettings.from_env()


def _runner(settings: ProtocolGuardDockerSettings) -> ProtocolGuardDockerRunner:
    runner = ProtocolGuardDockerRunner.__new__(ProtocolGuardDockerRunner)
    runner._settings = settings
    runner._progress_callback = None
    runner._current_workspace_snapshots = []
    return runner


def _job_paths(settings: ProtocolGuardDockerSettings, job_id: str) -> JobPaths:
    workspace = settings.workspace_root / job_id
    output = settings.output_root / job_id
    config_dir = settings.config_root / job_id
    workspace.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    config_dir.mkdir(parents=True, exist_ok=True)
    return JobPaths(
        job_id=job_id,
        workspace=workspace,
        output=output,
        config_dir=config_dir,
        config_file=config_dir / "config.toml",
        log_file=output / "analysis.log",
    )


def _touch_job(settings: ProtocolGuardDockerSettings, job_id: str, *, age_days: int = 0) -> None:
    paths = [
        settings.workspace_root / job_id,
        settings.output_root / job_id,
        settings.config_root / job_id,
        settings.output_root / "_workspace_snapshots" / job_id,
    ]
    timestamp = time.time() - age_days * 24 * 60 * 60
    for path in paths:
        path.mkdir(parents=True, exist_ok=True)
        marker = path / "marker.txt"
        marker.write_text(job_id, encoding="utf-8")
        os.utime(marker, (timestamp, timestamp))
        os.utime(path, (timestamp, timestamp))


def _set_job_mtime(settings: ProtocolGuardDockerSettings, job_id: str, timestamp: float) -> None:
    paths = [
        settings.workspace_root / job_id,
        settings.output_root / job_id,
        settings.config_root / job_id,
        settings.output_root / "_workspace_snapshots" / job_id,
    ]
    for path in paths:
        marker = path / "marker.txt"
        os.utime(marker, (timestamp, timestamp))
        os.utime(path, (timestamp, timestamp))


def test_config_cleanup_defaults(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = _settings(monkeypatch, tmp_path)

    assert settings.workspace_snapshots_enabled is False
    assert settings.runtime_cleanup_enabled is True
    assert settings.runtime_retention_days == 7
    assert settings.runtime_retention_max_jobs == 20
    assert settings.assert_keep_full_artifacts is False


def test_config_invalid_retention_values_fall_back(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PG_RUNTIME_RETENTION_DAYS", "not-an-int")
    monkeypatch.setenv("PG_RUNTIME_RETENTION_MAX_JOBS", "also-bad")

    settings = _settings(monkeypatch, tmp_path)

    assert settings.runtime_retention_days == 7
    assert settings.runtime_retention_max_jobs == 20


def test_snapshot_disabled_does_not_copy_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = _settings(monkeypatch, tmp_path)
    runner = _runner(settings)
    job_paths = _job_paths(settings, "job-disabled")
    (job_paths.workspace / "source.c").write_text("int main(void) { return 0; }", encoding="utf-8")

    snapshot = runner._snapshot_workspace(job_paths, stage="builder")

    assert snapshot is None
    assert not (settings.output_root / "_workspace_snapshots").exists()
    assert runner._current_workspace_snapshots == []


def test_snapshot_enabled_copies_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PG_WORKSPACE_SNAPSHOTS_ENABLED", "1")
    settings = _settings(monkeypatch, tmp_path)
    runner = _runner(settings)
    job_paths = _job_paths(settings, "job-enabled")
    (job_paths.workspace / "source.c").write_text("int main(void) { return 0; }", encoding="utf-8")

    snapshot = runner._snapshot_workspace(job_paths, stage="builder")

    assert snapshot is not None
    assert (snapshot / "source.c").read_text(encoding="utf-8") == "int main(void) { return 0; }"
    assert runner._current_workspace_snapshots == [{"stage": "builder", "path": str(snapshot)}]


def test_rotation_deletes_old_job_across_managed_roots(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(monkeypatch, tmp_path)
    runner = _runner(settings)
    _touch_job(settings, "old-job", age_days=8)
    _touch_job(settings, "recent-job")

    runner._rotate_runtime_artifacts_once()

    assert not (settings.workspace_root / "old-job").exists()
    assert not (settings.output_root / "old-job").exists()
    assert not (settings.config_root / "old-job").exists()
    assert not (settings.output_root / "_workspace_snapshots" / "old-job").exists()
    assert (settings.workspace_root / "recent-job").exists()


def test_rotation_keeps_newest_twenty_and_deletes_older_excess(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(monkeypatch, tmp_path)
    runner = _runner(settings)
    for index in range(22):
        _touch_job(settings, f"job-{index:02d}")
        _set_job_mtime(settings, f"job-{index:02d}", time.time() + index)

    runner._rotate_runtime_artifacts_once()

    assert not (settings.workspace_root / "job-00").exists()
    assert not (settings.workspace_root / "job-01").exists()
    for index in range(2, 22):
        assert (settings.workspace_root / f"job-{index:02d}").exists()


def test_rotation_excludes_active_job(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = _settings(monkeypatch, tmp_path)
    runner = _runner(settings)
    _touch_job(settings, "active-job", age_days=8)

    runner._rotate_runtime_artifacts_once(active_job_id="active-job")

    assert (settings.workspace_root / "active-job").exists()


def test_rotation_ignores_symlinked_job_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = _settings(monkeypatch, tmp_path)
    runner = _runner(settings)
    target = tmp_path / "outside"
    target.mkdir()
    settings.workspace_root.mkdir(parents=True, exist_ok=True)
    (settings.workspace_root / "linked-job").symlink_to(target, target_is_directory=True)

    runner._rotate_runtime_artifacts_once()

    assert target.exists()
    assert (settings.workspace_root / "linked-job").is_symlink()


def test_assertion_cleanup_preserves_deliverables(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    settings = _settings(monkeypatch, tmp_path)
    runner = _runner(settings)
    job_paths = _job_paths(settings, "assert-job")
    (job_paths.workspace / "project").mkdir()
    (job_paths.config_dir / "config.toml").write_text("[project]", encoding="utf-8")
    (job_paths.output / "analysis.log").write_text("logs", encoding="utf-8")
    (job_paths.output / "assert_tasks").mkdir()
    (job_paths.output / "assert_tasks" / "task.txt").write_text("task", encoding="utf-8")
    (job_paths.output / "instrumented_code").mkdir()
    (job_paths.output / "instrumented_code" / "source.c").write_text("code", encoding="utf-8")
    (job_paths.output / "assert_tasks.zip").write_text("zip", encoding="utf-8")
    (job_paths.output / "instrumentation.diff").write_text("diff", encoding="utf-8")

    runner.cleanup_assertion_intermediates(
        job_id=job_paths.job_id,
    )

    assert job_paths.workspace.exists()
    assert job_paths.config_dir.exists()
    assert (job_paths.output / "analysis.log").exists()
    assert (job_paths.output / "assert_tasks.zip").exists()
    assert (job_paths.output / "instrumentation.diff").exists()
    assert (job_paths.output / "assert_tasks").exists()
    assert (job_paths.output / "instrumented_code").exists()


def test_assertion_cleanup_can_keep_full_artifacts(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("PG_ASSERT_KEEP_FULL_ARTIFACTS", "1")
    settings = _settings(monkeypatch, tmp_path)
    runner = _runner(settings)
    job_paths = _job_paths(settings, "assert-job")
    (job_paths.workspace / "project").mkdir()
    (job_paths.config_dir / "config.toml").write_text("[project]", encoding="utf-8")
    (job_paths.output / "assert_tasks").mkdir()

    runner.cleanup_assertion_intermediates(
        job_id=job_paths.job_id,
    )

    assert job_paths.workspace.exists()
    assert job_paths.config_dir.exists()
    assert (job_paths.output / "assert_tasks").exists()
