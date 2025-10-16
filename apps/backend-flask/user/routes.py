"""User profile endpoints."""

from __future__ import annotations

from copy import deepcopy

from flask import Blueprint, request

try:
    from ..utils.auth import verify_access_token
    from ..utils.responses import success_response, unauthorized
except ImportError:
    from utils.auth import verify_access_token
    from utils.responses import success_response, unauthorized

bp = Blueprint("user", __name__, url_prefix="/api/user")


@bp.get("/info")
def user_info():
    user = verify_access_token(request.headers.get("Authorization"))
    if not user:
        return unauthorized()
    return success_response(deepcopy(user))
