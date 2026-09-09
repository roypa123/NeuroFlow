"""Registry conformance -- "one test, whole catalog" (docs/17-testing-
strategy.md #17.5, named as a Phase 6 deliverable by docs/19-roadmap.md).
Runs against every node currently registered, present and future, with no
per-node addition to this file required.

**Scope note on property descriptions:** every property on the 18 node
types added this phase has a `description` (verified while writing them),
matching the §13.8 authoring checklist. Nodes shipped before this phase
(Set, IF, Code, HTTP Request, Wait, ...) predate that checklist item and
were not retrofitted here -- doing so would mean editing ~9 files outside
this phase's own additions for a purely cosmetic gap. This test therefore
does not assert every property has a description; it checks the
structural properties that are already true of the whole catalog today
(unique keys, valid subtitle references, resolvable icons and
`load_options_method`s) and leaves the description backfill as a named,
separate cleanup rather than silently red-lining pre-existing nodes.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from app.engine.registry import build_runtime_registry
from app.modules.nodes.descriptors import NodeTypeDescriptor

_PARAM_REF = re.compile(r"\$parameter\.(\w+)")
_ICON_NAMES: frozenset[str] = frozenset(
    json.loads(
        (
            Path(__file__).resolve().parents[2] / "fixtures" / "lucide_icon_names.json"
        ).read_text()
    )
)


def _to_pascal_case(kebab: str) -> str:
    """Mirrors `icon-lookup.ts`'s `toPascalCase` exactly, so this test
    fails on precisely the icon names the frontend would silently fall
    back to a generic icon for."""
    return "".join(part[:1].upper() + part[1:] for part in kebab.split("-") if part)


def _descriptors() -> list[NodeTypeDescriptor]:
    return build_runtime_registry().all_descriptors()


def test_no_duplicate_key_version_pairs() -> None:
    keys = [(d.key, d.version) for d in _descriptors()]
    assert len(keys) == len(set(keys))


def test_every_key_is_namespaced() -> None:
    for d in _descriptors():
        assert d.key.startswith("neuroflow."), d.key


def test_subtitle_only_references_declared_parameters() -> None:
    for d in _descriptors():
        if not d.subtitle:
            continue
        declared = {p.name for p in d.properties}
        for referenced in _PARAM_REF.findall(d.subtitle):
            assert referenced in declared, (
                f"{d.key}'s subtitle references undeclared parameter '{referenced}'"
            )


def test_load_options_method_resolves_to_a_real_method() -> None:
    registry = build_runtime_registry()
    for d in _descriptors():
        node_cls = registry.get(d.key, d.version)
        for prop in d.properties:
            if prop.load_options_method is None:
                continue
            assert hasattr(node_cls, prop.load_options_method), (
                f"{d.key}.{prop.name} references a load_options_method "
                f"'{prop.load_options_method}' that doesn't exist on {node_cls}"
            )


def test_icon_resolves_to_a_real_lucide_icon() -> None:
    for d in _descriptors():
        pascal = _to_pascal_case(d.icon)
        assert pascal in _ICON_NAMES, f"{d.key}'s icon '{d.icon}' doesn't resolve"


def test_input_and_output_ports_have_unique_labels_when_there_are_multiple() -> None:
    for d in _descriptors():
        for ports in (d.inputs, d.outputs):
            if len(ports) <= 1:
                continue
            labels = [p.label for p in ports]
            assert len(labels) == len(set(labels)), (
                f"{d.key} has duplicate port labels: {labels}"
            )
