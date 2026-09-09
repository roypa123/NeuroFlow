from __future__ import annotations

from app.modules.nodes.base import NodeExecutionContext
from app.modules.nodes.descriptors import Item
from app.nodes.markdown_ import MarkdownNode


async def test_markdown_to_html() -> None:
    node = MarkdownNode()
    items = [Item(json={"src": "# Hello"})]
    ctx = NodeExecutionContext(
        input_items=items,
        params={
            "direction": "markdownToHtml",
            "sourceField": "src",
            "destinationField": "out",
        },
    )

    result = await node.execute(ctx)

    assert result["main"][0][0].json_["out"] == "<h1>Hello</h1>"


async def test_html_to_markdown() -> None:
    node = MarkdownNode()
    items = [Item(json={"src": "<strong>bold</strong>"})]
    ctx = NodeExecutionContext(
        input_items=items,
        params={
            "direction": "htmlToMarkdown",
            "sourceField": "src",
            "destinationField": "out",
        },
    )

    result = await node.execute(ctx)

    assert result["main"][0][0].json_["out"].strip() == "**bold**"
