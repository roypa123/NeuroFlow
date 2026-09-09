"""Generates one Markdown reference page per node type under docs/nodes/,
from the real descriptors in app/nodes/ -- the "Node documentation
generated from descriptors" deliverable named by docs/19-roadmap.md's
Phase 6 entry.

Like scripts/build_node_catalog.py, this is the one script allowed to
import both app.modules.nodes and app.nodes; the API server never does
(docs/03-system-architecture.md #3.9). Run it whenever a node is added,
removed, or its descriptor changes:

    python scripts/generate_node_docs.py

tests/unit/test_node_docs.py regenerates the docs into a temp directory
and fails if they don't match the checked-in docs/nodes/ tree, so a
changed node can't ship with stale documentation.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from build_node_catalog import build_registry  # noqa: E402

from app.modules.nodes.descriptors import (  # noqa: E402
    NodeProperty,
    NodeTypeDescriptor,
)
from app.modules.nodes.registry import NodeRegistry  # noqa: E402

DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "nodes"


def _property_row(prop: NodeProperty) -> str:
    required = "Yes" if prop.required else "No"
    description = prop.description or ""
    return (
        f"| `{prop.name}` | {prop.display_name} | {prop.type} | "
        f"{required} | {description} |"
    )


def render_node_doc(descriptor: NodeTypeDescriptor) -> str:
    lines = [
        f"# {descriptor.name}",
        "",
        f"`{descriptor.key}` (v{descriptor.version}) -- "
        f"{descriptor.group}/{descriptor.category}",
        "",
        descriptor.description,
        "",
    ]

    if descriptor.aliases:
        lines += [f"**Aliases:** {', '.join(descriptor.aliases)}", ""]

    lines += ["## Ports", ""]
    inputs = ", ".join(p.label or "main" for p in descriptor.inputs) or "none"
    outputs = ", ".join(p.label or "main" for p in descriptor.outputs) or "none"
    lines += [f"- **Inputs:** {inputs}", f"- **Outputs:** {outputs}", ""]

    if descriptor.credentials:
        cred_types = ", ".join(
            f"`{t}`" for req in descriptor.credentials for t in req.types
        )
        lines += ["## Credentials", "", f"Accepts: {cred_types}", ""]

    if descriptor.properties:
        lines += [
            "## Properties",
            "",
            "| Name | Display Name | Type | Required | Description |",
            "| --- | --- | --- | --- | --- |",
        ]
        lines += [_property_row(p) for p in descriptor.properties]
        lines += [""]

    return "\n".join(lines)


def generate_all(registry: NodeRegistry) -> dict[str, str]:
    """Returns {filename: content} for every registered node, sorted by
    key so output ordering is stable across runs."""
    descriptors = sorted(registry.all_descriptors(), key=lambda d: d.key)
    return {f"{d.key}.md": render_node_doc(d) for d in descriptors}


def main() -> None:
    registry = build_registry()
    docs = generate_all(registry)

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    existing = {p.name for p in DOCS_DIR.glob("*.md")}
    for filename, content in docs.items():
        (DOCS_DIR / filename).write_text(content, encoding="utf-8")
    # Remove docs for nodes that no longer exist (e.g. a renamed key).
    for stale in existing - set(docs):
        (DOCS_DIR / stale).unlink()

    print(f"Wrote {len(docs)} node doc(s) to {DOCS_DIR}")


if __name__ == "__main__":
    main()
