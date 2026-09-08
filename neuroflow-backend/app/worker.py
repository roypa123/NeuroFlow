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
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.engine.registry import build_runtime_registry
from app.engine.run_execution import run_execution
from app.engine.sweeper import recovery_sweep, resume_sweep, watchdog_sweep

# The worker's own import chain (engine -> executions/workflows
# repositories) never touches app.modules.users/organizations/audit/auth,
# but Execution/Workflow declare string ForeignKeys into their tables
# ("users.id", etc.). SQLAlchemy only resolves those lazily, against
# whichever models have actually been imported into Base.metadata in this
# process -- so, exactly like alembic/env.py, every model module must be
# imported here explicitly, or the first real query raises
# NoReferencedTableError. The API process gets this incidentally (auth's
# router pulls users.models in transitively); the worker does not.
from app.modules.audit import models as _audit_models  # noqa: F401
from app.modules.auth import models as _auth_models  # noqa: F401
from app.modules.credentials import models as _credentials_models  # noqa: F401
from app.modules.organizations import models as _organizations_models  # noqa: F401
from app.modules.projects import models as _projects_models  # noqa: F401
from app.modules.schedules import models as _schedules_models  # noqa: F401
from app.modules.schedules.service import schedule_tick
from app.modules.users import models as _users_models  # noqa: F401
from app.modules.variables import models as _variables_models  # noqa: F401
from app.modules.webhooks import models as _webhooks_models  # noqa: F401
from app.modules.workflows import models as _workflows_models  # noqa: F401

logger = get_logger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    configure_logging()
    ctx["registry"] = build_runtime_registry()
    logger.info("worker.startup", node_types=len(ctx["registry"].all_descriptors()))


async def shutdown(ctx: dict[str, Any]) -> None:
    logger.info("worker.shutdown")


_SWEEP_MINUTES = set(range(0, 60, 5))
_EVERY_MINUTE = set(range(60))
# mypy's structural match against arq's WorkerCoroutine Protocol is oddly
# sensitive to watchdog_sweep's unused-ctx param name; an explicit cast is
# clearer here than a type: ignore.
_watchdog_coroutine = cast(WorkerCoroutine, watchdog_sweep)
_resume_coroutine = cast(WorkerCoroutine, resume_sweep)
_schedule_tick_coroutine = cast(WorkerCoroutine, schedule_tick)

_CRON_JOBS = [
    cron(recovery_sweep, minute=_SWEEP_MINUTES, run_at_startup=False),
    cron(_watchdog_coroutine, minute=_SWEEP_MINUTES, run_at_startup=False),
    cron(_resume_coroutine, minute=_SWEEP_MINUTES, run_at_startup=False),
    # Schedule triggers need minute-level precision -- see docs/09-domain-
    # modules.md #9.12.
    cron(_schedule_tick_coroutine, minute=_EVERY_MINUTE, run_at_startup=False),
]


def _build_redis_settings() -> RedisSettings:
    # A network-hosted Redis can silently drop an idle connection (NAT/LB
    # timeout) without either side seeing a FIN -- the worker's own queue
    # poll loop then dies with a raw ConnectionError instead of just
    # reconnecting, taking the whole process down. retry_on_error makes
    # redis-py transparently reconnect and retry the single failed command
    # instead of propagating it.
    settings = RedisSettings.from_dsn(str(get_settings().redis_url))
    settings.retry_on_timeout = True
    settings.retry_on_error = [RedisConnectionError, RedisTimeoutError]
    return settings


class WorkerSettings:
    """arq reads this class by name (`arq app.worker.WorkerSettings`)."""

    functions: list[Any] = [run_execution]
    cron_jobs = _CRON_JOBS
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _build_redis_settings()
    max_jobs = get_settings().worker_max_jobs
