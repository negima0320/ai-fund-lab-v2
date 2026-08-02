# Phase24-HS Upstream Planning Exposure Preflight and Partial Submit Lifecycle Contract Review

## 1. Executive Summary

Phase24-HS freezes the Production Runtime contract for the Phase24-HR finding:

```text
PHASE24_HR_EXPECTED_VALID_EXPOSURE_BLOCK_UPSTREAM_PLANNING_REVIEW_REQUIRED_WITH_PARTIAL_SUBMIT_CONTRACT_GAP
```

Primary design decision:

```text
Planning must perform deterministic Submit feasibility preflight before
APPROVED Pending materialization.
```

Submit Guard remains the final hard pre-broker guard. It must not be weakened, bypassed, or converted into a sizing optimizer.

No implementation or Runtime test was performed.

## 2. Primary Judgment

```text
PHASE24_HS_DESIGN_COMPLETE_PLANNING_PREFLIGHT_REQUIRED
```

## 3. Scope and Constraints

This task is Design Review / Contract Freeze only.

No changes were made to:

```text
max exposure
target exposure
cash reserve
BUY quantity
Position Sizing
Portfolio Policy
Submit Guard
Strategy
PM
Runtime code
Historical-specific behavior
```

Runtime Test was not executed.

## 4. Confirmed Phase24-HR Facts

2022-07-25:

```text
current_exposure = 685,510
max_exposure = 850,000
remaining_exposure = 164,490
BUY 66590 = 166,400
SELL 23880 = 88,800
BUY-only post exposure = 851,910
```

Result:

```text
BUY = BLOCKED
SELL = ACCEPTED
Submit Guard = correct
Planning produced a BUY that deterministic Submit Guard rejected
```

## 5. Planning Responsibility

Planning must guarantee deterministic submit feasibility before an item becomes APPROVED Pending.

Planning responsibilities:

| Responsibility | Contract |
|---|---|
| Position Count | Check active policy when present and materialize post-plan evidence |
| Cash | Check planned BUY against canonical cash and buying_power |
| Exposure | Check planned BUY against canonical remaining exposure |
| Weight | Preserve Position Sizing target evidence; do not silently resize |
| Safety | Bind Safety decision and fail closed if Safety blocks |
| Submit Feasibility | Prove deterministic Submit Guard feasibility before Pending approval |

Planning may not approve a BUY known to violate active hard exposure.

Conditional exception:

```text
If a constraint depends on broker state unavailable until Submit, the item
must be REVIEW_REQUIRED or explicitly marked as unresolved. It must not be
APPROVED as submit-feasible.
```

Evidence:

```text
reports/phase24_hs_upstream_planning_exposure_preflight_and_partial_submit_lifecycle_contract_review/planning_responsibility_contract.json
```

## 6. Submit Responsibility

Submit Guard is:

```text
HARD_SAFETY_AND_FINAL_BROKER_BOUNDARY_GUARD
```

Submit Guard may:

```text
validate Pending / Approval / Safety / freshness / idempotency
validate broker capability
validate cash, buying_power, max_exposure, max_position_weight
validate SELL current quantity and broker-available quantity
fail closed before broker boundary
```

Submit Guard must not:

```text
score investments
change Strategy or PM decisions
widen max_exposure
silently shrink BUY quantity
pre-credit same-day SELL capacity without approved contract
bypass Policy or Safety evidence
```

Evidence:

```text
reports/phase24_hs_upstream_planning_exposure_preflight_and_partial_submit_lifecycle_contract_review/submit_responsibility_contract.json
```

## 7. Canonical Exposure Authority

Canonical owner:

```text
Submit Guard hard exposure authority derived from active
CapitalDeploymentPolicy and Runtime Current / Persistent Ledger market value.
```

Formula:

```text
current_exposure = sum(Runtime Current positions[].market_value)
remaining_exposure = active max_exposure - current_exposure
BUY feasible = current_exposure + pending BUY estimated_amount <= active max_exposure
```

Active source:

```text
policy_source = configs/runtime_v2/capital_deployment.json
policy_version = capital_deployment_v1
current_source = .runtime/persistent_ledger/state.json
```

Planning must consume this same authority for deterministic preflight. Planning does not replace Submit as final guard.

Evidence:

```text
reports/phase24_hs_upstream_planning_exposure_preflight_and_partial_submit_lifecycle_contract_review/exposure_authority_contract.json
reports/phase24_hs_upstream_planning_exposure_preflight_and_partial_submit_lifecycle_contract_review/layer_reconciliation_contract.json
```

## 8. Layer Responsibility Matrix

| Layer | Exposure Responsibility |
|---|---|
| Portfolio Policy | Strategy target exposure guidance; DRAFT / NOT_ELIGIBLE in current run |
| Portfolio Construction | Member intent/ranking; no executable exposure guarantee |
| Capital Deployment / Position Sizing | Target notional and quantity candidate evidence |
| Runtime Planning | Map quantity to execution intent and attach deterministic feasibility evidence |
| Pending | Must not be APPROVED without feasibility PASS or explicit REVIEW contract |
| Submit | Final hard guard before broker boundary |

For 2022-07-25, the relevant values should be aligned across Runtime Planning, Pending, and Submit:

```text
portfolio_value = 950,740
cash = 265,230
market_value = 685,510
current_exposure = 685,510
remaining_exposure = 164,490
planned_buy = 166,400
planned_sell = 88,800
```

## 9. Planning Preflight Contract

Question:

```text
Can Planning create orders that deterministic Submit Guard will reject?
```

Answer:

```text
NO
```

Required deterministic preflight checks:

```text
cash
buying_power
current_exposure + planned BUY amount <= active max_exposure
planned BUY amount <= active max_position_weight notional
max_buy_order_amount when configured
position count when active
Safety action permission
listed issue and opportunity row authority
Pending reservation / duplicate evidence when available
```

Evidence:

```text
reports/phase24_hs_upstream_planning_exposure_preflight_and_partial_submit_lifecycle_contract_review/planning_preflight_contract.json
```

## 10. Partial Submit Contract

Frozen contract:

```text
PLAN_INTEGRITY_AT_APPROVAL
ITEM_LEVEL_HARD_GUARD_AT_SUBMIT
FAIL_CLOSED_ON_PARTIAL_OUTCOME
```

For BUY BLOCK / SELL ACCEPT:

| Topic | Contract |
|---|---|
| BUY Block | BUY remains NOT_SUBMITTED / BLOCKED |
| SELL Accept | SELL acceptance may stand if quantity and broker availability passed |
| Runtime Continue | No automatic continuation in current long-run validation profile |
| Runtime HALT | Yes when stop_on_review_required=true |
| Pending Consume | Do not consume whole Pending as success |
| Approval Hash | Preserve as evidence; partial outcome breaks full-plan completion |

Partial submit is not approved as an automatic continuation feature in this task. Formal partial lifecycle support is deferred to a separate design/implementation task if needed.

Evidence:

```text
reports/phase24_hs_upstream_planning_exposure_preflight_and_partial_submit_lifecycle_contract_review/partial_submit_contract.json
```

## 11. Design Options

| Option | Judgment |
|---|---|
| Option A: Planning checks Submit Feasibility | Selected |
| Option B: Planning -> Submit Reject -> Planning Bug only | Rejected as final design |
| Option C: Formal Partial Submit Support | Deferred |
| Option D: Preserve Planning / Submit responsibility separation | Required constraint with Option A |

Recommended design:

```text
Option A with Option D constraints
```

This keeps Submit Guard hard and final while preventing deterministic invalid orders from becoming APPROVED Pending.

Evidence:

```text
reports/phase24_hs_upstream_planning_exposure_preflight_and_partial_submit_lifecycle_contract_review/design_options.json
```

## 12. Architecture Review

Reviewed:

```text
docs/02_architecture/runtime_architecture_v2.md
docs/02_architecture/strategy_architecture_v1.md
docs/02_architecture/autonomous_ai_operations_architecture.md
docs/phase_reports/phase22_f_capital_deployment.md
docs/phase_reports/phase22_j_position_sizing.md
docs/phase_reports/phase22_g_runtime_planning.md
docs/phase_reports/phase24_hr_capital_deployment_submit_guard_exposure_authority_audit.md
```

Architecture findings:

```text
Submit Guard hard boundary = CONFORMANT
BUY/SELL guard separation = CONFORMANT
Dynamic Strategy exposure DRAFT/NOT_ELIGIBLE = CONFORMANT
Planning/Pending/Submit unit consistency = NEXT IMPLEMENTATION REQUIRED
```

Evidence:

```text
reports/phase24_hs_upstream_planning_exposure_preflight_and_partial_submit_lifecycle_contract_review/architecture_review.json
```

## 13. Contract Freeze

Frozen:

```text
Canonical Exposure Owner = Submit Guard hard authority from CapitalDeploymentPolicy + Runtime Current
Planning Responsibility = deterministic submit feasibility proof before APPROVED Pending
Submit Responsibility = final hard pre-broker guard
Partial Submit = fail-closed review state, not automatic continuation
```

## 14. Next Task

```text
Phase24-HT Planning Submit Feasibility Preflight Evidence Implementation
```

Scope:

```text
Add Production/Demo/Historical common Planning/Pending preflight evidence
using the canonical Submit exposure authority.
Do not weaken Submit Guard.
Do not change max_exposure, target exposure, cash reserve, BUY quantity,
Position Sizing, Portfolio Policy, Strategy, or PM.
```

## 15. Validation

Validation required:

```text
JSON validity
Evidence consistency
git diff --check
```

Runtime Test:

```text
NOT RUN
```

## 16. Files Created

```text
docs/phase_reports/phase24_hs_upstream_planning_exposure_preflight_and_partial_submit_lifecycle_contract_review.md
reports/phase_reports/phase24_hs_upstream_planning_exposure_preflight_and_partial_submit_lifecycle_contract_review.json
reports/phase24_hs_upstream_planning_exposure_preflight_and_partial_submit_lifecycle_contract_review/
```
