# Phase30-Z - REENTRY Genuine Recovery Authority Repair

Task ID: `Phase30-Z`

## Primary Judgment

```text
PHASE30_Z_REENTRY_GENUINE_RECOVERY_AUTHORITY_REPAIRED
```

`REPAIR_STATUS = REPAIRED`

Phase30-Z repaired the REENTRY-specific behavior gap found by Phase30-Y. No
Strategy threshold tuning, model change, Accepted Generation change, Safety
change, SELL / REDUCE / EXIT redesign, BUY_NEW redesign, or Historical outcome
feedback was introduced.

## Root Cause

The REENTRY recovery hurdle was too permissive:

- generic prior exit context such as `EXIT` could still be treated as sufficient
  prior campaign recovery context;
- technical recovery could pass when either trend or momentum passed;
- REENTRY did not explicitly reuse Phase30-W Entry Admission blocks for
  overheated, reversal-risk, insufficient-evidence, review, or reject states;
- repeated same-symbol prior exits were not exposed to Portfolio Construction as
  churn-suppression evidence.

## Genuine Recovery Contract

REENTRY now requires:

- cooldown satisfied;
- prior campaign identity from PIT ledger / campaign authority;
- prior EXIT cause available and not generic;
- prior EXIT cause sufficiently resolved by current evidence;
- current Continuation Quality acceptable when present;
- current Downside Risk acceptable when present;
- Entry Admission not blocked;
- corporate-action and capacity evidence pass / are available;
- repeated unresolved same-symbol churn suppressed.

## Prior Exit Cause Authority

Runtime prior-exit materialization now carries:

- `prior_exit_reason`;
- `prior_exit_reason_codes`;
- `prior_same_symbol_exit_count`.

Generic `EXIT`, `SELL`, empty, or `UNKNOWN` prior exit context no longer proves
genuine recovery. It resolves to review / wait semantics via
`insufficient_prior_exit_context`.

## Recovery-to-Exit-Cause Mapping

Trend / momentum / hard-stop / corporate-action recovery now requires trend
recovery and momentum confirmation. Reversal / overheated prior exits require
current Entry Admission normalization. Portfolio-competition exits require
renewed relative opportunity strength.

## Entry Admission Reuse

REENTRY now consumes the same Entry Admission evidence used by Phase30-W.

Blocked states/actions include:

```text
OVERHEATED_DECELERATING_ENTRY
REVERSAL_RISK_ENTRY
INSUFFICIENT_ENTRY_EVIDENCE
BUY_WAIT
REJECT
REVIEW_REQUIRED
NO_ADD
```

## Churn Suppression

Repeated unresolved same-symbol reentry is blocked using prior same-symbol exit
count and current PIT recovery evidence. The repair does not use historical PnL
outcomes as Runtime input.

## Genuine Recovery Preservation

37770-type recovery remains possible. Negative diagnostic Expected Edge does not
hard-reject REENTRY when prior cause, CQ, risk, Entry Admission, trend,
momentum, opportunity rank, quality, corporate-action, and capacity evidence all
pass.

## Expected Edge

```text
UNCALIBRATED
```

Expected Edge remains diagnostic-only for REENTRY.

## Production Integrity

```text
PHASE30_P_STRATEGY_MIGRATION_PRESERVED = YES
PHASE30_W_ENTRY_ADMISSION_PRESERVED = YES
PHASE30_W_ONE_LOT_REPAIR_PRESERVED = YES
BUY_SELL_INDEPENDENCE = PASS
LEGACY_STRATEGY_PATH_REINTRODUCED = NO
```

## Leakage Flags

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
```

## Tests

Focused pytest:

```text
python3 -m pytest tests/strategy/test_phase30_z_reentry_genuine_recovery.py tests/strategy/test_phase29_l21k_prior_exit_materialization.py tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l16_semantic_reentry_cooldown_and_recovery_hurdle tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21r3_reentry_capacity_authority_resolves_normal_excessive_and_missing_cases tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21s_capacity_severe_and_buy_quality_reject_remain_zero tests/strategy/test_phase30_w_entry_one_lot_repair.py tests/strategy/test_phase30_p_strategy_intelligence_production_migration.py tests/strategy/test_phase30_s_position_sizing_production_handoff.py -q
```

Result:

```text
41 passed
```

Compile:

```text
PYTHONPYCACHEPREFIX=.pytest_pycache python3 -m compileall -q src/ai_fund_lab_v2/strategy/portfolio_construction.py src/ai_fund_lab_v2/strategy/shadow_runtime.py tests/strategy/test_phase30_z_reentry_genuine_recovery.py
```

Result:

```text
PASS
```

## Long Historical

```text
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## 100BD Gate

```text
USER_OPERATED_FRESH_100BD_READY
```

## Recommended Next Task

```text
Phase30-AA - Fresh 100BD Long-Horizon Validation
```
