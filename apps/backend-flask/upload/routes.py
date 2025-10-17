"""File upload placeholder endpoint."""

from __future__ import annotations

from flask import Blueprint, request

try:
    from ..utils.auth import verify_access_token
    from ..utils.responses import success_response, unauthorized
except ImportError:
    from utils.auth import verify_access_token
    from utils.responses import success_response, unauthorized

bp = Blueprint("upload", __name__)


@bp.post("/api/upload")
def upload():
    user = verify_access_token(request.headers.get("Authorization"))
    if not user:
        return unauthorized()
    return success_response(
        {
            "url": "https://unpkg.com/@vbenjs/static-source@0.1.7/source/logo-v1.webp",
        }
    )
