# Phase28-D39: Portfolio Construction Existing-Baseline Over-Target Passive Convergence Implementation

## Primary Judgment

```text
PHASE28_D39_PASSIVE_CONVERGENCE_IMPLEMENTED_SHORT_VALIDATION_PASS
```

Supporting judgments:

```text
PHASE28_D39_EXISTING_BASELINE_OVER_TARGET_DIRECTIONALITY_REPAIRED
PHASE28_D39_BUY_SELL_INDEPENDENCE_PRESERVED
PHASE28_D39_SELECTED_REGRESSIONS_PASS_WITH_OPEN_NON_D39_FULL_FILE_FAILURES
```

Fresh Test Entry Decision:

```text
CONDITIONAL
```

Reason: D39 focused tests and selected D25/D28/D31/D34/D36 regressions pass, but a full run of `tests/strategy/test_phase22_e_portfolio_construction.py` still has 3 non-D39 fixture/expectation failures. No fresh 100BD was executed.

## Implemented Repair

Implemented D38 `PASSIVE_CONVERGENCE` in:

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py
```

Primary behavior:

```text
baseline_existing_required_weight > target_gross_exposure
+
valid retained existing lifecycle baseline
→ OVER_TARGET_EXISTING_BASELINE
→ transition_mode = PASSIVE_CONVERGENCE
→ available_incremental_budget = 0
→ positive_increment_allowed = false
→ Portfolio Construction does not globally BLOCK
```

The D28 formula is preserved:

```text
available_incremental_budget =
max(target_gross_exposure - baseline_existing_required_weight, 0)
```

## Boundary Details

Passive convergence is limited to baseline composed from valid existing-position lifecycle targets:

```text
PM HOLD retained current_weight
PM ADD retained current_weight
PM REDUCE resolved remaining target
PM EXIT / REMOVE zero target
```

The classifier requires retained HOLD/ADD baseline to have observed `current_weight`. Missing-current-weight synthetic targets are not treated as passive convergence.

Invalid positive increment remains fail-closed:

```text
final_target_weight_sum > target_gross_exposure + tolerance
+
accepted_add_increment > 0 or accepted_buy_new_weight > 0
→ positive_increment_over_target_gross_exposure
→ BLOCK
```

## 2023-06-01 Result

Focused reproduction:

```text
test_phase28_d39_20230601_exact_passive_convergence_replay
```

Result:

```text
PASS
target_gross_exposure = 0.54
baseline_existing_required_weight = 0.677443
available_incremental_budget = 0
total_target_weight = 0.677443
aggregate_exposure_state = OVER_TARGET_EXISTING_BASELINE
producer_result_status != BLOCK
```

Expected symbol behavior:

```text
21340 ADD    baseline preserved / increment 0
30410 ADD    baseline preserved / increment 0
59550 ADD    baseline preserved / increment 0
76470 HOLD   baseline preserved
93990 REDUCE LIGHT -> target_weight 0.048188
94320 ADD    baseline preserved / increment 0
BUY_NEW      accepted allocation 0
```

## Contract Results

BUY_NEW:

```text
accepted_buy_new_weight = 0 while over target
Portfolio Construction does not globally BLOCK
```

ADD:

```text
PM ADD is preserved
baseline retained
accepted_incremental_weight = 0
```

HOLD:

```text
baseline retained
no synthetic REDUCE
no synthetic SELL
```

REDUCE:

```text
D34 canonical partial reduction executes
aggregate may remain above target
```

EXIT:

```text
PM EXIT zero target preserved
D25 full-liquidation authority unchanged
```

BUY / SELL independence:

```text
BUY_NEW / BUY_ADD unavailable while over target
SELL_REDUCE / SELL_EXIT remain available when PM authority is valid
NO_ACTION remains available for retained baseline
```

Active Policy -> PM aggregate de-risk:

```text
DEFERRED
```

## Validation

D39 focused Portfolio Construction:

```text
7 passed
```

Covered:

```text
retained baseline > target PASS
2023-06-01 exact replay PASS
ADD over target increment zero PASS
BUY_NEW over target allocation zero PASS
REDUCE over target PASS
EXIT over target PASS
invalid positive increment fail-closed PASS
```

D28 / D34 selected Portfolio Construction regressions:

```text
6 passed
```

D25 / D31 / D36 selected regressions:

```text
8 passed
```

Compile:

```text
PASS
```

Command:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache_d39 python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py tests/strategy/test_phase22_e_portfolio_construction.py
```

Diff check:

```text
PASS
```

Full PC test file attempt:

```text
python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py -q
```

Result:

```text
40 passed
3 failed
```

The 3 failures are non-D39 default fixture / producer-status selection expectations and are recorded as open gaps. The D39 focused tests and selected regressions pass.

## Changed Files

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py
tests/strategy/test_phase22_e_portfolio_construction.py
docs/01_requirements/phase_roadmap.md
docs/phase_reports/phase28_d39_portfolio_construction_existing_baseline_over_target_passive_convergence_implementation.md
reports/phase_reports/phase28_d39_portfolio_construction_existing_baseline_over_target_passive_convergence_implementation.json
reports/phase28_d39_portfolio_construction_existing_baseline_over_target_passive_convergence_implementation/
```

## Scope Guard

```text
Config changed = false
Schema changed = false
Threshold changed = false
Portfolio Policy changed = false
Position Management changed = false
Position Sizing changed = false
Runtime Planning changed = false
Sell Planning changed = false
Pending changed = false
Approval changed = false
Submit changed = false
Broker changed = false
Resume executed = false
Fresh run executed = false
Long Historical executed = false
Runtime authority violation = false
```

## Evidence

```text
reports/phase28_d39_portfolio_construction_existing_baseline_over_target_passive_convergence_implementation/
reports/phase_reports/phase28_d39_portfolio_construction_existing_baseline_over_target_passive_convergence_implementation.json
```

Minimum required evidence files were produced:

```text
changed_file_inventory.json
implementation_trace.json
passive_convergence_validation.json
20230601_reproduction.json
under_target_regression.json
at_target_regression.json
buy_new_over_target_validation.json
add_over_target_validation.json
hold_over_target_validation.json
reduce_over_target_validation.json
exit_over_target_validation.json
invalid_positive_increment_validation.json
buy_sell_independence_validation.json
d25_regression.json
d28_regression.json
d31_regression.json
d34_regression.json
d36_regression.json
short_regression_results.json
compile_validation.json
architecture_conformance.json
open_gap_inventory.json
fresh_test_contract.json
```

## Open Gaps

```text
Full tests/strategy/test_phase22_e_portfolio_construction.py has 3 non-D39 failures.
Active Policy -> PM aggregate de-risk remains deferred.
Fresh 100BD was not executed in D39.
```

## Next Phase

```text
Triage/resolve non-D39 PC full-file fixture failures if a broad local test gate is required,
then execute fresh 100BD.
```
