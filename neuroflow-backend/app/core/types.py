"""Shared SQLAlchemy base, naming convention, and mixins.

The naming convention MUST be set before the first migration: without it,
Alembic autogenerates unnamed constraints that cannot be dropped later
without raw SQL. See docs/08-backend-architecture.md #8.6.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.uuid7 import uuid7

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    # Every `Mapped[datetime]` column is `timestamptz`, never naive
    # `timestamp` -- docs/10-database-schema.md #10.6: "timestamptz always,
    # UTC always". Set once here rather than per-column so it cannot drift.
    type_annotation_map = {datetime: DateTime(timezone=True)}


class UUIDPrimaryKey:
    """UUIDv7 primary key -- time-ordered inserts, non-enumerable ids.

    See docs/20-adrs.md ADR-003.
    """

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid7)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )
