"""HTTP Request -- the universal escape hatch. See
docs/13-node-catalog-and-sdk.md #13.3/#13.5.

Uses `ctx.http` (the SSRF-guarded client from `app.core.http_client`), per
docs/13-node-catalog-and-sdk.md #13.3: "a node that reaches for `httpx`
directly bypasses [the SSRF policy] and MUST fail review." The optional
`credentialId` parameter (a `credential`-type property, per Phase 5's
declarative auth injection -- docs/15-security-and-credentials.md #15.6
item 3) is resolved by `app.engine` into `ctx.credentials["credentialId"]`
before this node runs; the node calls `ctx.authenticated_request` and never
sees the decrypted value.
"""
from __future__ import annotations

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import (
    CredentialRequirement,
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
        credentials=[
            CredentialRequirement(
                types=["httpHeaderAuth", "httpBasicAuth", "oauth2Generic"], required=False
            )
        ],
        properties=[
            NodeProperty(
                name="credentialId",
                display_name="Authentication",
                type="credential",
                type_options={
                    "credentialTypes": ["httpHeaderAuth", "httpBasicAuth", "oauth2Generic"]
                },
                description="Optional. Applied to the request via the credential's declared auth.",
            ),
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
        results: list[Item] = []
        for index, item in enumerate(ctx.input_items or [Item(json={})]):
            params = ctx.params_for_item(index)
            method = params.get("method", "GET")
            url = params["url"]
            timeout_ms = params.get("timeout", 30000)
            body = params.get("body") if params.get("sendBody") else None

            if ctx.http is None:
                raise RuntimeError("HTTP Request node requires ctx.http to be set")
            response = await ctx.authenticated_request(
                "credentialId", method, url, json=body, timeout=timeout_ms / 1000
            )
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
