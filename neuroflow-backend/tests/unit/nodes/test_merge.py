from __future__ import annotations

from app.modules.nodes.base import NodeExecutionContext
from app.modules.nodes.descriptors import Item
from app.nodes.merge import MergeNode


async def test_append_mode_concatenates_both_inputs_in_order() -> None:
    node = MergeNode()
    input1 = [Item(json={"a": 1})]
    input2 = [Item(json={"b": 2})]
    ctx = NodeExecutionContext(
        input_items=[*input1, *input2],
        input_items_by_port={"Input 1": input1, "Input 2": input2},
        params={"mode": "append"},
    )

    result = await node.execute(ctx)

    assert result["main"][0] == [*input1, *input2]


async def test_merge_by_key_inner_joins_and_prefers_input2_fields() -> None:
    node = MergeNode()
    input1 = [Item(json={"id": 1, "name": "a"}), Item(json={"id": 2, "name": "b"})]
    input2 = [Item(json={"id": 1, "name": "override"})]
    ctx = NodeExecutionContext(
        input_items=[*input1, *input2],
        input_items_by_port={"Input 1": input1, "Input 2": input2},
        params={"mode": "mergeByKey", "keyField": "id"},
    )

    result = await node.execute(ctx)

    merged = result["main"][0]
    assert len(merged) == 1
    assert merged[0].json_ == {"id": 1, "name": "override"}
