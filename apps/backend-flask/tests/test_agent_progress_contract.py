from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from pg_agent_progress.claude import (
    message_to_dict,
    progress_events_from_message,
    result_code_from_message,
)
from pg_agent_progress.events import (
    MAX_PROGRESS_EVENT_BYTES,
    PROGRESS_PREFIX,
    encode_progress_event,
)
from pg_agent_progress.legacy import decode_progress_event, normalize_event


def sdk(message_type, **fields):
    return type(message_type, (), fields)()


@pytest.mark.parametrize("stage", ["instrumentation", "fuzz-config-build", "builder"])
@pytest.mark.parametrize(
    "name,activity,primary",
    [
        ("Bash", "command", "make"),
        ("Read", "inspect", "main.c"),
        ("Edit", "write", "main.c"),
        ("TodoWrite", "plan", None),
        ("custom", "tool", None),
    ],
)
def test_tool_normalization(stage, name, activity, primary):
    block = sdk(
        "ToolUseBlock",
        name=name,
        id="call-1",
        input={
            "command": "make",
            "file_path": "main.c",
            "description": "Build",
            "content": "private source",
        },
    )
    message = sdk("AssistantMessage", session_id=None, model="test", content=[block])
    (event,) = progress_events_from_message(message, stage=stage)
    assert event["stage"] == stage
    assert event["metadata"]["activity"] == activity
    assert event["metadata"]["tool_id"] == "call-1"
    assert event["metadata"].get("primary") == primary
    assert "private source" not in json.dumps(event)
    assert "sdk_message_type" not in event
    assert (
        decode_progress_event(
            PROGRESS_PREFIX + encode_progress_event(event, ts_ms=123), stage
        )["metadata"]
        == event["metadata"]
    )


@pytest.mark.parametrize("carrier", ["AssistantMessage", "UserMessage"])
@pytest.mark.parametrize("is_error", [False, True])
def test_tool_result_messages(carrier, is_error):
    message = sdk(
        carrier,
        session_id=None,
        model="test",
        content=[
            sdk(
                "ToolResultBlock",
                tool_use_id="call",
                content="tool output",
                is_error=is_error,
            )
        ],
    )
    (event,) = progress_events_from_message(message, stage="builder")
    assert event["message"] == "tool output"
    assert event["metadata"] == {
        "activity": "tool_result",
        "tool_id": "call",
        "is_error": is_error,
    }
    assert (
        decode_progress_event(
            PROGRESS_PREFIX + encode_progress_event(event, ts_ms=0), "builder"
        )["critical"]
        is is_error
    )


@pytest.mark.parametrize("error", [False, True])
def test_results_and_metrics(error):
    message = sdk(
        "ResultMessage",
        is_error=error,
        stop_reason="end_turn",
        total_cost_usd=0.25,
        num_turns=2,
        session_id="session",
        duration_ms=1234,
        duration_api_ms=1000,
        usage={"input_tokens": 12, "output_tokens": 8, "cache_read_input_tokens": 4},
        model_usage={"model": {"costUSD": 0.20}},
        errors=[],
        result="done",
    )
    (event,) = progress_events_from_message(message, stage="builder")
    assert result_code_from_message(message) == int(error)
    assert event["type"] == "result"
    assert event["metadata"] == {
        "activity": "result",
        "status": "failed" if error else "completed",
        "result": "done",
        "model": "model",
        "duration_ms": 1234,
        "cost_usd": 0.25,
        "input_tokens": 12,
        "output_tokens": 8,
        "cache_read_tokens": 4,
    }
    assert decode_progress_event(
        PROGRESS_PREFIX + encode_progress_event(event, ts_ms=0), "builder"
    )["critical"]


def test_text_thinking_and_unknown_blocks():
    message = sdk(
        "AssistantMessage",
        session_id=None,
        model="test",
        content=[
            sdk("TextBlock", text=" hello "),
            sdk("ThinkingBlock", thinking="Inspect project", signature="secret"),
            sdk("UnknownBlock"),
        ],
    )
    events = progress_events_from_message(message)
    assert [e["metadata"]["activity"] for e in events] == [
        "message",
        "thinking",
        "message",
    ]
    assert events[0]["message"] == "hello"
    assert events[1]["message"] == "Inspect project"
    assert "secret" not in json.dumps(events)


@pytest.mark.parametrize("subtype", ["init", "hook_started", "task_started"])
def test_system_messages(subtype):
    (event,) = progress_events_from_message(
        sdk("SystemMessage", subtype=subtype, data={"description": "ready"})
    )
    assert event["message"] == "ready"
    assert event["metadata"]["activity"] == "status"


def test_stream_unknown_and_hidden_messages():
    (event,) = progress_events_from_message(
        sdk("StreamEvent", event={"type": "delta"}, session_id="session")
    )
    assert event["metadata"]["activity"] == "status"
    assert (
        progress_events_from_message(
            sdk("SystemMessage", subtype="thinking_tokens", data={})
        )
        == []
    )
    assert (
        progress_events_from_message(sdk("UnknownMessage"))[0]["metadata"]["activity"]
        == "message"
    )
    assert result_code_from_message(sdk("UnknownMessage")) is None


@pytest.mark.parametrize("payload", ["{broken", "[]", "null", "42", '"text"'])
def test_malformed_progress_is_readable(payload):
    line = PROGRESS_PREFIX + payload
    assert decode_progress_event(line, "builder-log") == {
        "stage": "builder-log",
        "message": line,
        "critical": False,
    }
    assert decode_progress_event("ordinary stdout", "builder-log") is None


def test_unicode_limit_preserves_error_and_correlation():
    event = {
        "type": "error",
        "stage": "builder",
        "message": "编译输出" * 5000,
        "metadata": {
            "activity": "tool_result",
            "tool_id": "call-1",
            "is_error": True,
            "primary": "x" * 20000,
        },
        "traceback": "private traceback",
    }
    line = encode_progress_event(event, ts_ms=42)
    assert len(line.encode("utf-8")) <= MAX_PROGRESS_EVENT_BYTES
    payload = json.loads(line)
    assert payload["truncated"] is True
    assert payload["ts_ms"] == 42
    assert payload["metadata"] == {
        "activity": "tool_result",
        "tool_id": "call-1",
        "is_error": True,
    }
    assert "private traceback" not in line
    assert decode_progress_event(PROGRESS_PREFIX + line, "builder")["critical"] is True


def test_path_dataclass_and_recursive_sanitization():
    @dataclasses.dataclass
    class Diagnostic:
        path: Path
        data: dict

    raw = message_to_dict(
        Diagnostic(
            Path("main.c"),
            {"thinking_tokens": 10, "nested": [{"thinking_tokens": 1, "value": 2}]},
        )
    )
    assert json.loads(json.dumps(raw, default=str)) == {
        "path": "main.c",
        "data": {"nested": [{"value": 2}]},
    }


def test_legacy_repr_and_workflow_compatibility():
    event = normalize_event(
        {
            "id": 1,
            "timestamp": "now",
            "stage": "claude-message",
            "message": "ThinkingBlock(thinking='Inspect\\nthen build', signature='secret')",
            "metadata": {"sdk_message_type": "ThinkingBlock"},
        },
        "builder",
    )
    assert event == {
        "id": 1,
        "timestamp": "now",
        "stage": "builder",
        "message": "Inspect\nthen build",
        "metadata": {"activity": "thinking"},
    }
    failed = normalize_event(
        {
            "stage": "claude-message",
            "message": "UserMessage(content=[ToolResultBlock(content='failed', is_error=True)])",
        },
        "builder",
    )
    assert failed["metadata"]["is_error"] is True
    workflow = {"stage": "completed", "message": "Bundle ready"}
    assert normalize_event(workflow) == workflow


def test_system_subclasses_keep_hook_and_task_descriptions():
    system = type("SystemMessage", (), {})
    message = type(
        "HookEventMessage",
        (system,),
        {"subtype": "hook_started", "data": {}, "description": "Running build hook"},
    )()
    (event,) = progress_events_from_message(message, stage="builder")
    assert event["metadata"]["activity"] == "status"
    assert event["message"] == "Running build hook"


def test_runner_errors_and_terminal_results_remain_critical_when_truncated():
    for event_type, activity in (("error", "status"), ("result", "result")):
        event = {
            "type": event_type,
            "stage": "builder",
            "message": "失败" * 10000,
            "metadata": {"activity": activity},
        }
        normalized = decode_progress_event(
            PROGRESS_PREFIX + encode_progress_event(event, ts_ms=0), "builder"
        )
        assert normalized["critical"] is True
        assert normalized["metadata"]["activity"] == activity


def test_business_results_are_not_agent_results():
    event = normalize_event(
        {"type": "result", "stage": "fuzz-config-completed", "message": "Bundle ready"}
    )
    assert event == {
        "type": "result",
        "stage": "fuzz-config-completed",
        "message": "Bundle ready",
    }


@pytest.mark.parametrize(
    "text,expected",
    [
        ("ThinkingBlock(thinking='Check next command\\", "Check next command..."),
        ("ThinkingBlock(thinking='Inspect\\nthen build", "Inspect\nthen build..."),
    ],
)
def test_truncated_legacy_thinking(text, expected):
    event = normalize_event(
        {
            "stage": "claude-message",
            "message": text,
            "metadata": {"sdk_message_type": "ThinkingBlock"},
        },
        "builder",
    )
    assert event["message"] == expected
    assert event["metadata"]["activity"] == "thinking"
