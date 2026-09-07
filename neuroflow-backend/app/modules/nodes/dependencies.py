"""DI wiring for the nodes module. No session dependency -- the catalog is
a static, process-wide resource. See docs/08-backend-architecture.md #8.4."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from app.modules.nodes.controller import NodeTypeController
from app.modules.nodes.service import NodeTypeService


def get_node_type_service() -> NodeTypeService:
    return NodeTypeService()


NodeTypeServiceDep = Annotated[NodeTypeService, Depends(get_node_type_service)]


def get_node_type_controller(service: NodeTypeServiceDep) -> NodeTypeController:
    return NodeTypeController(service)


NodeTypeControllerDep = Annotated[NodeTypeController, Depends(get_node_type_controller)]
