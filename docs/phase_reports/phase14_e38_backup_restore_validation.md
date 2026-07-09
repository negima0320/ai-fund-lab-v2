# Phase14-E38 Runtime v2 Demo Operation Backup / Reset / Restore Validation

## Summary

Phase14-E38 validates that the Demo Operation Rehearsal can be repeated safely by backing up, resetting, and restoring the existing Runtime v2 operational state.

This phase did not add a Runtime module, CLI, Runtime path, rehearsal path, fake adapter, test-only Submit, or test-only SELL path.

Final judgment: `PHASE14E38_BACKUP_RESTORE_READY`

## Scope

Validated targets:

- `.runtime/`
- `reports/runtime_v2/`
- `reports/public/runtime_v2/`

Record targets:

- `docs/phase_reports/`
- `reports/phase_reports/`

Backup destination:

- `/private/tmp/phase14e38_backup_20260709T061615`

This is outside the Runtime v2 operational tree. No `.runtime/backups/phase14e38` and no `reports/runtime_v2/rehearsals` path were created.

## Validation Boundary

Allowed:

- existing Runtime paths backup
- existing Runtime paths reset
- existing Runtime paths restore
- existing Runtime v2 initializer/writers
- existing report writer
- external `/private/tmp` archive for backup
- phase report result recording

Forbidden and not performed:

- new Runtime module
- new CLI
- new Runtime path
- new rehearsal path
- fake adapter
- test-only Submit
- test-only SELL
- Runtime bypass for Submit/SELL
- manual JSON editing
- Current direct edit
- Production order
- Notification actual send

## Pre-Validation State

Before backup:

- Current cash: `949000.0`
- Current buying_power: `949000.0`
- Current positions: `5`
- Current source: `runtime_v2_runtime_owned_fill_projection`
- Pending state: `APPROVED`
- Pending items: `5`
- Pending target session date: `2026-07-09`

## Backup Validation

Backup source targets:

- `.runtime/`
- `reports/runtime_v2/`
- `reports/public/runtime_v2/`

Backup root:

- `/private/tmp/phase14e38_backup_20260709T061615`

Backup method:

- recursive file copy to external archive
- SHA-256 signature over relative file paths and file content hashes

Backup signature:

- file count: `20347`
- total bytes: `5180470135`
- sha256: `e87ae1c8756833da27afe5d326613e4d084b6157127d670e19f4273818d34fa5`

Backup verification:

- pre-backup signature matched backup signature
- backup root is outside Runtime operational tree
- no new Runtime path created

## Reset Validation

Reset method:

- existing Runtime v2 `initialize_demo_operation_current_sot`
- external initializer backup root under `/private/tmp/phase14e38_backup_20260709T061615/initializer_internal_backup`
- existing Runtime v2 Pending writer
- existing Runtime v2 Runtime State writer
- existing Runtime v2 report writer

Reset expected state:

- cash: `1000000.0`
- buying_power: `1000000.0`
- market_value: `0`
- total_equity: `1000000.0`
- positions: `0`
- Pending items: `0`
- orders ledger: empty
- executions ledger: empty
- positions ledger: empty
- cash ledger: one initial cash record
- events ledger: one initialization event
- Public Report redaction scan: PASS

Reset observed state:

| Field | Value |
| --- | ---: |
| cash | 1000000.0 |
| buying_power | 1000000.0 |
| market_value | 0 |
| total_equity | 1000000.0 |
| positions_count | 0 |
| pending_state | PENDING_APPROVAL |
| pending_items | 0 |
| orders_jsonl_bytes | 0 |
| executions_jsonl_bytes | 0 |
| positions_jsonl_bytes | 0 |
| cash_records | 1 |
| event_records | 1 |
| redaction_passed | true |

Reset result:

- `reset_ok=true`

## Restore Validation

Restore method:

- remove the reset versions of the three existing targets
- restore each target from the external `/private/tmp` backup archive
- recompute SHA-256 signature over restored targets

Restore signature:

- file count: `20347`
- total bytes: `5180470135`
- sha256: `e87ae1c8756833da27afe5d326613e4d084b6157127d670e19f4273818d34fa5`

Restore verification:

- restored signature matched pre-backup signature
- `restore_ok=true`

Post-restore state:

- Current cash: `949000.0`
- Current buying_power: `949000.0`
- Current positions: `5`
- Current source: `runtime_v2_runtime_owned_fill_projection`
- Pending state: `APPROVED`
- Pending items: `5`
- Pending target session date: `2026-07-09`

## Path Guard Verification

Checked:

- `.runtime/backups/phase14e38`: absent
- `reports/runtime_v2/rehearsals`: absent

This confirms the validation did not create a new rehearsal-specific Runtime path.

## Reusable Commands

### Backup Command Shape

Use an external archive path outside Runtime v2 operational tree:

```bash
PYTHONPATH=src python3 - <<'PY'
# copy .runtime, reports/runtime_v2, reports/public/runtime_v2
# to /private/tmp/phase14e38_backup_{timestamp}
# compute content signature
PY
```

### Reset Command Shape

Use existing Runtime v2 components only:

```bash
PYTHONPATH=src python3 - <<'PY'
# call initialize_demo_operation_current_sot(...)
# write empty Pending via write_pending_order_plan(...)
# write runtime_state/current_state.json via write_runtime_state(...)
# regenerate Runtime/Public report via generate_public_report_from_current(...)
PY
```

### Restore Command Shape

Restore only the existing Runtime/report targets:

```bash
PYTHONPATH=src python3 - <<'PY'
# restore .runtime, reports/runtime_v2, reports/public/runtime_v2
# from the external archive
# recompute signature and compare with pre-backup signature
PY
```

These are command shapes, not new Runtime CLI or modules.

## Acceptance Mapping

- Backup procedure completed: PASS.
- Restore procedure completed: PASS.
- Reset procedure completed: PASS.
- Existing Runtime only: PASS.
- New Runtime module: not created.
- New Runtime CLI: not created.
- New Runtime path: not created.
- New rehearsal path: not created.
- Demo Operation can be repeated from backup/reset/restore: PASS.

## Final Judgment

`PHASE14E38_BACKUP_RESTORE_READY`

