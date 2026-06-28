# Phase11 Final Summary / Phase12 Handoff

作成日: 2026-06-29

## Final Judgement

```text
PHASE11_COMPLETE
PHASE12_DEMO_FULL_OPERATION_READY_FOR_DESIGN
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```

Phase11 は Safety Layer / System Guard / Refined Safety / MAX_EXPOSURE / 通知・ブログ連携 / 監査まで完了した。

今回の最終handoff作成では、実装変更、Broker API接続、WebSocket接続、LINE実送信、Demo/Production発注、自動売却、自動復帰、AI再学習、1年/5年backtest再実行は行っていない。

## Read Materials

- `docs/phase_reports/phase11_completion_audit.md`
- `reports/phase_reports/phase11_completion_audit.json`
- `docs/phase_reports/phase11_safety_refinement_plan.md`
- `docs/02_architecture/safety_layer_phase11_refined_design.md`
- `docs/phase_reports/phase11_safety_refine_b_guard_classification_implementation.md`
- `docs/phase_reports/phase11_safety_refine_c_notification_blog_integration.md`
- `docs/phase_reports/phase11_safety_refine_d0_review_block_semantics_investigation.md`
- `docs/phase_reports/phase11_safety_refine_d1_non_blocking_review_policy.md`
- `docs/phase_reports/phase11_max_exposure_investigation.md`
- `docs/phase_reports/phase11_safety_cap_fix_equity_linked_exposure.md`
- `docs/phase_reports/phase11_safety_on_outperformance_attribution.md`
- `docs/phase_reports/phase11z_fix_h_1y_equity_linked_exposure.md`
- `docs/phase_reports/phase11z_fix_g_5y_refined_mainline_full.md`
- `docs/phase_reports/phase10_final_summary_and_phase11_handoff.md`
- `docs/01_requirements/phase_roadmap.md`
- Related JSON reports under `reports/phase_reports/`

## Phase11 Timeline

Phase11-A: Safety Architecture

- Safety Layer を Broker Runtime / Runtime 本体から分離する設計を作成。
- Broker Source of Truth、Fail Closed、Default Deny、secret/raw response非保存を前提にした。

Phase11-B: Safety Runtime Foundation

- `safety_phase11` subsystem を作成。
- Safety State Machine、SafetyManager、Guards、Event Writer、Report Writerを実装。
- 判定は `ALLOW / BLOCK / REVIEW_REQUIRED / EMERGENCY_STOP`。

Phase11-C: Hourly Position Monitor

- 外部接続なしの read-only / mock monitor を実装。
- Broker Position、Realtime Quote風データ、Orders、Executions、freshness、個別急落、Market Crash、Broker Divergence、Duplicate Order Riskを監視対象にした。

Phase11-D: Safety Report / Human Review

- Safety Report、Human Review Queue、Blocked Order Summary、Emergency Candidate Summary、Market Crash / Recovery Summaryを整備。
- Markdown / JSON reportとreview queueを生成できるようにした。

Phase11-E: Emergency Stop Foundation

- 緊急停止の基盤を実装。
- 新規買い、自動売却、retry、自動復帰を止め、read-only sync / audit / report / Human Reviewを残す設計にした。

Phase11-F: Recovery / Manual Unlock

- `RECOVERY_CANDIDATE -> MANUAL_APPROVED -> NORMAL` のみ復帰可能にした。
- 自動復帰は実装せず、manual approvalとlatest Safety Checkを必須にした。

Phase11-G: Safety Integration Dry Run

- mock broker snapshot / positions / quotes / orders / executions / market summaryで統合dry-runを実施。
- HourlyPositionMonitor、SafetyManager、EmergencyStopEvaluator、RecoveryEvaluator、Report、Review Queue、Manual Unlockを外部接続なしで連携確認した。

Phase11-Z Initial Audit

- 初回5年統合監査で `trade_count=4` という異常を検出。
- 原因は integrated audit runner が簡略stubに近く、4銘柄固定、注文生成、fill、ledger、close logicがmainline Paper Trading相当ではなかったこと。

Fix-A / Fix-B / Fix-B2 / Fix-D / E2 / E3 / F / G / H

- Fix-A: 4銘柄固定stubを廃止し、60銘柄universe、日次候補、BUY/SELL/replacement、cash recycling、position close、trade_count定義分離を導入。
- Fix-B / Fix-B2: 1年smoke、Emergency Stop多発、normal_market profile、低リターン要因を調査。
- Fix-D: mainline Paper Trading / CAP5 Order Flow Adapterを導入。
- E2 / E3: refined Safety mainline short / medium smokeを実施。
- Fix-F: refined Safety 1年 mainline smokeをPASS。
- Fix-G: refined Safety 5年 mainline fullをPASS。ただし、この時点ではMAX_EXPOSURE固定85万円cap修正前。
- Fix-H: equity-linked MAX_EXPOSURE後の1年smokeをPASS。

Safety Role Redefinition

- Safety Layerを「市場下落で買いを止める装置」から「システム事故・発注事故・Broker不整合を止める装置」へ再定義した。
- Market crash / individual drawdown / daily lossは投資判断またはHuman Review対象へ移した。

Review Required Semantics

- Refine-D0で `REVIEW_REQUIRED` がrunner上で実質 `BLOCK` と同じになっていることを確認。
- Refine-D1で `BLOCKING_REVIEW / NON_BLOCKING_REVIEW / INFO_ONLY` を導入。
- Market/price/position reviewは `NON_BLOCKING_REVIEW` とし、fillを止めずにHuman Review / Report / Notificationへ送る仕様へ修正した。

MAX_EXPOSURE Fixed Cap Problem

- 5年fullで収益差の主因が `MAX_EXPOSURE_EXCEEDED` であることを調査。
- `max_total_exposure=850000円` が固定金額として効き続け、資産成長後も新規BUYを過剰に止めていた。
- Safety-Cap-Fixで equity-linked ratio capへ変更した。

Safety ON Outperformance Attribution

- Fix-H 1年smokeで Safety ON が Safety OFF を上回った理由を既存artifactのみで調査。
- 結論は `CONCLUSION_A`: MAX_EXPOSUREが悪いBUYを止めたため、Safety ONが実力で良化した可能性が高い。

## Final Safety Role

最終仕様:

```text
市場下落・個別下落 = 投資判断 / NON_BLOCKING_REVIEW / 通知 / 買い場候補
System / Broker / Order異常 = BLOCK / SYSTEM_EMERGENCY_STOP
```

Safety LayerはAI学習データを作るものではない。Safety result、Audit result、Broker Snapshot、Paper Ledger、PnL、portfolio state、cash、selected / bought / affordable data、order result、execution result、PM multiplier imitationはAI学習へ使用しない。

### Stop / Block Conditions

- Duplicate Order
- duplicate broker order risk
- severe Broker Divergence
- Position mismatch
- Runtime state不整合
- Order / Execution重大不一致
- critical stale quote / broker snapshot
- manual emergency
- secret/raw保存疑い
- unknown severe error
- Cash / buying_power hard violation
- MAX_EXPOSURE for new BUY

### Non-Blocking Review Conditions

- Market crash
- Market stress
- Individual drawdown
- Daily loss
- HIGH_RISK_REVIEW
- SELL_REVIEW_REQUIRED
- BUY_OPPORTUNITY_REVIEW
- BUY_REVIEW_REQUIRED

これらは通知、Human Review Queue、Blog/Public Reportに出すが、単独ではfill停止しない。自動売却、自動復帰、自動買い停止は行わない。

## MAX_EXPOSURE Final Spec

旧問題:

```text
max_total_exposure=850000円 が固定金額として効き続け、資産成長後も新規BUYを過剰に止めた
```

新仕様:

```text
max_total_exposure_ratio = 0.85
max_total_exposure_absolute_cap = null
exposure_basis = equity
base_equity = current_total_equity
max_allowed_exposure = base_equity * 0.85
```

判定式:

```text
current_exposure = current_position_market_value
projected_exposure = current_exposure + new_buy_order_value

if side == BUY and projected_exposure > max_allowed_exposure:
    BLOCK / MAX_EXPOSURE_EXCEEDED
else:
    ALLOW
```

SELL / exposure reducing order は常に通す。

Demo / Productionでは、`base_equity` を Paper ledger equityではなく、Broker actual equity / buying_power basisへ接続する必要がある。Phase11ではBroker接続は行っていない。

## Notification / Blog / Public Report

- LINE notification payload生成に対応した。
- LINE実送信は未実施。
- Blog / Public Daily Reportに `Safety / Market Review` セクションを追加した。
- System Emergencyだけを停止扱いにする。
- Market stress / Buy opportunity / Position reviewは、買い場候補・人間確認・自動売却なし・自動停止なしとして表現する。

使う表現:

```text
市場下落を検知しました
買い場候補として確認してください
自動売却はしていません
自動停止ではありません
人間確認対象です
```

避ける表現:

```text
暴落のため強制停止
暴落のため自動売却
市場急落によりEmergency Stop
```

## Audit Results

### Fix-H 1-Year Refined Mainline Smoke

Period:

```text
2025-06-01 to 2026-05-31
profile: mainline_paper_adapter
```

Safety ON:

```text
business_days: 260
orders_generated: 436
orders_allowed_by_safety: 316
orders_blocked_by_safety: 120
buy_fill_count: 159
sell_fill_count: 151
trade_count: 310
final_equity: 1,784,520
total_return: 0.78452
annualized_return: 0.72588
max_drawdown: -0.121077
profit_factor: 1.574577
```

Safety OFF:

```text
orders_generated: 397
buy_fill_count: 193
sell_fill_count: 185
trade_count: 378
final_equity: 1,426,090
total_return: 0.42609
annualized_return: 0.397185
max_drawdown: -0.214177
profit_factor: 1.262163
```

MAX_EXPOSURE after equity-linked cap:

```text
max_exposure_blocked_buy_orders: 120
max_exposure_blocked_sell_orders: 0
max_exposure_allowed_sell_orders: 156
average_base_equity: 1,431,061
average_max_allowed_exposure: 1,216,402
fixed_absolute_cap_used: false
max_total_exposure_ratio: 0.85
exposure_basis: equity
```

### Fix-G 5-Year Refined Mainline Full

Period:

```text
2021-06-01 to 2026-05-31
profile: mainline_paper_adapter
```

Safety ON:

```text
business_days: 1304
orders_generated: 4795
orders_allowed_by_safety: 639
orders_blocked_by_safety: 4156
buy_fill_count: 300
sell_fill_count: 298
trade_count: 598
final_equity: 4,246,630
annualized_return: 0.312197
max_drawdown: -0.251216
```

Safety OFF:

```text
orders_generated: 1587
buy_fill_count: 755
sell_fill_count: 747
trade_count: 1502
final_equity: 19,921,280
annualized_return: 0.754366
max_drawdown: -0.268152
```

Important caveat:

```text
Fix-G 5年fullはMAX_EXPOSURE固定85万円cap修正前の結果
```

したがってFix-Gは、refined Safety + mainline adapterが5年完走できること、market/price系ReviewがEmergency Stop化しないこと、System系だけがHard Gateになることの監査証跡として扱う。equity-linked MAX_EXPOSURE修正後の5年収益評価としては扱わない。

Exit caveat:

```text
exit_source=fallback
```

これはPhase12 Demo mechanicsのブロッカーではないが、Production品質の収益評価前にはmainline Exit統合を閉じる必要がある。

## Safety ON Outperformance Attribution

結論:

```text
CONCLUSION_A
MAX_EXPOSUREが悪いBUYを止めたため、Safety ONが実力で良化した可能性が高い
```

根拠:

```text
blocked BUY: 120
20営業日後平均return: -0.042473
20営業日後positive_rate: 0.316667
OFFで実際に買われた該当lot近似realized PnL: -103,690
OFF該当lot win_rate: 0.428571
OFF該当lot profit_factor: 0.747375
OFF最大DD期間中にONでblockされたBUY: 32
```

解釈:

- Safety ONは取引数を減らしたが、損失lotと高DD局面での追加exposureを抑えた。
- blocked候補には45営業日内の大きな上昇余地もあったため、完全に「すべて悪い注文」ではない。
- ただし20営業日後平均return、OFF実買いlot近似PnL、DD改善を合わせると、Fix-HのSafety ON優位は偶然だけとは言いにくい。

Limit:

- order_id redactionにより、OFFで買われた該当lotのrealized PnLはFIFO近似。
- 完全因果証明ではない。
- 今後は `blocked_order_trace.json`、`order_decision_trace.json`、stable internal join key、future return after blockをartifact化するのが望ましい。

## Remaining Risks

- `exit_source=fallback` はPhase12 Demo mechanicsのブロッカーではないが、Production品質の収益評価前に解消が必要。
- Demo/ProductionではMAX_EXPOSURE `base_equity` を Broker actual equity / buying_power basisへ接続する必要がある。
- Human Review運用手順、manual approval、review queue確認フローはPhase12で実地確認が必要。
- LINE実送信はまだ未実装/未実施。
- equity-linked MAX_EXPOSURE修正後の5年fullはまだ再実行していない。
- Safety ON Outperformance Attributionはorder_id redactionにより近似分析。
- Live order execution remains blocked until Phase12 design and explicit approval.

## Phase12 Handoff

Phase12の目的:

```text
Demo Full Operation Validation
Productionと同一Runtimeで、Demo環境における発注・約定・Fill Monitor・Broker Snapshot・Reportを30営業日検証する
```

Phase12開始前提:

- Phase11 Safety subsystemは完了。
- refined SafetyはSystem事故を止め、market/price reviewをNON_BLOCKING_REVIEWとして扱う。
- MAX_EXPOSUREはequity-linked ratio capへ移行済み。
- LINE payload / Blog / Public Reportは生成可能。
- 実発注はまだ禁止。

Phase12で最初に設計すべきこと:

1. Demo Full Operation Design / Preflight Planを作成する。
2. Demo Broker actual equity / buying_powerをMAX_EXPOSURE `base_equity` に使う設計を確定する。
3. Order Plan -> Safety -> Approval -> Demo Executor の手動承認境界を定義する。
4. CLMKabuNewOrderは、Phase12設計と明示承認が完了するまで実行しない。
5. Fill Monitor、Orders、Executions、Broker Snapshot、Ledger、Report、LINE payload、Blog/Public Reportの一連の照合手順を作る。
6. Human Review Queue / Manual Unlock / Emergency Stop runbookを運用者目線で確認する。
7. Broker Snapshot / Paper Ledger / PnL / Safety result / Audit resultをAI学習へ混入させない監査を継続する。
8. 30営業日のDemo validation完了までProduction発注は禁止する。

Phase12で維持する禁止境界:

- Production発注禁止。
- Demo発注も設計・承認前は禁止。
- 自動売却禁止。
- 自動復帰禁止。
- LINE実送信は別途承認まで禁止。
- Broker Source of Truthを維持。
- Fail Closed / Default Deny / Secret Redaction / Raw Response保存禁止を維持。

## Current Integrity Confirmation

- Broker API接続: not executed in this final summary step
- WebSocket接続: false
- LINE実送信: false
- Demo order: false
- Production order: false
- auto_sell_executed: false
- auto_recovery_executed: false
- AI retraining: false
- one_year_backtest_rerun: false
- five_year_backtest_rerun: false
- Runtime large change: false
- implementation_changed: false

## Final Status

```text
PHASE11_COMPLETE
PHASE12_DEMO_FULL_OPERATION_READY_FOR_DESIGN
LIVE_ORDER_EXECUTION_REMAINS_BLOCKED
```
