"""Serves the node type catalog from the generated snapshot file -- never
by importing `app/nodes/` at runtime. See the module-boundary note in
docs/09-domain-modules.md #9.7 and the architectural decision recorded in
this phase's plan: the registry's "boot" happens in
`scripts/build_node_catalog.py`, decoupled from the API process's boot.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.modules.nodes.descriptors import NodeTypeDescriptor
from app.modules.nodes.exceptions import NodeTypeNotFoundError

CATALOG_PATH = Path(__file__).parent / "catalog.generated.json"


@lru_cache(maxsize=1)
def _load_catalog() -> dict[str, NodeTypeDescriptor]:
    raw = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    descriptors = [NodeTypeDescriptor.model_validate(entry) for entry in raw]
    return {d.key: d for d in descriptors}


class NodeTypeService:
    def list_all(self) -> list[NodeTypeDescriptor]:
        return list(_load_catalog().values())

    def get(self, key: str) -> NodeTypeDescriptor:
        catalog = _load_catalog()
        if key not in catalog:
            raise NodeTypeNotFoundError(f"Unknown node type: {key}")
        return catalog[key]
