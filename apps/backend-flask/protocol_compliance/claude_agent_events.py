"""Public Claude Agent SDK event helpers for ProtocolGuard workflows."""

from __future__ import annotations

from .claude_builder.claude_agent_events import (
    HIDDEN_SYSTEM_SUBTYPES,
    HIDDEN_THINKING_KEYS,
    PROGRESS_PREFIX,
    decode_progress_event,
    decode_progress_line,
    encode_progress_event,
    is_hidden_system_message,
    json_default,
    message_to_dict,
    progress_events_from_message,
    result_code_from_message,
    sanitize_event_value,
    summarize_tool_input,
    tool_stage,
    truncate,
)

__all__ = [
    "HIDDEN_SYSTEM_SUBTYPES",
    "HIDDEN_THINKING_KEYS",
    "PROGRESS_PREFIX",
    "decode_progress_event",
    "decode_progress_line",
    "encode_progress_event",
    "is_hidden_system_message",
    "json_default",
    "message_to_dict",
    "progress_events_from_message",
    "result_code_from_message",
    "sanitize_event_value",
    "summarize_tool_input",
    "tool_stage",
    "truncate",
]
