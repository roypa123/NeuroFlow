from __future__ import annotations

from app.modules.nodes.base import NodeExecutionContext
from app.modules.nodes.descriptors import Item
from app.nodes.compare_datasets import CompareDatasetsNode


async def test_splits_into_only_a_only_b_and_both() -> None:
    node = CompareDatasetsNode()
    input_a = [Item(json={"id": 1}), Item(json={"id": 2})]
    input_b = [Item(json={"id": 2}), Item(json={"id": 3})]
    ctx = NodeExecutionContext(
        input_items=[*input_a, *input_b],
        input_items_by_port={"Input A": input_a, "Input B": input_b},
        params={"keyField": "id"},
    )

    result = await node.execute(ctx)

    only_a, only_b, in_both = result["main"]
    assert [i.json_["id"] for i in only_a] == [1]
    assert [i.json_["id"] for i in only_b] == [3]
    assert [i.json_["id"] for i in in_both] == [2]
