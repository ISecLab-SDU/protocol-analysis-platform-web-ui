"""Utility helpers for building consistent API responses."""

from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple

from flask import Response, make_response


def success_response(data: Any, message: str = "ok") -> Dict[str, Any]:
    """Wrap a payload in the shared success envelope."""
    return {
        "code": 0,
        "data": data,
        "error": None,
        "message": message,
    }


def error_response(message: str, error: Optional[Any] = None) -> Dict[str, Any]:
    """Wrap an error payload in the shared error envelope."""
    return {
        "code": -1,
        "data": None,
        "error": error,
        "message": message,
    }


def paginate(
    items: list[Any],
    page: int,
    page_size: int,
) -> Tuple[list[Any], int]:
    """Slice a list using 1-based pagination."""
    total = len(items)
    start = max(page - 1, 0) * page_size
    end = start + page_size
    return items[start:end], total


def unauthorized() -> Tuple[Response, int]:
    """Flask-compatible unauthorized response."""
    payload = error_response("Unauthorized Exception", "Unauthorized Exception")
    return make_response(payload, 401)


def forbidden(message: str = "Forbidden Exception") -> Tuple[Response, int]:
    """Flask-compatible forbidden response."""
    payload = error_response(message, message)
    return make_response(payload, 403)


def sleep(ms: int) -> None:
    """Pause execution for the specified milliseconds."""
    time.sleep(max(ms, 0) / 1000.0)
