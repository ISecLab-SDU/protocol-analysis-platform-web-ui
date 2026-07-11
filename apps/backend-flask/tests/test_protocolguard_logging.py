from __future__ import annotations

import logging
from typing import Any, cast
import sys
import types
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance._docker_runner.config import ProtocolGuardDockerSettings  # noqa: E402
from protocol_compliance._docker_runner.job import JobPaths  # noqa: E402
from protocol_compliance._docker_runner.runner import ProtocolGuardDockerRunner  # noqa: E402
from protocol_compliance.job_logging import JobStageLogger  # noqa: E402


def _load_configure_logging():
    source = (BACKEND_ROOT / "app.py").read_text(encoding="utf-8")
    marker = "def _configure_logging() -> None:"
    start = source.index(marker)
    end = source.index("\n\ndef create_app", start)
    module = types.ModuleType("app_logging_config")
    exec(
        "import logging\nfrom logging.config import dictConfig\n\n" + source[start:end],
        module.__dict__,
    )
    return module._configure_logging


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


def test_app_logging_config_uses_protocol_compliance_prefix() -> None:
    _configure_logging = _load_configure_logging()
    _configure_logging()

    protocol_logger = logging.getLogger("protocol_compliance")
    nested_logger = logging.getLogger("protocol_compliance._docker_runner.runner")

    assert protocol_logger.level == logging.DEBUG
    assert nested_logger.getEffectiveLevel() == logging.DEBUG
    assert logging.getLogger().getEffectiveLevel() == logging.INFO
    assert logging.getLogger("werkzeug").getEffectiveLevel() == logging.INFO


def test_job_stage_logger_emits_backend_and_frontend_logs(caplog: pytest.LogCaptureFixture) -> None:
    events: list[tuple[str, str, str]] = []
    logger = JobStageLogger(
        job_id="job-1",
        logger=logging.getLogger("protocol_compliance.test"),
        progress_callback=lambda job_id, stage, message: events.append((job_id, stage, message)),
    )

    with caplog.at_level(logging.DEBUG, logger="protocol_compliance.test"):
        with logger.state(stage="workspace", workspace="/tmp/work"):
            logger.debug("Preview %s", "input")
            logger.info("Prepared %s", "workspace", artifact="source.tar")
            logger.warning("Retrying %s", "operation")

    assert events == [
        ("job-1", "workspace", "Prepared workspace"),
        ("job-1", "workspace", "Retrying operation"),
    ]
    assert [record.levelno for record in caplog.records] == [
        logging.DEBUG,
        logging.INFO,
        logging.WARNING,
    ]
    assert cast(Any, caplog.records[1]).protocolguard_context == {
        "artifact": "source.tar",
        "workspace": "/tmp/work",
    }
    assert "[job job-1][workspace] Prepared workspace" in caplog.text


def test_job_stage_logger_preserves_traceback(caplog: pytest.LogCaptureFixture) -> None:
    logger = JobStageLogger(
        job_id="job-2",
        logger=logging.getLogger("protocol_compliance.traceback_test"),
    )

    with caplog.at_level(logging.ERROR, logger="protocol_compliance.traceback_test"):
        try:
            raise RuntimeError("boom")
        except RuntimeError:
            logger.log(logging.ERROR, "Workflow failed", stage="error", exc_info=True)

    assert len(caplog.records) == 1
    assert caplog.records[0].exc_info is not None
    assert "RuntimeError: boom" in caplog.text


def test_runner_log_step_preserves_frontend_event_and_backend_context(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(monkeypatch, tmp_path)
    runner = _runner(settings)
    job_paths = _job_paths(settings, "job-log-step")
    events: list[tuple[str, str, str]] = []
    runner._progress_callback = lambda job_id, stage, message: events.append((job_id, stage, message))

    with caplog.at_level(logging.INFO, logger="protocol_compliance._docker_runner.runner"):
        runner._log_step(
            job_paths,
            "inputs",
            "Copied rules file to project context: /tmp/rules.json",
            context={"destination": "/tmp/rules.json"},
        )

    assert events == [
        (
            "job-log-step",
            "inputs",
            "Copied rules file to project context: /tmp/rules.json",
        )
    ]
    assert cast(Any, caplog.records[0]).protocolguard_context == {"destination": "/tmp/rules.json"}


def test_runner_lifecycle_progress_order_is_preserved(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings(monkeypatch, tmp_path)
    runner = _runner(settings)
    job_paths = _job_paths(settings, "job-lifecycle")
    events: list[tuple[str, str, str]] = []
    runner._progress_callback = lambda job_id, stage, message: events.append((job_id, stage, message))
    job_logger = runner._logger(job_paths)
    built_image = "protocolguard-builder:job-lifecycle"

    with job_logger.state(stage="init"):
        job_logger.info("Starting ProtocolGuard static analysis job")
    with job_logger.state(stage="workspace"):
        job_logger.info("Staging workspace directories")
        job_logger.info("Workspace directories prepared")
    with job_logger.state(stage="cleanup", image=built_image):
        job_logger.info("Removing temporary builder image %s", built_image)

    assert events == [
        ("job-lifecycle", "init", "Starting ProtocolGuard static analysis job"),
        ("job-lifecycle", "workspace", "Staging workspace directories"),
        ("job-lifecycle", "workspace", "Workspace directories prepared"),
        (
            "job-lifecycle",
            "cleanup",
            "Removing temporary builder image protocolguard-builder:job-lifecycle",
        ),
    ]
