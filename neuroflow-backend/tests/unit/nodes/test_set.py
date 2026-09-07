from __future__ import annotations

from app.modules.nodes.base import NodeExecutionContext
from app.modules.nodes.descriptors import Item
from app.nodes.set_ import SetNode


async def test_merge_mode_combines_input_with_fields() -> None:
    node = SetNode()
    ctx = NodeExecutionContext(
        input_items=[Item(json={"existing": 1})],
        params={"mode": "merge", "fields": {"added": 2}},
    )

    result = await node.execute(ctx)

    assert result["main"][0][0].json_ == {"existing": 1, "added": 2}


async def test_keep_only_set_mode_discards_input_fields() -> None:
    node = SetNode()
    ctx = NodeExecutionContext(
        input_items=[Item(json={"existing": 1})],
        params={"mode": "keepOnlySet", "fields": {"only": True}},
    )

    result = await node.execute(ctx)

    assert result["main"][0][0].json_ == {"only": True}
