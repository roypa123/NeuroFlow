"""Audit routes: declarations only -- see docs/08-backend-architecture.md
#8.1. Read-only for now -- no frontend page consumes it yet."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from app.api.deps import RequestContextDep
from app.modules.audit.dependencies import AuditControllerDep
from app.modules.audit.schemas import AuditLogRead

router = APIRouter(prefix="/audit-logs", tags=["audit"])


@router.get("", response_model=list[AuditLogRead])
async def list_audit_logs(
    ctx: RequestContextDep,
    controller: AuditControllerDep,
    organization_id: Annotated[UUID, Query(alias="organizationId")],
) -> list[AuditLogRead]:
    return await controller.list_for_organization(ctx, organization_id)
