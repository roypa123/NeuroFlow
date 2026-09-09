"""Date & Time -- parse/format, add/subtract, and diff timestamps. See
docs/13-node-catalog-and-sdk.md #13.5. Stdlib `datetime` only (no
`dateutil`/`pendulum` dependency); input values must already be ISO-8601
strings or epoch seconds, which covers every timestamp this app itself
ever produces (`created_at`, `finished_at`, ...)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import (
    DisplayOptions,
    Item,
    NodeProperty,
    NodeTypeDescriptor,
    PortSpec,
    PropertyOption,
)

_UNIT_SECONDS = {"seconds": 1, "minutes": 60, "hours": 3600, "days": 86400}


def _parse(value: Any) -> datetime:
    if isinstance(value, int | float):
        return datetime.fromtimestamp(value, tz=UTC)
    text = str(value)
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


class DateTimeNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.dateTime",
        version=1,
        name="Date & Time",
        group="data",
        category="Core",
        description="Formats, shifts, or diffs date/time values.",
        icon="calendar-clock",
        color="cat-data",
        aliases=["date", "time"],
        subtitle="={{ $parameter.operation }}",
        inputs=[PortSpec(type="main")],
        outputs=[PortSpec(type="main")],
        idempotent=True,
        properties=[
            NodeProperty(
                name="operation",
                display_name="Operation",
                type="options",
                default="format",
                description="Which date/time transformation to apply.",
                options=[
                    PropertyOption(label="Format", value="format"),
                    PropertyOption(label="Add / Subtract", value="addSubtract"),
                    PropertyOption(label="Difference", value="difference"),
                    PropertyOption(label="Now", value="now"),
                ],
            ),
            NodeProperty(
                name="inputField",
                display_name="Input Field",
                type="string",
                description="Field holding an ISO-8601 string or epoch seconds.",
                display_options=DisplayOptions(
                    show={"operation": ["format", "addSubtract", "difference"]}
                ),
            ),
            NodeProperty(
                name="compareField",
                display_name="Compare Field",
                type="string",
                description="Field holding the timestamp to diff against.",
                display_options=DisplayOptions(show={"operation": ["difference"]}),
            ),
            NodeProperty(
                name="amount",
                display_name="Amount",
                type="number",
                default=0,
                description="Negative to subtract.",
                display_options=DisplayOptions(show={"operation": ["addSubtract"]}),
            ),
            NodeProperty(
                name="unit",
                display_name="Unit",
                type="options",
                default="days",
                description="Unit for Amount (Add/Subtract) or the result "
                "(Difference).",
                options=[
                    PropertyOption(label=u.title(), value=u) for u in _UNIT_SECONDS
                ],
                display_options=DisplayOptions(
                    show={"operation": ["addSubtract", "difference"]}
                ),
            ),
            NodeProperty(
                name="format",
                display_name="Output Format (strftime)",
                type="string",
                default="%Y-%m-%dT%H:%M:%S%z",
                description="Python strftime format string for the output.",
                display_options=DisplayOptions(show={"operation": ["format"]}),
            ),
            NodeProperty(
                name="destinationField",
                display_name="Destination Field",
                type="string",
                default="result",
                required=True,
                description="Field on the output item to write the result to.",
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        params = ctx.params
        operation = params.get("operation", "format")
        destination = params.get("destinationField", "result")
        input_field = params.get("inputField", "")
        unit_seconds = _UNIT_SECONDS.get(params.get("unit", "days"), 86400)

        results: list[Item] = []
        source_items = ctx.input_items or [Item(json={})]
        for item in source_items:
            value: Any
            if operation == "now":
                value = datetime.now(UTC).isoformat()
            elif operation == "format":
                value = _parse(item.json_.get(input_field)).strftime(
                    params.get("format", "%Y-%m-%dT%H:%M:%S%z")
                )
            elif operation == "addSubtract":
                delta = timedelta(seconds=float(params.get("amount", 0)) * unit_seconds)
                value = (_parse(item.json_.get(input_field)) + delta).isoformat()
            else:  # difference
                start = _parse(item.json_.get(input_field))
                end = _parse(item.json_.get(params.get("compareField", "")))
                value = (end - start).total_seconds() / unit_seconds
            results.append(Item(json={**item.json_, destination: value}))
        return {"main": [results]}
