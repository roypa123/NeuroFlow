"""Password hashing and JWT encode/decode.

See docs/15-security-and-credentials.md #15.2. Passwords use argon2id.
Access tokens are short-lived JWTs; refresh tokens are opaque and handled in
the auth module (they are stored hashed, never as JWTs).
"""
from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

_pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_opaque_token(token: str) -> str:
    """SHA-256 over a randomly-generated opaque token (refresh tokens,
    password-reset tokens, API keys): the token itself already carries all
    the entropy, so this is a lookup digest, not a password hash -- argon2
    would just add pointless CPU cost. Shared so every module hashing one
    of these uses the exact same digest, since the hash is also the
    lookup key at verification time."""
    return hashlib.sha256(token.encode()).hexdigest()


def hash_password(password: str) -> str:
    return str(_pwd_context.hash(password))


def verify_password(password: str, password_hash: str) -> bool:
    return bool(_pwd_context.verify(password, password_hash))


def create_access_token(
    *, user_id: UUID, org_id: UUID | None, role: str | None, jti: str
) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "org": str(org_id) if org_id else None,
        "role": role,
        "jti": jti,
        "iat": now,
        "exp": now + settings.access_token_ttl,
    }
    return jwt.encode(
        payload,
        settings.secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(
        token,
        settings.secret_key.get_secret_value(),
        algorithms=[settings.jwt_algorithm],
    )


def new_refresh_token_ttl() -> timedelta:
    return get_settings().refresh_token_ttl
