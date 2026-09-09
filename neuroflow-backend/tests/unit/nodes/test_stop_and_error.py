from __future__ import annotations

import pytest

from app.modules.nodes.base import NodeExecutionContext
from app.nodes.stop_and_error import StopAndErrorNode, WorkflowStoppedError


async def test_raises_with_the_configured_message() -> None:
    node = StopAndErrorNode()
    ctx = NodeExecutionContext(input_items=[], params={"message": "limit exceeded"})

    with pytest.raises(WorkflowStoppedError, match="limit exceeded"):
        await node.execute(ctx)
