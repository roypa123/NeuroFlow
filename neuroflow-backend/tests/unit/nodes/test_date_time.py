from __future__ import annotations

from app.modules.nodes.base import NodeExecutionContext
from app.modules.nodes.descriptors import Item
from app.nodes.date_time import DateTimeNode


async def test_format_operation() -> None:
    node = DateTimeNode()
    items = [Item(json={"ts": "2026-01-15T10:30:00+00:00"})]
    ctx = NodeExecutionContext(
        input_items=items,
        params={
            "operation": "format",
            "inputField": "ts",
            "format": "%Y-%m-%d",
            "destinationField": "day",
        },
    )

    result = await node.execute(ctx)

    assert result["main"][0][0].json_["day"] == "2026-01-15"


async def test_add_subtract_operation() -> None:
    node = DateTimeNode()
    items = [Item(json={"ts": "2026-01-15T00:00:00+00:00"})]
    ctx = NodeExecutionContext(
        input_items=items,
        params={
            "operation": "addSubtract",
            "inputField": "ts",
            "amount": 1,
            "unit": "days",
            "destinationField": "shifted",
        },
    )

    result = await node.execute(ctx)

    assert result["main"][0][0].json_["shifted"].startswith("2026-01-16")


async def test_difference_operation_in_days() -> None:
    node = DateTimeNode()
    items = [
        Item(
            json={
                "start": "2026-01-15T00:00:00+00:00",
                "end": "2026-01-17T00:00:00+00:00",
            }
        )
    ]
    ctx = NodeExecutionContext(
        input_items=items,
        params={
            "operation": "difference",
            "inputField": "start",
            "compareField": "end",
            "unit": "days",
            "destinationField": "diff",
        },
    )

    result = await node.execute(ctx)

    assert result["main"][0][0].json_["diff"] == 2.0


async def test_now_operation_with_no_input_items_still_produces_one_item() -> None:
    node = DateTimeNode()
    ctx = NodeExecutionContext(
        input_items=[], params={"operation": "now", "destinationField": "now"}
    )

    result = await node.execute(ctx)

    assert len(result["main"][0]) == 1
    assert "now" in result["main"][0][0].json_
