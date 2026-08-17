# Phase30-AK3R0 - Post-AK2 Zero-BUY Fresh Regression Root-Cause Audit

Task ID: `Phase30-AK3R0`

Audit boundary:

```text
READ_ONLY_REGRESSION_AUDIT
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AK3R0
FRESH_RUN_EXECUTED_BY_CODEX = NO
REPLAY_RESUME_MUTATION_BY_CODEX = NO
```

Compared runs:

```text
Before: runtime-test-historical-extended-smoke-20260816T120536241332Z
After:  runtime-test-historical-extended-smoke-20260816T220031787551Z
Dates:  2022-08-10, 2022-08-12
```

## Primary Judgment

```text
POST_AK2_ZERO_BUY_ROOT_CAUSE_CONFIRMED_SUBMIT_FEASIBILITY_AUTHORITY_HANDOFF_GAP
```

AK2 did materialize minimum executable one-lot authority in PC/PS and increased
positive PS quantities. The zero-BUY regression did not come from Candidate,
SI, Entry, PC target collapse, or PS zeroing.

The behavioral failure materialized later:

```text
PC/PS minimum executable one-lot admission
-> Runtime planning / Pending BUY items
-> Submit feasibility REVIEW_REQUIRED
-> item-scoped review atomic BUY batch block
-> no submitted orders
-> no fills
```

Root cause:

```text
MINIMUM_EXECUTABLE_ONE_LOT_ADMISSION_REACHED_PENDING_WITH_EXECUTABLE_NOTIONAL_ABOVE_SELECTED_POSITION_AMOUNT
SUBMIT_ITEM_SCOPED_REVIEW_BLOCKED_ATOMIC_BUY_BATCH
```

## Before / After Chain Summary

### 2022-08-10

| Layer | Before | After |
| --- | ---: | ---: |
| Buy Quality decisions | 50 | 50 |
| PC target-positive members | 16 | 16 |
| AK2 authority in PC | 0 | 57 string hits |
| PS positive quantities | 8 | 13 |
| AK2 authority in PS | 0 | 92 string hits |
| Runtime BUY-like plans | 8 | 13 |
| Morning pending items | 8 | 13 |
| Submit pending state | `APPROVED` | `REVIEW_REQUIRED` |
| Submitted orders | 8 | 0 |
| BUY fills | 8 | 0 |

After pending item review:

```text
ITEM_REVIEW_REQUIRED: 5
BLOCKED_BY_BATCH_REVIEW: 8
reason: estimated amount exceeds selected_position_amount
```

Review-required one-lot items:

| Symbol | selected_position_amount | executable notional | reserved notional |
| --- | ---: | ---: | ---: |
| 38410 | 46,469 | 80,800 | 96,700 |
| 39950 | 29,731 | 52,800 | 61,500 |
| 47770 | 46,904 | 68,400 | 78,000 |
| 83060 | 42,206 | 71,350 | 85,920 |
| 99840 | 88,428 | 132,880 | 162,380 |

### 2022-08-12

| Layer | Before | After |
| --- | ---: | ---: |
| Buy Quality decisions | 50 | 50 |
| PC target-positive members | 16 | 18 |
| AK2 authority in PC | 0 | 90 string hits |
| PS positive quantities | 2 | 17 |
| AK2 authority in PS | 0 | 146 string hits |
| Runtime BUY-like plans | 2 | 17 |
| Morning pending items | 5 | 17 |
| Submit pending state | `APPROVED` | `REVIEW_REQUIRED` |
| Submitted orders | 6 | 0 |
| BUY fills | 2 | 0 |

After pending item review:

```text
ITEM_REVIEW_REQUIRED: 7
BLOCKED_BY_BATCH_REVIEW: 10
reason: estimated amount exceeds selected_position_amount
```

Review-required one-lot items:

| Symbol | selected_position_amount | executable notional | reserved notional |
| --- | ---: | ---: | ---: |
| 24370 | 78,253 | 109,500 | 136,700 |
| 38100 | 44,516 | 68,000 | 76,000 |
| 47770 | 43,968 | 69,600 | 78,400 |
| 54010 | 23,492 | 42,710 | 50,290 |
| 70800 | 26,359 | 37,200 | 43,000 |
| 83060 | 45,831 | 72,710 | 86,350 |
| 99840 | 98,948 | 140,250 | 162,880 |

## Required Flags

```text
FIRST_BEHAVIORAL_DIFFERENCE_LAYER =
  POSITION_SIZING_MINIMUM_EXECUTABLE_ONE_LOT_ADMISSION_TO_SUBMIT_FEASIBILITY

CANDIDATE_TOP50_BEFORE_AFTER_EQUAL =
  YES_SYMBOL_ORDER_EQUAL_FOR_AUDITED_TOP10_AND_DECISION_COUNT
  ARTIFACT_HASH_DIFFERS_BY_RUN_LINEAGE

SI_DECISIONS_BEFORE_AFTER_EQUAL =
  NO_ARTIFACT_HASH_DIFFERS
  NO_EVIDENCE_SI_ZEROED_BUYS

ENTRY_DECISIONS_BEFORE_AFTER_EQUAL =
  YES_FOR_2022_08_10_ACTION_DISTRIBUTION
  2022_08_12_DIFFERS_AFTER_PRIOR_ZERO_FILL_STATE

PC_POSITIVE_BEFORE = 2022-08-10:16, 2022-08-12:16
PC_POSITIVE_AFTER  = 2022-08-10:16, 2022-08-12:18
PC_TARGETS_COLLAPSED_AFTER_AK2 = NO

AK2_AUTHORITY_MATERIALIZED = YES
AK2_AUTHORITY_COUNT =
  PC: 2022-08-10:57, 2022-08-12:90
  PS: 2022-08-10:92, 2022-08-12:146

PS_POSITIVE_BEFORE = 2022-08-10:8, 2022-08-12:2
PS_POSITIVE_AFTER  = 2022-08-10:13, 2022-08-12:17
PS_ZERO_DOMINANT_REASON_AFTER = NOT_ZERO_DOMINANT_PS_POSITIVE_INCREASED_AFTER_AK2

PRE_EXISTING_BUY_DISAPPEARANCE_REASON_DISTRIBUTION =
  batch_submit_blocked_by_item_scoped_review:
    2022-08-10: 8
    2022-08-12: 10
  estimated_amount_exceeds_selected_position_amount_new_one_lot_items:
    2022-08-10: 5
    2022-08-12: 7

FRESH_RUN_INITIAL_STATE_INTEGRITY =
  PASS_EMPTY_INITIAL_STATE_CONFIRMED

BEFORE_AFTER_RUNTIME_CONFIG_EQUIVALENT =
  YES_PROFILE_AND_SOURCE_COMMIT_EQUIVALENT

AK2_SCOPE_LEAK_CONFIRMED =
  YES_SUBMIT_FEASIBILITY_DID_NOT_CONSUME_MINIMUM_EXECUTABLE_ONE_LOT_AUTHORITY

AK2_CHANGE_DIRECTLY_CAUSED_ZERO_BUY =
  YES_VIA_NEW_REVIEW_REQUIRED_ONE_LOT_ITEMS_AND_ATOMIC_BATCH_NO_SUBMISSION

POST_AK2_ZERO_BUY_ROOT_CAUSE =
  SUBMIT_FEASIBILITY_MINIMUM_EXECUTABLE_ONE_LOT_AUTHORITY_HANDOFF_GAP
```

## Evidence

Primary evidence files:

```text
reports/phase_reports/phase30_ak3r0_post_ak2_zero_buy_fresh_regression_root_cause_audit.json
reports/phase_reports/phase30_ak3r0/before_after_zero_buy_chain_summary.json
```

Key runtime artifacts inspected:

```text
daily/<date>/strategy/buy_quality_decisions.json
daily/<date>/strategy/strategy_intelligence.json
daily/<date>/strategy/portfolio_construction.json
daily/<date>/strategy/position_sizing.json
daily/<date>/strategy/runtime_planning.json
daily/<date>/morning/planning_evidence.json
daily/<date>/submit/runtime_manifest.json
daily/<date>/execution/submitted_order_authority.json
daily/<date>/execution/historical_fill_authority.json
daily/<date>/execution/fills.json
.runtime/pending_order_plan/history/<date>/<pending_plan_id>.json
```

## Interpretation

AK2 restored the intended PC/PS admission behavior: sub-selected-position
amount opportunities can become executable one-lot BUY candidates. That
authority did not propagate to Submit feasibility, where the existing guard
still treats executable notional above `selected_position_amount` as
`REVIEW_REQUIRED`.

Because BUY submit is atomic under item-scoped review, the new review-required
one-lot items prevented even feasibility-PASS legacy BUY items from submitting.

## Implementation Authorization

```text
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AK3R0
```

## Recommended Next Task

```text
Phase30-AK3R1 - Submit Feasibility Minimum Executable One-Lot Authority Handoff Repair
```

Repair boundary for the next task:

```text
Propagate and consume canonical minimum_executable_one_lot_authority in
planning_submit_feasibility / pending promotion / submit guard so that only
authorized one-lot notional-over-selected-position cases pass, while ordinary
over-cap orders remain REVIEW_REQUIRED.
```
