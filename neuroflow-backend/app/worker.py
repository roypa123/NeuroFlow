"""arq worker entrypoint: `arq app.worker.WorkerSettings`.

This is the SECOND entrypoint into the same image as app.main -- see
docs/03-system-architecture.md #3.3. The API and worker are deliberately
identical images with different commands, so there is no "works in the
API, missing in the worker" class of bug entirely.

Phase 4 fills this in for real: `run_execution` is the job the API
enqueues by name (`pool.enqueue_job("run_execution", execution_id)`,
never by importing this module -- see docs/12-execution-engine.md), and
the recovery sweeper/watchdog run on a schedule per #12.11.
"""
from __future__ import annotations

from typing import Any, cast

from arq import cron
from arq.connections import RedisSettings
from arq.typing import WorkerCoroutine

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.engine.registry import build_runtime_registry
from app.engine.run_execution import run_execution
from app.engine.sweeper import recovery_sweep, watchdog_sweep

logger = get_logger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    configure_logging()
    ctx["registry"] = build_runtime_registry()
    logger.info("worker.startup", node_types=len(ctx["registry"].all_descriptors()))


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("worker.shutdown")


_SWEEP_MINUTES = set(range(0, 60, 5))
# mypy's structural match against arq's WorkerCoroutine Protocol is oddly
# sensitive to watchdog_sweep's unused-ctx param name; an explicit cast is
# clearer here than a type: ignore.
_watchdog_coroutine = cast(WorkerCoroutine, watchdog_sweep)

_CRON_JOBS = [
    cron(recovery_sweep, minute=_SWEEP_MINUTES, run_at_startup=False),
    cron(_watchdog_coroutine, minute=_SWEEP_MINUTES, run_at_startup=False),
]


class WorkerSettings:
    """arq reads this class by name (`arq app.worker.WorkerSettings`)."""

    functions: list[Any] = [run_execution]
    cron_jobs = _CRON_JOBS
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(str(get_settings().redis_url))
    max_jobs = get_settings().worker_max_jobs
