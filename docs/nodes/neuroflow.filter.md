# Filter

`neuroflow.filter` (v1) -- flow/Core

Keeps only the items matching a condition.

**Aliases:** keep, where

## Ports

- **Inputs:** main
- **Outputs:** main

## Properties

| Name | Display Name | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `value1` | Value 1 | string | Yes | Left-hand side of the comparison. |
| `operator` | Operator | options | No | How Value 1 and Value 2 are compared. |
| `value2` | Value 2 | string | Yes | Right-hand side of the comparison. |
