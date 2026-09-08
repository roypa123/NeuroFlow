"""Credential model. See docs/09-domain-modules.md #9.6 and
docs/10-database-schema.md #10.8.

No `data` column of any kind that could be selected by accident -- only the
envelope-encryption ciphertext, key, and nonce. See docs/15-security-and-
credentials.md #15.6: absence, not masking, is what makes a secret-leak via
a future `SELECT *` structurally impossible rather than merely unlikely.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.types import Base, TimestampMixin, UUIDPrimaryKey


class Credential(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "credentials"
    __table_args__ = (
        Index("uq_credentials_project_name", "project_id", "name", unique=True),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    type: Mapped[str] = mapped_column(String(100))
    encrypted_data: Mapped[bytes] = mapped_column(LargeBinary)
    encrypted_dek: Mapped[bytes] = mapped_column(LargeBinary)
    nonce: Mapped[bytes] = mapped_column(LargeBinary)
    key_version: Mapped[int] = mapped_column(Integer, default=1)
    oauth_expires_at: Mapped[datetime | None] = mapped_column(default=None)
    last_tested_at: Mapped[datetime | None] = mapped_column(default=None)
    test_status: Mapped[str | None] = mapped_column(String(20), default=None)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)
