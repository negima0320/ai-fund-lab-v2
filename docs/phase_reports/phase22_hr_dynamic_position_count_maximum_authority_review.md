# Phase22-HR Dynamic Position Count Maximum Authority Review

## Primary Judgment

```text
PHASE22_HR_REVIEW_REQUIRED_FOR_SAFETY_HARD_MAXIMUM
```

Legacy active `max_positions=5` and Strategy Dynamic Position Count maximum authority are now separated. `strategy_maximum_position_count` is no longer constrained to the legacy active value and is configured as `8`.

However, an independent Safety hard maximum authority was not found. Therefore Dynamic Position Count cannot be production-ready `PASS`; it remains shadow-only and `REVIEW_REQUIRED` until Safety hard maximum is formally defined.

Runtime switch ready: `NO`.
Legacy retirement ready: `NO`.

## Reviewed Sources

- `docs/phase_reports/phase21_k_final_design_freeze_phase21_closure_and_phase22_entry_approval.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/03_ai_design/portfolio_manager_policy_design.md`
- `docs/03_ai_design/capital_deployment_design.md`
- `docs/phase_reports/phase22_h_dynamic_position_count.md`
- `docs/phase_reports/phase22_f_capital_deployment.md`
- `docs/phase_reports/phase22_e_portfolio_construction.md`
- `src/ai_fund_lab_v2/strategy/dynamic_position_count.py`
- `configs/strategy/dynamic_position_count.json`
- `schemas/strategy/dynamic_position_count.schema.json`
- `src/ai_fund_lab_v2/runtime_v2/policy/capital_deployment.py`
- `configs/runtime_v2/capital_deployment.json`
- `configs/runtime_v2/capital_deployment_demo.json`

## Legacy Max Authority

Evidence:

```text
reports/phase22_hr_dynamic_position_count_maximum_authority_review/phase22_hr_evidence_20260727/legacy_max_authority_inventory.json
```

`max_positions=5` is an active Runtime / Capital Deployment policy limit. It is used by current Morning Planning slot calculation and appears in Submit / Pending metadata paths.

It is not proven to be:

- independent Safety hard maximum
- Broker limit
- Japanese market absolute limit
- formally justified Strategy maximum

Therefore Phase22-HR must not treat the legacy `5` as Safety hard maximum.

## Safety Hard Maximum

Evidence:

```text
reports/phase22_hr_dynamic_position_count_maximum_authority_review/phase22_hr_evidence_20260727/safety_hard_max_inventory.json
```

Finding:

```text
safety_hard_maximum_status = REVIEW_REQUIRED
safety_hard_maximum = null
```

No separate Safety Layer position-count hard cap authority was identified. This is the reason for the primary judgment.

## Strategy Maximum

Evidence:

```text
reports/phase22_hr_dynamic_position_count_maximum_authority_review/phase22_hr_evidence_20260727/strategy_max_rationale.json
```

Updated config:

```text
configs/strategy/dynamic_position_count.json
```

Key fields:

```text
legacy_active_max_positions_reference = runtime_v2.capital_deployment.max_positions
strategy_minimum_position_count = 0
strategy_maximum_position_count = 8
safety_hard_maximum_reference = OPEN_DESIGN_DECISION
safety_hard_maximum_status = REVIEW_REQUIRED
```

`strategy_maximum_position_count=8` is not a PnL-optimized result and not a claim of production acceptance. It is an explicit Strategy capacity ceiling that proves the Dynamic Position Count artifact is no longer mechanically capped by legacy `5`. Candidate and Opportunity capacity still constrain target count.

## Capital Capacity

Evidence:

```text
reports/phase22_hr_dynamic_position_count_maximum_authority_review/phase22_hr_evidence_20260727/capital_capacity_analysis.json
```

Capital affordability is not decided in HR:

```text
affordable_position_count = DEFERRED_TO_PHASE22_I_J
```

HR does not decide target cash, exposure, position sizing, JPY allocation, share quantity, or lot rounding.

## Authority Contract

Evidence:

```text
reports/phase22_hr_dynamic_position_count_maximum_authority_review/phase22_hr_evidence_20260727/authority_separation_validation.json
```

Separated fields:

```text
legacy_active_max_positions = 5
strategy_minimum_position_count = 0
strategy_target_position_count = shadow/review-required
strategy_maximum_position_count = 8
safety_hard_maximum = null
safety_hard_maximum_status = REVIEW_REQUIRED
available_candidate_count = input capacity
available_opportunity_count = input capacity
affordable_position_count = DEFERRED
```

Required relation is enforced when Safety hard maximum is resolved:

```text
strategy_target <= strategy_maximum
strategy_maximum <= safety_hard_maximum
strategy_target <= available_candidate_count
strategy_target <= available_opportunity_count
```

When Safety hard maximum is unresolved, production-ready count is not allowed to PASS.

## Config / Artifact Changes

Config now separates:

```text
legacy_active_max_positions_reference
strategy_minimum_position_count
strategy_maximum_position_count
safety_hard_maximum_reference
safety_hard_maximum_status
```

Artifact now emits:

```text
legacy_active_max_positions
strategy_minimum_position_count
strategy_target_position_count
strategy_maximum_position_count
safety_hard_maximum
safety_hard_maximum_status
ceiling_authority_status
difference_from_legacy_ceiling
```

Shadow artifact evidence:

```text
reports/phase22_hr_dynamic_position_count_maximum_authority_review/phase22_hr_evidence_20260727/dynamic_position_count_hr_shadow_artifact.json
```

Observed:

```text
producer_result_status = REVIEW_REQUIRED
ceiling_authority_status = REVIEW_REQUIRED
difference_from_legacy_ceiling = 3
```

## Failure Contract

Implemented / tested:

| Case | Result |
|---|---|
| Safety hard maximum undefined | `REVIEW_REQUIRED` |
| Legacy max reused as Safety hard max | `BLOCK` |
| Strategy max > resolved Safety max | `BLOCK` |
| invalid count hierarchy | schema error / `BLOCK` |
| config missing | `REVIEW_REQUIRED` |
| hash/date mismatch | `BLOCK` |

Missing input does not fall back to `5`.

## Runtime Preservation

Evidence:

```text
reports/phase22_hr_dynamic_position_count_maximum_authority_review/phase22_hr_evidence_20260727/runtime_preservation.json
```

Unchanged:

- Runtime `CapitalDeploymentPolicy.max_positions=5`
- Morning Planning available-slot calculation
- ADD Planning
- Sell Planning
- Pending
- Submit
- Approval
- Execution

No Runtime switch was performed.

## Tests

PASS:

```text
python3 -m pytest tests/strategy/test_phase22_h_dynamic_position_count.py
```

Result:

```text
11 passed
```

PASS:

```text
python3 -m pytest tests/strategy/test_phase22_a_market_context.py ... tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py
```

Result:

```text
111 passed
```

PASS:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache_phase22hr python3 -m compileall src/ai_fund_lab_v2/strategy tests/strategy
```

Covered:

- Legacy max and Strategy max separation
- Legacy max and Safety hard max separation
- Strategy maximum greater than 5
- Safety cap undefined -> `REVIEW_REQUIRED`
- Legacy 5 implicit Safety cap -> `BLOCK`
- Strategy maximum above resolved Safety maximum -> `BLOCK`
- Runtime max unchanged
- Runtime behavior unchanged

## Long Tests Not Executed

Not executed:

- 5BD
- 20BD
- 200BD
- 1-year
- 3-year
- long runtime smoke

## Acceptance

Accepted:

- Legacy max authority identified
- Safety hard max authority reviewed and marked unresolved
- Strategy maximum evidence recorded
- Legacy max / Strategy max / Safety max separated
- Strategy maximum is no longer constrained to legacy 5
- Runtime max and behavior preserved
- Runtime switch not performed
- Legacy retirement not performed
- Required report / JSON / evidence produced

Remaining review item:

```text
Independent Safety hard maximum authority must be formally defined.
```

## Next Gate

```text
Phase22-H Closure: NO
Phase22-I Entry: NO for production-ready count
Runtime switch ready: NO
Legacy retirement ready: NO
```

Phase22-I can only proceed as a read-only foundation if the gate explicitly accepts unresolved Safety hard maximum as a known upstream review item.
