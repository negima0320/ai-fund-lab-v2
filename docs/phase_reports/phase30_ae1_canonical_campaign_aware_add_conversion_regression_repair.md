# Phase30-AE1 - Canonical Campaign-Aware ADD Conversion Regression Repair

Task ID: `Phase30-AE1`

Root cause authority:

```text
docs/phase_reports/phase30_ae0_pc_campaign_identity_add_conversion_regression_lineage_audit.md
```

## Primary Judgment

```text
PHASE30_AE1_CANONICAL_CAMPAIGN_AWARE_ADD_CONVERSION_REGRESSION_REPAIRED
REPAIR_STATUS = REPAIRED
```

Phase30-AE1 repaired the AE0-confirmed regression where canonical campaign id
existed in SI / PM evidence but did not reach the PC current-position ADD
bridge. The repair does not increase ADD by policy. It only restores the
existing contract for ADD-worthy, same-campaign, execution-feasible ADDs:

```text
PM ADD -> PC campaign continuation PASS -> PC positive incremental target
-> PS positive quantity_delta -> Runtime BUY_ADD
```

## Canonical Campaign Propagation

Implemented:

- Position Management now emits canonical `position_campaign_id` from Strategy
  Intelligence lifecycle context when present.
- Portfolio Construction resolves `current_position_campaign_id` from canonical
  Current campaign id first, then canonical PM campaign id.
- Portfolio Construction resolves `pm_position_campaign_id` from canonical
  PM/SI campaign fields and no longer consumes `lifecycle_reference` as
  campaign authority.
- `runtime-current-*` is explicitly rejected as canonical campaign identity.
- PC ADD evidence now preserves PM/SI ADD-worthiness and Entry Admission fields
  for ADD bridge gating.
- PC preserves reference price authority metadata so a valid PC ADD target can
  continue into PS quantity conversion.

Code locations:

- `src/ai_fund_lab_v2/strategy/position_management.py:1381`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:944`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:989`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:1028`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:2998`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:3102`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py:4118`

## PM -> PC

```text
PM_CANONICAL_POSITION_CAMPAIGN_ID_EXPOSED = YES
PC_CURRENT_CAMPAIGN_ID_PROPAGATION = PASS
PC_PM_CAMPAIGN_ID_CANONICAL = PASS
runtime-current-* AS CAMPAIGN AUTHORITY = 0
```

The AE0 shape is now repaired:

```text
PM lifecycle_reference = runtime-current-11110
PM strategy_intelligence_campaign_id = pc-canonical-11110-0001
PC current_position_campaign_id = pc-canonical-11110-0001
PC pm_position_campaign_id = pc-canonical-11110-0001
PC opportunity_position_campaign_id = pc-canonical-11110-0001
campaign_continuation = PASS
```

## PC ADD Continuation

Healthy ADD now passes only when all required evidence passes:

```text
PM ADD = PASS
campaign_continuation = PASS
expected_edge = PASS
incremental_value = PASS
opportunity_cost = PASS
no_loss_averaging = PASS
capital_availability = PASS
execution_feasibility = PASS
add_worthiness = PASS
entry_admission = PASS
```

Campaign identity alone does not authorize ADD.

## PC -> PS -> Runtime BUY_ADD

End-to-end focused regression confirms:

```text
PC target_weight_change > 0
PS quantity_delta_candidate > 0
Runtime planning_intent = BUY_ADD
Runtime order_side_intent = BUY
```

## Healthy ADD Sentinel

Sentinel:

```text
canonical campaign identity match
PM ADD
HEALTHY_CONTINUATION_ENTRY / ADD_ALLOWED
Expected Edge PASS
Opportunity Cost PASS
No-loss PASS
Capital PASS
Execution PASS
```

Result:

```text
PC target_weight_change > 0
PC add_allocation_eligibility_status = PASS
PS positive quantity_delta
Runtime BUY_ADD
```

## Correct NO_ADD Sentinel

Sentinel:

```text
canonical campaign identity match
REVERSAL_RISK_ENTRY / NO_ADD
```

Result:

```text
target_weight_change = 0
add_allocation_eligibility_status = FAIL_CLOSED
BUY_ADD = NO
reason includes ADD_WORTHINESS_NO_ADD / ADD_ENTRY_ADMISSION_NO_ADD
```

This preserves the 2022-08-31 class of correct NO_ADD behavior.

## Campaign Lifecycle Preservation

```text
BUY_NEW -> new canonical campaign = PRESERVED
ADD -> same campaign = PRESERVED
REDUCE -> same campaign = PRESERVED
EXIT -> close = PRESERVED
REENTRY -> new campaign under Phase30-Z = PRESERVED
```

No campaign ledger, campaign id generator, execution ledger, Current valuation,
or lifecycle materialization logic was changed.

## Legacy Retirement Integrity

```text
runtime-current-* AS CAMPAIGN AUTHORITY = 0
LEGACY_CAMPAIGN_FALLBACK_REFERENCE_COUNT = 0
OBSOLETE_HOLD_ADD_HEURISTIC_REFERENCE_COUNT = 0
ONE_PRODUCTION_CAMPAIGN_LIFECYCLE_PATH = YES
```

Search notes:

- Retired AC reference names remain absent in `src tests`.
- `runtime-current-*` remains only as non-authoritative position reference
  generation, explicit rejection, or regression fixture input.
- No symbol-only campaign fallback, AC rollback, duplicate campaign authority,
  or legacy HOLD/ADD heuristic was introduced.

## Production Integrity

```text
PHASE30_AC_CAMPAIGN_LIFECYCLE_PRESERVED = YES
PHASE30_AD1_BOOTSTRAP_PRESERVED = YES
PHASE30_W_ENTRY_ADMISSION_PRESERVED = YES
PHASE30_W_ONE_LOT_ADMISSION_PRESERVED = YES
PHASE30_Z_REENTRY_PRESERVED = YES
PHASE30_S_HANDOFF_PRESERVED = YES
SELL_REDUCE_EXIT_SEMANTICS_PRESERVED = YES
BUY_SELL_INDEPENDENCE = PASS
EXPECTED_EDGE = UNCALIBRATED
```

## Leakage

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
```

No fresh 20BD, 100BD, or long Historical run was executed.

## Tests

Compile:

```text
PYTHONPYCACHEPREFIX=.pytest_pycache python3 -m compileall -q src/ai_fund_lab_v2/strategy/position_management.py src/ai_fund_lab_v2/strategy/portfolio_construction.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase30_p_strategy_intelligence_production_migration.py tests/strategy/test_phase30_s_position_sizing_production_handoff.py
PASS
```

Focused ADD chain:

```text
python3 -m pytest \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase30_ae1_canonical_si_campaign_repairs_runtime_current_add_mismatch \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase30_ae1_canonical_campaign_preserves_reversal_risk_no_add \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase28_d55_a_add_evidence_resolver_valid_case_drives_positive_increment \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase28_d55_a_missing_campaign_authority_fails_closed \
  tests/strategy/test_phase22_e_portfolio_construction.py::test_phase28_d55_a_campaign_mismatch_and_future_baseline_fail_closed \
  tests/strategy/test_phase22_j_position_sizing.py::test_phase28_c_add_target_weight_bridge_reaches_positive_quantity_delta \
  tests/strategy/test_phase22_g_runtime_planning.py::test_phase29_l21f_runtime_planning_consumes_soft_cap_buy_add_positive_quantity \
  tests/strategy/test_phase30_s_position_sizing_production_handoff.py::test_phase30_ae1_pm_pc_ps_runtime_canonical_campaign_buy_add_e2e \
  tests/strategy/test_phase30_p_strategy_intelligence_production_migration.py::test_phase30_ae1_pm_exposes_canonical_position_campaign_id_from_si -q
```

Result:

```text
9 passed
```

Phase30 preservation:

```text
python3 -m pytest tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py tests/strategy/test_phase30_l_strategy_intelligence_gap_repair.py tests/strategy/test_phase30_n_strategy_intelligence_campaign_authority.py tests/strategy/test_phase30_p_strategy_intelligence_production_migration.py tests/strategy/test_phase30_s_position_sizing_production_handoff.py tests/strategy/test_phase30_w_entry_one_lot_repair.py tests/strategy/test_phase30_z_reentry_genuine_recovery.py -q
```

Result:

```text
57 passed
```

Portfolio Construction / Phase28-29 ADD related:

```text
python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py::test_phase28_c_add_target_weight_bridge_reaches_positive_quantity_delta tests/strategy/test_phase22_j_position_sizing.py::test_phase28_c_add_lot_rounding_zero_delta_is_explicit tests/strategy/test_phase22_j_position_sizing.py::test_phase29_e_ps_preflight_classifies_one_lot_above_concentration_headroom tests/strategy/test_phase22_j_position_sizing.py::test_phase29_l19_ps_preflight_materializes_strategy_safety_lot_boundary tests/strategy/test_phase22_g_runtime_planning.py::test_phase29_l21f_runtime_planning_consumes_soft_cap_buy_add_positive_quantity -q
```

Result:

```text
106 passed
```

## Long Historical

```text
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Fresh Validation Gate

```text
USER_OPERATED_FRESH_20BD_RERUN_READY
```

## Recommended Next Task

```text
Phase30-AE2 - Fresh 20BD ADD Conversion / Winner Amplification Validation
```
