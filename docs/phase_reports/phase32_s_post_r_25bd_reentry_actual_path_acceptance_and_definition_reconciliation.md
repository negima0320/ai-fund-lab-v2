# Phase32-S - Post-R 25BD Re-entry Actual-Path Acceptance + Historical REENTRY Definition Reconciliation

## Executive Summary

Post-R 25BD fresh run `runtime-test-historical-extended-smoke-20260827T020800725952Z` completed the requested 2022-10-03 through 2022-11-08 window and closed `REVIEW_REQUIRED`.

The Phase32-R repair is **not accepted on the actual path**. The new persistent ledger provenance fields exist, but for the critical 83060 2022-10-04 close they are not populated with the authoritative PM identity. Daily execution artifacts preserve `source_decision_id = pm-2022-10-04-83060-exit` and `position_campaign_id = pc-48e93512585fb65b-83060-0001`; `.runtime/persistent_ledger/executions.jsonl` records the same SELL with `source_decision_id = ""`, `source_pm_decision_id = ""`, and `position_campaign_id = ""`.

Because the strict-prior bridge reads `.runtime/persistent_ledger/executions.jsonl`, every audited input manifest has `pm_exit_reason_matched_close_count = 0`. The resulting REENTRY rows still materialize as `prior_exit_reason = SELL_EXIT`, `previous_exit_reason_class = GENERIC`, and no `STRICT_PRIOR_PM_DECISION_EVIDENCE`.

Trading outcome equality versus Pre-R is therefore expected and not a performance failure: semantic repair did not reach the state consumed by the strict-prior bridge, so all semantic REENTRY candidates stayed at zero target/requested/accepted weight before PC competition, Cash, or lot execution could change the portfolio.

## Run Identity

| field | value |
|---|---|
| post-R run | `runtime-test-historical-extended-smoke-20260827T020800725952Z` |
| run directory | `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T020800725952Z` |
| period | 2022-10-03 through 2022-11-08 |
| completed business days | 25 |
| `run_state.json` | `COMPLETED` |
| `final_summary.json` | `REVIEW_REQUIRED` |
| `fresh_run_summary.json` | `REVIEW_REQUIRED`, `error = close returned REVIEW_REQUIRED` |

## R Actual-Path Provenance Proof

83060 / 2022-10-04 has authoritative PM and daily execution provenance, but the persistent ledger does not retain the identity fields required by the Phase32-L strict-prior join.

| stage | observed fields |
|---|---|
| PM decision | `pm_decision_id = pm-2022-10-04-83060-exit`; `decision_reason = trend_and_opportunity_broken`; `reason_codes = [trend_and_opportunity_broken]`; `position_campaign_id = pc-48e93512585fb65b-83060-0001` |
| daily execution fill | `source_decision_id = pm-2022-10-04-83060-exit`; `source_decision_type = EXIT`; `position_campaign_id = pc-48e93512585fb65b-83060-0001` |
| daily realized slice | `source_decision_id = pm-2022-10-04-83060-exit`; `source_decision_type = EXIT`; `position_campaign_id = pc-48e93512585fb65b-83060-0001` |
| persistent order ledger | 83060 SELL has `source_decision_type = SELL_EXIT`, `source_pm_business_date = 2022-10-04`, `source_position_symbol = 83060`, but `source_pm_decision_id = ""` |
| persistent execution ledger | 83060 SELL has `source_decision_type = SELL_EXIT`, `source_pm_business_date = 2022-10-04`, `source_position_symbol = 83060`, but `source_decision_id = ""`, `source_pm_decision_id = ""`, `position_campaign_id = ""` |
| strict-prior bridge | `pm_exit_reason_matched_close_count = 0` on 2022-10-05, 2022-10-11, 2022-10-27, and 2022-11-08 |

Judgment: Phase32-R schema/materialization fields are present, but actual-path ledger identity preservation is incomplete. The bridge cannot join `execution.source_decision_id == pm.pm_decision_id/decision_id` because the persistent execution row has an empty source decision id.

## 83060 Lifecycle

| date | observed state |
|---|---|
| 2022-10-03 | BUY fill exists in persistent ledger as `source_decision_type = BUY_NEW`; source id and campaign id are blank in the ledger. |
| 2022-10-04 | PM EXIT has detailed reason `trend_and_opportunity_broken`; daily fill keeps PM id/campaign; persistent ledger drops PM id/campaign. |
| 2022-10-05 to 2022-10-07 | semantic `REENTRY`; `previous_exit_reason_class = GENERIC`; `prior_exit_reason = SELL_EXIT`; cooldown `FAIL_CLOSED`; recovery `REVIEW_REQUIRED`; blocker `insufficient_prior_exit_context`; target `0.0`. |
| 2022-10-11 to 2022-10-26 | semantic `REENTRY`; cooldown `PASS`; still `GENERIC` / `SELL_EXIT`; recovery `REVIEW_REQUIRED`; blocker `insufficient_prior_exit_context`; target `0.0`. |
| 2022-10-27 | semantic `REENTRY`; cooldown `PASS`; still `GENERIC` / `SELL_EXIT`; recovery `FAIL_CLOSED`; blocker `reentry_buy_quality_not_requalified`; target `0.0`. |
| 2022-10-28 to 2022-11-08 | semantic `REENTRY`; cooldown `PASS`; still `GENERIC` / `SELL_EXIT`; recovery `FAIL_CLOSED`; blocker `reentry_opportunity_not_requalified`; target `0.0`. |

No 83060 row observed `prior_exit_reason_authority = STRICT_PRIOR_PM_DECISION_EVIDENCE`. No 83060 row changed to a non-GENERIC prior-exit class.

## Post-R REENTRY Funnel

Canonical count source: deduplicated day-symbol rows from `daily/*/strategy_eod_shadow/portfolio_construction.json`. Duplicate-inclusive REENTRY artifact rows across strategy/position-sizing shadows were much larger (`5,532`), so the canonical funnel below uses one PC row per day-symbol.

| funnel stage | count |
|---|---:|
| semantic REENTRY rows, 25BD | 236 |
| semantic REENTRY rows through 2022-10-27 | 136 |
| unique REENTRY symbols | 28 |
| strict prior PM context available | 0 |
| non-GENERIC prior-exit rows | 0 |
| cooldown PASS | 161 |
| current opportunity requalified | 48 |
| REENTRY_ELIGIBLE | 0 |
| target_weight > 0 | 0 |
| requested_weight > 0 | 0 |
| accepted_weight > 0 | 0 |
| COMPETITOR_SELECTED / target membership | 0 |
| PS executable quantity > 0 | 0 |
| Runtime REENTRY BUY | 0 |
| actual REENTRY fill | 0 |

Compared with the Pre-R early sample through 2022-10-27, semantic REENTRY remains `136` and non-GENERIC remains `0`. That is the key acceptance failure.

## Block-Reason Decomposition

Canonical 236 REENTRY rows:

| block reason | count | representative row |
|---|---:|---|
| minimum cooldown / churn protection | 76 | 83060 on 2022-10-05 through 2022-10-07: `reentry_cooldown_status = FAIL_CLOSED` |
| insufficient prior-exit context | 44 | 83060 on 2022-10-11: cooldown `PASS`, current opportunity `PASS`, `previous_exit_reason_class = GENERIC`, recovery `REVIEW_REQUIRED` |
| opportunity_not_requalified | 188 | 83060 on 2022-10-28: cooldown `PASS`, recovery `FAIL_CLOSED`, reason `reentry_opportunity_not_requalified` |
| repeated churn | 3 | rows with `reentry_repeated_unresolved_churn` |
| buy_quality_not_requalified | 1 | 83060 on 2022-10-27 |
| continuation | 0 | all canonical rows have `reentry_continuation_quality_status = PASS` |
| downside | 0 | all canonical rows have `reentry_downside_risk_status = PASS` |
| PC competition / Cash | 0 as final gate | rows never reach positive target or target membership |
| lot/executability | 0 as final gate | all `phase29_l19_lot_resolution.final_allocated_quantity = 0` because target is already zero |

The blocker counts overlap because a row can be cooldown-passed and still blocked by context/current evidence. The primary post-R blocker remains prior-exit identity/context materialization, because the intended R repair did not allow the strict-prior bridge to match any PM close.

## Clearly-Strong-Again Cases

There are partial “strong again” cases under existing PIT-safe evidence:

- `48` rows have `reentry_opportunity_qualification_status = PASS`.
- `106` rows have `reentry_trend_recovery_status = PASS`.
- `140` rows have `reentry_momentum_recovery_status = PASS`.
- All `236` rows have continuation `PASS` and downside `PASS`.
- Most rows also have buy quality `PASS` (`229 / 236`) with `quality_action = REDUCED_ALLOCATION_ONLY`.

However, these rows are still blocked before capital admission because `prior_exit_context_status = REVIEW_REQUIRED` and `previous_exit_reason_class = GENERIC`. Example: 83060 on 2022-10-11 has cooldown `PASS`, opportunity qualification `PASS`, quality `PASS`, continuation `PASS`, downside `PASS`, but `reentry_recovery_status = REVIEW_REQUIRED`, `reentry_recovery_reason = insufficient_prior_exit_context`, and `target_weight = 0.0`.

## Existing Short-Term Strength Evidence Inventory

Existing artifacts already expose several PIT-safe strength proxies:

| evidence | observed field(s) |
|---|---|
| short momentum | `momentum_trajectory_action`, `momentum_trajectory_classification`, `momentum_trajectory_feature_snapshot.price_momentum_return_1d/3d/5d/10d/20d` |
| short/medium moving average relationship | `momentum_trajectory_feature_snapshot.trend_ma_5_20_ratio`, `trend_ma_20_60_ratio`, `trend_close_over_ma_20d`, `reentry_trend_close_over_ma_20d` |
| trend recovery | `reentry_trend_recovery_status` |
| momentum recovery | `reentry_momentum_recovery_status` |
| continuation | `reentry_continuation_quality_status`, entry admission consumed evidence `continuation_quality_status` |
| downside | `reentry_downside_risk_status`, entry admission consumed evidence `downside_risk_status` |
| buy quality | `quality_status`, `quality_action`, `buy_quality_authority`, `entry_admission_action` |
| rank | `input_opportunity_rank`, `opportunity_buy_rank`, `reentry_rank`, `rank_authority` |

Existing evidence appears sufficient to express renewed strength directionally. No MA5 threshold or new feature should be added until the identity/context defect is repaired and re-audited, because current evidence is not the first failing gate for the key acceptance path.

## Historical REENTRY Definition Reconciliation

Prior reports did observe REENTRY activity, but the definitions are not the same population as Phase32-J/K current semantic REENTRY capitalization.

| reference | observed statement | definition implication |
|---|---|---|
| Phase30-C | `REENTRY: 47`; `previously traded symbol is classified as REENTRY`; `REENTRY campaigns: 9` | selected BUY / campaign lifecycle classification for symbols previously traded |
| Phase30-F | `REENTRY fills = 82` | realized fill/campaign lifecycle category |
| Phase32-J | semantic REENTRY selected `0`; PC `REENTRY_BLOCK` dominant | current PC semantic authority population where prior same-symbol exit turns a would-be new buy into `semantic_buy_type = REENTRY` and gates target weight |
| Phase32-K | Spring `978` and Plateau `3,522` semantic REENTRY rows; selected `0`; all `GENERIC` prior class | strict semantic REENTRY eligibility, not historical campaign/fill lifecycle labeling |

Conclusion: historical `REENTRY fill` was a lifecycle/campaign or selected-buy classification: a buy after prior ownership can be labeled REENTRY after the fact. Current `semantic_buy_type = REENTRY` is an earlier PC gate contract that must pass strict prior-exit context and renewed evidence before any target weight exists. These are related but not identical definitions.

This means historical REENTRY success is real under the older/broader fill classification, while Phase32-J/K/S selected `0` is also real under the stricter PC semantic definition. The likely regression boundary is the introduction or hardening of the fail-closed PC semantic REENTRY authority before Phase32-J/K, combined with missing detailed prior-exit materialization from persistent execution state. Exact commit boundary was not established in this read-only artifact audit.

## Trading Outcome Equality

Pre-R and Post-R 25BD Holdings/Equity remain identical because semantic repair did not occur at the strict-prior input consumed by PC:

1. Post-R through 2022-10-27 canonical semantic REENTRY count matches the Pre-R early sample: `136`.
2. Non-GENERIC prior context remains `0`.
3. Strict-prior PM matched close count remains `0`.
4. No REENTRY candidate receives positive target/requested/accepted weight.
5. No REENTRY row reaches PC selection, Cash competition, lot executability, Runtime REENTRY BUY, or fill.

So the same non-REENTRY BUY/ADD/SELL path is selected. The unchanged portfolio is not a new performance defect; it is the expected consequence of no semantic-context delta.

## REVIEW_REQUIRED Classification

`final_summary.json` reports `review_summary.non_blocking_review = true`, `review_reasons = [strategy_shadow_review_required_non_blocking]`, and strategy review dates `2022-10-07`, `2022-10-27`, `2022-11-08`.

This is separated from the Phase32-S semantic acceptance finding. The run’s `REVIEW_REQUIRED` close status is not evidence that the REENTRY semantic audit failed; the audit fails because persistent ledger provenance did not preserve the strict PM identity and the bridge matched zero closes.

## REENTRY Contract Assessment

The contract may still be over-suppressive, but this run cannot fairly test the post-context contract because context is not repaired on the authoritative actual path. The presence of 48 current-opportunity-pass rows, 106 trend-recovery-pass rows, and 140 momentum-recovery-pass rows suggests there are candidates worth rechecking after the ledger identity defect is fixed.

Current status: `REENTRY_CONTRACT_OVER_SUPPRESSION_CANDIDATE = UNRESOLVED`. It should not be escalated to YES until at least one fresh actual-path run shows non-GENERIC strict prior PM context and still blocks clearly renewed candidates solely because of the re-entry contract.

## Defect / No-Defect Judgment

Defect confirmed: Phase32-R did not preserve the necessary PM/campaign provenance into `.runtime/persistent_ledger/executions.jsonl` on the actual historical fresh-run path.

The daily fill and realized-slice artifacts prove the upstream PM identity exists for 83060, so the remaining defect is between daily execution artifact provenance and persistent ledger order/execution persistence/projection consumed by the strict-prior bridge.

## Recommendation

Do not continue to longer 650BD validation for REENTRY acceptance yet. A longer run would likely reproduce the same zero-match bridge condition at greater cost. Next step should be a narrow read/write repair of persistent ledger identity preservation for actual order/execution rows, then a short fresh validation that explicitly requires `pm_exit_reason_matched_close_count > 0`, `STRICT_PRIOR_PM_DECISION_EVIDENCE`, and at least one non-GENERIC semantic REENTRY prior context before any performance comparison.

## Final Judgments

PHASE32_S_LEDGER_PROVENANCE_ACTUAL_PATH_OBSERVED = NO

PHASE32_S_STRICT_PRIOR_PM_MATCH_OBSERVED = NO

PHASE32_S_NON_GENERIC_REENTRY_CONTEXT_OBSERVED = NO

PHASE32_S_SEMANTIC_REENTRY_TOTAL = 236 canonical 25BD day-symbol rows; 136 through 2022-10-27

PHASE32_S_REENTRY_ELIGIBLE = 0

PHASE32_S_POSITIVE_TARGET_REENTRY = 0

PHASE32_S_SELECTED_REENTRY = 0

PHASE32_S_REENTRY_FILL = 0

PHASE32_S_POST_R_PRIMARY_REENTRY_BLOCKER = persistent ledger execution/order provenance identity not populated (`source_decision_id`, `source_pm_decision_id`, `position_campaign_id` blank), causing strict-prior PM bridge `pm_exit_reason_matched_close_count = 0` and all prior-exit context to remain GENERIC/REVIEW_REQUIRED

PHASE32_S_INSUFFICIENT_PRIOR_CONTEXT_REMAINS_MATERIAL = YES

PHASE32_S_CLEARLY_STRONG_AGAIN_ROWS_EXIST = PARTIAL

PHASE32_S_CLEARLY_STRONG_AGAIN_STILL_BLOCKED = YES

PHASE32_S_EXISTING_EVIDENCE_SUFFICIENT_FOR_STRENGTH_REQUALIFICATION = PARTIAL

PHASE32_S_HISTORICAL_REENTRY_DEFINITION_MATCHES_CURRENT_SEMANTIC_REENTRY = NO

PHASE32_S_HISTORICAL_REENTRY_SUCCESS_CONFIRMED = YES

PHASE32_S_REENTRY_REGRESSION_SUSPECTED = PARTIAL

PHASE32_S_REENTRY_REGRESSION_BOUNDARY = unresolved exact commit; likely when fail-closed PC semantic REENTRY authority became authoritative before Phase32-J/K, amplified by missing persistent execution PM provenance

PHASE32_S_25BD_TRADING_OUTCOME_IDENTICAL_REASON = semantic context did not change: strict-prior PM matched close count stayed 0, non-GENERIC prior context stayed 0, all semantic REENTRY target/requested/accepted weights stayed 0 before PC/Cash/lot/fill

PHASE32_S_REENTRY_CONTRACT_OVER_SUPPRESSION_CANDIDATE = UNRESOLVED

PHASE32_S_PHASE32_R_ACTUAL_PATH_ACCEPTED = NO

PHASE32_S_LONGER_FRESH_VALIDATION_READY = NO

PHASE32_S_NEXT_STEP = narrow persistent-ledger actual-path provenance repair from daily execution/order provenance into `.runtime/persistent_ledger/orders.jsonl` and `executions.jsonl`, then rerun a short acceptance requiring nonzero strict PM close matches and non-GENERIC prior-exit materialization before 650BD continuation
