# Phase29-L21T-Q1B — Production MARKET BUY Reservation Authority Completion

## Judgment

`PHASE29_L21T_Q1B_MARKET_BUY_STOP_HIGH_RESERVATION_AUTHORITY_REPAIRED_SCOPED_REPLAY_PASS`

`RESUME_SAFE_NOW = YES_SCOPED_FROM_2023_06_08_STRATEGY_SHADOW_GENERATION`

Scope: no fresh-run, no long Historical resume. Only the Q3B/Q1B scoped recovery and 2023-06-08 replay boundary were executed.

## Production Authority

Tachibana Stockhouse states that cash buy orders require deposits at least equal to estimated purchase amount. It defines LIMIT estimated amount as limit price times shares plus fees/tax, and MARKET estimated amount as stop-high price-limit price times shares plus fees/tax. It also states MARKET and close-market order amount limits are calculated using the price-limit upper price.

JPX defines daily price limits from the previous close or final quote as the base price, with the regular domestic-stock price-limit table. For the 2023-06-08 case, the implemented authority uses previous close before the target session and JPX regular bands.

Fee/tax modeling remains outside the current Runtime v2 ledger semantics; this repair completes the price/notional authority and records broker cash semantics explicitly.

Sources:

- Tachibana Stockhouse order rules: https://t-stockhouse.jp/product/stock/rule.php
- JPX regular domestic stock price-limit table: https://www.jpx.co.jp/equities/trading/domestic/06.html

## Code Changes

- Added [order_reservation.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/runtime_v2/order_reservation.py) as the common Production/Demo/Historical order-condition-derived reservation authority.
- Wired MARKET/LIMIT reservation into strategy and morning pending producers:
  - [strategy_authority.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py)
  - [morning_pipeline.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py)
- Added top-level `reservation_price_type` propagation through pending model/reader:
  - [models.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/runtime_v2/pending/models.py)
  - [reader.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/runtime_v2/pending/reader.py)
- Extended Q3B scoped recovery in [runtime_test.py](/Users/negishi/work/ai-fund-lab-v2/scripts/runtime_test.py) to accept submit-only precommit HALT state as a valid recovery classification.

## Runtime Evidence

Run: `runtime-test-historical-smoke-20260812T083943290963Z`

Recovery:

```text
recover-failed-execution
classification = SUBMIT_ONLY_PRECOMMIT_HALT
status = PASS
rewind = 2023-06-08:execution -> 2023-06-08:morning
superseded submit rows = 4
execution/cash/position failed rows = 0
```

Scoped replay:

```text
jobs = morning,sell_planning,submit,execution
status = PASS
next_job = 2023-06-08:strategy_shadow_generation
current_safety_state = BUY_REVIEW_REQUIRED
```

Reservation evidence:

```text
30410 BUY qty 100  prev_close 1269  stop_high 1569  reserved_notional 156900
59550 BUY qty 1100 prev_close 100   stop_high 150   reserved_notional 165000
67310 BUY qty 100  prev_close 3000  stop_high 3700  reserved_notional 370000

aggregate BUY reservation = 691900
starting cash = 437870
BUY lane = REVIEW_REQUIRED
```

The reservation authority records:

```text
reservation_price_type = market_buy_stop_high_cash_reservation
source_authority = production_market_buy_price_limit_authority
source_field = previous_close
future_execution_price_used = false
target_day_ohlc_used = false
arbitrary_percentage_buffer_used = false
runtime_path = Production/Demo/Historical common runtime_v2
```

Submit/execution result:

```text
submitted orders on 2023-06-08 = 1
submitted/executed = 24350 SELL qty 200 at 269
BUY submit rows = 0
final cash = 491670
negative cash = NO
```

## Regression

```text
python3 -m pytest tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase29_l21t_q1b_market_buy_reservation_uses_previous_close_stop_high tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase29_l21t_q1b_limit_buy_reservation_uses_limit_price tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase29_l21t_q1b_market_buy_stop_high_aggregate_blocks_batch_before_submit -q
3 passed

python3 -m pytest tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py -q
12 passed

python3 -m pytest tests/runtime_v2/test_phase17_k_runtime_test_runner.py::test_phase29_l21t_q3b_failed_execution_recovery_dry_run_detects_scope tests/runtime_v2/test_phase17_k_runtime_test_runner.py::test_phase29_l21t_q3b_failed_execution_recovery_rewinds_and_preserves_prior_ledger tests/runtime_v2/test_phase17_k_runtime_test_runner.py::test_phase29_l21t_q1b_recovery_rewinds_submit_only_precommit_halt tests/runtime_v2/test_phase17_k_runtime_test_runner.py::test_phase29_l21t_q3b_failed_execution_recovery_refuses_coherent_state -q
4 passed

python3 -m pytest tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py -q
58 passed

python3 -m pytest tests/runtime_v2/test_phase26_step4_position_sizing_authority.py::test_phase29_l21t_h_position_sizing_consumes_authorized_one_lot_buy_add_and_reentry tests/strategy/test_phase22_j_position_sizing.py::test_phase29_l21t_c_ps_materializes_buy_add_one_lot_increment_when_continuous_delta_floors_to_zero tests/strategy/test_phase22_j_position_sizing.py::test_phase29_l21t_c_ps_preserves_reentry_semantics_for_one_lot_quantity_authority tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21s_buy_add_one_lot_fallback_preserves_add_semantics tests/strategy/test_phase22_e_portfolio_construction.py::test_phase29_l21s_reentry_pass_keeps_semantic_when_one_lot_fallback_applies tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py::test_phase29_l21t_m_buy_item_scoped_review_composes_valid_reduce_sell tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py::test_phase29_l21t_m_buy_item_scoped_review_composes_valid_exit_sell_and_submit_filters_buy -q
8 passed

PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-q1b-pycache python3 -m py_compile ...
PASS
```

## User Command For Focused Continuation

The scoped replay has already advanced the run to `2023-06-08:strategy_shadow_generation`. To continue from that boundary without re-running the repaired day:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resume \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id runtime-test-historical-smoke-20260812T083943290963Z \
  --confirm --yes-i-understand-this-mutates-trading-state \
  --json
```
