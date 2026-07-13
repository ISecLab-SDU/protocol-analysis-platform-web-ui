"""Shared Claude Agent SDK event conversion helpers."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
)

PROGRESS_PREFIX = "PG_PROGRESS_JSON "
HIDDEN_THINKING_KEYS = frozenset({"thinking_tokens"})
HIDDEN_SYSTEM_SUBTYPES = frozenset({"thinking_tokens"})
FRONTEND_METADATA_KEYS = frozenset(
    {
        "duration_api_ms",
        "duration_ms",
        "errors",
        "is_error",
        "model",
        "model_usage",
        "result",
        "sdk_message_type",
        "session_id",
        "status",
        "tool",
        "tool_input",
        "tool_use_id",
        "usage",
    }
)
FRONTEND_TOOL_INPUT_KEYS = frozenset(
    {"command", "description", "file_path", "path", "pattern"}
)


def json_default(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)
    if isinstance(value, Path):
        return str(value)
    return repr(value)


def sanitize_event_value(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        value = dataclasses.asdict(value)
    if isinstance(value, dict):
        return {
            key: sanitize_event_value(item)
            for key, item in value.items()
            if str(key) not in HIDDEN_THINKING_KEYS
        }
    if isinstance(value, list):
        return [sanitize_event_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_event_value(item) for item in value)
    return value


def truncate(text: Any, limit: int = 1000) -> str:
    value = str(text)
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def summarize_tool_input(name: str, tool_input: dict[str, Any]) -> str:
    if name == "Bash":
        return truncate(tool_input.get("command") or tool_input)
    if name in {"Read", "Write", "Edit", "MultiEdit"}:
        path = tool_input.get("file_path") or tool_input.get("path")
        if path:
            return truncate(path)
    if name in {"Glob", "Grep"}:
        pattern = tool_input.get("pattern")
        path = tool_input.get("path")
        if pattern and path:
            return truncate(f"{pattern} in {path}")
        if pattern:
            return truncate(pattern)
    return truncate(json.dumps(tool_input, ensure_ascii=False, default=json_default))


def tool_stage(name: str) -> str:
    if name == "Bash":
        return "claude-command"
    if name in {"Read", "Glob", "Grep", "LS"}:
        return "claude-inspect"
    if name in {"Write", "Edit", "MultiEdit"}:
        return "claude-write"
    if name in {"TodoWrite"}:
        return "claude-step"
    return "claude-tool"


def message_to_dict(message: Any) -> dict[str, Any]:
    if dataclasses.is_dataclass(message) and not isinstance(message, type):
        return sanitize_event_value(dataclasses.asdict(message))
    return {"repr": repr(message)}


def is_hidden_system_message(message: Any) -> bool:
    subtype = getattr(message, "subtype", "")
    data = getattr(message, "data", {}) or {}
    return str(subtype) in HIDDEN_SYSTEM_SUBTYPES or str(data.get("subtype", "")) in HIDDEN_SYSTEM_SUBTYPES


def progress_events_from_message(
    message: Any,
    *,
    result_label: str = "Claude agent",
) -> list[dict[str, Any]]:
    if is_hidden_system_message(message):
        return []
    if isinstance(message, AssistantMessage):
        return _assistant_events(message)
    if isinstance(message, UserMessage):
        return _user_events(message)
    if isinstance(message, ResultMessage):
        return [_result_event(message, result_label=result_label)]
    if isinstance(message, StreamEvent):
        return [_stream_event(message)]
    if isinstance(message, SystemMessage):
        return [_system_event(message)]
    return [
        {
            "type": "sdk-message",
            "stage": "claude-message",
            "message": truncate(message),
            "sdk_message_type": type(message).__name__,
        }
    ]


def result_code_from_message(message: Any) -> int | None:
    if isinstance(message, ResultMessage):
        return 1 if message.is_error else 0
    return None


def encode_progress_event(event: dict[str, Any], *, ts_ms: int) -> str:
    payload = {
        "source": "claude-agent-sdk",
        "ts_ms": ts_ms,
        **sanitize_event_value(event),
    }
    return json.dumps(payload, ensure_ascii=False, default=json_default)


def decode_progress_line(line: str, default_stage: str) -> tuple[str, str] | None:
    event = decode_progress_event(line, default_stage)
    if event is None:
        return None
    return str(event["stage"]), str(event["message"])


def decode_progress_event(line: str, default_stage: str) -> dict[str, Any] | None:
    if not line.startswith(PROGRESS_PREFIX):
        return None
    raw_payload = line[len(PROGRESS_PREFIX):]
    try:
        payload = json.loads(raw_payload)
    except json.JSONDecodeError:
        return {"stage": "claude-status", "message": line[:500]}
    stage = str(payload.get("stage") or default_stage)
    message = payload.get("message")
    if not message:
        message = payload.get("type") or raw_payload
    metadata = {}
    for key, value in payload.items():
        if key not in FRONTEND_METADATA_KEYS or value is None:
            continue
        if key == "tool_input" and isinstance(value, dict):
            value = {
                input_key: input_value
                for input_key, input_value in value.items()
                if input_key in FRONTEND_TOOL_INPUT_KEYS
            }
        metadata[key] = sanitize_event_value(value)
    return {
        "stage": stage,
        "message": str(message),
        **({"metadata": metadata} if metadata else {}),
    }


def _assistant_events(message: AssistantMessage) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    if message.session_id:
        events.append(
            {
                "type": "sdk-message",
                "stage": "claude-status",
                "message": f"Assistant turn received from {message.model}",
                "sdk_message_type": "AssistantMessage",
                "session_id": message.session_id,
                "model": message.model,
            }
        )
    for block in message.content:
        if isinstance(block, TextBlock):
            text = block.text.strip()
            if text:
                events.append(
                    {
                        "type": "progress",
                        "stage": "claude-message",
                        "message": truncate(text),
                        "sdk_message_type": "TextBlock",
                    }
                )
        elif isinstance(block, ToolUseBlock):
            summary = summarize_tool_input(block.name, block.input)
            events.append(
                {
                    "type": "progress",
                    "stage": tool_stage(block.name),
                    "message": f"{block.name}: {summary}",
                    "sdk_message_type": "ToolUseBlock",
                    "tool": block.name,
                    "tool_use_id": block.id,
                    "tool_input": block.input,
                }
            )
        elif isinstance(block, ToolResultBlock):
            content = block.content
            if isinstance(content, list):
                content = json.dumps(content, ensure_ascii=False, default=json_default)
            events.append(
                {
                    "type": "progress",
                    "stage": "claude-observation",
                    "message": truncate(content or "<empty tool result>"),
                    "sdk_message_type": "ToolResultBlock",
                    "tool_use_id": block.tool_use_id,
                    "is_error": bool(block.is_error),
                }
            )
        else:
            events.append(
                {
                    "type": "sdk-message",
                    "stage": "claude-message",
                    "message": truncate(block),
                    "sdk_message_type": type(block).__name__,
                }
            )
    return events


def _user_events(message: UserMessage) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for block in message.content:
        if not isinstance(block, ToolResultBlock):
            continue
        content = block.content
        if isinstance(content, list):
            content = json.dumps(content, ensure_ascii=False, default=json_default)
        events.append(
            {
                "type": "progress",
                "stage": "claude-observation",
                "message": truncate(content or "<empty tool result>"),
                "sdk_message_type": "ToolResultBlock",
                "tool_use_id": block.tool_use_id,
                "is_error": bool(block.is_error),
            }
        )
    if events:
        return events
    return [
        {
            "type": "sdk-message",
            "stage": "claude-message",
            "message": truncate(message),
            "sdk_message_type": "UserMessage",
        }
    ]


def _system_event(message: SystemMessage) -> dict[str, Any]:
    data = getattr(message, "data", {}) or {}
    subtype = getattr(message, "subtype", type(message).__name__)
    stage = "claude-status"
    if subtype.startswith("hook_"):
        stage = "claude-hook"
    elif subtype.startswith("task_"):
        stage = "claude-task"
    hook_event = getattr(message, "hook_event_name", "") or data.get("hook_event_name")
    description = (
        getattr(message, "description", None)
        or data.get("description")
        or hook_event
        or subtype
    )
    return {
        "type": "sdk-message",
        "stage": stage,
        "message": truncate(description),
        "sdk_message_type": type(message).__name__,
        "subtype": subtype,
        "data": data,
    }


def _stream_event(message: StreamEvent) -> dict[str, Any]:
    event = message.event or {}
    event_type = event.get("type", "stream_event")
    return {
        "type": "sdk-message",
        "stage": "claude-stream",
        "message": truncate(event_type),
        "sdk_message_type": "StreamEvent",
        "session_id": message.session_id,
        "event": event,
    }


def _result_event(message: ResultMessage, *, result_label: str) -> dict[str, Any]:
    status = "failed" if message.is_error else "completed"
    details = []
    if message.stop_reason:
        details.append(f"stop={message.stop_reason}")
    if message.total_cost_usd is not None:
        details.append(f"cost=${message.total_cost_usd:.4f}")
    details.append(f"turns={message.num_turns}")
    return {
        "type": "result",
        "stage": "claude-status",
        "message": f"{result_label} {status} ({', '.join(details)})",
        "sdk_message_type": "ResultMessage",
        "status": status,
        "session_id": message.session_id,
        "duration_ms": message.duration_ms,
        "duration_api_ms": message.duration_api_ms,
        "usage": message.usage,
        "model_usage": message.model_usage,
        "errors": message.errors,
        "result": truncate(message.result or "", 2000),
    }
