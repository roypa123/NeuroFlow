"""Pydantic schemas for audit logs. See docs/09-domain-modules.md #9.14."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.schema import CamelModel


class AuditLogRead(CamelModel):
    id: UUID
    organization_id: UUID
    actor_id: UUID | None
    action: str
    resource_type: str
    resource_id: UUID
    changes: dict[str, Any] | None
    created_at: datetime
