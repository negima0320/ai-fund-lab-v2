# Phase22-MR System Status Shared-State Regression Review and Repair

## Primary Judgment

`PHASE22_MR_SYSTEM_STATUS_EXPECTATION_CONTRACT_UPDATED`

The four `tests/runtime_v2/test_phase19_ax_system_status.py` failures were reproduced and repaired. Root cause was stale shared-state expectations in an integration-style test that reads repository-local `.runtime`. The current `system-status` result is formally `REVIEW_REQUIRED`, which maps to exit code `10`. Production fail-closed behavior was preserved.

## Reproduction

Targeted reproduction:

```text
python3 -m pytest tests/runtime_v2/test_phase19_ax_system_status.py -vv
```

Before repair:

```text
1 passed, 4 failed
actual exit code: 10
expected exit codes: 0 or 20
```

Actual JSON reported:

```text
status = REVIEW_REQUIRED
exit_code = 10
inspection_judgment = REVIEW_REQUIRED
exit_code_basis = overall_inspection
data_judgment = REVIEW_REQUIRED
model_health_judgment = REVIEW_REQUIRED
runtime_execution_judgment = PASS
runtime_state_judgment = PASS
inspection_mode = HISTORICAL_LIFECYCLE_GATE_DONE
target_business_date = 2026-07-06
```

## Exit Code Authority

`scripts/runtime_test.py` defines:

- `0 = PASS`
- `10 = REVIEW_REQUIRED`
- `20 = BLOCKED`
- `30 = HALT`

`system-status` returns `report["exit_code"]` from `build_system_status_report`. Current shared `.runtime` has review findings, so exit code `10` is the correct fail-closed result.

## Shared State Inventory

The test invokes:

```text
PYTHONPATH=src:. python scripts/runtime_test.py system-status
```

without a temporary runtime root. It therefore reads repository-local `.runtime`, including:

- `.runtime/runtime_state/accepted_buy_ai_bundle.json`
- `.runtime/persistent_ledger/state.json`
- `.runtime/pending_order_plan/pending_order_plan.json`
- `reports/runtime_tests` closed run context
- runtime feature and BUY AI artifacts for the resolved target business date

Current inspected state resolves as shared runtime root, historical mode, lifecycle gate done, target business date `2026-07-06`.

## System Status Contract

System Status is a read-only whole-system health command. It reports review conditions without mutating Runtime state or connecting to Broker. Review-only findings must return `10`, not `0`, and must not be converted into `20` unless the report is blocked.

## Phase22-M Independence

Phase22-M changed Strategy observability and added `summarize --scope strategy*`. `system-status` parser, dispatch, producer, default scope, and exit-code mapping are separate. No Phase22-M code path is involved in the observed `system-status` command.

## Root Cause

Classification:

```text
STALE_TEST_EXPECTATION
SHARED_STATE_ISOLATION_BUG
INTENTIONAL_FAIL_CLOSED_STATE
```

The test expected a previous `HISTORICAL_POST_RUN` / target `2026-07-14` / PASS-like state. Current shared `.runtime` resolves `HISTORICAL_LIFECYCLE_GATE_DONE` / target `2026-07-06`, with review-required data/model health findings. Phase20-I already established that system-status shared-state tests must assert authority semantics rather than fixed local artifact values.

## Fix

Only `tests/runtime_v2/test_phase19_ax_system_status.py` was changed.

The test now asserts:

- exit code `10` for current `REVIEW_REQUIRED`
- `status_summary.inspection_judgment == REVIEW_REQUIRED`
- `exit_code_basis == overall_inspection`
- model health review semantics
- Runtime execution/state remain PASS
- broker connectivity remains NOT_PERFORMED
- inspection mode and target date come from reported context
- `--write-evidence` is review exit code `10`, not blocked `20`
- non-mutation of authority/current/pending files

Production code was not changed.

## Production-common Justification

This is a test expectation repair, not a Runtime behavior repair. The production-common contract is stronger after the repair because the test no longer treats a review-required system as PASS or BLOCKED.

## Test Isolation

The test remains an integration-style shared-state test, but the assertions now reflect that shared state can legitimately evolve. No fixture cleanup or state mutation was added.

## Runtime Preservation

Runtime Planning, Pending, Submit, Execution, Ledger, Current, AI Status, Strategy Observability, and existing summarize scopes were preserved.

## Tests

Passed:

- `tests/runtime_v2/test_phase19_ax_system_status.py -vv`: 5 passed.
- Phase22-M tests then system-status: 10 passed.
- AI status then system-status: 10 passed.
- system-status repeated twice: 10 passed.
- Phase22-M + summarize + system-status: 28 passed.
- Runtime short + AI status + system-status: 27 passed.
- Phase22-A through M plus system-status: 119 passed.
- compileall: PASS.
- run-status direct CLI: PASS.

## Long Tests Not Executed

5BD, 20BD, 200BD, 1-year, 3-year, and long runtime smoke tests were not executed.

## Blocking Gaps

None.

## Non-blocking Gaps

The Phase19-AX test still uses repository-local shared `.runtime`; future cleanup could add a fully isolated fixture version, but this is not required for Phase22-N entry.

## Phase22-N Gate

Phase22-N entry ready: YES.
Runtime switch ready: NO / REVIEW_REQUIRED.
Legacy retirement ready: NO.
