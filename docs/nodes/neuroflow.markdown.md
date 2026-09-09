# Markdown

`neuroflow.markdown` (v1) -- data/Core

Converts a field between Markdown and HTML.

**Aliases:** md

## Ports

- **Inputs:** main
- **Outputs:** main

## Properties

| Name | Display Name | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `direction` | Direction | options | No | Which way to convert. |
| `sourceField` | Source Field | string | Yes | Field on each input item holding the source text. |
| `destinationField` | Destination Field | string | Yes | Field on the output item to write the converted text to. |
