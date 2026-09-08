"""Pydantic schemas for executions. See docs/11-api-design.md #11.8."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import Field

from app.core.schema import CamelModel
from app.modules.workflows.schemas import WorkflowGraph

ExecutionStatus = Literal[
    "queued", "running", "success", "error", "canceled", "waiting"
]
ExecutionMode = Literal["manual", "trigger", "webhook", "schedule", "retry", "sub"]
NodeExecutionStatus = Literal["running", "success", "error", "skipped"]


class ExecutionSummary(CamelModel):
    id: UUID
    workflow_id: UUID
    workflow_version_id: UUID
    project_id: UUID
    status: ExecutionStatus
    mode: ExecutionMode
    started_at: datetime | None
    finished_at: datetime | None
    duration_ms: int | None
    created_at: datetime


class NodeExecutionRead(CamelModel):
    id: UUID
    node_id: str
    node_name: str
    node_type: str
    status: NodeExecutionStatus
    run_index: int
    items_in: int | None
    items_out: int | None
    error: dict[str, Any] | None
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None


class ExecutionRead(ExecutionSummary):
    trigger_data: dict[str, Any] | None
    error: dict[str, Any] | None
    parent_execution_id: UUID | None
    retry_of_execution_id: UUID | None
    graph: WorkflowGraph
    nodes: list[NodeExecutionRead] = Field(default_factory=list)


class ItemRead(CamelModel):
    json_: dict[str, Any] = Field(default_factory=dict, alias="json")

    model_config = {"populate_by_name": True}


class NodeDataRead(CamelModel):
    input_items: list[ItemRead] = Field(default_factory=list)
    output_items: list[ItemRead] = Field(default_factory=list)
    truncated: bool = False


class RetryRequest(CamelModel):
    from_failed_node: bool = True


class BulkDeleteFilter(CamelModel):
    workflow_id: UUID | None = None
    status: ExecutionStatus | None = None


class BulkDeleteRequest(CamelModel):
    filter: BulkDeleteFilter


class BulkDeleteResponse(CamelModel):
    deleted: int


class ExecutionStatsResponse(CamelModel):
    by_status: dict[str, int]
    total: int
