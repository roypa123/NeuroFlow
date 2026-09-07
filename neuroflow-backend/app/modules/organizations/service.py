"""Organization, membership, and invitation business rules.

Framework-agnostic -- raises AppError subclasses, never HTTPException.
Permission checks (`require()`) deliberately do NOT live here: per
app/core/permissions.py's docstring, `require()` is called only from
controllers, so this service stays usable from a future worker/CLI context
with no user in scope. See docs/08-backend-architecture.md #8.1.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.permissions import Role
from app.modules.audit.service import AuditService
from app.modules.organizations.exceptions import (
    AlreadyMemberError,
    InvitationEmailMismatchError,
    InvitationInvalidError,
    LastOwnerError,
    MemberNotFoundError,
    OrganizationNotFoundError,
)
from app.modules.organizations.models import (
    Invitation,
    Organization,
    OrganizationMember,
)
from app.modules.organizations.repository import (
    InvitationRepository,
    OrganizationRepository,
)
from app.modules.projects.repository import ProjectRepository
from app.modules.users.models import User
from app.modules.users.repository import UserRepository

INVITATION_TTL = timedelta(days=7)

Memberships = list[tuple[Organization, Role]]


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(slots=True, frozen=True)
class IssuedInvitation:
    invitation: Invitation
    token: str


class OrganizationService:
    def __init__(
        self,
        organizations: OrganizationRepository,
        invitations: InvitationRepository,
        projects: ProjectRepository,
        users: UserRepository,
        audit: AuditService,
    ) -> None:
        self._organizations = organizations
        self._invitations = invitations
        self._projects = projects
        self._users = users
        self._audit = audit

    async def create_with_owner(
        self, *, name: str, owner_user_id: UUID
    ) -> Organization:
        """The one place an org is bootstrapped: an owner membership plus a
        default Personal project. Used both by a fresh signup
        (AuthService.register) and by an existing user creating an
        additional organization, so the rule lives in exactly one place."""
        organization = await self._organizations.create(name=name)
        await self._organizations.add_member(
            organization_id=organization.id, user_id=owner_user_id, role=Role.OWNER
        )
        await self._projects.create(
            organization_id=organization.id, name="Personal", is_personal=True
        )
        return organization

    async def get_role_for_member(
        self, *, organization_id: UUID, user_id: UUID
    ) -> Role:
        """The single chokepoint every org-scoped controller uses to check
        access. Raises NotFoundError, never PermissionError, for a
        non-member."""
        membership = await self._organizations.get_membership(
            organization_id=organization_id, user_id=user_id
        )
        if membership is None:
            raise OrganizationNotFoundError("Organization not found")
        return membership.role

    async def get(
        self, *, organization_id: UUID, user_id: UUID
    ) -> tuple[Organization, Role]:
        role = await self.get_role_for_member(
            organization_id=organization_id, user_id=user_id
        )
        organization = await self._organizations.get_by_id(organization_id)
        if organization is None:
            raise OrganizationNotFoundError("Organization not found")
        return organization, role

    async def list_for_user(self, user_id: UUID) -> Memberships:
        memberships = await self._organizations.list_memberships_for_user(user_id)
        return [(org, member.role) for member, org in memberships]

    async def rename(
        self, *, organization_id: UUID, name: str, actor_id: UUID
    ) -> Organization:
        organization = await self._organizations.get_by_id(organization_id)
        if organization is None:
            raise OrganizationNotFoundError("Organization not found")
        old_name = organization.name
        await self._organizations.update_name(organization, name=name)
        await self._audit.record(
            organization_id=organization_id,
            actor_id=actor_id,
            action="organization.updated",
            resource_type="organization",
            resource_id=organization_id,
            changes={"name": {"from": old_name, "to": name}},
        )
        return organization

    async def list_members(
        self, organization_id: UUID
    ) -> list[tuple[OrganizationMember, User]]:
        return await self._organizations.list_members(organization_id)

    async def invite(
        self,
        *,
        organization_id: UUID,
        email: str,
        role: Role,
        invited_by_user_id: UUID,
    ) -> IssuedInvitation:
        existing_user = await self._users.get_by_email(email)
        if existing_user is not None:
            existing_membership = await self._organizations.get_membership(
                organization_id=organization_id, user_id=existing_user.id
            )
            if existing_membership is not None:
                raise AlreadyMemberError(
                    "This user is already a member of the organization"
                )
        if (
            await self._invitations.get_active_by_email(
                organization_id=organization_id, email=email
            )
            is not None
        ):
            raise AlreadyMemberError(
                "An active invitation already exists for this email"
            )

        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + INVITATION_TTL
        invitation = await self._invitations.create(
            organization_id=organization_id,
            email=email,
            role=role,
            token_hash=_hash_token(token),
            invited_by_user_id=invited_by_user_id,
            expires_at=expires_at,
        )
        await self._audit.record(
            organization_id=organization_id,
            actor_id=invited_by_user_id,
            action="organization.member_invited",
            resource_type="invitation",
            resource_id=invitation.id,
            changes={
                "email": {"from": None, "to": email},
                "role": {"from": None, "to": role.value},
            },
        )
        return IssuedInvitation(invitation=invitation, token=token)

    async def accept_invitation(
        self, *, token: str, accepting_user_id: UUID
    ) -> tuple[UUID, Role]:
        now = datetime.now(UTC)
        invitation = await self._invitations.get_active_by_hash(_hash_token(token))
        if invitation is None or invitation.expires_at < now:
            raise InvitationInvalidError("Invitation is invalid or expired")

        accepting_user = await self._users.get_by_id(accepting_user_id)
        if accepting_user is None:
            raise InvitationInvalidError("Invitation is invalid or expired")
        if invitation.email.lower() != accepting_user.email.lower():
            raise InvitationEmailMismatchError(
                "This invitation was sent to a different email address"
            )
        if (
            await self._organizations.get_membership(
                organization_id=invitation.organization_id, user_id=accepting_user_id
            )
            is not None
        ):
            raise AlreadyMemberError("Already a member of this organization")

        await self._organizations.add_member(
            organization_id=invitation.organization_id,
            user_id=accepting_user_id,
            role=invitation.role,
        )
        await self._invitations.mark_accepted(invitation, at=now)
        await self._audit.record(
            organization_id=invitation.organization_id,
            actor_id=accepting_user_id,
            action="organization.invitation_accepted",
            resource_type="organization_member",
            resource_id=accepting_user_id,
        )
        return invitation.organization_id, invitation.role

    async def update_member_role(
        self,
        *,
        organization_id: UUID,
        target_user_id: UUID,
        role: Role,
        actor_id: UUID,
    ) -> None:
        member = await self._organizations.get_membership(
            organization_id=organization_id, user_id=target_user_id
        )
        if member is None:
            raise MemberNotFoundError("Member not found")
        if member.role == Role.OWNER and role != Role.OWNER:
            await self._require_not_last_owner(organization_id)
        old_role = member.role
        await self._organizations.update_member_role(member, role=role)
        await self._audit.record(
            organization_id=organization_id,
            actor_id=actor_id,
            action="organization.member_role_changed",
            resource_type="organization_member",
            resource_id=target_user_id,
            changes={"role": {"from": old_role.value, "to": role.value}},
        )

    async def remove_member(
        self, *, organization_id: UUID, target_user_id: UUID, actor_id: UUID
    ) -> None:
        member = await self._organizations.get_membership(
            organization_id=organization_id, user_id=target_user_id
        )
        if member is None:
            raise MemberNotFoundError("Member not found")
        if member.role == Role.OWNER:
            await self._require_not_last_owner(organization_id)
        await self._organizations.remove_member(member)
        await self._audit.record(
            organization_id=organization_id,
            actor_id=actor_id,
            action="organization.member_removed",
            resource_type="organization_member",
            resource_id=target_user_id,
        )

    async def _require_not_last_owner(self, organization_id: UUID) -> None:
        if await self._organizations.count_owners(organization_id) <= 1:
            raise LastOwnerError("An organization must have at least one owner")
