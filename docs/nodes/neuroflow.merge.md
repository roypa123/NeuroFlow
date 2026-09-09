# Merge

`neuroflow.merge` (v1) -- flow/Core

Combines two input branches into one.

**Aliases:** join, combine

## Ports

- **Inputs:** Input 1, Input 2
- **Outputs:** main

## Properties

| Name | Display Name | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `mode` | Mode | options | No | How to combine Input 1 and Input 2. |
| `keyField` | Key Field | string | Yes | Field present on both inputs to match items by. |
