"""Reachability-aware DAG scheduling. See docs/12-execution-engine.md #12.3.

A node runs once every upstream node it depends on has completed *and* at
least one incoming edge actually carried data (its source activated that
output handle). A node whose only live incoming edges all come from a dead
branch (e.g. connected solely to an IF node's "false" output when "true"
was taken) is marked `skipped` instead of waiting forever -- and that skip
cascades to its own successors the same way.
"""

from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime
from typing import Any
from uuid import UUID

from redis.asyncio import Redis

from app.core.execution_channels import cancel_key
from app.core.object_storage import ObjectStorage
from app.engine.context import ExecutionContext
from app.engine.dag import DAG
from app.engine.events import EventPublisher
from app.engine.models import NodeResult
from app.engine.runtime import run_node
from app.modules.executions.repository import (
    ExecutionDataRepository,
    NodeExecutionRepository,
)
from app.modules.nodes.descriptors import Item
from app.modules.workflows.schemas import GraphEdge


class ExecutionCanceledError(Exception):
    pass


class ExecutionFailedError(Exception):
    def __init__(self, error: dict[str, Any]) -> None:
        super().__init__(error.get("message", "Node execution failed"))
        self.error = error


class ExecutionSuspendedError(Exception):
    """Raised the moment a node's `NodeResult.status == "waiting"` reaches
    the batch loop -- mirrors `ExecutionFailedError`'s short-circuit, since
    the resume payload isn't known yet and successors must not be
    scheduled from a dead/incomplete branch. See docs/12-execution-
    engine.md #12.5."""

    def __init__(self, resume_token: str, resume_after: datetime | None) -> None:
        super().__init__("Execution suspended")
        self.resume_token = resume_token
        self.resume_after = resume_after


def _handle_of(edge: GraphEdge) -> str:
    return edge.source_handle or "main"


def _target_handle_of(edge: GraphEdge) -> str:
    """Which of the target node's declared input ports this edge feeds --
    e.g. Merge/Compare Datasets' "Input 1"/"Input 2". Defaults to "main"
    for every existing single-input node, whose edges never set
    `target_handle` -- see this phase's plan, finding #2."""
    return edge.target_handle or "main"


async def execute_dag(
    dag: DAG,
    ctx: ExecutionContext,
    *,
    execution_id: UUID,
    node_exec_repo: NodeExecutionRepository,
    data_repo: ExecutionDataRepository,
    storage: ObjectStorage,
    redis: Redis,
    publisher: EventPublisher,
    trigger_items: list[Item] | None = None,
    preloaded: dict[str, NodeResult] | None = None,
) -> None:
    completed: dict[str, NodeResult] = dict(preloaded or {})
    # node id -> input port handle -> items delivered on that port. Most
    # nodes declare one "main" input port; Merge/Compare Datasets declare
    # two, and `target_handle` (already modeled on `GraphEdge`, previously
    # unused) is what keeps their two branches from being flattened
    # together -- see this phase's plan, finding #2.
    inputs: dict[str, dict[str, list[Item]]] = {}
    ready: deque[str] = deque()
    enqueued: set[str] = set(completed.keys())

    def process_completion(node_id: str, result: NodeResult) -> None:
        completed[node_id] = result
        for edge in dag.nodes_by_id[node_id].outgoing:
            target = edge.target
            if target in completed or target in enqueued:
                continue
            target_incoming = dag.nodes_by_id[target].incoming
            if any(e.source not in completed for e in target_incoming):
                continue  # still waiting on another upstream branch

            active_incoming = [
                e
                for e in target_incoming
                if completed[e.source].status == "success"
                and completed[e.source].outputs.get(_handle_of(e))
            ]
            enqueued.add(target)
            if active_incoming or not target_incoming:
                gathered_by_port: dict[str, list[Item]] = {}
                for e in active_incoming:
                    port_items = gathered_by_port.setdefault(_target_handle_of(e), [])
                    port_items.extend(
                        completed[e.source].outputs.get(_handle_of(e), [])
                    )
                inputs[target] = gathered_by_port
                ready.append(target)
            else:
                # Every upstream branch feeding this node is dead --
                # cascade the skip to its own successors too.
                process_completion(target, NodeResult(status="skipped"))

    for node_id in dag.trigger_node_ids():
        if node_id in completed:
            continue
        inputs[node_id] = {"main": trigger_items or []}
        ready.append(node_id)
        enqueued.add(node_id)

    for node_id, result in list(completed.items()):
        process_completion(node_id, result)

    while ready:
        if await redis.get(cancel_key(execution_id)):
            raise ExecutionCanceledError

        batch_size = min(len(ready), ctx.max_parallel)
        batch_ids = [ready.popleft() for _ in range(batch_size)]
        for node_id in batch_ids:
            await publisher.publish("node.started", {"nodeId": node_id})

        results = await asyncio.gather(
            *(
                run_node(
                    dag.nodes_by_id[node_id],
                    inputs.get(node_id, {}),
                    ctx,
                    execution_id=execution_id,
                    node_exec_repo=node_exec_repo,
                    data_repo=data_repo,
                    storage=storage,
                )
                for node_id in batch_ids
            )
        )

        for node_id, result in zip(batch_ids, results, strict=True):
            for level, message in result.logs:
                await publisher.publish(
                    "node.log", {"nodeId": node_id, "level": level, "message": message}
                )
            await publisher.publish(
                "node.finished",
                {
                    "nodeId": node_id,
                    "status": result.status,
                    "durationMs": result.duration_ms,
                    "itemsOut": result.items_out,
                },
            )
            if result.status == "waiting":
                raise ExecutionSuspendedError(
                    result.resume_token or "", result.resume_after
                )
            on_error = dag.nodes_by_id[node_id].node.on_error
            if result.status == "error" and on_error == "stop":
                default_error = {"message": "Node execution failed"}
                raise ExecutionFailedError(result.error or default_error)
            process_completion(node_id, result)
