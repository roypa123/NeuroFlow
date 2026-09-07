"""Node-type routes: declarations only. See docs/11-api-design.md #11.9."""
from __future__ import annotations

from fastapi import APIRouter

from app.modules.nodes.dependencies import NodeTypeControllerDep
from app.modules.nodes.descriptors import NodeTypeDescriptor

router = APIRouter(prefix="/node-types", tags=["node-types"])


@router.get("", response_model=list[NodeTypeDescriptor])
async def list_node_types(
    controller: NodeTypeControllerDep,
) -> list[NodeTypeDescriptor]:
    return await controller.list_all()


@router.get("/{key}", response_model=NodeTypeDescriptor)
async def get_node_type(
    key: str, controller: NodeTypeControllerDep
) -> NodeTypeDescriptor:
    return await controller.get(key)
