"""Set / Edit Fields -- builds or reshapes item JSON. See
docs/13-node-catalog-and-sdk.md #13.5.

`fields` is a plain JSON object today because there is no expression
evaluator yet (docs/12-execution-engine.md #12.6, Phase 4) -- each value is
used as a literal. Once the evaluator exists, values containing `{{ }}`
will be resolved per item via `ctx.params_for_item`, with no change to this
node's descriptor.
"""

from __future__ import annotations

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import (
    Item,
    NodeProperty,
    NodeTypeDescriptor,
    PortSpec,
    PropertyOption,
)


class SetNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.set",
        version=1,
        name="Set",
        group="data",
        category="Core",
        description="Build or reshape item JSON.",
        icon="pencil-line",
        color="cat-data",
        aliases=["edit fields", "set field", "assign"],
        subtitle="={{ $parameter.mode }}",
        inputs=[PortSpec(type="main")],
        outputs=[PortSpec(type="main")],
        idempotent=True,
        properties=[
            NodeProperty(
                name="mode",
                display_name="Mode",
                type="options",
                default="merge",
                options=[
                    PropertyOption(label="Merge with input", value="merge"),
                    PropertyOption(label="Keep only fields set", value="keepOnlySet"),
                ],
            ),
            NodeProperty(
                name="fields",
                display_name="Fields",
                type="json",
                default={},
                required=True,
                description="JSON object merged into (or replacing) each item.",
                placeholder='{"status": "processed"}',
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        params = ctx.params
        mode = params.get("mode", "merge")
        fields = params.get("fields") or {}
        results: list[Item] = []
        for item in ctx.input_items:
            new_json = {**item.json_, **fields} if mode == "merge" else dict(fields)
            results.append(Item(json=new_json, paired_item=item.paired_item))
        return {"main": [results]}
