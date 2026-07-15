# Phase17-Z Historical Runtime 5BD Smoke Test Clean Rerun

## Status

`IN_PROGRESS`

## Scope

Phase17-Z executes the Historical Runtime 5 Business Days clean smoke test for:

- `2026-07-06`
- `2026-07-07`
- `2026-07-08`
- `2026-07-09`
- `2026-07-10`

This phase does not introduce a design change. Runtime Test Runner clean lifecycle is the execution authority:

1. close
2. rollback
3. backup
4. reset
5. plan
6. run

## Required Materials Reviewed

- `docs/phase_reports/phase17_r_historical_data_readiness_environment_and_temporal_authority_closure.md`
- `docs/phase_reports/phase17_s_historical_morning_json_serialization_and_evidence_closure.md`
- `docs/phase_reports/phase17_t_opportunity_artifact_identity_and_feature_contract_review.md`
- `docs/phase_reports/phase17_u_opportunity_feature_contract_authority_review.md`
- `docs/phase_reports/phase17_v_opportunity_market_sector_runtime_authority_closure.md`
- `docs/phase_reports/phase17_w_historical_morning_capability_guard_closure.md`
- `docs/phase_reports/phase17_x_historical_sell_planning_temporal_authority_and_pending_pm_continuity_closure.md`
- `docs/phase_reports/phase17_y_pm_adapter_registry_artifact_identity_closure.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/historical_runtime_test_contract.md`
- `docs/02_architecture/runtime_test_specification.md`
- `docs/02_architecture/historical_runtime_test_contract.md`

Requested but not present under `docs/02_architecture/`:

- `historical_runtime_contract.md`

## First Clean Run

Lifecycle:

- close: `runtime-test-historical-smoke-20260714T231426061528Z` -> `PASS`
- rollback: `backup-historical-smoke-20260714T231337630570Z` -> `PASS`
- backup: `backup-historical-smoke-20260714T235507138881Z` -> `PASS`
- reset: `backup-historical-smoke-20260714T235507138881Z` -> `PASS`
- plan: `runtime-test-historical-smoke-20260714T235530623052Z` -> `PASS`
- run: `runtime-test-historical-smoke-20260714T235530623052Z` -> `HALT`

Stop point:

```text
2026-07-06:submit
Runtime CLI exit_code=20
Runner exit_code=30
```

## Root Cause Classification

Classification:

- `Integration Bug`
- `Temporal Authority Bug`
- `Submit Safety Authority Propagation Bug`

Root cause:

The Historical Data Readiness, Morning, and Sell Planning chain correctly established run-scoped neutral Historical safety authority for `2026-07-06`:

```text
safety_authority=historical_initial_no_external_effect
safety_source=data_readiness_historical_temporal_authority
safety_policy_version=historical_replay_neutral_safety_v1
runtime_test_run_id=runtime-test-historical-smoke-20260714T235530623052Z
```

Pending and Approval were aligned to that authority and business date. However, the Submit job passed the raw latest Runtime safety decision into `run_submit_pipeline`, while Morning and Sell Planning already used the Data Readiness effective temporal safety authority.

The raw latest safety pointer referenced a different business date:

```text
business_date=2026-07-10
reason=HIGH_RISK_REVIEW
safety_decision=REVIEW_REQUIRED
safety_source=reports/safety/phase11/2026-07-10_safety_report.json
```

This was not a simple path-string mismatch. The effective artifact identity and temporal authority were different: Submit used stale/global latest safety evidence rather than the run-scoped Pending/Approval safety authority for `2026-07-06`.

Secondary issue:

Historical neutral safety represented `broker_write=BLOCKED` correctly, but also marked `buy_submit` / `sell_submit` as `BLOCKED`. In Historical Runtime, submit must enter the normal Submit Pipeline and HistoricalSubmitAdapter while broker write remains disabled. Therefore Runtime submit transition is `ALLOWED_FOR_REPLAY`; external broker write remains `BLOCKED`.

## Production Runtime Fix

Implemented in `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`:

- Submit now receives the same effective temporal safety authority used by Morning and Sell Planning.
- Submit is now covered by the Runtime Data Readiness Gate before the Submit Pipeline, so Pending / Approval / Safety authority is revalidated inside the independent Submit job process.
- Historical environment composition now passes the run-scoped `historical_asof_view.json` evidence path into `HistoricalSubmitAdapter`.
- Historical replay neutral safety sets `block_submit=false`.
- Historical replay neutral safety permits `buy_submit` and `sell_submit` as `ALLOWED_FOR_REPLAY`.
- `broker_write` remains `BLOCKED`; external writes remain disabled by environment composition and adapter boundary.
- Historical submit OHLCV source hash validation now prefers the run-scoped as-of evidence physical SHA when present, while retaining fail-closed hash checking.

No Historical-only test bypass, smoke-test fallback, frozen evidence mutation, or Runtime Test-only path was added.

## Validation After Fix

- `PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py` -> `14 passed`
- `PYTHONPYCACHEPREFIX=/Users/negishi/work/ai-fund-lab-v2/.pytest_cache/pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py` -> `PASS`

## Second Clean Run

Lifecycle:

- close: `runtime-test-historical-smoke-20260714T235530623052Z` -> `PASS`
- rollback: `backup-historical-smoke-20260714T235507138881Z` -> `PASS`
- backup: `backup-historical-smoke-20260714T235854033906Z` -> `PASS`
- reset: `backup-historical-smoke-20260714T235854033906Z` -> `PASS`
- plan: `runtime-test-historical-smoke-20260714T235908007454Z` -> `PASS`
- run: `runtime-test-historical-smoke-20260714T235908007454Z` -> `HALT`

Stop point:

```text
2026-07-06:submit
Runtime CLI exit_code=20
Runner exit_code=30
```

Additional classification:

- `Consumer Readiness Bug`
- `Submit Job Process Boundary Bug`

Root cause refinement:

The first fix correctly unified Submit with the effective safety authority object, but Submit runs as an independent Runtime CLI process. The Data Readiness authority manifest existed only in the earlier `data_readiness` process and was not reloaded or recomputed in the later `submit` process. As a result, Submit still lacked the run-scoped Pending / Approval / Safety authority context and fell back to the raw latest safety pointer.

Production Runtime fix:

- `_data_readiness_required_for_job("submit")` now returns `True`.
- Submit therefore rechecks the normal Runtime Data Readiness Gate with `readiness_scope=submit` before calling `run_submit_pipeline`.
- This is not a test-only fallback; it is the production-required Submit consumer readiness gate.

## Third Clean Run

Lifecycle:

- close: `runtime-test-historical-smoke-20260714T235908007454Z` -> `PASS`
- rollback: `backup-historical-smoke-20260714T235854033906Z` -> `PASS`
- backup: `backup-historical-smoke-20260715T000129184839Z` -> `PASS`
- reset: `backup-historical-smoke-20260715T000129184839Z` -> `PASS`
- plan: `runtime-test-historical-smoke-20260715T000148281465Z` -> `PASS`
- run: `runtime-test-historical-smoke-20260715T000148281465Z` -> `HALT`

Stop point:

```text
2026-07-06:submit
Runtime CLI exit_code=10
Runner exit_code=30
```

Additional classification:

- `Data Authority Bug`
- `Historical Submit Adapter Authority Bug`

Root cause:

Submit safety/readiness was fixed and Submit Guard passed. HistoricalSubmitAdapter then halted on `source hash mismatch` because it compared the active OHLCV source hash:

```text
4059ea4daa77cf9b338d57bb11d4497f0f4cde81405d35b594243667813a9f5f
```

against a stale fixed Phase17-D PIT manifest hash:

```text
c0f9b435e4a951dca1c97a3712571586b9028ace6747328fd7e6e69cfecc479d
```

The current run-scoped Market Refresh evidence already established the active physical source hash in:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260715T000148281465Z/daily/2026-07-06/market_refresh/historical_asof_view.json
```

This was not a path-only mismatch. It was a physical source SHA256 authority mismatch caused by the adapter reading stale static evidence instead of run-scoped Runtime evidence.

Production Runtime fix:

- `resolve_environment_composition` accepts `historical_asof_view_path`.
- CLI passes the run-scoped market refresh evidence path for Historical jobs.
- HistoricalSubmitAdapter validates OHLCV physical SHA256 against the run-scoped as-of authority when present.
- If run-scoped evidence is missing, the existing PIT manifest hash check remains fail-closed.

## Next Required Action

## Fourth Clean Run

Lifecycle:

- close: `runtime-test-historical-smoke-20260715T000148281465Z` -> `PASS`
- rollback: `backup-historical-smoke-20260715T000129184839Z` -> `PASS`
- backup: `backup-historical-smoke-20260715T000641297043Z` -> `PASS`
- reset: `backup-historical-smoke-20260715T000641297043Z` -> `PASS`
- plan: `runtime-test-historical-smoke-20260715T000657942695Z` -> `PASS`
- run: `runtime-test-historical-smoke-20260715T000657942695Z` -> `HALT`

Stop point:

```text
2026-07-06:execution
Runtime CLI exit_code=20
Runner exit_code=30
```

Additional classification:

- `Integration Bug`
- `Execution Current Apply Bug`
- `Historical Execution Cash Authority Bug`

Root cause:

Submit successfully created accepted Historical execution evidence and Execution accepted OrderList / Position / Cash evidence. Execution then halted before Current update because reconciliation was evaluated against the pre-execution Current state:

```text
execution_acceptance_status=PASS
runtime_owned_projection_status=NOT_EXECUTED
current_apply_status=NOT_EXECUTED
reconcile_status=REVIEW_REQUIRED
reconcile_findings=7
```

The normal Runtime-owned fill projection was guarded behind a `demo/production` mode check and was also sequenced after the reconciliation status decision for non-demo modes. Historical execution therefore never reached the same Runtime-owned Current projection used by normal accepted executions.

In addition, HistoricalExecutionSnapshotProvider emitted fixed `cash_available=0` / `buying_power=0`. That was not a path-only mismatch. It was a simulated broker Cash evidence authority mismatch: accepted fill cash effects and the Runtime starting Current cash implied `191600.0` for 2026-07-06, while the evidence asserted `0`.

Production Runtime fix:

- Execution now applies accepted Runtime-owned fill projection before reconciliation for all formal Runtime modes.
- `project_runtime_owned_fills_to_current` supports `historical` through the same Runtime-owned Submit Ledger authority as demo/production.
- Historical projection remains `production_equivalent=false`; production remains `production_equivalent=true`.
- HistoricalExecutionSnapshotProvider derives cash/buying_power from starting Current cash plus accepted fill `cash_effect` evidence, instead of emitting fixed zero.

No Historical-only reconciliation bypass, Runtime Test-only fallback, or smoke-only exception was added.

Validation after fix:

- `PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py tests/runtime_v2/test_phase14e23_execution_acceptance_policy.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py` -> `16 passed`
- `PYTHONPYCACHEPREFIX=/Users/negishi/work/ai-fund-lab-v2/.pytest_cache/pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py` -> `PASS`

## Next Required Action

Rerun clean lifecycle from the beginning:

1. close
2. rollback
3. backup
4. reset
5. plan
6. run
