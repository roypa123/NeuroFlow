from __future__ import annotations

from app.modules.nodes.base import NodeExecutionContext
from app.modules.nodes.descriptors import Item
from app.nodes.html_extract import HtmlExtractNode


async def test_extracts_text_for_a_single_match() -> None:
    node = HtmlExtractNode()
    items = [Item(json={"html": "<div><h1>Title</h1></div>"})]
    ctx = NodeExecutionContext(
        input_items=items,
        params={
            "sourceField": "html",
            "cssSelector": "h1",
            "destinationField": "title",
        },
    )

    result = await node.execute(ctx)

    assert result["main"][0][0].json_["title"] == "Title"


async def test_extracts_a_list_for_multiple_matches() -> None:
    node = HtmlExtractNode()
    items = [Item(json={"html": "<ul><li>a</li><li>b</li></ul>"})]
    ctx = NodeExecutionContext(
        input_items=items,
        params={
            "sourceField": "html",
            "cssSelector": "li",
            "destinationField": "items",
        },
    )

    result = await node.execute(ctx)

    assert result["main"][0][0].json_["items"] == ["a", "b"]


async def test_extracts_an_attribute_value() -> None:
    node = HtmlExtractNode()
    items = [Item(json={"html": '<a href="https://example.com">link</a>'})]
    ctx = NodeExecutionContext(
        input_items=items,
        params={
            "sourceField": "html",
            "cssSelector": "a",
            "attribute": "href",
            "destinationField": "url",
        },
    )

    result = await node.execute(ctx)

    assert result["main"][0][0].json_["url"] == "https://example.com"
