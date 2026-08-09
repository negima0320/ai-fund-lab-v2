# Phase28-D11: PM ADD Strategy Artifact Propagation Repair Design

## 1. Task

```text
Task ID: Phase28-D11
Task Type: DESIGN ONLY / READ_ONLY
Implementation: not performed
Config / Schema / Threshold change: not performed
Resume / fresh run / long historical: not performed
```

## 2. Primary Judgment

```text
PHASE28_D11_PM_ADD_STRATEGY_PM_ADAPTER_PROPAGATION_REPAIR_DESIGNED
```

PM ADD disappears before Portfolio Construction.

The first producer that converts the ADD authority signal into `UNRESOLVED` is:

```text
src/ai_fund_lab_v2/strategy/position_management.py
_positions_from_runtime_current
```

This is a Runtime / Strategy artifact propagation defect at the Strategy Position Management adapter boundary.

## 3. Required Documents Reviewed

```text
docs/phase_reports/phase28_d10_pm_add_to_canonical_buy_add_conversion_and_attribution_audit.md
docs/phase_reports/phase28_c_canonical_add_allocation_bridge_implementation.md
docs/phase_reports/phase28_b_incremental_investment_eligibility_and_canonical_add_allocation_design.md
docs/02_architecture/strategy_architecture_v1.md
docs/02_architecture/portfolio_construction_and_position_sizing_contract.md
docs/02_architecture/runtime_architecture_v2.md
docs/01_requirements/phase_roadmap.md
```

D10 established:

```text
PM ADD count: 21
BUY_ADD plan count: 0
first stop: PM_ADD_NOT_PROPAGATED_TO_STRATEGY_POSITION_MANAGEMENT
```

Phase28-C established:

```text
Portfolio Construction and Position Sizing contain the canonical ADD bridge.
The bridge is reached only when Portfolio Construction receives pm_action = ADD.
```

The architecture documents require:

```text
PM ADD remains directional authority.
Portfolio Construction integrates PM ADD into target weight.
Position Sizing turns positive delta into quantity.
Runtime Planning maps existing position + positive delta into BUY_ADD.
```

## 4. Trace Summary

Observed D10 run:

```text
run_id: runtime-test-historical-smoke-20260806T005408544432Z
sample date: 2023-04-04
sample ADD symbol: 94320
```

### 4.1 PM ADD Producer

Producer:

```text
Runtime Position Management producer
src/ai_fund_lab_v2/runtime_v2/position_management/producer.py
```

Code evidence:

```text
producer.py:823-841 emits decision_result.decision_type and top-level decision_type
producer.py:646-648 marks ADD as outside SELL Planning scope, not as SELL
```

Artifact evidence:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260806T005408544432Z/daily/2023-04-04/position_management/pm_decisions.json
```

Observed row:

```json
{
  "symbol": "94320",
  "decision_type": "ADD",
  "decision": null,
  "action": null,
  "pm_decision_id": "pm-2023-04-04-94320-add",
  "decision_id": null,
  "reason_codes": [
    "strong_trend_continuation",
    "opportunity_rank_still_high",
    "no_loss_averaging"
  ]
}
```

Judgment:

```text
PM ADD is generated correctly.
```

## 5. ADD Consumer and First UNRESOLVED Producer

Consumer:

```text
Strategy Position Management
src/ai_fund_lab_v2/strategy/position_management.py
```

Active path:

```text
_positions_from_runtime_current
```

Code evidence:

```text
position_management.py:1271-1275 builds decisions_by_symbol
position_management.py:1287 selects the PM decision for the symbol
position_management.py:1288 reads action from action or decision only
position_management.py:1321 reads source_pm_decision_ref from decision_id only
```

Current code condition:

```python
action = str(decision.get("action") or decision.get("decision") or "UNRESOLVED").upper()
source_pm_decision_ref = str(decision.get("decision_id") or "")
```

The Runtime PM artifact uses:

```text
decision_type = ADD
pm_decision_id = pm-2023-04-04-94320-add
```

It does not provide:

```text
action
decision
decision_id
```

Therefore Strategy PM emits:

```text
action = UNRESOLVED
source_pm_decision_ref = ""
```

Artifact evidence:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260806T005408544432Z/daily/2023-04-04/strategy/position_management.json
```

Observed row:

```json
{
  "security_code": "94320",
  "action": "UNRESOLVED",
  "intensity": "UNRESOLVED",
  "source_pm_decision_ref": "",
  "reason_codes": [
    "runtime_current_position_requires_strategy_pm_evaluation"
  ],
  "adapter_source": "runtime_current_position_adapter",
  "adapter_contract_version": "runtime_current_holdings_to_strategy_pm.v1"
}
```

First null / first loss location:

```text
ADD first disappears in Strategy Position Management.
The exact producer is _positions_from_runtime_current.
```

Fallback path:

```text
_positions_from_existing_decisions
```

This path has the same compatibility gap:

```text
position_management.py:1234 reads action or decision only
position_management.py:1258 reads decision_id only
```

## 6. Portfolio Construction Judgment

Portfolio Construction is not the first failing producer.

Code evidence:

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py
portfolio_construction.py:712 reads pm.action or UNRESOLVED
portfolio_construction.py:713 calls _membership_from_pm_action
portfolio_construction.py:1501-1510 maps ADD to RETAIN / INCREASE
```

Relevant behavior:

```python
if action == "ADD":
    return "RETAIN", "INCREASE"
```

Observed Portfolio Construction row:

```json
{
  "security_code": "94320",
  "pm_action": "UNRESOLVED",
  "membership_intent": "UNRESOLVED",
  "weight_intent": "UNRESOLVED",
  "current_position": true,
  "target_weight": 0.0,
  "reason_codes": [
    "candidate_duplicate_reconciled:94320",
    "pm_action:UNRESOLVED"
  ]
}
```

Judgment:

```text
Portfolio Construction is innocent for D11.
If it receives ADD, it has a valid ADD path.
It is not responsible for reconstructing PM ADD from UNRESOLVED.
```

## 7. Phase28-C Relation

Phase28-C direct causality:

```text
false
```

Reason:

```text
The Phase28-C ADD bridge is gated by pm_action = ADD.
D10/D11 evidence shows ADD is converted to UNRESOLVED in Strategy Position Management before Portfolio Construction.
The bridge is never reached.
```

Phase28-C repair required:

```text
false
```

## 8. Root Cause

```text
Runtime PM producer and Strategy PM consumer use incompatible field names for the same PM action authority.
```

Runtime PM emits:

```text
decision_type
pm_decision_id
```

Strategy PM consumes:

```text
action
decision
decision_id
```

The missing compatibility read causes a valid PM ADD to become:

```text
UNRESOLVED
```

This is not an intended specification behavior. It is a Runtime / Strategy adapter defect.

## 9. Repair Options

### Option A: Preserve ADD in Strategy Position Management

Design:

```text
Normalize inbound Runtime PM decision_type into Strategy PM action.
Preserve pm_decision_id into source_pm_decision_ref when decision_id is absent.
```

Scope:

```text
src/ai_fund_lab_v2/strategy/position_management.py
```

Target functions:

```text
_positions_from_runtime_current
_positions_from_existing_decisions
```

Judgment:

```text
Recommended
```

Reason:

```text
This repairs the first loss point and preserves all downstream authority boundaries.
```

### Option B: Convert UNRESOLVED to ADD in Portfolio Construction

Judgment:

```text
Rejected
```

Reason:

```text
Portfolio Construction would infer PM authority from a missing signal.
True UNRESOLVED rows could become ADD incorrectly.
This fixes the wrong layer.
```

### Option C: Downstream Recovery

Examples:

```text
Position Sizing
Runtime Planning
Pending
Approval
Submit
Summary CLI
```

Judgment:

```text
Rejected
```

Reason:

```text
These paths would recover a symptom after target allocation semantics were already lost.
They are outside D11 allowed scope.
```

## 10. Primary Recommendation

```text
Option A
```

D12 should repair only the Strategy Position Management inbound PM decision adapter.

Required D12 behavior:

```text
action / decision remain supported
decision_type is accepted as compatible inbound PM action
decision_id remains supported
pm_decision_id is accepted as compatible inbound PM decision reference
no downstream layer is changed
```

## 11. Minimal Repair Scope

Only target:

```text
src/ai_fund_lab_v2/strategy/position_management.py
```

Functions:

```text
_positions_from_runtime_current
_positions_from_existing_decisions
```

Suggested design shape:

```text
Introduce or inline a small compatibility normalization:

action = action || decision || decision_type
source_pm_decision_ref = decision_id || pm_decision_id
```

Do not change:

```text
Expected Edge
Incremental Investment Value
Opportunity Cost
Portfolio Construction
Position Sizing
Runtime Planning
Pending
Approval
Submit
Broker
Config
Schema
Threshold
Summary CLI
BUY Quality
Market Context
Corporate Event
Cash Policy
```

## 12. Final Judgment

```text
ADD Producer:
Runtime Position Management producer

ADD Consumer:
Strategy Position Management runtime_current_position_adapter

First UNRESOLVED Producer:
src/ai_fund_lab_v2/strategy/position_management.py::_positions_from_runtime_current

Root Cause:
Runtime PM emits decision_type=ADD / pm_decision_id, while Strategy PM reads only action/decision / decision_id.

Phase28-C Direct Causality:
false

Runtime Defect:
true

Portfolio Construction:
innocent

Minimal Repair Scope:
Strategy Position Management inbound PM decision normalization only.

Primary Recommendation:
Option A

Next Phase:
Phase28-D12 PM ADD Strategy Position Management Adapter Repair Implementation
```

## 13. Deliverables

```text
Main Report:
docs/phase_reports/phase28_d11_pm_add_strategy_artifact_propagation_repair_design.md

Summary:
reports/phase_reports/phase28_d11_pm_add_strategy_artifact_propagation_repair_design.json

Evidence:
reports/phase28_d11_pm_add_strategy_artifact_propagation_repair_design/
```
