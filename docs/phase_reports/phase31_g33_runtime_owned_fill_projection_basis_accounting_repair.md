# Phase31-G33 - Runtime-Owned Fill Projection Basis / Accounting Repair

Task type: IMPLEMENTATION - FOCUSED ACCOUNTING / BASIS REPAIR

Fresh run / resume / replay / Historical rerun / long Historical: NO

## Primary Judgment

PRIMARY_JUDGMENT =
PHASE31_G33_RUNTIME_OWNED_FILL_PROJECTION_BASIS_ACCOUNTING_REPAIRED_ACCEPTED

G33 repairs the single G32 blocker in runtime-owned fill projection. The repair
does not change Strategy, Market Context, Market Quality, Risk Pacing,
Candidate / BUY Quality, PM, Portfolio Construction, Position Sizing, Re-entry,
ADD value semantics, Safety, Submit Strategy logic, thresholds, parameters, or
Historical behavior.

## Pre-Repair Reproduction

The exact G32 failing test was reproduced unchanged before modification:

```text
tests/runtime_v2/test_phase24_h_cost_basis_authority.py::test_phase24_h_phase24g_generalized_sequence_reconciles_execution_basis_pnl
```

Observed:

```text
expected open cost_basis sum = 659,070
actual open cost_basis sum   = 711,030
delta                        = 51,960
```

PRE_REPAIR_FAILURE_REPRODUCED = YES

## Root Cause

Runtime-owned fill projection filtered canonical execution events with:

```text
event_date < current_as_of -> already applied
```

even when `current_as_of` was later than the target projection business date.
In the failing sequence, the bootstrap empty Current carried
`as_of = 2026-01-01` while the projection target and executions were
`2022-07-29` and earlier. All target-period executions were incorrectly removed
from the pending event set, so open basis was rebuilt from latest position
valuation `average_price` rows instead of execution-derived cost basis.

The authoritative idempotency boundary is the explicit applied execution
identity set. Current `as_of` can suppress earlier executions only when that
Current date is not after the target projection business date.

ROOT_CAUSE_CLASS =
PROJECTED_LEDGER_STATE_STALE

ROOT_CAUSE_CONFIDENCE =
HIGH

## Repair

Changed:

- `src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py`

The event lower-bound check now applies only when:

```text
current_as_of <= target business_date
```

Updated permanent SoT:

- `docs/02_architecture/runtime_temporal_freshness_contract.md`

The architecture now states that future-dated empty/bootstrap Current timestamps
must not be treated as proof that older target-period executions were already
applied.

## Fill-by-Fill Accounting Trace

Each fill below uses execution price as the canonical basis price. Basis is
removed on SELL using moving-average open cost. Full EXIT clears open cost.

| # | Date | Symbol | Side | Qty | Price | Pre qty | Pre cost | Pre avg | Post qty | Post cost | Post avg | Realized delta | Cash delta |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 2022-07-04 | 94320 | BUY | 1100 | 155.2 | 0 | 0 | 0.0000 | 1100 | 170720 | 155.2000 | 0 | -170720 |
| 2 | 2022-07-05 | 94320 | BUY | 100 | 156.6 | 1100 | 170720 | 155.2000 | 1200 | 186380 | 155.3167 | 0 | -15660 |
| 3 | 2022-07-11 | 94340 | BUY | 1100 | 153.9 | 0 | 0 | 0.0000 | 1100 | 169290 | 153.9000 | 0 | -169290 |
| 4 | 2022-07-11 | 23880 | BUY | 1400 | 132 | 0 | 0 | 0.0000 | 1400 | 184800 | 132.0000 | 0 | -184800 |
| 5 | 2022-07-13 | 66590 | BUY | 1000 | 145 | 0 | 0 | 0.0000 | 1000 | 145000 | 145.0000 | 0 | -145000 |
| 6 | 2022-07-14 | 23880 | SELL | 1400 | 113 | 1400 | 184800 | 132.0000 | 0 | 0 | 0.0000 | -26600 | 158200 |
| 7 | 2022-07-15 | 66590 | SELL | 1000 | 122 | 1000 | 145000 | 145.0000 | 0 | 0 | 0.0000 | -23000 | 122000 |
| 8 | 2022-07-15 | 23880 | BUY | 1400 | 113 | 0 | 0 | 0.0000 | 1400 | 158200 | 113.0000 | 0 | -158200 |
| 9 | 2022-07-19 | 24370 | BUY | 100 | 1235 | 0 | 0 | 0.0000 | 100 | 123500 | 1235.0000 | 0 | -123500 |
| 10 | 2022-07-19 | 23880 | SELL | 1400 | 115 | 1400 | 158200 | 113.0000 | 0 | 0 | 0.0000 | 2800 | 161000 |
| 11 | 2022-07-19 | 66590 | BUY | 1400 | 122 | 0 | 0 | 0.0000 | 1400 | 170800 | 122.0000 | 0 | -170800 |
| 12 | 2022-07-20 | 66590 | SELL | 1400 | 118 | 1400 | 170800 | 122.0000 | 0 | 0 | 0.0000 | -5600 | 165200 |
| 13 | 2022-07-20 | 23880 | BUY | 1400 | 120 | 0 | 0 | 0.0000 | 1400 | 168000 | 120.0000 | 0 | -168000 |
| 14 | 2022-07-21 | 23880 | SELL | 1400 | 122 | 1400 | 168000 | 120.0000 | 0 | 0 | 0.0000 | 2800 | 170800 |
| 15 | 2022-07-22 | 23880 | BUY | 1500 | 119 | 0 | 0 | 0.0000 | 1500 | 178500 | 119.0000 | 0 | -178500 |
| 16 | 2022-07-25 | 66590 | BUY | 1600 | 102 | 0 | 0 | 0.0000 | 1600 | 163200 | 102.0000 | 0 | -163200 |
| 17 | 2022-07-25 | 23880 | SELL | 1500 | 110 | 1500 | 178500 | 119.0000 | 0 | 0 | 0.0000 | -13500 | 165000 |
| 18 | 2022-07-26 | 66590 | SELL | 1600 | 103 | 1600 | 163200 | 102.0000 | 0 | 0 | 0.0000 | 1600 | 164800 |
| 19 | 2022-07-26 | 23880 | BUY | 1300 | 120 | 0 | 0 | 0.0000 | 1300 | 156000 | 120.0000 | 0 | -156000 |
| 20 | 2022-07-26 | 24370 | SELL | 100 | 1249 | 100 | 123500 | 1235.0000 | 0 | 0 | 0.0000 | 1400 | 124900 |
| 21 | 2022-07-27 | 66590 | BUY | 1600 | 103 | 0 | 0 | 0.0000 | 1600 | 164800 | 103.0000 | 0 | -164800 |
| 22 | 2022-07-28 | 66590 | SELL | 1600 | 103 | 1600 | 164800 | 103.0000 | 0 | 0 | 0.0000 | 0 | 164800 |
| 23 | 2022-07-28 | 24370 | BUY | 100 | 1370 | 0 | 0 | 0.0000 | 100 | 137000 | 1370.0000 | 0 | -137000 |
| 24 | 2022-07-29 | 66590 | BUY | 1600 | 104 | 0 | 0 | 0.0000 | 1600 | 166400 | 104.0000 | 0 | -166400 |
| 25 | 2022-07-29 | 23880 | SELL | 1300 | 121 | 1300 | 156000 | 120.0000 | 0 | 0 | 0.0000 | 1300 | 157300 |

Final reconciled state:

```text
open cost_basis = 659,070
cash            = 282,130
realized_pnl    = -58,800
market_value    = 653,650
unrealized_pnl  = -5,420
total delta     = -64,220
```

FIRST_DIVERGENCE_FILL_IDENTIFIED =
YES

FIRST_DIVERGENCE_SYMBOL =
94320

FIRST_DIVERGENCE_SIDE =
BUY

FIRST_DIVERGENCE_OPERATION =
BUY

FIRST_DIVERGENCE_EXPECTED_STATE =
post quantity 1100, post cost_basis 170720, average_price 155.2, cash delta -170720

FIRST_DIVERGENCE_ACTUAL_STATE =
fill incorrectly excluded by future `current_as_of`; state unchanged and later open basis derived from latest position snapshot

## Accounting Authority Inventory

| Component | Quantity | Cost basis / average price | Realized PnL | Cash | Classification |
| --- | --- | --- | --- | --- | --- |
| Runtime-owned fill projection | writes projected Current from accepted order/execution/fill evidence | writes open basis and moving average | derives realized PnL from SELL proceeds minus disposed basis | applies execution cash effects | AUTHORITATIVE |
| Execution read-only pipeline / ledger projection | writes execution/order/position ledger evidence | supplies execution and position evidence | evidence source | evidence source | AUTHORITATIVE_INPUT |
| Current valuation refresh | updates valuation price / market value / unrealized PnL under basis contract | must preserve quantity/average/basis metadata | no realized PnL authority | no trade cash authority | DERIVED_READ_ONLY_FOR_BASIS |
| Performance/event readers | normalize ledger execution events | read-only | read-only | read-only | DERIVED_READ_ONLY |
| Latest broker/position snapshot average price fallback | valuation evidence only when execution-derived cost is unavailable | fallback, fail-closed by basis checks | no authority | no authority | LEGACY_COMPATIBILITY_CHECK |

ACCOUNTING_AUTHORITY_INVENTORY_COMPLETE = YES

DUPLICATE_COST_BASIS_AUTHORITY_COUNT = 0

DUPLICATE_POSITION_QUANTITY_AUTHORITY_COUNT = 0

RUNTIME_FILL_PROJECTION_AUTHORITY_CHANGED = NO

## Verification

Original failed test:

```bash
python3 -m pytest tests/runtime_v2/test_phase24_h_cost_basis_authority.py::test_phase24_h_phase24g_generalized_sequence_reconciles_execution_basis_pnl -q
```

Result:

```text
1 passed
```

Focused basis and projection regressions:

```bash
python3 -m pytest tests/runtime_v2/test_phase24_h_cost_basis_authority.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py -q
```

Result:

```text
25 passed
```

G32 focused suite after repair:

```bash
python3 -m pytest tests/runtime_v2/test_phase31_g30_authority_lineage.py tests/strategy/test_phase22_a_market_context.py tests/strategy/test_phase22_l_market_context_resolution.py tests/strategy/test_phase22_c_portfolio_policy.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase26_h_adaptive_buy_quality.py tests/strategy/test_phase22_d_position_management.py tests/strategy/test_phase22_g_runtime_planning.py tests/strategy/test_phase30_s_position_sizing_production_handoff.py tests/strategy/test_phase30_w_entry_one_lot_repair.py tests/strategy/test_phase31_b10_alternative_c_marginal_capital_priority.py tests/strategy/test_phase29_l21k_prior_exit_materialization.py tests/runtime_v2/test_phase26_step5_runtime_planning_authority.py tests/runtime_v2/test_phase26_step6_submit_guard_authority.py tests/runtime_v2/test_phase17_bv10_historical_sell_execution_projection.py tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py tests/runtime_v2/test_phase19_bi_empty_pending_no_action_contract.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py tests/runtime_v2/test_phase24_h_cost_basis_authority.py tests/runtime_v2/test_phase20_l_long_run_readiness_destructive.py
```

Result:

```text
552 passed
```

PY_COMPILE =
PASS with `PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache-g33 python3 -m compileall -q src tests`

GIT_DIFF_CHECK =
PASS

## Required Summary Output

PRIMARY_JUDGMENT =
PHASE31_G33_RUNTIME_OWNED_FILL_PROJECTION_BASIS_ACCOUNTING_REPAIRED_ACCEPTED

PRE_REPAIR_FAILURE_REPRODUCED =
YES

PRE_REPAIR_EXPECTED_COST_BASIS =
659070

PRE_REPAIR_ACTUAL_COST_BASIS =
711030

PRE_REPAIR_DELTA =
51960

FILL_BY_FILL_ACCOUNTING_TRACE_COMPLETE =
YES

FIRST_DIVERGENCE_FILL_IDENTIFIED =
YES

FIRST_DIVERGENCE_SYMBOL =
94320

FIRST_DIVERGENCE_SIDE =
BUY

FIRST_DIVERGENCE_OPERATION =
BUY

ROOT_CAUSE_CLASS =
PROJECTED_LEDGER_STATE_STALE

ROOT_CAUSE_CONFIDENCE =
HIGH

ACCOUNTING_AUTHORITY_INVENTORY_COMPLETE =
YES

DUPLICATE_COST_BASIS_AUTHORITY_COUNT =
0

RUNTIME_FILL_PROJECTION_AUTHORITY_CHANGED =
NO

BUY_BASIS_CONTRACT =
PASS

ADD_BASIS_CONTRACT =
PASS

PARTIAL_SELL_BASIS_CONTRACT =
PASS

FULL_EXIT_BASIS_CLEARANCE =
PASS

REENTRY_BASIS_REINITIALIZATION =
PASS

MULTI_SYMBOL_ACCOUNTING_ISOLATION =
PASS

PRICE_QUANTITY_ADJUSTMENT_BASIS_CONTRACT =
PASS

BASIS_METADATA_MISMATCH_COUNT =
0

REALIZED_PNL_RECONCILIATION =
PASS

UNREALIZED_PNL_RECONCILIATION =
PASS

TOTAL_EQUITY_RECONCILIATION =
PASS

CASH_DECISION_EQUIVALENCE =
PASS

POSITION_QUANTITY_DECISION_EQUIVALENCE =
PASS

STRATEGY_DECISION_EQUIVALENCE =
PASS

G33_PRODUCTION_BEHAVIOR_CHANGE_CLASS =
ACCOUNTING_BASIS_REPAIR_ONLY_NO_STRATEGY_DECISION_CHANGE

FILL_IDEMPOTENCY =
PASS

DUPLICATE_FILL_ECONOMIC_EFFECT_COUNT =
0

BASIS_STATE_RELOAD_COMPATIBILITY =
PASS

BASIS_FIELD_LOSS_ON_RELOAD_COUNT =
0

STRATEGY_AUTHORITY_LINEAGE_REGRESSION =
NO

LINEAGE_HASH_MISMATCH_COUNT =
0

FUTURE_INPUT_COUNT =
0

HISTORICAL_RESULT_INPUT_COUNT =
0

PAPER_LEDGER_STRATEGY_INPUT_COUNT =
0

AUDIT_RESULT_STRATEGY_INPUT_COUNT =
0

LEGACY_ACCOUNTING_PATH_MATRIX_COMPLETE =
YES

PERMANENT_LEGACY_ACCOUNTING_FALLBACK_COUNT =
0

G33_FOCUSED_BASIS_TESTS =
PASS

ORIGINAL_G32_FAILED_TEST =
PASS

COST_BASIS_REGRESSION =
PASS

RUNTIME_FILL_PROJECTION_REGRESSION =
PASS

BASIS_METADATA_REGRESSION =
PASS

LINEAGE_REGRESSION =
PASS

ORIGINAL_G32_SUITE_RESULT =
552 passed

G33_EXPANDED_SUITE_RESULT =
552 passed

G32_FOCUSED_SUITE_AFTER_REPAIR =
PASS

PERMANENT_ACCOUNTING_CONTRACT_DOCUMENTED =
YES

G33_DIFF_SCOPE =
PASS

FRESH_RUN_EXECUTED =
NO

RESUME_EXECUTED =
NO

REPLAY_EXECUTED =
NO

HISTORICAL_RERUN_EXECUTED =
NO

LONG_HISTORICAL_EXECUTED =
NO

PY_COMPILE =
PASS

GIT_DIFF_CHECK =
PASS

NEXT_TASK_RECOMMENDATION =
PHASE31_G34_PRODUCTION_EQUIVALENT_INTEGRATED_FINAL_REACCEPTANCE
