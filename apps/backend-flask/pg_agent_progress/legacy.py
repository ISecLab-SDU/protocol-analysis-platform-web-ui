"""Read compatibility for archived and older Claude progress producers.

This module has no SDK dependency. New provider adapters may emit the contract
in events.py directly; only legacy inputs require these mappings.
"""

from __future__ import annotations

from typing import Any

from .events import (
    METADATA_KEYS,
    decode_progress_event as decode_envelope,
    is_critical_event,
    sanitize_event_value,
    truncate,
)

_STAGE_ACTIVITIES = {
    "status": "status",
    "message": "message",
    "thinking": "thinking",
    "command": "command",
    "inspect": "inspect",
    "write": "write",
    "step": "plan",
    "tool": "tool",
    "observation": "tool_result",
    "result": "result",
    "hook": "status",
    "task": "status",
    "stream": "status",
}


def _repr_field(text: str, field: str) -> str:
    # Match the former UI recovery, including truncated quoted strings.
    marker = f"{field}="
    start = text.rfind(marker)
    if start < 0:
        return text
    start += len(marker)
    quote = text[start : start + 1]
    if quote not in {"'", '"'}:
        return text
    value = []
    index = start + 1
    while index < len(text):
        character = text[index]
        if character == quote:
            return "".join(value)
        if character == "\\":
            index += 1
            if index == len(text):
                break
            character = {"n": "\n", "r": "\r", "t": "\t"}.get(text[index], text[index])
        value.append(character)
        index += 1
    partial = "".join(value).rstrip()
    return partial if partial.endswith("...") else partial + "..."


def normalize_event(
    event: dict[str, Any], default_stage: str = "agent"
) -> dict[str, Any]:
    """Return neutral presentation fields; preserve API IDs and timestamps."""
    stage = str(event.get("stage") or default_stage)
    message = str(event.get("message") or event.get("type") or "progress")
    old = event.get("metadata")
    old = old if isinstance(old, dict) else {}
    legacy = {**event, **old}
    metadata = {
        key: value
        for key, value in old.items()
        if key in METADATA_KEYS and value is not None
    }
    activity = metadata.get("activity")
    if stage.startswith("claude-"):
        activity = activity or _STAGE_ACTIVITIES.get(stage[7:], "status")
        stage = {
            "builder-log": "builder",
            "instrumentation-log": "instrumentation",
        }.get(default_stage, default_stage)
    sdk_type = legacy.get("sdk_message_type")
    if not sdk_type and message.startswith(("ThinkingBlock(", "UserMessage(")):
        sdk_type = message.split("(", 1)[0]
    if sdk_type == "ResultMessage" or (event.get("type") == "result" and activity):
        activity = "result"
    elif sdk_type == "ThinkingBlock":
        activity = "thinking"
        if message.startswith("ThinkingBlock("):
            message = _repr_field(message, "thinking")
    elif sdk_type == "ToolResultBlock" or (
        sdk_type == "UserMessage" and "ToolResultBlock(" in message
    ):
        activity = "tool_result"
        metadata["is_error"] = (
            legacy.get("is_error") is True
            or "is_error=True" in message
            or "tool_use_result='Error:" in message
        )
        if message.startswith("UserMessage("):
            metadata["quiet"] = not metadata["is_error"]
            message = _repr_field(message, "content")
    if sdk_type == "UserMessage" and activity != "tool_result":
        metadata["quiet"] = True
    if activity:
        metadata["activity"] = activity
        for key in ("tool", "is_error", "status", "result", "model", "duration_ms"):
            if legacy.get(key) is not None:
                metadata[key] = legacy[key]
        if legacy.get("tool_use_id") is not None:
            metadata["tool_id"] = legacy["tool_use_id"]
        tool_input = legacy.get("tool_input") or {}
        if isinstance(tool_input, dict):
            primary = (
                tool_input.get("command")
                if activity == "command"
                else (tool_input.get("file_path") or tool_input.get("path"))
                if activity in {"inspect", "write"}
                else None
            )
            if primary:
                metadata["primary"] = truncate(primary)
            if tool_input.get("description"):
                metadata["description"] = truncate(tool_input["description"])
        if sdk_type == "AssistantMessage" and activity == "status":
            metadata["quiet"] = True
        usage = legacy.get("usage") or {}
        if isinstance(usage, dict):
            for source, target in (
                ("input_tokens", "input_tokens"),
                ("output_tokens", "output_tokens"),
                ("cache_read_input_tokens", "cache_read_tokens"),
            ):
                if isinstance(usage.get(source), (int, float)):
                    metadata[target] = usage[source]
        model_usage = legacy.get("model_usage") or {}
        if isinstance(model_usage, dict) and model_usage:
            model, metrics = next(iter(model_usage.items()))
            metadata.setdefault("model", model)
            if isinstance(metrics, dict) and isinstance(
                metrics.get("costUSD"), (int, float)
            ):
                metadata["cost_usd"] = metrics["costUSD"]
        if isinstance(legacy.get("total_cost_usd"), (int, float)):
            metadata["cost_usd"] = legacy["total_cost_usd"]
    event_type = event.get("type", "progress")
    if event_type not in {"progress", "error", "result"}:
        event_type = "progress"
    if event_type == "error":
        metadata["is_error"] = True
    result = {
        key: event[key]
        for key in ("id", "timestamp", "ts_ms", "truncated", "original_bytes")
        if key in event
    }
    result.update(stage=stage, message=message)
    if "type" in event:
        result["type"] = event_type
    if metadata:
        result["metadata"] = sanitize_event_value(metadata)
    return result


def decode_progress_event(line: str, default_stage: str) -> dict[str, Any] | None:
    payload = decode_envelope(line, default_stage)
    if payload is None:
        return None
    event = normalize_event(payload, default_stage)
    event["critical"] = is_critical_event(event)
    event.pop("type", None)
    return event


def decode_progress_line(line: str, default_stage: str) -> tuple[str, str] | None:
    event = decode_progress_event(line, default_stage)
    return (event["stage"], event["message"]) if event is not None else None
