# HTTP Request

`neuroflow.http` (v1) -- action/Core

Make an HTTP request to any URL.

**Aliases:** api, rest, curl, fetch, webhook

## Ports

- **Inputs:** main
- **Outputs:** main

## Credentials

Accepts: `httpHeaderAuth`, `httpBasicAuth`, `oauth2Generic`

## Properties

| Name | Display Name | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `credentialId` | Authentication | credential | No | Optional. Applied via the credential's declared auth. |
| `method` | Method | options | No |  |
| `url` | URL | string | Yes |  |
| `sendBody` | Send Body | boolean | No |  |
| `body` | Body | json | No |  |
| `timeout` | Timeout (ms) | number | No | Request timeout, in milliseconds. |
| `paginationMode` | Pagination | options | No | Follow a next-page URL found in each response body. |
| `nextUrlField` | Next URL Field | string | No | Dot-path in the response body to the next page's URL. |
| `maxRequests` | Max Requests | number | No | Stop following pages after this many requests. |
