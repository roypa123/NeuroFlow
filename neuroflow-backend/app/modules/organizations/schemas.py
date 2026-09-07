"""Pydantic schemas for organizations, members, and invitations. See
docs/11-api-design.md #11.5, #11.6."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from app.core.permissions import Role
from app.core.schema import CamelModel


class OrganizationMembershipRead(CamelModel):
    """An organization as seen through one caller's membership in it: id,
    name, and *that caller's* role. Used both by GET /auth/me's
    `organizations` list and by the organizations endpoints themselves --
    the shape is identical in both places, so it is one schema, not two."""

    id: UUID
    name: str
    role: Role


class OrganizationCreate(CamelModel):
    name: str = Field(min_length=1, max_length=200)


class OrganizationUpdate(CamelModel):
    name: str = Field(min_length=1, max_length=200)


class MemberRead(CamelModel):
    user_id: UUID
    email: str
    name: str
    role: Role


class MemberRoleUpdate(CamelModel):
    role: Role


class InvitationCreate(CamelModel):
    email: EmailStr
    role: Role


class InvitationRead(CamelModel):
    id: UUID
    organization_id: UUID
    email: str
    role: Role
    expires_at: datetime
    # The raw, single-use invite token, shown exactly once: there is no
    # email infra in this codebase yet, so the inviting admin copies a link
    # containing this instead of it arriving by email.
    token: str


class InvitationAcceptResult(CamelModel):
    organization_id: UUID
    role: Role
