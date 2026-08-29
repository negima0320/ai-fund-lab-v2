# Phase32-AE - Post-AD Actual-Path Campaign Convergence / Final REENTRY Blocker Audit

## Executive Summary

READ-ONLY audit was performed against the latest post-AD fresh Historical artifact run:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T071407047414Z`

This is the latest post-AD run, not the older `runtime-test-historical-extended-smoke-20260827T055917572299Z`. At audit time `run_state.json` reported `status=RUNNING`, completed business days through `2022-11-07`, and daily artifacts existed through `2022-11-08`. The acceptance window requested here is available through `2022-10-26`.

Primary result:

- Phase32-AD succeeded on the strict-prior PM EXIT reason path for 83060: the 2022-10-04 EXIT PM decision is materialized into 2022-10-25/26 REENTRY context as `trend_and_opportunity_broken`, with `previous_exit_reason_class=TREND_MOMENTUM`.
- Full campaign convergence is still PARTIAL, not closed. The EXIT-side PM/fill/realized-slice lineage uses one canonical campaign id, but the 2022-10-03 BUY-side runtime planning and runtime-test fill observability do not fully preserve source PM/order provenance, and `positions/position_campaigns.json` does not show a retained 83060 campaign row in the audited artifacts.
- 83060 2022-10-25 and 2022-10-26 remained target zero because Portfolio Construction assigned `reentry_semantic_state=REENTRY_NOT_ELIGIBLE_SAFETY`, producing `REENTRY_BLOCK` before sizing. This is the first authoritative zero-target predicate observed. It is not Cash, PC competition, or lot/executability.

No production code, config, schema, thresholds, model files, runtime state, resume, replay, backtest, or fresh-run execution was performed.

## Actual Run Identity

| Field | Value |
| --- | --- |
| Run id | `runtime-test-historical-extended-smoke-20260827T071407047414Z` |
| Path | `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T071407047414Z` |
| Status at audit | `RUNNING` |
| Completed days in `run_state.json` | `2022-10-03` through `2022-11-07`, with exchange holidays/weekends absent |
| Daily artifacts present | Through `2022-11-08` |
| Required AE window | Available through `2022-10-26` |

## 83060 BUY -> EXIT Campaign Lineage

Canonical campaign id observed for the lifecycle:

`pc-c8110934d3adf7af-83060-0001`

### BUY Side

| Stage | Artifact | Observed id / status | Judgment |
| --- | --- | --- | --- |
| Strategy / PC | `daily/2022-10-03/strategy/portfolio_construction.json` | 83060 selected as `BUY_NEW`; PC had no prior PM campaign, as expected for a new entry. | PASS for BUY admission, not a PM campaign source |
| Runtime planning | `daily/2022-10-03/strategy/runtime_planning.json` | 83060 `planning_intent=BUY_NEW`, `order_side_intent=BUY`, `quantity_delta_candidate=100`; source PM fields are blank. | PARTIAL |
| Pending generation evidence | `daily/2022-10-03/morning/pending_generation_evidence.json` | Rank lineage references 83060 `BUY_NEW`; serialized pending object is not embedded in the evidence artifact. | PARTIAL |
| Submitted order authority | `daily/2022-10-03/execution/submitted_order_authority.json` | `status=PASS`, `submitted_order_count=7`, execution reference includes `execution-equivalent:sha256:b1bed5695d2d6d1ce542018f627525237a72e646373da15ed9285849c69ad2e1`. | PARTIAL |
| Runtime-test fill observability | `daily/2022-10-03/execution/fills.json` | 83060 BUY fill has `position_campaign_id=pc-c8110934d3adf7af-83060-0001`, `source_decision_id=MISSING`, `source_decision_type=BUY`. | Campaign PASS, source lineage PARTIAL |
| Realized slices | `daily/2022-10-03/execution/realized_slices.json` | No realized slice, as BUY does not realize a close. | N/A |
| `positions/position_campaigns.json` | `daily/2022-10-03/positions/position_campaigns.json` | No retained 83060 campaign row found in the position campaign list. | PARTIAL / gap |

### EXIT Side

| Stage | Artifact | Observed id / status | Judgment |
| --- | --- | --- | --- |
| Strategy PM | `daily/2022-10-04/strategy/position_management.json` | 83060 carries `position_campaign_id=pc-c8110934d3adf7af-83060-0001`; reason includes `trend_and_opportunity_broken`. | YES |
| PM daily artifact | `daily/2022-10-04/position_management/pm_decisions.json` | `pm_decision_id=pm-2022-10-04-83060-exit`, `decision_type=EXIT`, `decision_status=SELL_FULL_POSITION`, `decision_reason=trend_and_opportunity_broken`, same campaign id. | YES |
| Runtime planning | `daily/2022-10-04/strategy/runtime_planning.json` | 83060 plan has `planning_intent=SELL_EXIT`, `order_side_intent=SELL`, `source_pm_decision_id=pm-2022-10-04-83060-exit`, `quantity_delta_candidate=-100`. | YES |
| Pending generation evidence | `daily/2022-10-04/morning/pending_generation_evidence.json` | Rank lineage references 83060 `SELL_EXIT`; serialized pending object is not embedded in this evidence artifact. | PARTIAL |
| Submitted order authority | `daily/2022-10-04/execution/submitted_order_authority.json` | `status=PASS`, `submitted_order_count=6`, execution reference includes `execution-equivalent:sha256:b3375cf6a3b074e5cbe22741a0380b47a5cafd8edddf0f74ae0cfd43cb91d70f`. | PARTIAL |
| Fill | `daily/2022-10-04/execution/fills.json` | 83060 SELL fill has `position_campaign_id=pc-c8110934d3adf7af-83060-0001`, `source_decision_id=pm-2022-10-04-83060-exit`, `source_decision_type=EXIT`. | YES |
| Realized slice | `daily/2022-10-04/execution/realized_slices.json` | 83060 close slice has same campaign id and `source_decision_id=pm-2022-10-04-83060-exit`. | YES |

## Campaign Convergence Table

| Link | Expected | Observed | Judgment |
| --- | --- | --- | --- |
| BUY campaign = EXIT campaign | Same lifecycle id | BUY fill and EXIT PM/fill/realized all use `pc-c8110934d3adf7af-83060-0001`. | YES |
| Current campaign = PM campaign | Current preserves campaign into PM | 2022-10-04 PM inherited `pc-c8110934d3adf7af-83060-0001`; however retained `positions/position_campaigns.json` row for 83060 was not found. | PARTIAL |
| PM campaign = pending/order | PM id preserved into planning; full pending/order object not embedded in run evidence. | Runtime planning preserves PM decision id; submitted order authority stores execution reference only. | PARTIAL |
| Order/execution/fill campaign | No campaign rewrite, no alternate namespace | Runtime-test fills show same campaign on BUY and EXIT, with no `ledger-derived-*` id for 83060. | YES for fills, PARTIAL for copied ledger visibility |
| EXIT campaign = realized slice | Same PM and campaign | Realized slice uses `pc-c8110934d3adf7af-83060-0001` and `pm-2022-10-04-83060-exit`. | YES |

Conclusion: campaign convergence is improved but not fully closeable from these actual artifacts. The strict bridge is working, but the full provenance closure gate remains PARTIAL because pending/order/persistent ledger objects are not fully materialized in the run artifact set and `positions/position_campaigns.json` does not retain an 83060 campaign row.

## Canonical Authority Proof

`positions/position_campaigns.json` exists on the audited days, but it does not provide a complete retained 83060 lifecycle row in the inspected artifacts. The canonical campaign id nevertheless appears consistently in downstream lifecycle observability:

- 2022-10-03 BUY fill: `pc-c8110934d3adf7af-83060-0001`
- 2022-10-04 PM decision: `pc-c8110934d3adf7af-83060-0001`
- 2022-10-04 SELL fill: `pc-c8110934d3adf7af-83060-0001`
- 2022-10-04 realized slice: `pc-c8110934d3adf7af-83060-0001`

No alternate `ledger-derived-*` campaign id was observed for the 83060 lifecycle in the audited actual-path artifacts.

## Strict Bridge Proof

The strict prior bridge is accepted for the 83060 semantic path.

| Date | Field | Value |
| --- | --- | --- |
| 2022-10-04 | PM decision id | `pm-2022-10-04-83060-exit` |
| 2022-10-04 | PM reason | `trend_and_opportunity_broken` |
| 2022-10-04 | PM campaign | `pc-c8110934d3adf7af-83060-0001` |
| 2022-10-04 | SELL fill source decision | `pm-2022-10-04-83060-exit` |
| 2022-10-04 | SELL fill campaign | `pc-c8110934d3adf7af-83060-0001` |
| 2022-10-25 | Bridge authority | `persistent_ledger_execution_history_with_strict_prior_pm_exit_reason_bridge` |
| 2022-10-25 | `pm_exit_reason_matched_close_count` | `17` |
| 2022-10-25 | 83060 prior reason | `trend_and_opportunity_broken` |
| 2022-10-25 | 83060 previous class | `TREND_MOMENTUM` |
| 2022-10-26 | Bridge authority | `persistent_ledger_execution_history_with_strict_prior_pm_exit_reason_bridge` |
| 2022-10-26 | `pm_exit_reason_matched_close_count` | `18` |
| 2022-10-26 | 83060 prior reason | `trend_and_opportunity_broken` |
| 2022-10-26 | 83060 previous class | `TREND_MOMENTUM` |

Note: the PC member row carries the materialized prior reason and class, while the authority string is carried in `strategy/input_manifest.json` under `strategy_input_sources.prior_exit_state`.

## 83060 2022-10-25 / 2022-10-26 Analysis

| Field | 2022-10-25 | 2022-10-26 |
| --- | --- | --- |
| `semantic_buy_type` | `REENTRY` | `REENTRY` |
| `prior_exit_business_date` | `2022-10-04` | `2022-10-04` |
| `prior_exit_reason` | `trend_and_opportunity_broken` | `trend_and_opportunity_broken` |
| `prior_exit_reason_codes` | `["trend_and_opportunity_broken"]` | `["trend_and_opportunity_broken"]` |
| `previous_exit_reason_class` | `TREND_MOMENTUM` | `TREND_MOMENTUM` |
| `business_days_since_exit` | `14` | `15` |
| Cooldown / recovery | PASS inferred by `reentry_recovery_status=PASS` | PASS inferred by `reentry_recovery_status=PASS` |
| `reentry_recovery_reason` | `reentry_recovery_qualified` | `reentry_recovery_qualified` |
| `reentry_semantic_state` | `REENTRY_NOT_ELIGIBLE_SAFETY` | `REENTRY_NOT_ELIGIBLE_SAFETY` |
| Buy quality | `PASS`, `REDUCED_ALLOCATION_ONLY` | `PASS`, `REDUCED_ALLOCATION_ONLY` |
| Rank | `10` | `9` |
| PC competitor | `requested_weight=0.0`, `accepted_weight=0.0`, `reason_codes=["REENTRY_BLOCK"]` | `requested_weight=0.0`, `accepted_weight=0.0`, `reason_codes=["REENTRY_BLOCK"]` |
| Target weight | `0.0` | `0.0` |
| PS executable quantity | `0` | `0` |
| Runtime BUY | none, no positive quantity delta | none, no positive quantity delta |
| Fill | none | none |

## Final Zero-Target Blocker

The first authoritative zero-target predicate for 83060 on both 2022-10-25 and 2022-10-26 is:

`Portfolio Construction semantic re-entry safety predicate: reentry_semantic_state=REENTRY_NOT_ELIGIBLE_SAFETY`

This predicate produced `REENTRY_BLOCK` and `target_weight=0.0` before Position Sizing. Position Sizing then correctly consumed the zero target and produced no executable REENTRY quantity. Cash, PC competition, and lot/executability are downstream effects here, not the first cause.

## Clearly Strong Again Judgment

| Date | Judgment | Evidence |
| --- | --- | --- |
| 2022-10-25 | CLEARLY_STRONG | Rank 10, `reentry_recovery_status=PASS`, positive 5d/20d momentum, supportive trend ratios, continuation with caution, downside pass, buy quality pass. The remaining cautions are participation quality/risk, not failure of the requested strength evidence. |
| 2022-10-26 | PARTIAL | Rank 9, `reentry_recovery_status=PASS`, positive 5d/20d momentum and supportive trend ratios, but short-term reversal/exhaustion risk is elevated and momentum is mixed/unresolved. |

Existing PIT-safe evidence appears sufficient to identify at least the 2022-10-25 row as clearly strong again under the user policy. Because provenance closure is still PARTIAL, formal `REENTRY_CONTRACT_OVER_SUPPRESSION` should remain UNRESOLVED rather than closed as a strategy-contract defect in AE.

## Broader REENTRY Funnel Through 2022-10-26

Scope: canonical day-symbol rows in `strategy/portfolio_construction.json` from 2022-10-03 through 2022-10-26.

Strict context count is inferred from the daily strict bridge manifest: symbol present in `prior_exit_state.supplied_symbols` with positive `pm_exit_reason_matched_close_count`.

| Funnel step | Count |
| --- | ---: |
| Semantic REENTRY total | 122 |
| Unique REENTRY symbols | 21 |
| Strict context | 122 |
| Non-GENERIC prior context | 87 |
| `REENTRY_ELIGIBLE` | 0 |
| Positive target | 0 |
| Selected | 0 |
| PS executable | 0 |
| Runtime REENTRY fill | 0 |

Primary blocker distribution:

| `reentry_semantic_state` | Count |
| --- | ---: |
| `REENTRY_NOT_ELIGIBLE_CURRENT_EVIDENCE` | 63 |
| `REENTRY_NOT_ELIGIBLE_CHURN_PROTECTION` | 52 |
| `REENTRY_INSUFFICIENT_EVIDENCE` | 5 |
| `REENTRY_NOT_ELIGIBLE_SAFETY` | 2 |

The two `REENTRY_NOT_ELIGIBLE_SAFETY` rows are the 83060 positive-control rows on 2022-10-25 and 2022-10-26.

## Trading Outcome Equality Reason

Classification: `B` with provenance closure caveat.

Strict PM prior context is now observed and non-GENERIC REENTRY context is materialized. However, no REENTRY row through 2022-10-26 became `REENTRY_ELIGIBLE`, no REENTRY row received positive target weight, no REENTRY was selected, and no REENTRY quantity became executable or filled. Therefore matching Equity/Cash/Exposure/Holdings is explained by later REENTRY semantic gates keeping target at zero, not by Cash or lot winning over an already positive REENTRY target.

## Provenance Closure Judgment

The provenance defect is PARTIAL:

- PM inheritance: YES
- Fill observability same campaign: YES
- Realized-slice campaign: YES
- Strict PM match > 0: YES
- Non-GENERIC prior context: YES
- One complete campaign per lifecycle across all requested authorities: PARTIAL
- Current / `positions/position_campaigns.json` retained authority proof: PARTIAL
- Pending/order/persistent execution preservation as fully materialized run artifacts: PARTIAL

This means the strict prior reason repair is accepted on actual path, but the broader campaign convergence gate should not be declared fully closed from AE artifacts.

## REENTRY Contract Judgment

`REENTRY_CONTRACT_OVER_SUPPRESSION` remains UNRESOLVED in the formal AE sense because provenance closure is not fully closed. Substantively, the next strategy-contract candidate is narrow and visible: 83060 on 2022-10-25 is clearly strong again under existing PIT-safe evidence yet is blocked by `REENTRY_NOT_ELIGIBLE_SAFETY` after prior context has become `TREND_MOMENTUM`.

## Remaining Resume / Mode Parity Risk

AD's `RESUME_RECOVERY_CAMPAIGN_SAFE=PARTIAL` and `MODE_PARITY=PARTIAL` remain separate residual risks. AE did not modify or test resume, recovery, or mode parity.

## Final Judgments

PHASE32_AE_CANONICAL_CAMPAIGN_SINGLE_LIFECYCLE = PARTIAL

PHASE32_AE_CURRENT_CAMPAIGN_MATCH = PARTIAL

PHASE32_AE_PM_CAMPAIGN_MATCH = YES

PHASE32_AE_PENDING_CAMPAIGN_MATCH = PARTIAL

PHASE32_AE_ORDER_CAMPAIGN_MATCH = PARTIAL

PHASE32_AE_EXECUTION_CAMPAIGN_MATCH = PARTIAL

PHASE32_AE_FILL_CAMPAIGN_MATCH = YES

PHASE32_AE_REALIZED_SLICE_CAMPAIGN_MATCH = YES

PHASE32_AE_STRICT_PM_MATCH_OBSERVED = YES

PHASE32_AE_NON_GENERIC_PRIOR_CONTEXT_OBSERVED = YES

PHASE32_AE_83060_10_25_CLEARLY_STRONG_AGAIN = YES

PHASE32_AE_83060_10_26_CLEARLY_STRONG_AGAIN = PARTIAL

PHASE32_AE_83060_10_25_REENTRY_ELIGIBLE = NO

PHASE32_AE_83060_10_26_REENTRY_ELIGIBLE = NO

PHASE32_AE_83060_10_25_POSITIVE_TARGET = NO

PHASE32_AE_83060_10_26_POSITIVE_TARGET = NO

PHASE32_AE_FINAL_ZERO_TARGET_BLOCKER = Portfolio Construction semantic re-entry safety predicate: `reentry_semantic_state=REENTRY_NOT_ELIGIBLE_SAFETY`, producing `REENTRY_BLOCK` and `target_weight=0.0` before Position Sizing.

PHASE32_AE_SEMANTIC_REENTRY_TOTAL = 122

PHASE32_AE_STRICT_CONTEXT_REENTRY = 122

PHASE32_AE_REENTRY_ELIGIBLE_TOTAL = 0

PHASE32_AE_POSITIVE_TARGET_TOTAL = 0

PHASE32_AE_SELECTED_REENTRY_TOTAL = 0

PHASE32_AE_REENTRY_FILL_TOTAL = 0

PHASE32_AE_TRADING_OUTCOME_IDENTICAL_REASON = B: AD strict prior context is accepted, but no REENTRY cleared later semantic eligibility gates; all REENTRY targets remained zero before sizing and execution.

PHASE32_AE_PROVENANCE_DEFECT_CLOSED = PARTIAL

PHASE32_AE_REENTRY_CONTRACT_OVER_SUPPRESSION = UNRESOLVED

PHASE32_AE_LONGER_VALIDATION_READY = NO

PHASE32_AE_NEXT_STEP = Do a narrow follow-up audit or repair of remaining campaign materialization gaps for Current / `positions/position_campaigns.json` / pending-order copied lineage, then separately audit the `REENTRY_NOT_ELIGIBLE_SAFETY` predicate against the 83060 2022-10-25 positive-control row.
