"""Aggregate -- combines all input items into one (or, with `batchSize`,
several) output item(s) holding an array. See docs/13-node-catalog-and-
sdk.md #13.5.

`batchSize` is the one real consumer of `ctx.helpers().batch(...)`
(`app/modules/nodes/base.py`'s `NodeHelpers`, added this phase, finding
#5): chunking `ctx.input_items` into groups of N lets a downstream node
process the aggregated data in bulk-sized pieces (e.g. calling a
bulk-insert API 50 rows at a time) instead of always producing one giant
array.
"""

from __future__ import annotations

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import (
    DisplayOptions,
    Item,
    NodeProperty,
    NodeTypeDescriptor,
    PortSpec,
    PropertyOption,
)


class AggregateNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.aggregate",
        version=1,
        name="Aggregate",
        group="data",
        category="Core",
        description="Combines all items into one array field.",
        icon="layers",
        color="cat-data",
        aliases=["combine", "collect"],
        subtitle="={{ $parameter.mode }}",
        inputs=[PortSpec(type="main")],
        outputs=[PortSpec(type="main")],
        idempotent=True,
        properties=[
            NodeProperty(
                name="mode",
                display_name="Mode",
                type="options",
                default="wholeItems",
                description="What to collect into the output array.",
                options=[
                    PropertyOption(label="All Item Data", value="wholeItems"),
                    PropertyOption(label="One Field's Values", value="fieldValues"),
                ],
            ),
            NodeProperty(
                name="sourceField",
                display_name="Source Field",
                type="string",
                required=True,
                description="Field to collect values from, one per input item.",
                display_options=DisplayOptions(show={"mode": ["fieldValues"]}),
            ),
            NodeProperty(
                name="destinationField",
                display_name="Destination Field",
                type="string",
                default="data",
                required=True,
                description="Field on the output item to hold the aggregated array.",
            ),
            NodeProperty(
                name="batchSize",
                display_name="Batch Size",
                type="number",
                default=0,
                description="Split into multiple output items of this many "
                "aggregated rows each. 0 means one output item for everything.",
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        params = ctx.params
        mode = params.get("mode", "wholeItems")
        source_field = params.get("sourceField", "")
        destination_field = params.get("destinationField", "data")
        batch_size = int(params.get("batchSize") or 0)

        def to_value(item: Item) -> object:
            return item.json_ if mode == "wholeItems" else item.json_.get(source_field)

        chunks: list[list[Item]] = (
            ctx.helpers().batch(ctx.input_items, batch_size)
            if batch_size > 0
            else [ctx.input_items]
        )
        results = [
            Item(json={destination_field: [to_value(item) for item in chunk]})
            for chunk in chunks
            if chunk
        ]
        return {"main": [results]}
