# Phase15-AR Pending Lifecycle Contract / Stale Pending Handling

Date: 2026-07-10

## Final Judgment

```text
PHASE15AR_PENDING_LIFECYCLE_STALE_PENDING_HANDLING_COMPLETE
```

Phase15-AR implemented the regular Runtime path for reviewing stale active Pending and transitioning it without direct JSON edits, deletion, or overwrite.

This phase did not modify the real runtime `.runtime/pending_order_plan/pending_order_plan.json`.  All verification used temporary Runtime roots.

## Objective

Phase15-AQ detects stale active Pending as `REVIEW_REQUIRED`.  Phase15-AR adds the safe regular path to resolve that state:

```text
Pending
↓
Expired / Cancelled / Superseded / Review Required
↓
History
```

The current Pending slot is never simply deleted.

## Pending State Contract

The Runtime Pending contract now explicitly recognizes:

```text
CREATED
PENDING_REVIEW
APPROVED
REJECTED
CONSUMED
EXPIRED
CANCELLED
SUPERSEDED
REVIEW_REQUIRED
EMPTY
```

Key guarantees:

- `APPROVED` alone is not sufficient for Submit.
- `EXPIRED / CANCELLED / REJECTED / CONSUMED / SUPERSEDED / EMPTY` are terminal and Submit-blocked.
- `REVIEW_REQUIRED` is Submit-blocked until Operator review.
- `EMPTY` means there is no active Pending in the fixed current slot.

## CLI Job

Added Runtime v2 CLI job:

```text
--job pending_lifecycle
```

Added action:

```text
--pending-action review|expire|cancel
```

The normal action is:

```text
--pending-action review
```

It evaluates the active Pending, submit attempt evidence, approval expiry, target date, policy hash, and safety evidence before applying any transition.

## Automatic Transition Rules

### Auto EXPIRED

The job transitions `APPROVED` to `EXPIRED` only when:

```text
target_session_date elapsed
approval expired or stale evidence present
consumed=false
submit attempt not detected
unknown submit risk=false
```

Then it writes immutable history and replaces the current slot with an explicit `EMPTY` artifact.

### Auto REVIEW_REQUIRED

The job transitions active Pending to `REVIEW_REQUIRED` when submit evidence indicates possible unknown outcome:

```text
submit attempt detected
broker request may have been attempted
unknown outcome risk
```

In this case the current Pending slot is not released.

## History Contract

History path:

```text
.runtime/pending_order_plan/history/<target_session_date>/<pending_plan_id>.json
```

History includes:

```text
pending_plan_id
previous_state
new_state
transition_reason
transitioned_at
transitioned_by
source_pending_path
target_session_date
approval_status
approval_at
approval_expires_at
consumed
policy_version
policy_hash
safety_decision_id
submit_attempt_detected
unknown_submit_risk
submit_manifest_paths
pending_payload
```

History is immutable.  Existing history is not overwritten.

## Current Pending Slot

After terminal expiration/cancellation, the fixed slot becomes:

```json
{
  "schema_version": "runtime_v2_pending_slot_v1",
  "status": "EMPTY",
  "state": "EMPTY",
  "active_pending": false
}
```

The Pending reader now treats this slot as valid `EMPTY` instead of invalid JSON for the legacy full Pending schema.

## Data Readiness Integration

Data Readiness behavior:

- stale active `APPROVED` Pending -> `REVIEW_REQUIRED`, next action `run pending_lifecycle`
- `EXPIRED` + slot `EMPTY` -> Pending readiness `READY`
- unknown submit risk -> `REVIEW_REQUIRED`, next action `review broker/submit evidence`

## Manifest / Report / Notification

Runtime manifest now includes:

```text
pending_lifecycle_status
pending_plan_id
previous_state
new_state
transition_reason
target_session_date
approval_expires_at
consumed
submit_attempt_detected
unknown_submit_risk
submit_evidence_paths
history_path
current_pending_path
idempotent_noop
next_operator_action
```

Report summary includes:

```text
pending_lifecycle
```

Notification payload includes:

```text
pending_lifecycle_status
pending_lifecycle_reason
```

Notification remains payload-only.

## Regression Coverage

Added:

```text
tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py
```

Coverage:

- stale `APPROVED / unconsumed` Pending with no submit attempt -> `EXPIRED`
- history artifact is saved
- current Pending slot becomes `EMPTY`
- Data Readiness becomes Pending `READY` after expiration
- submit attempt / unknown outcome -> `REVIEW_REQUIRED`
- unknown outcome is not expired and slot is not released
- valid same-day `APPROVED` Pending is `NOOP`
- `EMPTY` slot is reader-valid and idempotent
- CLI manifest, report, and notification include lifecycle evidence
- repeated expiration is idempotent
- state contract marks terminal states as Submit-blocked

## Verification

```text
python3 -m pytest tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py
```

Result:

```text
9 passed
```

```text
python3 -m pytest \
  tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py \
  tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py \
  tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py \
  tests/runtime_v2/test_phase15l_submit_policy_hash_consistency_guard.py \
  tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py \
  tests/runtime_v2/test_phase15r_report_notification_reason_propagation.py \
  tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py \
  tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py
```

Result:

```text
43 passed
```

## Operator Execution After This Phase

For the actual stale Runtime Pending, the Operator should use the regular CLI job separately:

```text
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job pending_lifecycle \
  --pending-action review \
  --business-date 2026-07-10 \
  --runtime-root .runtime
```

Then review:

```text
Pending Lifecycle manifest
History artifact
Current Pending slot artifact
Data Readiness re-evaluation
```

This report does not execute that operation.

## Prohibited Actions Confirmation

Not performed:

- real Runtime Pending modification
- direct Pending JSON edit
- Pending deletion
- Current edit
- Morning / SELL Planning real operation
- Submit
- Execution
- Broker Write
- Order placement
- Notification real send
- launchd change
- stale Pending carryover
- unknown submit outcome auto-expiration

## Completion

```text
PHASE15AR_PENDING_LIFECYCLE_STALE_PENDING_HANDLING_COMPLETE
```
