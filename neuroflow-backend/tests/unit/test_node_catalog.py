"""The generated node catalog must match what the real implementations in
app/nodes/ would produce -- see scripts/build_node_catalog.py and this
phase's plan for why the catalog is a checked-in artifact rather than
built at API-process startup (app.api/app.main must never import
app.nodes -- docs/03-system-architecture.md #3.9).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from build_node_catalog import build_registry, generate_catalog_json  # noqa: E402

from app.modules.nodes.base import (  # noqa: E402
    BaseNode,
    NodeExecutionContext,
    NodeOutput,
)
from app.modules.nodes.descriptors import NodeTypeDescriptor  # noqa: E402
from app.modules.nodes.registry import (  # noqa: E402
    DuplicateNodeKeyError,
    NodeRegistry,
)
from app.modules.nodes.service import CATALOG_PATH  # noqa: E402


def test_generated_catalog_is_up_to_date() -> None:
    registry = build_registry()
    fresh = generate_catalog_json(registry)
    checked_in = CATALOG_PATH.read_text(encoding="utf-8")
    assert fresh == checked_in, (
        "app/modules/nodes/catalog.generated.json is stale -- run "
        "`python scripts/build_node_catalog.py` and commit the result."
    )


class _DummyNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="test.dummy",
        name="Dummy",
        group="action",
        category="Test",
        description="d",
        icon="circle",
        color="cat-core",
    )

    async def execute(self, _ctx: NodeExecutionContext) -> NodeOutput:
        return {"main": [[]]}


def test_registry_rejects_duplicate_keys() -> None:
    registry = NodeRegistry()
    registry.register(_DummyNode)
    with pytest.raises(DuplicateNodeKeyError):
        registry.register(_DummyNode)
