"""Shared Claude Agent SDK event conversion helpers."""

from __future__ import annotations

import dataclasses
import json
from typing import Any

from .events import json_default, sanitize_event_value, truncate
from .legacy import normalize_event

HIDDEN_SYSTEM_SUBTYPES = frozenset({"thinking_tokens"})
FRONTEND_TOOL_INPUT_KEYS = frozenset(
    {"command", "description", "file_path", "path", "pattern"}
)


def frontend_tool_input(tool_input: dict[str, Any]) -> dict[str, Any]:
    return {
        key: truncate(value)
        for key, value in tool_input.items()
        if key in FRONTEND_TOOL_INPUT_KEYS and value is not None
    }


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
    return (
        str(subtype) in HIDDEN_SYSTEM_SUBTYPES
        or str(data.get("subtype", "")) in HIDDEN_SYSTEM_SUBTYPES
    )


def _is_message(value: Any, name: str) -> bool:
    return any(base.__name__ == name for base in type(value).__mro__)


def _legacy_events_from_message(
    message: Any,
    *,
    result_label: str = "Agent",
) -> list[dict[str, Any]]:
    if is_hidden_system_message(message):
        return []
    if _is_message(message, "AssistantMessage"):
        return _assistant_events(message)
    if _is_message(message, "UserMessage"):
        return _user_events(message)
    if _is_message(message, "ResultMessage"):
        return [_result_event(message, result_label=result_label)]
    if _is_message(message, "StreamEvent"):
        return [_stream_event(message)]
    if _is_message(message, "SystemMessage"):
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
    if _is_message(message, "ResultMessage"):
        return 1 if message.is_error else 0
    return None


def _assistant_events(message: Any) -> list[dict[str, Any]]:
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
        if _is_message(block, "TextBlock"):
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
        elif _is_message(block, "ToolUseBlock"):
            summary = summarize_tool_input(block.name, frontend_tool_input(block.input))
            events.append(
                {
                    "type": "progress",
                    "stage": tool_stage(block.name),
                    "message": f"{block.name}: {summary}",
                    "sdk_message_type": "ToolUseBlock",
                    "tool": block.name,
                    "tool_use_id": block.id,
                    "tool_input": frontend_tool_input(block.input),
                }
            )
        elif _is_message(block, "ToolResultBlock"):
            content = block.content
            if type(content).__name__ == "list":
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
        elif type(block).__name__ == "ThinkingBlock":
            events.append(
                {
                    "type": "progress",
                    "stage": "claude-thinking",
                    "message": truncate(getattr(block, "thinking", "")),
                    "sdk_message_type": "ThinkingBlock",
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


def _user_events(message: Any) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for block in message.content:
        if not _is_message(block, "ToolResultBlock"):
            continue
        content = block.content
        if type(content).__name__ == "list":
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


def _system_event(message: Any) -> dict[str, Any]:
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


def _stream_event(message: Any) -> dict[str, Any]:
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


def _result_event(message: Any, *, result_label: str) -> dict[str, Any]:
    status = "failed" if message.is_error else "completed"
    details = []
    if getattr(message, "stop_reason", None):
        details.append(f"stop={getattr(message, 'stop_reason', None)}")
    if message.total_cost_usd is not None:
        details.append(f"cost=${message.total_cost_usd:.4f}")
    details.append(f"turns={message.num_turns}")
    return {
        "type": "result",
        "stage": "claude-status",
        "message": f"{result_label} {status} ({', '.join(details)})",
        "sdk_message_type": "ResultMessage",
        "status": status,
        "total_cost_usd": getattr(message, "total_cost_usd", None),
        "session_id": message.session_id,
        "duration_ms": message.duration_ms,
        "duration_api_ms": message.duration_api_ms,
        "usage": message.usage,
        "model_usage": getattr(message, "model_usage", None),
        "errors": getattr(message, "errors", None),
        "result": truncate(message.result or "", 2000),
    }


def progress_events_from_message(
    message: Any, *, stage: str = "agent", result_label: str = "Agent"
) -> list[dict[str, Any]]:
    """Translate Claude messages into the stable progress contract."""
    return [
        normalize_event(event, stage)
        for event in _legacy_events_from_message(message, result_label=result_label)
    ]
