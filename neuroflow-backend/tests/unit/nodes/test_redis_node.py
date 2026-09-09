"""Unit coverage for the pure client-builder and the credential-required
error path. The actual read/write operations against a real Redis
instance are covered live in `tests/integration/test_redis_node.py` --
see this phase's plan."""

from __future__ import annotations

import pytest

from app.modules.nodes.base import NodeExecutionContext
from app.nodes.redis_ import RedisNode, _build_client


def test_build_client_uses_credential_fields() -> None:
    client = _build_client(
        {
            "host": "cache.example.com",
            "port": 6380,
            "password": "pw",
            "db": 2,
            "tls": True,
        }
    )

    connection_kwargs = client.connection_pool.connection_kwargs
    assert connection_kwargs["host"] == "cache.example.com"
    assert connection_kwargs["port"] == 6380
    assert connection_kwargs["password"] == "pw"
    assert connection_kwargs["db"] == 2


async def test_missing_credential_raises() -> None:
    node = RedisNode()
    ctx = NodeExecutionContext(input_items=[], params={"operation": "get", "key": "k"})

    with pytest.raises(RuntimeError, match="requires a credential"):
        await node.execute(ctx)
