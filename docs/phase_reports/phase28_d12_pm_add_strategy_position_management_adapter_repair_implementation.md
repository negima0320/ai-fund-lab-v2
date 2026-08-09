# Phase28-D12: PM ADD Strategy Position Management Adapter Repair Implementation

## 1. Executive Summary

Primary Judgment:

```text
PHASE28_D12_PM_ADD_STRATEGY_PM_ADAPTER_REPAIRED_SHORT_VALIDATION_PASS
```

Phase28-C Chain Judgment:

```text
PM_ADD_TO_BUY_ADD_FOCUSED_CHAIN_CONFIRMED
```

D12 implemented the single approved D11 repair: Strategy Position Management now accepts Runtime PM canonical fields.

```text
action priority: action -> decision -> decision_type -> UNRESOLVED
decision ref priority: decision_id -> pm_decision_id -> empty
```

No Portfolio Construction, Position Sizing, Runtime Planning, Pending, Approval, Submit, Broker, Summary CLI, config, schema, threshold, or performance condition was changed.

## 2. Scope

Implementation scope:

```text
src/ai_fund_lab_v2/strategy/position_management.py
```

Target adapters:

```text
_positions_from_runtime_current
_positions_from_existing_decisions
```

Test scope:

```text
tests/strategy/test_phase22_d_position_management.py
```

## 3. D11 Design Accepted

D11 concluded:

```text
ADD Producer: Runtime Position Management producer
ADD Consumer: Strategy Position Management runtime_current_position_adapter
First UNRESOLVED Producer: _positions_from_runtime_current
Root Cause: decision_type / pm_decision_id were not consumed
Primary Recommendation: Option A
```

D12 accepted Option A exactly:

```text
Preserve PM ADD in Strategy Position Management.
```

## 4. Pre-implementation Audit

Runtime PM producer fields:

```text
decision_type
pm_decision_id
```

Strategy PM previous fields:

```text
action
decision
decision_id
```

D10 sample:

```json
{
  "symbol": "94320",
  "decision_type": "ADD",
  "pm_decision_id": "pm-2023-04-04-94320-add",
  "action": null,
  "decision": null,
  "decision_id": null
}
```

Previous output:

```text
action = UNRESOLVED
source_pm_decision_ref = ""
```

Portfolio Construction audit:

```text
Portfolio Construction consumes Strategy PM action.
If action = ADD, it maps to RETAIN / INCREASE.
```

## 5. Current Defect

The defect was a field compatibility gap:

```text
Runtime PM canonical artifact:
decision_type=ADD, pm_decision_id=...

Strategy PM adapter:
read action/decision and decision_id only
```

Valid PM ADD was therefore not propagated to Portfolio Construction.

## 6. Implementation

Added helpers:

```text
_normalized_pm_action
_normalized_pm_decision_ref
_pm_action_field_conflicts
_normalized_text
```

Code locations:

```text
src/ai_fund_lab_v2/strategy/position_management.py:1226-1254
```

Both adapters now use the helpers:

```text
_positions_from_existing_decisions: 1265, 1268, 1292
_positions_from_runtime_current: 1322, 1339, 1356
```

## 7. Changed Files

```text
src/ai_fund_lab_v2/strategy/position_management.py
tests/strategy/test_phase22_d_position_management.py
docs/phase_reports/phase28_d12_pm_add_strategy_position_management_adapter_repair_implementation.md
reports/phase_reports/phase28_d12_pm_add_strategy_position_management_adapter_repair_implementation.json
reports/phase28_d12_pm_add_strategy_position_management_adapter_repair_implementation/
docs/01_requirements/phase_roadmap.md
```

## 8. Action Normalization

Priority:

```text
1. action
2. decision
3. decision_type
4. UNRESOLVED
```

Normalization:

```text
trim
upper-case
existing PM_ACTIONS validation
```

Validated Runtime canonical actions:

```text
ADD
HOLD
REDUCE
EXIT
```

## 9. Decision Reference Normalization

Priority:

```text
1. decision_id
2. pm_decision_id
3. empty
```

Expected D10-equivalent behavior:

```text
pm_decision_id = pm-2023-04-04-94320-add
source_pm_decision_ref = pm-2023-04-04-94320-add
```

ID regeneration was not introduced.

## 10. Field Priority

Existing compatibility remains first:

```text
action-only rows keep action.
decision-only rows keep decision.
decision_id remains preferred over pm_decision_id.
```

Runtime canonical compatibility is added only after existing fields:

```text
decision_type
pm_decision_id
```

## 11. Conflict Behavior

Equivalent values:

```text
action=ADD, decision_type=ADD -> ADD
```

Conflicting supported values:

```text
action=HOLD, decision_type=ADD -> HOLD
decision=ADD, decision_type=EXIT -> ADD
```

Priority is preserved, and conflict evidence is materialized:

```text
pm_action_field_conflict:...
```

Unsupported first action value:

```text
decision_type=REBUY -> UNRESOLVED
```

No unsupported value is inferred as ADD.

## 12. Runtime Current Adapter

Adapter:

```text
_positions_from_runtime_current
```

Validated behavior:

```text
decision_type=ADD -> action=ADD
decision_type=HOLD -> action=HOLD
decision_type=REDUCE -> action=REDUCE
decision_type=EXIT -> action=EXIT
pm_decision_id -> source_pm_decision_ref
```

Focused result:

```text
9 passed, 12 deselected
```

## 13. Existing Decisions Adapter

Adapter:

```text
_positions_from_existing_decisions
```

Validated behavior:

```text
decision_type=ADD -> action=ADD
pm_decision_id -> source_pm_decision_ref
action=ADD remains ADD
decision=ADD remains ADD
```

## 14. Reason / Lineage Preservation

Existing PM reason codes are preserved:

```text
reason_codes
decision_reason_codes
```

New evidence is appended only for supported action field conflicts:

```text
pm_action_field_conflict:...
```

Lineage preservation:

```text
decision_id -> source_pm_decision_ref
pm_decision_id -> source_pm_decision_ref when decision_id is absent
```

## 15. Phase28-C Chain Validation

Existing Phase28-C focused regression was run without changing Phase28-C.

Portfolio Construction:

```text
python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py -k phase28_c
2 passed, 23 deselected
```

Position Sizing:

```text
python3 -m pytest -q tests/strategy/test_phase22_j_position_sizing.py -k phase28_c
2 passed, 36 deselected
```

Runtime Planning:

```text
python3 -m pytest -q tests/strategy/test_phase22_g_runtime_planning.py -k "phase27_d2e_runtime_planning_maps_canonical_quantity_delta_to_runtime_action or buy_add"
1 passed, 38 deselected
```

Confirmed focused chain:

```text
PM ADD -> Portfolio Construction pm_action=ADD
ADD -> RETAIN / INCREASE
target_weight increase
positive quantity_delta
existing position + positive delta -> BUY_ADD
```

## 16. Non-ADD Regression

Full Position Management regression:

```text
python3 -m pytest -q tests/strategy/test_phase22_d_position_management.py
21 passed
```

Covered:

```text
HOLD
REDUCE
EXIT
missing decision
true UNRESOLVED
legacy action form
legacy decision form
runtime current adapter
existing decisions adapter
reason trace
schema validation
```

## 17. Focused Fixtures

D10-equivalent focused fixture:

```text
Runtime Current position exists
symbol = 94320
decision_type = ADD
pm_decision_id = pm-2023-04-04-94320-add
action / decision / decision_id absent
```

Result:

```text
Strategy PM action = ADD
source_pm_decision_ref = pm-2023-04-04-94320-add
```

## 18. Short Regression

Short validation total:

```text
26 passed
```

Breakdown:

```text
Position Management: 21 passed
Portfolio Construction Phase28-C: 2 passed
Position Sizing Phase28-C: 2 passed
Runtime Planning BUY_ADD focused: 1 passed
```

No resume, fresh run, or long historical was executed.

## 19. Compile / JSON Validation

Initial compile attempt:

```text
python3 -m py_compile ...
FAILED_ENVIRONMENT_PYCACHE_PERMISSION
```

Reason:

```text
macOS Python attempted to write pyc under /Users/negishi/Library/Caches.
```

Successful compile:

```text
/usr/bin/env PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/position_management.py tests/strategy/test_phase22_d_position_management.py
PASS
```

JSON validation:

```text
PASS
```

## 20. Architecture Conformance

Runtime Authority violation:

```text
false
```

Performance condition changed:

```text
false
```

Conformance:

```text
PM remains existing-position action authority.
PM ADD remains directional intent only.
Portfolio Construction remains target-weight authority.
Position Sizing remains quantity-delta authority.
Runtime Planning remains BUY_ADD mapper.
UNRESOLVED is not read as ADD in Portfolio Construction.
```

## 21. Known Limitations

D12 is a propagation repair only.

It does not prove that the next full historical run will complete, because a known SELL listed_info HALT class remains open.

## 22. Open Gaps

Open:

```text
2023-06-14 submit HALT
symbol = 30410
side = SELL
reason = listed_info_missing
```

Also open:

```text
Summary CLI PM ADD count versus actual BUY_ADD funnel observability
```

Both are intentionally out of D12 scope.

## 23. 2023-06-14 HALT Separation

D12 did not modify:

```text
listed_info producer
SELL pending authority
Submit Guard
Broker normalization
```

The 2023-06-14 / 30410 SELL listed_info gap remains separate and should be repaired next.

## 24. Fresh 100BD Contract

Fresh 100BD should not be run yet.

Reason:

```text
The known 2023-06-14 / 30410 SELL listed_info_missing HALT remains unrepaired.
```

Recommended next repair before fresh 100BD:

```text
Strategy Executable SELL Non-Opportunity listed_info Authority Repair
```

## 25. Final Judgment

```text
Primary Judgment:
PHASE28_D12_PM_ADD_STRATEGY_PM_ADAPTER_REPAIRED_SHORT_VALIDATION_PASS

Phase28-C Chain Judgment:
PM_ADD_TO_BUY_ADD_FOCUSED_CHAIN_CONFIRMED

Implemented Repair:
Strategy PM inbound normalization for action -> decision -> decision_type
and decision_id -> pm_decision_id.

Runtime PM ADD propagation:
confirmed

source_pm_decision_ref:
pm_decision_id preserved when decision_id is absent

Portfolio Construction reached:
confirmed

target weight increase:
confirmed by Phase28-C focused regression

positive quantity delta:
confirmed by Phase28-C Position Sizing regression

BUY_ADD focused chain:
confirmed by Runtime Planning focused regression

HOLD / REDUCE / EXIT regression:
PASS

Runtime Authority violation:
false

Performance condition change:
false

Implementation changed:
true

Config / Schema / Threshold changed:
false / false / false

Resume / Fresh / Long Historical:
false / false / false
```

## 26. Next Phase

```text
Phase28-D13 Strategy Executable SELL Non-Opportunity listed_info Authority Repair
```

Fresh 100BD:

```text
Not yet recommended.
```

Deliverables:

```text
docs/phase_reports/phase28_d12_pm_add_strategy_position_management_adapter_repair_implementation.md
reports/phase_reports/phase28_d12_pm_add_strategy_position_management_adapter_repair_implementation.json
reports/phase28_d12_pm_add_strategy_position_management_adapter_repair_implementation/
```
