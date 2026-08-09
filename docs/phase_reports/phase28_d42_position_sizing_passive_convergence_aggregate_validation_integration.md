# Phase28-D42: Position Sizing Passive-Convergence Aggregate Validation Integration

## Judgment

Primary Judgment:

```text
PHASE28_D42_PS_PASSIVE_CONVERGENCE_AGGREGATE_VALIDATION_INTEGRATED_SHORT_VALIDATION_PASS
```

Supporting Judgment:

```text
PHASE28_D42_PS_AGGREGATE_DIRECTIONALITY_REPAIRED_FRESH_100BD_READY
```

Fresh Test Entry Decision:

```text
READY
```

## Implemented Repair

Position Sizing now consumes Portfolio Construction passive-convergence authority and allows aggregate target weight above dynamic gross exposure only when structured PC evidence proves:

```text
aggregate_exposure_state = OVER_TARGET_EXISTING_BASELINE
transition_mode = PASSIVE_CONVERGENCE
positive_increment_allowed = false
accepted_add_increment <= tolerance
accepted_buy_new_weight <= tolerance
```

The implementation does not infer authorization from reason strings. It reads the canonical structured location:

```text
portfolio_construction.incremental_budget_reconciliation
```

The repair updates both aggregate checks:

```text
build_position_sizing_payload producer_result_status logic
validate_position_sizing_artifact final schema validation
```

True unauthorized aggregate overweight remains fail-closed with:

```text
aggregate_target_weight_above_exposure_cap
```

## Changed Files

Implementation:

```text
src/ai_fund_lab_v2/strategy/position_sizing.py
```

Tests:

```text
tests/strategy/test_phase22_j_position_sizing.py
```

Reports:

```text
docs/phase_reports/phase28_d42_position_sizing_passive_convergence_aggregate_validation_integration.md
reports/phase_reports/phase28_d42_position_sizing_passive_convergence_aggregate_validation_integration.json
reports/phase28_d42_position_sizing_passive_convergence_aggregate_validation_integration/
```

Roadmap:

```text
docs/01_requirements/phase_roadmap.md
```

No config, schema, or threshold change was made.

## 2023-06-01 Replay

Target:

```text
run_id = runtime-test-historical-smoke-20260807T075946923450Z
business_date = 2023-06-01
```

Result:

```text
producer_result_status = PASS
schema validation = PASS
target_gross_exposure_ratio = 0.54
total_target_weight = 0.677443
positions_materialized = 50
aggregate_target_weight_above_exposure_cap absent
aggregate_over_target_passive_convergence_authorized present
```

Target rows:

```text
21340 ADD delta = 0
30410 ADD delta = 0
59550 ADD delta = 0
76470 HOLD delta = 0
94320 ADD delta = 0
38560 NEW target = 0
67310 NEW target = 0
83060 NEW target = 0
93990 REDUCE target_weight = 0.048188
```

## Validation Matrix

```text
2023-06-01 exact replay = PASS
passive convergence aggregate > target = PASS
ADD zero increment over target = PASS
HOLD over target = PASS
BUY_NEW zero allocation = PASS
REDUCE over target = PASS
EXIT over target = PASS
invalid positive increment = BLOCK preserved
missing passive convergence authority = BLOCK preserved
ordinary under-target = PASS
at-target / rounding tolerance = PASS
unauthorized aggregate overweight = BLOCK preserved
D31 regression = PASS
D34 regression = PASS
D36 regression = PASS
D39 compatibility = PASS
BUY/SELL independence = PASS
py_compile = PASS
JSON validation = PASS
git diff --check = PASS
```

Short validation commands:

```text
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase22_j_position_sizing.py -k 'phase28_d42 or phase28_d31 or phase28_d34 or phase22_pw or phase24_ii'
17 passed, 40 deselected

PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase22_j_position_sizing.py
57 passed

PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py -k 'phase28_d39'
7 passed, 36 deselected

PYTHONPYCACHEPREFIX=/Users/negishi/work/ai-fund-lab-v2/.pycache_tmp python3 -m py_compile src/ai_fund_lab_v2/strategy/position_sizing.py
PASS
```

Note: initial `python3 -m py_compile` without `PYTHONPYCACHEPREFIX` was blocked by macOS user cache write permission. Re-running with a workspace pycache prefix passed.

## Architecture Conformance

Portfolio Construction remains the sole producer of passive-convergence authority.

Position Sizing consumes that authority and does not duplicate PC policy logic outside the aggregate validation predicate.

Unchanged:

```text
Portfolio Construction
Portfolio Policy
Position Management
Runtime Planning
Sell Planning
Pending
Approval
Submit
Broker
Config
Schema
Thresholds
```

## Runtime Authority

Runtime authority violation:

```text
NO
```

Execution restrictions:

```text
Resume executed = NO
Fresh run executed = NO
Long Historical executed = NO
Runtime mutation = NO
```

## Evidence

Evidence directory:

```text
reports/phase28_d42_position_sizing_passive_convergence_aggregate_validation_integration/
```

Files:

```text
changed_file_inventory.json
pc_authority_consumption_trace.json
passive_convergence_predicate_validation.json
20230601_reproduction.json
aggregate_validator_validation.json
invalid_positive_increment_validation.json
missing_authority_validation.json
d31_regression.json
d34_regression.json
d36_regression.json
d39_compatibility.json
buy_sell_independence.json
short_regression_results.json
compile_validation.json
architecture_conformance.json
fresh_test_contract.json
open_gap_inventory.json
```

## Open Gaps

No D42 blocking gap remains in short validation.

Next step:

```text
User-run fresh 100BD
```
