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
ExecutionMode = Literal[
    "manual", "trigger", "webhook", "schedule", "retry", "sub", "error"
]
NodeExecutionStatus = Literal["running", "success", "error", "skipped", "waiting"]


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
    # Only set while status == "waiting". Exposed to anyone who can already
    # view this specific execution (EXECUTION_READ) -- it is a capability
    # scoped to this one execution, not an account-wide secret, and lets
    # the editor offer a "Resume now" action for a workflow under test
    # rather than requiring a real external approval link every time. See
    # docs/12-execution-engine.md #12.5.
    resume_token: str | None = None


class ItemRead(CamelModel):
    json_: dict[str, Any] = Field(default_factory=dict, alias="json")

    model_config = {"populate_by_name": True}


class NodeDataRead(CamelModel):
    input_items: list[ItemRead] = Field(default_factory=list)
    output_items: list[ItemRead] = Field(default_factory=list)
    truncated: bool = False


class RetryRequest(CamelModel):
    from_failed_node: bool = True


class ResumeRequest(CamelModel):
    # The token itself is the authorization for this endpoint -- an
    # approval link recipient need not be a NeuroFlow member. See
    # docs/12-execution-engine.md #12.5.
    resume_token: str
    payload: dict[str, Any] | None = None


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
