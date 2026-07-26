# Phase20-L: Long-run Readiness Destructive Review

## 1. Executive Summary

Phase20-L performed a destructive review of Phase20-J/K performance observability before 20BD / 1y / 3y Historical runs.

Final judgment: `PHASE20_L_LONG_RUN_READY_WITH_NON_BLOCKING_GAPS`.

Blocking issues found and corrected in this phase:

- corrupt / mismatched observability JSON could be silently treated as missing
- duplicate execution rows could be counted twice by observability reconstruction
- tiny floating residual quantity could keep a campaign open
- Runtime PASS and analysis readiness were not explicitly separated in summary payloads

No Runtime trading logic, Strategy logic, AI, Opportunity, PM, Risk, Capital Allocation, Broker, Ledger, Current projection, Training, Calibration, or Validation was changed.

## 2. Scope and Non-goals

Scope: destructive design review, implementation inspection, synthetic fixtures, targeted regression, and minimal observability-consumer/writer hardening.

Non-goals: long Historical runs, Full Backtest, Benchmark source implementation, fee/tax/slippage modeling, UX filtering, Parquet migration, or Strategy changes.

## 3. Reviewed Documents

- `docs/phase_reports/phase20_j_performance_observability_gap_closure.md`
- `docs/phase_reports/phase20_k_performance_observability_consumer_correction.md`
- `docs/phase_reports/phase20_h_runtime_test_cli_consolidation_and_summarize_scope_implementation.md`
- `docs/phase_reports/phase20_i_ai_system_status_non_regression_failure_attribution.md`
- `docs/02_architecture/performance_metric_benchmark_experiment_contract.md`
- `docs/02_architecture/runtime_test_specification.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/phase_reports/phase19_by_runtime_test_summarize_run_authority_correction.md`
- `docs/03_operations/runtime_test_command_guide.md`
- `docs/01_requirements/phase_roadmap.md`

## 4. Reviewed Implementation

- `scripts/runtime_test.py`
- `src/ai_fund_lab_v2/runtime_v2/`
- `tests/runtime_v2/test_phase20_j_performance_observability.py`
- `tests/runtime_v2/test_phase20_k_performance_observability_consumer.py`
- `tests/runtime_v2/test_phase19_bv_runtime_test_summarize.py`
- `tests/runtime_v2/test_phase19_bw_system_status_scoped_output.py`
- `tests/runtime_v2/test_phase17_k_runtime_test_runner.py`
- `tests/runtime_v2/test_phase18v_runtime_test_fresh_run.py`
- `tests/runtime_v2/test_phase19_bj_runtime_test_abandon.py`

## 5. Current Readiness Baseline

5BD source run `runtime-test-historical-smoke-20260722T060403688727Z` remains the short-run evidence baseline:

- fresh-run: PASS
- completed days: 5
- Phase20-J producer evidence: PASS
- Phase20-K consumer correction: PASS
- benchmark snapshots: MISSING / NOT_CONFIRMED by design

## 6. Position Campaign Identity Review

Reviewed destructive cases:

- full EXIT then reBUY
- same-day EXIT then reBUY
- partial REDUCE then ADD
- multiple ADD
- multiple REDUCE then EXIT
- tiny residual quantity

Corrective action: added `POSITION_QUANTITY_EPSILON = 1e-6` for observability campaign closure and reopening decisions. This is not a Runtime trading quantity change.

## 7. Decision-to-Execution Linkage Review

Available exact/partial join keys:

- `position_campaign_id`
- `source_decision_type`
- `source_decision_id`
- `order_plan_item_id`
- `pending_item_id`
- `order_id`
- `execution_id`
- `realized_slice_id`

Remaining non-blocking gap: `source_decision_id` and `pending_item_id` can be `MISSING` in existing evidence. Consumer must not infer an exact join from symbol/date alone when IDs are missing.

## 8. Realized PnL / Cost Basis Review

Average-cost behavior was tested with BUY / ADD / REDUCE / ADD / REDUCE / EXIT and same-day reBUY. Duplicate execution IDs are now deduped before observability reconstruction.

Daily realized slices remain daily evidence, not cumulative files. Cumulative realized PnL is obtained by aggregating daily realized slices or campaign summaries.

## 9. PM Snapshot Temporal Review

PM snapshot remains decision-time evidence. Run-scoped body is the authority; shared `.runtime` paths are references only and can be stale after later runs.

No post-hoc fields are written to PM decision snapshots.

## 10. HALT / Resume Review

Run/resume keeps the same `run_id` and writes daily evidence through deterministic paths. Evidence file writes are atomic replacement, not append. Duplicate execution rows are now deduped by execution key before reconstruction, reducing resume/idempotency double-count risk.

Remaining gap: no full HALT/resume synthetic end-to-end test was added in this phase because it would require broader runner simulation. Existing resume behavior and new duplicate-execution fixture cover the core aggregation failure mode.

## 11. Abandon / Rollback Review

Run evidence is retained after abandon/rollback. Summary continues to use run-scoped evidence and the final-state hash guard for shared `.runtime` detail. If shared runtime no longer matches final hashes, current detail is not authority.

## 12. Run Authority Review

Confirmed and hardened:

- run evidence is scoped by run root
- completed-business-day filtering excludes stale daily files
- run_id mismatch is rejected from observability aggregation
- payload business_date mismatch is rejected
- corrupt JSON is reported as REVIEW_REQUIRED, not AVAILABLE

## 13. Missing / Corrupt Evidence Review

Corrective action: `_load_performance_observability` now records `read_issues` for:

- JSON read failure
- run_id mismatch
- business_date mismatch
- unknown schema version

These issues affect Observability Completeness and Performance Analysis Readiness, not Runtime Judgment.

## 14. Snapshot Selection Review

Campaign snapshots are deduped by `position_campaign_id` with priority:

1. latest snapshot business date
2. more complete event history
3. CLOSED over earlier OPEN

Non-blocking future gap: add monotonicity and event-set containment validation if 1y/3y evidence shows contradictory snapshots.

## 15. Determinism Review

Ordering is stable through sorted file traversal and sorted campaign output. Synthetic repeat checks showed deterministic counts and values. `generated_at` remains intentionally non-deterministic only for freshly written artifacts.

## 16. Scalability Review

Observed 5BD run evidence:

- daily JSON files: 295
- observability files: 25
- observability bytes: 104,878

Synthetic loader checks:

| Days | Files | Bytes | Load seconds | Campaign snapshots | Deduped campaigns |
|---:|---:|---:|---:|---:|---:|
| 20 | 100 | 143,276 | 0.0068 | 100 | 5 |
| 245 | 1,225 | 1,760,436 | 0.0683 | 1,225 | 5 |
| 735 | 3,675 | 5,283,816 | 0.2358 | 3,675 | 5 |

This synthetic shape is not a real Historical performance guarantee, but it indicates no 20BD blocker in current observability loading.

Non-blocking future gaps:

- scope-specific lazy loading
- streaming aggregation
- JSONL/Parquet for very high execution volumes
- date/symbol/campaign filters

## 17. Human / JSON Long-run Usability

Human output currently limits displayed rows to 20 positions and 10 lifecycles. For 1y/3y diagnosis, additional filters may be useful:

- `--symbol`
- `--campaign-id`
- `--limit`
- `--sort`
- `--date-from`
- `--date-to`

Not implemented in Phase20-L because this is UX/readability, not a 20BD blocker.

## 18. Benchmark Gap Impact

20BD Observability Validation: benchmark gap is non-blocking.

1y Strategy Performance Diagnosis: benchmark is strongly recommended before making market-relative conclusions.

Absolute return remains valid, but benchmark-relative attribution remains `MISSING_SOURCE_NOT_CONFIRMED`.

## 19. Fees / Tax / Slippage Gap Impact

Gross realized PnL is available. Net realized PnL remains unavailable because fees/tax/slippage are missing. No fee model was invented.

20BD: non-blocking for observability validation.

1y/3y: may materially affect net performance interpretation and should be addressed before final strategy-quality judgment.

## 20. Architecture Hole Findings

Judgments must remain separated:

- Runtime Judgment
- Run Lifecycle Judgment
- Observability Completeness Judgment
- Performance Analysis Readiness Judgment
- Long-run Readiness Judgment

Corrective action: summary payload now includes separate `observability_completeness_judgment` and `performance_analysis_readiness_judgment` with `runtime_judgment_impact=NONE`.

Position Campaign ID is currently Analysis Authority, not Runtime trading authority.

## 21. Blocking Findings

Blocking findings before correction:

- corrupt / mismatched evidence could be hidden as not retained
- duplicate execution rows could inflate observability
- tiny residual quantity could keep a campaign open
- Runtime PASS and Analysis Readiness were not explicitly separate

All were corrected in Phase20-L.

## 22. Non-blocking Findings

- TOPIX benchmark source not confirmed
- net realized PnL unavailable
- stable lot IDs unavailable
- long-run human filtering not implemented
- snapshot monotonicity validation not yet implemented
- full HALT/resume end-to-end synthetic fixture remains future work

## 23. Corrective Actions

Implemented:

- execution-row dedupe before observability reconstruction
- campaign closure epsilon for observability identity
- observability loader read issue reporting
- run_id / business_date / schema mismatch rejection
- separate Observability Completeness and Performance Analysis Readiness judgments
- destructive regression tests

## 24. Runtime Impact

Runtime impact: `NONE`.

## 25. Strategy Impact

Strategy impact: `NONE`.

## 26. Authority Impact

Authority impact: additive analysis/observability authority only. No Runtime decision authority changed.

## 27. Validation

Executed:

```text
py_compile
targeted pytest: 45 passed
synthetic 20BD / 245BD / 735BD loader checks
```

Long Historical, Full Backtest, Broker, Training, Calibration, Validation, and Experiment runs were not executed.

## 28. Long-run Readiness Judgment

20BD: READY.

1y: READY WITH NON-BLOCKING GAPS; benchmark and net PnL limitations must be considered before strategy-quality conclusions.

3y: TECHNICALLY READY FOR OBSERVABILITY LOADING in synthetic checks, but long-run UX/filtering and storage format improvements are recommended.

## 29. Final Judgment

`PHASE20_L_LONG_RUN_READY_WITH_NON_BLOCKING_GAPS`
