"""Envelope encryption for credentials: AES-256-GCM with a per-credential
data key wrapped by a master key. See docs/15-security-and-credentials.md
#15.5 and docs/20-adrs.md ADR-013.

    master key (env / KMS, 32 bytes, never in the database)
       |-wraps-> per-credential data key (DEK, random 32 bytes)
                    |-encrypts-> credential JSON -> ciphertext + nonce + tag

Decryption is reserved for CredentialService.get_decrypted, called only from
worker code -- see the import-linter contract in
docs/17-testing-strategy.md #17.7.
"""
from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

CURRENT_KEY_VERSION = 1
_AAD = b"credential:v1"


@dataclass(slots=True, frozen=True)
class EncryptedBlob:
    ciphertext: bytes
    encrypted_dek: bytes
    nonce: bytes
    key_version: int = CURRENT_KEY_VERSION


def _master_key_bytes(master_key_b64: str) -> bytes:
    key = base64.b64decode(master_key_b64)
    if len(key) != 32:
        raise ValueError("Master key must decode to exactly 32 bytes")
    return key


def encrypt_credential(plaintext: dict[str, Any], master_key_b64: str) -> EncryptedBlob:
    master = _master_key_bytes(master_key_b64)
    dek = AESGCM.generate_key(bit_length=256)

    data_nonce = os.urandom(12)
    ciphertext = AESGCM(dek).encrypt(
        data_nonce, json.dumps(plaintext).encode(), _AAD
    )

    wrap_nonce = os.urandom(12)
    wrapped_dek = wrap_nonce + AESGCM(master).encrypt(wrap_nonce, dek, None)

    return EncryptedBlob(
        ciphertext=ciphertext,
        encrypted_dek=wrapped_dek,
        nonce=data_nonce,
        key_version=CURRENT_KEY_VERSION,
    )


def decrypt_credential(blob: EncryptedBlob, master_key_b64: str) -> dict[str, Any]:
    master = _master_key_bytes(master_key_b64)
    wrap_nonce, wrapped = blob.encrypted_dek[:12], blob.encrypted_dek[12:]
    dek = AESGCM(master).decrypt(wrap_nonce, wrapped, None)
    plaintext = AESGCM(dek).decrypt(blob.nonce, blob.ciphertext, _AAD)
    result: dict[str, Any] = json.loads(plaintext)
    return result
