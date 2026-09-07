"""Regenerates app/modules/nodes/catalog.generated.json from the real node
implementations in app/nodes/.

This script -- and only this script -- is allowed to import both
app.modules.nodes (the registry) and app.nodes (the node implementations).
The API server never does; see docs/03-system-architecture.md #3.9 and the
pyproject.toml import-linter contract. Run it whenever a node is added,
removed, or its descriptor changes:

    python scripts/build_node_catalog.py

tests/unit/test_node_catalog.py regenerates the catalog in-memory and
fails if it doesn't match the checked-in file, so a changed node can't
ship without this being re-run.
"""
from __future__ import annotations

import importlib
import inspect
import json
import pkgutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.nodes as nodes_package  # noqa: E402
from app.modules.nodes.base import BaseNode  # noqa: E402
from app.modules.nodes.registry import NodeRegistry  # noqa: E402


def build_registry() -> NodeRegistry:
    registry = NodeRegistry()
    for module_info in pkgutil.iter_modules(nodes_package.__path__):
        module = importlib.import_module(f"{nodes_package.__name__}.{module_info.name}")
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, BaseNode)
                and obj is not BaseNode
                and obj.__module__ == module.__name__
            ):
                registry.register(obj)
    return registry


def generate_catalog_json(registry: NodeRegistry) -> str:
    descriptors = sorted(registry.all_descriptors(), key=lambda d: d.key)
    payload = [d.model_dump(mode="json", by_alias=True) for d in descriptors]
    return json.dumps(payload, indent=2) + "\n"


def main() -> None:
    registry = build_registry()
    output = generate_catalog_json(registry)
    catalog_path = (
        Path(__file__).resolve().parent.parent
        / "app/modules/nodes/catalog.generated.json"
    )
    catalog_path.write_text(output, encoding="utf-8")
    print(f"Wrote {len(registry.all_descriptors())} node type(s) to {catalog_path}")


if __name__ == "__main__":
    main()
