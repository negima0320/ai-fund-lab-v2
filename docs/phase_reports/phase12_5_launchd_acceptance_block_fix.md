# Phase12.5 launchd Acceptance BLOCK Fix

作成日: 2026-07-02  
目的: launchd / plist Acceptance GateでBLOCKになった自動運用経路を修正する。  
判定: **REVIEW_REQUIRED**

`demo_submit`, `fill_monitor`, `safety_monitor`, `reconcile` のlaunchd last exit code=2は修正し、launchd経由artifact生成・mtime対応・共通Submit metadataを確認した。  
一方、`daily_report` は `--send-notifications` 付きで実通知送信を伴うため、kickstartは安全審査で拒否された。notification artifactのlaunchd由来確認は未完了のため、最終PASSではなくREVIEW_REQUIREDとする。

## 1. BLOCK原因

### 修正済み

1. `demo_submit`, `fill_monitor`, `safety_monitor`, `reconcile` の `last exit code=2`
   - Python例外ではなく、CLIが運用上の `BLOCK` / `SYSTEM_EMERGENCY_STOP` をプロセス失敗としてexit 2にしていた。
   - launchdのヘルスでは「scriptがartifactを書けたか」と「artifact内の運用status」を分離すべきだった。

2. Submit plistが `scripts/run_demo_submit.py` 固定
   - `run_demo_submit.py` 内部は共通Submitへ移っていたが、plist上は古いDemo名のscriptを呼んでいた。

3. artifact mtimeとlaunchd log時刻の不一致
   - 監査時点ではSubmit/Fill/Safety/Reconcile artifactがlaunchd log時刻ではなく後続手動/別実行時刻で更新されていた。

4. latest Submit artifactに共通Submit metadataがない
   - 古い `artifact_type=demo_submit` artifactが残っていた。

### 未完了

1. `daily_report` / notification artifactのlaunchd由来確認
   - `daily_report` jobは `--send-notifications` 付き。
   - kickstartは実通知送信を伴うため安全審査で拒否された。
   - そのためnotification artifactのlaunchd由来確認は未完了。

2. reports symlink先へのlaunchd書き込み確認
   - `daily_report` launchd実行が未完了のため、reports symlink先へlaunchdから書けることは今回確定できない。

## 2. 修正内容

### Submit共通入口

- `scripts/run_submit_operation.py` を追加。
- `tools/launchd/com.aifundlab.operations.demo_submit.plist` のProgramArgumentsを以下へ変更。

```text
/Users/negishi/work/ai-fund-lab-v2/scripts/run_submit_operation.py
```

- 既存 `scripts/run_demo_submit.py` は互換用に残したが、内部では `run_submit_operation()` を呼ぶ。
- 登録済みplist `~/Library/LaunchAgents/com.aifundlab.operations.demo_submit.plist` もrepo plistへ同期。
- `launchctl bootout` / `launchctl bootstrap` で `demo_submit` jobのみ再読込した。

### CLI exit code分離

以下のCLIを、artifactを書けた場合はexit 0にするよう修正した。

- `scripts/run_submit_operation.py`
- `scripts/run_demo_submit.py`
- `scripts/run_fill_monitor.py`
- `scripts/run_safety_monitor.py`
- `scripts/run_reconcile.py`

運用上のBLOCKはartifact内の `status` に残し、launchd process failureとは分離する。

### launchd由来metadata

`_base_payload()` に `invocation` を追加。

```json
{
  "source": "launchd",
  "xpc_service_name": "com.aifundlab.operations.<job>",
  "launchd_job_label": "com.aifundlab.operations.<job>",
  "pid": 1234
}
```

`operations/notifications.py` の `notification_result` にも同様の `invocation` metadataを追加した。

### Submit安全修正

manual_overrideなどのglobal blockがあるDemo Submitでは、item単位でも必ず `BLOCKED_ITEM` にし、Demo broker adapterへ進まないようにした。

確認結果:

- `approval_manual_override_detected=true`
- `blocks=["manual_override_approval_not_allowed_for_runtime_submit"]`
- `accepted_order_count=0`
- `broker_order_api_called=false`
- `production_order_submitted=false`

## 3. 変更ファイル

- `scripts/run_submit_operation.py`
- `scripts/run_demo_submit.py`
- `scripts/run_fill_monitor.py`
- `scripts/run_safety_monitor.py`
- `scripts/run_reconcile.py`
- `tools/launchd/com.aifundlab.operations.demo_submit.plist`
- `src/ai_fund_lab_v2/operations/operations.py`
- `src/ai_fund_lab_v2/operations/notifications.py`

前回Phase12.5修正からの関連変更もワークツリーに残っている。

## 4. repo plist / registered plist差分

全11件でrepo plistとregistered plistのSHA-256一致を確認した。

特に `demo_submit`:

```text
tools/launchd/com.aifundlab.operations.demo_submit.plist
~/Library/LaunchAgents/com.aifundlab.operations.demo_submit.plist
```

両方とも同一hash。

plist syntax:

```text
plutil -lint tools/launchd/*.plist
```

結果: 全plist OK

## 5. launchctl確認結果

launchctl再読込・起動確認を行ったjob:

- `com.aifundlab.operations.demo_submit`
- `com.aifundlab.operations.fill_monitor`
- `com.aifundlab.operations.safety_monitor`
- `com.aifundlab.operations.reconcile`

| Job | ProgramArguments | runs | last exit code | 判定 |
|---|---|---:|---|---|
| demo_submit | `scripts/run_submit_operation.py --root .runtime/operations --execute-demo-order --second-password-present` | 1 | 0 | PASS |
| fill_monitor | `scripts/run_fill_monitor.py --root .runtime/operations` | 3 | 0 | PASS |
| safety_monitor | `scripts/run_safety_monitor.py --root .runtime/operations` | 3 | 0 | PASS |
| reconcile | `scripts/run_reconcile.py --root .runtime/operations` | 3 | 0 | PASS |
| daily_report | `scripts/run_daily_report.py --root .runtime/operations --send-notifications` | 0 | never exited | REVIEW_REQUIRED |

`daily_report` は実通知送信を伴うためkickstart未実施。

## 6. artifact mtimeとログ時刻の対応

対象4jobはlaunchd log mtimeとartifact mtimeが一致した。

| Job | log mtime | artifact | artifact mtime | 対応 |
|---|---|---|---|---|
| demo_submit | 2026-07-02 21:48:46 +0900 | `submitted_orders/2026-07-02/submitted_orders.json` | 2026-07-02 21:48:46 +0900 | PASS |
| fill_monitor | 2026-07-02 21:48:55 +0900 | `fill_events/2026-07-02/fill_events.json` | 2026-07-02 21:48:55 +0900 | PASS |
| safety_monitor | 2026-07-02 21:48:55 +0900 | `safety_monitor/2026-07-02/safety_monitor_result.json` | 2026-07-02 21:48:55 +0900 | PASS |
| reconcile | 2026-07-02 21:48:55 +0900 | `reconciliation_result/2026-07-02/reconciliation_result.json` | 2026-07-02 21:48:55 +0900 | PASS |

stderrは対象4jobとも0 bytes。

## 7. Submit共通入口metadata確認

最新 `submitted_orders/2026-07-02/submitted_orders.json`:

```json
{
  "artifact_type": "submit_operation",
  "status": "BLOCK",
  "invocation": {
    "source": "launchd",
    "xpc_service_name": "com.aifundlab.operations.demo_submit",
    "launchd_job_label": "com.aifundlab.operations.demo_submit"
  },
  "runtime_submit_entry": "run_submit_operation",
  "executor_kind": "DemoOrderExecutor",
  "adapter_kind": "TachibanaDemoOrderAdapter",
  "approval_manual_override_detected": true,
  "broker_order_api_called": false,
  "production_order_submitted": false
}
```

manual_override guardにより、発注前に全itemが `BLOCKED_ITEM` になった。実API発注は行われていない。

## 8. notification artifact由来確認

修正内容:

- `notification_result` に `invocation` metadataを追加。
- `send_success_semantics`, `delivery_confirmation`, `report_source` は前回修正済み。

未確認:

- `daily_report` launchd kickstartは `--send-notifications` により実通知送信を伴うため、安全審査で拒否された。
- そのため、最新notification artifactで `invocation.source=launchd` を確認するところまでは未完了。

## 9. reports symlink確認

`.runtime/operations/reports` はiCloud配下へのsymlink。

```text
.runtime/operations/reports -> /Users/negishi/Library/Mobile Documents/com~apple~CloudDocs/AIFundLab/operations_reports
```

未確認:

- `daily_report` launchd kickstart未実施のため、launchdからsymlink先へ書けることは今回確定できない。

## 10. 実施検証

### plist syntax validation

```text
plutil -lint tools/launchd/*.plist
```

結果: PASS

### Python compile

```text
PYTHONPYCACHEPREFIX=/private/tmp/aifundlab_pycache python3 -m compileall -q src/ai_fund_lab_v2/operations scripts/run_submit_operation.py scripts/run_demo_submit.py scripts/run_fill_monitor.py scripts/run_safety_monitor.py scripts/run_reconcile.py
```

結果: PASS

### affected tests

```text
PYTHONPYCACHEPREFIX=/private/tmp/aifundlab_pycache python3 -m pytest tests/phase12/test_phase12_demo_submit_guard.py tests/phase12/test_phase12_5_production_equivalent_guards.py -q
```

結果: 15 passed

```text
PYTHONPYCACHEPREFIX=/private/tmp/aifundlab_pycache python3 -m pytest tests/phase12/test_phase12_5_production_equivalent_guards.py tests/phase12/test_phase12_demo_submit_guard.py tests/phase12/test_phase12_audit.py tests/phase12/test_operations_launchd.py tests/phase12/test_market_closed_safe_skip.py tests/phase12/test_operations_fill_monitor_states.py -q
```

結果: 25 passed

### JSON validation

対象artifact:

- `submitted_orders/2026-07-02/submitted_orders.json`
- `fill_events/2026-07-02/fill_events.json`
- `safety_monitor/2026-07-02/safety_monitor_result.json`
- `reconciliation_result/2026-07-02/reconciliation_result.json`

結果: PASS

### secret canary

実secret出力は検出されていない。コード上の `Bearer {token}` テンプレートや環境変数名はsecret値ではない。

## 11. 残課題

1. `daily_report` launchd経由確認
   - 実通知送信を伴うため、明示承認が必要。

2. notification artifactのlaunchd由来確認
   - `daily_report` launchd実行後に `invocation.source=launchd` を確認する。

3. reports symlink先へのlaunchd書き込み確認
   - `daily_report` launchd実行後にreport artifact mtimeとlog mtimeを照合する。

4. latest Approvalのmanual_override
   - Submitは安全にBLOCKするようになったが、Approval artifact自体は `manual_override / 600000` のまま。

## 12. 禁止事項遵守

今回、以下は行っていない。

- Production接続
- Production注文
- 実API発注
- artifact削除
- secret出力
- フルバックテスト
- AI再学習

実施したlaunchctl操作:

- `demo_submit` のplist再読込のための `bootout` / `bootstrap`
- `demo_submit`, `fill_monitor`, `safety_monitor`, `reconcile` の `kickstart`

