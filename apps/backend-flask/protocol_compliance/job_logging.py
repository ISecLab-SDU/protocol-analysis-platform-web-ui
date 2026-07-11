"""Job-scoped logging helpers for ProtocolGuard workflows."""

from __future__ import annotations

import contextlib
import logging
from types import TracebackType
from collections.abc import Callable, Iterator, Mapping
from typing import Any, Optional

ProgressCallback = Callable[[str, str, str], None]
ExcInfo = (
    bool
    | BaseException
    | tuple[type[BaseException], BaseException, TracebackType | None]
    | tuple[None, None, None]
    | None
)


class JobStageLogger:
    """Bind job and stage context while preserving frontend progress events."""

    def __init__(
        self,
        *,
        job_id: str,
        logger: logging.Logger,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> None:
        self._job_id = job_id
        self._logger = logger
        self._progress_callback = progress_callback
        self._state_stack: list[dict[str, object]] = [{}]

    @contextlib.contextmanager
    def state(self, **state: object) -> Iterator["JobStageLogger"]:
        current = self._state_stack[-1]
        self._state_stack.append({**current, **state})
        try:
            yield self
        finally:
            self._state_stack.pop()

    def debug(
        self,
        message: str,
        *args: object,
        emit_progress: bool = False,
        exc_info: ExcInfo = None,
        frontend_message: Optional[str] = None,
        **fields: object,
    ) -> None:
        self.log(
            logging.DEBUG,
            message,
            *args,
            emit_progress=emit_progress,
            exc_info=exc_info,
            frontend_message=frontend_message,
            **fields,
        )

    def info(
        self,
        message: str,
        *args: object,
        emit_progress: bool = True,
        exc_info: ExcInfo = None,
        frontend_message: Optional[str] = None,
        **fields: object,
    ) -> None:
        self.log(
            logging.INFO,
            message,
            *args,
            emit_progress=emit_progress,
            exc_info=exc_info,
            frontend_message=frontend_message,
            **fields,
        )

    def warning(
        self,
        message: str,
        *args: object,
        emit_progress: bool = True,
        exc_info: ExcInfo = None,
        frontend_message: Optional[str] = None,
        **fields: object,
    ) -> None:
        self.log(
            logging.WARNING,
            message,
            *args,
            emit_progress=emit_progress,
            exc_info=exc_info,
            frontend_message=frontend_message,
            **fields,
        )

    def error(
        self,
        message: str,
        *args: object,
        emit_progress: bool = True,
        exc_info: ExcInfo = None,
        frontend_message: Optional[str] = None,
        **fields: object,
    ) -> None:
        self.log(
            logging.ERROR,
            message,
            *args,
            emit_progress=emit_progress,
            exc_info=exc_info,
            frontend_message=frontend_message,
            **fields,
        )

    def log(
        self,
        level: int,
        message: str,
        *args: object,
        emit_progress: bool = True,
        exc_info: ExcInfo = None,
        frontend_message: Optional[str] = None,
        **fields: object,
    ) -> None:
        state = self._state_stack[-1]
        stage = str(fields.pop("stage", state.get("stage", "general")) or "general")
        context = self._build_context(state, fields)
        self._logger.log(
            level,
            "[job %s][%s] " + message,
            self._job_id,
            stage,
            *args,
            exc_info=exc_info,
            extra={"protocolguard_context": context},
        )
        progress_callback = self._progress_callback
        if emit_progress and progress_callback:
            self._emit_progress(stage, frontend_message or self._format_message(message, args))

    def _build_context(
        self,
        state: Mapping[str, object],
        fields: Mapping[str, object],
    ) -> dict[str, object]:
        context = {
            key: value
            for key, value in {**state, **fields}.items()
            if key != "stage" and value is not None
        }
        return context

    def _emit_progress(self, stage: str, message: str) -> None:
        progress_callback = self._progress_callback
        if progress_callback is None:
            return
        try:
            progress_callback(self._job_id, stage, message)
        except Exception:  # pragma: no cover - defensive
            self._logger.debug("Progress callback failed for job %s", self._job_id, exc_info=True)

    @staticmethod
    def _format_message(message: str, args: tuple[Any, ...]) -> str:
        if not args:
            return message
        try:
            return message % args
        except Exception:  # pragma: no cover - fallback for unusual logging args
            return " ".join([message, *(str(arg) for arg in args)])
