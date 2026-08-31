# Phase32-AZ - Post-Partial-Execution Current Valuation Safety Authority READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260831T003243720082Z`
- Current halt: `2023-10-11:current_valuation_refresh`
- Exit code: `20`
- Canonical reason: `historical_safety_temporal_authority_missing`
- Audit mode: READ-ONLY for source/config/runtime state. No rewind, regeneration, recovery, replay, resume, fresh-run, Pending edit, runtime-state edit, or code change was performed.

Phase32-AY had already executed the same-run canonical regeneration and resume. The current state now includes an authoritative `92460` same-day SELL execution and must not be rewound through submit/execution.

## Current Failure Path

Actual path:

`execution`
-> `Pending post-consumption state`
-> `current_valuation_refresh`
-> `runtime_data_readiness_gate`
-> `historical_safety_temporal_authority`
-> HALT/REVIEW_REQUIRED before valuation producer

Evidence:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T003243720082Z/run_state.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T003243720082Z/daily/2023-10-11/current_valuation_refresh/runtime_manifest.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T003243720082Z/daily/2023-10-11/current_valuation_refresh/safety_authority_decision.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T003243720082Z/daily/2023-10-11/current_valuation_refresh/valuation_apply_evidence.json`

Run state:

- `status = HALT`
- `next_job = 2023-10-11:current_valuation_refresh`
- completed `2023-10-11` jobs before the halt:
  - `market_refresh`: `0`
  - `data_readiness`: `0`
  - `morning`: `0`
  - `sell_planning`: `0`
  - `submit`: `0`
  - `execution`: `0`
  - `current_valuation_refresh`: `20`

Current valuation manifest:

- `final_state = REVIEW_REQUIRED`
- `exit_code = 20`
- `reason = historical_safety_temporal_authority_missing`
- `data_readiness_status = REVIEW_REQUIRED`
- `data_readiness_scope = current_valuation`
- `data_readiness_review_reasons = [historical_safety_temporal_authority_missing, pending_review_required]`
- `component_reasons.safety = [historical_safety_temporal_authority_missing]`
- `component_reasons.pending = [pending_review_required]`
- `review_guard_codes = [PENDING_BATCH_REVIEW_REQUIRED, TEMPORAL_MISMATCH]`
- `review_guard_classes = [BATCH_LEVEL_FAILURE, DATA_INTEGRITY_SAFETY]`
- `batch_blocking_review_guard_count = 2`

Valuation producer was not reached:

- `valuation_apply_evidence.status = NOT_EXECUTED`
- `blocked_before_producer = true`
- `blocking_stage = runtime_data_readiness_gate`
- `blocking_reason = historical_safety_temporal_authority_missing`
- `execution_reached = false`

## Exact Current-Valuation Failing Invariant

`current_valuation_refresh` requires Historical neutral safety temporal authority to be resolved by Data Readiness before valuation. That authority is denied because the current active Pending remains `REVIEW_REQUIRED` in `MIXED_SELL_ITEM_SCOPED_REVIEW`, and the current valuation residual adapter does not classify this post-partial-execution shape as compatible.

Computed Pending review-scope authority on the current actual Pending:

- contract: `pending_review_scope_authority`
- contract version: `phase30_ak9r27_v1`
- lifecycle state: `REVIEW_REQUIRED`
- review scope: `MIXED_SELL_ITEM_SCOPED_REVIEW`
- structural validity: `PASS`
- batch blocked: `false`
- partial submit allowed: `true`
- sell continuation allowed: `true`
- terminal item ids: `[strategy-63ee5549e637f6d247bc]`
- executable item ids: `[strategy-63ee5549e637f6d247bc]`
- executable sell item ids: `[strategy-63ee5549e637f6d247bc]`
- reviewed buy item ids: `[strategy-17b52bb1ef77d6312d14, strategy-7f7dbf5b074dc8f8ef12]`
- reviewed sell item ids: `[strategy-23fa7fa4d9acabff2823]`
- non-terminal item ids: `[]`
- `pending_scope_allows_sell_continuation(..., readiness_scope=submit) = true`
- `pending_scope_allows_current_valuation_residual(...) = false`

The first bad boundary is:

`Pending review-scope authority -> Historical Safety temporal authority current_valuation adapter`

The Pending shape is structurally valid and already supported for sell continuation/partial submit, but it is not admitted by the current valuation residual compatibility predicate.

## Pending Post-Consumption State

Current Pending:

- `pending_plan_id = pending-strategy-plan-historical-2023-10-11-84b153a169af27d4`
- `state = REVIEW_REQUIRED`
- `review_scope = MIXED_SELL_ITEM_SCOPED_REVIEW`
- `sell_continuation_allowed = true`
- `approved_item_ids = [strategy-63ee5549e637f6d247bc]`
- `approved_sell_item_ids = [strategy-63ee5549e637f6d247bc]`
- `review_required_sell_item_ids = [strategy-23fa7fa4d9acabff2823]`
- `review_required_buy_item_ids = [strategy-17b52bb1ef77d6312d14, strategy-7f7dbf5b074dc8f8ef12]`
- target session date: `2023-10-11`

Item states:

| Symbol | Side | Quantity | Pending item id | State | Feasibility | Meaning |
|---|---:|---:|---|---|---|---|
| `92460` | SELL | `100` | `strategy-63ee5549e637f6d247bc` | `CONSUMED` | `PASS` | submitted/executed exactly once |
| `50280` | SELL | `100` | `strategy-23fa7fa4d9acabff2823` | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | unresolved corporate action; must not submit |
| `38560` | BUY | `100` | `strategy-17b52bb1ef77d6312d14` | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | reserved notional exceeds dynamic cash capacity; must not submit |
| `76920` | BUY | `400` | `strategy-7f7dbf5b074dc8f8ef12` | `REVIEW_REQUIRED` | `REVIEW_REQUIRED` | unresolved corporate action; must not submit |

This is not an empty or fully terminalized Pending. It is a valid mixed review residual after one executable SELL item was consumed.

## Intended Post-Execution Contract

Existing Architecture explicitly states that if execution has already been applied and current valuation remains pending, repair or resume may restart only at `current_valuation_refresh` after explicit authorization. It also requires no duplicate execution, Ledger append, Cash mutation, or Pending terminalization, and valuation apply exactly once.

Existing code/tests already define a limited current-valuation residual concept:

- consumed Pending can allow current valuation;
- post-submit residual BUY review can allow current valuation;
- terminal-only residuals can allow current valuation;
- unresolved SELL review under the older BUY-only residual contract remains fail-closed.

The current code path does not yet define the post-AX mixed SELL residual after executable subset consumption. Specifically, `pending_scope_allows_current_valuation_residual()` admits only:

- terminal-only residuals, or
- `BUY_ITEM_SCOPED_REVIEW` with reviewed BUY items and no reviewed SELL items.

It does not admit:

- `MIXED_SELL_ITEM_SCOPED_REVIEW`
- consumed executable SELL item plus unresolved reviewed SELL/BUY items
- no remaining executable item after submit/execution consumption

Therefore, the answer to:

`DOES_REMAINING_REVIEW_PENDING_INVALIDATE_CURRENT_VALUATION_AUTHORITY_BY_DESIGN_OR_BY_GAP`

is:

`BY_CONTRACT_GAP`

The fail-closed result is expected under current implementation, but the missing contract is now exposed by Phase32-AX/AY actual path.

## Order Authority vs Valuation Authority

The implementation currently couples remaining order review to valuation safety authority through Data Readiness:

- Pending component returns `REVIEW_REQUIRED` because current valuation residual compatibility is false.
- Historical daily neutral safety authority then marks `pending_lifecycle_state` as mismatched.
- Safety component returns `historical_safety_temporal_authority_missing`.
- `current_valuation_refresh` stops before valuation producer.

This is appropriate for genuinely unsafe or malformed Pending, but too broad for the current actual shape:

- `92460` execution is already authoritative.
- `50280`, `38560`, and `76920` remain non-executable and unsubmitted.
- The valuation consumer should value authoritative post-execution holdings/cash and should not need to submit, clear, or infer reviewed orders.

Current valuation appears to require one of:

- Pending EMPTY / inactive,
- Pending CONSUMED / fully terminal,
- terminal-only residual,
- BUY-only post-submit residual adapter,
- or independent Historical neutral safety authority whose Pending compatibility predicate passes.

It lacks an explicit item-scoped compatibility condition for the mixed SELL residual state.

## 92460 State Integrity

`92460_STATE_MUST_BE_PRESERVED = YES`

Ledger counts for `2023-10-11`:

- orders: `1`
- executions: `1`
- positions: `4`
- cash: `1`
- events: `0`

`92460` order:

- symbol: `92460`
- quantity: `100`
- pending item: `strategy-63ee5549e637f6d247bc`
- order plan item: `strategy-63ee5549e637f6d247bc`
- source decision: `rp-2023-10-11-92460-sell_exit-3a396b4dce6e273e`
- source PM decision: `pm-2023-10-11-92460-reduce`
- order ledger record: `ledger-order-submit-29c815c88b17d133`

`92460` execution:

- execution id: `execution-equivalent:sha256:556c3bddb2e10ce4f176ad94cf498ec6673b7504c35dd0a02ae14f947158009c`
- filled quantity: `100`
- average price: `3250.0`
- cash effect: `325000.0`
- ledger execution record: `ledger-execution-equivalent-556c3bddb2e10ce4`

`92460` position transition:

- quantity: `0.0`
- pending item: `strategy-63ee5549e637f6d247bc`
- source decision: `rp-2023-10-11-92460-sell_exit-3a396b4dce6e273e`
- source PM decision: `pm-2023-10-11-92460-reduce`
- dedup key: `historical-position-transition:2023-10-11:92460:execution-equivalent:sha256:556c3bddb2e10ce4f176ad94cf498ec6673b7504c35dd0a02ae14f947158009c`

Cash:

- `cash = 1141580.0`
- `buying_power = 1141580.0`

Current state:

- `.runtime/persistent_ledger/state.json` is as of `2023-10-11`.
- `.runtime/runtime_state/current_state.json` is as of `2023-10-11`.
- `execution/current_apply_evidence.json` reports `status = APPLIED`.

No duplicate order or execution was observed.

## Remaining Reviewed Items

Under current architecture, the remaining reviewed items should not be submitted or silently cleared.

Current best-supported representation is to keep them as active same-day item-scoped residual review evidence:

- `50280`: active `REVIEW_REQUIRED`, unresolved corporate action, unsubmitted.
- `38560`: active `REVIEW_REQUIRED`, cash capacity review, unsubmitted.
- `76920`: active `REVIEW_REQUIRED`, unresolved corporate action, unsubmitted.

They should not be terminalized merely to allow valuation unless a specific lifecycle contract says they are next-day re-evaluation residuals or day-closed non-executable items. No existing evidence inspected in AZ proves such terminalization has already occurred or is currently authorized.

Therefore:

`DO_REVIEWED_ITEMS_NEED_TERMINALIZATION_BEFORE_VALUATION = NO, not by current evidence; valuation needs a compatible residual-review authority, not silent clearing.`

## Previous Repair Coverage

Classification:

`SAME_MIXED_REVIEW_CONTRACT_GAP_NEXT_CONSUMER`

Reason:

- Phase32-AA repaired the earlier corporate-action authority leak where `50280` reached Submit as approved.
- Phase32-AE covered partial-submit replay/finalization for already accepted submit evidence.
- Phase32-AX repaired normal fresh-run mixed SELL review so `50280` stays reviewed while `92460` can progress independently.
- Phase32-AY proved regeneration and resume through `submit` and `execution`, then exposed the next consumer: `current_valuation_refresh`.

Prior focused tests reached Planning/Pending/Submit/Execution behavior, but did not include a post-execution current valuation readiness case where:

- `review_scope = MIXED_SELL_ITEM_SCOPED_REVIEW`,
- one executable SELL is already consumed,
- reviewed SELL and BUY items remain unresolved,
- current valuation must value authoritative post-execution Current/Cash without submitting or clearing residual review items.

This is not evidence that AX broke 92460. It is evidence that AX's new valid residual Pending shape was not added to the current valuation safety authority contract.

## Minimal Repair Boundary

Do not repair in AZ.

Narrowest repair scope for a future phase:

1. Extend `pending_review_scope_authority` / Historical safety temporal authority current-valuation adapter to recognize a post-partial-execution `MIXED_SELL_ITEM_SCOPED_REVIEW` residual shape only when:
   - Pending structural validity is PASS;
   - target session date equals business date;
   - all approved/executable items have authoritative terminal/consumed side-effect evidence;
   - remaining reviewed items are explicitly non-submittable;
   - no duplicate submit/execution risk exists;
   - reviewed SELL/BUY items remain reviewed and are not cleared;
   - runtime mode/environment is Historical simulated for this neutral safety authority.
2. Keep Data Readiness fail-closed for malformed Pending, unconsumed executable items, missing safety context, stale run/profile/evidence-root binding, duplicate side-effect ambiguity, and non-Historical environments.
3. Add focused regression coverage:
   - post-AX mixed SELL partial execution -> current valuation readiness PASS;
   - reviewed residual items stay REVIEW_REQUIRED/unsubmitted;
   - missing/malformed consumed evidence remains REVIEW_REQUIRED;
   - duplicate 92460 evidence fails closed;
   - existing BUY-only residual current valuation tests remain PASS;
   - existing unresolved SELL before execution still fails closed.

Strategy semantics change: NO.

SELL semantics change: NO.

Fail-closed behavior weakened: NO; it must be narrowed to a verified residual-review shape only.

## Same-Run Continuation Safety

Safe continuation classification:

`RESUME_FROM_CURRENT_VALUATION_REFRESH_SAFE`

with strict conditions:

- Future repair must affect only current valuation readiness/authority for this already-applied post-execution state.
- Do not replay `morning`, `sell_planning`, `submit`, or `execution`.
- Preserve the existing `92460` order/execution/ledger/current state.
- Resume from current `next_job = 2023-10-11:current_valuation_refresh`.
- Before resume, verify duplicate append counts are still zero and Pending retains the expected mixed residual shape.

Fresh run required: NO by current evidence.

Current run can still be saved without reexecuting `92460`: YES, if the future repair is limited to current valuation authority and same-run resume starts at `current_valuation_refresh`.

## Required Final Answers

1. `EXACT_CURRENT_VALUATION_FAILING_INVARIANT`: Historical neutral safety temporal authority for `current_valuation` cannot resolve because the active Pending is `REVIEW_REQUIRED` / `MIXED_SELL_ITEM_SCOPED_REVIEW` with residual reviewed items, and `pending_scope_allows_current_valuation_residual()` returns false.
2. `FIRST_BAD_BOUNDARY`: Pending review-scope authority -> Historical Safety temporal authority current-valuation adapter.
3. `IS_92460_POST_EXECUTION_STATE_CORRECT`: YES. One order, one execution, one position transition, one cash update; no duplicate observed.
4. `SHOULD_92460_STATE_BE_PRESERVED`: YES.
5. `WHY_DOES_REMAINING_REVIEW_PENDING_BLOCK_VALUATION`: Data Readiness treats the residual mixed SELL review Pending as `pending_review_required`; safety temporal authority then reports `pending_lifecycle_state` mismatch and `historical_safety_temporal_authority_missing`.
6. `IS_THAT_BLOCK_INTENDED_OR_A_CONTRACT_GAP`: CONTRACT_GAP. It is fail-closed under current code, but missing for the new AX-valid post-partial-execution shape.
7. `WHAT_IS_THE_CORRECT_POST_PARTIAL_EXECUTION_PENDING_SHAPE`: Active same-day `REVIEW_REQUIRED` Pending with `review_scope = MIXED_SELL_ITEM_SCOPED_REVIEW`, consumed `92460`, reviewed/unsubmitted `50280`, `38560`, `76920`, and no remaining submittable executable item.
8. `DO_REVIEWED_ITEMS_NEED_TERMINALIZATION_BEFORE_VALUATION`: NO, not by current evidence. They must remain reviewed/unsubmitted unless a separate lifecycle contract terminalizes them.
9. `IS_THIS_PREVIOUS_REPAIR_INCOMPLETE`: YES, as next-consumer coverage gap for the same mixed review contract.
10. `IS_THIS_A_CORRECTNESS_DEFECT`: YES. Valuation authority is incorrectly blocked for already-authoritative holdings/cash because residual order review is not separated for the new mixed SELL residual shape.
11. `MINIMAL_REPAIR_SCOPE`: Extend current valuation residual Pending compatibility and Historical safety temporal authority for verified post-partial-execution `MIXED_SELL_ITEM_SCOPED_REVIEW`; add focused tests; preserve fail-closed for all ambiguous shapes.
12. `SAFE_CONTINUATION_POINT_AFTER_REPAIR`: `2023-10-11:current_valuation_refresh`.
13. `CAN_CURRENT_RUN_STILL_BE_SAVED_WITHOUT_REEXECUTING_92460`: YES.
14. `IS_FRESH_RUN_REQUIRED`: NO by current evidence.
15. `FINAL_JUDGMENT`: `PHASE32_AZ_POST_PARTIAL_EXECUTION_CURRENT_VALUATION_CONTRACT_GAP_IDENTIFIED`

