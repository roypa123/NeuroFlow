"""Executes one node: parameter/expression resolution, retries (idempotent
nodes only), per-node error policy, and `NodeExecution`/`ExecutionData`
persistence. See docs/12-execution-engine.md #12.4.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import tenacity

from app.core.config import get_settings
from app.core.object_storage import ObjectStorage
from app.core.uuid7 import uuid7
from app.engine.context import ExecutionContext
from app.engine.dag import DagNode
from app.engine.expressions import ExpressionError
from app.engine.models import NodeResult
from app.engine.redaction import SecretRegistry
from app.modules.executions.repository import (
    ExecutionDataRepository,
    NodeExecutionRepository,
)
from app.modules.nodes.base import ExecutionSuspended, NodeExecutionContext
from app.modules.nodes.descriptors import Item, NodeTypeDescriptor

INLINE_THRESHOLD_BYTES = 64 * 1024


def flatten_output(
    descriptor: NodeTypeDescriptor, node_output: dict[str, list[list[Item]]]
) -> dict[str, list[Item]]:
    """Maps a node's positional `NodeOutput` arrays onto handle ids the
    frontend/DAG both understand -- the same `label or "main"` convention
    `BaseNode.tsx` uses for React Flow handle ids (docs/06-canvas-and-editor.md
    #6.4)."""
    result: dict[str, list[Item]] = {}
    for port_type, arrays in node_output.items():
        ports_of_type = [p for p in descriptor.outputs if p.type == port_type]
        for index, items in enumerate(arrays):
            if index < len(ports_of_type):
                handle = ports_of_type[index].label or "main"
            else:
                handle = "main"
            result.setdefault(handle, []).extend(items)
    return result


def build_error_dict(
    dag_node: DagNode, exc: Exception, *, secret_registry: SecretRegistry | None = None
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "nodeId": dag_node.node.id,
        "nodeName": dag_node.node.name or dag_node.node.id,
        "message": str(exc),
        "code": type(exc).__name__,
    }
    if isinstance(exc, ExpressionError):
        base["expression"] = exc.expression
        base["scope"] = exc.scope
    # Provider errors frequently echo the request, including a credential
    # value -- redact before this is ever persisted or shown in the UI.
    # See docs/15-security-and-credentials.md #15.6 item 5.
    if secret_registry is not None:
        base = secret_registry.redact_json(base)
    return base


async def store_items(
    items: list[Item],
    *,
    execution_id: UUID,
    data_repo: ExecutionDataRepository,
    storage: ObjectStorage,
    secret_registry: SecretRegistry | None = None,
) -> UUID | None:
    if not items:
        return None
    payload = [item.model_dump(by_alias=True) for item in items]
    if secret_registry is not None:
        payload = secret_registry.redact_json(payload)
    raw = json.dumps(payload, default=str).encode()

    max_bytes = get_settings().max_payload_mb * 1024 * 1024
    if len(raw) > max_bytes:
        row = await data_repo.create_inline(
            execution_id=execution_id,
            data=None,
            item_count=len(items),
            size_bytes=len(raw),
            truncated=True,
        )
        return row.id
    if len(raw) <= INLINE_THRESHOLD_BYTES:
        row = await data_repo.create_inline(
            execution_id=execution_id,
            data=payload,
            item_count=len(items),
            size_bytes=len(raw),
        )
        return row.id
    object_key = f"executions/{execution_id}/{uuid7()}.json"
    await storage.put(object_key, raw, content_type="application/json")
    row = await data_repo.create_object_reference(
        execution_id=execution_id,
        object_key=object_key,
        item_count=len(items),
        size_bytes=len(raw),
    )
    return row.id


def _retry_kwargs(dag_node: DagNode) -> dict[str, Any]:
    node = dag_node.node
    return {
        "stop": tenacity.stop_after_attempt(max(1, node.max_tries)),
        "wait": tenacity.wait_exponential_jitter(
            initial=node.wait_between_tries_ms / 1000
        ),
        # ExecutionSuspended is a deliberate control-flow signal, not a
        # transient failure -- retrying it would turn a Wait node's
        # suspension into a busy-retry loop.
        "retry": tenacity.retry_if_exception_type(Exception)
        & tenacity.retry_if_not_exception_type(ExecutionSuspended),
        "reraise": True,
    }


async def run_node(
    dag_node: DagNode,
    input_items: list[Item],
    ctx: ExecutionContext,
    *,
    execution_id: UUID,
    node_exec_repo: NodeExecutionRepository,
    data_repo: ExecutionDataRepository,
    storage: ObjectStorage,
) -> NodeResult:
    node = dag_node.node
    descriptor = dag_node.descriptor
    node_cls = ctx.registry.get(node.type, node.type_version)

    started_at = datetime.now(UTC)
    node_exec = await node_exec_repo.create(
        execution_id=execution_id,
        node_id=node.id,
        node_name=node.name or node.id,
        node_type=node.type,
        run_index=0,
        started_at=started_at,
    )

    resolver = ctx.build_resolver(node, input_items)
    captured_logs: list[tuple[str, str]] = []

    async def _attempt() -> dict[str, list[list[Item]]]:
        params0 = resolver(0)
        binding = ctx.credential_bindings.get(node.id)
        node_ctx = NodeExecutionContext(
            input_items=input_items,
            params=params0,
            http=ctx.http_client,
            credentials={"credentialId": binding} if binding is not None else {},
            workflow=ctx.workflow_info,
            execution=ctx.execution_info,
            run_index=0,
            resolver=resolver,
        )
        instance = node_cls()
        try:
            return await instance.execute(node_ctx)
        finally:
            # Captures logs even on failure/retry -- a retried attempt's
            # own log lines (e.g. "Retrying after 429") still matter.
            captured_logs.extend(node_ctx.logs)

    retries = 0
    try:
        if descriptor.idempotent and node.max_tries > 1:
            retrying = tenacity.AsyncRetrying(**_retry_kwargs(dag_node))
            output = await retrying.wraps(_attempt)()
            retries = retrying.statistics.get("attempt_number", 1) - 1
        else:
            output = await _attempt()
    except ExecutionSuspended as exc:
        finished_at = datetime.now(UTC)
        await node_exec_repo.finish(
            node_exec,
            status="waiting",
            at=finished_at,
            items_in=len(input_items),
        )
        return NodeResult(
            status="waiting",
            duration_ms=_ms(started_at, finished_at),
            items_in=len(input_items),
            resume_token=exc.resume_token,
            resume_after=exc.resume_after,
        )
    except Exception as exc:  # noqa: BLE001 -- node/expression errors are data, not crashes
        error = build_error_dict(dag_node, exc, secret_registry=ctx.secret_registry)
        finished_at = datetime.now(UTC)
        duration_ms = _ms(started_at, finished_at)
        if node.on_error == "stop":
            await node_exec_repo.finish(
                node_exec,
                status="error",
                at=finished_at,
                items_in=len(input_items),
                error=error,
            )
            return NodeResult(
                status="error",
                error=error,
                duration_ms=duration_ms,
                items_in=len(input_items),
            )
        # continue / continueErrorOutput: emit the error as data rather than
        # failing the whole execution -- docs/12-execution-engine.md #12.4.
        error_item = Item(json={"error": error})
        handle = "error" if node.on_error == "continueErrorOutput" else "main"
        outputs = {handle: [error_item]}
        output_data_id = await store_items(
            [error_item],
            execution_id=execution_id,
            data_repo=data_repo,
            storage=storage,
            secret_registry=ctx.secret_registry,
        )
        await node_exec_repo.finish(
            node_exec,
            status="error",
            at=finished_at,
            items_in=len(input_items),
            items_out=1,
            error=error,
            output_data_id=output_data_id,
        )
        return NodeResult(
            status="error",
            outputs=outputs,
            error=error,
            duration_ms=duration_ms,
            items_in=len(input_items),
        )

    flattened = flatten_output(descriptor, output)
    all_output_items = [item for items in flattened.values() for item in items]
    finished_at = datetime.now(UTC)
    output_data_id = await store_items(
        all_output_items,
        execution_id=execution_id,
        data_repo=data_repo,
        storage=storage,
        secret_registry=ctx.secret_registry,
    )
    await node_exec_repo.finish(
        node_exec,
        status="success",
        at=finished_at,
        items_in=len(input_items),
        items_out=len(all_output_items),
        output_data_id=output_data_id,
    )
    ctx.record_node_output(node.name or node.id, all_output_items)
    return NodeResult(
        status="success",
        outputs=flattened,
        duration_ms=_ms(started_at, finished_at),
        items_in=len(input_items),
        items_out=len(all_output_items),
        retries=retries,
        logs=[(level, ctx.secret_registry.redact(msg)) for level, msg in captured_logs],
    )


def _ms(started: datetime, finished: datetime) -> int:
    return int((finished - started).total_seconds() * 1000)
