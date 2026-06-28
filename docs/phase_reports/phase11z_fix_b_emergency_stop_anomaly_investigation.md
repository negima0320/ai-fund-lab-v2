# Phase11-Z-Fix-B Emergency Stop Anomaly Investigation

- status: PHASE11Z_FIX_B_EMERGENCY_STOP_ANOMALY_INVESTIGATION_COMPLETE
- created_at: 2026-06-28
- scope: Investigation only: Phase11-Z-Fix-B Emergency Stop 110 days / low return anomaly
- implementation_changed: false
- full_5y_backtest_rerun: false
- broker_api_connected: false
- websocket_connected: false
- demo_order_submitted: false
- production_order_submitted: false
- auto_sell_executed: false
- auto_recovery_executed: false
- ai_retraining_executed: false

## Conclusion

Fix-BのPASSは維持しない。暫定的に `PHASE11Z_FIX_B_RESULT_SUSPECT` とし、5年full rerunは保留する。

直接原因は、実市場由来ではない決定的mock injectionでEmergencyへ入り、その後SparseなRecovery / Manual Approval simulationまで `EMERGENCY_STOP` に滞在すること。`EMERGENCY_STOP` state-before 110日のうち、93日は新規Emergency reasonなしの状態滞在だった。

Market Crashだけが主因ではない。Emergency entryは duplicate active order、individual emergency candidate、manual emergency、broker divergence mockから発生した。Market Crashはperiodic booleanであり、実市場のindex returnやcandidate universe drawdownから算出されていないため、妥当性検証には使えない。

`win_rate=0.0` と `profit_factor=0.0` は実績ではなく、コード上のplaceholderである。closed tradesをFIFOで再計算すると、22 close中 12勝 / 10敗、realized profit 16000、realized loss -11700、computed win_rate 約0.545、computed profit_factor 約1.368だった。

## Emergency Stop Breakdown

- emergency_stop_days_total: 110
- first_emergency_stop_date: 2025-07-18
- last_emergency_stop_date: 2026-05-25

### Streaks

```json
[
  {
    "start": "2025-07-18",
    "end": "2025-07-24",
    "days": 5
  },
  {
    "start": "2025-07-30",
    "end": "2025-09-05",
    "days": 28
  },
  {
    "start": "2025-10-03",
    "end": "2025-10-20",
    "days": 12
  },
  {
    "start": "2026-01-29",
    "end": "2026-02-26",
    "days": 21
  },
  {
    "start": "2026-03-25",
    "end": "2026-05-25",
    "days": 44
  }
]
```

### Emergency Entry Dates

```json
[
  {
    "date": "2025-07-17",
    "from_state": "NORMAL",
    "to_state": "EMERGENCY_STOP",
    "primary_reason": "DUPLICATE_ACTIVE_BUY_ORDER",
    "reason_codes": [
      "DUPLICATE_ACTIVE_BUY_ORDER",
      "BROKER_DUPLICATE_ORDER_RISK",
      "DUPLICATE_ORDER_BLOCKED",
      "BROKER_DUPLICATE_ORDER_RISK"
    ]
  },
  {
    "date": "2025-07-29",
    "from_state": "NORMAL",
    "to_state": "EMERGENCY_STOP",
    "primary_reason": "EMERGENCY_CANDIDATE",
    "reason_codes": [
      "EMERGENCY_CANDIDATE",
      "EMERGENCY_CANDIDATE",
      "EMERGENCY_CANDIDATE",
      "EMERGENCY_CANDIDATE",
      "EMERGENCY_CANDIDATE"
    ]
  },
  {
    "date": "2025-10-02",
    "from_state": "NORMAL",
    "to_state": "EMERGENCY_STOP",
    "primary_reason": "MANUAL_EMERGENCY_STOP",
    "reason_codes": [
      "MANUAL_EMERGENCY_STOP",
      "MANUAL_EMERGENCY_STOP",
      "MANUAL_EMERGENCY_STOP"
    ]
  },
  {
    "date": "2026-01-28",
    "from_state": "NORMAL",
    "to_state": "EMERGENCY_STOP",
    "primary_reason": "DUPLICATE_ACTIVE_BUY_ORDER",
    "reason_codes": [
      "DUPLICATE_ACTIVE_BUY_ORDER",
      "BROKER_DUPLICATE_ORDER_RISK",
      "BROKER_DUPLICATE_ORDER_RISK",
      "BROKER_DUPLICATE_ORDER_RISK"
    ]
  },
  {
    "date": "2026-03-24",
    "from_state": "NORMAL",
    "to_state": "EMERGENCY_STOP",
    "primary_reason": "BROKER_DIVERGENCE_DETECTED",
    "reason_codes": [
      "BROKER_DIVERGENCE_DETECTED",
      "BROKER_DIVERGENCE_DETECTED",
      "BROKER_DIVERGENCE_DETECTED"
    ]
  }
]
```

### Days By Reason

```json
{
  "NO_NEW_TRIGGER_STATE_RESIDENCY": 93,
  "RECOVERY_CANDIDATE_REVIEW_REQUIRED": 17,
  "MAX_EXPOSURE_EXCEEDED": 5,
  "STOP_LOSS_CANDIDATE": 3,
  "BROKER_DIVERGENCE_DETECTED": 3,
  "MARKET_CRASH_EMERGENCY": 3,
  "MARKET_CRASH_BUY_STOP": 3,
  "EMERGENCY_CANDIDATE": 3,
  "INDIVIDUAL_DRAWDOWN_WARNING": 3,
  "CASH_BUFFER_VIOLATION": 2,
  "BROKER_SNAPSHOT_STALE": 2,
  "QUOTE_STALE": 2,
  "QUOTE_STALE_FOR_MONITOR": 1
}
```

### Days By Guard

```json
{
  "StateResidency": 93,
  "MarketRecoveryGuard": 17,
  "IndividualCrashGuard": 9,
  "MarketCrashGuard": 6,
  "MaxExposureGuard": 5,
  "BrokerDivergenceGuard": 3,
  "QuoteStaleGuard": 3,
  "CashBufferGuard": 2,
  "BrokerSnapshotFreshness": 2
}
```

## Market Crash Guard

`_market_summary()` は以下のperiodic mockである。

- market_crash: `index > 0 and index % 83 == 20`
- severe_crash: `index > 0 and index % 211 == 55`
- daily_loss_pct: `index % 127 == 80` のとき `-0.06`

index return、candidate universe drawdown、extreme down ratio、stop-limit candidate ratioは計算されていない。

```json
[
  {
    "date": "2025-06-30",
    "business_day_index": 20,
    "state_before": "NORMAL",
    "state_after": "BUY_STOP",
    "market_crash": true,
    "severe_crash": false,
    "daily_loss_pct": "0.00",
    "recovery_candidate": false,
    "market_crash_reason_codes": [
      "MARKET_CRASH_BUY_STOP",
      "MARKET_CRASH_BUY_STOP",
      "MARKET_CRASH_BUY_STOP"
    ],
    "index_return_values": "not_market_data_derived_mock_boolean",
    "candidate_universe_drawdown": "not_computed",
    "extreme_down_ratio": "not_computed",
    "stop_limit_candidate_ratio": "not_computed",
    "buy_stop_required": true,
    "emergency_candidate": false
  },
  {
    "date": "2025-08-18",
    "business_day_index": 55,
    "state_before": "EMERGENCY_STOP",
    "state_after": "EMERGENCY_STOP",
    "market_crash": false,
    "severe_crash": true,
    "daily_loss_pct": "0.00",
    "recovery_candidate": false,
    "market_crash_reason_codes": [
      "MARKET_CRASH_EMERGENCY",
      "MARKET_CRASH_EMERGENCY",
      "MARKET_CRASH_EMERGENCY"
    ],
    "index_return_values": "not_market_data_derived_mock_boolean",
    "candidate_universe_drawdown": "not_computed",
    "extreme_down_ratio": "not_computed",
    "stop_limit_candidate_ratio": "not_computed",
    "buy_stop_required": false,
    "emergency_candidate": true
  },
  {
    "date": "2025-10-23",
    "business_day_index": 103,
    "state_before": "NORMAL",
    "state_after": "BUY_STOP",
    "market_crash": true,
    "severe_crash": false,
    "daily_loss_pct": "0.00",
    "recovery_candidate": false,
    "market_crash_reason_codes": [
      "MARKET_CRASH_BUY_STOP",
      "MARKET_CRASH_BUY_STOP",
      "MARKET_CRASH_BUY_STOP"
    ],
    "index_return_values": "not_market_data_derived_mock_boolean",
    "candidate_universe_drawdown": "not_computed",
    "extreme_down_ratio": "not_computed",
    "stop_limit_candidate_ratio": "not_computed",
    "buy_stop_required": true,
    "emergency_candidate": false
  },
  {
    "date": "2026-02-17",
    "business_day_index": 186,
    "state_before": "EMERGENCY_STOP",
    "state_after": "EMERGENCY_STOP",
    "market_crash": true,
    "severe_crash": false,
    "daily_loss_pct": "0.00",
    "recovery_candidate": false,
    "market_crash_reason_codes": [
      "MARKET_CRASH_BUY_STOP",
      "MARKET_CRASH_BUY_STOP",
      "MARKET_CRASH_BUY_STOP"
    ],
    "index_return_values": "not_market_data_derived_mock_boolean",
    "candidate_universe_drawdown": "not_computed",
    "extreme_down_ratio": "not_computed",
    "stop_limit_candidate_ratio": "not_computed",
    "buy_stop_required": true,
    "emergency_candidate": false
  }
]
```

## Stale / Divergence / Duplicate / Manual Emergency Injection

```json
{
  "QuoteStaleGuard": {
    "trigger_count": 3,
    "trigger_dates": [
      {
        "date": "2025-07-07",
        "index": 25,
        "reason_codes": [
          "QUOTE_STALE_FOR_MONITOR",
          "QUOTE_STALE",
          "QUOTE_STALE"
        ]
      },
      {
        "date": "2025-11-25",
        "index": 126,
        "reason_codes": [
          "QUOTE_STALE_FOR_MONITOR",
          "QUOTE_STALE",
          "QUOTE_STALE"
        ]
      },
      {
        "date": "2026-04-15",
        "index": 227,
        "reason_codes": [
          "QUOTE_STALE_FOR_MONITOR",
          "QUOTE_STALE",
          "QUOTE_STALE"
        ]
      }
    ],
    "source_of_trigger": "integrated_backtest_audit deterministic mock injection",
    "is_fixture_injection": true,
    "is_market_data_derived": false,
    "is_random_or_periodic_injection": "periodic deterministic modulo injection",
    "threshold_or_formula": "index % 101 == 25",
    "should_be_emergency_or_review": "BLOCK/BUY_STOP is reasonable for stale quote; not emergency by itself"
  },
  "BrokerSnapshotFreshness": {
    "trigger_count": 2,
    "trigger_dates": [
      {
        "date": "2025-09-02",
        "index": 66,
        "reason_codes": [
          "BROKER_SNAPSHOT_STALE"
        ]
      },
      {
        "date": "2026-05-13",
        "index": 247,
        "reason_codes": [
          "BROKER_SNAPSHOT_STALE"
        ]
      }
    ],
    "source_of_trigger": "integrated_backtest_audit deterministic mock injection",
    "is_fixture_injection": true,
    "is_market_data_derived": false,
    "is_random_or_periodic_injection": "periodic deterministic modulo injection",
    "threshold_or_formula": "index % 181 == 66",
    "should_be_emergency_or_review": "REVIEW_REQUIRED for stale; emergency only when unavailable/missing critical"
  },
  "BrokerDivergenceGuard": {
    "trigger_count": 2,
    "trigger_dates": [
      {
        "date": "2025-08-01",
        "index": 44,
        "reason_codes": [
          "BROKER_DIVERGENCE_DETECTED",
          "BROKER_DIVERGENCE_DETECTED",
          "BROKER_DIVERGENCE_DETECTED"
        ]
      },
      {
        "date": "2026-03-24",
        "index": 211,
        "reason_codes": [
          "BROKER_DIVERGENCE_DETECTED",
          "BROKER_DIVERGENCE_DETECTED",
          "BROKER_DIVERGENCE_DETECTED"
        ]
      }
    ],
    "source_of_trigger": "integrated_backtest_audit deterministic mock injection",
    "is_fixture_injection": true,
    "is_market_data_derived": false,
    "is_random_or_periodic_injection": "periodic deterministic modulo injection",
    "threshold_or_formula": "index % 167 == 44",
    "should_be_emergency_or_review": "REVIEW_REQUIRED unless severe; current evaluator treats reason as emergency in EmergencyStopEvaluator"
  },
  "DuplicateOrderGuard": {
    "trigger_count": 2,
    "trigger_dates": [
      {
        "date": "2025-07-17",
        "index": 33,
        "reason_codes": [
          "DUPLICATE_ACTIVE_BUY_ORDER",
          "BROKER_DUPLICATE_ORDER_RISK",
          "DUPLICATE_ORDER_BLOCKED",
          "BROKER_DUPLICATE_ORDER_RISK"
        ]
      },
      {
        "date": "2026-01-28",
        "index": 172,
        "reason_codes": [
          "DUPLICATE_ACTIVE_BUY_ORDER",
          "BROKER_DUPLICATE_ORDER_RISK",
          "BROKER_DUPLICATE_ORDER_RISK",
          "BROKER_DUPLICATE_ORDER_RISK"
        ]
      }
    ],
    "source_of_trigger": "integrated_backtest_audit deterministic mock injection",
    "is_fixture_injection": true,
    "is_market_data_derived": false,
    "is_random_or_periodic_injection": "periodic deterministic modulo injection",
    "threshold_or_formula": "index % 139 == 33",
    "should_be_emergency_or_review": "duplicate active buy can be emergency, but mock duplicate injected periodically"
  },
  "ManualEmergencyStop": {
    "trigger_count": 1,
    "trigger_dates": [
      {
        "date": "2025-10-02",
        "index": 88,
        "reason_codes": [
          "MANUAL_EMERGENCY_STOP",
          "MANUAL_EMERGENCY_STOP",
          "MANUAL_EMERGENCY_STOP"
        ]
      }
    ],
    "source_of_trigger": "integrated_backtest_audit deterministic mock injection",
    "is_fixture_injection": true,
    "is_market_data_derived": false,
    "is_random_or_periodic_injection": "periodic deterministic modulo injection",
    "threshold_or_formula": "index % 251 == 88",
    "should_be_emergency_or_review": "emergency when manual flag active; current mock injects it once"
  },
  "DailyLossGuard": {
    "trigger_count": 2,
    "trigger_dates": [
      {
        "date": "2025-09-22",
        "index": 80,
        "reason_codes": [
          "DAILY_LOSS_BUY_STOP",
          "DAILY_LOSS_BUY_STOP",
          "DAILY_LOSS_BUY_STOP"
        ]
      },
      {
        "date": "2026-03-18",
        "index": 207,
        "reason_codes": [
          "DAILY_LOSS_BUY_STOP",
          "DAILY_LOSS_BUY_STOP",
          "DAILY_LOSS_BUY_STOP",
          "DAILY_LOSS_BUY_STOP"
        ]
      }
    ],
    "source_of_trigger": "integrated_backtest_audit deterministic mock injection",
    "is_fixture_injection": true,
    "is_market_data_derived": false,
    "is_random_or_periodic_injection": "periodic deterministic modulo injection",
    "threshold_or_formula": "index % 127 == 80, daily_loss_pct=-0.06",
    "should_be_emergency_or_review": "BUY_STOP at -5%; emergency at -10%; injected -6% should be BUY_STOP not emergency"
  }
}
```

## Recovery / Manual Approval

```json
{
  "recovery_candidate_dates": [
    "2025-07-01",
    "2025-07-24",
    "2025-09-05",
    "2025-10-20",
    "2026-02-26",
    "2026-04-10",
    "2026-05-25"
  ],
  "manual_approved_dates": [
    "2025-07-24",
    "2025-07-25",
    "2025-09-05",
    "2025-09-08",
    "2025-10-20",
    "2025-10-21",
    "2026-02-26",
    "2026-02-27",
    "2026-05-25",
    "2026-05-26"
  ],
  "normal_return_dates": [
    "2025-07-25",
    "2025-09-08",
    "2025-10-21",
    "2026-02-27",
    "2026-05-26"
  ],
  "recovery_candidate_to_normal_anomalies": [
    {
      "date": "2025-07-02",
      "from_prev_after": "RECOVERY_CANDIDATE",
      "current_before": "RECOVERY_CANDIDATE",
      "current_after": "NORMAL",
      "reason_codes": []
    }
  ],
  "assessment": "Manual approval simulation can release EMERGENCY_STOP, but only on sparse modulo dates. One BUY_STOP->RECOVERY_CANDIDATE->NORMAL path bypasses MANUAL_APPROVED in daily state output, so recovery validation needs tightening."
}
```

Manual approval simulationはEmergency解除自体は行うが、`index % 11 == 0` に依存するため長期滞在が起きる。また、BUY_STOP後に `RECOVERY_CANDIDATE -> NORMAL` が1件あり、日次出力上はMANUAL_APPROVEDを経由していない。

## Win Rate / Profit Factor

```json
{
  "reported_win_rate": 0.0,
  "reported_profit_factor": 0.0,
  "closed_trades_count": 22,
  "winning_closed_trades": 12,
  "losing_closed_trades": 10,
  "breakeven_closed_trades": 0,
  "total_realized_profit": "16000.000000",
  "total_realized_loss": "-11700.000000",
  "computed_win_rate": 0.5454545454545454,
  "computed_profit_factor": 1.3675213675213675,
  "definition_issue": "integrated_backtest_audit.py currently returns win_rate=0.0 and profit_factor=0.0 constants instead of computing from closed sell fills."
}
```

`integrated_backtest_audit.py` は `win_rate` と `profit_factor` を固定 `0.0` で返しているため、Fix-Bレポートの低パフォーマンス表示は一部メトリクス未実装を含む。

## Safety ON / OFF Comparison

```json
{
  "safety_on": {
    "orders_generated": 526,
    "buy_fill_count": 27,
    "sell_fill_count": 22,
    "trade_count": 49,
    "final_equity": 1005400.0,
    "total_return": 0.0054,
    "max_drawdown": -0.088358,
    "emergency_stop_days": 110,
    "buy_stop_days": 8,
    "blocked_by_safety": 43
  },
  "safety_off_lightweight": {
    "orders_generated": 531,
    "buy_fill_count": 31,
    "sell_fill_count": 26,
    "trade_count": 57,
    "final_equity": 947410.0,
    "total_return": -0.05259,
    "max_drawdown": -0.114606,
    "emergency_stop_days": 0,
    "buy_stop_days": 0,
    "blocked_by_safety": 0
  }
}
```

Safety OFFは軽量な同期間再計算であり、5年fullではない。Safety ONは取引数を減らしたが、Safety OFFよりfinal equityとmax drawdownは良い。したがって、低リターンの主因をSafety過剰停止だけとは判断できない。

## PASS Condition Review

Fix-BのPASS条件は、注文・約定・closeの発生確認には有効だったが、品質ゲートとして不足している。

```json
{
  "current_status": "PASS",
  "should_be_downgraded_to_suspect": true,
  "missing_pass_conditions": [
    "maximum acceptable EMERGENCY_STOP residency",
    "market crash evidence must be market-data-derived or clearly labelled stress injection",
    "win_rate/profit_factor must be computed or omitted",
    "recovery must require RECOVERY_CANDIDATE->MANUAL_APPROVED->NORMAL without bypass",
    "mock anomaly injection density must be bounded/declared"
  ]
}
```

## Fix Candidates

- Add stress_fixture_mode or anomaly_injection_profile so smoke can separate normal-market audit from forced anomaly stress tests.
- Reduce or parameterize periodic mock emergency injections for 1Y smoke.
- Compute MarketCrashGuard inputs from market summary values instead of periodic booleans, or label them explicitly as synthetic stress events.
- Change EmergencyStopEvaluator so non-severe BROKER_DIVERGENCE_DETECTED is review unless explicitly severe.
- Improve recovery/manual approval simulation cadence and enforce RECOVERY_CANDIDATE -> MANUAL_APPROVED -> NORMAL in daily state outputs.
- Compute realized PnL, win_rate, and profit_factor from closed sell fills.
- Strengthen PASS conditions for emergency residency, metric validity, and realistic/non-stress smoke profile.


## Code Evidence

```json
{
  "performance_placeholder": "src/ai_fund_lab_v2/safety_phase11/integrated_backtest_audit.py:641",
  "profit_factor_placeholder": "src/ai_fund_lab_v2/safety_phase11/integrated_backtest_audit.py:642",
  "market_injection": "src/ai_fund_lab_v2/safety_phase11/integrated_backtest_audit.py:833",
  "mock_divergence_snapshot_orders_manual_emergency": "src/ai_fund_lab_v2/safety_phase11/integrated_backtest_audit.py:852",
  "state_sticky_emergency": "src/ai_fund_lab_v2/safety_phase11/integrated_backtest_audit.py:1049",
  "pass_conditions_missing_quality_gates": "src/ai_fund_lab_v2/safety_phase11/integrated_backtest_audit.py:701"
}
```

## Data Use

This investigation result is not AI training data. Backtest outcome, Paper Ledger, Broker Snapshot, PnL, portfolio state, cash, selected / bought / affordable data, order result, execution result, Safety result, Audit result, and PM multiplier imitation remain forbidden for AI learning.

## Result

```text
PHASE11Z_FIX_B_RESULT_SUSPECT
PHASE11Z_FIX_C_FULL_5Y_ON_HOLD
PHASE11_COMPLETE_ON_HOLD
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
