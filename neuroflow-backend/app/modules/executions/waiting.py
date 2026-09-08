"""Shared "wait for an execution to finish, then fetch its last
successful node's output" helper.

Used by both sub-workflow execution (`app.nodes.execute_workflow`,
worker-side) and the webhook `last_node` response mode
(`app.modules.webhooks.ingress_controller`, API-side). Neither of those
two may import the other (the API/engine import boundary in
pyproject.toml), so this lives in `app.modules.executions`, which both
already depend on.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from arq.connections import ArqRedis
from redis.asyncio import Redis
from redis.asyncio.client import PubSub

from app.core.database import session_scope
from app.core.execution_channels import channel_name
from app.modules.executions.models import Execution
from app.modules.executions.repository import ExecutionDataRepository, NodeExecutionRepository
from app.modules.nodes.descriptors import Item


async def subscribe(redis: Redis, execution_id: UUID) -> PubSub:
    """Call this *before* the execution is enqueued -- subscribing after
    enqueueing races the child publishing `execution.finished` into a
    channel nothing is listening to yet."""
    pubsub = redis.pubsub()
    await pubsub.subscribe(channel_name(execution_id))
    return pubsub


async def wait_for_finish(
    pubsub: PubSub, *, timeout_seconds: float, poll_seconds: float = 15.0
) -> str:
    """Returns the terminal status, or "timeout" if `timeout_seconds`
    elapses first. Always unsubscribes/closes `pubsub` before returning."""
    try:
        elapsed = 0.0
        while elapsed < timeout_seconds:
            remaining = min(poll_seconds, timeout_seconds - elapsed)
            message = await pubsub.get_message(
                ignore_subscribe_messages=True, timeout=remaining
            )
            elapsed += remaining
            if message is None:
                continue
            payload = json.loads(message["data"])
            if payload.get("event") == "execution.finished":
                return str(payload.get("status", "error"))
        return "timeout"
    finally:
        await pubsub.aclose()  # type: ignore[no-untyped-call]


async def load_last_output_items(execution_id: UUID) -> list[Item]:
    """Known simplification: the "last" node by finish timestamp, not a
    proper DAG-terminal-node computation -- correct for the common
    single-branch case, which is all a sub-workflow call or a `last_node`
    webhook response needs to prove this phase."""
    async with session_scope() as session:
        node_exec_repo = NodeExecutionRepository(session)
        data_repo = ExecutionDataRepository(session)
        rows = await node_exec_repo.list_for_execution(execution_id)
        successful = [r for r in rows if r.status == "success"]
        if not successful:
            return []
        last = max(successful, key=lambda r: r.finished_at or r.started_at)
        if last.output_data_id is None:
            return []
        data_row = await data_repo.get(last.output_data_id)
        if data_row is None or data_row.kind != "inline" or not data_row.data:
            return []
        return [Item.model_validate(entry) for entry in data_row.data]


async def apply_resume(
    execution: Execution,
    payload: dict[str, Any] | None,
    *,
    node_executions: NodeExecutionRepository,
    data: ExecutionDataRepository,
    queue: ArqRedis,
) -> None:
    """The actual resume mechanism (docs/12-execution-engine.md #12.5):
    flips the suspended node's row from `waiting` to `success` (with
    `payload` as its output, or a pass-through of its original input for a
    duration-only Wait), then flips the execution back to `queued` and
    re-enqueues the same `run_execution` job -- which rehydrates completed
    nodes via `_hydrate_preloaded` and continues from exactly where it
    stopped.

    Shared by `ExecutionService.resume`/`resume_due` (event- and
    time-based resume) and `app.engine.sweeper.resume_sweep` (the cron
    job), so both paths can never drift apart.
    """
    waiting_row = await node_executions.get_waiting(execution.id)
    if waiting_row is not None:
        output_items: list[Item] = []
        if payload:
            output_items = [Item(json=payload)]
        elif waiting_row.input_data_id is not None:
            input_row = await data.get(waiting_row.input_data_id)
            if (
                input_row is not None
                and input_row.kind == "inline"
                and isinstance(input_row.data, list)
            ):
                output_items = [Item.model_validate(entry) for entry in input_row.data]

        output_data_id = None
        if output_items:
            serialized = [item.model_dump(by_alias=True) for item in output_items]
            raw = json.dumps(serialized, default=str).encode()
            data_row = await data.create_inline(
                execution_id=execution.id,
                data=serialized,
                item_count=len(output_items),
                size_bytes=len(raw),
            )
            output_data_id = data_row.id

        await node_executions.finish(
            waiting_row,
            status="success",
            at=datetime.now(UTC),
            items_in=waiting_row.items_in,
            items_out=len(output_items),
            output_data_id=output_data_id,
        )

    execution.status = "queued"
    execution.resume_token = None
    execution.resume_after = None
    await queue.enqueue_job("run_execution", execution.id)
