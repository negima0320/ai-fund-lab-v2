# Phase13-E Runtime v2 Implementation / Migration Plan

作成日: 2026-07-07

判定: DESIGN_ONLY

## 1. 目的

Runtime Architecture v2 を実装する前に、実装順序と移行順序を固定する。

本計画で整理すること:

- 何から実装するか
- 既存 Runtime をどこから切り離すか
- どの Current State を最初に固定するか
- 既存 artifact をどう扱うか
- `demo_ledger` をどう legacy 化するか
- どの段階で Acceptance Test を置くか
- どの段階まで Submit / Broker 注文 / `launchd` を禁止するか

Phase13-E は実装計画と移行計画の作成のみである。実装変更、Submit、Broker 注文、Demo 注文、Production 注文、通知送信、`launchd` 再開は行わない。

既存の `plist` / `launchd` 設定は Runtime v2 の正規構成として継承しない。既存 plist は legacy 保持対象ではない。Runtime v2 の `launchd` / scheduler 設定は、Acceptance Test と Manual Rehearsal 完了後に新規作成する。Phase13-E では plist 削除・新規 plist 作成・`launchd` 再開は行わない。実際の plist 削除や新規作成は、後続の明示フェーズで行う。

## 2. 前提

Phase13-E でも、既存 Runtime 制御を v2 の正規フローとして継承しない。

既存コードや既存 artifact は以下の目的でのみ参照する。

```text
既存問題の確認
移行対象の把握
legacy 化対象の把握
破壊してはいけない artifact の確認
```

以下の目的では使わない。

```text
新 Runtime の正規フローの根拠
Current State の決定方法
Submit 対象の選び方
約定後の保有確定方法
Report / Audit の Current 判定方法
```

Runtime v2 の実装は、次の固定原則から始める。

- Runtime Current は Phase 単位・日付単位ではなく、役割ごとの固定 Path で管理する。
- `pending_order_plan/pending_order_plan.json` だけを Submit 対象にする。
- `persistent_ledger/state.json` を現在保有、現金、買付余力、総資産の中心にする。
- `submitted_orders` と `broker_orders` は現在保有 SoT ではない。
- 約定して初めて保有になる。
- Report は Derived であり、Runtime Current 入力ではない。
- Notification Send は Delivery Ledger で二重送信を防ぐ。

## 3. 実装サブフェーズ概要

| Phase ID | Name | Primary Goal | Submit / Broker Order |
| --- | --- | --- | --- |
| Phase13-F | Current State Contract 固定 | Current State の固定 Path、schema、読み取り rule を contract 化する | 禁止 |
| Phase13-G | Runtime State Machine / Orchestrator Skeleton | Runtime State Machine と Orchestrator の骨格を作る | 禁止 |
| Phase13-H | Persistent Ledger Mainline 接続 | Persistent Ledger を Runtime 本線の Current State に接続する | 禁止 |
| Phase13-I | Pending Order Plan Lifecycle / Consume | Pending lifecycle と consume を完成させる | 禁止 |
| Phase13-J | Broker ReadOnly Ingestion / Execution Pipeline | Broker ReadOnly を Ledger / Asset に安全に取り込む | 禁止 |
| Phase13-K | Report / Notification / Audit Rewire | Report / Notification / Audit を Current State 中心に再配線する | 禁止 |
| Phase13-L | Legacy Runtime Isolation / demo_ledger Legacy 化 | 既存 Runtime と `demo_ledger` を v2 本線から隔離する | 禁止 |
| Phase13-M | Acceptance Test / Manual Rehearsal | 受け入れテストと手動リハーサルを行う | 原則禁止。必要時も Demo 限定かつ明示承認 |

Production 注文は全サブフェーズで禁止する。

## 4. サブフェーズ詳細

| Phase ID | 目的 | 対象 Component | 対象 Current State | 変更対象コード候補 | 作成/更新する設計書 | 作成/更新するテスト | 禁止事項 | 完了条件 | 次フェーズへ進む条件 | Rollback / Recovery 方針 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Phase13-F | Runtime Current の固定 Path、schema、読み取りルール、欠損時の扱いをコード上の contract として固定する | Current State Runtime, Runtime State Machine Runtime, Audit Runtime | `persistent_ledger/state.json`, `pending_order_plan/pending_order_plan.json`, `runtime_state/current_state.json`, `notification_delivery/delivery_ledger.jsonl` | current state reader, schema validator, path resolver, audit checks | Current State contract document, schema / validation policy | Current State fixed path test, no date-based Current resolution test, no phase-based Current resolution test | Submit 禁止, Broker 注文禁止, Demo 注文禁止, Production 注文禁止, `launchd` 再開禁止 | fixed path contract と unknown flags が定義され、欠損時に BUY / Approval / Submit を block できる | Contract tests PASS。日付別 / Phase 別 Current resolution が失敗する | 実装前 state に戻す。artifact は削除しない。contract 変更は design review に戻す |
| Phase13-G | Runtime State Machine と Runtime Orchestrator の骨格を作る | Runtime Orchestrator, Runtime State Machine Runtime, Operation Guard Runtime | `runtime_state/current_state.json`, `persistent_ledger/events.jsonl` | orchestrator skeleton, state transition validator, run_id / runtime_id manager | State Machine transition design update | State Machine transition test, BLOCKED / REVIEW_REQUIRED / HALT transition test | Submit 禁止, Broker 注文禁止, Notification Send 禁止, `launchd` 再開禁止 | allowed transition と invalid transition が定義され、外部副作用なしで dry-run 可能 | State transition tests PASS。既存 Runtime flow を参照根拠にしていない | Orchestrator entrypoint を disabled に戻す。state file は migration record 付きで補正 |
| Phase13-H | Persistent Ledger を Runtime 本線の Current State として接続する | Ledger Runtime, Asset Runtime, Planning Runtime, Approval Runtime, Report Runtime, Reconcile Runtime, Audit Runtime | `persistent_ledger/state.json`, `persistent_ledger/orders.jsonl`, `persistent_ledger/executions.jsonl`, `persistent_ledger/positions.jsonl`, `persistent_ledger/cash_history.jsonl`, `persistent_ledger/events.jsonl` | ledger reader adapter, asset state adapter, planning / approval / report input adapter | Persistent Ledger mainline connection design | Current State unknown blocks BUY / Approval / Submit test, order is not asset test | Submit 禁止, Broker 注文禁止, `demo_ledger` 新規 SoT 化禁止 | Daily Plan / Approval / Report / Reconcile / Audit が Ledger Current を読む計画が確定 | ledger state tests PASS。保有 unknown を 0 と扱わない | adapter を feature flag で off。ledger records は削除せず migration event で補正 |
| Phase13-I | Pending Order Plan の lifecycle を完成させる | Planning Runtime, Approval Runtime, Submit Runtime, Runtime State Machine Runtime, Audit Runtime | `pending_order_plan/pending_order_plan.json`, `persistent_ledger/orders.jsonl`, `persistent_ledger/events.jsonl` | pending lifecycle validator, consume writer, submit preflight guard | Pending lifecycle / consume design update | Pending-only Submit source test, consumed pending cannot resubmit test, POST_SEND_UNKNOWN no auto-resend test | Submit 実行禁止, Broker 注文禁止, Production 注文禁止 | `APPROVED`, `SUBMITTING`, `SUBMITTED`, `CONSUMED`, `EXPIRED`, `BLOCKED`, `REVIEW_REQUIRED`, `POST_SEND_UNKNOWN` が定義・検証される | lifecycle tests PASS。`order_plan/YYYY-MM-DD` fallback が禁止される | pending state を直接巻き戻さない。新しい pending_plan_id と review evidence で補正 |
| Phase13-J | Broker ReadOnly 結果を Persistent Ledger へ安全に取り込む | Broker Runtime, Execution / Fill Runtime, Ledger Runtime, Asset Runtime, Reconcile Runtime | `persistent_ledger/orders.jsonl`, `persistent_ledger/executions.jsonl`, `persistent_ledger/positions.jsonl`, `persistent_ledger/cash_history.jsonl`, `persistent_ledger/state.json` | broker readonly adapter, execution ingestion, position ingestion, cash ingestion, dedup policy | Broker ReadOnly ingestion / execution pipeline design | Execution creates position test, position + cash creates asset state test, production broker_orders fallback prohibition test, demo fallback review flag test | Broker Order Submit 禁止, Production 注文禁止, Demo 注文禁止 | ReadOnly ingestion で注文・約定・保有・資産が分離される | ingestion tests PASS。Production fallback prohibition PASS | ingestion records は dedup key と correction event で補正。破壊的削除禁止 |
| Phase13-K | Report / Notification / Audit を Current State 中心へ再配線する | Report Runtime, Notification Runtime, Audit Runtime, Reconcile Runtime | `persistent_ledger/state.json`, `pending_order_plan/pending_order_plan.json`, `notification_delivery/delivery_ledger.jsonl`, `persistent_ledger/events.jsonl` | report input adapter, notification payload generator, delivery ledger writer, audit guard | Report / Notification / Audit rewire design | Report derived-only test, notification delivery dedup test | Notification Send 禁止, Submit 禁止, Broker 注文禁止 | Report が Current State から生成され、Report 自体を Current 入力にしない | Report / notification / audit tests PASS | generated report / payload は再生成可能。送信 ledger は削除せず correction event で扱う |
| Phase13-L | 既存 Runtime 制御と `demo_ledger` を v2 本線から切り離す | Runtime Orchestrator, Migration Runtime, Ledger Runtime, Report Runtime, Audit Runtime | `persistent_ledger/*`, `runtime_state/current_state.json`, legacy artifact references | legacy resolver isolation, `demo_ledger` write stop, migration inventory, compatibility shim | Legacy isolation / demo_ledger legacy plan | Legacy runtime not used as v2 source test, no date-based resolver test | 破壊的 cleanup 禁止, artifact 削除禁止, Submit 禁止, Broker 注文禁止 | legacy resolver が v2 Current 決定元から外れ、`demo_ledger` が本線 SoT でなくなる | isolation tests PASS。破壊してはいけない artifact inventory 完了 | isolation flag を off。既存 artifact は削除しない。migration proposal に戻す |
| Phase13-M | Runtime v2 の受け入れテストと手動リハーサルを行う | All Runtime Components | All Runtime Current State | acceptance runner, manual rehearsal scripts / docs, production prohibition audit | Acceptance test plan, manual rehearsal runbook | 全 Acceptance Test、Manual Rehearsal、Production order prohibition audit | Production 注文禁止。Submit / Broker 注文は最後まで原則禁止。必要な場合も Demo 限定かつ明示承認後 | Acceptance Test PASS, Manual Rehearsal PASS, launchd 再開判定可能 | launchd 再開条件をすべて満たす。Production order prohibition audit PASS | 失敗時は該当サブフェーズへ戻す。自動再送・破壊的削除は禁止 |

## 5. 移行対象 artifact 分類

| Artifact | Current に昇格 | History / Evidence | Derived | legacy 隔離 | 破壊的削除禁止 | migration 候補 | 方針 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `order_plan/YYYY-MM-DD` | しない | はい | いいえ | いいえ | はい | 必要時のみ pending promotion evidence | Submit 対象にしない。History / Evidence として hash / link 表示に使う |
| `approval_artifact/YYYY-MM-DD` | しない | はい | いいえ | いいえ | はい | approval linkage evidence | Current 承認状態ではない。pending approval linkage の evidence として扱う |
| `submitted_orders/YYYY-MM-DD` | しない | はい | いいえ | legacy 参照あり | はい | `persistent_ledger/orders.jsonl` への migration 候補 | 注文履歴であり、現在保有 SoT ではない |
| `broker_orders/YYYY-MM-DD` | しない | はい | いいえ | いいえ | はい | orders ingestion / Demo fallback evidence | Production では現在保有確定に使わない。Demo fallback は review flags 必須 |
| `broker_executions/YYYY-MM-DD` | 直接昇格しない | はい | いいえ | いいえ | はい | `persistent_ledger/executions.jsonl` / positions update | 約定確定の正規根拠。Ledger ingestion 後に Current へ反映 |
| `broker_positions/YYYY-MM-DD` | 直接昇格しない | はい | いいえ | いいえ | はい | `persistent_ledger/positions.jsonl` | 保有確定の正規根拠。Ledger ingestion 後に Current へ反映 |
| `ledger/YYYY-MM-DD` | しない | はい | いいえ | legacy | はい | Persistent Ledger migration 候補 | v2 本線 SoT ではない。差分確認と migration evidence に限定 |
| `demo_ledger` | しない | 必要に応じて | いいえ | はい | はい | `persistent_ledger` migration 候補 | 新規書き込み停止を目指す。削除ではなく legacy isolation |
| `reports/YYYY-MM-DD` | しない | evidence link 可 | はい | いいえ | はい | なし | Derived。Runtime Current 入力にしない |
| `audit_result` | しない | はい | はい | いいえ | はい | review event migration 候補 | 異常検知と説明に使う。Submit 対象選択元にしない |
| `notifications` | しない | delivery evidence 可 | はい | いいえ | はい | Delivery Ledger migration 候補 | payload / result は Derived。Send は Delivery Ledger で dedup |
| existing `plist` / `launchd` settings | しない | いいえ | いいえ | legacy 保持不要 | Phase13-E では削除禁止 | Runtime v2 では新規作成 | 既存 launchd plist は Runtime v2 の正規構成として継承しない。Acceptance Test / Manual Rehearsal 完了後、後続の明示フェーズで新規作成する |

Current として管理する固定 Path:

```text
pending_order_plan/pending_order_plan.json
persistent_ledger/state.json
persistent_ledger/orders.jsonl
persistent_ledger/executions.jsonl
persistent_ledger/positions.jsonl
persistent_ledger/cash_history.jsonl
persistent_ledger/events.jsonl
runtime_state/current_state.json
notification_delivery/delivery_ledger.jsonl
```

## 6. 既存コード参照ポリシー

既存コードを読む場合は、以下の目的だけに限定する。

```text
現状の問題箇所を特定する
v2 で置き換える対象を把握する
legacy isolation 対象を把握する
既存 artifact を壊さないための依存確認をする
```

既存コードを v2 の正規設計根拠にしない。

禁止する使い方:

- 既存 Runtime flow を v2 の正規フローにする。
- 既存の日付別 resolver を Current State 決定方法にする。
- `order_plan/YYYY-MM-DD` を Submit 対象選択の根拠にする。
- `approval_artifact/YYYY-MM-DD` を Current 承認状態にする。
- `submitted_orders` / `broker_orders` を現在保有 SoT にする。
- `reports/YYYY-MM-DD` を Runtime Current 入力にする。

## 7. Acceptance Test 計画

| Test | 目的 | 対象フェーズ | PASS 条件 |
| --- | --- | --- | --- |
| Current State fixed path test | Current が固定 Path からのみ読まれることを確認 | Phase13-F | fixed paths 以外を Current としない |
| No date-based Current resolution test | 日付別 artifact から Current を自動選択しないことを確認 | Phase13-F / L | `YYYY-MM-DD` resolver が v2 Current で使われない |
| No phase-based Current resolution test | Phase 番号を Runtime SoT にしないことを確認 | Phase13-F | Phase scoped path を Current としない |
| Pending-only Submit source test | Submit 対象が pending のみであることを確認 | Phase13-I | `order_plan/YYYY-MM-DD` fallback が失敗する |
| Consumed pending cannot resubmit test | `CONSUMED` pending の再 Submit を防ぐ | Phase13-I | `CONSUMED` から `SUBMITTING` へ戻れない |
| POST_SEND_UNKNOWN no auto-resend test | 結果不明時の自動再送を防ぐ | Phase13-I / M | Broker ReadOnly / Review Required に進む |
| Order is not asset test | 注文を資産扱いしないことを確認 | Phase13-H / J | order record だけでは position が増えない |
| Execution creates position test | 約定が保有を作ることを確認 | Phase13-J | execution ingestion 後に position 更新 |
| Position + cash creates asset state test | 保有と現金から asset state を作ることを確認 | Phase13-J | `state.json` が position / cash を反映 |
| Current State unknown blocks BUY / Approval / Submit test | 不明 state を保有 0 扱いしない | Phase13-F / H | BUY / Approval / Submit が BLOCKED または REVIEW_REQUIRED |
| Report is derived-only test | Report を Current 入力にしない | Phase13-K | report から Runtime Current を復元しない |
| Notification delivery dedup test | 通知二重送信を防ぐ | Phase13-K | 同じ payload_hash / channel / target_date を二重送信しない |
| Production broker_orders fallback prohibition test | Production で broker_orders fallback を保有確定に使わない | Phase13-J / M | Production fallback が BLOCKED / REVIEW_REQUIRED |
| Demo broker_orders fallback review flag test | Demo fallback に review flags が付く | Phase13-J / M | `review_required=true`, `production_equivalent=false` |
| Legacy runtime not used as v2 source test | 既存 Runtime を v2 source にしない | Phase13-L | legacy resolver を Current 決定に使わない |

## 8. launchd 再開条件

`launchd` 再開は、少なくとも以下がすべて完了するまで禁止する。

```text
Current State Contract PASS
Runtime State Machine PASS
Pending lifecycle PASS
Persistent Ledger mainline PASS
Broker ReadOnly ingestion PASS
Report / Notification / Audit rewire PASS
Legacy Runtime isolation PASS
Acceptance Test PASS
Manual Rehearsal PASS
Production order prohibition audit PASS
```

`launchd` 再開前に確認すること:

- Runtime v2 が固定 Path Current を読む。
- 日付別 / Phase 別 artifact が Current 決定元ではない。
- Submit source が pending only である。
- `CONSUMED` / `POST_SEND_UNKNOWN` の二重 Submit が防止される。
- Production 注文が禁止されている。
- Notification Send が Delivery Ledger で dedup される。
- Report が Derived として扱われる。
- Manual Rehearsal が PASS している。
- 既存 plist を Runtime v2 の正規構成として継承していない。
- Runtime v2 用 scheduler / plist は Acceptance Test と Manual Rehearsal 完了後に新規作成する計画になっている。

## 9. Production 注文禁止

Phase13-E は実装計画のみである。

禁止:

```text
Production 注文は禁止
Demo 注文もこの作業では実行しない
Submit も実行しない
Broker 注文も実行しない
launchd も再開しない
notification 送信もしない
既存 plist を削除しない
新規 plist を作成しない
```

Phase13-M までの原則:

- Submit / Broker 注文は最後まで原則禁止。
- 必要な場合も Demo 限定かつ明示承認後。
- Production 注文は禁止。
- 既存 launchd plist は Runtime v2 の正規構成として継承しない。
- 既存 plist は legacy 保持対象ではないが、Phase13-E では削除しない。
- Runtime v2 の `launchd` / scheduler 設定は Acceptance Test と Manual Rehearsal 完了後に新規作成する。
- `POST_SEND_UNKNOWN` を自動再送で解消しない。
- 破壊的 cleanup や artifact 削除は禁止。

## 10. 完了条件

- Runtime v2 実装フェーズ分割案が作成されている。
- 移行対象 artifact の分類が作成されている。
- Acceptance Test 計画が作成されている。
- `launchd` 再開条件が明記されている。
- Production 注文禁止が明記されている。
- `runtime_architecture_v2.md` に Phase13-E 要約が追記されている。
- JSON レポートが作成され、妥当性確認されている。
- 実装変更が一切行われていない。
