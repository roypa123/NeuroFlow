"""The arq job-queue connection pool used by the API to enqueue work.

The API enqueues jobs **by name** (`pool.enqueue_job("run_execution", ...)`)
-- it never imports `app.engine`/`app.worker`, so this module stays a leaf
dependency of `app.modules.executions` without crossing the import-linter
boundary in `pyproject.toml`. See this phase's plan finding #1.
"""
from __future__ import annotations

from arq.connections import ArqRedis, RedisSettings, create_pool

from app.core.config import get_settings

_pool: ArqRedis | None = None


async def get_arq_pool() -> ArqRedis:
    global _pool
    if _pool is None:
        _pool = await create_pool(RedisSettings.from_dsn(str(get_settings().redis_url)))
    return _pool


async def close_arq_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
