# Phase11-Z-Fix-A Integrated Safety Backtest Audit Runner

- status: IMPLEMENTED
- created_at: 2026-06-28
- scope: Phase11-Z integrated safety backtest audit runner repair
- broker_api_connected: false
- websocket_connected: false
- demo_order_submitted: false
- production_order_submitted: false
- auto_sell_executed: false
- auto_recovery_executed: false
- ai_retraining_executed: false
- full_5y_backtest_rerun: false

## Summary

Phase11-Z anomaly investigationで判明した `trade_count=4` 問題に対して、Phase11-Z用の独立監査runnerを修正した。

修正対象は Safety Phase11 の監査adapterのみであり、既存Production Runtime、Broker API、Paper Trading本体、AI学習処理は変更していない。

## Fixed Root Cause

旧runnerの問題:

- 4銘柄固定stub
- BUYのみ
- 既保有なら買わない
- sell / exit / replacementなし
- position closeなし
- `trade_count = len(trades)` の曖昧定義

Fix-A後:

- 60銘柄の監査用candidate universe
- 日次複数候補生成
- BUY / SELL / replacement候補
- max holding days / profit take / drawdown review exit
- cash recycling
- position open / closeを分離集計
- trade_count定義を明記
- manual approval simulationを明示
- docs出力先をconfigで分離

## Candidate Generation

監査用candidate universe:

```text
60 issues
```

日次候補:

```text
daily_candidate_count=6
```

候補scoreは銘柄codeと営業日indexから決定的に生成する。これはAI学習ではなく、Safety統合監査用の疑似candidateである。

旧4銘柄固定:

```text
fixed_4_code_stub_used=false
```

## Sell / Exit / Replacement

通常exit simulation:

- max holding days超過
- profit taking threshold超過
- drawdown review threshold到達

replacement:

- position上限到達時
- candidateに入っていない低priority保有をsell candidate化
- sell後にbuy candidateを通す

注意:

Emergency Stopによる自動売却ではない。Emergency中は order flow を止め、`auto_sell_executed=false` を維持する。

## Metrics Definition

追加・分離した集計:

```text
orders_generated
orders_before_safety
orders_allowed_by_safety
orders_blocked_by_safety
orders_review_required
orders_emergency_stopped
buy_orders_submitted
sell_orders_submitted
buy_fill_count
sell_fill_count
round_trip_count
position_open_count
position_close_count
final_position_count
ledger_entry_count
```

定義:

```text
trade_count = buy_fill_count + sell_fill_count
round_trip_count = closed positions count
```

## Recovery Simulation

Phase11方針:

```text
auto_recovery_executed=false
```

を維持した。

監査用には以下を分離した。

- Recovery Guard detection
- Human Review required
- manual_approval_simulated=true
- MANUAL_APPROVED -> NORMAL は latest Safety Check ALLOW の場合のみ

manual approval simulationを無効化したfixtureでは、RECOVERY_CANDIDATEから自動NORMAL復帰しないことをテストしている。

## Report Output Isolation

`IntegratedBacktestAuditConfig.docs_dir` を追加した。

挙動:

- 本番reports_dirが `reports` の場合は従来どおり `docs/phase_reports`
- tests / tmp reports では `docs_dir` 指定によりtmpへ出力
- `reports_dir != reports` かつ `docs_dir` 未指定なら `reports_dir/phase_reports` へ出力

これによりテスト時に `docs/phase_reports/phase11z_integrated_safety_backtest_full_5y.md` を上書きしない。

## Pass Conditions

追加したPASS条件:

- `orders_generated > 0`
- `orders_before_safety > 0`
- `buy_fill_count > 0`
- `sell_fill_count > 0`
- `position_open_count > 0`
- `position_close_count > 0`
- `trade_count` が極端に少なすぎない
- 4銘柄固定stub未使用
- candidate universeが30銘柄以上
- manual approval simulation利用可能
- Recoveryが自動NORMAL復帰しない
- testsでdocs outputが隔離される

## Lightweight Smoke

5年fullは再実行していない。

tmp出力先で120営業日の短期smokeのみ実行した。

```text
business_day_count: 120
status: PASS
candidate_universe_size: 60
orders_generated: 233
orders_before_safety: 233
buy_fill_count: 15
sell_fill_count: 10
trade_count: 25
round_trip_count: 10
position_open_count: 15
position_close_count: 10
final_position_count: 5
```

## Test

実行:

```text
PYTHONPATH=src python3 -m pytest tests/safety_phase11/test_integrated_backtest_audit.py -q
```

結果:

```text
9 passed
```

確認:

- 4銘柄固定stubを使っていない。
- 複数候補が生成される。
- buy fill / sell fill が発生する。
- position close が発生する。
- trade_count定義が明示される。
- Safetyがpre-orderで呼ばれる。
- BUY_STOP中に新規買いしない。
- EMERGENCY_STOP中に新規買い・auto sell・retryしない。
- Recoveryはmanual approval simulationなしにNORMAL復帰しない。
- manual approval simulationありでMANUAL_APPROVED経由を検証する。
- tmp outputを使い、固定docs pathを上書きしない。
- secret / raw responseが保存されない。

## Safety Confirmation

今回行っていないこと:

- Broker API接続
- Login / Logout
- WebSocket接続
- CLMKabuNewOrder
- Demo発注
- Production発注
- Emergency Stopによる自動売却
- 自動復帰
- AI再学習
- Safety結果のAI学習投入
- Production Runtime本体の大規模変更
- Broker Snapshot実更新
- 既存Paper Ledger破壊
- 5年full backtest再実行
- フルテスト

## Result

```text
PHASE11Z_FIX_A_INTEGRATED_AUDIT_RUNNER_COMPLETE
PHASE11Z_FIX_B_1Y_SMOKE_READY
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
