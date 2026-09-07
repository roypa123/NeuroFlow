"""DI wiring for the auth module. See docs/08-backend-architecture.md #8.4."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.api.deps import SessionDep
from app.modules.auth.controller import AuthController
from app.modules.auth.repository import (
    PasswordResetTokenRepository,
    RefreshTokenRepository,
)
from app.modules.auth.service import AuthService
from app.modules.organizations.dependencies import OrganizationServiceDep
from app.modules.users.repository import UserRepository


def get_auth_service(
    session: SessionDep, organizations: OrganizationServiceDep
) -> AuthService:
    return AuthService(
        users=UserRepository(session),
        organizations=organizations,
        refresh_tokens=RefreshTokenRepository(session),
        password_reset_tokens=PasswordResetTokenRepository(session),
    )


def get_auth_controller(
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthController:
    return AuthController(service)


AuthControllerDep = Annotated[AuthController, Depends(get_auth_controller)]
