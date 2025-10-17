"""Authentication endpoints mirroring the Nitro mock implementation."""

from __future__ import annotations

from copy import deepcopy
from typing import Optional

from flask import Blueprint, make_response, request

try:
    from ..utils import cookies
    from ..utils.auth import (
        generate_access_token,
        generate_refresh_token,
        verify_access_token,
        verify_refresh_token,
    )
    from ..utils.data import MOCK_CODES, MOCK_USERS
    from ..utils.responses import (
        error_response,
        forbidden,
        success_response,
        unauthorized,
    )
except ImportError:
    from utils import cookies
    from utils.auth import (
        generate_access_token,
        generate_refresh_token,
        verify_access_token,
        verify_refresh_token,
    )
    from utils.data import MOCK_CODES, MOCK_USERS
    from utils.responses import (
        error_response,
        forbidden,
        success_response,
        unauthorized,
    )

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _find_user(username: str, password: Optional[str] = None):
    for user in MOCK_USERS:
        if user["username"] != username:
            continue
        if password is not None and user.get("password") != password:
            continue
        return user
    return None


@bp.post("/login")
def login():
    payload = request.get_json(silent=True) or {}
    username = payload.get("username")
    password = payload.get("password")

    if not username or not password:
        response = make_response(
            error_response(
                "BadRequestException", "Username and password are required"
            ),
            400,
        )
        cookies.clear_refresh_token_cookie(response)
        return response

    user = _find_user(str(username), str(password))
    if not user:
        response, status = forbidden("Username or password is incorrect.")
        cookies.clear_refresh_token_cookie(response)
        return response, status

    access_token = generate_access_token(user)
    refresh_token = generate_refresh_token(user)

    user_payload = deepcopy(user)
    user_payload["accessToken"] = access_token

    response = make_response(success_response(user_payload))
    cookies.set_refresh_token_cookie(response, refresh_token)
    return response


@bp.post("/refresh")
def refresh():
    refresh_token = cookies.get_refresh_token_from_request(request)
    if not refresh_token:
        return forbidden()

    userinfo = verify_refresh_token(refresh_token)
    if not userinfo:
        return forbidden()

    user = _find_user(userinfo["username"])
    if not user:
        return forbidden()

    access_token = generate_access_token(user)
    response = make_response(access_token)
    cookies.set_refresh_token_cookie(response, refresh_token)
    return response


@bp.post("/logout")
def logout():
    response = make_response(success_response(""))
    cookies.clear_refresh_token_cookie(response)
    return response


@bp.get("/codes")
def codes():
    user = verify_access_token(request.headers.get("Authorization"))
    if not user:
        return unauthorized()

    codes = []
    for item in MOCK_CODES:
        if item["username"] == user["username"]:
            codes = item["codes"]
            break

    return success_response(codes)
