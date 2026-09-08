"""Shared node-discovery walk. Used by `scripts/build_node_catalog.py`
(build-time catalog generation, run by hand/CI) and by
`app/engine/registry.py` (real registry built once at worker boot) -- see
this phase's plan for why the walk itself is factored out rather than
duplicated between the two.

Lives under `app.nodes`, so `app.api`/`app.main` never import it either,
per the import-linter contract in `pyproject.toml`.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from pathlib import Path

from app.modules.nodes.base import BaseNode
from app.modules.nodes.registry import NodeRegistry

_PACKAGE_NAME = __name__.rsplit(".", 1)[0]  # "app.nodes"
_PACKAGE_DIR = Path(__file__).resolve().parent


def discover_and_register(registry: NodeRegistry) -> NodeRegistry:
    for module_info in pkgutil.iter_modules([str(_PACKAGE_DIR)]):
        if module_info.name.startswith("_"):
            continue
        module = importlib.import_module(f"{_PACKAGE_NAME}.{module_info.name}")
        for _name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, BaseNode)
                and obj is not BaseNode
                and obj.__module__ == module.__name__
            ):
                registry.register(obj)
    return registry
