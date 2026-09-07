"""Pydantic schemas for organizations. See docs/11-api-design.md #11.5."""
from __future__ import annotations

from uuid import UUID

from app.core.permissions import Role
from app.core.schema import CamelModel


class OrganizationMembershipRead(CamelModel):
    id: UUID
    name: str
    role: Role
