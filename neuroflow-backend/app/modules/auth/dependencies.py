"""DI wiring for the auth module. See docs/08-backend-architecture.md #8.4."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.api.deps import SessionDep
from app.modules.auth.controller import AuthController
from app.modules.auth.repository import RefreshTokenRepository
from app.modules.auth.service import AuthService
from app.modules.organizations.repository import OrganizationRepository
from app.modules.projects.repository import ProjectRepository
from app.modules.users.repository import UserRepository


def get_auth_service(session: SessionDep) -> AuthService:
    return AuthService(
        users=UserRepository(session),
        organizations=OrganizationRepository(session),
        projects=ProjectRepository(session),
        refresh_tokens=RefreshTokenRepository(session),
    )


def get_auth_controller(
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthController:
    return AuthController(service)


AuthControllerDep = Annotated[AuthController, Depends(get_auth_controller)]
