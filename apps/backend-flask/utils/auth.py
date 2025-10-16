"""Lightweight JWT verification compatible with the mock backend."""

from __future__ import annotations

import base64
import json
import hmac
import hashlib
from typing import Any, Dict, Optional

MOCK_USERS = [
    {
        "id": 0,
        "password": "123456",
        "realName": "Vben",
        "roles": ["super"],
        "username": "vben",
    },
    {
        "id": 1,
        "password": "123456",
        "realName": "Admin",
        "roles": ["admin"],
        "username": "admin",
        "homePath": "/workspace",
    },
    {
        "id": 2,
        "password": "123456",
        "realName": "Jack",
        "roles": ["user"],
        "username": "jack",
        "homePath": "/analytics",
    },
]

ACCESS_TOKEN_SECRET = "access_token_secret"


class TokenVerificationError(Exception):
    """Raised when an access token fails validation."""


def _base64url_decode(data: str) -> bytes:
    """Decode a base64 urlsafe string."""
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _verify_signature(
    header_b64: str,
    payload_b64: str,
    signature_b64: str,
    secret: str,
) -> None:
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected = hmac.new(
        secret.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    expected_b64 = base64.urlsafe_b64encode(expected).rstrip(b"=")
    signature_bytes = signature_b64.encode("utf-8")
    if not hmac.compare_digest(expected_b64, signature_bytes):
        raise TokenVerificationError("invalid signature")


def decode_jwt(token: str, secret: str) -> Dict[str, Any]:
    """Decode a HS256 JWT without external dependencies."""
    segments = token.split(".")
    if len(segments) != 3:
        raise TokenVerificationError("invalid token segments")

    header_b64, payload_b64, signature_b64 = segments
    header_bytes = _base64url_decode(header_b64)
    header = json.loads(header_bytes.decode("utf-8"))
    if header.get("alg") != "HS256":
        raise TokenVerificationError("unsupported algorithm")

    _verify_signature(header_b64, payload_b64, signature_b64, secret)

    payload_bytes = _base64url_decode(payload_b64)
    return json.loads(payload_bytes.decode("utf-8"))


def verify_access_token(auth_header: Optional[str]) -> Optional[Dict[str, Any]]:
    """Validate the Authorization header and return the corresponding user."""
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]

    try:
        payload = decode_jwt(token, ACCESS_TOKEN_SECRET)
    except TokenVerificationError:
        return None
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    username = payload.get("username")
    if not username:
        return None

    user = next((item for item in MOCK_USERS if item["username"] == username), None)
    if not user:
        return None

    user_info = dict(user)
    user_info.pop("password", None)
    return user_info
