"""Workflow Trigger -- the receiving counterpart of `Execute Sub-workflow`
(`app/nodes/execute_workflow.py`). Marks a workflow as callable as a
sub-workflow; the payload passed by the caller becomes this trigger's
output items, exactly like `ManualTrigger` treats a manual test payload.
See docs/13-node-catalog-and-sdk.md #13.5.
"""

from __future__ import annotations

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import Item, NodeTypeDescriptor, PortSpec


class WorkflowTriggerNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.workflowTrigger",
        version=1,
        name="Workflow Trigger",
        group="trigger",
        category="Core",
        description="Runs this workflow when called by an Execute Sub-workflow node.",
        icon="workflow",
        color="cat-trigger",
        aliases=["sub-workflow trigger", "called by"],
        subtitle=None,
        inputs=[],
        outputs=[PortSpec(type="main")],
        idempotent=True,
        properties=[],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        items = ctx.input_items or [Item(json={})]
        return {"main": [items]}
