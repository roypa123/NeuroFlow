"""HMAC/header webhook signature verification. See docs/15-security-and-
credentials.md #15.9 -- both details called out as "easy to get wrong and
both fatal" get their own test: raw-body comparison and the timestamp
replay window.
"""

from __future__ import annotations

import hashlib
import hmac
import time

from app.modules.webhooks.service import verify_signature

SECRET = "whsec_test_secret"
BODY = b'{"event":"payment.succeeded","amount":4200}'


def _sign(body: bytes, secret: str = SECRET) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_none_auth_always_passes() -> None:
    assert verify_signature(None, raw_body=BODY, headers={}) is True
    assert verify_signature({"type": "none"}, raw_body=BODY, headers={}) is True


def test_valid_hmac_signature_passes() -> None:
    auth = {"type": "hmac", "secret": SECRET}
    headers = {"x-webhook-signature": _sign(BODY)}

    assert verify_signature(auth, raw_body=BODY, headers=headers) is True


def test_wrong_secret_fails() -> None:
    auth = {"type": "hmac", "secret": SECRET}
    headers = {"x-webhook-signature": _sign(BODY, secret="wrong")}

    assert verify_signature(auth, raw_body=BODY, headers=headers) is False


def test_signature_computed_over_different_body_fails() -> None:
    # Verifies against the raw bytes actually received, not a re-serialized
    # version -- re-serializing changes whitespace/key order and the
    # signature would never match a real provider's.
    auth = {"type": "hmac", "secret": SECRET}
    headers = {
        "x-webhook-signature": _sign(b'{"event":"payment.succeeded","amount":9999}')
    }

    assert verify_signature(auth, raw_body=BODY, headers=headers) is False


def test_missing_signature_header_fails() -> None:
    auth = {"type": "hmac", "secret": SECRET}

    assert verify_signature(auth, raw_body=BODY, headers={}) is False


def test_stale_timestamp_is_rejected_even_with_a_valid_signature() -> None:
    auth = {"type": "hmac", "secret": SECRET}
    old_timestamp = str(int(time.time()) - 3600)  # 1 hour old
    headers = {
        "x-webhook-signature": _sign(BODY),
        "x-webhook-timestamp": old_timestamp,
    }

    assert verify_signature(auth, raw_body=BODY, headers=headers) is False


def test_fresh_timestamp_with_valid_signature_passes() -> None:
    auth = {"type": "hmac", "secret": SECRET}
    headers = {
        "x-webhook-signature": _sign(BODY),
        "x-webhook-timestamp": str(int(time.time())),
    }

    assert verify_signature(auth, raw_body=BODY, headers=headers) is True


def test_header_auth_mode_compares_the_declared_header_value() -> None:
    auth = {"type": "headerAuth", "headerValue": "expected-secret"}

    assert (
        verify_signature(
            auth, raw_body=BODY, headers={"authorization": "expected-secret"}
        )
        is True
    )
    assert (
        verify_signature(auth, raw_body=BODY, headers={"authorization": "wrong"})
        is False
    )
