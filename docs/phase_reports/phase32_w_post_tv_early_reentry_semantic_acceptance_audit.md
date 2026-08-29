# Phase32-W Post-T/V Early REENTRY Semantic Acceptance Audit

## Executive Summary

READ-ONLY audit of `runtime-test-historical-extended-smoke-20260827T035349208209Z` through 2022-10-19 shows a partial Phase32-T/V actual-path effect, but not acceptance.

PM decisions and daily fills now carry PM/campaign provenance for the primary 83060 EXIT. However, persistent order and execution ledger records do not preserve that provenance: `source_decision_id`, `source_pm_decision_id`, and `position_campaign_id` remain empty on the 83060 persistent SELL order/execution. The strict-prior bridge therefore reports `pm_exit_reason_matched_close_count = 0` on every audited day, and all semantic REENTRY rows retain `previous_exit_reason_class = GENERIC`.

Trading outcome equality by 2022-10-19 is not a performance failure. The field-level reason is that REENTRY candidates never reached positive target, PC selection, PS executable quantity, or fill. The next blocker after cooldown is unresolved prior-exit context from missing persistent ledger provenance.

No production code, config, threshold, model, PM, PC/MCC, Risk Pacing, PS, Runtime state, fresh-run, resume, replay, or backtest was changed or executed.

## Run Identity

| Item | Value |
|---|---|
| Run id | `runtime-test-historical-extended-smoke-20260827T035349208209Z` |
| Run path | `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T035349208209Z` |
| Audit window | 2022-10-03 through 2022-10-19 |
| Run status at read | `RUNNING` |
| Next job at read | `2022-10-24:market_refresh` |
| Source commit in plan | `887a3361eed9f46dccfa6b5b04cb8bb7ee83aa59` |
| Historical authority | `CURRENT_ACCEPTED_RUNTIME_ON_HISTORICAL_DATA` |
| Accepted generation | `phase19_aq_accepted_generation_641e6e313543f013` |

## 83060 Actual-Path Trace

| Date | Stage | Evidence |
|---|---|---|
| 2022-10-03 | BUY fill | `execution/fills.json`: `symbol=83060`, `side=BUY`, `source_decision_id=MISSING`, `position_campaign_id=pc-228f21b28c9b7664-83060-0001` |
| 2022-10-04 | PM EXIT | `position_management/pm_decisions.json`: `pm_decision_id=pm-2022-10-04-83060-exit`, `decision_reason=trend_and_opportunity_broken`, `position_campaign_id=pc-228f21b28c9b7664-83060-0001` |
| 2022-10-04 | Daily fill | `execution/fills.json`: `source_decision_id=pm-2022-10-04-83060-exit`, `source_decision_type=EXIT`, `position_campaign_id=pc-228f21b28c9b7664-83060-0001` |
| 2022-10-04 | Realized slice | `execution/realized_slices.json`: `source_decision_id=pm-2022-10-04-83060-exit`, `position_campaign_id=pc-228f21b28c9b7664-83060-0001` |
| 2022-10-04 | Pending lineage | `.runtime/pending_order_plan/history/2022-10-04/...json`: top-level `source_pm_decision_id=""`; lineage item has `pm_decision_id=runtime-current-83060`, not the PM decision id |
| 2022-10-04 | Persistent order ledger | `.runtime/persistent_ledger/orders.jsonl`: `symbol=83060`, `side=SELL`, `source_decision_id=""`, `source_pm_decision_id=""`, `position_campaign_id=""`, `source_pm_business_date=2022-10-04` |
| 2022-10-04 | Persistent execution ledger | `.runtime/persistent_ledger/executions.jsonl`: `symbol=83060`, `side=SELL`, `source_decision_id=""`, `source_pm_decision_id=""`, `position_campaign_id=""`, `source_pm_business_date=2022-10-04` |

## 83060 REENTRY Lifecycle

| Date | Days Since Exit | Rank | Prior Exit | Class | Cooldown | Opportunity | Trend | Momentum | Quality | State | Target |
|---|---:|---:|---|---|---|---|---|---|---|---|---:|
| 2022-10-05 | 0 | 10 | `EXIT` | `GENERIC` | `FAIL_CLOSED` | `PASS` | `FAIL` | `FAIL` | `PASS` | `REENTRY_NOT_ELIGIBLE_CHURN_PROTECTION` | 0.0 |
| 2022-10-06 | 1 | 9 | `EXIT` | `GENERIC` | `FAIL_CLOSED` | `PASS` | `FAIL` | `FAIL` | `PASS` | `REENTRY_NOT_ELIGIBLE_CHURN_PROTECTION` | 0.0 |
| 2022-10-07 | 2 | 9 | `EXIT` | `GENERIC` | `FAIL_CLOSED` | `PASS` | `FAIL` | `FAIL` | `PASS` | `REENTRY_NOT_ELIGIBLE_CHURN_PROTECTION` | 0.0 |
| 2022-10-11 | 4 | 9 | `EXIT` | `GENERIC` | `PASS` | `PASS` | `FAIL` | `FAIL` | `PASS` | `REENTRY_INSUFFICIENT_EVIDENCE` | 0.0 |
| 2022-10-12 | 5 | 10 | `EXIT` | `GENERIC` | `PASS` | `PASS` | `FAIL` | `FAIL` | `PASS` | `REENTRY_INSUFFICIENT_EVIDENCE` | 0.0 |
| 2022-10-13 | 6 | 9 | `EXIT` | `GENERIC` | `PASS` | `PASS` | `FAIL` | `FAIL` | `PASS` | `REENTRY_INSUFFICIENT_EVIDENCE` | 0.0 |
| 2022-10-14 | 7 | 9 | `EXIT` | `GENERIC` | `PASS` | `PASS` | `FAIL` | `FAIL` | `PASS` | `REENTRY_INSUFFICIENT_EVIDENCE` | 0.0 |
| 2022-10-17 | 8 | 8 | `EXIT` | `GENERIC` | `PASS` | `PASS` | `FAIL` | `FAIL` | `PASS` | `REENTRY_INSUFFICIENT_EVIDENCE` | 0.0 |
| 2022-10-18 | 9 | 8 | `EXIT` | `GENERIC` | `PASS` | `PASS` | `PASS` | `FAIL` | `PASS` | `REENTRY_INSUFFICIENT_EVIDENCE` | 0.0 |
| 2022-10-19 | 10 | 7 | `EXIT` | `GENERIC` | `PASS` | `PASS` | `PASS` | `FAIL` | `PASS` | `REENTRY_INSUFFICIENT_EVIDENCE` | 0.0 |

83060 becomes stronger by rank and some short-trend evidence later in the window, but it does not satisfy the full current REENTRY recovery contract. On 2022-10-19 it has rank 7, cooldown PASS, opportunity PASS, trend PASS, continuation PASS, downside PASS, and quality PASS, but momentum recovery remains FAIL and prior-exit context remains GENERIC.

## T/V Acceptance Gate

| Gate | Result | Evidence |
|---|---|---|
| PM provenance extraction | `PASS` | 2022-10-04 PM decision has `pm_decision_id=pm-2022-10-04-83060-exit` and `position_campaign_id=pc-228f21b28c9b7664-83060-0001` |
| Daily fill provenance | `PASS` | 2022-10-04 fill has `source_decision_id=pm-2022-10-04-83060-exit`, `source_decision_type=EXIT`, `position_campaign_id=pc-...-83060-0001` |
| Persistent order ledger provenance non-empty | `FAIL` | 83060 SELL order has empty `source_decision_id`, `source_pm_decision_id`, `position_campaign_id` |
| Persistent execution ledger provenance non-empty | `FAIL` | 83060 SELL execution has empty `source_decision_id`, `source_pm_decision_id`, `position_campaign_id` |
| `pm_exit_reason_matched_close_count > 0` | `FAIL` | `strategy/input_manifest.json` shows `0` on every audited day |
| `prior_exit_reason_authority=STRICT_PRIOR_PM_DECISION_EVIDENCE` | `FAIL` | No semantic REENTRY row has strict prior PM authority |
| `previous_exit_reason_class != GENERIC` | `FAIL` | All 66 semantic REENTRY rows are `GENERIC` |

Actual-path acceptance is therefore PARTIAL: T provenance appears in daily execution artifacts, but the authoritative persistent ledger and strict-prior bridge do not consume it successfully.

## Early REENTRY Funnel

Canonical day-symbol unit: `semantic_buy_type=REENTRY` in `strategy/portfolio_construction.json`, 2022-10-03 through 2022-10-19.

| Funnel Step | Count |
|---|---:|
| semantic REENTRY total | 66 |
| unique REENTRY symbols | 13 |
| strict prior PM context available | 0 |
| non-GENERIC prior-exit rows | 0 |
| cooldown PASS | 36 |
| opportunity qualification PASS | 11 |
| trend recovery PASS | 27 |
| momentum recovery PASS | 28 |
| continuation PASS | 66 |
| downside PASS | 66 |
| buy quality PASS | 66 |
| REENTRY_ELIGIBLE | 0 |
| target_weight > 0 | 0 |
| requested_weight > 0 | 0 |
| accepted_weight > 0 | 0 |
| COMPETITOR_SELECTED | 0 |
| PS executable quantity > 0 | 0 |
| Runtime REENTRY BUY | 0 |
| actual REENTRY fill | 0 |

State distribution:

| State | Count |
|---|---:|
| `REENTRY_NOT_ELIGIBLE_CHURN_PROTECTION` | 30 |
| `REENTRY_NOT_ELIGIBLE_CURRENT_EVIDENCE` | 29 |
| `REENTRY_INSUFFICIENT_EVIDENCE` | 7 |

## Non-GENERIC Examples

No semantic REENTRY row has non-GENERIC prior-exit context.

There are non-GENERIC `previous_exit_reason_class` examples in non-REENTRY duplicate/current-position rows, such as `TREND_MOMENTUM` for active-position PM-action rows. Those do not satisfy this audit gate because their `reentry_semantic_state` is `REENTRY_NOT_APPLICABLE` and `semantic_buy_type` is not `REENTRY`.

## Blocker Decomposition

Sequential blocker decomposition for the 66 semantic REENTRY rows:

| Primary Blocker | Count | Representative Row |
|---|---:|---|
| cooldown | 30 | 2022-10-05 83060, rank 10, `REENTRY_NOT_ELIGIBLE_CHURN_PROTECTION`, `reentry_minimum_cooldown_not_satisfied` |
| insufficient prior-exit context | 36 | 2022-10-11 83060, rank 9, `REENTRY_INSUFFICIENT_EVIDENCE`, `insufficient_prior_exit_context` |

For rows that pass cooldown, the dominant final blocker is `insufficient_prior_exit_context`, caused by `previous_exit_reason_class=GENERIC` and absent strict prior PM authority.

## Clearly Strong Again Cases

Rows satisfying all of the following were searched:

- cooldown PASS
- opportunity qualification PASS
- trend recovery PASS
- momentum recovery PASS
- continuation PASS
- downside PASS
- buy quality PASS
- strong rank

Count: `0`.

Near-miss 83060 examples:

| Date | Evidence | Missing |
|---|---|---|
| 2022-10-18 | rank 8, cooldown PASS, opportunity PASS, trend PASS, quality PASS, continuation PASS, downside PASS | momentum FAIL, prior context GENERIC |
| 2022-10-19 | rank 7, cooldown PASS, opportunity PASS, trend PASS, quality PASS, continuation PASS, downside PASS | momentum FAIL, prior context GENERIC |

Because no row satisfies all current evidence gates, over-suppression cannot be proven from this window alone. The open concern is narrower: the current run cannot test non-GENERIC REENTRY behavior because strict-prior PM context never materializes.

## MA5 / Short-Trend Evidence Inventory

Existing actual features include MA5-equivalent or short-trend evidence:

- `price_momentum_return_1d`
- `price_momentum_return_3d`
- `price_momentum_return_5d`
- `price_momentum_return_10d`
- `price_momentum_return_20d`
- `momentum_1d_vs_5d_delta`
- `momentum_5d_vs_20d_delta`
- `trend_close_over_ma_20d`
- `trend_ma_5_20_ratio`
- `trend_ma_20_60_ratio`
- `volume_momentum_ratio_5d`

83060 selected evidence:

| Date | 5d Return | 20d Return | 1d vs 5d | 5d vs 20d | Close / MA20 | MA5 / MA20 |
|---|---:|---:|---:|---:|---:|---:|
| 2022-10-05 | -0.026054 | -0.073517 | 0.021864 | 0.047463 | 0.945741 | 0.938749 |
| 2022-10-11 | 0.003241 | -0.104915 | -0.007224 | 0.108156 | 0.936346 | 0.951786 |
| 2022-10-18 | 0.048916 | -0.057629 | -0.039142 | 0.106544 | 1.005374 | 0.975651 |
| 2022-10-19 | 0.065604 | -0.058252 | -0.055632 | 0.123857 | 1.018599 | 0.991266 |

The current REENTRY contract consumes short-trend/strength evidence through `reentry_trend_recovery_status`, `reentry_momentum_recovery_status`, opportunity rank, buy quality, continuation, and downside fields. However, in this audited run the strict-prior context failure prevents a clean test of whether non-GENERIC REENTRY rows would be admitted once clearly strong again.

## Reason Trading Outcome Stayed Same

The trading outcome stayed visually identical because REENTRY never reached deployment:

1. PM/campaign provenance appears in daily PM/fill artifacts.
2. Persistent order/execution ledger provenance remains empty.
3. Strict-prior bridge cannot match PM EXIT reason to closed execution: `pm_exit_reason_matched_close_count=0`.
4. Semantic REENTRY rows retain `prior_exit_reason=EXIT` and `previous_exit_reason_class=GENERIC`.
5. All REENTRY rows stop at cooldown or insufficient/current evidence before positive target weight.
6. No REENTRY row reaches PC selection, PS executable quantity, runtime BUY, or fill.

## REENTRY Contract Assessment

The current contract is stronger than short churn protection: after cooldown it still requires meaningful prior-exit context and renewed current evidence. That is reasonable in principle, because a REENTRY after `TREND_MOMENTUM` or `HARD_STOP` should prove recovery rather than merely wait out a clock.

For this run, over-suppression is unresolved rather than proven. The evidence cannot distinguish a too-strict REENTRY policy from missing actual-path provenance, because strict-prior PM context is absent for every semantic REENTRY row. The immediate defect candidate remains provenance materialization into persistent ledger / bridge identity, not MA5 threshold design.

## Next Step

Do not use this running validation as Phase32-T/V acceptance evidence. The next step should be a narrow actual-path repair or audit of why pending/submit/persistent ledger records lose PM decision identity despite daily fills carrying it. After that, use a user-operated fresh validation; Codex should not resume or mutate this run.

## Final Judgments

PHASE32_W_LEDGER_PROVENANCE_ACTUAL_PATH_OBSERVED = NO

PHASE32_W_STRICT_PRIOR_PM_MATCH_OBSERVED = NO

PHASE32_W_NON_GENERIC_REENTRY_CONTEXT_OBSERVED = NO

PHASE32_W_SEMANTIC_REENTRY_TOTAL = 66

PHASE32_W_STRICT_CONTEXT_REENTRY = 0

PHASE32_W_REENTRY_ELIGIBLE = 0

PHASE32_W_POSITIVE_TARGET_REENTRY = 0

PHASE32_W_SELECTED_REENTRY = 0

PHASE32_W_REENTRY_FILL = 0

PHASE32_W_POST_T_PRIMARY_REENTRY_BLOCKER = persistent ledger PM provenance not populated; strict-prior bridge cannot match PM EXIT reason, so cooldown-passing REENTRY rows stop at `insufficient_prior_exit_context`

PHASE32_W_CLEARLY_STRONG_AGAIN_ROWS_EXIST = NO

PHASE32_W_CLEARLY_STRONG_AGAIN_STILL_BLOCKED = NO

PHASE32_W_EXISTING_EVIDENCE_SUFFICIENT_FOR_STRENGTH_REQUALIFICATION = PARTIAL

PHASE32_W_MA5_EQUIVALENT_EVIDENCE_EXISTS = YES

PHASE32_W_REENTRY_CONTRACT_OVER_SUPPRESSION_CANDIDATE = UNRESOLVED

PHASE32_W_TRADING_OUTCOME_IDENTICAL_REASON = daily PM/fill provenance is partially present, but persistent ledger provenance and strict-prior PM bridge are not; all REENTRY candidates stop before positive target, selection, executable quantity, or fill

PHASE32_W_PHASE32_TV_ACTUAL_PATH_ACCEPTED = PARTIAL

PHASE32_W_CURRENT_RUN_CONTINUE = NO

PHASE32_W_NEXT_STEP = Narrow repair/audit of pending-to-submit-to-persistent-ledger PM provenance preservation, then user-operated new fresh validation.
