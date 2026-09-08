"""SQL access for webhook registrations. No business rules -- see
docs/08-backend-architecture.md #8.1's test for this layer."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.webhooks.models import WebhookRegistration


class WebhookRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        workflow_id: UUID,
        node_id: str,
        path: str,
        method: str,
        auth: dict[str, Any] | None,
        response_mode: str,
        is_test: bool = False,
        expires_at: datetime | None = None,
    ) -> WebhookRegistration:
        row = WebhookRegistration(
            workflow_id=workflow_id,
            node_id=node_id,
            path=path,
            method=method,
            auth=auth,
            response_mode=response_mode,
            is_test=is_test,
            expires_at=expires_at,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def find_active(
        self, *, path: str, method: str, is_test: bool, now: datetime
    ) -> WebhookRegistration | None:
        stmt = select(WebhookRegistration).where(
            WebhookRegistration.path == path,
            WebhookRegistration.method == method,
            WebhookRegistration.is_test == is_test,
            or_(
                WebhookRegistration.expires_at.is_(None),
                WebhookRegistration.expires_at > now,
            ),
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_workflow(self, workflow_id: UUID) -> list[WebhookRegistration]:
        stmt = select(WebhookRegistration).where(
            WebhookRegistration.workflow_id == workflow_id,
            WebhookRegistration.is_test.is_(False),
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_for_workflow(self, workflow_id: UUID) -> None:
        rows = await self.list_for_workflow(workflow_id)
        for row in rows:
            await self._session.delete(row)
        await self._session.flush()
