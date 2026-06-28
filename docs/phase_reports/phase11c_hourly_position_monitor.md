# Phase11-C Hourly Position Monitor

- status: IMPLEMENTED
- created_at: 2026-06-28
- scope: pure / mock hourly position monitor for Phase11 Safety Layer
- broker_api_connected: false
- login_logout_executed: false
- websocket_connected: false
- demo_order_submitted: false
- production_order_submitted: false
- clm_kabu_new_order_executed: false
- runtime_behavior_changed: false
- broker_snapshot_updated: false
- paper_ledger_updated: false
- cron_or_launchagent_registered: false
- ai_learning_updated: false

## 1. Summary

Phase11-C では、Phase11-B の `safety_phase11` subsystem に、日中 read-only 監視用の Hourly Position Monitor を追加した。

今回の monitor は、入力済み snapshot / quote / order / execution 風データを使う pure / mock monitor である。Broker API、WebSocket、Demo / Production 発注、Runtime 本体の大規模変更は行っていない。

Safety Layer / Hourly Monitor は AI 学習データを作るものではない。Runtime 安全判定と人間確認のための監視 subsystem である。

AI学習に使わないもの:

```text
Backtest outcome
Paper Ledger
Broker Snapshot
PnL
Portfolio state
Cash
selected / bought / affordable data
Order result
Execution result
Safety result
Audit result
PM multiplier imitation
```

## 2. Implemented Files

追加:

```text
src/ai_fund_lab_v2/safety_phase11/hourly_monitor.py
src/ai_fund_lab_v2/safety_phase11/monitor_schedule.py
tests/safety_phase11/test_hourly_monitor.py
tests/safety_phase11/test_monitor_schedule.py
reports/phase_reports/phase11c_hourly_position_monitor.json
```

最小更新:

```text
src/ai_fund_lab_v2/safety_phase11/__init__.py
src/ai_fund_lab_v2/safety_phase11/models.py
```

## 3. HourlyPositionMonitor Input / Output

入力:

- business_date
- environment
- runtime_id
- current_safety_state
- broker_snapshot
- positions
- quotes
- orders
- executions
- candidate_universe_market_summary
- previous_portfolio_value
- current_portfolio_value
- manual_emergency_stop
- config

出力:

- overall decision
- next recommended safety state
- transition allowed / reason
- SafetyCheckResult list
- SafetyEvent list
- HumanReviewItem list
- monitor summary

## 4. Implemented Monitoring Items

実装した監視:

- Individual Crash
- Quote Freshness
- Broker Snapshot Freshness
- Orders / Executions Consistency
- Market Crash
- Market Recovery
- Broker Divergence
- Duplicate Order Risk
- Daily Loss
- Manual Emergency Stop

個別銘柄急落しきい値:

```text
-7%  : INDIVIDUAL_DRAWDOWN_WARNING
-10% : STOP_LOSS_CANDIDATE
-15% : EMERGENCY_CANDIDATE
```

Phase11 では自動売却しない。Safety Event / Report / Human Review の対象にする。

## 5. Monitor Schedule

`monitor_schedule.py` で推奨監視タイミングを定義した。

```text
09:05
09:30
10:30
12:35
14:45
15:20
```

提供機能:

- schedule definition
- market hours 判定
- next monitor time / datetime 算出

実際の cron / LaunchAgent / automation 登録は行っていない。

## 6. Report / Event Output

Hourly Monitor Report 保存先:

```text
reports/safety/phase11/hourly_monitor/
```

Safety Event 保存先:

```text
.runtime/safety/phase11/events/
```

保存前に Phase11 sanitizer を通す。

保存禁止:

```text
raw request
raw response
plaintext account id
plaintext order id
plaintext execution id
auth id
private key
virtual URL
second password
```

Report には no-live-order confirmation を含める。

## 7. Test Coverage

実行した軽量テスト:

```text
PYTHONPATH=src python3 -m pytest tests/safety_phase11 -q
```

結果:

```text
28 passed
```

確認したこと:

- 正常データでは `ALLOW`。
- 個別銘柄 -7% で `WARNING` / `REVIEW_REQUIRED`。
- 個別銘柄 -10% で `STOP_LOSS_CANDIDATE` / `BUY_STOP` 候補。
- 個別銘柄 -15% で `EMERGENCY_CANDIDATE` / `EMERGENCY_STOP` 候補。
- stale quote は `BLOCK`。
- missing broker snapshot は `REVIEW_REQUIRED`。
- duplicate active buy order は `EMERGENCY_STOP`。
- execution exists but position missing は `REVIEW_REQUIRED`。
- market crash は `BUY_STOP` 候補。
- recovery guard は自動 `NORMAL` 復帰しない。
- monitor schedule は6タイミングを返す。
- report / event に forbidden secret / raw values が保存されない。

## 8. Safety Confirmation

今回行っていないこと:

- Broker API接続
- Login / Logout
- WebSocket接続
- `CLMKabuNewOrder`
- Demo発注
- Production発注
- Runtime本体への大規模変更
- Broker Snapshot更新
- Paper Ledger更新
- 長時間バックテスト
- フルテスト
- AI学習処理変更
- cron / LaunchAgent 登録

## 9. Result

判定:

```text
PHASE11C_HOURLY_POSITION_MONITOR_COMPLETE
PHASE11D_READY_FOR_SAFETY_REPORT
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
