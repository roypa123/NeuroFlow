"""Manual Trigger -- runs a workflow from the editor. See
docs/13-node-catalog-and-sdk.md #13.5."""
from __future__ import annotations

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import Item, NodeTypeDescriptor, PortSpec


class ManualTriggerNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.manualTrigger",
        version=1,
        name="Manual Trigger",
        group="trigger",
        category="Core",
        description="Runs the workflow when you click Test in the editor.",
        icon="mouse-pointer-click",
        color="cat-core",
        aliases=["manual", "test"],
        subtitle=None,
        inputs=[],
        outputs=[PortSpec(type="main")],
        idempotent=True,
        properties=[],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        items = ctx.input_items or [Item(json={})]
        return {"main": [items]}
