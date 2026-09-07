"""DI wiring for the audit module. See docs/08-backend-architecture.md #8.4."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.api.deps import SessionDep
from app.modules.audit.controller import AuditController
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.organizations.dependencies import OrganizationServiceDep


def get_audit_service(session: SessionDep) -> AuditService:
    return AuditService(AuditRepository(session))


AuditServiceDep = Annotated[AuditService, Depends(get_audit_service)]


def get_audit_controller(
    service: AuditServiceDep, organizations: OrganizationServiceDep
) -> AuditController:
    return AuditController(service, organizations)


AuditControllerDep = Annotated[AuditController, Depends(get_audit_controller)]
