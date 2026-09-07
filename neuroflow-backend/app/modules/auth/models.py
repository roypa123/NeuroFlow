"""Refresh token model. Tokens are stored hashed, never as the bearer
secret itself -- see app/core/security.py's module docstring and
docs/15-security-and-credentials.md #15.2."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, String
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
