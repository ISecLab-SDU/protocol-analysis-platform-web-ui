"""Error types for ProtocolGuard Docker integration."""

from __future__ import annotations

from typing import List, Optional

__all__ = [
    "ProtocolGuardDockerError",
    "ProtocolGuardExecutionError",
    "ProtocolGuardNotAvailableError",
]


class ProtocolGuardDockerError(RuntimeError):
    """Base exception for Docker integration errors."""


class ProtocolGuardNotAvailableError(ProtocolGuardDockerError):
    """Raised when Docker SDK or engine is unavailable."""


class ProtocolGuardExecutionError(ProtocolGuardDockerError):
    """Raised when the container exits with a non-zero status."""

    def __init__(
        self,
        message: str,
        *,
        logs: Optional[List[str]] = None,
        log_excerpt: Optional[str] = None,
        image: Optional[str] = None,
        status: Optional[int] = None,
    ) -> None:
        super().__init__(message)
        self.logs = logs or []
        self.log_excerpt = log_excerpt
        self.image = image
        self.status = status
