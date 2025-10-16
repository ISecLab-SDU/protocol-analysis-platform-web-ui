"""Miscellaneous API endpoints."""

from __future__ import annotations

from flask import Blueprint, make_response, request

try:
    from ..utils.responses import error_response
except ImportError:
    from utils.responses import error_response

bp = Blueprint("misc", __name__)


@bp.get("/api/status")
def status():
    status_code = int(request.args.get("status", 200))
    response = make_response(error_response(str(status_code)))
    response.status_code = status_code
    return response


@bp.get("/api/test")
def test_get():
    return "Test get handler"


@bp.post("/api/test")
def test_post():
    return "Test post handler"
