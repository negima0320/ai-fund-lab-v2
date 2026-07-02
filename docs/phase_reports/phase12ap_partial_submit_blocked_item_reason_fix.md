# Phase12-AP Partial Submit BLOCKED_ITEM Reason Fix

## 目的

2026-07-02朝のDemo Submitで、5候補中4件がBrokerへ送信され、23930 / 2393 日本ケアサプライだけが `BLOCKED_ITEM` になった理由を特定し、理由不明の `BLOCK` がFill Monitor / Safety Monitor / Reconcileへ連鎖しないように最小修正した。

追加注文、Production注文、LINE/Discord実送信、AI再学習、Backtestは実施していない。

## 原因

23930 / 2393 日本ケアサプライの `BLOCKED_ITEM` 原因は、Approval単位の `max_notional=600000` に対する残予算不足だった。

- 先行してBroker受付済みの3件: 45600 + 60000 + 199000 = 304600円
- 23930の想定約定代金: 429500円
- 23930直前のApproval残予算: 600000 - 304600 = 295400円
- 23930を加えた場合の累計: 734100円
- 超過額: 134100円

したがって、block reasonは `remaining_approval_budget_insufficient`、blocking stageは `approval_budget` とする。

## 23930 expected_notional確認

23930の `expected_notional=429500` は妥当。

- internal code: 23930
- broker issue code: 2393
- 銘柄名: 日本ケアサプライ
- quantity: 100株
- limit / reference price: 4295円
- expected_notional: 4295 * 100 = 429500円

Max ExposureはPASSしており、Buying PowerもPASSしていた。原因はMax ExposureやBuying Powerではなく、Approval予算の残額不足。

## 修正内容

### Submit artifact

`BLOCKED_ITEM` には必ず以下を残すようにした。

- `block_reason`
- `block_reasons`
- `blocking_stage`
- `remaining_approval_budget`
- `item_expected_notional`
- `cumulative_submitted_notional`
- `max_notional`
- `approval_budget`
- `max_exposure_result`
- `buying_power_result`
- `internal_code`
- `broker_issue_code`
- `projected_buying_power_usage_before_item`
- `projected_buying_power_usage_if_submitted`

また、該当itemを `blocked_items` 配列へ追加するようにした。

### Partial Submit status

5件中4件成功、1件item blockのような部分成功は、全体を不透明な `BLOCK` にせず、`PARTIAL_PASS_WITH_ITEM_BLOCKS` とする。

2026-07-02のsubmit artifactは以下の状態へ修復した。

- status: `PARTIAL_PASS_WITH_ITEM_BLOCKS`
- accepted_order_count: 4
- blocked_item_count: 1
- broker_order_api_called: true
- demo_order_submitted: true
- production_order_submitted: false

23930のitem block後、61660 / 6166 は残予算内のため続行され、Broker受付済みになった。この挙動は今回の設計上正常。

### 後続処理

Fill Monitorは `BLOCKED_ITEM` を未知状態として扱わず、説明済みitem blockとして記録する。

Safety Monitorは、Approval予算不足のような説明済みitem blockを `SYSTEM_EMERGENCY_STOP` にしない。

Reconcileは、受付済み4件とblock済み1件を分けて扱い、理由不明の緊急停止へ落とさない。

### Daily Report

2026-07-02のDaily Reportを再生成し、通常の翌営業日候補と本日Submit結果を混同しないようにした。

Reportには以下を分けて表示する。

- 本日Brokerへ送信済みの注文: 4件
- Item単位BLOCK: 2393 日本ケアサプライ / 100株 / `remaining_approval_budget_insufficient`

## 再評価結果

- Fill Monitor: PASS
- Safety Monitor: PASS
- Reconcile: REVIEW_REQUIRED
- Daily Report: regenerated
- Operation Audit: REVIEW_REQUIRED

Reconcile / Auditの `REVIEW_REQUIRED` は、2026-07-02が朝Submit中心の不完全運用日であることによる確認状態であり、23930の理由不明BLOCKや `SYSTEM_EMERGENCY_STOP` ではない。

## テスト

追加・更新した軽量テスト:

- 5 items / approval budget 600000 / item4予算超過で `BLOCKED_ITEM`
- `blocked_items` にitem4が入る
- item5が残予算内なら続行する
- partial successが不透明な `BLOCK` にならない
- Fill Monitorがaccepted + blocked mixを扱える
- Safety / Reconcileが説明済みitem blockを緊急停止にしない
- Reportが送信済み4件とblock 1件を分けて表示する

実行結果:

- `python3 -m pytest tests/phase12/test_phase12_demo_submit_guard.py tests/phase12/test_operations_fill_monitor_states.py -q`: PASS
- `python3 -m pytest tests/phase12 -q`: PASS（90 passed）
- `python3 -m py_compile` 対象CLI / operations module: PASS

## 禁止事項確認

- Demo追加注文: 未実施
- Production注文: 未実施
- Production Unlock: 未実施
- LINE/Discord実送信: 未実施
- AI再学習: 未実施
- Backtest: 未実施
- raw request / raw response保存: 未実施
- secret保存: 未実施
- Phase9変更: 未実施

## Remaining gaps

- 2026-07-02のDaily Reportは、不完全運用日のため `INCOMPLETE_OPERATION_REPORT` として生成されている。
- Operation Auditは `REVIEW_REQUIRED` のまま。これは不完全運用日の確認状態であり、追加注文やProduction注文を示すものではない。
