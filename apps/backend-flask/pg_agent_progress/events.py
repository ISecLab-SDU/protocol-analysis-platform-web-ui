"""SDK-free progress envelope, JSON transport, and presentation metadata."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path
from typing import Any

PROGRESS_PREFIX = "PG_PROGRESS_JSON "
MAX_PROGRESS_EVENT_BYTES = 3500
HIDDEN_THINKING_KEYS = frozenset({"thinking_tokens"})
ACTIVITIES = frozenset(
    {
        "status",
        "message",
        "thinking",
        "command",
        "inspect",
        "write",
        "plan",
        "tool",
        "tool_result",
        "result",
    }
)
METADATA_KEYS = frozenset(
    {
        "activity",
        "tool",
        "tool_id",
        "primary",
        "description",
        "is_error",
        "status",
        "result",
        "model",
        "duration_ms",
        "cost_usd",
        "input_tokens",
        "output_tokens",
        "cache_read_tokens",
        "quiet",
    }
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
    if isinstance(value, (list, tuple)):
        return [sanitize_event_value(item) for item in value]
    return value


def truncate(text: Any, limit: int = 1000) -> str:
    value = str(text)
    return value if len(value) <= limit else value[: limit - 3] + "..."


def is_agent_event(metadata: Any) -> bool:
    return isinstance(metadata, dict) and metadata.get("activity") in ACTIVITIES


def is_critical_event(event: dict[str, Any]) -> bool:
    metadata = event.get("metadata") or {}
    return (
        event.get("type") in {"error", "result"}
        or metadata.get("activity") == "result"
        or metadata.get("is_error") is True
        or metadata.get("status") == "failed"
    )


def encode_progress_event(event: dict[str, Any], *, ts_ms: int) -> str:
    """Bound the transport by UTF-8 bytes, retaining essential event semantics."""
    metadata = event.get("metadata") or {}
    payload = {
        "ts_ms": ts_ms,
        "type": event.get("type")
        if event.get("type") in {"progress", "error", "result"}
        else "progress",
        "stage": truncate(event.get("stage") or "progress", 100),
        "message": str(event.get("message") or ""),
    }
    if isinstance(metadata, dict) and metadata:
        payload["metadata"] = sanitize_event_value(
            {
                key: value
                for key, value in metadata.items()
                if key in METADATA_KEYS and value is not None
            }
        )
    encoded = json.dumps(payload, ensure_ascii=False, default=json_default)
    size = len(encoded.encode("utf-8"))
    if size <= MAX_PROGRESS_EVENT_BYTES:
        return encoded
    payload["truncated"] = True
    payload["original_bytes"] = size
    if "metadata" in payload:
        payload["metadata"] = {
            key: value
            for key, value in payload["metadata"].items()
            if key in {"activity", "is_error", "status", "tool_id", "quiet"}
        }
        # IDs from a runtime must not defeat the transport bound.
        for key in ("tool_id", "status"):
            if key in payload["metadata"]:
                payload["metadata"][key] = truncate(payload["metadata"][key], 200)
    message = payload["message"]
    low, high = 0, len(message)
    while low < high:
        midpoint = (low + high + 1) // 2
        payload["message"] = message[:midpoint]
        if (
            len(
                json.dumps(payload, ensure_ascii=False, default=json_default).encode(
                    "utf-8"
                )
            )
            <= MAX_PROGRESS_EVENT_BYTES
        ):
            low = midpoint
        else:
            high = midpoint - 1
    payload["message"] = message[:low]
    return json.dumps(payload, ensure_ascii=False, default=json_default)


def decode_progress_event(line: str, default_stage: str) -> dict[str, Any] | None:
    """Decode current events without importing an agent SDK."""
    if not line.startswith(PROGRESS_PREFIX):
        return None
    try:
        payload = json.loads(line[len(PROGRESS_PREFIX) :])
        if not isinstance(payload, dict):
            raise ValueError("Expected a progress object")
    except (ValueError, TypeError):
        return {"stage": default_stage, "message": line[:500]}
    return payload
