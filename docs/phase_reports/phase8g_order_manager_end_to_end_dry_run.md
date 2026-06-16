# Phase8-G Order Manager End-to-End Dry-run

## 1. 目的

Phase8-Gでは、Order Managerのdry-run workflowを一括実行できるCLIを実装した。

実装対象:

```text
Order Manager dry-run orchestration CLI
Review queue / review status dashboard
Paper ledger history diff
Safety Guard dry-run report link
Phase8 end-to-end no-live-order audit
```

## 2. 実装境界

Phase8-Gでも以下は実行しない。

```text
moomoo SDK接続
OpenD接続
実API smoke
実発注
自動発注
発注API実装
```

明示フラグなしのread-only smoke入口は以下の通りSKIPPEDになる。

```text
python3 scripts/smoke_moomoo_readonly_phase8c.py --runtime-dir /private/tmp/phase8g-runtime --reports-dir /private/tmp/phase8g-reports
-> SKIPPED / executed=false
```

## 3. Dry-run orchestration

CLI:

```text
scripts/run_phase8g_order_manager_dry_run.py
```

実行順:

```text
1. Broker snapshot loader
2. Phase7 Capital Allocation artifact loader
3. Paper ledger loader
4. Reconciliation
5. Safety lock state read
6. Order Plan Generator
7. OrderPlan validation
8. OrderPlan store
9. Human Review report writer
10. Paper ledger dry-run update
11. Safety dry-run統合レポート生成
12. Safety report link生成
```

normalized broker snapshotとpaper ledgerが存在しない場合はfail-closedとし、外部接続には進まない。

## 4. Review queue

CLI:

```text
scripts/generate_phase8g_review_queue.py
```

入力:

```text
.runtime/order_manager/plans/
.runtime/order_manager/review/
.runtime/order_manager/audit/
```

出力:

```text
pending_review
approved
rejected
needs_change
invalid_blocked
```

`approved` でも実発注許可にはならない。

```text
approval_does_not_allow_live_order = true
```

## 5. Paper ledger history diff

CLI:

```text
scripts/diff_phase8g_paper_ledger_history.py
```

比較対象:

```text
cash delta
buying power delta
position delta
paper execution delta
blocked / waiting item
```

Broker snapshotとは分離したまま、paper ledger同士だけを比較する。

## 6. Safety report link

Order Manager側に以下を保存する。

```text
.runtime/order_manager/audit/<plan_id>_safety_links.json
.runtime/order_manager/audit/<plan_id>_safety_links.md
```

含めるリンク:

```text
OrderPlan
Reconciliation id
Paper ledger dry-run result
Order Manager dry-run report
Safety dry-run report
```

既存Safety実装は変更しない。

## 7. CLI確認

mock normalized snapshotとpaper ledgerを入力に一括dry-run CLIを確認した。

結果:

```text
plan_status = READY_FOR_REVIEW
phase7_decision_count = 9
reconciliation_status = WARNING
safety_status = UNLOCKED
```

生成確認:

```text
OrderPlan JSON
Human Review markdown
Paper ledger dry-run result
Order Manager dry-run JSON / markdown
Safety links JSON / markdown
Review queue JSON
Paper ledger diff JSON
```

## 8. 実行したテスト

```text
python3 -m pytest tests/order_manager
-> 40 passed

python3 -m pytest tests/broker
-> 56 passed

python3 -m pytest
-> 842 passed
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

python3 scripts/audit_phase8f_order_manager_dry_run_workflow.py
-> PASS

python3 scripts/audit_phase8g_end_to_end_no_live_order.py
-> PASS
```

Phase8-G auditでは以下を確認した。

```text
orchestration CLIが外部接続しない
smokeは明示フラグなしでSKIPPED
moomoo SDK / OpenD接続の自動実行なし
発注系API tokenなし
executable=false固定
live_order_allowed=false固定
requires_human_review=true固定
approvalしてもlive order許可にならない
paper ledgerとBroker snapshotが分離されている
Phase7 artifact欠損時はfail-closed
reconciliation halt時は通常planを生成しない
locked時はREVIEW_ONLY_LOCKED
end-to-end dry-run reportが生成される
```

## 10. Phase8-Hへの引き継ぎ

Phase8-Hでは以下を実装する。

```text
dry-run結果のoperator-facing dashboard整備
review queueの時系列履歴
approval / rejection後の再plan生成フロー
paper ledger diffのmarkdown化
Safety reportへの逆リンク反映方針の設計
Phase8総合completion audit
```

引き続き実発注、自動発注、OpenD接続実行、発注API実装は禁止する。
