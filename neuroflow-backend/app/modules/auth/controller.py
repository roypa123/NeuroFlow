"""Auth orchestration: map service results to response schemas.

No SQL and no HTTP-transport concerns here (cookies are the router's job,
since they are wire mechanics rather than a domain rule) -- see
docs/08-backend-architecture.md #8.1's test for this layer.
"""
from __future__ import annotations

from uuid import UUID

from app.api.deps import RequestContext
from app.core.exceptions import NotFoundError
from app.core.permissions import Permission, require
from app.modules.auth.schemas import (
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyRead,
    LoginResponse,
    TokenResponse,
)
from app.modules.auth.service import AuthService, Memberships, Session
from app.modules.organizations.schemas import OrganizationMembershipRead
from app.modules.organizations.service import OrganizationService
from app.modules.users.models import User
from app.modules.users.schemas import UserRead


def _build_user_read(user: User, organizations: Memberships) -> UserRead:
    return UserRead(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
        organizations=[
            OrganizationMembershipRead(id=org.id, name=org.name, role=role)
            for org, role in organizations
        ],
    )


class AuthController:
    def __init__(self, service: AuthService) -> None:
        self._service = service

    async def register(
        self, *, email: str, password: str, name: str
    ) -> tuple[LoginResponse, Session]:
        session = await self._service.register(
            email=email, password=password, name=name
        )
        return self._to_login_response(session), session

    async def login(
        self, *, email: str, password: str
    ) -> tuple[LoginResponse, Session]:
        session = await self._service.login(email=email, password=password)
        return self._to_login_response(session), session

    async def refresh(self, *, refresh_token: str) -> tuple[TokenResponse, Session]:
        session = await self._service.refresh(refresh_token=refresh_token)
        response = TokenResponse(
            access_token=session.access_token,
            expires_in=session.access_token_expires_in,
        )
        return response, session

    async def logout(self, *, refresh_token: str) -> None:
        await self._service.logout(refresh_token=refresh_token)

    async def forgot_password(self, *, email: str) -> None:
        await self._service.request_password_reset(email=email)

    async def reset_password(self, *, token: str, new_password: str) -> None:
        await self._service.reset_password(token=token, new_password=new_password)

    async def me(self, user_id: UUID) -> UserRead:
        result = await self._service.get_current_user(user_id)
        if result is None:
            raise NotFoundError("User not found")
        user, organizations = result
        return _build_user_read(user, organizations)

    def _to_login_response(self, session: Session) -> LoginResponse:
        return LoginResponse(
            access_token=session.access_token,
            expires_in=session.access_token_expires_in,
            user=_build_user_read(session.user, session.organizations),
        )


class ApiKeyController:
    """Separate from AuthController: this is org-scoped resource
    management (list/create/revoke a key), not session/credential
    handling, even though both live in the `auth` module per
    docs/09-domain-modules.md #9.2."""

    def __init__(
        self, service: AuthService, organizations: OrganizationService
    ) -> None:
        self._service = service
        self._organizations = organizations

    async def list_for_organization(
        self, ctx: RequestContext, organization_id: UUID
    ) -> list[ApiKeyRead]:
        role = await self._organizations.get_role_for_member(
            organization_id=organization_id, user_id=ctx.user_id
        )
        require(role, Permission.API_KEY_MANAGE, scopes=ctx.scopes)
        keys = await self._service.list_api_keys(organization_id)
        return [ApiKeyRead.model_validate(key) for key in keys]

    async def create(
        self, ctx: RequestContext, organization_id: UUID, payload: ApiKeyCreate
    ) -> ApiKeyCreated:
        role = await self._organizations.get_role_for_member(
            organization_id=organization_id, user_id=ctx.user_id
        )
        require(role, Permission.API_KEY_MANAGE, scopes=ctx.scopes)
        api_key, raw = await self._service.issue_api_key(
            organization_id=organization_id,
            user_id=ctx.user_id,
            name=payload.name,
            scopes=payload.scopes,
            expires_at=payload.expires_at,
        )
        return ApiKeyCreated(
            id=api_key.id,
            name=api_key.name,
            prefix=api_key.prefix,
            scopes=[Permission(s) for s in api_key.scopes],
            last_used_at=api_key.last_used_at,
            expires_at=api_key.expires_at,
            created_at=api_key.created_at,
            key=raw,
        )

    async def revoke(
        self, ctx: RequestContext, organization_id: UUID, key_id: UUID
    ) -> None:
        role = await self._organizations.get_role_for_member(
            organization_id=organization_id, user_id=ctx.user_id
        )
        require(role, Permission.API_KEY_MANAGE, scopes=ctx.scopes)
        await self._service.revoke_api_key(
            organization_id=organization_id, key_id=key_id, actor_id=ctx.user_id
        )
