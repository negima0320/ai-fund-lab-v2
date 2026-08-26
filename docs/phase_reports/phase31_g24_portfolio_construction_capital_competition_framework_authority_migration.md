# Phase31-G24 - Portfolio Construction Capital Competition Framework / Authority Migration

## Scope

Task type: IMPLEMENTATION - STAGE 3 ONLY.

G24 implemented a Portfolio Construction-owned capital competition framework for
`NEW_BUY`, `ADD`, and `CASH`, and materialized Portfolio Construction as the
final owner of `NO_DEPLOYABLE_OPPORTUNITY`.

No fresh-run, resume, replay, Historical rerun, or long Historical was executed.
Strategy, Risk Pacing semantics, Re-entry semantics, ADD valuation semantics,
SELL/PM, Safety, Submit, and Execution were not changed.

## Current PC Authority Inventory

Current Portfolio Construction paths inspected:

- NEW_BUY admission: opportunity/candidate reconciliation, buy-quality
  attachment, broker eligibility, Strategy Intelligence entry admission, target
  member selection, low-price/re-entry allocation guard, lot-aware final
  reallocation.
- ADD admission: PM `ADD` visibility, canonical ADD allocation bridge,
  ADD investment evidence, broker eligibility, ADD worthiness, incremental
  budget reconciliation, lot-aware final reallocation.
- Cash/reserve behavior: Portfolio Policy target gross exposure/cash reserve
  evidence, incremental-budget residuals, lot-aware remaining cash,
  `residual_cash_reason`.
- Candidate competition: target member ordering, marginal-capital priority,
  quality-adjusted lot-aware ordering, deterministic symbol tie-break.
- Target portfolio construction: equal-weight target allocation under Portfolio
  Policy target gross exposure and single-name cap.
- Max positions: consumed from Portfolio Policy as policy metadata; PC does not
  create a new count limit in G24.
- Single-name concentration: strategy cap remains PC allocation constraint;
  Safety hard cap remains separate evidence/boundary.
- Re-entry gate consumption: existing semantic re-entry and low-price guard are
  preserved as constraint evidence.
- Lot/sizing interaction: Position Sizing/preflight lot evidence remains
  evidence; PC chooses allocation/reconsideration without creating a new
  authoritative sizing service.
- Replacement after SELL: existing released capacity / residual rebatch behavior
  preserved.
- Terminal no-deployable outcome: now materialized by
  `capital_competition.final_no_deployable_opportunity_authority`.

Current no-deployable decision sites:

- PC target-member exclusion / zero target weight reasons.
- PC incremental-budget reconciliation residuals.
- PC lot-aware final reallocation skipped candidates and residual cash reason.
- Downstream Runtime/Submit/Execution may still observe zero/no-action states,
  but G24 does not authorize them to recreate `NO_DEPLOYABLE_OPPORTUNITY`.

## Implementation Summary

Added `build_capital_competition_framework(...)` in
`src/ai_fund_lab_v2/strategy/portfolio_construction.py`.

The framework emits:

- `capital_competition`
- `capital_competition_authority`
- `capital_competitor_types`
- `cash_competitor`
- `cash_reason_codes`
- `final_no_deployable_opportunity`
- `final_no_deployable_opportunity_authority`

The same framework is also attached to lot-aware final reallocation evidence so
the final PC-owned state is visible after lot feasibility and residual
reconsideration.

The implementation is structural/evidence-only for existing target construction
behavior. It does not change Portfolio Policy numeric targets, Risk Pacing
behavior, Re-entry rules, ADD semantics, SELL behavior, Submit, or Execution.

## Test Results

Focused Portfolio Construction:

```text
python3 -m pytest tests/strategy/test_phase22_e_portfolio_construction.py
112 passed
```

Focused regression:

```text
python3 -m pytest tests/strategy/test_phase22_c_portfolio_policy.py tests/strategy/test_phase22_a_market_context.py tests/strategy/test_phase22_l_market_context_resolution.py tests/strategy/test_phase26_h_adaptive_buy_quality.py tests/strategy/test_phase22_d_position_management.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase30_s_position_sizing_production_handoff.py tests/strategy/test_phase22_g_runtime_planning.py tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py tests/runtime_v2/test_phase19_bi_empty_pending_no_action_contract.py
258 passed
```

Compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py
PASS
```

Diff check:

```text
git diff --check -- src/ai_fund_lab_v2/strategy/portfolio_construction.py tests/strategy/test_phase22_e_portfolio_construction.py
PASS
```

## Required Summary Output

```text
PRIMARY_JUDGMENT =
PHASE31_G24_PC_CAPITAL_COMPETITION_FRAMEWORK_IMPLEMENTED_ACCEPTED

CURRENT_PC_AUTHORITY_INVENTORY_COMPLETE = YES

CURRENT_NO_DEPLOYABLE_DECISION_SITES =
PC target-member exclusion / zero target weight reasons;
PC incremental-budget reconciliation residuals;
PC lot-aware final reallocation skipped candidates / residual_cash_reason;
downstream zero/no-action observers only, not final authority

DUPLICATE_NO_DEPLOYABLE_AUTHORITY_PRESENT = PARTIAL

CANONICAL_COMPETITOR_TYPES_IMPLEMENTED = YES

CASH_COMPETITOR_PRESENT = YES

ADD_AUTOMATIC_PRIORITY = NO

NEW_BUY_AUTOMATIC_PRIORITY = NO

FINAL_NO_DEPLOYABLE_OPPORTUNITY_OWNER = PORTFOLIO_CONSTRUCTION

DOWNSTREAM_NO_DEPLOYABLE_RECLASSIFICATION_COUNT = 0

CONSTRAINT_EVIDENCE_DECISION_SEPARATION = PASS

POSITION_SIZING_AUTHORITY_CHANGED = NO

SECOND_DISCRETE_QUANTITY_DECISION_CREATED = NO

STRATEGY_SAFETY_CAP_SEPARATION = PASS

SAFETY_AUTHORITY_CHANGED = NO

CASH_REASON_CODES_IMPLEMENTED = YES

IDLE_CASH_ALWAYS_FAILURE = NO

RECONSIDERABLE_VS_TERMINAL_CONSTRAINT_MODEL = PASS

PC_RESIDUAL_RECONSIDERATION_LOOP_IMPLEMENTED = YES

RESIDUAL_LOOP_TERMINATION = PASS

RESIDUAL_LOOP_DUPLICATE_EXECUTION_RISK = NO

REENTRY_BEHAVIOR_CHANGED = NO

ADD_BEHAVIOR_CHANGED = NO

ADD_COMPETITOR_FRAMEWORK_ONLY = YES

RISK_PACING_AUTHORITATIVE_IN_G24 = NO

RISK_PACING_BEHAVIORAL_EFFECT_COUNT = 0

BUY_SELL_INDEPENDENCE = PASS

SELL_BEHAVIOR_CHANGED = NO

SUBMIT_LOGIC_CHANGED = NO

EXECUTION_LOGIC_CHANGED = NO

PC_REASON_CODE_CONTRACT = PASS

HISTORICAL_OUTCOME_USED_FOR_COMPETITION = NO

TEMPORARY_COMPATIBILITY_PATHS =
Existing downstream zero/no-action consumers remain observational compatibility
only; canonical final no-deployable authority is PC capital_competition.

PERMANENT_LEGACY_FALLBACK_CREATED = NO

G24_FOCUSED_TESTS = PASS

PC_EXISTING_REGRESSION = PASS

SIZING_EXISTING_REGRESSION = PASS

RUNTIME_BOUNDARY_REGRESSION = PASS

G24_PRODUCTION_BEHAVIOR_CHANGE_CLASS =
STRUCTURAL_ONLY_NO_DECISION_CHANGE

DUPLICATE_AUTHORITY_COUNT = 0

CANONICAL_SOT_CHANGED = NO

G24_DIFF_SCOPE = PASS

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

HISTORICAL_RERUN_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

GIT_DIFF_CHECK = PASS

NEXT_TASK_RECOMMENDATION =
Proceed to the next staged validation/design task. Do not run Historical
optimization or tune parameters from G24.
```
