# Phase32-GA — Long-vs-Fresh Actual BUY Divergence Root-Cause Decomposition READ-ONLY Audit

## Scope

- Long run: `runtime-test-historical-extended-smoke-20260903T213011268067Z`
- Fresh June 1M run: `runtime-test-historical-extended-smoke-20260904T112908488385Z`
- Compared same-day completed window at final read: `2023-06-01` through `2023-07-05`
- `SAME_DAY_COMPLETED_DATE_COUNT = 25`

The fresh run was externally active while this audit was being performed. This report freezes the final read-only snapshot observed by Codex: `25` common completed business dates through `2023-07-05`.

READ-ONLY confirmation:

- Production changed: NO
- SHADOW changed: NO
- Source/config/schema changed: NO
- Runtime/Pending/Ledger state mutated: NO
- fresh-run/resume/replay/recover executed by Codex: NO
- Future return / MFE / MAE / final campaign outcome used for Production judgment: NO

## Evidence Sources

- Run state: `reports/runtime_tests/runs/<run_id>/run_state.json`
- Actual BUY fills: `daily/<date>/execution/fills.json`
- Portfolio Construction: `daily/<date>/strategy/portfolio_construction.json`
- PM decisions: `daily/<date>/position_management/pm_decisions.json`
- Prior reports:
  - `docs/phase_reports/phase32_fz_june_long_vs_fresh_same_day_portfolio_state_target_weight_legacy_divergence_read_only_audit.md`
  - `docs/phase_reports/phase32_fx_buy_opportunity_ranking_vs_pm_hold_sell_evidence_semantic_overlap_read_only_audit.md`
  - `docs/phase_reports/phase32_fy_late_top50_outside_hold_loss_portfolio_drag_attribution_read_only_audit.md`
  - `docs/phase_reports/phase32_fk_post_deterioration_re_add_authority_long_lived_history_bias_exhaustive_read_only_audit.md`
  - `docs/phase_reports/phase32_fl_winner_deterioration_profit_protection_add_loss_attribution_read_only_audit.md`

## Same-Day Opportunity Baseline

Phase32-FZ established that the long and fresh runs see essentially the same current opportunity universe over the overlapping June window:

| Metric | FZ evidence |
|---|---:|
| Top50 overlap | 100.0% |
| Top20 overlap | 100.0% |
| Opportunity rank equality | 100.0% |
| Full signal equality: rank + quality + BQ + Entry + MCV | 83.73% |
| Same-symbol PC target exact equality | 61.42% |

GA extends the actual BUY comparison through `2023-07-05`. The central fact remains unchanged: Candidate Selection is not the dominant source of divergence. The same opportunity/rank universe maps into materially different actual BUY fills because current portfolio/campaign state changes the downstream path.

## BUY Set Classification

Actual BUY fills were classified by same business date and symbol.

| Classification | Count |
|---|---:|
| `BOTH_BUY_COUNT` | 21 |
| `LONG_ONLY_BUY_COUNT` | 36 |
| `FRESH_ONLY_BUY_COUNT` | 47 |
| Total BUY union | 104 |
| `ACTUAL_BUY_OVERLAP_RATE` | 20.19% |

Approximate divergent BUY notional from canonical fill notional fields:

| Side | Divergent notional |
|---|---:|
| Long-only BUY | 3,047,620 |
| Fresh-only BUY | 2,589,460 |

Action type distribution:

| Side | BUY_NEW | BUY_ADD |
|---|---:|---:|
| Long-only | 35 | 1 |
| Fresh-only | 40 | 7 |

## First Divergence Stage Distribution

For each divergent BUY, GA assigned the first observable causal boundary using pre-fill PC/PM state. When BQ/Entry fields differed only because one run already held the symbol and the other did not, the boundary was attributed to `Current Position Membership`, not to Candidate Selection.

| First divergence stage | Count | Share |
|---|---:|---:|
| Current Position Membership | 39 | 47.0% |
| PC membership / target | 31 | 37.3% |
| Campaign Identity / Prior Ownership Context | 9 | 10.8% |
| Runtime Planning / Fill | 3 | 3.6% |
| Capital Competition / Cash | 1 | 1.2% |
| Opportunity Ranking | 0 | 0.0% |
| PM | 0 | 0.0% |
| MCV | 0 | 0.0% |

Required stage shares:

- `ALREADY_HELD_STATE_DIVERGENCE_SHARE = 39/83 = 47.0%`
- `CAMPAIGN_STATE_FIRST_DIVERGENCE_SHARE = 9/83 = 10.8%`
- `PRIOR_EXIT_FIRST_DIVERGENCE_SHARE = 0 direct first-stage rows; prior ownership is material through the 9 campaign-history rows and repeated BUY_NEW/EXIT cycles`
- `ADD_PATH_FIRST_DIVERGENCE_SHARE = 0 explicit ADD-specific first-stage gate; 8/83 divergent BUYs were BUY_ADD-type and were first explained by current-position or PC relationship state`
- `PM_FIRST_DIVERGENCE_SHARE = 0/83 = 0.0%`
- `PC_TARGET_FIRST_DIVERGENCE_SHARE = 31/83 = 37.3%`
- `MCV_FIRST_DIVERGENCE_SHARE = 0/83 = 0.0%`
- `CAPITAL_AVAILABILITY_FIRST_DIVERGENCE_SHARE = 1/83 = 1.2%`
- `RUNTIME_FIRST_DIVERGENCE_SHARE = 3/83 = 3.6%`

The three `Runtime Planning / Fill` rows are small residual cases where the inspected PC fields were already aligned enough that the first visible split was at order/fill materialization. They did not show a fail-closed, HALT, duplicate, or broker/execution correctness defect in the inspected evidence.

## Root-Cause Buckets

| Root bucket | Count | Share |
|---|---:|---:|
| `A. CURRENT_POSITION_STATE` | 39 | 47.0% |
| `F. PC TARGET / RELATIONSHIP` | 31 | 37.3% |
| `B. CAMPAIGN_HISTORY` | 9 | 10.8% |
| `J. RUNTIME / EXECUTION` | 3 | 3.6% |
| `H. CASH / CAPITAL AVAILABILITY` | 1 | 1.2% |
| `C. REENTRY / PRIOR EXIT` | 0 direct first boundary |
| `D. ADD-SPECIFIC GATE` | 0 direct first boundary |
| `E. PM HOLD/REDUCE/EXIT` | 0 |
| `G. MCV / CAPITAL PRIORITY` | 0 |
| `I. LOT / CAP / HEADROOM` | 0 isolated |
| `K. CANDIDATE SIGNAL DIFFERENCE` | 0 after relationship-derived BQ/Entry differences were attributed upstream |
| `L. OTHER` | 0 |

Interpretation:

The divergence is overwhelmingly downstream of the shared current opportunity universe. The dominant mechanism is portfolio path dependence: what is already held, which campaign identity exists, and how PC maps the same security evidence into target membership and executable allocation.

## Long-Only BUY Root Cause

`LONG_ONLY_BUY_COUNT = 36`

| First divergence stage | Count |
|---|---:|
| Current Position Membership | 17 |
| PC membership / target | 14 |
| Campaign Identity / Prior Ownership Context | 2 |
| Runtime Planning / Fill | 2 |
| Capital Competition / Cash | 1 |

Long-only buys were almost entirely `BUY_NEW` (`35/36`). The long run bought symbols that fresh did not primarily because the long portfolio state produced different PC target membership or because the fresh run already had a different same-symbol or adjacent relationship state by that date.

No evidence shows PM action divergence as the first boundary for long-only buys.

## Fresh-Only BUY Root Cause

`FRESH_ONLY_BUY_COUNT = 47`

| First divergence stage | Count |
|---|---:|
| Current Position Membership | 22 |
| PC membership / target | 17 |
| Campaign Identity / Prior Ownership Context | 7 |
| Runtime Planning / Fill | 1 |

Fresh-only buys are the clearest evidence that same current opportunity can be capitalized in the fresh run while the long run does not buy the same symbol. This is not caused by lower candidate rank in the long run: FZ established 100% rank equality and 100% Top20/Top50 overlap. The suppression is mostly from incumbent holdings, existing campaign relationship, and PC target transformation.

## Strong Opportunity Suppression

`FRESH_ONLY_STRONG_BUY_SUPPRESSED_COUNT = 1`

The one fresh-only strong/high case suppressed in long was first classified as `A_CURRENT_POSITION_STATE`.

`FRESH_ONLY_STRONG_BUY_SUPPRESSION_REASONS = {A_CURRENT_POSITION_STATE: 1}`

`LONG_ONLY_MARGINAL_SUBSTITUTION_COUNT = 0`

GA did not find a broad pattern where the long run routinely skipped fresh-only strong candidates and substituted clearly marginal long-only buys on the same day. The broader divergence is larger than that narrower pattern: it is a portfolio-state and PC-target path dependence problem, not simply "long buys bad rank while fresh buys good rank."

## Repeated BUY_NEW / EXIT Cycle

`REPEATED_BUY_NEW_EXIT_SYMBOL_COUNT = 81`

Definition used: same symbol has at least two BUY-side `BUY_NEW` fills and at least one EXIT-like SELL fill in the long run through the compared endpoint (`2023-07-05`).

The count demonstrates that repeated same-symbol campaign cycling is common in the long run. This does not prove that historical state is factually wrong, but it does show that the long run carries materially more campaign and prior-ownership context than the fresh June run.

For `67310`, the long run had:

- `BUY_NEW count = 6`
- `EXIT count = 6`

## 67310 Root-Cause Trace

Observed divergent cases:

| Date | Side | Rank long/fresh | Quality long/fresh | MCV long/fresh | Held before fill long/fresh | Target long | Target fresh | Long accepted BUY_NEW | Fresh accepted BUY_NEW | Outcome |
|---|---|---:|---|---|---|---:|---:|---:|---:|---|
| 2023-06-05 | Long-only | 5 / 5 | HIGH / HIGH | ELIGIBLE_COMPARABLE / ELIGIBLE_COMPARABLE | false / false | 17.7701% | 0.0000% | 3.4483% | 4.0000% | Long BUY_NEW 300,000; fresh no fill |
| 2023-06-27 | Long-only | 2 / 2 | HIGH / HIGH | ELIGIBLE_COMPARABLE / ELIGIBLE_COMPARABLE | false / false | 16.9298% | 0.0000% | 4.2535% | 4.1667% | Long BUY_NEW 300,000; fresh no fill |

`67310_FIRST_DIVERGENCE_ROOT_CAUSE = PC membership / target`

67310 is not a Candidate Selection divergence. On both divergent dates, rank, quality, and MCV were aligned. The first bad or at least first materially divergent boundary is PC target materialization: long gave 67310 a high final target and bought it, while fresh carried no final target/fill despite comparable same-day evidence and non-zero accepted BUY_NEW weight metadata. This is a PC target/relationship/final-allocation path dependence case.

The repeated long BUY_NEW/EXIT history for 67310 is material context, but GA does not prove the repeated history is factually incorrect. The evidence supports that portfolio/campaign state strongly changes whether the same current opportunity reaches capital.

## ADD / NEW Relationship Gap

`INCUMBENT_NEW_ADD_PATH_GAP_FOUND = PARTIAL`

Evidence:

- Divergent BUY_ADD fills: `8/83`
- Fresh-only BUY_ADD: `7`
- Long-only BUY_ADD: `1`
- No explicit ADD-specific first divergence gate was isolated as the first boundary.
- Most ADD-like differences were explained first by current-position membership or PC target/relationship.

Judgment:

There is a real incumbent relationship path difference, but GA did not prove that prior ADD history itself is the dominant or first causal blocker in this June window.

`PRIOR_ADD_HISTORY_MATERIAL = NO concrete dominant evidence in GA window`

`REENTRY_HISTORY_MATERIAL = PARTIAL`

Prior ownership and repeated campaign cycling are material as portfolio/campaign context, but direct prior-exit or REENTRY gates were not isolated as the first boundary for divergent BUY fills in this snapshot.

## PM / PC / Capital Materiality

`PM_CAPITAL_RETENTION_MATERIAL = PARTIAL`

PM action was not the first divergence stage in the inspected divergent BUY rows (`0/83`). However, existing positions retained by PM create the portfolio state that later changes PC membership and available capital. Therefore PM retention is material indirectly, not as a direct first failing boundary in GA.

`PC_RELATIONSHIP_STATE_MATERIAL = YES`

PC membership/target plus current-position state accounts for `70/83 = 84.3%` of divergent BUYs. This is the dominant observed mechanism.

`CAPITAL_PRIORITY_MATERIAL = YES`

Capital priority is material through PC target/final allocation and the single isolated cash/capital-availability first boundary. It is not primarily an MCV-class mismatch in this window.

## Historical State Correctness vs Authority Strength

`ACCUMULATED_STATE_PROBLEM_TYPE = B`

State data appears factually valid in the inspected evidence: current positions, campaign identities, and prior BUY/EXIT histories are real artifacts. The problem is not "bad state rows" or stale/corrupt execution evidence.

The issue is that correct accumulated state has strong downstream authority over how the same current opportunity is converted into portfolio membership and capital. That authority creates high path dependence between a long run and a fresh same-day run.

`HISTORY_NEUTRALITY_VIOLATION_FOUND = NO as a proven correctness defect in GA; YES as a design-risk signal`

GA did not find a specific Architecture/SoT violation proving that old ownership history incorrectly overrides a current PIT opportunity. It did find that current opportunity reevaluation is highly path dependent.

`CURRENT_OPPORTUNITY_REEVALUATION_GAP_FOUND = YES`

Same rank/quality opportunities can be bought in one run and ignored in the other because the existing portfolio/campaign state changes PC final target materialization.

## Path Dependence Judgment

`CURRENT_OPPORTUNITY_TO_PORTFOLIO_PATH_DEPENDENCE = HIGH`

Rationale:

- Top50/Top20/rank equality remains effectively complete.
- Actual BUY overlap is only `20.19%`.
- `84.3%` of divergent buys are first explained by current-position state or PC target/relationship.
- Campaign/prior-ownership context adds another `10.8%`.

The long-vs-fresh difference is therefore not primarily "different opportunities"; it is "same opportunities, different portfolio-state translation."

## Architecture Judgment

`ARCHITECTURE_JUDGMENT = MULTI_FACTOR_PORTFOLIO_STATE_PATH_DEPENDENCE`

The current architecture preserves campaign continuity and position-aware PC behavior, which are valid concepts. But the evidence shows that the current opportunity-to-capital path is not history-neutral: existing position/campaign state materially changes whether an otherwise comparable current opportunity receives capital.

This is not yet a proven Production correctness defect. It is a design refinement target.

## Required Final Answers

- `SAME_DAY_COMPLETED_DATE_COUNT = 25`
- `BOTH_BUY_COUNT = 21`
- `LONG_ONLY_BUY_COUNT = 36`
- `FRESH_ONLY_BUY_COUNT = 47`
- `ACTUAL_BUY_OVERLAP_RATE = 20.19%`
- `FIRST_DIVERGENCE_STAGE_DISTRIBUTION = Current Position 39; PC target/relationship 31; Campaign/prior ownership 9; Runtime/fill 3; Cash/capital 1; Opportunity/PM/MCV 0`
- `ALREADY_HELD_STATE_DIVERGENCE_SHARE = 47.0%`
- `CAMPAIGN_STATE_FIRST_DIVERGENCE_SHARE = 10.8%`
- `PRIOR_EXIT_FIRST_DIVERGENCE_SHARE = 0 direct first-boundary rows; material through campaign-history context`
- `ADD_PATH_FIRST_DIVERGENCE_SHARE = 0 direct first-boundary rows; 8 divergent BUY_ADD rows captured under current-position/PC relationship`
- `PM_FIRST_DIVERGENCE_SHARE = 0.0%`
- `PC_TARGET_FIRST_DIVERGENCE_SHARE = 37.3%`
- `MCV_FIRST_DIVERGENCE_SHARE = 0.0%`
- `CAPITAL_AVAILABILITY_FIRST_DIVERGENCE_SHARE = 1.2%`
- `RUNTIME_FIRST_DIVERGENCE_SHARE = 3.6%`
- `REPEATED_BUY_NEW_EXIT_SYMBOL_COUNT = 81`
- `67310_FIRST_DIVERGENCE_ROOT_CAUSE = PC membership / target`
- `INCUMBENT_NEW_ADD_PATH_GAP_FOUND = PARTIAL`
- `PRIOR_ADD_HISTORY_MATERIAL = NO concrete dominant evidence in GA window`
- `REENTRY_HISTORY_MATERIAL = PARTIAL`
- `PM_CAPITAL_RETENTION_MATERIAL = PARTIAL`
- `PC_RELATIONSHIP_STATE_MATERIAL = YES`
- `CAPITAL_PRIORITY_MATERIAL = YES`
- `FRESH_ONLY_STRONG_BUY_SUPPRESSED_COUNT = 1`
- `FRESH_ONLY_STRONG_BUY_SUPPRESSION_REASONS = A_CURRENT_POSITION_STATE: 1`
- `LONG_ONLY_MARGINAL_SUBSTITUTION_COUNT = 0`
- `CURRENT_OPPORTUNITY_TO_PORTFOLIO_PATH_DEPENDENCE = HIGH`
- `ACCUMULATED_STATE_PROBLEM_TYPE = B: state data is correct but its decision authority is strong`
- `HISTORY_NEUTRALITY_VIOLATION_FOUND = NO proven correctness defect; design-risk signal present`
- `CURRENT_OPPORTUNITY_REEVALUATION_GAP_FOUND = YES`
- `ARCHITECTURE_JUDGMENT = MULTI_FACTOR_PORTFOLIO_STATE_PATH_DEPENDENCE`
- `CORRECTNESS_DEFECT_FOUND = NO`
- `DESIGN_REFINEMENT_JUSTIFIED = YES`
- `PRODUCTION_REPAIR_JUSTIFIED = NO`
- `NEXT_DESIGN_DIRECTION = Design a SHADOW current-opportunity-to-capital comparator that re-evaluates incumbents, fresh candidates, and recently exited names under a common next-capital-unit frame while preserving bounded churn and campaign continuity`
- `LONG_HORIZON_VALIDATION_SAFE_TO_CONTINUE = YES`

## Next Recommended Step

Proceed with a design-only follow-up for a current-opportunity re-evaluation comparator:

- compare incumbent retention, ADD, BUY_NEW, and recently exited symbols under one decision-time next-capital-unit frame;
- keep audit lineage separate from current decision authority;
- avoid using future returns or realized PnL for threshold/rank design;
- keep Production unchanged until SHADOW evidence proves a correctness or architecture contract improvement.

## Final Judgment

`PHASE32_GA_LONG_VS_FRESH_BUY_DIVERGENCE_ROOT_CAUSE_IDENTIFIED_PORTFOLIO_STATE_PC_TARGET_PATH_DEPENDENCE_DESIGN_REFINEMENT_JUSTIFIED_NO_PRODUCTION_REPAIR_YET`
