# Phase14-E17 Runtime v2 Submit Pipeline Connection Fix

作成日: 2026-07-08

## 最終判定

**PHASE14E17_SUBMIT_PIPELINE_CONNECTED**

補足: Runtime v2 Submit pipelineの接続は完了した。一方、実Demo Broker responseは5件すべて `REJECTED_OR_UNKNOWN` だったため、運用状態としては `REVIEW_REQUIRED` で停止している。追加Submitは行わない。

## 背景

Day1 Demo運用でMorning Jobは成功し、以下のPendingが生成済みだった。

- Pending state: `APPROVED`
- target_session_date: `2026-07-08`
- items: 5
- symbols: `65220`, `78780`, `68970`, `63270`, `45910`
- each quantity: 100
- total estimated_amount: 500,000
- approval linked
- consumed: false
- 9000番台なし

一方、Submit Jobは起動していたが、manifestでは以下のCHECKPOINT-only状態だった。

```text
Open Demo Submit checkpoint recorded; broker write is disabled in rehearsal.
demo_submit_executed=false
submitted_order_ids=[]
ledger_order_record_ids=[]
consume.consumed=false
```

これはDay1 Demo運用のBlockerだった。

## 実装内容

### 1. Runtime v2 Submit Pipeline追加

追加:

- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`

責務:

- fixed Current Path の `.runtime/pending_order_plan/pending_order_plan.json` を読む
- `state=APPROVED` を要求
- `target_session_date == business_date` を要求
- Pending内のapproval linkをApproval Artifact相当へ復元
- approval hash / approved_item_ids / items整合を確認
- consumed / submitted / post_send_unknown / blocked / review_required系PendingをBLOCK
- `submit-enabled=true` かつ `job=submit` のみSubmit許可
- Demo Capability guardを適用
- Demoでは9000番台をBLOCK
- approved Pending全件をSubmit対象にする
- RuntimeV2SubmitCommandを生成
- Demo Submit adapterへ渡す
- Broker responseを `ACCEPTED` / `REJECTED_OR_UNKNOWN` / `POST_SEND_UNKNOWN` / `BLOCKED` 系に分類
- manifest detailsへ件数とitem resultを記録
- Ledger ordersへsanitized recordを追記
- PendingをCONSUMEDへ更新し、再Submitを禁止

### 2. Runtime v2 CLI接続

更新:

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`

接続:

- `--job submit --submit-enabled true` の場合だけ `run_submit_pipeline(...)` を実行
- `--submit-enabled false` のsubmit jobは `DISABLED` stageとして記録
- Submit pipeline stageをmanifestへ出力
- `demo_submit_executed` を実Submit結果から反映
- Submit結果が `BLOCKED` なら exit code 10
- Submit結果が `REVIEW_REQUIRED` なら exit code 20

### 3. Fake Adapter Preflight追加

更新:

- `src/ai_fund_lab_v2/runtime_v2/broker_adapter/fake_demo_submit.py`

目的:

- Runtime v2 Submit pipelineのunit/integration testで、Broker APIを呼ばずにpreflight/submit境界を検証する。

### 4. Legacy Isolation維持

Runtime v2配下から `ai_fund_lab_v2.broker.*` を静的importしない契約を維持した。

実Tachibana adapter/settingsはSubmit adapter boundaryとして遅延ロードし、Phase13-X Legacy Runtime Isolation GuardをPASSしている。

## Unit / Integration Tests

追加:

- `tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py`

確認:

- approved Pending 5件が全件Submit対象になる
- Fake adapterで5件全件submitted/accepted扱いになる
- PendingがCONSUMEDになる
- submitted_order_idsが5件記録される
- ledger_order_record_idsが5件記録される
- Ledger ordersが5件追加される
- Demo 9000番台はSubmit前にBLOCKされる
- Production capabilityでは9000番台をBLOCKしない
- CLI manifestに `runtime_v2_submit_pipeline` stageが出る
- `demo_submit_executed=true` がmanifestへ反映される

実行:

```text
python3 -m pytest tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py
4 passed
```

全体:

```text
python3 -m pytest tests/runtime_v2
318 passed
```

## Real Demo Submit Result

実行前確認:

- environment: `demo`
- base_url: `https://demo-kabuka.e-shiten.jp/e_api_v4r9`
- Pending state: `APPROVED`
- Pending target_session_date: `2026-07-08`
- Pending items: 5
- Approval linked: yes
- consumed: false
- 9000番台Pending: none

### Sandbox実行

最初のsandbox内実行は5件とも `PRE_SEND_FAILURE / BrokerTransportError` でBLOCKした。

- demo_submit_executed: false
- submitted_count: 0
- Pending consumed: false
- Ledger orders: 0
- raw request/response/secret saved: false

ネットワーク制限由来の可能性があったため、同じRuntime v2 Submit Jobを1回だけ権限昇格で再実行した。

### Unsandboxed Demo Submit

実行:

```text
PYTHONPATH=/Users/negishi/work/ai-fund-lab-v2/src \
TACHIBANA_API_ENV=demo \
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job submit \
  --business-date 2026-07-08 \
  --submit-enabled true \
  --notification-mode payload-only \
  --stop-on-review-required \
  --stop-on-blocked \
  --runtime-root .runtime \
  --reports-root reports/runtime_v2 \
  --public-reports-root reports/public/runtime_v2 \
  --manifest-root .runtime/runtime_state/run_manifest \
  --log-root .runtime/runtime_state/logs
```

結果:

- exit_code: 20
- final_state: `REVIEW_REQUIRED`
- manifest: `.runtime/runtime_state/run_manifest/2026-07-08/runtime-v2-submit-2026-07-08-20260708T053642.093652+0000.json`
- demo_submit_executed: true
- submitted_count: 5
- accepted_count: 0
- rejected_count: 5
- unknown_count: 0
- blocked_count: 0
- pending_consumed: true
- submitted_symbols: `65220`, `78780`, `68970`, `63270`, `45910`
- Broker response classification: all `REJECTED_OR_UNKNOWN`

## Current Artifacts After Submit

Pending:

- path: `.runtime/pending_order_plan/pending_order_plan.json`
- state: `CONSUMED`
- consume_reason: `runtime_v2 submit attempted with partial failure; automatic resubmit forbidden`
- submitted_order_ids: 5
- ledger_order_record_ids: 5
- raw_request_saved: false
- raw_response_saved: false
- secret_saved: false

Ledger:

- path: `.runtime/persistent_ledger/orders.jsonl`
- records: 5
- source: `runtime_v2_submit_pipeline`
- status: all `REJECTED_OR_UNKNOWN`
- review_required: true

Report:

- `reports/runtime_v2/2026-07-08/runtime_report.json`
- `reports/runtime_v2/2026-07-08/runtime_report.md`
- `reports/public/runtime_v2/2026-07-08/public_report.md`
- `reports/public/runtime_v2/latest.md`

Runtime reportには5件のorder statusとPending `CONSUMED` が反映されている。

## Safety / Prohibited Actions

- Production注文: なし
- Production Broker API Write: なし
- Notification実送信: なし
- launchd load/unload/bootstrap: なし
- Phase9 Runtime呼び出し: なし
- Phase9 writer呼び出し: なし
- `.runtime/demo` Current path復活: なし
- phase artifact Current扱い: なし
- raw request保存: なし
- raw response保存: なし
- secret保存: なし
- 追加再Submit: なし

## Acceptance

| Criteria | Result |
| --- | --- |
| Submit JobがCHECKPOINT-onlyでない | PASS |
| submit-enabled=true + job=submit でSubmit pipelineが走る | PASS |
| Morning生成済みPending 5件が通常ロジックでSubmit対象になる | PASS |
| 5件全件を送信対象にする | PASS |
| Demo Broker responseが記録される | PASS |
| submitted_order_idsが記録される | PASS |
| ledger_order_record_idsが記録される | PASS |
| Ledger ordersが追加される | PASS |
| manifestにdemo_submit_executed=true | PASS |
| submitted/accepted/rejected/unknown/blocked count記録 | PASS |
| 9000番台Demo BLOCKがSubmit前にも効く | PASS |
| Productionでは9000番台をBLOCKしない | PASS |
| Runtime評価資金100万円基準 | PASS |
| raw request / raw response / secret保存なし | PASS |
| Production注文なし | PASS |
| Notification実送信なし | PASS |
| Phase9未使用 | PASS |
| tests/runtime_v2 PASS | PASS |

## Next Review

Broker側の5件結果が `REJECTED_OR_UNKNOWN` だったため、次フェーズではBroker response normalizerまたはデモ注文仕様の確認が必要である。

ただし、E17の主目的である「Submit JobをPending CurrentからDemo Broker Submitへ接続する」ことは完了した。
