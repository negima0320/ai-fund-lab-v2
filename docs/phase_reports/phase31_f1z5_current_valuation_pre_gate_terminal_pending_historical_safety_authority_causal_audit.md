# Phase31-F1Z5 — Current Valuation Pre-Gate Terminal Pending / Historical Safety Authority Causal Audit

## Primary Judgment

`PHASE31_F1Z5_COMMON_PENDING_SCOPE_CONSUMER_GAP_CAUSES_BOTH_PRE_GATE_BLOCKERS`

The two observed 2022-12-09 `current_valuation_refresh` pre-producer blockers are not independent.

Both are downstream of the same consumer-semantics gap:

```text
F1Z2 introduced item.state = NOT_EXECUTABLE for execution-authority-unavailable terminal items.
Pending review-scope / Data Readiness / Historical Safety consumers do not yet classify NOT_EXECUTABLE as a terminal residual item.
```

The actual pre-gate failure chain is:

```text
active Pending state = REVIEW_REQUIRED
items:
  75590 BUY  CONSUMED
  34940 SELL NOT_EXECUTABLE / EXECUTION_AUTHORITY_UNAVAILABLE
  56100 SELL CONSUMED

PendingReviewScopeAuthority does not include NOT_EXECUTABLE in terminal_item_ids
review_scope is empty and no reviewed BUY authority exists
pending_scope_current_valuation_adapter_ready = false
pending_allows_daily_neutral_safety = false

Data Readiness:
  pending_review_required
  historical_safety_temporal_authority_missing

current_valuation_refresh stops at runtime_data_readiness_gate before producer
```

This is consumer overblocking after F1Z2 terminalization, not a valuation price/basis producer failure.

## Target

```text
TARGET_RUN_ID = runtime-test-historical-extended-smoke-20260821T050423121340Z
TARGET_BOUNDARY = 2022-12-09:current_valuation_refresh
TASK_TYPE = READ_ONLY_CAUSAL_AUDIT_AND_REPAIR_DESIGN
```

No implementation, fresh-run, resume, replay, long Historical, Strategy mutation, Runtime mutation, fixture mutation, or canonical runtime artifact mutation was executed.

## Evidence Read

Minimum authority read:

- `docs/phase_reports/phase31_f1z4_2022_12_09_current_valuation_refresh_halt_root_cause_audit.md`
- `docs/phase_reports/phase31_f1z3_f1z2_production_acceptance_clean_100bd_resume_readiness.md`
- `docs/phase_reports/phase31_f1z2_execution_authority_unavailable_item_terminal_continuation_implementation.md`
- `docs/phase_reports/phase31_f1z1_execution_authority_unavailable_item_terminal_continuation_design.md`
- `src/ai_fund_lab_v2/runtime_v2/data_readiness.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/review_scope_authority.py`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/safety_temporal_authority.py`
- `tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py`
- `.runtime/pending_order_plan/pending_order_plan.json`
- `.runtime/persistent_ledger/state.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260821T050423121340Z/daily/2022-12-09/data_readiness/data_readiness.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260821T050423121340Z/daily/2022-12-09/current_valuation_refresh/runtime_manifest.json`

## F1Z5-1 — Pending State Decomposition

The exact active Pending consumed by the 2022-12-09 `current_valuation` Data Readiness gate is:

```text
path = .runtime/pending_order_plan/pending_order_plan.json
pending_plan_id = pending-strategy-plan-historical-2022-12-09-055b6551b8aef624
state = REVIEW_REQUIRED
environment = historical
plan_created_date = 2022-12-09
target_session_date = 2022-12-09
intended_submit_date = 2022-12-09
review_scope = ""
sell_continuation_allowed = false
approved_item_ids = [
  strategy-bbb2db1df2402f341abf,
  strategy-e32622aee210e99906b1
]
review_required_buy_item_ids = []
review_required_sell_item_ids = []
consume.consumed = false
```

Residual item map:

| Symbol | Side | Quantity | State | Classification | Same-day retryable |
| --- | --- | ---: | --- | --- | --- |
| `75590` | BUY | 100 | `CONSUMED` | submitted/consumed | no |
| `34940` | SELL | 100 | `NOT_EXECUTABLE` | terminal execution authority unavailable | no |
| `56100` | SELL | 100 | `CONSUMED` | submitted/consumed | no |

`76920` is not present in the active 2022-12-09 Pending. Its genuine 2022-12-08 BUY item-scoped review was preserved on the prior day and was not carried into this active Pending.

```text
PENDING_PLAN_STATE = REVIEW_REQUIRED
PENDING_RETRYABLE_ITEM_COUNT = 0
PENDING_TERMINAL_NOT_EXECUTABLE_COUNT = 1
PENDING_TRUE_REVIEW_REQUIRED_COUNT = 0
```

## F1Z5-2 — 34940 Terminal Semantics

Actual active Pending item:

```text
symbol = 34940
side = SELL
quantity = 100
state = NOT_EXECUTABLE
approved = false
batch_submit_status = NOT_EXECUTABLE
item_review_reason = EXECUTION_AUTHORITY_UNAVAILABLE
feasibility_status = NOT_EXECUTABLE_EXECUTION_AUTHORITY_UNAVAILABLE
```

F1Z2 design requires:

```text
retry_eligible_same_day = false
next_day_re_evaluation_required = true
no order / no fill / no cash mutation / no position mutation
```

The active Pending item persists the canonical terminal state and reason, but Data Readiness does not currently distinguish this terminal residual from a generic plan-level `REVIEW_REQUIRED`.

Exact consumer predicates:

- `data_readiness._pending_readiness_payload()` branches on `state == "REVIEW_REQUIRED"`.
- It can return READY for:
  - failed-attempt retry ineligible,
  - sell continuation adapter,
  - `current_valuation` post-submit residual BUY review adapter.
- The current valuation adapter calls `pending_scope_current_valuation_adapter_ready()`.
- That adapter relies on `pending_scope_allows_current_valuation_residual()`.
- `PendingReviewScopeAuthority` currently marks terminal items only when item state is one of:

```text
CONSUMED
EXPIRED
CANCELLED
SUPERSEDED
```

`NOT_EXECUTABLE` is not included. Therefore the actual `34940` terminal item is not represented as terminal scope evidence.

```text
DATA_READINESS_RECOGNIZES_TERMINAL_NOT_EXECUTABLE = NO
```

## F1Z5-3 — 76920 Review Semantics

`76920` is a genuine item-scoped BUY review:

```text
corporate_action_event_not_resolved
```

Existing current valuation pre-gate tests already encode that post-submit residual BUY review can be non-blocking for current valuation when it is item-scoped and all executable items are consumed:

```text
test_phase30_ak9r6_post_submit_residual_buy_review_allows_current_valuation_readiness
test_phase30_ak9r6_isolated_cli_reaches_current_valuation_producer_with_residual_buy_review
```

Those tests require:

```text
review_scope = BUY_ITEM_SCOPED_REVIEW
review_required_buy_item_ids are present
reviewed BUY items remain REVIEW_REQUIRED
approved executable items are CONSUMED
no reviewed SELL items
no batch_blocked authority
```

Thus, a correctly scoped residual BUY review is not supposed to block valuation of unrelated already-held positions. It remains deferred and must not submit.

For the actual 2022-12-09 boundary, `76920` is no longer in the active Pending, so it is not an actual blocker.

```text
76920_CURRENT_VALUATION_BLOCKING_AUTHORITY = NON_BLOCKING
```

## F1Z5-4 — Pending Plan-Level vs Item-Level Semantics

The actual consumer behavior is plan-level overblocking for this F1Z2 shape.

`PendingReviewScopeAuthority` on actual Pending produced:

```text
lifecycle_state = REVIEW_REQUIRED
review_scope = ""
reviewed_buy_item_ids = []
reviewed_sell_item_ids = []
terminal_item_ids = [
  strategy-bbb2db1df2402f341abf,
  strategy-e32622aee210e99906b1
]
batch_blocked = false
pending_scope_allows_current_valuation_residual = false
pending_scope_current_valuation_adapter_ready = false
pending_allows_daily_neutral_safety = false
```

Note that `terminal_item_ids` contains only the two `CONSUMED` items. It excludes the F1Z2 terminal `34940 NOT_EXECUTABLE`.

Data Readiness then falls through to:

```text
status = REVIEW_REQUIRED
reason = pending_review_required
```

This violates the F1Z1/F1Z2 terminal continuation architecture for a known no-side-effect non-executable item, but only in downstream consumers. F1Z2 Submit terminalization itself worked.

```text
PENDING_PLAN_LEVEL_OVERBLOCKING = YES
```

## F1Z5-5 — Expected Historical Safety Authority

Expected authority:

```text
producer = ai_fund_lab_v2.runtime_v2.historical_support.safety_temporal_authority
contract_id = historical_safety_temporal_authority
contract_version = phase30_ak9r28_v1
expected_artifact = Data Readiness safety component embedded in data_readiness.json / runtime_manifest.json
expected_business_date = 2022-12-09
expected_temporal_binding = business_date == pending target_session_date == safety_business_date == 2022-12-09
expected_consumer = ai_fund_lab_v2.runtime_v2.data_readiness._safety_readiness_payload
expected_historical_neutral_semantics = no broker write, no external delivery, historical_simulated broker environment, runtime-test run/profile/evidence root bound, pending lifecycle compatible
```

There is no requirement that `.runtime/runtime_state/safety/latest_safety_decision.json` exist for this Historical-neutral path. In Historical mode, Data Readiness may synthesize/resolve neutral safety authority when the pending lifecycle is compatible and temporal bindings match.

```text
EXPECTED_HISTORICAL_SAFETY_AUTHORITY =
historical_safety_temporal_authority / HISTORICAL_DAILY_NEUTRAL over data_readiness_historical_temporal_authority, business-date bound to 2022-12-09
```

## F1Z5-6 — Missing Safety Evidence Root Cause

`.runtime/runtime_state/safety/latest_safety_decision.json` does not exist. That alone is not fatal in Historical, because earlier 2022-12-09 jobs resolved historical-neutral authority without it.

For the actual current valuation scope:

```text
evaluate_historical_pending_safety_authority.status = REVIEW_REQUIRED
evaluate_historical_pending_safety_authority.reason = historical_pending_safety_authority_mismatch
mismatched_fields = [pending_lifecycle_state]
pending_scope_compatible = false

evaluate_historical_daily_neutral_safety_authority.status = REVIEW_REQUIRED
reason = historical_daily_neutral_safety_authority_not_available
mismatched_fields = [pending_lifecycle_state]
pending_scope_compatible = false
```

Data Readiness then reports:

```text
safety_status = REVIEW_REQUIRED
safety_reason = historical_safety_temporal_authority_missing
missing_evidence = [historical_safety_temporal_authority]
stale_artifacts = [safety]
source_paths.safety_decision = .runtime/runtime_state/safety/latest_safety_decision.json
```

The first safety failure is not that a compatible authority artifact was produced under the wrong path. The first failure is that the pending lifecycle state is not compatible under current consumer semantics.

```text
SAFETY_AUTHORITY_ARTIFACT_EXISTS = NO
SAFETY_AUTHORITY_TEMPORAL_BINDING = FAIL
SAFETY_AUTHORITY_CONSUMER_RESOLUTION = FAIL
FIRST_SAFETY_AUTHORITY_FAILURE = pending_lifecycle_state not compatible because F1Z2 NOT_EXECUTABLE terminal item is not recognized by pending review-scope / current valuation adapters
```

## F1Z5-7 — Compare Earlier 12/09 Jobs

Earlier 2022-12-09 jobs had historical-neutral safety ready:

| Job | Data readiness scope | Pending slot | Safety result |
| --- | --- | --- | --- |
| `data_readiness` | `morning` | `EMPTY` | READY / `historical_neutral_no_event_safety_ready` |
| `morning` | `morning` | `EMPTY` | READY / `historical_neutral_no_event_safety_ready` |
| `sell_planning` | `sell_planning` | `APPROVED` | READY / `historical_neutral_no_event_safety_ready` |
| `submit` | `submit` | `APPROVED` | READY / `historical_neutral_no_event_safety_ready` |
| `execution` | no pre-gate Data Readiness summary | safety file missing in manifest only | not the stopping gate |
| `current_valuation_refresh` | `current_valuation` | `REVIEW_REQUIRED` | REVIEW_REQUIRED / `historical_safety_temporal_authority_missing` |

The delta is the post-submit Pending shape:

```text
before submit/execution = APPROVED plan, compatible
after submit/execution = REVIEW_REQUIRED plan with consumed executable items plus terminal NOT_EXECUTABLE item
```

The same historical-neutral mechanism cannot resolve because current consumers only recognize the older post-submit residual BUY review shape, not the F1Z2 terminal NOT_EXECUTABLE residual shape.

```text
EARLIER_1209_SAFETY_READY = YES
CURRENT_VALUATION_SAFETY_DELTA = active Pending changed to REVIEW_REQUIRED with NOT_EXECUTABLE residual; pending_scope compatibility becomes false
```

## F1Z5-8 — Causality Between Pending and Safety Failure

The causal relation is:

```text
NOT_EXECUTABLE terminal residual not recognized
-> pending current valuation adapter returns false
-> pending readiness returns pending_review_required
-> historical daily neutral safety says pending_lifecycle_state mismatch
-> historical_safety_temporal_authority_missing
```

```text
BLOCKER_CAUSAL_RELATION = COMMON_UPSTREAM_CAUSE
```

The common upstream cause is consumer semantics not updated for the F1Z2 terminal item lifecycle.

## F1Z5-9 — Current Valuation Independence

Existing architecture supports current valuation independence from unrelated residual BUY review only when review scope evidence is item-scoped and executable items are consumed. F1Z1/F1Z2 extends this principle to known terminal non-executable items:

```text
Known no-order/no-fill/no-mutation terminal item
should not prevent valuation of already-held positions,
provided Pending/Ledger identity is unambiguous and fail-closed cases remain blocked.
```

The current Data Readiness consumer needs item-level scope, not only plan-level `REVIEW_REQUIRED`.

```text
CURRENT_VALUATION_PENDING_INDEPENDENCE = REQUIRED
```

## F1Z5-10 — 34940 Latent Valuation Problem

This is separate from the pre-gate defect.

Observed:

```text
34940 current position quantity = 100
quantity_basis = ADJUSTED
current_price = 188.0
valuation_quote_status = AUTHORIZED_STALE_VALUATION
valuation_as_of = 2022-12-08
source_market_date = 2022-12-07
stale_accounting_valuation_not_fresh_market_signal = true
stale_reason = listed_held_position_no_valid_close_ca_clear
stale_authority = pit_listed_raw_no_valid_close_corporate_event_authority
corporate_action_ambiguity_status = CLEAR
```

2022-12-09 market evidence:

```text
raw OHLCV row exists for 34940 with null O/H/L/C and null AdjO/AdjH/AdjL/AdjC
normalized OHLCV row absent for 34940
```

The existing current valuation contract can safely handle this family only if the current valuation producer produces explicit `AUTHORITATIVELY_LEGITIMATE_STALE_VALUATION` / `AUTHORIZED_STALE_VALUATION` evidence for 2022-12-09, including:

- same-day listed-issues evidence,
- raw row with no valid close evidence,
- normalized absence evidence,
- corporate-action ambiguity `CLEAR`,
- stable symbol identity,
- prior authoritative current valuation,
- retained valuation price provenance,
- matching `quantity_basis` and `valuation_price_basis`,
- `stale_authority`,
- `stale_reason`,
- stale accounting marker.

Because current valuation did not execute, the canonical 2022-12-09 current valuation stale classification is not produced yet. Strategy-side evidence suggests the same stale family is likely available, but it is not a substitute for the current valuation producer artifact.

```text
34940_STALE_VALUATION_ELIGIBILITY = UNRESOLVED
```

## F1Z5-11 — Repair Decomposition

Required work should be separated:

```text
PENDING_REPAIR_REQUIRED = YES
SAFETY_AUTHORITY_REPAIR_REQUIRED = YES
VALUATION_PRICE_REPAIR_REQUIRED = DESIGN_REQUIRED
```

Recommended repair decomposition:

1. Pending consumer repair:
   - Teach `PendingReviewScopeAuthority` / current valuation adapter that `NOT_EXECUTABLE` with `feasibility_status = NOT_EXECUTABLE_EXECUTION_AUTHORITY_UNAVAILABLE` and no side effect is terminal.
   - Keep unknown, retryable, approved, malformed, and sell review states fail-closed.

2. Historical Safety authority propagation repair:
   - Reuse the same updated pending compatibility in `historical_safety_temporal_authority`.
   - Do not globally ignore missing safety decisions.
   - Continue requiring business-date, run-id, profile-id, evidence-root, broker-write, and external-delivery bindings.

3. Valuation stale-price design / validation:
   - After pre-gate can pass, validate whether current valuation producer emits canonical authorized stale valuation for 34940 on 2022-12-09.
   - Do not assume Strategy-side position_sizing evidence is sufficient for the current valuation apply authority.

Do not combine item terminal pending repair with stale-price valuation policy unless the next actual artifact proves they are coupled.

## F1Z5-12 — Safety Boundaries

Any future repair must preserve fail-closed behavior for:

- unknown Pending side effect,
- retryable unresolved executable order,
- approved item not consumed/submitted,
- Pending/Ledger contradiction,
- missing/ambiguous Safety authority after pending compatibility check,
- future-dated Safety evidence,
- run-id/profile/evidence-root mismatch,
- broker-write or external-delivery mismatch,
- ambiguous valuation price authority,
- price/quantity basis mismatch,
- unknown position state,
- reviewed SELL item,
- malformed review scope,
- true batch cash failure.

```text
FAIL_CLOSED_SAFETY_BOUNDARIES_PRESERVED = YES
```

## Performance Evidence

`current_valuation_refresh` did not execute/PASS for 2022-12-09.

```text
PERFORMANCE_EVIDENCE_VALID_THROUGH = 2022-12-08
```

Do not authorize 2022-12-09 performance evidence until current valuation passes.

## Required Output

```text
PRIMARY_JUDGMENT = PHASE31_F1Z5_COMMON_PENDING_SCOPE_CONSUMER_GAP_CAUSES_BOTH_PRE_GATE_BLOCKERS

PENDING_PLAN_STATE = REVIEW_REQUIRED

PENDING_RESIDUAL_ITEM_MAP = 75590:BUY:CONSUMED; 34940:SELL:NOT_EXECUTABLE:EXECUTION_AUTHORITY_UNAVAILABLE; 56100:SELL:CONSUMED; 76920:NOT_IN_ACTIVE_2022_12_09_PENDING

PENDING_RETRYABLE_ITEM_COUNT = 0

PENDING_TERMINAL_NOT_EXECUTABLE_COUNT = 1

PENDING_TRUE_REVIEW_REQUIRED_COUNT = 0

DATA_READINESS_RECOGNIZES_TERMINAL_NOT_EXECUTABLE = NO

76920_CURRENT_VALUATION_BLOCKING_AUTHORITY = NON_BLOCKING

PENDING_PLAN_LEVEL_OVERBLOCKING = YES

EXPECTED_HISTORICAL_SAFETY_AUTHORITY = historical_safety_temporal_authority / HISTORICAL_DAILY_NEUTRAL over data_readiness_historical_temporal_authority, business-date bound to 2022-12-09

SAFETY_AUTHORITY_ARTIFACT_EXISTS = NO

SAFETY_AUTHORITY_TEMPORAL_BINDING = FAIL

SAFETY_AUTHORITY_CONSUMER_RESOLUTION = FAIL

FIRST_SAFETY_AUTHORITY_FAILURE = pending_lifecycle_state mismatch caused by unrecognized F1Z2 NOT_EXECUTABLE terminal residual

EARLIER_1209_SAFETY_READY = YES

CURRENT_VALUATION_SAFETY_DELTA = current_valuation sees post-submit REVIEW_REQUIRED Pending containing consumed executable items plus unrecognized NOT_EXECUTABLE 34940 residual

BLOCKER_CAUSAL_RELATION = COMMON_UPSTREAM_CAUSE

CURRENT_VALUATION_PENDING_INDEPENDENCE = REQUIRED

34940_STALE_VALUATION_ELIGIBILITY = UNRESOLVED

PENDING_REPAIR_REQUIRED = YES

SAFETY_AUTHORITY_REPAIR_REQUIRED = YES

VALUATION_PRICE_REPAIR_REQUIRED = DESIGN_REQUIRED

FAIL_CLOSED_SAFETY_BOUNDARIES_PRESERVED = YES

PERFORMANCE_EVIDENCE_VALID_THROUGH = 2022-12-08

IMPLEMENTATION_CHANGED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

GIT_DIFF_CHECK = PASS

NEXT_TASK_RECOMMENDATION = Implement a focused Pending review-scope/current-valuation adapter repair for F1Z2 terminal NOT_EXECUTABLE residual items, share that compatibility with Historical Safety temporal authority, preserve all fail-closed boundaries, then run focused unit tests before any operator resume. Treat 34940 2022-12-09 stale valuation as a separate follow-up validation/design gate after pre-gate repair.
```
