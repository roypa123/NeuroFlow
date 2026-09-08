"""Webhook Trigger -- HTTP ingress with auth modes and response modes. See
docs/13-node-catalog-and-sdk.md #13.5 and docs/09-domain-modules.md #9.11.

Like every trigger node, `execute()` is a pass-through: the real work is
`WorkflowService.activate` reading this node's `path`/`method`/`auth`/
`responseMode` parameters off the graph and calling `WebhookService.
register` -- the ingress router (`app.modules.webhooks.ingress_router`,
mounted outside `/api/v1`) is what actually creates the execution, seeding
this node's `ctx.input_items` from the inbound request body.
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


class WebhookTriggerNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.webhookTrigger",
        version=1,
        name="Webhook",
        group="trigger",
        category="Core",
        description="Starts the workflow when an HTTP request hits its URL.",
        icon="webhook",
        color="cat-trigger",
        aliases=["http trigger", "inbound"],
        subtitle="={{ $parameter.method }} /webhook/{{ $parameter.path }}",
        inputs=[],
        outputs=[PortSpec(type="main")],
        idempotent=True,
        properties=[
            NodeProperty(
                name="path",
                display_name="Path",
                type="string",
                required=True,
                description="Left blank to generate a random UUID path.",
            ),
            NodeProperty(
                name="method",
                display_name="Method",
                type="options",
                default="POST",
                options=[
                    PropertyOption(label=m, value=m)
                    for m in ("GET", "POST", "PUT", "PATCH", "DELETE")
                ],
            ),
            NodeProperty(
                name="authMode",
                display_name="Authentication",
                type="options",
                default="none",
                options=[
                    PropertyOption(label="None", value="none"),
                    PropertyOption(label="Header Auth", value="headerAuth"),
                    PropertyOption(label="HMAC Signature", value="hmac"),
                ],
            ),
            NodeProperty(
                name="hmacSecret",
                display_name="HMAC Secret",
                type="string",
                display_options=DisplayOptions(show={"authMode": ["hmac"]}),
            ),
            NodeProperty(
                name="headerAuthValue",
                display_name="Expected Header Value",
                type="string",
                display_options=DisplayOptions(show={"authMode": ["headerAuth"]}),
            ),
            NodeProperty(
                name="responseMode",
                display_name="Response",
                type="options",
                default="immediate",
                options=[
                    PropertyOption(label="Immediately", value="immediate"),
                    PropertyOption(label="When Last Node Finishes", value="last_node"),
                ],
                description="'Respond node' mode is a Phase 6 node -- not built yet.",
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        items = ctx.input_items or [Item(json={})]
        return {"main": [items]}
