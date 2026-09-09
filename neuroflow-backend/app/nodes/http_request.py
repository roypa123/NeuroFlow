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

Phase 6 adds optional pagination (`ctx.helpers().paginate`, added this
phase -- finding #5 of this phase's plan): when enabled, each item
processed follows `nextUrlField` in the response body until it's absent
or `maxRequests` is reached, emitting one output item per page instead of
one item per input item.
"""

from __future__ import annotations

from typing import Any

import httpx

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


def _response_to_item(response: httpx.Response) -> Item:
    try:
        payload = response.json()
    except ValueError:
        payload = {"text": response.text}
    return Item(json={"statusCode": response.status_code, "body": payload})


def _dig(body: Any, dotted_path: str) -> Any:
    value = body
    for segment in dotted_path.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(segment)
    return value


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
                types=["httpHeaderAuth", "httpBasicAuth", "oauth2Generic"],
                required=False,
            )
        ],
        properties=[
            NodeProperty(
                name="credentialId",
                display_name="Authentication",
                type="credential",
                type_options={
                    "credentialTypes": [
                        "httpHeaderAuth",
                        "httpBasicAuth",
                        "oauth2Generic",
                    ]
                },
                description="Optional. Applied via the credential's declared auth.",
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
                description="Request timeout, in milliseconds.",
            ),
            NodeProperty(
                name="paginationMode",
                display_name="Pagination",
                type="options",
                default="none",
                description="Follow a next-page URL found in each response body.",
                options=[
                    PropertyOption(label="None", value="none"),
                    PropertyOption(label="Next URL In Body", value="nextUrlInBody"),
                ],
            ),
            NodeProperty(
                name="nextUrlField",
                display_name="Next URL Field",
                type="string",
                default="nextUrl",
                description="Dot-path in the response body to the next page's URL.",
                display_options=DisplayOptions(
                    show={"paginationMode": ["nextUrlInBody"]}
                ),
            ),
            NodeProperty(
                name="maxRequests",
                display_name="Max Requests",
                type="number",
                default=10,
                description="Stop following pages after this many requests.",
                display_options=DisplayOptions(
                    show={"paginationMode": ["nextUrlInBody"]}
                ),
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        if ctx.http is None:
            raise RuntimeError("HTTP Request node requires ctx.http to be set")

        results: list[Item] = []
        for index, item in enumerate(ctx.input_items or [Item(json={})]):
            params = ctx.params_for_item(index)
            method = params.get("method", "GET")
            url = params["url"]
            timeout_ms = params.get("timeout", 30000)
            body = params.get("body") if params.get("sendBody") else None

            async def fetch_page(
                cursor: str | None,
                method: str = method,
                url: str = url,
                body: Any = body,
                timeout_ms: float = timeout_ms,
            ) -> httpx.Response:
                target = cursor or url
                return await ctx.authenticated_request(
                    "credentialId", method, target, json=body, timeout=timeout_ms / 1000
                )

            if params.get("paginationMode") == "nextUrlInBody":
                next_url_field = params.get("nextUrlField", "nextUrl")
                max_requests = int(params.get("maxRequests", 10))

                def extract_items(response: httpx.Response) -> list[Item]:
                    return [_response_to_item(response)]

                def extract_next(
                    response: httpx.Response, field: str = next_url_field
                ) -> str | None:
                    if response.status_code >= 400:
                        return None
                    next_url = _dig(_body_or_none(response), field)
                    return next_url if isinstance(next_url, str) else None

                async for page_items in ctx.helpers().paginate(
                    fetch_page, extract_items, extract_next, max_pages=max_requests
                ):
                    results.extend(page_items)
                continue

            response = await fetch_page(None)
            ctx.log("info", f"{method} {url} -> {response.status_code}")
            page_item = _response_to_item(response)
            results.append(
                Item(
                    json=page_item.json_,
                    paired_item=item.paired_item or {"item": index},
                )
            )
        return {"main": [results]}


def _body_or_none(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None
