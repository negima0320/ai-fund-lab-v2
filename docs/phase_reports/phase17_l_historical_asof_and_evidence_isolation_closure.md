# Phase17-L Historical As-of and Evidence Isolation Closure

## Final Judgment

`PHASE17_L_HISTORICAL_ASOF_AND_EVIDENCE_ISOLATION_ACCEPTED`

Phase17-I/Kの5BD初回runは、2026-07-06の`market_refresh`で`future_row_detected`によりHALTした。この停止はFuture Data Guardとして正しい。原因はRuntime Coreではなく、Historical test supportが物理canonical parquet全体を通常Market Refreshに渡していたことで、2026-07-06評価時に2026-07-10までの物理行が見えていた点である。

## Failed Run Freeze

- failed run: `runtime-test-historical-smoke-20260714T033547145415Z`
- backup: `backup-historical-smoke-20260714T033440758704Z`
- halted job: `2026-07-06:market_refresh`
- CLI exit code: `20`
- readiness: `INVALID`
- blocked reason: `future_row_detected`
- data_until: `2026-07-10`
- requested_to_date: `2026-07-06`

The failed run was not resumed. No rollback, reset, restore, feature generation, canonical update, J-Quants fetch, submit, execution, Demo, or Production operation was executed in Phase17-L.

## Closure Implemented

1. Added Historical as-of resolver: `src/ai_fund_lab_v2/runtime_v2/historical_support/asof.py`.
2. Historical Market Refresh now validates a logical as-of view before consumer readiness.
3. Physical canonical data remains unchanged; future rows may exist physically, but must be excluded from the logical consumer view.
4. Demo/Production Future Data Guard remains strict; `future_row_detected` is not bypassed outside Historical as-of resolution.
5. Runtime Test identity is propagated from runner to Runtime CLI and Market Refresh evidence.
6. Historical Market Refresh evidence is scoped to `reports/runtime_tests/runs/<run_id>/daily/<business_date>/<job>/`.
7. Runner no longer uses profile accepted feature dates as authority; profile values are comparison-only.
8. Runtime v2 Mainline remains the only runtime path.

## 5BD As-of Audit

The 5BD window now resolves as follows:

| business_date | status | logical latest | physical max | future rows excluded from normalized OHLCV |
| --- | --- | --- | --- | ---: |
| 2026-07-06 | PASS | 2026-07-06 | 2026-07-10 | 16784 |
| 2026-07-07 | PASS | 2026-07-07 | 2026-07-10 | 12578 |
| 2026-07-08 | PASS | 2026-07-08 | 2026-07-10 | 8384 |
| 2026-07-09 | PASS | 2026-07-09 | 2026-07-10 | 4196 |
| 2026-07-10 | PASS | 2026-07-10 | 2026-07-10 | 0 |

Detailed evidence: `reports/phase17_l_historical_asof_and_evidence_isolation_closure/historical_asof_view_audit.json`.

## Evidence Collision

Collision was confirmed: `.runtime/operations/market_refresh/2026-07-06/market_data_refresh_detail.json` contained Historical failure evidence while `.runtime/operations/market_refresh/2026-07-06/market_refresh_manifest.json` remained Demo evidence. Phase17-L closes this by routing Historical Runtime Test evidence to the run-specific evidence tree while keeping normal operational paths as the default for non-test operation.

## Tests

- `tests/runtime_v2/test_phase17_l_historical_asof_and_evidence_isolation.py`: 6 passed.
- `tests/runtime_v2/test_phase17_k_runtime_test_runner.py`: 11 passed.
- Related Market Refresh/Data Readiness suite: 16 related tests passed; 2 existing Morning fixture tests stopped on `market_evidence_missing` before the target carryover stage.

## Acceptance Gates

All Phase17-L gates passed, including:

- `FAILED_RUN_EVIDENCE_FROZEN`
- `FAILED_RUN_NOT_RESUMED`
- `PHYSICAL_DATA_UNCHANGED`
- `HISTORICAL_ASOF_VIEW_READY`
- `FUTURE_ROWS_EXCLUDED_FROM_CONSUMER`
- `FUTURE_DATA_GUARD_UNCHANGED`
- `MARKET_REFRESH_HISTORICAL_READY`
- `DATA_READINESS_HISTORICAL_READY`
- `ALL_5BD_FEATURE_DATES_NORMAL_CONTRACT`
- `PROFILE_VALUES_COMPARISON_ONLY`
- `RUN_SPECIFIC_EVIDENCE_ISOLATED`
- `RUN_ID_PROPAGATED`
- `RUNNER_REMAINS_THIN`
- `NORMAL_RUNTIME_V2_MAINLINE_USED`
- `NO_ALTERNATE_RUNTIME`
- `NO_TRADING_STATE_MUTATION_DURING_PHASE17_L`

## Next

Recommended next prefix: `Phase17-M`

Work Name: `Historical Runtime 5BD Smoke Test Clean Rerun`

The existing failed run must remain frozen and must not be resumed. Phase17-M should close/freeze the failed run, rollback to the saved backup, validate, create a new backup/reset/plan/run_id, and rerun cleanly from 2026-07-06.
