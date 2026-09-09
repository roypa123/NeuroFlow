# Compare Datasets

`neuroflow.compareDatasets` (v1) -- data/Core

Diffs two inputs by a key field.

**Aliases:** diff

## Ports

- **Inputs:** Input A, Input B
- **Outputs:** onlyInA, onlyInB, inBoth

## Properties

| Name | Display Name | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `keyField` | Key Field | string | Yes | Field present on both inputs to match items by. |
