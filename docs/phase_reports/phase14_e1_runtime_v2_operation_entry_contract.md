# Phase14-E1 Runtime v2 Operation Entry Contract

作成日: 2026-07-07

## 最終判定

**PHASE14E1_OPERATION_ENTRY_CONTRACT_COMPLETE**

Phase14-D25で、Runtime Core Blockerは0件である一方、launchd前にOperation Designが必要であることを確認した。

本資料では、Runtime v2の日次運用で呼び出してよい正規入口を固定する。手動実行、dry-run、Demo運用、Simulation、将来のlaunchd運用は、すべて同じRuntime v2正規entryを通る。検証用script、Phase14-D系script、旧Runtime、Phase9 daily runtime、Phase9 blog writerは日次運用entryにしない。

今回は設計のみであり、コード変更、Broker API呼び出し、Submit、Notification送信、launchd/plist変更、Current SoT追加writeは行っていない。

## 背景と前提

D23/D25の整理:

- Manual Demo OperationはREADY。
- Runtime v2 Core ContractはMOSTLY READY。
- launchdはNOT READY。
- ProductionはNOT READY。
- D25でRuntime Core Blockerは0件。
- launchd前の最初のOperation DesignはRuntime v2正規entryの固定である。

D21/D22のCurrent SoT前提:

```text
.runtime/persistent_ledger/state.json
.runtime/persistent_ledger/orders.jsonl
.runtime/persistent_ledger/executions.jsonl
.runtime/persistent_ledger/positions.jsonl
.runtime/persistent_ledger/cash.jsonl
.runtime/persistent_ledger/events.jsonl
.runtime/pending_order_plan/pending_order_plan.json
.runtime/runtime_state/current_state.json
.runtime/notification_delivery/delivery_ledger.jsonl
```

Currentは上記固定Pathのみであり、phase番号配下、`.runtime/demo/...`、`.runtime/production/...`、`.runtime/simulation/...`、`.runtime/backtest/...` をCurrent扱いしない。

## 正規CLI Entry

設計上の正規entry名:

```text
python -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation
```

このentryは、Runtime v2 Orchestratorを呼び出す唯一のOperation Entryである。

責務:

- runtime mode、business date、submit可否、notification mode、dry-run/preflight条件を受け取る。
- Runtime v2 Current State Readerで固定Current Pathを読む。
- Runtime v2 Orchestratorにrun requestを渡す。
- Runtime State Machineに従い、`REVIEW_REQUIRED`、`BLOCKED`、`HALT`で停止する。
- Submit-enabledの場合でも、Submit Runtimeへ進む前にpending-only、approval、duplicate、environment、Safety/Operation guardを確認する。
- Report / Notification payload / AuditをDerived / Evidenceとして生成する。
- Exit codeを運用状態と対応させる。

やらないこと:

- AI判断ロジックを実装しない。
- 旧Runtime entrypointを呼ばない。
- Phase9 daily runtimeを呼ばない。
- Phase9 blog writerを直接呼ばない。
- Legacy `OrderCommand` / `RuntimeMode`をSubmit authorityにしない。
- phase番号配下artifactをCurrentとして読まない。
- `.runtime/demo/...` などmode-rooted Currentを読まない。
- Report / Blog / AuditをSubmit sourceにしない。

## CLI引数案

| Argument | Values | Default | 意味 |
| --- | --- | --- | --- |
| `--mode` | `demo`, `simulation`, `production` | 必須 | runtime mode。path分岐ではなくadapter/config/metadataを選ぶ |
| `--business-date` | `YYYY-MM-DD` | system calendar resolved date | 対象business date |
| `--submit-enabled` | `true`, `false` | `false` | Broker Submit外部副作用を許可するか |
| `--notification-mode` | `payload-only`, `send-disabled`, `send-enabled` | `payload-only` | 通知payload生成と実送信の扱い |
| `--dry-run` | flag | false | Current writeと外部副作用を行わず、実行計画とguard結果だけ生成 |
| `--preflight-only` | flag | false | Submit/Notification直前までのguard確認で停止 |
| `--max-orders` | integer | mode policy | 1 runでSubmit可能な最大注文数 |
| `--require-manual-approval` | flag | true for demo/production submit | approval artifactとpending hash一致を必須化 |
| `--stop-on-review-required` | flag | true | `REVIEW_REQUIRED`検出時に先へ進まない |
| `--stop-on-blocked` | flag | true | `BLOCKED`検出時に先へ進まない |
| `--read-only-broker-sync` | flag | false | SubmitせずBroker ReadOnly同期だけ許可する |
| `--report-enabled` | `true`, `false` | true | Report artifact生成可否 |
| `--audit-enabled` | `true`, `false` | true | Audit生成可否 |

禁止する引数思想:

- `--root .runtime/demo` のようにCurrent rootをmodeで切る指定。
- `--order-plan-path order_plan/YYYY-MM-DD/...` のようにSubmit sourceを直接指定する指定。
- `--approval-artifact-path approval_artifact/YYYY-MM-DD/...` のようにHistoryからSubmit対象を選ぶ指定。
- `--phase-artifact-as-current` のようにper-run artifactをCurrent扱いする指定。

## 実行モード別Contract

| Mode | Entry | Submit | Broker API | Current write | Notification | 用途 |
| --- | --- | --- | --- | --- | --- | --- |
| manual demo dry-run | 正規CLI | 禁止 | 禁止またはReadOnlyのみ | 原則なし | payload-only | 手動確認、guard確認 |
| manual demo preflight | 正規CLI | 禁止 | ReadOnly可 | 原則なし | payload-only | Demo Submit直前確認 |
| manual demo submit-enabled | 正規CLI | Demoのみ可 | Demo Submit / ReadOnly可 | fixed Currentのみ | payload-only | 手動Demo運用 |
| manual simulation | 正規CLI | simulated submitのみ | 実Broker禁止 | simulation run artifact。Production/Demo Currentへ混入禁止 | payload-only | Simulation Harness |
| launchd demo initial | 正規CLI | 初期はfalse推奨。許可時は明示Acceptance後 | ReadOnly可、Demo Submitは別Acceptance後 | fixed Currentのみ | payload-only | 日次自動リハーサル |
| future production | 正規CLI | 別Production Acceptance後のみ | Production ReadOnly/Submitは明示承認後 | fixed Currentのみ | payload-onlyまたはsend-enabled | 将来本番 |

## Submit-enabled / Submit-disabled

### submit-disabled

`--submit-enabled false` は初期defaultである。

許可:

- Market Refresh
- Feature Refresh
- Current State Read
- AI inference
- Planning
- Approval prepare/link check
- Pending state read
- Submit preflight
- Broker ReadOnly sync
- Execution Reflection from existing Broker evidence
- Ledger / Asset update if evidence policy permits
- Reconcile
- Report
- Notification payload
- Audit

禁止:

- Broker Submit
- Demo Submit
- Production Submit
- Submit attempt event as actual external send

### submit-enabled

`--submit-enabled true` は外部副作用を許可する危険モードであり、以下を満たす場合のみ許可する。

- `--mode demo` かつDemo Submit Acceptance済み、または将来Production Acceptance済み。
- Submit sourceは `.runtime/pending_order_plan/pending_order_plan.json` のみ。
- Pending stateは `APPROVED`。
- Approval artifact hashとpending plan hashが一致。
- Duplicate submit guard PASS。
- `CONSUMED` pendingではない。
- `POST_SEND_UNKNOWN`後の自動再送ではない。
- Safety / Operation GuardがALLOW。
- `--max-orders` を超えない。
- Production注文は禁止継続。Production submit-enabledは別フェーズで明示解除されるまでBLOCK。

## Notification Mode

初期launchd方針は **payload-only** とする。

| Mode | 意味 | 外部送信 | Delivery Ledger |
| --- | --- | --- | --- |
| `payload-only` | payload生成のみ。送信しない | なし | read/write不要またはdry ledgerのみ |
| `send-disabled` | 送信処理を明示無効化。payloadも必要に応じて生成 | なし | readのみ可 |
| `send-enabled` | Delivery Ledger guard後に外部通知送信 | あり | 必須 |

`send-enabled` はNotification Send / Ack Contract、Delivery Ledger test、二重送信防止、失敗時の`POST_SEND_UNKNOWN`相当分類が完了するまでlaunchd初期運用では使わない。

## Stop Behavior

| Runtime result | Behavior | Exit code |
| --- | --- | --- |
| `SUCCESS` / `REPORT_READY` | 正常終了 | 0 |
| `BLOCKED` | 先へ進まず停止。Submit/Notification Send禁止 | 10 |
| `REVIEW_REQUIRED` | 先へ進まず停止。ReadOnly/Report/Auditのみ可 | 20 |
| `HALT` | 継続不可。manual recoveryのみ | 30 |
| config/env error | mode/env/credential/endpoint不整合 | 40 |
| broker readonly failure | ReadOnly取得失敗。Submitへ進まない | 50 |
| submit blocked | submit-enabledでもguardでSubmit禁止 | 60 |
| unexpected error | 未分類例外。`HALT`相当で扱う | 70 |

launchdでは、exit codeをプロセス失敗だけでなく運用状態として扱う。`BLOCKED` / `REVIEW_REQUIRED` は事故ではなく安全停止である。ただし、launchd再実行で自動的にSubmitへ進んではならない。

## Log出力先

正規entryの標準ログ方針:

```text
.runtime/runtime_state/logs/YYYY-MM-DD/run_<run_id>.log
.runtime/runtime_state/run_manifest/YYYY-MM-DD/run_<run_id>.json
.runtime/persistent_ledger/events.jsonl
```

LogはHistory / Evidenceであり、Current SoTではない。

禁止:

- secret、raw request、raw response、plain broker idsをlogへ保存しない。
- logからCurrentを復元しない。
- phase番号配下logを日次運用Currentとして扱わない。

## Report出力先

Runtime v2 ReportはDerivedである。

標準出力先案:

```text
reports/runtime_v2/YYYY-MM-DD/runtime_report.json
reports/runtime_v2/YYYY-MM-DD/runtime_report.md
reports/runtime_v2/YYYY-MM-DD/notification_payload.json
reports/runtime_v2/YYYY-MM-DD/audit_result.json
reports/public/YYYY-MM-DD/public_report.md
```

`.runtime/phase14d*/...` はphase検証用のHistory / Evidence / per-run artifactであり、正規日次運用のCurrentではない。

Report、Blog、Audit、Notification PayloadはSubmit sourceではない。

## Current SoT Read / Write Conditions

Read:

- 正規entryはCurrent State Reader経由で固定Pathのみを読む。
- Current欠損、不明、stale、source不明の場合は、保有0や現金0として扱わず、`BLOCKED`または`REVIEW_REQUIRED`へ止める。

Write:

- `--dry-run` と `--preflight-only` ではCurrent writeしない。
- Current writeは各Single Writerだけが行う。
- Reconcile / Report / AuditはCurrent writerではない。
- Submit-enabled時も、Broker Submit前にCurrent writeでSubmit済みに見せない。
- Execution / Position / Cash evidenceが揃った後だけAsset Currentを更新する。

## 正規Entry以外の禁止一覧

日次運用entryとして禁止:

- `scripts/run_phase14d*.py`
- `scripts/run_phase14e*.py` のようなphase検証script
- 旧Phase9 daily runtime entry
- Phase9 blog writer direct call
- 旧launchd plist
- 旧Runtime entrypoint
- Legacy Order Manager
- `ai_fund_lab_v2.runtime.order_command.OrderCommand`
- 旧 `RuntimeMode` をSubmit authorityとして使う経路
- `order_plan/YYYY-MM-DD` から直接Submitする経路
- `approval_artifact/YYYY-MM-DD` から直接Submitする経路
- Report / Blog / AuditからSubmit対象を推測する経路

phase検証scriptは、必要な場合でも正規entryのwrapperまたはtest harnessとしてのみ許可し、日次運用の本線入口にしない。

## launchd接続前条件

launchd/plistへ接続する前に、以下を完了条件とする。

1. Current SoT write/read-backがD22同等にPASS。
2. Runtime v2 Operation Entry Contract実装とCLI test PASS。
3. Safety Integration Design完了。
4. Safety gateがPlanning / Approval / Submit前に接続済み。
5. Recovery / Restart Matrix完了。
6. Manual Intervention Runbook完了。
7. External Broker Action Sync Runbook完了。
8. Position Drift Classification完了。
9. Business Day / Carryover設計完了。
10. Demo Operation Runbook完了。
11. Notification初期方針をpayload-onlyに固定、またはsend-enabledのDelivery Ledger Acceptance完了。
12. launchdは旧plistを継承せず、Runtime v2正規CLIだけを呼ぶ新規設計にする。

## Future launchd Entry

launchdが呼ぶべき形:

```text
python -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --submit-enabled false \
  --notification-mode payload-only \
  --business-date auto \
  --require-manual-approval \
  --stop-on-review-required \
  --stop-on-blocked
```

初期launchdではsubmit-disabledを原則とする。Demo Submitをlaunchdで許可する場合は、別Acceptanceで`--submit-enabled true`、`--max-orders`、approval、duplicate、Safety、Recovery、Business Day guardを確認する。

Production launchdは本資料の対象外であり、Production Readiness / Pilot Contract完了まで禁止する。

## Phase14-E2以降への引き継ぎ

推奨順序:

1. **Phase14-E2: Safety Runtime Integration Design**
   - Safety結果をPlanning / Approval / Submit / Operation Guardにどう接続するか決める。

2. **Phase14-E3: Restart / Recovery Matrix**
   - `BLOCKED`、`REVIEW_REQUIRED`、`POST_SEND_UNKNOWN`、途中停止からの再開条件を表にする。

3. **Phase14-E4: Manual Intervention / External Broker Action Runbook**
   - Broker画面手動操作、外部取消、手動入出金、手動補正の記録と同期を定義する。

4. **Phase14-E5: Business Day / Carryover Contract**
   - holiday、翌営業日、unfilled carry、pending expiryを定義する。

5. **Phase14-E6: Runtime v2 CLI Skeleton**
   - 本Contractに沿った最小CLI実装とimport guard testを行う。

6. **Phase14-E7: launchd Demo Dry-run Design**
   - submit-disabled / payload-onlyでlaunchd接続設計を行う。

## Acceptance Criteria

| Criteria | 判定 |
| --- | --- |
| Runtime v2正規entryが定義されている | PASS |
| manual / dry-run / demo / simulation / launchd の関係が定義されている | PASS |
| submit-enabled / submit-disabled が明確 | PASS |
| notification初期方針がpayload-onlyで明確 | PASS |
| exit codeが定義されている | PASS |
| 旧Runtime / Phase9 / run_phase14d scriptsを正規entryにしないと明記 | PASS |
| launchd接続前条件が明記されている | PASS |
| コード変更していない | PASS |
| Broker API呼び出ししていない | PASS |
| Submitしていない | PASS |
| Notification送信していない | PASS |
| launchd/plist変更していない | PASS |

## 結論

Runtime v2の日次運用正規entryは、`python -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation` として設計固定する。

手動運用、dry-run、Demo、Simulation、将来launchdはこのentryを共有し、mode、submit-enabled、notification-mode、dry-run/preflightで挙動を分ける。

したがって最終判定は **PHASE14E1_OPERATION_ENTRY_CONTRACT_COMPLETE** とする。
