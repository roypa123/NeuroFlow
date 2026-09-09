# Date & Time

`neuroflow.dateTime` (v1) -- data/Core

Formats, shifts, or diffs date/time values.

**Aliases:** date, time

## Ports

- **Inputs:** main
- **Outputs:** main

## Properties

| Name | Display Name | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `operation` | Operation | options | No | Which date/time transformation to apply. |
| `inputField` | Input Field | string | No | Field holding an ISO-8601 string or epoch seconds. |
| `compareField` | Compare Field | string | No | Field holding the timestamp to diff against. |
| `amount` | Amount | number | No | Negative to subtract. |
| `unit` | Unit | options | No | Unit for Amount (Add/Subtract) or the result (Difference). |
| `format` | Output Format (strftime) | string | No | Python strftime format string for the output. |
| `destinationField` | Destination Field | string | Yes | Field on the output item to write the result to. |
