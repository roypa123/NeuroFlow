# Split Out

`neuroflow.splitOut` (v1) -- data/Core

Splits an array field into one item per element.

**Aliases:** explode, flatten

## Ports

- **Inputs:** main
- **Outputs:** main

## Properties

| Name | Display Name | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `fieldToSplit` | Field To Split Out | string | Yes | Field on each input item that holds an array. |
| `includeOtherFields` | Include Other Fields | boolean | No | Keep the rest of the source item's fields alongside each split-out element (nested under the same field name if it isn't itself an object). |
