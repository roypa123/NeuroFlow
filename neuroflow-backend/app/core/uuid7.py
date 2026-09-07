"""Minimal, dependency-free UUIDv7 generator (RFC 9562).

48-bit big-endian millisecond Unix timestamp + random tail. Time-ordered, so
B-tree inserts stay at the right edge instead of causing page splits the way
UUIDv4 does, while remaining non-enumerable. See docs/20-adrs.md ADR-003.
"""
from __future__ import annotations

import os
import time
import uuid


def uuid7() -> uuid.UUID:
    unix_ms = int(time.time() * 1000)
    ts_bytes = unix_ms.to_bytes(6, "big")
    rand = bytearray(os.urandom(10))

    # Version 7 in the high nibble of byte 6.
    rand[0] = (rand[0] & 0x0F) | 0x70
    # Variant 10xxxxxx in the high bits of byte 8.
    rand[2] = (rand[2] & 0x3F) | 0x80

    return uuid.UUID(bytes=bytes(ts_bytes) + bytes(rand))
