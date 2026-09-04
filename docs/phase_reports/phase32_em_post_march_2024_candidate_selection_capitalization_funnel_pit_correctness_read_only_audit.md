# Phase32-EM — Post-March-2024 Candidate Selection → Capitalization Funnel PIT Correctness READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Requested period: `2024-03-18` through `2024-05-31`
- Evidence coverage found in target run: `2024-03-18` through `2024-05-24`
- Evidence gap: `2024-05-27` through `2024-05-31` artifacts were not present in this run at audit time.
- Evidence used: target-run daily artifacts only:
  - `strategy/market_context.json`
  - `strategy/portfolio_policy.json`
  - `strategy/buy_quality_decisions.json`
  - `strategy/portfolio_construction.json`
  - `strategy/position_sizing.json`
  - `strategy/runtime_planning.json`
  - `position_management/pm_decisions.json`
  - `submit/runtime_manifest.json`
  - `execution/fills.json`
  - `current_valuation_refresh/valuation_projection.json`
- No future price, future return, later winner/loser outcome, later SELL result, campaign final PnL, or historical profitability was used for judgment.
- No Production, SHADOW, source, config, runtime state, Pending, Ledger, fresh-run, resume, replay, or recover action was executed.

## POST_MARCH_CANDIDATE_QUALITY_PROFILE

The system consistently produced a 50-ish candidate/BQ universe per business day. Candidate quality did not disappear after March, but the mix shifted toward reduced allocation and wait/reject states during RANGE/CORRECTION/BEAR conditions.

| Period | Days | Avg exposure | Min exposure | Avg cash | BQ FULL | BQ REDUCED | BQ WAIT | BQ REJECT | Top-5 moderate-or-better | BUY plans | BUY fills |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2024-03-18..03-29 | 9 | 71.93% | 38.67% | 528,747 | 44 | 237 | 110 | 51 | 36/45 | 27 | 18 |
| 2024-04-01..04-16 | 12 | 41.89% | 29.96% | 1,116,063 | 44 | 282 | 149 | 105 | 47/60 | 16 | 15 |
| 2024-04-17..04-30 | 9 | 30.79% | 19.32% | 1,326,872 | 33 | 215 | 112 | 86 | 45/45 | 11 | 11 |
| 2024-05-01..05-17 | 11 | 48.98% | 31.07% | 988,645 | 42 | 296 | 134 | 78 | 53/55 | 19 | 19 |
| 2024-05-20..05-24 | 5 | 80.42% | 71.12% | 377,750 | 19 | 144 | 60 | 27 | 21/25 | 8 | 7 |

Representative top-ranked candidate facts:

- `2024-04-17`: top ranks included `94320`, `76470`, `95010`, `89180`, `33500`; BQ actions were mostly `REDUCED_ALLOCATION_ONLY`, but final regime was `BEAR`, risk intent `CAUTIOUS_DEPLOYMENT`, and no BUY plan was produced.
- `2024-04-25`: top-ranked `76470` was a `REDUCE_CANDIDATE`; `94320` was retained; `95010`, `89180`, and `33500` did not become funded BUYs. Exposure was `19.32%`, cash `1,549,550`, and PC reported `final_no_deployable_opportunity=true`.
- `2024-05-08`: low exposure persisted (`33.43%`) while top ranked opportunities were mostly `ADD_CANDIDATE` / `REENTRY-like` with reduced allocation. Two BUY plans were produced and both filled.
- `2024-05-20`: reinvestment became substantial: regime `BULL`, exposure `82.15%`, three BUY fills, and buy notional `381,180`.

## CANDIDATE_SELECTION_CORRECTNESS

Classification: `STRONG_CANDIDATES_PRESENT` in many days, with `MODERATE_ONLY` during the deepest BEAR/low-exposure segment. No `DATA_OR_AUTHORITY_DEFECT` was found.

Evidence:

- Candidate/BQ artifacts showed `future_information_used=false`, `historical_result_input_used=false`, and decision-time feature dates matching the business date.
- Top candidate ranks were preserved into PC via `opportunity_buy_rank`, `rank_authority_status=PASS`, and `opportunity_rank_preserved`.
- Strong or moderate candidates were present in top-5 nearly every day; however, many were:
  - already-held retained positions,
  - PM REDUCE candidates,
  - REENTRY-constrained symbols,
  - `BUY_WAIT`,
  - or positive BQ but PC target `0.0`.

Judgment:

- Candidate selection was not the primary post-March low-growth failure path.
- The system knew about plausible opportunities, but many did not become deployable capital because downstream Entry/PC/PS semantics filtered them out or kept them at zero target.

## POST_MARCH_CAPITALIZATION_FUNNEL

Observed funnel shape:

`Candidate/BQ -> Entry/PC member -> PC target weight -> Position Sizing -> Runtime plan -> Submit -> Fill`

Aggregate observations:

- PC accepted NEW allocations were materially lower than the count of BQ-positive candidates:
  - `2024-04-17..04-30`: BQ FULL+REDUCED = `248`, PC accepted NEW count = `11`, BUY fills = `11`
  - `2024-05-01..05-17`: BQ FULL+REDUCED = `338`, PC accepted NEW count = `21`, BUY fills = `19`
- Accepted ADD allocations were `0` throughout the summarized period. Incumbent ADD-style evidence existed, but Production capital allocation remained overwhelmingly NEW-oriented at the executable plan level.
- Many positive BQ / ADD_CANDIDATE or REENTRY-like rows retained `target_weight=0.0`. Common contemporaneous reason codes included:
  - `selection_quality_caution_continuation`
  - `reentry_repeated_unresolved_churn`
  - `reentry_trend_recovery_not_satisfied`
  - `reentry_hard_stop_new_thesis_not_sufficient`
  - `reentry_unknown_prior_context_independence_not_established`
  - `non_positive_expected_edge_score`
  - `high_downside_risk_score`
- Explicit cash constraints were not the main PC blocker. Cash was often abundant while PC produced few or zero BUY plans.
- Lot/cap constraints existed in individual rows, but were not the dominant aggregate cause of low exposure. Examples include `aggregate_exposure_cap=0.74` on `2024-04-25`, but actual exposure was only `19.32%`, so the cap was not binding at portfolio level that day.

Classification:

- positive opportunity but zero quantity: `PRESENT`
- lot infeasible: `PRESENT_BUT_SECONDARY`
- cap constrained: `PRESENT_BUT_NOT_MAIN_PORTFOLIO_BINDING`
- cash constrained: `NOT_PRIMARY`
- NEW/ADD/REENTRY competition loss: `PRESENT`
- existing position competition: `PRESENT`
- risk/regime suppression: `PRESENT`
- target_weight <= current_weight: `PRESENT`

Judgment: `PORTFOLIO_CAPITALIZATION_GAP` as a design/semantic bottleneck, not a proven correctness defect. The strongest known opportunities were often selected into artifacts but not capitalized because PC/Entry semantics declined to convert them into target weight or executable quantity.

## CASH_HOLDING_ROOT_CAUSE

Focus: `2024-04-17..04-30`

- Average exposure: `30.79%`
- Average cash: `1,326,872`
- Regime: mostly `BEAR`, then `RANGE` by `2024-04-30`
- Risk intent: `CAUTIOUS_DEPLOYMENT`
- No-deployable-opportunity days: `2024-04-17`, `2024-04-19`, `2024-04-25`
- `2024-04-25`: exposure `19.32%`, cash `1,549,550`, zero BUY plans, three SELL fills, PC `final_no_deployable_opportunity=true`

Classification: `JUSTIFIED_RISK_SUPPRESSION + CAPITAL_COMPETITION_SUPPRESSION`.

Focus: `2024-05-01..05-17`

- Average exposure: `48.98%`
- Average cash: `988,645`
- Regime alternated among RANGE/CORRECTION/RECOVERY
- Risk intent stayed `CAUTIOUS_DEPLOYMENT` or `GRADUAL_REDEPLOYMENT`
- No no-deployable-opportunity days in this subwindow, but BUY plans remained sparse until the sharp `2024-05-15` and `2024-05-20` re-risking.

Classification: `CAPITAL_COMPETITION_SUPPRESSION + JUSTIFIED_RISK_SUPPRESSION`.

Overall cash judgment:

- Cash was not mainly idle because Execution lost orders.
- Cash was also not purely explained by absence of any candidate evidence.
- The main low-cash-deployment shape was: candidates existed, but current PC/Entry/Risk semantics allowed only a narrow subset to become executable BUYs.

## POST_BEAR_REINVESTMENT_CORRECTNESS

Path from `2024-04-25` exposure `19.32%` to `2024-05-20` exposure `82.15%`:

- `2024-04-25`: BEAR, CAUTIOUS, no deployable opportunity, zero BUY plan, three SELL fills.
- `2024-04-26`: BEAR, one BUY plan/fill.
- `2024-04-30`: RANGE, five BUY plans/fills, buy notional `534,000`, exposure recovered to `40.47%`.
- `2024-05-01..05-14`: cautious/gradual redeployment continued, usually one to three BUY fills per active deployment day.
- `2024-05-15`: CORRECTION but two large BUY fills, buy notional `727,170`, exposure rose to `69.11%`.
- `2024-05-20`: BULL, three BUY fills, buy notional `381,180`, exposure reached `82.15%`.

Classification: `BORDERLINE_BUT_CONTRACT_VALID`.

The re-risk path was delayed relative to available cash, but the delay is explainable from PIT evidence: BEAR/CORRECTION/RANGE regime states, cautious/gradual risk intent, and PC no-deployable or zero-target outcomes. Once current-day PIT authority produced funded BUY plans, those plans generally filled.

## POST_MARCH_BUY_EXECUTION_FUNNEL

Execution was not the primary bottleneck.

- `2024-04-17..04-30`: 11 runtime BUY plans, 11 BUY fills.
- `2024-05-01..05-17`: 19 runtime BUY plans, 19 BUY fills.
- Most planned BUYs that reached approval/fill path were executed.

Observed exceptions:

- `76920` appeared repeatedly as planned BUY but not filled on `2024-03-18`, `2024-03-21`, `2024-03-22`, `2024-03-25`, `2024-03-26`, `2024-03-27`, and `2024-04-01`.
- Submit manifests classified this as `BUY_ITEM_SCOPED_REVIEW`; reviewed BUY item IDs were not submitted, while unrelated approved items were submitted and filled.
- Representative reason observed for `76920`: `item_scoped_review_required` with review reason `corporate_action_event_not_resolved`.
- This is expected fail-closed item-scoped behavior, not an execution loss after approved submit.

Execution funnel classification:

- `PLANNED_AND_FILLED`: dominant path after `2024-04-17`
- `REVIEW_REQUIRED`: present, concentrated in `76920` item-scoped BUY review
- `CASH_CAPACITY`: not primary in audited evidence
- `BROKER/EXECUTION_REJECTION`: not reproduced as primary cause
- `PROVENANCE/AUTHORITY_FAILURE`: not reproduced as primary cause
- `OTHER`: none material

## POST_MARCH_LOW_GROWTH_ROOT_CAUSE

Classification: `MIXED`.

Components:

- `VALID_RISK_DEFENSIVENESS`: material. April had BEAR/CORRECTION/RANGE/RECOVERY states with CAUTIOUS or GRADUAL deployment, and cash was intentionally retained.
- `PORTFOLIO_CAPITALIZATION_GAP`: material. Candidate/BQ artifacts contained many positive or reduced-allocation candidates, but PC/Entry frequently left ADD_CANDIDATE/REENTRY-like candidates at zero target and produced few executable BUY plans.
- `MARKET_OPPORTUNITY_SCARCITY`: partial, not absolute. Strong candidates were not absent, but fully clean deployable candidates were scarcer under BEAR/CORRECTION/RANGE and REENTRY/expected-edge constraints.
- `CANDIDATE_SELECTION_GAP`: not established. Known strong/moderate opportunities were present in top-ranked artifacts and rank authority was preserved.
- `EXECUTION_GAP`: not established. Approved BUY plans usually filled; item-scoped reviewed buys were intentionally not submitted.

## Correctness / Repair Judgment

- No data/provenance/stale/future-leakage correctness defect was identified in candidate selection.
- No evidence shows a BUY plan was silently lost after approved submit/fill authority.
- The most important bottleneck is semantic: PC/Entry/Risk translated known opportunities into executable capital very selectively during the post-March defensive regime, especially for ADD/REENTRY-like rows.
- This is not enough to justify immediate Production repair from this audit alone, because changing it would alter Strategy/PC semantics and must not be derived from later growth weakness.
- It is enough to justify a SHADOW-only follow-up design/measurement study focused on the Candidate/BQ-positive -> PC target-zero boundary.

## Required Final Answers

- `POST_MARCH_CANDIDATE_QUALITY_PROFILE`: candidate universe stayed around 50/day; FULL/REDUCED candidates persisted, but April shifted toward WAIT/REJECT and reduced-only states. Details above.
- `CANDIDATE_SELECTION_CORRECTNESS`: `STRONG_CANDIDATES_PRESENT` / `MODERATE_ONLY` depending on date; no candidate selection authority defect found.
- `POST_MARCH_CAPITALIZATION_FUNNEL`: PC/Entry/Risk semantics were the dominant narrowing point; many BQ-positive candidates became target `0.0`, while accepted ADD allocations were `0`.
- `CASH_HOLDING_ROOT_CAUSE`: `JUSTIFIED_RISK_SUPPRESSION + CAPITAL_COMPETITION_SUPPRESSION`; not primarily cash-capacity or execution failure.
- `POST_BEAR_REINVESTMENT_CORRECTNESS`: `BORDERLINE_BUT_CONTRACT_VALID`; reinvestment resumed when PIT regime/risk/PC allowed funded BUYs.
- `POST_MARCH_BUY_EXECUTION_FUNNEL`: mostly `PLANNED_AND_FILLED`; item-scoped `REVIEW_REQUIRED` existed, especially `76920`, but did not prove execution defect.
- `POST_MARCH_LOW_GROWTH_ROOT_CAUSE`: `MIXED`, led by `VALID_RISK_DEFENSIVENESS` and `PORTFOLIO_CAPITALIZATION_GAP`.
- `CANDIDATE_REPAIR_JUSTIFIED`: `NO`
- `PC_REPAIR_JUSTIFIED`: `NO_PRODUCTION_REPAIR_FROM_THIS_AUDIT`; `SHADOW_FOLLOW_UP_JUSTIFIED`
- `EXECUTION_REPAIR_JUSTIFIED`: `NO`
- `PRODUCTION_CHANGE_EXECUTED`: `NO`
- `SHADOW_CHANGE_EXECUTED`: `NO`
- `TARGET_RUN_MUTATED`: `NO`
- `RUNTIME_STATE_MUTATED`: `NO`
- `FUTURE_OUTCOME_USED_FOR_JUDGMENT`: `NO`
- `NEXT_RECOMMENDED_STEP`: open a SHADOW-only audit/design phase on the BQ-positive / Entry-allowed / ADD-or-REENTRY-like candidate -> PC target-zero boundary, explicitly excluding future returns and Production tuning.

## Final Judgment

`PHASE32_EM_POST_MARCH_LOW_GROWTH_MIXED_VALID_RISK_DEFENSIVENESS_AND_PC_CAPITALIZATION_GAP_NO_CANDIDATE_OR_EXECUTION_CORRECTNESS_DEFECT`
