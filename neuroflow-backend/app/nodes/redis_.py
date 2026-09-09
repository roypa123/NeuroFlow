"""Redis -- get/set/incr/expire/publish/lpush/delete against a user's own
Redis instance, named by a `redisApi` credential. Named `redis_.py` so it
doesn't shadow the `redis` package it imports. See this phase's plan,
findings #3/#4 -- same "own connection, not the app's pool" rule as
`app/nodes/postgres.py`. Operates per input item (via
`ctx.params_for_item`) so `key`/`value` can reference each item's own
fields, e.g. writing one Redis key per row."""

from __future__ import annotations

from collections.abc import Awaitable
from typing import Any, cast

import redis.asyncio as redis_client

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


def _build_client(data: dict[str, Any]) -> redis_client.Redis:
    return redis_client.Redis(
        host=data.get("host", "localhost"),
        port=int(data.get("port", 6379)),
        password=data.get("password") or None,
        db=int(data.get("db", 0)),
        ssl=bool(data.get("tls", False)),
        decode_responses=True,
    )


class RedisNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.redis",
        version=1,
        name="Redis",
        group="action",
        category="Database",
        description="Reads or writes a key in Redis.",
        icon="database-zap",
        color="cat-app",
        aliases=["cache", "kv"],
        subtitle="={{ $parameter.operation }} {{ $parameter.key }}",
        inputs=[PortSpec(type="main")],
        outputs=[PortSpec(type="main")],
        credentials=[CredentialRequirement(types=["redisApi"], required=True)],
        idempotent=False,
        properties=[
            NodeProperty(
                name="credentialId",
                display_name="Credential",
                type="credential",
                required=True,
                type_options={"credentialTypes": ["redisApi"]},
            ),
            NodeProperty(
                name="operation",
                display_name="Operation",
                type="options",
                default="get",
                options=[
                    PropertyOption(label="Get", value="get"),
                    PropertyOption(label="Set", value="set"),
                    PropertyOption(label="Increment", value="incr"),
                    PropertyOption(label="Expire", value="expire"),
                    PropertyOption(label="Publish", value="publish"),
                    PropertyOption(label="List Push", value="lpush"),
                    PropertyOption(label="Delete", value="delete"),
                ],
            ),
            NodeProperty(name="key", display_name="Key", type="string", required=True),
            NodeProperty(
                name="value",
                display_name="Value",
                type="string",
                display_options=DisplayOptions(
                    show={"operation": ["set", "publish", "lpush"]}
                ),
            ),
            NodeProperty(
                name="ttlSeconds",
                display_name="TTL (seconds)",
                type="number",
                display_options=DisplayOptions(show={"operation": ["set", "expire"]}),
            ),
            NodeProperty(
                name="destinationField",
                display_name="Destination Field",
                type="string",
                default="result",
                required=True,
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        binding = ctx.credentials.get("credentialId")
        if binding is None:
            raise RuntimeError("Redis node requires a credential")

        client = _build_client(binding.data)
        results: list[Item] = []
        try:
            source_items = ctx.input_items or [Item(json={})]
            for index, item in enumerate(source_items):
                p = ctx.params_for_item(index) if ctx.input_items else ctx.params
                operation = p.get("operation", "get")
                key = p.get("key", "")
                ttl = p.get("ttlSeconds")
                destination = p.get("destinationField", "result")

                value: Any
                if operation == "get":
                    value = await client.get(key)
                elif operation == "set":
                    await client.set(
                        key, p.get("value", ""), ex=int(ttl) if ttl else None
                    )
                    value = "OK"
                elif operation == "incr":
                    value = await client.incr(key)
                elif operation == "expire":
                    value = await client.expire(key, int(ttl or 0))
                elif operation == "publish":
                    value = await client.publish(key, p.get("value", ""))
                elif operation == "lpush":
                    # redis-py's stub types `lpush` as `Awaitable[int] | int`
                    # (a shared sync/async codegen quirk unique to this
                    # command) even though the async client always returns
                    # a coroutine at runtime.
                    lpush_result = cast(
                        "Awaitable[int]", client.lpush(key, p.get("value", ""))
                    )
                    value = await lpush_result
                else:  # delete
                    value = await client.delete(key)

                results.append(Item(json={**item.json_, destination: value}))
        finally:
            await client.aclose()
        return {"main": [results]}
