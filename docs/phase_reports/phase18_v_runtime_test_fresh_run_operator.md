# Phase18-V Runtime Test Fresh-Run Operator

Run ID: `phase18v-runtime-test-fresh-run-operator-20260717T000000Z`

Primary: `PHASE18_V_RUNTIME_TEST_FRESH_RUN_OPERATOR_COMPLETE`

Secondary: `FRESH_RUN_COMMAND_READY`, `PHASE18_COMPLETE_WITH_OPERATIONAL_EXTENSION`, `PHASE19_NOT_STARTED`

## Command

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-extended-smoke --date-from 2026-06-29 --date-to 2026-07-10 --business-days 10 --initial-cash 1000000 --confirm --yes-i-understand-this-mutates-trading-state
```

## Acceptance

| Item | Status | Evidence |
|---|---:|---|
| fresh-run entrypoint | PASS | scripts/runtime_test.py fresh-run parser and command |
| ordered orchestration | PASS | Status -> Backup -> Reset -> Plan -> Run -> Validate -> Close summary |
| dry-run no mutation | PASS | dry-run test verifies no backup, reset, CLI execution, close mutation |
| failure stop | PASS | backup/reset/plan/run/validate failures stop later steps |
| normal Runtime CLI use | PASS | happy path test monkeypatches run_runtime_cli and verifies module command |
| evidence preservation | PASS | no purge path in fresh-run; new run_id generated |
| auto-prepare | LEGACY_INCOMPLETE_OPTION | option retained only as deprecated failure directing users to fresh-run |
| command guide | PASS | Fresh Run section added to docs/03_operations/runtime_test_command_guide.md |
| production prohibition | PASS | production profile rejected; broker write/external delivery disabled by profile checks |

## Tests

- `targeted`: `27 passed`
- `compile`: `PASS`
- `dry_run_command`: `DRY_RUN PASS; no Runtime CLI execution and no trading state mutation`

## Non-Execution Confirmation

Production Registry accepted state変更、Runtime accepted model switch、Production BUY restart、Broker write、External notification delivery、Historical 10BD実Run、Target変更、Feature変更、BV15変更はいずれも未実施です。

## Final

`PHASE18_V_RUNTIME_TEST_FRESH_RUN_OPERATOR_COMPLETE`

`FRESH_RUN_COMMAND_READY` / `PHASE18_COMPLETE_WITH_OPERATIONAL_EXTENSION` / `PHASE19_NOT_STARTED`
