"""SQL access for schedules. No business rules -- see
docs/08-backend-architecture.md #8.1's test for this layer."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.modules.schedules.models import Schedule


class ScheduleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        workflow_id: UUID,
        node_id: str,
        cron: str,
        timezone: str,
        catch_up: bool,
        next_run_at: datetime,
    ) -> Schedule:
        row = Schedule(
            workflow_id=workflow_id,
            node_id=node_id,
            cron=cron,
            timezone=timezone,
            catch_up=catch_up,
            next_run_at=next_run_at,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_for_workflow(self, workflow_id: UUID) -> list[Schedule]:
        stmt: Select[tuple[Schedule]] = select(Schedule).where(
            Schedule.workflow_id == workflow_id
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_for_workflow(self, workflow_id: UUID) -> None:
        rows = await self.list_for_workflow(workflow_id)
        for row in rows:
            await self._session.delete(row)
        await self._session.flush()

    async def claim_due(self, *, now: datetime) -> list[Schedule]:
        """`SELECT ... FOR UPDATE SKIP LOCKED` -- the belt-and-braces DB
        lock that makes a duplicate scheduler process unable to double-fire
        even if the Redis lock in `ScheduleService.tick` fails. See
        docs/09-domain-modules.md #9.12."""
        stmt = (
            select(Schedule)
            .where(Schedule.is_enabled.is_(True), Schedule.next_run_at <= now)
            .with_for_update(skip_locked=True)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def record_run(
        self, schedule: Schedule, *, ran_at: datetime, next_run_at: datetime
    ) -> None:
        schedule.last_run_at = ran_at
        schedule.next_run_at = next_run_at
        await self._session.flush()
