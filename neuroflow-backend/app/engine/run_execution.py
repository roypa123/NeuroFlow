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

from app.core.config import get_settings
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
from app.engine.scheduler import (
    ExecutionCanceledError,
    ExecutionFailedError,
    ExecutionSuspendedError,
    execute_dag,
)
from app.engine.secrets import SecretRegistry
from app.modules.audit.repository import AuditRepository
from app.modules.audit.service import AuditService
from app.modules.credentials.decryption import get_decrypted_credential
from app.modules.credentials.repository import CredentialRepository
from app.modules.credentials.types import CredentialBinding, get_credential_type
from app.modules.executions.repository import (
    ExecutionDataRepository,
    ExecutionRepository,
    NodeExecutionRepository,
)
from app.modules.nodes.base import ExecutionInfo, WorkflowInfo
from app.modules.nodes.descriptors import Item
from app.modules.projects.repository import ProjectRepository
from app.modules.variables.decryption import get_vars_snapshot
from app.modules.variables.repository import VariableRepository
from app.modules.workflows.repository import (
    WorkflowRepository,
    WorkflowVersionRepository,
)
from app.modules.workflows.schemas import WorkflowGraph

logger = get_logger(__name__)


async def _hydrate_preloaded(
    execution_id: UUID,
    node_exec_repo: NodeExecutionRepository,
    data_repo: ExecutionDataRepository,
) -> dict[str, NodeResult]:
    """Rebuilds `NodeResult`s for node runs already recorded against this
    execution id, so the scheduler treats them as done instead of
    re-running them. Used both by `retry(from_failed_node=True)` (a new
    execution id with copied rows) and by resume-after-suspend (the *same*
    execution id, whose suspended node's row `ExecutionService.resume` has
    already flipped from `waiting` to `success` before re-enqueueing) --
    for a brand-new execution this simply finds no rows and returns `{}`.

    Known simplification: `NodeExecution.output_data_id` (per
    docs/10-database-schema.md #10.5) stores one payload for the whole
    node, not per output handle -- so a *branch* node's replayed output is
    reattached under a synthetic "main" handle rather than its original
    "true"/"false" handle. This only affects retrying/resuming a run where
    a branch node itself succeeded before the failure/suspension point;
    the common linear-chain case is unaffected.
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


async def _resolve_credential_bindings(
    graph: WorkflowGraph,
    *,
    session: Any,
    organization_id: UUID,
    execution_id: UUID,
    secret_registry: SecretRegistry,
) -> dict[str, CredentialBinding]:
    """Resolved once per execution, before any node runs -- see this
    phase's plan finding #4: every decrypted value is registered with the
    execution's `SecretRegistry` here, at the one place decryption happens,
    rather than trusting every future call site to remember to redact.
    """
    credential_repo = CredentialRepository(session)
    audit = AuditService(AuditRepository(session))
    bindings: dict[str, CredentialBinding] = {}
    for node in graph.nodes:
        raw_id = node.parameters.get("credentialId")
        if not raw_id:
            continue
        try:
            credential = await credential_repo.get_by_id(UUID(str(raw_id)))
        except ValueError:
            credential = None
        if credential is None:
            continue
        credential_type = get_credential_type(credential.type)
        if credential_type is None:
            continue
        data = await get_decrypted_credential(
            credential.id,
            session=session,
            audit=audit,
            organization_id=organization_id,
            execution_id=execution_id,
        )
        secret_registry.register_many(data.values())
        bindings[node.id] = CredentialBinding(
            data=data, authenticate=credential_type.authenticate
        )
    return bindings


async def run_execution(_ctx: dict[str, Any], execution_id: UUID) -> None:
    registry = build_runtime_registry()
    redis = get_redis()

    async with session_scope() as session:
        execution_repo = ExecutionRepository(session)
        node_exec_repo = NodeExecutionRepository(session)
        data_repo = ExecutionDataRepository(session)
        workflow_repo = WorkflowRepository(session)
        version_repo = WorkflowVersionRepository(session)
        project_repo = ProjectRepository(session)

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
        project = (
            await project_repo.get_by_id(workflow.project_id)
            if workflow is not None
            else None
        )
        if workflow is None or version is None or project is None:
            await execution_repo.finish(
                execution,
                status="error",
                at=datetime.now(UTC),
                error={"message": "Workflow, project, or pinned version no longer exists"},
            )
            return

        graph = WorkflowGraph.model_validate(version.graph)
        publisher = EventPublisher(redis, execution_id)

        await execution_repo.mark_running(execution, at=datetime.now(UTC))
        await publisher.publish("execution.started", {"status": "running"})

        try:
            dag = DAG.from_graph(graph, registry)
        except GraphValidationError as exc:
            error = {
                "message": str(exc),
                "code": "execution.invalid_graph",
                "errors": exc.errors,
            }
            at = datetime.now(UTC)
            await execution_repo.finish(execution, status="error", at=at, error=error)
            await publisher.publish(
                "execution.finished", {"status": "error", "error": error}
            )
            return

        secret_registry = SecretRegistry()
        credential_bindings = await _resolve_credential_bindings(
            graph,
            session=session,
            organization_id=project.organization_id,
            execution_id=execution_id,
            secret_registry=secret_registry,
        )
        vars_snapshot, secret_var_values = await get_vars_snapshot(
            repository=VariableRepository(session),
            organization_id=project.organization_id,
            project_id=project.id,
            master_key=get_settings().credential_master_key.get_secret_value(),
        )
        secret_registry.register_many(secret_var_values)

        http_client = AsyncHttpClient(timeout=30.0)
        workflow_info = WorkflowInfo(
            id=str(workflow.id), name=workflow.name, active=workflow.is_active
        )
        engine_ctx = ExecutionContext(
            workflow_info=workflow_info,
            execution_info=ExecutionInfo(id=str(execution.id), mode=execution.mode),
            registry=registry,
            http_client=http_client,
            credential_bindings=credential_bindings,
            vars_snapshot=vars_snapshot,
            secret_registry=secret_registry,
        )
        storage = build_object_storage()

        preloaded = await _hydrate_preloaded(execution_id, node_exec_repo, data_repo)

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
                trigger_items=_trigger_items(execution.trigger_data),
                preloaded=preloaded,
            )
        except ExecutionCanceledError:
            await execution_repo.finish(
                execution, status="canceled", at=datetime.now(UTC)
            )
            await publisher.publish("execution.finished", {"status": "canceled"})
            return
        except ExecutionFailedError as exc:
            error = secret_registry.redact_json(exc.error)
            await execution_repo.finish(
                execution, status="error", at=datetime.now(UTC), error=error
            )
            await publisher.publish(
                "execution.finished", {"status": "error", "error": error}
            )
            return
        except ExecutionSuspendedError as exc:
            execution.status = "waiting"
            execution.resume_token = exc.resume_token
            execution.resume_after = exc.resume_after
            await session.flush()
            await publisher.publish(
                "execution.suspended",
                {
                    "status": "waiting",
                    "resumeAfter": exc.resume_after.isoformat() if exc.resume_after else None,
                },
            )
            return
        finally:
            await http_client.aclose()

        await execution_repo.finish(execution, status="success", at=datetime.now(UTC))
        await publisher.publish("execution.finished", {"status": "success"})


def _trigger_items(trigger_data: dict[str, Any] | None) -> list[Item]:
    """Webhook/schedule/sub-workflow executions carry their payload on
    `Execution.trigger_data` (set at creation, per docs/10-database-
    schema.md #10.5); a manual run has none. See app.nodes.manual_trigger/
    webhook_trigger/schedule_trigger -- every trigger node is a pass-
    through of whatever items the scheduler seeds it with."""
    if not trigger_data:
        return []
    return [Item(json=trigger_data)]
