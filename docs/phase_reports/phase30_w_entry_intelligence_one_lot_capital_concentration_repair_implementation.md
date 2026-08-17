# Phase30-W - Entry Intelligence / One-Lot Capital Concentration Repair Implementation

## Primary Judgment

```text
PHASE30_W_ENTRY_INTELLIGENCE_ONE_LOT_CONCENTRATION_REPAIR_IMPLEMENTED_FRESH_VALIDATION_READY
```

## Implementation Status

```text
IMPLEMENTED
```

Phase30-W implemented the Phase30-V design in the Production-common Strategy
path. No 78780-specific rule, symbol/date hard-code, 10BD outcome fit, future
price/return/MFE/MAE input, threshold tuning, model retraining, Accepted
Generation change, Safety hard-cap weakening, SELL/REDUCE redesign, forced
investment, or forced exposure was introduced.

## Entry Admission

`strategy_intelligence.py` now emits symbol-level `entry_admission` with:

```text
HEALTHY_CONTINUATION_ENTRY
CONTINUATION_WITH_CAUTION
OVERHEATED_DECELERATING_ENTRY
REVERSAL_RISK_ENTRY
INSUFFICIENT_ENTRY_EVIDENCE
```

The producer consumes existing CQ / Downside Risk / Relative Strength / Regime
evidence. It creates no new AI or model.

## Overheated / Decelerating Handling

The implemented interaction recognizes the Phase30-V class:

```text
strong medium-term structure
+ short-term reversal
+ deceleration
+ elevated exhaustion / reversal / volatility risk
```

That shape becomes `OVERHEATED_DECELERATING_ENTRY` and maps to BUY_WAIT for
BUY_NEW rather than FULL allocation. Elevated risk alone does not become a hard
reject; mixed risk without the full interaction becomes
`CONTINUATION_WITH_CAUTION` / reduced allocation semantics.

## BUY_WAIT

BUY_WAIT remains:

```text
non-Pending = true
next PIT date reevaluation = true
SELL independent = true
future commitment = false
```

Portfolio Construction consumes Entry Admission BUY_WAIT as BUY-side exclusion
for the day. It does not alter SELL / REDUCE / EXIT authority.

## One-Lot Admission

`portfolio_construction.py` now materializes `one_lot_admission` during
lot-aware final reallocation.

Minimum fields include:

- continuous target weight,
- minimum executable weight,
- effective post-trade weight,
- overshoot weight / ratio,
- Strategy concentration tolerance,
- Safety hard-cap status,
- Entry Admission state/action,
- ADD worthiness,
- relative opportunity,
- opportunity cost,
- residual destination if skipped,
- reason codes.

## Strategy Target vs Safety

The implementation preserves:

```text
Strategy target != Safety hard cap
```

Safety hard cap preservation remains necessary but is not sufficient for
Strategy one-lot concentration. Overheated / reversal / BUY_WAIT entry evidence
can defer a one-lot overshoot even when Safety remains preserved.

## Residual Reallocation

Phase29 residual recycling remains active. The queue now considers
quality-adjusted Entry / ADD evidence before priority and symbol tie-breaks.
Skipped or deferred capital can move to:

```text
BUY_NEW
BUY_ADD
REENTRY
Cash
```

Cash remains a valid destination. No forced investment or forced exposure was
introduced.

## ADD / Winner Concentration

ADD remains possible when incremental ADD evidence is strong. A high-quality ADD
fixture with Strategy soft-cap one-lot overshoot still receives incremental
capital.

Weak survivors are separated from ADD-worthy positions: a current position can
remain baseline-held while `NO_ADD` blocks incremental one-lot concentration.

## SELL Preservation

```text
BUY_SELL_INDEPENDENCE = PASS
```

Phase30-W did not redesign SELL / REDUCE. BUY_WAIT, Entry rejection, and
one-lot deferral affect only BUY-side capital deployment.

## 78780-Type Regression

No 78780/date-specific test was added.

The general fixture shape:

```text
strong medium momentum
negative short momentum
deceleration
elevated exhaustion / reversal / volatility
large one-lot overshoot
```

now produces:

```text
entry_state = OVERHEATED_DECELERATING_ENTRY
admission_action = BUY_WAIT
one_lot_admission.status = DEFER
```

It does not produce FULL allocation plus extreme one-lot concentration.

## Winner Preservation

```text
healthy BUY remains possible = YES
BUY_WAIT remains recoverable = YES
ADD remains possible = YES
no forced Cash = YES
no forced exposure = YES
```

Healthy continuation produces `BUY_NEW_ALLOWED`; high-quality ADD remains
allocatable; skipped capital can recycle to another executable candidate or
Cash.

## Production Integrity

```text
PHASE30_P_STRATEGY_MIGRATION_PRESERVED = YES
ONE_PRODUCTION_STRATEGY_AUTHORITY_PATH = YES
LEGACY_STRATEGY_PATH_REINTRODUCED = NO
PHASE30_S_HANDOFF_DEFECT_RECURRENCE = NO
```

## Leakage

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
```

## New AI / Model

```text
NEW_AI_CREATED = NO
PRODUCTION_MODEL_RETRAINED = NO
ACCEPTED_GENERATION_CHANGED = NO
Expected Edge = UNCALIBRATED
```

## Tests

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase30_w_pycache python3 -m compileall src/ai_fund_lab_v2/strategy
PASS

PYTHONPYCACHEPREFIX=/private/tmp/phase30_w_pycache python3 -m pytest \
  tests/strategy/test_phase30_w_entry_one_lot_repair.py \
  tests/strategy/test_phase30_p_strategy_intelligence_production_migration.py \
  tests/strategy/test_phase30_s_position_sizing_production_handoff.py \
  tests/strategy/test_phase22_e_portfolio_construction.py \
  tests/strategy/test_phase22_g_runtime_planning.py
163 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase30_w_pycache python3 -m pytest \
  tests/strategy/test_phase30_j_strategy_intelligence.py \
  tests/strategy/test_phase30_l_strategy_intelligence_gap_repair.py \
  tests/strategy/test_phase30_n_strategy_intelligence_campaign_authority.py
15 passed
```

Additional full Strategy sweep:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase30_w_pycache python3 -m pytest tests/strategy
510 passed, 4 failed
```

The four failures are not on the Phase30-W changed path:

- three dynamic capacity asset proportionality expectation failures,
- one rank-authority private helper call shape failure.

## Long Historical

```text
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

No fresh 10BD / 20BD / 100BD / long Historical was executed by Codex.

## Fresh Validation Gate

```text
USER_OPERATED_FRESH_VALIDATION_READY
```

## Recommended Next Task

```text
Phase30-X - Post-Repair Fresh Validation
```
