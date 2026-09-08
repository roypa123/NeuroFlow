"""Schedule model. See docs/09-domain-modules.md #9.12 and
docs/10-database-schema.md #10.9."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.types import Base, UUIDPrimaryKey


class Schedule(Base, UUIDPrimaryKey):
    __tablename__ = "schedules"
    __table_args__ = (
        # The scheduler's entire query plan (docs/10-database-schema.md
        # #10.9) -- must stay a partial index on is_enabled.
        Index(
            "ix_schedules_next_run",
            "next_run_at",
            postgresql_where=text("is_enabled"),
        ),
    )

    workflow_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), index=True
    )
    node_id: Mapped[str] = mapped_column(String(200))
    cron: Mapped[str] = mapped_column(String(100))
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    catch_up: Mapped[bool] = mapped_column(Boolean, default=False)
    next_run_at: Mapped[datetime] = mapped_column()
    last_run_at: Mapped[datetime | None] = mapped_column(default=None)
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
