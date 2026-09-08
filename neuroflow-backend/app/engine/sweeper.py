"""Recovery sweeper and watchdog -- arq cron jobs. See
docs/12-execution-engine.md #12.11.

Simplification: the watchdog uses the global `max_execution_seconds`
setting rather than each workflow's own `settings.timeoutSeconds` override
-- per-workflow timeout enforcement during the run itself (not just by the
watchdog after the fact) is a natural follow-up once a workflow actually
sets a non-default value in practice.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.core.config import get_settings
from app.core.database import session_scope
from app.core.logging import get_logger
from app.modules.executions.repository import (
    ExecutionDataRepository,
    ExecutionRepository,
    NodeExecutionRepository,
)
from app.modules.executions.waiting import apply_resume

logger = get_logger(__name__)

QUEUED_STALE_AFTER = timedelta(minutes=5)
WATCHDOG_GRACE_SECONDS = 60


async def recovery_sweep(ctx: dict[str, Any], *_args: Any, **_kwargs: Any) -> None:
    """Re-enqueues `queued` executions older than 5 minutes -- covers a
    Redis flush that lost the original arq job but left the DB row behind."""
    cutoff = datetime.now(UTC) - QUEUED_STALE_AFTER
    async with session_scope() as session:
        repo = ExecutionRepository(session)
        stale = await repo.list_stale_queued(older_than=cutoff)
        for execution in stale:
            logger.warning(
                "execution.recovery_reenqueue", execution_id=str(execution.id)
            )
            await ctx["redis"].enqueue_job("run_execution", execution.id)


async def watchdog_sweep(_ctx: dict[str, Any], *_args: Any, **_kwargs: Any) -> None:
    """Marks executions running longer than their timeout + grace as
    `error` with `code: "execution.timeout"`."""
    cutoff = datetime.now(UTC) - timedelta(
        seconds=get_settings().max_execution_seconds + WATCHDOG_GRACE_SECONDS
    )
    async with session_scope() as session:
        repo = ExecutionRepository(session)
        stuck = await repo.list_stuck_running(started_before=cutoff)
        for execution in stuck:
            logger.warning("execution.watchdog_timeout", execution_id=str(execution.id))
            timeout_error = {
                "message": "Execution exceeded its timeout",
                "code": "execution.timeout",
            }
            await repo.finish(
                execution, status="error", at=datetime.now(UTC), error=timeout_error
            )


async def resume_sweep(ctx: dict[str, Any], *_args: Any, **_kwargs: Any) -> None:
    """Time-based half of suspend/resume (docs/12-execution-engine.md
    #12.5): re-enqueues `waiting` executions whose `resume_after` has
    passed. No token check -- `list_due_for_resume` already selected only
    rows past their deadline, and unlike the event-based `POST
    .../resume` endpoint there is no external caller to authenticate."""
    async with session_scope() as session:
        execution_repo = ExecutionRepository(session)
        node_exec_repo = NodeExecutionRepository(session)
        data_repo = ExecutionDataRepository(session)
        due = await execution_repo.list_due_for_resume(now=datetime.now(UTC))
        for execution in due:
            logger.info("execution.resume_due", execution_id=str(execution.id))
            await apply_resume(
                execution,
                None,
                node_executions=node_exec_repo,
                data=data_repo,
                queue=ctx["redis"],
            )
