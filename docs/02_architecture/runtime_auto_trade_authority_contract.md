# Runtime Auto Trade Authority Contract

## Purpose

Runtime v2 may run normal automatic trading only when AI, Policy, Safety,
Pending, Submit Guard, Broker boundary, Execution, Current, and Evidence
contracts all agree. Runtime does not replace AI judgment; it controls whether
an already contracted decision may proceed.

## Authority Classes

| Authority | Meaning | Producer | Consumer | Normal Requirement |
|---|---|---|---|---|
| Auto Authority | Normal-state permission to continue the mainline | Policy + Safety + Submit Guard | Submit Pipeline / Execution Processor | Required for normal automatic flow |
| Human Review | Operator review for abnormal, uncertain, or safety-review cases | Safety / Runtime Review | Operator / Runtime | Not a submit authorization |
| Human Approval | Explicit approval for high-risk or promotion-gated Submit Pending | Operator Approval artifact | Pending Promotion / Submit Guard | Required only when policy or state requires it |
| Broker Write Authorization | Explicit authority to call write-capable Broker API | Runtime gate + configured mode + operator authorization when required | Broker Adapter | Required for any real broker write |
| Production Authorization | Permission to use production broker/write path | Production runbook + credentials + operator controls | Runtime Orchestrator | Separate from demo acceptance |
| Runtime Halt | Emergency stop that blocks inference, submit, broker write, and apply | Safety / Operator | Runtime Orchestrator | Overrides all other authorities |

## Normal Mainline

Normal operation is:

```text
AI decision
→ Policy
→ Safety
→ Authoritative Pending
→ Submit Guard
→ Broker Write Authorization
→ Submit
→ Broker ReadOnly Reconciliation
→ Execution Processor
→ Ledger Writer
→ Current Projector
→ Current Apply
→ Report
```

Human Review is not part of the normal automatic path unless Safety or Policy
returns review-required. Human Approval is not the same as Human Review; it is a
bounded authorization artifact for promotion or broker-write authority.

## Authorized No-Order Continuity

Submit may formally authorize a no-order day. When Submit exits `0` with
`submit_action=NO_SUBMISSION_REQUIRED`, `no_order_authority_evidence.status=PASS`,
`authority_type=AUTHORIZED_NO_ORDER`, `order_plan_status=NO_ORDER_AUTHORIZED`,
`pending_state=EMPTY`, `pending_item_count=0`, and `submitted_count=0`, Execution
must continue as a safe no-op:

```text
execution_action=NO_ACTION
fills=[]
ledger append count=0
current apply=NOT_REQUIRED
pending mutation=false
```

This is not fail-open. Missing, malformed, stale, ambiguous, or contradictory
submit authority remains `REVIEW_REQUIRED` or `BLOCKED`. Contradictions include
pending items with `NO_SUBMISSION_REQUIRED` and submitted orders with no-action
authority.

## Demo Acceptance Boundary

Demo-specific user authorization used for Phase15 broker-write acceptance does
not become a normal per-trade production requirement. Demo-only execution
fallbacks must carry:

```text
execution_equivalent=true
production_equivalent=false
```

and must be rejected by production execution authority.
