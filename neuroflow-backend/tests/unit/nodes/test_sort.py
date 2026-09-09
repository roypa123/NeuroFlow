from __future__ import annotations

from app.modules.nodes.base import NodeExecutionContext
from app.modules.nodes.descriptors import Item
from app.nodes.sort import SortNode


async def test_sorts_ascending_by_default() -> None:
    node = SortNode()
    items = [Item(json={"n": 3}), Item(json={"n": 1}), Item(json={"n": 2})]
    ctx = NodeExecutionContext(input_items=items, params={"sortField": "n"})

    result = await node.execute(ctx)

    assert [i.json_["n"] for i in result["main"][0]] == [1, 2, 3]


async def test_descending_order() -> None:
    node = SortNode()
    items = [Item(json={"n": 1}), Item(json={"n": 3}), Item(json={"n": 2})]
    ctx = NodeExecutionContext(
        input_items=items, params={"sortField": "n", "order": "descending"}
    )

    result = await node.execute(ctx)

    assert [i.json_["n"] for i in result["main"][0]] == [3, 2, 1]


async def test_missing_field_sorts_last() -> None:
    node = SortNode()
    items = [Item(json={"n": 1}), Item(json={}), Item(json={"n": 0})]
    ctx = NodeExecutionContext(input_items=items, params={"sortField": "n"})

    result = await node.execute(ctx)

    assert [i.json_ for i in result["main"][0]] == [{"n": 0}, {"n": 1}, {}]
