# Code

`neuroflow.code` (v1) -- data/Core

Run a JavaScript snippet against the input items.

**Aliases:** javascript, js, script, function

## Ports

- **Inputs:** main
- **Outputs:** main

## Properties

| Name | Display Name | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `mode` | Mode | options | No |  |
| `code` | Code | code | Yes | JavaScript. In 'Run Once for All Items' mode, `items` is an array of the input item JSON and the snippet's value becomes the output. In 'Run Once per Item' mode, `item` is a single item's JSON. The result must be an object or an array of objects. |
