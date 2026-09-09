# HTML Extract

`neuroflow.htmlExtract` (v1) -- data/Core

Extracts text or attributes from HTML using a CSS selector.

**Aliases:** scrape, css selector, parse html

## Ports

- **Inputs:** main
- **Outputs:** main

## Properties

| Name | Display Name | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `sourceField` | Source Field | string | Yes | Field on each input item holding an HTML string. |
| `cssSelector` | CSS Selector | string | Yes | CSS selector for the element(s) to extract. |
| `attribute` | Attribute | string | No | Extract this attribute's value instead of the element's text (e.g. "href"). |
| `destinationField` | Destination Field | string | Yes | Field on the output item to write the extracted value(s) to. |
