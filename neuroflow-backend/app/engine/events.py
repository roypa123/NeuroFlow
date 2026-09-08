"""Publishes execution lifecycle events to Redis pub/sub, relayed to
browsers by the API's SSE endpoint (`GET /executions/{id}/stream`). See
docs/12-execution-engine.md #12.10.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from redis.asyncio import Redis

from app.core.execution_channels import channel_name


class EventPublisher:
    """One instance per execution -- the monotonic sequence is what lets a
    reconnecting SSE client detect a gap and refetch instead of silently
    rendering an incomplete run (docs/12-execution-engine.md #12.10)."""

    def __init__(self, redis: Redis, execution_id: UUID) -> None:
        self._redis = redis
        self._execution_id = execution_id
        self._sequence = 0

    async def publish(self, event: str, data: dict[str, Any]) -> None:
        self._sequence += 1
        payload = {
            "event": event,
            "sequence": self._sequence,
            "executionId": str(self._execution_id),
            "timestamp": datetime.now(UTC).isoformat(),
            **data,
        }
        await self._redis.publish(channel_name(self._execution_id), json.dumps(payload))
