"""Helpers for managing refresh token cookies."""

from __future__ import annotations

from datetime import timedelta
from typing import Optional

from flask import Request, Response

COOKIE_NAME = "jwt"
COOKIE_TTL = timedelta(days=1)


def set_refresh_token_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=int(COOKIE_TTL.total_seconds()),
        httponly=True,
        secure=True,
        samesite="None",
        path="/",
    )


def clear_refresh_token_cookie(response: Response) -> None:
    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        samesite="None",
        secure=True,
    )


def get_refresh_token_from_request(request: Request) -> Optional[str]:
    return request.cookies.get(COOKIE_NAME)
