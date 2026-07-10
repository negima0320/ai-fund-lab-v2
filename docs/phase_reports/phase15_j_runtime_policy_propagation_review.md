# Phase15-J Runtime Policy Propagation Review

## Status

`PHASE15J_RUNTIME_POLICY_PROPAGATION_REVIEW_COMPLETE`

Phase15-J reviewed how the Capital Deployment Policy introduced through Phase15-H/I propagates across Runtime v2.

This phase did not perform implementation changes. The review is based on static code inspection of the Runtime v2 regular path.

## Review Scope

Flow reviewed:

```text
Capital Deployment Policy
↓
Morning Planning
↓
Capital Allocation
↓
Pending
↓
Approval
↓
Submit
↓
Broker
↓
Execution
↓
Current
↓
Report
↓
Notification
```

## Boundary Matrix

| Boundary | Policy Received | Policy Preserved | Consumer Uses Policy | Hidden Default Exists | Evidence |
|---|---|---|---|---|---|
| Capital Deployment Policy -> CLI | YES | YES | PARTIAL | NO hidden policy fallback for guarded jobs | `run_daily_operation.py` loads `--capital-deployment-policy`, emits `capital_deployment_policy_*` manifest fields |
| CLI -> Morning Planning | PARTIAL | NO | NO | YES | CLI requires policy for `morning`, but `run_morning_ai_planning_pending_pipeline()` receives only `max_orders`; policy object/path is not passed |
| Morning Planning -> Capital Allocation | NO | NO | NO | YES | `morning_pipeline.py` uses `max_orders=5`, `per_order_budget=min(planning_budget/max_orders, 100_000.0)`; `_allocation()` uses computed `per_order_budget` |
| Capital Allocation -> OrderPlan | NO | PARTIAL amount only | NO | YES upstream | `PlanningInput.capital_allocations` carries allocated amount and price evidence, but no policy version/source |
| OrderPlan -> Pending | NO | PARTIAL amount only | NO | YES upstream | `PendingOrderItem` has `estimated_amount`, price fields, but no `policy_version`, `policy_source`, or `capital_allocation_amount` field |
| Pending -> Approval | NO | NO | NO | N/A | `ApprovalRequest`/`ApprovalArtifact` preserve IDs/status only; policy metadata is not represented |
| Approval -> Submit | NO from Pending/Approval | NO | YES through separate policy reload | NO Submit hidden 100k cap after Phase15-I | Submit does not consume policy from Pending; it reloads explicit policy via `capital_deployment_policy_path` |
| Submit -> Broker Adapter | YES internally | PARTIAL | PARTIAL | NO side-neutral notional cap | `SubmitPipelineResult.submit_guard_policy` and `submit_guard_item_evidence`; `RuntimeV2SubmitCommand` sent to adapter has no policy metadata |
| Submit -> Ledger Orders | PARTIAL decision only | NO policy evidence | NO | N/A | `LedgerOrderRecord` stores order identity, side, symbol, quantity, status, normalization, response classification; no policy source/reason |
| Broker/Execution -> Ledger/Current | NO | NO | NO | N/A | Execution pipeline ingests Broker ReadOnly and projects fills; policy is not used and not needed for asset state calculation |
| Current -> Report | NO | NO | NO | N/A | Report loads fixed Current paths only; run manifest policy evidence is not in `CURRENT_INPUTS` |
| Report -> Notification | NO | NO | NO | N/A | Notification payload is built from report summary; policy reason/source are not in summary |

## Key Findings

### J-1. Morning Does Not Receive or Use Capital Deployment Policy

Severity: `BLOCKER`

Phase15-H made CLI evaluate the policy before `morning`, but Morning Planning still receives only:

```text
max_orders=args.max_orders
```

The policy object/path is not passed to `run_morning_ai_planning_pending_pipeline()`.

Evidence:

- `run_daily_operation.py`: `run_morning_ai_planning_pending_pipeline(... max_orders=args.max_orders)`
- `morning_pipeline.py`: function default `max_orders: int = 5`

Impact:

- Capital Deployment Policy is not the source of Morning order count or sizing.
- Policy can be loaded in manifest while Morning still uses Runtime-local sizing.

### J-2. Morning Still Contains Hidden Sizing Defaults

Severity: `BLOCKER`

Morning still contains:

```text
max_orders: int = 5
per_order_budget = min(float(planning_budget) / max(max_orders, 1), 100_000.0)
```

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`

Impact:

- Capital Allocation can still be throttled by Runtime-owned fixed defaults.
- Annual 50% deployment objective can be blocked before Submit.
- This is the main remaining hidden policy after Phase15-I removed Submit’s 100k cap.

### J-3. Pending Does Not Preserve Policy Version / Source

Severity: `HIGH`

`PendingOrderItem` preserves:

- `estimated_amount`
- `estimated_price`
- price source fields

It does not preserve:

- `policy_version`
- `policy_source`
- `capital_allocation_amount`
- active sizing constraints

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/pending/models.py`
- `pending_order_plan_to_payload()` serializes the dataclass as-is

Impact:

- Submit must reload policy separately and cannot prove that Pending was created from the same policy.
- Report/Notification cannot explain “why this amount” from Pending alone.

### J-4. Approval Drops Policy Context

Severity: `HIGH`

`ApprovalRequest` and `ApprovalArtifact` preserve pending/order IDs, requested/approved item IDs, status, hash, and reason. They do not preserve policy source or item-level capital allocation evidence.

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/approval/policy.py`
- `src/ai_fund_lab_v2/runtime_v2/approval/linkage.py`

Impact:

- Operator approval cannot later be audited against the active policy that produced the Pending items.
- A changed policy between Morning and Submit would be detectable in Submit evidence only if explicitly compared later; that comparison is not implemented.

### J-5. Submit Policy Evidence Exists but Is Not Written Into Ledger Orders

Severity: `MEDIUM`

Phase15-I added:

- `SubmitPipelineResult.submit_guard_policy`
- `SubmitPipelineResult.submit_guard_item_evidence`
- CLI manifest `submit_guard_policy`
- CLI manifest `submit_guard_item_evidence`

However, `LedgerOrderRecord` does not carry policy source, guard decision, or violated policy fields.

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/ledger/models.py`

Impact:

- Submit manifest contains policy evidence, but persistent order ledger does not.
- Report reads ledger/current, not run manifest, so policy reason is not reportable after the run unless manifest is separately retained and joined.

### J-6. Execution and Current Should Not Recalculate Policy, but Need Traceability Decision

Severity: `MEDIUM`

Execution and Current should not decide capital policy. They should reflect accepted orders, executions, and asset state.

Current state should not become a policy decision source. However, if Report/Notification must explain “why bought/sold/stopped,” either:

- policy evidence must be retained in ledger/order records, or
- reports must join to run manifest/submit guard evidence.

Evidence:

- `execution/readonly_pipeline.py` projects Broker ReadOnly and runtime-owned fills.
- `asset/runtime_owned_fill_projection.py` calculates Current from accepted Submit ledger and execution evidence.

Impact:

- Current correctly remains an asset SoT, not a policy SoT.
- But policy traceability stops before Report unless a deliberate evidence join is added.

### J-7. Report Does Not Consume Policy Evidence

Severity: `HIGH`

Report loads only:

```text
persistent_ledger/state.json
persistent_ledger/orders.jsonl
persistent_ledger/executions.jsonl
persistent_ledger/positions.jsonl
persistent_ledger/cash.jsonl
persistent_ledger/events.jsonl
pending_order_plan/pending_order_plan.json
runtime_state/current_state.json
```

It does not load:

```text
runtime_state/run_manifest/*.json
submit_guard_policy
submit_guard_item_evidence
capital_deployment_policy_*
```

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py`
- `CURRENT_INPUTS`

Impact:

- Report cannot explain active policy source, policy reason, guard decision, or violated policy.
- Phase15-M remains necessary for policy reason propagation.

### J-8. Notification Does Not Consume Policy Reason

Severity: `HIGH`

Notification payload is derived from report summary. Since report summary lacks policy evidence, notification also lacks:

- policy source
- guard decision
- violated policy
- review-required policy reason

Evidence:

- `notification/payload.py`
- `report/markdown_writer.py`

Impact:

- Notification cannot tell the operator “why buy/sell/stop” in policy terms.
- This is a direct gap against Phase15 purpose.

## Hidden Default / Placeholder Risk Inventory

| Area | Risk | Evidence | Severity |
|---|---|---|---|
| Morning order count | `max_orders=5` remains Runtime/CLI driven | `morning_pipeline.py`, `run_daily_operation.py` | BLOCKER |
| Morning per-order amount | `100_000.0` cap remains | `per_order_budget=min(..., 100_000.0)` | BLOCKER |
| Morning evaluation capital | Uses broker capability default before policy | `capability.default_evaluation_capital or asset_state.total_equity...` | HIGH |
| Pending policy fields | Missing `policy_version/source` | `PendingOrderItem` model | HIGH |
| Approval policy fields | Missing policy evidence | `ApprovalRequest`, `ApprovalArtifact` | HIGH |
| Report policy reason | Not consumed | `CURRENT_INPUTS` excludes run manifest | HIGH |
| Notification policy reason | Not consumed | payload built from summary only | HIGH |
| SELL broker available evidence | Current proxy still used in Phase15-I | `broker_available_quantity_source=current_proxy` | MEDIUM |

## Propagation Assessment

Current status:

```text
Capital Deployment Policy
↓  PASS at CLI manifest
Morning Planning
↓  GAP: not passed / hidden defaults remain
Capital Allocation
↓  GAP: amount only, no policy source
Pending
↓  GAP: policy source/version not preserved
Approval
↓  GAP: policy context lost
Submit
↓  PARTIAL PASS: policy reloaded, guard evidence emitted
Broker
↓  OK to omit policy from command, but traceability is not ledgered
Execution
↓  OK: should not recalculate policy
Current
↓  OK as asset SoT, but not policy explanation source
Report
↓  GAP: policy reason not explainable
Notification
   GAP: policy reason not explainable
```

## Required Follow-up

Recommended follow-up order:

1. Phase15-K/J-follow-up: Morning Planning must receive and use Capital Deployment Policy.
2. Add policy evidence to OrderPlan/Pending:
   - `policy_version`
   - `policy_source`
   - `capital_allocation_amount`
   - active sizing constraints
3. Preserve or link policy context through Approval.
4. Decide ledger/report traceability strategy:
   - write policy evidence into ledger order records, or
   - let Report load run manifest evidence.
5. Add Report/Notification policy reason propagation.
6. Keep Current policy-neutral, but make the policy evidence join explicit elsewhere.

## Prohibited Actions Check

Not performed:

- Runtime implementation changes
- Submit execution
- Broker Write
- Demo order
- Production order
- Notification real send
- launchd change

## Final Judgment

`PHASE15J_RUNTIME_POLICY_PROPAGATION_REVIEW_COMPLETE`

