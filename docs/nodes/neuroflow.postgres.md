# Postgres

`neuroflow.postgres` (v1) -- action/Database

Runs a SQL query against a Postgres database.

**Aliases:** sql, postgresql

## Ports

- **Inputs:** main
- **Outputs:** main

## Credentials

Accepts: `postgresApi`

## Properties

| Name | Display Name | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `credentialId` | Credential | credential | Yes | Postgres connection to run the query against. |
| `query` | Query | code | Yes | Use %(name)s placeholders bound from Query Parameters. |
| `queryParameters` | Query Parameters | json | No | Object of placeholder name -> value. |
