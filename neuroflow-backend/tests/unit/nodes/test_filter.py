from __future__ import annotations

from app.modules.nodes.base import NodeExecutionContext
from app.modules.nodes.descriptors import Item
from app.nodes.filter_ import FilterNode


async def test_keeps_only_matching_items() -> None:
    node = FilterNode()
    items = [Item(json={}), Item(json={})]
    ctx = NodeExecutionContext(
        input_items=items,
        params={"value1": "a", "operator": "equals", "value2": "a"},
    )

    result = await node.execute(ctx)

    assert result["main"][0] == items


async def test_drops_non_matching_items() -> None:
    node = FilterNode()
    items = [Item(json={})]
    ctx = NodeExecutionContext(
        input_items=items,
        params={"value1": "a", "operator": "equals", "value2": "b"},
    )

    result = await node.execute(ctx)

    assert result["main"][0] == []
