# Crypto

`neuroflow.crypto` (v1) -- data/Core

Hashes, signs, encodes, or generates random values.

**Aliases:** hash, hmac, base64

## Ports

- **Inputs:** main
- **Outputs:** main

## Properties

| Name | Display Name | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `action` | Action | options | No | What to do with the input field's value. |
| `algorithm` | Algorithm | options | No | Hash algorithm used for Hash/HMAC. |
| `secretField` | Secret | string | No | Plain-text HMAC key. Not a credential -- use a Credential or secret Variable if this value itself is sensitive. |
| `inputField` | Input Field | string | Yes | Field on each input item to read the value from. |
| `length` | Length | number | No | Number of hex characters to generate. |
| `destinationField` | Destination Field | string | Yes | Field on the output item to write the result to. |
