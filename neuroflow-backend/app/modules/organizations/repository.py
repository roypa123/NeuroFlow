"""SQL access for organizations and memberships. No business rules -- see
docs/08-backend-architecture.md #8.1's test for this layer."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.permissions import Role
from app.modules.organizations.models import (
    Invitation,
    Organization,
    OrganizationMember,
)
from app.modules.users.models import User


class OrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, name: str) -> Organization:
        organization = Organization(name=name)
        self._session.add(organization)
        await self._session.flush()
        return organization

    async def get_by_id(self, organization_id: UUID) -> Organization | None:
        return await self._session.get(Organization, organization_id)

    async def update_name(self, organization: Organization, *, name: str) -> None:
        organization.name = name

    async def add_member(
        self, *, organization_id: UUID, user_id: UUID, role: Role
    ) -> OrganizationMember:
        member = OrganizationMember(
            organization_id=organization_id, user_id=user_id, role=role
        )
        self._session.add(member)
        await self._session.flush()
        return member

    async def get_membership(
        self, *, organization_id: UUID, user_id: UUID
    ) -> OrganizationMember | None:
        stmt = select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_members(
        self, organization_id: UUID
    ) -> list[tuple[OrganizationMember, User]]:
        stmt = (
            select(OrganizationMember)
            .options(joinedload(OrganizationMember.user))
            .where(OrganizationMember.organization_id == organization_id)
            .order_by(OrganizationMember.created_at)
        )
        result = await self._session.execute(stmt)
        members = result.scalars().all()
        return [(member, member.user) for member in members]

    async def update_member_role(
        self, member: OrganizationMember, *, role: Role
    ) -> None:
        member.role = role

    async def remove_member(self, member: OrganizationMember) -> None:
        await self._session.delete(member)

    async def count_owners(self, organization_id: UUID) -> int:
        stmt = select(func.count()).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.role == Role.OWNER,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def list_memberships_for_user(
        self, user_id: UUID
    ) -> list[tuple[OrganizationMember, Organization]]:
        stmt = (
            select(OrganizationMember, Organization)
            .join(Organization, OrganizationMember.organization_id == Organization.id)
            .where(OrganizationMember.user_id == user_id)
            .order_by(OrganizationMember.created_at)
        )
        result = await self._session.execute(stmt)
        return [(member, org) for member, org in result.all()]


class InvitationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        organization_id: UUID,
        email: str,
        role: Role,
        token_hash: str,
        invited_by_user_id: UUID,
        expires_at: datetime,
    ) -> Invitation:
        invitation = Invitation(
            organization_id=organization_id,
            email=email,
            role=role,
            token_hash=token_hash,
            invited_by_user_id=invited_by_user_id,
            expires_at=expires_at,
        )
        self._session.add(invitation)
        await self._session.flush()
        return invitation

    async def get_active_by_hash(self, token_hash: str) -> Invitation | None:
        stmt = select(Invitation).where(
            Invitation.token_hash == token_hash,
            Invitation.accepted_at.is_(None),
            Invitation.revoked_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_by_email(
        self, *, organization_id: UUID, email: str
    ) -> Invitation | None:
        stmt = select(Invitation).where(
            Invitation.organization_id == organization_id,
            Invitation.email == email,
            Invitation.accepted_at.is_(None),
            Invitation.revoked_at.is_(None),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_accepted(self, invitation: Invitation, *, at: datetime) -> None:
        invitation.accepted_at = at
