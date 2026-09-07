"""Project model. See docs/09-domain-modules.md #9.5 and
docs/10-database-schema.md #10.5."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.types import Base, TimestampMixin, UUIDPrimaryKey


class Project(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "projects"

    organization_id: Mapped[UUID] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    # The project OrganizationService.create_with_owner creates for every
    # org -- kept undeletable (see ProjectService.soft_delete) so an org
    # always has somewhere for a brand-new member to land.
    is_personal: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)
