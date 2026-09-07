"""Audit business rules. Framework-agnostic -- see
docs/08-backend-architecture.md #8.1.

Called inline from other modules' services, in the same session/transaction
as the action being audited: a rollback of the action must also roll back
its audit entry, never leave a phantom record behind. See
docs/09-domain-modules.md #9.14.
"""
from __future__ import annotations

from typing import Any
from uuid import UUID

from app.modules.audit.models import AuditLog
from app.modules.audit.repository import AuditRepository


class AuditService:
    def __init__(self, repo: AuditRepository) -> None:
        self._repo = repo

    async def record(
        self,
        *,
        organization_id: UUID,
        actor_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: UUID,
        changes: dict[str, Any] | None = None,
    ) -> AuditLog:
        return await self._repo.create(
            organization_id=organization_id,
            actor_id=actor_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            changes=changes,
        )

    async def list_for_organization(
        self, organization_id: UUID, *, limit: int = 100
    ) -> list[AuditLog]:
        return await self._repo.list_for_organization(organization_id, limit=limit)
