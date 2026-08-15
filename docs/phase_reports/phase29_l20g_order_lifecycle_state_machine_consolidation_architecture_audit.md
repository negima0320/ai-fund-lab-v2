# Phase29-L20G - Order Lifecycle State Machine Consolidation Architecture Audit

Task ID: Phase29-L20G

Mode:

```text
READ-ONLY ARCHITECTURE / STATE MACHINE / ROOT CAUSE AUDIT
NO IMPLEMENTATION
NO CURRENT RUN MUTATION
NO RESUME / FRESH-RUN / RUN / PENDING_LIFECYCLE / REPAIR
NO LONG HISTORICAL EXECUTION
```

## 1. Primary Judgment

```text
PLAN_LEVEL_PENDING_STATE_CANNOT_REPRESENT_MIXED_ITEM_TERMINAL_OUTCOMES = CONFIRMED
ITEM_LEVEL_OUTCOME_EVIDENCE_EXISTS_IN_FRAGMENTS_BUT_IS_NOT_A_CONSUMED_LIFECYCLE_AUTHORITY = CONFIRMED
RECOMMENDED_TARGET = ITEM_LEVEL_TERMINAL_STATE_AUTHORITY_WITH_DERIVED_PLAN_STATE
```

The direct architecture gap is not Strategy, ADD, BUY_NEW, BUY_ADD, SELL,
REDUCE, or EXIT semantics. It is the Order Lifecycle authority boundary after
Submit and Execution: the system can create a composite BUY+SELL Pending plan,
and can independently submit/execute the SELL while the BUY is Corporate Action
quarantined, but it cannot derive a terminal plan state from mixed item
outcomes.

The current schema has `PendingOrderItem.state`, but there is no formal
item-level terminal state machine or single consumer that combines Submit
outcomes, Execution fills, and definitely-not-submitted quarantine outcomes.
The formal lifecycle state machine remains plan-level.

## 2. L20A-F Consolidated Root Chain

- L20A: Historical 2022-09-28 halted because Submit produced Corporate Action
  quarantine for 76920 BUY, and Execution did not consume a scoped
  no-submitted-order authority.
- L20B: Execution was repaired to recognize strict Historical CA quarantine
  no-submitted-order continuation.
- L20C: The next halt showed active APPROVED Pending survived into the next day.
- L20D: Pending lifecycle was repaired to terminalize strict Historical CA
  quarantine APPROVED -> EXPIRED -> EMPTY, while preserving POST_SEND_UNKNOWN
  fail-closed behavior.
- L20E: The runner did not invoke pending_lifecycle automatically after
  Execution emitted `PENDING_LIFECYCLE_REQUIRED`.
- L20F: The runner now invokes pending_lifecycle and gates day completion when
  Execution emits `PENDING_LIFECYCLE_REQUIRED`.
- L20G: A new mixed case appears where Execution emits `NOT_REQUIRED` because
  at least one order was submitted/executed, while a sibling item remains
  definitely not submitted and the plan remains REVIEW_REQUIRED.

## 3. L20F Real-run Validation

Run inspected read-only:

```text
runtime-test-historical-smoke-20260811T102145199169Z
status = HALT
next_job = 2022-09-30:current_valuation_refresh
completed tail = 2022-09-22, 2022-09-26, 2022-09-27, 2022-09-28, 2022-09-29
```

The 2022-09-29 evidence validates L20F:

```text
execution/pending_terminalization_evidence.json
status = PENDING_LIFECYCLE_REQUIRED
pending_plan_present = true
pending_item_count = 1

pending_lifecycle result
previous_state = APPROVED
new_state = EXPIRED
status = EXPIRED

day_completion/day_completion_evidence.json
status = PASS
pending_lifecycle_result.status = EXPIRED
active_pending_state_after = null
```

## 4. 2022-09-30 Mixed Outcome Reconstruction

Composite plan:

```text
source_order_plan_id = order-plan-pending-composite-2022-09-30-c14e16284adf
approved BUY item = 76920 / BUY / 1400
approved SELL item = 41650 / SELL / 200
buy_items_status = APPROVED
sell_items_status = APPROVED
plan state before submit = APPROVED
```

Submit evidence:

```text
final_state = REVIEW_REQUIRED
exit_code = 20
submitted_count = 1
blocked_count = 1
reason = submit completed with rejected/unknown/blocked items
```

Corporate Action continuation evidence:

```text
status = COMPLETED_WITH_SYMBOL_QUARANTINE
scope = CORPORATE_ACTION_SYMBOL_ONLY
affected_symbols = [76920]
production_applicability = NEVER
run_continuation = ALLOWED_FOR_HISTORICAL_REPLAY_ONLY
checks.other_item_results_independently_inspectable = true
checks.submitted_count_matches_pass_items = true
```

Execution evidence:

```text
execution final_state = CURRENT_STATE_LOADED
exit_code = 0
execution/pending_terminalization_evidence.status = NOT_REQUIRED
fills.json = 41650 SELL quantity 200
ledger_append_evidence.status = PASS
current_apply_evidence.status = APPLIED
```

Halt evidence:

```text
data_readiness.overall_status = REVIEW_REQUIRED
components.pending.reason = pending_review_required
components.pending.slot_status = REVIEW_REQUIRED
components.safety.reason = historical_safety_temporal_authority_missing
components.safety.pending_safety_authority.reason = historical_pending_safety_authority_mismatch
pending_safety_authority.pending_lifecycle_state = REVIEW_REQUIRED
```

This is a safe fail-closed halt under the current contract. It should not be
fixed by weakening Data Readiness or Safety.

## 5. Pending Schema Authority Map

Source evidence:

```text
src/ai_fund_lab_v2/runtime_v2/pending/models.py:11-26
src/ai_fund_lab_v2/runtime_v2/pending/models.py:77-86
src/ai_fund_lab_v2/runtime_v2/pending/models.py:145-190
```

Schema facts:

- `PendingPlanState` is a formal enum with plan states including APPROVED,
  SUBMITTED, CONSUMED, EXPIRED, BLOCKED, REVIEW_REQUIRED, POST_SEND_UNKNOWN,
  and EMPTY.
- `PendingOrderItem.state` is a free string, not a formal item lifecycle enum.
- `PendingOrderPlan` carries side/status fields such as `buy_items_status`,
  `sell_items_status`, `approved_buy_item_ids`, `approved_sell_item_ids`,
  `review_required_buy_item_ids`, and `review_required_sell_item_ids`.
- Those fields support side-aware review and continuation, but they are not a
  terminal outcome authority after Submit and Execution.

## 6. Submit State Machine

Source evidence:

```text
src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:575-626
```

Submit appends ledger order records for submitted items. If any item is unknown,
plan state becomes POST_SEND_UNKNOWN. If any item is rejected or blocked, plan
state becomes REVIEW_REQUIRED. Only when there are no unknown/rejected/blocked
items does Submit mark accepted items CONSUMED, set plan SUBMITTED, and consume
the plan.

This means mixed `submitted + blocked` is intentionally fail-closed at plan
level. It does not distinguish:

```text
definitely not submitted quarantine + submitted sibling
broker uncertain sibling + submitted sibling
generic rejected sibling + submitted sibling
```

## 7. Execution State Machine

Source evidence:

```text
src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py:438-440
src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py:444-499
src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py:574-615
```

Execution has two separate paths:

- Normal submitted-order execution path: processes orderlist/fills, writes
  ledger/current evidence, and reports `pending_terminalization_status =
  NOT_REQUIRED`.
- No-submitted-order path: resolves no-action authority and can emit
  `PENDING_LIFECYCLE_REQUIRED` when active Pending remains.

The L20B/L20D/L20F path is explicitly scoped to submitted_count zero. The source
returns NOT_APPLICABLE for Historical quarantine no-submitted authority when
`submitted_count != 0`, so 2022-09-30 cannot trigger L20F even though one
sibling is definitely not submitted.

## 8. Pending Lifecycle State Machine

Source evidence:

```text
src/ai_fund_lab_v2/runtime_v2/pending/lifecycle.py:21-43
src/ai_fund_lab_v2/runtime_v2/pending/lifecycle.py:47-58
src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py:376-423
src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py:446-503
```

Pending lifecycle is plan-level. L20D strict CA terminalization only applies
when:

```text
pending state = APPROVED
submitted_count_zero = true
blocked_count_matches_pending = true
all_pending_items_ca_blocked = true
no_generic_review_mixed_in = true
unknown_submit_risk = false
```

It cannot terminalize one quarantined item while preserving a filled sibling.
Applying the current whole-plan EXPIRED/EMPTY transition to a mixed filled plan
would corrupt or obscure the executed SELL sibling.

## 9. Data Readiness / Safety Consumer Contract

Source evidence:

```text
src/ai_fund_lab_v2/runtime_v2/data_readiness.py:2240-2267
src/ai_fund_lab_v2/runtime_v2/data_readiness.py:2332-2410
```

Data Readiness treats active REVIEW_REQUIRED Pending as REVIEW_REQUIRED unless
a narrow scoped continuation contract applies. Historical Safety rejects
pending lifecycle states outside APPROVED/CONSUMED/no-action terminal when no
explicit eligible exception exists.

This is correct. Data Readiness and Safety should remain consumers/checkers,
not hidden lifecycle mutators.

## 10. Day Completion Contract

Source evidence:

```text
scripts/runtime_test.py:6932-7008
scripts/runtime_test.py:7092-7134
```

L20F Day Completion only gates when:

```text
execution/pending_terminalization_evidence.status == PENDING_LIFECYCLE_REQUIRED
```

In the mixed submitted+quarantined case, Execution emits NOT_REQUIRED, so the
runner does not invoke pending_lifecycle and the day completion gate has no
required lifecycle marker to enforce.

## 11. Outcome Matrix

| Outcome | Current Definition | Item Terminal | Plan Terminal | Broker Uncertainty | Human Review | Day Completion | Ledger/Current |
|---|---|---:|---:|---:|---:|---:|---:|
| FILLED + FILLED | DEFINED | yes | CONSUMED/SUBMITTED | no | no | yes | allowed |
| QUARANTINED + FILLED | CONFLICTING | fragmentary | no | no | current yes | no | filled sibling allowed |
| REJECTED + FILLED | PARTIALLY_DEFINED | fragmentary | no | depends | yes | no | filled sibling allowed |
| BLOCKED + FILLED | PARTIALLY_DEFINED | fragmentary | no | depends | yes | no | filled sibling allowed |
| POST_SEND_UNKNOWN + FILLED | DEFINED_FAIL_CLOSED | no | no | yes | yes | no | filled sibling allowed, aggregate blocked |
| QUARANTINED + QUARANTINED | DEFINED after L20B/D/F | yes by strict all-items rule | EXPIRED/EMPTY | no | no for Historical continuation | yes | no mutation |
| REJECTED + REJECTED | PARTIALLY_DEFINED | no formal item terminal authority | no | no if broker-definite | yes | no | no fills |
| NO_ACTION | DEFINED | not applicable | EMPTY/no-action | no | no | yes | no mutation |
| BUY quarantine + SELL filled | CONFLICTING | BUY fragment, SELL fill | no | no | current yes | no | SELL allowed |
| BUY filled + SELL quarantine | CONFLICTING | BUY fill, SELL fragment | no | no | current yes | no | BUY allowed |

Desired matrix rule:

```text
Plan is terminal only when every item has a terminal outcome and no item has POST_SEND_UNKNOWN or unresolved broker uncertainty.
```

## 12. BUY/SELL Independence Assessment

BUY/SELL independence is partially implemented and must be preserved.

Evidence:

- `compose_with_existing_buy_pending` creates composite BUY+SELL plans and
  records composed BUY/SELL item counts.
- Phase24-HV states that BUY item-scoped REVIEW_REQUIRED prohibits BUY
  submission but must not invalidate independent SELL Planning or approved SELL
  submission.
- Phase29-L9 states that Corporate Action quarantine is symbol-only and
  unrelated symbols continue through normal guards.
- The 2022-09-30 run proves 41650 SELL executed and persisted despite 76920 BUY
  quarantine.

The remaining gap is not independence of execution. It is convergence of mixed
independent outcomes back into a terminal lifecycle aggregate.

## 13. Component Responsibility Map

| Component | Inputs | Outputs | Mutation Owner | Consumer Gap |
|---|---|---|---|---|
| Planning | Strategy/PM/current/market | PendingOrderItem, order plan | Planning/Pending writer | no terminal outcomes |
| Pending composition | Existing BUY pending, new SELL/ADD pending | composite pending plan | Pending composition | no post-submit merge outcome |
| Submit | approved pending, guards, CA registry | submit results, orders ledger, plan REVIEW_REQUIRED/SUBMITTED | Submit | item outcomes not persisted as lifecycle authority |
| CA quarantine | symbol registry, guard evidence | continuation evidence | Submit/runtime_test evidence | item-scoped quarantine not consumed in mixed lifecycle |
| Execution | submitted orders | fills, ledger/current, pending_terminalization evidence | Execution for fills only | NOT_REQUIRED hides unresolved sibling |
| Pending lifecycle | current pending + submit evidence | whole-plan terminalization | Pending lifecycle | all-items quarantine only |
| Data Readiness | pending + safety | READY/REVIEW_REQUIRED | checker only | correctly lacks mixed terminal proof |
| Safety | pending lifecycle state/context | safety authority decision | checker only | correctly fail-closed |
| Current/Ledger | fills/executions | state.json, current apply evidence | Execution/current projection | works for filled sibling |
| Runtime runner | job evidence | run_state, day_completion | runner | consumes only PENDING_LIFECYCLE_REQUIRED |
| Day Completion | execution/lifecycle evidence | append allowed/blocked | runner | no mixed-outcome lifecycle contract |

## 14. Architecture Debt

Primary debt:

```text
Order lifecycle authority is split across Submit, Execution, Pending lifecycle,
Data Readiness, Safety, and Day Completion without a single item outcome
authority.
```

Secondary debt:

- `REVIEW_REQUIRED` is used both for true human review and for
  definitely-not-submitted non-retryable Historical quarantine.
- Execution has no vocabulary for `MIXED_ITEM_LIFECYCLE_REQUIRED`.
- Pending lifecycle can only terminalize a whole plan safely when every item
  matches the same strict no-submitted quarantine shape.
- Day Completion relies on an Execution marker that is absent for submitted
  mixed plans.

## 15. Duplicate/Missing Authority

Missing:

- Formal `OrderItemLifecycleState` enum.
- Formal mapping from Submit item results to item terminal candidates.
- Formal mapping from Execution fills to FILLED/PARTIALLY_FILLED item outcomes.
- Formal derivation of plan terminal state from all item outcomes.
- Mixed submitted+not-submitted lifecycle marker.

Duplicate or orphaned:

- Plan state, side status fields, Submit aggregate status, Execution
  pending_terminalization status, Data Readiness pending status, and Safety
  pending lifecycle state all classify adjacent facts without a shared
  authority object.

## 16. Git Lineage

Read-only git search:

```text
git log -S pending_item_id:
1db2ce8 phase28 FIX
d470765 phase26 FIX
9e9b39d phase24 FIX
74742ae phase21 FIX
cfacef4 phase15
455f612 phase15
764c192 phase14
1ba8f59 phase13

git log -S compose_with_existing_buy_pending:
1db2ce8 phase28 FIX
d470765 phase26 FIX
74742ae phase21 FIX

git log -S submitted_count:
54f91f8 phase29途中x
1db2ce8 phase28 FIX
d470765 phase26 FIX
9e9b39d phase24 FIX
0f33158 phase23 FIX
9840c84 phase20 FIX
f4f8dbf phase19 FIX
...

git log -S corporate_action_symbol_quarantine:
54f91f8 phase29途中x
```

Conclusion:

```text
PRIOR_PARTIAL_IMPLEMENTATION_AND_AUTHORITY_MIGRATION_GAP = CONFIRMED
DELETED_FULL_ITEM_LIFECYCLE_IMPLEMENTATION = NOT_CONFIRMED
```

The repo has long-running item identity and side-aware composition lineage, but
the specific CA quarantine continuation is Phase29-era and did not add a
complete mixed item lifecycle authority.

## 17. Recommended Target State Machine

Recommended target: Option B.

```text
Item-level terminal state is authoritative.
Plan state is derived from item states and broker uncertainty.
```

Item states:

- PLANNED: supported as planning/source item status, not formal lifecycle.
- APPROVED: supported through plan approval and approved item ids.
- SUBMITTED: supported through Submit ledger order records.
- FILLED: supported through Execution fills, but not formal Pending item state.
- PARTIALLY_FILLED: unsupported as formal Pending lifecycle in inspected code.
- REJECTED: plan enum exists; item terminal authority incomplete.
- BLOCKED: plan enum exists; item terminal authority incomplete.
- QUARANTINED: evidence exists as CA continuation, not Pending enum.
- EXPIRED: plan enum exists; item terminal authority incomplete.
- CANCELLED: plan enum exists; item terminal authority incomplete.
- POST_SEND_UNKNOWN: plan enum exists; must remain fail-closed.
- REVIEW_REQUIRED: plan enum and item evidence strings exist.
- NO_ACTION: supported through EMPTY/no-action authority.

Derived plan rules:

```text
all items terminal and no broker uncertainty -> terminal aggregate
any POST_SEND_UNKNOWN -> POST_SEND_UNKNOWN / REVIEW_REQUIRED fail-closed
any non-terminal unresolved item -> REVIEW_REQUIRED
no items and no active pending -> EMPTY
```

## 18. Component Consolidation Recommendation

Do not create a large new component in L20G/L20H. Consolidate responsibility
incrementally around existing Pending lifecycle and runner evidence:

```text
Planning
  -> Pending/Submit item outcome evidence
  -> Execution fill outcome evidence
  -> Pending lifecycle derives item terminal outcomes and aggregate plan state
  -> Current/Ledger reconciliation remains fill-owned
  -> Day Completion consumes derived lifecycle evidence
```

The conceptual target may be called Order Lifecycle Authority, but the practical
repair should extend existing modules first.

Option comparison:

| Option | Correctness | Production Safety | Broker Uncertainty | BUY/SELL Independence | Migration Risk | Recommendation |
|---|---|---|---|---|---|---|
| A plan-level improved aggregate | medium | medium | weak | medium | low | insufficient |
| B item-level authoritative, plan derived | high | high | strong | high | medium | recommended |
| C hybrid existing | medium | medium | medium | medium | low | transitional only |
| D new standalone component | high | medium | strong | high | high | later only |

## 19. Minimal Repair Boundary

Minimal L20H repair should:

- Add a formal mixed-outcome detector for submitted+definitely-not-submitted
  sibling cases.
- Materialize item outcome evidence from Submit guard results and Execution
  fills.
- Preserve ledger/current mutation for filled siblings.
- Treat Historical CA quarantine `NOT_SUBMITTED` as terminal only when
  production_applicability is NEVER, run continuation is Historical-only, and
  no broker write/unknown risk exists.
- Derive aggregate plan terminal state only when every item is terminal.
- Teach Execution or Day Completion to emit/consume a marker such as
  `MIXED_ITEM_LIFECYCLE_REQUIRED`.
- Keep POST_SEND_UNKNOWN and unknown broker results fail-closed.

## 20. What Must NOT Be Fixed

Do not:

- Auto-terminalize POST_SEND_UNKNOWN.
- Convert generic REVIEW_REQUIRED to PASS.
- Weaken Data Readiness or Safety checks.
- Drop or rewrite the filled 41650 SELL ledger/current evidence.
- Treat all rejected/blocked cases as equivalent to CA quarantine.
- Change Strategy, PM, ADD, BUY_NEW, BUY_ADD, SELL, REDUCE, EXIT semantics.
- Mutate the current halted run in L20G.

## 21. Strategy Causality

```text
L19 Strategy = UNRELATED
ADD / BUY_ADD / BUY_NEW semantics = UNRELATED
SELL / REDUCE / EXIT semantics = UNRELATED
```

The Strategy produced a valid mixed BUY/SELL plan. Submit and Execution
correctly handled independent item feasibility/execution. The missing piece is
post-execution lifecycle convergence.

## 22. Current Run Mutation

```text
NO
```

No resume, repair, pending_lifecycle, fresh-run, run, abandon, reset, rollback,
broker write, evidence rewrite, or runtime-state mutation was executed for
`runtime-test-historical-smoke-20260811T102145199169Z`.

## 23. Long Historical Executed

```text
NO
```

Only read-only inspection commands were used.

## 24. Next Task Recommendation

Recommended next task:

```text
Phase29-L20H - Mixed-Outcome Item-Level Order Lifecycle Authority Repair
```

Exact scope:

- Implement item-level outcome materialization for Submit + Execution evidence.
- Add mixed `submitted + definitely_not_submitted_ca_quarantine` lifecycle
  detection.
- Preserve filled sibling ledger/current application.
- Derive plan terminal only when all items are terminal and no broker
  uncertainty exists.
- Keep POST_SEND_UNKNOWN fail-closed.
- Update runner/day completion to consume the mixed lifecycle evidence.
- Add tests for:
  - BUY quarantine + SELL filled.
  - BUY filled + SELL quarantine.
  - POST_SEND_UNKNOWN + filled sibling fail-closed.
  - rejected/blocked + filled sibling remains REVIEW_REQUIRED unless a formal
    terminal classification exists.
  - quarantine + quarantine remains covered by L20B/D/F.
- No Strategy/PM/ADD/BUY/SELL semantic change.

Continuation recommendation:

```text
IMPLEMENT_L20H_BEFORE_NEXT_LONG_HISTORICAL
FRESH_RUN_AFTER_L20H_SHORT_REGRESSION_PASS
```
