# Phase11-Z Trade Count Anomaly Investigation

- status: INVESTIGATION_COMPLETE
- created_at: 2026-06-28
- scope: Phase11-Z integrated safety backtest audit anomaly investigation
- implementation_changed: false
- broker_api_connected: false
- websocket_connected: false
- live_order_executed: false
- demo_order_executed: false
- production_order_executed: false
- auto_sell_executed: false
- auto_recovery_executed: false
- full_5y_backtest_rerun: false

## Conclusion

`trade_count=4` の直接原因は、Safety Layer が過剰に止めたことではなく、`integrated_backtest_audit.py` の統合監査runnerが簡略化されすぎていることである。

主因:

- `_candidate_code()` が4銘柄だけをローテーションする。
- `_virtual_buy()` が既保有銘柄を再購入しない。
- 売却 / exit / rebalance / replacement logic がない。
- positions は一度買うと最後まで残る。
- その結果、最初の4営業日に4銘柄を買った後、以後はSafetyが `ALLOW` でも `_virtual_buy()` が `None` を返す。

Safetyも後半の注文を止めているが、Safety OFF の小範囲比較でも `trade_count=4` のままだったため、根本原因はSafetyではなくrunner側のOrder Plan / Fill / Ledger相当stubである。

## Direct Evidence

5年監査の実データ:

```text
business_days: 1304
orders_before_safety: 1304
pre_order_ALLOW: 1156
virtual_orders_submitted: 4
virtual_fills: 4
ledger_trade_count: 4
position_open_count: 4
position_close_count: 0
```

最初の4営業日だけ約定:

```text
2021-06-01 BUY 7203
2021-06-02 BUY 6758
2021-06-03 BUY 9984
2021-06-04 BUY 8306
```

その後は候補がこの4銘柄に戻るが、既保有判定で追加発注されない。

関連コード:

- `src/ai_fund_lab_v2/safety_phase11/integrated_backtest_audit.py`
  - `_candidate_code()` は `7203 / 6758 / 9984 / 8306` の4銘柄固定。
  - `_virtual_buy()` は `if code in positions: return None`。
  - 売却処理は存在しない。
  - `trade_count` は `len(trades)`。

## Daily Flow Counts

```text
business_days: 1304
ai_signal_days: stubbed_every_business_day
candidate_generated_days: 1304
order_plan_generated_days: 1304
orders_before_safety: 1304
orders_allowed_by_safety: 1156
orders_blocked_by_safety_or_state: 1284
orders_review_required: 72
orders_emergency_stopped: 545
virtual_orders_submitted: 4
virtual_fills: 4
ledger_trade_count: 4
position_open_count: 4
position_close_count: 0
```

補足:

- `orders_allowed_by_safety=1156` なのに約定が4件しかない。
- これは、Safety後段の `_virtual_buy()` が既保有4銘柄を拒否し続けているため。
- `orders_blocked_by_safety_or_state` には `RECOVERY_CANDIDATE` / `EMERGENCY_STOP` 滞在によるstate blockも含む。

## Safety State Residency

`safety_state_before` 基準:

```text
NORMAL: 21 days
WARNING: 0 days
BUY_STOP: 1 day
EMERGENCY_STOP: 523 days
RECOVERY_CANDIDATE: 759 days
MANUAL_APPROVED: 0 days
```

`BUY_STOP` は短いが、`RECOVERY_CANDIDATE` と `EMERGENCY_STOP` に長期間滞在している。

これはPhase11の設計どおり「自動復帰しない」挙動ではある。ただし、5年監査runnerにmanual approval simulationがないため、実運用の復帰判断とは同等ではない。

## BLOCK / REVIEW / EMERGENCY Reason Breakdown

reason_code 上位:

```text
RECOVERY_CANDIDATE_REVIEW_REQUIRED: 66
MARKET_CRASH_BUY_STOP: 32
INDIVIDUAL_DRAWDOWN_WARNING: 28
STOP_LOSS_CANDIDATE: 24
DAILY_LOSS_BUY_STOP: 20
EMERGENCY_CANDIDATE: 18
BROKER_DIVERGENCE_DETECTED: 16
MAX_EXPOSURE_EXCEEDED: 16
QUOTE_STALE_FOR_MONITOR: 13
QUOTE_STALE: 13
MARKET_CRASH_EMERGENCY: 12
DUPLICATE_ACTIVE_BUY_ORDER: 10
BROKER_DUPLICATE_ORDER_RISK: 10
DUPLICATE_ORDER_BLOCKED: 10
MANUAL_EMERGENCY_STOP: 10
CASH_BUFFER_VIOLATION: 8
BROKER_SNAPSHOT_STALE: 7
```

guard別:

```text
MarketCrashGuard: 44
QuoteStaleGuard: 26
DuplicateOrderGuard: 20
CashBufferGuard: 8
MaxExposureGuard: 16
BrokerDivergenceGuard: 16
DailyLossGuard: 20
EmergencyStopGuard: 10
IndividualCrashGuard:
  warning: 28
  stop_loss_candidate: 24
  emergency_candidate: 18
MarketRecoveryGuard: 66
```

Safetyは正常に異常を検知している。一方、`pre_order_ALLOW=1156` が示す通り、Safetyが全注文を止めているわけではない。

## Safety OFF Comparison

軽量な読み取りスクリプトで、同じrunnerの `_candidate_code()` / `_virtual_buy()` を使い、Safety state gating を外した場合を小範囲で確認した。

```text
range: 2025-06-01..2026-05-31
business_days: 260
orders_generated: 260
virtual_fills: 4
trade_count: 4
final_equity: 1,012,900
positions: 7203, 6758, 9984, 8306
```

```text
range: 2021-06-01..2021-12-31
business_days: 154
orders_generated: 154
virtual_fills: 4
trade_count: 4
final_equity: 1,003,400
positions: 7203, 6758, 9984, 8306
```

Safety OFFでも `trade_count=4` のため、Safety過剰停止が主因ではない。

## Existing Paper Tradingとの差分

既存Paper Trading / Order Manager は以下を持つ。

- allocation decisions 由来の `BUY / SELL / HOLD`
- sell-first / buy-after-fill dependency
- replacement group
- cash buffer付き order plan
- pending orders
- virtual fill processor
- ledger positions / pending_orders / performance
- trade_count の累積更新

一方、Phase11-Z integrated audit runner は以下のstubである。

- AI / Order Plan は実接続ではなく日次固定候補。
- candidate universe は4銘柄だけ。
- max position count / replacement / rebalance がない。
- sell / exit logic がない。
- pending order / T+2 fill timing がない。
- Paper Ledger本体を使わず、runner内部の一時 `positions` と `trades` だけ。
- Order Planは既存 `generate_order_plan()` を通っていない。
- Virtual Fillは既存 `process_virtual_fills()` を通っていない。

したがって、今回のrunnerは「Safety subsystemの監査」には使えるが、「既存Paper Trading相当の取引頻度」を再現していない。

## trade_count Definition

Phase11-Z runnerの `trade_count` は以下である。

```text
len(trades)
```

ここで `trades` は `_virtual_buy()` が返した `AuditTrade` の数であり、実質的に「virtual BUY fill count」である。

これは以下ではない。

- round trip count
- sell fill count
- position close count
- full ledger entry count
- existing PaperTradingLedger performance.trade_count

売却処理がないため、`position_close_count=0` である。

## Recovery Candidate Count Interpretation

5年結果:

```text
business_days: 1304
RECOVERY_CANDIDATE_count: 1547
```

これは「日数」ではない。

`integrated_backtest_audit.py` は1営業日に以下2回のSafety集計を行う。

- HourlyPositionMonitor
- pre-order SafetyManager

`_update_safety_counts()` がそれぞれのstate candidateを加算するため、`RECOVERY_CANDIDATE_count` はイベント / チェック回数ベースであり、営業日数を超えうる。

実際の滞在日数は:

```text
RECOVERY_CANDIDATE days: 759
```

ただし、759営業日の滞在は長く、manual approval simulationがないため解除されない設計上の副作用である。

## Additional Finding

`docs/phase_reports/phase11z_integrated_safety_backtest_full_5y.md` が、調査時点でfixture相当の期間表示になっていた。

一方、JSON:

```text
reports/phase_reports/phase11z_integrated_safety_backtest_full_5y.json
```

は5年結果を保持している。

これはテスト実行時にphase report pathが固定で、tmp reportsを使っても docs 側へ書く設計だったことによる可能性が高い。調査のみのため修正はしていない。

## Root Cause by Layer

```text
AI / Order Plan:
  実AI / 既存Order Planではなく4銘柄固定stub。

Safety:
  異常検知は効いているが、主因ではない。
  Safety OFFでもtrade_count=4。

Fill:
  既存Virtual Fillではなくrunner内の簡易 _virtual_buy。
  既保有ならNone。

Ledger / Position Update:
  既存Paper Ledgerではなく一時dict。
  sell / close / replacement が存在しない。

Recovery:
  自動NORMAL復帰しない設計は守られている。
  ただしmanual approval simulationがないため長期残留する。
```

## Should We Fix?

修正は必要。

ただしSafety Layer本体ではなく、Phase11-Z integrated audit runner の監査adapterを改善すべきである。

候補:

1. 既存Paper Trading / Order Manager adapterを使う。
   - allocation decisions
   - order plan generator
   - pending order
   - virtual fill processor
   - ledger valuation

2. 少なくともPhase11-Z runnerに以下を追加する。
   - larger candidate universe
   - max position count
   - sell / exit / replacement logic
   - holding days
   - cash recycling
   - position close count
   - buy fill count / sell fill count / order generated count の分離

3. Recovery監査を分離する。
   - Recovery Candidate検出
   - Human Review pending
   - Manual Approval simulation
   - `MANUAL_APPROVED -> NORMAL` の検証
   - 自動復帰なしの検証

4. レポート出力パスを修正する。
   - testsで docs/phase_reports を上書きしない。
   - tmp reports指定時はphase docsもtmpへ逃がす。

## Should Phase11-Z Be Rerun?

はい。runner修正後に再実行すべき。

理由:

- 現在の5年結果はSafety subsystemの検知監査としては参考になる。
- しかし、既存Paper Trading相当の注文生成 / fill / ledger統合監査としては不十分。
- `trade_count=4` は実運用想定より明らかに低く、Phase12移行判断の根拠としては弱い。

推奨順序:

```text
Phase11-Z-Fix-A:
  integrated audit adapter修正

Phase11-Z-Fix-B:
  1年smoke再実行

Phase11-Z-Fix-C:
  5年full再実行

Phase11 Complete再判定
```

## Final Judgement

```text
PHASE11Z_TRADE_COUNT_ANOMALY_CONFIRMED
ROOT_CAUSE_INTEGRATED_AUDIT_RUNNER_STUB
SAFETY_NOT_PRIMARY_CAUSE
PHASE11Z_RERUN_REQUIRED_AFTER_RUNNER_FIX
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
