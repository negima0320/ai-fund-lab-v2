# Phase29-L21T-AH - Expected Edge Relative Allocation Semantics Implementation

## Primary Judgment

`PHASE29_L21T_AH_EXPECTED_EDGE_RELATIVE_ALLOCATION_SEMANTICS_IMPLEMENTED_FOCUSED_REGRESSION_PASS`

Current Phase remains `Phase29`.  Phase30 was not entered.

## Scope

| Field | Value |
| --- | --- |
| Task ID | `Phase29-L21T-AH` |
| Root Cause | `uncalibrated_relative_score_used_as_absolute_expected_return_gate` |
| AG design followed | `YES` |
| Strategy code changed | `NO` |
| Runtime implementation changed | `YES` |
| Config changed | `NO` |
| Model changed | `NO` |
| Retraining performed | `NO` |
| Target long run mutated by Codex | `NO` |
| Long Historical executed by Codex | `NO` |

Target run not touched:

```text
runtime-test-historical-extended-smoke-20260814T005603520480Z
```

## Implementation

Changed Runtime behavior:

```text
Uncalibrated runtime_opportunity_score <= 0 no longer blocks BUY_NEW solely by
score sign when calibration_applied=false and economic_units_available=false.
```

The candidate now proceeds to:

```text
Buy Quality relative_opportunity_quality
-> Portfolio Construction competition
-> Position Sizing
-> Lot / Safety / Submit feasibility
```

Preserved future calibrated economic behavior:

```text
calibration_applied=true
economic_units_available=true
calibrated economic score <= 0
-> BUY_INELIGIBLE
```

Top20 repair:

```text
below_opportunity_top20 is not a hard BUY_NEW rejection for uncalibrated score
artifacts.  top20 remains metadata / diagnostic evidence, not auto-BUY.
```

## Changed Files

Runtime / Strategy code:

```text
src/ai_fund_lab_v2/runtime_v2/buy_ai/opportunity_eligibility.py
src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py
src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py
src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py
```

Tests:

```text
tests/runtime_v2/test_phase17_bv15_opportunity_buy_eligibility_contract.py
tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py
```

Common SoT:

```text
docs/02_architecture/portfolio_construction_and_position_sizing_contract.md
docs/02_architecture/strategy_architecture_v1.md
docs/01_requirements/phase_roadmap.md
docs/phase_reports/phase30_a_entry_gate_100bd_baseline_status.md
```

Report:

```text
docs/phase_reports/phase29_l21t_ah_expected_edge_relative_allocation_semantics_implementation.md
reports/phase29_l21t_ah_expected_edge_relative_allocation_semantics_implementation/summary.json
```

## Authority Result

| Requirement | Result |
| --- | --- |
| Absolute zero gate removed for uncalibrated score | `YES` |
| Calibrated future contract preserved | `YES` |
| Top20 hard eligibility removed | `YES` |
| `runtime_opportunity_score` canonicalized | `YES` |
| `expected_edge_score` alias preserved | `YES` |
| Buy Quality relative authority preserved | `YES` |
| New component added | `NO` |
| BUY count forced | `NO` |
| Exposure forced | `NO` |
| Quality FAIL preserved | `YES` |
| Safety preserved | `YES` |
| Lot safeguards preserved | `YES` |
| ADD semantics changed | `NO` |
| SELL semantics changed | `NO` |
| REENTRY safeguards preserved | `YES` |
| Runtime / Historical common path | `YES` |
| Future return used by Runtime | `NO` |

## Focused Regression Mapping

| Case | Evidence |
| --- | --- |
| V1 uncalibrated negative score can proceed | `test_phase29_l21t_ah_resolver_allows_uncalibrated_negative_score_for_relative_competition` |
| V2 weak / Quality FAIL can reject | existing Buy Quality regression |
| V3 positive score preserved | existing opportunity eligibility / strategy regression |
| V4 invalid / missing / malformed score fails closed | `test_phase29_l21t_ah_malformed_economic_metadata_fails_closed` and existing invalid score checks |
| V5 calibrated economic negative blocks | `test_phase29_l21t_ah_calibrated_economic_negative_score_still_blocks` |
| V6 not top20 not hard rejected | `test_phase29_l21t_ah_not_top20_uncalibrated_is_metadata_not_hard_block` |
| V7 top20 not auto-BUY | high downside top-ranked fixture still blocks |
| V8 one lot > Safety hard cap | position sizing authority regression |
| V9 residual capital recycle | portfolio construction / position sizing regression |
| V10 BUY count not fixed | no forced BUY logic added |
| V11 no eligible opportunity cash allowed | existing empty/no-action regression |
| V12 ADD unchanged | pending composition ADD regression |
| V13 SELL / REDUCE / EXIT unchanged | reduce quantity contract and submit regression |
| V14 REENTRY preserved | prior exit materialization regression |
| V15 Production / Historical common path | common resolver used by loader, Morning, Submit, Shadow |
| V16 no forward-return leakage | no AF forward-return artifact imported by Runtime |

## Validation Results

Focused:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_bv15_opportunity_buy_eligibility_contract.py
9 passed
```

Strategy broader:

```text
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase26_h_adaptive_buy_quality.py
18 passed

PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py
221 passed
```

Runtime broader:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase23_i_strategy_planning_authority.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py
34 passed

PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py tests/strategy/test_phase29_l21k_prior_exit_materialization.py tests/runtime_v2/test_phase26_step4_position_sizing_authority.py
62 passed

PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py
31 passed

PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py
30 passed

PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase26_step5_runtime_planning_authority.py tests/runtime_v2/test_phase22_gr_runtime_planning_regression_repair.py
5 passed
```

Final checks are recorded in the implementation turn:

```text
py_compile
git diff --check
```

## Fresh Long-Horizon Rerun

Fresh 4-year rerun required:

```text
YES
```

Reason:

```text
The currently running target run was produced with pre-AH BUY eligibility
semantics for already completed days.  It is useful as partial operational
evidence, but it is mixed-code and should not be treated as the formal
post-AH long-horizon validation baseline.
```

Codex did not run or restart it.

## Final Status Fields

| Field | Value |
| --- | --- |
| Common SoT updated | `YES` |
| Phase30 entry register updated | `YES` |
| Target long run mutated by Codex | `NO` |
| Long Historical executed by Codex | `NO` |
| Phase30 entered | `NO` |

## Recommended Next Task

```text
Phase29-L21T-AI — Post-AH Expected Edge Relative Allocation Focused Fresh Validation Readiness
```

AI should be read-only / command-preparation first, and should not run the
long Historical unless explicitly authorized.
