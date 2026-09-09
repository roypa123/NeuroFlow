"""Merge -- combines two input branches into one output. See docs/13-node-
catalog-and-sdk.md #13.5.

The first node in the catalog to declare 2 input ports, exercising the
`target_handle`-based routing added this phase (`app/engine/scheduler.py`,
`ctx.input_items_by_port`) -- see this phase's plan, finding #2. Two
modes: `append` (concatenate both inputs, in order) and `mergeByKey` (an
inner join on `keyField`, merging each matched pair's JSON with Input 2's
fields winning on conflict -- unmatched items on either side are dropped,
a deliberate simplification kept honest by the mode's own description
rather than silently guessing what to do with them).
"""

from __future__ import annotations

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


class MergeNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.merge",
        version=1,
        name="Merge",
        group="flow",
        category="Core",
        description="Combines two input branches into one.",
        icon="merge",
        color="cat-flow",
        aliases=["join", "combine"],
        subtitle="={{ $parameter.mode }}",
        inputs=[
            PortSpec(type="main", label="Input 1"),
            PortSpec(type="main", label="Input 2"),
        ],
        outputs=[PortSpec(type="main")],
        idempotent=True,
        properties=[
            NodeProperty(
                name="mode",
                display_name="Mode",
                type="options",
                default="append",
                description="How to combine Input 1 and Input 2.",
                options=[
                    PropertyOption(label="Append", value="append"),
                    PropertyOption(label="Merge by Key", value="mergeByKey"),
                ],
            ),
            NodeProperty(
                name="keyField",
                display_name="Key Field",
                type="string",
                required=True,
                description="Field present on both inputs to match items by.",
                display_options=DisplayOptions(show={"mode": ["mergeByKey"]}),
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        params = ctx.params
        mode = params.get("mode", "append")
        input1 = ctx.input_items_by_port.get("Input 1", [])
        input2 = ctx.input_items_by_port.get("Input 2", [])

        if mode == "mergeByKey":
            key_field = params.get("keyField", "")
            by_key: dict[Any, Item] = {
                item.json_.get(key_field): item for item in input2
            }
            merged: list[Item] = []
            for item in input1:
                match = by_key.get(item.json_.get(key_field))
                if match is not None:
                    merged.append(Item(json={**item.json_, **match.json_}))
            return {"main": [merged]}

        return {"main": [[*input1, *input2]]}
