from __future__ import annotations

from app.modules.nodes.base import NodeExecutionContext
from app.modules.nodes.descriptors import Item
from app.nodes.remove_duplicates import RemoveDuplicatesNode


async def test_keeps_only_the_first_occurrence_by_field() -> None:
    node = RemoveDuplicatesNode()
    items = [
        Item(json={"id": 1, "v": "a"}),
        Item(json={"id": 1, "v": "b"}),
        Item(json={"id": 2, "v": "c"}),
    ]
    ctx = NodeExecutionContext(input_items=items, params={"compareField": "id"})

    result = await node.execute(ctx)

    assert [i.json_ for i in result["main"][0]] == [
        {"id": 1, "v": "a"},
        {"id": 2, "v": "c"},
    ]


async def test_empty_compare_field_compares_whole_item() -> None:
    node = RemoveDuplicatesNode()
    items = [Item(json={"a": 1}), Item(json={"a": 1}), Item(json={"a": 2})]
    ctx = NodeExecutionContext(input_items=items, params={})

    result = await node.execute(ctx)

    assert len(result["main"][0]) == 2
