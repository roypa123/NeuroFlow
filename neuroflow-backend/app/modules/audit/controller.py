"""Audit orchestration: authorize, call the service, map to response
schemas. See docs/08-backend-architecture.md #8.1."""
from __future__ import annotations

from uuid import UUID

from app.api.deps import RequestContext
from app.core.permissions import Permission, require
from app.modules.audit.schemas import AuditLogRead
from app.modules.audit.service import AuditService
from app.modules.organizations.service import OrganizationService


class AuditController:
    def __init__(
        self, service: AuditService, organizations: OrganizationService
    ) -> None:
        self._service = service
        self._organizations = organizations

    async def list_for_organization(
        self, ctx: RequestContext, organization_id: UUID
    ) -> list[AuditLogRead]:
        role = await self._organizations.get_role_for_member(
            organization_id=organization_id, user_id=ctx.user_id
        )
        require(role, Permission.AUDIT_READ, scopes=ctx.scopes)
        logs = await self._service.list_for_organization(organization_id)
        return [AuditLogRead.model_validate(log) for log in logs]
