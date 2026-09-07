"""SQL access for organizations and memberships. No business rules -- see
docs/08-backend-architecture.md #8.1's test for this layer."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import Role
from app.modules.organizations.models import Organization, OrganizationMember


class OrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, *, name: str) -> Organization:
        organization = Organization(name=name)
        self._session.add(organization)
        await self._session.flush()
        return organization

    async def add_member(
        self, *, organization_id: UUID, user_id: UUID, role: Role
    ) -> OrganizationMember:
        member = OrganizationMember(
            organization_id=organization_id, user_id=user_id, role=role
        )
        self._session.add(member)
        await self._session.flush()
        return member

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
