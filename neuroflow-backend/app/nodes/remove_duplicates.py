"""Remove Duplicates -- keeps only the first occurrence of each distinct
value. See docs/13-node-catalog-and-sdk.md #13.5. An empty `compareField`
compares each item's whole JSON body instead of a single field."""

from __future__ import annotations

import json
from typing import Any

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import NodeProperty, NodeTypeDescriptor, PortSpec


def _fingerprint(value: Any) -> str:
    return json.dumps(value, sort_keys=True, default=str)


class RemoveDuplicatesNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.removeDuplicates",
        version=1,
        name="Remove Duplicates",
        group="data",
        category="Core",
        description="Keeps only the first item for each distinct value.",
        icon="copy-minus",
        color="cat-data",
        aliases=["dedupe", "distinct", "unique"],
        subtitle="={{ $parameter.compareField }}",
        inputs=[PortSpec(type="main")],
        outputs=[PortSpec(type="main")],
        idempotent=True,
        properties=[
            NodeProperty(
                name="compareField",
                display_name="Compare Field",
                type="string",
                description="Field to compare items by. Leave empty to compare "
                "each item's entire JSON body.",
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        field = ctx.params.get("compareField", "")
        seen: set[str] = set()
        kept = []
        for item in ctx.input_items:
            value = item.json_.get(field) if field else item.json_
            key = _fingerprint(value)
            if key in seen:
                continue
            seen.add(key)
            kept.append(item)
        return {"main": [kept]}
