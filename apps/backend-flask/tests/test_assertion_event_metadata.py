from __future__ import annotations

import sys
from pathlib import Path
from typing import cast

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from protocol_compliance.assertion import (  # noqa: E402
    AssertGenerationProgressRegistry,
    _decode_instrumentation_progress_line,
    _emit_progress_callback,
)


def test_assertion_event_metadata_round_trips_through_snapshot() -> None:
    registry = AssertGenerationProgressRegistry()
    state = registry.create_job()
    callback = registry.make_callback(state.job_id)

    callback(
        state.job_id,
        "claude-command",
        "Bash: make",
        {
            "sdk_message_type": "ToolUseBlock",
            "tool": "Bash",
            "tool_input": {"command": "make"},
        },
    )

    snapshot = registry.snapshot(state.job_id)
    assert snapshot is not None
    events = cast(list[dict[str, object]], snapshot["events"])
    last_event = events[-1]
    assert last_event == {
        "timestamp": last_event["timestamp"],
        "stage": "claude-command",
        "message": "Bash: make",
        "metadata": {
            "sdk_message_type": "ToolUseBlock",
            "tool": "Bash",
            "tool_input": {"command": "make"},
        },
    }


def test_instrumentation_progress_line_decodes_claude_sdk_event() -> None:
    event = _decode_instrumentation_progress_line(
        'PG_PROGRESS_JSON {"stage":"claude-write","message":"Edit: /workspace/main.c",'
        '"sdk_message_type":"ToolUseBlock","tool":"Edit",'
        '"tool_input":{"file_path":"/workspace/main.c"}}'
    )

    assert event == {
        "stage": "claude-write",
        "message": "Edit: /workspace/main.c",
        "critical": False,
        "metadata": {
            "sdk_message_type": "ToolUseBlock",
            "tool": "Edit",
            "tool_input": {"file_path": "/workspace/main.c"},
        },
    }


def test_metadata_emission_keeps_three_argument_callback_compatible() -> None:
    received: list[tuple[str, str, str]] = []

    def callback(job_id: str, stage: str, message: str) -> None:
        received.append((job_id, stage, message))

    _emit_progress_callback(
        callback,
        "job-1",
        "claude-command",
        "Bash: make",
        {"tool": "Bash"},
    )

    assert received == [("job-1", "claude-command", "Bash: make")]
