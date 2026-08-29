# Phase32-Z Post-Y 25BD Actual-Path REENTRY Acceptance Audit

## Executive Summary

Run `runtime-test-historical-extended-smoke-20260827T045032683611Z` completed all 25 requested business days from `2022-10-03` through `2022-11-08`, then closed as `REVIEW_REQUIRED`. The close review is non-blocking strategy shadow review; daily runtime jobs were not halted.

Phase32-Y is partially observed in the actual fresh-run path:

- Real PM id is present for the 2022-10-04 83060 `SELL_EXIT` in PM, serialized pending history, persistent order ledger, and persistent execution ledger.
- `runtime-current-83060` remains only as nested current-position lineage and is not used as the canonical PM id.
- Campaign provenance is not preserved into serialized pending/order/execution for 83060: PM and fill artifacts show `pc-9147a5f91c842b2f-83060-0001`, but pending/order/execution ledger `position_campaign_id` is blank.
- The strict prior bridge never matches PM EXIT reason evidence: `pm_exit_reason_matched_close_count = 0` on every strategy input manifest.
- All 236 semantic REENTRY day-symbol rows remain `previous_exit_reason_class = GENERIC`, with `prior_exit_reason = EXIT` and no `STRICT_PRIOR_PM_DECISION_EVIDENCE`.

Primary conclusion: Phase32-Y fixed the durable PM id path but did not achieve full REENTRY semantic acceptance. The remaining actual-path blocker is strict prior PM context materialization, most likely because the bridge contract validates campaign as well as symbol/date/id and the campaign is blank in the persistent ledger path.

No production code/config/threshold/model/runtime state changes were made. No fresh-run/resume/replay/backtest was executed.

## Run Identity

- Run id: `runtime-test-historical-extended-smoke-20260827T045032683611Z`
- Evidence root: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T045032683611Z`
- Period: `2022-10-03` to `2022-11-08`
- Completed business days: 25
- Runtime status: `COMPLETED`
- Final status: `REVIEW_REQUIRED`
- Fresh-run summary: `failed_step = close`, `error = close returned REVIEW_REQUIRED`, `exit_code = 10`
- Final summary: `halt_summary.status = NOT_HALTED`, `operational_status = PASS`, `strategy_shadow_review_required = true`, `review_summary.non_blocking_review = true`

## 83060 Provenance Trace

### PM Producer

Artifact: `daily/2022-10-04/position_management/pm_decisions.json`

- `pm_decision_id = pm-2022-10-04-83060-exit`
- `decision_type = EXIT`
- `decision_status = SELL_FULL_POSITION`
- `decision_reason = trend_and_opportunity_broken`
- `reason_codes = [trend_and_opportunity_broken]`
- `position_campaign_id = pc-9147a5f91c842b2f-83060-0001`
- `quantity_requested = 100.0`

### Serialized Pending / Order Plan

Artifact read from actual pending history:

`.runtime/pending_order_plan/history/2022-10-04/pending-order-plan-buy-review-sell-continuation-2022-10-04-008865b7ef8e.json`

Nested payload item for `83060`:

- `pending_item_id = strategy-4da5d8f50db97ec0b5b0`
- `side = SELL`
- `quantity = 100.0`
- `source_decision_id = pm-2022-10-04-83060-exit`
- `source_pm_decision_id = pm-2022-10-04-83060-exit`
- `source_decision_type = EXIT`
- `source_pm_business_date = 2022-10-04`
- `source_position_symbol = 83060`
- `position_campaign_id = ""`
- Shallow lineage PM id: `pm-2022-10-04-83060-exit`
- Nested legacy lineage item PM id: `runtime-current-83060`
- `quantity_contract.planning_intent = SELL_EXIT`
- `quantity_contract.source_pm_decision_id = pm-2022-10-04-83060-exit`
- `quantity_contract.position_campaign_id = null`

Interpretation: canonical PM id materialized; campaign did not.

### Persistent Order Ledger

Artifact read from `.runtime/persistent_ledger/orders.jsonl` for `83060`, `2022-10-04`:

Submit order row:

- `record_id = ledger-order-submit-fdd75f01a314a4e4`
- `source = runtime_v2_submit_pipeline`
- `pending_item_id = strategy-4da5d8f50db97ec0b5b0`
- `side = SELL`
- `status = ACCEPTED`
- `source_decision_id = pm-2022-10-04-83060-exit`
- `source_pm_decision_id = pm-2022-10-04-83060-exit`
- `source_decision_type = EXIT`
- `source_pm_business_date = 2022-10-04`
- `source_position_symbol = 83060`
- `position_campaign_id = ""`

Execution readonly order row:

- `record_id = ledger-order-0a0fa25e5c76574b`
- `source = runtime_v2_execution_readonly_simulation`
- `pending_item_id = strategy-4da5d8f50db97ec0b5b0`
- `side = SELL`
- `status = filled`
- PM id fields match `pm-2022-10-04-83060-exit`
- `position_campaign_id = ""`

### Persistent Execution Ledger

Artifact read from `.runtime/persistent_ledger/executions.jsonl`:

BUY:

- `business_date = 2022-10-03`
- `side = BUY`
- `quantity = 100.0`
- `source_decision_id = ""`
- `source_pm_decision_id = ""`
- `position_campaign_id = ""`

SELL:

- `business_date = 2022-10-04`
- `side = SELL`
- `quantity = 100.0`
- `source_decision_id = pm-2022-10-04-83060-exit`
- `source_pm_decision_id = pm-2022-10-04-83060-exit`
- `source_decision_type = EXIT`
- `source_pm_business_date = 2022-10-04`
- `source_position_symbol = 83060`
- `position_campaign_id = ""`

Daily fill artifact `daily/2022-10-04/execution/fills.json` has:

- `source_decision_id = pm-2022-10-04-83060-exit`
- `source_decision_type = EXIT`
- `position_campaign_id = pc-9147a5f91c842b2f-83060-0001`

Interpretation: fill evidence has the campaign, but persistent ledger rows do not.

## Strict Prior Bridge Evidence

The bridge materialized evidence in daily `strategy/input_manifest.json` under `strategy_input_sources.prior_exit_state`.

Examples:

- `2022-10-05`: `candidate_supplied_count = 2`, `supplied_symbols = [83060, 89180]`, `pm_exit_reason_evidence_count = 5`, `pm_exit_reason_matched_close_count = 0`, `prior_closed_campaign_count = 3`
- `2022-10-11`: `candidate_supplied_count = 5`, `supplied_symbols = [33700, 41650, 44220, 83060, 89180]`, `pm_exit_reason_evidence_count = 11`, `pm_exit_reason_matched_close_count = 0`, `prior_closed_campaign_count = 6`
- `2022-10-25`: `candidate_supplied_count = 11`, `supplied_symbols` includes `83060`, `pm_exit_reason_evidence_count = 40`, `pm_exit_reason_matched_close_count = 0`, `prior_closed_campaign_count = 23`

The manifest states the join contract:

`execution.source_decision_id == pm.pm_decision_id/decision_id with symbol/date/campaign validation`

Because persistent ledger campaign is blank for the 83060 SELL while PM/fill campaign is populated, the artifact evidence is consistent with PM id propagation succeeding but strict PM reason matching failing at the campaign-validated bridge.

## 83060 REENTRY Timeline

| Date | BD Since Exit | Rank | Cooldown | Opportunity | Trend | Momentum | Continuation | Downside | Quality | Recovery | Reason | Prior Authority | Prior Reason | Class | Target |
| --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: |
| 2022-10-05 | 0 | 10 | FAIL_CLOSED | PASS | FAIL | FAIL | PASS | PASS | PASS | REVIEW_REQUIRED | insufficient_prior_exit_context | None | EXIT | GENERIC | 0.0 |
| 2022-10-06 | 1 | 9 | FAIL_CLOSED | PASS | FAIL | FAIL | PASS | PASS | PASS | REVIEW_REQUIRED | insufficient_prior_exit_context | None | EXIT | GENERIC | 0.0 |
| 2022-10-07 | 2 | 9 | FAIL_CLOSED | PASS | FAIL | FAIL | PASS | PASS | PASS | REVIEW_REQUIRED | insufficient_prior_exit_context | None | EXIT | GENERIC | 0.0 |
| 2022-10-11 | 4 | 9 | PASS | PASS | FAIL | FAIL | PASS | PASS | PASS | REVIEW_REQUIRED | insufficient_prior_exit_context | None | EXIT | GENERIC | 0.0 |
| 2022-10-12 | 5 | 10 | PASS | PASS | FAIL | FAIL | PASS | PASS | PASS | REVIEW_REQUIRED | insufficient_prior_exit_context | None | EXIT | GENERIC | 0.0 |
| 2022-10-13 | 6 | 9 | PASS | PASS | FAIL | FAIL | PASS | PASS | PASS | REVIEW_REQUIRED | insufficient_prior_exit_context | None | EXIT | GENERIC | 0.0 |
| 2022-10-14 | 7 | 9 | PASS | PASS | FAIL | FAIL | PASS | PASS | PASS | REVIEW_REQUIRED | insufficient_prior_exit_context | None | EXIT | GENERIC | 0.0 |
| 2022-10-17 | 8 | 8 | PASS | PASS | FAIL | FAIL | PASS | PASS | PASS | REVIEW_REQUIRED | insufficient_prior_exit_context | None | EXIT | GENERIC | 0.0 |
| 2022-10-18 | 9 | 8 | PASS | PASS | PASS | FAIL | PASS | PASS | PASS | REVIEW_REQUIRED | insufficient_prior_exit_context | None | EXIT | GENERIC | 0.0 |
| 2022-10-19 | 10 | 7 | PASS | PASS | PASS | FAIL | PASS | PASS | PASS | REVIEW_REQUIRED | insufficient_prior_exit_context | None | EXIT | GENERIC | 0.0 |
| 2022-10-20 | 11 | 8 | PASS | PASS | PASS | FAIL | PASS | PASS | PASS | REVIEW_REQUIRED | insufficient_prior_exit_context | None | EXIT | GENERIC | 0.0 |
| 2022-10-21 | 12 | 9 | PASS | PASS | PASS | FAIL | PASS | PASS | PASS | REVIEW_REQUIRED | insufficient_prior_exit_context | None | EXIT | GENERIC | 0.0 |
| 2022-10-24 | 13 | 9 | PASS | PASS | PASS | FAIL | PASS | PASS | PASS | REVIEW_REQUIRED | insufficient_prior_exit_context | None | EXIT | GENERIC | 0.0 |
| 2022-10-25 | 14 | 10 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | REVIEW_REQUIRED | insufficient_prior_exit_context | None | EXIT | GENERIC | 0.0 |
| 2022-10-26 | 15 | 9 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | REVIEW_REQUIRED | insufficient_prior_exit_context | None | EXIT | GENERIC | 0.0 |
| 2022-10-27 | 16 | 10 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | FAIL_CLOSED | reentry_buy_quality_not_requalified | None | EXIT | GENERIC | 0.0 |
| 2022-10-28 | 17 | 11 | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | FAIL_CLOSED | reentry_opportunity_not_requalified | None | EXIT | GENERIC | 0.0 |
| 2022-10-31 | 18 | 13 | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | FAIL_CLOSED | reentry_opportunity_not_requalified | None | EXIT | GENERIC | 0.0 |
| 2022-11-01 | 19 | 13 | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | FAIL_CLOSED | reentry_opportunity_not_requalified | None | EXIT | GENERIC | 0.0 |
| 2022-11-02 | 20 | 14 | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | FAIL_CLOSED | reentry_opportunity_not_requalified | None | EXIT | GENERIC | 0.0 |
| 2022-11-04 | 22 | 14 | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | FAIL_CLOSED | reentry_opportunity_not_requalified | None | EXIT | GENERIC | 0.0 |
| 2022-11-07 | 23 | 16 | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | FAIL_CLOSED | reentry_opportunity_not_requalified | None | EXIT | GENERIC | 0.0 |
| 2022-11-08 | 24 | 18 | PASS | FAIL | PASS | PASS | PASS | PASS | PASS | FAIL_CLOSED | reentry_opportunity_not_requalified | None | EXIT | GENERIC | 0.0 |

## 25BD REENTRY Funnel

Canonical source: daily `strategy/portfolio_construction.json`, `portfolio_members` rows with `semantic_buy_type = REENTRY`.

| Funnel Stage | Count |
| --- | ---: |
| Semantic REENTRY total | 236 |
| Unique symbols | 28 |
| Strict prior PM context | 0 |
| Non-GENERIC prior context | 0 |
| Cooldown PASS | 160 |
| Opportunity qualification PASS | 48 |
| Trend recovery PASS | 106 |
| Momentum recovery PASS | 140 |
| Continuation PASS | 236 |
| Downside PASS | 236 |
| Buy quality PASS | 236 |
| REENTRY_ELIGIBLE | 0 |
| target_weight > 0 | 0 |
| requested_weight > 0 | 0 |
| accepted_weight > 0 | 0 |
| selected | 0 |
| PS executable quantity > 0 | 0 |
| Runtime REENTRY BUY | 0 |
| Actual REENTRY fill | 0 |

Status distributions:

- `previous_exit_reason_class`: `GENERIC = 236`
- `prior_exit_reason`: `EXIT = 236`
- `prior_exit_reason_authority`: absent/None = 236
- `reentry_recovery_reason`: `reentry_opportunity_not_requalified = 188`, `insufficient_prior_exit_context = 44`, `reentry_repeated_unresolved_churn = 3`, `reentry_buy_quality_not_requalified = 1`

Comparison to Pre-Y/W baseline:

- Strict context remains `0 -> 0`.
- Non-GENERIC remains `0 -> 0`.
- Eligible remains `0 -> 0`.
- Selected remains `0 -> 0`.
- Fill remains `0 -> 0`.

## Clearly Strong Again Rows

Using existing PIT-safe evidence and no new thresholds, rows satisfying all of:

- cooldown PASS
- opportunity PASS
- trend recovery PASS
- momentum recovery PASS
- continuation PASS
- downside PASS
- buy quality PASS
- strong rank interpreted as rank `<= 10`

were observed:

- `2022-10-25 83060`, rank 10, target 0.0, blocked by `insufficient_prior_exit_context`
- `2022-10-26 83060`, rank 9, target 0.0, blocked by `insufficient_prior_exit_context`
- `2022-10-27 83060`, rank 10, target 0.0, blocked by `reentry_buy_quality_not_requalified`
- `2022-11-04 93180`, rank 5, target 0.0, blocked by `insufficient_prior_exit_context`
- `2022-11-08 93180`, rank 5, target 0.0, blocked by `insufficient_prior_exit_context`

The main 83060 positive-control rows are `2022-10-25` and `2022-10-26`: all listed strength/recovery gates pass, but target remains zero because strict prior context is not materialized.

## Existing Short-Trend Evidence

Existing artifacts contain enough PIT-safe fields to evaluate renewed strength without adding thresholds:

- `price_momentum_return_5d`: present in `technical_features.json` and buy-quality momentum feature snapshots.
- `momentum_1d_vs_5d_delta`: present in buy-quality momentum feature snapshots.
- `momentum_5d_vs_20d_delta`: present in buy-quality momentum feature snapshots.
- `trend_ma_5_20_ratio`: present in `technical_features.json` and buy-quality momentum feature snapshots.
- `trend_ma_20_60_ratio`: present in buy-quality momentum feature snapshots.
- `trend_close_over_ma_20d`: present in portfolio, technical, and buy-quality artifacts.
- `reentry_trend_recovery_status`: present on all 236 REENTRY rows.
- `reentry_momentum_recovery_status`: present on all 236 REENTRY rows.

Example 83060 `2022-10-25`:

- `price_momentum_return_5d = 0.0413550374`
- `momentum_1d_vs_5d_delta = -0.0345494228`
- `momentum_5d_vs_20d_delta = 0.0080314053`
- `trend_ma_5_20_ratio = 1.0386474148`
- `trend_close_over_ma_20d = 1.0559264822`
- Buy-quality classification: `HEALTHY_CONTINUATION`

Example 83060 `2022-10-26`:

- `price_momentum_return_5d = 0.0300566284`
- `momentum_5d_vs_20d_delta = 0.0058002033`
- `trend_ma_5_20_ratio = 1.0435002153`
- `trend_close_over_ma_20d = 1.0535695721`

## Trading Outcome Equality

Reason category: A/B hybrid, with A dominant.

- A: Phase32-Y did not fully reach semantic actual path because strict prior PM matching remained zero and all REENTRY prior contexts remained GENERIC.
- B: Some rows also later fail current evidence gates such as opportunity requalification, but that is downstream of the unmaterialized strict prior context and is not the primary acceptance result.
- C is not supported: no selected REENTRY rows and no REENTRY fills were observed.

Therefore identical Equity/Cash/Holdings is not a performance failure. It is explained by no REENTRY row receiving non-generic strict prior context, no row becoming REENTRY_ELIGIBLE, and all REENTRY weights remaining zero.

## REVIEW_REQUIRED Separation

The run-level `REVIEW_REQUIRED` is separated from REENTRY acceptance:

- `final_summary.json` reports `runtime_status = COMPLETED`, `halt_summary.status = NOT_HALTED`, `operational_status = PASS`.
- `close_authority_classification.strategy_review_status = REVIEW_REQUIRED`.
- `review_summary.non_blocking_review = true`.
- Daily morning/submit/execution/day-completion checks showed no non-pass runtime job status in the audited command summary.

This close review should not be interpreted as a REENTRY acceptance failure or runtime halt.

## Defect / No-Defect Judgment

No production behavior was changed in this audit.

Observed defect status:

- PM id provenance: repaired and observed in actual path.
- Campaign provenance: not repaired in actual serialized pending/order/execution path for 83060.
- Strict prior PM reason bridge: not accepted; match count remains zero.
- REENTRY semantic context: not accepted; all rows remain generic.

Minimum Phase32-Z acceptance condition is not met because:

- `pm_exit_reason_matched_close_count > 0`: not observed
- `prior_exit_reason_authority = STRICT_PRIOR_PM_DECISION_EVIDENCE`: not observed
- `previous_exit_reason_class != GENERIC`: not observed

## Final Judgments

PHASE32_Z_Y_PENDING_PM_PROVENANCE_OBSERVED = YES

PHASE32_Z_Y_LEDGER_PM_PROVENANCE_OBSERVED = YES

PHASE32_Z_STRICT_PRIOR_PM_MATCH_OBSERVED = NO

PHASE32_Z_NON_GENERIC_REENTRY_CONTEXT_OBSERVED = NO

PHASE32_Z_SEMANTIC_REENTRY_TOTAL = 236

PHASE32_Z_STRICT_CONTEXT_REENTRY = 0

PHASE32_Z_REENTRY_ELIGIBLE = 0

PHASE32_Z_POSITIVE_TARGET_REENTRY = 0

PHASE32_Z_SELECTED_REENTRY = 0

PHASE32_Z_REENTRY_FILL = 0

PHASE32_Z_PRIMARY_POST_CONTEXT_BLOCKER = strict_prior_pm_context_not_materialized; pm_exit_reason_matched_close_count=0; prior_exit_reason_authority=None; previous_exit_reason_class=GENERIC; campaign provenance blank in serialized pending/order/execution while PM/fill campaign is populated

PHASE32_Z_CLEARLY_STRONG_AGAIN_ROWS_EXIST = YES

PHASE32_Z_CLEARLY_STRONG_AGAIN_STILL_BLOCKED = YES

PHASE32_Z_EXISTING_EVIDENCE_SUFFICIENT_FOR_STRENGTH_REQUALIFICATION = YES

PHASE32_Z_PHASE32_Y_ACTUAL_PATH_ACCEPTED = PARTIAL

PHASE32_Z_TRADING_OUTCOME_IDENTICAL_REASON = A/B hybrid with A dominant: PM id provenance reached actual path, but strict prior PM match/non-generic REENTRY context did not; no REENTRY row became eligible, positive-weight, selected, or filled

PHASE32_Z_REENTRY_CONTRACT_OVER_SUPPRESSION_CANDIDATE = YES

PHASE32_Z_LONGER_VALIDATION_READY = NO

PHASE32_Z_NEXT_STEP = Narrow root-cause/repair of campaign provenance preservation into strategy-origin SELL_EXIT pending/order/execution and strict prior bridge campaign matching; rerun short fresh validation only after that repair.
