# Phase10-M Production Runtime Architecture Design

- status: DESIGN_COMPLETE
- created_at: 2026-06-27
- scope: architecture design only
- live_api_connected: false
- broker_order_api_called: false
- paper_ledger_updated: false

## 1. Summary

Phase10-M では、Tachibana read-only Broker Snapshot 完了後の production runtime architecture を設計した。

作成した設計書:

```text
docs/02_architecture/production_runtime_architecture.md
```

今回は設計のみであり、実 API 接続、demo 発注、production 発注、訂正、取消、第二暗証番号、unlock 相当処理、Paper Ledger 更新、Paper Test 2 Ledger 初期化、AI 学習処理変更、backtest は行っていない。

## 2. Baseline

前提:

```text
Phase10 Complete
p_no monotonic sequence bug fixed
demo login/session/logout PASS
demo account/balance PASS
demo positions PASS
demo orders PASS
demo executions/history safe
demo broker snapshot PASS
```

Demo口座の直近状態:

```text
buying_power=20000000
effective_positions=0
```

Paper Test 2 / production capital 前提:

```text
production_initial_capital_assumption=1000000
paper_test2_evaluation_cash=1000000
production_uses_broker_actual_cash=true
demo_rehearsal_uses_evaluation_cash_for_sizing=true
```

## 3. Architecture Decisions

Production Runtime は以下の manager に分割する。

- Broker Manager
- Order Manager
- Position Manager
- Fill Manager
- Safety Manager
- Portfolio / Capital Manager
- Report Manager
- Scheduler
- Runtime State Machine

責務分離:

- Broker Manager は broker state の入口。
- Order Manager は注文管理のみで、銘柄選定や投資判断は持たない。
- Safety Manager は order submission 前の必須 gate。
- Portfolio / Capital Manager は evaluation cash と broker actual cash を分離する。
- Report Manager は redacted report のみを生成する。
- Scheduler は business day guard と state transition を管理する。

## 4. State Machine

設計した日次状態:

```text
PREOPEN
ORDER_PREPARED
SAFETY_CHECKED
ORDER_SUBMITTED
WAITING_FILL
PARTIALLY_FILLED
FILLED
MONITORING
CLOSE_VALUATION
NIGHTLY_INFERENCE
REPORT_READY
EMERGENCY_STOP
```

重要ルール:

- unknown state は fail closed。
- stale snapshot では order submission へ進まない。
- approval gate 未通過では order submission へ進まない。
- EMERGENCY_STOP は任意状態から遷移可能。
- Production order submission は Phase10-T の readiness audit まで禁止。

## 5. Daily Runtime Flow

朝:

```text
previous business day AI decision
broker cash / buying_power check
existing positions check
existing orders check
duplicate prevention
safety check
order plan finalization
approval gate
order submission only when explicitly enabled
order accepted confirmation
```

日中:

```text
order list
order detail
executions
positions
broker snapshot
partial fill classification
rejected / expired / canceled classification
no automatic retry by default
```

1時間ごとの保有監視:

```text
broker positions
realtime quote
entry price
-7 percent warning candidate
-10 percent stop-loss candidate
-15 percent emergency candidate
initial action is notification / candidate only
automatic sell is deferred
```

夜:

```text
broker snapshot
ledger reconciliation
market data refresh
valuation
next-day inference
order candidate generation
report generation
notification
```

## 6. Broker Source Of Truth

Production:

```text
broker position/cash/order/execution is truth
```

Paper:

```text
Paper Ledger is evaluation and simulation only
```

Demo:

```text
Demo is production flow rehearsal
Demo actual cash may differ from evaluation cash
```

Paper Test 2 integration:

- Paper Test 2 uses 1,000,000 JPY evaluation cash.
- Broker Snapshot may initialize or reconcile state, but does not mutate Paper Ledger automatically.
- Paper positions and broker positions may diverge by design and must be classified rather than overwritten.

## 7. Cash / Capital Design

Demo:

```text
broker_actual_cash_or_buying_power=20000000
evaluation_cash=1000000
order_sizing_basis=evaluation_cash
```

Production:

```text
order_sizing_basis=broker_actual_cash_and_buying_power
configured_capital_target=1000000
broker_cash_is_upper_bound=true
```

Required controls:

- buying power upper bound
- per-position cap
- max positions
- cash buffer
- lot size
- round down to avoid cash overrun

## 8. Safety Design

Required guards:

- fail closed
- no-live-order default
- manual approval
- emergency stop
- stale snapshot guard
- broker divergence guard
- duplicate order guard
- order rejection guard
- quote stale guard
- p_no/session error guard
- daily loss guard
- cash buffer guard
- max exposure guard
- redaction guard
- business day guard

Initial sell automation policy:

```text
warning and candidate generation only
automatic sell deferred to a later audited phase
```

## 9. Scheduler Design

Recommended schedule:

```text
08:30 preopen broker snapshot
08:45 order preparation
08:55 safety approval gate
09:00 order submission, disabled until order phase
09:05 fill check
hourly position monitoring
10:30 broker reconciliation
12:35 broker reconciliation
14:45 broker reconciliation
15:30 close valuation
16:30 report / next-day candidate
weekend and holiday skip
```

## 10. Demo Rehearsal

Demo rehearsal uses the same state machine as production.

Differences:

- environment is demo.
- production order submission remains prohibited.
- evaluation cash is 1,000,000 JPY.
- demo actual broker cash is 20,000,000 JPY.
- demo order quantity, if enabled in a later phase, is sized from evaluation cash.

Demo order execution is not enabled in Phase10-M.

## 11. Phase Split

Next phases:

```text
Phase10-N runtime state machine skeleton
Phase10-O demo order design / no production
Phase10-P demo buy/sell smoke
Phase10-Q fill monitor
Phase10-R safety monitor
Phase10-S scheduler integration
Phase10-T production readiness audit
```

Phase10-N should implement:

- state enum
- transition validator
- immutable run manifests
- no-live-order default
- safety gate placeholders
- tests

Phase10-N should not implement broker order submission.

## 12. Verification

Performed:

```text
JSON validation: PASS
secret canary: PASS
forbidden CLMID audit: PASS
no runtime mutation confirmation: PASS
```

No runtime mutation:

```text
live_api_connected=false
demo_order_submitted=false
production_order_submitted=false
paper_ledger_updated=false
paper_test2_ledger_initialized=false
ai_learning_updated=false
backtest_run=false
```

## 13. Result

Phase10-M completion judgement:

```text
DESIGN_COMPLETE
```

次に進める状態:

```text
Phase10-N runtime state machine skeleton
```

