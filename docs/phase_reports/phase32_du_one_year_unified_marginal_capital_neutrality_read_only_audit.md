# Phase32-DU - One-Year Unified Marginal Capital Neutrality / Strongest-Opportunity Allocation READ-ONLY Audit

## Scope

- Target isolated backfill: `reports/runtime_tests/analysis/phase32_dt_dq_shadow_backfill_20260903`
- Source run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Window: `2022-10-03` through `2023-10-26`
- Mode: READ-ONLY audit of already-materialized DT analysis artifacts.
- Production/source-run/runtime mutation: none.
- Fresh-run/resume/recover/replay/long Historical executed by this phase: none.

## Current Source / Authority Context

Current repo HEAD during this audit:

- `1f64f49ee9a8dd48280007e4df656e5f03e231ca`

The DT artifacts identify the DQ evaluator as:

- `UNIFIED_MARGINAL_CAPITAL_SHADOW_AUTHORITY`
- contract: `phase32_dq_unified_marginal_capital_shadow.v1`
- schema: `unified_marginal_capital_shadow.v1`
- producer: `strategy.marginal_capital_value`

Portfolio Construction currently carries the unified marginal capital output as shadow/non-production authority:

- `unified_marginal_capital_shadow_authoritative_consumer_count = 0`
- `unified_marginal_capital_shadow_production_consumer = False`
- `dual_capital_authority = False`

Therefore DU treats the DQ/DT output as diagnostic PIT evidence, not Production trading authority.

## DT Evidence Acceptance

DT backfill evidence is accepted for DU analysis.

- `manifest.json` status: `PASS`
- `summary.json` status: `PASS`
- daily shadow files: 264
- first daily artifact: `2022-10-03`
- last daily artifact: `2023-10-26`
- all daily statuses: `PASS`
- all daily `source_run_id`: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- date mismatches: 0
- `future_information_used`: false in inspected daily provenance
- `analysis_only`: true in inspected daily provenance
- `original_production_decision_preserved`: true in inspected daily provenance
- `full_pc_recompute_executed`: false in inspected daily provenance

Competitor coverage:

- BUY_NEW rows: 2,483
- REENTRY rows: 5,196
- BUY_ADD rows: 152
- CASH rows: 264

`DT_BACKFILL_ACCEPTED_FOR_DU_ANALYSIS = YES`

## Overall Neutrality

Across 264 one-day competition sets:

- Agreement: 76
- Divergence: 188

Divergence classes:

| Divergence | Days |
| --- | ---: |
| AGREEMENT | 76 |
| Production NEW_OR_REENTRY / SHADOW Cash | 85 |
| Production NEW_OR_REENTRY / SHADOW REENTRY | 50 |
| Production NEW_OR_REENTRY / SHADOW ADD | 22 |
| Production NEW_OR_REENTRY / SHADOW NEW | 15 |
| Production ADD / SHADOW Cash | 8 |
| Production ADD / SHADOW REENTRY | 3 |
| Production Cash / SHADOW REENTRY | 3 |
| Production ADD / SHADOW NEW | 1 |
| Production ADD / SHADOW ADD | 1 |

This is not action-neutral agreement. Production and SHADOW differ on most days, especially around Production-funded NEW/REENTRY versus SHADOW Cash/REENTRY/ADD. However, these divergences are not all Production defects because the SHADOW winner can be infeasible, incomplete, concentration-blocked, or cash-calibration sensitive.

SHADOW winner types:

- CASH_OPTIONALITY: 94
- BUY_NEW_NEXT_LOT: 83
- REENTRY_NEXT_LOT: 64
- BUY_ADD_NEXT_LOT: 23

`PRODUCTION_SHADOW_NEUTRALITY_PROFILE = PARTIAL_NON_NEUTRAL_WITH_MATERIAL_SHADOW_RELIABILITY_LIMITS`

## Strong ADD Displacement

Primary DU focus: 22 cases where Production funded NEW_OR_REENTRY while SHADOW preferred ADD.

All 22 cases classify as:

`D_ADD_HIGH_VALUE_BUT_EVIDENCE_INCOMPLETE`

Every one of these ADD winners also had:

- marginal desirability: `HIGH_VALUE_EVIDENCE_INCOMPLETE`
- evidence completeness: `INCOMPLETE`
- missing input: `opportunity_quality_insufficient`
- execution feasibility: `INFEASIBLE_DUE_TO_LOT`
- portfolio risk cost: `BLOCKED_BY_CONCENTRATION`
- next executable quantity: `0.0`
- next lot notional: `0.0`

Therefore there are no clean cases in the DT backfill where a complete, executable, non-hard-blocked ADD was displaced by Production NEW/REENTRY.

### 22 Case List

| Date | Regime | ADD Symbol | Campaign | Class | BQ | Entry | Production funded |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2022-11-02 | RANGE | 99840 | pc-5a5765b1c257b5b8-99840-0001 | D | BUY_WAIT | ADD_REDUCED_ONLY | NEW_BUY 76920/78780/89380 |
| 2022-11-07 | RANGE | 99840 | pc-5a5765b1c257b5b8-99840-0001 | D | REDUCED_ALLOCATION_ONLY | ADD_REDUCED_ONLY | NEW_BUY 65790/78780/83060/88480 |
| 2022-11-28 | BULL | 45940 | pc-d849118022b497c9-45940-0001 | D | FULL_ALLOCATION_ELIGIBLE | ADD_REDUCED_ONLY | NEW_BUY 93180 |
| 2022-11-30 | BULL | 45940 | pc-d849118022b497c9-45940-0001 | D | FULL_ALLOCATION_ELIGIBLE | ADD_REDUCED_ONLY | NEW_BUY 44220 |
| 2022-12-22 | BEAR | 45410 | pc-97e69ccc8e91da3a-45410-0001 | D | FULL_ALLOCATION_ELIGIBLE | ADD_REDUCED_ONLY | NEW_BUY 53800/23530/83410/84180 |
| 2023-02-16 | BULL | 54010 | pc-0972f0d0a80bbd70-54010-0001 | D | REDUCED_ALLOCATION_ONLY | ADD_REDUCED_ONLY | NEW_BUY 93180/39450/14430/51030 |
| 2023-02-28 | BULL | 94320 | pc-7c5bd9294d48b016-94320-0001 | D | BUY_WAIT | ADD_REDUCED_ONLY | NEW_BUY 93180/48810/30830/23700 |
| 2023-03-07 | BULL | 94320 | pc-7c5bd9294d48b016-94320-0001 | D | FULL_ALLOCATION_ELIGIBLE | ADD_REDUCED_ONLY | NEW_BUY 93180/47720/45980 |
| 2023-03-16 | RANGE | 93180 | pc-b6f6bd3b13d372ee-93180-0001 | D | REDUCED_ALLOCATION_ONLY | ADD_REDUCED_ONLY | NEW_BUY 43880/72710/64240/70660 |
| 2023-03-17 | RANGE | 43880 | pc-77b04ae8a6085bfd-43880-0001 | D | REDUCED_ALLOCATION_ONLY | ADD_REDUCED_ONLY | NEW_BUY 76920/59350/39360 |
| 2023-03-20 | CORRECTION | 43880 | pc-77b04ae8a6085bfd-43880-0001 | D | BUY_WAIT | ADD_REDUCED_ONLY | NEW_BUY 76920/77930 |
| 2023-03-23 | RANGE | 59350 | pc-d1fef95b19b5416a-59350-0001 | D | REDUCED_ALLOCATION_ONLY | ADD_REDUCED_ONLY | NEW_BUY 57810/76700 |
| 2023-03-30 | RANGE | 43880 | pc-77b04ae8a6085bfd-43880-0001 | D | REDUCED_ALLOCATION_ONLY | ADD_REDUCED_ONLY | NEW_BUY 44440/76920/48920 |
| 2023-06-26 | BULL | 40520 | pc-3551cfa510023cea-40520-0001 | D | BUY_WAIT | ADD_REDUCED_ONLY | NEW_BUY 72030/78860 |
| 2023-06-27 | BULL | 40520 | pc-3551cfa510023cea-40520-0001 | D | FULL_ALLOCATION_ELIGIBLE | ADD_REDUCED_ONLY | NEW_BUY 77090/76920/68360 |
| 2023-09-27 | BULL | 94340 | pc-8d0b3d71adb1e835-94340-0001 | D | FULL_ALLOCATION_ELIGIBLE | ADD_REDUCED_ONLY | NEW_BUY 53800/13820/52480/38560 |
| 2023-09-28 | RECOVERY | 94340 | pc-8d0b3d71adb1e835-94340-0001 | D | BUY_WAIT | ADD_REDUCED_ONLY | NEW_BUY 78510/50100/55800/38560 |
| 2023-09-29 | RANGE | 94340 | pc-8d0b3d71adb1e835-94340-0001 | D | BUY_WAIT | ADD_REDUCED_ONLY | NEW_BUY 41760 |
| 2023-10-02 | CORRECTION | 94340 | pc-8d0b3d71adb1e835-94340-0001 | D | BUY_WAIT | ADD_REDUCED_ONLY | NEW_BUY 74770 |
| 2023-10-03 | BEAR | 94340 | pc-8d0b3d71adb1e835-94340-0001 | D | FULL_ALLOCATION_ELIGIBLE | ADD_REDUCED_ONLY | NEW_BUY 59660/45710 |
| 2023-10-04 | BEAR | 94340 | pc-8d0b3d71adb1e835-94340-0001 | D | BUY_WAIT | ADD_REDUCED_ONLY | NEW_BUY 92460/50280/52590 |
| 2023-10-13 | BEAR | 94340 | pc-8d0b3d71adb1e835-94340-0001 | D | FULL_ALLOCATION_ELIGIBLE | ADD_REDUCED_ONLY | NEW_BUY 36910/76920/38560/52590 |

`STRONG_ADD_DISPLACEMENT_CLASSIFICATION = D_ADD_HIGH_VALUE_BUT_EVIDENCE_INCOMPLETE: 22; A/B/C/E/F: 0`

## Feasible ADD Misses

Clean feasible ADD miss criteria:

- SHADOW prefers ADD
- ADD evidence complete enough
- next lot executable
- no hard concentration/risk violation
- Production funded NEW/REENTRY instead

Observed count: 0.

`FEASIBLE_STRONG_ADD_MISSED_FOR_NEW_REENTRY = 0`

Cases where Production retained Cash while a clean strong ADD existed: 0. There are no `Production Cash / SHADOW ADD` divergences in the DT summary.

`FEASIBLE_STRONG_ADD_MISSED_FOR_CASH = 0`

## NEW vs ADD Relative Strength

For direct NEW-vs-ADD coexistence, the 22 apparent ADD-over-NEW cases are not clean decision-time proofs that NEW was weaker. Production funded NEW_BUY rows while the SHADOW ADD winner was simultaneously incomplete, lot-infeasible, and concentration-blocked.

This does not prove Production is fully action-neutral, because Production still routes capital through NEW/REENTRY much more often than ADD and diverges from the unified comparator on 188/264 days. It does prove that the cleanest one-year DT evidence does not yet show a complete/executable ADD being wrongly displaced by NEW.

`NEW_VS_ADD_RELATIVE_STRENGTH_PROFILE = NOT_COMPARABLE_IN_PRIMARY_DISPLACEMENTS_DUE_TO_ADD_INCOMPLETE_LOT_INFEASIBLE_CONCENTRATION_BLOCKED`

## REENTRY vs ADD Relative Strength

REENTRY is a major SHADOW and Production competitor:

- REENTRY rows: 5,196
- SHADOW REENTRY winners: 64
- Production NEW_OR_REENTRY / SHADOW REENTRY: 50 days
- Production Cash / SHADOW REENTRY: 3 days
- Production ADD / SHADOW REENTRY: 3 days

The DT output supports that REENTRY benefits from a mature BUY_NEW-like path and often appears as the strongest SHADOW alternative. However, in the primary ADD displacement set, Production funded alternatives are represented as `NEW_BUY`; the evidence does not isolate clean REENTRY-over-ADD displacement where ADD was complete, executable, and unblocked.

`REENTRY_VS_ADD_RELATIVE_STRENGTH_PROFILE = REENTRY_PATH_MATURE_AND_OFTEN_COMPETITIVE; CLEAN_REENTRY_OVER_FEASIBLE_ADD_MISS_NOT_CONFIRMED`

## Regime Findings

### BULL / RECOVERY

ADD rows by regime:

- BULL: 90
- RECOVERY: 16

Primary 22 ADD displacement cases by regime:

- BULL: 8
- RECOVERY: 1

BULL/RECOVERY still show a winner-capitalization gap: many incumbent campaigns produce ADD competitors while Production continues to fund NEW/REENTRY and while actual BUY_ADD fills can remain scarce. But the DQ backfill says the visible ADD winners are not clean executable strongest opportunities: they are evidence-incomplete, lot-infeasible, and concentration-blocked.

`BULL_RECOVERY_WINNER_CAPITALIZATION_GAP = PARTIAL`

### BEAR

BEAR primary ADD displacement cases: 4. All 4 have the same incomplete/infeasible/concentration-blocked profile. BEAR also has 25 `Production NEW_OR_REENTRY / SHADOW Cash` divergences, suggesting cash optionality is important under the SHADOW comparator.

No BEAR-specific ADD preference is justified.

`BEAR_CAPITAL_ALLOCATION_NEUTRALITY = PARTIAL; NO_CLEAN_STRONG_ADD_MISS_CONFIRMED`

## Concentration / Headroom

All 152 BUY_ADD rows are marked `BLOCKED_BY_CONCENTRATION`, including:

- 40 high-value-evidence-incomplete rows
- 19 medium/complete/feasible rows
- 5 low/complete/feasible rows
- 88 lot-infeasible low/medium rows

This is a material constraint, not merely noise. It may be doing legitimate risk work for already-large positions, but it also prevents the current SHADOW from demonstrating that strong incumbent winners can graduate when the next lot is otherwise feasible. Because the clean feasible/unblocked miss count is zero, DU cannot label the cap overrestrictive from PIT evidence alone.

`CONCENTRATION_HEADROOM_IMPACT_ON_STRONG_ADD = MATERIAL_CONSTRAINT_NOT_YET_PROVEN_OVERRESTRICTIVE`

## Lot Granularity

BUY_ADD feasibility profile:

- Infeasible due to lot: 128/152
- Feasible but concentration-blocked: 24/152
- Primary ADD displacement cases with next executable quantity 0: 22/22

Lot granularity is a first-order winner-capitalization constraint. In the primary displacement set, it prevents interpreting SHADOW ADD as an executable next capital unit.

`LOT_GRANULARITY_IMPACT_ON_WINNER_CAPITALIZATION = MATERIAL_EXECUTION_LIMITATION_NOT_A_PURE_CAPITAL_RANKING_DEFECT`

## Evidence Incompleteness

High-value ADD evidence-incomplete rows:

- Total BUY_ADD rows with `HIGH_VALUE_EVIDENCE_INCOMPLETE`: 40
- Primary displacement rows in this class: 22
- Missing input in all 22 primary rows: `opportunity_quality_insufficient`

Owning boundary: DQ unified marginal capital evaluator / Portfolio Construction ADD investment evidence materialization. The SHADOW comparator currently allows an incomplete high-value ADD state to win the daily ranking even though the row is not complete enough to be accepted as Production-grade marginal capital authority.

`HIGH_VALUE_ADD_EVIDENCE_INCOMPLETENESS_ROOT_CAUSE = ADD_OPPORTUNITY_QUALITY_EVIDENCE_NOT_FULLY_MATERIALIZED_FOR_DQ_COMPARISON; OWNER=DQ_SHADOW_EVALUATOR_AND_PC_ADD_EVIDENCE_MATERIALIZATION`

## Campaign Graduation

DT summary:

- campaigns with ADD SHADOW rows: 17
- repeated ADD SHADOW campaigns: 14

Top repeated campaigns:

| Campaign | ADD shadow rows | Production ADD selected |
| --- | ---: | ---: |
| 94320 / pc-7c5bd9294d48b016-94320-0001 | 35 | 6 |
| 99840 / pc-5a5765b1c257b5b8-99840-0001 | 18 | 0 |
| 94320 / pc-401763653bc4df1d-94320-0001 | 15 | 1 |
| 94340 / pc-8d0b3d71adb1e835-94340-0001 | 14 | 0 |
| 83060 / pc-090162015342d58a-83060-0001 | 12 | 0 |

Repeated strength does not automatically graduate into increased capital because ADD still passes through separate feasibility, lot, BQ/entry compression, concentration/headroom, and evidence-completeness gates. Production has no fully unified next-dollar comparator that can say "this ADD beats the next NEW/REENTRY/cash use" after those gates are normalized.

`CAMPAIGN_GRADUATION_NEUTRALITY_PROFILE = IMPLICIT_AND_PARTIAL; REPEATED_ADD_SIGNAL_EXISTS_BUT_GRADUATION_IS_NOT_ACTION_NEUTRAL`

## 94320 Positive Control

94320 is the positive control that proves Production can fund ADD under some circumstances:

- 94320 total ADD shadow rows observed in this audit: 50 across two campaign families
- Production ADD selected rows: 7
- largest DT summary campaign: 35 ADD shadow rows / 6 Production ADD selected

What allowed 94320 to win capital: it appears in states where Production ADD survived the existing PC/BQ/lot/capital gates. But even for 94320, DT shows many ADD rows as low or medium, lot-infeasible, or concentration-blocked, and only two 94320 SHADOW ADD wins in the primary displacement shape.

`94320_NEUTRALITY_CONTROL = POSITIVE_CONTROL_PASS_FOR_PRODUCTION_ADD_CAPABILITY; NOT_PROOF_OF_GLOBAL_ACTION_NEUTRALITY`

## Failed-Graduation Controls

Observed controls:

- 99840: 26 ADD rows, 3 SHADOW wins, 2 Production ADD selected. Its primary SHADOW wins are high-value-evidence-incomplete, lot-infeasible, and concentration-blocked.
- 94340: 20 ADD rows, 7 SHADOW wins, 4 Production ADD selected. Its primary late-window wins are high-value-evidence-incomplete, lot-infeasible, and concentration-blocked.
- 83060: 15 ADD rows, 0 SHADOW wins, 0 Production ADD selected. Most rows are low/infeasible/concentration-blocked, with only two medium/complete/feasible rows still blocked by concentration.

These failed controls are not explained by a single fixed "ADD never wins" rule. The current root profile is a combination of incomplete ADD quality evidence, lot granularity, concentration/headroom, and lack of a Production-grade unified marginal comparator.

`FAILED_GRADUATION_ROOT_CAUSE_PROFILE = MIXED_LOT_CONCENTRATION_EVIDENCE_INCOMPLETENESS_AND_NO_PRODUCTION_UNIFIED_NEXT_CAPITAL_AUTHORITY`

## Production Cash Behavior

Cash-related divergences:

- Production NEW_OR_REENTRY / SHADOW Cash: 85
- Production ADD / SHADOW Cash: 8
- Production Cash / SHADOW REENTRY: 3

SHADOW Cash winner states:

- 93 `MEDIUM_VALUE + COMPLETE + FEASIBLE + LOW_COST`
- 1 `HIGH_VALUE + INCOMPLETE + FEASIBLE + EVIDENCE_INCOMPLETE`

This is a major calibration warning. It may mean Production overdeploys capital, SHADOW Cash is too conservative, or the current score normalization over-rewards optionality relative to funded securities. It must be repaired or validated before DQ promotion.

`SHADOW_CASH_CALIBRATION_STATUS = UNRESOLVED_MATERIAL_CALIBRATION_RISK`

## DQ SHADOW Quality

The DQ SHADOW is useful as a diagnostic tool because it exposes one-year action competition and preserves dual provenance. It is not ready for Production promotion because:

- 23 ADD winners exist, but 23/23 are high-value-evidence-incomplete, lot-infeasible, and concentration-blocked.
- 94 Cash winners create major calibration questions.
- 55 REENTRY winners are incomplete and lot-infeasible.
- SHADOW can rank incomplete/infeasible rows above actual funded rows.

`DQ_SHADOW_DECISION_QUALITY = PROMISING_BUT_NEEDS_REPAIR`

## Primary Winner-Capitalization Root Cause

Ranked by DU evidence:

1. `LOT_GRANULARITY` - 128/152 ADD rows are infeasible due to 100-share lot conversion; all 22 primary ADD displacement winners have next executable quantity 0.
2. `EVIDENCE_INCOMPLETENESS` - 40 ADD rows are high-value evidence-incomplete; all 22 primary displacement winners miss `opportunity_quality_insufficient`.
3. `CONCENTRATION_HEADROOM` - all 152 ADD rows are blocked by concentration; material but not proven overrestrictive.
4. `CAMPAIGN_GRADUATION_IMPLICITNESS` - repeated ADD signals do not become a unified graduation authority.
5. `CASH_OPTIONALITY_CALIBRATION` - 94 SHADOW Cash wins and 93 medium/complete/feasible/low-cost Cash wins need calibration before promotion.
6. `UNIFIED_MARGINAL_RANKING_GAP` - Production still does not have a single authoritative next-capital-unit comparator across NEW/REENTRY/ADD/Cash.

`PRIMARY_WINNER_CAPITALIZATION_ROOT_CAUSE = LOT_GRANULARITY_PLUS_EVIDENCE_INCOMPLETENESS_PLUS_CONCENTRATION_HEADROOM_WITH_MISSING_PRODUCTION_UNIFIED_MARGINAL_AUTHORITY`

## Core Judgment

The one-year DT backfill does not support a simple conclusion that Production repeatedly rejected clean feasible strong ADDs in favor of weaker NEW/REENTRY/Cash. The cleanest strong-ADD miss count is zero.

It also does not support saying Production is action-neutral. Agreement is only 76/264, and repeated ADD candidates often fail to become funded capital because the system lacks a Production-grade unified marginal capital authority that normalizes feasibility, completeness, concentration, and Cash before comparing action labels.

`STRONGEST_MARGINAL_OPPORTUNITY_RECEIVES_CAPITAL = PARTIAL`

`CURRENT_PRODUCTION_CAPITAL_ALLOCATION_PHILOSOPHY_ALIGNMENT = PARTIAL; PHILOSOPHY_NOT_FULLY_IMPLEMENTED_AS_SINGLE_NEXT_CAPITAL_UNIT_AUTHORITY`

## Repair / Promotion Readiness

No Production change should be made directly from DU. The next repair must improve the SHADOW/evidence contract first, especially:

- do not allow incomplete evidence to rank as Production-grade strongest opportunity
- do not allow infeasible next-lot rows to count as clean next-capital winners
- separate concentration-blocked from genuinely available headroom
- calibrate Cash optionality against deployable security opportunities
- make campaign graduation explicit without adding a fixed ADD preference

`PRODUCTION_REPAIR_REQUIRED = CONDITIONAL`

`DQ_PRODUCTION_PROMOTION_READINESS = NOT_READY`

`NEXT_RECOMMENDED_ARCHITECTURE_STEP = SHADOW_EVALUATOR_AND_EVIDENCE_COMPLETENESS_REPAIR_BEFORE_ANY_PRODUCTION_CAPITAL_VALUE_AUTHORITY_INTEGRATION`

## Prohibitions Confirmation

- Historical PnL/future return used for judgment: no
- Fixed ADD preference recommended: no
- Production change executed: no
- Target source run mutated: no
- Runtime state mutated: no
- Long runtime executed: no

## Required Final Answers

1. `DT_BACKFILL_ACCEPTED_FOR_DU_ANALYSIS = YES`
2. `PRODUCTION_SHADOW_NEUTRALITY_PROFILE = PARTIAL_NON_NEUTRAL_WITH_MATERIAL_SHADOW_RELIABILITY_LIMITS`
3. `STRONG_ADD_DISPLACEMENT_CLASSIFICATION = D_ADD_HIGH_VALUE_BUT_EVIDENCE_INCOMPLETE:22; A/B/C/E/F:0`
4. `FEASIBLE_STRONG_ADD_MISSED_FOR_NEW_REENTRY = 0`
5. `FEASIBLE_STRONG_ADD_MISSED_FOR_CASH = 0`
6. `NEW_VS_ADD_RELATIVE_STRENGTH_PROFILE = NOT_COMPARABLE_IN_PRIMARY_DISPLACEMENTS_DUE_TO_ADD_INCOMPLETE_LOT_INFEASIBLE_CONCENTRATION_BLOCKED`
7. `REENTRY_VS_ADD_RELATIVE_STRENGTH_PROFILE = REENTRY_PATH_MATURE_AND_OFTEN_COMPETITIVE; CLEAN_REENTRY_OVER_FEASIBLE_ADD_MISS_NOT_CONFIRMED`
8. `BULL_RECOVERY_WINNER_CAPITALIZATION_GAP = PARTIAL`
9. `BEAR_CAPITAL_ALLOCATION_NEUTRALITY = PARTIAL; NO_CLEAN_STRONG_ADD_MISS_CONFIRMED`
10. `CONCENTRATION_HEADROOM_IMPACT_ON_STRONG_ADD = MATERIAL_CONSTRAINT_NOT_YET_PROVEN_OVERRESTRICTIVE`
11. `LOT_GRANULARITY_IMPACT_ON_WINNER_CAPITALIZATION = MATERIAL_EXECUTION_LIMITATION_NOT_A_PURE_CAPITAL_RANKING_DEFECT`
12. `HIGH_VALUE_ADD_EVIDENCE_INCOMPLETENESS_ROOT_CAUSE = ADD_OPPORTUNITY_QUALITY_EVIDENCE_NOT_FULLY_MATERIALIZED_FOR_DQ_COMPARISON`
13. `CAMPAIGN_GRADUATION_NEUTRALITY_PROFILE = IMPLICIT_AND_PARTIAL`
14. `94320_NEUTRALITY_CONTROL = POSITIVE_CONTROL_PASS_FOR_PRODUCTION_ADD_CAPABILITY; NOT_PROOF_OF_GLOBAL_ACTION_NEUTRALITY`
15. `FAILED_GRADUATION_ROOT_CAUSE_PROFILE = MIXED_LOT_CONCENTRATION_EVIDENCE_INCOMPLETENESS_AND_NO_PRODUCTION_UNIFIED_NEXT_CAPITAL_AUTHORITY`
16. `SHADOW_CASH_CALIBRATION_STATUS = UNRESOLVED_MATERIAL_CALIBRATION_RISK`
17. `DQ_SHADOW_DECISION_QUALITY = PROMISING_BUT_NEEDS_REPAIR`
18. `PRIMARY_WINNER_CAPITALIZATION_ROOT_CAUSE = LOT_GRANULARITY_PLUS_EVIDENCE_INCOMPLETENESS_PLUS_CONCENTRATION_HEADROOM_WITH_MISSING_PRODUCTION_UNIFIED_MARGINAL_AUTHORITY`
19. `STRONGEST_MARGINAL_OPPORTUNITY_RECEIVES_CAPITAL = PARTIAL`
20. `CURRENT_PRODUCTION_CAPITAL_ALLOCATION_PHILOSOPHY_ALIGNMENT = PARTIAL`
21. `PRODUCTION_REPAIR_REQUIRED = CONDITIONAL`
22. `DQ_PRODUCTION_PROMOTION_READINESS = NOT_READY`
23. `NEXT_RECOMMENDED_ARCHITECTURE_STEP = SHADOW_EVALUATOR_AND_EVIDENCE_COMPLETENESS_REPAIR_BEFORE_ANY_PRODUCTION_CAPITAL_VALUE_AUTHORITY_INTEGRATION`
24. `FUTURE_OUTCOME_USED_FOR_JUDGMENT = NO`
25. `FIXED_ADD_PREFERENCE_RECOMMENDED = NO`
26. `PRODUCTION_CHANGE_EXECUTED = NO`
27. `TARGET_RUN_MUTATED = NO`
28. `RUNTIME_STATE_MUTATED = NO`
29. `LONG_RUNTIME_EXECUTED = NO`
30. `FINAL_JUDGMENT = PHASE32_DU_STRONGEST_MARGINAL_OPPORTUNITY_PARTIAL_SHADOW_NOT_READY_FOR_PRODUCTION_PROMOTION`

## Final Judgment

`PHASE32_DU_STRONGEST_MARGINAL_OPPORTUNITY_PARTIAL_SHADOW_NOT_READY_FOR_PRODUCTION_PROMOTION`
