# Limit

`neuroflow.limit` (v1) -- data/Core

Keeps only the first or last N items.

**Aliases:** take, head, tail

## Ports

- **Inputs:** main
- **Outputs:** main

## Properties

| Name | Display Name | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `maxItems` | Max Items | number | Yes | Maximum number of items to keep. |
| `keep` | Keep | options | No | Which end of the list to keep items from. |
