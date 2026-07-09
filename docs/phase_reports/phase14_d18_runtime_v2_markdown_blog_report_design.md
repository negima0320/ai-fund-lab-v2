# Phase14-D18 Runtime v2 Markdown / Blog Report Design

作成日: 2026-07-07

最終判定: **PHASE14D18_REPORT_DESIGN_COMPLETE**

## 1. 目的

Phase14-D18では、Runtime v2 `ReportArtifact` JSONとRuntime v2 Evidenceから、Runtime v2専用のMarkdown Report、Blog Draft、Public Reportを生成するための設計を定義する。

Phase14-D17で確認した通り、Runtime v2 Report Artifactは生成済みである。

- `.runtime/phase14d15/report/runtime_report.json`
- `.runtime/phase14d15/notification/notification_payload.json`

一方で、Runtime v2 ReportのMarkdown化とBlog Report生成は未接続だった。Phase14-D18ではこのgapを埋めるため、Phase9ロジックを正規フローとして復活させず、Runtime v2専用のReport rendering boundaryを設計する。

今回は設計のみであり、コード変更、Phase9コード変更、Phase9 writer直接呼び出し、Submit、Broker API呼び出し、Notification実送信、launchd / plist変更は行わない。

## 2. 設計方針

Runtime v2 Report生成は、次の三層に分離する。

```text
Runtime v2 ReportArtifact JSON
  -> Runtime v2 Markdown Report
  -> Runtime v2 Blog Draft / Public Report
```

各層はDerived Artifactであり、Current Stateではない。

Runtime v2のCurrent SoTは引き続き以下に限定する。

- `persistent_ledger/state.json`
- `pending_order_plan/pending_order_plan.json`
- `runtime_state/current_state.json`
- 必要に応じたBroker ReadOnly Evidence current / history

Report、Blog、Notification、AuditはSubmit sourceにならない。

## 3. Runtime v2 Report Artifact入力仕様

Runtime v2 Markdown writerの主入力は `ReportArtifact` JSONとする。

例:

```text
.runtime/phase14d15/report/runtime_report.json
```

必須入力フィールド:

| Field | 用途 |
| --- | --- |
| `report_id` | Derived artifactのsource ID |
| `schema_version` | renderer互換性確認 |
| `mode` | demo / production等の表示 |
| `environment` | demo-only / production禁止表示 |
| `business_date` | Report対象日 |
| `target_session_date` | 対象セッション |
| `report_type` | `runtime` 固定想定 |
| `sections[]` | Markdown本文の主要構成 |
| `source_current_paths[]` | Current SoT参照の明示 |
| `source_history_refs[]` | History / Evidence参照の明示 |
| `review_required` | Report status |
| `blocked` | BLOCKED表示 |
| `halt` | HALT表示 |
| `derived` | `true`必須 |
| `not_current_state` | `true`必須 |

推奨追加入力:

- `asset_state.json`
- `audit_result.json`
- `reconciliation_result.json`
- `notification_payload.json`
- `broker_readonly_after/tachibana_demo_snapshot.json`
- `ledger_events/*.json`
- `pending_order_plan/pending_order_plan.json`
- `approval_artifact/*.json`

ただし、Markdown writerは追加入力が欠けても、ReportArtifact JSONだけで最小Markdownを生成できる設計にする。

## 4. Markdown Report出力仕様

Runtime v2 Markdown Reportは、内部確認用の完整なRuntime reportとする。

推奨出力先:

```text
.runtime/runtime_v2/reports/YYYY-MM-DD/runtime_report.md
.runtime/runtime_v2/reports/YYYY-MM-DD/runtime_report.json
```

Phase14単発検証では、既存phase runtime root配下にも同等出力を許可する。

```text
.runtime/phase14d15/report/runtime_report.md
.runtime/phase14d15/report/runtime_report.json
```

Markdown構成:

1. Title
2. Status Summary
3. Environment / Mode
4. Runtime Flow Summary
5. Planning
6. Approval
7. Pending
8. Orders
9. Executions / Fill Evidence
10. Positions
11. Asset
12. Reconciliation
13. Review Required / Blocked / Halt
14. Source Current Paths
15. Source History / Evidence Refs
16. Prohibited Side Effects
17. Appendix

D15入力例では以下を表示する。

- `environment=demo`
- `review_required=false`
- `blocked=false`
- `halt=false`
- Orders: `ledger_orders=3 broker_orders=3`
- Executions: `ledger_executions=0 broker_executions=0`
- Positions: `ledger_positions=7 broker_positions=7`
- Asset: `cash=19999648`, `buying_power=19999648`
- Review event: `sell_execution_equivalent`

## 5. Blog Draft出力仕様

Blog Draftは人間が公開前に読む下書きであり、内部情報の一部を含めてもよい。ただし、secret、raw request、raw response、認証情報、口座識別情報は載せない。

推奨出力先:

```text
.runtime/runtime_v2/reports/YYYY-MM-DD/blog_draft.md
.runtime/runtime_v2/reports/YYYY-MM-DD/blog_draft.json
```

Phase14単発検証では:

```text
.runtime/phase14d15/blog/blog_draft.md
.runtime/phase14d15/blog/blog_draft.json
```

Blog Draft構成:

1. 本日のRuntime v2運用メモ
2. Demo / Production状態
3. 資産状況
4. 現在保有中の銘柄
5. 本日確認した注文
6. 本日のBUY / SELL
7. 約定・Position・Cash evidence
8. Reconcile / Audit結果
9. Review Required / Blockedの有無
10. 翌営業日の確認点
11. 注意書き

Blog DraftはRuntime v2のEvidenceを説明するものであり、AI判断そのものやFeature詳細を過剰に公開しない。

## 6. Public Report出力仕様

Public Reportは公開可能なMarkdownであり、Blog Draftより強いredaction policyを適用する。

推奨出力先:

```text
reports/public/runtime_v2/YYYY-MM-DD_public_report.md
reports/public/runtime_v2/YYYY-MM-DD_public_report.json
```

iCloud同期が必要な場合は、Phase9と同じ `reports/public` 配下に置いてよい。ただし、Phase9出力と混在させないため、Runtime v2専用ディレクトリを使う。

```text
reports/public/runtime_v2/
```

Phase9の既存出力先である以下は、Runtime v2の正規出力先にはしない。

```text
reports/public/phase9_daily/
```

Public Report構成:

1. 資産状況
2. 現在保有中の銘柄
3. 本日約定した銘柄
4. 本日の売却銘柄
5. Runtime v2運用状態
6. Reconcile / Audit概要
7. 注意書き

Public Reportでは以下を非表示または要約する。

- raw broker response
- raw request
- secret / credential
- second password有無
- endpoint詳細
- broker order id raw value
- internal hashの過剰表示
- AI model内部特徴量
- production credential情報
- full audit trace

## 7. Phase9出力を参考にする範囲

Phase9 Blog Report v4は、以下の見た目・項目・文体の参考としてのみ使う。

- 「資産状況」
- 「現在保有中の銘柄」
- 「本日約定した銘柄」
- 「本日の売却銘柄」
- 「AIの総括」相当の短いまとめ
- 「注意書き」
- 公開用の平易な文体

参考にしてよい過去出力例:

```text
reports/public/phase9_daily/2026-06-26_blog_report_v4.md
```

ただし、Phase9固有の以下はRuntime v2へ持ち込まない。

- Phase9 daily runtime
- Phase9 ledger / paper ledgerをCurrent SoTにすること
- Phase9 inference artifact前提
- Candidate Top50固定構成
- Opportunity Top20固定構成
- Phase9 writerの直接呼び出し
- Phase9 `blog_report_v2_writer.py` のRuntime v2 adapter化なしの再利用

Runtime v2では、AI候補一覧が存在しない日でもReportを生成できる必要がある。

## 8. Phase9ロジックを使わない境界

禁止境界:

| 項目 | 方針 |
| --- | --- |
| Phase9 writer直接呼び出し | 禁止 |
| Phase9 daily runtime復活 | 禁止 |
| Phase9 ledger / demo_ledgerをCurrent SoT化 | 禁止 |
| Runtime v2 ReportをPhase9 artifactから生成 | 禁止 |
| Phase9 order_plan / approval_artifactからSubmit | 禁止 |
| Report / AuditをSubmit source化 | 禁止 |

許可境界:

| 項目 | 方針 |
| --- | --- |
| 過去Markdownの見た目参照 | 許可 |
| 既存redaction観点の参照 | 許可 |
| 注意書き文言の参考 | 許可 |
| Public向け構成の参考 | 許可 |

実装時は、Runtime v2専用moduleを作る。

候補:

```text
src/ai_fund_lab_v2/runtime_v2/report_markdown/
src/ai_fund_lab_v2/runtime_v2/blog_report/
```

## 9. Current / History / Derived分類

| Artifact | 分類 | Submit source可否 |
| --- | --- | --- |
| `persistent_ledger/state.json` | Current SoT | No |
| `pending_order_plan/pending_order_plan.json` | Current Submit source | Yes, Pending-only |
| `runtime_state/current_state.json` | Current | No |
| `broker_readonly/current` | Current Evidence | No |
| `broker_readonly/history` | History Evidence | No |
| `runtime_report.json` | Derived | No |
| `runtime_report.md` | Derived | No |
| `blog_draft.md` | Derived | No |
| `public_report.md` | Derived | No |
| `notification_payload.json` | Derived | No |
| `audit_result.json` | Derived / Evidence | No |

ReportはDerivedであり、Currentではない。BlogもDerivedであり、Runtimeの判断やSubmitを駆動しない。

## 10. Notification Payloadとの関係

Notification PayloadはRuntime v2 ReportArtifactから派生する短文payloadである。

既存D15:

```text
.runtime/phase14d15/report/runtime_report.json
  -> .runtime/phase14d15/notification/notification_payload.json
```

D18設計では、Blog Draft / Public Reportも同じReportArtifactをsourceにする。

```text
runtime_report.json
  -> runtime_report.md
  -> blog_draft.md
  -> public_report.md
  -> notification_payload.json
```

または、Notification PayloadをBlogと並列に生成してもよい。

```text
runtime_report.json
  -> runtime_report.md
  -> blog_draft.md
  -> public_report.md
runtime_report.json
  -> notification_payload.json
```

Acceptanceでは以下を確認する。

- `source_report_id` が一致する。
- `business_date` が一致する。
- `environment` が一致する。
- Blog Draft生成とNotification実送信は分離される。
- Notification実送信は明示許可以前は禁止。

## 11. iCloud / reports/publicへの出力方針

内部Runtime v2 artifact:

```text
.runtime/runtime_v2/reports/YYYY-MM-DD/
```

公開候補:

```text
reports/public/runtime_v2/YYYY-MM-DD_public_report.md
reports/public/runtime_v2/YYYY-MM-DD_public_report.json
```

Phase9の既存symlink:

```text
reports/public/phase9_daily -> /Users/negishi/Library/Mobile Documents/com~apple~CloudDocs/AIFundLab/phase9_daily
```

Runtime v2でiCloud同期したい場合は、以下のどちらかを後続フェーズで明示的に選ぶ。

1. `reports/public/runtime_v2` を新規ディレクトリとして使う。
2. `reports/public/runtime_v2` をiCloud配下へsymlinkする。

Phase14-D18ではsymlink作成やiCloud出力変更は行わない。

## 12. launchd接続前の手動生成手順

launchd接続前は、手動CLIで生成する。

候補CLI:

```bash
python3 scripts/run_runtime_v2_report_markdown.py \
  --report .runtime/phase14d15/report/runtime_report.json \
  --evidence-root .runtime/phase14d15 \
  --output-root .runtime/phase14d15/report
```

Blog Draft:

```bash
python3 scripts/run_runtime_v2_blog_report.py \
  --report .runtime/phase14d15/report/runtime_report.json \
  --evidence-root .runtime/phase14d15 \
  --output-root .runtime/phase14d15/blog \
  --mode draft
```

Public Report:

```bash
python3 scripts/run_runtime_v2_blog_report.py \
  --report .runtime/phase14d15/report/runtime_report.json \
  --evidence-root .runtime/phase14d15 \
  --output-root reports/public/runtime_v2 \
  --mode public
```

手動生成時のguard:

- `report.derived == true`
- `report.not_current_state == true`
- `environment == demo` または明示された安全環境
- raw secretが入力にない
- raw request / raw responseを出力しない
- output rootがPhase9 daily directoryではない
- Notification送信しない
- launchd変更しない

## 13. Runtime v2 Markdown Writer責務

Runtime v2 Markdown writerの責務:

- `ReportArtifact` JSONを読み込む。
- schema / derived / not_current_stateを検証する。
- sectionsを安定した順序でMarkdown化する。
- Current / History / Derived refsを明示する。
- Review Required / Blocked / Haltを強調する。
- Markdownとmetadata JSONを出力する。
- 出力がSubmit sourceにならないことをmetadataへ書く。

責務外:

- Submit
- Broker API呼び出し
- Notification実送信
- AI再学習
- Phase9 artifact生成
- launchd/plist操作

## 14. Runtime v2 Blog Writer責務

Runtime v2 Blog writerの責務:

- Runtime v2 ReportArtifactをPublic向け構造へ変換する。
- optional evidenceから資産・保有・注文・売却・Reconcile/Audit概要を補足する。
- Draft / Publicの2モードを持つ。
- Public modeではredactionを必須にする。
- 出力metadataにsource report / evidence refsを書く。
- Phase9 writerを直接呼ばない。

Draft mode:

- 内部確認向け。
- source refsやreview reasonをやや詳しく出す。
- ただしsecret / raw request / raw responseは出さない。

Public mode:

- 公開向け。
- 口座情報、内部hash、詳細audit traceを伏せる。
- 投資助言ではない注意書きを入れる。
- Demo運用であることを明記する。

## 15. Acceptance Criteria

Phase14-D18設計のAcceptance Criteria:

| Criteria | 判定 |
| --- | --- |
| Runtime v2 Report Artifactの入力仕様が定義されている | PASS |
| Markdown Report出力仕様が定義されている | PASS |
| Blog Draft出力仕様が定義されている | PASS |
| Public Report出力仕様が定義されている | PASS |
| Phase9出力を参考にする範囲が明記されている | PASS |
| Phase9ロジックを使わない境界が明記されている | PASS |
| Current / History / Derived分類が明記されている | PASS |
| ReportがDerivedでありCurrentではないことが明記されている | PASS |
| Notification Payloadとの関係が整理されている | PASS |
| iCloud / reports/publicへの出力方針が明記されている | PASS |
| launchd接続前の手動生成手順が明記されている | PASS |
| Phase9コード変更なし | PASS |
| Phase9 writer直接呼び出しなし | PASS |
| Submitなし | PASS |
| Broker API呼び出しなし | PASS |
| Notification実送信なし | PASS |
| launchd/plist変更なし | PASS |

## 16. Final Decision

```text
PHASE14D18_REPORT_DESIGN_COMPLETE
```
