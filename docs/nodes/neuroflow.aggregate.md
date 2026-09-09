# Aggregate

`neuroflow.aggregate` (v1) -- data/Core

Combines all items into one array field.

**Aliases:** combine, collect

## Ports

- **Inputs:** main
- **Outputs:** main

## Properties

| Name | Display Name | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `mode` | Mode | options | No | What to collect into the output array. |
| `sourceField` | Source Field | string | Yes | Field to collect values from, one per input item. |
| `destinationField` | Destination Field | string | Yes | Field on the output item to hold the aggregated array. |
| `batchSize` | Batch Size | number | No | Split into multiple output items of this many aggregated rows each. 0 means one output item for everything. |
