"""Execution orchestration: authorize, call the service, map to response
schemas. See docs/08-backend-architecture.md #8.1."""
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from uuid import UUID

from redis.asyncio import Redis

from app.api.deps import RequestContext
from app.core.execution_channels import channel_name
from app.core.pagination import KeysetPage
from app.core.permissions import Permission, require
from app.modules.executions.models import Execution, NodeExecution
from app.modules.executions.schemas import (
    BulkDeleteRequest,
    BulkDeleteResponse,
    ExecutionRead,
    ExecutionStatsResponse,
    ExecutionSummary,
    ItemRead,
    NodeDataRead,
    NodeExecutionRead,
    RetryRequest,
)
from app.modules.executions.service import ExecutionService
from app.modules.workflows.repository import WorkflowVersionRepository
from app.modules.workflows.schemas import WorkflowGraph

# SSE clients poll for a new pubsub message at this interval when idle, so
# the connection can also notice the client disconnecting and a
# keep-alive comment can be sent -- see docs/11-api-design.md #11.8.
SSE_POLL_TIMEOUT_SECONDS = 15.0


def _to_summary(execution: Execution) -> ExecutionSummary:
    return ExecutionSummary(
        id=execution.id,
        workflow_id=execution.workflow_id,
        workflow_version_id=execution.workflow_version_id,
        project_id=execution.project_id,
        status=execution.status,
        mode=execution.mode,
        started_at=execution.started_at,
        finished_at=execution.finished_at,
        duration_ms=execution.duration_ms,
        created_at=execution.created_at,
    )


def _to_node_read(row: NodeExecution) -> NodeExecutionRead:
    return NodeExecutionRead(
        id=row.id,
        node_id=row.node_id,
        node_name=row.node_name,
        node_type=row.node_type,
        status=row.status,
        run_index=row.run_index,
        items_in=row.items_in,
        items_out=row.items_out,
        error=row.error,
        started_at=row.started_at,
        finished_at=row.finished_at,
        duration_ms=row.duration_ms,
    )


class ExecutionController:
    def __init__(
        self,
        service: ExecutionService,
        versions: WorkflowVersionRepository,
        redis: Redis,
    ) -> None:
        self._service = service
        self._versions = versions
        self._redis = redis

    async def _to_read(self, execution: Execution) -> ExecutionRead:
        version = await self._versions.get_by_id(execution.workflow_version_id)
        graph = (
            WorkflowGraph.model_validate(version.graph) if version else WorkflowGraph()
        )
        nodes = await self._service.get_nodes(execution.id)
        return ExecutionRead(
            **_to_summary(execution).model_dump(),
            trigger_data=execution.trigger_data,
            error=execution.error,
            parent_execution_id=execution.parent_execution_id,
            retry_of_execution_id=execution.retry_of_execution_id,
            graph=graph,
            nodes=[_to_node_read(n) for n in nodes],
        )

    async def list_for_project(
        self,
        ctx: RequestContext,
        project_id: UUID,
        *,
        workflow_id: UUID | None,
        status: str | None,
        mode: str | None,
        limit: int | None,
        cursor: str | None,
    ) -> KeysetPage[ExecutionSummary]:
        role = await self._service.get_role_for_project(
            project_id=project_id, user_id=ctx.user_id
        )
        require(role, Permission.EXECUTION_READ, scopes=ctx.scopes)
        rows, next_cursor, has_more = await self._service.list_for_project(
            project_id=project_id,
            user_id=ctx.user_id,
            workflow_id=workflow_id,
            status=status,
            mode=mode,
            limit=limit,
            cursor_token=cursor,
        )
        return KeysetPage[ExecutionSummary](
            items=[_to_summary(r) for r in rows],
            next_cursor=next_cursor,
            has_more=has_more,
        )

    async def get(self, ctx: RequestContext, execution_id: UUID) -> ExecutionRead:
        execution, _project, role = await self._service.get(
            execution_id=execution_id, user_id=ctx.user_id
        )
        require(role, Permission.EXECUTION_READ, scopes=ctx.scopes)
        return await self._to_read(execution)

    async def get_node_data(
        self, ctx: RequestContext, execution_id: UUID, node_id: str
    ) -> NodeDataRead:
        execution, _project, role = await self._service.get(
            execution_id=execution_id, user_id=ctx.user_id
        )
        require(role, Permission.EXECUTION_DATA_READ, scopes=ctx.scopes)
        input_items, output_items = await self._service.get_node_data(
            execution_id=execution.id, node_id=node_id
        )
        return NodeDataRead(
            input_items=[ItemRead.model_validate(i) for i in input_items],
            output_items=[ItemRead.model_validate(i) for i in output_items],
        )

    async def cancel(self, ctx: RequestContext, execution_id: UUID) -> ExecutionRead:
        execution, project, role = await self._service.get(
            execution_id=execution_id, user_id=ctx.user_id
        )
        require(role, Permission.WORKFLOW_EXECUTE, scopes=ctx.scopes)
        execution = await self._service.cancel(
            execution=execution,
            organization_id=project.organization_id,
            actor_id=ctx.user_id,
        )
        return await self._to_read(execution)

    async def retry(
        self, ctx: RequestContext, execution_id: UUID, payload: RetryRequest
    ) -> ExecutionRead:
        execution, project, role = await self._service.get(
            execution_id=execution_id, user_id=ctx.user_id
        )
        require(role, Permission.WORKFLOW_EXECUTE, scopes=ctx.scopes)
        new_execution = await self._service.retry(
            execution=execution,
            organization_id=project.organization_id,
            actor_id=ctx.user_id,
            from_failed_node=payload.from_failed_node,
        )
        return await self._to_read(new_execution)

    async def delete(self, ctx: RequestContext, execution_id: UUID) -> None:
        execution, project, role = await self._service.get(
            execution_id=execution_id, user_id=ctx.user_id
        )
        require(role, Permission.WORKFLOW_EXECUTE, scopes=ctx.scopes)
        await self._service.delete(
            execution=execution,
            organization_id=project.organization_id,
            actor_id=ctx.user_id,
        )

    async def bulk_delete(
        self, ctx: RequestContext, project_id: UUID, payload: BulkDeleteRequest
    ) -> BulkDeleteResponse:
        role = await self._service.get_role_for_project(
            project_id=project_id, user_id=ctx.user_id
        )
        require(role, Permission.WORKFLOW_EXECUTE, scopes=ctx.scopes)
        deleted = await self._service.bulk_delete(
            project_id=project_id,
            user_id=ctx.user_id,
            workflow_id=payload.filter.workflow_id,
            status=payload.filter.status,
        )
        return BulkDeleteResponse(deleted=deleted)

    async def stats(
        self, ctx: RequestContext, project_id: UUID
    ) -> ExecutionStatsResponse:
        role = await self._service.get_role_for_project(
            project_id=project_id, user_id=ctx.user_id
        )
        require(role, Permission.EXECUTION_READ, scopes=ctx.scopes)
        by_status = await self._service.stats(
            project_id=project_id, user_id=ctx.user_id
        )
        total = sum(by_status.values())
        return ExecutionStatsResponse(by_status=by_status, total=total)

    async def stream(
        self, ctx: RequestContext, execution_id: UUID
    ) -> AsyncIterator[bytes]:
        # Authorize before subscribing -- an execution the caller can't see
        # must not leak even its existence via the stream.
        _execution, _project, role = await self._service.get(
            execution_id=execution_id, user_id=ctx.user_id
        )
        require(role, Permission.EXECUTION_READ, scopes=ctx.scopes)

        pubsub = self._redis.pubsub()
        await pubsub.subscribe(channel_name(execution_id))
        try:
            while True:
                message = await pubsub.get_message(
                    ignore_subscribe_messages=True, timeout=SSE_POLL_TIMEOUT_SECONDS
                )
                if message is None:
                    yield b": keep-alive\n\n"
                    continue
                payload = json.loads(message["data"])
                event_name = payload.get("event", "message")
                yield f"event: {event_name}\ndata: {json.dumps(payload)}\n\n".encode()
                if event_name == "execution.finished":
                    return
        finally:
            await pubsub.unsubscribe(channel_name(execution_id))
            # redis-py's PubSub.aclose has no type stub.
            await pubsub.aclose()  # type: ignore[no-untyped-call]
