"""DI wiring for the auth module. See docs/08-backend-architecture.md #8.4."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.api.deps import SessionDep
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.auth.controller import ApiKeyController, AuthController
from app.modules.auth.repository import (
    ApiKeyRepository,
    PasswordResetTokenRepository,
    RefreshTokenRepository,
)
from app.modules.auth.service import AuthService
from app.modules.organizations.dependencies import OrganizationServiceDep
from app.modules.users.repository import UserRepository


def get_auth_service(
    session: SessionDep, organizations: OrganizationServiceDep
) -> AuthService:
    # AuditService built directly here, not via audit.dependencies -- same
    # cycle-avoidance reason documented in
    # organizations/dependencies.py's get_organization_service.
    audit = AuditService(AuditRepository(session))
    return AuthService(
        users=UserRepository(session),
        organizations=organizations,
        refresh_tokens=RefreshTokenRepository(session),
        password_reset_tokens=PasswordResetTokenRepository(session),
        api_keys=ApiKeyRepository(session),
        audit=audit,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def get_auth_controller(service: AuthServiceDep) -> AuthController:
    return AuthController(service)


AuthControllerDep = Annotated[AuthController, Depends(get_auth_controller)]


def get_api_key_controller(
    service: AuthServiceDep, organizations: OrganizationServiceDep
) -> ApiKeyController:
    return ApiKeyController(service, organizations)


ApiKeyControllerDep = Annotated[ApiKeyController, Depends(get_api_key_controller)]
