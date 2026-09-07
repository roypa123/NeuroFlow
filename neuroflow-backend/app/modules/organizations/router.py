"""Organization routes: declarations only -- see
docs/08-backend-architecture.md #8.1. Endpoint set mirrors
docs/11-api-design.md #11.6.

`POST /invitations/{token}/accept` is deliberately its own router with no
`/organizations` prefix: the accepting user doesn't know the org id yet --
the token alone identifies it. See `invitations_router` below.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, status

from app.api.deps import RequestContextDep
from app.modules.organizations.dependencies import OrganizationControllerDep
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

router = APIRouter(prefix="/organizations", tags=["organizations"])
invitations_router = APIRouter(prefix="/invitations", tags=["organizations"])


@router.get("", response_model=list[OrganizationMembershipRead])
async def list_my_organizations(
    ctx: RequestContextDep, controller: OrganizationControllerDep
) -> list[OrganizationMembershipRead]:
    return await controller.list_mine(ctx)


@router.post(
    "", response_model=OrganizationMembershipRead, status_code=status.HTTP_201_CREATED
)
async def create_organization(
    payload: OrganizationCreate,
    ctx: RequestContextDep,
    controller: OrganizationControllerDep,
) -> OrganizationMembershipRead:
    return await controller.create(ctx, payload)


@router.get("/{organization_id}", response_model=OrganizationMembershipRead)
async def get_organization(
    organization_id: UUID, ctx: RequestContextDep, controller: OrganizationControllerDep
) -> OrganizationMembershipRead:
    return await controller.get(ctx, organization_id)


@router.patch("/{organization_id}", response_model=OrganizationMembershipRead)
async def update_organization(
    organization_id: UUID,
    payload: OrganizationUpdate,
    ctx: RequestContextDep,
    controller: OrganizationControllerDep,
) -> OrganizationMembershipRead:
    return await controller.update(ctx, organization_id, payload)


@router.get("/{organization_id}/members", response_model=list[MemberRead])
async def list_members(
    organization_id: UUID, ctx: RequestContextDep, controller: OrganizationControllerDep
) -> list[MemberRead]:
    return await controller.list_members(ctx, organization_id)


@router.post(
    "/{organization_id}/invitations",
    response_model=InvitationRead,
    status_code=status.HTTP_201_CREATED,
)
async def invite_member(
    organization_id: UUID,
    payload: InvitationCreate,
    ctx: RequestContextDep,
    controller: OrganizationControllerDep,
) -> InvitationRead:
    return await controller.invite(ctx, organization_id, payload)


@router.patch("/{organization_id}/members/{user_id}", response_model=MemberRead)
async def update_member_role(
    organization_id: UUID,
    user_id: UUID,
    payload: MemberRoleUpdate,
    ctx: RequestContextDep,
    controller: OrganizationControllerDep,
) -> MemberRead:
    return await controller.update_member_role(ctx, organization_id, user_id, payload)


@router.delete(
    "/{organization_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT
)
async def remove_member(
    organization_id: UUID,
    user_id: UUID,
    ctx: RequestContextDep,
    controller: OrganizationControllerDep,
) -> None:
    await controller.remove_member(ctx, organization_id, user_id)


@invitations_router.post("/{token}/accept", response_model=InvitationAcceptResult)
async def accept_invitation(
    token: str, ctx: RequestContextDep, controller: OrganizationControllerDep
) -> InvitationAcceptResult:
    return await controller.accept_invitation(ctx, token)
