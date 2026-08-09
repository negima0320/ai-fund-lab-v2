# Phase28-D3: Runtime Sell Pending Reconciliation Implementation

Task ID: `Phase28-D3`

Task Type: `IMPLEMENTATION / SHORT VALIDATION ONLY`

Status: `COMPLETE`

Primary Judgment: `PHASE28_D3_RUNTIME_SELL_PENDING_RECONCILIATION_IMPLEMENTED_SHORT_VALIDATION_PASS_FRESH_100BD_READY`

Phase28-D Restart Entry Decision: `APPROVED`

Implementation Changed: `true`

Config Changed: `false`

Schema Changed: `false`

Threshold Changed: `false`

Resume Executed: `false`

Fresh Run Executed: `false`

Long Historical Executed: `false`

## 1. Executive Summary

Phase28-D3 implemented the Phase28-D2 accepted repair: Sell Planning no longer treats an active same-symbol SELL pending item as an immediate conflict. It now classifies the existing SELL pending item against the new Sell Planning intent by same-day identity, lineage, state, intent class, quantity compatibility, and submitted/partial-fill state.

Same-intent duplicate and compatible same-day SELL pending are preserved or reconciled idempotently. True conflict, submitted/post-send-like state, partial fill, generation mismatch, stale pending, unknown identity, or incompatible quantity fail closed to `REVIEW_REQUIRED` while preserving the original active pending slot.

No fresh 100BD run, resume, or long historical execution was performed.

## 2. Scope

Implemented one Runtime/Sell Planning pending orchestration repair:

```text
existing active SELL pending
+ new Sell Planning SELL intent
-> classify
-> preserve / reconcile / fail closed
```

Out of scope and unchanged:

- Phase28-C ADD bridge
- Portfolio Construction
- Position Sizing
- Runtime Planning mapping
- PM ADD / HOLD / REDUCE / EXIT thresholds
- Safety and Data Readiness semantics
- Broker Submit semantics
- Approval Authority
- Config, schema, thresholds, model, training

## 3. Phase28-D2 Design Accepted

D3 follows Phase28-D2 Option C:

```text
Existing plan reconciliation
```

The executable authority remains:

```text
.runtime/pending_order_plan/pending_order_plan.json
```

Direct submit from PM decisions, strategy artifacts, order-plan evidence, approval artifact alone, proposed replacement evidence, or conflict evidence remains prohibited.

## 4. Pre-implementation Audit

Confirmed before implementation:

- `_pending_sell_conflict(...)` was the coarse same-symbol SELL conflict gate.
- It read `.runtime/pending_order_plan/pending_order_plan.json` directly and returned conflict by symbol only.
- `_write_no_signal_pending(...)` preserved active BUY pending only on non-review no-signal paths.
- `REVIEW_REQUIRED` / `BLOCKED` no-signal paths could write an empty pending plan.
- Existing Pending model already had side-specific fields and item lineage fields.
- Existing composition preserved BUY items via `compose_with_existing_buy_pending`.
- Submit consumes only Pending authority and was not changed.
- 76470-equivalent fixture could be built with existing Pending model and Sell Planning pipeline.

## 5. Current Defect

The defect was not fail-closed behavior itself. The defect was that same-symbol active SELL pending was treated as conflict before classification, and the review/no-signal path could overwrite the active pending slot with an empty plan.

## 6. Implementation Overview

Implemented:

- `SellPendingReconciliationResult`
- `reconcile_with_existing_sell_pending(...)`
- `active_pending_snapshot(...)`
- pending SELL classification helper functions
- pending SELL reconciliation evidence materialization
- Sell Planning lineage attachment for pending items
- no-signal preservation guard for review/block paths

Removed from the active flow:

- immediate `_pending_sell_conflict(...)` gate before quantity planning

The legacy function remains present but is no longer used by the D3 sell planning flow.

## 7. Changed Files

- `src/ai_fund_lab_v2/runtime_v2/pending/composition.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py`
- `docs/01_requirements/phase_roadmap.md`

## 8. Pending Identity Classifier

Classifier inputs include:

- `business_date`
- `target_session_date`
- normalized same-symbol comparison
- `side`
- intent class from `quantity_contract.source_decision`, `source_decision_type`, or pending item id
- `source_pm_decision_id` when present
- `accepted_generation_id` when present
- plan state and item state
- existing and new quantity

Existing artifacts are not broken when optional fields are absent. Missing identity does not permit unsafe replacement.

## 9. Same-intent Duplicate Handling

Same lineage + same intent + equivalent quantity + not submitted/partial-filled:

```text
PENDING_SELL_IDEMPOTENT_DUPLICATE_PRESERVED
```

The existing item is preserved and no duplicate item is generated.

## 10. Compatible Update Handling

Same date / symbol / side with compatible SELL lineage and equivalent quantity:

```text
PENDING_SELL_COMPATIBLE_UPDATE_MERGED
```

The implementation preserves one SELL item and carries existing BUY items through the existing composition path.

## 11. True Conflict Handling

True conflicts fail closed:

- incompatible quantity
- submitted/post-send-like state
- partial fill evidence
- generation mismatch
- stale pending
- ambiguous identity
- multiple same-symbol existing SELL items

The original pending slot is preserved and `pending_continuity_evidence.json` records the review reason.

## 12. REDUCE / EXIT Priority

Priority remains:

```text
EXIT > REDUCE > HOLD > ADD
```

Implemented behavior:

- existing REDUCE + new EXIT: replace with EXIT candidate when same-symbol compatible and not submitted
- existing EXIT + new REDUCE: preserve existing EXIT, no silent downgrade

PM quantity authority was not expanded.

## 13. Quantity Reconciliation

Quantity is not part of base identity. It is used for compatibility classification.

Equivalent quantity permits duplicate preserve or compatible merge. Incompatible quantity is:

```text
PENDING_SELL_CONFLICTING_QUANTITY_REVIEW
```

No max/min shortcut was introduced.

## 14. Pending State Handling

Replace/reconcile is allowed only for non-committed active pending. Submitted, submitting, and post-send unknown-like states are review-only. Partial fill evidence on item status also reviews.

## 15. No-signal Preservation

For `REVIEW_REQUIRED` or `BLOCKED`, `_write_no_signal_pending(...)` now checks active pending first. If an active pending plan exists for the same date/session, it records evidence and returns without writing an empty current pending plan.

Reason codes:

- `PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED`
- `PENDING_PLAN_NO_SIGNAL_DID_NOT_OVERWRITE_ACTIVE`

## 16. Generation / Hash Guard

The implementation records existing pending plan id, state, item ids, and hash in reconciliation/no-signal evidence. Generation mismatch between existing and new pending items reviews.

No large transaction framework was introduced.

## 17. Idempotency

Repeated Sell Planning with the same PM decision id and equivalent quantity preserves the existing SELL pending item instead of creating a duplicate.

## 18. BUY / SELL Independence

SELL reconciliation preserves existing BUY items through the existing composition helper. SELL review/no-signal preservation does not clear BUY. BUY logic and Submit behavior were not changed.

## 19. Observability

New evidence:

- `pending_sell_reconciliation_evidence.json`
- `no_signal_preservation_evidence.json`
- enhanced `pending_continuity_evidence.json` for review preservation paths

Evidence includes existing plan id/hash/state/item ids, classification, resolution action, quantity before/after, reason codes, review flag, resume safety, and opposite-side preservation.

## 20. Failure Behavior

Failure behavior is fail-closed:

```text
REVIEW_REQUIRED + original pending preserved
```

Submit-started or partial-fill cases are not auto-replaced.

## 21. Focused Fixtures

Added `tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py`.

Covered:

- 76470-equivalent same-day Strategy SELL + PM REDUCE compatible reconciliation
- same-lineage REDUCE duplicate preserve
- quantity conflict review with original preserve
- submitted pending review with no replacement
- review no-signal does not overwrite active pending

## 22. Unit Tests

D3 focused tests:

```text
5 passed
```

Existing pending composition tests:

```text
13 passed
```

## 23. Short Regression

Short regression command covered Sell Planning, Pending composition, Pending persistence, Submit pipeline, REDUCE/EXIT quantity, historical sell planning authority, and Phase28-C ADD fixtures.

Result:

```text
115 passed, 60 warnings
```

Warnings are pre-existing `DeprecationWarning` entries in PM producer array truth-value handling.

## 24. Phase28-C Regression

Phase28-C related strategy fixtures remained passing as part of the 115-test short regression:

- `tests/strategy/test_phase22_e_portfolio_construction.py`
- `tests/strategy/test_phase22_j_position_sizing.py`

Phase28-C changed files were not edited.

## 25. Architecture Conformance

Conforms:

- Pending executable authority unchanged
- Submit Guard unchanged
- no direct PM/Strategy submit path introduced
- Safety/Data Readiness unchanged
- PM quantity authority not expanded
- Performance logic untouched
- Historical-only branch not introduced

## 26. Known Limitations

The D3 repair is intentionally minimal. It does not introduce a full canonical pending composer, multi-slot executable authority, or broad lifecycle transaction framework.

## 27. Open Gaps

Non-blocking future gaps:

- Full first-class Pending reconciliation service remains a future design option.
- Remaining-quantity reconciliation after confirmed partial fills still requires execution authority integration beyond D3.

## 28. Fresh 100BD Contract

Do not resume:

```text
runtime-test-historical-smoke-20260805T124145808243Z
```

After this D3 short validation, Phase28-D requires a fresh 100BD historical runtime run owned by the user/operator.

## 29. Final Judgment

```text
PHASE28_D3_RUNTIME_SELL_PENDING_RECONCILIATION_IMPLEMENTED_SHORT_VALIDATION_PASS_FRESH_100BD_READY
```

## 30. Phase28-D Restart Entry Decision

```text
APPROVED
```
