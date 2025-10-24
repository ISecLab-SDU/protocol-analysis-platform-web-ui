"""Assertion generation helpers and Docker orchestration glue."""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Callable, Dict, List, Optional, Tuple

from .docker_runner import (
    ProtocolGuardDockerError,
    ProtocolGuardDockerRunner,
    ProtocolGuardDockerSettings,
    ProtocolGuardExecutionError,
    ProtocolGuardNotAvailableError,
)

LOGGER = logging.getLogger(__name__)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


AssertGenerationJobStatus = str  # Literal['queued', 'running', 'completed', 'failed']


@dataclass
class AssertGenerationProgressEvent:
    timestamp: str
    stage: str
    message: str


@dataclass
class AssertGenerationProgressState:
    job_id: str
    status: AssertGenerationJobStatus
    stage: str
    message: str
    created_at: str
    updated_at: str
    events: List[AssertGenerationProgressEvent] = field(default_factory=list)
    result: Optional[Dict[str, object]] = None
    error: Optional[str] = None
    details: Optional[Dict[str, object]] = None


class AssertGenerationError(RuntimeError):
    """Base error for assertion generation orchestration."""


class AssertGenerationNotReadyError(AssertGenerationError):
    """Raised when Docker integration is disabled or unavailable."""


class AssertGenerationExecutionError(AssertGenerationError):
    """Raised when the assertion generation container fails."""

    def __init__(
        self,
        message: str,
        *,
        logs: Optional[List[str]] = None,
        details: Optional[Dict[str, object]] = None,
    ) -> None:
        super().__init__(message)
        self.logs = logs or []
        self.details = details or {}


class AssertGenerationProgressRegistry:
    """Track live progress for assertion generation jobs."""

    def __init__(self) -> None:
        self._states: Dict[str, AssertGenerationProgressState] = {}
        self._lock = threading.Lock()

    def create_job(self) -> AssertGenerationProgressState:
        job_id = str(uuid.uuid4())
        now = _now_iso()
        state = AssertGenerationProgressState(
            job_id=job_id,
            status="queued",
            stage="queued",
            message="Job queued",
            created_at=now,
            updated_at=now,
        )
        state.events.append(
            AssertGenerationProgressEvent(timestamp=now, stage="queued", message="Job queued")
        )
        with self._lock:
            self._states[job_id] = state
        return state

    def mark_running(self, job_id: str, stage: str, message: str) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            state.status = "running"
            self._append_event(state, stage, message)

    def append_event(self, job_id: str, stage: str, message: str) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            self._append_event(state, stage, message)

    def complete(self, job_id: str, result: Dict[str, object]) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            state.status = "completed"
            state.result = result
            self._append_event(state, "completed", "Assertion generation completed successfully")

    def fail(
        self,
        job_id: str,
        stage: str,
        message: str,
        *,
        error: Optional[str] = None,
        details: Optional[Dict[str, object]] = None,
    ) -> None:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return
            state.status = "failed"
            state.error = error or message
            state.details = details
            self._append_event(state, stage, message)

    def snapshot(self, job_id: str) -> Optional[Dict[str, object]]:
        with self._lock:
            state = self._states.get(job_id)
            if not state:
                return None
            state_copy = AssertGenerationProgressState(
                job_id=state.job_id,
                status=state.status,
                stage=state.stage,
                message=state.message,
                created_at=state.created_at,
                updated_at=state.updated_at,
                events=list(state.events),
                result=state.result,
                error=state.error,
                details=state.details.copy() if state.details else None,
            )

        return {
            "jobId": state_copy.job_id,
            "status": state_copy.status,
            "stage": state_copy.stage,
            "message": state_copy.message,
            "createdAt": state_copy.created_at,
            "updatedAt": state_copy.updated_at,
            "events": [
                {"timestamp": event.timestamp, "stage": event.stage, "message": event.message}
                for event in state_copy.events
            ],
            "result": state_copy.result,
            "error": state_copy.error,
            "details": state_copy.details,
        }

    def make_callback(self, job_id: str) -> Callable[[str, str, str], None]:
        def callback(_job_id: str, stage: str, message: str) -> None:
            target_id = job_id or _job_id
            safe_stage = stage or "progress"
            safe_message = message or ""
            self.append_event(target_id, safe_stage, safe_message)

        return callback

    def _append_event(
        self,
        state: AssertGenerationProgressState,
        stage: str,
        message: str,
    ) -> None:
        timestamp = _now_iso()
        state.stage = stage or state.stage
        state.message = message or state.message
        state.updated_at = timestamp
        state.events.append(
            AssertGenerationProgressEvent(timestamp=timestamp, stage=stage or state.stage, message=message)
        )


PROGRESS_REGISTRY = AssertGenerationProgressRegistry()


@lru_cache(maxsize=1)
def _docker_settings() -> ProtocolGuardDockerSettings:
    return ProtocolGuardDockerSettings.from_env()


def run_assert_generation(
    *,
    code_stream: BinaryIO,
    code_file_name: str,
    database_stream: BinaryIO,
    database_file_name: str,
    build_instructions: Optional[str],
    notes: Optional[str],
    job_id: Optional[str] = None,
    progress_callback: Optional[Callable[[str, str, str], None]] = None,
) -> Dict[str, object]:
    """Dispatch assertion generation via Docker."""

    job_identifier = job_id or str(uuid.uuid4())
    settings = _docker_settings()
    if not settings.enabled:
        raise AssertGenerationNotReadyError("ProtocolGuard Docker integration is disabled")

    try:
        runner = ProtocolGuardDockerRunner(settings)
    except ProtocolGuardNotAvailableError as exc:
        raise AssertGenerationNotReadyError(str(exc)) from exc

    try:
        return runner.run_assert_generation(
            code_stream=code_stream,
            code_filename=code_file_name,
            database_stream=database_stream,
            database_filename=database_file_name,
            build_instructions=build_instructions,
            notes=notes,
            job_id=job_identifier,
            progress_callback=progress_callback,
        )
    except ProtocolGuardExecutionError as exc:
        details: Dict[str, object] = {
            "image": getattr(exc, "image", None),
            "status": getattr(exc, "status", None),
        }
        if exc.log_excerpt:
            details["logExcerpt"] = exc.log_excerpt
        raise AssertGenerationExecutionError(
            str(exc),
            logs=list(getattr(exc, "logs", []) or []),
            details=details,
        ) from exc
    except ProtocolGuardDockerError as exc:
        raise AssertGenerationError(str(exc)) from exc


def submit_assert_generation_job(
    *,
    code_payload: Tuple[str, bytes],
    database_payload: Tuple[str, bytes],
    build_instructions: Optional[str],
    notes: Optional[str],
) -> Dict[str, object]:
    """Launch assertion generation asynchronously and return initial snapshot."""

    state = PROGRESS_REGISTRY.create_job()
    job_id = state.job_id

    def _run_job() -> None:
        PROGRESS_REGISTRY.mark_running(job_id, "init", "Preparing assertion generation inputs")
        progress_callback = PROGRESS_REGISTRY.make_callback(job_id)
        progress_callback(job_id, "inputs", "Persisting uploaded artefacts")

        try:
            code_name, code_bytes = code_payload
            database_name, database_bytes = database_payload

            result = run_assert_generation(
                code_stream=BytesIO(code_bytes),
                code_file_name=code_name,
                database_stream=BytesIO(database_bytes),
                database_file_name=database_name,
                build_instructions=build_instructions,
                notes=notes,
                job_id=job_id,
                progress_callback=progress_callback,
            )
            PROGRESS_REGISTRY.complete(job_id, result)
        except AssertGenerationExecutionError as exc:
            details = exc.details.copy()
            if exc.logs:
                details["logs"] = list(exc.logs)
            PROGRESS_REGISTRY.fail(
                job_id,
                "error",
                "Assertion generation execution failed",
                error=str(exc),
                details=details or None,
            )
        except AssertGenerationNotReadyError as exc:
            PROGRESS_REGISTRY.fail(
                job_id,
                "error",
                "Assertion generation backend is not ready",
                error=str(exc),
            )
        except AssertGenerationError as exc:
            PROGRESS_REGISTRY.fail(
                job_id,
                "error",
                "Assertion generation service error",
                error=str(exc),
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            LOGGER.exception("Assertion generation job %s encountered an unexpected error", job_id)
            PROGRESS_REGISTRY.fail(
                job_id,
                "error",
                "Unexpected assertion generation failure",
                error=str(exc),
            )

    worker = threading.Thread(target=_run_job, name=f"assert-generation-{job_id[:8]}", daemon=True)
    worker.start()
    snapshot = PROGRESS_REGISTRY.snapshot(job_id)
    assert snapshot is not None
    return snapshot


def get_assert_generation_job(job_id: str) -> Optional[Dict[str, object]]:
    return PROGRESS_REGISTRY.snapshot(job_id)


def get_assert_generation_result(job_id: str) -> Optional[Dict[str, object]]:
    snapshot = PROGRESS_REGISTRY.snapshot(job_id)
    if not snapshot:
        return None
    if snapshot.get("status") != "completed":
        return None
    result = snapshot.get("result")
    if isinstance(result, dict):
        return result
    return None


def get_assert_generation_zip_path(job_id: str) -> Optional[Path]:
    snapshot = PROGRESS_REGISTRY.snapshot(job_id)
    if not snapshot:
        return None
    result = snapshot.get("result")
    if not isinstance(result, dict):
        return None
    artifacts = result.get("artifacts")
    if not isinstance(artifacts, dict):
        return None
    raw_zip = artifacts.get("zipPath")
    if not raw_zip:
        return None
    zip_path = Path(raw_zip)
    if not zip_path.exists():
        return None
    return zip_path
