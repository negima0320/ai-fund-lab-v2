# Phase15-BJ Runtime Acceptance Step2 Submit Scope Review

## 1. Executive Summary

Phase15-BJ reviewed the Submit Scope boundary in design-only / review-only mode.

Final judgment:

```text
SUBMIT_SCOPE_REVIEW_REQUIRED
```

Submit Scope is not ready to proceed to actual Submit Acceptance yet.

Reason:

- Phase15-BH Review Pending is confirmed as review evidence only.
- Authoritative Submit Pending remains `EMPTY`.
- Review Pending is not automatically convertible to Submit Pending.
- The existing Submit Runtime correctly uses only `pending_order_plan/pending_order_plan.json` as Submit source.
- However, the producer / apply path that promotes a reviewed SELL/HOLD decision into an authoritative Submit Pending has not been accepted.
- Human Review and Human Approval are still separate concepts, but the Human Approval artifact/apply contract for this boundary is not closed.
- Approval expiration / revocation enforcement must be acceptance-proven before Submit.

No Submit, Execution, Broker Write, Approval Apply, Pending mutation, Current mutation, Notification Send, or Production Write was executed.

## 2. Read Documents

Read:

- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/phase_reports/phase15_bh_runtime_acceptance_step1_sell_hold_review_only_morning.md`
- `docs/phase_reports/phase15_bi_system_purpose_phase15_purpose_alignment_review.md`
- `docs/phase_reports/phase14_e51_sell_submit_execution_cleanup_cycle.md`
- `docs/phase_reports/phase14_e52_sell_submit_guard_contract_audit.md`
- `docs/phase_reports/phase14_e53_buy_sell_submit_guard_regression_audit.md`

Pending / Submit implementation and regression references reviewed:

- `src/ai_fund_lab_v2/runtime_v2/review_only/sell_hold_morning.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/models.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/reader.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/consume.py`
- `src/ai_fund_lab_v2/runtime_v2/approval/models.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/guards.py`

## 3. Scope

Acceptance target:

```text
Review Pending
↓
Submit Pending
```

Acceptance target excluded:

```text
Submit
Execution
Broker Write
Current apply
Notification send
Production Write
```

## 4. Current Review Pending

Artifact:

```text
.runtime/runtime_state/sell_hold_review_only/2026-07-10/review_pending.json
```

Evidence:

| Field | Value |
|---|---|
| `schema_version` | `runtime_v2_review_pending_v1` |
| `pending_type` | `SELL_HOLD_REVIEW_ONLY` |
| `state` | `REVIEW_REQUIRED` |
| `approval_required` | `false` |
| `submit_allowed` | `false` |
| `broker_write_allowed` | `false` |
| `authoritative_submit_pending` | `false` |
| `item_count` | `5` |

Review linkage source:

```text
.runtime/runtime_state/human_review/2026-07-10/4591_high_risk_review.json
```

Human Review linkage:

| Field | Value |
|---|---|
| `review_id` | `human_review_b15c7967207e475fb287c929a9faa20c` |
| `event_id` | `safety_event_314f67fe2ecb43f0a90816dac53c0aeb` |
| `issue_code` | `4591` |
| `review_status` | `REVIEWED` |
| `review_decision` | `SELL_HOLD_REVIEW_REQUIRED` |
| `automatic_trade_authorized` | `false` |
| `broker_write_authorized` | `false` |

Allowed actions:

```text
human_review
sell_hold_inference_for_review
sell_planning_for_review
```

Blocked actions:

```text
buy_inference
buy_planning
buy_submit
sell_submit
auto_sell
auto_recovery
broker_write
approval_apply
pending_mutation
current_position_mutation
```

Judgment:

```text
REVIEW_PENDING_CONFIRMED_NOT_SUBMIT_PENDING
```

Review Pending is not an executable order plan. It cannot be consumed by Submit Runtime and must not be promoted without a separate approval/promotion producer.

## 5. Current Authoritative Submit Pending

Artifact:

```text
.runtime/pending_order_plan/pending_order_plan.json
```

Current state:

| Field | Value |
|---|---|
| `schema_version` | `runtime_v2_pending_slot_v1` |
| `state` | `EMPTY` |
| `active_pending` | `false` |
| `last_terminal_state` | `EXPIRED` |
| `last_pending_plan_id` | `pending-order-plan-50fd2eb10e0ea01f` |

Judgment:

```text
NO_AUTHORITATIVE_SUBMIT_PENDING
```

The BH Review Pending did not mutate or replace the authoritative Submit Pending slot.

## 6. Submit Pending Contract

Formal Submit Pending must be:

| Item | Contract |
|---|---|
| Producer | Human-approved Submit Pending promotion producer |
| Artifact | `.runtime/pending_order_plan/pending_order_plan.json` |
| Schema | `PendingOrderPlan` / fixed Runtime v2 pending current |
| Pending ID | New `pending_plan_id` required |
| Approval Source | Explicit Human Approval artifact or accepted approval policy |
| Promotion Rule | Review Pending may be evidence input only. Promotion requires explicit selected items, approval, policy hash, safety decision, broker/current freshness, target session, expiration, and audit linkage. |
| Expiration | Required on pending constraints and approval linkage |
| Cancel Rule | Required; cancellation must create terminal history and cannot silently restore old pending |
| History | Required for previous pending state and promotion evidence |
| Consumer | Submit Runtime only when state is `APPROVED` and all guards pass |

Difference from Review Pending:

| Review Pending | Submit Pending |
|---|---|
| Review evidence | Executable intent candidate |
| Stored under `runtime_state/sell_hold_review_only/...` | Stored only at `.runtime/pending_order_plan/pending_order_plan.json` |
| `submit_allowed=false` | May be submitted only after `state=APPROVED` |
| `broker_write_allowed=false` | Broker Write still requires Submit Guard |
| No authority to place orders | Sole Submit source |

## 7. Human Approval Contract

Human Review is not Human Approval.

Human Review answers:

```text
Can SELL/HOLD review evidence be generated?
```

Human Approval must answer:

```text
Which exact Submit Pending items may proceed to Submit?
```

Required Human Approval contract:

| Item | Contract |
|---|---|
| Approver | Human operator or explicitly accepted approval policy |
| Approval Artifact | Required |
| Approval Scope | Selected pending items only |
| Approval Target | `pending_plan_id`, `approved_item_ids`, source review ids, source order/review hash |
| Approval期限 | Required |
| Approval取消 | Required |
| Approval Audit | Required; must link Review Pending, Human Review, Safety, Policy, Broker, Current |

Current judgment:

```text
APPROVAL_CONTRACT_REVIEW_REQUIRED
```

Reason:

- Human Review artifact exists.
- Human Approval artifact/apply path from Review Pending to Submit Pending is not accepted.
- Approval Apply was prohibited and not executed.

## 8. Submit Guard Review

Submit source:

```text
pending_order_plan/pending_order_plan.json
```

The Submit preflight rejects other sources through:

```text
submit source must be pending_order_plan current
```

Submit start conditions:

| Area | Required condition |
|---|---|
| Pending | fixed current path exists, valid schema, `state=APPROVED` |
| Approval | approval link exists, status `APPROVED`, hash matches Pending |
| Approval item scope | `approved_item_ids` match approved Pending items |
| Pending lifecycle | not consumed, not submitted, not post-send-unknown, not blocked/review-required |
| Policy | active policy exists and matches Pending/Approval policy hash |
| Safety | `safety_allows_action(action="submit", side=BUY/SELL)` returns allowed |
| BUY guard | cash, buying power, exposure, policy, symbol capability, quantity |
| SELL guard | Runtime-owned Current quantity and Broker available quantity |
| Broker state | SELL requires Broker available quantity evidence; broker-only positions are not sell source |
| Current | Current state must provide cash/buying power/positions as required |
| Runtime State | Submit must be entered only from accepted state machine path |

Current 4591 Safety scope:

```text
sell_submit=BLOCKED
broker_write=BLOCKED
```

Therefore, current Review-only evidence cannot be submitted.

Known gap:

```text
Approval expiration field exists, but current-time expiry enforcement in Submit Guard was not acceptance-proven in BJ.
```

This must be closed before real Submit Acceptance.

## 9. Runtime State Machine Boundary

Required formal path:

```text
Review Pending
↓
Human Approval
↓
Submit Pending
↓
Submit
↓
Execution
↓
Current
↓
Report
```

Current accepted path:

```text
Review Pending
↓
Human Review Output
```

Boundary assessment:

| Transition | Status |
|---|---|
| Review Pending -> Submit Pending | `REVIEW_REQUIRED` |
| Submit Pending -> Submit | `NOT_ACCEPTED` |
| Submit -> Execution | `NOT_ACCEPTED` |
| Execution -> Current | `NOT_ACCEPTED` |
| Current -> Report | `NOT_ACCEPTED` |

Authority gap:

```text
No accepted promotion/apply producer exists from Review Pending to authoritative Submit Pending.
```

## 10. Remaining Acceptance

Still remaining:

| Area | Boundary |
|---|---|
| Submit Pending Promotion | Review evidence + Human Approval -> authoritative Pending |
| Submit | APPROVED Pending -> Broker Submit preflight / write boundary |
| Execution | Submitted order -> Broker ReadOnly execution/fill evidence |
| Current | Execution/fill evidence -> Runtime-owned position/cash apply |
| Report | Current/reconcile evidence -> operator report |
| Notification | Payload -> real delivery / delivery ledger |
| Multi-Day | Pending/history/current/report continuity across days |

## 11. Regression

Command:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase15bh_sell_hold_review_only_morning.py tests/runtime_v2/test_phase13_p_pending_no_fallback.py tests/runtime_v2/test_phase13_p_pending_lifecycle.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py
```

Result:

```text
17 passed
```

Covered:

- Review Pending is not authoritative Submit Pending.
- Review-only Morning does not mutate authoritative Pending.
- Submit reader uses only fixed pending current path.
- Pending lifecycle blocks unsafe reverse transitions.
- Submit Guard uses side-specific policy evidence.
- SELL requires Broker available quantity.
- Broker-only positions are not SELL source.

Not proven:

- Approval Apply path.
- Review Pending to Submit Pending promotion.
- Current-time expired Approval rejection.
- Submit execution.
- Broker Write absence in a real submit attempt.

## 12. Runtime Mutation Statement

No prohibited Runtime mutation occurred.

Not executed:

```text
Submit
Execution
Broker Write
Approval Apply
Pending mutation
Current mutation
Notification Send
Production Write
```

Writes performed:

- Phase15-BJ Markdown report.
- Phase15-BJ JSON report.

## 13. Blockers

1. No accepted producer/apply path promotes Review Pending to authoritative Submit Pending.
2. Human Review and Human Approval are not yet separated by an accepted artifact/apply contract.
3. Review Pending itself does not carry `review_id` / `event_id`; linkage exists through Human Review and Safety evidence, but promotion should require explicit linkage.
4. Approval expiration and revocation enforcement must be acceptance-proven.
5. Current Safety remains `REVIEW_REQUIRED`; `sell_submit` and `broker_write` are `BLOCKED`.

## 14. Final Judgment

```text
SUBMIT_SCOPE_REVIEW_REQUIRED
```

Recommended next prefix:

```text
Phase15-BK Runtime Acceptance Step2 Submit Pending Promotion Contract Closure
```

BK should close the promotion / approval contract first. Submit itself should still not be executed until a later explicit Submit Acceptance scope.
