"""Schedule business rules and the lock-guarded tick. See docs/09-domain-
modules.md #9.12.

Two layers of protection against double-firing, deliberately both present
even though the second alone is sufficient: a Redis `SET NX EX` fast-path
lock avoids two worker processes even querying the table in the same
second, and `ScheduleRepository.claim_due`'s `SELECT ... FOR UPDATE SKIP
LOCKED` is what actually *guarantees* correctness -- a concurrent tick
simply skips any row already locked by another transaction, so a
duplicate scheduler cannot double-fire even if the Redis lock fails. Not
belt-and-braces theater: double-firing a billing workflow is not a
recoverable class of bug.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from croniter import croniter
from redis.asyncio import Redis

from app.core.database import session_scope
from app.core.logging import get_logger
from app.modules.executions.repository import ExecutionRepository
from app.modules.schedules.exceptions import InvalidCronExpressionError
from app.modules.schedules.models import Schedule
from app.modules.schedules.repository import ScheduleRepository
from app.modules.workflows.repository import WorkflowRepository, WorkflowVersionRepository

logger = get_logger(__name__)

_TICK_LOCK_KEY = "schedules:tick:lock"
_TICK_LOCK_TTL_SECONDS = 55


def compute_next_run(cron: str, *, after: datetime) -> datetime:
    try:
        return croniter(cron, after).get_next(datetime)  # type: ignore[no-any-return]
    except (ValueError, KeyError) as exc:
        raise InvalidCronExpressionError(f"Invalid cron expression: {cron}") from exc


class ScheduleService:
    def __init__(self, repository: ScheduleRepository) -> None:
        self._repository = repository

    async def register(
        self,
        *,
        workflow_id: UUID,
        node_id: str,
        cron: str,
        timezone: str,
        catch_up: bool,
    ) -> Schedule:
        next_run_at = compute_next_run(cron, after=datetime.now(UTC))
        return await self._repository.create(
            workflow_id=workflow_id,
            node_id=node_id,
            cron=cron,
            timezone=timezone,
            catch_up=catch_up,
            next_run_at=next_run_at,
        )

    async def unregister(self, workflow_id: UUID) -> None:
        await self._repository.delete_for_workflow(workflow_id)

    async def list_for_workflow(self, workflow_id: UUID) -> list[Schedule]:
        return await self._repository.list_for_workflow(workflow_id)


async def try_acquire_tick_lock(redis: Redis) -> bool:
    acquired = await redis.set(_TICK_LOCK_KEY, "1", ex=_TICK_LOCK_TTL_SECONDS, nx=True)
    return bool(acquired)


async def claim_and_advance_due(
    repository: ScheduleRepository, *, now: datetime
) -> list[Schedule]:
    """Claims every due, enabled schedule and advances `next_run_at` in the
    same transaction the caller commits -- the two must never be split
    across transactions, or a crash between them re-fires the same window
    forever. Known simplification (`catch_up` is stored but a missed
    window still fires once, jumping straight to the next future
    occurrence, rather than backfilling every missed run -- full backfill
    is a natural follow-up once a real deployment needs it)."""
    due = await repository.claim_due(now=now)
    claimed: list[Schedule] = []
    for schedule in due:
        next_run_at = compute_next_run(schedule.cron, after=now)
        await repository.record_run(schedule, ran_at=now, next_run_at=next_run_at)
        claimed.append(schedule)
    return claimed


async def schedule_tick(ctx: dict[str, Any], *_args: Any, **_kwargs: Any) -> None:
    """arq cron job, registered in `app.worker`. Fires every enabled,
    due schedule's workflow. No authenticated actor exists for a
    time-triggered run, so the execution is created directly (the same
    actor-free pattern as webhook ingress and sub-workflow calls) rather
    than through `ExecutionService.create_and_enqueue`."""
    redis: Redis = ctx["redis"]
    if not await try_acquire_tick_lock(redis):
        return
    async with session_scope() as session:
        schedule_repo = ScheduleRepository(session)
        workflow_repo = WorkflowRepository(session)
        version_repo = WorkflowVersionRepository(session)
        execution_repo = ExecutionRepository(session)

        due = await claim_and_advance_due(schedule_repo, now=datetime.now(UTC))
        for schedule in due:
            workflow = await workflow_repo.get_by_id(schedule.workflow_id)
            if workflow is None:
                continue
            version = None
            if workflow.active_version_id is not None:
                version = await version_repo.get_by_id(workflow.active_version_id)
            if version is None:
                version = await version_repo.get_latest(workflow.id)
            if version is None:
                continue
            execution = await execution_repo.create(
                workflow_id=workflow.id,
                workflow_version_id=version.id,
                project_id=workflow.project_id,
                mode="schedule",
                trigger_data={"scheduledAt": datetime.now(UTC).isoformat()},
                created_by=None,
                created_at=datetime.now(UTC),
            )
            logger.info(
                "schedule.fired", schedule_id=str(schedule.id), execution_id=str(execution.id)
            )
            await redis.enqueue_job("run_execution", execution.id)
