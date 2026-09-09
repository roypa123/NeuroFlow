# Switch

`neuroflow.switch` (v1) -- flow/Core

Routes each item to one of several outputs based on rules.

**Aliases:** route, case

## Ports

- **Inputs:** main
- **Outputs:** 0, 1, 2, fallback

## Properties

| Name | Display Name | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `numOutputs` | Number of Outputs | options | No | How many numbered rule outputs to use (2-4). |
| `value1_0` | Rule 1: Value 1 | string | No | Left-hand side of this rule's comparison. Leave unset to skip this rule slot entirely. |
| `operator_0` | Rule 1: Operator | options | No | How Value 1 and Value 2 are compared. |
| `value2_0` | Rule 1: Value 2 | string | No | Right-hand side of this rule's comparison. |
| `value1_1` | Rule 2: Value 1 | string | No | Left-hand side of this rule's comparison. Leave unset to skip this rule slot entirely. |
| `operator_1` | Rule 2: Operator | options | No | How Value 1 and Value 2 are compared. |
| `value2_1` | Rule 2: Value 2 | string | No | Right-hand side of this rule's comparison. |
| `value1_2` | Rule 3: Value 1 | string | No | Left-hand side of this rule's comparison. Leave unset to skip this rule slot entirely. |
| `operator_2` | Rule 3: Operator | options | No | How Value 1 and Value 2 are compared. |
| `value2_2` | Rule 3: Value 2 | string | No | Right-hand side of this rule's comparison. |
