# Phase24-HR Capital Deployment vs Submit Guard Exposure Authority Audit

## 1. Executive Summary

Phase24-HR audited the 2022-07-25 Submit HALT from the Operator 20BD revalidation run.

The BUY block is an expected valid Submit Guard exposure block under the active Capital Deployment Policy:

```text
current_exposure = 685,510
max_exposure = 850,000
remaining_max_exposure = 164,490
BUY 66590 estimated_amount = 166,400
overage = 1,910
```

The root issue is not Phase24-H cost basis, Safety, Pending, Eligibility, or a Submit Guard threshold defect. The unresolved system issue is that upstream planning approved a BUY that the active Submit hard guard must reject, while the same Pending also contained a valid SELL that was accepted. This exposes a partial submit lifecycle contract gap.

No code or configuration repair was performed.

## 2. Primary Judgment

```text
PHASE24_HR_EXPECTED_VALID_EXPOSURE_BLOCK_UPSTREAM_PLANNING_REVIEW_REQUIRED_WITH_PARTIAL_SUBMIT_CONTRACT_GAP
```

## 3. Scope and Constraints

Audited:

```text
Market Context
Portfolio Policy
Portfolio Construction
Capital Deployment
Position Sizing
Runtime Planning
Pending
Submit Guard
```

Not changed:

```text
max_exposure
target exposure
cash reserve
position sizing
BUY quantity
Portfolio Policy
Capital Deployment
Submit Guard threshold
Strategy maximum
Safety hard maximum
Phase24-H cost basis repair
```

No historical-only, date-specific, run-specific, symbol-specific, fixture-specific, or test-only branch was added.

## 4. Failed Runtime Identity

```text
run_id = runtime-test-historical-extended-smoke-20260731T052507224758Z
profile = historical-extended-smoke
requested_business_days = 20
completed_business_days = 15
halt_business_date = 2022-07-25
halt_job = submit
fresh_run_status = HALT
fresh_run_exit_code = 30
submit_exit_code = 20
```

Primary evidence:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260731T052507224758Z
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260731T052507224758Z/daily/2022-07-25/submit/runtime_manifest.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260731T052507224758Z/daily/2022-07-25/submit/cli_result.json
```

## 5. Confirmed Submit Evidence

Pending:

```text
state = APPROVED
approved_item_count = 2
```

BUY item:

```text
symbol = 66590
side = BUY
quantity = 1600
estimated_price = 104
estimated_amount = 166,400
capital_allocation_amount = 166,400
opportunity_rank = 4
opportunity_eligibility = BUY_ELIGIBLE
safety = PASS
submit_guard = BLOCKED
reason = estimated amount exceeds remaining max_exposure
```

SELL item:

```text
symbol = 23880
side = SELL
quantity = 800
estimated_price = 111
estimated_amount = 88,800
submit_status = ACCEPTED
```

Submit result:

```text
submitted_count = 1
blocked_count = 1
review_required = true
reason = submit completed with rejected/unknown/blocked items
```

## 6. Exposure Authority Inventory

Active Submit exposure authority:

```text
policy_source = configs/runtime_v2/capital_deployment.json
policy_version = capital_deployment_v1
max_exposure = 850,000
```

Current exposure authority:

```text
source = .runtime/persistent_ledger/state.json
formula = sum(positions[].market_value)
current_exposure = 685,510
```

Strategy dynamic exposure:

```text
portfolio_policy.target_gross_exposure_ratio = 0.79
portfolio_policy.maximum_gross_exposure_ratio = 0.88
artifact_lifecycle_status = DRAFT
runtime_consumer_eligibility = NOT_ELIGIBLE
```

Detailed evidence:

```text
reports/phase24_hr_capital_deployment_submit_guard_exposure_authority_audit/exposure_authority_inventory.json
reports/phase24_hr_capital_deployment_submit_guard_exposure_authority_audit/exposure_ownership_matrix.json
```

## 7. 2022-07-25 Exposure Reconstruction

Before submit:

```text
portfolio_value = 950,740
cash = 265,230
market_value = 685,510
current_gross_exposure = 685,510
current_net_exposure = 685,510
configured_max_exposure = 850,000
remaining_max_exposure = 164,490
```

Pending:

```text
BUY 66590 = 166,400
SELL 23880 = 88,800
```

Projected exposure:

```text
BUY only = 851,910
SELL only = 596,710
SELL then BUY = 763,110
```

Judgment:

```text
BUY only exceeds max_exposure by 1,910.
SELL then BUY would be under max_exposure, but current Submit Guard does not pre-credit same-day SELL exposure reduction before fill.
```

Detailed evidence:

```text
reports/phase24_hr_capital_deployment_submit_guard_exposure_authority_audit/2022_07_25_exposure_reconstruction.json
```

## 8. Capital Deployment Calculation

Capital Deployment for BUY 66590 was effectively derived from Phase22 Position Sizing:

```text
target_weight = 0.18
portfolio_value = 950,740
target_notional = 171,133.2
reference_price = 104
lot-rounded quantity = 1600
planned BUY notional = 166,400
```

The standalone Capital Deployment Decision Artifact is not materialized. Runtime Planning records:

```text
capital_deployment = MERGED_INTO_RUNTIME_PLANNING
```

No evidence was found that same-day SELL 88,800 was credited to BUY capacity upstream.

## 9. Submit Guard Calculation

Submit Guard BUY formula:

```text
current_state["current_exposure"] + estimated_amount > policy.max_exposure
```

Applied:

```text
685,510 + 166,400 = 851,910
851,910 > 850,000
```

Result:

```text
guard_decision = BLOCKED
violated_policy = max_exposure
violated_policy_source = configs/runtime_v2/capital_deployment.json
should_have_been_blocked_at_planning = true
```

The calculation uses market value, not cost basis.

## 10. Same-Day BUY / SELL Semantics

Observed contract:

```text
Submit iterates approved_item_ids item-by-item.
BUY and SELL are evaluated independently.
SELL is not credited to BUY exposure capacity before execution/fill.
SELL validates current/broker-available quantity.
BUY validates cash, buying_power, max_exposure, position weight, and buy order cap.
```

For this Pending:

```text
approved_item_ids = [BUY 66590, SELL 23880]
BUY = BLOCKED
SELL = ACCEPTED
Pending = REVIEW_REQUIRED
Runtime test = HALT because stop_on_review_required=true
```

Detailed evidence:

```text
reports/phase24_hr_capital_deployment_submit_guard_exposure_authority_audit/same_day_buy_sell_semantics.json
```

## 11. Architecture and Policy Version Comparison

Conformant:

```text
Submit Guard validates Pending before broker boundary.
BUY and SELL notional/quantity guards are separated.
Submit Guard did not shrink BUY quantity.
Submit Guard did not widen max_exposure.
Dynamic Strategy exposure remains DRAFT / NOT_ELIGIBLE.
```

Review required:

```text
Planning/Pending can approve a BUY that active Submit hard exposure will reject.
Partial submit lifecycle is unresolved when one item is accepted and another is blocked.
```

Detailed evidence:

```text
reports/phase24_hr_capital_deployment_submit_guard_exposure_authority_audit/architecture_conformance.json
```

## 12. Root Cause

Primary root cause:

```text
PARTIAL_SUBMIT_CONTRACT_GAP
```

Secondary classification:

```text
EXPECTED_VALID_GUARD_BLOCK
```

Explanation:

```text
Submit Guard correctly blocked BUY because pre-submit exposure plus BUY
amount exceeded active max_exposure. The unresolved system behavior is
that SELL was accepted while BUY was blocked, leaving Pending in
REVIEW_REQUIRED and causing the runtime_test profile to HALT.
```

Not root causes:

```text
PHASE24_H_REGRESSION
MARKET_VALUE_COST_BASIS_CONFUSION
PENDING_BUY_DOUBLE_COUNT
hidden Submit-only max_exposure drift
Safety Authority failure
Eligibility failure
SELL quantity failure
```

Detailed evidence:

```text
reports/phase24_hr_capital_deployment_submit_guard_exposure_authority_audit/root_cause_analysis.json
```

## 13. Expected Block vs Runtime Defect Judgment

BUY exposure block:

```text
EXPECTED VALID GUARD BLOCK
```

Submit Guard authority defect:

```text
NO
```

Runtime correctness defect:

```text
NO for BUY guard calculation.
REVIEW_REQUIRED for partial submit lifecycle semantics.
```

Architecture/authority divergence:

```text
NO active max_exposure policy divergence.
YES upstream planning/submit acceptance boundary review required.
```

## 14. Repair Decision

```text
NO_CODE_REPAIR_IN_PHASE24_HR
```

Reason:

```text
The BUY block is correct under active Submit hard max_exposure.
Repairing it by widening max_exposure, pre-crediting SELL proceeds,
shrinking BUY quantity, or ignoring remaining exposure would weaken guard
semantics without an approved contract.
```

Detailed decision:

```text
reports/phase24_hr_capital_deployment_submit_guard_exposure_authority_audit/repair_decision.json
```

## 15. Implementation Change if Required

No implementation change was made.

No changes to:

```text
src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py
src/ai_fund_lab_v2/runtime_v2/submit/guards.py
configs/runtime_v2/capital_deployment.json
configs/safety/portfolio_limits.json
strategy configs
Phase24-H cost basis implementation
```

## 16. Regression Validation

Validation performed:

```text
python3 -m pytest tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase17_bv14_market_status_buy_eligibility_guard.py tests/runtime_v2/test_phase24_h_cost_basis_authority.py -q
16 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase24hr_pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py src/ai_fund_lab_v2/runtime_v2/submit/guards.py src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py
compile pass
```

Detailed matrix:

```text
reports/phase24_hr_capital_deployment_submit_guard_exposure_authority_audit/regression_test_matrix.json
```

## 17. Phase24-H Non-Regression

Phase24-H cost basis repair is preserved.

No evidence indicates that open cost basis, average price, realized PnL, unrealized PnL, quantity, cash, market value, or fill notional caused the HALT.

Exposure uses:

```text
positions[].market_value
```

It does not use:

```text
positions[].cost_basis
positions[].average_price
```

## 18. Runtime Revalidation Gate

Do not rerun the same 20BD Runtime gate yet.

Next rerun should wait until the upstream planning exposure preflight and partial submit lifecycle contract are reviewed. Re-running the same profile before that will likely reproduce the same valid BUY block / partial submit HALT.

## 19. Remaining Gaps

Remaining gaps:

```text
Standalone Capital Deployment Decision Artifact is not materialized.
Submit Guard does not materialize numeric remaining_max_exposure in guard evidence, though it is derivable.
Same-day SELL crediting policy for BUY capacity is not explicitly contracted.
Partial submit lifecycle after SELL accepted / BUY blocked is not explicitly contracted.
Planning can approve a BUY that active Submit Guard marks should_have_been_blocked_at_planning=true.
```

## 20. Recommended Next Task

```text
Phase24-HS Upstream Planning Exposure Preflight and Partial Submit Lifecycle Contract Review
```

This must be completed before:

```text
PM Profit Retention implementation
Re-entry Control implementation
Opportunity threshold change
Position sizing change
Portfolio exposure tuning
```

## 21. Files Created or Updated

Created:

```text
docs/phase_reports/phase24_hr_capital_deployment_submit_guard_exposure_authority_audit.md
reports/phase_reports/phase24_hr_capital_deployment_submit_guard_exposure_authority_audit.json
reports/phase24_hr_capital_deployment_submit_guard_exposure_authority_audit/
```

Updated:

```text
docs/01_requirements/phase_roadmap.md
```
