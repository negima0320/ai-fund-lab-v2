# Phase8-E Order Plan Generator

## 1. 目的

Phase8-Eでは、Order ManagerのOrder Plan Generatorを実装した。

実装対象:

```text
Capital Allocation decision loader
Order Plan Generator
SELL_FIRST_BUY_AFTER_FILL dependency validation
Human Review approval record
Paper ledger dry-run update
Human Review report拡張
Phase8-E audit
```

## 2. 実装境界

Phase8-Eでも以下は実行しない。

```text
moomoo SDK接続
OpenD接続
実API smoke
実発注
自動発注
発注API実装
```

## 3. Order Plan Generator仕様

入力:

```text
Capital Allocation decision
Broker snapshot
Paper ledger
Order Manager ReconciliationResult
Safety lock state
```

出力:

```text
OrderPlan
OrderPlanItem
```

生成するaction:

```text
BUY
SELL
HOLD
```

ただし全planは以下を固定する。

```text
executable = false
live_order_allowed = false
requires_human_review = true
```

## 4. SELL_FIRST_BUY_AFTER_FILL

replacement_group_id が同じSELL/BUYでは、BUY itemに以下を設定する。

```text
depends_on_fill_item_id = SELL item id
requires_broker_snapshot_refresh = true
action = REPLACE_BUY_AFTER_FILL_PLAN
```

同時発注前提にはしない。

## 5. Safety / Reconciliation

locked時:

```text
plan_status = REVIEW_ONLY_LOCKED
通常plan生成禁止
```

reconciliation halt candidate時:

```text
plan_status = REVIEW_ONLY_RECONCILIATION_HALT
通常plan生成禁止
```

invalid dependency時:

```text
plan_status = INVALID_INPUT
```

## 6. Paper ledger update

OrderPlanをdry-runとしてPaperLedgerへ反映する。

```text
Broker snapshotは変更しない
paper executionとして記録する
SELLを先に反映する
依存BUYはSELL反映後のみ反映する
cash不足BUYは反映しない
```

## 7. Human Review approval

approval recordは `.runtime/order_manager/review/` に保存する。

```text
approval_does_not_allow_live_order = true
```

承認しても実発注許可にはならない。

## 8. 実行したテスト

```text
python3 -m pytest tests/order_manager
-> 25 passed

python3 -m pytest tests/broker
-> 56 passed

python3 -m pytest
-> 827 passed
```

通常pytestでは、moomoo SDK / OpenD / 実API接続は実行されない。

## 9. Audit結果

```text
python3 scripts/audit_phase8b_moomoo_order_manager_foundation.py
-> PASS

python3 scripts/audit_phase8c_moomoo_readonly_smoke.py
-> PASS

python3 scripts/audit_phase8d_order_manager_reconciliation.py
-> PASS

python3 scripts/audit_phase8e_order_plan_generator.py
-> PASS
```

Phase8-E auditでは以下を確認した。

```text
発注系API tokenなし
moomoo SDK / OpenD接続の自動実行なし
executable=false固定
live_order_allowed=false固定
requires_human_review=true固定
approvalしてもlive order許可にならない
SELL_FIRST_BUY_AFTER_FILL dependency検証あり
reconciliation halt時は通常planを生成しない
locked時はREVIEW_ONLY_LOCKED
paper ledgerとBroker snapshot保存先が分離されている
```

## 10. 実API smoke

Phase8-Eでは実API smokeを実行していない。

明示フラグなしのPhase8-C smoke入口のみ確認した。

```text
python3 scripts/smoke_moomoo_readonly_phase8c.py --runtime-dir /private/tmp/phase8e-runtime --reports-dir /private/tmp/phase8e-reports
-> SKIPPED
```

OpenD接続、moomoo SDK接続、実口座read-only取得は実行していない。

## 11. Phase8-Fへの引き継ぎ

Phase8-Fでは以下を実装する。

```text
OrderPlan永続化
OrderPlan history reader
Human Review approval flowのCLI
Paper ledger update command
Capital Allocation実artifactとの接続
Safety dry-runとの統合レポート
```

引き続き実発注、自動発注、OpenD接続実行、発注API実装は禁止する。
