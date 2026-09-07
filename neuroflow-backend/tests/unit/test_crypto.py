"""Envelope encryption round-trip -- docs/15-security-and-credentials.md #15.5.

The property under test is the one the whole credential-storage design
depends on: encrypt(plaintext) then decrypt(blob) with the same master key
recovers the original data exactly, and decryption fails closed (raises,
never returns garbage) under a wrong key or corrupted ciphertext.
"""
from __future__ import annotations

import base64
import os

import pytest

from app.core.crypto import decrypt_credential, encrypt_credential

MASTER_KEY = base64.b64encode(os.urandom(32)).decode()
OTHER_MASTER_KEY = base64.b64encode(os.urandom(32)).decode()


def test_round_trip_recovers_original_plaintext() -> None:
    plaintext = {"apiKey": "sk-live-abc123", "region": "us-east-1"}

    blob = encrypt_credential(plaintext, MASTER_KEY)
    recovered = decrypt_credential(blob, MASTER_KEY)

    assert recovered == plaintext


def test_ciphertext_does_not_contain_plaintext_secret() -> None:
    plaintext = {"apiKey": "sk-live-super-secret-value"}
    blob = encrypt_credential(plaintext, MASTER_KEY)

    assert b"sk-live-super-secret-value" not in blob.ciphertext
    assert b"sk-live-super-secret-value" not in blob.encrypted_dek


def test_wrong_master_key_fails_closed() -> None:
    blob = encrypt_credential({"secret": "value"}, MASTER_KEY)

    with pytest.raises(Exception):  # noqa: B017, PT011 -- any AEAD failure is correct here
        decrypt_credential(blob, OTHER_MASTER_KEY)


def test_two_encryptions_of_the_same_plaintext_produce_different_ciphertext() -> None:
    # Each credential gets its own random data key and nonce -- a leaked
    # ciphertext must not reveal that two credentials share a value.
    plaintext = {"apiKey": "same-value"}

    blob_a = encrypt_credential(plaintext, MASTER_KEY)
    blob_b = encrypt_credential(plaintext, MASTER_KEY)

    assert blob_a.ciphertext != blob_b.ciphertext
    assert blob_a.encrypted_dek != blob_b.encrypted_dek


def test_master_key_of_wrong_length_is_rejected() -> None:
    short_key = base64.b64encode(os.urandom(16)).decode()

    with pytest.raises(ValueError, match="32 bytes"):
        encrypt_credential({"a": "b"}, short_key)
