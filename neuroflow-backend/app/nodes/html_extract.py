"""HTML Extract -- CSS-selector extraction from an HTML string field. See
docs/13-node-catalog-and-sdk.md #13.5's "XML/HTML/Markdown" row (this
node covers HTML; see `app/nodes/markdown_.py` for the other new format
this phase covers; a dedicated XML node is explicitly deferred, see this
phase's plan). Uses `beautifulsoup4` with the stdlib `html.parser`
backend -- no `lxml` dependency needed.
"""

from __future__ import annotations

from bs4 import BeautifulSoup

from app.modules.nodes.base import BaseNode, NodeExecutionContext, NodeOutput
from app.modules.nodes.descriptors import (
    Item,
    NodeProperty,
    NodeTypeDescriptor,
    PortSpec,
)


class HtmlExtractNode(BaseNode):
    descriptor = NodeTypeDescriptor(
        key="neuroflow.htmlExtract",
        version=1,
        name="HTML Extract",
        group="data",
        category="Core",
        description="Extracts text or attributes from HTML using a CSS selector.",
        icon="code-xml",
        color="cat-data",
        aliases=["scrape", "css selector", "parse html"],
        subtitle="={{ $parameter.cssSelector }}",
        inputs=[PortSpec(type="main")],
        outputs=[PortSpec(type="main")],
        idempotent=True,
        properties=[
            NodeProperty(
                name="sourceField",
                display_name="Source Field",
                type="string",
                required=True,
                description="Field on each input item holding an HTML string.",
            ),
            NodeProperty(
                name="cssSelector",
                display_name="CSS Selector",
                type="string",
                required=True,
                description="CSS selector for the element(s) to extract.",
                placeholder="article h1, .price",
            ),
            NodeProperty(
                name="attribute",
                display_name="Attribute",
                type="string",
                description="Extract this attribute's value instead of the "
                'element\'s text (e.g. "href").',
            ),
            NodeProperty(
                name="destinationField",
                display_name="Destination Field",
                type="string",
                default="extracted",
                required=True,
                description="Field on the output item to write the extracted "
                "value(s) to.",
            ),
        ],
    )

    async def execute(self, ctx: NodeExecutionContext) -> NodeOutput:
        params = ctx.params
        source_field = params.get("sourceField", "")
        selector = params.get("cssSelector", "")
        attribute = params.get("attribute") or None
        destination = params.get("destinationField", "extracted")

        results: list[Item] = []
        for item in ctx.input_items:
            html = str(item.json_.get(source_field, ""))
            soup = BeautifulSoup(html, "html.parser")
            matches = soup.select(selector)
            values = [
                (el.get(attribute) if attribute else el.get_text(strip=True))
                for el in matches
            ]
            value = values[0] if len(values) == 1 else values
            results.append(Item(json={**item.json_, destination: value}))
        return {"main": [results]}
