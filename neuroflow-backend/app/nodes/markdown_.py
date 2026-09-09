"""Markdown -- converts between Markdown and HTML. See docs/13-node-
catalog-and-sdk.md #13.5's "XML/HTML/Markdown" row (this node covers
Markdown; see `app/nodes/html_extract.py` for HTML). Named `markdown_.py`
so it doesn't shadow the `markdown` package it imports."""

from __future__ import annotations

import markdown as markdown_lib
from markdownify import markdownify

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import (
    Item,
    NodeProperty,
    NodeTypeDescriptor,
    PortSpec,
    PropertyOption,
)


class MarkdownNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.markdown",
        version=1,
        name="Markdown",
        group="data",
        category="Core",
        description="Converts a field between Markdown and HTML.",
        icon="file-text",
        color="cat-data",
        aliases=["md"],
        subtitle="={{ $parameter.direction }}",
        inputs=[PortSpec(type="main")],
        outputs=[PortSpec(type="main")],
        idempotent=True,
        properties=[
            NodeProperty(
                name="direction",
                display_name="Direction",
                type="options",
                default="markdownToHtml",
                description="Which way to convert.",
                options=[
                    PropertyOption(label="Markdown to HTML", value="markdownToHtml"),
                    PropertyOption(label="HTML to Markdown", value="htmlToMarkdown"),
                ],
            ),
            NodeProperty(
                name="sourceField",
                display_name="Source Field",
                type="string",
                required=True,
                description="Field on each input item holding the source text.",
            ),
            NodeProperty(
                name="destinationField",
                display_name="Destination Field",
                type="string",
                default="converted",
                required=True,
                description="Field on the output item to write the converted text to.",
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        params = ctx.params
        direction = params.get("direction", "markdownToHtml")
        source_field = params.get("sourceField", "")
        destination = params.get("destinationField", "converted")

        results: list[Item] = []
        for item in ctx.input_items:
            text = str(item.json_.get(source_field, ""))
            value = (
                markdown_lib.markdown(text)
                if direction == "markdownToHtml"
                else markdownify(text)
            )
            results.append(Item(json={**item.json_, destination: value}))
        return {"main": [results]}
