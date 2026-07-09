# Phase14-D6 Existing Demo Order Resolution / Cleanup Design

作成日: 2026-07-07

## Status

```text
PHASE14D6_ORDER_RESOLUTION_PLAN_COMPLETE
```

Phase14-D6 は設計・調査のみである。新規 Demo BUY Submit、SELL Submit、Production 注文、本番 Broker API Write、実資金運用、注文取消、注文訂正、Notification 実送信、launchd / plist 変更、AI 再学習、Backtest / Simulation は行っていない。

## 1. 目的

Phase14-D で送信された `9432 BUY 100` が、Phase14-D5 の ReadOnly before snapshot 時点で未約定 `remaining_quantity=100` のまま残っている。

9000番台銘柄はデモ環境で約定しない前提として扱うため、この注文を Runtime v2 上の未解決 Broker order として整理し、次の D5 再試験へ進めるための安全な処理方針を定義する。

## 2. Current Evidence

根拠:

- `.runtime/phase14d5/broker_readonly_before/tachibana_demo_snapshot.json`
- `.runtime/phase14d5/broker_readonly_before/snapshot_report.json`
- `reports/phase_reports/phase14_d5_pure_runtime_v2_demo_buy_retest.json`

最終観測:

| Item | Value |
| --- | --- |
| observed_at | `2026-07-07T03:15:42.886668+00:00` |
| environment | `demo` |
| order issue | `9432` |
| side | `buy` |
| quantity | `100` |
| executed_quantity | `0` |
| remaining_quantity | `100` |
| status | `未約定` |
| order_id_hash | `order_347b4cfc8e59e728` |
| executions | `0` |
| account readonly | `PASS` |
| orders readonly | `PASS` |
| positions readonly | `PASS` |
| quotes readonly | `PASS_WITH_EMPTY_RESULT` |
| execution detail readonly | `FAIL / FAILED_BROKER_READONLY_FETCH` |

Phase14-D5 はこの unresolved order を検知したため、新規 `7203 BUY 100` Submit 前に停止した。

## 3. State Classification

推奨分類:

```text
Runtime unresolved broker order state: REVIEW_REQUIRED
Next submit gate state: BLOCKED_UNTIL_ORDER_RESOLVED
Fill monitoring state: MONITORING_FILL_NOT_SUITABLE_FOR_9000_SERIES
```

理由:

- Broker order list では未約定、残数量100が確認できる。
- 約定詳細 ReadOnly は失敗しており、Execution evidence がない。
- 9000番台はデモ約定対象外として除外済みのため、単純な `MONITORING_FILL` 継続では D5 再試験を不必要に止め続ける可能性が高い。
- 自動取消、自動再発注、自動SELLは行わない。
- 次の新規BUY/SELLテストは、この unresolved order が解決または明示隔離されるまで BLOCKED とする。

## 4. Pending Plan Handling

Pending plan は `CONSUMED` 扱いにしてよい。ただし、これは「Submit source を再利用しない」という意味に限定する。

方針:

- Phase14-D の pending source は再Submit禁止。
- Brokerに accepted された注文が存在するため、Pending は `SUBMITTED -> CONSUMED` 相当で閉じる。
- `CONSUMED` は約定完了、Asset反映完了、注文解決完了を意味しない。
- Broker order lifecycle は別 evidence として `REVIEW_REQUIRED_UNRESOLVED_OPEN_ORDER` で追跡する。
- Asset Current SoT は `persistent_ledger/state.json` とし、BrokerOrder単体からAssetを作らない。

Ledger / Asset:

- BrokerOrder evidence は Ledger order record に投影可。
- Execution evidence がないため Ledger execution は作らない。
- Position / Cash evidence に変化がない限り Asset position / cash は変更しない。
- Reconcile は unresolved open order と execution detail fetch failure を finding として扱う。

## 5. Cancel Eligibility Design

取消対象にできる可能性はある。ただし、Phase14-D6では取消APIを実行しない。

取消検討条件:

- environment が `demo`
- base URL が demo endpoint
- Production credential / Production endpoint ではない
- ReadOnly order list で対象注文を再確認できる
- issue_code が `9432`
- side が `buy`
- original quantity が `100`
- remaining_quantity が `100`
- executed_quantity が `0`
- status が open / unfilled 相当
- order_id_hash が Phase14-D evidence と一致
- 手動 cancel approval artifact が存在
- cancel source が dedicated cancel plan のみ
- cancel-all を使わない

取消に進んではいけない条件:

- 注文が消えている
- 約定済み、部分約定、残数量不明
- order_id / cancel required fields が確定できない
- ReadOnly detail が不安定で対象注文を一意に特定できない
- Production endpoint / production credential
- POST_SEND_UNKNOWN 後の自動再送
- Runtime v2 以外の旧 Submit authority

## 6. Demo Cancellation Guard Plan

Phase14-D7 以降で取消APIを使う場合の guard:

1. `environment == demo`
2. `base_url == DEMO_BASE_URL`
3. `base_url != PROD_BASE_URL`
4. `cancel_mode == manual_only`
5. `cancel_target_count == 1`
6. `cancel_all == false`
7. `target_order_hash == order_347b4cfc8e59e728`
8. `issue_code == 9432`
9. `side == BUY`
10. `remaining_quantity == 100`
11. `executed_quantity == 0`
12. `approval_hash == cancel_plan_hash`
13. `duplicate_cancel_guard == PASS`
14. `POST_SEND_UNKNOWN` では自動再送しない
15. raw request / raw response / secret を保存しない

許可する場合でも、CLMID は個別取消のみとし、一括取消は対象外にする。

```text
Allowed candidate: CLMKabuCancelOrder
Forbidden: CLMKabuCancelOrderAll
Forbidden: CLMKabuCorrectOrder
```

## 7. Reflection After Cancel

Cancel が実行された場合の反映方針:

1. Cancel response は redacted summary のみ保存。
2. ReadOnly order list で canceled / 取消済み / remaining 0 / open order absent を確認。
3. Execution evidence がない場合、Ledger execution は作らない。
4. Cancel event は Ledger order lifecycle event として記録する。
5. Position / Cash evidence から Asset を再構築する。
6. BrokerOrderのみから Asset を作らない。
7. Reconcile は open order 解消、execution absence、position/cash unchanged を検証する。
8. Report は Current / Evidence / Derived を分離して表示する。
9. Notification は payload 生成のみ。
10. Audit は cancel source にならず evidence としてのみ扱う。

## 8. Next D5 Re-test Conditions

次の D5 再試験へ進む条件:

- 9432 open order が ReadOnly order list から消えている、または canceled / expired と分類できる。
- execution detail fetch failure が残っていても、order list 上で open remaining order が存在しないことを確認できる。
- unresolved order finding が `RESOLVED` または `ISOLATED_DO_NOT_BLOCK_NEW_SCENARIO` になる。
- D5 用 pending plan は Phase14-D / D5 blocked attempt と別ID。
- D5 issue は 9000番台以外。
- D5 BUY は1件のみ。
- Pending-only Submit / Approval必須 / duplicate guard が PASS。
- Production endpoint / production credential に到達しない。

## 9. Acceptance Criteria

| Criteria | Result |
| --- | --- |
| 9432 BUY 100 の最終観測状態を整理している | PASS |
| 未約定 / remaining_quantity=100 の扱いを定義している | PASS |
| Runtime state を REVIEW_REQUIRED / BLOCKED として分類している | PASS |
| Pending plan の CONSUMED 扱いの意味を限定している | PASS |
| 未約定注文をCancel対象にできる条件を定義している | PASS |
| Demo取消API guardを定義している | PASS |
| Cancel後の Ledger / Asset / Reconcile / Report / Audit 反映方針を定義している | PASS |
| 次のD5再試験へ進む条件を定義している | PASS |
| 新規Demo BUY Submitを行っていない | PASS |
| SELL Submitを行っていない | PASS |
| Cancel APIを実行していない | PASS |
| Production注文 / 本番Broker API Writeを行っていない | PASS |

## 10. Final Decision

```text
PHASE14D6_ORDER_RESOLUTION_PLAN_COMPLETE
```

Phase14-D6では、既存 `9432 BUY 100` を unresolved open broker order として `REVIEW_REQUIRED` に分類し、次回D5再試験はこの注文が cancel / expire / isolated として安全に整理されるまで BLOCKED とする設計を完了した。
