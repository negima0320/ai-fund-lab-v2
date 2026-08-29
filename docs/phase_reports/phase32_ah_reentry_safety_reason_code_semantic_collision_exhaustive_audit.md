# Phase32-AH - REENTRY Safety Reason-Code Semantic Collision Exhaustive Audit

## Executive Summary

Read-only audit completed for the Phase32-AG `_reentry_safety_status(...)` repair.

The original broad-token false-positive class is fixed for the observed production path: positive/support evidence containing `BROKER`, `CASH`, or `SAFETY` no longer becomes `FAIL_CLOSED` solely because those nouns are present. Against the captured post-AD run `runtime-test-historical-extended-smoke-20260827T071407047414Z`, 122 actual REENTRY rows carried `BROKER_PRODUCT_CATEGORY_SUPPORTED`; all 583 REENTRY-shaped rows through 2022-10-26 compute `PASS` under the repaired safety helper, and no positive-support actual artifact value still computes `FAIL_CLOSED`.

The 83060 positive controls are preserved under the repaired predicate. For 2022-10-25 and 2022-10-26, recomputing canonical REENTRY semantic eligibility from the stored PIT row yields `safety_restriction_status=PASS`, `eligibility_status=PASS`, and `reentry_semantic_state=REENTRY_ELIGIBLE`.

However, AG is not exhaustive as a general safety vocabulary contract. The focused negative-control invocation confirms canonical blockers such as `BROKER_PRODUCT_CATEGORY_UNSUPPORTED`, `BUYING_POWER_AFTER_CASH_BUFFER`, `INSUFFICIENT_BUYING_POWER`, `SAFETY_HARD_CAP_VIOLATION`, `MINIMUM_LOT_EXCEEDS_SAFETY_HARD_CAP`, and `CORPORATE_ACTION_BLOCKING` still fail closed, but several production/contract spelling variants and unknown/review statuses would currently pass if routed directly into `_reentry_safety_status(...)`: `BROKER_PRODUCT_CATEGORY_UNKNOWN`, `broker_eligibility_status=UNKNOWN`, `safety_status=REVIEW_REQUIRED`, `INSUFFICIENT_CASH`, `SAFETY_CAP_BOUND`, `CORPORATE_ACTION_BLOCK`, and `CORPORATE_EVENT_BLOCK`.

Final repair decision: `NARROW_GAP`. The demonstrated AG false-positive repair is semantically correct and separate from the R-AG provenance/campaign path. A narrow taxonomy hardening should be performed before short fresh validation if the goal is exhaustive protection against false-pass variants.

## Scope And Evidence

- Run artifact scanned: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T071407047414Z`
- Artifact period scanned: `daily/2022-10-03` through `daily/2022-10-26`
- Code audited:
  - `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
  - `src/ai_fund_lab_v2/broker/issue_code_normalizer.py`
  - `src/ai_fund_lab_v2/runtime_v2/buy_ai/opportunity_eligibility.py`
- Focused verification:
  - `PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase32_ah_pycache python3 -m pytest tests/strategy/test_phase30_z_reentry_genuine_recovery.py -q`
  - Result: `12 passed in 0.11s`

No production code, config, schema, threshold, model, runtime state, run state, replay, resume, backtest, or fresh-run was changed or executed.

## Reason / Status Inventory

| Value | Producer / Source | Field | Semantic | Reachability | AG treatment | Class |
|---|---|---|---|---|---|---|
| `BROKER_PRODUCT_CATEGORY_SUPPORTED` | `broker.issue_code_normalizer.classify_broker_security` | `broker_eligibility_reason`, `reason_codes` | Broker product supported | Actual REENTRY rows | `PASS` | B |
| `BROKER_PRODUCT_CATEGORY_UNSUPPORTED` / `broker_product_category_unsupported` | `broker.issue_code_normalizer`, `opportunity_eligibility` | reason code | Unsupported broker product category | Actual producer, helper direct | `FAIL_CLOSED` | A |
| `BROKER_PRODUCT_CATEGORY_UNKNOWN` | `broker.issue_code_normalizer` | reason code | Unknown broker product category | Possible broker classification | `PASS` if routed only as code | C |
| `broker_eligibility_status=PASS` | PC candidate row | status field | Broker eligible | Actual REENTRY rows | `PASS` | B |
| `broker_eligibility_status=UNKNOWN` | status vocabulary | status field | Unknown broker eligibility | Possible status alias | `PASS` | C |
| `broker_eligible=False` | PC safety helper input | boolean field | Explicit broker ineligible | Helper direct | `FAIL_CLOSED` | A |
| `tradable=False` | Broker/PC safety helper input | boolean field | Explicit non-tradable | Helper direct | `FAIL_CLOSED` | A |
| `listed_info_not_current` | broker normalizer | reason code | Listed-info currentness failure | Helper direct | `FAIL_CLOSED` | A |
| `listed_info_code_mismatch` | broker normalizer | reason code | Broker identity mismatch | Helper direct | `FAIL_CLOSED` | A |
| `BUYING_POWER_AFTER_CASH_BUFFER` / `buying_power_after_cash_buffer` | cash/buying-power contracts | reason code | Buying power blocked after cash buffer | Helper direct | `FAIL_CLOSED` | A |
| `INSUFFICIENT_BUYING_POWER` / `insufficient_buying_power` | buying-power contracts | reason code | Insufficient buying power | Helper direct | `FAIL_CLOSED` | A |
| `INSUFFICIENT_CASH` | cash execution vocabulary | reason code | Cash/execution inability | Possible downstream vocabulary | `PASS` if routed only as code | A/C |
| `CASH_OPTIONALITY*`, `CASH_PREFERRED*`, `NO_VALID_COMPETITOR` | PC/Cash competition | reason code | Cash preference/observability/competition | Not REENTRY safety authority | `PASS` | B/D |
| `safety_hard_cap_preserved` | PC safety support | reason code / boolean | Safety cap preserved | Helper direct | `PASS` unless boolean false | B |
| `SAFETY_HARD_CAP_VIOLATION` / `safety_hard_cap_violation` | safety hard-cap contracts | reason code | Safety hard-cap violation | Helper direct | `FAIL_CLOSED` | A |
| `MINIMUM_LOT_EXCEEDS_SAFETY_HARD_CAP` / `minimum_lot_exceeds_safety_hard_cap` | lot/safety cap contracts | reason code | One lot exceeds safety hard cap | Helper direct | `FAIL_CLOSED` | A |
| `SAFETY_CAP_BOUND` | PC cap vocabulary | reason code | Safety cap bound / cap-limited | Possible cap vocabulary | `PASS` if routed only as code | E |
| `safety_status=REVIEW_REQUIRED` | status vocabulary | status field | Safety unresolved/review | Possible status alias | `PASS` | C |
| `safety_status=VIOLATION` | status vocabulary | status field | Safety violation | Helper direct | `FAIL_CLOSED` | A |
| `explicit_safety_prohibition` | safety prohibition vocabulary | reason code | Explicit safety prohibition | Helper direct | `FAIL_CLOSED` | A |
| `execution_safety_block` / `execution_safety_blocked` | execution safety contracts | reason code | Execution safety block | Helper direct | `FAIL_CLOSED` | A |
| `corporate_action_status=NO_EVENT` | PC corporate-action evidence | status field | No blocking event | Actual REENTRY rows | `PASS` | B |
| `corporate_action_blocking` | PC recovery/safety code | reason code | Corporate action blocks REENTRY | Helper direct | `FAIL_CLOSED` | A |
| `reentry_corporate_action_blocking` | `_reentry_recovery_evidence` | recovery reason | Corporate action blocks REENTRY | Recovery path | `FAIL_CLOSED` through recovery; also covered as safety code | A |
| `CORPORATE_ACTION_BLOCK` | opportunity eligibility hard reasons | reason code | Corporate action hard block | Existing production vocabulary | `PASS` if routed only as safety code | A |
| `CORPORATE_EVENT_BLOCK` | opportunity eligibility hard reasons | reason code | Corporate event hard block | Existing production vocabulary | `PASS` if routed only as safety code | A |
| `liquidity_capacity_status=NORMAL` | PC liquidity/capacity | status field | Liquidity/capacity normal | Actual REENTRY rows | `PASS` | B |
| `liquidity_status=UNKNOWN` | helper argument | status argument | Unknown liquidity evidence | Helper direct | `REVIEW_REQUIRED` | C |
| `liquidity_block` | opportunity eligibility hard reasons | reason code | Liquidity hard block | Current-candidate/evidence vocabulary | `PASS` if routed only as safety code | A/D |
| `capacity_ratio > 0.03` or `liquidity_status=SEVERE` | `_reentry_recovery_evidence` | structured values | Capacity unavailable | Recovery path | `FAIL_CLOSED` via recovery, not safety helper | A |

Inventory completeness is `PARTIAL` rather than `YES` because the repository contains many generic `UNKNOWN` and `REVIEW_REQUIRED` statuses outside the REENTRY safety consumer. The audit covered the requested safety-related families and the actual REENTRY artifact vocabulary.

## Positive Collision Matrix

| Positive/support value | Actual observed? | Old broad-token behavior | AG treatment | Result |
|---|---:|---|---|---|
| `BROKER_PRODUCT_CATEGORY_SUPPORTED` | 122 REENTRY rows | Would match `broker` and fail closed | `PASS` | Fixed |
| `broker_eligibility_status=PASS` | 122 REENTRY rows | Not the original text-code trigger alone | `PASS` | Clean |
| `liquidity_capacity_status=NORMAL` | 217 REENTRY rows | Not blocked | `PASS` | Clean |
| `corporate_action_status=NO_EVENT` | 83060 positive rows and wider PC rows | Not a negative code | `PASS` | Clean |
| `cash_optionality_preserved` / positive cash support text | Unit/helper proof | Would match `cash` if scanned as text | `PASS` | Fixed |
| `safety_hard_cap_preserved` / `safety_pass` support text | Unit/helper proof | Would match `safety` or `hard_cap` if scanned as text | `PASS` | Fixed |

Actual artifact positive false-blocks after applying the AG predicate: `0`.

## Negative Coverage Matrix

| Category | Production vocabulary checked | AG outcome | Judgment |
|---|---|---|---|
| Broker unsupported | `BROKER_PRODUCT_CATEGORY_UNSUPPORTED`, `broker_product_category_unsupported` | `FAIL_CLOSED` | Covered |
| Broker unknown | `BROKER_PRODUCT_CATEGORY_UNKNOWN`, `broker_eligibility_status=UNKNOWN` | `PASS` | Gap |
| Broker listed-info failures | `listed_info_not_current`, `listed_info_code_mismatch` | `FAIL_CLOSED` | Covered |
| Tradability | `tradable=False` | `FAIL_CLOSED` | Covered |
| Buying power | `BUYING_POWER_AFTER_CASH_BUFFER`, `INSUFFICIENT_BUYING_POWER` | `FAIL_CLOSED` | Covered |
| Cash execution inability | `INSUFFICIENT_CASH` | `PASS` | Gap if routed to this helper |
| Safety hard cap | `SAFETY_HARD_CAP_VIOLATION`, `MINIMUM_LOT_EXCEEDS_SAFETY_HARD_CAP` | `FAIL_CLOSED` | Covered |
| Safety cap bound | `SAFETY_CAP_BOUND` | `PASS` | Ambiguous gap |
| Safety review status | `safety_status=REVIEW_REQUIRED` | `PASS` | Gap |
| Execution safety | `execution_safety_block`, `execution_safety_blocked` | `FAIL_CLOSED` | Covered |
| Corporate action | `CORPORATE_ACTION_BLOCKING`, `reentry_corporate_action_blocking` | `FAIL_CLOSED` | Covered |
| Corporate action alias | `CORPORATE_ACTION_BLOCK` | `PASS` | Gap if routed to this helper |
| Corporate event alias | `CORPORATE_EVENT_BLOCK` | `PASS` | Gap if routed to this helper |
| Liquidity unknown | helper `liquidity_status=UNKNOWN` | `REVIEW_REQUIRED` | Covered |
| Liquidity block code | `liquidity_block` | `PASS` | Gap if routed to safety helper; may be current-candidate authority instead |

## False-PASS Risk

`FALSE_PASS_RISK = YES`.

This is not observed on the actual 2022-10-03 through 2022-10-26 REENTRY artifacts. It is a contract risk in the helper’s vocabulary coverage:

- Status aliases `UNKNOWN` and `REVIEW_REQUIRED` are not treated as review-required by `_reentry_safety_status(...)`, except for the separate `liquidity_status` argument.
- `FAILED` is not in the helper's blocking status set; `FAIL` and `FAIL_CLOSED` are.
- Blocking aliases `CORPORATE_ACTION_BLOCK`, `CORPORATE_EVENT_BLOCK`, `liquidity_block`, `SAFETY_CAP_BOUND`, and `INSUFFICIENT_CASH` are present in repository vocabulary but are not explicit safety helper reason codes.
- The actual REENTRY path mitigates some of this through `_reentry_recovery_evidence(...)`: corporate-action non-pass statuses and capacity failures block before the safety helper. That mitigation does not make the helper taxonomy exhaustive.

## Remaining Substring Authority Inventory

| Location | Pattern | Decision authority? | Assessment |
|---|---|---|---|
| `_reentry_safety_status(...)` | exact membership after lower/tokenization | Yes | Fixed for broad noun collision; still taxonomy-limited |
| `_reentry_current_candidate_status(...)` | `any(token in text for token in ("not_selected", "negative_opportunity", "quality", "candidate", "opportunity"))` | Yes, current-candidate gate | Remaining free-text authority, but not Safety/broker/Cash/corporate noun collision |
| `_reentry_block_state_and_reason(...)` | recovery reason substring maps `corporate_action`, `safety`, `hard_cap`, `broker` to safety state when recovery already failed | Classification after failed recovery | Noun mapping remains, but only after `recovery_status != PASS`; it does not create the original positive-support false block |
| `_previous_exit_reason_class(...)` | text/code substring classification | Prior-exit semantic class | Not safety authority |
| ADD/residual/Cash diagnostics | substring/token scans in non-REENTRY safety contexts | Mixed | Out of AH consumer path or observability/competition, not the AG collision path |

`PHASE32_AH_REMAINING_FREE_TEXT_SAFETY_AUTHORITY = PARTIAL`: the original safety helper no longer broad-scans nouns, but adjacent REENTRY gates still use text-derived classification for current-candidate and recovery-state labelling.

## Actual Artifact Vocabulary Scan

Structured scan of `strategy/portfolio_construction.json` through 2022-10-26:

- REENTRY-shaped rows found recursively: `583`
- Unique symbols: `22`
- Computed repaired safety status distribution:
  - `PASS`: `583`
  - `REVIEW_REQUIRED`: `0`
  - `FAIL_CLOSED`: `0`
- Rows that would have been broad-token safety-block candidates under the old predicate: `126`
- Observed positive false-blocks after AG predicate: `0`

Top REENTRY reason/status evidence:

| Count | Value |
|---:|---|
| 244 | `REENTRY_IDENTITY_PRIOR_EXIT` |
| 149 | `reentry_opportunity_not_requalified` |
| 140 | `REENTRY_CHURN_PROTECTION_SATISFIED` |
| 126 | `REENTRY_BLOCKED_CURRENT_ELIGIBILITY` |
| 122 | `BROKER_PRODUCT_CATEGORY_SUPPORTED` |
| 122 | `opportunity_rank_preserved` |
| 117 | `candidate_eligible` |
| 117 | `selection_quality_caution_continuation` |
| 115 | `strategy_intelligence_entry_reduced_allocation_only` |
| 104 | `REENTRY_BLOCKED_CHURN_PROTECTION` |
| 88 | `buy_quality_reduced_allocation_only` |
| 36 | `reentry_minimum_cooldown_not_satisfied` |
| 16 | `buy_quality_wait` |
| 15 | `reentry_trend_recovery_not_satisfied` |
| 15 | `reentry_momentum_recovery_not_satisfied` |
| 14 | `insufficient_prior_exit_context` |
| 13 | `buy_quality_full_allocation_eligible` |
| 10 | `REENTRY_INSUFFICIENT_EVIDENCE` |
| 5 | `opportunity_no_buy_reason_hard_block:high_downside_risk_score|non_positive_expected_edge_score` |
| 5 | `opportunity_no_buy_reason_present:high_downside_risk_score|non_positive_expected_edge_score` |
| 4 | `REENTRY_BLOCKED_SAFETY` stored in pre-AG artifact |
| 2 | `reentry_recovery_qualified` |

Important status evidence:

| Count | Field | Value |
|---:|---|---|
| 224 | `reentry_recovery_status` | `FAIL_CLOSED` |
| 217 | `liquidity_capacity_status` | `NORMAL` |
| 140 | `reentry_cooldown_status` | `PASS` |
| 122 | `broker_eligibility_status` | `PASS` |
| 104 | `reentry_cooldown_status` | `FAIL_CLOSED` |
| 16 | `reentry_recovery_status` | `REVIEW_REQUIRED` |
| 4 | `reentry_recovery_status` | `PASS` |

The stored `REENTRY_BLOCKED_SAFETY` values are from the captured pre-AG/post-AD run artifacts and are not post-repair output. Recomputing the safety predicate against those rows is the relevant read-only control.

## 83060 Positive Controls

For 83060, actual stored PC rows have:

| Date | Stored state | Stored safety | Prior exit | Class | Recovery | Broker support | Recomputed AG safety | Recomputed semantic |
|---|---|---|---|---|---|---|---|---|
| 2022-10-25 | `REENTRY_NOT_ELIGIBLE_SAFETY` | `FAIL_CLOSED` | `2022-10-04 trend_and_opportunity_broken` | `TREND_MOMENTUM` | `PASS / reentry_recovery_qualified` | `BROKER_PRODUCT_CATEGORY_SUPPORTED` | `PASS` | `REENTRY_ELIGIBLE / PASS` |
| 2022-10-26 | `REENTRY_NOT_ELIGIBLE_SAFETY` | `FAIL_CLOSED` | `2022-10-04 trend_and_opportunity_broken` | `TREND_MOMENTUM` | `PASS / reentry_recovery_qualified` | `BROKER_PRODUCT_CATEGORY_SUPPORTED` | `PASS` | `REENTRY_ELIGIBLE / PASS` |

Focused recomputation output:

```text
2022-10-25 safety_restriction_status=PASS eligibility_status=PASS reentry_semantic_state=REENTRY_ELIGIBLE
2022-10-26 safety_restriction_status=PASS eligibility_status=PASS reentry_semantic_state=REENTRY_ELIGIBLE
```

## Genuine Negative Controls

Non-mutating helper invocation with repository vocabulary:

| Case | Input | Result |
|---|---|---|
| Broker block | `BROKER_PRODUCT_CATEGORY_UNSUPPORTED` | `FAIL_CLOSED` |
| Broker block | `broker_product_category_unsupported` | `FAIL_CLOSED` |
| Tradability block | `tradable=False` | `FAIL_CLOSED` |
| Buying-power block | `BUYING_POWER_AFTER_CASH_BUFFER` | `FAIL_CLOSED` |
| Buying-power block | `INSUFFICIENT_BUYING_POWER` | `FAIL_CLOSED` |
| Safety hard-cap | `SAFETY_HARD_CAP_VIOLATION` | `FAIL_CLOSED` |
| Safety hard-cap / lot | `MINIMUM_LOT_EXCEEDS_SAFETY_HARD_CAP` | `FAIL_CLOSED` |
| Corporate action | `CORPORATE_ACTION_BLOCKING` | `FAIL_CLOSED` |
| Liquidity unknown | `liquidity_status=UNKNOWN` | `REVIEW_REQUIRED` |

Negative-control gaps:

| Case | Input | Current result |
|---|---|---|
| Broker unknown | `BROKER_PRODUCT_CATEGORY_UNKNOWN` | `PASS` |
| Broker unknown status | `broker_eligibility_status=UNKNOWN` | `PASS` |
| Safety review | `safety_status=REVIEW_REQUIRED` | `PASS` |
| Cash inability alias | `INSUFFICIENT_CASH` | `PASS` |
| Safety cap alias | `SAFETY_CAP_BOUND` | `PASS` |
| Corporate action alias | `CORPORATE_ACTION_BLOCK` | `PASS` |
| Corporate event alias | `CORPORATE_EVENT_BLOCK` | `PASS` |

## Cash Semantics

AG correctly removes the old “cash noun means safety block” behavior. Positive/observational Cash vocabulary such as Cash optionality, Cash preference, valid reserve, and `NO_VALID_COMPETITOR` should not be REENTRY Safety blockers by noun presence.

The remaining gap is narrower: cash execution inability vocabulary must be handled through explicit buying-power/execution fields or exact codes. `INSUFFICIENT_BUYING_POWER` and `BUYING_POWER_AFTER_CASH_BUFFER` are covered; `INSUFFICIENT_CASH` is not covered if routed directly to `_reentry_safety_status(...)`.

## Broker Semantics

Supported/eligible broker evidence is clean:

- `BROKER_PRODUCT_CATEGORY_SUPPORTED` -> `PASS`
- `broker_eligibility_status=PASS` -> `PASS`

Explicit unsupported product-category evidence is clean:

- `BROKER_PRODUCT_CATEGORY_UNSUPPORTED` -> `FAIL_CLOSED`
- `broker_product_category_unsupported` -> `FAIL_CLOSED`

Remaining broker gap:

- `BROKER_PRODUCT_CATEGORY_UNKNOWN` and status-level `UNKNOWN` currently pass in the safety helper if no other gate catches them. Unknown broker eligibility should be `REVIEW_REQUIRED` or fail-closed by explicit contract, not silent `PASS`.

## Safety Semantics

Positive safety support is clean:

- `safety_hard_cap_preserved` and positive safety-pass text do not block by noun.

Explicit safety hard-cap blockers are mostly clean:

- `SAFETY_HARD_CAP_VIOLATION` -> `FAIL_CLOSED`
- `MINIMUM_LOT_EXCEEDS_SAFETY_HARD_CAP` -> `FAIL_CLOSED`
- `explicit_safety_prohibition` -> `FAIL_CLOSED`

Remaining safety gap:

- `safety_status=REVIEW_REQUIRED` currently passes.
- `SAFETY_CAP_BOUND` currently passes as a reason code. Its contract meaning is ambiguous between “cap-limited but safe” and “safety cap blocked”; it should be explicitly classified rather than inherited by omission.

## Corporate Action Semantics

The REENTRY recovery path already blocks non-pass corporate-action status:

- `_corporate_action_evidence(...)` reads `corporate_action_status`, `corporate_event_status`, `corporate_action_blocking_status`, and `corporate_event_blocking_status`.
- `_reentry_recovery_evidence(...)` emits `reentry_corporate_action_blocking` when the corporate-action status is neither pass/resolved/no-event.
- `_reentry_block_state_and_reason(...)` maps that failed recovery to `REENTRY_NOT_ELIGIBLE_SAFETY`.

The standalone safety helper covers `corporate_action_blocking`, `corporate_event_blocking`, and `reentry_corporate_action_blocking`, but not the opportunity hard-reason aliases `CORPORATE_ACTION_BLOCK` and `CORPORATE_EVENT_BLOCK`. That is a narrow taxonomy gap, not an observed 83060 false-block.

## R-AG Regression Risk Note

The Safety semantic path and the R-AG provenance/campaign path are separate concerns:

- R/AA/AD/Y repairs preserve PM/pending/ledger/campaign lineage.
- AG changes only the PC-side REENTRY safety predicate.
- The repaired predicate consumes row fields and reason codes; it does not write or reinterpret `pm_decision_id`, `source_pm_decision_id`, `position_campaign_id`, or strict-prior PM evidence.

No evidence was found that AG can regress campaign/provenance identity. The remaining AH issue is vocabulary taxonomy coverage.

## Repair Decision

`PHASE32_AH_REPAIR_DECISION = NARROW_GAP`.

Recommended minimal follow-up boundary:

- Add explicit `REVIEW_REQUIRED` handling for status fields that carry `UNKNOWN`, `MISSING`, or `REVIEW_REQUIRED`.
- Add exact aliases for canonical production blockers if they are intended to be safety-helper authority:
  - `broker_product_category_unknown` -> likely `REVIEW_REQUIRED`
  - `insufficient_cash` -> likely `FAIL_CLOSED` or explicit Cash/execution authority
  - `corporate_action_block`, `corporate_event_block`, `liquidity_block` -> likely `FAIL_CLOSED` if routed to Safety
  - `safety_cap_bound` -> must be contract-classified before deciding
- Keep the scope limited to vocabulary/status taxonomy. Do not change thresholds, cooldown, recovery requirements, Cash/PC/MCC/Risk Pacing, sizing, or performance behavior.

Short fresh validation is not recommended until the narrow taxonomy gap is closed or explicitly accepted as out-of-scope by contract.

## Final Judgments

PHASE32_AH_REASON_CODE_INVENTORY_COMPLETE = PARTIAL

PHASE32_AH_POSITIVE_COLLISION_CODES_FOUND = `BROKER_PRODUCT_CATEGORY_SUPPORTED`, `cash_optionality_preserved`, `safety_hard_cap_preserved`, positive support text containing `cash`, `safety`, or `broker`

PHASE32_AH_POSITIVE_COLLISION_REMAINING = NO

PHASE32_AH_NEGATIVE_BLOCKING_VOCABULARY_COMPLETE = PARTIAL

PHASE32_AH_FALSE_PASS_RISK = YES

PHASE32_AH_REMAINING_FREE_TEXT_SAFETY_AUTHORITY = PARTIAL

PHASE32_AH_ACTUAL_ARTIFACT_POSITIVE_FALSE_BLOCK_REMAINS = NO

PHASE32_AH_BROKER_SEMANTICS_CLEAN = PARTIAL

PHASE32_AH_CASH_SEMANTICS_CLEAN = PARTIAL

PHASE32_AH_SAFETY_SEMANTICS_CLEAN = PARTIAL

PHASE32_AH_CORPORATE_ACTION_SEMANTICS_CLEAN = PARTIAL

PHASE32_AH_83060_10_25_REENTRY_ELIGIBLE_PRESERVED = YES

PHASE32_AH_83060_10_26_REENTRY_ELIGIBLE_PRESERVED = YES

PHASE32_AH_GENUINE_NEGATIVE_BLOCKS_PRESERVED = PARTIAL

PHASE32_AH_AG_REPAIR_SEMANTICALLY_COMPLETE = PARTIAL

PHASE32_AH_REPAIR_DECISION = NARROW_GAP

PHASE32_AH_PRODUCTION_REPAIR_JUSTIFIED = YES

PHASE32_AH_IMPLEMENTATION_READY = YES

PHASE32_AH_SHORT_FRESH_VALIDATION_READY = NO

PHASE32_AH_NEXT_STEP = Implement a narrow Phase32-AI taxonomy repair for `_reentry_safety_status(...)`: preserve positive support PASS behavior, add explicit review/fail handling for observed production negative/unknown aliases, add focused tests for each gap, then run user-operated short fresh validation after acceptance.
