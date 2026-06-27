# Production Runtime Architecture

作成日: 2026-06-27
改訂日: 2026-06-28

## 1. Purpose

本書は Tachibana read-only Broker Snapshot 完了後の、実運用を見据えた runtime architecture を定義する。

Phase10 と Phase11 の責務を明確に分離する。

```text
Phase10 = 動かすための基盤
Phase11 = 安全に動かすための基盤
```

Phase10-M / N では実 API 接続、demo 発注、production 発注、訂正、取消、第二暗証番号、unlock 相当処理は行わない。

## 2. Operating Principles

最重要原則:

- Broker を source of truth とする。
- Paper Ledger は評価・シミュレーション専用とする。
- Demo は production runtime の rehearsal 環境とする。
- Production は broker actual cash / buying power / positions / orders / executions を正とする。
- Runtime Foundation は実行順序、状態遷移、manifest、interface を管理する。
- Safety Layer は停止判断、危険検知、復旧判断を管理する。
- Phase10 Runtime Foundation は Safety 判定ロジックを持たない。
- Paper Ledger、Broker Snapshot、backtest、cash、portfolio、PnL は AI 学習データに混入させない。

## 3. Current Baseline

Phase10 の到達状況:

- Tachibana demo login/session/logout: PASS
- account/balance: PASS
- positions: PASS
- orders: PASS
- executions/history: safe empty or safe skip
- broker snapshot: PASS
- p_no monotonic sequence bug: fixed
- demo buying power: 20,000,000 JPY
- demo effective positions: 0

Paper Test 2 の評価前提:

- evaluation cash: 1,000,000 JPY
- broker demo actual cash: 20,000,000 JPY
- demo rehearsal の発注数量は evaluation cash を基準に算出する。
- production は broker actual cash / buying_power を基準にする。

## 4. Phase10 Runtime Foundation Components

### 4.1 Runtime State Machine

責務:

- 日次運用状態を一方向に進める。
- unknown state を `HALT` に寄せる。
- invalid transition を `BLOCKED` として current state を維持する。
- state transition ごとに immutable manifest schema を作れるようにする。

Phase10-N state:

```text
PREOPEN
ORDER_PREPARED
ORDER_SUBMITTED
WAITING_FILL
PARTIALLY_FILLED
FILLED
MONITORING
CLOSE_VALUATION
NIGHTLY_INFERENCE
REPORT_READY
HALT
```

Phase10-N には Safety state を含めない。

### 4.2 Runtime Context / Mode

責務:

- runtime mode を表現する。
- Paper / Demo / Production の共通 context を提供する。
- evaluation cash と broker actual cash を分離する。

Runtime mode:

```text
paper
demo
production
```

Context fields:

```text
business_date
evaluation_cash
broker_actual_cash
broker_snapshot_path
paper_ledger_path
paper_test_id
runtime_id
```

### 4.3 Runtime Manifest

責務:

- 各 state / transition の immutable manifest schema を提供する。
- 副作用がなかったことを明示する。

Phase10-N では file output は行わない。

No-mutation flags:

```text
broker_api_called=false
demo_order_submitted=false
production_order_submitted=false
paper_ledger_updated=false
broker_snapshot_updated=false
ai_learning_updated=false
backtest_run=false
```

### 4.4 Transition Validator

責務:

- allowed transition を判定する。
- unknown state / target を `HALT` に分類する。
- Safety 判定は行わない。

### 4.5 Scheduler Interface

責務:

- runtime job の呼び出し口だけを定義する。
- scheduler 起動や launchd 連携は行わない。

Methods:

```text
preopen()
order_prepare()
submit()
fill_check()
monitor()
close()
nightly()
report()
```

### 4.6 Order Executor Interface

責務:

- Paper / Demo / Production の executor 差し替え口を定義する。
- Phase10-N では実 executor を実装しない。

Methods:

```text
prepare(context, order_plan)
submit(context, prepared_order)
status(context, order_ref)
```

### 4.7 Broker Runtime Interface

責務:

- Broker Snapshot / order status / fill status / position snapshot の差し替え口を定義する。
- Phase10-N では実 broker call を行わない。

Methods:

```text
preopen_snapshot(context)
order_status(context)
fill_status(context)
position_snapshot(context)
close_snapshot(context)
```

### 4.8 Run Lock

責務:

- 同一 business_date の runtime 多重実行を防ぐための基盤を提供する。
- Phase10-N では in-memory store のみ。
- file lock / process lock は後続フェーズで追加する。

### 4.9 Business Day Guard

責務:

- weekend / holiday skip の基盤を提供する。
- Phase10-N では weekday / weekend と明示 holiday set のみ。
- 取引所カレンダー連携は後続フェーズで差し替える。

## 5. Phase11 Safety Layer Boundary

以下は Phase10 Runtime Foundation には含めない。

- Safety Manager
- Safety State Machine
- Emergency Stop
- Hourly Position Monitor
- -7 percent Warning
- -10 percent Stop Loss Candidate
- -15 percent Emergency Candidate
- Duplicate Order Guard
- Broker Divergence Guard
- Quote Stale Guard
- Cash Buffer Guard
- Daily Loss Guard
- Position Risk Guard
- Recovery
- Safety Report

Phase11 は Runtime Foundation の上に Safety Layer として独立実装する。Runtime は Safety の結果を受け取れる interface を後続で持てるが、Phase10-N 時点では Safety 判定を持たない。

## 6. Daily Runtime Flow

Phase10 Runtime Foundation が表現する日次 flow:

1. `PREOPEN`
2. `ORDER_PREPARED`
3. `ORDER_SUBMITTED`
4. `WAITING_FILL`
5. `PARTIALLY_FILLED` or `FILLED`
6. `MONITORING`
7. `CLOSE_VALUATION`
8. `NIGHTLY_INFERENCE`
9. `REPORT_READY`

この flow は処理順序の骨格であり、実 API や発注を実行しない。

Phase11 以降では、この flow の間に Safety Layer の判断を挿入する。

## 7. Broker Source Of Truth

Production:

- Broker cash is true cash.
- Broker buying power is true buying power.
- Broker positions are true positions.
- Broker orders and executions are true order/fill records.

Paper:

- Paper Ledger is simulation state only.
- Paper positions do not imply broker positions.
- Paper fills do not imply broker executions.

Demo:

- Demo broker state is rehearsal state.
- Demo cash may differ from evaluation cash.
- Demo order sizing must be based on evaluation cash when simulating 1,000,000 JPY production capital.

## 8. Cash And Capital

Demo rehearsal:

- broker actual buying power: 20,000,000 JPY
- evaluation cash: 1,000,000 JPY
- order sizing uses evaluation cash.
- broker actual cash is only an upper bound and rehearsal capability check.

Production:

- use broker actual cash / buying power.
- never assume configured capital is available if broker says otherwise.

Phase10-N does not enforce capital rules. Capital checks are introduced through later executor and Safety phases.

## 9. Scheduler Plan

Recommended future schedule:

| Time | Job | Notes |
|---|---|---|
| 08:30 | preopen broker snapshot | future broker runtime implementation |
| 08:45 | order preparation | previous business day candidates |
| 09:00 | order submission | disabled until order phase enables it |
| 09:05 | fill check | order status and executions |
| hourly | position monitoring | Phase11 safety layer |
| 10:30 | broker reconciliation | future read-only reconciliation |
| 12:35 | broker reconciliation | future read-only reconciliation |
| 14:45 | broker reconciliation | future read-only reconciliation |
| 15:30 | close valuation | broker snapshot and valuation |
| 16:30 | report / next-day candidate | redacted reports |

Phase10-N implements only the scheduler interface, not scheduler execution.

## 10. Demo Rehearsal

Demo rehearsal goal:

- Exercise production state machine without production money.
- Keep production order execution disabled.
- Use evaluation cash 1,000,000 JPY for sizing.
- Treat demo broker actual cash 20,000,000 JPY as capacity, not allocation.

Demo order execution is not enabled in Phase10-N.

## 11. Phase Split

Planned phases:

- Phase10-M: production runtime architecture design
- Phase10-N: runtime foundation skeleton
- Phase10-O: demo order design, no production
- Phase10-P: demo buy/sell smoke, no production
- Phase10-Q: fill monitor foundation
- Phase10-S: scheduler integration
- Phase10-T: production readiness audit
- Phase11: safety layer

Phase10-N implements only runtime foundation. It does not implement broker order submission, Safety Manager, or Safety guards.

## 12. Required Artifacts For Future Runtime

Suggested runtime paths:

- `.runtime/production_runtime/state/latest_state.json`
- `.runtime/production_runtime/runs/YYYY-MM-DD/run_manifest.json`
- `.runtime/production_runtime/locks/`
- `.runtime/production_runtime/approvals/`
- `.runtime/production_runtime/reconciliation/`
- `.runtime/production_runtime/reports/`

Safety artifacts should live under a Phase11-owned namespace when implemented.

## 13. Completion Criteria For Runtime Foundation

Runtime foundation requires:

- state machine tests PASS
- transition validator tests PASS
- runtime context supports paper / demo / production
- immutable manifest schema exists
- order executor interface exists
- broker runtime interface exists
- run lock foundation exists
- business day guard foundation exists
- no broker API calls
- no order submission
- no Paper Ledger updates
- no Broker Snapshot updates
- no AI learning changes
- no Safety placeholder in Phase10-N runtime package

