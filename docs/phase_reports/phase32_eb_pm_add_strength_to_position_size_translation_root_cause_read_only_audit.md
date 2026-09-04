# Phase32-EB — PM ADD Strength-to-Position-Size Translation Root-Cause READ-ONLY Audit

## Scope

Target evidence:

`reports/runtime_tests/analysis/phase32_dw_dq_shadow_backfill_20260903T000001`

Source run:

`runtime-test-historical-extended-smoke-20260902T060955933565Z`

Covered window:

`2022-10-03` through `2023-10-26`

Current source commit inspected:

`1f64f49ee9a8dd48280007e4df656e5f03e231ca`

This audit used only existing source, reports, and DW backfill artifacts. No source, config, runtime state, Pending state, Ledger state, replay, resume, recover, fresh-run, or long Historical command was executed.

## Evidence Read

Primary evidence read:

- Phase32-DP, DU, DV, DW phase reports.
- DW one-year DQ shadow backfill `summary.json` and daily `unified_marginal_capital_shadow.json` artifacts.
- Current Portfolio Construction ADD bridge in `src/ai_fund_lab_v2/strategy/portfolio_construction.py`.
- Current Position Sizing ADD consumer in `src/ai_fund_lab_v2/strategy/position_sizing.py`.
- Current Strategy Intelligence BQ / Entry ADD logic in `src/ai_fund_lab_v2/strategy/strategy_intelligence.py`.
- G43, G115, G119, G129 ADD-related reports where relevant.

The audit did not use future prices, future returns, future regimes, campaign final outcomes, or Historical PnL to classify ADD strength.

## ADD Funnel Reconstruction

DW records 152 `BUY_ADD_NEXT_LOT` rows. The reconstructed funnel is:

`PM ADD intent`
-> `Portfolio Construction ADD allocation bridge`
-> `target_weight`
-> `desired_continuous_increment_weight`
-> `accepted_continuous_increment_weight`
-> `Position Sizing lot-aware quantity`
-> `next_executable_quantity`
-> `Stage-B executable capital ranking`
-> Production selection comparison.

Observed DW ADD lot-status distribution:

| State | Count |
| --- | ---: |
| `NO_POSITIVE_DESIRED_INCREMENT` | 99 |
| `NO_ACCEPTED_CONTINUOUS_INCREMENT` | 22 |
| `BQ_BLOCKS_INCREMENT` | 9 |
| `EXECUTABLE_INCREMENT_AVAILABLE` | 19 |
| `SAFETY_HARD_CAP_BLOCK` | 3 |

Headroom distribution for the same 152 rows:

| Headroom state | Count |
| --- | ---: |
| `HEADROOM_AVAILABLE` | 144 |
| `LESS_THAN_ONE_LOT_HEADROOM` | 3 |
| `SAFETY_HARD_CAP_BLOCKED` | 4 |
| `STRATEGY_CAP_BLOCKED` | 1 |

Therefore the dominant suppressor is not final arbitration and not simple 100-share discreteness. The dominant suppressor is that most PM ADD rows do not become a positive continuous desired increment before executable-lot ranking.

## PM ADD Semantic Contract

Current `PM action = ADD` means:

`B. this position is eligible to be considered for ADD if Portfolio Construction creates incremental weight`

It does not currently mean:

`A. this position deserves more capital now in a positive amount`

All 152 DW ADD rows carry the same PM reason-code set:

`no_loss_averaging`, `opportunity_rank_still_high`, `strong_trend_continuation`

Those reason codes prove PM-recognized continuation strength and ADD intent. They do not themselves set the incremental size. PC then requires separate ADD investment evidence and target-weight arithmetic before any positive increment exists.

This is consistent with G115/G129 ownership:

- PM owns ADD intent and eligibility.
- PC owns marginal capital / target-weight authority.
- PS owns discrete quantity consumption.
- Runtime consumes PS/PC-bound quantities and must not re-decide ADD priority.

G129 remains intact: positive `BUY_ADD` Submit authority is order-increment scoped when PC/PS have produced a positive increment. EB does not reclassify G129 as defective.

## Strength-to-Target Mapping

Current PC logic computes ADD target movement from:

`candidate_target_weight - current_weight`

and then applies ADD bridge evidence, BQ/Entry authority, acceleration tier, risk pacing, headroom, safety, broker, corporate-action, and liquidity guardrails.

Evidence-family consumption:

| Evidence family | Current role in target/increment formation |
| --- | --- |
| PM `ADD` action | Eligibility gate, not direct magnitude |
| PM `strong_trend_continuation` | Used by acceleration strong-tier predicate, but only after a positive base increment exists |
| PM `opportunity_rank_still_high` | Same as above; does not independently create target expansion |
| PM `no_loss_averaging` | Guardrail / eligibility preservation |
| current weight | Arithmetic base; can collapse desired increment to zero when equal to target |
| candidate target weight | Primary base increment source |
| expected edge | Required PASS for ADD bridge / acceleration; failing states keep target unchanged |
| incremental investment value | Required PASS; `UNKNOWN` blocks or prevents high-quality ADD materialization |
| opportunity cost | Required PASS; `NEW_BUY_SUPERIOR` blocks or prevents ADD materialization |
| BQ action | Can hard-block incremental ADD on `BUY_WAIT`; `REDUCED_ALLOCATION_ONLY` down-tiers |
| Entry ADD state | Interpreted as caution/allowed/no-add; can suppress participation |
| risk pacing | Can down-tier or fail acceleration, but is not the dominant 99-row zero cause |
| structured headroom | Mostly available; not the dominant 99-row zero cause |
| DQ unified marginal value | SHADOW only; no authoritative consumer and no backflow into Production target weight |

The important structural property is that acceleration only scales a positive `pre_acceleration_incremental_weight`; it does not create a positive base increment when target equals current. If `candidate_target_weight <= current_weight`, a strong incumbent can remain at zero desired increment even with PM ADD intent and headroom.

## 99 No-Positive-Desired-Increment Cases

All 99 rows have `lot_status_decomposition.state = NO_POSITIVE_DESIRED_INCREMENT` and reason `desired_continuous_increment_zero`.

Distribution by BQ/Entry:

| BQ action | Entry action | Count |
| --- | --- | ---: |
| `BUY_WAIT` | `ADD_REDUCED_ONLY` | 34 |
| `FULL_ALLOCATION_ELIGIBLE` | `ADD_REDUCED_ONLY` | 30 |
| `REDUCED_ALLOCATION_ONLY` | `ADD_REDUCED_ONLY` | 19 |
| `REDUCED_ALLOCATION_ONLY` | `NO_ADD` | 7 |
| `FULL_ALLOCATION_ELIGIBLE` | `NO_ADD` | 7 |
| `BUY_WAIT` | `NO_ADD` | 1 |
| `BUY_WAIT` | `ADD_ALLOWED` | 1 |

Headroom:

- 98 of 99 have `HEADROOM_AVAILABLE`.
- 1 of 99 has `STRATEGY_CAP_BLOCKED`.

Strong-ish zero-increment subset:

Definition used in this audit:

`NO_POSITIVE_DESIRED_INCREMENT + HEADROOM_AVAILABLE + BQ in {FULL_ALLOCATION_ELIGIBLE, REDUCED_ALLOCATION_ONLY} + Entry in {ADD_REDUCED_ONLY, ADD_ALLOWED}`

Count:

49 rows.

Those 49 are not clean executable missed ADDs. Their ADD opportunity-quality classes are:

| Opportunity quality class | Count |
| --- | ---: |
| `BLOCKED` | 35 |
| `INSUFFICIENT` | 14 |

Their ADD evidence states are dominated by:

| expected edge | incremental value | opportunity cost | PIT status | Count |
| --- | --- | --- | ---: |
| `WEAKENING` | `UNKNOWN` | `NEW_BUY_SUPERIOR` | `COMPARISON_INSUFFICIENT` | 20 |
| `WEAKENING` | `UNKNOWN` | `PASS` | `COMPARISON_INSUFFICIENT` | 15 |
| `IMPROVING` | `UNKNOWN` | `NEW_BUY_SUPERIOR` | `COMPARISON_INSUFFICIENT` | 12 |
| `UNKNOWN` | `UNKNOWN` | `NEW_BUY_SUPERIOR` | `COMPARISON_INSUFFICIENT` | 2 |

Root-cause profile for the 99:

| Category | Classification |
| --- | --- |
| `CURRENT_WEIGHT_ALREADY_AT_TARGET` | Present as arithmetic symptom: target equals current |
| `ADD_TARGET_WEIGHT_UNCHANGED` | Dominant materialized result |
| `PM_ADD_NOT_MATERIAL_TO_TARGET_WEIGHT` | Structurally present |
| `BQ_OR_ENTRY_PRE_TARGET_SUPPRESSION` | Material, especially `BUY_WAIT` and `NO_ADD`, but not the only cause |
| `RISK_PACING_PRE_TARGET_SUPPRESSION` | Secondary, not dominant in the 99 |
| `PORTFOLIO_FIT_PRE_TARGET_SUPPRESSION` | Secondary; 98/99 still had headroom |
| `MISSING_STRENGTH_TO_TARGET_MAPPING` | Primary architectural root cause |
| `OTHER` | No dominant independent class found |

Conclusion:

`NO_POSITIVE_DESIRED_INCREMENT` is mainly produced before lot and before final capital arbitration. PM strength is visible, but there is no first-class PC target-refresh rule saying how much additional weight a repeatedly strong incumbent deserves when current target already equals current weight.

## Positive Desired But Zero Accepted

31 rows had positive desired increment but zero accepted increment:

| State | Count |
| --- | ---: |
| `NO_ACCEPTED_CONTINUOUS_INCREMENT` | 22 |
| `BQ_BLOCKS_INCREMENT` | 9 |

Headroom:

- 30 of 31 have `HEADROOM_AVAILABLE`.
- 1 of 31 has `SAFETY_HARD_CAP_BLOCKED`.

Observed pattern:

- Some rows are genuine BQ/Entry suppression.
- Some rows have `IMPROVING + POSITIVE + PASS` ADD evidence, but are still zeroed by Entry `NO_ADD`, risk/safety/headroom, or downstream accepted-increment resolution.
- Some rows have visible next executable quantity in DQ diagnostics but accepted continuous weight remains zero because the Production PC bridge did not authorize the increment.

This confirms a second, smaller boundary after positive desired increment:

`desired_continuous_increment_weight > 0`
-> `accepted_continuous_increment_weight = 0`

That boundary is material but smaller than the 99-row no-positive-desired layer.

## BQ ADD Suppression

Explicit `BQ_BLOCKS_INCREMENT` rows:

9.

BQ/Entry also appears in the 99 zero-desired rows:

- `BUY_WAIT` participates in 36 zero-desired rows.
- `NO_ADD` participates in 15 zero-desired rows.

This is material, but EB does not classify it as a defect by itself. BQ/Entry is a legitimate PIT safety/quality authority when it blocks weak or incomplete ADDs. The defect/risk is not "BQ is too strict"; it is that BQ/Entry and ADD investment evidence are the main places where PM strength fails to become a positive target refresh, without a dedicated incumbent graduation sizing authority.

## Positive Controls

Executable ADD path exists.

`EXECUTABLE_INCREMENT_AVAILABLE` rows:

19.

Symbols:

| Symbol | Executable rows |
| --- | ---: |
| 94320 | 9 |
| 94340 | 4 |
| 99840 | 3 |
| 83060 | 1 |
| 54010 | 1 |
| 59550 | 1 |

Stage-B ADD winners:

11.

DW reports all Stage-B ADD winners matched Production ADD family selection. This proves:

- Production can fund ADD when PC/PS materialize a valid increment.
- DQ Stage-B does not need a fixed ADD preference.
- The main missing mechanism is pre-arbitration strength-to-size materialization, not a universal ADD execution blockage.

## 94320 Strength-to-Size Control

94320 is the best positive control:

- Total ADD rows: 50.
- `EXECUTABLE_INCREMENT_AVAILABLE`: 9.
- Stage-B ADD winners: 5.
- Production selected ADD rows: 7.
- Dominant non-executable states: no positive desired increment, no accepted continuous increment, and BQ block.

Representative executable 94320 ADD rows include:

| Date | Desired increment | Accepted increment | Quantity | Stage-B | Production selected |
| --- | ---: | ---: | ---: | --- | --- |
| 2022-11-01 | 0.032258 | 0.032258 | 200 | yes | yes |
| 2023-02-13 | 0.033333 | 0.033333 | 200 | yes | yes |
| 2023-02-22 | 0.040000 | 0.040000 | 300 | yes | yes |
| 2023-02-24 | 0.033333 | 0.033333 | 200 | yes | yes |
| 2023-03-15 | 0.029412 | 0.029412 | 200 | yes | yes |

94320 proves the positive path works when:

- ADD evidence is sufficiently positive.
- BQ/Entry is not hard-blocking.
- PC creates a positive accepted increment.
- PS can consume an executable next lot.

It also proves repeated PM ADD can spend many days with zero desired increment before becoming fundable. This is exactly the translation weakness EB is characterizing.

## Failed Graduation Controls

| Symbol / campaign profile | Observed strength-to-size profile |
| --- | --- |
| 99840 first campaign | 18 rows, 14 zero desired, no executable ADD, target already high at roughly 12.7%-15.4%; BQ/Entry and opportunity-cost frequently block |
| 94340 later campaign | 14 rows, 8 zero desired, 6 positive-desired-zero, no executable ADD; target stays around 2.7%-2.9% |
| 83060 main campaign | 12 rows, 10 zero desired, 1 positive-desired-zero, 1 executable; no Stage-B/Production ADD |
| 40520 | 7 rows, all zero desired, no executable ADD |
| 43880 | 12 rows, all zero desired, no executable ADD |
| 54010 | 6 rows, 5 zero desired, 1 executable Stage-B/Production ADD |

These are not all the same failure:

- Some are high current-weight / current-target cases.
- Some are BQ/Entry caution cases.
- Some lack incremental-value or opportunity-cost evidence.
- Some remain below lot or accepted-increment thresholds.

The common architectural theme is that repeated incumbent strength is not itself materialized as a durable target-weight refresh / graduation episode with a quantified marginal capital request.

## NEW / REENTRY / ADD Symmetry

NEW and REENTRY sizing are closer to total-position target sizing:

`quality-adjusted target weight`
-> full target notional
-> executable initial/new lot.

ADD sizing is incremental:

`current target/current weight`
-> positive delta only if PC target exceeds current
-> accepted increment
-> next executable lot.

Therefore the current Production path is not semantically symmetric at the marginal-capital level. ADD must first prove a positive delta against its existing weight, while NEW/REENTRY materializes a fresh total target. DW adds a SHADOW next-lot comparator, but that comparator has `authoritative_consumer_count = 0` and does not feed Production target weights.

This is not a G129 violation. G129 governs how a positive BUY_ADD increment is submitted once authorized. EB shows that many strong ADDs never become a positive authorized increment.

## Current Root Cause

Primary root cause:

`MISSING_FIRST_CLASS_PM_ADD_STRENGTH_TO_TARGET_WEIGHT_REFRESH_AUTHORITY`

Expanded:

PM repeatedly emits ADD intent with strong continuation reason codes, but current PC treats that intent primarily as eligibility. The continuous ADD size is still anchored to the existing candidate target versus current weight. If current weight already equals the materialized target, acceleration cannot start because it only scales a positive base increment. DQ can observe an ADD next-lot opportunity in SHADOW, but Production has no authoritative feedback path from incumbent strength / repeated graduation evidence into a refreshed target weight or accepted continuous increment.

Secondary causes:

- BQ/Entry caution or wait states materially suppress ADD, sometimes correctly.
- ADD opportunity evidence is often incomplete or negative for incremental value / opportunity cost.
- 31 positive desired rows are later zeroed before accepted increment.
- Lot and hard-cap constraints matter, but after DW they are no longer the dominant explanation.

## Repair Boundary

No Production repair is executed in EB.

Recommended next repair boundary:

Create a PC-owned SHADOW-first `ADD_STRENGTH_TO_INCREMENT_TARGET_AUTHORITY` / graduation sizing contract that:

- Consumes PM ADD intent and reason codes as strength evidence, not as fixed ADD preference.
- Requires fresh PIT evidence for continuation, expected edge, incremental value, opportunity cost, BQ, Entry, safety, broker, corporate action, liquidity, and headroom.
- Computes a candidate incremental target weight when repeated incumbent strength is sufficient even if current target equals current weight.
- Separates intrinsic incumbent strength from executable capital feasibility, preserving the DW two-stage design.
- Emits explicit reasons when strength is visible but no positive target refresh is authorized.
- Does not reserve capital across days.
- Does not use Historical PnL/future outcome.
- Does not enable Model 2.
- Does not bypass G115/G119/G129 authority ownership.

A fixed ADD bonus is not recommended. The repair should be evidence-tiered and action-neutral at the marginal-capital comparison boundary.

## Required Final Answers

1. `ADD_STRENGTH_TO_SIZE_FUNNEL_RECONSTRUCTED = YES`
2. `NO_POSITIVE_DESIRED_INCREMENT_ROOT_CAUSE_PROFILE = 99_TOTAL; 98_HEADROOM_AVAILABLE; DOMINANT_ADD_TARGET_WEIGHT_UNCHANGED/CURRENT_WEIGHT_EQUALS_TARGET; 49_STRONGISH_HEADROOM_BQ_ENTRY_NOT_HARD_BLOCKED_BUT_OPPORTUNITY_QUALITY_BLOCKED_OR_INSUFFICIENT; PRIMARY_MISSING_STRENGTH_TO_TARGET_MAPPING`
3. `PM_ADD_SEMANTIC_CONTRACT = ELIGIBILITY_AND_INTENT_NOT_DIRECT_SIZE_AUTHORITY`
4. `INCUMBENT_STRENGTH_TO_TARGET_WEIGHT_MAPPING = PARTIAL; PM_REASON_CODES_CAN_ENABLE_ACCELERATION_ONLY_AFTER_POSITIVE_BASE_INCREMENT; THEY_DO_NOT_CREATE_BASE_TARGET_REFRESH`
5. `ADD_SIZING_RESOLUTION_STATUS = MOSTLY_BINARY_BEFORE_TARGET_REFRESH_WITH_PARTIAL_POSITIVE_CONTROLS`
6. `CURRENT_VS_TARGET_WEIGHT_PROFILE = ZERO_DESIRED_MOSTLY_CURRENT_WEIGHT_EQUALS_TARGET_DESPITE_HEADROOM; NOT_GENERALLY_HEADROOM_EXHAUSTION`
7. `REPEATED_STRONG_ZERO_INCREMENT_CAMPAIGNS = PRESENT; 94320/99840/94340/43880/83060/40520_SHOW_REPEATED_PM_ADD_WITH_ZERO_DESIRED_INCREMENT`
8. `ADD_RECOMPETITION_AND_TARGET_REFRESH_STATUS = PARTIAL; DAILY_FRESH_PIT_RECOMPETITION_EXISTS_BUT_DURABLE_GRADUATION_TARGET_REFRESH_IS_NOT_FIRST_CLASS`
9. `POSITIVE_DESIRED_TO_ZERO_ACCEPTED_ROOT_CAUSE_PROFILE = 31_TOTAL; 22_NO_ACCEPTED_CONTINUOUS_INCREMENT; 9_BQ_BLOCKS_INCREMENT; 30_HEADROOM_AVAILABLE; MIXED_BQ_ENTRY_EVIDENCE_AND_ACCEPTED_INCREMENT_RESOLUTION`
10. `BQ_ADD_SUPPRESSION_MATERIALITY = MATERIAL_BUT_NOT_STANDALONE_DEFECT; 9_EXPLICIT_BQ_BLOCKS_AND_36_BUY_WAIT_ZERO_DESIRED_ROWS`
11. `EXECUTABLE_ADD_POSITIVE_CONTROL_PROFILE = PASS; 19_EXECUTABLE_INCREMENT_AVAILABLE; 11_STAGE_B_ADD_WINNERS; PRODUCTION_CAN_FUND_ADD_WHEN_PC_PS_MATERIALIZE_INCREMENT`
12. `94320_STRENGTH_TO_SIZE_CONTROL = PASS_AS_POSITIVE_CONTROL_WITH_REPEATED_ZERO_AND_LATER_EXECUTABLE_ADD_CASES`
13. `FAILED_GRADUATION_STRENGTH_TO_SIZE_PROFILE = MIXED_ZERO_TARGET_BQ_ENTRY_EVIDENCE_INCOMPLETENESS_AND_ACCEPTED_INCREMENT_ZERO; NOT_SINGLE_LOT_ONLY_CAUSE`
14. `NEW_ADD_POSITION_SIZE_SEMANTIC_SYMMETRY = NO; NEW_USES_TOTAL_TARGET_SIZING_WHILE_ADD_REQUIRES_POSITIVE_INCREMENT_ABOVE_CURRENT_WEIGHT`
15. `REENTRY_ADD_POSITION_SIZE_SEMANTIC_SYMMETRY = NO; REENTRY_REQUALIFIES_AS_NEW_EQUIVALENT_TOTAL_TARGET_WHILE_ADD_REMAINS_INCREMENT_ONLY`
16. `MARGINAL_CAPITAL_VALUE_TO_TARGET_WEIGHT_BOUNDARY = NOT_CONNECTED_IN_PRODUCTION; DW_DQ_IS_SHADOW_ONLY_WITH_AUTHORITATIVE_CONSUMER_COUNT_ZERO`
17. `STRONG_WINNER_ZERO_INCREMENT_CASES = PRESENT_AS_STRONGISH_PM_ADD_HEADROOM_ROWS_BUT_CLEAN_COMPLETE_EXECUTABLE_HIGH_VALUE_MISS_NOT_CONFIRMED`
18. `WINNER_CAPITALIZATION_PRE_ARBITRATION_ROOT_CAUSES = MISSING_STRENGTH_TO_TARGET_MAPPING > ADD_EVIDENCE_INCOMPLETENESS > BQ_ENTRY_SUPPRESSION > ACCEPTED_INCREMENT_ZERO > LOT/HARD_CAP_SECONDARY`
19. `STRENGTH_TO_POSITION_SIZE_TRANSLATION_STATUS = STRUCTURALLY_WEAK_PARTIAL_CONTROLS_EXIST`
20. `PROPOSED_REPAIR_BOUNDARY = PC_OWNED_SHADOW_FIRST_ADD_STRENGTH_TO_INCREMENT_TARGET_AUTHORITY_WITH_FRESH_PIT_EVIDENCE_AND_DW_TWO_STAGE_FEASIBILITY`
21. `FIXED_ADD_BONUS_RECOMMENDED = NO`
22. `MODEL2_ENABLED = NO`
23. `FUTURE_OUTCOME_USED = NO`
24. `PRODUCTION_CHANGE_EXECUTED = NO`
25. `TARGET_RUN_MUTATED = NO`
26. `RUNTIME_STATE_MUTATED = NO`
27. `LONG_RUNTIME_EXECUTED = NO`
28. `NEXT_RECOMMENDED_STEP = DESIGN_AND_IMPLEMENT_SHADOW_ONLY_PC_ADD_STRENGTH_TO_INCREMENT_TARGET_AUTHORITY_THEN_REBACKFILL_DW_STYLE_EVIDENCE`
29. `FINAL_JUDGMENT = PHASE32_EB_PM_ADD_STRENGTH_TO_POSITION_SIZE_TRANSLATION_STRUCTURALLY_WEAK_SHADOW_REPAIR_DESIGN_REQUIRED_NO_PRODUCTION_CHANGE`

## Final Judgment

`PHASE32_EB_PM_ADD_STRENGTH_TO_POSITION_SIZE_TRANSLATION_STRUCTURALLY_WEAK_SHADOW_REPAIR_DESIGN_REQUIRED_NO_PRODUCTION_CHANGE`
