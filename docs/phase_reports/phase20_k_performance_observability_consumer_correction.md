# Phase20-K: Performance Observability Consumer Correction

## 1. Executive Summary

Phase20-K corrected the `summarize` consumer and human formatter for Phase20-J run-scoped observability evidence. Producer/schema/evidence writer behavior was preserved.

Final judgment: `PHASE20_K_OBSERVABILITY_CONSUMER_CORRECTION_COMPLETE`.

## 2. Scope and Non-goals

Scope was limited to summary loading, aggregation, metric status classification, and human output formatting.

Non-goals: Runtime, AI, Opportunity, PM producer, Risk, Capital Allocation, Broker, Execution, Ledger, Current, Evidence Producer, Training, Calibration, Validation, or Experiment changes.

## 3. Reviewed Documents

- `docs/phase_reports/phase20_j_performance_observability_gap_closure.md`
- `reports/phase_reports/phase20_j_performance_observability_gap_closure.json`
- `docs/phase_reports/phase20_h_runtime_test_cli_consolidation_and_summarize_scope_implementation.md`
- `docs/phase_reports/phase20_i_ai_system_status_non_regression_failure_attribution.md`
- `docs/02_architecture/performance_metric_benchmark_experiment_contract.md`
- `docs/02_architecture/runtime_test_specification.md`
- `docs/03_operations/runtime_test_command_guide.md`
- `docs/phase_reports/phase19_by_runtime_test_summarize_run_authority_correction.md`

## 4. Reviewed Implementation

- `scripts/runtime_test.py`
- `tests/runtime_v2/test_phase20_j_performance_observability.py`
- `tests/runtime_v2/test_phase19_bv_runtime_test_summarize.py`
- `tests/runtime_v2/test_phase19_bw_system_status_scoped_output.py`

## 5. Short-run Evidence Findings

The 5BD run `runtime-test-historical-smoke-20260722T060403688727Z` had valid Phase20-J producer evidence:

- 5 daily position campaign snapshots per day
- 5 unique `position_campaign_id` values
- 8 fills
- 3 realized slices
- PM decision snapshots with ADD/HOLD/REDUCE/EXIT
- benchmark snapshots correctly `MISSING / NOT_CONFIRMED`

## 6. Producer Assessment

Producer follow-up was not required. The observed defects were consumer aggregation and formatting issues.

## 7. Consumer Defect Attribution

Defects found:

- daily campaign snapshots were counted as distinct lifecycles
- human lifecycle formatter read `status` instead of `campaign_status`
- positions formatter obscured closed campaign realized PnL
- `Realized PnL` and `Execution Notional` were included in warnings despite available evidence

## 8. Campaign Deduplication Correction

`_load_performance_observability` now retains `position_campaign_snapshot_count` and deduplicates campaigns by `position_campaign_id`.

Snapshot selection rank:

1. latest snapshot business date
2. larger event history
3. CLOSED state over earlier OPEN state

## 9. Lifecycle Summary Correction

Lifecycle scope now reports `campaign_count` and uses deduplicated campaign records. Human output shows:

```text
symbol
position_campaign_id
campaign_status
event_count
opened_business_date
closed_business_date
realized_pnl
unrealized_pnl
total_campaign_pnl
```

The 5BD run now shows `position_campaigns: 5`, not 25.

## 10. Positions Summary Correction

Positions scope uses campaign rows when Phase20-J evidence exists. Closed campaigns remain visible and display `realized`, `unrealized`, and `total` separately.

## 11. Performance Metric Correction

`Realized PnL` now reconciles final current state `realized_pnl` against sum of realized-slice gross PnL when both are available.

`Execution Notional` now reports:

```text
buy_execution_notional
sell_execution_notional
total_execution_notional
```

Turnover, drawdown, cash utilization, exposure, and concentration remain `NOT_AVAILABLE` unless contract-grade evidence exists.

## 12. Warning Semantics

Human metric warnings now include only `MISSING`, `NOT_AVAILABLE`, `NOT_RETAINED`, or `REVIEW_REQUIRED` metric statuses. `DERIVABLE_PARTIAL` with an available value is not treated as a missing warning.

Gross realized PnL and net realized PnL remain distinct. Net realized PnL is unavailable while fees/tax are missing.

## 13. Human / JSON Consistency

Human output is derived from scope JSON fields:

- campaign count from `campaign_count`
- status from `campaign_status`
- realized PnL from `realized_pnl`
- total PnL from `total_campaign_pnl`
- warnings from metric statuses

## 14. Run Authority

Consumer aggregation uses `reports/runtime_tests/runs/<RUN_ID>/daily/<DATE>/...` and `completed_business_days`. Shared `.runtime` detail remains guarded by final-state hash matching.

## 15. Temporal Integrity

Decision-time PM evidence, execution evidence, EOD campaign snapshots, and post-hoc summary remain separated. Campaign summaries are `POST_HOC_ATTRIBUTION_ONLY`.

## 16. Backward Compatibility

Existing JSON fields were not removed. Old runs without Phase20-J evidence continue to return `MISSING`, `NOT_RETAINED`, or `DERIVABLE_PARTIAL`.

## 17. Remaining Gaps

- benchmark source remains `NOT_CONFIRMED`
- net realized PnL remains unavailable while fees/tax are missing
- stable lot IDs remain unavailable
- drawdown and daily equity curve require retained daily valuation evidence or baseline artifacts

## 18. Runtime Impact

Runtime impact: `NONE`.

## 19. Strategy Impact

Strategy impact: `NONE`.

## 20. Authority Impact

Authority impact: summary consumer correction only. No Runtime decision authority changed.

## 21. Validation

Executed short checks only:

```text
py_compile
targeted pytest for Phase20-K consumer tests
targeted summarize checks against runtime-test-historical-smoke-20260722T060403688727Z
Phase20-H/I scoped regression
JSON validation
git diff --check
```

Long Historical, Broker, Training, Calibration, Validation, and Experiment runs were not executed.

## 22. Final Judgment

`PHASE20_K_OBSERVABILITY_CONSUMER_CORRECTION_COMPLETE`
