# Phase8-F Order Manager Dry-run Workflow

## 1. 目的

Phase8-Fでは、Order Managerを実運用前のdry-runワークフローとして使えるようにした。

実装対象:

```text
OrderPlan永続化
OrderPlan history reader
Human Review approval flow CLI
Paper ledger dry-run command
Phase7 Capital Allocation artifact接続
Safety dry-run統合レポート
Phase8-F audit
```

## 2. 実装境界

Phase8-Fでも以下は実行しない。

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
python3 scripts/smoke_moomoo_readonly_phase8c.py --runtime-dir /private/tmp/phase8f-runtime --reports-dir /private/tmp/phase8f-reports
-> SKIPPED / executed=false
```

## 3. OrderPlan永続化

保存先:

```text
.runtime/order_manager/plans/
```

保存時に必須とする項目:

```text
plan_id
generated_at
schema_version
source
status
```

保存時にも以下を強制する。

```text
executable = false
live_order_allowed = false
requires_human_review = true
```

破損、不正flag、必須項目欠落はfail-closedとして扱う。

## 4. OrderPlan履歴

history readerは以下を提供する。

```text
latest取得
plan_id指定取得
status filter
破損JSON skip + warning
sanitized summary
```

履歴summaryは実口座識別子やsensitive tokenを表示しない。

## 5. Approval flow

CLI:

```text
scripts/create_phase8f_approval_record.py
```

decision:

```text
approved
rejected
needs_change
```

ただし承認しても実発注許可にはならない。

```text
approval_does_not_allow_live_order = true
```

planが以下を満たさない場合、approval作成は禁止する。

```text
executable=false
live_order_allowed=false
requires_human_review=true
```

## 6. Paper ledger dry-run command

CLI:

```text
scripts/apply_phase8f_paper_ledger_dry_run.py
```

保存済みOrderPlanとPaperLedger JSONを読み、dry-runとしてPaperLedgerへ反映する。

```text
Broker snapshotは変更しない
SELL_FIRST_BUY_AFTER_FILL dependencyを検証する
blocked / waiting BUYは反映しない
paper executionとしてのみ記録する
実約定とは混同しない
```

## 7. Phase7 artifact接続

確認した現物artifact:

```text
reports/capital_allocation_ai/phase7_final/phase7_final_summary.json
reports/capital_allocation_ai/phase7a/capital_allocation_decisions.csv
```

接続結果:

```text
Primary policy = CAP5
Shadow policy = CAP4
Shadow policy = POLICY_Y_CAP4_EDGE08_CONF5
Phase8互換decision = 9件
```

Phase7 artifactが欠損する場合はfail-closedとする。

Phase7 CSV上のreview-only / no-action行はOrderPlan候補から除外し、未知actionはINVALID_INPUT相当として停止する。

## 8. Safety dry-run統合レポート

生成対象:

```text
OrderPlan
ReconciliationResult
Safety lock state
Paper ledger dry-run result
Human Review approval record
```

保存先:

```text
.runtime/order_manager/audit/
reports/phase_reports/
```

生成script:

```text
scripts/generate_phase8f_order_manager_dry_run_report.py
```

## 9. 実行したテスト

```text
python3 -m pytest tests/order_manager
-> 34 passed

python3 -m pytest tests/broker
-> 56 passed

python3 -m pytest
-> 836 passed
```

通常pytestでは、moomoo SDK / OpenD / 実API接続は実行されない。

## 10. Audit結果

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
```

Phase8-F auditでは以下を確認した。

```text
実API接続が走らない
moomoo SDK / OpenD接続の自動実行なし
発注系API tokenなし
executable=false固定
live_order_allowed=false固定
requires_human_review=true固定
approvalしてもlive order許可にならない
paper ledgerとBroker snapshotが分離されている
OrderPlan保存時に安全flagが強制される
history readerがsensitive/account identifierを出さない
Phase7 artifact欠損時はfail-closed
```

## 11. Phase8-Gへの引き継ぎ

Phase8-Gでは以下を実装する。

```text
Order Manager dry-run orchestration CLI
Broker snapshot loader + Phase7 artifact loader + reconciliation + plan generator + report writerの一括dry-run
review queue / review status dashboard
paper ledger history diff
Safety Guard dry-run reportとの相互リンク
Phase8 end-to-end no-live-order audit
```

引き続き実発注、自動発注、OpenD接続実行、発注API実装は禁止する。
