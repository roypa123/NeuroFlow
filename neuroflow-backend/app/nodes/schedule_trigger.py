"""Schedule Trigger -- cron/interval trigger. See docs/13-node-catalog-and-
sdk.md #13.5 and docs/09-domain-modules.md #9.12.

Like every trigger node, `execute()` is a pass-through: the real work is
`WorkflowService.activate` reading this node's `cron`/`timezone`/`catchUp`
parameters off the graph and calling `ScheduleService.register`; the
lock-guarded `schedule_tick` arq cron job (`app.modules.schedules.service`)
is what actually creates executions when a schedule comes due.
"""

from __future__ import annotations

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import (
    Item,
    NodeProperty,
    NodeTypeDescriptor,
    PortSpec,
)


class ScheduleTriggerNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.scheduleTrigger",
        version=1,
        name="Schedule",
        group="trigger",
        category="Core",
        description="Starts the workflow on a cron schedule.",
        icon="clock",
        color="cat-trigger",
        aliases=["cron", "interval", "timer"],
        subtitle="={{ $parameter.cron }}",
        inputs=[],
        outputs=[PortSpec(type="main")],
        idempotent=True,
        properties=[
            NodeProperty(
                name="cron",
                display_name="Cron Expression",
                type="string",
                required=True,
                default="0 * * * *",
                placeholder="0 * * * *",
                description="Standard 5-field cron syntax.",
            ),
            NodeProperty(
                name="timezone",
                display_name="Timezone",
                type="string",
                default="UTC",
            ),
            NodeProperty(
                name="catchUp",
                display_name="Catch Up Missed Runs",
                type="boolean",
                default=False,
                description="If the worker was down when due, run once on restart.",
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        items = ctx.input_items or [Item(json={})]
        return {"main": [items]}
