"""Keyset (cursor) and offset pagination helpers.

Keyset pagination is used for anything that grows without bound
(executions, audit logs, agent runs). Offset pagination is reserved for
small, bounded collections. See docs/11-api-design.md #11.3.
"""
from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Generic, TypeVar
from uuid import UUID

from app.core.schema import CamelModel

T = TypeVar("T")

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


@dataclass(slots=True, frozen=True)
class Cursor:
    """Opaque pagination cursor: (created_at, id). The id tiebreaker matters
    -- without it, rows sharing a timestamp are silently skipped or
    duplicated."""

    created_at: datetime
    id: UUID

    def encode(self) -> str:
        payload = {"c": self.created_at.isoformat(), "i": str(self.id)}
        raw = json.dumps(payload, separators=(",", ":")).encode()
        return base64.urlsafe_b64encode(raw).decode()

    @classmethod
    def decode(cls, token: str) -> Cursor:
        raw = base64.urlsafe_b64decode(token.encode())
        payload = json.loads(raw)
        return cls(
            created_at=datetime.fromisoformat(payload["c"]), id=UUID(payload["i"])
        )


def clamp_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_LIMIT
    return max(1, min(limit, MAX_LIMIT))


class KeysetPage(CamelModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None
    has_more: bool = False


class OffsetPage(CamelModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


def build_keyset_page(
    rows: list[Any],
    *,
    limit: int,
    cursor_fields: tuple[str, str] = ("created_at", "id"),
) -> tuple[list[Any], str | None, bool]:
    """rows must be fetched with limit + 1 so we can detect has_more without
    a second query."""
    has_more = len(rows) > limit
    page_rows = rows[:limit]
    next_cursor = None
    if has_more and page_rows:
        last = page_rows[-1]
        next_cursor = Cursor(
            created_at=getattr(last, cursor_fields[0]),
            id=getattr(last, cursor_fields[1]),
        ).encode()
    return page_rows, next_cursor, has_more
