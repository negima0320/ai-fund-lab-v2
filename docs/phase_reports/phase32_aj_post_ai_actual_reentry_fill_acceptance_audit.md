# Phase32-AJ — Post-AI Actual REENTRY Fill Acceptance Audit

## Executive Summary

Phase32-AI is observed on the actual fresh-run path for the target case `83060`. On `2022-10-26`, `83060` was a semantic `REENTRY`, carried strict prior PM exit context from the `2022-10-04` PM EXIT, passed recovery and safety, received positive target capital, was selected/planned for `BUY`, had executable quantity `100`, and received an actual `BUY` fill for `100`.

The old and new campaigns are distinct:

- Old campaign: `pc-18fbb6a878b4a2a9-83060-0001`
- New fill campaign: `pc-a0ba4ed1846ca7b1-83060-0002`

This confirms the actual REENTRY business path. Two provenance caveats remain: the serialized pending snapshot and fill row still carry empty or `MISSING` decision linkage fields, and the `2022-10-26` current-valuation projection temporarily shows a different generated campaign id for the reopened position. The `2022-10-27` campaign artifact materializes the expected new campaign id. Therefore the REENTRY acceptance itself is `YES`, while the full canonical lineage path is judged `PARTIAL`.

## Run Identity

- Run id: `runtime-test-historical-extended-smoke-20260827T085323245637Z`
- Evidence root: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T085323245637Z`
- Observed run state: `RUNNING`
- Audited period: `2022-10-03` through `2022-10-26`, with `2022-10-27` campaign materialization checked for post-fill identity.
- Constraints honored: no production/config/schema/threshold/model/runtime-state mutation; no fresh-run, resume, replay, or backtest.

## 83060 Lifecycle

| Date | Artifact | Observation |
| --- | --- | --- |
| 2022-10-03 | `execution/fills.json` | `BUY 100`, campaign `pc-18fbb6a878b4a2a9-83060-0001` |
| 2022-10-04 | `position_management/pm_decisions.json` | PM EXIT decision `pm-2022-10-04-83060-exit`, reason code `trend_and_opportunity_broken`, campaign `pc-18fbb6a878b4a2a9-83060-0001` |
| 2022-10-04 | `execution/fills.json` | `SELL 100`, same old campaign, `source_decision_id=pm-2022-10-04-83060-exit` |
| 2022-10-25 | `strategy/portfolio_construction.json` | First eligible semantic REENTRY row observed; target positive and PS executable, but no fill |
| 2022-10-26 | strategy/planning/execution artifacts | Semantic REENTRY selected, runtime BUY planned, actual `BUY 100` fill |
| 2022-10-27 | `positions/position_campaigns.json` | Open campaign materialized as `pc-a0ba4ed1846ca7b1-83060-0002` |

## 83060 Semantic And Gate Evidence

### 2022-10-25

`83060` was already semantically repaired before the fill day:

- `semantic_buy_type=REENTRY`
- `prior_exit_business_date=2022-10-04`
- `prior_exit_reason=trend_and_opportunity_broken`
- `previous_exit_reason_class=TREND_MOMENTUM`
- `reentry_cooldown_status=PASS`
- `reentry_recovery_status=PASS`
- `reentry_recovery_reason=reentry_recovery_qualified`
- `reentry_opportunity_qualification_status=PASS`
- `reentry_trend_recovery_status=PASS`
- `reentry_momentum_recovery_status=PASS`
- `reentry_continuation_quality_status=PASS`
- `reentry_downside_risk_status=PASS`
- `reentry_safety_restriction_status=PASS`
- `reentry_semantic_status=PASS`
- `reentry_semantic_state=REENTRY_ELIGIBLE`
- `target_weight=0.068203`
- `requested_buy_new_weight=0.032258`
- `accepted_buy_new_weight=0.032258`
- `target_member_eligibility.status=PASS`
- `current_competitor_status=COMPETITOR_SELECTED`
- PS `executable_quantity=100`

No `83060` execution fill was found for `2022-10-25`.

### 2022-10-26

The actual fill day carries the complete REENTRY gate chain:

| Gate | Field / Value |
| --- | --- |
| Semantic type | `semantic_buy_type=REENTRY` |
| Strict prior context | prior exit date `2022-10-04`, reason `trend_and_opportunity_broken`, class `TREND_MOMENTUM` |
| Cooldown | `reentry_cooldown_status=PASS`, `business_days_since_exit=15` |
| Opportunity | `reentry_opportunity_qualification_status=PASS` |
| Trend recovery | `reentry_trend_recovery_status=PASS` |
| Momentum recovery | `reentry_momentum_recovery_status=PASS` |
| Recovery aggregate | `reentry_recovery_status=PASS`, reason `reentry_recovery_qualified` |
| Continuation | `reentry_continuation_quality_status=PASS` |
| Downside | `reentry_downside_risk_status=PASS` |
| Safety | `reentry_safety_restriction_status=PASS` |
| Semantic state | `reentry_semantic_state=REENTRY_ELIGIBLE` |
| Broker eligibility | `broker_eligibility_status=PASS`, reason `BROKER_PRODUCT_CATEGORY_SUPPORTED` |
| Rank | `opportunity_buy_rank=9`, `construction_priority=16` |
| Quality | `quality_status=PASS`, `reentry_buy_quality_action=REDUCED_ALLOCATION_ONLY` |
| Target | `target_weight=0.067378` |
| Requested | `requested_buy_new_weight=0.038462` |
| Accepted | `accepted_buy_new_weight=0.038462` |
| Lot-aware target | `lot_aware_final_target_weight=0.067378` |
| PC selection | `current_competitor_status=COMPETITOR_SELECTED` |
| PS executable | `executable_quantity=100`, `quantity_delta=100` |
| Runtime planning | selected in `morning/planning_evidence.json` |
| Execution | `BUY 100` fill in `execution/fills.json` |

The minimum executable one-lot authority admitted the target:

- `authority_type=PORTFOLIO_CONSTRUCTION_MINIMUM_EXECUTABLE_ONE_LOT_ADMISSION`
- `decision=ADMIT`
- `admission_decision=PASS`
- `intent=REENTRY`
- `one_lot_quantity=100`
- `one_lot_notional=70940`
- `final_promoted_target_weight=0.067378`
- `ps_final_quantity=100`
- `safety_hard_cap_preserved=true`
- `strategy_cap_preserved=true`

## Capital Competition And Sizing

For `2022-10-26`, `83060` participated in normal target/member competition and was selected:

- `target_member_eligibility.status=PASS`
- `target_resolution.status=PASS`
- `target_resolution.reason=lot_aware_final_reallocation`
- `current_competitor_status=COMPETITOR_SELECTED`
- `competitor_type=NEW_BUY`
- `requested_weight=0.067378`
- `accepted_weight=0.067378`
- `reason_codes` include `COMPETITOR_SELECTED` and `RISK_PACING_GRADUAL_CONFIRMED_COMPETITOR_ALLOWED`

Position sizing then authorized executable quantity:

- `evidence_class=EXECUTABLE`
- `executable_quantity=100`
- `quantity_delta=100`
- `requested_notional=70940`
- `requested_weight=0.067378`
- `target_weight=0.067378`
- `lot_size=100`

The marginal cash/competition diagnostic still reports `CASH_OPTIONALITY` as the top-level interaction winner and labels `83060` as `CASH_PREFERRED`/`LOSER` in that diagnostic layer. This did not block canonical deployment: the same day-local artifacts show `83060` selected, pending-feasible, quantity-authorized, submitted through execution authority, and filled.

## Runtime BUY And Fill

`2022-10-26/morning/planning_evidence.json` shows:

- `status=PASS`
- `selected_symbols` includes `83060`
- `pending_item_count=6`
- `production_decision_allowed=true`
- `strategy_artifact_eligibility=ELIGIBLE_FOR_PLANNING_AUTHORITY`
- `legacy_planning_authority_used=false`
- `runtime_switch_performed=false`
- `broker_write_performed=false`

The day-local pending snapshot embedded in `current_valuation_refresh/current_valuation_manifest.json` shows `83060` as:

- `side=BUY`
- `state=CONSUMED`
- `quantity=100`
- `reference_price=709.4`
- `pending_item_id=strategy-775b635dcbdfb3798d14`
- `planning_submit_feasibility.status=PASS`
- `canonical_discrete_quantity_submit_authority.status=PASS`
- `one_lot_submit_authority.status=PASS`
- `authorized_quantity=100`

The execution fill is present:

- `execution_id=execution-equivalent:sha256:d5829ba220d4e9793e639693da135524187a36912c86245bd023786e5745a12a`
- `order_id=sha256:d5829ba220d4e9793e639693da135524187a36912c86245bd023786e5745a12a`
- `symbol=83060`
- `side=BUY`
- `source_decision_type=BUY`
- `quantity=100`
- `execution_price=711.5`
- `gross_notional=71150`
- `position_campaign_id=pc-a0ba4ed1846ca7b1-83060-0002`

## Campaign Identity

The old campaign opened and closed cleanly:

- Open: `2022-10-03 BUY 100`, campaign `pc-18fbb6a878b4a2a9-83060-0001`
- Close: `2022-10-04 SELL 100`, campaign `pc-18fbb6a878b4a2a9-83060-0001`
- PM close authority: `pm-2022-10-04-83060-exit`, reason `trend_and_opportunity_broken`

The REENTRY fill created a distinct new campaign:

- `2022-10-26 BUY 100`, campaign `pc-a0ba4ed1846ca7b1-83060-0002`
- `2022-10-27 positions/position_campaigns.json` shows that same campaign open with `current_quantity=100`, `opened_business_date=2022-10-26`, and `average_price=711.5`.

Residual campaign caveat: `2022-10-26/current_valuation_refresh/current_valuation_manifest.json` shows the candidate current position using `pc-8b423cfaeb07bb90-83060-0001`, while the fill and next-day campaign artifact use `pc-a0ba4ed1846ca7b1-83060-0002`. This is a projection/materialization parity issue to monitor, not evidence that the REENTRY fill failed.

## Lineage And Bypass Check

No runtime bypass was observed:

- `legacy_planning_authority_used=false`
- `runtime_switch_performed=false`
- runtime quantity contract reports `legacy_planning_used=false`
- runtime quantity contract reports `legacy_position_sizing_used=false`
- `cash_winner_redecision_runtime=false`
- `lower_priority_implicit_promotion_runtime=false`
- `ps_authorized_quantity_reoptimized_by_runtime=false`
- pending submit feasibility consumed canonical PC/PS quantity authority

However, full lineage preservation is not perfect in the serialized execution artifacts:

- Day-local pending snapshot has `source_decision_id=""`, `source_pm_decision_id=""`, and `position_campaign_id=""`.
- Fill row has `source_decision_id=MISSING`, `pending_item_id=MISSING`, and `order_plan_item_id=MISSING`.

Judgment: the actual REENTRY path is accepted for semantic/sizing/execution behavior, but the canonical identity lineage is still `PARTIAL`.

## 25BD REENTRY Funnel Through 2022-10-26

Canonical day-symbol counts from portfolio construction, position sizing, and fills:

| Funnel stage | Count |
| --- | ---: |
| Semantic REENTRY rows | 122 |
| Unique REENTRY symbols | 21 |
| Strict non-GENERIC prior context | 87 |
| Safety PASS | 122 |
| Recovery PASS | 2 |
| REENTRY_ELIGIBLE | 2 |
| Positive target | 2 |
| Selected target member | 2 |
| Competitor selected | 2 |
| PS executable quantity > 0 | 2 |
| Actual REENTRY fills | 1 |

The two eligible/positive/executable rows are both `83060` on `2022-10-25` and `2022-10-26`; only `2022-10-26` filled. Excluding `83060`, no other REENTRY rows reached eligibility or fill by `2022-10-26`.

Unique REENTRY symbols observed:

`17570`, `33580`, `33700`, `41650`, `44220`, `44870`, `45750`, `48330`, `59860`, `65500`, `66190`, `73560`, `73590`, `76470`, `79220`, `83060`, `89180`, `91070`, `92540`, `93600`, `96100`.

## Portfolio Difference

Compared with the pre-AI baseline run for `2022-10-26`, the post-AI run includes the `83060` REENTRY fill:

- Pre-AI cash after valuation: `198580`
- Post-AI cash after valuation: `183230`
- Difference: `-15350`

Fill set difference:

- Post-AI adds `83060 BUY 100 @ 711.5` and `21630 BUY 100 @ 528.5`
- Pre-AI instead has `30930 BUY 100 @ 1086.5`
- Net cash effect: `(71150 + 52850) - 108650 = 15350`

Therefore the `2022-10-26` portfolio difference is partially explained by the `83060` REENTRY fill, but not solely; there is also a same-day buy selection substitution involving `21630` and `30930`.

## Defect / No-Defect Judgment

No Phase32-AI safety repair defect is observed on the target actual path. The repaired structured taxonomy permits the legitimate `83060` REENTRY once strict prior PM context, recovery, continuation, downside, safety, quality, capital selection, and sizing are all satisfied.

Residual non-blocking issues remain in lineage/projection materialization:

- Missing source and pending identifiers in the final fill row.
- Empty source/campaign fields in the day-local pending snapshot.
- Temporary mismatch between same-day current valuation campaign id and the fill/new campaign id.

These should be tracked as provenance/materialization follow-up, not as evidence that the REENTRY safety repair failed.

## Recommendation

Longer validation is ready. Continue with a user-operated longer fresh validation, while monitoring campaign identity parity and execution fill lineage preservation for reopened REENTRY positions.

## Final Judgments

PHASE32_AJ_83060_SEMANTIC_REENTRY = YES

PHASE32_AJ_STRICT_PRIOR_CONTEXT = YES

PHASE32_AJ_RECOVERY_PASS = YES

PHASE32_AJ_SAFETY_PASS = YES

PHASE32_AJ_REENTRY_ELIGIBLE = YES

PHASE32_AJ_POSITIVE_TARGET = YES

PHASE32_AJ_NORMAL_CAPITAL_COMPETITION = YES

PHASE32_AJ_SELECTED = YES

PHASE32_AJ_EXECUTABLE_QUANTITY = 100

PHASE32_AJ_RUNTIME_BUY = YES

PHASE32_AJ_FILL_QUANTITY = 100

PHASE32_AJ_NEW_CAMPAIGN_CREATED = YES

PHASE32_AJ_OLD_NEW_CAMPAIGN_DISTINCT = YES

PHASE32_AJ_CANONICAL_REENTRY_PATH = PARTIAL

PHASE32_AJ_LEGACY_OR_BYPASS_PATH_USED = NO

PHASE32_AJ_2022_10_26_PORTFOLIO_DIFFERENCE_EXPLAINED_BY_REENTRY = PARTIAL

PHASE32_AJ_OTHER_REENTRY_ELIGIBLE_TOTAL = 0

PHASE32_AJ_OTHER_REENTRY_FILL_TOTAL = 0

PHASE32_AJ_83060_ACTUAL_REENTRY_ACCEPTED = YES

PHASE32_AJ_REENTRY_SAFETY_REPAIR_ACTUAL_PATH_ACCEPTED = YES

PHASE32_AJ_LONGER_VALIDATION_READY = YES

PHASE32_AJ_NEXT_STEP = User-operated longer fresh validation; monitor reopened-position campaign identity parity and fill lineage fields.
