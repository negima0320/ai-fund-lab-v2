# Phase25-A2 Daily Evaluation Evidence Schema and Producer

## 1. Primary Judgment

```text
PHASE25_A2_DAILY_EVALUATION_EVIDENCE_IMPLEMENTATION_COMPLETE_WITH_NON_BLOCKING_GAPS
```

Phase25-A2 implemented Daily Evaluation Evidence v1 only. It did not implement Run Summary, Benchmark adapter, Compound Reinvestment Trace, Cash Attribution Materialization, Experiment Comparison, Strategy changes, Runtime behavior changes, Planning changes, Submit changes, or Safety changes.

## 2. Implemented Scope

Implemented:

- Daily Evaluation Evidence schema.
- Read-only Daily Evaluation Evidence producer.
- Daily evidence materialization command.
- Opportunity Utilization Observability.
- Schema-level internal validation.
- Short read-only validation on an existing 2024 10BD run day.

Out of scope and not implemented:

- Run-level Performance Summary.
- Benchmark source or benchmark-relative metrics.
- Compound Reinvestment Trace materialization.
- Cash Attribution waterfall materialization.
- Experiment Comparison.
- Runtime, Strategy, Position Sizing, Planning, Submit, Safety, BUY, ADD, REDUCE, EXIT, or Market Context behavior changes.

## 3. Created Producer

Producer:

```text
phase25_daily_evaluation_evidence_producer
```

Module:

```text
src/ai_fund_lab_v2/runtime_v2/performance_evaluation/daily_evidence.py
```

CLI:

```text
PYTHONPATH=src python3 scripts/runtime_test.py daily-evidence --run-id <RUN_ID> [--business-date YYYY-MM-DD] --json
```

Materialization path:

```text
reports/performance_evaluations/<RUN_ID>/daily/<YYYY-MM-DD>/daily_evaluation_evidence.json
```

The producer reads Runtime Test evidence and writes only post-hoc Performance Evaluation artifacts. It does not mutate Runtime evidence, Runtime state, Strategy artifacts, Ledger, Current, Pending, Planning, Submit, Safety, or accepted generation.

## 4. Schema

Schema file:

```text
schemas/runtime_test/daily_evaluation_evidence.schema.json
```

Schema version:

```text
phase25_daily_evaluation_evidence.v1
```

Required top-level blocks:

- `capital`
- `returns`
- `risk`
- `activity`
- `opportunity_utilization`
- `benchmark`
- `attribution_inputs`
- `missing_fields`
- `warnings`
- `temporal_safety`

## 5. Capital Fields

Implemented required capital fields:

- `runtime_evaluation_capital`
- `buying_power`
- `cash`
- `market_value`
- `total_equity`
- `cash_ratio`
- `gross_exposure_ratio`
- `net_exposure_ratio`
- `position_count`
- `idle_cash`
- `target_gross_exposure_ratio`
- `target_cash_reserve_ratio`
- `policy_cash_buffer`
- `pending_reserved_cash`
- `actual_deployed_notional`
- `executed_buy_notional`
- `executed_sell_notional`

Authority:

```text
EOD_CURRENT_AFTER_EXECUTION_AND_CURRENT_VALUATION_REFRESH
```

When a field cannot be observed from retained evidence, the producer emits structured `NOT_OBSERVABLE` or `NOT_AVAILABLE`; it does not infer or zero-fill missing authority.

## 6. Opportunity Utilization Support

Implemented Opportunity Pipeline fields:

- `generated_opportunity_count`
- `eligible_opportunity_count`
- `planned_buy_count`
- `submitted_buy_count`
- `executed_buy_count`

Implemented reject reason buckets:

- `capital_constraint_count`
- `position_count_constraint_count`
- `safety_constraint_count`
- `eligibility_constraint_count`
- `lot_size_constraint_count`
- `price_constraint_count`
- `planning_rejection_count`
- `unknown_constraint_count`

Classification policy:

```text
EVIDENCE_ONLY_NO_INFERENCE
```

If runtime planning or lineage evidence is unavailable, Opportunity Utilization status becomes `NOT_OBSERVABLE`. If submitted BUY side cannot be determined from submitted order authority, the submitted BUY count becomes `UNKNOWN`.

## 7. Read-only Validation

Validation performed:

- Python compile with workspace-safe pycache.
- Unit tests for Daily Evidence producer and CLI materialization.
- JSON validation of schema file.
- Read-only materialization on existing 2024 run day:

```text
runtime-test-historical-extended-smoke-20260802T113114833349Z
2024-01-18
```

Result:

```text
PASS
```

Generated sample:

```text
reports/performance_evaluations/runtime-test-historical-extended-smoke-20260802T113114833349Z/daily/2024-01-18/daily_evaluation_evidence.json
```

Sample observed facts:

- Cash: `388010`
- Market Value: `679650`
- Total Equity: `1067660`
- Cash Ratio: `0.36342093925032315`
- Gross Exposure Ratio: `0.6365790607496769`
- Position Count: `4`
- Generated Opportunity Count: `6`
- Eligible Opportunity Count: `6`
- Planned BUY Count: `0`
- Submitted BUY Count: `0`
- Executed BUY Count: `0`

## 8. Non-Blocking Gaps

- `pending_reserved_cash` remains `NOT_OBSERVABLE` until a canonical same-date pending reservation authority is added to the daily evidence contract.
- First-day `daily_return` remains `NOT_AVAILABLE` when no previous daily evaluation evidence exists.
- Benchmark remains `MISSING` until the user approves a PIT-safe benchmark source.
- Submitted BUY count is `UNKNOWN` if submitted order authority does not expose side-specific submitted order records.
- Cash Attribution, Compound Reinvestment Trace, Run Summary, and Experiment Comparison are intentionally deferred to later Phase25 tasks.

## 9. Blocking Gaps

No blocking gap remains for Phase25-A2 acceptance.

## 10. Recommended Next Task

```text
Phase25-A3 Run-level Performance Summary Aggregator
```

Phase25-A3 should consume Daily Evaluation Evidence v1 and aggregate run-level metrics without rescanning mutable latest Runtime state.
