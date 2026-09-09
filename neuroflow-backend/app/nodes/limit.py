"""Limit -- keeps only the first or last N items. See docs/13-node-
catalog-and-sdk.md #13.5."""

from __future__ import annotations

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import (
    NodeProperty,
    NodeTypeDescriptor,
    PortSpec,
    PropertyOption,
)


class LimitNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.limit",
        version=1,
        name="Limit",
        group="data",
        category="Core",
        description="Keeps only the first or last N items.",
        icon="scissors",
        color="cat-data",
        aliases=["take", "head", "tail"],
        subtitle="={{ $parameter.keep }} {{ $parameter.maxItems }}",
        inputs=[PortSpec(type="main")],
        outputs=[PortSpec(type="main")],
        idempotent=True,
        properties=[
            NodeProperty(
                name="maxItems",
                display_name="Max Items",
                type="number",
                default=1,
                required=True,
            ),
            NodeProperty(
                name="keep",
                display_name="Keep",
                type="options",
                default="firstItems",
                options=[
                    PropertyOption(label="First Items", value="firstItems"),
                    PropertyOption(label="Last Items", value="lastItems"),
                ],
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        max_items = max(0, int(ctx.params.get("maxItems", 1)))
        keep_last = ctx.params.get("keep", "firstItems") == "lastItems"
        items = ctx.input_items
        sliced = (
            items[-max_items:] if keep_last and max_items > 0 else items[:max_items]
        )
        return {"main": [sliced]}
