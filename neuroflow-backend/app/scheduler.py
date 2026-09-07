"""Cron/schedule ticker entrypoint: `python -m app.scheduler`.

Runs as exactly one replica (docs/03-system-architecture.md #3.3); a Redis
lock guards against an accidental second instance double-firing schedules,
and schedules/schedules.py additionally claims rows with
`SELECT ... FOR UPDATE SKIP LOCKED` (docs/09-domain-modules.md #9.12) so a
lock failure alone can never cause a double fire.

The schedules module (docs/10-database-schema.md #10.9) lands in Phase 5;
until then this ticks and logs so the process is real and observable
without crash-looping in `docker compose up`.
"""
from __future__ import annotations

import asyncio
import contextlib
import signal
import uuid

from app.core.logging import configure_logging, get_logger
from app.core.redis import get_redis

TICK_SECONDS = 10
LOCK_KEY = "scheduler:singleton-lock"
LOCK_TTL_SECONDS = 30

logger = get_logger(__name__)


async def run() -> None:
    configure_logging()
    redis = get_redis()
    instance_id = str(uuid.uuid4())
    logger.info("scheduler.startup", instance_id=instance_id)

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    while not stop.is_set():
        # Only the replica holding the lock ticks -- see the docstring above
        # for why this is defence-in-depth rather than the sole guarantee.
        got_lock = await redis.set(
            LOCK_KEY, instance_id, nx=True, ex=LOCK_TTL_SECONDS
        )
        if not got_lock:
            holder = await redis.get(LOCK_KEY)
            if holder == instance_id:
                got_lock = True
                await redis.expire(LOCK_KEY, LOCK_TTL_SECONDS)

        if got_lock:
            logger.debug("scheduler.tick", instance_id=instance_id)
            # TODO(phase-5): claim due `schedules` rows and enqueue
            # executions -- see docs/09-domain-modules.md #9.12.

        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(stop.wait(), timeout=TICK_SECONDS)

    logger.info("scheduler.shutdown", instance_id=instance_id)
    await redis.aclose()


if __name__ == "__main__":
    asyncio.run(run())
