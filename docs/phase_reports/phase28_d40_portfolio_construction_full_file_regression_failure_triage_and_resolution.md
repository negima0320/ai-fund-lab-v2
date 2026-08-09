# Phase28-D40: Portfolio Construction Full-File Regression Failure Triage and Resolution

## Primary Judgment

```text
PHASE28_D40_PC_FULL_FILE_REGRESSION_CLEAN_FRESH_100BD_READY
```

Fresh Test Entry Decision:

```text
READY
```

## Scope

D40 triaged and resolved the 3 full-file failures left after D39.

No production code, config, schema, threshold, resume, fresh run, long historical run, or runtime mutation was performed.

## Initial Failure Inventory

Initial required command:

```text
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py -q -vv
```

Initial result:

```text
40 passed
3 failed
```

Failing tests:

```text
test_phase23_ao_target_weight_authority_equal_weight_and_cap
test_phase23_ao_negative_new_opportunity_is_not_forced_into_target_membership
test_phase26_a_no_buy_reason_opportunity_is_excluded_without_target_count_slot_limit
```

## Failure 1

```text
test_phase23_ao_target_weight_authority_equal_weight_and_cap
```

Classification:

```text
INVALID_DEFAULT_FIXTURE
```

Observed before D40:

```text
expected total_target_weight = 0.6
actual total_target_weight = 0.4
producer_result_status = REVIEW_REQUIRED
baseline_existing_required_weight = 0.4
target_gross_exposure = 0.9
available_incremental_budget = 0.5
accepted_add_increment = 0
accepted_buy_new_weight = 0
```

First divergence:

```text
default fixture mixed an equal-weight/cap normal test with PM REVIEW_REQUIRED
and REDUCE/HOLD retained-baseline rows.
```

D39 code path entered:

```text
NO
```

Passive Convergence state entered:

```text
NO
```

Resolution:

```text
test-only fixture repair
```

The test now uses a pure BUY_NEW normal-under-target fixture with three eligible candidates, no current rows, and PASS PM rows.

## Failure 2

```text
test_phase23_ao_negative_new_opportunity_is_not_forced_into_target_membership
```

Classification:

```text
INVALID_DEFAULT_FIXTURE
```

Observed before D40:

```text
expected weight_reason = negative_opportunity_not_selected
actual weight_reason = target_weight_authority_unresolved
producer_result_status = REVIEW_REQUIRED
baseline_existing_required_weight = 0.5
target_gross_exposure = 0.8
available_incremental_budget = 0.3
accepted_add_increment = 0
accepted_buy_new_weight = 0
```

First divergence:

```text
default PM fixture was REVIEW_REQUIRED and included REDUCE current_weight missing,
so target-weight authority stayed unresolved before negative opportunity semantics
could be tested.
```

D39 code path entered:

```text
NO
```

Passive Convergence state entered:

```text
NO
```

Resolution:

```text
test-only fixture repair
```

The test now uses an explicit under-target fixture without sell intents and with a PASS PM artifact.

## Failure 3

```text
test_phase26_a_no_buy_reason_opportunity_is_excluded_without_target_count_slot_limit
```

Classification:

```text
INVALID_DEFAULT_FIXTURE
```

Observed before D40:

```text
expected 8888 target_membership = true
actual 8888 target_membership = false
producer_result_status = REVIEW_REQUIRED
baseline_existing_required_weight = 0.4
target_gross_exposure = 0.8
available_incremental_budget = 0.4
accepted_add_increment = 0
accepted_buy_new_weight = 0
```

First divergence:

```text
default PM fixture was REVIEW_REQUIRED and included REDUCE current_weight missing,
so no-buy exclusion and replacement slot semantics were not reached.
```

D39 code path entered:

```text
NO
```

Passive Convergence state entered:

```text
NO
```

Resolution:

```text
test-only fixture repair
```

The test now uses an explicit under-target fixture without sell intents and with a PASS PM artifact.

## D39 Causality

```text
D39_REAL_REGRESSION count = 0
```

All 3 failures occurred outside the D39 passive convergence path:

```text
baseline_existing_required_weight <= target_gross_exposure
aggregate_exposure_state != OVER_TARGET_EXISTING_BASELINE
```

No D39 production behavior was weakened. The old unconditional:

```text
baseline > target -> BLOCK
```

was not restored.

## Changes

Production code changed:

```text
NO
```

Test-only changes:

```text
YES
```

Changed test file:

```text
tests/strategy/test_phase22_e_portfolio_construction.py
```

The repair adds explicit normal-under-target fixtures for the three tests instead of using the obsolete default PM/current fixture.

## Validation

Full Portfolio Construction file:

```text
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py -q
```

Result:

```text
43 passed
```

Selected regressions:

```text
10 passed
```

Covered:

```text
D39 2023-06-01 reproduction
D39 passive convergence
invalid positive increment fail-closed
D28
D34
D25
D31
D36
BUY / SELL independence
```

Compile:

```text
PASS
```

Diff check:

```text
PASS
```

JSON validation:

```text
PASS
```

## Evidence

```text
reports/phase28_d40_portfolio_construction_full_file_regression_failure_triage_and_resolution/
reports/phase_reports/phase28_d40_portfolio_construction_full_file_regression_failure_triage_and_resolution.json
```

Required evidence files:

```text
full_file_failure_inventory.json
failure_1_root_cause.json
failure_2_root_cause.json
failure_3_root_cause.json
d39_causality_matrix.json
changed_file_inventory.json
full_pc_test_result.json
selected_regression_results.json
architecture_conformance.json
fresh_test_contract.json
open_gap_inventory.json
```

## Scope Guard

```text
Config changed = false
Schema changed = false
Threshold changed = false
Resume executed = false
Fresh run executed = false
Long Historical executed = false
Runtime mutated = false
```

## Next Phase

```text
Fresh 100BD entry
```
