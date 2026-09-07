"""UUIDv7 properties that docs/20-adrs.md ADR-003 depends on: time-ordering
(so Postgres B-tree inserts stay at the right edge) and the correct
version/variant bits (so any UUIDv7-aware tooling recognises them)."""
from __future__ import annotations

import time
import uuid

from app.core.uuid7 import uuid7


def test_generates_a_valid_uuid() -> None:
    value = uuid7()
    assert isinstance(value, uuid.UUID)


def test_version_and_variant_bits_are_correct() -> None:
    value = uuid7()
    assert value.version == 7
    # RFC 9562 variant 10xxxxxx.
    assert value.variant == uuid.RFC_4122


def test_successive_ids_are_time_ordered() -> None:
    # UUIDv7 only orders the millisecond-timestamp prefix -- two ids minted
    # in the same millisecond may sort either way on their random tail, by
    # spec. What ADR-003 actually relies on (B-tree inserts landing at the
    # right edge) is the timestamp prefix being non-decreasing, not a total
    # order over the full 128 bits.
    ids = [uuid7() for _ in range(50)]
    timestamps = [int.from_bytes(i.bytes[:6], "big") for i in ids]
    assert timestamps == sorted(timestamps)


def test_ids_from_different_milliseconds_sort_strictly_by_time() -> None:
    first = uuid7()
    time.sleep(0.002)
    second = uuid7()
    assert first < second


def test_ids_generated_in_the_same_millisecond_are_still_unique() -> None:
    ids = {uuid7() for _ in range(1000)}
    assert len(ids) == 1000


def test_timestamp_prefix_reflects_generation_time() -> None:
    before_ms = int(time.time() * 1000)
    value = uuid7()
    after_ms = int(time.time() * 1000)

    embedded_ms = int.from_bytes(value.bytes[:6], "big")
    assert before_ms <= embedded_ms <= after_ms
