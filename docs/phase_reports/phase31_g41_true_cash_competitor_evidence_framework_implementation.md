# Phase31-G41 — True Cash Competitor Evidence Framework Implementation

## Scope

Task type: IMPLEMENTATION — EVIDENCE / STRUCTURAL SLICE.

G41 implemented only G39 Slice G41: canonical Cash / Optionality competitor
evidence inside Portfolio Construction.

Changed files:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `tests/strategy/test_phase31_g41_cash_competitor_evidence.py`

G41 did not activate the G42/G43 winner-changing Market x Candidate x Cash
interaction. It did not change Position Sizing, PM, SELL, Safety, Runtime
capital decisions, configuration, thresholds, parameters, fixtures, fresh-run,
resume, replay, Historical rerun, or long Historical.

No new permanent architecture rule beyond G38 was required.

## Primary Judgment

`PHASE31_G41_TRUE_CASH_COMPETITOR_EVIDENCE_FRAMEWORK_IMPLEMENTED_ACCEPTED`

Canonical `cash_competitor_evidence.v1` is now materialized in Portfolio
Construction for every capital competition framework. Cash evidence exists even
when deployable NEW_BUY / ADD competitors exist. It consumes Market Quality
lineage through Risk Pacing evidence, consumes authoritative Risk Pacing,
consumes canonical Opportunity Quality distribution, includes portfolio / lot /
residual context, and prepares semantic dominance inputs for later G42/G43.

Current final winner behavior remains unchanged.

## Pre-G41 Cash Semantics Inventory

| Current cash meaning | Producer / field | Current decision role | G41 migration |
| --- | --- | --- | --- |
| residual cash | `_remaining_cash_weight`, `remaining_cash_weight` | leftover cash weight after target allocation / lot reallocation | KEEP and include in canonical evidence |
| policy reserve | `_capital_cash_reason_codes`, `VALID_POLICY_RESERVE` | cash remains valid allocation | MIGRATE into canonical reason evidence |
| lot residual | `residual_cash_reason`, `UNAVOIDABLE_LOT_RESIDUAL`, `LOT_RESIDUAL` | cash remains when lot cannot use capital | KEEP as lot context |
| concentration residual | `CONCENTRATION_LIMIT`, `CONCENTRATION_BLOCK` | cash remains when concentration blocks deployment | KEEP as portfolio context |
| no-valid-competitor fallback | `NO_VALID_COMPETITOR`, `final_no_deployable_opportunity` | PC-owned no deployable judgment | KEEP as terminal/no-deployable context |
| old capital competition CASH record | `cash_competitor` | thin compatibility record | KEEP_TEMPORARILY with canonical evidence nested |

`PRE_G41_CASH_SEMANTICS_INVENTORY_COMPLETE = YES`

## Implementation Summary

G41 added:

- `canonical_cash_competitor_evidence` at the capital competition root,
- the same evidence nested under existing `cash_competitor`,
- `cash_preference_semantic`,
- opportunity-quality distribution,
- Market Quality / Risk Pacing lineage hashes,
- lot / residual / portfolio context,
- explicit forbidden-input and no-quantity-authority flags.

Canonical schema:

```text
cash_competitor_evidence.v1
```

`CANONICAL_CASH_COMPETITOR_SCHEMA_IMPLEMENTED = YES`

`CASH_COMPETITOR_OWNER = PORTFOLIO_CONSTRUCTION`

`DUPLICATE_CASH_COMPETITOR_AUTHORITY_COUNT = 0`

`CASH_EVIDENCE_EXISTS_WITH_DEPLOYABLE_COMPETITORS = YES`

## Evidence Inputs

Cash evidence consumes:

- Market Quality state and identity from Risk Pacing component evidence,
- Risk Pacing intent and lineage,
- canonical Opportunity Quality classes from G40,
- deployable competitor population across NEW_BUY and ADD,
- portfolio concentration state,
- gross exposure / cash / residual context,
- lot feasibility and residual cash reason.

Cash does not recompute Market Quality, recompute Risk Pacing, produce alpha,
rank symbols, or compute quantity.

`CASH_CONSUMES_MARKET_QUALITY = YES`

`CASH_RECOMPUTES_MARKET_QUALITY = NO`

`CASH_CONSUMES_RISK_PACING = YES`

`CASH_RECOMPUTES_RISK_PACING = NO`

`CASH_CONSUMES_CANONICAL_OPPORTUNITY_QUALITY = YES`

`LEGACY_CLASS_USED_AS_CASH_PRIMARY_INPUT = NO`

`PORTFOLIO_CONTEXT_INCLUDED_IN_CASH_EVIDENCE = YES`

`FIXED_EXPOSURE_TARGET_CREATED = NO`

`ADD_INCLUDED_IN_CASH_COMPETITOR_CONTEXT = YES`

`REENTRY_SEPARATE_CASH_RULE_CREATED = NO`

`CASH_CONSUMES_LOT_FEASIBILITY = YES`

`CASH_RECOMPUTES_QUANTITY = NO`

## Cash Preference Semantics

G41 implements semantic states, not a numeric score:

- `OPTIONALITY_LOW`
- `OPTIONALITY_NEUTRAL`
- `OPTIONALITY_ELEVATED`
- `OPTIONALITY_PREFERRED`

These states are derived from Risk Pacing intent, evidence completeness,
Opportunity Quality distribution, and lot / residual context. They are evidence
for later dominance rules only; they do not yet alter the final winner.

`CASH_PREFERENCE_SEMANTIC_IMPLEMENTED = YES`

`OUTCOME_OPTIMIZED_CASH_SCORE_CREATED = NO`

`CASH_DOMINANCE_INPUTS_MATERIALIZED = YES`

`CURRENT_FINAL_WINNER_RULE_CHANGED = NO`

## Reason Codes

Implemented canonical reason families include:

- `HEALTHY_MARKET_OPTIONALITY_LOW`
- `CAUTIOUS_MARKET_OPTIONALITY_ELEVATED`
- `RECOVERY_INCOMPLETE_OPTIONALITY_ELEVATED`
- `PRESERVE_OPTIONALITY_PREFERRED`
- `STRONG_OPPORTUNITY_PRESENT`
- `MARGINAL_OPPORTUNITY_SET`
- `NO_DEPLOYABLE_OPPORTUNITY`
- `LOT_RESIDUAL_OPTIONALITY`
- `CONCENTRATION_OPTIONALITY`
- `CASH_EVIDENCE_MISSING_INPUT_FAIL_CLOSED`

`CANONICAL_CASH_REASON_CODES_IMPLEMENTED = YES`

## PIT / Forbidden Inputs

Missing Market Quality, missing Risk Pacing, missing completeness, or missing
Opportunity Quality population materializes `INCOMPLETE_FAIL_CLOSED` and
`OPTIONALITY_PREFERRED`. It does not silently assume neutral Cash preference.

`CASH_EVIDENCE_MISSING_INPUT_FAIL_CLOSED = YES`

`CASH_COMPETITOR_PIT_CONTRACT = PASS`

`FUTURE_INPUT_COUNT = 0`

`HISTORICAL_OUTCOME_INPUT_COUNT = 0`

`PAPER_LEDGER_INPUT_COUNT = 0`

`AUDIT_RESULT_INPUT_COUNT = 0`

`CASH_HISTORICAL_PERFORMANCE_INPUT_COUNT = 0`

`CASH_MFE_MAE_INPUT_COUNT = 0`

`CASH_LATER_OUTCOME_INPUT_COUNT = 0`

`CASH_CREATES_ALPHA_FEATURE = NO`

## Evidence Responsiveness

G41 tests prove:

- Cash evidence exists with selected securities present.
- Same opportunity set produces different Cash semantics under NORMAL,
  CAUTIOUS, GRADUAL, and PRESERVE.
- Same market produces different Cash semantics when STRONG opportunities are
  present versus only marginal opportunities.
- NORMAL and CAUTIOUS differ in canonical `cash_preference_semantic`.
- GRADUAL and PRESERVE have distinct semantic roles.
- STRONG opportunity presence reduces optionality context.
- Marginal opportunity sets elevate optionality context.

`CASH_RESPONDS_TO_OPPORTUNITY_SET = YES`

`CASH_RESPONDS_TO_MARKET_QUALITY = YES`

`NORMAL_CAUTION_CASH_EVIDENCE_DIFFERENCE = YES`

`GRADUAL_CASH_EVIDENCE_ROLE_DEFINED = YES`

`PRESERVE_CASH_EVIDENCE_ROLE_DEFINED = YES`

`STRONG_OPPORTUNITY_AFFECTS_CASH_CONTEXT = YES`

`MARGINAL_OPPORTUNITY_SET_CAN_ELEVATE_CASH_CONTEXT = YES`

## Boundary Checks

`POSITION_SIZING_AUTHORITY_CHANGED = NO`

`SECOND_DISCRETE_QUANTITY_AUTHORITY_CREATED = NO`

`PM_SEMANTICS_CHANGED = NO`

`SELL_REDUCE_EXIT_SEMANTICS_CHANGED = NO`

`BUY_SELL_INDEPENDENCE_REGRESSION = NO`

`SAFETY_AUTHORITY_CHANGED = NO`

`RISK_PACING_ECONOMIC_BINDING_ACTIVATED_IN_G41 = NO`

`G41_PC_WINNER_EQUIVALENCE = PASS`

## G37 Defect Progress

`UNREACHABLE_WEAK_CLASS_DEFECT_REPAIRED = YES_FROM_G40`

`TRUE_CASH_COMPETITOR_EVIDENCE_DEFECT_REPAIRED = YES`

`TRUE_CASH_COMPETITOR_ECONOMIC_BINDING_DEFECT_REPAIRED = NO_DEFERRED_TO_G42_G43`

`PRE_FINAL_INTERACTION_DEFECT_REPAIRED = NO_DEFERRED_TO_G42`

`CAUTIOUS_GRADUAL_BINDING_DEFECT_REPAIRED = NO_DEFERRED_TO_G43`

## Legacy Cash Migration Matrix

| Legacy cash path | G41 classification |
| --- | --- |
| residual cash path | KEEP and include in canonical evidence |
| no-valid-competitor fallback | KEEP as PC final/no-deployable context |
| lot residual evidence | KEEP and include in lot feasibility summary |
| policy reserve evidence | MIGRATE into canonical reason evidence |
| old capital_competition CASH record | KEEP_TEMPORARILY with nested canonical evidence |
| independent second Cash policy | REMOVE / not created |

`G41_LEGACY_CASH_MIGRATION_MATRIX_COMPLETE = YES`

`CASH_COMPATIBILITY_MAPPING_ONE_WAY = YES`

`OLD_CASH_POLICY_REEXECUTED = NO`

## Validation

G41 cash evidence tests:

```text
python3 -m pytest tests/strategy/test_phase31_g41_cash_competitor_evidence.py tests/strategy/test_phase31_g40_opportunity_quality_continuum.py tests/strategy/test_phase22_e_portfolio_construction.py
```

Result:

```text
135 passed
```

Focused regression:

```text
python3 -m pytest tests/strategy/test_phase31_g41_cash_competitor_evidence.py tests/strategy/test_phase31_g40_opportunity_quality_continuum.py tests/strategy/test_phase31_b4_marginal_capital_value_shadow.py tests/strategy/test_phase31_b6_marginal_capital_shadow_bridge.py tests/strategy/test_phase31_b8_pending_cash_causality_bridge.py tests/strategy/test_phase31_b10_alternative_c_marginal_capital_priority.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_c_portfolio_policy.py tests/strategy/test_phase22_l_market_context_resolution.py tests/strategy/test_phase30_j_strategy_intelligence.py tests/strategy/test_phase31_g4_pm_severity_persistence.py tests/strategy/test_phase31_g8_pm_severity_action_mapping.py tests/strategy/test_phase22_j_position_sizing.py -k 'not real'
```

Result:

```text
300 passed, 9 deselected
```

Compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py tests/strategy/test_phase31_g41_cash_competitor_evidence.py
```

Result:

```text
PASS
```

`G41_CASH_EVIDENCE_TESTS = PASS`

`G41_FOCUSED_REGRESSION = PASS`

`PY_COMPILE = PASS`

`GIT_DIFF_CHECK = PASS`

## Required Summary Output

`PRIMARY_JUDGMENT = PHASE31_G41_TRUE_CASH_COMPETITOR_EVIDENCE_FRAMEWORK_IMPLEMENTED_ACCEPTED`

`PRE_G41_CASH_SEMANTICS_INVENTORY_COMPLETE = YES`

`CANONICAL_CASH_COMPETITOR_SCHEMA_IMPLEMENTED = YES`

`CASH_COMPETITOR_OWNER = PORTFOLIO_CONSTRUCTION`

`DUPLICATE_CASH_COMPETITOR_AUTHORITY_COUNT = 0`

`CASH_EVIDENCE_EXISTS_WITH_DEPLOYABLE_COMPETITORS = YES`

`CASH_CONSUMES_MARKET_QUALITY = YES`

`CASH_RECOMPUTES_MARKET_QUALITY = NO`

`CASH_CONSUMES_RISK_PACING = YES`

`CASH_RECOMPUTES_RISK_PACING = NO`

`CASH_CONSUMES_CANONICAL_OPPORTUNITY_QUALITY = YES`

`LEGACY_CLASS_USED_AS_CASH_PRIMARY_INPUT = NO`

`PORTFOLIO_CONTEXT_INCLUDED_IN_CASH_EVIDENCE = YES`

`FIXED_EXPOSURE_TARGET_CREATED = NO`

`CASH_PREFERENCE_SEMANTIC_IMPLEMENTED = YES`

`OUTCOME_OPTIMIZED_CASH_SCORE_CREATED = NO`

`CASH_DOMINANCE_INPUTS_MATERIALIZED = YES`

`CURRENT_FINAL_WINNER_RULE_CHANGED = NO`

`CANONICAL_CASH_REASON_CODES_IMPLEMENTED = YES`

`CASH_EVIDENCE_MISSING_INPUT_FAIL_CLOSED = YES`

`CASH_COMPETITOR_PIT_CONTRACT = PASS`

`FUTURE_INPUT_COUNT = 0`

`HISTORICAL_OUTCOME_INPUT_COUNT = 0`

`PAPER_LEDGER_INPUT_COUNT = 0`

`AUDIT_RESULT_INPUT_COUNT = 0`

`CASH_HISTORICAL_PERFORMANCE_INPUT_COUNT = 0`

`CASH_MFE_MAE_INPUT_COUNT = 0`

`CASH_LATER_OUTCOME_INPUT_COUNT = 0`

`CASH_CREATES_ALPHA_FEATURE = NO`

`CASH_RESPONDS_TO_OPPORTUNITY_SET = YES`

`CASH_RESPONDS_TO_MARKET_QUALITY = YES`

`NORMAL_CAUTION_CASH_EVIDENCE_DIFFERENCE = YES`

`GRADUAL_CASH_EVIDENCE_ROLE_DEFINED = YES`

`PRESERVE_CASH_EVIDENCE_ROLE_DEFINED = YES`

`STRONG_OPPORTUNITY_AFFECTS_CASH_CONTEXT = YES`

`MARGINAL_OPPORTUNITY_SET_CAN_ELEVATE_CASH_CONTEXT = YES`

`ADD_INCLUDED_IN_CASH_COMPETITOR_CONTEXT = YES`

`REENTRY_SEPARATE_CASH_RULE_CREATED = NO`

`CASH_CONSUMES_LOT_FEASIBILITY = YES`

`CASH_RECOMPUTES_QUANTITY = NO`

`POSITION_SIZING_AUTHORITY_CHANGED = NO`

`SECOND_DISCRETE_QUANTITY_AUTHORITY_CREATED = NO`

`PM_SEMANTICS_CHANGED = NO`

`SELL_REDUCE_EXIT_SEMANTICS_CHANGED = NO`

`BUY_SELL_INDEPENDENCE_REGRESSION = NO`

`SAFETY_AUTHORITY_CHANGED = NO`

`RISK_PACING_ECONOMIC_BINDING_ACTIVATED_IN_G41 = NO`

`G41_PC_WINNER_EQUIVALENCE = PASS`

`UNREACHABLE_WEAK_CLASS_DEFECT_REPAIRED = YES_FROM_G40`

`TRUE_CASH_COMPETITOR_EVIDENCE_DEFECT_REPAIRED = YES`

`TRUE_CASH_COMPETITOR_ECONOMIC_BINDING_DEFECT_REPAIRED = NO_DEFERRED_TO_G42_G43`

`PRE_FINAL_INTERACTION_DEFECT_REPAIRED = NO_DEFERRED_TO_G42`

`CAUTIOUS_GRADUAL_BINDING_DEFECT_REPAIRED = NO_DEFERRED_TO_G43`

`G41_LEGACY_CASH_MIGRATION_MATRIX_COMPLETE = YES`

`CASH_COMPATIBILITY_MAPPING_ONE_WAY = YES`

`OLD_CASH_POLICY_REEXECUTED = NO`

`G41_CASH_EVIDENCE_TESTS = PASS`

`G41_FOCUSED_REGRESSION = PASS`

`PY_COMPILE = PASS`

`GIT_DIFF_CHECK = PASS`

`CONFIG_CHANGE_EXECUTED = NO`

`THRESHOLD_CHANGE_EXECUTED = NO`

`PARAMETER_TUNING_EXECUTED = NO`

`FIXTURE_CHANGE_EXECUTED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`REPLAY_EXECUTED = NO`

`HISTORICAL_RERUN_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`NEXT_TASK_RECOMMENDATION = PHASE31_G42_PRE_FINAL_MARKET_CANDIDATE_CASH_INTERACTION_IMPLEMENTATION`
