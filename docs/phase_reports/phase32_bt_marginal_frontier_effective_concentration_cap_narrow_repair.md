# Phase32-BT Marginal Frontier Effective Concentration Cap Narrow Repair

## Executive Summary

Phase32-BT repaired the Phase32-BS Strategy concentration-cap propagation gap
in `canonical_marginal_capital_frontier_authority.v1`.

The root defect was:

```text
2022-10-11 94340
Strategy cap = 0.18
Safety hard cap = 0.25
effective cap = 0.18

frontier candidate cap used before BT = 0.25 fallback
lot #3 post_weight = 0.1875299199
lot #3 incorrectly accepted under Safety cap while breaching Strategy cap
```

BT now resolves and materializes:

```text
effective_single_name_cap = min(strategy cap, safety hard cap)
```

for every NEW / REENTRY / ADD candidate before feasibility is evaluated.
Implicit `0.25` fallback was removed from the marginal frontier path. Missing
or ambiguous cap evidence now fail-closes as `REVIEW_REQUIRED`.

Post-BT read-only reproduction of the saved BQ/BRS target artifacts:

```text
94340 lot #1: 700 -> 900, post_weight 0.13004064, PASS
94340 lot #2: 900 -> 1100, post_weight 0.1587852799, PASS
94340 lot #3: 1100 -> 1300, post_weight 0.1875299199, INFEASIBLE_CAP_BLOCKED

BF boundary = PASS
94340 aggregated final target quantity = 1100
94340 aggregated final quantity delta = 400
```

No fresh-run, resume, replay, or backtest was executed.

## Required Inputs

Read:

- `docs/phase_reports/phase32_bs_multi_lot_add_concentration_cap_boundary_audit.md`
- `docs/phase_reports/phase32_br_add_repeated_lot_quantity_consistency_narrow_repair.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`

Relevant SoT boundary:

```text
Portfolio Construction remains allocation and Strategy concentration authority.
Position Sizing remains executable quantity authority.
Safety remains hard guardrail authority.
Strategy target and Safety hard limit are separate authorities.
```

## Changed Files

```text
src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py
tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py
tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py
tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py
docs/phase_reports/phase32_bt_marginal_frontier_effective_concentration_cap_narrow_repair.md
```

`marginal_capital_frontier_authority.py` was not changed in BT; the BR boundary
guard remains intact.

## Repair Boundary

The narrow production-shaped source repair is inside:

```text
common_marginal_capital_frontier_shadow.build_canonical_marginal_capital_frontier_payload()
common_marginal_capital_frontier_shadow._security_candidate()
common_marginal_capital_frontier_shadow._feasibility()
```

The new cap authority section is:

```text
effective_single_name_cap_authority:
  status: PASS | REVIEW_REQUIRED
  authority_type: EFFECTIVE_SINGLE_NAME_CONCENTRATION_CAP_AUTHORITY
  strategy_single_name_cap
  safety_hard_cap
  effective_single_name_cap
  cap_source_role
  source_observations
  future_information_used: false
  historical_outcome_used: false
```

Resolution order:

```text
1. PC Strategy concentration authority
   - single_name_weight_cap
   - strategy_maximum_position_weight
   - strategy_single_name_cap

2. PS preflight effective/safety cap evidence
   - effective_maximum_position_weight
   - strategy_maximum_position_weight
   - safety_maximum_position_weight

3. Safety hard cap payload
   - safety_maximum_position_weight
   - maximum_position_weight
   - max_position_weight
```

When both Strategy and Safety are available:

```text
effective_single_name_cap = min(strategy_single_name_cap, safety_hard_cap)
```

When PS preflight provides `effective_maximum_position_weight`, the resolver
checks it against the computed `min(strategy, safety)` and fail-closes on
conflict.

For focused historical unit fixtures only, an explicit member-level
`single_name_cap` remains accepted as row-scoped PC cap evidence when no
top-level cap authority is present. The implicit `0.25` fallback is no longer
used.

## 2022-10-11 94340 Actual Artifact Reproduction

Input artifacts:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T161503510098Z/daily/2022-10-11/strategy/portfolio_construction.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T161503510098Z/daily/2022-10-11/strategy/position_sizing_preflight.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260828T161503510098Z/daily/2022-10-11/strategy/marginal_capital_frontier_authority.json
```

Source cap evidence:

```text
PC single_name_weight_cap = 0.18
PS strategy_maximum_position_weight = 0.18
PS safety_maximum_position_weight = 0.25
PS effective_maximum_position_weight = 0.18
effective derivation = min(strategy_maximum_position_weight, safety_maximum_position_weight)
```

Post-BT reproduction:

```text
authority_result.status = PASS
authority_result.accepted_target_count = 6
pc_to_ps_consumer_switch_boundary.status = PASS
pc_to_ps_consumer_switch_boundary.review_reasons = []
pc_to_ps_consumer_switch_boundary.aggregated_ps_target_count = 5
```

94340 lot trace:

| Lot | Pre qty | Post qty | Pre weight | Post weight | Effective cap | Feasibility | Authority disposition |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | 700 | 900 | 0.101296 | 0.13004064 | 0.18 | `PASS` | `ACCEPTED_INCREMENTAL_TARGET` |
| 2 | 900 | 1100 | 0.13004064 | 0.1587852799 | 0.18 | `PASS` | `ACCEPTED_INCREMENTAL_TARGET` |
| 3 | 1100 | 1300 | 0.1587852799 | 0.1875299199 | 0.18 | `FAIL` / `cap_blocked` | `INFEASIBLE_CAP_BLOCKED` |

94340 BF aggregate:

| Field | Value |
| --- | ---: |
| `current_quantity` | 700 |
| `final_quantity_delta` | 400 |
| `final_target_quantity` | 1100 |

BR quantity progression is preserved: lot #3 is still materialized as
`1100 -> 1300`; it is simply blocked before acceptance by the effective
Strategy concentration cap.

## Focused Test Coverage

Added / updated checks:

- 94340 saved-artifact reproduction: `700 -> 900` PASS, `900 -> 1100` PASS,
  `1100 -> 1300` cap blocked at 18%.
- Safety hard cap preservation: with Strategy cap 30% and Safety cap 25%,
  a lot crossing 25% is `INFEASIBLE_CAP_BLOCKED`.
- Strategy cap absent: fail-closed `REVIEW_REQUIRED`.
- Ambiguous Strategy cap: fail-closed `REVIEW_REQUIRED`.
- NEW / REENTRY candidates consume the same effective cap contract.
- BR quantity progression and BF net aggregation tests remain intact under
  explicit high-cap fixtures.
- BG/BO PIT provenance and legacy fallback-disabled tests remain intact.

## Verification

Focused regression:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py \
  tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py \
  tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py

50 passed
```

Adjacent regression:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py \
  tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py \
  tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py

90 passed
```

BO/BG adjacent regression slice:

```text
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py \
  tests/strategy/test_phase32_au_shadow_frontier_cash_source_resolver.py \
  tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py \
  tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py \
  tests/strategy/test_phase22_j_position_sizing.py \
  tests/strategy/test_phase31_g62_position_sizing_g61_binding.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py

208 passed
```

Compile check:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m py_compile \
  src/ai_fund_lab_v2/strategy/common_marginal_capital_frontier_shadow.py \
  src/ai_fund_lab_v2/strategy/marginal_capital_frontier_authority.py \
  tests/strategy/test_phase32_as_common_marginal_capital_frontier_shadow.py \
  tests/strategy/test_phase32_az_marginal_capital_frontier_authority.py \
  tests/strategy/test_phase32_bg_pc_to_ps_consumer_switch.py

PASS
```

## Scope Preservation

Unchanged:

```text
Cash resolver
allocation budget
marginal value weights / thresholds
PM
PS quantity arithmetic
Runtime mapping
Pending / Orders / Execution
REDUCE / EXIT
Risk Pacing
legacy fallback policy
fixed share / ADD multiplier / position count policy
```

Legacy fallback remains disabled.

## Final Judgments

```text
PHASE32_BT_EFFECTIVE_CAP_PROPAGATED = YES
PHASE32_BT_STRATEGY_CAP_ENFORCED_PER_LOT = YES
PHASE32_BT_SAFETY_CAP_PRESERVED = YES
PHASE32_BT_94340_ACCEPTED_LOTS = 2
PHASE32_BT_94340_FINAL_TARGET_QUANTITY = 1100
PHASE32_BT_CAP_CROSSING_LOT_BLOCKED = YES
PHASE32_BT_BF_BOUNDARY_PASS = YES
PHASE32_BT_REGRESSION_STATUS = PASS
PHASE32_BT_FRESH_VALIDATION_READY = YES
PHASE32_BT_NEXT_STEP = User-operated short fresh validation or resume from the post-BO halted run to confirm 2022-10-11 morning proceeds with 94340 capped at two ADD lots.
```
