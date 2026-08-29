# Phase32-AF - REENTRY_NOT_ELIGIBLE_SAFETY Exact Predicate / Over-Suppression Deep Audit

## Executive Summary

READ-ONLY audit was performed for:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T071407047414Z`

Primary positive control: `83060 / 2022-10-25`  
Secondary control: `83060 / 2022-10-26`

`REENTRY_NOT_ELIGIBLE_SAFETY` is produced in `src/ai_fund_lab_v2/strategy/portfolio_construction.py` by `_canonical_reentry_semantic_eligibility(...)` after temporal, cooldown, recovery, and current-candidate gates pass. The exact safety predicate is `_reentry_safety_status(...)`.

Root cause: `_reentry_safety_status(...)` scans free-text reason strings and all row `reason_codes`, and fail-closes on any occurrence of `"broker"`. For 83060 on both 2022-10-25 and 2022-10-26, the only matching safety token is the positive eligibility reason code:

`BROKER_PRODUCT_CATEGORY_SUPPORTED`

This is not a genuine safety failure. It is a stale / over-broad token predicate that misclassifies positive broker support evidence as a safety restriction.

Conclusion: `REENTRY_CONTRACT_OVER_SUPPRESSION = YES`. Production repair is justified, but no implementation was performed in this audit.

## Exact Code Predicate

Production module:

`src/ai_fund_lab_v2/strategy/portfolio_construction.py`

Relevant functions:

- `_semantic_reentry_evidence(...)`
- `_reentry_recovery_evidence(...)`
- `_canonical_reentry_semantic_eligibility(...)`
- `_reentry_safety_status(...)`
- `_reentry_block_state_and_reason(...)`

The relevant precedence is:

```python
semantic = _semantic_reentry_evidence(...)
recovery = _reentry_recovery_evidence(...)
safety_status = _reentry_safety_status(...)

if semantic_type != "REENTRY":
    return REENTRY_NOT_APPLICABLE

if prior_exit_date is same-day/future:
    return REENTRY_NOT_ELIGIBLE_PRIOR_EXIT_CONTEXT

if cooldown_status != "PASS":
    return REENTRY_NOT_ELIGIBLE_CHURN_PROTECTION

if recovery_status != "PASS":
    return state derived from recovery_reason

if current_candidate_status != "PASS":
    return REENTRY_NOT_ELIGIBLE_CURRENT_EVIDENCE

if safety_status == "FAIL_CLOSED":
    return REENTRY_NOT_ELIGIBLE_SAFETY

return REENTRY_ELIGIBLE
```

Exact safety predicate:

```python
def _reentry_safety_status(row, liquidity_status, reason_text):
    text = " ".join([
        reason_text,
        " ".join(str(item) for item in row.get("reason_codes") or []),
    ]).lower()

    if any(token in text for token in (
        "safety",
        "broker",
        "cash",
        "buying_power",
        "corporate_action_blocking",
    )):
        return "FAIL_CLOSED"

    if liquidity_status == "UNKNOWN":
        return "REVIEW_REQUIRED"

    return "PASS"
```

This predicate is not field-specific. It treats positive and negative reason-code tokens identically.

## Predicate Components

| Component | Field/source | Blocking condition | 83060 2022-10-25 |
| --- | --- | --- | --- |
| Free-text safety token | target/review reason text | Contains `safety`, `broker`, `cash`, `buying_power`, or `corporate_action_blocking` | No blocking token except via reason codes |
| Row reason codes | `row.reason_codes` | Same substring scan | FAIL due `BROKER_PRODUCT_CATEGORY_SUPPORTED` |
| Liquidity unknown | `liquidity_status` | `UNKNOWN` returns `REVIEW_REQUIRED`, not safety fail | `NORMAL` |
| Prior exit class | `previous_exit_reason_class` | Not directly consumed by safety helper | `TREND_MOMENTUM` |
| Churn | cooldown and prior count | Evaluated before safety | PASS |
| Recovery | rank, BQ, trend, momentum, CA, capacity, CQ, downside, entry admission | Evaluated before safety | PASS |

The first blocking field is `reason_codes`.

## 83060 2022-10-25 Full Field Trace

| Group | Field | Value | Status |
| --- | --- | --- | --- |
| Prior context | `prior_exit_business_date` | `2022-10-04` | PASS |
| Prior context | `prior_exit_reason` | `trend_and_opportunity_broken` | PASS |
| Prior context | `prior_exit_reason_codes` | `["trend_and_opportunity_broken"]` | PASS |
| Prior context | `previous_exit_reason_class` | `TREND_MOMENTUM` | PASS |
| Prior context | strict authority | `persistent_ledger_execution_history_with_strict_prior_pm_exit_reason_bridge`; matched closes `17` | PASS |
| Churn | `business_days_since_exit` | `14` | PASS |
| Churn | cooldown threshold | `3` completed BD | PASS |
| Churn | repeated churn | `prior_same_symbol_exit_count=1` | PASS |
| Current strength | rank | `10` | PASS |
| Current strength | opportunity qualification | `reentry_opportunity_qualification_status=PASS` | PASS |
| Current strength | trend recovery | `trend_close_over_ma_20d=1.055926`, `reentry_trend_recovery_status=PASS` | PASS |
| Current strength | momentum recovery | `price_momentum_return_20d=0.033324`, `reentry_momentum_recovery_status=PASS` | PASS |
| Current strength | 5d return | `0.041355` | supportive |
| Current strength | 20d return | `0.033324` | supportive |
| Current strength | `trend_ma_5_20_ratio` | `1.038647` | supportive |
| Current strength | continuation | `strategy_intelligence_continuation_quality_status=PASS` | PASS |
| Current strength | downside | `strategy_intelligence_downside_risk_status=PASS` | PASS |
| Buy quality | `quality_status` | `PASS` | PASS |
| Buy quality | `buy_quality_authority.quality_action` | `FULL_ALLOCATION_ELIGIBLE` | PASS |
| Entry admission | `entry_state` | `CONTINUATION_WITH_CAUTION` | PASS, reduced |
| Entry admission | `admission_action` | `BUY_NEW_REDUCED_ONLY` | PASS, reduced |
| Entry admission | reversal/exhaustion | manageable / manageable | PASS |
| Capacity | `liquidity_capacity_status` | `NORMAL` | PASS |
| Corporate action | `reentry_corporate_action_status` | `NO_EVENT` | PASS |
| Candidate | `reentry_candidate_eligibility_status` | `PASS` | PASS |
| Renewed evidence | `reentry_renewed_current_evidence_status` | `PASS` | PASS |
| Safety | `reason_codes` | includes `BROKER_PRODUCT_CATEGORY_SUPPORTED` | FAIL_CLOSED by substring `"broker"` |
| Final | `reentry_semantic_state` | `REENTRY_NOT_ELIGIBLE_SAFETY` | BLOCK |
| Target | `normal_target_weight` -> `target_weight` | `0.032258` -> `0.0` | zeroed |

`FIRST_FALSE_OR_BLOCKING_PREDICATE = _reentry_safety_status(...): "broker" substring in row.reason_codes via BROKER_PRODUCT_CATEGORY_SUPPORTED`

## 10/26 Comparison

| Field | 2022-10-25 | 2022-10-26 |
| --- | --- | --- |
| Business days since exit | `14` | `15` |
| Rank | `10` | `9` |
| Prior class | `TREND_MOMENTUM` | `TREND_MOMENTUM` |
| Recovery status | `PASS` | `PASS` |
| Candidate status | `PASS` | `PASS` |
| Renewed evidence | `PASS` | `PASS` |
| Liquidity capacity | `NORMAL` | `NORMAL` |
| Corporate action | `NO_EVENT` | `NO_EVENT` |
| Safety token hit | `broker` from `BROKER_PRODUCT_CATEGORY_SUPPORTED` | same |
| Semantic state | `REENTRY_NOT_ELIGIBLE_SAFETY` | same |
| Normal target | `0.032258` | `0.038462` |
| Final target | `0.0` | `0.0` |

10/26 has more caution than 10/25: reversal and exhaustion risks are `ELEVATED_RISK`, short-term reversal is true, and momentum trajectory is `MIXED_OR_UNRESOLVED`. But those cautions did not create the safety block. The exact first blocker remains the same `BROKER_PRODUCT_CATEGORY_SUPPORTED` substring collision.

## Safety 2-Row Detail

The AE-window semantic REENTRY distribution through 2022-10-26 is:

| State | Count |
| --- | ---: |
| `REENTRY_NOT_ELIGIBLE_CURRENT_EVIDENCE` | 63 |
| `REENTRY_NOT_ELIGIBLE_CHURN_PROTECTION` | 52 |
| `REENTRY_INSUFFICIENT_EVIDENCE` | 5 |
| `REENTRY_NOT_ELIGIBLE_SAFETY` | 2 |

The two Safety rows are exactly:

| Date | Symbol | Prior class | Rank | Recovery | Candidate | Reason-code trigger |
| --- | --- | --- | ---: | --- | --- | --- |
| 2022-10-25 | 83060 | `TREND_MOMENTUM` | 10 | PASS | PASS | `BROKER_PRODUCT_CATEGORY_SUPPORTED` |
| 2022-10-26 | 83060 | `TREND_MOMENTUM` | 9 | PASS | PASS | `BROKER_PRODUCT_CATEGORY_SUPPORTED` |

No 83060-independent Safety example was found in the requested through-2022-10-26 sample.

## Recovery PASS vs Safety FAIL

Recovery PASS and Safety PASS are independent contracts in the implementation. `_reentry_recovery_evidence(...)` verifies prior context, rank, buy quality, corporate action, capacity, entry admission, continuation quality, downside risk, and technical recovery. It returned:

`reentry_recovery_status=PASS`, `reentry_recovery_reason=reentry_recovery_qualified`

After that, `_canonical_reentry_semantic_eligibility(...)` invokes a separate safety gate. The safety gate does not inspect structured broker eligibility status. It only scans text and reason codes. Therefore:

```text
BROKER_PRODUCT_CATEGORY_SUPPORTED
-> contains "broker"
-> _reentry_safety_status = FAIL_CLOSED
-> REENTRY_NOT_ELIGIBLE_SAFETY
```

This is not duplicated recovery. It is a stale / over-broad safety state defect.

## Architecture / Philosophy Comparison

Relevant SoT findings:

- Strategy Intelligence says REENTRY is preserved and not blanket-banned; it should distinguish genuine recovery from churn / unresolved continuation.
- Phase30-Z requires cooldown, non-generic prior cause, recovery of the prior cause, acceptable CQ/downside, non-blocking Entry Admission, corporate-action/capacity evidence, and repeated-churn suppression. 83060 10/25 satisfies these.
- Dual-path capital architecture says once re-entry is eligible, it enters the same current capital competition with no permanent discount or bonus merely because it is a re-entry.
- Phase31-G54 says `REENTRY_BEHAVES_AS_BUY_NEW_AFTER_ELIGIBILITY = YES` and receives no special penalty or bonus after eligibility is resolved.

The current Safety predicate is not aligned with that architecture for this case. It blocks a recovered REENTRY because a positive broker eligibility code contains the substring `"broker"`.

## Historical REENTRY Compatibility

Historical REENTRY is structurally reachable:

- `tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l16_semantic_reentry_cooldown_and_recovery_hurdle` asserts a cooldown-passed, trend/momentum prior-exit case reaches `REENTRY_ELIGIBLE` and `target_weight=0.05`.
- `tests/strategy/test_phase30_z_reentry_genuine_recovery.py` asserts genuine recovery remains possible even with negative diagnostic expected edge when prior cause, CQ, risk, entry admission, trend, momentum, rank, quality, corporate action, and capacity pass.
- Phase29-L21Q documents previous observed re-entry fills before later strict gating.

Current actual-path compatibility is weaker: through 2022-10-26 this run has 122 semantic REENTRY rows and zero `REENTRY_ELIGIBLE`. The contract is structurally reachable in tests, but the observed Safety branch reveals a current actual-path false block for rows that reach the late safety gate with positive broker reason codes.

## Counterfactual Structural Audit

Without using future returns, 83060 2022-10-25 is structurally eligible if only this Safety predicate is removed or narrowed:

- temporal contract PASS
- cooldown PASS
- prior context PASS
- recovery PASS
- current candidate PASS
- renewed evidence PASS
- liquidity NORMAL
- corporate action NO_EVENT
- `normal_target_weight=0.032258`

The next structural step would be `REENTRY_ELIGIBLE`, then a positive target candidate entering capital competition. This does not imply a fill or profit; it only confirms dependency order.

## Short-Term Churn Purpose

This Safety block is not short-term churn protection:

- cooldown threshold is `3` completed BD
- 83060 has `14` and `15` completed BD since exit
- `churn_protection_status=PASS`
- `prior_same_symbol_exit_count=1`

The block also is not a prior-history long-term penalty. It does not directly check `TREND_MOMENTUM` or `prior_exit_reason`. It is caused by text-token scanning of a positive broker support code.

## Clearly-Strong-Again Contradiction

83060 2022-10-25 remains a valid CLEARLY_STRONG positive control using PIT-safe evidence:

- rank 10
- 5d return `0.041355`
- 20d return `0.033324`
- `trend_ma_5_20_ratio=1.038647`
- `trend_close_over_ma_20d=1.055926`
- trend recovery PASS
- momentum recovery PASS
- continuation PASS
- downside PASS
- buy quality PASS / full allocation eligible in BUY Quality authority
- reversal and exhaustion risk manageable

The Safety result contradicts this evidence because it is not consuming a real safety risk field. Classification: stale safety state defect.

## Over-Suppression Judgment

All required YES conditions for over-suppression are satisfied for 83060 2022-10-25:

- strict prior context valid: YES
- cooldown satisfied: YES
- recovery PASS: YES
- current strength sufficient: YES
- safety block remains due stale/redundant/non-risk token: YES
- architecture says no permanent special penalty and no blanket ban: YES

`REENTRY_CONTRACT_OVER_SUPPRESSION = YES`

## Minimal Repair Options

Preferred repair: `E`

Minimal boundary:

Narrow `_reentry_safety_status(...)` so positive support reason codes such as `BROKER_PRODUCT_CATEGORY_SUPPORTED` and Cash/competition observability strings do not trigger fail-closed Safety by substring. Safety should consume structured negative fields or explicit blocking codes only, for example `broker_eligibility_status=FAIL_CLOSED`, `broker_product_category_unsupported`, `buying_power_blocked`, `safety_hard_cap_violation`, or `corporate_action_blocking`.

Do not change cooldown, recovery thresholds, rank, buy quality, Cash, PC/MCC, Risk Pacing, or model behavior.

## Implementation Readiness

Implementation is ready as a narrow production repair because:

- exact component is identified: `_reentry_safety_status(...)`
- exact false trigger is identified: `BROKER_PRODUCT_CATEGORY_SUPPORTED`
- exact positive controls are identified: 83060 2022-10-25 and 2022-10-26
- structural counterfactual is clear: removing the false Safety trigger allows eligibility to proceed to normal capital competition
- the repair can be bounded to structured negative safety evidence only

## Final Judgments

PHASE32_AF_SAFETY_PREDICATE_FUNCTION = `src/ai_fund_lab_v2/strategy/portfolio_construction.py::_reentry_safety_status`

PHASE32_AF_SAFETY_PREDICATE_EXACT_CONDITION = `any(token in lower(reason_text + row.reason_codes) for token in ("safety", "broker", "cash", "buying_power", "corporate_action_blocking"))`

PHASE32_AF_83060_10_25_FIRST_BLOCKING_FIELD = `row.reason_codes[0] = BROKER_PRODUCT_CATEGORY_SUPPORTED`, matched by substring token `"broker"`

PHASE32_AF_83060_10_26_FIRST_BLOCKING_FIELD = `row.reason_codes[0] = BROKER_PRODUCT_CATEGORY_SUPPORTED`, matched by substring token `"broker"`

PHASE32_AF_RECOVERY_PASS_SAFETY_FAIL_CAUSE = Recovery and safety are separate gates; recovery passed, then safety fail-closed because positive broker support reason code matched an over-broad `"broker"` substring scan.

PHASE32_AF_SAFETY_IS_SHORT_TERM_CHURN_ONLY = NO

PHASE32_AF_SAFETY_USES_PRIOR_EXIT_HISTORY_LONG_TERM = NO

PHASE32_AF_DUPLICATED_RECOVERY_REQUIREMENT = NO

PHASE32_AF_STALE_SAFETY_STATE_DEFECT = YES

PHASE32_AF_CLEARLY_STRONG_AGAIN_EVIDENCE_VALID = YES

PHASE32_AF_83060_10_25_STRUCTURALLY_ELIGIBLE_WITHOUT_SAFETY = YES

PHASE32_AF_SAFETY_ROWS_TOTAL = 2

PHASE32_AF_HISTORICAL_REENTRY_PATH_COMPATIBLE = PARTIAL

PHASE32_AF_ARCHITECTURE_ALIGNMENT = NO

PHASE32_AF_REENTRY_CONTRACT_OVER_SUPPRESSION = YES

PHASE32_AF_PRODUCTION_REPAIR_JUSTIFIED = YES

PHASE32_AF_IMPLEMENTATION_READY = YES

PHASE32_AF_PREFERRED_REPAIR_OPTION = E

PHASE32_AF_MINIMAL_REPAIR_BOUNDARY = Narrow `_reentry_safety_status(...)` to explicit negative structured safety / broker / buying-power / corporate-action blocking evidence; do not substring-fail on positive support codes such as `BROKER_PRODUCT_CATEGORY_SUPPORTED`, and do not alter cooldown, recovery, rank, BUY Quality, Cash, PC/MCC, Risk Pacing, or models.

PHASE32_AF_LONGER_VALIDATION_READY = NO

PHASE32_AF_NEXT_STEP = Implement the narrow `_reentry_safety_status(...)` predicate repair with focused tests for positive broker support codes and explicit negative broker/safety/corporate-action blocks, then run a user-operated fresh validation.
