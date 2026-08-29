# Phase32-AI - REENTRY Safety Structured Taxonomy Completion Repair

## Executive Summary

Phase32-AI completed the narrow taxonomy repair identified by Phase32-AH. The repair keeps the Phase32-AG positive-support behavior and closes the inverse false-pass gap by making `_reentry_safety_status(...)` a three-state structured contract:

- `PASS`: explicit positive/support structured statuses and non-blocking support codes.
- `REVIEW_REQUIRED`: unresolved structured statuses or review/unknown exact codes.
- `FAIL_CLOSED`: explicit blocking structured statuses, explicit false safety booleans, and exact canonical blocking reason-code aliases.

No REENTRY recovery, cooldown, rank, BUY Quality, Cash competition, PC/MCC, Risk Pacing, sizing, model, SELL logic, runtime state, fresh-run, resume, replay, or backtest was changed or executed.

## Inherited AH Gaps

Phase32-AH confirmed that Phase32-AG fixed the original positive collision, but left narrow false-pass risks if routed directly into `_reentry_safety_status(...)`:

- Review/unknown: `BROKER_PRODUCT_CATEGORY_UNKNOWN`, `broker_eligibility_status=UNKNOWN`, `safety_status=REVIEW_REQUIRED`.
- Explicit blocker aliases: `INSUFFICIENT_CASH`, `CORPORATE_ACTION_BLOCK`, `CORPORATE_EVENT_BLOCK`, `liquidity_block`.
- Contract-ambiguous: `SAFETY_CAP_BOUND`.

AI classifies these with exact structured semantics, not noun substring matching.

## Production Vocabulary Classification

| Vocabulary | Producer / Contract Evidence | AI Classification | Reason |
|---|---|---|---|
| `BROKER_PRODUCT_CATEGORY_SUPPORTED` | `broker.issue_code_normalizer.classify_broker_security` support reason | `PASS` | Supported cash-equity product category |
| `broker_eligibility_status=PASS` | PC broker eligibility field | `PASS` | Structured pass |
| `BROKER_PRODUCT_CATEGORY_UNSUPPORTED` | Broker normalizer unsupported category | `FAIL_CLOSED` | Explicit unsupported broker product |
| `broker_eligible=False` | Structured broker boolean | `FAIL_CLOSED` | Explicit ineligibility |
| `tradable=False` | Structured tradability boolean | `FAIL_CLOSED` | Explicit non-tradable |
| `listed_info_not_current` | Broker normalizer error | `FAIL_CLOSED` | Listed-info currentness failure |
| `listed_info_code_mismatch` | Broker normalizer error | `FAIL_CLOSED` | Identity mismatch |
| `BROKER_PRODUCT_CATEGORY_UNKNOWN` | Broker normalizer unknown category | `REVIEW_REQUIRED` | Unresolved broker classification |
| `broker_eligibility_status=UNKNOWN` | Safety-relevant structured status | `REVIEW_REQUIRED` | Unknown is not positive evidence |
| `INSUFFICIENT_BUYING_POWER` | Buying-power vocabulary | `FAIL_CLOSED` | Execution cannot be funded |
| `BUYING_POWER_AFTER_CASH_BUFFER` | Buying-power/cash-buffer vocabulary | `FAIL_CLOSED` | Execution blocked after reserve |
| `INSUFFICIENT_CASH` | Position sizing evidence class for non-executable residual/current capital | `FAIL_CLOSED` | Execution/capital inability when routed to Safety |
| `CASH_OPTIONALITY*`, `CASH_PREFERRED*`, `NO_VALID_COMPETITOR` | PC/Cash competition and observability | `PASS` / not Safety authority | Cash preference is not Safety failure |
| `safety_hard_cap_preserved` | Safety support vocabulary | `PASS` | Preserved cap is positive evidence |
| `safety_status=PASS` | Structured safety status | `PASS` | Structured pass |
| `safety_status=REVIEW_REQUIRED` | Structured safety status | `REVIEW_REQUIRED` | Unresolved Safety evidence |
| `SAFETY_HARD_CAP_VIOLATION` | Safety hard-cap vocabulary | `FAIL_CLOSED` | Explicit violation |
| `MINIMUM_LOT_EXCEEDS_SAFETY_HARD_CAP` | Lot/safety hard-cap vocabulary | `FAIL_CLOSED` | Minimum executable lot breaches hard cap |
| `explicit_safety_prohibition` | Safety prohibition vocabulary | `FAIL_CLOSED` | Explicit prohibition |
| `execution_safety_block` / `execution_safety_blocked` | Execution safety vocabulary | `FAIL_CLOSED` | Explicit execution safety block |
| `SAFETY_CAP_BOUND` | Position sizing evidence class with `TERMINAL_FOR_CURRENT_CAPITAL_AUTHORITY`; PC residual reconsideration treats it terminal | `FAIL_CLOSED` when routed to Safety | Safety hard-cap bound, not positive support |
| `corporate_action_status=NO_EVENT` | PC corporate-action evidence | `PASS` | No event |
| `CORPORATE_ACTION_BLOCKING` / `reentry_corporate_action_blocking` | PC recovery/safety vocabulary | `FAIL_CLOSED` | Explicit corporate action block |
| `CORPORATE_ACTION_BLOCK` | Buy Quality / opportunity hard reason | `FAIL_CLOSED` | Canonical hard-block alias |
| `CORPORATE_EVENT_BLOCK` | Buy Quality / opportunity hard reason | `FAIL_CLOSED` | Canonical hard-block alias |
| `liquidity_status=UNKNOWN` | REENTRY safety helper input | `REVIEW_REQUIRED` | Unknown liquidity is unresolved |
| `liquidity_capacity_status=NORMAL` | PC liquidity/capacity status | `PASS` | Normal capacity |
| `liquidity_block` | Buy Quality / opportunity hard reason | `FAIL_CLOSED` | Canonical hard-block alias |

## Status Normalization

`_reentry_safety_status(...)` now consumes structured safety-relevant fields with explicit status normalization:

- PASS-like: `PASS`, `ELIGIBLE`, `SUPPORTED`, `NORMAL`, `AVAILABLE`, `SUFFICIENT`, `ALLOWED`, `PRESERVED`, `NON_BLOCKING`, `NO_EVENT`, `CURRENT`, `OK`, `RESOLVED`, `NO_BLOCKING_EVENT`, `NOT_APPLICABLE`.
- Review-like: `UNKNOWN`, `MISSING`, `REVIEW_REQUIRED`.
- Blocking-like: `FAIL`, `FAILED`, `FAIL_CLOSED`, `BLOCK`, `BLOCKED`, `REJECT`, `REJECTED`, `UNSUPPORTED`, `VIOLATION`, `PROHIBITED`.

Unrecognized non-empty values in safety-relevant structured status fields return `REVIEW_REQUIRED` rather than silently passing.

## Old / New Taxonomy

Old pre-AG behavior:

```text
reason text/code contains safety/broker/cash/buying_power/corporate_action_blocking -> FAIL_CLOSED
```

AG behavior:

```text
explicit blocking status/code/false boolean -> FAIL_CLOSED
liquidity UNKNOWN -> REVIEW_REQUIRED
otherwise PASS
```

AI behavior:

```text
explicit blocking status/code/false boolean -> FAIL_CLOSED
explicit review/unknown code or structured status -> REVIEW_REQUIRED
unrecognized safety-relevant structured status -> REVIEW_REQUIRED
liquidity UNKNOWN/MISSING/REVIEW_REQUIRED -> REVIEW_REQUIRED
otherwise PASS
```

The implementation remains exact-code / exact-field based. It does not use generic noun matching or broad negative-word scanning.

## Positive Regression Matrix

| Case | Expected return | Observed return | Test status |
|---|---|---|---|
| `BROKER_PRODUCT_CATEGORY_SUPPORTED` | `PASS` | `PASS` | PASS |
| `broker_eligibility_status=PASS` | `PASS` | `PASS` | PASS |
| `broker_product_category_status=SUPPORTED` | `PASS` | `PASS` | PASS |
| positive Cash optionality/support text | `PASS` | `PASS` | PASS |
| `cash_buying_power_status=AVAILABLE` | `PASS` | `PASS` | PASS |
| `buying_power_status=SUFFICIENT` | `PASS` | `PASS` | PASS |
| `safety_hard_cap_preserved` | `PASS` | `PASS` | PASS |
| `safety_status=PASS` | `PASS` | `PASS` | PASS |
| `corporate_action_status=NO_EVENT` | `PASS` | `PASS` | PASS |
| `liquidity_capacity_status=NORMAL` | `PASS` | `PASS` | PASS |

## Review Regression Matrix

| Case | Expected return | Observed return | Test status |
|---|---|---|---|
| `BROKER_PRODUCT_CATEGORY_UNKNOWN` | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | PASS |
| `broker_eligibility_status=UNKNOWN` | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | PASS |
| `broker_product_category_status=MISSING` | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | PASS |
| `safety_status=REVIEW_REQUIRED` | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | PASS |
| unrecognized structured Safety status | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | PASS |
| `liquidity_status=UNKNOWN` | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | PASS |

## Negative Regression Matrix

| Case | Expected return | Observed return | Test status |
|---|---|---|---|
| `BROKER_PRODUCT_CATEGORY_UNSUPPORTED` | `FAIL_CLOSED` | `FAIL_CLOSED` | PASS |
| `broker_eligible=False` | `FAIL_CLOSED` | `FAIL_CLOSED` | PASS |
| `tradable=False` | `FAIL_CLOSED` | `FAIL_CLOSED` | PASS |
| `INSUFFICIENT_BUYING_POWER` | `FAIL_CLOSED` | `FAIL_CLOSED` | PASS |
| `BUYING_POWER_AFTER_CASH_BUFFER` | `FAIL_CLOSED` | `FAIL_CLOSED` | PASS |
| `INSUFFICIENT_CASH` | `FAIL_CLOSED` | `FAIL_CLOSED` | PASS |
| `SAFETY_HARD_CAP_VIOLATION` | `FAIL_CLOSED` | `FAIL_CLOSED` | PASS |
| `SAFETY_CAP_BOUND` | `FAIL_CLOSED` | `FAIL_CLOSED` | PASS |
| `MINIMUM_LOT_EXCEEDS_SAFETY_HARD_CAP` | `FAIL_CLOSED` | `FAIL_CLOSED` | PASS |
| `explicit_safety_prohibition` | `FAIL_CLOSED` | `FAIL_CLOSED` | PASS |
| `CORPORATE_ACTION_BLOCKING` | `FAIL_CLOSED` | `FAIL_CLOSED` | PASS |
| `CORPORATE_ACTION_BLOCK` | `FAIL_CLOSED` | `FAIL_CLOSED` | PASS |
| `CORPORATE_EVENT_BLOCK` | `FAIL_CLOSED` | `FAIL_CLOSED` | PASS |
| `liquidity_block` | `FAIL_CLOSED` | `FAIL_CLOSED` | PASS |
| `safety_status=FAILED` | `FAIL_CLOSED` | `FAIL_CLOSED` | PASS |
| `execution_safety_status=PROHIBITED` | `FAIL_CLOSED` | `FAIL_CLOSED` | PASS |

## 83060 Controls

Captured artifact compatibility used:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T071407047414Z`

Structured scan through 2022-10-26:

- REENTRY rows: `583`
- Unique symbols: `22`
- Recomputed AI safety distribution:
  - `PASS`: `583`

83060 recomputation:

| Date | Safety | Eligibility | Semantic state |
|---|---|---|---|
| 2022-10-25 | `PASS` | `PASS` | `REENTRY_ELIGIBLE` |
| 2022-10-26 | `PASS` | `PASS` | `REENTRY_ELIGIBLE` |

## Adjacent Technical Debt

No adjacent REENTRY gates were changed. These remain separate audit candidates, as Phase32-AH noted:

- `_reentry_current_candidate_status(...)` still classifies current-candidate status from specific text tokens.
- `_reentry_block_state_and_reason(...)` still maps already-failed recovery reasons into block state labels.
- `_previous_exit_reason_class(...)` still classifies prior-exit reason strings/codes.

AI deliberately avoids refactoring these to keep the repair bounded to Safety taxonomy completion.

## Changed Files

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
  - Completed exact three-state Safety taxonomy in `_reentry_safety_status(...)`.
- `tests/strategy/test_phase30_z_reentry_genuine_recovery.py`
  - Added AI positive, review, and negative taxonomy regression matrices.
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
  - Added SoT language for the three-state REENTRY Safety contract and Cash/Safety-cap semantics.
- `docs/phase_reports/phase32_ai_reentry_safety_structured_taxonomy_completion_repair.md`
  - This report.

## Verification

| Command | Result |
|---|---|
| `PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase32_ai_pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py` | PASS |
| `PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase32_ai_pycache python3 -m pytest tests/strategy/test_phase30_z_reentry_genuine_recovery.py -q` | `15 passed in 0.23s` |
| `PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase32_ai_pycache python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l16_semantic_reentry_cooldown_and_recovery_hurdle -q` | `1 passed in 4.10s` |
| `PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase32_ai_pycache python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py -k 'phase29_l16 or phase31_g26' -q` | `9 passed, 113 deselected in 4.18s` |
| `PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase32_ai_pycache python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase30_z_reentry_genuine_recovery.py -q` | `137 passed in 2.29s` |
| `git diff --check -- src/ai_fund_lab_v2/strategy/portfolio_construction.py tests/strategy/test_phase30_z_reentry_genuine_recovery.py docs/02_architecture/strategy_intelligence_architecture_v1.md` | PASS |

## Registry Status

No Accepted Artifact Registry member for `src/ai_fund_lab_v2/strategy/portfolio_construction.py` was found in `.runtime`, docs, src, scripts, or configs search. Registry refresh is not applicable for this repair.

## Fresh Validation Readiness

Short fresh validation is ready from the Safety taxonomy perspective. Validation should be user-operated per the Phase32-AI constraints.

## Final Judgments

PHASE32_AI_BROKER_UNKNOWN_REVIEW = YES

PHASE32_AI_SAFETY_REVIEW_STATUS_REVIEW = YES

PHASE32_AI_INSUFFICIENT_CASH_CLASSIFICATION = FAIL_CLOSED

PHASE32_AI_SAFETY_CAP_BOUND_CLASSIFICATION = FAIL_CLOSED

PHASE32_AI_CORPORATE_ACTION_BLOCK_FAIL_CLOSED = YES

PHASE32_AI_CORPORATE_EVENT_BLOCK_FAIL_CLOSED = YES

PHASE32_AI_LIQUIDITY_BLOCK_CLASSIFICATION = FAIL_CLOSED

PHASE32_AI_UNKNOWN_DOES_NOT_SILENTLY_PASS = YES

PHASE32_AI_POSITIVE_SUPPORT_DOES_NOT_BLOCK = YES

PHASE32_AI_EXPLICIT_NEGATIVE_FAILS_CLOSED = YES

PHASE32_AI_THREE_STATE_SAFETY_CONTRACT = YES

PHASE32_AI_83060_10_25_REENTRY_ELIGIBLE_PRESERVED = YES

PHASE32_AI_83060_10_26_FALSE_SAFETY_BLOCK_ABSENT = YES

PHASE32_AI_CHURN_GATE_CHANGED = NO

PHASE32_AI_RECOVERY_GATE_CHANGED = NO

PHASE32_AI_CURRENT_EVIDENCE_GATE_CHANGED = NO

PHASE32_AI_CASH_PC_MCC_CHANGED = NO

PHASE32_AI_RISK_PACING_CHANGED = NO

PHASE32_AI_REGRESSION_STATUS = PASS

PHASE32_AI_OTHER_SAFETY_TAXONOMY_GAP_REMAINS = NO

PHASE32_AI_SHORT_FRESH_VALIDATION_READY = YES

PHASE32_AI_NEXT_STEP = User-operated short fresh validation after accepting the narrow Safety taxonomy repair.
