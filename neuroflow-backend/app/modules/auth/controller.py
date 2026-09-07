"""Auth orchestration: map service results to response schemas.

No SQL and no HTTP-transport concerns here (cookies are the router's job,
since they are wire mechanics rather than a domain rule) -- see
docs/08-backend-architecture.md #8.1's test for this layer.
"""
from __future__ import annotations

from uuid import UUID

from app.core.exceptions import NotFoundError
from app.modules.auth.schemas import LoginResponse, TokenResponse
from app.modules.auth.service import AuthService, Memberships, Session
from app.modules.organizations.schemas import OrganizationMembershipRead
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
