# Phase31-B10 — Alternative C Mutating Marginal Capital Priority Implementation

## PRIMARY_JUDGMENT

`PHASE31_B10_ALTERNATIVE_C_MUTATING_MARGINAL_CAPITAL_PRIORITY_IMPLEMENTED`

Alternative C is now implemented as a narrow Production-common ordering authority. Portfolio Construction owns canonical marginal-capital priority across already-eligible BUY_NEW and already-positive-increment BUY_ADD candidates, and Runtime/Pending reserved-cash feasibility consumes that order.

This is not Alternative E. No thresholds, caps, PM ADD semantics, Market Context logic, Submit, Execution, SELL logic, winner headroom, or Safety hard cap were changed.

## PRODUCTION_AUTHORITY

`src/ai_fund_lab_v2/strategy/marginal_capital_value.py`

Authority:

`MARGINAL_CAPITAL_VALUE_AUTHORITY`

Contract:

`phase31_b10_marginal_capital_value_authority.v1`

Production consumers:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/runtime_planning.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`

Diagnostic shadow now delegates comparison semantics to the Production-common authority:

- `src/ai_fund_lab_v2/strategy/marginal_capital_value_shadow.py`

## Contract Results

`PC_OWNS_CANONICAL_PRIORITY = YES`

`RUNTIME_CONSUMES_PC_PRIORITY = YES`

`PENDING_CASH_PRESERVES_PRIORITY = YES`

`BUY_ADD_UNCONDITIONAL_PRIORITY = NO`

`BUY_NEW_UNCONDITIONAL_PRIORITY = NO`

`STRONG_ADD_PROTECTION = PASS`

`STRONG_NEW_PROTECTION = PASS`

`EQUAL_PRIORITY_STABLE_ORDER = PASS`

`QUANTITY_AUTHORITY_PRESERVED = YES`

`CASH_SEMANTICS_PRESERVED = YES`

`BUY_SELL_INDEPENDENCE_PRESERVED = YES`

`PENDING_REVIEW_SCOPE_PRESERVED = YES`

`NORMAL_STRATEGY_CAP_CHANGED = NO`

`SAFETY_HARD_CAP_CHANGED = NO`

`WINNER_HEADROOM_ADDED = NO`

`FUTURE_INFORMATION_USED = NO`

`LEGACY_PRIORITY_FALLBACK_ACTIVE = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`USER_OPERATED_FRESH_VALIDATION_READY = YES`

## Implementation Summary

Added:

- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- `tests/strategy/test_phase31_b10_alternative_c_marginal_capital_priority.py`
- this report

Updated:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/runtime_planning.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/models.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`
- `src/ai_fund_lab_v2/strategy/marginal_capital_value_shadow.py`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/runtime_architecture_v2.md`

Portfolio Construction now materializes:

- `canonical_marginal_capital_priority_index`
- `marginal_capital_value_class`
- `marginal_capital_value_authority`

Runtime Planning propagates the authority into BUY plans and assigns canonical Strategy order. Strategy authority carries the same fields into `PendingOrderItem` and `_cash_feasible_buy_batch` evidence, so Pending reserved-cash feasibility consumes candidates in canonical PC priority order.

If comparison evidence is insufficient, the implementation preserves deterministic stable order with explicit insufficiency evidence. It does not invent a score or activate a legacy priority fallback.

## B0 Regressions

`B0_2022_08_19_REGRESSION = PASS`

Focused regression demonstrates that when 94320 has canonical marginal priority 1, it reaches reserved-cash ordering before lower-canonical BUY_NEW items and is evaluated first by `_cash_feasible_buy_batch`.

`B0_2022_08_24_REGRESSION = PASS`

Focused regression demonstrates that 94320 reaches reserved-cash ordering before 43760 and receives the first reservation opportunity under limited cash.

These are development regressions only. They do not assert profitability.

## Guardrails

Preserved:

- PM ADD semantics
- Expected Edge thresholds
- Incremental Investment Value thresholds
- Opportunity Cost thresholds
- Market Context logic
- normal Strategy cap
- Safety hard cap
- winner headroom absence
- Position Sizing quantity authority
- Pending Review Scope authority
- Submit feasibility authority
- Execution path
- SELL independence

Not implemented:

- ADD always first
- NEW always first
- fixed ADD reserve
- fixed NEW/ADD split
- ADD bonus
- NEW penalty
- numeric lifecycle premium
- 94320-specific rule
- new alpha feature
- performance-tuned threshold
- Alternative E winner headroom

## TEST_RESULTS

Compile:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/phase31_b10_pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/marginal_capital_value.py src/ai_fund_lab_v2/strategy/marginal_capital_value_shadow.py src/ai_fund_lab_v2/strategy/portfolio_construction.py src/ai_fund_lab_v2/strategy/runtime_planning.py src/ai_fund_lab_v2/runtime_v2/pending/models.py src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py
```

Result: PASS

B10 focused tests:

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase31_b10_pycache python3 -m pytest -q tests/strategy/test_phase31_b10_alternative_c_marginal_capital_priority.py
```

Result:

`7 passed in 0.19s`

Shadow + reserved-cash regression:

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase31_b10_pycache python3 -m pytest -q tests/strategy/test_phase31_b4_marginal_capital_value_shadow.py tests/strategy/test_phase31_b6_marginal_capital_shadow_bridge.py tests/strategy/test_phase31_b8_pending_cash_causality_bridge.py tests/runtime_v2/test_phase30_ak3r2b_cash_feasible_buy_batch.py tests/strategy/test_phase31_b10_alternative_c_marginal_capital_priority.py
```

Result:

`33 passed in 0.44s`

Portfolio Construction / lot regression:

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase31_b10_pycache python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase30_w_entry_one_lot_repair.py tests/strategy/test_phase31_b10_alternative_c_marginal_capital_priority.py
```

Result:

`129 passed in 2.27s`

Submit / Pending / guard regression:

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase31_b10_pycache python3 -m pytest -q tests/runtime_v2/test_phase26_step6_submit_guard_authority.py tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py tests/runtime_v2/test_phase31_a5_executable_membership_guard.py
```

Result:

`56 passed in 2.48s`

No fresh-run, resume, replay, 25BD, 100BD, 500BD, or long Historical was executed by Codex.

## User-Operated Fresh Validation Command

Recommended initial clean validation command, to be run by the user only:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --start-date 2022-08-10 \
  --business-days 20 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Do not add `--json`.

## Performance Claim Restriction

B10 establishes correct Production-common ordering behavior only.

It does not claim:

- return improved
- MDD improved
- winner contribution improved
- final profitability proven

Performance must be evaluated separately from clean user-operated Historical evidence.

## NEXT_RECOMMENDATION

User-operated fresh validation of Alternative C behavior, followed by read-only review of:

- BUY_NEW / BUY_ADD ordering evidence
- 94320 B0 regression days
- Pending reserved-cash causality
- BUY/SELL independence
- quantity authority preservation
- Safety / guard behavior
- capital deployment and risk metrics

Remain in Phase31. Alternative E remains unauthorized.
