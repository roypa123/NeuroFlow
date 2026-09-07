"""Cursor pagination -- docs/11-api-design.md #11.3. The id tiebreaker is
the property under test: two rows sharing a created_at must still each get
a distinct, correctly-ordered cursor."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.core.pagination import Cursor, build_keyset_page, clamp_limit


def test_cursor_round_trips_through_encode_decode() -> None:
    original = Cursor(created_at=datetime(2026, 9, 7, 12, 0, 0, tzinfo=UTC), id=uuid4())

    decoded = Cursor.decode(original.encode())

    assert decoded == original


def test_cursor_is_opaque_base64_not_readable_json() -> None:
    cursor = Cursor(created_at=datetime.now(UTC), id=uuid4())
    encoded = cursor.encode()

    # It must not be plain, inspectable JSON -- clients are not meant to
    # construct cursors themselves.
    assert not encoded.startswith("{")


def test_clamp_limit_applies_default_and_max() -> None:
    assert clamp_limit(None) == 20
    assert clamp_limit(5) == 5
    assert clamp_limit(1000) == 100
    assert clamp_limit(0) == 1
    assert clamp_limit(-5) == 1


@dataclass
class _Row:
    created_at: datetime
    id: UUID


def test_build_keyset_page_detects_has_more_via_the_extra_row() -> None:
    # Caller fetches limit + 1 rows; build_keyset_page trims the extra one
    # and uses it only to decide has_more, per docs/11-api-design.md #11.3.
    now = datetime.now(UTC)
    rows = [_Row(created_at=now, id=uuid4()) for _ in range(4)]

    page, next_cursor, has_more = build_keyset_page(rows, limit=3)

    assert len(page) == 3
    assert has_more is True
    assert next_cursor is not None
    assert Cursor.decode(next_cursor).id == rows[2].id


def test_build_keyset_page_reports_no_more_when_exhausted() -> None:
    now = datetime.now(UTC)
    rows = [_Row(created_at=now, id=uuid4()) for _ in range(2)]

    page, next_cursor, has_more = build_keyset_page(rows, limit=3)

    assert len(page) == 2
    assert has_more is False
    assert next_cursor is None
