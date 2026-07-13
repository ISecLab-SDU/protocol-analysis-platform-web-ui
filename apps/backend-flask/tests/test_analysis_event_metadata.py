from __future__ import annotations

import sqlite3
from pathlib import Path

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
