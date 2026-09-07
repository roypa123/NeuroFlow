"""Workflow and version models. See docs/09-domain-modules.md #9.8 and
docs/10-database-schema.md #10.4."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.types import Base, TimestampMixin, UUIDPrimaryKey


class Workflow(Base, UUIDPrimaryKey, TimestampMixin):
    __tablename__ = "workflows"

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(default=None)
    kind: Mapped[str] = mapped_column(String(20), default="workflow")
    is_active: Mapped[bool] = mapped_column(default=False)
    # Circular reference to workflow_versions -- use_alter defers the FK
    # constraint to a second ALTER TABLE so the two tables can be created in
    # either order. See docs/10-database-schema.md #10.4.
    active_version_id: Mapped[UUID | None] = mapped_column(
        ForeignKey(
            "workflow_versions.id",
            use_alter=True,
            name="fk_workflows_active_version_id_workflow_versions",
            ondelete="SET NULL",
        ),
        default=None,
    )
    settings: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    deleted_at: Mapped[datetime | None] = mapped_column(default=None)


class WorkflowVersion(Base, UUIDPrimaryKey):
    __tablename__ = "workflow_versions"
    __table_args__ = (UniqueConstraint("workflow_id", "version"),)

    workflow_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int] = mapped_column(Integer)
    graph: Mapped[dict[str, Any]] = mapped_column(JSONB)
    pinned_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    # sha256 of the canonicalised graph -- dedupes no-op saves so an
    # unmodified re-save doesn't grow the version history. See
    # docs/10-database-schema.md #10.4.
    checksum: Mapped[str] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(default=None)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    # Immutable -- no updated_at, unlike TimestampMixin: a version, once
    # written, never changes.
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
