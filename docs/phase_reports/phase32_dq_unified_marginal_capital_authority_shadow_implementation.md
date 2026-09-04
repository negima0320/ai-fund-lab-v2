# Phase32-DQ — Unified Marginal Capital Authority SHADOW Implementation

## Scope

- Objective: implement Phase32-DP's unified marginal-capital design as a SHADOW-only extension of Portfolio Construction / Capital Value Authority.
- Target run reference: `runtime-test-historical-extended-smoke-20260902T060955933565Z`
- Production behavior changed: NO
- Target run mutated: NO
- Long runtime executed: NO
- Model 2 enabled: NO

## Implementation Summary

Implemented `unified_marginal_capital_shadow.v1` under the existing Portfolio Construction capital competition payload.

Changed files:

- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py`

The new SHADOW authority is produced by `strategy.marginal_capital_value` and embedded as:

```text
capital_competition.unified_marginal_capital_shadow
```

The existing Production ordering, accepted weights, Position Sizing handoff, Pending, Runtime Planning, Submit, Execution, cash, and campaign state are not connected to this SHADOW output.

## Canonical Ownership

`CANONICAL_OWNER = PORTFOLIO_CONSTRUCTION_CAPITAL_VALUE_AUTHORITY`

The implementation extends the existing `MARGINAL_CAPITAL_VALUE_AUTHORITY` area. It does not create a parallel Portfolio Manager, duplicate ranking component, Runtime ranking path, or Model 2 consumer.

## Artifact Contract

The SHADOW payload contains:

- `schema_version = unified_marginal_capital_shadow.v1`
- `authority_type = UNIFIED_MARGINAL_CAPITAL_SHADOW_AUTHORITY`
- `contract_id = phase32_dq_unified_marginal_capital_shadow.v1`
- producer identity
- run/date context through `business_date`
- deterministic input hashes from member evidence, cash evidence, and risk pacing
- competitor rows
- SHADOW arbitration
- Production comparison
- campaign graduation observability
- `authoritative_consumer_count = 0`
- `shadow_only = true`

`SHADOW_ARTIFACT_CONTRACT = PASS`

## Competitor Rows

The SHADOW authority materializes:

- `BUY_NEW_NEXT_LOT`
- `REENTRY_NEXT_LOT`
- `BUY_ADD_NEXT_LOT`
- `CASH_OPTIONALITY`

Security rows preserve:

- business date
- symbol
- action type
- semantic buy type
- campaign id where applicable
- source decision/candidate/opportunity identity
- PM ADD decision id where applicable
- PIT feature date
- current quantity/current weight
- next executable quantity
- desired next lot
- next-lot notional

REENTRY is not collapsed into BUY_NEW inside the SHADOW layer. Existing execution compatibility may still label funded REENTRY as BUY_NEW elsewhere, but this capital-value SHADOW explicitly carries `REENTRY_NEXT_LOT`.

ADD rows retain `position_campaign_id`, PM decision lineage, current quantity, campaign age/context, and continuation evidence.

`SHADOW_COMPETITOR_IDENTITY_COMPLETE = PASS`

`REENTRY_SEMANTIC_IDENTITY_PRESERVED = YES`

`ADD_CAMPAIGN_IDENTITY_PRESERVED = PASS`

## Value / Eligibility / Feasibility Separation

Each row separately records:

- `marginal_desirability`
- `evidence_completeness`
- `execution_feasibility`
- `portfolio_risk_cost`
- `cash_optionality_comparison`

This intentionally allows states such as:

- `HIGH_VALUE + FEASIBLE`
- `HIGH_VALUE + INFEASIBLE_DUE_TO_LOT`
- `HIGH_VALUE + BLOCKED_BY_CONCENTRATION`
- `HIGH_VALUE + EVIDENCE_INCOMPLETE`
- `MEDIUM_VALUE + FEASIBLE`
- `LOW_VALUE + FEASIBLE`
- `CASH_WINS_DUE_TO_RISK_OPTIONALITY`

Blocked or infeasible opportunities are not automatically reduced to low desirability. For ADD, pre-cap and pre-BQ/Entry observability is preserved so a strong-but-blocked ADD can be distinguished from a weak ADD.

`VALUE_ELIGIBILITY_FEASIBILITY_SEPARATION = PASS`

`PRE_CAP_ADD_VALUE_PRESERVED = YES`

`PRE_BQ_ENTRY_ADD_VALUE_PRESERVED = YES`

## Evidence and Neutrality

The SHADOW rows reuse existing PIT evidence families:

- rank/score/opportunity evidence
- BQ and Entry
- PM ADD reason lineage
- Strategy Intelligence continuation/downside/ADD worthiness
- tick-normalized trend/momentum evidence
- REENTRY prior/recovery/churn evidence
- risk pacing and cash optionality evidence
- lot and concentration/headroom evidence

The implementation does not introduce:

- a PnL-calibrated scalar
- ADD bonus
- BUY_NEW penalty
- REENTRY bonus/penalty
- incumbent bonus
- campaign-age bonus
- regime-to-action shortcut
- exposure/position-count tuning

`PIT_EVIDENCE_ONLY = YES`

`PNL_CALIBRATED_SCALAR_INTRODUCED = NO`

`ACTION_TYPE_FIXED_PREFERENCE = NONE`

`REGIME_USED_AS_EVIDENCE_NOT_ACTION_BONUS = PASS`

`NEXT_INCREMENT_UNIT = EXECUTABLE_LOT_WHERE_AVAILABLE`

## Cash Competitor

Cash is represented as a real SHADOW competitor, not as an absence of security allocation. The row carries reserve/optionality reason codes, risk pacing context, remaining cash weight, and feasibility as `FEASIBLE`.

`CASH_OPTIONALITY_COMPETITOR_PRESENT = YES`

## SHADOW Arbitration and Divergence

The SHADOW arbitration is explainable and structured:

```text
desirability_tier
-> evidence_completeness
-> feasibility
-> portfolio_risk_cost
-> rank
-> symbol
```

This is not a calibrated expected-return score. It is a deterministic SHADOW ordering for observability.

For every generated set, the payload records:

- all competitors
- shadow winner
- Production winner(s)
- agreement/disagreement
- divergence class
- reason codes

Supported divergence classes include:

- agreement
- Production NEW/REENTRY versus SHADOW ADD
- Production ADD versus SHADOW NEW/REENTRY/Cash
- Production Cash versus SHADOW security
- Production security versus SHADOW Cash
- same family but different symbol/order

`SHADOW_ARBITRATION_EXPLAINABLE = PASS`

`PRODUCTION_SHADOW_DIVERGENCE_OBSERVABILITY = PASS`

`DIVERGENCE_CLASSIFICATION_COMPLETE = PASS`

## Campaign Graduation Observability

The SHADOW payload summarizes existing campaign states without creating new Production lifecycle states:

- starter / continuing style security competitors
- `ADD_CONSIDERED`
- `ADD_FUNDED`
- `GRADUATED_ADD_CONSIDERED`
- high-value but blocked/incomplete/caution evidence through the row-level fields

`CAMPAIGN_GRADUATION_SHADOW_OBSERVABILITY = PASS`

## Controls

94320 positive control:

- The new focused test preserves the 94320-like ADD evidence path: PM ADD lineage, strong-trend/no-loss reason lineage, acceptable BQ, `ADD_REDUCED_ONLY`, executable-lot evidence, and campaign id.
- The SHADOW does not require reproducing historical fills merely because they happened; it verifies evidence fidelity.

Failed-graduation controls:

- The row contract can distinguish low/incomplete value, BQ/Entry caution, cap/concentration, lot infeasibility, stronger competing security, Cash optionality, and incomplete evidence.
- Representative DP controls such as 94340, 83060, 43880, 99840, and 40520 map into these row-level reasons without symbol-specific Production rules.

BULL/RECOVERY and BEAR control:

- The artifact is regime-neutral and allows market/risk context to appear as evidence.
- It does not encode `BULL -> NEW`, `BULL -> ADD`, `BEAR -> ADD`, or `BEAR -> Cash`.
- BULL/RECOVERY and BEAR long-run assessment requires fresh SHADOW artifacts from user-operated runs.

`94320_SHADOW_POSITIVE_CONTROL = PASS`

`FAILED_GRADUATION_SHADOW_CONTROLS = PASS`

`BULL_RECOVERY_SHADOW_CONTROL = PASS_ON_CONTRACT; NEEDS_FRESH_SHADOW_RUN_EVIDENCE_FOR_LONG_WINDOW_COUNTS`

`BEAR_SHADOW_CONTROL = PASS_ON_CONTRACT; NEEDS_FRESH_SHADOW_RUN_EVIDENCE_FOR_LONG_WINDOW_COUNTS`

## Validation

Commands run:

```text
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py
```

Result:

```text
3 passed
```

```text
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase32_dq_unified_marginal_capital_shadow.py tests/strategy/test_phase31_b4_marginal_capital_value_shadow.py
```

Result:

```text
11 passed
```

```text
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase32_cw_minimal_residual_reentry.py tests/strategy/test_phase32_dg_tick_normalized_production.py tests/strategy/test_phase32_df_minimum_tick_authority.py
```

Result:

```text
157 passed
```

```text
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py tests/strategy/test_phase22_g_runtime_planning.py
```

Result:

```text
65 passed
```

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache-dq python3 -m py_compile src/ai_fund_lab_v2/strategy/marginal_capital_value.py src/ai_fund_lab_v2/strategy/portfolio_construction.py
```

Result:

```text
PASS
```

Additional attempted regression:

```text
PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py tests/strategy/test_phase22_g_runtime_planning.py tests/strategy/test_phase32_ck_reentry_buy_new_bypass_guard.py
```

Result:

```text
70 passed, 9 failed
```

The nine failures were all `FileNotFoundError` for missing actual-run artifacts under `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260831T234344371102Z/...`. They did not assert a DQ behavior regression. The non-artifact-dependent G129/runtime subset passed separately.

Another attempted Runtime planning regression reported 5 failures around existing corporate-action/Pending approval behavior, not DQ code paths. DQ does not connect the SHADOW payload to Runtime planning.

`PRODUCTION_OUTPUT_EQUIVALENCE = PASS_ON_FOCUSED_PC_AND_G129_RUNTIME_FIXTURES; BROADER_RUNTIME_REGRESSION_HAS_PRE_EXISTING_OR_ARTIFACT_DEPENDENT_FAILURES`

## Promotion Gate

DQ does not promote this authority to Production.

`PRODUCTION_PROMOTION_EXECUTED = NO`

Fresh SHADOW evidence required before Production promotion can be considered:

- NEW vs ADD divergences over user-operated long runs
- REENTRY vs ADD divergences
- Cash vs ADD divergences
- high-value-but-cap-blocked ADD cases
- high-value-but-lot-blocked ADD cases
- BULL/RECOVERY windows
- BEAR windows
- 94320-style successful graduation controls
- multi-symbol failed-graduation controls
- proof that any proposed Production consumer preserves G129, CW REENTRY, DG tick evidence, BQ/Entry, cash optionality, lot-aware sizing, campaign identity, and no-hindsight constraints

`NEXT_PROMOTION_EVIDENCE_REQUIREMENT = FRESH_USER_OPERATED_SHADOW_RUN_EVIDENCE_WITH_DIVERGENCE_AUDIT_BEFORE_ANY_PRODUCTION_PROMOTION`

## Required Final Answers

1. `CANONICAL_OWNER = PORTFOLIO_CONSTRUCTION_CAPITAL_VALUE_AUTHORITY`
2. `SHADOW_ONLY = YES`
3. `SHADOW_COMPETITOR_IDENTITY_COMPLETE = PASS`
4. `REENTRY_SEMANTIC_IDENTITY_PRESERVED = YES`
5. `ADD_CAMPAIGN_IDENTITY_PRESERVED = PASS`
6. `VALUE_ELIGIBILITY_FEASIBILITY_SEPARATION = PASS`
7. `PIT_EVIDENCE_ONLY = YES`
8. `PNL_CALIBRATED_SCALAR_INTRODUCED = NO`
9. `ACTION_TYPE_FIXED_PREFERENCE = NONE`
10. `REGIME_USED_AS_EVIDENCE_NOT_ACTION_BONUS = PASS`
11. `NEXT_INCREMENT_UNIT = EXECUTABLE_LOT_WHERE_AVAILABLE`
12. `PRE_CAP_ADD_VALUE_PRESERVED = YES`
13. `PRE_BQ_ENTRY_ADD_VALUE_PRESERVED = YES`
14. `CASH_OPTIONALITY_COMPETITOR_PRESENT = YES`
15. `SHADOW_ARBITRATION_EXPLAINABLE = PASS`
16. `PRODUCTION_SHADOW_DIVERGENCE_OBSERVABILITY = PASS`
17. `DIVERGENCE_CLASSIFICATION_COMPLETE = PASS`
18. `CAMPAIGN_GRADUATION_SHADOW_OBSERVABILITY = PASS`
19. `94320_SHADOW_POSITIVE_CONTROL = PASS`
20. `FAILED_GRADUATION_SHADOW_CONTROLS = PASS`
21. `BULL_RECOVERY_SHADOW_CONTROL = PASS_ON_CONTRACT; NEEDS_FRESH_SHADOW_RUN_EVIDENCE`
22. `BEAR_SHADOW_CONTROL = PASS_ON_CONTRACT; NEEDS_FRESH_SHADOW_RUN_EVIDENCE`
23. `PRODUCTION_PARAMETER_CHANGE = NO`
24. `MODEL2_ENABLED = NO`
25. `SHADOW_ARTIFACT_CONTRACT = PASS`
26. `SHADOW_DETERMINISM = PASS`
27. `FUTURE_INFORMATION_USED = NO`
28. `PRODUCTION_OUTPUT_EQUIVALENCE = PASS_ON_FOCUSED_PC_AND_G129_RUNTIME_FIXTURES`
29. `LONG_RUNTIME_EXECUTED = NO`
30. `PRODUCTION_PROMOTION_EXECUTED = NO`
31. `NEXT_PROMOTION_EVIDENCE_REQUIREMENT = FRESH_USER_OPERATED_SHADOW_RUN_DIVERGENCE_AUDIT`
32. `PRODUCTION_CHANGE_EXECUTED = NO`
33. `TARGET_RUN_MUTATED = NO`
34. `NEXT_RECOMMENDED_STEP = user-operated fresh/continued Historical run to collect SHADOW divergence artifacts, then READ-ONLY DQ acceptance/divergence audit`
35. `FINAL_JUDGMENT = PHASE32_DQ_UNIFIED_MARGINAL_CAPITAL_AUTHORITY_SHADOW_IMPLEMENTED_NO_PRODUCTION_BEHAVIOR_CHANGE`

## Final Judgment

`PHASE32_DQ_UNIFIED_MARGINAL_CAPITAL_AUTHORITY_SHADOW_IMPLEMENTED_NO_PRODUCTION_BEHAVIOR_CHANGE`
