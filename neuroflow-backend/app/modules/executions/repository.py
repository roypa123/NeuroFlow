"""SQL access for executions and their node runs/payloads. No business
rules -- see docs/08-backend-architecture.md #8.1's test for this layer."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, literal, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.executions.models import Execution, ExecutionData, NodeExecution


class ExecutionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        workflow_id: UUID,
        workflow_version_id: UUID,
        project_id: UUID,
        mode: str,
        trigger_data: dict[str, Any] | None,
        created_by: UUID | None,
        created_at: datetime,
        retry_of_execution_id: UUID | None = None,
    ) -> Execution:
        execution = Execution(
            workflow_id=workflow_id,
            workflow_version_id=workflow_version_id,
            project_id=project_id,
            status="queued",
            mode=mode,
            trigger_data=trigger_data,
            created_by=created_by,
            created_at=created_at,
            retry_of_execution_id=retry_of_execution_id,
        )
        self._session.add(execution)
        await self._session.flush()
        return execution

    async def get_by_id(self, execution_id: UUID) -> Execution | None:
        stmt = select(Execution).where(Execution.id == execution_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_with_filters(
        self,
        *,
        project_id: UUID | None,
        workflow_id: UUID | None,
        status: str | None,
        mode: str | None,
        limit: int,
        cursor: tuple[datetime, UUID] | None,
    ) -> list[Execution]:
        stmt = select(Execution)
        if project_id is not None:
            stmt = stmt.where(Execution.project_id == project_id)
        if workflow_id is not None:
            stmt = stmt.where(Execution.workflow_id == workflow_id)
        if status is not None:
            stmt = stmt.where(Execution.status == status)
        if mode is not None:
            stmt = stmt.where(Execution.mode == mode)
        if cursor is not None:
            cursor_created_at, cursor_id = cursor
            stmt = stmt.where(
                tuple_(Execution.created_at, Execution.id)
                < tuple_(literal(cursor_created_at), literal(cursor_id))
            )
        stmt = stmt.order_by(Execution.created_at.desc(), Execution.id.desc()).limit(
            limit + 1
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def stats_by_status(self, *, project_id: UUID) -> dict[str, int]:
        stmt = (
            select(Execution.status, func.count())
            .where(Execution.project_id == project_id)
            .group_by(Execution.status)
        )
        result = await self._session.execute(stmt)
        return dict(result.tuples().all())

    async def list_stale_queued(self, *, older_than: datetime) -> list[Execution]:
        stmt = select(Execution).where(
            Execution.status == "queued", Execution.created_at < older_than
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_stuck_running(self, *, started_before: datetime) -> list[Execution]:
        stmt = select(Execution).where(
            Execution.status == "running", Execution.started_at < started_before
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_running(self, execution: Execution, *, at: datetime) -> None:
        execution.status = "running"
        execution.started_at = at
        await self._session.flush()

    async def finish(
        self,
        execution: Execution,
        *,
        status: str,
        at: datetime,
        error: dict[str, Any] | None = None,
    ) -> None:
        execution.status = status
        execution.finished_at = at
        execution.error = error
        if execution.started_at is not None:
            elapsed = (at - execution.started_at).total_seconds()
            execution.duration_ms = int(elapsed * 1000)
        await self._session.flush()

    async def delete(self, execution: Execution) -> None:
        await self._session.delete(execution)
        await self._session.flush()

    async def bulk_delete(
        self, *, project_id: UUID, workflow_id: UUID | None, status: str | None
    ) -> int:
        rows = await self.list_with_filters(
            project_id=project_id,
            workflow_id=workflow_id,
            status=status,
            mode=None,
            limit=10_000,
            cursor=None,
        )
        for row in rows[:10_000]:
            await self._session.delete(row)
        await self._session.flush()
        return len(rows[:10_000])


class NodeExecutionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        *,
        execution_id: UUID,
        node_id: str,
        node_name: str,
        node_type: str,
        run_index: int,
        started_at: datetime,
    ) -> NodeExecution:
        row = NodeExecution(
            execution_id=execution_id,
            node_id=node_id,
            node_name=node_name,
            node_type=node_type,
            status="running",
            run_index=run_index,
            started_at=started_at,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def finish(
        self,
        row: NodeExecution,
        *,
        status: str,
        at: datetime,
        items_in: int | None = None,
        items_out: int | None = None,
        error: dict[str, Any] | None = None,
        input_data_id: UUID | None = None,
        output_data_id: UUID | None = None,
    ) -> None:
        row.status = status
        row.finished_at = at
        row.items_in = items_in
        row.items_out = items_out
        row.error = error
        row.input_data_id = input_data_id
        row.output_data_id = output_data_id
        row.duration_ms = int((at - row.started_at).total_seconds() * 1000)
        await self._session.flush()

    async def list_for_execution(self, execution_id: UUID) -> list[NodeExecution]:
        stmt = (
            select(NodeExecution)
            .where(NodeExecution.execution_id == execution_id)
            .order_by(NodeExecution.started_at)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_node_id(
        self, execution_id: UUID, node_id: str, *, run_index: int = 0
    ) -> NodeExecution | None:
        stmt = select(NodeExecution).where(
            NodeExecution.execution_id == execution_id,
            NodeExecution.node_id == node_id,
            NodeExecution.run_index == run_index,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def copy_successful(
        self,
        *,
        from_execution_id: UUID,
        to_execution_id: UUID,
        up_to_node_id: str | None,
    ) -> list[NodeExecution]:
        """Used by retry(from_failed_node=True): copies every successful
        node run from the original execution into the new one, pointing at
        the *same* `execution_data` rows (immutable, safe to share) -- see
        docs/09-domain-modules.md #9.9."""
        source_rows = await self.list_for_execution(from_execution_id)
        copied: list[NodeExecution] = []
        for row in source_rows:
            if row.node_id == up_to_node_id:
                break
            if row.status != "success":
                continue
            new_row = NodeExecution(
                execution_id=to_execution_id,
                node_id=row.node_id,
                node_name=row.node_name,
                node_type=row.node_type,
                status=row.status,
                run_index=row.run_index,
                items_in=row.items_in,
                items_out=row.items_out,
                input_data_id=row.input_data_id,
                output_data_id=row.output_data_id,
                error=row.error,
                started_at=row.started_at,
                finished_at=row.finished_at,
                duration_ms=row.duration_ms,
            )
            self._session.add(new_row)
            copied.append(new_row)
        if copied:
            await self._session.flush()
        return copied


class ExecutionDataRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_inline(
        self,
        *,
        execution_id: UUID,
        data: Any,
        item_count: int,
        size_bytes: int,
        truncated: bool = False,
    ) -> ExecutionData:
        row = ExecutionData(
            execution_id=execution_id,
            kind="inline",
            data=data,
            size_bytes=size_bytes,
            item_count=item_count,
            truncated=truncated,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def create_object_reference(
        self,
        *,
        execution_id: UUID,
        object_key: str,
        item_count: int,
        size_bytes: int,
        truncated: bool = False,
    ) -> ExecutionData:
        row = ExecutionData(
            execution_id=execution_id,
            kind="object",
            object_key=object_key,
            size_bytes=size_bytes,
            item_count=item_count,
            truncated=truncated,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, data_id: UUID) -> ExecutionData | None:
        stmt = select(ExecutionData).where(ExecutionData.id == data_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
