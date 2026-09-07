"""Node-type orchestration. Read-only, no auth beyond being logged in --
the catalog carries no tenant data. See docs/08-backend-architecture.md
#8.1."""
from __future__ import annotations

from app.modules.nodes.descriptors import NodeTypeDescriptor
from app.modules.nodes.service import NodeTypeService


class NodeTypeController:
    def __init__(self, service: NodeTypeService) -> None:
        self._service = service

    async def list_all(self) -> list[NodeTypeDescriptor]:
        return self._service.list_all()

    async def get(self, key: str) -> NodeTypeDescriptor:
        return self._service.get(key)
