from __future__ import annotations

from app.modules.nodes.base import NodeExecutionContext
from app.modules.nodes.descriptors import Item
from app.nodes.split_out import SplitOutNode


async def test_splits_an_array_field_into_one_item_per_element() -> None:
    node = SplitOutNode()
    items = [Item(json={"tags": ["a", "b", "c"]})]
    ctx = NodeExecutionContext(input_items=items, params={"fieldToSplit": "tags"})

    result = await node.execute(ctx)

    assert [i.json_ for i in result["main"][0]] == [
        {"tags": "a"},
        {"tags": "b"},
        {"tags": "c"},
    ]


async def test_include_other_fields_keeps_the_rest_of_the_item() -> None:
    node = SplitOutNode()
    items = [Item(json={"id": 1, "tags": ["a", "b"]})]
    ctx = NodeExecutionContext(
        input_items=items,
        params={"fieldToSplit": "tags", "includeOtherFields": True},
    )

    result = await node.execute(ctx)

    assert [i.json_ for i in result["main"][0]] == [
        {"id": 1, "tags": "a"},
        {"id": 1, "tags": "b"},
    ]


async def test_non_array_field_is_skipped() -> None:
    node = SplitOutNode()
    items = [Item(json={"tags": "not-a-list"})]
    ctx = NodeExecutionContext(input_items=items, params={"fieldToSplit": "tags"})

    result = await node.execute(ctx)

    assert result["main"][0] == []
