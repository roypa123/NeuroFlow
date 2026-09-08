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
from app.modules.organizations import models as _organizations_models  # noqa: F401
from app.modules.projects import models as _projects_models  # noqa: F401
from app.modules.users import models as _users_models  # noqa: F401
from app.modules.workflows import models as _workflows_models  # noqa: F401

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
