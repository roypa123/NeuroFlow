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
    # A network-hosted Redis (vs. a same-host container) can silently drop an
    # idle connection (NAT/LB timeout) without either side seeing a FIN --
    # the next command then blocks until the OS-level TCP timeout, which can
    # be a minute or more, stalling the DAG scheduler's cancel-flag check
    # between every node. socket_timeout/health_check_interval bound that to
    # a few seconds and retry_on_timeout recovers automatically instead of
    # surfacing it as an execution failure.
    return ConnectionPool.from_url(
        str(settings.redis_url),
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=10,
        socket_keepalive=True,
        health_check_interval=30,
        retry_on_timeout=True,
    )


def get_redis() -> Redis:
    return Redis(connection_pool=get_redis_pool())
