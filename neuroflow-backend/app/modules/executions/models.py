"""Execution models. See docs/09-domain-modules.md #9.9 and
docs/10-database-schema.md #10.5/#10.6.

Linear FK order (unlike workflows/workflow_versions' circular reference):
`Execution` (self-referencing `parent_execution_id` is fine inline) ->
`ExecutionData` (FKs `Execution`) -> `NodeExecution` (FKs both). No
`use_alter` needed.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.types import Base, UUIDPrimaryKey


class Execution(Base, UUIDPrimaryKey):
    __tablename__ = "executions"
    __table_args__ = (
        Index("ix_executions_workflow_created", "workflow_id", "created_at"),
        Index("ix_executions_project_created", "project_id", "created_at"),
        # Stays tiny (hundreds of rows) even at tens of millions of total
        # rows -- what the worker and the recovery sweeper scan constantly.
        # See docs/10-database-schema.md #10.5.
        Index(
            "ix_executions_status_created",
            "status",
            "created_at",
            postgresql_where=text("status IN ('queued','running','waiting')"),
        ),
    )

    workflow_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflows.id", ondelete="CASCADE"), index=True
    )
    workflow_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("workflow_versions.id"), index=True
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    status: Mapped[str] = mapped_column(String(20))
    mode: Mapped[str] = mapped_column(String(20))
    trigger_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    error: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    resume_token: Mapped[str | None] = mapped_column(String(64), unique=True, default=None)
    resume_after: Mapped[datetime | None] = mapped_column(default=None)
    parent_execution_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("executions.id", ondelete="CASCADE"), default=None
    )
    retry_of_execution_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("executions.id", ondelete="SET NULL"), default=None
    )
    started_at: Mapped[datetime | None] = mapped_column(default=None)
    finished_at: Mapped[datetime | None] = mapped_column(default=None)
    duration_ms: Mapped[int | None] = mapped_column(Integer, default=None)
    created_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    created_at: Mapped[datetime] = mapped_column(index=True)


class ExecutionData(Base, UUIDPrimaryKey):
    __tablename__ = "execution_data"

    execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("executions.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(10))  # "inline" | "object"
    data: Mapped[dict[str, Any] | list[Any] | None] = mapped_column(JSONB, default=None)
    object_key: Mapped[str | None] = mapped_column(default=None)
    size_bytes: Mapped[int] = mapped_column(Integer)
    item_count: Mapped[int] = mapped_column(Integer)
    truncated: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column()


class NodeExecution(Base, UUIDPrimaryKey):
    __tablename__ = "node_executions"
    __table_args__ = (
        Index(
            "uq_node_executions_execution_node_run",
            "execution_id",
            "node_id",
            "run_index",
            unique=True,
        ),
    )

    execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("executions.id", ondelete="CASCADE"), index=True
    )
    node_id: Mapped[str] = mapped_column(String(200))
    node_name: Mapped[str] = mapped_column(String(200))
    node_type: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20))
    run_index: Mapped[int] = mapped_column(Integer, default=0)
    items_in: Mapped[int | None] = mapped_column(Integer, default=None)
    items_out: Mapped[int | None] = mapped_column(Integer, default=None)
    input_data_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("execution_data.id", ondelete="SET NULL"), default=None
    )
    output_data_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("execution_data.id", ondelete="SET NULL"), default=None
    )
    error: Mapped[dict[str, Any] | None] = mapped_column(JSONB, default=None)
    started_at: Mapped[datetime] = mapped_column()
    finished_at: Mapped[datetime | None] = mapped_column(default=None)
    duration_ms: Mapped[int | None] = mapped_column(Integer, default=None)
