# Phase32-CI — Post-CH Day-0 Two-Buy Collapse Exact Trace

## Executive Summary

Post-CH Day-0 collapse is confirmed.

On `2022-10-03`, Pre-CH/Post-CC produced 8 BF targets, 7 submitted/fillable BUY_NEW fills, and 53.279% security allocation. Post-CH produced 2 BF targets, 2 BUY_NEW fills, and 4.922% security allocation. Cash residual rose from 20.721% to 69.078%.

The collapse is upstream of Runtime/Execution. Runtime/submit consumed only the BF/PS outputs it received:

- Pre-CH submitted orders: 7
- Post-CH submitted orders: 2
- Post-CH fills: `94340` +200, `37820` +300

CH did not mark `REDUCED_ALLOCATION_ONLY` as production-deployable false. The Post-CH rows inspected all had `candidate_eligible=true` and `production_deployable_new=true`.

However, CH caused a material lot-minimum collapse by making quality-authorized target magnitude binding before BF:

- Expensive one-lot symbols where one trading lot exceeds the reduced quality target are now blocked at CC/BF as `INFEASIBLE_LOT: lot_minimum_exceeds_quality_authorized_target`.
- Cheap multi-lot symbols `89180` and `76470` are zeroed before BF by PC lot-aware final reallocation with `minimum_lot_exceeds_remaining_budget`, even though their quality-authorized target would support many smaller lots. This is a PC lot-aware ordering/budget interaction exposed by CH and looks like the primary unintended collapse mechanism.

## Run Identity

| Role | Run ID | Local artifact status |
| --- | --- | --- |
| Post-CH | `runtime-test-historical-extended-smoke-20260829T040121420255Z` | Available |
| Pre-CH/Post-CC | `runtime-test-historical-extended-smoke-20260829T021541366158Z` | Available |
| CG old baseline | `runtime-test-historical-extended-smoke-20260828T000823285458Z` | Not present under `reports/runtime_tests/runs` locally |

CG old baseline evidence is therefore referenced from `phase32_cg_pre_phase32_vs_current_final_investment_decision_semantic_delta_audit.md`. Per CG, old baseline Day-0 also had 7 BUY fills and the same core OLD/CURRENT re-expansion defect for reduced Buy Quality targets.

## Day-0 Aggregate Comparison

| Metric | Pre-CH/Post-CC | Post-CH |
| --- | ---: | ---: |
| Authority accepted incremental targets | 59 lots | 5 lots |
| BF aggregated PS targets | 8 symbols | 2 symbols |
| Submitted order count | 7 | 2 |
| Actual fills | 7 | 2 |
| Security allocation weight | 53.279% | 4.922% |
| Authorized Cash allocation weight | 20.721% | 69.078% |

## Symbol Trace

| Symbol | Pre-CH fill | Post-CH fill | Post-CH base target | Post-CH quality target | Post-CH production deployable | First zero/block boundary |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| 94340 | 200 | 200 | 3.3636% | 3.3636% | true | Filled; no effective quality reduction |
| 37820 | 400 | 300 | 3.3636% | 2.4103% | true | Quality-bounded CC expansion: 400 -> 300 |
| 33700 | 100 | 0 | 3.3636% | 2.1670% | true | CC `INFEASIBLE_LOT`, one lot = 3.4100% > quality target |
| 83060 | 100 | 0 | 3.3636% | 2.0607% | true | CC `INFEASIBLE_LOT`, one lot = 6.4800% > quality target |
| 92420 | 100 | 0 | 3.3636% | 2.0691% | true | CC `INFEASIBLE_LOT`, one lot = 13.7500% > quality target |
| 58200 | 100 | 0 | 3.3636% | 2.0120% | true | CC `INFEASIBLE_LOT`, one lot = 17.4670% > quality target |
| 89180 | 3700 | 0 | 3.3636% | 1.9686% | true | PC lot-aware final reallocation zero: `minimum_lot_exceeds_remaining_budget` |
| 76470 | 0 fill, 1200 BF/PS target | 0 | 3.3636% | 1.9385% | true | PC lot-aware final reallocation zero: `minimum_lot_exceeds_remaining_budget` |

## Exact Boundary Findings

### 94340

`94340` is a control. It carries `REDUCED_ALLOCATION_ONLY`, but the Buy Quality adjustment is effectively 1.0.

Post-CH:

- `target_weight=0.033636`
- `pre_quality_base_target_weight=0.033636`
- `quality_authorized_target_weight=0.033636`
- CC lots: 2
- BF quantity: 200
- PS quantity: 200
- Fill: 200

Conclusion: FULL-equivalent behavior is non-regressed for this symbol.

### 37820

`37820` demonstrates intended CH behavior.

Pre-CH:

- PC final target remained 3.3636%
- BF quantity: 400
- Fill: 400

Post-CH:

- base target: 3.3636%
- quality target: 2.4103%
- CC executable target quantity: 300
- BF quantity: 300
- Fill: 300

Conclusion: 400 -> 300 is the intended quality ceiling effect.

### 33700 / 83060 / 92420 / 58200

These are expensive one-lot rows. Post-CH keeps them candidate-eligible and production-deployable, but one trading lot exceeds the Buy Quality-authorized reduced target.

Observed Post-CH blocker:

```text
authority_disposition = INFEASIBLE_LOT
constraints.reason_codes = [lot_minimum_exceeds_quality_authorized_target]
```

This is directly caused by CH making the quality ceiling binding and disallowing implicit one-lot rescue.

Semantic interpretation:

- Correct relative to CH hard contract.
- Materially broad in Day-0 production effect.
- Needs policy/design decision if the intended production semantics should allow an explicit PIT one-lot exception for reduced-but-deployable candidates.

### 89180 / 76470

These are low-priced multi-lot candidates where quality target should still allow many lots.

Post-CH:

- `89180`: quality target 1.9686%, but PC target becomes 0 before BF.
- `76470`: quality target 1.9385%, but PC target becomes 0 before BF.
- first boundary: PC lot-aware final reallocation
- reason: `minimum_lot_exceeds_remaining_budget`
- BF then sees zero PC production target and blocks via `INELIGIBLE_PC_PRODUCTION_ADMISSION_BLOCKED`.

This does not look like the intended CH semantic. These rows are not below one-lot in quality target terms; they are zeroed by the legacy PC lot-aware ordering/budget path before the BF quality-bounded multi-lot expansion can capitalize the reduced target.

## Cash Causality

Cash is an outcome, not the primary blocker.

Post-CH Cash allocation is high because security candidates disappeared or were zeroed before/at BF:

- Security allocation: 4.922%
- Cash allocation: 69.078%
- Cash reason: `remaining_budget_allocated_to_cash_optionality`

No evidence showed Cash beating valid security lots directly as the first boundary for the disappeared symbols.

## OLD Baseline Note

The local CG old baseline run directory is absent. From `phase32_cg_pre_phase32_vs_current_final_investment_decision_semantic_delta_audit.md`:

- OLD Day-0 BUY fills: 7
- CURRENT/Pre-CH Day-0 BUY fills: 7
- OLD and CURRENT both preserved the reduced Buy Quality re-expansion defect.
- 89180 Day-0 re-expanded from 1.9686% quality target back to 3.3636% final target and 3,700 shares.
- 94340 Day-0 had no effective quality reduction.

Thus Post-CH is the first observed actual path where the Buy Quality ceiling is binding, and it exposes the lot-minimum collapse.

## Defect Judgment

CH's core target ceiling repair is semantically active. It correctly prevents reduced targets from re-expanding to base target magnitude.

But actual Day-0 behavior is too broad for production readiness:

1. Expensive reduced candidates are eliminated when one lot exceeds the quality target.
2. Low-priced reduced multi-lot candidates can be zeroed by PC lot-aware final reallocation before BF, despite having deployable quality-authorized target magnitude.
3. The PC artifact still shows some reduced candidates re-expanded to one-lot target weights before BF blocks them, meaning the preservation is not consistently enforced at every PC sub-boundary even though BF prevents PS consumption.

The safest next repair is narrow and semantic:

- preserve CH ceiling,
- keep no implicit one-lot rescue unless an explicit PIT authority is designed,
- prevent PC lot-aware final reallocation from zeroing quality-deployable NEW/REENTRY before BF can apply quality-bounded multi-lot competition,
- ensure `final_deployable_target_weight <= quality_authorized_target_weight` remains true after lot-aware final reallocation, not only at BF.

## Final Judgments

PHASE32_CI_PRE_CH_DAY0_BUY_COUNT = 7 fills, 8 BF/PS targets

PHASE32_CI_POST_CH_DAY0_BUY_COUNT = 2

PHASE32_CI_DISAPPEARED_SYMBOLS = 33700, 83060, 92420, 58200, 89180; additionally 76470 disappeared from BF/PS target set though it had no Pre-CH fill

PHASE32_CI_PRIMARY_ZERO_BOUNDARY = Mixed: CC/BF `lot_minimum_exceeds_quality_authorized_target` for expensive one-lot reduced candidates; PC lot-aware final reallocation `minimum_lot_exceeds_remaining_budget` for 89180/76470

PHASE32_CI_QUALITY_REDUCTION_BEHAVIOR_CORRECT = PARTIAL

PHASE32_CI_LOT_MINIMUM_ZERO_COLLAPSE = YES

PHASE32_CI_DEPLOYABILITY_REGRESSION = NO

PHASE32_CI_CASH_WIN_CAUSAL = NO

PHASE32_CI_CH_NARROW_REPAIR_REQUIRED = YES

PHASE32_CI_LONGER_VALIDATION_READY = NO

PHASE32_CI_NEXT_STEP = Narrow repair of the PC lot-aware / BF entry-boundary interaction so quality-authorized NEW/REENTRY targets are not zeroed before common-frontier multi-lot competition, while preserving the CH quality ceiling and requiring explicit PIT authority for any below-one-lot reduced candidate exception.
