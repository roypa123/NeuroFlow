from __future__ import annotations

from app.modules.nodes.base import NodeExecutionContext
from app.modules.nodes.descriptors import Item
from app.nodes.if_ import IfNode


async def test_matching_condition_routes_to_true_output() -> None:
    node = IfNode()
    items = [Item(json={})]
    ctx = NodeExecutionContext(
        input_items=items,
        params={"value1": "a", "operator": "equals", "value2": "a"},
    )

    result = await node.execute(ctx)

    assert result["main"][0] == items
    assert result["main"][1] == []


async def test_non_matching_condition_routes_to_false_output() -> None:
    node = IfNode()
    items = [Item(json={})]
    ctx = NodeExecutionContext(
        input_items=items,
        params={"value1": "a", "operator": "equals", "value2": "b"},
    )

    result = await node.execute(ctx)

    assert result["main"][0] == []
    assert result["main"][1] == items


async def test_greater_than_coerces_numeric_strings() -> None:
    node = IfNode()
    items = [Item(json={})]
    ctx = NodeExecutionContext(
        input_items=items,
        params={"value1": "10", "operator": "greaterThan", "value2": "2"},
    )

    result = await node.execute(ctx)

    assert result["main"][0] == items
