# Phase32-CY — Winner ADD Marginal Capital Competition / Capitalization READ-ONLY Audit

## Scope

This is a READ-ONLY audit.

No Strategy, threshold, model, score, sizing, config, runtime state, Pending,
Ledger, run artifact, resume, recover, replay, fresh-run, or long Historical
command was modified or executed.

Primary run:

```text
runtime-test-historical-extended-smoke-20260901T223409325599Z
```

Audit snapshot:

```text
run_status = RUNNING
source_commit = a56f2bc26105eb14fd67322b7cd53c0d6ef1b1bd
completed_business_days_used = 113
first_completed_date_used = 2022-10-03
LATEST_COMPLETED_DATE_USED = 2023-03-17
next_job_at_snapshot = 2023-03-20:data_readiness
```

The run was active while this audit was performed. The report freezes the
evidence set at the above snapshot.

## References Read

- `docs/phase_reports/phase31_g129_buy_add_actual_path_narrow_repair.md`
- `docs/phase_reports/phase32_ch_post_april_plateau_root_cause_winner_capitalization_funnel_read_only_audit.md`
- `docs/phase_reports/phase32_ci_new_reentry_add_action_type_bias_post_april_opportunity_capture_root_cause_audit.md`
- `docs/phase_reports/phase32_cw_minimal_residual_reentry_unknown_context_production_repair.md`
- `docs/phase_reports/phase32_cx_reentry_suppression_accumulation_vs_long_horizon_growth_decay_read_only_audit.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/runtime_architecture_v2.md`

Source paths inspected:

- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `src/ai_fund_lab_v2/strategy/runtime_planning.py`
- `src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py`

## Architecture Baseline

Current SoT says Portfolio Construction already owns NEW_BUY / BUY_ADD / Cash
capital competition. BUY_ADD is not entitled to capital because it is an ADD,
and BUY_NEW is not entitled to capital because it is NEW. Strong ADD may outrank
weaker or comparable NEW only when PIT lifecycle evidence supports it.

The accepted current limitation is not absence of capital competition. It is
that NEW_BUY, BUY_ADD, Cash, and future rotation do not yet share a common
high-resolution marginal capital value unit. The high-resolution marginal
capital value document records this as a future architecture capability, not a
current correctness defect.

BUY_ADD canonical chain remains:

```text
PM ADD
-> canonical position decision
-> Portfolio Construction target/increment authority
-> Position Sizing positive quantity_delta_candidate
-> Runtime Planning BUY_ADD
-> Pending / Approval / Submit
-> Execution
```

Runtime must not re-rank, re-size, or infer BUY_ADD from PM ADD alone.

## BUY_ADD Actual Path Map

Actual completed-run evidence confirms BUY_ADD can still traverse the full
Production path after CW:

| Date | Symbol | Campaign | Qty | Notional |
|---|---|---|---:|---:|
| 2022-10-06 | 94340 | pc-674562547125d12f-94340-0001 | 100 | 14,780 |
| 2022-10-12 | 94340 | pc-674562547125d12f-94340-0001 | 100 | 14,640 |
| 2022-10-13 | 94340 | pc-674562547125d12f-94340-0001 | 100 | 14,570 |
| 2022-11-01 | 94320 | pc-f97f5131b256d0c5-94320-0001 | 100 | 16,390 |
| 2023-01-31 | 94320 | pc-56fe03f336dc0c03-94320-0001 | 100 | 15,680 |
| 2023-02-13 | 94320 | pc-56fe03f336dc0c03-94320-0001 | 100 | 15,370 |
| 2023-02-15 | 54010 | pc-2af0ce1c2a7bbed4-54010-0001 | 100 | 58,640 |
| 2023-02-22 | 94320 | pc-56fe03f336dc0c03-94320-0001 | 100 | 15,860 |
| 2023-02-24 | 94320 | pc-56fe03f336dc0c03-94320-0001 | 100 | 15,760 |
| 2023-03-15 | 94320 | pc-56fe03f336dc0c03-94320-0001 | 100 | 15,840 |

`BUY_ADD_ACTUAL_PATH_MAP = PM_ADD_TO_PC_TO_PS_TO_RUNTIME_TO_FILL_CONFIRMED_FOR_10_FILLS`

## BUY_ADD Funnel

Completed snapshot funnel:

| Stage | Count |
|---|---:|
| Runtime PM ADD observations | 104 |
| Canonical PC ADD rows | 104 |
| ADD capital competitors | 104 |
| Selected positive ADD competitors | 12 |
| Authorized ADD increment rows | 12 |
| PS positive ADD quantity delta | 12 |
| Runtime BUY_ADD plans | 12 |
| BUY_ADD fills | 10 |
| BUY_ADD notional | 197,530 |
| BUY_NEW fills | 186 |
| BUY_NEW notional | 11,552,310 |
| REENTRY fills | 0 |

Two authorized/planned BUY_ADD cases were not counted as completed fills in the
frozen execution evidence. No contradiction with G129 was found in completed
BUY_ADD fills.

`BUY_ADD_FUNNEL = THIN_BUT_FUNCTIONAL`

## First Blocker Distribution

For canonical PC ADD rows that did not become same-day BUY_ADD plans, the first
materialized blocker distribution was:

| First blocker | Count | Classification |
|---|---:|---|
| ADD eligibility fail-closed / ADD no positive authority | 48 | legitimate |
| BUY Quality blocks incremental ADD | 32 | legitimate |
| ADD lost to NEW_BUY / no positive ADD delta | 6 | potentially unfair or semantic-gap |
| PS lot or cap infeasible | 6 | legitimate |

Additional authority-row evidence:

| Authority row class | Count |
|---|---:|
| LOT_INFEASIBLE | 2 |
| CAP_HEADROOM_INSUFFICIENT | 0 |
| CASH / residual cash preferred | 36 |

`BUY_ADD_FIRST_BLOCKER_DISTRIBUTION = ADD_ELIGIBILITY_48, BUY_QUALITY_32, ADD_LOST_TO_NEW_BUY_6, PS_LOT_OR_CAP_6`

`LEGITIMATE_ADD_BLOCK_COUNT = 86`

`POTENTIALLY_UNFAIR_ADD_BLOCK_COUNT = 6`

The 6 potentially unfair rows are not accepted as proven unfair Production
mistakes. They are the rows where current artifacts show ADD losing to NEW_BUY
or collapsing to no positive ADD delta despite PM ADD context. They require a
common marginal-capital semantic to decide whether the held-position increment
was actually stronger than the funded starter.

## Marginal Capital Semantics

`CURRENT_MARGINAL_CAPITAL_SEMANTIC_GAP = PRESENT_AS_ARCHITECTURE_LIMITATION_NOT_CONFIRMED_CORRECTNESS_DEFECT`

Reason:

- Current source exposes `marginal_capital_value` classes and priority ordering.
- PC includes ADD-vs-NEW-vs-Cash competition and staged ADD increment authority.
- The high-resolution SoT explicitly says a common next-executable-increment
  value unit is future work.
- Existing `runtime_opportunity_score` is evidence, not a calibrated expected
  return, yen value, or action-neutral marginal capital unit.

`ACTION_TYPE_CAPITAL_SCORE_SEMANTICS = PARTIAL_COMPARABILITY_ONLY`

BUY_NEW, BUY_ADD, and REENTRY all surface PIT opportunity/rank/quality evidence,
but action-specific gates remain different. Score-only cross-action comparison
is not valid authority.

## Winner Evidence Consumption

Existing winner / continuation evidence currently consumed by ADD competition
includes:

- PM ADD directional intent;
- current position and campaign id;
- BUY Quality action;
- continuation/downside evidence where materialized;
- incremental investment value status;
- opportunity-cost status;
- current weight, target weight, accepted increment;
- lot, cap, and cash feasibility;
- capital competition reason codes;
- G129 order-increment authority downstream.

`EXISTING_WINNER_DECISION_TIME_EVIDENCE = AVAILABLE_AND_PARTIALLY_CONSUMED`

`WINNER_EVIDENCE_CONSUMED_BY_CAPITAL_COMPETITION = YES_PARTIAL`

The evidence is consumed enough to authorize real BUY_ADD fills. It is not yet
resolved into a high-resolution action-neutral next-lot value.

## ADD vs NEW / REENTRY Competition Cases

Same-day NEW-vs-ADD competition was present on 76 completed dates. BUY_ADD won
and filled 10 times; NEW_BUY filled 186 times. REENTRY filled 0 times in this
snapshot, so post-CW REENTRY/ADD capital interaction remains early-path
insufficient for final long-horizon acceptance.

`ADD_VS_NEW_REENTRY_COMPETITION_CASES = NEW_VS_ADD_76_DATES, REENTRY_FILL_0`

`STRONG_WINNER_TO_WEAKER_STARTER_SUBSTITUTION_COUNT = 3_SHADOW_ONLY`

The count is deliberately conservative. It covers actual same-day cases where a
non-BUY_WAIT PM ADD row with ADD_LOST_TO_NEW_BUY evidence coexisted with funded
BUY_NEW. It is not a Production-defect count because raw score/rank does not
prove the ADD increment beat the starter on action-neutral marginal value.

## ADD Feasibility Blocks

`ADD_LOT_INFEASIBILITY_COUNT = 6_PC_ADD_BLOCKS_WITH_2_AUTHORITY_LOT_INFEASIBLE_ROWS`

`ADD_SINGLE_NAME_CAP_BLOCK_COUNT = 0_AUTHORITY_CAP_ROWS`

`ADD_CASH_SCARCITY_BLOCK_COUNT = 36_AUTHORITY_ROWS_WITH_CASH_OR_RESIDUAL_CASH_PREFERRED`

Cash and lot blocks are legitimate when they preserve the distinction between
desirability and executable feasibility. This audit found no evidence that
Runtime resurrected a zero ADD or converted a reviewed ADD into executable
authority.

## Action-Type Capitalization Rates

For the frozen Post-CW completed window:

| Action | Fills | Notional | Fill share of observed BUY fills |
|---|---:|---:|---:|
| BUY_NEW | 186 | 11,552,310 | 94.9% |
| BUY_ADD | 10 | 197,530 | 5.1% |
| REENTRY | 0 | 0 | 0.0% |

`POST_CW_ACTION_TYPE_CAPITALIZATION_RATES = BUY_NEW_DOMINANT_EARLY_WINDOW, BUY_ADD_FUNCTIONAL, REENTRY_ZERO_FILL_SO_FAR`

`ACTION_TYPE_STRUCTURAL_BIAS = STRUCTURAL_ASYMMETRY_PRESENT_NOT_FIXED_PRIORITY_ORDER`

No source or artifact evidence showed a fixed `BUY_NEW > BUY_ADD` priority
rule. The asymmetry is that BUY_ADD and REENTRY must pass additional lifecycle
and incremental-evidence gates before they can become capital competitors.

## Winner Position Growth Distribution

BUY_ADD campaign growth observed:

| Symbol | Campaign | ADD fills | Added qty | Added notional |
|---|---|---:|---:|---:|
| 94340 | pc-674562547125d12f-94340-0001 | 3 | 300 | 43,990 |
| 94320 | pc-f97f5131b256d0c5-94320-0001 | 1 | 100 | 16,390 |
| 94320 | pc-56fe03f336dc0c03-94320-0001 | 5 | 500 | 78,510 |
| 54010 | pc-2af0ce1c2a7bbed4-54010-0001 | 1 | 100 | 58,640 |

`WINNER_POSITION_GROWTH_DISTRIBUTION = CONCENTRATED_IN_94320_94340_54010_EARLY_GROWTH_WINDOW`

`STARTER_PROLIFERATION_WITH_VALID_ADD_COUNT = 3_SHADOW_ONLY`

This is the same conservative population as the strong-winner substitution
screen. It is enough to keep the design question open, not enough to prove a
mandatory Production repair.

## Diversification Assessment

`DIVERSIFICATION_VS_UNDERCAPITALIZED_WINNER_ASSESSMENT = MIXED`

The current contract rightly allows NEW diversification and Cash to beat weak
or infeasible ADD. The unresolved concern is whether current low-resolution
comparison can distinguish:

```text
strong incumbent next-lot opportunity
```

from:

```text
weaker starter admission
```

without using hindsight. The frozen Post-CW window contains only early growth
evidence through 2023-03-17 and does not yet cover the post-April plateau
window where CH/CI found zero BUY_ADD. More evidence is required before calling
this a current Production defect.

## G129 / Campaign Identity

`G129_BUY_ADD_CORRECTNESS = PASS_ON_ACTUAL_COMPLETED_FILLS`

Observed:

- 10 BUY_ADD fills had positive order quantity.
- `order_plan_item_id == pending_item_id` for all 10.
- no G129 order-increment mismatch was observed in completed fills.

`BUY_ADD_CAMPAIGN_IDENTITY_CORRECT = PASS_ON_OBSERVED_ADD_FILLS`

Observed:

- ADD fills preserved non-empty campaign ids.
- no same-day PC current campaign mismatch was found for completed BUY_ADD fills.

## Post-CW REENTRY / ADD Capital Interaction

`POST_CW_REENTRY_ADD_CAPITAL_INTERACTION = INSUFFICIENT_EVIDENCE_FOR_FILLED_REENTRY_INTERACTION`

CW repaired the residual REENTRY penalty surface and the run is progressing, but
the frozen completed window still has zero REENTRY fills. REENTRY/ADD marginal
capital interaction should be rechecked once the run reaches the post-April
window and actual REENTRY pass/fill cases appear.

## Neutral Marginal Capital Principle

`NEUTRAL_MARGINAL_CAPITAL_PRINCIPLE_SATISFIED = PARTIAL`

Satisfied:

- no unconditional BUY_NEW or BUY_ADD label priority was found;
- Runtime consumes PC/PS output and does not re-decide capital priority;
- positive BUY_ADD can win and execute;
- zero/reviewed ADD does not leak into Submit.

Not fully satisfied:

- current comparison remains low-resolution and class/rank based;
- no common action-neutral next-executable-increment value authority exists;
- REENTRY is still not observed as a filled capital competitor in the frozen
  Post-CW window.

## Root Cause

`WINNER_CAPITALIZATION_ROOT_CAUSE = LOW_RESOLUTION_MARGINAL_CAPITAL_VALUE_AND_ACTION_SPECIFIC_GATE_ASYMMETRY_NOT_BUY_ADD_RUNTIME_BREAKAGE`

Current evidence does not show BUY_ADD is broken downstream. The actual
root-cause candidate is architectural:

```text
held-position ADD evidence can be valid and still fail to become a comparable
next-lot capital value against NEW_BUY/Cash because the accepted system lacks a
high-resolution common marginal capital authority.
```

This is consistent with CH/CI and the high-resolution marginal capital value
SoT. It is not proven as a mandatory correctness defect in the current
Post-CW completed window.

## Required Final Answers

1. `LATEST_COMPLETED_DATE_USED`: `2023-03-17`
2. `WINNER_CAPITALIZATION_PHILOSOPHY_PRESERVED`: `YES_PARTIAL`
3. `BUY_ADD_ACTUAL_PATH_MAP`: `PM_ADD_TO_PC_TO_PS_TO_RUNTIME_TO_FILL_CONFIRMED_FOR_10_FILLS`
4. `BUY_ADD_FUNNEL`: `104_PM_ADD -> 104_PC_ADD -> 12_AUTHORIZED -> 12_RUNTIME_PLANS -> 10_FILLS`
5. `BUY_ADD_FIRST_BLOCKER_DISTRIBUTION`: `ADD_ELIGIBILITY_48, BUY_QUALITY_32, ADD_LOST_TO_NEW_BUY_6, PS_LOT_OR_CAP_6`
6. `LEGITIMATE_ADD_BLOCK_COUNT`: `86`
7. `POTENTIALLY_UNFAIR_ADD_BLOCK_COUNT`: `6`
8. `CURRENT_MARGINAL_CAPITAL_SEMANTIC_GAP`: `PRESENT_AS_ARCHITECTURE_LIMITATION_NOT_CONFIRMED_CORRECTNESS_DEFECT`
9. `ACTION_TYPE_CAPITAL_SCORE_SEMANTICS`: `PARTIAL_COMPARABILITY_ONLY`
10. `EXISTING_WINNER_DECISION_TIME_EVIDENCE`: `AVAILABLE_AND_PARTIALLY_CONSUMED`
11. `WINNER_EVIDENCE_CONSUMED_BY_CAPITAL_COMPETITION`: `YES_PARTIAL`
12. `ADD_VS_NEW_REENTRY_COMPETITION_CASES`: `NEW_VS_ADD_76_DATES, REENTRY_FILL_0`
13. `STRONG_WINNER_TO_WEAKER_STARTER_SUBSTITUTION_COUNT`: `3_SHADOW_ONLY`
14. `ADD_LOT_INFEASIBILITY_COUNT`: `6_PC_ADD_BLOCKS_WITH_2_AUTHORITY_LOT_INFEASIBLE_ROWS`
15. `ADD_SINGLE_NAME_CAP_BLOCK_COUNT`: `0`
16. `ADD_CASH_SCARCITY_BLOCK_COUNT`: `36_AUTHORITY_ROWS`
17. `POST_CW_ACTION_TYPE_CAPITALIZATION_RATES`: `BUY_NEW_186_FILLS_11552310_NOTIONAL, BUY_ADD_10_FILLS_197530_NOTIONAL, REENTRY_0`
18. `ACTION_TYPE_STRUCTURAL_BIAS`: `STRUCTURAL_ASYMMETRY_PRESENT_NOT_FIXED_PRIORITY_ORDER`
19. `WINNER_POSITION_GROWTH_DISTRIBUTION`: `94340_3_ADD_FILLS, 94320_6_ADD_FILLS_ACROSS_2_CAMPAIGNS, 54010_1_ADD_FILL`
20. `STARTER_PROLIFERATION_WITH_VALID_ADD_COUNT`: `3_SHADOW_ONLY`
21. `DIVERSIFICATION_VS_UNDERCAPITALIZED_WINNER_ASSESSMENT`: `MIXED_MORE_POST_APRIL_EVIDENCE_REQUIRED`
22. `G129_BUY_ADD_CORRECTNESS`: `PASS`
23. `BUY_ADD_CAMPAIGN_IDENTITY_CORRECT`: `PASS`
24. `POST_CW_REENTRY_ADD_CAPITAL_INTERACTION`: `INSUFFICIENT_EVIDENCE_FOR_FILLED_REENTRY_INTERACTION`
25. `NEUTRAL_MARGINAL_CAPITAL_PRINCIPLE_SATISFIED`: `PARTIAL`
26. `WINNER_CAPITALIZATION_ROOT_CAUSE`: `LOW_RESOLUTION_MARGINAL_CAPITAL_VALUE_AND_ACTION_SPECIFIC_GATE_ASYMMETRY`
27. `PRODUCTION_REPAIR_REQUIRED`: `MORE_EVIDENCE_REQUIRED`
28. `NEW_COMPONENT_REQUIRED`: `NO_FOR_CURRENT_REPAIR; POSSIBLE_FUTURE_HIGH_RESOLUTION_MARGINAL_CAPITAL_AUTHORITY`
29. `NEW_MODEL_REQUIRED`: `NO`
30. `NEW_FEATURE_REQUIRED`: `NO_FOR_ACCEPTANCE; FUTURE_CAPABILITY_DESIGN_ONLY_IF_POST_APRIL_EVIDENCE_CONFIRMS_NEED`
31. `OUTCOME_DATA_USED_TO_CLASSIFY_ADD_COMPETITION`: `NO`
32. `PRODUCTION_CHANGE_EXECUTED`: `NO`
33. `TARGET_RUN_MUTATED`: `NO`
34. `NEXT_RECOMMENDED_STEP`: `continue_user_operated_post_CW_long_run_to_post_April_window_then_repeat_READ_ONLY_add_competition_audit`
35. `FINAL_JUDGMENT`: `PHASE32_CY_WINNER_ADD_MARGINAL_CAPITAL_COMPETITION_GAP_CHARACTERIZED_MORE_POST_APRIL_EVIDENCE_REQUIRED_NO_PRODUCTION_REPAIR_YET`

## Final Judgment

```text
PHASE32_CY_WINNER_ADD_MARGINAL_CAPITAL_COMPETITION_GAP_CHARACTERIZED_MORE_POST_APRIL_EVIDENCE_REQUIRED_NO_PRODUCTION_REPAIR_YET
```

Current Post-CW artifacts preserve the accepted BUY_ADD philosophy and G129
correctness. BUY_ADD is functional and can capitalize winners, but it is narrow.
The main unresolved issue is not a downstream Runtime ADD defect; it is the
known absence of a high-resolution common marginal-capital authority that can
compare a held winner's next executable ADD lot against BUY_NEW, REENTRY, and
Cash on an action-neutral PIT basis.

No Production repair is justified from the current 113BD frozen window alone.
The next safe action is to let the user-operated run continue into the
post-April window and then re-audit ADD competition with the same no-hindsight
rules.
