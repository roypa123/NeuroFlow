"""Split Out -- the inverse of Aggregate: takes a field holding an array
and emits one output item per array element. See docs/13-node-catalog-
and-sdk.md #13.5."""

from __future__ import annotations

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import (
    Item,
    NodeProperty,
    NodeTypeDescriptor,
    PortSpec,
)


class SplitOutNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.splitOut",
        version=1,
        name="Split Out",
        group="data",
        category="Core",
        description="Splits an array field into one item per element.",
        icon="split",
        color="cat-data",
        aliases=["explode", "flatten"],
        subtitle="={{ $parameter.fieldToSplit }}",
        inputs=[PortSpec(type="main")],
        outputs=[PortSpec(type="main")],
        idempotent=True,
        properties=[
            NodeProperty(
                name="fieldToSplit",
                display_name="Field To Split Out",
                type="string",
                required=True,
                description="Field on each input item that holds an array.",
            ),
            NodeProperty(
                name="includeOtherFields",
                display_name="Include Other Fields",
                type="boolean",
                default=False,
                description="Keep the rest of the source item's fields alongside "
                "each split-out element (nested under the same field name if it "
                "isn't itself an object).",
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        field = ctx.params.get("fieldToSplit", "")
        include_others = bool(ctx.params.get("includeOtherFields", False))
        results: list[Item] = []
        for item in ctx.input_items:
            values = item.json_.get(field)
            if not isinstance(values, list):
                continue
            others = {k: v for k, v in item.json_.items() if k != field}
            for value in values:
                if include_others:
                    base = value if isinstance(value, dict) else {field: value}
                    results.append(Item(json={**others, **base}))
                else:
                    base = value if isinstance(value, dict) else {field: value}
                    results.append(Item(json=base))
        return {"main": [results]}
