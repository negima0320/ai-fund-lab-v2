# Phase11-Z-Fix-B2 Low Return Root Cause Investigation

- status: PHASE11Z_FIX_B2_LOW_RETURN_ROOT_CAUSE_INVESTIGATION_COMPLETE
- created_at: 2026-06-28
- scope: Investigation only: Fix-B2 normal_market 1Y low return root cause
- implementation_changed: false
- full_5y_backtest_rerun: false
- ai_retraining_executed: false
- broker_api_connected: false
- websocket_connected: false
- demo_order_submitted: false
- production_order_submitted: false
- auto_sell_executed: false
- auto_recovery_executed: false

## Conclusion

Fix-B2 normal_market 1年smokeは **Safety監査には使えるが、収益評価には不十分** と判定する。

低リターンの直接原因はSafetyではない。normal_marketではSafetyが全件ALLOWで、`orders_blocked_by_safety=0`、`orders_review_required=0`、`orders_emergency_stopped=0`、`EMERGENCY_STOP days=0` だった。Safety OFF軽量比較もONと完全一致した。

主因は、Phase11-Z runnerが既存の勝てる本線を十分に再利用していないこと。Candidate / Opportunity / Capital Allocation / OrderPlan / Virtual Fill / Paper Ledger / Exitの多くが監査専用stubであり、Phase7-G CAP5/CAP4やPhase9 daily operationの本線とは別物である。

## Revenue Evaluation Suitability

```text
B. Safety監査には使えるが、収益評価には不十分
```

## Fix-B2 Normal Market Summary

```json
{
  "period": [
    "2025-06-01",
    "2026-05-31"
  ],
  "business_days": 260,
  "performance": {
    "annualized_return": 0.013658,
    "average_holding_days": 63.0,
    "average_realized_pnl": 418.518519,
    "breakeven_closed_trades": 0,
    "buy_fill_count": 32,
    "closed_trades_count": 27,
    "exposure_ratio": 0.5132,
    "final_equity": 1014500.0,
    "initial_cash": 1000000.0,
    "losing_closed_trades": 11,
    "max_drawdown": -0.017423,
    "performance_metrics_placeholder": false,
    "profit_factor": 1.79021,
    "realized_loss": -14300.0,
    "realized_profit": 25600.0,
    "round_trip_count": 27,
    "sell_fill_count": 27,
    "total_return": 0.0145,
    "trade_count": 59,
    "trade_count_definition": "buy_fill_count + sell_fill_count",
    "win_rate": 0.592593,
    "winning_closed_trades": 16
  },
  "flow_counts": {
    "ai_signal_days": 260,
    "buy_fill_count": 32,
    "buy_orders_submitted": 32,
    "candidate_count_total": 1560,
    "candidate_generated_days": 260,
    "candidate_universe_size": 60,
    "final_position_count": 5,
    "fixed_4_code_stub_used": false,
    "ledger_entry_count": 59,
    "normal_market_profile": true,
    "order_plan_generated_days": 260,
    "orders_allowed_by_safety": 538,
    "orders_before_safety": 538,
    "orders_blocked_by_safety": 0,
    "orders_emergency_stopped": 0,
    "orders_generated": 538,
    "orders_review_required": 0,
    "periodic_mock_emergency_injection_enabled": false,
    "position_close_count": 27,
    "position_open_count": 32,
    "recovery_candidate_count_definition": "event/check count, not unique days; see state_residency_days for day count",
    "round_trip_count": 27,
    "sell_fill_count": 27,
    "sell_orders_submitted": 27,
    "stress_injection_profile": false,
    "trade_count_definition": "trade_count = buy_fill_count + sell_fill_count; round_trip_count = closed positions count",
    "virtual_fills": 59,
    "virtual_orders_submitted": 59
  },
  "safety": {
    "ALLOW_count": 798,
    "BLOCK_count": 0,
    "BUY_STOP_days": 0,
    "EMERGENCY_STOP_count": 0,
    "MANUAL_APPROVED_count": 0,
    "RECOVERY_CANDIDATE_count": 0,
    "REVIEW_REQUIRED_count": 0,
    "broker_divergence_guard_count": 0,
    "cash_buffer_guard_count": 0,
    "daily_loss_guard_count": 0,
    "duplicate_order_guard_count": 0,
    "emergency_candidate_count": 0,
    "individual_warning_count": 0,
    "market_crash_guard_count": 0,
    "max_exposure_guard_count": 0,
    "quote_stale_guard_count": 0,
    "safety_check_count": 260,
    "stop_loss_candidate_count": 0
  },
  "state_residency_days": {
    "BUY_STOP": 0,
    "EMERGENCY_STOP": 0,
    "MANUAL_APPROVED": 0,
    "NORMAL": 260,
    "RECOVERY_CANDIDATE": 0,
    "WARNING": 0
  },
  "avg_position_count": 5.15,
  "trade_reason_counts": {
    "NEW_BUY_AUDIT_CANDIDATE": 32,
    "MAX_HOLDING_DAYS_EXIT": 27
  }
}
```

## Component Reuse Table

| Component | Existing mainline reused? | Phase11-Z current behavior |
| --- | --- | --- |
| Candidate AI / Daily Inference | no | Uses deterministic _candidate_codes_for_day over 60 fixed audit universe; no daily_inference_runner, no feature parquet, no model prediction. |
| Opportunity scoring | no | Uses _candidate_score(seed/index modulo) only; no candidate/opportunity feature score or public confidence mapping. |
| Capital Allocation | no | Uses simple max_positions=8, buy_slots<=2, cash*0.18/150k cap; no CAP5/CAP4 engine, no PM multiplier, no replacement edge. |
| Order Plan Generator | no | Uses internal _planned_orders; does not call generate_order_plan or dependency validator. |
| Safety Pre-order Check | partial | Uses SafetyManager guards, but not integrated with production runtime/order manager plan schema. |
| Virtual Fill Processor | no | Uses _virtual_buy_from_plan/_virtual_sell_from_plan same-day synthetic price; no pending order, no next business day open fill, no no-fill policy. |
| Paper Ledger | no | Uses local positions/cash/trades lists; does not use PaperTradingLedger, PendingOrderState, PerformanceSnapshot. |
| Exit / Sell Logic | no | Only MAX_HOLDING_DAYS_EXIT occurred in normal smoke; no Position AI, no exit guard, no sell-first dependency with real ledger. |
| Replacement Logic | partial/stub | Has simplified replacement sell when max positions reached, but normal smoke produced only MAX_HOLDING_DAYS_EXIT and NEW_BUY reasons. |
| Performance Metrics | partial | Fix-B2 computes closed-trade metrics, but not Phase7 strict accounting metrics, T+2, costs/slippage, capital utilization/replacement metrics. |


## Phase7 / Phase9 Comparison

Phase7-G primary CAP5は同じ初期資金100万円から、2021-09-08〜2026-06-12で大幅な複利成績を示している。一方、Fix-B2 normal_marketはSafety統合監査用の1年stubであり、候補生成・配分・約定・台帳が違う。

```json
{
  "phase7_reference_results": [
    {
      "policy_id": "CAP5_0BPS",
      "role": "primary",
      "period": "2021-09-08..2026-06-12",
      "initial_cash": 1000000.0,
      "final_equity": 614731820.0,
      "total_return": 613.73182,
      "annualized_return": 2.867856,
      "max_drawdown": -0.336457,
      "profit_factor": 2.075184,
      "win_rate": 0.607018,
      "trade_count": 570,
      "average_holding_days": 18.54386,
      "replacement_rate": 0.484211,
      "capital_utilization": 0.821288
    },
    {
      "policy_id": "CAP5_10BPS",
      "role": "primary",
      "period": "2021-09-08..2026-06-12",
      "initial_cash": 1000000.0,
      "final_equity": 289949882.53916,
      "total_return": 288.949883,
      "annualized_return": 2.301551,
      "max_drawdown": -0.322224,
      "profit_factor": 2.409936,
      "win_rate": 0.606299,
      "trade_count": 508,
      "average_holding_days": 18.273622,
      "replacement_rate": 0.547244,
      "capital_utilization": 0.821173
    },
    {
      "policy_id": "CAP5_30BPS",
      "role": "primary",
      "period": "2021-09-08..2026-06-12",
      "initial_cash": 1000000.0,
      "final_equity": 226981639.35525,
      "total_return": 225.981639,
      "annualized_return": 2.13558,
      "max_drawdown": -0.344186,
      "profit_factor": 2.24806,
      "win_rate": 0.587137,
      "trade_count": 482,
      "average_holding_days": 18.315353,
      "replacement_rate": 0.560166,
      "capital_utilization": 0.82698
    },
    {
      "policy_id": "CAP4_0BPS",
      "role": "conservative",
      "period": "2021-09-08..2026-06-12",
      "initial_cash": 1000000.0,
      "final_equity": 442305560.0,
      "total_return": 441.30556,
      "annualized_return": 2.608722,
      "max_drawdown": -0.28237,
      "profit_factor": 1.999434,
      "win_rate": 0.633094,
      "trade_count": 556,
      "average_holding_days": 18.863309,
      "replacement_rate": 0.399281,
      "capital_utilization": 0.831432
    },
    {
      "policy_id": "A_FIXED_20BD_0BPS",
      "role": "reference",
      "period": "2021-09-08..2026-06-12",
      "initial_cash": 1000000.0,
      "final_equity": 199474980.0,
      "total_return": 198.47498,
      "annualized_return": 2.051401,
      "max_drawdown": -0.353677,
      "profit_factor": 1.822186,
      "win_rate": 0.597809,
      "trade_count": 639,
      "average_holding_days": 20.0,
      "replacement_rate": 0.0,
      "capital_utilization": 0.84669
    },
    {
      "policy_id": "C3_MIN15_T2_0BPS",
      "role": "reference_high_turnover",
      "period": "2021-09-08..2026-06-12",
      "initial_cash": 1000000.0,
      "final_equity": 873471440.0,
      "total_return": 872.47144,
      "annualized_return": 3.164948,
      "max_drawdown": -0.362357,
      "profit_factor": 2.937808,
      "win_rate": 0.612782,
      "trade_count": 532,
      "average_holding_days": 16.958647,
      "replacement_rate": 0.81391,
      "capital_utilization": 0.814687
    }
  ],
  "phase9_daily_operation_design": "Phase9 validates daily paper trading operation flow, not long-term return; it uses Candidate/Opportunity/Position/Capital artifacts, OrderPlan, Human Review, PendingOrder, next-day Virtual Fill, Ledger valuation, reports.",
  "phase9_first_e2e_counts": {
    "candidate_count": 50,
    "opportunity_count": 20,
    "allocation_count": 5,
    "order_plan_count": 5
  },
  "fix_b2_normal_market": {
    "candidate_universe_size": 60,
    "candidate_count_total": 1560,
    "trade_count": 59,
    "final_equity": 1014500.0,
    "total_return": 0.0145,
    "exposure_ratio": 0.5132,
    "average_holding_days": 63.0
  }
}
```

## Entry / Candidate Difference

- Fix-B2: 60 fixed audit universe; daily top 6 from deterministic seed/index score; no model prediction, feature parquet, hard gate, liquidity/listing filter beyond static universe, ETF/ETN handling, lookback, or date-aligned prediction.
- Mainline: Phase9 reads candidate/opportunity feature frames, applies universe_eligible, liquidity/rank tie-breakers, top_candidates=50 and top_opportunities=20; Phase7-G uses ranked_daily artifact with 56,995 rows over 2021-2026.

## Exit / Sell Difference

- Fix-B2: normal_market exits were 27 MAX_HOLDING_DAYS_EXIT only; no realized Position AI/Exit Guard, no replacement edge confirmation, no partial close, no sell-first buy-after-fill dependency in actual fill flow.
- Mainline: Phase7 includes minimum holding days, replacement cap, replacement edge/confirmation, emergency/defensive reviews; Phase9 OrderPlan preserves sell-first and buy-after-fill dependency into pending orders and virtual fills.

## Allocation / Sizing Difference

- Fix-B2: max_positions=8, buy_slots<=2/day, notional=min(150k,cash*0.18), local cash buffer 50k, simple priority score, no CAP5 policy.
- Mainline: CAP5/CAP4 use target position value, 5% cash buffer, 20% max position weight, primary top ranks, replacement policy, 100-share lots, conservative T+2 cash unavailable accounting.

## Fill / Ledger Difference

- Fix-B2: same-day synthetic _base_price, local cash/positions/trades, no pending orders, no next-day open, no slippage/cost, no PaperTradingLedger valuation history, no no-fill/reject/expire state.
- Mainline: Phase9 virtual fill processes approved pending orders on virtual_execution_date at next business day open, SELL before dependent BUY, no-fill policy, cash/positions/performance snapshot, ledger diff and execution records.

## Performance Metrics Difference

- Fix-B2: closed-trade win_rate/profit_factor now computed, but strict accounting metrics like capital_utilization, turnover, replacement_rate, settlement cash, costs/slippage are absent.
- Phase7: strict backtest includes exact shares/cash, T+2, cost/slippage, turnover, capital utilization, replacement count/rate, skip reasons, daily portfolio ledger.

## Safety ON / OFF Comparison

```json
{
  "safety_on": {
    "orders_generated": 538,
    "orders_allowed_by_safety": 538,
    "buy_fill_count": 32,
    "sell_fill_count": 27,
    "trade_count": 59,
    "final_equity": 1014500.0,
    "total_return": 0.0145,
    "max_drawdown": -0.017423,
    "win_rate": 0.592593,
    "profit_factor": 1.79021,
    "blocked_count": 0,
    "review_required_count": 0,
    "emergency_stop_days": 0,
    "buy_stop_days": 0
  },
  "safety_off_lightweight": {
    "orders_generated": 538,
    "orders_allowed_by_safety": 538,
    "buy_fill_count": 32,
    "sell_fill_count": 27,
    "trade_count": 59,
    "final_equity": 1014500.0,
    "total_return": 0.0145,
    "max_drawdown": -0.017423,
    "win_rate": 0.592593,
    "profit_factor": 1.79021,
    "blocked_count": 0,
    "review_required_count": 0,
    "emergency_stop_days": 0,
    "buy_stop_days": 0,
    "note": "Identical because normal_market Safety produced zero block/review/emergency events."
  }
}
```

## Root Cause Ranking

- Entry/candidate alpha is absent: deterministic audit score replaces existing Candidate/Opportunity AI and Phase7 ranked_daily edge.
- Allocation is simplified: no CAP5/CAP4 target allocation, replacement edge, capital utilization optimization, or T+2 accounting.
- Exit is simplistic: normal smoke exits only max holding days, with average holding 63 calendar days versus Phase7 CAP5 ~18.5 trading days.
- Fill/ledger is simplified: same-day synthetic price and local ledger omit next-day open, pending order lifecycle, no-fill policy, strict ledger valuation, costs/slippage.
- Normal profile has no market/position stress and no real price path beyond synthetic _base_price, so returns are mechanically limited.

## Recommended Fix Candidates

- Before 5Y full, create an integrated audit adapter that consumes existing Phase9 daily inference/order plan artifacts or a fixture equivalent of them.
- Reuse Phase7/Phase9 Candidate/Opportunity ranking inputs instead of deterministic _candidate_score.
- Reuse CAP5/CAP4 allocation logic or load AllocationDecisionSet into order_plan_generator.
- Route orders through PaperTradingLedger/PendingOrderState/process_virtual_fills in an isolated temp/runtime audit ledger.
- Preserve Safety as pre-order layer, but keep return evaluation tied to mainline trading logic.
- Keep Fix-B2 standalone runner as Safety subsystem smoke, not revenue benchmark.


## Phase11-Z-Fix-C Recommendation

```json
{
  "run_full_5y_now": false,
  "reason": "A 5Y run of the current audit-only trading stub would validate Safety plumbing but would not answer whether production-like Paper Trading remains performant.",
  "next_step": "Phase11-Z-Fix-D or Fix-C-prep: align integrated audit runner with mainline Paper Trading / CAP5 order flow, then rerun 1Y smoke before 5Y full."
}
```

## Data Use

This investigation result is not AI training data. Backtest outcome, Paper Ledger, Broker Snapshot, PnL, portfolio state, cash, selected / bought / affordable data, order result, execution result, Safety result, Audit result, and PM multiplier imitation remain forbidden for AI learning.

## Result

```text
PHASE11Z_FIX_B2_LOW_RETURN_INVESTIGATION_REQUIRED
PHASE11Z_FIX_C_FULL_5Y_ON_HOLD
PHASE11_COMPLETE_ON_HOLD
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
