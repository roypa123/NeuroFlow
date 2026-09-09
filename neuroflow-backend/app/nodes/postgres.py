"""Postgres -- runs a parametrized query against a user's own database,
named by a `postgresApi` credential. See docs/13-node-catalog-and-sdk.md
#13.5 and this phase's plan, findings #3/#4: the credential has no
`AuthenticationSpec` (it isn't an HTTP auth scheme), so this node reads
`ctx.credentials["credentialId"].data` directly and opens its own short-
lived `psycopg` connection -- never the app's own database pool. One of
only two "integration" nodes this phase ships, chosen because the target
infrastructure (Postgres) is actually reachable and live-testable in this
environment, unlike the vendor SaaS APIs this phase explicitly defers.
"""

from __future__ import annotations

from typing import Any

import psycopg
from psycopg.rows import dict_row

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import (
    CredentialRequirement,
    Item,
    NodeProperty,
    NodeTypeDescriptor,
    PortSpec,
)


def _build_conninfo(data: dict[str, Any]) -> str:
    parts = [
        f"host={data.get('host', '')}",
        f"port={data.get('port', 5432)}",
        f"dbname={data.get('database', '')}",
        f"user={data.get('user', '')}",
        f"password={data.get('password', '')}",
        f"sslmode={'require' if data.get('ssl') else 'prefer'}",
    ]
    return " ".join(parts)


class PostgresNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.postgres",
        version=1,
        name="Postgres",
        group="action",
        category="Database",
        description="Runs a SQL query against a Postgres database.",
        icon="database",
        color="cat-app",
        aliases=["sql", "postgresql"],
        subtitle="={{ $parameter.query }}",
        inputs=[PortSpec(type="main")],
        outputs=[PortSpec(type="main")],
        credentials=[CredentialRequirement(types=["postgresApi"], required=True)],
        idempotent=False,
        properties=[
            NodeProperty(
                name="credentialId",
                display_name="Credential",
                type="credential",
                required=True,
                description="Postgres connection to run the query against.",
                type_options={"credentialTypes": ["postgresApi"]},
            ),
            NodeProperty(
                name="query",
                display_name="Query",
                type="code",
                required=True,
                placeholder="SELECT * FROM users WHERE id = %(id)s",
                description="Use %(name)s placeholders bound from Query Parameters.",
            ),
            NodeProperty(
                name="queryParameters",
                display_name="Query Parameters",
                type="json",
                default={},
                description="Object of placeholder name -> value.",
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        params = ctx.params
        query = params.get("query", "")
        query_params = params.get("queryParameters") or {}
        binding = ctx.credentials.get("credentialId")
        if binding is None:
            raise RuntimeError("Postgres node requires a credential")

        conninfo = _build_conninfo(binding.data)
        results: list[Item] = []
        async with await psycopg.AsyncConnection.connect(conninfo) as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(query, query_params)
                if cur.description is not None:
                    rows = await cur.fetchall()
                    results = [Item(json=dict(row)) for row in rows]
                else:
                    results = [Item(json={"rowCount": cur.rowcount})]
            await conn.commit()
        return {"main": [results]}
