# Webhook

`neuroflow.webhookTrigger` (v1) -- trigger/Core

Starts the workflow when an HTTP request hits its URL.

**Aliases:** http trigger, inbound

## Ports

- **Inputs:** none
- **Outputs:** main

## Properties

| Name | Display Name | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `path` | Path | string | Yes | Left blank to generate a random UUID path. |
| `method` | Method | options | No |  |
| `authMode` | Authentication | options | No |  |
| `hmacSecret` | HMAC Secret | string | No |  |
| `headerAuthValue` | Expected Header Value | string | No |  |
| `responseMode` | Response | options | No | 'Respond node' mode is a Phase 6 node -- not built yet. |
