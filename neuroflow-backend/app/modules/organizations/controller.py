"""Organization orchestration: authorize, call the service, map to
response schemas. See docs/08-backend-architecture.md #8.1.

Every method starts by resolving the caller's role via
`OrganizationService.get_role_for_member`, which 404s for a non-member --
that single call is what makes cross-tenant access 404 instead of 403
everywhere in this module (docs/17-testing-strategy.md #17.4).
"""
from __future__ import annotations

from uuid import UUID

from app.api.deps import RequestContext
from app.core.permissions import Permission, Role, require
from app.modules.organizations.models import OrganizationMember
from app.modules.organizations.schemas import (
    InvitationAcceptResult,
    InvitationCreate,
    InvitationRead,
    MemberRead,
    MemberRoleUpdate,
    OrganizationCreate,
    OrganizationMembershipRead,
    OrganizationUpdate,
)
from app.modules.organizations.service import OrganizationService
from app.modules.users.models import User


def _to_member_read(member: OrganizationMember, user: User) -> MemberRead:
    return MemberRead(
        user_id=user.id, email=user.email, name=user.name, role=member.role
    )


class OrganizationController:
    def __init__(self, service: OrganizationService) -> None:
        self._service = service

    async def list_mine(self, ctx: RequestContext) -> list[OrganizationMembershipRead]:
        memberships = await self._service.list_for_user(ctx.user_id)
        return [
            OrganizationMembershipRead(id=org.id, name=org.name, role=role)
            for org, role in memberships
        ]

    async def create(
        self, ctx: RequestContext, payload: OrganizationCreate
    ) -> OrganizationMembershipRead:
        # Any authenticated user may create a new organization -- they
        # become its owner, so there is nothing else to authorize.
        organization = await self._service.create_with_owner(
            name=payload.name, owner_user_id=ctx.user_id
        )
        return OrganizationMembershipRead(
            id=organization.id, name=organization.name, role=Role.OWNER
        )

    async def get(
        self, ctx: RequestContext, organization_id: UUID
    ) -> OrganizationMembershipRead:
        organization, role = await self._service.get(
            organization_id=organization_id, user_id=ctx.user_id
        )
        return OrganizationMembershipRead(
            id=organization.id, name=organization.name, role=role
        )

    async def update(
        self, ctx: RequestContext, organization_id: UUID, payload: OrganizationUpdate
    ) -> OrganizationMembershipRead:
        role = await self._service.get_role_for_member(
            organization_id=organization_id, user_id=ctx.user_id
        )
        require(role, Permission.MEMBER_MANAGE, scopes=ctx.scopes)
        organization = await self._service.rename(
            organization_id=organization_id, name=payload.name, actor_id=ctx.user_id
        )
        return OrganizationMembershipRead(
            id=organization.id, name=organization.name, role=role
        )

    async def list_members(
        self, ctx: RequestContext, organization_id: UUID
    ) -> list[MemberRead]:
        # Any member may see the roster -- no additional permission beyond
        # membership itself (already checked via get_role_for_member).
        await self._service.get_role_for_member(
            organization_id=organization_id, user_id=ctx.user_id
        )
        members = await self._service.list_members(organization_id)
        return [_to_member_read(member, user) for member, user in members]

    async def invite(
        self, ctx: RequestContext, organization_id: UUID, payload: InvitationCreate
    ) -> InvitationRead:
        role = await self._service.get_role_for_member(
            organization_id=organization_id, user_id=ctx.user_id
        )
        require(role, Permission.MEMBER_MANAGE, scopes=ctx.scopes)
        issued = await self._service.invite(
            organization_id=organization_id,
            email=payload.email,
            role=payload.role,
            invited_by_user_id=ctx.user_id,
        )
        return InvitationRead(
            id=issued.invitation.id,
            organization_id=issued.invitation.organization_id,
            email=issued.invitation.email,
            role=issued.invitation.role,
            expires_at=issued.invitation.expires_at,
            token=issued.token,
        )

    async def accept_invitation(
        self, ctx: RequestContext, token: str
    ) -> InvitationAcceptResult:
        organization_id, role = await self._service.accept_invitation(
            token=token, accepting_user_id=ctx.user_id
        )
        return InvitationAcceptResult(organization_id=organization_id, role=role)

    async def update_member_role(
        self,
        ctx: RequestContext,
        organization_id: UUID,
        target_user_id: UUID,
        payload: MemberRoleUpdate,
    ) -> MemberRead:
        role = await self._service.get_role_for_member(
            organization_id=organization_id, user_id=ctx.user_id
        )
        require(role, Permission.MEMBER_MANAGE, scopes=ctx.scopes)
        await self._service.update_member_role(
            organization_id=organization_id,
            target_user_id=target_user_id,
            role=payload.role,
            actor_id=ctx.user_id,
        )
        members = await self._service.list_members(organization_id)
        member, user = next(m for m in members if m[1].id == target_user_id)
        return _to_member_read(member, user)

    async def remove_member(
        self, ctx: RequestContext, organization_id: UUID, target_user_id: UUID
    ) -> None:
        role = await self._service.get_role_for_member(
            organization_id=organization_id, user_id=ctx.user_id
        )
        require(role, Permission.MEMBER_MANAGE, scopes=ctx.scopes)
        await self._service.remove_member(
            organization_id=organization_id,
            target_user_id=target_user_id,
            actor_id=ctx.user_id,
        )
