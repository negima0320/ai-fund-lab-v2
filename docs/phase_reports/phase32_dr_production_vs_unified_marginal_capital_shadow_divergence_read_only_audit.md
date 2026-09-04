# Phase32-DR — Production vs Unified Marginal Capital SHADOW Divergence READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Audit type: READ-ONLY
- Valid DQ SHADOW schema: `unified_marginal_capital_shadow.v1`
- Valid SHADOW artifact path: `daily/<business_date>/strategy/portfolio_construction.json` under `capital_competition.unified_marginal_capital_shadow`
- Production change executed: NO
- Target run mutated: NO
- Fresh-run/resume/recover/replay/long runtime executed by Codex: NO
- Future outcome / later PnL used for divergence judgment: NO

Mandatory references read:

- `docs/phase_reports/phase32_dq_unified_marginal_capital_authority_shadow_implementation.md`
- `docs/phase_reports/phase32_dp_winner_capitalization_unified_marginal_capital_allocation_deep_dive_shadow_audit.md`
- `docs/phase_reports/phase32_do_post_cw_dg_one_year_growth_persistence_capital_utilization_read_only_audit.md`
- Current Portfolio Construction / Capital Value Authority source locations:
  - `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
  - `src/ai_fund_lab_v2/strategy/portfolio_construction.py`

Run-state identity at inspection:

- `status = RUNNING`
- `next_job = 2023-11-15:market_refresh`
- `profile_id = historical-extended-smoke`
- run-captured source commit: `a56f2bc26105eb14fd67322b7cd53c0d6ef1b1bd`
- run-captured source dirty: `true`
- current workspace HEAD during this audit: `1f64f49ee9a8dd48280007e4df656e5f03e231ca`

The workspace source is ahead of the run-captured baseline. This audit therefore uses the target run's already-materialized artifacts for Production-vs-SHADOW findings, and current source only to confirm the DQ contract shape. No source behavior is inferred into already-completed run dates.

## Evidence Sufficiency

Valid post-DQ SHADOW artifacts were found only for:

| Business date | Candidate count | Competitor profile | Production-vs-SHADOW result |
|---|---:|---|---|
| `2023-11-10` | 56 | `REENTRY_NEXT_LOT=55`, `CASH_OPTIONALITY=1` | `AGREEMENT` |
| `2023-11-13` | 43 | `BUY_NEW_NEXT_LOT=2`, `REENTRY_NEXT_LOT=40`, `CASH_OPTIONALITY=1` | `AGREEMENT` |
| `2023-11-14` | 42 | `REENTRY_NEXT_LOT=41`, `CASH_OPTIONALITY=1` | `Production NEW_OR_REENTRY / SHADOW REENTRY` |

Aggregate competitor rows:

| Competitor type | Count |
|---|---:|
| `REENTRY_NEXT_LOT` | 136 |
| `BUY_NEW_NEXT_LOT` | 2 |
| `BUY_ADD_NEXT_LOT` | 0 |
| `CASH_OPTIONALITY` | 3 |
| Total | 141 |

`DQ_SHADOW_EVIDENCE_SUFFICIENCY = INSUFFICIENT`

The evidence is sufficient to confirm that the DQ artifact is being materialized and that Production comparison metadata is populated. It is not sufficient for a production decision because the available window contains only 3 SHADOW competition sets, only 2 BUY_NEW rows, no BUY_ADD rows, no actual ADD-vs-NEW/REENTRY/Cash divergence, and no broad regime coverage.

## Agreement Profile

| Metric | Count |
|---|---:|
| Total comparison sets | 3 |
| Agreement | 2 |
| Divergence | 1 |
| Agreement rate | 66.7% |
| Divergence rate | 33.3% |

Observed Production winners:

- `CASH_OPTIONALITY`: 1 set (`2023-11-10`)
- `NEW_BUY`: 3 funded rows across 2 dates (`38520`, `44140`, `83060`)

Observed SHADOW winners:

- `CASH_OPTIONALITY`: 1 set (`2023-11-10`)
- `BUY_NEW_NEXT_LOT`: 1 set (`2023-11-13`, `38520`)
- `REENTRY_NEXT_LOT`: 1 set (`2023-11-14`, `70110`)

`PRODUCTION_SHADOW_AGREEMENT_PROFILE = 3_SETS; AGREEMENT_2; DIVERGENCE_1; AGREEMENT_RATE_66.7_PERCENT`

## Divergence Classes

| Divergence class | Count |
|---|---:|
| `AGREEMENT` | 2 |
| Production NEW -> SHADOW ADD | 0 |
| Production REENTRY -> SHADOW ADD | 0 |
| Production Cash -> SHADOW ADD | 0 |
| Production ADD -> SHADOW NEW | 0 |
| Production ADD -> SHADOW REENTRY | 0 |
| Production security -> SHADOW Cash | 0 |
| Production Cash -> SHADOW NEW | 0 |
| Production Cash -> SHADOW REENTRY | 0 |
| Same action family, different symbol/order | 0 |
| Production NEW_OR_REENTRY -> SHADOW REENTRY | 1 |

`DIVERGENCE_CLASS_PROFILE = AGREEMENT_2; PRODUCTION_NEW_OR_REENTRY_TO_SHADOW_REENTRY_1; ADD_DIVERGENCE_NOT_OBSERVED`

The only observed divergence is `2023-11-14`: Production funded `83060` as `NEW_BUY`, while SHADOW winner was `70110` as `REENTRY_NEXT_LOT`. The SHADOW winner was still `INCOMPLETE`, `INFEASIBLE_DUE_TO_LOT`, and `BLOCKED_BY_CONCENTRATION`, so this does not establish that Production failed to fund a feasible stronger opportunity.

## Strong ADD Lost Cases

No `BUY_ADD_NEXT_LOT` rows exist in valid post-DQ SHADOW artifacts.

`STRONG_ADD_LOST_TO_NEW_CASES = NOT_OBSERVED`

`STRONG_ADD_LOST_TO_REENTRY_CASES = NOT_OBSERVED`

`STRONG_ADD_LOST_TO_CASH_CASES = NOT_OBSERVED`

This is an evidence gap, not evidence that ADD competition is healthy. The DR central question specifically requires actual ADD competitors and ADD-related divergences; neither is present in the valid post-DQ window.

## ADD Value vs Feasibility

| ADD SHADOW bucket | Count |
|---|---:|
| `HIGH_VALUE + FEASIBLE` | 0 |
| `HIGH_VALUE + BLOCKED_BY_CONCENTRATION` | 0 |
| `HIGH_VALUE + INFEASIBLE_DUE_TO_LOT` | 0 |
| `HIGH_VALUE + EVIDENCE_INCOMPLETE` | 0 |
| `MEDIUM_VALUE + FEASIBLE` | 0 |
| `LOW_VALUE` | 0 |

`ADD_VALUE_FEASIBILITY_PROFILE = NO_BUY_ADD_NEXT_LOT_ROWS_OBSERVED`

`HIGH_VALUE_ADD_BLOCKED_BY_CONCENTRATION_MATERIALITY = NOT_OBSERVED`

`HIGH_VALUE_ADD_BQ_ENTRY_COMPRESSION = INSUFFICIENT_EVIDENCE`

The valid post-DQ window contains many REENTRY rows with incomplete evidence, lot infeasibility, and concentration blocking. That cannot be substituted for ADD evidence.

## Neutrality Checks

### NEW

`2023-11-13` contains two Production `NEW_BUY` funded rows, `38520` and `44140`. SHADOW also selected `38520` as the winning security competitor. This is a clean local agreement case for NEW funding, but the sample is too small to judge structural NEW neutrality.

`PRODUCTION_NEW_CAPITAL_NEUTRALITY = PRELIMINARY_CLEAN_IN_AVAILABLE_EVIDENCE; INSUFFICIENT_FOR_STRUCTURAL_JUDGMENT`

### REENTRY

The window contains 136 `REENTRY_NEXT_LOT` competitors and one SHADOW REENTRY winner (`70110` on `2023-11-14`). Production did not fund that SHADOW REENTRY winner; however the SHADOW row was incomplete, lot-infeasible, and concentration-blocked. This is not enough to classify a Production REENTRY neutrality defect.

`PRODUCTION_REENTRY_CAPITAL_NEUTRALITY = INSUFFICIENT_EVIDENCE; ONE_DIVERGENCE_NOT_FEASIBLE_COMPLETE_ENOUGH_TO_PROVE_DEFECT`

### Cash

`2023-11-10` is a Production Cash and SHADOW Cash agreement. The cash winner carried incomplete evidence / fail-closed reason codes and no valid competitor, so Cash was not observed suppressing a feasible high-value security competitor in the valid DQ window.

`PRODUCTION_CASH_CAPITAL_NEUTRALITY = PRELIMINARY_CLEAN_FOR_ONE_CASH_WIN; INSUFFICIENT_FOR_STRUCTURAL_JUDGMENT`

## Regime Divergence

The valid DQ SHADOW sets all carry `CAUTIOUS_DEPLOYMENT` risk-pacing context in the inspected cash/risk evidence. No BULL, RECOVERY, RANGE, CORRECTION, or BEAR-diverse comparison profile is available from valid post-DQ artifacts.

| Regime / risk context | Agreement | Divergence |
|---|---:|---:|
| `CAUTIOUS_DEPLOYMENT` | 2 | 1 |

`REGIME_DIVERGENCE_PROFILE = INSUFFICIENT_EVIDENCE; ONLY_CAUTIOUS_DEPLOYMENT_CONTEXT_OBSERVED`

No conclusion can be drawn about BULL excessive NEW deployment, BEAR suppression of incumbent ADD, or Cash dominance across weak-opportunity periods.

## Campaign Graduation

No valid post-DQ `BUY_ADD_NEXT_LOT` rows were observed. Therefore repeated high-value ADD opportunities, ADD fills from SHADOW-selected opportunities, cap-blocked ADD cases, BQ/Entry-blocked ADD cases, and Production NEW/REENTRY/Cash displacement of ADD cannot be audited on actual DQ artifacts yet.

`CAMPAIGN_GRADUATION_GAP_PROFILE = INSUFFICIENT_EVIDENCE; NO_ADD_COMPETITOR_ROWS_IN_VALID_DQ_WINDOW`

`SUCCESSFUL_GRADUATION_SHADOW_CONTROL = INSUFFICIENT_EVIDENCE`

Some rows, such as `94320` and `94340` on `2023-11-10`, appear in SHADOW with continuation-like Entry actions (`ADD_REDUCED_ONLY`) but are typed as `REENTRY_NEXT_LOT` in the DQ artifact and remain incomplete/infeasible/concentration-blocked. They are not valid successful ADD graduation controls for DR.

## Root Cause Classification

Available post-DQ evidence does not establish a material Production capital-allocation gap. The stronger statement is that the DQ SHADOW observation window has not yet reached the capital-allocation situations DR was designed to test.

`PRIMARY_CAPITAL_ALLOCATION_GAP = INSUFFICIENT_EVIDENCE`

Ranked observations:

1. `INSUFFICIENT_EVIDENCE`: only 3 valid DQ sets and zero ADD competitors.
2. `NO_MATERIAL_GAP_OBSERVED`: no feasible high-value ADD was observed losing to NEW/REENTRY/Cash.
3. `REENTRY_SEMANTIC_ASYMMETRY`: one Production NEW-vs-SHADOW REENTRY divergence exists, but it is not complete/feasible enough to prove a defect.

No cap/headroom, BQ/Entry compression, lot granularity, Cash optionality, or unified-ranking gap can be promoted from hypothesis to confirmed DR root cause using this evidence alone.

## Core Judgment

`STRONGEST_MARGINAL_OPPORTUNITY_RECEIVES_CAPITAL = INSUFFICIENT_EVIDENCE`

The available evidence is directionally useful but too thin. Production and SHADOW agree on 2 of 3 sets. The only divergence does not show Production ignoring a complete, feasible, stronger opportunity. Most importantly, there are no `BUY_ADD_NEXT_LOT` competitors, so the winner-capitalization / ADD-neutrality question remains untested in actual post-DQ artifacts.

## Promotion Readiness

`DQ_PRODUCTION_PROMOTION_READINESS = MORE_SHADOW_EVIDENCE_REQUIRED`

DQ should not be promoted on this evidence. The correct next validation requires more user-operated run coverage until valid post-DQ SHADOW artifacts include:

- actual `BUY_ADD_NEXT_LOT` competitors,
- at least several Production NEW / REENTRY / Cash vs SHADOW ADD comparison opportunities,
- at least one successful ADD graduation control if naturally present,
- broader risk/regime contexts beyond the current cautious-deployment sample,
- enough divergences to identify a concrete authority boundary rather than a sampling artifact.

`PROPOSED_PRODUCTION_REPAIR_SCOPE = NONE_CONFIRMED; CONTINUE_SHADOW_EVIDENCE_COLLECTION_AND_RERUN_DIVERGENCE_AUDIT`

No Production repair scope is justified from DR evidence yet. In particular, no fixed ADD preference, NEW penalty, REENTRY penalty, regime shortcut, concentration cap change, or exposure/position-count tuning is recommended.

## Required Final Answers

1. `DQ_SHADOW_EVIDENCE_SUFFICIENCY = INSUFFICIENT`
2. `PRODUCTION_SHADOW_AGREEMENT_PROFILE = 3_SETS; AGREEMENT_2; DIVERGENCE_1; AGREEMENT_RATE_66.7_PERCENT`
3. `DIVERGENCE_CLASS_PROFILE = AGREEMENT_2; PRODUCTION_NEW_OR_REENTRY_TO_SHADOW_REENTRY_1; ADD_DIVERGENCE_NOT_OBSERVED`
4. `STRONG_ADD_LOST_TO_NEW_CASES = NOT_OBSERVED`
5. `STRONG_ADD_LOST_TO_REENTRY_CASES = NOT_OBSERVED`
6. `STRONG_ADD_LOST_TO_CASH_CASES = NOT_OBSERVED`
7. `ADD_VALUE_FEASIBILITY_PROFILE = NO_BUY_ADD_NEXT_LOT_ROWS_OBSERVED`
8. `HIGH_VALUE_ADD_BLOCKED_BY_CONCENTRATION_MATERIALITY = NOT_OBSERVED`
9. `HIGH_VALUE_ADD_BQ_ENTRY_COMPRESSION = INSUFFICIENT_EVIDENCE`
10. `PRODUCTION_NEW_CAPITAL_NEUTRALITY = PRELIMINARY_CLEAN_IN_AVAILABLE_EVIDENCE; INSUFFICIENT_FOR_STRUCTURAL_JUDGMENT`
11. `PRODUCTION_REENTRY_CAPITAL_NEUTRALITY = INSUFFICIENT_EVIDENCE; ONE_DIVERGENCE_NOT_FEASIBLE_COMPLETE_ENOUGH_TO_PROVE_DEFECT`
12. `PRODUCTION_CASH_CAPITAL_NEUTRALITY = PRELIMINARY_CLEAN_FOR_ONE_CASH_WIN; INSUFFICIENT_FOR_STRUCTURAL_JUDGMENT`
13. `REGIME_DIVERGENCE_PROFILE = INSUFFICIENT_EVIDENCE; ONLY_CAUTIOUS_DEPLOYMENT_CONTEXT_OBSERVED`
14. `CAMPAIGN_GRADUATION_GAP_PROFILE = INSUFFICIENT_EVIDENCE; NO_ADD_COMPETITOR_ROWS_IN_VALID_DQ_WINDOW`
15. `SUCCESSFUL_GRADUATION_SHADOW_CONTROL = INSUFFICIENT_EVIDENCE`
16. `FUTURE_OUTCOME_USED_FOR_DIVERGENCE_JUDGMENT = NO`
17. `PRIMARY_CAPITAL_ALLOCATION_GAP = INSUFFICIENT_EVIDENCE`
18. `STRONGEST_MARGINAL_OPPORTUNITY_RECEIVES_CAPITAL = INSUFFICIENT_EVIDENCE`
19. `DQ_PRODUCTION_PROMOTION_READINESS = MORE_SHADOW_EVIDENCE_REQUIRED`
20. `PROPOSED_PRODUCTION_REPAIR_SCOPE = NONE_CONFIRMED; CONTINUE_SHADOW_EVIDENCE_COLLECTION_AND_RERUN_DIVERGENCE_AUDIT`
21. `FIXED_ADD_PREFERENCE_RECOMMENDED = NO`
22. `PRODUCTION_CHANGE_EXECUTED = NO`
23. `TARGET_RUN_MUTATED = NO`
24. `LONG_RUNTIME_EXECUTED = NO`
25. `NEXT_RECOMMENDED_STEP = CONTINUE_USER_OPERATED_TARGET_RUN_UNTIL_VALID_DQ_SHADOW_WINDOW_CONTAINS_ADD_COMPETITORS_AND_ACTION_NEUTRAL_DIVERGENCES; THEN_RERUN_DR_OR_SUCCESSOR_READ_ONLY_AUDIT`
26. `FINAL_JUDGMENT = PHASE32_DR_POST_DQ_SHADOW_DIVERGENCE_AUDIT_INSUFFICIENT_EVIDENCE_MORE_SHADOW_REQUIRED`

## Final Judgment

`PHASE32_DR_POST_DQ_SHADOW_DIVERGENCE_AUDIT_INSUFFICIENT_EVIDENCE_MORE_SHADOW_REQUIRED`

The DQ SHADOW artifact is present and usable, and the available 3-set sample does not show a concrete Production allocation defect. But it also does not exercise the central DR question: no ADD competitor appears in the valid post-DQ window, so the system has not yet produced evidence that can confirm or falsify whether Production sends scarce capital to the strongest ADD-vs-NEW-vs-REENTRY-vs-Cash marginal opportunity.
