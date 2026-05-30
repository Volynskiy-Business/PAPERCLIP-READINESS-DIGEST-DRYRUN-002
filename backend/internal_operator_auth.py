from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class InternalOperatorAuthConfig:
    secret: str
    issuer: str
    audience: str
    required_role: str
    role_claim: str = "role"


def load_internal_operator_auth_config() -> InternalOperatorAuthConfig | None:
    secret = os.environ.get("INTERNAL_OPERATOR_JWT_SECRET")
    issuer = os.environ.get("INTERNAL_OPERATOR_JWT_ISSUER")
    audience = os.environ.get("INTERNAL_OPERATOR_JWT_AUDIENCE")
    required_role = os.environ.get("INTERNAL_OPERATOR_JWT_REQUIRED_ROLE")
    role_claim = os.environ.get("INTERNAL_OPERATOR_JWT_ROLE_CLAIM", "role")
    if not all([secret, issuer, audience, required_role, role_claim]):
        return None
    return InternalOperatorAuthConfig(
        secret=secret,
        issuer=issuer,
        audience=audience,
        required_role=required_role,
        role_claim=role_claim,
    )


def verify_internal_operator_jwt(token: str, *, config: InternalOperatorAuthConfig | None = None) -> dict[str, Any] | None:
    resolved_config = config or load_internal_operator_auth_config()
    if resolved_config is None:
        return None

    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError:
        return None

    header = _decode_segment(header_segment)
    payload = _decode_segment(payload_segment)
    if not isinstance(header, dict) or not isinstance(payload, dict):
        return None
    if header.get("alg") != "HS256" or header.get("typ") != "JWT":
        return None

    signed_value = f"{header_segment}.{payload_segment}".encode("ascii")
    expected_signature = hmac.new(
        resolved_config.secret.encode("utf-8"),
        signed_value,
        hashlib.sha256,
    ).digest()
    actual_signature = _decode_signature(signature_segment)
    if actual_signature is None or not hmac.compare_digest(actual_signature, expected_signature):
        return None

    if payload.get("iss") != resolved_config.issuer:
        return None
    if not _audience_matches(payload.get("aud"), resolved_config.audience):
        return None
    if not _role_matches(payload.get(resolved_config.role_claim), resolved_config.required_role):
        return None
    if not isinstance(payload.get("sub"), str) or not payload["sub"].strip():
        return None

    now = int(time.time())
    exp = payload.get("exp")
    iat = payload.get("iat")
    nbf = payload.get("nbf")
    if not isinstance(exp, int) or exp <= now:
        return None
    if iat is not None and (not isinstance(iat, int) or iat > now):
        return None
    if nbf is not None and (not isinstance(nbf, int) or nbf > now):
        return None

    return payload


def _decode_segment(value: str) -> Any:
    decoded = _urlsafe_b64decode(value)
    if decoded is None:
        return None
    try:
        return json.loads(decoded)
    except json.JSONDecodeError:
        return None


def _decode_signature(value: str) -> bytes | None:
    return _urlsafe_b64decode(value, binary=True)


def _urlsafe_b64decode(value: str, *, binary: bool = False) -> bytes | str | None:
    padding = "=" * (-len(value) % 4)
    try:
        raw = base64.urlsafe_b64decode(value + padding)
    except (ValueError, base64.binascii.Error):
        return None
    if binary:
        return raw
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _audience_matches(value: Any, expected: str) -> bool:
    if isinstance(value, str):
        return value == expected
    if isinstance(value, list):
        return expected in value
    return False


def _role_matches(value: Any, expected: str) -> bool:
    if isinstance(value, str):
        return value == expected
    if isinstance(value, list):
        return expected in value
    return False
