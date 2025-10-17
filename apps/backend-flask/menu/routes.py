"""Menu-related endpoints."""

from __future__ import annotations

from copy import deepcopy

from flask import Blueprint, request

try:
    from ..utils.auth import verify_access_token
    from ..utils.data import MOCK_MENUS
    from ..utils.responses import success_response, unauthorized
except ImportError:
    from utils.auth import verify_access_token
    from utils.data import MOCK_MENUS
    from utils.responses import success_response, unauthorized

bp = Blueprint("menu", __name__, url_prefix="/api/menu")


@bp.get("/all")
def menu_all():
    user = verify_access_token(request.headers.get("Authorization"))
    if not user:
        return unauthorized()

    menus = []
    for item in MOCK_MENUS:
        if item["username"] == user["username"]:
            menus = deepcopy(item["menus"])
            break
    return success_response(menus)
