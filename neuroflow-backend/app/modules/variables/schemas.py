"""Pydantic schemas for variables. See docs/11-api-design.md #11.12."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.core.schema import CamelModel

_KEY_PATTERN = r"^[A-Z][A-Z0-9_]*$"


class VariableRead(CamelModel):
    id: UUID
    organization_id: UUID
    project_id: UUID | None
    key: str
    # Absent, not masked, when is_secret -- same structural-absence
    # principle as CredentialRead. See docs/15-security-and-credentials.md
    # #15.6 item 1.
    value: str | None
    is_secret: bool
    created_at: datetime
    updated_at: datetime


class VariableCreate(CamelModel):
    project_id: UUID | None = None
    key: str = Field(pattern=_KEY_PATTERN, max_length=100)
    value: str
    is_secret: bool = False


class VariableUpdate(CamelModel):
    value: str | None = None
    is_secret: bool | None = None
