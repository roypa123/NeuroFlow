# Remove Duplicates

`neuroflow.removeDuplicates` (v1) -- data/Core

Keeps only the first item for each distinct value.

**Aliases:** dedupe, distinct, unique

## Ports

- **Inputs:** main
- **Outputs:** main

## Properties

| Name | Display Name | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `compareField` | Compare Field | string | No | Field to compare items by. Leave empty to compare each item's entire JSON body. |
