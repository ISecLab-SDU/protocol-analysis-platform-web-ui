#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import dataclasses
import json
import os
import shutil
import time
import traceback
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    StreamEvent,
    SystemMessage,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
    query,
)

PROGRESS_PREFIX = "PG_PROGRESS_JSON "
WORKSPACE = Path(os.environ.get("PG_CLAUDE_WORKSPACE", "/workspace"))
PROMPT_PATH = WORKSPACE / "claude_builder_prompt.md"
EVENTS_PATH = WORKSPACE / "claude_builder_events.jsonl"
CLAUDE_CONFIG_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", "/root/.claude"))
CLAUDE_SETTINGS_PATH = CLAUDE_CONFIG_DIR / "settings.json"
CLAUDE_CLI_PATH = os.environ.get("PG_CLAUDE_CLI_PATH") or shutil.which("claude") or "claude"


def _json_default(value: Any) -> Any:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return dataclasses.asdict(value)
    if isinstance(value, Path):
        return str(value)
    return repr(value)


def _now_ms() -> int:
    return int(time.time() * 1000)


def _emit(event: dict[str, Any]) -> None:
    payload = {
        "source": "claude-agent-sdk",
        "ts_ms": _now_ms(),
        **event,
    }
    line = json.dumps(payload, ensure_ascii=False, default=_json_default)
    print(f"{PROGRESS_PREFIX}{line}", flush=True)
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def _truncate(text: Any, limit: int = 1000) -> str:
    value = str(text)
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def _summarize_tool_input(name: str, tool_input: dict[str, Any]) -> str:
    if name == "Bash":
        return _truncate(tool_input.get("command") or tool_input)
    if name in {"Read", "Write", "Edit", "MultiEdit"}:
        path = tool_input.get("file_path") or tool_input.get("path")
        if path:
            return _truncate(path)
    if name in {"Glob", "Grep"}:
        pattern = tool_input.get("pattern")
        path = tool_input.get("path")
        if pattern and path:
            return _truncate(f"{pattern} in {path}")
        if pattern:
            return _truncate(pattern)
    return _truncate(json.dumps(tool_input, ensure_ascii=False, default=_json_default))


def _tool_stage(name: str) -> str:
    if name == "Bash":
        return "claude-command"
    if name in {"Read", "Glob", "Grep", "LS"}:
        return "claude-inspect"
    if name in {"Write", "Edit", "MultiEdit"}:
        return "claude-write"
    if name in {"TodoWrite"}:
        return "claude-step"
    return "claude-tool"


def _message_to_dict(message: Any) -> dict[str, Any]:
    if dataclasses.is_dataclass(message) and not isinstance(message, type):
        return dataclasses.asdict(message)
    return {"repr": repr(message)}


def _handle_assistant(message: AssistantMessage) -> None:
    if message.session_id:
        _emit(
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
                _emit(
                    {
                        "type": "progress",
                        "stage": "claude-message",
                        "message": _truncate(text),
                        "sdk_message_type": "TextBlock",
                    }
                )
        elif isinstance(block, ToolUseBlock):
            summary = _summarize_tool_input(block.name, block.input)
            _emit(
                {
                    "type": "progress",
                    "stage": _tool_stage(block.name),
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
                content = json.dumps(content, ensure_ascii=False, default=_json_default)
            _emit(
                {
                    "type": "progress",
                    "stage": "claude-observation",
                    "message": _truncate(content or "<empty tool result>"),
                    "sdk_message_type": "ToolResultBlock",
                    "tool_use_id": block.tool_use_id,
                    "is_error": bool(block.is_error),
                }
            )
        else:
            _emit(
                {
                    "type": "sdk-message",
                    "stage": "claude-message",
                    "message": _truncate(block),
                    "sdk_message_type": type(block).__name__,
                }
            )


def _handle_system(message: SystemMessage) -> None:
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
    _emit(
        {
            "type": "sdk-message",
            "stage": stage,
            "message": _truncate(description),
            "sdk_message_type": type(message).__name__,
            "subtype": subtype,
            "data": data,
        }
    )


def _handle_stream_event(message: StreamEvent) -> None:
    event = message.event or {}
    event_type = event.get("type", "stream_event")
    _emit(
        {
            "type": "sdk-message",
            "stage": "claude-stream",
            "message": _truncate(event_type),
            "sdk_message_type": "StreamEvent",
            "session_id": message.session_id,
            "event": event,
        }
    )


def _build_claude_environment() -> dict[str, str]:
    env = {
        key: value
        for key, value in os.environ.items()
        if key.startswith("ANTHROPIC_")
        or key.startswith("CLAUDE_")
        or key in {"IS_SANDBOX", "PG_HOST_UID", "PG_HOST_GID"}
    }
    env["CLAUDE_AGENT_SDK_CLIENT_APP"] = "protocolguard-claude-builder"
    env.setdefault("CLAUDE_CONFIG_DIR", str(CLAUDE_CONFIG_DIR))
    env.setdefault("CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC", "1")
    return env


def _handle_result(message: ResultMessage) -> int:
    status = "failed" if message.is_error else "completed"
    details = []
    if message.stop_reason:
        details.append(f"stop={message.stop_reason}")
    if message.total_cost_usd is not None:
        details.append(f"cost=${message.total_cost_usd:.4f}")
    details.append(f"turns={message.num_turns}")
    _emit(
        {
            "type": "result",
            "stage": "claude-status",
            "message": f"Claude builder {status} ({', '.join(details)})",
            "sdk_message_type": "ResultMessage",
            "status": status,
            "session_id": message.session_id,
            "duration_ms": message.duration_ms,
            "duration_api_ms": message.duration_api_ms,
            "usage": message.usage,
            "model_usage": message.model_usage,
            "errors": message.errors,
            "result": _truncate(message.result or "", 2000),
        }
    )
    return 1 if message.is_error else 0


def _handle_message(message: Any) -> int | None:
    raw = _message_to_dict(message)
    with EVENTS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"raw": raw}, ensure_ascii=False, default=_json_default) + "\n")
    if isinstance(message, AssistantMessage):
        _handle_assistant(message)
        return None
    if isinstance(message, ResultMessage):
        return _handle_result(message)
    if isinstance(message, StreamEvent):
        _handle_stream_event(message)
        return None
    if isinstance(message, SystemMessage):
        _handle_system(message)
        return None
    _emit(
        {
            "type": "sdk-message",
            "stage": "claude-message",
            "message": _truncate(message),
            "sdk_message_type": type(message).__name__,
        }
    )
    return None


async def _run() -> int:
    if not PROMPT_PATH.exists():
        _emit(
            {
                "type": "error",
                "stage": "claude-status",
                "message": f"Prompt file not found: {PROMPT_PATH}",
            }
        )
        return 2

    prompt = PROMPT_PATH.read_text(encoding="utf-8")
    env = _build_claude_environment()

    options = ClaudeAgentOptions(
        cwd=WORKSPACE,
        permission_mode="bypassPermissions",
        tools={"type": "preset", "preset": "claude_code"},
        allowed_tools=[
            "Bash",
            "Read",
            "Write",
            "Edit",
            "MultiEdit",
            "Glob",
            "Grep",
            "LS",
            "TodoWrite",
        ],
        include_hook_events=True,
        include_partial_messages=False,
        max_turns=int(os.environ.get("PG_CLAUDE_MAX_TURNS", "40")),
        model=os.environ.get("PG_CLAUDE_MODEL") or os.environ.get("ANTHROPIC_MODEL"),
        cli_path=CLAUDE_CLI_PATH,
        settings=str(CLAUDE_SETTINGS_PATH) if CLAUDE_SETTINGS_PATH.exists() else None,
        env=env,
    )

    _emit(
        {
            "type": "progress",
            "stage": "claude-status",
            "message": "Starting Claude Agent SDK builder typed stream",
            "sdk_message_type": "runner",
        }
    )

    result_code = 1
    saw_result = False
    try:
        async for message in query(prompt=prompt, options=options):
            maybe_code = _handle_message(message)
            if maybe_code is not None:
                result_code = maybe_code
                saw_result = True
    except Exception as exc:
        if saw_result and result_code != 0:
            _emit(
                {
                    "type": "error",
                    "stage": "claude-status",
                    "message": _truncate(exc),
                    "sdk_message_type": "runner",
                }
            )
            return result_code
        raise
    return result_code


def main() -> int:
    try:
        return asyncio.run(_run())
    except Exception as exc:
        _emit(
            {
                "type": "error",
                "stage": "claude-status",
                "message": _truncate(exc),
                "traceback": traceback.format_exc(),
            }
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
