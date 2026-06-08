"""Flask backend package for protocol compliance services."""

from __future__ import annotations

from typing import Any


def create_app(*args: Any, **kwargs: Any) -> Any:
    from app import create_app as factory

    return factory(*args, **kwargs)

__all__ = ["create_app"]
