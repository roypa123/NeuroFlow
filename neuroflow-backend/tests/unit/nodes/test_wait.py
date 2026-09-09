"""Wait raises ExecutionSuspended rather than returning normally -- the
node's entire job. See docs/12-execution-engine.md #12.5."""

from __future__ import annotations

import pytest

from app.modules.nodes.base import ExecutionSuspended, NodeExecutionContext
from app.nodes.wait import WaitNode


async def test_duration_mode_suspends_with_a_future_resume_after() -> None:
    node = WaitNode()
    ctx = NodeExecutionContext(
        input_items=[], params={"mode": "duration", "durationSeconds": 30}
    )

    with pytest.raises(ExecutionSuspended) as exc_info:
        await node.execute(ctx)

    assert exc_info.value.resume_token
    assert exc_info.value.resume_after is not None


async def test_webhook_mode_suspends_with_no_resume_after() -> None:
    node = WaitNode()
    ctx = NodeExecutionContext(input_items=[], params={"mode": "webhook"})

    with pytest.raises(ExecutionSuspended) as exc_info:
        await node.execute(ctx)

    assert exc_info.value.resume_token
    assert exc_info.value.resume_after is None


async def test_each_suspension_gets_a_unique_resume_token() -> None:
    node = WaitNode()
    ctx = NodeExecutionContext(input_items=[], params={"mode": "webhook"})

    tokens = set()
    for _ in range(5):
        with pytest.raises(ExecutionSuspended) as exc_info:
            await node.execute(ctx)
        tokens.add(exc_info.value.resume_token)

    assert len(tokens) == 5
