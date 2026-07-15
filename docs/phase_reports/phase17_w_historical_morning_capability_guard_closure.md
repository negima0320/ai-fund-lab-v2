# Phase17-W Historical Morning Capability Guard Closure

## Status

`PHASE17_W_HISTORICAL_MORNING_CAPABILITY_ACCEPTED`

## Scope

The frozen failed run `runtime-test-historical-smoke-20260714T225334802121Z` stopped at `2026-07-06:morning` with `exit_code=40`, `final_state=BLOCKED`, and reason `morning pipeline supports demo/production capability only`.

That run was not resumed, mutated, advanced, or given post-hoc evidence. New closure evidence was written under `reports/phase17_w_historical_morning_capability_guard_closure/`.

## Classification

- `HISTORICAL_MORNING_CAPABILITY_WIRING_GAP`
- `LEGACY_MODE_NAME_BASED_GUARD`
- `HISTORICAL_RUNTIME_REPLAY_INTEGRATION_INCOMPLETE`

The failed run already had Data Readiness `READY`, Candidate AI `PASS`, Opportunity AI `PASS`, Opportunity Feature Contract v2 `READY`, and Historical Safety authority `historical_initial_no_external_effect`.

## Closure

The Morning pipeline no longer admits Historical by mode string. Historical Morning is admitted only through `evaluate_morning_capability`, which requires historical replay, `historical_simulated` broker environment, simulation, all external writes disabled, submit disabled, and runtime-test run/profile/evidence context.

Historical safety now propagates from Data Readiness into Planning as `data_readiness_historical_temporal_authority`, with replay planning permissions allowed and submit/broker writes blocked.

Run-scoped Morning evidence writing now emits capability, planning, pending-generation, and external-effect evidence for future blocked or halted Morning runs under the actual runtime test run id.

## Verification

- `pytest`: 68 passed
- `py_compile`: PASS
- `runtime_test.py plan`: PASS, no actual 5BD run executed

## Next Clean Rerun Prefix

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase17_w_pycache python3 scripts/runtime_test.py plan --profile historical-smoke --business-days 5 --start-date 2026-07-06 --json
```
