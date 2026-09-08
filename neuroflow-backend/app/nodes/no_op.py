"""No-Op -- structural clarity on the canvas; passes items through
unchanged. See docs/13-node-catalog-and-sdk.md #13.5."""

from __future__ import annotations

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import NodeTypeDescriptor, PortSpec


class NoOpNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.noOp",
        version=1,
        name="No-Op",
        group="flow",
        category="Core",
        description="Does nothing. Useful for organizing a graph visually.",
        icon="circle-dashed",
        color="cat-flow",
        aliases=["noop", "passthrough", "do nothing"],
        inputs=[PortSpec(type="main")],
        outputs=[PortSpec(type="main")],
        idempotent=True,
        properties=[],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        return {"main": [ctx.input_items]}
