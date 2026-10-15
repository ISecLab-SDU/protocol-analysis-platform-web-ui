"""Pi subprocess transport shared by Docker workflows; full audit precedes UI bounds."""
from __future__ import annotations

import json
import os
import queue
import signal
import subprocess
import threading
import time
import traceback
from pathlib import Path
from typing import Callable, Any


def redact(text: str) -> str:
    for name, secret in os.environ.items():
        if secret and any(part in name.upper() for part in ("API_KEY", "AUTH_TOKEN", "ACCESS_TOKEN", "PASSWORD", "SECRET")):
            text = text.replace(secret, "[REDACTED]")
    return text


def run_pi_task(*, cwd: str, prompt: str, workflow: str,
                emit: Callable[[dict[str, Any]], Any], audit_path: Path,
                task_num: int | None = None) -> int:
    process = None
    readers = []
    def publish(event):
        def sanitize(value):
            if isinstance(value, str):
                return redact(value)
            if isinstance(value, dict):
                return {key: sanitize(item) for key, item in value.items()}
            if isinstance(value, list):
                return [sanitize(item) for item in value]
            return value
        event = sanitize(event)
        try:
            audit_path.parent.mkdir(parents=True, exist_ok=True)
            with audit_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")
        except OSError as exc:
            emit({"type": "error", "stage": workflow, "message": redact(f"Pi audit write failed at {audit_path}: {exc}"), "metadata": {"activity": "status", "is_error": True}})
        emit(event)
    try:
        runner = Path(os.environ.get("PG_PI_RUNNER", "/opt/protocolguard/pi-agent/runner.mjs"))
        if not runner.is_file():
            raise FileNotFoundError(f"Pi worker unavailable at {runner}; rebuild the Pi-enabled image")
        timeout = int(os.environ.get("PG_PI_TIMEOUT_SECONDS", "1800"))
        if timeout <= 0:
            raise ValueError("PG_PI_TIMEOUT_SECONDS must be positive")
        process = subprocess.Popen(["node", str(runner)], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            cwd=cwd, start_new_session=True)
        messages = queue.Queue()
        def read_stream(stream, channel):
            try:
                for line in stream:
                    messages.put((channel, line))
            finally:
                messages.put((channel, None))
        for stream, channel in [(process.stdout, "stdout"), (process.stderr, "stderr")]:
            reader = threading.Thread(target=read_stream, args=(stream, channel), daemon=True)
            reader.start()
            readers.append(reader)
        process.stdin.write(json.dumps({"cwd": cwd, "prompt": prompt, "workflow": workflow, "task_num": task_num}))
        process.stdin.close()
        deadline = time.monotonic() + timeout + 10
        ended = set()
        completed = False
        failure = "No completed Pi result received"
        while len(ended) < 2:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"Pi {workflow} exceeded {timeout}s timeout (pid {process.pid})")
            try:
                channel, line = messages.get(timeout=min(remaining, 1))
            except queue.Empty:
                continue
            if line is None:
                ended.add(channel)
                continue
            if channel == "stderr":
                publish({"type": "progress", "stage": workflow, "message": line.rstrip(), "metadata": {"activity": "status"}})
                continue
            try:
                event = json.loads(line)
            except ValueError as exc:
                raise ValueError(f"Invalid Pi JSON stream: {line.rstrip()}") from exc
            if not isinstance(event, dict) or event.get("stage") != workflow:
                raise ValueError(f"Invalid Pi {workflow} event: {event!r}")
            publish(event)
            metadata = event.get("metadata", {})
            if metadata.get("activity") == "result":
                completed = metadata.get("status") == "completed"
            if event.get("type") == "error" or metadata.get("status") == "failed":
                failure = event.get("message") or failure
        code = process.wait(timeout=max(0.1, deadline-time.monotonic()))
        if code != 0 or not completed:
            raise RuntimeError(f"Pi {workflow} failed (exit code {code}, completed result {completed}): {failure}")
        return 0
    except Exception:
        publish({"type": "error", "stage": workflow, "message": traceback.format_exc(), "metadata": {"activity": "status", "is_error": True}})
        return 1
    finally:
        if process is not None:
            # Kill the whole session, including tool children surviving the Node worker.
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
            for reader in readers:
                reader.join(timeout=1)
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream:
                    stream.close()
