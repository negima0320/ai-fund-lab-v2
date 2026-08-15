# Phase29-L21O — PC Candidate 548 to 72 Exhaustive Zero Allocation Reconciliation Audit

Task ID: `Phase29-L21O`  
Target run: `runtime-test-historical-smoke-20260811T152905733571Z`  
Mode: read-only audit. No implementation, configuration, threshold, model, schema, accepted-generation, runtime, pending, resume, abort, repair, fresh run, or historical-run mutation was performed.

## Executive Summary

The 548 PC candidate baseline is fully reconciled. The reproduced definition is `portfolio_members` with `membership_intent = ADD_CANDIDATE` through the fixed L21M/L21N baseline ending `2023-08-18`. This yields exactly:

- Total PC candidates: 548.
- Positive allocation: 72.
- Zero allocation: 476.
- Unexplained: 0.

The dominant zero reason is not cash, gross exposure, or Buy Quality. It is PC re-entry policy: 309 / 476 zero candidates are `semantic_buy_type = REENTRY` and are blocked before final target membership by `semantic_reentry_recovery_hurdle_not_satisfied`. Of those, 193 are `reentry_corporate_action_status_missing` and 116 are `reentry_expected_edge_below_threshold`.

The second largest group is lot/Safety expression: 153 / 476 are official minimum-policy-lot Safety hard cap blocks. These are the ADD_CANDIDATE subset of the L21M/L21N lot problem. A one-round-lot lens finds 25 zero candidates with pre-lot target >0, BQ non-reject, broker valid, cash available, gross headroom, and Safety-contained one-lot feasibility. Those are the actionable architecture-gap candidates.

Primary judgment:

`PHASE29_L21O_PC_ZERO_ALLOCATION_FULLY_EXPLAINED_REENTRY_POLICY_DOMINANT_WITH_ACTIONABLE_ONE_LOT_EXPRESSION_GAP`

## Baseline

Audited sources:

- `docs/01_requirements/phase_roadmap.md`
- `docs/phase_reports/phase29_l21l_capital_utilization_root_cause_audit.md`
- `docs/phase_reports/phase29_l21m_portfolio_construction_lot_concentration_root_cause_audit.md`
- `docs/phase_reports/phase29_l21n_minimum_meaningful_notional_policy_necessity_and_removal_impact_audit.md`
- `docs/phase_reports/phase29_l21e_buy_add_overshoot_authorized_quantity_zero_root_cause_audit.md`
- `docs/phase_reports/phase29_l21f_buy_add_soft_cap_position_sizing_integration_repair.md`
- `docs/phase_reports/phase29_l21g_buy_new_funnel_regression_and_capital_deployment_audit.md`
- `docs/phase_reports/phase29_l21h_opportunity_buy_quality_semantics_entry_supply_root_cause_audit.md`
- `docs/phase_reports/phase29_l21i_opportunity_score_semantic_contract_repair.md`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T152905733571Z/daily/*/strategy/portfolio_construction.json`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T152905733571Z/daily/*/strategy/position_sizing.json`

PC Candidate Funnel:

| Stage | Count |
|---|---:|
| Total PC candidates | 548 |
| Positive allocation | 72 |
| Zero allocation | 476 |

Important definition note: the reproduced 548 are `membership_intent = ADD_CANDIDATE`. They are semantic `BUY_NEW` or `REENTRY`; existing-position `RETAIN / ADD` rows are not part of this 548 baseline.

## 548 Candidate Master Reconciliation

Candidate-level fields were reconciled from PC member rows and same-day Position Sizing/lot evidence:

- `business_date`, `symbol`, `semantic_buy_type`, opportunity rank/score, BQ action.
- PC membership, current position status, current/final/pre-lot target weights.
- one round lot notional/weight, minimum policy lot evidence, Strategy cap, Safety hard cap.
- available cash, current gross exposure, target gross exposure.
- final allocation result and primary zero reason.

All 548 candidates were BQ non-reject:

| BQ action | Positive | Zero |
|---|---:|---:|
| `FULL_ALLOCATION_ELIGIBLE` | 65 | 451 |
| `REDUCED_ALLOCATION_ONLY` | 7 | 25 |

Semantic distribution:

| Semantic | Positive | Zero |
|---|---:|---:|
| `BUY_NEW` | 72 | 167 |
| `REENTRY` | 0 | 309 |

## Positive 72 Control Group

The positive group is entirely `BUY_NEW`, not `REENTRY`.

Positive vs zero comparison:

| Metric | Positive 72 | Zero 476 |
|---|---:|---:|
| Average rank | 4.32 | 4.31 |
| Median rank | 4 | 4 |
| Average final target weight | 15.38% | 0.00% |
| Average pre-lot normal target | 15.21% | 15.02% |
| Average one-lot notional | 44,714 JPY | 503,875 JPY |
| Median one-lot notional | 35,375 JPY | 397,000 JPY |
| Average one-lot weight | 4.68% | 51.76% |

The groups do not meaningfully differ by BQ or rank. The decisive differences are semantic re-entry gating and lot/price expression.

## Zero 476 Primary Reason Breakdown

The 476 zero candidates were assigned to exactly one primary bucket each:

| Primary reason | Count | % | BUY_NEW count | BUY_ADD count | Safety-contained count | Cash-available count | Gross-headroom count |
|---|---:|---:|---:|---:|---:|---:|---:|
| `NO_ELIGIBLE_OPPORTUNITY_AFTER_PORTFOLIO_FIT` | 309 | 64.9% | 309 | 0 | 0 | 0 | 0 |
| `SAFETY_HARD_CAP_BLOCK` | 153 | 32.1% | 153 | 0 | 25 | 89 | 89 |
| `BROKER_INFEASIBLE` | 12 | 2.5% | 12 | 0 | 0 | 0 | 0 |
| `CASH_INSUFFICIENT` | 2 | 0.4% | 2 | 0 | 2 | 2 | 2 |
| `UNEXPLAINED` | 0 | 0.0% | 0 | 0 | 0 | 0 | 0 |
| Total | 476 | 100.0% | 476 | 0 | 27 | 91 | 91 |

Bucket meanings:

- `NO_ELIGIBLE_OPPORTUNITY_AFTER_PORTFOLIO_FIT`: REENTRY candidates with pre-lot normal target but no final target because re-entry recovery hurdle failed.
- `SAFETY_HARD_CAP_BLOCK`: official minimum policy lot exceeds Safety hard cap. This is not necessarily the same as one-round-lot Safety feasibility.
- `BROKER_INFEASIBLE`: PC/lot evidence reports broker/lot infeasible.
- `CASH_INSUFFICIENT`: official required allocation exceeds remaining lot-aware budget.

## Potentially Actionable Zero Allocation

Special filter:

- BQ non-reject.
- PC candidate row present.
- broker valid.
- available cash >= one round lot.
- one round lot within gross exposure headroom.
- one round lot within Safety hard cap.
- no corporate-action quarantine bucket.
- no data/review bucket.
- final allocation zero.

Result:

- Potentially actionable zero allocation: 25.
- All 25 have pre-lot normal target >0 and final PC target 0.
- 23 are official `SAFETY_HARD_CAP_BLOCK` under the minimum-policy-lot interpretation.
- 2 are official `CASH_INSUFFICIENT` under the minimum-policy-lot / remaining-budget interpretation.

These are the L21O-critical candidates: they are not tiny/no-quality/no-cash/no-gross/no-Safety cases under a one-round-lot expression. They remain blocked because the current official expression requires more than the feasible one-lot fallback.

## Competition vs Infeasibility

Zero allocation classification:

| Class | Count | Interpretation |
|---|---:|---|
| A. Lower priority than allocated opportunity | 0 confirmed in the 548 candidate baseline |
| B. Truly infeasible under current official lot/Safety/broker/budget rules | 167 |
| C. Strategy policy zero | 309 |
| D. Materialization / lot expression zero | 25 actionable subset within B |
| E. Unknown | 0 |

For this 548 definition, the large drop is not ordinary competition loss. Positive and zero average rank are almost identical, and zero rows are dominated by REENTRY policy or infeasible lot expression.

## Residual Cash Days

Residual cash remained on all zero-candidate days:

- Zero candidates with residual cash >0 on their day: 476 / 476.
- Zero candidates on days with residual cash >20%: 431 / 476.
- Days with at least one zero candidate: 212.
- Days with at least one zero candidate and residual cash >20%: 185.

High residual examples:

| Date | Zero | Positive | Residual cash weight | Current gross | Target gross | Residual reason | One-lot feasible zero count | Allocated symbols |
|---|---:|---:|---:|---:|---:|---|---:|---|
| 2022-08-22 | 1 | 0 | 80.48% | 19.52% | 100% | `CONCENTRATION_LIMIT` | 0 | none |
| 2023-08-07 | 2 | 0 | 78.97% | 21.03% | 100% | `CONCENTRATION_LIMIT` | 0 | none |
| 2023-08-08 | 3 | 0 | 78.81% | 21.19% | 100% | `CONCENTRATION_LIMIT` | 0 | none |
| 2023-07-31 | 2 | 0 | 78.75% | 21.25% | 100% | `CONCENTRATION_LIMIT` | 1 | none |
| 2023-08-09 | 4 | 0 | 78.63% | 21.37% | 100% | `CONCENTRATION_LIMIT` | 1 | none |

This confirms that many zero candidates occurred with abundant residual cash. The reason is not aggregate cash scarcity; it is candidate-level eligibility/expression.

## Rank Analysis

Rank distribution:

| Rank bucket | Positive | Zero |
|---|---:|---:|
| rank 1 | 7 | 19 |
| rank 2 | 8 | 69 |
| rank 3 | 11 | 93 |
| rank 4-5 | 26 | 172 |
| rank 6+ | 20 | 123 |

Rank 1/2 zero:

- Total rank 1/2 zero: 88.
- Primary reasons:
  - `NO_ELIGIBLE_OPPORTUNITY_AFTER_PORTFOLIO_FIT`: 65.
  - `SAFETY_HARD_CAP_BLOCK`: 17.
  - `BROKER_INFEASIBLE`: 6.

Thus even high-rank zeros are explained. Most are high-rank REENTRY rows that fail re-entry recovery authority, not low-quality candidates.

## BUY_NEW vs BUY_ADD

Within the reproduced 548 PC candidate baseline:

| Group | Candidate count | Positive | Zero | Positive rate |
|---|---:|---:|---:|---:|
| BUY_NEW semantic | 239 | 72 | 167 | 30.1% |
| REENTRY semantic | 309 | 0 | 309 | 0.0% |
| Existing BUY_ADD semantic | 0 | 0 | 0 | n/a |

L21F BUY_ADD materialization is therefore not the driver of this 548->72 drop. This baseline is overwhelmingly a BUY_NEW/REENTRY target-membership problem.

## Target Weight Materialization

There are two relevant target concepts:

- Final PC `target_weight` / `lot_aware_final_target_weight`.
- Pre-lot `normal_target_weight`.

Findings:

- Final target >0 but final allocation 0: 0.
- Pre-lot normal target >0 but final allocation 0: 476.
- Pre-lot target >0, one lot Safety-contained, cash available, gross headroom, final allocation 0: 25.
- One-lot Safety-contained zero candidates: 27.
- Cash-available zero candidates under one-lot lens: 91.
- Gross-headroom zero candidates under one-lot lens: 91.

The materialization issue is not that a final PC target got lost downstream. It is that PC final target is zeroed before PS/RP for policy or official lot-expression reasons.

## Legacy Constraint Audit

No evidence was found that the 476 zero allocations were stopped by:

- legacy `max_positions`,
- legacy `max_exposure`,
- stale fixed allocation cap,
- historical-only constraints,
- shadow-only constraints.

Legacy fields exist in architecture and observability for comparison, but the zero reason evidence points to current PC re-entry policy, current Strategy/Safety/lot contracts, broker infeasibility, and remaining budget. The 18% Strategy cap is active by design; the Safety hard cap remains 25%.

## Root Cause Classification

Primary:

`REENTRY_RECOVERY_POLICY_ZERO_TARGET_DOMINANT`

Secondary:

`OFFICIAL_MINIMUM_POLICY_LOT_SAFETY_HARD_CAP_BLOCK`

Actionable architecture subset:

`ONE_LOT_SAFETY_CONTAINED_TARGET_EXPRESSION_GAP`

Not primary:

- Buy Quality.
- Aggregate cash scarcity.
- Gross exposure budget scarcity.
- Runtime Planning mapping.
- Submit/fill.
- Legacy max positions/max exposure.

## Regression Assessment

Regression is not confirmed.

Current behavior is restrictive, but there is no evidence that the same 548 candidates were previously allocated correctly and then regressed. L21G/L21H classified earlier BUY_NEW thinness and score semantics as pre-existing or semantic-contract issues, L21I repaired BQ score semantics, and L21K repaired prior EXIT materialization after the target run. The target run cannot prove L21K's effect.

## Architecture Assessment

Architecture gap is confirmed.

The system can explain every zero candidate, but the explanation exposes two design gaps:

1. REENTRY rows can repeatedly reach PC as BQ-eligible candidates but receive zero final target because prior-exit/recovery evidence is missing or insufficient. L21K likely targets part of this, but the target run predates that repair.
2. A smaller but actionable one-lot expression subset remains Safety/cash/gross feasible but zero under the current official minimum-policy-lot and Strategy expression.

This is not a reason to relax BQ or force buying fixed counts. It is a reason to repair/validate re-entry authority and design a narrow one-lot expression contract.

## Recommended Next Task

Recommended next task:

`Phase29-L21P — Re-entry Candidate Target Materialization Validation / Post-L21K Historical Evidence Audit`

Scope:

- Validate whether L21K materially reduces the 309 REENTRY zero-target cases in a new operator-controlled validation run.
- Separately carry forward L21N's one-lot fallback design for the 25 actionable one-lot expression candidates.
- Preserve BQ, Safety hard cap, gross exposure, cash, broker lot, and PC competition authority.

Do not implement threshold relaxation or fixed BUY count forcing.

## Primary Judgment

Required final answers:

1. 548->72の476件は全件説明できたか: YES.
2. UNEXPLAINEDは何件か: 0.
3. 最大のzero allocation理由: `NO_ELIGIBLE_OPPORTUNITY_AFTER_PORTFOLIO_FIT` / REENTRY recovery hurdle, 309件.
4. Safety hard capで正当に落ちた件数: official minimum-policy-lot basisで153件.
5. Strategy soft capだけで落ちた件数: 0件をprimary分類。
6. minimum meaningful notional関連件数: 153件がofficial minimum-policy-lot Safety block、plus 25件がone-lot actionable subset.
7. one-lotならSafety内だった件数: 27件。cash/grossも含めると25件。
8. Cash不足件数: primary `CASH_INSUFFICIENT` は2件。
9. Gross exposure不足件数: primary bucketでは0件。
10. 他Opportunityとの競争に正当に負けた件数: 0件をprimary確認。
11. Cashを残したまま買わなかった件数: zero 476件すべての日でresidual cashあり。>20% residual cash日は431件。
12. rank 1 / 2 zero件数: 88件。
13. BUY_NEWとBUY_ADDのどちらに問題が偏っているか: 548 baselineはBUY_NEW/REENTRY側。既存BUY_ADDは含まれない。
14. target_weight >0なのにallocation=0だった件数: final PC targetでは0件。pre-lot normal targetでは476件。
15. target >0 + Safety内 + cashあり + grossあり + allocation=0件数: final PC target基準では0件。pre-lot normal target基準では25件。
16. legacy constraint混入はあるか: 見つからない。
17. regression confirmedか: NO.
18. Architecture gapか: YES.
19. 修正が必要か: YES, design/validation first.
20. 次Taskでどこを修正すべきか: re-entry target materialization validation after L21K, plus separate one-lot expression design from L21N.

Primary judgment:

`PHASE29_L21O_PC_ZERO_ALLOCATION_FULLY_EXPLAINED_REENTRY_POLICY_DOMINANT_WITH_ACTIONABLE_ONE_LOT_EXPRESSION_GAP`
