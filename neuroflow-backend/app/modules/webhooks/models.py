"""Webhook registration model. See docs/09-domain-modules.md #9.11 and
docs/10-database-schema.md #10.9."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.types import Base, UUIDPrimaryKey


class WebhookRegistration(Base, UUIDPrimaryKey):
    __tablename__ = "webhook_registrations"
    __table_args__ = (
        Index(
            "uq_webhook_registrations_path_method_test",
            "path",
            "method",
            "is_test",
            unique=True,
        ),
    )

    workflow_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), index=True
    )
    node_id: Mapped[str] = mapped_column(String(200))
    path: Mapped[str] = mapped_column(String(300))
    method: Mapped[str] = mapped_column(String(10), default="POST")
    is_test: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime | None] = mapped_column(default=None)
    auth: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    response_mode: Mapped[str] = mapped_column(String(20), default="immediate")
    # server_default, not a Python-side default -- see
    # app/modules/executions/models.py's ExecutionData.created_at for why
    # relying on application code to always set this is a live bug waiting
    # to happen, not a style nit.
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
