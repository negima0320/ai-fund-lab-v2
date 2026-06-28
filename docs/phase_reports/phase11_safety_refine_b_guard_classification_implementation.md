# Phase11-Safety-Refine-B Guard Classification Implementation

作成日: 2026-06-28

## Status

```text
PHASE11_SAFETY_REFINE_B_GUARD_CLASSIFICATION_IMPLEMENTED
LIGHTWEIGHT_TESTS_PASS
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
PHASE11Z_FULL_5Y_REMAINS_ON_HOLD
```

## Purpose

Phase11-Safety-Refine の refined design に合わせて、Safety Layer を「相場下落を止める装置」から「システム事故・発注事故・Broker不整合を止める装置」へ実装上も寄せた。

## Read Materials

- `docs/02_architecture/safety_layer_phase11_refined_design.md`
- `docs/phase_reports/phase11_safety_refinement_plan.md`
- `reports/phase_reports/phase11_safety_refinement_plan.json`
- `docs/02_architecture/safety_layer_phase11_architecture.md`
- `src/ai_fund_lab_v2/safety_phase11/`

## Updated Files

- `src/ai_fund_lab_v2/safety_phase11/models.py`
- `src/ai_fund_lab_v2/safety_phase11/state_machine.py`
- `src/ai_fund_lab_v2/safety_phase11/guards.py`
- `src/ai_fund_lab_v2/safety_phase11/safety_manager.py`
- `src/ai_fund_lab_v2/safety_phase11/hourly_monitor.py`
- `src/ai_fund_lab_v2/safety_phase11/emergency_stop.py`
- `src/ai_fund_lab_v2/safety_phase11/recovery.py`
- `src/ai_fund_lab_v2/safety_phase11/manual_unlock.py`
- `src/ai_fund_lab_v2/safety_phase11/report_schema.py`
- `src/ai_fund_lab_v2/safety_phase11/report_writer.py`
- `src/ai_fund_lab_v2/safety_phase11/integrated_backtest_audit.py`
- `tests/safety_phase11/test_guards_and_manager.py`
- `tests/safety_phase11/test_hourly_monitor.py`
- `tests/safety_phase11/test_emergency_stop.py`
- `tests/safety_phase11/test_safety_report_writer.py`
- `tests/safety_phase11/test_review_queue_writer.py`
- `tests/safety_phase11/test_writers.py`
- `tests/safety_phase11/test_integration_dry_run.py`

## Emergency Stopに残した条件

System emergencyとして残したもの:

- Duplicate Order。
- duplicate broker order risk。
- severe Broker Divergence。
- Position mismatch。
- Order / Execution重大不一致。
- Broker Snapshot unavailable / critical stale / missing。
- Runtime state不整合。
- manual emergency stop。
- secret/raw response保存疑い。
- unknown severe error。

実装上は `SYSTEM_EMERGENCY_STOP` を追加し、既存 `EMERGENCY_STOP` との互換も残した。

## Emergency Stopから外した条件

原則Emergency Stopにしないもの:

- 市場全体の下落。
- market crash guard。
- 個別銘柄下落。
- daily loss。

これらは `REVIEW_REQUIRED` を返し、Human Reviewへ送る。

## Market Crash Guard 新分類

旧:

```text
market crash -> BUY_STOP / EMERGENCY_STOP
```

新:

```text
market_crash -> MARKET_STRESS
severe_market_crash -> BUY_OPPORTUNITY_REVIEW
```

どちらも:

- Emergency Stopではない。
- 自動売却なし。
- 自動買い停止なし。
- Human Review対象。
- Reportに買い場候補として出す。

## Individual Crash Guard 新分類

旧:

```text
-7%  -> WARNING
-10% -> STOP_LOSS_CANDIDATE / BUY_STOP
-15% -> EMERGENCY_CANDIDATE / EMERGENCY_STOP
```

新:

```text
-7%  -> INDIVIDUAL_DRAWDOWN_WARNING
-10% -> SELL_REVIEW_REQUIRED
-15% -> HIGH_RISK_REVIEW
```

どれも自動売却せず、Emergency Stopにしない。保有継続、売却、縮小、買い増しはHuman Review対象。

## Daily Loss Guard 新分類

旧:

```text
daily loss -> BUY_STOP / EMERGENCY_STOP
```

新:

```text
review threshold -> DAILY_LOSS_REVIEW_REQUIRED
stress threshold -> MARKET_STRESS_DAILY_LOSS
```

損失そのものではSystem Emergencyにしない。valuation異常、cash不整合、Broker不整合を伴う場合のみsystem faultとして別guardで止める。

## Report / Review Queue

追加・変更:

- `market_stress_summary`
- `buy_opportunity_review`
- `buy_review_required`
- `sell_review_required`
- `high_risk_review`
- `refined_safety_confirmation`
- `new_buy_without_human_review`
- `emergency_stop_from_market_price_decline=false`
- `auto_sell_executed=false`
- `auto_buy_stop_executed=false`

Market stress / individual drawdown はEmergency候補ではなく、Human Review対象として保存する。

## Lightweight Tests

実行:

```text
PYTHONPATH=src python3 -m pytest tests/safety_phase11 -q
```

結果:

```text
73 passed
```

確認済み:

- market crashだけではEmergency Stopにならない。
- market crashは `MARKET_STRESS` / `BUY_OPPORTUNITY_REVIEW` になる。
- individual -15%だけではEmergency Stopにならない。
- individual -15%は `HIGH_RISK_REVIEW` になる。
- daily lossだけではEmergency Stopにならない。
- duplicate orderはSystem Emergency候補。
- severe broker divergenceはSystem Emergency候補。
- position mismatch / order execution mismatchはreviewまたはsystem emergency候補。
- manual emergencyはSystem Emergency。
- critical staleはEmergencyStopEvaluatorでSystem Emergency候補。
- quote stale単独は `BLOCK` / `BUY_REVIEW_REQUIRED`。
- reportにmarket stress / buy opportunity reviewが出る。
- auto_sell_executed=false。
- auto_recovery_executed=false。
- secret/raw responseが保存されない。

## Prohibited Actions Confirmation

今回実施していない:

- Broker API接続。
- Login/Logout。
- WebSocket接続。
- CLMKabuNewOrder。
- Demo発注。
- Production発注。
- 自動売却。
- 自動復帰。
- AI再学習。
- Safety結果のAI学習投入。
- 5年full backtest。
- フルテスト。

## Next

次は refined Safety 分類で短期 mainline smoke を実行し、Safety ON/OFF比較で相場下落が過剰停止しないことを確認する。

```text
PHASE11_REFINED_SHORT_MAINLINE_SMOKE_READY
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
