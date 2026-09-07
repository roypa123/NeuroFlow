"""Pydantic schemas for users. See docs/11-api-design.md #11.5."""
from __future__ import annotations

from uuid import UUID

from app.core.schema import CamelModel
from app.modules.organizations.schemas import OrganizationMembershipRead


class UserRead(CamelModel):
    id: UUID
    email: str
    name: str
    avatar_url: str | None
    organizations: list[OrganizationMembershipRead]
