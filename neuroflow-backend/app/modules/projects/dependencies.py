"""DI wiring for the projects module. See docs/08-backend-architecture.md
#8.4."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.api.deps import SessionDep
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.organizations.dependencies import OrganizationServiceDep
from app.modules.projects.controller import ProjectController
from app.modules.projects.repository import ProjectRepository
from app.modules.projects.service import ProjectService


def get_project_service(
    session: SessionDep, organizations: OrganizationServiceDep
) -> ProjectService:
    # AuditService is built directly here too, for the same reason
    # organizations/dependencies.py builds its own: avoiding a wiring-layer
    # import back into audit/dependencies.py.
    audit = AuditService(AuditRepository(session))
    return ProjectService(
        projects=ProjectRepository(session), organizations=organizations, audit=audit
    )


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]


def get_project_controller(service: ProjectServiceDep) -> ProjectController:
    return ProjectController(service)


ProjectControllerDep = Annotated[ProjectController, Depends(get_project_controller)]
