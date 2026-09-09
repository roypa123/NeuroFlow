"""Filter -- keeps only items matching a condition, evaluated per item
(not batch-level -- see docs/13-node-catalog-and-sdk.md #13.5 and the
per-item rationale documented in `app/nodes/switch.py`, which this node
mirrors)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import (
    NodeProperty,
    NodeTypeDescriptor,
    PortSpec,
    PropertyOption,
)


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


class FilterNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.filter",
        version=1,
        name="Filter",
        group="flow",
        category="Core",
        description="Keeps only the items matching a condition.",
        icon="list-filter",
        color="cat-flow",
        aliases=["keep", "where"],
        subtitle=(
            "={{ $parameter.value1 }} {{ $parameter.operator }} {{ $parameter.value2 }}"
        ),
        inputs=[PortSpec(type="main")],
        outputs=[PortSpec(type="main")],
        idempotent=True,
        properties=[
            NodeProperty(
                name="value1", display_name="Value 1", type="string", required=True
            ),
            NodeProperty(
                name="operator",
                display_name="Operator",
                type="options",
                default="equals",
                options=[
                    PropertyOption(label="Equals", value="equals"),
                    PropertyOption(label="Not Equals", value="notEquals"),
                    PropertyOption(label="Contains", value="contains"),
                    PropertyOption(label="Greater Than", value="greaterThan"),
                    PropertyOption(label="Less Than", value="lessThan"),
                ],
            ),
            NodeProperty(
                name="value2", display_name="Value 2", type="string", required=True
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        kept = []
        for index, item in enumerate(ctx.input_items):
            params = ctx.params_for_item(index)
            operator = _OPERATORS.get(
                params.get("operator", "equals"), _OPERATORS["equals"]
            )
            if operator(params.get("value1"), params.get("value2")):
                kept.append(item)
        return {"main": [kept]}
