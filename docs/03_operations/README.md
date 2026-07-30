# Operations Runbook Index

This directory is the permanent operations documentation entrypoint for AI Fund Lab v2.
Phase reports may record evidence and change history, but operator commands that are meant to be reused must be promoted here.

## Daily Operation

- Demo daily operation: [demo_daily_operation_runbook.md](../operations/demo_daily_operation_runbook.md)
- Runtime Test operation: [runtime_test_command_guide.md](runtime_test_command_guide.md)

## Data Acquisition And Updates

- J-Quants data operations: [jquants_data_operations_runbook.md](jquants_data_operations_runbook.md)
- Corporate Event source materialization: [jquants_data_operations_runbook.md#corporate-event-source-materialization](jquants_data_operations_runbook.md#corporate-event-source-materialization)

## AI Generation Operation

- Accepted Generation lifecycle commands are not yet consolidated into a permanent runbook. Until that runbook exists, use the relevant architecture contract and phase evidence, and add/update a permanent runbook whenever an operator command is changed.

## Runtime Test

- Runtime Test command guide: [runtime_test_command_guide.md](runtime_test_command_guide.md)
- Before any 10BD/20BD run, complete the Corporate Event materialization and validation gate in [J-Quants data operations](jquants_data_operations_runbook.md#corporate-event-validation-gate).

## Backup And Restore

- Runtime Test backup/reset procedures: [runtime_test_command_guide.md#backup](runtime_test_command_guide.md#backup)
- Broader Production/Demo backup and restore commands are not yet consolidated into a dedicated permanent runbook.

## Incident Response

- No dedicated incident response runbook exists yet. Incident-handling tasks must add or update a permanent operations runbook instead of leaving commands only in phase reports.

## Broker Connectivity

- Demo operation broker boundary: [demo_daily_operation_runbook.md](../operations/demo_daily_operation_runbook.md)
- Broker connectivity diagnostics are not consolidated here yet. Do not run Broker write commands unless a separate approved runbook explicitly authorizes them.

## Documentation Update Rule

Any task that adds or changes an operator CLI, argument, materialization procedure, runtime start/stop procedure, recovery command, or validation command must update:

- this index,
- the relevant permanent runbook,
- command examples so they match `--help`,
- validation commands,
- rollback or failure procedure.

Recording commands only in a phase report is not sufficient for acceptance.
