"""Auth business rules: registration, credential verification, and refresh
token issuance/rotation.

Framework-agnostic -- raises AppError subclasses, never HTTPException, so it
stays callable outside of a request (e.g. from the worker) even though
nothing there needs it yet. See docs/08-backend-architecture.md #8.1.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.core.config import get_settings
from app.core.permissions import Role
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth.exceptions import (
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
)
from app.modules.auth.repository import RefreshTokenRepository
from app.modules.organizations.models import Organization
from app.modules.organizations.repository import OrganizationRepository
from app.modules.projects.repository import ProjectRepository
from app.modules.users.models import User
from app.modules.users.repository import UserRepository

Memberships = list[tuple[Organization, Role]]


@dataclass(slots=True, frozen=True)
class Session:
    user: User
    organizations: Memberships
    access_token: str
    access_token_expires_in: int
    refresh_token: str
    refresh_token_expires_at: datetime


def _hash_token(token: str) -> str:
    # SHA-256 over a 48-byte random token: the token itself already carries
    # all the entropy, so this is a lookup digest, not a password hash --
    # argon2 (used for passwords) would just add pointless CPU cost here.
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        organizations: OrganizationRepository,
        projects: ProjectRepository,
        refresh_tokens: RefreshTokenRepository,
    ) -> None:
        self._users = users
        self._organizations = organizations
        self._projects = projects
        self._refresh_tokens = refresh_tokens

    async def register(self, *, email: str, password: str, name: str) -> Session:
        if await self._users.get_by_email(email) is not None:
            raise EmailAlreadyRegisteredError(
                "An account with this email already exists"
            )

        user = await self._users.create(
            email=email, password_hash=hash_password(password), name=name
        )
        organization = await self._organizations.create(
            name=f"{name}'s Organization"
        )
        await self._organizations.add_member(
            organization_id=organization.id, user_id=user.id, role=Role.OWNER
        )
        await self._projects.create(organization_id=organization.id, name="Personal")

        return await self._issue_session(user, [(organization, Role.OWNER)])

    async def login(self, *, email: str, password: str) -> Session:
        user = await self._users.get_by_email(email)
        if user is None or user.password_hash is None:
            raise InvalidCredentialsError("Invalid email or password")
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password")

        organizations = await self._memberships_for(user.id)
        await self._users.touch_last_login(user, at=datetime.now(UTC))
        return await self._issue_session(user, organizations)

    async def refresh(self, *, refresh_token: str) -> Session:
        now = datetime.now(UTC)
        stored = await self._refresh_tokens.get_active_by_hash(
            _hash_token(refresh_token)
        )
        if stored is None or stored.expires_at < now:
            raise InvalidRefreshTokenError("Refresh token is invalid or expired")

        user = await self._users.get_by_id(stored.user_id)
        if user is None:
            raise InvalidRefreshTokenError("Refresh token is invalid or expired")

        # Rotate on every use: the presented token becomes single-use, so a
        # stolen-and-replayed cookie is detected the moment the legitimate
        # client refreshes next (it will fail, since its token was just
        # revoked here).
        await self._refresh_tokens.revoke(stored, at=now)
        organizations = await self._memberships_for(user.id)
        return await self._issue_session(user, organizations)

    async def logout(self, *, refresh_token: str) -> None:
        stored = await self._refresh_tokens.get_active_by_hash(
            _hash_token(refresh_token)
        )
        if stored is not None:
            await self._refresh_tokens.revoke(stored, at=datetime.now(UTC))

    async def get_current_user(
        self, user_id: UUID
    ) -> tuple[User, Memberships] | None:
        user = await self._users.get_by_id(user_id)
        if user is None:
            return None
        return user, await self._memberships_for(user_id)

    async def _memberships_for(self, user_id: UUID) -> Memberships:
        memberships = await self._organizations.list_memberships_for_user(user_id)
        return [(org, member.role) for member, org in memberships]

    async def _issue_session(self, user: User, organizations: Memberships) -> Session:
        settings = get_settings()
        primary_org, primary_role = organizations[0] if organizations else (None, None)

        access_token = create_access_token(
            user_id=user.id,
            org_id=primary_org.id if primary_org else None,
            role=primary_role.value if primary_role else None,
            jti=secrets.token_urlsafe(16),
        )
        refresh_token = secrets.token_urlsafe(48)
        expires_at = datetime.now(UTC) + settings.refresh_token_ttl
        await self._refresh_tokens.create(
            user_id=user.id,
            token_hash=_hash_token(refresh_token),
            expires_at=expires_at,
        )
        return Session(
            user=user,
            organizations=organizations,
            access_token=access_token,
            access_token_expires_in=int(settings.access_token_ttl.total_seconds()),
            refresh_token=refresh_token,
            refresh_token_expires_at=expires_at,
        )
