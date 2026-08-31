# Phase32-BQ — Lot-Blocked PM REDUCE Reconsidered FULL EXIT Production Implementation

## Objective

Implement the narrow production promotion accepted by Phase32-BP:

```text
PM REDUCE
-> REDUCE unexecutable specifically because of discrete-lot granularity
-> BO semantic reconsideration = SHADOW_FULL_EXIT
-> Strategy-owned canonical reconsidered FULL EXIT
-> ordinary downstream SELL_EXIT
```

No fresh-run, resume, recover, replay, or long Historical command was executed by Codex.

## References Read

- `docs/phase_reports/phase32_bp_bo_full_exit_production_promotion_acceptance_read_only_audit.md`
- `docs/phase_reports/phase32_bo_profit_cushion_contextualized_shadow_refinement_evaluation.md`
- `docs/02_architecture/position_management_reduce_quantity_contract.md`
- `docs/02_architecture/position_management_decision_trace_contract.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`

Phase32-BP accepted only a narrow production path with authority owned by the Strategy materialization adapter with explicit PM-derived reconsideration authority. Phase32-BO semantics were preserved as-is.

## Root Cause / Implementation Boundary

Before BQ, a PM `REDUCE` whose partial quantity rounded to zero under Japanese round-lot constraints could only materialize as intentional no-order evidence. That was correct for ordinary lot-blocked REDUCE cases, but BP accepted a narrower case where the already-validated BO semantic track proves that the lot-blocked REDUCE is a deteriorating winner that should be reconsidered as FULL EXIT.

The implemented boundary is:

```text
Sell Planning quantity materialization
after REDUCE quantity contract
before executable SELL order planning / Pending publication
```

Runtime, Submit, Execution, Ledger, and broker adapters do not invent EXIT. They only consume the resulting ordinary `SELL_EXIT` item when the Strategy-owned reconsideration authority passes.

## Canonical Authority

```text
PM_REDUCE_LOT_BLOCKED_RECONSIDERED_FULL_EXIT
```

Contract version:

```text
phase32_bq_pm_reduce_lot_blocked_reconsidered_full_exit.v1
```

Required eligibility:

- source PM action is `REDUCE`
- campaign and current-position authority exist and match
- desired reduce quantity is positive
- executable reduce quantity is exactly zero
- no-order semantic is specifically `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`
- same-date PIT Strategy Intelligence and market context evidence are available and current
- BO reconsideration result is `SHADOW_FULL_EXIT`
- stale, cross-run, future-dated, malformed, or mismatched evidence fails closed

Explicit exclusions:

- executable REDUCE
- minimum-notional no-order
- BUY / ADD / HOLD
- native PM EXIT
- BO HOLD
- BO INSUFFICIENT
- ambiguous BO episodes outside the accepted FULL_EXIT subset

## Files Changed

- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py`
- `docs/02_architecture/position_management_reduce_quantity_contract.md`
- `docs/02_architecture/position_management_decision_trace_contract.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/phase_reports/phase32_bq_lot_blocked_reduce_reconsidered_full_exit_production_implementation.md`

## Behavior Implemented

Eligible lot-blocked PM REDUCE is now reconsidered through `build_unrepresentable_reduce_exit_shadow_payload`. When the BO semantic decision is `SHADOW_FULL_EXIT`, Sell Planning creates an ordinary full-quantity `SELL_EXIT` order plan item.

The quantity contract preserves:

- `source_pm_action = REDUCE`
- original `source_decision_id`
- original PM reason
- original reduce intensity
- original REDUCE quantity contract
- `reconsidered_action = FULL_EXIT`
- `reconsideration_reason = PM_REDUCE_LOT_BLOCKED_RECONSIDERED_FULL_EXIT`
- BO PIT evidence and artifact hash
- campaign / position campaign id
- `runtime_invented_exit = false`

Same-day retry/idempotency now reuses an equivalent existing SELL Pending instead of overwriting or duplicating it.

## Production Paths Preserved

- executable REDUCE remains executable partial REDUCE
- BO HOLD remains no promotion
- BO INSUFFICIENT remains no promotion
- native PM EXIT remains unchanged
- minimum-notional no-order remains unchanged
- BUY / ADD / G129 authority remains unchanged
- KI-006 BUY_WAIT / explicit zero ADD preservation remains unchanged
- AX-BE mixed review, pending lifecycle, temporal safety, and feature-date gate contracts remain unchanged

## Focused Validation

Compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py
PASS
```

BQ direct focused tests:

```text
python3 -m pytest tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py -q
19 passed
```

Adjacent regression suite:

```text
python3 -m pytest \
  tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py \
  tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py \
  tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py \
  tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py \
  tests/runtime_v2/test_phase30_ak9r27_pending_review_scope_authority.py \
  tests/runtime_v2/test_phase30_ak9r28_historical_safety_temporal_authority.py \
  tests/strategy/test_phase31_c0d_unrepresentable_reduce_exit_shadow.py \
  tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py \
  tests/strategy/test_phase22_g_runtime_planning.py::test_phase32_f_runtime_does_not_resurrect_buy_wait_add_when_ps_delta_zero \
  tests/strategy/test_phase32_x_recoverable_deterioration_episode.py -q
143 passed
```

Diff hygiene:

```text
git diff --check ... selected BQ files
PASS
```

## Required Final Answers

1. `PRODUCTION_IMPLEMENTED`: YES
2. `PRODUCTION_AUTHORITY_OWNER`: Strategy materialization adapter with explicit PM-derived reconsideration authority
3. `RUNTIME_INVENTS_EXIT`: NO
4. `BO_FULL_EXIT_PROMOTED`: YES, only for eligible lot-blocked REDUCE
5. `EXECUTABLE_REDUCE_UNCHANGED`: YES
6. `BO_HOLD_UNCHANGED`: YES
7. `BO_INSUFFICIENT_UNCHANGED`: YES
8. `NATIVE_PM_EXIT_UNCHANGED`: YES
9. `MIN_NOTIONAL_UNCHANGED`: YES
10. `CAMPAIGN_PRESERVED`: YES
11. `ORIGINAL_PM_REDUCE_PROVENANCE_PRESERVED`: YES
12. `RECONSIDERED_EXIT_AUDITABLE`: YES
13. `DUPLICATE_GUARD_IMPLEMENTED`: YES
14. `RESUME_RETRY_IDEMPOTENCY`: PASS in focused same-day Pending retry test
15. `PENDING_REVIEW_SAFETY`: PASS in adjacent focused regressions
16. `HISTORICAL_TEMPORAL_SAFETY`: PASS in adjacent focused regressions
17. `PROFIT_CUSHION_SEMANTIC_PRESERVED`: YES
18. `NEW_FEATURE_ADDED`: NO
19. `NEW_MODEL_ADDED`: NO
20. `THRESHOLD_OR_WEIGHT_CHANGED`: NO
21. `AMBIGUOUS_297_PROMOTED`: NO
22. `COMMON_SOT_UPDATED`: YES
23. `FOCUSED_REGRESSION_RESULT`: PASS, 143 selected focused regressions
24. `FRESH_RUN_EXECUTED_BY_CODEX`: NO
25. `RESUME_EXECUTED_BY_CODEX`: NO
26. `READY_FOR_USER_LONG_HISTORICAL_VALIDATION`: YES
27. `EXACT_USER_VALIDATION_COMMAND`:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --start-date 2022-10-03 \
  --business-days 650 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

28. `FINAL_JUDGMENT`: `PHASE32_BQ_LOT_BLOCKED_REDUCE_RECONSIDERED_FULL_EXIT_PRODUCTION_IMPLEMENTED_READY_FOR_USER_LONG_HISTORICAL_VALIDATION`

## Final Judgment

`PHASE32_BQ_LOT_BLOCKED_REDUCE_RECONSIDERED_FULL_EXIT_PRODUCTION_IMPLEMENTED_READY_FOR_USER_LONG_HISTORICAL_VALIDATION`
