# Phase23-BK Post-execution Strategy Shadow Current-position Mapping Repair

## Primary Judgment

```text
PHASE23_BK_POST_EXECUTION_CURRENT_POSITION_MAPPING_SHORT_VALIDATION_PASS
```

## Root Cause

Target run `runtime-test-historical-smoke-20260730T073848376953Z` technically completed `2026-07-06`, and Fill / Position / Cash / Ledger / Runtime State Refresh were valid. Close became `REVIEW_REQUIRED` because post-execution Strategy Shadow Runtime Planning emitted `unresolved_mapping:portfolio_membership_unresolved` for the seven just-filled Runtime-owned positions.

The information was not lost in Fill, Position State, Ledger, or Runtime State Refresh. The loss occurred at Runtime Planning membership resolution: Portfolio Construction and Position Management saw the same-day current positions but left post-exec PM action / portfolio membership as `UNRESOLVED`; Runtime Planning had no Production-common branch that used Runtime-owned current-position lineage as the close-time membership authority for zero-delta positions.

## Repair

`src/ai_fund_lab_v2/strategy/runtime_planning.py` now materializes a `current_position_membership_authority` per current position. Runtime-owned, same-business-date, PIT-safe current positions resolve to `CURRENT_PORTFOLIO_MEMBER` or `NEWLY_FILLED_PORTFOLIO_MEMBER`. For the close-time zero-delta case, this maps to `NO_ACTION`, `order_side_intent=NONE`, `pending_eligibility=NOT_REQUIRED`, `quantity_required=false`, and `planned_quantity=0`.

Invalid authority remains fail-closed: missing ownership authority, external/non-runtime source, business/as-of mismatch, future valuation/source date, or fill quantity mismatch keeps the plan `UNRESOLVED` / `REVIEW_REQUIRED`.

## Contract Confirmation

Canonical post-exec membership source is Runtime-owned current-position lineage, not a broker snapshot, latest fallback, or a Historical-specific branch. Strategy Shadow remains read-only and does not write Pending, Submit, Broker, Ledger, or existing Run artifacts.

For the seven symbols `31330, 45640, 45960, 66340, 67400, 89180, 94320`, isolated read-only reproduction resolves all rows to `NEWLY_FILLED_PORTFOLIO_MEMBER`, with `unresolved_count=0`, `pending_eligibility REVIEW_REQUIRED count=0`, and no generated order quantity.

## Evidence

Evidence directory:

```text
reports/phase23_bk_post_execution_strategy_shadow_current_position_mapping_repair/
```

Key files include `root_cause.json`, `fill_position_lineage_trace.json`, `runtime_planning_membership_trace.json`, `canonical_post_execution_reproduction.json`, `negative_fail_closed_cases.json`, `existing_run_hash_preservation.json`, and `test_results.json`.

## Short Validation

```text
py_compile PASS
pytest tests/strategy/test_phase22_g_runtime_planning.py -q PASS (22 passed)
isolated BK reproduction PASS
JSON validation PASS
```

Long runtime, fresh-run, 1BD, 10BD, Broker Write, Runtime Switch, and J-Quants fetch were not executed.

## Next Operator Action

`READY_FOR_1BD_RUNTIME_RERUN = YES` for operator-side validation after Evidence Review. `READY_FOR_10BD = NO` until the 1BD rerun evidence is reviewed.
