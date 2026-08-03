# Phase25-A3 Capital Efficiency and Compound Reinvestment Trace

## 1. Executive Summary

Phase25-A3 implemented a read-only Capital Efficiency Trace artifact that supplements Daily Evaluation Evidence v1.

It materializes same-day capital authority from Current through Portfolio Policy, Capital Deployment, Position Sizing, Runtime Planning, Submit, and Execution evidence where available.

No Runtime, Strategy, Planning, Submit, Safety, Position Sizing, Capital Policy, or config behavior was changed.

## 2. Primary Judgment

```text
PHASE25_A3_CAPITAL_EFFICIENCY_TRACE_COMPLETE_COMPOUND_REINVESTMENT_AMBIGUOUS
```

Compound Reinvestment Judgment:

```text
COMPOUND_REINVESTMENT_AMBIGUOUS
```

## 3. Implemented Scope

Implemented:

- `phase25_capital_efficiency_trace.v1`
- `phase25_capital_efficiency_trace_producer`
- `capital-trace` read-only CLI
- Capital authority trace
- Symbol-level trace
- Opportunity-to-Planning trace
- Binding constraint evidence-only classification
- Compound reinvestment layered trace
- 2024-01-18 diagnostic materialization
- Unit and CLI validation
- Deterministic materialization check

Not implemented:

- Strategy improvement
- Runtime behavior changes
- Cash Attribution Waterfall
- Benchmark implementation
- Run-level Performance Summary
- Experiment Comparison
- Fixed 1,000,000 JPY or 850,000 JPY cap removal

## 4. Read-only Producer

Producer:

```text
phase25_capital_efficiency_trace_producer
```

Module:

```text
src/ai_fund_lab_v2/runtime_v2/performance_evaluation/capital_trace.py
```

CLI:

```text
PYTHONPATH=src python3 scripts/runtime_test.py capital-trace --run-id <RUN_ID> --business-date YYYY-MM-DD --json
```

The producer reads existing Runtime Test evidence and writes only:

```text
reports/performance_evaluations/<RUN_ID>/daily/<BUSINESS_DATE>/capital_efficiency_trace.json
```

## 5. Artifact and Schema

Artifact:

```text
phase25_capital_efficiency_trace
```

Schema version:

```text
phase25_capital_efficiency_trace.v1
```

Schema:

```text
schemas/runtime_test/capital_efficiency_trace.schema.json
```

Required blocks:

- `daily_summary`
- `capital_authority_trace`
- `symbol_traces`
- `opportunity_pipeline`
- `compound_reinvestment`
- `authority_conflicts`
- `missing_fields`
- `warnings`
- `source_artifact_refs`
- `temporal_safety`

## 6. Capital Authority Trace

Trace chain:

```text
Current Total Equity
  -> Portfolio Policy
  -> Capital Deployment
  -> Position Sizing
  -> Runtime Planning
  -> Submit
  -> Execution
```

For 2024-01-18:

| Field | Value |
|---|---:|
| initial_capital | 1,000,000 |
| runtime_evaluation_capital | 1,000,000 |
| current_total_equity | 1,067,660 |
| current_cash | 388,010 |
| current_market_value | 679,650 |
| position_sizing_capital_base | 1,067,660 |
| capital_deployment_evaluation_capital | 1,000,000 |
| capital_deployment_max_exposure | 850,000 |

## 7. Symbol-level Trace

Symbol trace is limited to generated opportunity/planning symbols when Runtime Planning evidence is present.

For 2024-01-18, six opportunities were traced:

| Symbol | Pipeline Status | Primary Binding Constraint |
|---|---|---|
| 67310 | `REJECTED` | `MIN_NOTIONAL` |
| 76470 | `REJECTED` | `PLANNING_POLICY` |
| 89180 | `REJECTED` | `PLANNING_POLICY` |
| 91070 | `REJECTED` | `MIN_NOTIONAL` |
| 94320 | `REJECTED` | `PLANNING_POLICY` |
| 95010 | `REJECTED` | `PLANNING_POLICY` |

These classifications are based on explicit planning/sizing evidence such as `NO_ORDER_MINIMUM_NOTIONAL_UNMET`, `no_action_strategy_intent`, and current-position zero-delta reasons.

## 8. Opportunity-to-Planning Trace

2024-01-18 pipeline:

| Stage | Count |
|---|---:|
| Generated Opportunity | 6 |
| Eligible Opportunity | 6 |
| Sized Opportunity | 6 |
| Planned BUY | 0 |
| Submitted BUY | 0 |
| Executed BUY | 0 |

Interpretation:

- Opportunities existed and eligibility was available.
- They reached Position Sizing.
- None became planned BUY.
- The trace records the evidence stage; it does not change Strategy behavior.

## 9. Binding Constraint Contract

Implemented candidates:

- `MIN_NOTIONAL`
- `PLANNING_POLICY`
- `SAFETY`
- `POSITION_COUNT`
- `LOT_SIZE`
- `REFERENCE_PRICE`
- `UNKNOWN`

Rules:

- Primary binding is set only from explicit evidence text.
- If a reason is not observable, binding constraint is `UNKNOWN` with `NOT_OBSERVABLE`.
- Multiple constraints are separated as primary and secondary.

## 10. Compound Reinvestment Trace

Layer 1: Sizing Base

- Position Sizing used `portfolio_total_equity = 1,067,660`.
- Current total equity was also `1,067,660`.

Layer 2: Downstream Cap

- Fixed `capital_deployment_evaluation_capital = 1,000,000` is present.
- Fixed `capital_deployment_max_exposure = 850,000` is present.
- Current market value `679,650` is below max exposure, so current-day max exposure binding is not observed.
- Aggregate feasibility and submit capital limit remain `NOT_OBSERVABLE`.

Layer 3: Actual Deployment

- Planned BUY notional: `0`
- Submitted BUY notional: `NOT_OBSERVABLE`
- Executed BUY notional: `0`

## 11. Compound Reinvestment Judgment

Judgment:

```text
COMPOUND_REINVESTMENT_AMBIGUOUS
```

Reasons:

- Position Sizing uses current total equity.
- No post-profit BUY or ADD execution sample exists on 2024-01-18.
- Submit and aggregate feasibility capital limits are not fully observable.
- Fixed capital policy is present, even though current-day max exposure binding is not observed.

Therefore confirmation is prohibited by contract.

## 12. 2024-01-18 Diagnostic

Sample artifact:

```text
reports/performance_evaluations/runtime-test-historical-extended-smoke-20260802T113114833349Z/daily/2024-01-18/capital_efficiency_trace.json
```

Diagnostic result:

```text
Generated Opportunity = 6
Eligible Opportunity = 6
Sized Opportunity = 6
Planned BUY = 0
Submitted BUY = 0
Executed BUY = 0
```

Confirmed on this date:

- `runtime_evaluation_capital` remained 1,000,000.
- `current_total_equity` was 1,067,660.
- `position_sizing_capital_base` matched current total equity.
- Fixed capital deployment config was present.
- Compound reinvestment could not be confirmed from this single no-BUY day.

## 13. Authority Conflicts

Confirmed conflicts:

| Conflict | Evidence |
|---|---|
| `runtime_evaluation_capital_vs_current_total_equity` | 1,000,000 vs 1,067,660 |
| `position_sizing_capital_base_vs_runtime_evaluation_capital` | 1,067,660 vs 1,000,000 |

These are reported as authority conflicts, not automatically treated as Runtime defects in this task.

## 14. Blocking Gaps

No blocking gap remains for A3 implementation acceptance.

## 15. Non-Blocking Gaps

- Aggregate feasibility limit remains `NOT_OBSERVABLE`.
- Submit capital limit remains `NOT_OBSERVABLE`.
- Submitted BUY notional remains `NOT_OBSERVABLE` when no side-specific submitted order notional exists.
- Compound reinvestment requires at least one post-profit BUY or ADD sample.
- Cash Attribution Waterfall is deferred to Phase25-A4.

## 16. Required User Evidence

To resolve Compound Reinvestment from `AMBIGUOUS`, provide or run evidence containing:

- A post-profit BUY or ADD date.
- Position Sizing artifact for that date.
- Runtime Planning artifact for that date.
- Submit authority and submitted order evidence for that date.
- Execution fills for that date.
- Current valuation evidence before and after the action.

## 17. Required User-Run Tests

Codex did not run long Historical Runtime tests.

Recommended user/operator runs:

- Existing 2024 run materialization across all completed days.
- A short run containing at least one post-profit BUY or ADD.
- Later 20BD/60BD/200BD/252BD runs only after A4/A5 materialization is ready.

## 18. Recommended Next Task

Because an authority conflict is now explicitly confirmed, do not jump directly to Runtime fixes.

Recommended next task:

```text
Capital Authority Conflict Review
```

If the user wants to continue the Phase25-A evidence build first:

```text
Phase25-A4 Cash Ratio Attribution Materialization
```

## 19. Validation

Validation performed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m compileall scripts/runtime_test.py src/ai_fund_lab_v2/runtime_v2/performance_evaluation
```

Result: PASS

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase25_a3_capital_efficiency_trace.py
```

Result:

```text
3 passed
```

```text
python3 -m json.tool schemas/runtime_test/capital_efficiency_trace.schema.json
```

Result: PASS

```text
PYTHONPATH=src python3 scripts/runtime_test.py capital-trace --run-id runtime-test-historical-extended-smoke-20260802T113114833349Z --profile historical-extended-smoke --business-date 2024-01-18 --json
```

Result: PASS

Determinism:

```text
54eacaad49f33b375af1e2e4effd04dcd85880e19a2f33334d1a3cbf8438b506
```

The hash remained stable after rerun.
