from __future__ import annotations

from app.modules.nodes.base import NodeExecutionContext
from app.modules.nodes.descriptors import Item
from app.nodes.manual_trigger import ManualTriggerNode


async def test_passes_through_input_items() -> None:
    node = ManualTriggerNode()
    ctx = NodeExecutionContext(input_items=[Item(json={"a": 1})], params={})

    result = await node.execute(ctx)

    assert result["main"][0][0].json_ == {"a": 1}


async def test_produces_one_empty_item_with_no_input() -> None:
    node = ManualTriggerNode()
    ctx = NodeExecutionContext(input_items=[], params={})

    result = await node.execute(ctx)

    assert len(result["main"][0]) == 1
    assert result["main"][0][0].json_ == {}
