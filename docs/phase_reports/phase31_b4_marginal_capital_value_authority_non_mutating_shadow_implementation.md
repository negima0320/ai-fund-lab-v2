# Phase31-B4 — MARGINAL_CAPITAL_VALUE_AUTHORITY Non-Mutating Shadow Implementation

## PRIMARY_JUDGMENT

PHASE31_B4_MARGINAL_CAPITAL_VALUE_AUTHORITY_NON_MUTATING_SHADOW_IMPLEMENTED

## Summary

B4 added a Strategy-owned, non-mutating shadow producer for `MARGINAL_CAPITAL_VALUE_AUTHORITY_SHADOW`.

The producer answers the read-only question: if Alternative C existed today, how would already-relevant `BUY_NEW` and positive-increment `BUY_ADD` marginal capital units be ordered using current PIT Strategy/Portfolio Construction evidence?

It does not connect to the Production Runtime path and does not alter Portfolio Construction, Position Sizing, Runtime Planning, Pending, Submit, Execution, fills, ledger/current valuation, Safety, or Market Context behavior.

## Required Fields

SHADOW_PRODUCER = `ai_fund_lab_v2.strategy.marginal_capital_value_shadow`

SHADOW_ARTIFACT = `strategy_artifacts/marginal_capital_value_shadow/<business_date>/marginal_capital_value_shadow.json`

PC_OWNS_PRIORITY = YES

ACTUAL_PC_DECISION_MUTATED = NO

ACTUAL_PS_QUANTITY_MUTATED = NO

ACTUAL_RUNTIME_ORDER_MUTATED = NO

ACTUAL_PENDING_MUTATED = NO

ACTUAL_SUBMIT_OR_EXECUTION_MUTATED = NO

BUY_ADD_LABEL_PRIORITY = NO

BUY_NEW_LABEL_PRIORITY = NO

STRONG_NEW_PROTECTION = PASS

WEAK_ADD_PROTECTION = PASS

COMPARISON_INSUFFICIENT_EXPLICIT = PASS

LOT_AWARE_SHADOW = PASS

FUTURE_INFORMATION_USED = NO

NORMAL_STRATEGY_CAP_CHANGED = NO

SAFETY_HARD_CAP_CHANGED = NO

BUY_SELL_INDEPENDENCE_PRESERVED = YES

B0_DEVELOPMENT_CASES_REPRODUCIBLE = YES, via focused 94320 shadow fixture coverage.

LONG_HISTORICAL_EXECUTED = NO

SHADOW_VALIDATION_READY = YES

MUTATING_ALTERNATIVE_C_AUTHORIZED = NO

## Implementation

Added:

- `src/ai_fund_lab_v2/strategy/marginal_capital_value_shadow.py`
- `tests/strategy/test_phase31_b4_marginal_capital_value_shadow.py`

The shadow artifact includes:

- `schema_version`
- `business_date`
- `producer`
- `authority_type = MARGINAL_CAPITAL_VALUE_AUTHORITY_SHADOW`
- `mode = NON_MUTATING_SHADOW`
- `pit_status`
- `future_information_used = false`
- `candidate_units`
- `canonical_shadow_order`
- `actual_pc_order`
- `actual_runtime_cash_batch_order`
- `order_differences`
- `comparison_status`
- `lot_materialization_status`
- `source_artifacts`
- `source_hashes`
- `actual_decision_mutated = false`

Candidate units materialize the requested identity, lifecycle intent, semantic comparison class, source evidence, expected-edge state, incremental-value state, opportunity-cost state, rank, market context state, weights, accepted incremental weight, lot-aware quantity requirement, lot feasibility, concentration status, comparison sufficiency, and actual PC/Runtime order where available.

## Semantic Contract

The shadow class set is:

- `BLOCKED_OR_NOT_ELIGIBLE`
- `ELIGIBLE_WEAK`
- `ELIGIBLE_COMPARABLE`
- `ELIGIBLE_STRONG`
- `REVIEW_REQUIRED`
- `COMPARISON_INSUFFICIENT`

`BUY_ADD` receives no priority from the ADD label alone. Strong ADD treatment requires explicit PIT-valid lifecycle evidence: expected edge non-weakening/pass, positive incremental investment value, opportunity cost pass, ADD-worthiness/pass, and same-campaign continuation evidence.

`BUY_NEW` receives no priority from the NEW label alone. Strong NEW treatment requires explicit PIT entry/opportunity evidence.

When evidence is insufficient, the artifact emits `COMPARISON_INSUFFICIENT`; deterministic fallback ordering is display-only and is not treated as investment superiority.

## No Future Leakage

The producer filters known future/outcome fields out of `source_evidence` and sets `future_information_used = false`.

It does not consume future price, future/forward return, future PnL, later campaign outcome, MFE/MAE labels, selected/bought outcome, fill outcome, future-known regime, or Historical performance labels.

## TEST_RESULTS

Focused unit tests:

`PYTHONPATH=src python3 -m pytest -q tests/strategy/test_phase31_b4_marginal_capital_value_shadow.py`

Result:

`8 passed in 0.04s`

Compile check:

`PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache PYTHONPATH=src python3 -m py_compile src/ai_fund_lab_v2/strategy/marginal_capital_value_shadow.py`

Result:

PASS

The first compile attempt without `PYTHONPYCACHEPREFIX` failed because Python attempted to write bytecode under `/Users/negishi/Library/Caches/com.apple.python/...`, outside the permitted workspace/cache path. Re-running with the pycache prefix under `/private/tmp` passed.

## Scope Control

No fresh-run, resume, replay, 25BD, 100BD, 500BD, or long Historical runtime was executed.

No Strategy/Runtime production path was connected to this shadow producer.

No actual PC output, PS quantity, Runtime Planning order, Pending membership, Submit, Execution, fill, ledger/current, Safety, Market Context, Strategy cap, or Safety hard cap behavior was mutated.

## Next Recommendation

Run a focused shadow-evidence validation task before any mutating Alternative C authorization.
