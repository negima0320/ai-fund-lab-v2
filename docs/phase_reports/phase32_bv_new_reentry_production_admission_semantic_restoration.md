# Phase32-BV — NEW/REENTRY Production Admission Semantic Restoration

## Executive Summary

Phase32-BV narrowly repaired the Phase32-BU NEW allocation semantic drift.

The defect was that BG/BF common frontier activation allowed `NEW_FIRST_LOT`
rows with legacy PC `target_weight = 0` to become BF/PS-consumable targets. The
repair restores the existing PC-owned production admission boundary for
`NEW_FIRST_LOT` and `REENTRY_FIRST_LOT` while preserving ADD next-lot common
frontier behavior.

The implementation keeps zero-target first-lot rows visible as frontier
candidates for explainability, but marks them non-deployable before authority
acceptance:

```text
INELIGIBLE_PC_PRODUCTION_ADMISSION_BLOCKED
```

No rank threshold, quality threshold, marginal value weight, Cash, allocation
budget, PM, PS arithmetic, Runtime, REDUCE, EXIT, Safety, or Risk Pacing logic
was tuned.

## Required Inputs

Read:

- `docs/phase_reports/phase32_bu_post_bt_new_allocation_semantic_drift_audit.md`
- `docs/phase_reports/phase32_bt_marginal_frontier_effective_concentration_cap_narrow_repair.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/strategy_architecture_v1.md`

Relevant SoT principle:

```text
eligible candidate but target_weight = 0 is a valid Portfolio Construction
outcome; Position Sizing must not reinterpret rank/score/candidate status into
deployment.
```

## Changed Files

```text
src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py
tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py
tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py
docs/02_architecture/portfolio_construction_and_position_sizing_contract.md
docs/phase_reports/phase32_bv_new_reentry_production_admission_semantic_restoration.md
```

## Repair Boundary

The narrow implementation is inside:

```text
common_marginal_capital_frontier_shadow._production_first_lot_admission()
common_marginal_capital_frontier_shadow._constraints()
common_marginal_capital_frontier_shadow._blocked_disposition()
```

For `NEW_FIRST_LOT` and `REENTRY_FIRST_LOT`, production admission now requires:

```text
target_weight > 0
membership_intent not in EXCLUDE / AVOID / NOT_SELECTED / INELIGIBLE
target_weight_resolution.status is PASS or absent/not-applicable
```

If this evidence is missing, the first-lot row fails closed as
`REVIEW_REQUIRED`. If PC explicitly produced a non-deployable zero target, the
row is blocked and cannot become an accepted target.

ADD remains outside this first-lot admission gate:

```text
ADD_NEXT_LOT -> add_next_lot_not_gated_by_new_first_lot_admission
```

ADD is still controlled by campaign identity, ADD evidence, no-loss-averaging,
Cash/budget, effective Strategy/Safety cap, Risk Pacing, and common capital
competition.

## 2022-10-03 Semantic Reproduction

Input artifacts:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T223340854231Z/daily/2022-10-03/strategy/portfolio_construction.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T223340854231Z/daily/2022-10-03/strategy/position_sizing_preflight.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T223340854231Z/daily/2022-10-03/strategy/marginal_capital_frontier_authority.json
```

Non-fresh in-memory rebuild after BV:

| Metric | Value |
| --- | ---: |
| Authority status | `PASS` |
| Accepted target count | 8 |
| Accepted target type | `NEW_FIRST_LOT` |
| BF boundary status | `PASS` |
| BF aggregated target count | 8 |
| Active switch status in reproduction | `PASS` |
| Legacy zero-target NEW promoted | 0 |

Accepted symbols:

```text
33700, 37820, 58200, 76470, 83060, 89180, 92420, 94340
```

Blocked Phase32-BU zero-promotion examples:

| Symbol | Legacy PC Target | BV Disposition | Admission Reason |
| --- | ---: | --- | --- |
| 41920 | 0.000000 | `INELIGIBLE_PC_PRODUCTION_ADMISSION_BLOCKED` | `pc_first_lot_target_weight_zero`, `pc_first_lot_zero_weight_reason_minimum_lot_exceeds_remaining_budget` |
| 45750 | 0.000000 | `INELIGIBLE_PC_PRODUCTION_ADMISSION_BLOCKED` | `pc_first_lot_target_weight_zero`, `pc_first_lot_zero_weight_reason_minimum_lot_exceeds_remaining_budget` |
| 33500 | 0.000000 | `INELIGIBLE_PC_PRODUCTION_ADMISSION_BLOCKED` | `pc_first_lot_target_weight_zero`, `pc_first_lot_zero_weight_reason_minimum_lot_exceeds_remaining_budget` |
| 67860 | 0.000000 | `INELIGIBLE_PC_PRODUCTION_ADMISSION_BLOCKED` | `pc_first_lot_target_weight_zero`, `pc_first_lot_zero_weight_reason_minimum_lot_exceeds_remaining_budget` |
| 82540 | 0.000000 | `INELIGIBLE_PC_PRODUCTION_ADMISSION_BLOCKED` | `pc_first_lot_target_weight_zero`, `pc_first_lot_zero_weight_reason_minimum_lot_exceeds_remaining_budget` |

Positive PC-admitted NEW rows still compete in the frontier. For example,
`83060`, `37820`, and `94340` are accepted with
`pc_first_lot_positive_target_weight_admitted`. `93600` is PC-admitted but
blocked by effective cap, which preserves the BT guardrail rather than the
BU zero-promotion defect.

## Regression Coverage

Added focused coverage:

- legacy PC `target_weight = 0` NEW is not PS-consumable;
- positive PC-admitted NEW can compete and become a BF target;
- REENTRY requires the same PC production admission;
- ADD multi-lot does not depend on NEW/REENTRY first-lot admission;
- saved Post-BT `2022-10-03` reproduction blocks zero-weight NEW promotion;
- BG/BL/BO tests now use positive first-lot PC targets where they test switched
  NEW/REENTRY consumption, while preserving legacy fallback-disabled assertions.

Verification:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py \
  tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py \
  tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py

55 passed
```

Adjacent regression:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py \
  tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py \
  tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py \
  tests/strategy/test_phase32_au_shadow_frontier_cash_source_resolver.py \
  tests/strategy/test_phase22_j_position_sizing.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py

209 passed
```

Compile check:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py \
  src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py \
  tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py \
  tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py \
  tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py

PASS
```

## Scope Preservation

Preserved:

- ADD next-lot common frontier;
- multi-lot ADD quantity progression;
- BT effective Strategy/Safety cap propagation;
- Cash and budget conservation;
- Cash first-class competition;
- no legacy fallback for switched rows;
- PIT flags and submit-feasibility provenance;
- PM, PS quantity arithmetic, Runtime, Pending, Orders, Execution, REDUCE,
  EXIT, Safety, and Risk Pacing behavior outside the target source boundary.

Not used:

- historical outcome / PnL;
- fill-count matching;
- fixed position count;
- rank/quality threshold tuning;
- marginal value weight tuning.

## Final Judgments

PHASE32_BV_NEW_ADMISSION_RESTORED = YES

PHASE32_BV_REENTRY_ADMISSION_RESTORED = YES

PHASE32_BV_LEGACY_ZERO_NEW_PROMOTION_BLOCKED = YES

PHASE32_BV_ADD_COMMON_FRONTIER_PRESERVED = YES

PHASE32_BV_MULTI_LOT_ADD_PRESERVED = YES

PHASE32_BV_CAPITAL_COMPETITION_PRESERVED = YES

PHASE32_BV_DAY0_NEW_SEMANTIC_DRIFT_REPAIRED = YES

PHASE32_BV_REGRESSION_STATUS = PASS

PHASE32_BV_FRESH_VALIDATION_READY = YES

PHASE32_BV_NEXT_STEP = User-operated short fresh validation from 2022-10-03 to confirm active BG/BV artifacts produce no legacy-zero NEW/REENTRY promotions while preserving ADD multi-lot authority and BT cap behavior on the actual runtime path.
