# Phase32-AB Post-AA Actual-Path Acceptance and Final Zero-Target Cause Audit

## Executive Summary

Phase32-AB audited the Post-AA fresh run:

```text
runtime-test-historical-extended-smoke-20260827T055917572299Z
```

through `2022-10-27` in READ-ONLY mode. No production code, config, threshold, model, runtime state, fresh run, resume, replay, or backtest was executed.

Result: Phase32-AA is **not accepted on this actual path**. The authoritative 2022-10-04 PM daily artifact and daily fill carry a non-empty campaign for `83060`, but serialized Pending, persistent order, persistent execution, and the runtime PM projection still carry blank `position_campaign_id`. Strict-prior PM reason matching remains zero through the 2022-10-25 and 2022-10-26 positive-control dates.

The 83060 zero-target cause is therefore not a later Cash/PC/lot outcome under repaired provenance. The first authoritative blocker remains:

```text
Portfolio Construction semantic re-entry eligibility
-> reentry_recovery_status = REVIEW_REQUIRED
-> reentry_recovery_reason = insufficient_prior_exit_context
-> previous_exit_reason_class = GENERIC
-> target_weight = 0
```

## AA Actual-Path Acceptance

AA acceptance required non-empty campaign in Pending/order/execution plus strict PM match and non-GENERIC prior context. The run fails those gates.

| Boundary | 83060 / 2022-10-04 actual value |
|---|---|
| PM daily `pm_decision_id` | `pm-2022-10-04-83060-exit` |
| PM daily reason | `trend_and_opportunity_broken` |
| PM daily campaign | `pc-e6d857c27b1d386e-83060-0001` |
| Runtime PM projection campaign | blank |
| Serialized Pending campaign | blank |
| Persistent order campaign | blank |
| Persistent execution campaign | blank |
| Daily fill campaign | `pc-e6d857c27b1d386e-83060-0001` |
| 2022-10-25 `pm_exit_reason_evidence_count` | `40` |
| 2022-10-25 `pm_exit_reason_matched_close_count` | `0` |
| 2022-10-26 `pm_exit_reason_evidence_count` | `45` |
| 2022-10-26 `pm_exit_reason_matched_close_count` | `0` |
| Prior exit authority | `EXECUTION_ROW_FALLBACK` / blank in PC rows |
| Prior exit reason | `EXIT` |
| Previous exit class | `GENERIC` |

## 83060 EXIT Provenance Trace

PM daily artifact:

```text
business_date = 2022-10-04
symbol = 83060
pm_decision_id = pm-2022-10-04-83060-exit
decision_type = EXIT
decision_status = SELL_FULL_POSITION
decision_reason = trend_and_opportunity_broken
reason_codes = [trend_and_opportunity_broken]
position_campaign_id = pc-e6d857c27b1d386e-83060-0001
```

Serialized Pending:

```text
pending_item_id = strategy-0291c977ffa6dc9d9314
side = SELL
quantity = 100
source_decision_id = pm-2022-10-04-83060-exit
source_pm_decision_id = pm-2022-10-04-83060-exit
source_decision_type = EXIT
source_pm_business_date = 2022-10-04
source_position_symbol = 83060
position_campaign_id = blank
strategy_authority_lineage.position_campaign_id = absent/blank
quantity_contract.position_campaign_id = absent/blank
```

Persistent order:

```text
business_date = 2022-10-04
symbol = 83060
side = SELL
quantity = 100
source_decision_id = pm-2022-10-04-83060-exit
source_pm_decision_id = pm-2022-10-04-83060-exit
source_decision_type = EXIT
source_pm_business_date = 2022-10-04
source_position_symbol = 83060
position_campaign_id = blank
```

Persistent execution:

```text
business_date = 2022-10-04
symbol = 83060
side = SELL
filled_quantity = 100
source_decision_id = pm-2022-10-04-83060-exit
source_pm_decision_id = pm-2022-10-04-83060-exit
source_decision_type = EXIT
source_pm_business_date = 2022-10-04
source_position_symbol = 83060
position_campaign_id = blank
```

## Strict Bridge Predicate

Implementation source:

```text
src/ai_fund_lab_v2/strategy/shadow_runtime.py
```

Effective predicate, reconstructed from `_supply_prior_exit_state()`, `_resolve_prior_closed_campaigns_from_executions()`, `_strict_prior_pm_exit_reason_evidence_by_decision()`, and `_matched_pm_exit_reason_for_close()`:

```text
1. Read persistent_ledger/executions.jsonl.
2. Keep executions with execution.business_date < decision business_date.
3. Require symbol present.
4. Require filled_quantity or quantity > 0.
5. BUY opens/rebuilds a same-symbol campaign state.
6. SELL with open prior quantity reduces the state.
7. SELL fully closes the state when post-sell quantity <= epsilon.
8. For the close, derive campaign_id from execution.position_campaign_id,
   else current reconstructed state campaign_id, else ledger-derived fallback.
9. Read strict-prior PM evidence from run daily PM artifacts and runtime PM artifacts
   where PM artifact business_date < decision business_date.
10. PM row must be EXIT or REDUCE.
11. PM row must have pm_decision_id / decision_id / source_pm_decision_id.
12. PM row must have symbol.
13. PM row must have reason or reason codes.
14. execution.source_decision_id or source_pm_decision_id must be present.
15. PM evidence lookup by that decision id must exist.
16. PM evidence business_date must equal execution close business_date.
17. PM evidence symbol must equal execution close symbol.
18. If PM evidence campaign and execution campaign are both non-empty, they must match.
19. If PM evidence campaign and reconstructed close campaign_id are both non-empty, they must match.
20. Only then materialize STRICT_PRIOR_PM_DECISION_EVIDENCE reason.
```

## Exact Failed Predicate

For 83060 on the 2022-10-25 decision date:

| Predicate | Expected | Execution actual | PM actual | Result |
|---|---|---|---|---|
| Strict-prior execution date | `< 2022-10-25` | `2022-10-04` | `2022-10-04` | PASS |
| Execution side / close | full SELL after prior BUY | SELL 100 after BUY 100 | `EXIT` / `SELL_FULL_POSITION` | PASS |
| Source decision id | non-empty | `pm-2022-10-04-83060-exit` | `pm-2022-10-04-83060-exit` | PASS |
| Symbol | `83060` | `83060` | `83060` | PASS |
| PM reason evidence | present | id lookup present | `trend_and_opportunity_broken` | PASS |
| PM date equals execution close date | `2022-10-04` | `2022-10-04` | `2022-10-04` | PASS |
| Execution campaign | non-empty PM campaign | blank | `pc-e6d857c27b1d386e-83060-0001` | SOFT PASS for predicate 18 because execution campaign is blank |
| Reconstructed close campaign id | PM campaign | `ledger-derived-83060-0001` | `pc-e6d857c27b1d386e-83060-0001` | **FAIL** |

First failed strict bridge predicate:

```text
PM evidence campaign must equal reconstructed close campaign_id.
pc-e6d857c27b1d386e-83060-0001 != ledger-derived-83060-0001
```

The reconstructed close campaign became ledger-derived because the persistent BUY and SELL executions did not carry the actual `position_campaign_id`.

## 10/25 and 10/26 Positive-Control Analysis

| Field | 2022-10-25 / 83060 | 2022-10-26 / 83060 |
|---|---:|---:|
| `semantic_buy_type` | `REENTRY` | `REENTRY` |
| prior exit date | `2022-10-04` | `2022-10-04` |
| prior exit reason | `EXIT` | `EXIT` |
| previous exit class | `GENERIC` | `GENERIC` |
| cooldown / churn | PASS, 14 BD since exit | PASS, 15 BD since exit |
| opportunity qualification | PASS | PASS |
| rank | `10` | `9` |
| trend recovery | PASS | PASS |
| momentum recovery | PASS | PASS |
| continuation | PASS | PASS |
| downside | PASS | PASS |
| buy quality artifact action | `FULL_ALLOCATION_ELIGIBLE` | `FULL_ALLOCATION_ELIGIBLE` |
| PC row quality action | `REDUCED_ALLOCATION_ONLY` | `REDUCED_ALLOCATION_ONLY` |
| `reentry_recovery_status` | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` |
| `reentry_recovery_reason` | `insufficient_prior_exit_context` | `insufficient_prior_exit_context` |
| `reentry_semantic_state` | `REENTRY_INSUFFICIENT_EVIDENCE` | `REENTRY_INSUFFICIENT_EVIDENCE` |
| PC target weight | `0.0` | `0.0` |
| PS requested weight | `0.0` | `0.0` |
| PS executable quantity | `0` | `0` |
| PC/Cash downstream status | defeated / deferred after zero request | defeated / deferred after zero request |

Authoritative first zero-target blocker:

```text
Portfolio Construction semantic re-entry gate:
reentry_eligibility.eligibility_status != PASS
reentry_recovery_status = REVIEW_REQUIRED
reentry_recovery_reason = insufficient_prior_exit_context
previous_exit_reason_class = GENERIC
```

This precedes Cash competition and lot executability. Cash/lot artifacts later show `accepted_weight=0`, `requested_weight=0`, and `executable_quantity=0`, but those are downstream consequences of PC setting the REENTRY target to zero.

## Clearly-Strong-Again Assessment

Existing PIT-safe evidence supports that both 10/25 and 10/26 are stronger than the immediate post-exit period:

| Evidence | 2022-10-25 | 2022-10-26 |
|---|---:|---:|
| rank | `10` | `9` |
| `trend_close_over_ma_20d` | `1.055926` | `1.053570` |
| `price_momentum_return_20d` | `0.033324` | `0.024256` |
| `price_momentum_return_5d` | `0.041355` | `0.030057` |
| `trend_ma_5_20_ratio` | `1.038647` | `1.043500` |
| continuation | PASS | PASS |
| downside | PASS | PASS |
| buy quality | FULL in BQ artifact | FULL in BQ artifact |

However, both rows also contain cautionary evidence:

- PC quality action is `REDUCED_ALLOCATION_ONLY`.
- Selection tier is `CAUTION_CONTINUATION`.
- Runtime opportunity score is negative.
- 10/26 entry evidence includes `short_term_reversal = true`, elevated reversal/exhaustion/participation risk.

Therefore the artifact-based “clearly strong again” judgment is **PARTIAL** for both dates: hard re-entry recovery evidence is mostly supportive, but the row is not cleanly strong across all existing evidence dimensions.

## Broader Sample

Through 2022-10-27:

| Metric | Count |
|---|---:|
| Semantic REENTRY rows | `136` |
| strict PM context rows | `0` |
| non-GENERIC prior context rows | `0` |
| REENTRY recovery PASS rows | `0` |
| positive target REENTRY rows | `0` |

Recovery reason distribution:

| Reason | Count |
|---|---:|
| `reentry_opportunity_not_requalified` | `109` |
| `insufficient_prior_exit_context` | `26` |
| `reentry_buy_quality_not_requalified` | `1` |

There is no broader strict non-GENERIC positive sample. The same provenance failure is material beyond 83060 because no REENTRY row has strict PM context.

## Trading Outcome Equality

Classification: **A**.

The 10/27 Equity/Holdings equality is explained by AA actual path still not being accepted. The run did not reach the state where repaired non-GENERIC prior context could alter REENTRY eligibility. All REENTRY targets remain zero, so later portfolio outcome equality is expected and not a separate performance signal.

## Provenance Closure and Remaining Defect

The provenance defect is not closed in this actual path.

Observed closure status:

- PM daily campaign exists: YES.
- Daily fill campaign exists: YES.
- Serialized Pending campaign exists: NO.
- Persistent order campaign exists: NO.
- Persistent execution campaign exists: NO.
- Strict PM reason match exists: NO.
- Non-GENERIC REENTRY context exists: NO.

This is still a mandatory actual-path provenance defect. The first materialized artifact failure is serialized Pending campaign blank. The strict bridge first failed predicate is campaign mismatch between PM evidence and reconstructed ledger-derived close campaign.

## REENTRY Contract Assessment

REENTRY contract over-suppression is **UNRESOLVED** in AB. Because AA provenance did not reach the actual path, AB cannot fairly decide whether a non-GENERIC, strict-PM, “clearly strong again” row would still be over-suppressed by a later re-entry contract gate.

The current target-zero reason remains valid under the existing contract because prior context is still generic.

## Next Step

Do not tune REENTRY, Cash, PC/MCC, Risk Pacing, sizing, thresholds, or MA evidence. The next step should be a narrow provenance repair/audit at the actual first failed materialization boundary:

```text
authoritative PM/daily fill campaign exists
-> serialized Pending campaign remains blank
-> persistent order/execution campaign remains blank
-> strict bridge reconstructs ledger-derived campaign and rejects PM campaign
```

Before implementation, reconcile why the 2022-10-04 actual path contains multiple campaign identities for 83060:

```text
PM daily artifact: pc-e6d857c27b1d386e-83060-0001
strategy/position_management artifact: pc-621be524366e3fcd-83060-0001
runtime/current position source: blank
```

That identity split should be treated as part of the provenance contract failure, not papered over by another single-field guess.

## Final Judgments

PHASE32_AB_AA_PENDING_CAMPAIGN_OBSERVED = NO

PHASE32_AB_AA_ORDER_CAMPAIGN_OBSERVED = NO

PHASE32_AB_AA_EXECUTION_CAMPAIGN_OBSERVED = NO

PHASE32_AB_STRICT_PM_MATCH_OBSERVED = NO

PHASE32_AB_NON_GENERIC_PRIOR_CONTEXT_OBSERVED = NO

PHASE32_AB_PHASE32_AA_ACTUAL_PATH_ACCEPTED = NO

PHASE32_AB_STRICT_BRIDGE_FIRST_FAILED_PREDICATE = PM evidence campaign `pc-e6d857c27b1d386e-83060-0001` does not equal reconstructed close campaign `ledger-derived-83060-0001`, because persistent execution campaign is blank.

PHASE32_AB_83060_2022_10_25_CLEARLY_STRONG_AGAIN = PARTIAL

PHASE32_AB_83060_2022_10_26_CLEARLY_STRONG_AGAIN = PARTIAL

PHASE32_AB_83060_FINAL_ZERO_TARGET_BLOCKER = `semantic_reentry_recovery_hurdle_not_satisfied` / `insufficient_prior_exit_context` in Portfolio Construction before Cash, lot, or PS.

PHASE32_AB_REENTRY_ELIGIBLE_83060_10_25 = NO

PHASE32_AB_REENTRY_ELIGIBLE_83060_10_26 = NO

PHASE32_AB_POSITIVE_TARGET_83060_10_25 = NO

PHASE32_AB_POSITIVE_TARGET_83060_10_26 = NO

PHASE32_AB_BROADER_SAME_BLOCKER_MATERIAL = YES

PHASE32_AB_PROVENANCE_DEFECT_CLOSED = NO

PHASE32_AB_REENTRY_CONTRACT_OVER_SUPPRESSION = UNRESOLVED

PHASE32_AB_TRADING_OUTCOME_IDENTICAL_REASON = A: AA actual path still not accepted; strict/non-GENERIC prior context never materialized, so all REENTRY targets remained zero.

PHASE32_AB_PRODUCTION_REPAIR_JUSTIFIED = YES

PHASE32_AB_IMPLEMENTATION_READY = NO

PHASE32_AB_LONGER_VALIDATION_READY = NO

PHASE32_AB_NEXT_STEP = Narrow provenance-boundary repair planning for Pending/order/execution campaign materialization after resolving the observed 83060 campaign identity split; then user-operated short fresh validation.
