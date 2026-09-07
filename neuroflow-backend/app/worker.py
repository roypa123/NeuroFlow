"""arq worker entrypoint: `arq app.worker.WorkerSettings`.

This is the SECOND entrypoint into the same image as app.main -- see
docs/03-system-architecture.md #3.3. The API and worker are deliberately
identical images with different commands, so there is no "works in the API,
missing in the worker" class of bug.

The execution engine (docs/12-execution-engine.md) lands in Phase 4; this
file is deliberately minimal until then -- a real, connectable worker
process rather than a placeholder that would need rewriting, but with no
job functions registered yet.
"""
from __future__ import annotations

from typing import Any

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    configure_logging()
    logger.info("worker.startup")


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("worker.shutdown")


class WorkerSettings:
    """arq reads this class by name (`arq app.worker.WorkerSettings`)."""

    functions: list[Any] = []  # populated by app.engine in Phase 4
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(str(get_settings().redis_url))
    max_jobs = get_settings().worker_max_jobs
