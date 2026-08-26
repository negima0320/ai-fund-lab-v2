# Phase31-G25 - Position Sizing Lot / Residual Evidence Integration and PC Reconsideration

## Scope

Task type: IMPLEMENTATION - STAGE 4 ONLY.

G25 implemented the minimum Position Sizing / Portfolio Construction interface
for canonical lot and residual evidence:

- Position Sizing now emits canonical sizing evidence per position and in lot
  feasibility preflight rows.
- Portfolio Construction consumes canonical sizing evidence when classifying
  competitor rejection and reconsideration.
- Portfolio Construction remains owner of reconsideration, Cash, and final
  `NO_DEPLOYABLE_OPPORTUNITY`.
- Position Sizing remains owner of discrete quantity.

No Market Quality semantic change, Risk Pacing behavioral activation, Re-entry
semantic redesign, ADD valuation redesign, BUY Quality redesign, SELL/PM
change, Safety logic change, Submit logic change, Execution logic change,
threshold tuning, parameter tuning, Historical optimization, fresh-run, resume,
replay, Historical rerun, or long Historical was performed.

## Current Sizing Output Inventory

Current Position Sizing already exposed:

- requested allocation through PC target weight / target notional
- executable quantity through `target_quantity_candidate`,
  `transaction_quantity_candidate`, and `quantity_delta_candidate`
- lot size through `trading_unit`
- lot infeasibility through `pc_ps_zero_delta_taxonomy` and
  `phase29_l19_lot_resolution`
- quantity delta through `quantity_delta_candidate` / `final_quantity_delta`
- target and current weight
- strategy cap through `maximum_position_weight`,
  `strategy_cap_weight`, and headroom fields
- safety cap through `safety_maximum_position_weight`,
  `safety_hard_cap_weight`, and preservation fields
- residual cash through payload `residual_cash_ratio` and lot-aware residual
  fields
- zero quantity through `quantity_status`
- rejection causes through `reason_codes`

G25 normalized these into canonical evidence fields rather than replacing the
existing Phase28/29 lot-first outputs.

## Implementation Summary

Changed:

- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `tests/strategy/test_phase22_j_position_sizing.py`
- `tests/strategy/test_phase22_e_portfolio_construction.py`

Position Sizing now emits:

- `canonical_sizing_evidence_schema_version`
- aggregate `canonical_sizing_evidence`
- per-position `canonical_sizing_evidence`
- per-position `canonical_sizing_evidence_class`
- per-position `sizing_outcome_terminality`
- per-position `residual_capital_classification`
- preflight-row `canonical_sizing_evidence`
- preflight-row `canonical_sizing_evidence_class`
- preflight-row `sizing_outcome_terminality`
- preflight-row `residual_capital_classification`

Evidence classes:

- `EXECUTABLE`
- `LOT_INFEASIBLE`
- `STRATEGY_CAP_BOUND`
- `SAFETY_CAP_BOUND`
- `INSUFFICIENT_CASH`
- `NO_POSITIVE_QUANTITY_DELTA`
- `INVALID_INPUT`
- `UNAVAILABLE_AUTHORITY`

Portfolio Construction now reads canonical sizing evidence from skipped
competitors / feasibility rows before falling back to legacy lot-aware reason
strings. PC uses that evidence only to classify reconsiderable vs terminal
competitor disposition. It does not compute quantity.

## Test Results

Focused PS + PC:

```text
python3 -m pytest tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_e_portfolio_construction.py
219 passed
```

Focused regression:

```text
python3 -m pytest tests/strategy/test_phase22_c_portfolio_policy.py tests/strategy/test_phase22_a_market_context.py tests/strategy/test_phase22_l_market_context_resolution.py tests/strategy/test_phase26_h_adaptive_buy_quality.py tests/strategy/test_phase22_d_position_management.py tests/strategy/test_phase22_g_runtime_planning.py tests/strategy/test_phase30_s_position_sizing_production_handoff.py tests/strategy/test_phase30_w_entry_one_lot_repair.py tests/strategy/test_phase31_b10_alternative_c_marginal_capital_priority.py tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py tests/runtime_v2/test_phase19_bi_empty_pending_no_action_contract.py
178 passed
```

Compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/position_sizing.py src/ai_fund_lab_v2/strategy/portfolio_construction.py
PASS
```

Diff check:

```text
git diff --check -- src/ai_fund_lab_v2/strategy/position_sizing.py src/ai_fund_lab_v2/strategy/portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_e_portfolio_construction.py
PASS
```

## Required Summary Output

```text
PRIMARY_JUDGMENT =
PHASE31_G25_SIZING_RESIDUAL_EVIDENCE_PC_RECONSIDERATION_IMPLEMENTED_ACCEPTED

CURRENT_SIZING_OUTPUT_INVENTORY_COMPLETE = YES

MISSING_CANONICAL_RESIDUAL_FIELDS = NONE_AFTER_G25

MISSING_CANONICAL_CONSTRAINT_FIELDS = NONE_AFTER_G25

CANONICAL_SIZING_EVIDENCE_DEFINED = YES

POSITION_SIZING_AUTHORITY_CHANGED = NO

SECOND_DISCRETE_QUANTITY_DECISION_CREATED = NO

PC_RECOMPUTES_QUANTITY = NO

RAW_ZERO_QUANTITY_REINTERPRETATION = NO

ZERO_QUANTITY_REASON_REQUIRED = YES

UNEXPLAINED_ZERO_QUANTITY_FAIL_CLOSED = YES

SIZING_OUTCOME_TERMINALITY_CONTRACT = PASS

PC_CONSUMES_SIZING_EVIDENCE = YES

PC_OWNS_RECONSIDERATION = YES

POSITION_SIZING_OWNS_RECONSIDERATION = NO

PC_RECONSIDERATION_DETERMINISTIC = PASS

RESIDUAL_CAPITAL_CLASSIFICATION = PASS

REALLOCATABLE_RESIDUAL_RECONSIDERATION_SUPPORTED = YES

FORCED_FULL_INVESTMENT = NO

CASH_REMAINS_VALID_COMPETITOR = YES

LOT_FIRST_CONTRACT = PASS

PHASE28_29_LOT_REPAIR_REGRESSION = NO

STRATEGY_SAFETY_BOUND_REASON_SEPARATION = PASS

SAFETY_AUTHORITY_CHANGED = NO

CASH_DOUBLE_USE_COUNT = 0

RESIDUAL_CASH_ACCOUNTING = PASS

DUPLICATE_COMPETITOR_COUNT = 0

DUPLICATE_SYMBOL_ALLOCATION_COUNT = 0

LOOP_TERMINATION = PASS

REENTRY_BEHAVIOR_CHANGED = NO

ADD_BEHAVIOR_CHANGED = NO

ADD_VALUATION_SEMANTICS_CHANGED = NO

RISK_PACING_AUTHORITATIVE_IN_G25 = NO

RISK_PACING_BEHAVIORAL_EFFECT_COUNT = 0

BUY_SELL_INDEPENDENCE = PASS

SELL_BEHAVIOR_CHANGED = NO

RUNTIME_STRATEGY_REDECISION_CREATED = NO

SUBMIT_LOGIC_CHANGED = NO

EXECUTION_LOGIC_CHANGED = NO

END_TO_END_REASON_TRACE = PASS

G25_FOCUSED_TESTS = PASS

PC_REGRESSION = PASS

SIZING_REGRESSION = PASS

LOT_AWARE_REGRESSION = PASS

RUNTIME_BOUNDARY_REGRESSION = PASS

G25_PRODUCTION_BEHAVIOR_CHANGE_CLASS =
STRUCTURAL_ONLY_NO_DECISION_CHANGE

DUPLICATE_AUTHORITY_COUNT = 0

CANONICAL_SOT_CHANGED = NO

G25_DIFF_SCOPE = PASS

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

HISTORICAL_RERUN_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

GIT_DIFF_CHECK = PASS

NEXT_TASK_RECOMMENDATION =
Proceed to G26 only after reviewing the G25 evidence interface. G26 may address
ADD capital competition semantics, but G25 intentionally did not change ADD
valuation or prioritization behavior.
```
