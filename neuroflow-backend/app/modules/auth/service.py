"""Auth business rules: registration, credential verification, refresh
token issuance/rotation, and password reset.

Framework-agnostic -- raises AppError subclasses, never HTTPException, so it
stays callable outside of a request (e.g. from the worker) even though
nothing there needs it yet. See docs/08-backend-architecture.md #8.1.
"""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.permissions import Permission, Role
from app.core.security import (
    create_access_token,
    hash_opaque_token,
    hash_password,
    verify_password,
)
from app.core.uuid7 import uuid7
from app.modules.audit.service import AuditService
from app.modules.auth.exceptions import (
    ApiKeyNotFoundError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidPasswordResetTokenError,
    InvalidRefreshTokenError,
)
from app.modules.auth.models import ApiKey
from app.modules.auth.repository import (
    ApiKeyRepository,
    PasswordResetTokenRepository,
    RefreshTokenRepository,
)
from app.modules.organizations.models import Organization
from app.modules.organizations.service import OrganizationService
from app.modules.users.models import User
from app.modules.users.repository import UserRepository

PASSWORD_RESET_TTL = timedelta(hours=1)
API_KEY_PREFIX = "nf_live_"  # noqa: S105 -- a public marker, not a secret

Memberships = list[tuple[Organization, Role]]

logger = get_logger(__name__)


@dataclass(slots=True, frozen=True)
class Session:
    user: User
    organizations: Memberships
    access_token: str
    access_token_expires_in: int
    refresh_token: str
    refresh_token_expires_at: datetime


class AuthService:
    def __init__(
        self,
        users: UserRepository,
        organizations: OrganizationService,
        refresh_tokens: RefreshTokenRepository,
        password_reset_tokens: PasswordResetTokenRepository,
        api_keys: ApiKeyRepository,
        audit: AuditService,
    ) -> None:
        self._users = users
        self._organizations = organizations
        self._refresh_tokens = refresh_tokens
        self._password_reset_tokens = password_reset_tokens
        self._api_keys = api_keys
        self._audit = audit

    async def register(self, *, email: str, password: str, name: str) -> Session:
        if await self._users.get_by_email(email) is not None:
            raise EmailAlreadyRegisteredError(
                "An account with this email already exists"
            )

        user = await self._users.create(
            email=email, password_hash=hash_password(password), name=name
        )
        organization = await self._organizations.create_with_owner(
            name=f"{name}'s Organization", owner_user_id=user.id
        )
        return await self._issue_session(user, [(organization, Role.OWNER)])

    async def login(self, *, email: str, password: str) -> Session:
        user = await self._users.get_by_email(email)
        if user is None or user.password_hash is None:
            raise InvalidCredentialsError("Invalid email or password")
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password")

        organizations = await self._organizations.list_for_user(user.id)
        await self._users.touch_last_login(user, at=datetime.now(UTC))
        return await self._issue_session(user, organizations)

    async def refresh(self, *, refresh_token: str) -> Session:
        now = datetime.now(UTC)
        stored = await self._refresh_tokens.get_by_hash(
            hash_opaque_token(refresh_token)
        )
        if stored is None or stored.expires_at < now:
            raise InvalidRefreshTokenError("Refresh token is invalid or expired")

        if stored.revoked_at is not None:
            # This exact token was already rotated away once. Presenting it
            # again means a copy of it leaked and is being replayed -- we
            # can no longer tell which caller is the legitimate one, so the
            # whole rotation family is killed and everyone must re-login.
            #
            # The explicit commit (see RefreshTokenRepository.commit's
            # docstring) matters here specifically: this branch is about to
            # raise, and get_session()'s rollback-on-exception would
            # otherwise silently undo the very revocation that makes this
            # a real security control rather than a no-op.
            await self._refresh_tokens.revoke_family(stored.family_id, at=now)
            await self._refresh_tokens.commit()
            logger.warning(
                "auth.refresh_token_reuse_detected", family_id=str(stored.family_id)
            )
            raise InvalidRefreshTokenError("Refresh token is invalid or expired")

        user = await self._users.get_by_id(stored.user_id)
        if user is None:
            raise InvalidRefreshTokenError("Refresh token is invalid or expired")

        await self._refresh_tokens.revoke(stored, at=now)
        organizations = await self._organizations.list_for_user(user.id)
        return await self._issue_session(
            user, organizations, family_id=stored.family_id
        )

    async def logout(self, *, refresh_token: str) -> None:
        stored = await self._refresh_tokens.get_by_hash(
            hash_opaque_token(refresh_token)
        )
        if stored is not None and stored.revoked_at is None:
            await self._refresh_tokens.revoke(stored, at=datetime.now(UTC))

    async def get_current_user(
        self, user_id: UUID
    ) -> tuple[User, Memberships] | None:
        user = await self._users.get_by_id(user_id)
        if user is None:
            return None
        return user, await self._organizations.list_for_user(user_id)

    async def request_password_reset(self, *, email: str) -> None:
        user = await self._users.get_by_email(email)
        if user is None:
            return  # always looks like success -- no user enumeration

        token = secrets.token_urlsafe(32)
        await self._password_reset_tokens.create(
            user_id=user.id,
            token_hash=hash_opaque_token(token),
            expires_at=datetime.now(UTC) + PASSWORD_RESET_TTL,
        )
        # No outbound email infra exists in this codebase yet -- logging the
        # token is the same limitation the endpoint already had as a stub.
        logger.info("auth.password_reset_requested", user_id=str(user.id))

    async def reset_password(self, *, token: str, new_password: str) -> None:
        now = datetime.now(UTC)
        stored = await self._password_reset_tokens.get_active_by_hash(
            hash_opaque_token(token)
        )
        if stored is None or stored.expires_at < now:
            raise InvalidPasswordResetTokenError("Reset token is invalid or expired")

        user = await self._users.get_by_id(stored.user_id)
        if user is None:
            raise InvalidPasswordResetTokenError("Reset token is invalid or expired")

        await self._users.set_password(user, password_hash=hash_password(new_password))
        await self._password_reset_tokens.mark_used(stored, at=now)
        # Resetting the password ends every existing session -- if the
        # reset was needed because credentials leaked, a session started
        # with the old password must not survive it.
        await self._refresh_tokens.revoke_all_for_user(user.id, at=now)

    async def issue_api_key(
        self,
        *,
        organization_id: UUID,
        user_id: UUID,
        name: str,
        scopes: list[Permission],
        expires_at: datetime | None,
    ) -> tuple[ApiKey, str]:
        raw = f"{API_KEY_PREFIX}{secrets.token_urlsafe(32)}"
        api_key = await self._api_keys.create(
            organization_id=organization_id,
            user_id=user_id,
            name=name,
            key_hash=hash_opaque_token(raw),
            prefix=raw[: len(API_KEY_PREFIX) + 4],
            scopes=[scope.value for scope in scopes],
            expires_at=expires_at,
        )
        await self._audit.record(
            organization_id=organization_id,
            actor_id=user_id,
            action="auth.api_key_issued",
            resource_type="api_key",
            resource_id=api_key.id,
            changes={"name": {"from": None, "to": name}},
        )
        return api_key, raw

    async def list_api_keys(self, organization_id: UUID) -> list[ApiKey]:
        return await self._api_keys.list_for_organization(organization_id)

    async def revoke_api_key(
        self, *, organization_id: UUID, key_id: UUID, actor_id: UUID
    ) -> None:
        api_key = await self._api_keys.get_by_id(key_id)
        if api_key is None or api_key.organization_id != organization_id:
            raise ApiKeyNotFoundError("API key not found")
        await self._api_keys.revoke(api_key, at=datetime.now(UTC))
        await self._audit.record(
            organization_id=organization_id,
            actor_id=actor_id,
            action="auth.api_key_revoked",
            resource_type="api_key",
            resource_id=key_id,
        )

    async def _issue_session(
        self, user: User, organizations: Memberships, *, family_id: UUID | None = None
    ) -> Session:
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
            token_hash=hash_opaque_token(refresh_token),
            family_id=family_id or uuid7(),
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
