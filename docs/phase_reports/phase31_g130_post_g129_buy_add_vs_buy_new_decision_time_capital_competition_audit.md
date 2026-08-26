# Phase31-G130 — Post-G129 BUY_ADD vs BUY_NEW Decision-Time Capital Competition Evidence Audit

## Final Decision

`G130_ADD_NEW_CAPITAL_COMPETITION_PARTIAL_EVIDENCE_FOLLOWUP_REQUIRED`

## Scope

Task type: READ-ONLY evidence audit.

Primary run:

`runtime-test-historical-extended-smoke-20260825T235520054579Z`

Completed immutable evidence audited:

`2022-10-03` through `2022-12-16`

Primary focus window:

`2022-11-21` through `2022-12-12`

No code, config, threshold, weight, model, fresh-run, resume, replay, long Historical, or run mutation was performed.

## Source Basis

Read and used as contract basis:

- `docs/phase_reports/phase31_g129_buy_add_actual_path_narrow_repair.md`
- `docs/phase_reports/phase31_g128_buy_add_submit_review_campaign_materialization_root_cause_audit.md`
- `docs/phase_reports/phase31_g127_buy_add_winner_scaling_actual_funnel_return_audit.md`
- `docs/phase_reports/phase31_g112_repeated_add_marginal_capital_competition_contract_audit.md`

Common SoT / architecture inspected:

- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/02_architecture/runtime_architecture_v2.md`

Current source inspected read-only for authority topology:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`

## Primary Judgment

POST_G129_ADD_NEW_CAPITAL_COMPETITION_CONFORMANT = `PARTIAL`

G129 successfully repaired the actual BUY_ADD materialization path: BUY_ADD now reaches Runtime and fills materially more often than the prior G127/G128 diagnostic run. The ADD rows also carry same-date PIT ADD evidence and explicit ADD-vs-NEW_BUY opportunity-cost PASS evidence.

However, the stricter G130 question asks whether each ADD increment proves itself as the best next executable capital increment against ADD, NEW_BUY, and Cash. On the focus-window ADD fills, ADD-vs-NEW_BUY is explicit PASS, but ADD-vs-Cash is not explicit PASS. The authoritative rows repeatedly state:

`CASH_PREFERRED_PARTICIPATION_VALID_IS_NOT_ADD_BEATS_CASH`

Therefore the actual design is conformant with the current staged G115 participation-shoulder contract, but only partially conformant with a stricter "true marginal capital winner versus Cash" interpretation.

This audit does not use later PnL, later return, final campaign outcome, MFE/MAE, or old-run performance as production decision-quality evidence.

## Aggregate Funnel

Window:

`2022-10-03` through `2022-12-16`

| Metric | Count |
| --- | ---: |
| PM_ADD_COUNT | 48 |
| PM_NEW_COUNT | 1201 proxy: PC NEW_BUY competitors reaching capital competition |
| PC_NEW_COMPETITOR_COUNT | 1201 |
| PC_ADD_COMPETITOR_COUNT | 48 |
| AUTHORIZED_NEW_COUNT | 182 |
| AUTHORIZED_ADD_COUNT | 15 |
| RUNTIME_BUY_NEW_COUNT | 194 |
| RUNTIME_BUY_ADD_COUNT | 15 |
| FILLED_BUY_NEW_COUNT | 83 |
| FILLED_BUY_ADD_COUNT | 13 |

Notional:

| Metric | JPY |
| --- | ---: |
| NEW_FILL_NOTIONAL | 5,202,110 |
| ADD_FILL_NOTIONAL | 138,210 |

Dates:

| Metric | Value |
| --- | --- |
| ADD_DATES | 13 fill rows across 10 fill dates |
| NEW_DATES | 83 fill rows across 34 fill dates |
| DATES_WITH_ADD_AND_NEW_COMPETITION | all ADD authorization dates had same-date NEW_BUY frontier rows |

`PM_NEW_COUNT` is reported as a proxy because Position Management owns existing-position ADD/HOLD/REDUCE/EXIT, while BUY_NEW originates from candidate / opportunity evidence and reaches PC as NEW_BUY competitors.

## Focus Window ADD Evidence

Focus-window actual BUY_ADD fills:

| Date | Symbol | Prior Qty | ADD Increment | Post-Increment Qty | PM Action | Candidate Score | Best NEW_BUY Score | ADD vs NEW | Cash Classification | Runtime | Fill |
| --- | --- | ---: | ---: | ---: | --- | ---: | ---: | --- | --- | --- | --- |
| 2022-11-29 | 76470 | 1200 | 100 | 1300 | ADD | 0.3189931 | 0.16297291 | EXPLICIT_PASS | SECURITY_FRONTIER_COMPARABLE_WITH_STRONGER_OR_EQUAL_ALTERNATIVE | BUY_ADD | PASS |
| 2022-11-30 | 76470 | 1300 | 100 | 1400 | ADD | 0.34505777 | 0.21260248 | EXPLICIT_PASS | CASH_PREFERRED_PARTICIPATION_VALID_IS_NOT_ADD_BEATS_CASH | BUY_ADD | PASS |
| 2022-12-02 | 76470 | 1400 | 100 | 1500 | ADD | 0.40651062 | 0.25983442 | EXPLICIT_PASS | CASH_PREFERRED_PARTICIPATION_VALID_IS_NOT_ADD_BEATS_CASH | BUY_ADD | PASS |
| 2022-12-06 | 76470 | 1500 | 100 | 1600 | ADD | 0.42251035 | 0.27563508 | EXPLICIT_PASS | CASH_PREFERRED_PARTICIPATION_VALID_IS_NOT_ADD_BEATS_CASH | BUY_ADD | PASS |
| 2022-12-08 | 76470 | 1600 | 100 | 1700 | ADD | 0.41972718 | 0.25153989 | EXPLICIT_PASS | CASH_PREFERRED_PARTICIPATION_VALID_IS_NOT_ADD_BEATS_CASH | BUY_ADD | PASS |

Required ADD fields:

- PM reason for 76470 ADD: `no_loss_averaging`, `opportunity_rank_still_high`, `strong_trend_continuation`.
- incremental investment value: `POSITIVE / PASS`, producer `existing_pc_expected_edge_cascade_contract`.
- opportunity cost: `PASS`, producer `portfolio_construction_same_day_score_competition`.
- lot feasibility: `LOT_EXECUTABLE_COMPATIBLE`.
- position / cap utilization: one executable 100-share increment, headroom preserved.
- final PC authority reason: `COMPARABLE_MARGINAL_RESIDUAL_SHOULDER_ONE_INCREMENT_AUTHORIZED`.
- PS quantity: positive 100-share delta.
- Submit / Fill: PASS for the five filled focus-window ADD rows above.

One additional focus-window ADD authorization occurred on `2022-12-01 / 76470` and reached Runtime BUY_ADD 100, but the same-day Submit/Fill evidence did not materialize that ADD; the submitted BUY was `45910`. This is outside the primary ADD-vs-NEW/Cash capital-frontier question and is not used to judge the filled ADD decisions.

## Same-Date NEW_BUY Frontier

FULL_SAME_DATE_NEW_BUY_FRONTIER_RECONSTRUCTED = `YES`

For each ADD authorization date, the PC `capital_competition.competitors[]` artifact contains the same-date NEW_BUY frontier. Examples in the focus window:

| Date | ADD | NEW_BUY Frontier Count | Executable NEW_BUY Receiving Capital |
| --- | --- | ---: | --- |
| 2022-11-29 | 76470 | 24 | 76920 |
| 2022-11-30 | 76470 | 10 | 21200 |
| 2022-12-01 | 76470 | 15 | 45910 |
| 2022-12-02 | 76470 | 21 | 64880 |
| 2022-12-06 | 76470 | 24 | 79010, 54710 |
| 2022-12-08 | 76470 | 25 | 37790, 82560, 61440 |

ADD_VS_NEW_FULL_FRONTIER = `YES`

Every actual filled focus-window ADD has ADD opportunity-cost PASS against best same-date NEW_BUY score.

ADD_VS_NEW_EXPLICIT_PASS_COUNT = `5`

ADD_VS_NEW_IMPLICIT_PASS_COUNT = `0`

ADD_VS_NEW_NOT_COMPARED_COUNT = `0`

ADD_VS_NEW_CONTRACT_GAP_COUNT = `0`

ADD_VS_NEW_EXPLICIT_PASS_RATE = `5/5`

## ADD vs ADD Competition

ADD_VS_ADD_FULL_FRONTIER = `YES`

Current Post-G129 artifacts include:

- `add_vs_add_frontier_complete = true`
- `add_vs_new_buy_final_frontier_complete = true`
- `cash_first_class_in_marginal_frontier = true`
- `marginal_lot_reevaluation_present = true`
- `symbol_order_privilege = false`

The only multiple-ADD authorized day in the audited window was `2022-10-12`:

| Date | Frontier Iteration | Symbol | Candidate Score | Best NEW_BUY Score | Budget Before | Budget After |
| --- | ---: | --- | ---: | ---: | ---: | ---: |
| 2022-10-12 | 1 | 94320 | 0.4254797 | 0.15602367 | 0.090496 | 0.075350 |
| 2022-10-12 | 2 | 94340 | 0.28578058 | 0.15602367 | 0.075350 | 0.061278 |

The order is consistent with candidate score in this observed case. No first-come, symbol-order, or repeated-prior-ADD advantage was proven from the artifacts.

ADD_VS_ADD_EXPLICIT_PASS_RATE = `1/1 multiple-ADD day frontier order consistent`

ADD_ALLOCATION_ORDER_DEPENDENT = `NO`

UNINTENDED_INCUMBENCY_ADVANTAGE = `UNPROVEN`

## ADD vs Cash

ADD_VS_CASH_FULL_FRONTIER = `PARTIAL`

Cash is present as a first-class frontier participant in the G115 authority, but most observed ADD authorizations are not explicit ADD-over-Cash wins. They are staged comparable-marginal one-increment authorizations under a participation shoulder.

Focus-window classification:

| Classification | Count |
| --- | ---: |
| EXPLICIT_ADD_BEATS_CASH | 0 |
| PARTICIPATION_SHOULDER_ONLY | 4 |
| SECURITY_FRONTIER_COMPARABLE_WITH_STRONGER_OR_EQUAL_ALTERNATIVE | 1 |
| NOT_EVALUATED | 0 |
| INSUFFICIENT_EVIDENCE | 0 |
| CONTRACT_GAP | 0 |

ADD_MARGINAL_VALUE_EXPLICITLY_BEATS_CASH_RATE = `0/5`

This is the core partial-conformance finding. `CASH_PREFERRED_PARTICIPATION_VALID` is explicitly not equivalent to "ADD beats Cash"; the row says so. This is consistent with current G115 staged participation semantics, but it does not prove the strictest G130 marginal-capital interpretation.

## Repeated ADD Freshness

Repeated focus-window ADDs after first 76470 ADD:

| Date | Symbol | Category | New same-date evidence |
| --- | --- | --- | --- |
| 2022-11-30 | 76470 | FRESH_MARGINAL_REEVALUATION | current same-date candidate score, expected-edge PASS, opportunity-cost PASS, G115 iteration |
| 2022-12-02 | 76470 | FRESH_MARGINAL_REEVALUATION | current same-date candidate score, expected-edge PASS, opportunity-cost PASS, G115 iteration |
| 2022-12-06 | 76470 | FRESH_MARGINAL_REEVALUATION | current same-date candidate score, expected-edge PASS, opportunity-cost PASS, G115 iteration |
| 2022-12-08 | 76470 | FRESH_MARGINAL_REEVALUATION | current same-date candidate score, expected-edge PASS, opportunity-cost PASS, G115 iteration |

REPEATED_ADD_FRESH_REEVALUATION_RATE = `4/4`

The repeated 76470 ADDs are not stale-evidence reuse in the artifacts. Each carries same-date opportunity score and same-date G115 authority. The partial issue is not freshness; it is Cash marginal dominance.

## Anchor Campaigns

### 76470

Observed exact focus-window ADD path:

`1200 -> 1300 -> 1400 -> 1500 -> 1600 -> 1700`

All five filled increments:

- PM ADD = YES.
- incremental investment value = POSITIVE/PASS.
- opportunity cost = PASS vs best same-date NEW_BUY.
- lot state = executable.
- PS positive quantity = 100.
- Runtime semantic = BUY_ADD.
- fill = YES.

76470_REPEATED_ADD_DECISION_CONFORMANT = `PARTIAL`

Reason: NEW_BUY comparison and freshness are conformant; explicit ADD-over-Cash proof is absent for the repeated comparable-marginal participation-shoulder rows.

### 94320

Observed Post-G129 ADD fills:

`200 -> 300 -> 400 -> 500 -> 600 -> 700`

Dates:

- 2022-10-12
- 2022-10-28
- 2022-11-01
- 2022-11-04
- 2022-11-09

Each authorized ADD row has ADD-vs-NEW score PASS and is classified as `COMPARABLE_MARGINAL_RESIDUAL_SHOULDER_ONE_INCREMENT_AUTHORIZED`. Like 76470, the repeated increments are refreshed same-date, but the Cash comparison is participation-shoulder rather than explicit ADD-over-Cash.

94320_REPEATED_ADD_DECISION_CONFORMANT = `PARTIAL`

### 94340

Observed Post-G129 path:

- Initial BUY_NEW: 2022-10-03, 200 shares.
- ADD filled: 2022-10-06, 2022-10-12, 2022-10-13.
- Quantity reaches 500.
- From 2022-10-14 through 2022-12-06, PM action is HOLD, not ADD.
- On 2022-12-07, PM action becomes EXIT with reason `weak_hold_score`.

94340_ADD_STOP_REASON =
`PM stopped emitting ADD after 2022-10-13; subsequent same-date PM evidence was HOLD with structured_hold_worthiness / downside_risk_contained rather than ADD, then EXIT on 2022-12-07 via weak_hold_score. No PC/PS/Runtime ADD suppression was observed after PM stopped requesting ADD.`

UNBOUNDED_ADD_BEHAVIOR_CONFIRMED = `NO`

94340 is a useful control: G129 did not create automatic unbounded ADD.

## Counterfactual Capital Destination

This is decision-time only and does not use later performance.

For every focus-window actual ADD fill, a same-date selected NEW_BUY competitor existed:

| Date | ADD | Next canonical selected NEW_BUY competitor if ADD increment were absent |
| --- | --- | --- |
| 2022-11-29 | 76470 | 76920 |
| 2022-11-30 | 76470 | 21200 |
| 2022-12-02 | 76470 | 64880 |
| 2022-12-06 | 76470 | 79010 / 54710 frontier; largest accepted NEW_BUY 79010 |
| 2022-12-08 | 76470 | 37790 / 82560 / 61440 frontier; largest accepted NEW_BUY 61440 |

NEXT_CANONICAL_COMPETITOR_IDENTIFIED_RATE = `5/5`

This is not a performance counterfactual and no later return was used.

## BUY_NEW Fairness

BUY_NEW_CAN_BEAT_ADD_IN_ACTUAL_FRONTIER = `YES`

BUY_NEW_STRUCTURALLY_DISADVANTAGED = `NO`

Evidence:

- All ADD authorization dates retained full NEW_BUY frontier rows.
- NEW_BUY competitors received executable capital on ADD dates.
- G129 did not add an ADD-only priority override.
- `capital_competition_authority.new_buy_automatic_priority = false`.
- `capital_competition_authority.add_automatic_priority = false`.
- Runtime does not re-rank capital priority.

BUY_NEW_CAN_BEAT_ADD_RATE = `observed qualitatively; exact binary rate not derivable because multi-allocation permits ADD and NEW_BUY to both receive capital on the same date`

## Authority Topology

NEW_ADD_FINAL_CAPITAL_PRIORITY_PRODUCER =
`PORTFOLIO_CONSTRUCTION / capital_competition.canonical_add_marginal_capital_competition_authority`, consuming PM ADD, candidate opportunity evidence, Market-Candidate-Cash, Risk Pacing, and budget envelope.

ADD_ADD_FINAL_CAPITAL_PRIORITY_PRODUCER =
`PORTFOLIO_CONSTRUCTION / canonical_add_marginal_capital_competition_authority.frontier_iteration`

SECURITY_CASH_FINAL_CAPITAL_PRIORITY_PRODUCER =
`PORTFOLIO_CONSTRUCTION / market_candidate_cash_interaction + canonical_add_marginal_capital_competition_authority`

Architecture gap status:

`PARTIAL`: a producer exists and records Cash as first-class, but the filled focus-window ADD rows mostly rely on `COMPARABLE_MARGINAL_RESIDUAL_SHOULDER_ONE_INCREMENT_AUTHORIZED`, not explicit ADD-over-Cash dominance.

## Defect Classification

Problematic or partial cases classify as:

| Class | Count | Meaning |
| --- | ---: | --- |
| A correct decision, evidence complete | 0 |
| C ADD vs NEW comparison missing | 0 |
| D ADD vs ADD comparison missing | 0 |
| E ADD vs Cash marginal comparison missing / partial | 5 |
| F repeated ADD uses stale evidence | 0 |
| G incumbent campaign structural advantage | 0 proven |
| H BUY_NEW evidence not consumed correctly | 0 |
| I capital priority producer disagreement | 0 |
| J lot/discrete artifact changes winner unexpectedly | 0 |
| K observability gap only | 0 |

The E classification is not based on poor later return. It is based on the same-date authority rows stating that participation-valid is not ADD-beats-Cash.

## Required Metrics

TOTAL_ADD_FILLS = `13`

TOTAL_NEW_FILLS = `83`

ADD_FILL_NOTIONAL = `138,210`

NEW_FILL_NOTIONAL = `5,202,110`

ADD_DATES = `10 filled ADD dates`

NEW_DATES = `34 filled NEW dates`

DATES_WITH_ADD_AND_NEW_COMPETITION = `14 ADD authorization dates with NEW_BUY frontier present`

ADD_VS_NEW_EXPLICIT_PASS_RATE = `5/5 focus-window actual ADD fills`

ADD_VS_ADD_EXPLICIT_PASS_RATE = `1/1 multiple-ADD day frontier order consistent`

ADD_VS_CASH_EXPLICIT_PASS_RATE = `0/5 focus-window actual ADD fills`

REPEATED_ADD_FRESH_REEVALUATION_RATE = `4/4 focus-window repeated ADDs`

BUY_NEW_CAN_BEAT_ADD_RATE = `not exactly derivable under multi-allocation; actual NEW_BUY capital observed on ADD dates`

NEXT_CANONICAL_COMPETITOR_IDENTIFIED_RATE = `5/5`

## Required Judgments

POST_G129_ADD_NEW_CAPITAL_COMPETITION_CONFORMANT = `PARTIAL`

FULL_SAME_DATE_NEW_BUY_FRONTIER_RECONSTRUCTED = `YES`

ADD_VS_NEW_FULL_FRONTIER = `YES`

ADD_VS_ADD_FULL_FRONTIER = `YES`

ADD_VS_CASH_FULL_FRONTIER = `PARTIAL`

ADD_VALUE_IS_TRUE_INCREMENTAL_MARGINAL_VALUE = `PARTIAL`

REPEATED_ADD_FRESH_REEVALUATION = `YES`

BUY_NEW_STRUCTURALLY_DISADVANTAGED = `NO`

UNINTENDED_INCUMBENCY_ADVANTAGE = `UNPROVEN`

76470_REPEATED_ADD_DECISION_CONFORMANT = `PARTIAL`

94320_REPEATED_ADD_DECISION_CONFORMANT = `PARTIAL`

94340_ADD_STOP_REASON =
`PM ceased ADD after 2022-10-13 and held 500 shares until 2022-12-07 EXIT on weak_hold_score; no unbounded ADD path observed.`

MANDATORY_REPAIR_FOUND = `NO`

REPAIR_BOUNDARY =
`NONE_FOR_G130; if stricter true ADD-over-Cash marginal dominance is required, the narrow next boundary is PORTFOLIO_CONSTRUCTION / canonical_add_marginal_capital_competition_authority classification of COMPARABLE_MARGINAL_RESIDUAL_SHOULDER_ONE_INCREMENT_AUTHORIZED.`

FUTURE_INFORMATION_USED_FOR_DECISION_AUDIT = `NO`

PERFORMANCE_ATTRIBUTION_USED_FOR_DECISION_JUDGMENT = `NO`

CODE_CHANGED = `NO`

CONFIG_CHANGED = `NO`

FRESH_RUN_EXECUTED = `NO`

RESUME_EXECUTED = `NO`

REPLAY_EXECUTED = `NO`

LONG_HISTORICAL_EXECUTED = `NO`

RUN_MUTATED = `NO`

## Performance Attribution

Performance divergence was only the trigger for this audit. No later PnL or old-run outcome was used to decide whether ADD or NEW_BUY was correct.

Descriptive-only observation:

Post-G129 completed artifacts show BUY_ADD materialization increased materially relative to G127/G128's diagnostic state: `13` filled ADD rows were observed by `2022-12-16`, while G127 had only `5` true ADD fills across a much longer completed window before G129. This confirms G129 activated ADD materialization; it does not prove the economic correctness of each ADD.

PERFORMANCE_ATTRIBUTION_USED_FOR_DECISION_JUDGMENT = `NO`

## Recommended Next Action

G131 should be a narrow design/acceptance task, not tuning:

Determine whether the current G115 `COMPARABLE_MARGINAL_RESIDUAL_SHOULDER_ONE_INCREMENT_AUTHORIZED` contract is intentionally allowed to authorize one ADD lot when Cash is first-class but not explicitly beaten, or whether authoritative ADD should require explicit ADD-over-Cash marginal dominance.

Do not introduce fixed ADD limits, cooldowns, holding periods, regime multipliers, performance-derived thresholds, or symbol filters.
