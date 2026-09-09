"""Unit coverage for the pure connection-string builder and the
credential-required error path. The actual query execution against a
real database is covered live in
`tests/integration/test_postgres_node.py` -- see this phase's plan."""

from __future__ import annotations

import pytest

from app.modules.nodes.base import NodeExecutionContext
from app.nodes.postgres import PostgresNode, _build_conninfo


def test_build_conninfo_includes_all_fields() -> None:
    conninfo = _build_conninfo(
        {
            "host": "db.example.com",
            "port": 5433,
            "database": "app",
            "user": "alice",
            "password": "secret",
            "ssl": True,
        }
    )

    assert "host=db.example.com" in conninfo
    assert "port=5433" in conninfo
    assert "dbname=app" in conninfo
    assert "user=alice" in conninfo
    assert "password=secret" in conninfo
    assert "sslmode=require" in conninfo


def test_build_conninfo_defaults_ssl_to_prefer() -> None:
    conninfo = _build_conninfo(
        {"host": "h", "database": "d", "user": "u", "password": "p"}
    )

    assert "sslmode=prefer" in conninfo


async def test_missing_credential_raises() -> None:
    node = PostgresNode()
    ctx = NodeExecutionContext(input_items=[], params={"query": "SELECT 1"})

    with pytest.raises(RuntimeError, match="requires a credential"):
        await node.execute(ctx)
