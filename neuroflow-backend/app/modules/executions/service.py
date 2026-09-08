"""Execution business rules. Framework-agnostic -- raises `AppError`
subclasses, never `HTTPException`. See docs/08-backend-architecture.md #8.1
and docs/09-domain-modules.md #9.9.

Access is resolved via `WorkflowService.get`/`get_role_for_project`, the
same project->org->role chokepoint every other module uses: an execution
belonging to a workflow the caller's org can't see 404s via that lookup
failing, never 403s.
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from arq.connections import ArqRedis
from redis.asyncio import Redis

from app.core.execution_channels import cancel_key
from app.core.pagination import Cursor, build_keyset_page, clamp_limit
from app.core.permissions import Role
from app.modules.audit.service import AuditService
from app.modules.executions.exceptions import (
    ExecutionNotCancelableError,
    ExecutionNotFoundError,
    ExecutionNotResumableError,
    ExecutionNotRetryableError,
)
from app.modules.executions.models import Execution, NodeExecution
from app.modules.executions.repository import (
    ExecutionDataRepository,
    ExecutionRepository,
    NodeExecutionRepository,
)
from app.modules.executions.waiting import apply_resume
from app.modules.projects.models import Project
from app.modules.workflows.service import WorkflowService

_CANCELABLE_STATUSES = {"queued", "running", "waiting"}
_RETRYABLE_STATUSES = {"error", "canceled"}


class ExecutionService:
    def __init__(
        self,
        executions: ExecutionRepository,
        node_executions: NodeExecutionRepository,
        execution_data: ExecutionDataRepository,
        workflows: WorkflowService,
        audit: AuditService,
        redis: Redis,
        queue: ArqRedis,
    ) -> None:
        self._executions = executions
        self._node_executions = node_executions
        self._data = execution_data
        self._workflows = workflows
        self._audit = audit
        self._redis = redis
        self._queue = queue

    async def create_and_enqueue(
        self,
        *,
        workflow_id: UUID,
        mode: str,
        trigger_data: dict[str, Any] | None,
        actor_id: UUID,
    ) -> Execution:
        workflow, project, _role = await self._workflows.get(
            workflow_id=workflow_id, user_id=actor_id
        )
        version = await self._workflows.get_active_version(workflow)
        execution = await self._executions.create(
            workflow_id=workflow.id,
            workflow_version_id=version.id,
            project_id=project.id,
            mode=mode,
            trigger_data=trigger_data,
            created_by=actor_id,
            created_at=datetime.now(UTC),
        )
        await self._queue.enqueue_job("run_execution", execution.id)
        await self._audit.record(
            organization_id=project.organization_id,
            actor_id=actor_id,
            action="execution.created",
            resource_type="execution",
            resource_id=execution.id,
            changes={"workflowId": str(workflow.id), "mode": mode},
        )
        return execution

    async def create_and_enqueue_system(
        self,
        *,
        workflow_id: UUID,
        mode: str,
        trigger_data: dict[str, Any] | None,
        parent_execution_id: UUID | None = None,
    ) -> Execution:
        """For triggers with no authenticated actor: webhook ingress and
        the schedule tick. Resolves the workflow via `WorkflowService.
        get_unchecked` rather than `get()`'s actor-authorization check --
        there is no actor, only the system itself. Still pins
        `workflow_version_id` at enqueue time exactly like
        `create_and_enqueue` (docs/12-execution-engine.md #12.2)."""
        workflow = await self._workflows.get_unchecked(workflow_id)
        if workflow is None:
            raise ExecutionNotFoundError("Workflow not found")
        version = await self._workflows.get_active_version(workflow)
        execution = await self._executions.create(
            workflow_id=workflow.id,
            workflow_version_id=version.id,
            project_id=workflow.project_id,
            mode=mode,
            trigger_data=trigger_data,
            created_by=None,
            created_at=datetime.now(UTC),
        )
        if parent_execution_id is not None:
            execution.parent_execution_id = parent_execution_id
        await self._queue.enqueue_job("run_execution", execution.id)
        return execution

    async def get_role_for_project(self, *, project_id: UUID, user_id: UUID) -> Role:
        return await self._workflows.get_role_for_project(
            project_id=project_id, user_id=user_id
        )

    async def get(
        self, *, execution_id: UUID, user_id: UUID
    ) -> tuple[Execution, Project, Role]:
        execution = await self._executions.get_by_id(execution_id)
        if execution is None:
            raise ExecutionNotFoundError("Execution not found")
        _workflow, project, role = await self._workflows.get(
            workflow_id=execution.workflow_id, user_id=user_id
        )
        return execution, project, role

    async def list_for_project(
        self,
        *,
        project_id: UUID,
        user_id: UUID,
        workflow_id: UUID | None,
        status: str | None,
        mode: str | None,
        limit: int | None,
        cursor_token: str | None,
    ) -> tuple[list[Execution], str | None, bool]:
        await self._workflows.get_role_for_project(
            project_id=project_id, user_id=user_id
        )
        page_limit = clamp_limit(limit)
        cursor = Cursor.decode(cursor_token) if cursor_token else None
        rows = await self._executions.list_with_filters(
            project_id=project_id,
            workflow_id=workflow_id,
            status=status,
            mode=mode,
            limit=page_limit,
            cursor=(cursor.created_at, cursor.id) if cursor else None,
        )
        page_rows, next_cursor, has_more = build_keyset_page(rows, limit=page_limit)
        return page_rows, next_cursor, has_more

    async def get_nodes(self, execution_id: UUID) -> list[NodeExecution]:
        return await self._node_executions.list_for_execution(execution_id)

    async def get_node_data(
        self, *, execution_id: UUID, node_id: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        row = await self._node_executions.get_by_node_id(execution_id, node_id)
        if row is None:
            raise ExecutionNotFoundError("Node run not found")
        return await self._load_items(row.input_data_id), await self._load_items(
            row.output_data_id
        )

    async def _load_items(self, data_id: UUID | None) -> list[dict[str, Any]]:
        if data_id is None:
            return []
        row = await self._data.get(data_id)
        if row is None or row.kind != "inline" or not isinstance(row.data, list):
            return []
        return [entry for entry in row.data if isinstance(entry, dict)]

    async def cancel(
        self, *, execution: Execution, organization_id: UUID, actor_id: UUID
    ) -> Execution:
        if execution.status not in _CANCELABLE_STATUSES:
            raise ExecutionNotCancelableError(
                f"Execution is already {execution.status}"
            )
        if execution.status == "queued":
            await self._executions.finish(
                execution, status="canceled", at=datetime.now(UTC)
            )
        else:
            await self._redis.set(cancel_key(execution.id), "1", ex=3600)
        await self._audit.record(
            organization_id=organization_id,
            actor_id=actor_id,
            action="execution.canceled",
            resource_type="execution",
            resource_id=execution.id,
        )
        return execution

    async def resume(
        self, *, execution_id: UUID, resume_token: str, payload: dict[str, Any] | None
    ) -> Execution:
        """The token itself is the authorization -- an approval-link
        recipient need not be a NeuroFlow member -- so this takes no
        `actor_id`/role check, unlike every other mutating method here.
        See docs/12-execution-engine.md #12.5."""
        execution = await self._executions.get_by_id(execution_id)
        if execution is None:
            raise ExecutionNotFoundError("Execution not found")
        if execution.status != "waiting" or execution.resume_token != resume_token:
            raise ExecutionNotResumableError(
                "Execution is not waiting, or the resume token is invalid"
            )
        await apply_resume(
            execution,
            payload,
            node_executions=self._node_executions,
            data=self._data,
            queue=self._queue,
        )
        return execution

    async def retry(
        self,
        *,
        execution: Execution,
        organization_id: UUID,
        actor_id: UUID,
        from_failed_node: bool,
    ) -> Execution:
        if execution.status not in _RETRYABLE_STATUSES:
            raise ExecutionNotRetryableError(
                "Only a failed or canceled execution can be retried"
            )
        new_execution = await self._executions.create(
            workflow_id=execution.workflow_id,
            workflow_version_id=execution.workflow_version_id,
            project_id=execution.project_id,
            mode="retry",
            trigger_data=execution.trigger_data,
            created_by=actor_id,
            created_at=datetime.now(UTC),
            retry_of_execution_id=execution.id,
        )
        if from_failed_node:
            failed_node_id = (execution.error or {}).get("nodeId")
            await self._node_executions.copy_successful(
                from_execution_id=execution.id,
                to_execution_id=new_execution.id,
                up_to_node_id=failed_node_id,
            )
        await self._queue.enqueue_job("run_execution", new_execution.id)
        await self._audit.record(
            organization_id=organization_id,
            actor_id=actor_id,
            action="execution.retried",
            resource_type="execution",
            resource_id=new_execution.id,
            changes={
                "retriedFrom": str(execution.id),
                "fromFailedNode": from_failed_node,
            },
        )
        return new_execution

    async def delete(
        self, *, execution: Execution, organization_id: UUID, actor_id: UUID
    ) -> None:
        await self._executions.delete(execution)
        await self._audit.record(
            organization_id=organization_id,
            actor_id=actor_id,
            action="execution.deleted",
            resource_type="execution",
            resource_id=execution.id,
        )

    async def bulk_delete(
        self,
        *,
        project_id: UUID,
        user_id: UUID,
        workflow_id: UUID | None,
        status: str | None,
    ) -> int:
        await self._workflows.get_role_for_project(
            project_id=project_id, user_id=user_id
        )
        return await self._executions.bulk_delete(
            project_id=project_id, workflow_id=workflow_id, status=status
        )

    async def stats(self, *, project_id: UUID, user_id: UUID) -> dict[str, int]:
        await self._workflows.get_role_for_project(
            project_id=project_id, user_id=user_id
        )
        return await self._executions.stats_by_status(project_id=project_id)
