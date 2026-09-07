"""HTTP Request -- the universal escape hatch. See
docs/13-node-catalog-and-sdk.md #13.3/#13.5.

Uses `httpx` directly. This is a deliberate, documented placeholder: the
real runtime's `ctx.http` (SSRF allow/deny policy, response size caps,
credential redaction -- #13.3) is a Phase 4 engine concern that does not
exist yet, and no `credentials` requirement is declared on this descriptor
for the same reason (Phase 5). Nothing invokes `execute()` in production
today -- there is no engine to call it -- so this is safe as a
unit-testable stand-in, not a live request path.
"""
from __future__ import annotations

import httpx

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import (
    DisplayOptions,
    Item,
    NodeProperty,
    NodeTypeDescriptor,
    PortSpec,
    PropertyOption,
)


class HttpRequestNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.http",
        version=1,
        name="HTTP Request",
        group="action",
        category="Core",
        description="Make an HTTP request to any URL.",
        icon="globe",
        color="cat-app",
        aliases=["api", "rest", "curl", "fetch", "webhook"],
        subtitle="={{ $parameter.method }} {{ $parameter.url }}",
        inputs=[PortSpec(type="main")],
        outputs=[PortSpec(type="main")],
        idempotent=False,
        properties=[
            NodeProperty(
                name="method",
                display_name="Method",
                type="options",
                default="GET",
                options=[
                    PropertyOption(label=m, value=m)
                    for m in ("GET", "POST", "PUT", "PATCH", "DELETE")
                ],
            ),
            NodeProperty(
                name="url",
                display_name="URL",
                type="string",
                required=True,
                placeholder="https://api.example.com/v1/users",
            ),
            NodeProperty(
                name="sendBody",
                display_name="Send Body",
                type="boolean",
                default=False,
                display_options=DisplayOptions(
                    show={"method": ["POST", "PUT", "PATCH"]}
                ),
            ),
            NodeProperty(
                name="body",
                display_name="Body",
                type="json",
                default={},
                display_options=DisplayOptions(show={"sendBody": [True]}),
            ),
            NodeProperty(
                name="timeout",
                display_name="Timeout (ms)",
                type="number",
                default=30000,
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        params = ctx.params
        method = params.get("method", "GET")
        url = params["url"]
        timeout_ms = params.get("timeout", 30000)
        body = params.get("body") if params.get("sendBody") else None

        results: list[Item] = []
        async with httpx.AsyncClient(timeout=timeout_ms / 1000) as client:
            for index, item in enumerate(ctx.input_items or [Item(json={})]):
                response = await client.request(method, url, json=body)
                ctx.log("info", f"{method} {url} -> {response.status_code}")
                try:
                    payload = response.json()
                except ValueError:
                    payload = {"text": response.text}
                results.append(
                    Item(
                        json={"statusCode": response.status_code, "body": payload},
                        paired_item=item.paired_item or {"item": index},
                    )
                )
        return {"main": [results]}
