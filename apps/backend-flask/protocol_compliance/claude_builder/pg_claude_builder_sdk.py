#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
import os
import shutil
import time
import traceback
from pathlib import Path
from typing import Any

from claude_agent_sdk import (
    ClaudeAgentOptions,
    query,
)

try:
    from protocol_compliance.claude_agent_events import (
        PROGRESS_PREFIX,
        encode_progress_event,
        is_hidden_system_message as _is_hidden_system_message,
        json_default as _json_default,
        message_to_dict as _message_to_dict,
        progress_events_from_message,
        result_code_from_message,
        truncate as _truncate,
    )
except ModuleNotFoundError:  # pragma: no cover - container-local script path
    from claude_agent_events import (
        PROGRESS_PREFIX,
        encode_progress_event,
        is_hidden_system_message as _is_hidden_system_message,
        json_default as _json_default,
        message_to_dict as _message_to_dict,
        progress_events_from_message,
        result_code_from_message,
        truncate as _truncate,
    )

WORKSPACE = Path(os.environ.get("PG_CLAUDE_WORKSPACE", "/workspace"))
PROMPT_PATH = WORKSPACE / "claude_builder_prompt.md"
EVENTS_PATH = WORKSPACE / "claude_builder_events.jsonl"
CLAUDE_CONFIG_DIR = Path(os.environ.get("CLAUDE_CONFIG_DIR", "/root/.claude"))
CLAUDE_SETTINGS_PATH = CLAUDE_CONFIG_DIR / "settings.json"
CLAUDE_CLI_PATH = os.environ.get("PG_CLAUDE_CLI_PATH") or shutil.which("claude") or "claude"


def _now_ms() -> int:
    return int(time.time() * 1000)


def _emit_progress_event(event: dict[str, Any]) -> None:
    line = encode_progress_event(event, ts_ms=_now_ms())
    print(f"{PROGRESS_PREFIX}{line}", flush=True)
    EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with EVENTS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


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


def _handle_message(message: Any) -> int | None:
    if _is_hidden_system_message(message):
        return None

    raw = _message_to_dict(message)
    with EVENTS_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"raw": raw}, ensure_ascii=False, default=_json_default) + "\n")
    for event in progress_events_from_message(message, result_label="Claude builder"):
        _emit_progress_event(event)
    return result_code_from_message(message)


async def _run() -> int:
    if not PROMPT_PATH.exists():
        _emit_progress_event(
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

    _emit_progress_event(
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
            _emit_progress_event(
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
        _emit_progress_event(
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
