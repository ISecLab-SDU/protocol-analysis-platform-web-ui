"""JWT utilities and authentication helpers for the Flask backend."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from copy import deepcopy
from typing import Any, Dict, Optional

from .data import MOCK_USERS

ACCESS_TOKEN_SECRET = "access_token_secret"
REFRESH_TOKEN_SECRET = "refresh_token_secret"
ACCESS_TOKEN_TTL = 7 * 24 * 60 * 60
REFRESH_TOKEN_TTL = 30 * 24 * 60 * 60
DEFAULT_SUPER_USERNAME = "vben"


class TokenVerificationError(Exception):
    """Raised when a JWT fails validation."""


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def _sign(signing_input: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return _base64url_encode(digest)


def _encode_jwt(payload: Dict[str, Any], secret: str, ttl: int) -> str:
    now = int(time.time())
    data = payload.copy()
    data.setdefault("iat", now)
    data.setdefault("exp", now + ttl)

    header = {"alg": "HS256", "typ": "JWT"}
    header_segment = _base64url_encode(
        json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    payload_segment = _base64url_encode(
        json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
    signature_segment = _sign(signing_input, secret)
    return ".".join([header_segment, payload_segment, signature_segment])


def decode_jwt(token: str, secret: str) -> Dict[str, Any]:
    segments = token.split(".")
    if len(segments) != 3:
        raise TokenVerificationError("invalid token segments")

    header_b64, payload_b64, signature_b64 = segments
    header_bytes = _base64url_decode(header_b64)
    header = json.loads(header_bytes.decode("utf-8"))
    if header.get("alg") != "HS256":
        raise TokenVerificationError("unsupported algorithm")

    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
    expected_signature = _sign(signing_input, secret)
    if not hmac.compare_digest(expected_signature, signature_b64):
        raise TokenVerificationError("invalid signature")

    payload_bytes = _base64url_decode(payload_b64)
    payload = json.loads(payload_bytes.decode("utf-8"))

    exp = payload.get("exp")
    if isinstance(exp, (int, float)):
        if int(time.time()) >= int(exp):
            raise TokenVerificationError("token expired")

    return payload


def _sanitize_user(user: Dict[str, Any]) -> Dict[str, Any]:
    sanitized = dict(user)
    sanitized.pop("password", None)
    return sanitized


def generate_access_token(user: Dict[str, Any]) -> str:
    payload = _sanitize_user(user)
    return _encode_jwt(payload, ACCESS_TOKEN_SECRET, ACCESS_TOKEN_TTL)


def generate_refresh_token(user: Dict[str, Any]) -> str:
    payload = {"username": user["username"]}
    return _encode_jwt(payload, REFRESH_TOKEN_SECRET, REFRESH_TOKEN_TTL)


def _load_user(username: str) -> Optional[Dict[str, Any]]:
    user = next((item for item in MOCK_USERS if item["username"] == username), None)
    return dict(user) if user else None


_DEFAULT_USER = _load_user(DEFAULT_SUPER_USERNAME)
_DEFAULT_SANITIZED_USER = _sanitize_user(_DEFAULT_USER) if _DEFAULT_USER else None


def verify_access_token(auth_header: Optional[str]) -> Optional[Dict[str, Any]]:
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ", 1)[1]
    try:
        payload = decode_jwt(token, ACCESS_TOKEN_SECRET)
    except (TokenVerificationError, json.JSONDecodeError, UnicodeDecodeError):
        return None

    username = payload.get("username")
    if not isinstance(username, str):
        return None

    user = _load_user(username)
    if not user:
        return None

    result = dict(user)
    result.pop("password", None)
    return result


def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = decode_jwt(token, REFRESH_TOKEN_SECRET)
    except (TokenVerificationError, json.JSONDecodeError, UnicodeDecodeError):
        return None
    username = payload.get("username")
    if not isinstance(username, str):
        return None
    user = _load_user(username)
    if not user:
        return None
    sanitized = dict(user)
    sanitized.pop("password", None)
    return sanitized
