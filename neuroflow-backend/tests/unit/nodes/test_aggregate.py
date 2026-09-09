from __future__ import annotations

from app.modules.nodes.base import NodeExecutionContext
from app.modules.nodes.descriptors import Item
from app.nodes.aggregate import AggregateNode


async def test_whole_items_mode_combines_all_items_into_one_array_field() -> None:
    node = AggregateNode()
    items = [Item(json={"a": 1}), Item(json={"a": 2})]
    ctx = NodeExecutionContext(
        input_items=items, params={"mode": "wholeItems", "destinationField": "data"}
    )

    result = await node.execute(ctx)

    assert len(result["main"][0]) == 1
    assert result["main"][0][0].json_ == {"data": [{"a": 1}, {"a": 2}]}


async def test_field_values_mode_collects_one_field() -> None:
    node = AggregateNode()
    items = [Item(json={"name": "a"}), Item(json={"name": "b"})]
    ctx = NodeExecutionContext(
        input_items=items,
        params={
            "mode": "fieldValues",
            "sourceField": "name",
            "destinationField": "names",
        },
    )

    result = await node.execute(ctx)

    assert result["main"][0][0].json_ == {"names": ["a", "b"]}


async def test_batch_size_splits_into_multiple_output_items() -> None:
    node = AggregateNode()
    items = [Item(json={"a": i}) for i in range(5)]
    ctx = NodeExecutionContext(
        input_items=items,
        params={"mode": "wholeItems", "destinationField": "data", "batchSize": 2},
    )

    result = await node.execute(ctx)

    batches = result["main"][0]
    assert len(batches) == 3
    assert [len(b.json_["data"]) for b in batches] == [2, 2, 1]
