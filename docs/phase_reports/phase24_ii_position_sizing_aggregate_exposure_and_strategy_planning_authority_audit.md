# Phase24-II Position Sizing Aggregate Exposure and Strategy Planning Authority Audit

## 1. Primary Judgment

`PHASE24_II_POSITION_SIZING_AGGREGATE_EXPOSURE_PRECISION_REPAIRED_SHORT_VALIDATION_PASS_OPERATOR_RESUME_REQUIRED`

## 2. Scope

対象Runは `runtime-test-historical-extended-smoke-20260801T223117629647Z`、Business Dateは `2023-06-14`。

Phase24-IHで対象だったHistorical Safety Authority問題は解消済みであり、本Taskでは主原因として扱わない。Runtime resume、長時間Historical Runtime Test、Broker接続、Submit、外部配送は実行していない。

## 3. Reviewed Evidence

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260801T223117629647Z/daily/2023-06-14/morning/runtime_manifest.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260801T223117629647Z/daily/2023-06-14/strategy/portfolio_construction.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260801T223117629647Z/daily/2023-06-14/strategy/position_sizing.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260801T223117629647Z/daily/2023-06-14/strategy/runtime_planning.json`
- `.runtime/pending_order_plan/pending_order_plan.json`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `src/ai_fund_lab_v2/strategy/runtime_planning.py`
- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- Phase24-IF / IH reports

## 4. Direct Runtime Evidence

Morning Runtime:

- `final_state = REVIEW_REQUIRED`
- `reason = morning pipeline review required: strategy_planning_authority_unresolved`
- `safety_status = PASS`
- `final_safety_status = READY`
- `historical_neutral_authority_generated_or_resolved = true`

Portfolio Construction:

- `producer_result_status = PASS`
- `reason_codes = duplicate_existing_candidate_reconciled:76470, duplicate_existing_candidate_reconciled:94320`
- `target_gross_exposure = 0.79`
- `resolved_target_member_count = 6`
- `total_target_weight = 0.790002`
- `target_weight_sum_tolerance = 0.000003`

Position Sizing before repair:

- `schema_version = position_sizing_shadow_error.v1`
- `producer_result_status = BLOCK`
- `error = aggregate_target_weight_above_exposure_cap`
- `reason_codes = ["strategy_shadow_generation_error"]`

## 5. Numeric Evidence

Selected target weights:

| Symbol | Target Weight |
|---|---:|
| 21340 | 0.131667 |
| 59550 | 0.131667 |
| 67310 | 0.131667 |
| 99840 | 0.131667 |
| 37820 | 0.131667 |
| 40520 | 0.131667 |

Calculation:

- Aggregate target weight: `0.790002`
- Exposure cap: `0.79`
- Difference: `0.000002`
- Rounding precision: `6`
- Correct tolerance: `max(0.000001, selected_count * 0.000001 / 2)`
- With selected count 6: `0.000003`

Classification:

`ROUNDING_ONLY_OVERFLOW`

This is not a real policy overflow. A genuine overflow such as `0.791000 > 0.79 + 0.000003` remains blocked.

## 6. Phase24-IF Consistency

Phase24-IF repaired Portfolio Construction to accept six-decimal serialized target-weight sums using selected-member-count-scaled tolerance. Position Sizing still used fixed `0.000001` in both producer comparison and schema validation.

Before repair:

- Portfolio Construction: PASS
- Position Sizing: BLOCK

After repair:

- Both use shared `target_weight_sum_tolerance`.
- Policy cap is unchanged.
- Real overflow still fails closed.

## 7. Quantity Authority Classification

Before repair, Runtime Planning emitted independent-looking Quantity Authority reviews for:

- `21340`
- `37820`
- `40520`
- `59550`
- `67310`
- `99840`

Because Position Sizing had BLOCKed and did not produce quantity rows, this was downstream overstatement rather than independent quantity authority defect.

Classification:

`OVERSTATED_DOWNSTREAM_REVIEW`

Repair:

- Runtime Planning now treats Position Sizing `producer_result_status=BLOCK` as upstream block propagation.
- It emits `quantity_not_produced_due_to_upstream_block` rather than `review_required_quantity_authority:<symbol>`.
- Non-submittable state is preserved.

## 8. Existing Position Classification

Existing position symbols:

- `76470`
- `94320`

Portfolio Construction reconciled duplicated candidate/current membership into one membership each, with:

- `membership_intent = UNRESOLVED`
- `target_weight = 0.0`
- `reason_codes = candidate_duplicate_reconciled:<symbol>, pm_action:UNRESOLVED`

Runtime Planning classified these as:

- `planning_intent = UNRESOLVED`
- `order_side_intent = UNRESOLVED`
- `reason = unresolved_mapping:portfolio_membership_unresolved`

This remains fail-closed and was not changed. No automatic HOLD, ADD, or NO_PLAN mapping was introduced.

## 9. Root Cause

Primary Root Cause:

`position_sizing_aggregate_target_weight_precision_contract_mismatch_with_portfolio_construction`

Secondary Root Cause:

`runtime_planning_classified_position_sizing_block_quantity_absence_as_independent_quantity_authority_review`

## 10. Repair Summary

Implemented:

- Added `src/ai_fund_lab_v2/strategy/target_weight_precision.py`.
- Portfolio Construction now uses shared target-weight precision helper.
- Position Sizing producer and schema validation use the shared tolerance.
- Strategy Shadow validation uses the same tolerance.
- Runtime Planning treats Position Sizing BLOCK as upstream block propagation.

Not changed:

- Strategy logic
- Ranking
- Eligibility
- PM decision logic
- Position Sizing policy
- Target gross exposure
- Cash reserve
- Safety Guard
- Submit Guard

## 11. Regression

Executed:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/phase24_ii_pycache PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_g_runtime_planning.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py tests/runtime_v2/test_phase17_bj_historical_daily_neutral_safety_authority.py tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py
```

Result:

- `123 passed`

Compile:

- PASS

Runtime executed:

- `NO`

## 12. Recommended Next Task

Operator resume:

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src

python3 scripts/runtime_test.py resume \
  --run-id runtime-test-historical-extended-smoke-20260801T223117629647Z \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```
