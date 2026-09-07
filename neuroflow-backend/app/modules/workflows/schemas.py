"""Pydantic schemas for workflows. See docs/11-api-design.md #11.7.

The graph shape (`WorkflowGraph`/`GraphNode`/`GraphEdge`) matches what
`@xyflow/react` produces on the frontend so the canvas store can send its
state straight through -- see docs/06-canvas-and-editor.md #6.3.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.schema import CamelModel


class Position(CamelModel):
    x: float
    y: float


class GraphNode(CamelModel):
    id: str
    type: str
    type_version: int = 1
    name: str | None = None
    position: Position
    parameters: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(CamelModel):
    id: str
    source: str
    target: str
    source_handle: str | None = None
    target_handle: str | None = None


class Viewport(CamelModel):
    x: float = 0
    y: float = 0
    zoom: float = 1


class WorkflowGraph(CamelModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
    viewport: Viewport = Field(default_factory=Viewport)


class WorkflowSettings(CamelModel):
    timezone: str = "UTC"
    error_workflow_id: UUID | None = None
    timeout_seconds: int = 3600
    max_concurrency: int = 1


class WorkflowSummary(CamelModel):
    id: UUID
    project_id: UUID
    name: str
    description: str | None
    kind: str
    is_active: bool
    version: int
    updated_at: datetime


class WorkflowRead(CamelModel):
    id: UUID
    project_id: UUID
    name: str
    description: str | None
    kind: str
    is_active: bool
    active_version_id: UUID | None
    version: int
    settings: WorkflowSettings
    graph: WorkflowGraph
    created_at: datetime
    updated_at: datetime


class WorkflowCreate(CamelModel):
    project_id: UUID
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class WorkflowUpdate(CamelModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    settings: WorkflowSettings | None = None
    graph: WorkflowGraph | None = None
    base_version_id: UUID | None = None
    note: str | None = None


class WorkflowDuplicateRequest(CamelModel):
    name: str | None = None


class WorkflowImportRequest(CamelModel):
    project_id: UUID
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    settings: WorkflowSettings = Field(default_factory=WorkflowSettings)
    graph: WorkflowGraph


class WorkflowExport(CamelModel):
    name: str
    description: str | None
    settings: WorkflowSettings
    graph: WorkflowGraph


class WorkflowValidateRequest(CamelModel):
    graph: WorkflowGraph


class WorkflowValidateResponse(CamelModel):
    valid: bool
    errors: list[str] = Field(default_factory=list)


class WorkflowVersionRead(CamelModel):
    id: UUID
    version: int
    checksum: str
    note: str | None
    created_by: UUID | None
    created_at: datetime


class WorkflowVersionDetail(WorkflowVersionRead):
    graph: WorkflowGraph
