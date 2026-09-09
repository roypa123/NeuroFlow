from __future__ import annotations

from app.modules.nodes.base import NodeExecutionContext
from app.modules.nodes.descriptors import Item
from app.nodes.workflow_trigger import WorkflowTriggerNode


async def test_passes_through_the_caller_payload() -> None:
    node = WorkflowTriggerNode()
    items = [Item(json={"orderId": "123"})]
    ctx = NodeExecutionContext(input_items=items, params={})

    result = await node.execute(ctx)

    assert result["main"][0] == items


async def test_defaults_to_one_empty_item_when_called_with_none() -> None:
    node = WorkflowTriggerNode()
    ctx = NodeExecutionContext(input_items=[], params={})

    result = await node.execute(ctx)

    assert result["main"][0] == [Item(json={})]
