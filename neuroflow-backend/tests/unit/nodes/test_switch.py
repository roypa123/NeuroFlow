from __future__ import annotations

from app.modules.nodes.base import NodeExecutionContext
from app.modules.nodes.descriptors import Item
from app.nodes.switch import SwitchNode


async def test_routes_each_item_to_the_first_matching_rule() -> None:
    node = SwitchNode()
    items = [Item(json={"tier": "gold"}), Item(json={"tier": "silver"})]
    ctx = NodeExecutionContext(
        input_items=items,
        params={
            "numOutputs": 2,
            "value1_0": "gold",
            "operator_0": "equals",
            "value2_0": "gold",
        },
    )
    # No resolver is bound in this unit test, so `params_for_item` just
    # returns the static params above for every item -- this exercises
    # per-item routing logic against a fixed rule, not expression
    # substitution itself (covered by the expression-evaluator tests).

    result = await node.execute(ctx)

    assert result["main"][0] == items  # both items match the same static rule
    assert result["main"][1] == []
    assert result["main"][3] == []  # fallback


async def test_unmatched_items_fall_back() -> None:
    node = SwitchNode()
    items = [Item(json={"tier": "bronze"})]
    ctx = NodeExecutionContext(
        input_items=items,
        params={
            "numOutputs": 2,
            "value1_0": "gold",
            "operator_0": "equals",
            "value2_0": "silver",
        },
    )

    result = await node.execute(ctx)

    assert result["main"][3] == items


async def test_only_active_slots_up_to_num_outputs_are_evaluated() -> None:
    node = SwitchNode()
    items = [Item(json={})]
    ctx = NodeExecutionContext(
        input_items=items,
        params={
            "numOutputs": 2,
            # Rule 2 (slot index 2) would match, but numOutputs=2 means
            # only slots 0-1 are active.
            "value1_2": "a",
            "operator_2": "equals",
            "value2_2": "a",
        },
    )

    result = await node.execute(ctx)

    assert result["main"][2] == []
    assert result["main"][3] == items
