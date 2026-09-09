"""Compare Datasets -- diffs two input branches by a key field into
three outputs: items only in A, only in B, and in both. See docs/13-
node-catalog-and-sdk.md #13.5. Like `app/nodes/merge.py`, exercises the
multi-input-port routing added this phase (`ctx.input_items_by_port`) --
see this phase's plan, finding #2."""

from __future__ import annotations

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import (
    Item,
    NodeProperty,
    NodeTypeDescriptor,
    PortSpec,
)


class CompareDatasetsNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.compareDatasets",
        version=1,
        name="Compare Datasets",
        group="data",
        category="Core",
        description="Diffs two inputs by a key field.",
        icon="git-compare",
        color="cat-data",
        aliases=["diff"],
        subtitle="={{ $parameter.keyField }}",
        inputs=[
            PortSpec(type="main", label="Input A"),
            PortSpec(type="main", label="Input B"),
        ],
        outputs=[
            PortSpec(type="main", label="onlyInA"),
            PortSpec(type="main", label="onlyInB"),
            PortSpec(type="main", label="inBoth"),
        ],
        idempotent=True,
        properties=[
            NodeProperty(
                name="keyField",
                display_name="Key Field",
                type="string",
                required=True,
                description="Field present on both inputs to match items by.",
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        key_field = ctx.params.get("keyField", "")
        input_a = ctx.input_items_by_port.get("Input A", [])
        input_b = ctx.input_items_by_port.get("Input B", [])
        keys_b = {item.json_.get(key_field) for item in input_b}
        keys_a = {item.json_.get(key_field) for item in input_a}

        only_a: list[Item] = [
            i for i in input_a if i.json_.get(key_field) not in keys_b
        ]
        only_b: list[Item] = [
            i for i in input_b if i.json_.get(key_field) not in keys_a
        ]
        in_both: list[Item] = [i for i in input_a if i.json_.get(key_field) in keys_b]

        return {"main": [only_a, only_b, in_both]}
