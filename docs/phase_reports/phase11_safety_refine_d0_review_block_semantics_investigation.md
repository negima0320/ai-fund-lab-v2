# Phase11-Safety-Refine-D0 Review / Block Semantics Investigation

作成日: 2026-06-29

## Status

```text
PHASE11_REVIEW_BLOCK_SEMANTICS_INVESTIGATION_COMPLETE
REVIEW_REQUIRED_CURRENTLY_BLOCKS_FILL
PHASE11_1Y_MAINLINE_SMOKE_ON_HOLD
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```

## Conclusion

`REVIEW_REQUIRED` は現在の integrated mainline smoke runner では注文を止めている。

`REVIEW_REQUIRED` になった order は `pending_orders` に入らず、後続日の virtual fill に到達しない。したがって現状の `REVIEW_REQUIRED` は、通知・レポート・Human Review Queueに載せるだけではなく、実質的に `BLOCK` と同じく order flow を止める。

これは refined Safety の思想から見ると強すぎる。特に `HIGH_RISK_REVIEW` / `SELL_REVIEW_REQUIRED` のような market/price 系 review が fill を止めており、Safety が投資判断を上書きしている可能性がある。

## Read Materials

- `docs/phase_reports/phase11z_fix_e3_refined_mainline_medium_smoke.md`
- `reports/phase_reports/phase11z_fix_e3_refined_mainline_medium_smoke.json`
- `reports/safety/phase11/integrated_backtest/fix_e3_refined_mainline_medium_smoke/summary.json`
- `reports/safety/phase11/integrated_backtest/fix_e3_refined_mainline_medium_smoke/daily_audit.json`
- `reports/safety/phase11/integrated_backtest/fix_e3_refined_mainline_medium_smoke/virtual_trades.json`
- `reports/safety/phase11/notifications/2025-11-30_line_notification_payload.json`
- `src/ai_fund_lab_v2/safety_phase11/models.py`
- `src/ai_fund_lab_v2/safety_phase11/safety_manager.py`
- `src/ai_fund_lab_v2/safety_phase11/guards.py`
- `src/ai_fund_lab_v2/safety_phase11/hourly_monitor.py`
- `src/ai_fund_lab_v2/safety_phase11/integrated_backtest_audit.py`
- `src/ai_fund_lab_v2/safety_phase11/review_queue_writer.py`
- `src/ai_fund_lab_v2/safety_phase11/notification_payload_writer.py`
- `src/ai_fund_lab_v2/safety_phase11/public_report_section.py`

## Code Flow Finding

Mainline adapterでは、各営業日の先頭で既存 `pending_orders` を `process_virtual_fills` に渡す。

その後、新規 planned order ごとに pre-order Safety を評価する。

該当箇所:

- `src/ai_fund_lab_v2/safety_phase11/integrated_backtest_audit.py:485`
- `src/ai_fund_lab_v2/safety_phase11/integrated_backtest_audit.py:624`
- `src/ai_fund_lab_v2/safety_phase11/integrated_backtest_audit.py:645`
- `src/ai_fund_lab_v2/safety_phase11/integrated_backtest_audit.py:648`

現在の分岐:

```text
if safety_result.overall_decision is not ALLOW:
    continue

pending = _pending_order_from_adapter_plan(...)
new_pending.append(pending)
```

つまり `REVIEW_REQUIRED` / `BLOCK` / `EMERGENCY_STOP` はすべて `continue` され、pending order化されない。

## Review Required Behavior

E3 medium smokeの実績:

```text
orders_generated: 922
orders_allowed_by_safety: 14
orders_blocked_by_safety: 330
orders_review_required: 578
orders_emergency_stopped: 0
virtual_orders_submitted: 14
virtual_fills: 14
```

`REVIEW_REQUIRED` のfill到達:

```text
review_required_orders_total: 578
review_required_orders_filled: 0
review_required_orders_not_filled: 578
review_required_orders_skipped: 578
review_required_orders_pending: 0
```

E3 artifactsには `REVIEW_REQUIRED` orderごとの `side` が保存されていないため、`review_required_buy_orders` / `review_required_sell_orders` は直接計測できない。ただし code flow上、sideに関係なく `overall_decision != ALLOW` は pending化されない。

## Decision Fill Reachability

```text
ALLOW orders: 14
ALLOW fill count: 14
ALLOW fill rate: 1.0

BLOCK orders: 330
BLOCK fill count: 0
BLOCK fill rate: 0.0

REVIEW_REQUIRED orders: 578
REVIEW_REQUIRED fill count: 0
REVIEW_REQUIRED fill rate: 0.0

EMERGENCY_STOP orders: 0
EMERGENCY_STOP fill count: 0
EMERGENCY_STOP fill rate: 0.0
```

結論:

```text
REVIEW_REQUIREDは現在fillへ進まない。
```

## Counter Definitions

`orders_allowed_by_safety`

- order count。
- planned orderごとに `overall_decision == ALLOW` なら1加算。

`orders_blocked_by_safety`

- order count。
- planned orderごとに `overall_decision == BLOCK` なら1加算。
- state由来の BUY_STOP / RECOVERY_CANDIDATE block でも加算され得る。

`orders_review_required`

- order count。
- planned orderごとに `overall_decision == REVIEW_REQUIRED` なら1加算。
- review queue item countではない。
- raw guard occurrence countでもない。

`orders_emergency_stopped`

- order count。
- planned orderごとに `overall_decision == EMERGENCY_STOP` なら1加算。

`review_required_count_by_reason`

- raw guard result occurrence count。
- order countではない。
- review queue item countでもない。

## Review Granularity

Review occurrence:

```text
raw_review_occurrence_count: 1023

HIGH_RISK_REVIEW: 943
SELL_REVIEW_REQUIRED: 54
INDIVIDUAL_DRAWDOWN_WARNING: 20
QUOTE_MISSING_FOR_MONITOR: 6
```

Block occurrence:

```text
raw_block_occurrence_count: 330

MAX_EXPOSURE_EXCEEDED: 330
```

Review粒度:

```text
unique_review_days: 116
unique_review_items_by_date_reason: 116
max_reviews_per_day: 11
median_reviews_per_day: 11.0
review_per_business_day: 8.525
```

E3 daily artifactは `triggered_reason_codes` に issue_code を残していないため、`unique_review_items_by_date_issue_reason` は計測不能。現時点では、同一銘柄 / 同一日 / 同一理由の重複有無を artifact から確定できない。

ただし `HIGH_RISK_REVIEW: 943` は120営業日に対して多く、raw occurrenceをそのままHuman Review扱いにするには過剰。

## Market / Price Review

market/price系reason:

```text
HIGH_RISK_REVIEW
SELL_REVIEW_REQUIRED
INDIVIDUAL_DRAWDOWN_WARNING
```

これらはEmergency Stopにはなっていない。

しかし現在の order flow では、これらが `overall_decision == REVIEW_REQUIRED` を作ると pending order化されず、fillへ進まない。

結論:

```text
market/price系ReviewはEmergencyではないが、現runnerではfillを止めている。
```

## MAX_EXPOSURE_EXCEEDED

Fix-E2後の `MaxExposureGuard` は `side != BUY` を allow にしている。

該当箇所:

- `src/ai_fund_lab_v2/safety_phase11/guards.py:119`
- `src/ai_fund_lab_v2/safety_phase11/guards.py:120`

E3結果:

```text
max_exposure_blocked_buy_orders: 330
max_exposure_blocked_sell_orders: 0
max_exposure_allowed_sell_orders: 4
max_exposure_allowed_exposure_reducing_orders: 4
```

結論:

```text
MAX_EXPOSURE_EXCEEDEDは新規BUYのみ止めている。
SELL / exposure reducing order は止めていない。
```

## Notification / Blog Load

LINE payload:

```text
notification_level: POSITION_REVIEW
line_sections_count: 3
line_triggered_events_count: 5
line_recommended_actions_count: 3
line_send_executed: false
```

Blog / Public Report:

```text
blog_safety_section_review_count: 5
public_report_safety_section_review_count: 5
```

通知・ブログは raw occurrence 943件をそのまま出していない。日次サマリー粒度に集約されている。

結論:

```text
通知負荷は現状では日次まとめ。
問題は通知爆発よりも、REVIEW_REQUIREDがorder flowを止めること。
```

## What Needs To Change Next

通知集約だけでは不十分。

必要な対応:

1. `REVIEW_REQUIRED` をすべて fill停止扱いにしない。
2. market/price系 review は `NON_BLOCKING_REVIEW` または notification-only に分離する。
3. `BLOCK` は system fault / hard risk gate に限定する。
4. `MAX_EXPOSURE_EXCEEDED` は新規BUYのhard risk gateとして残す。
5. review queue / notification は raw occurrence ではなく、日付×銘柄×理由で集約する。
6. 次回smokeでは per-order decision, side, issue_code, reason を保存して、fill到達率を直接検証できるようにする。

## One Year Smoke Readiness

現時点では、1年 refined mainline smokeへ進むべきではない。

理由:

- `REVIEW_REQUIRED` が実質BLOCKとして働いている。
- market/price系Reviewがfillを止めている。
- Review粒度が raw occurrence寄りで、運用負荷の評価に不十分。
- per-order side/reason がartifactに残っておらず、buy/sell別の影響を直接検証できない。

次は Review / Block semantics の policy refinement を実装し、その後に短期または中期 smoke を再実行する。

## Prohibited Actions Confirmation

今回実施していない:

- 修正実装。
- 1年full。
- 5年full。
- Broker API接続。
- WebSocket接続。
- LINE実送信。
- CLMKabuNewOrder。
- Demo発注。
- Production発注。
- 自動売却。
- 自動復帰。
- AI再学習。
- Safety結果のAI学習投入。
- Broker Snapshot実更新。
- 既存Paper Ledger破壊。
- フルテスト。

## Result

```text
PHASE11_REVIEW_BLOCK_SEMANTICS_INVESTIGATION_COMPLETE
REVIEW_REQUIRED_CURRENTLY_BLOCKS_FILL
PHASE11_1Y_MAINLINE_SMOKE_ON_HOLD
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
