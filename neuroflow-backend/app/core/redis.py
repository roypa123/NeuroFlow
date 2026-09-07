"""Redis connection pool.

Used for the arq job queue, execution pub/sub fan-out, rate-limit counters,
distributed locks (scheduler singleton, per-workflow concurrency), and short
caches (node type registry, OAuth state).
"""
from __future__ import annotations

from functools import lru_cache

from redis.asyncio import ConnectionPool, Redis

from app.core.config import get_settings


@lru_cache
def get_redis_pool() -> ConnectionPool:
    settings = get_settings()
    return ConnectionPool.from_url(str(settings.redis_url), decode_responses=True)


def get_redis() -> Redis:
    return Redis(connection_pool=get_redis_pool())
