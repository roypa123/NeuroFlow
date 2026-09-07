"""Password hashing and JWT round-trip -- docs/15-security-and-credentials.md #15.2."""
from __future__ import annotations

import uuid

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_does_not_return_the_plaintext() -> None:
    hashed = hash_password("correct horse battery staple")
    assert hashed != "correct horse battery staple"
    assert hashed.startswith("$argon2")


def test_verify_password_accepts_the_correct_password() -> None:
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed)


def test_verify_password_rejects_the_wrong_password() -> None:
    hashed = hash_password("correct horse battery staple")
    assert not verify_password("wrong password", hashed)


def test_hashing_the_same_password_twice_produces_different_hashes() -> None:
    # argon2 salts each hash independently -- two users with the same
    # password must not have identical rows.
    assert hash_password("shared-password") != hash_password("shared-password")


def test_access_token_round_trips_claims() -> None:
    user_id = uuid.uuid4()
    org_id = uuid.uuid4()

    token = create_access_token(
        user_id=user_id, org_id=org_id, role="admin", jti="jti-1"
    )
    claims = decode_access_token(token)

    assert claims["sub"] == str(user_id)
    assert claims["org"] == str(org_id)
    assert claims["role"] == "admin"
    assert claims["jti"] == "jti-1"


def test_access_token_with_no_org_encodes_null_org() -> None:
    token = create_access_token(
        user_id=uuid.uuid4(), org_id=None, role=None, jti="jti-2"
    )
    claims = decode_access_token(token)
    assert claims["org"] is None


def test_decode_rejects_a_tampered_token() -> None:
    token = create_access_token(
        user_id=uuid.uuid4(), org_id=None, role="member", jti="jti-3"
    )
    tampered = token[:-4] + ("aaaa" if not token.endswith("aaaa") else "bbbb")

    with pytest.raises(jwt.PyJWTError):
        decode_access_token(tampered)
