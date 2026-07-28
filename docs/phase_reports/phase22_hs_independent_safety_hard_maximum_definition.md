# Phase22-HS Independent Safety Hard Maximum Definition

## Primary Judgment

```text
PHASE22_HS_INDEPENDENT_SAFETY_HARD_MAXIMUM_DEFINED
```

Independent Safety position-count hard maximum is formally defined:

```text
safety_hard_maximum = 10
authority_owner = Safety Layer
override_allowed = false
effective_scope = production / demo / historical
```

This resolves the Phase22-HR gap without using legacy active `max_positions=5` as Safety authority. Runtime switch was not performed, and current Runtime `CapitalDeploymentPolicy.max_positions=5` remains active.

## Reviewed SoT

- `docs/phase_reports/phase21_k_final_design_freeze_phase21_closure_and_phase22_entry_approval.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/03_ai_design/portfolio_manager_policy_design.md`
- `docs/03_ai_design/capital_deployment_design.md`
- `docs/phase_reports/phase22_h_dynamic_position_count.md`
- `docs/phase_reports/phase22_hr_dynamic_position_count_maximum_authority_review.md`
- `docs/phase_reports/phase22_f_capital_deployment.md`
- `docs/phase_reports/phase21_i_cutover_completeness_runtime_wiring_and_regression_preservation_audit.md`
- `docs/phase_reports/phase21_j_legacy_retirement_authority_revocation_and_data_decommission_architecture.md`

## Existing Safety Authority Inventory

Evidence:

```text
reports/phase22_hs_independent_safety_hard_maximum_definition/phase22_hs_evidence_20260727/existing_safety_authority_inventory.json
```

Existing Safety paths reviewed:

- `src/ai_fund_lab_v2/runtime_v2/safety/evaluation.py`
- `src/ai_fund_lab_v2/runtime_v2/safety/producer.py`
- `src/ai_fund_lab_v2/safety_phase11/guards.py`

Existing `MaxExposureGuard` can read `config.max_position_count`, but no independent portfolio position-count hard maximum config existed before this task.

## Broker / Market Limit Inventory

Evidence:

```text
reports/phase22_hs_independent_safety_hard_maximum_definition/phase22_hs_evidence_20260727/broker_market_limit_inventory.json
```

Repository-local formal sources did not identify a Tachibana API or Japanese market absolute holding-count limit. No external limit was guessed, and no broker technical limit was mixed into Strategy maximum.

## Capital Capacity Analysis

Evidence:

```text
reports/phase22_hs_independent_safety_hard_maximum_definition/phase22_hs_evidence_20260727/capital_capacity_analysis.json
```

Basis:

```text
evaluation_capital = 1,000,000 JPY
max_exposure = 850,000 JPY
legacy_active_max_positions = 5
strategy_maximum_position_count = 8
```

At Safety hard maximum `10`, average exposure capacity is `85,000 JPY` per position if fully spread. This is an absolute ceiling, not a sizing formula. Cash / exposure / sizing affordability remains later-phase responsibility.

No backtest PnL, historical return, future return, paper ledger PnL, or selected/bought result was used.

## Candidate Values Comparison

Evidence:

```text
reports/phase22_hs_independent_safety_hard_maximum_definition/phase22_hs_evidence_20260727/candidate_value_comparison.json
```

Compared:

| Candidate | Judgment |
|---:|---|
| 8 | Valid but equal to Strategy maximum, so Safety ceiling and Strategy ceiling would be too tightly coupled |
| 10 | Selected; gives 25% headroom above Strategy maximum 8 while limiting operational and reconciliation load |
| 12 | Rejected for initial Safety hard max due to smaller average capital per position and higher Pending / Submit / reconciliation complexity |

## Selected Safety Hard Maximum

```text
safety_hard_maximum = 10
```

Selection rationale:

- independent from legacy active `5`
- independent from Strategy maximum `8`
- high enough to not mechanically cap Dynamic Position Count at the Strategy ceiling
- low enough to bound concentration, small-position fragmentation, Pending volume, Submit volume, partial-fill complexity, and reconciliation burden
- applicable to Production / Demo / Historical as the same Safety contract

## Authority Owner

Evidence:

```text
reports/phase22_hs_independent_safety_hard_maximum_definition/phase22_hs_evidence_20260727/authority_owner_validation.json
```

Authority owner:

```text
Safety Layer
```

This follows Strategy Architecture v1 and Capital Deployment Design: Strategy owns targets; Safety owns hard limits; Runtime executes without recalculating Strategy or Safety policy.

No Design Change Request is required.

## Config Contract

Added:

```text
configs/safety/portfolio_limits.json
schemas/safety/portfolio_limits.schema.json
src/ai_fund_lab_v2/runtime_v2/safety/portfolio_limits.py
```

Config schema:

```text
portfolio_safety_limits.v1
```

Contract:

```text
position_count.safety_hard_maximum = 10
authority = Safety hard limit
authority_owner = Safety Layer
override_allowed = false
effective_scope = production / demo / historical
```

Config hash is recorded in the machine-readable report and evidence.

## Safety Artifact / Contract

The Safety limit contract is read-only. It does not enforce Runtime behavior in this task.

Contract payload fields include:

```text
schema_version
config_version
config_source
authority_owner
safety_hard_maximum
override_allowed=false
source_references
config_hash
runtime_switch_performed=false
legacy_active_max_positions_changed=false
```

## Dynamic Position Count Update

Updated:

```text
configs/strategy/dynamic_position_count.json
src/ai_fund_lab_v2/strategy/dynamic_position_count.py
schemas/strategy/dynamic_position_count.schema.json
tests/strategy/test_phase22_h_dynamic_position_count.py
```

Dynamic Position Count now references:

```text
safety_hard_maximum_reference = configs/safety/portfolio_limits.json#position_count.safety_hard_maximum
safety_hard_maximum_status = RESOLVED
```

It still remains `DRAFT / REVIEW_REQUIRED / NOT_ELIGIBLE` when Market Context or Portfolio Policy inputs are unresolved.

## Failure Contract

Implemented / tested:

| Case | Result |
|---|---|
| Safety config missing | `REVIEW_REQUIRED` evidence helper / loader error |
| invalid authority owner | `BLOCK` via config validation |
| override_allowed=true | `BLOCK` via config validation |
| safety hard max < strategy max | `BLOCK` |
| legacy 5 reused as Safety value | `BLOCK` |
| invalid config hash | `BLOCK` |
| Production / Demo / Historical scope mismatch | `BLOCK` |
| non-integer / zero / negative value | `BLOCK` |

No missing fallback to `8` or legacy `5` is implemented.

## Runtime Preservation

Evidence:

```text
reports/phase22_hs_independent_safety_hard_maximum_definition/phase22_hs_evidence_20260727/runtime_preservation.json
```

Unchanged:

- Runtime `CapitalDeploymentPolicy.max_positions=5`
- Morning Planning available slots
- ADD Planning
- Sell Planning
- Pending
- Submit
- Approval
- Execution
- Ledger
- Current

Runtime switch: `NO`.

## Tests

PASS:

```text
python3 -m pytest tests/strategy/test_phase22_h_dynamic_position_count.py
```

Result:

```text
13 passed
```

PASS:

```text
python3 -m pytest tests/strategy/test_phase22_a_market_context.py ... tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py
```

Result:

```text
113 passed
```

## Long Tests Not Executed

Not executed:

- 5BD
- 20BD
- 200BD
- 1-year
- 3-year
- long runtime smoke

## Blocking Gaps

None for independent Safety hard maximum definition.

## Non-blocking Gaps

Market Context threshold/source open decisions remain unresolved. This can still keep daily Dynamic Position Count artifacts at `REVIEW_REQUIRED / NOT_ELIGIBLE`, but it is no longer a Safety hard maximum blocker.

## Phase22-H Closure

```text
YES for Safety ceiling and maximum authority.
```

Daily artifact production may still be `REVIEW_REQUIRED` until Market Context is resolved.

## Phase22-I Entry

```text
YES_READ_ONLY_FOUNDATION
```

Phase22-I may proceed as a read-only Dynamic Cash / Exposure foundation while preserving Runtime switch `NO` and legacy retirement `NO`.
