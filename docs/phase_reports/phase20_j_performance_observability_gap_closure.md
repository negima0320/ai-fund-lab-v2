# Phase20-J: Performance Observability Gap Closure

## 1. Executive Summary

Phase20-J implemented run-scoped performance observability for future Runtime Test runs. The change is additive and does not alter Runtime, AI, Opportunity, PM, Risk, Capital Allocation, Accepted Generation, Training, Calibration, Validation, or Broker behavior.

Final judgment: `PHASE20_J_PERFORMANCE_OBSERVABILITY_GAP_CLOSURE_COMPLETE_WITH_BENCHMARK_SOURCE_GAP`.

## 2. Scope and Non-goals

Scope was limited to evidence writers, schemas, summarize integration, operator documentation, and short tests.

Non-goals: performance improvement, strategy changes, experiment execution, long historical runs, external benchmark fetch, and runtime decision input changes.

## 3. Reviewed Documents

- `docs/phase_reports/phase20_i_ai_system_status_non_regression_failure_attribution.md`
- `docs/phase_reports/phase20_h_runtime_test_cli_consolidation_and_summarize_scope_implementation.md`
- `docs/phase_reports/phase20_g_runtime_test_cli_responsibility_and_observability_integration_audit.md`
- `docs/phase_reports/phase20_a_performance_baseline_and_attribution_evidence_inventory.md`
- `docs/phase_reports/phase20_b_performance_metric_benchmark_experiment_contract.md`
- `docs/phase_reports/phase20_c_read_only_performance_baseline_extraction.md`
- `docs/phase_reports/phase20_d_trade_and_position_management_attribution_baseline.md`
- `docs/phase_reports/phase20_e_performance_diagnosis_and_attribution_report.md`
- `docs/phase_reports/phase20_f_performance_improvement_candidate_identification.md`
- `docs/02_architecture/performance_metric_benchmark_experiment_contract.md`
- `docs/03_operations/runtime_test_command_guide.md`

## 4. Reviewed Implementation

- `scripts/runtime_test.py`
- `src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py`
- `src/ai_fund_lab_v2/runtime_v2/simulation/broker.py`
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- Runtime v2 execution, submit, pending, ledger, and current valuation references found by targeted search.

## 5. Existing Observability Gap Confirmation

Phase20-A to I confirmed that the 20BD baseline could report return and drawdown but could not fully attribute performance to BUY/HOLD/ADD/REDUCE/EXIT without retained fill-level realized PnL, PM decision body snapshots, and benchmark evidence.

## 6. Position Campaign Identity

Added run-scoped deterministic `position_campaign_id`.

Policy: `RUN_SCOPED_DETERMINISTIC_EXECUTION_REPLAY_SYMBOL_SEQUENCE`.

Behavior:

- initial BUY opens a campaign
- ADD remains in the same campaign
- REDUCE remains in the same campaign
- full EXIT closes the campaign
- reBUY after full EXIT starts a new campaign
- symbol-only identity is prohibited

## 7. Fill / Realized Slice Observability

Added daily fill evidence:

```text
daily/<DATE>/execution/fills.json
```

Added daily realized slice evidence:

```text
daily/<DATE>/execution/realized_slices.json
```

Runtime cost basis was confirmed as average-cost projection in `runtime_owned_fill_projection.py` and `simulation/broker.py`. Stable lot IDs were not confirmed, so the formal realized PnL unit is `realized_slice`; lot-level remains `MISSING`.

Fees, tax, and slippage are recorded as `{ "value": "MISSING", "status": "NOT_AVAILABLE" }` when unavailable.

## 8. PM Decision Snapshot

Added daily PM decision snapshot:

```text
daily/<DATE>/position_management/pm_decisions.json
```

The snapshot is decision-time only and excludes future/post-hoc outcome fields.

## 9. BUY Observability

BUY executions are linked to `position_campaign_id`, fill evidence, and available order-plan identifiers. Candidate/opportunity fields remain authority references or `MISSING` where not retained in Runtime Test evidence.

## 10. REDUCE / EXIT Linkage

SELL executions and realized slices carry available join keys:

```text
position_campaign_id
source_decision_type
source_decision_id
order_plan_item_id
pending_item_id
order_id
execution_id
realized_slice_id
```

## 11. Benchmark Source Assessment

Local non-report/non-runtime search found no confirmed TOPIX or J-Quants-compatible benchmark source implementation. External benchmark acquisition was not performed.

## 12. Benchmark Evidence Implementation

Added missing-status benchmark snapshot:

```text
daily/<DATE>/benchmark/benchmark_snapshot.json
```

Current status:

```text
Benchmark source = NOT_CONFIRMED
Benchmark implementation = NOT_PERFORMED
Status = MISSING
Required decision = USER_OR_ARCHITECTURE_APPROVAL
```

## 13. Run Evidence Layout

Added run-scoped daily outputs under:

```text
reports/runtime_tests/runs/<RUN_ID>/daily/<DATE>/
```

The layout avoids writing post-hoc attribution into shared `.runtime`.

## 14. Summary Scope Integration

Updated `summarize --scope performance`, `positions`, `lifecycle`, and `full` to consume Phase20-J evidence additively.

Old runs return `NOT_RETAINED`, `MISSING`, or `DERIVABLE_PARTIAL`.

## 15. Schema / Contract Changes

Added schemas:

- `schemas/runtime_test/position_campaign.schema.json`
- `schemas/runtime_test/runtime_fill_observability.schema.json`
- `schemas/runtime_test/realized_slice.schema.json`
- `schemas/runtime_test/pm_decision_snapshot.schema.json`
- `schemas/runtime_test/benchmark_snapshot.schema.json`

No new architecture document was required.

## 16. Temporal Integrity

Decision-time evidence, execution-time evidence, EOD valuation, and post-hoc attribution remain separated. PM snapshots do not include MFE/MAE, post-sale return, future benchmark rows, or future price outcomes.

## 17. Long-run Scalability Assessment

Evidence is partitioned by date and type. This is suitable for 1y/3y historical runs because summarize can load only known daily files, and large monolithic JSON is avoided. Future improvement may add JSONL/Parquet export if daily execution volume grows materially.

## 18. Backward Compatibility

Existing summary JSON fields were not removed or renamed. New fields are additive. Old runs remain summarizable.

## 19. Remaining Gaps

- stable lot IDs are still not available
- fees/tax/slippage are not available
- candidate/opportunity body snapshots may remain partial when not retained
- TOPIX benchmark source is not confirmed
- approval/submit linkage may still be partial when IDs are absent upstream

## 20. Runtime Impact

Runtime impact: `NONE` for trading decisions. Runtime Test writes additional evidence after jobs complete.

## 21. Strategy Impact

Strategy impact: `NONE`.

## 22. Authority Impact

Authority impact: additive Runtime Test evidence authority only. No Accepted Generation, Training, Calibration, Validation, or Broker authority change.

## 23. Validation

Executed:

```text
python3 -m py_compile scripts/runtime_test.py tests/runtime_v2/test_phase20_j_performance_observability.py
python3 -m pytest -q tests/runtime_v2/test_phase20_j_performance_observability.py
python3 -m pytest -q tests/runtime_v2/test_phase20_j_performance_observability.py tests/runtime_v2/test_phase19_bv_runtime_test_summarize.py tests/runtime_v2/test_phase19_bw_system_status_scoped_output.py tests/runtime_v2/test_phase19_av_ai_status.py
python3 -m json.tool reports/phase_reports/phase20_j_performance_observability_gap_closure.json
python3 -m json.tool schemas/runtime_test/*.schema.json
git diff --check
```

Long-running Historical, Broker, Training, Calibration, Validation, and Experiment runs were not executed.

## 24. Final Judgment

`PHASE20_J_PERFORMANCE_OBSERVABILITY_GAP_CLOSURE_COMPLETE_WITH_BENCHMARK_SOURCE_GAP`
