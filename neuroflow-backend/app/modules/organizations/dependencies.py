"""DI wiring for the organizations module. See
docs/08-backend-architecture.md #8.4."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.api.deps import SessionDep
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.organizations.controller import OrganizationController
from app.modules.organizations.repository import (
    InvitationRepository,
    OrganizationRepository,
)
from app.modules.organizations.service import OrganizationService
from app.modules.projects.repository import ProjectRepository
from app.modules.users.repository import UserRepository


def get_organization_service(session: SessionDep) -> OrganizationService:
    # Constructs AuditService directly (not via audit.dependencies) so this
    # module never imports audit's DI wiring -- audit/dependencies.py
    # imports *this* module (to build the OrganizationService an audit-log
    # read needs for its membership check), and a wiring-layer import back
    # the other way would be a cycle. The service layer itself has no such
    # constraint: organizations/service.py already imports audit/service.py
    # directly, which is fine since audit/service.py imports nothing here.
    audit = AuditService(AuditRepository(session))
    return OrganizationService(
        organizations=OrganizationRepository(session),
        invitations=InvitationRepository(session),
        projects=ProjectRepository(session),
        users=UserRepository(session),
        audit=audit,
    )


OrganizationServiceDep = Annotated[
    OrganizationService, Depends(get_organization_service)
]


def get_organization_controller(
    service: OrganizationServiceDep,
) -> OrganizationController:
    return OrganizationController(service)


OrganizationControllerDep = Annotated[
    OrganizationController, Depends(get_organization_controller)
]
