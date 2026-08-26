# Phase31-G23 - Portfolio Policy Risk Pacing Shadow Producer

## Scope

Task type: IMPLEMENTATION - STAGE 2 ONLY.

G23 implemented Portfolio Policy-owned Risk Pacing materialization as
non-authoritative shadow evidence. It did not connect Risk Pacing to Portfolio
Construction or any other authoritative consumer.

No Portfolio Construction, Position Sizing, Re-entry, ADD, BUY, SELL, PM,
Safety, Submit, or Execution behavior was changed. No threshold tuning,
parameter tuning, fresh-run, resume, replay, Historical rerun, or long
Historical was executed.

## Files Changed

Implemented:

- `src/ai_fund_lab_v2/strategy/portfolio_policy.py`
- `tests/strategy/test_phase22_c_portfolio_policy.py`

Report:

- `docs/phase_reports/phase31_g23_portfolio_policy_risk_pacing_shadow_producer.md`

Canonical SoT was not changed.

## Implementation Summary

Portfolio Policy now materializes these shadow-only fields:

- `risk_pacing_intent`
- `risk_pacing_reason_codes`
- `risk_pacing_evidence_completeness`
- `risk_pacing_as_of`
- `risk_pacing_authority`
- `risk_pacing_mode = SHADOW_NON_AUTHORITATIVE`
- `risk_pacing_component_evidence`

The new fields are evidence outputs only. Existing authoritative Portfolio
Policy fields keep their prior semantics.

## Implemented States

- `NORMAL_DEPLOYMENT`
- `CAUTIOUS_DEPLOYMENT`
- `GRADUAL_REDEPLOYMENT`
- `PRESERVE_OPTIONALITY`

Semantic mapping:

- healthy Market Quality -> `NORMAL_DEPLOYMENT`
- recovery confirmation incomplete -> `GRADUAL_REDEPLOYMENT`
- conflicted / narrowing Market Quality -> `CAUTIOUS_DEPLOYMENT`
- missing, insufficient, or temporally invalid Market Quality ->
  `PRESERVE_OPTIONALITY`

No numeric exposure target, BUY count, position count, cooldown, or new policy
parameter was introduced.

## Reason Codes

Implemented:

- `RISK_PACING_NORMAL`
- `RISK_PACING_CAUTIOUS`
- `RISK_PACING_GRADUAL_REDEPLOYMENT`
- `RISK_PACING_PRESERVE_OPTIONALITY`
- `RISK_PACING_INSUFFICIENT_MARKET_QUALITY`
- `RISK_PACING_TEMPORAL_AUTHORITY_INVALID`

Reason codes describe contemporaneous Market Context / Portfolio Policy evidence
only.

## Shadow Contract

```text
CURRENT_STAGE = G23
SHADOW_OWNER = PORTFOLIO_POLICY
FIRST_AUTHORITATIVE_CONSUMER_PLANNED = G24
FINAL_SHADOW_REMOVAL_STAGE = G28
```

No permanent shadow path or comparison path is created.

## Test Results

Portfolio Policy focused tests:

```text
python3 -m pytest tests/strategy/test_phase22_c_portfolio_policy.py
14 passed
```

Focused compatibility regression:

```text
python3 -m pytest tests/strategy/test_phase22_a_market_context.py tests/strategy/test_phase22_l_market_context_resolution.py tests/strategy/test_phase26_h_adaptive_buy_quality.py tests/strategy/test_phase22_d_position_management.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase30_s_position_sizing_production_handoff.py
277 passed
```

Compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_policy.py
PASS
```

## Acceptance Judgment

```text
PRIMARY_JUDGMENT =
PHASE31_G23_RISK_PACING_SHADOW_IMPLEMENTED_ACCEPTED
```

## Required Summary Output

```text
PRIMARY_JUDGMENT =
PHASE31_G23_RISK_PACING_SHADOW_IMPLEMENTED_ACCEPTED

RISK_PACING_OWNER = PORTFOLIO_POLICY

RISK_PACING_STATES_IMPLEMENTED =
NORMAL_DEPLOYMENT, CAUTIOUS_DEPLOYMENT, GRADUAL_REDEPLOYMENT,
PRESERVE_OPTIONALITY

RISK_PACING_FIELDS_MATERIALIZED =
risk_pacing_intent, risk_pacing_reason_codes,
risk_pacing_evidence_completeness, risk_pacing_as_of, risk_pacing_authority,
risk_pacing_mode, risk_pacing_component_evidence

RISK_PACING_MATERIALIZED = YES

RISK_PACING_SHADOW_ONLY = YES

RISK_PACING_AUTHORITATIVE_CONSUMER_COUNT = 0

RISK_PACING_FAIL_CLOSED = YES

MISSING_QUALITY_NORMAL_DEPLOYMENT = NO

RISK_PACING_REASON_CODES_IMPLEMENTED =
RISK_PACING_NORMAL, RISK_PACING_CAUTIOUS, RISK_PACING_GRADUAL_REDEPLOYMENT,
RISK_PACING_PRESERVE_OPTIONALITY, RISK_PACING_INSUFFICIENT_MARKET_QUALITY,
RISK_PACING_TEMPORAL_AUTHORITY_INVALID

RISK_PACING_COMPLETENESS_DEFINED = YES

RISK_PACING_AS_OF_EXPLICIT = YES

RISK_PACING_DETERMINISTIC = PASS

MARKET_QUALITY_OWNER_CHANGED = NO

PORTFOLIO_CONSTRUCTION_BEHAVIOR_CHANGED = NO

RISK_PACING_USED_BY_PC = NO

SELL_BEHAVIOR_CHANGED = NO

PM_BEHAVIOR_CHANGED = NO

ADD_INTENT_BEHAVIOR_CHANGED = NO

BUY_SELL_INDEPENDENCE = PASS

SAFETY_BEHAVIOR_CHANGED = NO

SUBMIT_BEHAVIOR_CHANGED = NO

EXECUTION_BEHAVIOR_CHANGED = NO

FIXED_EXPOSURE_TARGET_CREATED = NO

FIXED_BUY_COUNT_CREATED = NO

FIXED_POSITION_COUNT_CREATED = NO

NEW_NUMERIC_POLICY_PARAMETER_COUNT = 0

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_INPUT_COUNT = 0

EVIDENCE_FEEDBACK_INPUT_COUNT = 0

PORTFOLIO_POLICY_SCHEMA_COMPATIBILITY = PASS

EXISTING_POLICY_SEMANTICS_CHANGED = NO

G23_FOCUSED_TESTS = PASS

PORTFOLIO_POLICY_EXISTING_REGRESSION = PASS

PC_COMPATIBILITY_REGRESSION = PASS

AUTHORITATIVE_BEHAVIOR_EQUIVALENCE = PASS

DUPLICATE_AUTHORITY_COUNT = 0

SHADOW_REMOVAL_CONTRACT = PASS

PERMANENT_SHADOW_PATH_ALLOWED = NO

CANONICAL_SOT_CHANGED = NO

G23_DIFF_SCOPE = PASS

PRODUCTION_BEHAVIOR_CHANGE = NO

CONFIG_PARAMETER_CHANGED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

HISTORICAL_RERUN_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

GIT_DIFF_CHECK = PASS

NEXT_TASK_RECOMMENDATION =
Proceed to G24 Portfolio Construction capital competitor framework planning /
implementation only after accepting G23. Do not run Historical before
integrated focused acceptance.
```
