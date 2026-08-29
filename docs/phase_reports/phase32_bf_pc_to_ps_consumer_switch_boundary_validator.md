# Phase32-BF PC-to-PS Consumer Switch Boundary Validator

## Executive Summary

Phase32-BF implemented a consumer-disabled PC-to-PS boundary validator inside:

```text
canonical_marginal_capital_frontier_authority.v1
```

The new section is:

```text
pc_to_ps_consumer_switch_boundary
```

It aggregates BC accepted incremental targets into PS-shaped final net target
rows while keeping production consumers disabled. No PM, REDUCE, EXIT, Safety,
Runtime, Pending, Order, Execution, or production Position Sizing logic was
changed.

Primary result:

```text
Boundary implementation PASS.
Actual 50BD read-only validation PASS: 50 / 50 days.
BC accepted lot rows: 301.
BF aggregated PS-boundary rows: 240.
ADD accepted lot rows: 93.
ADD aggregated net target rows: 32.
Legacy zero fallback allowed: 0 rows.
Production consumer count: 0.
```

Consumer switch readiness is `PARTIAL`: the boundary shape is now implemented
and validated, but the production consumer remains disabled by design and a
separate explicit switch phase is still required.

## Required Inputs

Read:

- `docs/phase_reports/phase32_be_consumer_switch_dry_run_validation.md`
- `docs/phase_reports/phase32_bc_budget_bounded_frontier_acceptance_implementation.md`
- `docs/phase_reports/phase32_ay_marginal_capital_frontier_production_migration_design.md`

Implementation targets:

- `src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py`
- `tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`

## Boundary Contract

The BF boundary is PC-owned and consumer-disabled:

```text
schema_version = pc_to_ps_consumer_switch_boundary_validator.v1
owner = PORTFOLIO_CONSTRUCTION
production_consumer_enabled = false
production_consumer_count = 0
feeds_position_sizing = false
feeds_runtime_planning = false
feeds_pending = false
legacy_target_gap_input_used = false
legacy_target_gap_fallback_allowed = false
legacy_zero_fallback_allowed = false
fallback_policy = FAIL_CLOSED_REVIEW_REQUIRED_NO_LEGACY_ZERO_FALLBACK
```

It consumes only the in-artifact BC accepted target rows and capital
conservation evidence. It does not read or consume legacy production target-gap
rows.

## Implemented Aggregation

`accepted_incremental_targets[]` are grouped by:

```text
symbol
semantic_type
position_campaign_id
```

Rules:

- `NEW_FIRST_LOT`: one first-lot final target per symbol.
- `REENTRY_FIRST_LOT`: one first-lot final target per symbol.
- `ADD_NEXT_LOT`: accepted lot #1/#2/#N for the same symbol/campaign are
  netted into one final quantity delta.
- final target quantity must equal current quantity plus final quantity delta.
- aggregate security allocation must match source BC security allocation.

Fail-closed `REVIEW_REQUIRED` conditions:

- missing or invalid authority payload
- production consumer unexpectedly enabled
- source authority result not `PASS`
- source capital conservation not `PASS`
- duplicate accepted target identity
- missing ADD position campaign id
- non-contiguous ADD lot sequence
- duplicate NEW/REENTRY first-lot target for the same symbol
- final quantity delta inconsistency
- aggregated security allocation conservation mismatch

## Actual-Path Read-Only Validation

Target run:

```text
runtime-test-historical-extended-smoke-20260828T000823285458Z
```

No fresh-run, resume, replay, backtest, or runtime state mutation was executed.
The BF boundary was materialized in memory from existing daily artifacts.

Coverage:

| Field | Value |
| --- | ---: |
| Characterized days | 50 |
| Coverage start | `2022-10-03` |
| Coverage end | `2022-12-14` |
| Authority PASS | 50 / 50 |
| Budget authority PASS | 50 / 50 |
| Source capital conservation PASS | 50 / 50 |
| BF boundary PASS | 50 / 50 |

## Target Aggregation Results

BC accepted target rows:

| Type | Accepted lot rows | Quantity delta |
| --- | ---: | ---: |
| `NEW_FIRST_LOT` | 182 | 38,800 |
| `REENTRY_FIRST_LOT` | 26 | 2,600 |
| `ADD_NEXT_LOT` | 93 | 9,300 |
| Total | 301 | 50,700 |

BF aggregated PS-boundary rows:

| Type | Aggregated rows | Quantity delta |
| --- | ---: | ---: |
| `NEW_FIRST_LOT` | 182 | 38,800 |
| `REENTRY_FIRST_LOT` | 26 | 2,600 |
| `ADD_NEXT_LOT` | 32 | 9,300 |
| Total | 240 | 50,700 |

ADD lot acceptance:

| ADD lot | Accepted rows |
| --- | ---: |
| lot #1 | 32 |
| lot #2 | 31 |
| lot #3 | 30 |

Aggregated lot-count distribution:

| Accepted lots per aggregated row | Rows |
| --- | ---: |
| 1 | 209 |
| 2 | 1 |
| 3 | 30 |

Multi-lot net quantity rows:

```text
31
```

## ADD Net Quantity Examples

| Date | Symbol | Campaign | Accepted lots | Current qty | Final target qty | Net delta |
| --- | --- | --- | --- | ---: | ---: | ---: |
| `2022-10-05` | `94340` | `pc-993d47f0f8d7e622-94340-0001` | `[1,2,3]` | 200 | 500 | 300 |
| `2022-10-06` | `94340` | `pc-993d47f0f8d7e622-94340-0001` | `[1,2,3]` | 200 | 500 | 300 |
| `2022-10-07` | `94320` | `pc-e0c5da196f07ea55-94320-0001` | `[1,2,3]` | 200 | 500 | 300 |
| `2022-10-12` | `94320` | `pc-e0c5da196f07ea55-94320-0001` | `[1,2,3]` | 200 | 500 | 300 |
| `2022-10-19` | `94320` | `pc-e0c5da196f07ea55-94320-0001` | `[1,2,3]` | 300 | 600 | 300 |

This resolves the BE caveat: cumulative ADD target rows are not passed onward
as independent baselines. The BF boundary emits one net incremental quantity
per symbol/campaign.

## Lineage / Runtime Mapping

Validation results:

| Check | Result |
| --- | ---: |
| Missing ADD campaign lineage | 0 |
| Runtime/Pending lineage status not PASS | 0 |
| Final quantity delta inconsistency | 0 |
| Aggregated allocation mismatch | 0 |
| Legacy fallback flags set | 0 |
| Production consumer count | 0 |

Each aggregated row preserves:

- `accepted_frontier_candidate_ids`
- `source_pm_decision_ids`
- `source_candidate_ids`
- `source_pc_evidence_ids`
- `position_campaign_id` for ADD

## Capital Conservation

BF aggregation preserves the BC source conservation identity:

```text
sum(aggregated accepted_incremental_weight)
= sum(BC accepted_incremental_targets accepted_incremental_weight)
```

and:

```text
sum(aggregated accepted_incremental_notional)
= sum(BC accepted_incremental_targets accepted_incremental_notional)
```

Result:

```text
PASS: 50 / 50 days
```

## Legacy Fallback Proof

The BF boundary emits explicit fallback-disabled fields at both boundary and
row level:

```text
legacy_target_gap_input_used = false
legacy_target_gap_fallback_allowed = false
legacy_zero_fallback_allowed = false
```

Actual-path validation:

```text
fallback_bad_rows = 0
```

The current production consumer is still OFF, so this is a boundary proof, not
an active production switch.

## Focused Verification

Executed:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py
```

Result:

```text
20 passed
```

Executed:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py tests/strategy/test_phase32_au_shadow_frontier_cash_source_resolver.py
```

Result:

```text
34 passed
```

Executed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m py_compile src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py
```

Result:

```text
PASS
```

Focused BF test coverage includes:

- ADD 3 lots -> net +300 shares
- NEW / REENTRY aggregation
- duplicate target identity fail-closed
- missing authority fail-closed
- legacy zero fallback impossible
- PS final quantity delta consistency
- deterministic rerun
- production consumer remains OFF

## Changed Files

| File | Purpose |
| --- | --- |
| `src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py` | Added BF switch-boundary validator and aggregated PS target rows. |
| `tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py` | Added focused BF regression coverage. |
| `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md` | Added permanent PC-to-PS boundary contract. |
| `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md` | Added permanent BF aggregation/fallback contract. |

## Judgment

No production behavior changed. BF resolves the BE aggregation caveat and
proves that switched rows can be shaped for PS without falling back to legacy
ADD zero / target-gap behavior. A future phase may implement the actual
consumer switch, but it must explicitly enable the consumer and keep the
fail-closed no-fallback policy.

## Final Judgments

```text
PHASE32_BF_TARGET_AGGREGATION_PASS = YES
PHASE32_BF_MULTI_LOT_NET_QUANTITY_PASS = YES
PHASE32_BF_CAMPAIGN_LINEAGE_PASS = YES
PHASE32_BF_PS_BOUNDARY_COMPATIBLE = YES
PHASE32_BF_LEGACY_FALLBACK_ZERO = NO
PHASE32_BF_FAIL_CLOSED_PASS = YES
PHASE32_BF_CAPITAL_CONSERVATION = PASS
PHASE32_BF_PRODUCTION_CONSUMER_ENABLED = NO
PHASE32_BF_CONSUMER_SWITCH_READY = PARTIAL
PHASE32_BF_PRODUCTION_BEHAVIOR_CHANGED = NO
PHASE32_BF_NEXT_STEP = Implement the explicit production consumer switch in a separate phase, keeping BF boundary rows as the only switched target source and treating missing/invalid authority as REVIEW_REQUIRED with no legacy zero fallback.
```
