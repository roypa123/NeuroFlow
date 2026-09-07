"""IF -- boolean condition routing two outputs. See
docs/13-node-catalog-and-sdk.md #13.5 and docs/06-canvas-and-editor.md #6.5
for the true/false branch labels this descriptor's `outputs` drive."""
from __future__ import annotations

from typing import Any

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import (
    NodeProperty,
    NodeTypeDescriptor,
    PortSpec,
    PropertyOption,
)

_OPERATORS = {
    "equals": lambda a, b: a == b,
    "notEquals": lambda a, b: a != b,
    "contains": lambda a, b: b in a if isinstance(a, str | list) else False,
    "greaterThan": lambda a, b: _coerce_number(a) > _coerce_number(b),
    "lessThan": lambda a, b: _coerce_number(a) < _coerce_number(b),
}


def _coerce_number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


class IfNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.if",
        version=1,
        name="IF",
        group="flow",
        category="Core",
        description="Routes items to true/false outputs based on a condition.",
        icon="split",
        color="cat-flow",
        aliases=["condition", "branch", "switch"],
        subtitle="={{ $parameter.value1 }} {{ $parameter.operator }} {{ $parameter.value2 }}",
        inputs=[PortSpec(type="main")],
        outputs=[PortSpec(type="main", label="true"), PortSpec(type="main", label="false")],
        idempotent=True,
        properties=[
            NodeProperty(name="value1", display_name="Value 1", type="string", required=True),
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
            NodeProperty(name="value2", display_name="Value 2", type="string", required=True),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        params = ctx.params
        operator = _OPERATORS[params.get("operator", "equals")]
        value1, value2 = params.get("value1"), params.get("value2")
        matched = operator(value1, value2)
        true_items = ctx.input_items if matched else []
        false_items = [] if matched else ctx.input_items
        return {"main": [true_items, false_items]}
