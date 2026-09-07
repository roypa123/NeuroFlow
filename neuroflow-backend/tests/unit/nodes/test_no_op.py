from __future__ import annotations

from app.modules.nodes.base import NodeExecutionContext
from app.modules.nodes.descriptors import Item
from app.nodes.no_op import NoOpNode


async def test_passes_items_through_unchanged() -> None:
    node = NoOpNode()
    items = [Item(json={"a": 1}), Item(json={"b": 2})]
    ctx = NodeExecutionContext(input_items=items, params={})

    result = await node.execute(ctx)

    assert result["main"][0] == items
