# Phase31-G22 - Market Quality Evidence Producer / Schema / Reason-Code Implementation

## Scope

Task type: IMPLEMENTATION - STAGE 1 ONLY.

G22 implemented Market Quality evidence-only materialization inside the
canonical Market Context artifact. It did not change Portfolio Policy,
Risk Pacing, Portfolio Construction, Position Sizing, Re-entry, ADD, BUY, SELL,
PM, Safety, Submit, or Execution behavior.

No threshold tuning, parameter tuning, Historical optimization, fresh-run,
resume, replay, Historical rerun, or long Historical was executed.

## Files Changed

Implemented:

- `src/ai_fund_lab_v2/strategy/market_context.py`
- `tests/strategy/test_phase22_l_market_context_resolution.py`

Report:

- `docs/phase_reports/phase31_g22_market_quality_evidence_producer_schema_reason_codes.md`

Canonical SoT was not changed.

## Implementation Summary

Market Context now materializes these evidence-only fields on newly produced
Market Context artifacts:

- `market_quality_state`
- `market_quality_reason_codes`
- `market_quality_evidence_completeness`
- `market_quality_component_evidence`
- `market_quality_as_of`

The fields are produced by Market Context only. Existing readers remain
backward compatible with old draft fixture artifacts that do not contain the new
fields.

## Implemented States

Implemented with the Stage 1 input scope:

- `HEALTHY_EXPANSION`
- `HEALTHY_RECOVERY`
- `RECOVERY_CONFIRMATION_INCOMPLETE`
- `SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH`
- `SHORT_TERM_BREADTH_BREAKDOWN`
- `CONFLICTED_MARKET_STRUCTURE`
- `INSUFFICIENT_EVIDENCE`

Not implemented / unreachable in G22:

- `FRAGILE_RECOVERY` as a standalone state
- `SECTOR_PARTICIPATION_NARROWING`

`FRAGILE_RECOVERY` is currently represented as a reason family where supported.
Sector participation remains deferred because G19/G21 found its semantics not
production-ready.

## Input Scope

Used:

- existing 5D return
- existing 20D return
- existing 5D breadth
- existing 20D breadth
- existing volatility evidence
- existing confidence / uncertainty / coverage evidence

Deferred:

- sector participation
- transition path
- days since transition
- transition churn
- external feeds
- Historical outcome

Forbidden and not used:

- future returns
- later PnL
- Paper Ledger
- fill outcomes
- later campaign outcome
- audit/test result feedback

## Reason Codes

Implemented reason-code families:

- `MARKET_QUALITY_HEALTHY`
- `MARKET_QUALITY_FRAGILE`
- `MARKET_STRUCTURE_CONFLICTED`
- `SHORT_TERM_PARTICIPATION_NARROWING`
- `RECOVERY_CONFIRMATION_INCOMPLETE`
- `MARKET_QUALITY_INSUFFICIENT_EVIDENCE_*`

Reason codes describe contemporaneous Market Context evidence only.

## Evidence Completeness

Implemented:

- `COMPLETE`
- `PARTIAL`
- `INSUFFICIENT`

`INSUFFICIENT_EVIDENCE` is emitted when required inputs are missing,
temporally invalid, blocked, or source authority is unavailable. Missing or
invalid evidence does not fall back to HEALTHY, BULL, NORMAL, or DEFAULT_OK.

## Behavior Change Audit

G22 does not connect Market Quality to any authoritative consumer.

```text
MARKET_QUALITY_AUTHORITATIVE_CONSUMER_COUNT = 0
PRODUCTION_BEHAVIOR_CHANGE = NO
```

Existing Market Direction fields and regime taxonomy are preserved. No second
regime classifier was created.

## Test Results

Focused Market Context tests:

```text
python3 -m pytest tests/strategy/test_phase22_a_market_context.py tests/strategy/test_phase22_l_market_context_resolution.py
11 passed
```

Consumer compatibility regression:

```text
python3 -m pytest tests/strategy/test_phase22_c_portfolio_policy.py tests/strategy/test_phase26_h_adaptive_buy_quality.py tests/strategy/test_phase22_d_position_management.py tests/strategy/test_phase22_e_portfolio_construction.py
164 passed
```

Compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/market_context.py
PASS
```

The first `python3 -m py_compile` attempt without `PYTHONPYCACHEPREFIX` failed
because macOS Python attempted to write bytecode under
`/Users/negishi/Library/Caches/com.apple.python/...`, which was not writable in
the sandbox. The redirected compile passed.

## Acceptance Judgment

```text
PRIMARY_JUDGMENT =
PHASE31_G22_MARKET_QUALITY_EVIDENCE_ONLY_IMPLEMENTED_ACCEPTED
```

## Required Summary Output

```text
PRIMARY_JUDGMENT =
PHASE31_G22_MARKET_QUALITY_EVIDENCE_ONLY_IMPLEMENTED_ACCEPTED

MARKET_DIRECTION_BEHAVIOR_CHANGED = NO

MARKET_REGIME_AUTHORITY_CHANGED = NO

SECOND_REGIME_CLASSIFIER_CREATED = NO

MARKET_QUALITY_FIELDS_MATERIALIZED = YES

MARKET_QUALITY_OWNER = MARKET_CONTEXT

MARKET_QUALITY_STATES_IMPLEMENTED =
HEALTHY_EXPANSION, HEALTHY_RECOVERY, RECOVERY_CONFIRMATION_INCOMPLETE,
SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH, SHORT_TERM_BREADTH_BREAKDOWN,
CONFLICTED_MARKET_STRUCTURE, INSUFFICIENT_EVIDENCE

MARKET_QUALITY_REASON_CODES_IMPLEMENTED =
MARKET_QUALITY_HEALTHY, MARKET_QUALITY_FRAGILE, MARKET_STRUCTURE_CONFLICTED,
SHORT_TERM_PARTICIPATION_NARROWING, RECOVERY_CONFIRMATION_INCOMPLETE,
MARKET_QUALITY_INSUFFICIENT_EVIDENCE_*

EVIDENCE_COMPLETENESS_DEFINED = YES

MARKET_QUALITY_AS_OF_EXPLICIT = YES

MARKET_QUALITY_PIT_CONTRACT = PASS

FUTURE_INFORMATION_INPUT_COUNT = 0

HISTORICAL_OUTCOME_INPUT_INCLUDED = NO

EVIDENCE_FEEDBACK_INPUT_COUNT = 0

SECTOR_PARTICIPATION_INCLUDED = NO

NEW_EXTERNAL_DATA_INCLUDED = NO

MARKET_QUALITY_FAIL_CLOSED = YES

IMPLICIT_HEALTHY_FALLBACK = NO

IMPLICIT_BULL_FALLBACK = NO

COMPONENT_EVIDENCE_AUDITABLE = YES

PRODUCTION_ARTIFACT_CONTAINS_HISTORICAL_ANALYSIS = NO

MARKET_QUALITY_DETERMINISTIC = PASS

MARKET_QUALITY_AUTHORITATIVE_CONSUMER_COUNT = 0

PRODUCTION_BEHAVIOR_CHANGE = NO

SCHEMA_BACKWARD_COMPATIBILITY = PASS

EXISTING_MARKET_CONTEXT_CONSUMERS_COMPATIBLE = PASS

NEW_PRODUCTION_NUMERIC_PARAMETER_COUNT = 0

HISTORICAL_PARAMETER_OPTIMIZATION = NO

DUPLICATE_AUTHORITY_COUNT = 0

G22_FOCUSED_TESTS = PASS

MARKET_CONTEXT_EXISTING_REGRESSION = PASS

CANONICAL_SOT_CHANGED = NO

G22_DIFF_SCOPE = PASS

PORTFOLIO_POLICY_CHANGED = NO

PORTFOLIO_CONSTRUCTION_CHANGED = NO

POSITION_SIZING_CHANGED = NO

REENTRY_CHANGED = NO

ADD_CHANGED = NO

BUY_LOGIC_CHANGED = NO

SELL_LOGIC_CHANGED = NO

PM_CHANGED = NO

SAFETY_CHANGED = NO

SUBMIT_CHANGED = NO

EXECUTION_CHANGED = NO

CONFIG_PARAMETER_CHANGED = NO

IMPLEMENTATION_EXECUTED = YES

PRODUCTION_CODE_CHANGED = YES, MARKET_CONTEXT_EVIDENCE_ONLY

CONFIG_CHANGED = NO

SCHEMA_MIGRATION_EXECUTED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

GIT_DIFF_CHECK = PASS

NEXT_TASK_RECOMMENDATION =
Proceed to G23 Portfolio Policy Risk Pacing shadow producer only after accepting
G22. Do not run Historical before integrated focused acceptance.
```
