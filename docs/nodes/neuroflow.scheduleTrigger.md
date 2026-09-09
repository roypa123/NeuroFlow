# Schedule

`neuroflow.scheduleTrigger` (v1) -- trigger/Core

Starts the workflow on a cron schedule.

**Aliases:** cron, interval, timer

## Ports

- **Inputs:** none
- **Outputs:** main

## Properties

| Name | Display Name | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `cron` | Cron Expression | string | Yes | Standard 5-field cron syntax. |
| `timezone` | Timezone | string | No |  |
| `catchUp` | Catch Up Missed Runs | boolean | No | If the worker was down when due, run once on restart. |
