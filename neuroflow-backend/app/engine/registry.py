"""Builds the real, executable node registry once at worker boot. See this
phase's plan finding #5: shares the discovery walk with
`scripts/build_node_catalog.py` rather than duplicating it, but is a
separate call site since the two run at different times for different
purposes (build-time catalog snapshot vs. runtime execution registry).
"""

from __future__ import annotations

from functools import lru_cache

from app.modules.nodes.registry import NodeRegistry
from app.nodes._discovery import discover_and_register


@lru_cache(maxsize=1)
def build_runtime_registry() -> NodeRegistry:
    return discover_and_register(NodeRegistry())
