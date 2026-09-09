# Redis

`neuroflow.redis` (v1) -- action/Database

Reads or writes a key in Redis.

**Aliases:** cache, kv

## Ports

- **Inputs:** main
- **Outputs:** main

## Credentials

Accepts: `redisApi`

## Properties

| Name | Display Name | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `credentialId` | Credential | credential | Yes | Redis connection to run the operation against. |
| `operation` | Operation | options | No | Redis command to run. |
| `key` | Key | string | Yes | Redis key (or channel, for Publish). |
| `value` | Value | string | No | Value to write. |
| `ttlSeconds` | TTL (seconds) | number | No | Expiry, in seconds. |
| `destinationField` | Destination Field | string | Yes | Field on the output item to write the result to. |
