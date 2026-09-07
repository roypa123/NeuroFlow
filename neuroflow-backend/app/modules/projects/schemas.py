"""Pydantic schemas for projects. See docs/11-api-design.md #11.6."""
from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.core.schema import CamelModel


class ProjectRead(CamelModel):
    id: UUID
    organization_id: UUID
    name: str
    is_personal: bool


class ProjectCreate(CamelModel):
    organization_id: UUID
    name: str = Field(min_length=1, max_length=200)


class ProjectUpdate(CamelModel):
    name: str = Field(min_length=1, max_length=200)
