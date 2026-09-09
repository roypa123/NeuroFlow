# Execute Workflow

`neuroflow.executeWorkflow` (v1) -- flow/Core

Runs another workflow as a sub-workflow.

**Aliases:** subworkflow, call

## Ports

- **Inputs:** main
- **Outputs:** main

## Properties

| Name | Display Name | Type | Required | Description |
| --- | --- | --- | --- | --- |
| `workflowId` | Workflow | string | Yes | The id of the workflow to run. |
| `waitForCompletion` | Wait For Completion | boolean | No |  |
