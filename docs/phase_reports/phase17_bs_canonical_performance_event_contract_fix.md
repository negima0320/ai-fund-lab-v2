# Phase17-BS Canonical Performance Event Contract Fix

## Executive Summary

Phase17-BS implemented a shared Canonical Performance Event Contract for Runtime v2 Persistent Ledger execution rows. The fix keeps raw broker-detail execution evidence for audit, while requiring performance/report consumers to count only canonical `execution_equivalent` events through a resolver.

Final judgment: `PHASE17_BS_FIX_REQUIRED`

The BS code path and targeted regressions pass. Formal acceptance is not claimed because full `tests/runtime_v2` still has 5 pre-existing baseline/hash guard failures unrelated to the BS resolver or Morning reason change.

## Contract Implemented

- Canonical performance fill: `execution_evidence_type == "execution_equivalent"`
- Raw broker-detail execution: audit/reconciliation evidence only, not performance metric input
- Resolver: `ai_fund_lab_v2.runtime_v2.ledger.performance_events.resolve_performance_fills`
- Loader: `load_canonical_execution_events(...)`
- Dedup key: canonical ledger execution dedup/source identity
- BUY/SELL: same canonical contract
- Missing equivalent: `REVIEW_REQUIRED`, no raw-detail fallback into performance metrics
- Historical/Demo/Production: same interpretation contract; environment differences remain external-effect boundaries

## Runtime Accounting Impact

Accounting remains unchanged for the accepted run:

- final cash: `191600.0`
- final market value: `813700.0`
- final total equity: `1005300.0`
- final positions: `5`

The Runtime-owned fill projection now computes cash/PnL from the canonical resolver instead of duplicating a local `execution_equivalent` filter.

## Dedup Verification

For target run `runtime-test-historical-smoke-20260715T232527885578Z`:

- raw execution representations: `10`
- canonical performance fills: `5`
- trade count: `5`
- turnover / gross traded notional: `808400.0`
- raw all-row aggregation would double count: `True`
- canonical view prevents double count: `True`

Detailed lineage is recorded in `order_execution_lineage_verification.json`.

## Morning Reason Fix

The Morning no-signal diagnostic now reports the binding predicate when available position slots are exhausted:

- previous frozen evidence: `NO_SIGNAL:available_cash_missing_or_zero`
- new binding reason for 2026-07-07 through 2026-07-10: `NO_SIGNAL:max_positions_reached`
- runtime decision changed: `false`

Observed rows: `4`

## Files Changed

- `src/ai_fund_lab_v2/runtime_v2/ledger/performance_events.py`
- `src/ai_fund_lab_v2/runtime_v2/ledger/__init__.py`
- `src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `tests/runtime_v2/test_phase17_bs_canonical_performance_event_contract.py`

## Evidence Files

- `reports/phase17_bs_canonical_performance_event_contract_fix/summary.json`
- `reports/phase17_bs_canonical_performance_event_contract_fix/canonical_event_contract.json`
- `reports/phase17_bs_canonical_performance_event_contract_fix/order_execution_lineage_verification.json`
- `reports/phase17_bs_canonical_performance_event_contract_fix/performance_metric_dedup_verification.json`
- `reports/phase17_bs_canonical_performance_event_contract_fix/morning_reason_verification.json`
- `reports/phase_reports/phase17_bs_canonical_performance_event_contract_fix.json`

## Verification

- BS dedicated tests: `6 passed`
- Ledger / execution / accounting / Morning related tests: `27 passed`
- `py_compile`: `PASS with PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache`
- `git diff --check`: `PASS`
- JSON validation: `PASS`

Full `tests/runtime_v2` result:

- `875 passed, 5 failed`
- status: `FAILED_PREEXISTING_BASELINE_GUARDS`
- BS-related failure identified: `False`

Failures observed:

- `tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py::test_phase15bm_isolated_fixture_does_not_modify_existing_runtime_root`
- `tests/runtime_v2/test_phase15bs_demo_broker_write_preconditions_finalization.py::test_phase15bs_existing_runtime_hashes_are_preserved`
- `tests/runtime_v2/test_phase15bt_explicit_demo_broker_write_execution.py::test_phase15bt_existing_runtime_hashes_remain_preserved`
- `tests/runtime_v2/test_phase15bw_runtime_end_to_end_daily_system_test_review.py::test_phase15bw_existing_runtime_hashes_unchanged`
- `tests/runtime_v2/test_phase16av_registry_consumer_cutover.py::test_feature_schema_registry_member_matches_legacy`

## Prohibited Operations Confirmation

- `runtime_test.py run/resume/reset/rollback/close`: not executed
- Frozen Run editing: not performed
- `.runtime` manual edit: not performed
- Ledger manual fix: not performed
- Registry refresh: not performed
- broker write / real submit: not performed
- external notification: not performed
- J-Quants fetch: not performed
- backtest-only trading logic: not added

## Acceptance Assessment

The canonical performance event contract itself is implemented and verified. The accepted run still has 5 substantive fills, 5 canonical performance fills, unchanged accounting, and retained raw audit evidence.

Formal BS acceptance remains blocked only by the full regression requirement. Since full `tests/runtime_v2` is not 0 failed in this workspace, the correct final judgment is:

`PHASE17_BS_FIX_REQUIRED`
