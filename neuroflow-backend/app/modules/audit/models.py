"""Audit log model. Append-only -- see docs/09-domain-modules.md #9.14 and
docs/10-database-schema.md #10.11."""
from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.types import Base, TimestampMixin, UUIDPrimaryKey


class AuditLog(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "audit_logs"
    __table_args__ = (
        Index(
            "ix_audit_logs_organization_id_created_at", "organization_id", "created_at"
        ),
        Index(
            "ix_audit_logs_resource_type_resource_id_created_at",
            "resource_type",
            "resource_id",
            "created_at",
        ),
    )

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE")
    )
    # SET NULL, not CASCADE: a deleted actor must not erase the historical
    # record of what they did.
    actor_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str] = mapped_column(String(50), index=True)
    resource_id: Mapped[UUID]
    changes: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    ip: Mapped[str | None] = mapped_column(String(45), default=None)
    user_agent: Mapped[str | None] = mapped_column(String(500), default=None)
