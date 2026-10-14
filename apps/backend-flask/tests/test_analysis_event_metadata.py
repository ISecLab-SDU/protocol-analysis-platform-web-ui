from __future__ import annotations

import sqlite3
from pathlib import Path

from protocol_compliance.analysis import AnalysisProgressRegistry
from protocol_compliance.state_repository import AnalysisStateRepository


def test_analysis_event_metadata_round_trips_and_migrates_legacy_database(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "analysis-state.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE analysis_jobs (
                job_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                stage TEXT NOT NULL,
                message TEXT NOT NULL,
                workspace_path TEXT,
                output_path TEXT,
                config_path TEXT,
                logs_path TEXT,
                database_path TEXT,
                result_json TEXT,
                error_text TEXT,
                details_json TEXT,
                docker_logs_json TEXT,
                workspace_snapshots_json TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT
            );
            CREATE TABLE analysis_job_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                stage TEXT NOT NULL,
                message TEXT NOT NULL,
                FOREIGN KEY(job_id) REFERENCES analysis_jobs(job_id) ON DELETE CASCADE
            );
            """
        )

    repository = AnalysisStateRepository(database_path)
    repository.record_progress(
        job_id="job-claude",
        status="running",
        stage="claude-command",
        message="Bash: make",
        created_at="2026-07-13T10:00:00+00:00",
        updated_at="2026-07-13T10:00:00+00:00",
    )
    repository.add_event(
        job_id="job-claude",
        timestamp="2026-07-13T10:00:00+00:00",
        stage="claude-command",
        message="Bash: make",
        metadata={
            "sdk_message_type": "ToolUseBlock",
            "tool": "Bash",
            "tool_input": {"command": "make"},
        },
    )

    assert repository.fetch_events(job_id="job-claude") == [
        {
            "id": 1,
            "timestamp": "2026-07-13T10:00:00+00:00",
            "stage": "claude-command",
            "message": "Bash: make",
            "metadata": {
                "sdk_message_type": "ToolUseBlock",
                "tool": "Bash",
                "tool_input": {"command": "make"},
            },
        }
    ]

    with sqlite3.connect(database_path) as connection:
        indexes = {
            row[1]
            for row in connection.execute(
                "PRAGMA index_list(analysis_job_events)"
            ).fetchall()
        }
    assert "idx_analysis_job_events_job_id_id" in indexes


def test_debug_event_does_not_rewrite_analysis_job_state(tmp_path: Path) -> None:
    database_path = tmp_path / "analysis-state.sqlite3"
    registry = AnalysisProgressRegistry()
    registry._repository = AnalysisStateRepository(database_path)
    state = registry.create_job()
    registry.mark_running(state.job_id, "compile", "Starting compilation")

    registry.append_event(
        state.job_id,
        "claude-command",
        "Bash: make",
        metadata={"tool": "Bash", "tool_input": {"command": "make"}},
    )

    persisted = next(
        job
        for job in registry._repository.fetch_jobs()
        if job["job_id"] == state.job_id
    )
    events = registry._repository.fetch_events(job_id=state.job_id)
    assert persisted["stage"] == "compile"
    assert events[-1]["stage"] == "claude-command"


def test_agent_activity_preserves_live_and_persisted_workflow_state(
    tmp_path: Path,
) -> None:
    registry = AnalysisProgressRegistry()
    registry._repository = AnalysisStateRepository(tmp_path / "state.sqlite3")
    state = registry.create_job()
    registry.mark_running(state.job_id, "compile", "Starting compilation")
    registry.append_event(
        state.job_id,
        "builder",
        "Agent completed",
        metadata={"activity": "result", "status": "completed"},
    )
    snapshot = registry.snapshot(state.job_id)
    assert snapshot["stage"] == "compile"
    assert snapshot["status"] == "running"
    assert snapshot["events"][-1]["metadata"]["activity"] == "result"
    assert registry._repository.fetch_jobs()[0]["stage"] == "compile"


def test_legacy_analysis_events_are_normalized_on_api_read(tmp_path: Path) -> None:
    registry = AnalysisProgressRegistry()
    registry._repository = AnalysisStateRepository(tmp_path / "state.sqlite3")
    state = registry.create_job()
    registry._repository.add_event(
        job_id=state.job_id,
        timestamp="now",
        stage="claude-command",
        message="Bash: make",
        metadata={"tool": "Bash", "tool_input": {"command": "make"}},
    )
    event = registry.snapshot(state.job_id)["events"][-1]
    assert event["id"]
    assert event["stage"] == "builder"
    assert event["metadata"] == {
        "activity": "command",
        "tool": "Bash",
        "primary": "make",
    }


def test_legacy_read_does_not_rewrite_archive_storage(tmp_path: Path) -> None:
    registry = AnalysisProgressRegistry()
    registry._repository = AnalysisStateRepository(tmp_path / "state.sqlite3")
    state = registry.create_job()
    registry._repository.add_event(
        job_id=state.job_id,
        timestamp="now",
        stage="claude-thinking",
        message="Inspect target",
        metadata={"sdk_message_type": "ThinkingBlock"},
    )
    assert (
        registry.snapshot(state.job_id)["events"][-1]["metadata"]["activity"]
        == "thinking"
    )
    assert (
        registry._repository.fetch_events(job_id=state.job_id)[-1]["stage"]
        == "claude-thinking"
    )
