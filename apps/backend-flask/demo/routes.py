"""Miscellaneous demo endpoints."""

from __future__ import annotations

from flask import Blueprint, make_response, request

try:
    from ..utils.auth import verify_access_token
    from ..utils.responses import unauthorized
except ImportError:
    from utils.auth import verify_access_token
    from utils.responses import unauthorized

bp = Blueprint("demo", __name__, url_prefix="/api/demo")


@bp.get("/bigint")
def bigint():
    user = verify_access_token(request.headers.get("Authorization"))
    if not user:
        return unauthorized()

    data = """
  {
    "code": 0,
    "message": "success",
    "data": [
              {
                "id": 123456789012345678901234567890123456789012345678901234567890,
                "name": "John Doe",
                "age": 30,
                "email": "john-doe@demo.com"
                },
                {
                "id": 987654321098765432109876543210987654321098765432109876543210,
                "name": "Jane Smith",
                "age": 25,
                "email": "jane@demo.com"
                }
            ]
  }
  """
    response = make_response(data)
    response.headers["Content-Type"] = "application/json"
    return response
