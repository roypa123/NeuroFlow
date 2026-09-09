"""Sort -- orders items by a field. See docs/13-node-catalog-and-sdk.md
#13.5. Comparison prefers numeric ordering when both sides parse as
numbers, falling back to string ordering otherwise (the same permissive
coercion `app/nodes/if_.py` already established for its own comparisons);
missing fields sort last regardless of order."""

from __future__ import annotations

from typing import Any

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import (
    NodeProperty,
    NodeTypeDescriptor,
    PortSpec,
    PropertyOption,
)

_MISSING = object()


def _sort_key(value: Any) -> tuple[int, float | str]:
    if value is _MISSING or value is None:
        return (2, "")
    try:
        return (0, float(value))
    except (TypeError, ValueError):
        return (1, str(value))


class SortNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.sort",
        version=1,
        name="Sort",
        group="data",
        category="Core",
        description="Orders items by a field.",
        icon="arrow-down-up",
        color="cat-data",
        aliases=["order by"],
        subtitle="={{ $parameter.sortField }} ({{ $parameter.order }})",
        inputs=[PortSpec(type="main")],
        outputs=[PortSpec(type="main")],
        idempotent=True,
        properties=[
            NodeProperty(
                name="sortField",
                display_name="Sort Field",
                type="string",
                required=True,
            ),
            NodeProperty(
                name="order",
                display_name="Order",
                type="options",
                default="ascending",
                options=[
                    PropertyOption(label="Ascending", value="ascending"),
                    PropertyOption(label="Descending", value="descending"),
                ],
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        field = ctx.params.get("sortField", "")
        descending = ctx.params.get("order", "ascending") == "descending"
        ordered = sorted(
            ctx.input_items,
            key=lambda item: _sort_key(item.json_.get(field, _MISSING)),
            reverse=descending,
        )
        return {"main": [ordered]}
