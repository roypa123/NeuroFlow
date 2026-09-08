"""The arq job function that actually runs a workflow execution -- the
implementation of the lifecycle in docs/12-execution-engine.md #12.2.
Registered as `app.worker.WorkerSettings.functions`; enqueued by the API
via `pool.enqueue_job("run_execution", execution_id)` (by name, so the API
process never imports this module -- see this phase's plan finding #1).
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.database import session_scope
from app.core.http_client import AsyncHttpClient
from app.core.logging import get_logger
from app.core.object_storage import build_object_storage
from app.core.redis import get_redis
from app.engine.context import ExecutionContext
from app.engine.dag import DAG, GraphValidationError
from app.engine.events import EventPublisher
from app.engine.models import NodeResult
from app.engine.registry import build_runtime_registry
from app.engine.scheduler import ExecutionCanceled, ExecutionFailed, execute_dag
from app.modules.executions.repository import (
    ExecutionDataRepository,
    ExecutionRepository,
    NodeExecutionRepository,
)
from app.modules.nodes.base import ExecutionInfo, WorkflowInfo
from app.modules.nodes.descriptors import Item
from app.modules.workflows.repository import WorkflowRepository, WorkflowVersionRepository
from app.modules.workflows.schemas import WorkflowGraph

logger = get_logger(__name__)


async def _hydrate_preloaded(
    execution_id: UUID,
    node_exec_repo: NodeExecutionRepository,
    data_repo: ExecutionDataRepository,
) -> dict[str, NodeResult]:
    """Rebuilds `NodeResult`s for node runs `ExecutionService.retry(
    from_failed_node=True)` already copied from the original execution, so
    the scheduler treats them as done instead of re-running them.

    Known simplification: `NodeExecution.output_data_id` (per
    docs/10-database-schema.md #10.5) stores one payload for the whole
    node, not per output handle -- so a *branch* node's replayed output is
    reattached under a synthetic "main" handle rather than its original
    "true"/"false" handle. This only affects retrying a run where a branch
    node itself succeeded before the failure point; the common linear-chain
    retry is unaffected.
    """
    rows = await node_exec_repo.list_for_execution(execution_id)
    preloaded: dict[str, NodeResult] = {}
    for row in rows:
        items: list[Item] = []
        if row.output_data_id is not None:
            data_row = await data_repo.get(row.output_data_id)
            if data_row is not None and data_row.kind == "inline" and data_row.data:
                items = [Item.model_validate(entry) for entry in data_row.data]
        preloaded[row.node_id] = NodeResult(
            status="success",
            outputs={"main": items} if items else {},
            items_in=row.items_in or 0,
            items_out=row.items_out or 0,
        )
    return preloaded


async def run_execution(_ctx: dict[str, Any], execution_id: UUID) -> None:
    registry = build_runtime_registry()
    redis = get_redis()

    async with session_scope() as session:
        execution_repo = ExecutionRepository(session)
        node_exec_repo = NodeExecutionRepository(session)
        data_repo = ExecutionDataRepository(session)
        workflow_repo = WorkflowRepository(session)
        version_repo = WorkflowVersionRepository(session)

        execution = await execution_repo.get_by_id(execution_id)
        if execution is None:
            logger.error("execution.run_missing", execution_id=str(execution_id))
            return
        if execution.status != "queued":
            logger.warning(
                "execution.run_skipped_not_queued",
                execution_id=str(execution_id),
                status=execution.status,
            )
            return

        workflow = await workflow_repo.get_by_id(execution.workflow_id)
        version = await version_repo.get_by_id(execution.workflow_version_id)
        if workflow is None or version is None:
            await execution_repo.finish(
                execution,
                status="error",
                at=datetime.now(UTC),
                error={"message": "Workflow or pinned version no longer exists"},
            )
            return

        graph = WorkflowGraph.model_validate(version.graph)
        publisher = EventPublisher(redis, execution_id)

        await execution_repo.mark_running(execution, at=datetime.now(UTC))
        await publisher.publish("execution.started", {"status": "running"})

        try:
            dag = DAG.from_graph(graph, registry)
        except GraphValidationError as exc:
            error = {"message": str(exc), "code": "execution.invalid_graph", "errors": exc.errors}
            await execution_repo.finish(execution, status="error", at=datetime.now(UTC), error=error)
            await publisher.publish("execution.finished", {"status": "error", "error": error})
            return

        http_client = AsyncHttpClient(timeout=30.0)
        engine_ctx = ExecutionContext(
            workflow_info=WorkflowInfo(id=str(workflow.id), name=workflow.name, active=workflow.is_active),
            execution_info=ExecutionInfo(id=str(execution.id), mode=execution.mode),
            registry=registry,
            http_client=http_client,
        )
        storage = build_object_storage()

        preloaded = (
            await _hydrate_preloaded(execution_id, node_exec_repo, data_repo)
            if execution.retry_of_execution_id is not None
            else None
        )

        try:
            await execute_dag(
                dag,
                engine_ctx,
                execution_id=execution_id,
                node_exec_repo=node_exec_repo,
                data_repo=data_repo,
                storage=storage,
                redis=redis,
                publisher=publisher,
                trigger_items=[],
                preloaded=preloaded,
            )
        except ExecutionCanceled:
            await execution_repo.finish(execution, status="canceled", at=datetime.now(UTC))
            await publisher.publish("execution.finished", {"status": "canceled"})
            return
        except ExecutionFailed as exc:
            await execution_repo.finish(
                execution, status="error", at=datetime.now(UTC), error=exc.error
            )
            await publisher.publish("execution.finished", {"status": "error", "error": exc.error})
            return
        finally:
            await http_client.aclose()

        await execution_repo.finish(execution, status="success", at=datetime.now(UTC))
        await publisher.publish("execution.finished", {"status": "success"})
