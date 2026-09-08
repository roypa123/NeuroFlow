"""Variable model. See docs/09-domain-modules.md #9.13 and
docs/10-database-schema.md #10.11.

Deviates from the schema doc's single `encrypted_value bytea` column: a
secret variable's envelope needs the same three parts a credential's does
(ciphertext, wrapped DEK, nonce) to be rotatable without decrypting every
row, so it gets the same three columns as `credentials` rather than a
hand-rolled single-blob framing -- internal consistency with the one other
encrypted-at-rest table wins over matching the doc's column count exactly.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.types import Base, TimestampMixin, UUIDPrimaryKey


class Variable(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "variables"
    __table_args__ = (
        CheckConstraint("key ~ '^[A-Z][A-Z0-9_]*$'", name="key_screaming_snake_case"),
        Index(
            "uq_variables_org_project_key",
            "organization_id",
            "project_id",
            "key",
            unique=True,
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    project_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), default=None
    )
    key: Mapped[str] = mapped_column(String(100))
    value: Mapped[str | None] = mapped_column(Text, default=None)
    encrypted_value: Mapped[bytes | None] = mapped_column(LargeBinary, default=None)
    encrypted_dek: Mapped[bytes | None] = mapped_column(LargeBinary, default=None)
    nonce: Mapped[bytes | None] = mapped_column(LargeBinary, default=None)
    key_version: Mapped[int | None] = mapped_column(Integer, default=None)
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)
