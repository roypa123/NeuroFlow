from __future__ import annotations

from app.modules.nodes.base import NodeExecutionContext
from app.modules.nodes.descriptors import Item
from app.nodes.error_trigger import ErrorTriggerNode


async def test_passes_through_the_error_payload() -> None:
    node = ErrorTriggerNode()
    items = [Item(json={"message": "boom", "nodeId": "n1"})]
    ctx = NodeExecutionContext(input_items=items, params={})

    result = await node.execute(ctx)

    assert result["main"][0] == items
