# Phase29-L20C - Historical Corporate Action Quarantine Pending Lifecycle Root Cause Audit

Task ID: Phase29-L20C

Mode:

```text
READ_ONLY ROOT CAUSE AUDIT
NO SOURCE IMPLEMENTATION CHANGE
NO CURRENT HALTED RUN MUTATION
NO RESUME / FRESH-RUN / RUN / REPAIR / PENDING_LIFECYCLE COMMAND
NO LONG HISTORICAL EXECUTION
```

## Primary Judgment

```text
PHASE29_L20C_HISTORICAL_CA_QUARANTINE_PENDING_LIFECYCLE_GAP_CONFIRMED_L20B_CORRECT_BUT_PENDING_TERMINALIZATION_REPAIR_REQUIRED
```

The current 2022-09-29 `data_readiness` HALT is caused by the exact 2022-09-28
Corporate Action quarantined Pending item remaining in the active Pending slot
as stale `APPROVED` / unconsumed evidence.

L20B succeeded for the previous Execution halt: 2022-09-28 Execution consumed
the strict Historical quarantine no-submitted-orders authority and completed
`NO_ACTION` without orderlist, fills, Ledger mutation, or Current mutation.
The new halt is a downstream Pending lifecycle gap, not proof that L20B failed.

## Direct HALT Cause

```text
run_id: runtime-test-historical-smoke-20260811T074704995096Z
business_date: 2022-09-29
job: data_readiness
runtime_cli_exit_code: 20
runner_exit_code: 30
overall_status: REVIEW_REQUIRED
direct_blocker: stale_approved_pending_exists
safety_blocker: historical_safety_temporal_authority_missing
next_operator_action: run pending_lifecycle
```

Evidence:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T074704995096Z/daily/2022-09-29/data_readiness/data_readiness.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T074704995096Z/run_state.json
```

## Pending Identity

The 2022-09-29 stale Pending is the same 2022-09-28 quarantined Corporate
Action item.

```text
pending_item_id: strategy-684afbc85b0459b42a67
symbol: 76920
side: BUY
quantity: 2000
producer business date: 2022-09-28
target_session_date: 2022-09-28
safety_decision_id: historical-neutral-safety:2022-09-28
approval status: APPROVED
pending lifecycle state: APPROVED
consumed: false
terminal: false
retry eligibility: NOT_CLASSIFIED_INELIGIBLE
source order plan id: strategy-plan-historical-2022-09-28-3722aefe6e929259
source order plan path: .runtime/runtime_state/strategy_planning/2022-09-28/order_plan.json
source planning id: rp-2022-09-28-76920-buy_new-030e9219dc314716
```

Evidence:

```text
.runtime/pending_order_plan/pending_order_plan.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T074704995096Z/daily/2022-09-28/morning/pending_generation_evidence.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T074704995096Z/daily/2022-09-28/submit/runtime_manifest.json
reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T074704995096Z/daily/2022-09-28/submit/corporate_action_symbol_quarantine_continuation.json
```

## Lifecycle Trace

```text
2022-09-28 morning
  Pending generated as APPROVED for 76920 BUY 2000.
  Pending item id strategy-684afbc85b0459b42a67.
  Safety context bound to historical-neutral-safety:2022-09-28.

2022-09-28 submit
  Pending slot status APPROVED.
  pending_item_count = 1.
  submitted_count = 0.
  blocked_count = 1.
  final_state = REVIEW_REQUIRED.
  Submit item status = REVIEW_REQUIRED / NOT_SUBMITTED-equivalent.
  violated_policy = historical_corporate_action_symbol_quarantine.
  Corporate Action quarantine artifact status = COMPLETED_WITH_SYMBOL_QUARANTINE.

2022-09-28 execution
  L20B authority accepted: historical_corporate_action_quarantine_no_submitted_orders.
  execution_action = NO_ACTION.
  orderlist_required = false.
  submitted_order_count = 0.
  fill_count = 0.
  Ledger append counts = 0.
  Current apply = NOT_REQUIRED.
  pending_terminalization_status = ALREADY_TERMINAL.
  pending_consumed = false.
  pending_mutated = false.

2022-09-29 data_readiness
  Pending slot still points to 2022-09-28 active APPROVED Pending.
  Data Readiness reports stale_approved_pending_exists.
  Historical pending safety authority expects 2022-09-29 but Pending safety context is 2022-09-28.
  Safety reports historical_pending_safety_authority_mismatch and historical_safety_temporal_authority_missing.
  Runtime fails closed with REVIEW_REQUIRED.
```

## Pending Terminalization Contract

Existing Pending vocabulary:

```text
CREATED
PENDING_REVIEW
PENDING_APPROVAL
APPROVED
REJECTED
SUBMITTING
SUBMITTED
CONSUMED
EXPIRED
CANCELLED
SUPERSEDED
BLOCKED
REVIEW_REQUIRED
POST_SEND_UNKNOWN
EMPTY
```

Existing terminal states:

```text
CONSUMED
EXPIRED
CANCELLED
REJECTED
SUPERSEDED
EMPTY
```

For a Historical Corporate Action quarantined item that is intentionally
`NOT_SUBMITTED`, has no broker submit attempt, and must not retry as the same
stale order on the next day, the closest existing formal terminal outcome is:

```text
APPROVED -> EXPIRED
then current slot -> EMPTY
```

This matches the existing stale Pending lifecycle contract: stale
`APPROVED / unconsumed` Pending with no submit attempt transitions to
`EXPIRED`, writes history, and releases the active slot as `EMPTY`.

Actual state:

```text
APPROVED
active_pending = true
consumed = false
target_session_date = 2022-09-28
```

Expected terminal/non-retryable state before the 2022-09-29 morning gate:

```text
EXPIRED history + EMPTY current slot
```

## Terminalization Authority Owner

The correct owner is the Pending lifecycle component, not Strategy, Safety, or
Data Readiness.

Architecture evidence:

```text
src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py
src/ai_fund_lab_v2/runtime_v2/pending/lifecycle.py
docs/phase_reports/phase15_ar_pending_lifecycle_stale_pending_handling.md
```

Submit owns broker-boundary blocking and Corporate Action fail-closed
classification. Execution owns no-submitted-orders/no-fill/no-ledger behavior.
Data Readiness owns fail-closed detection of stale or temporally mismatched
Pending. The Pending lifecycle manager owns transition from stale active
`APPROVED` to terminal `EXPIRED` plus `EMPTY` slot materialization.

## L20B Relationship

```text
L20B classification: correct but incomplete downstream lifecycle
```

L20B correctly repaired:

```text
Submit scoped quarantine completion
-> Historical-only no-submitted-orders authority
-> Execution NO_ACTION
```

L20B did not repair:

```text
Corporate Action quarantined Pending
-> terminal/non-retryable Pending lifecycle outcome
-> next-day EMPTY slot
```

The L20B `ALREADY_TERMINAL` wording is semantically incorrect for this
quarantine-only active Pending case. Execution evidence simultaneously records:

```text
pending_item_count = 1
pending_classification = VALID
pending_consumed = false
pending_mutated = false
```

The Pending slot proves it was not terminal. Therefore this is:

```text
A. Incorrect terminalization classification
C. Pending lifecycle producer/propagation defect
```

It is not a Data Readiness defect and not an L19 Strategy defect.

## Safety Causality

Data Readiness and Historical Safety behavior are correct fail-closed downstream
reactions.

2022-09-29 correctly refuses to reuse a 2022-09-28 active `APPROVED` Pending
safety context:

```text
pending.reason = stale_approved_pending_exists
safety.pending_safety_authority.reason = historical_pending_safety_authority_mismatch
safety.reason = historical_safety_temporal_authority_missing
final_safety_status = REVIEW_REQUIRED
```

Safety must not be changed to accept stale `APPROVED` Pending globally.

## Strategy Causality

```text
L19 causality = UNRELATED
```

The halted item is a Strategy-produced 2022-09-28 `BUY_NEW` / `BUY` Pending, but
the 2022-09-29 failure occurs after Submit quarantine and Execution continuation.
No evidence ties the halt to L19 lot-floor residual reallocation, ADD, BUY_ADD,
SELL, REDUCE, EXIT, Portfolio Construction, or Position Sizing semantics.

## BUY / SELL Behavior

The lifecycle gap is side-symmetric.

L20B tests cover quarantine-only BUY and quarantine-only SELL Execution
continuation. Both produce no-submitted-orders `NO_ACTION` and neither mutates
Pending. Therefore either side can carry forward as stale `APPROVED` unless a
Pending lifecycle transition runs.

Existing L9/L11 evidence also includes real SELL quarantine cases. No evidence
supports treating this as BUY-only.

## Mixed Case

Expected lifecycle for mixed dates:

```text
Symbol A quarantined by Corporate Action:
  A remains REVIEW_REQUIRED / QUARANTINED / NOT_SUBMITTED.
  A must become terminal/non-retryable, likely EXPIRED + history, without
  being silently retried next day.

Symbol B actually submitted/executed:
  B follows normal submit/execution/ledger/current lifecycle.
  B's Pending lifecycle must not be invalidated by A.
```

Current architecture supports separation at Submit classification and L20B
Execution authority only when `submitted_count == 0`. Mixed submitted-count
cases are deliberately not converted to Execution NO_ACTION and still require
normal orderlist evidence.

The open gap is item-scoped Pending terminalization in mixed plans. A repair
must not terminalize an entire mixed Pending plan incorrectly if executable
items still require normal lifecycle handling.

## Retry Semantics

A 2022-09-28 quarantined Pending must not silently retry as a 2022-09-29 order.

Allowed distinctions:

```text
same stale order retry: not allowed without explicit authority
next-day new Strategy decision: allowed only as a fresh 2022-09-29 decision
next-day same symbol but fresh order: still subject to quarantine registry and normal guards
quarantine registry: may block the unresolved symbol again
Human Review resolution: future authority, not automatic in Historical continuation
```

The current 9/29 Data Readiness correctly treats the old order as stale rather
than adopting it into the new day.

## Production Safety Impact

Production and Demo semantics must remain unchanged:

```text
Unresolved Corporate Action -> REVIEW_REQUIRED -> fail-closed
```

Any repair should stay strictly in Historical Runtime Test continuation
infrastructure or regular Pending lifecycle terminalization. It must not
automatically approve, submit, adjust, or silently terminalize unresolved
Corporate Action orders in Production/Demo in a way that bypasses Human Review.

## Regression Assessment

```text
Regression confirmed: NOT_PROVEN
Prior partial implementation: YES
Missing lifecycle propagation gap: YES
Duplicate authority: NO
```

Evidence:

```text
Phase29-L9 implemented symbol-scoped Historical CA quarantine and registry.
Phase29-L11 repaired real-payload classification.
Phase29-L20B repaired Execution consumption of quarantine no-submitted-orders authority.
Phase15-AR already implemented generic stale Pending EXPIRED + EMPTY lifecycle.
No evidence was found that CA quarantine-specific Pending terminalization was
previously implemented and then removed.
```

Therefore the safest classification is a new integration gap exposed by L20B,
not a proven regression.

## Existing Test Coverage

Covered:

```text
Generic stale APPROVED Pending -> REVIEW_REQUIRED in Data Readiness
Generic stale APPROVED Pending -> EXPIRED + EMPTY via pending_lifecycle
Data Readiness READY after generic expiration
Unknown submit risk -> REVIEW_REQUIRED and slot retained
Historical stale active Pending safety mismatch remains REVIEW_REQUIRED
Historical no-action EMPTY terminal safety authority
CA quarantine classifier persists symbol scope
CA registry blocks same symbol but not unrelated symbols
L20B quarantine-only BUY Execution NO_ACTION
L20B quarantine-only SELL Execution NO_ACTION
L20B mixed quarantine + submitted order keeps orderlist-required path
L20B generic REVIEW_REQUIRED does not become NO_ACTION
```

Missing:

```text
CA quarantine-only BUY Pending terminalization
CA quarantine-only SELL Pending terminalization
2022-09-28 quarantine -> 2022-09-29 Data Readiness READY after terminalization
CA quarantine item does not retry as stale next-day Pending
Mixed quarantine + executable order item-scoped terminalization
Next-day fresh Strategy order for previously quarantined symbol remains governed by registry
CA quarantine registry + Pending lifecycle interaction
CA quarantine-specific retry eligibility evidence
Execution pending_terminalization_status does not report ALREADY_TERMINAL for active APPROVED Pending
Runtime Test runner progression across quarantine terminalization
```

## Repair Required

```text
YES
```

Root Cause:

```text
HISTORICAL_CA_QUARANTINE_PENDING_NOT_TERMINALIZED_AND_CARRIED_AS_STALE_APPROVED_PENDING
```

## Recommended Repair Scope

Recommended next task:

```text
Phase29-L20D Historical Corporate Action Quarantine Pending Terminalization Repair
```

Minimum scope:

```text
1. Preserve Production/Demo Corporate Action fail-closed behavior.
2. Preserve generic stale APPROVED Pending fail-closed behavior.
3. Add strict Historical-only CA quarantine Pending lifecycle terminalization.
4. Prefer existing terminal vocabulary: EXPIRED + EMPTY slot, unless deeper architecture review proves another existing terminal state is more appropriate.
5. Ensure quarantine-only BUY and SELL both terminalize.
6. Ensure mixed quarantine + executable plans terminalize only quarantined/non-submitted items or otherwise preserve executable item lifecycle correctly.
7. Correct or narrow Execution `pending_terminalization_status=ALREADY_TERMINAL` for active APPROVED quarantine cases.
8. Add next-day Data Readiness regression proving no stale APPROVED carryover after strict quarantine terminalization.
```

Explicitly prohibited repair shape:

```text
Data Readiness ignores all stale APPROVED Pending in Historical
Safety accepts mismatched stale Pending temporal authority
Corporate Action REVIEW_REQUIRED is downgraded to PASS
Production/Demo unresolved Corporate Action auto-continues
```

## Current Run Mutation

```text
NO
```

Only read-only evidence inspection was performed. The current halted run
`runtime-test-historical-smoke-20260811T074704995096Z` was not resumed,
repaired, reset, abandoned, rolled back, or otherwise mutated.

## Historical Executed

```text
NO
```

No Runtime Test `fresh-run`, `resume`, `run`, or `pending_lifecycle` command was
executed by Codex in L20C.

## Recommended Next Task

```text
Phase29-L20D Historical Corporate Action Quarantine Pending Terminalization Repair
```

The L20D repair should start from existing Pending lifecycle contracts and add
the smallest strict Historical quarantine bridge needed to make the quarantined
Pending terminal/non-retryable before next-day Data Readiness.
