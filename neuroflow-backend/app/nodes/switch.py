"""Switch -- routes each item to one of up to 3 numbered outputs plus a
fallback, based on the first matching rule. See docs/13-node-catalog-and-
sdk.md #13.5.

Unlike `IfNode` (`app/nodes/if_.py`), which evaluates its condition once
against item 0 and routes the *whole batch* together (a documented
simplification already shipped in that node), Switch evaluates each rule
per item via `ctx.params_for_item(index)` -- the per-item expression
resolver `ExecutionContext.build_resolver` already supports (docs/12-
execution-engine.md #12.6), just not yet used by any flow-control node.
This is the more useful and no more complex behavior for a node whose
whole point is routing a mixed batch, so it's the one used here rather
than repeating IF's simplification.

The number of rule outputs is fixed at registration time (there is no
dynamic-descriptor mechanism), so `numOutputs` (2-4) only toggles which
rule fields are visible via `display_options`; unused rule slots are
simply never matched.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import (
    DisplayOptions,
    Item,
    NodeProperty,
    NodeTypeDescriptor,
    PortSpec,
    PropertyOption,
)

_RULE_SLOTS = 3


def _coerce_number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


_OPERATORS: dict[str, Callable[[Any, Any], bool]] = {
    "equals": lambda a, b: bool(a == b),
    "notEquals": lambda a, b: bool(a != b),
    "contains": lambda a, b: b in a if isinstance(a, str | list) else False,
    "greaterThan": lambda a, b: _coerce_number(a) > _coerce_number(b),
    "lessThan": lambda a, b: _coerce_number(a) < _coerce_number(b),
}

_OPERATOR_OPTIONS = [
    PropertyOption(label="Equals", value="equals"),
    PropertyOption(label="Not Equals", value="notEquals"),
    PropertyOption(label="Contains", value="contains"),
    PropertyOption(label="Greater Than", value="greaterThan"),
    PropertyOption(label="Less Than", value="lessThan"),
]


def _rule_properties(slot: int) -> list[NodeProperty]:
    visible_when = [n for n in (2, 3, 4) if n > slot]
    show = DisplayOptions(show={"numOutputs": visible_when})
    return [
        NodeProperty(
            name=f"value1_{slot}",
            display_name=f"Rule {slot + 1}: Value 1",
            type="string",
            display_options=show,
        ),
        NodeProperty(
            name=f"operator_{slot}",
            display_name=f"Rule {slot + 1}: Operator",
            type="options",
            default="equals",
            options=_OPERATOR_OPTIONS,
            display_options=show,
        ),
        NodeProperty(
            name=f"value2_{slot}",
            display_name=f"Rule {slot + 1}: Value 2",
            type="string",
            display_options=show,
        ),
    ]


class SwitchNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.switch",
        version=1,
        name="Switch",
        group="flow",
        category="Core",
        description="Routes each item to one of several outputs based on rules.",
        icon="shuffle",
        color="cat-flow",
        aliases=["route", "case"],
        subtitle="={{ $parameter.numOutputs }} outputs",
        inputs=[PortSpec(type="main")],
        outputs=[
            PortSpec(type="main", label="0"),
            PortSpec(type="main", label="1"),
            PortSpec(type="main", label="2"),
            PortSpec(type="main", label="fallback"),
        ],
        idempotent=True,
        properties=[
            NodeProperty(
                name="numOutputs",
                display_name="Number of Outputs",
                type="options",
                default=2,
                options=[PropertyOption(label=str(n), value=n) for n in (2, 3, 4)],
                description="How many numbered rule outputs to use (2-4).",
            ),
            *[prop for slot in range(_RULE_SLOTS) for prop in _rule_properties(slot)],
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        num_outputs = int(ctx.params.get("numOutputs", 2))
        active_slots = min(num_outputs, _RULE_SLOTS)
        buckets: list[list[Item]] = [[] for _ in range(_RULE_SLOTS + 1)]

        for index, item in enumerate(ctx.input_items):
            params = ctx.params_for_item(index)
            matched_slot: int | None = None
            for slot in range(active_slots):
                value1 = params.get(f"value1_{slot}")
                if value1 is None:
                    # An unconfigured rule slot's `value1`/`value2` both
                    # default to `None`, which would otherwise accidentally
                    # match via `equals(None, None)` -- treat "no value1
                    # set" as "this rule slot isn't configured yet."
                    continue
                operator_name = params.get(f"operator_{slot}", "equals")
                operator = _OPERATORS.get(operator_name, _OPERATORS["equals"])
                value2 = params.get(f"value2_{slot}")
                if operator(value1, value2):
                    matched_slot = slot
                    break
            buckets[matched_slot if matched_slot is not None else _RULE_SLOTS].append(
                item
            )

        return {"main": buckets}
