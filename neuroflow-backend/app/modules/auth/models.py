"""Refresh, password-reset, and API key models. Every secret here is
stored hashed, never as the bearer value itself -- see
app/core/security.py's module docstring and
docs/15-security-and-credentials.md #15.2."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ARRAY, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.types import Base, TimestampMixin, UUIDPrimaryKey
from app.core.uuid7 import uuid7


class RefreshToken(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "refresh_tokens"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # Shared across every token produced by rotating one login -- see
    # AuthService.refresh(): presenting an already-revoked token means the
    # chain was stolen and replayed, and the fix is to kill the whole
    # family, not just the one token, since we can no longer tell which
    # copy is the legitimate client.
    family_id: Mapped[UUID] = mapped_column(default=uuid7, index=True)
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None] = mapped_column(default=None)


class PasswordResetToken(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "password_reset_tokens"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime]
    used_at: Mapped[datetime | None] = mapped_column(default=None)


class ApiKey(Base, UUIDPrimaryKey, TimestampMixin):
    """See docs/09-domain-modules.md #9.2. Scopes are `Permission` values
    (app/core/permissions.py) stored as plain strings -- the key can never
    do more than its owner's own role already allows (checked separately,
    at request time, against their current membership), scopes only ever
    narrow that further. See `require()`'s docstring."""

    __tablename__ = "api_keys"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    key_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    # First few characters of the raw key (e.g. "nf_live_ab12"), kept so
    # the list view can help a user recognise which key is which without
    # ever storing or re-displaying the full secret.
    prefix: Mapped[str] = mapped_column(String(16))
    scopes: Mapped[list[str]] = mapped_column(ARRAY(String))
    last_used_at: Mapped[datetime | None] = mapped_column(default=None)
    expires_at: Mapped[datetime | None] = mapped_column(default=None)
    revoked_at: Mapped[datetime | None] = mapped_column(default=None)
