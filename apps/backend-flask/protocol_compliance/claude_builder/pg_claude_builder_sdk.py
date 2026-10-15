#!/usr/bin/env python3
from __future__ import annotations

import errno
import os
import select
import sys
import time
import traceback
from pathlib import Path
from typing import Any

from pg_agent_progress.pi import run_pi_task, redact

from pg_agent_progress.events import (
    PROGRESS_PREFIX,
    encode_progress_event,
    is_critical_event,
)
from pg_agent_progress.legacy import normalize_event

WORKSPACE = Path(os.environ.get("PG_CLAUDE_WORKSPACE", "/workspace"))
PROMPT_PATH = WORKSPACE / "claude_builder_prompt.md"
EVENTS_PATH = WORKSPACE / "claude_builder_events.jsonl"


def _now_ms() -> int:
    return int(time.time() * 1000)


def _append_audit_line(line: str) -> None:
    try:
        EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with EVENTS_PATH.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    except OSError:
        # Audit output must never determine whether the build succeeds.
        return


def _write_progress_line(line: str, *, critical: bool) -> bool:
    payload = f"{PROGRESS_PREFIX}{line}\n".encode("utf-8", errors="replace")
    deadline = time.monotonic() + 0.25 if critical else time.monotonic()
    offset = 0
    while offset < len(payload):
        try:
            written = os.write(sys.stdout.fileno(), payload[offset:])
            if written <= 0:
                return False
            offset += written
        except BlockingIOError:
            if time.monotonic() >= deadline:
                return False
            select.select([], [sys.stdout.fileno()], [], max(0.0, deadline - time.monotonic()))
        except OSError as exc:
            if exc.errno not in {errno.EAGAIN, errno.EWOULDBLOCK}:
                return False
            if time.monotonic() >= deadline:
                return False
    return True


def _emit_progress_event(event: dict[str, Any]) -> bool:
    event = normalize_event(event, "builder")
    line = encode_progress_event(event, ts_ms=_now_ms())
    _append_audit_line(line)
    critical = (
        is_critical_event(event)
        or event.get("metadata", {}).get("activity") == "status"
    )
    return _write_progress_line(line, critical=critical)


def _run() -> int:
    return run_pi_task(cwd=str(WORKSPACE), prompt=PROMPT_PATH.read_text(encoding="utf-8"),
        workflow="builder", emit=_emit_progress_event,
        audit_path=EVENTS_PATH.with_suffix(".raw.jsonl"))


def main() -> int:
    try:
        return _run()
    except Exception as exc:
        _emit_progress_event(
            {
                "type": "error",
                "stage": "claude-status",
                "message": redact(traceback.format_exc()),
            }
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
