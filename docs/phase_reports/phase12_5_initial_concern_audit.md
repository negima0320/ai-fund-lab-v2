# Phase12.5 Initial Concern Audit

## Status

`PHASE12_5_INITIAL_CONCERN_AUDIT_COMPLETE`

今回は初期懸念の一次監査のみ。実装変更、artifact削除、launchd変更、実API発注、本番接続、通知新規送信、フルバックテスト、大規模テストは実施していない。

## 読んだartifact / コード / report一覧

### Artifact

- `.runtime/operations/approval_artifact/2026-06-29/approval_artifact.json`
- `.runtime/operations/approval_artifact/2026-06-30/approval_artifact.json`
- `.runtime/operations/approval_artifact/2026-07-01/approval_artifact.json`
- `.runtime/operations/approval_artifact/2026-07-02/approval_artifact.json`
- `.runtime/operations/approval_request/2026-07-01/approval_request.json`
- `.runtime/operations/approval_request/2026-07-02/approval_request.json`
- `.runtime/operations/submitted_orders/2026-06-29/submitted_orders.json`
- `.runtime/operations/submitted_orders/2026-06-30/submitted_orders.json`
- `.runtime/operations/submitted_orders/2026-07-01/submitted_orders.json`
- `.runtime/operations/submitted_orders/2026-07-02/submitted_orders.json`
- `.runtime/operations/order_plan/2026-07-01/order_plan.json`
- `.runtime/operations/order_plan/2026-07-02/order_plan.json`
- `.runtime/operations/broker_orders/2026-07-02/orders.json`
- `.runtime/operations/broker_executions/2026-07-02/executions.json`
- `.runtime/operations/broker_positions/2026-07-02/positions.json`
- `.runtime/operations/fill_events/2026-07-02/fill_events.json`
- `.runtime/operations/reconciliation_result/2026-07-02/reconciliation_result.json`
- `.runtime/operations/daily_report_refs/2026-06-29/daily_report_refs.json`
- `.runtime/operations/daily_report_refs/2026-06-30/daily_report_refs.json`
- `.runtime/operations/daily_report_refs/2026-07-01/daily_report_refs.json`
- `.runtime/operations/daily_report_refs/2026-07-02/daily_report_refs.json`
- `.runtime/operations/notifications/2026-06-30/notification_result.json`
- `.runtime/operations/notifications/2026-07-02/notification_result.json`
- `.runtime/operations/daily_manifest/2026-07-02/daily_manifest.json`
- `.runtime/operations/demo_ledger/state.json`

### Report

- `.runtime/operations/reports/2026-07-02/public_report.md`
- `.runtime/operations/reports/2026-07-02/line_payload.json`
- `.runtime/operations/reports/2026-07-02/discord_payload.json`

`.runtime/operations/reports` はiCloud配下へのsymlinkで、今回は読み取りのみ実施した。

### Code / launchd

- `src/ai_fund_lab_v2/operations/operations.py`
- `src/ai_fund_lab_v2/operations/notifications.py`
- `scripts/run_approval_prepare.py`
- `scripts/run_demo_daily_operation.py`
- `scripts/run_daily_report.py`
- `tools/launchd/com.aifundlab.operations.auto_approval.plist`
- `tools/launchd/com.aifundlab.operations.daily_report.plist`
- `/Users/negishi/Library/LaunchAgents/com.aifundlab.operations.auto_approval.plist`
- `/Users/negishi/Library/LaunchAgents/com.aifundlab.operations.daily_report.plist`
- `/tmp/aifundlab.operations.auto_approval.out.log`
- `/tmp/aifundlab.operations.daily_report.out.log`

## 1. manual_override / 600000 の現在状態

結論: 解消済みではない。2026-07-02の最新Approval artifactとApproval requestに `manual_override / 600000` が残っている。

確認結果:

| Date | Approval status | approval_max_notional | source | 備考 |
| --- | --- | --- | --- | --- |
| 2026-06-29 | `APPROVED` | null | null | 古いschema |
| 2026-06-30 | `APPROVED` | null | null | 古いschema。submitted側には60万円budget痕跡あり |
| 2026-07-01 | `APPROVED` | `850000` | `dynamic_max_exposure` | Phase12-AS方針通り |
| 2026-07-02 | `APPROVED` | `600000` | `manual_override` | 現在も残存 |

2026-07-02のApproval requestでは以下も確認した。

- `dynamic_approval_max_notional=0`
- `manual_override=600000`
- `current_exposure=965200`
- `available_exposure_budget=0`
- `available_buying_power_or_cash=34800`

つまり、通常のDynamic Approval Max方針なら2026-07-02 Approvalは承認されない可能性が高い。manual overrideにより `APPROVED` になっている状態であり、単なる古いartifact表示ではない。

## Runtimeが現在も参照しているか

2026-07-02朝Submit artifactは以下を持つ。

- `submit_run_date=2026-07-02`
- `order_plan_source_date=2026-07-01`
- `approval_source_date=2026-07-01`
- `approval_artifact_path=.runtime/operations/approval_artifact/2026-07-01/approval_artifact.json`

したがって、2026-07-02朝Submitの参照先は2026-07-01 Approvalであり、ファイルパス上はPhase12-AS後の `850000 / dynamic_max_exposure` artifactを指している。

ただし、2026-07-02 `submitted_orders` 内の各itemの `approval_budget.approval_max_notional` は `600000` のままで、4件accepted + 1件blockedの直接原因になっている。

さらに、`_resolve_submit_order_plan_date` は当日Plan/Approvalがなければ前営業日Plan/Approvalを参照する。2026-07-03朝Submit時点で2026-07-03のPlan/Approvalが未生成なら、2026-07-02の `manual_override / 600000` Approvalを参照する可能性がある。

判定:

- 古いartifactにだけ残っている: No
- 最新Approval artifactでは解消済み: No
- Runtimeが現在も参照し得る: Yes
- 既存2026-07-02 Submit結果に影響済み: Yes
- 次営業日Submitに影響し得る: Yes

## Daily Report / Blog Report / Notification への影響

Daily Report / Notificationは2026-07-02を `NORMAL_OPERATION_DAY` / `PASS` と扱っている。

一方で、2026-07-02 Submitは `PARTIAL_PASS_WITH_ITEM_BLOCKS` で、blocked item理由は `remaining_approval_budget_insufficient`。これは60万円budget痕跡と整合する。

影響:

- Daily Report本文では、結果として1銘柄だけが「本日約定」として見える。
- Notification payloadでは `Submit: STALE_IGNORED` と表示され、manual override自体は明示されない。
- Approval Maxの異常がDaily Report / Notificationから十分に見えない。

修正必要性:

- 必要。少なくとも2026-07-02 Approval artifactを通常運用方針と整合させるか、manual override artifactを次営業日Submitの参照対象にしないガードが必要。

## 2. Public Report の整合性確認

結論: Runtime stateの根本破綻というより、Report生成時のSource of Truth表示混在が主問題。ただし、読者向けには「本日約定」と「Broker約定0件 / 保有0件」が同居しており、Production Equivalent acceptance上は修正対象。

### 確認したRuntime state

2026-07-02のBroker / Fill state:

| Artifact | 内容 |
| --- | --- |
| `broker_orders` | 4件。6166, 2962, 4179, 4265 が `status=全部約定`, `executed_quantity=100`, `remaining_quantity=0` |
| `broker_executions` | 0件 |
| `broker_positions` | 0件 |
| `fill_events` | 5件。4件 `ACCEPTED`, 1件 `BLOCKED_ITEM` |
| `reconciliation_result` | `PASS_WITH_BLOCKED_ITEMS`。`broker_orders_used_as_execution_fallback=true`, `demo_empty_executions_positions_explained=true` |
| `demo_ledger` | Persistent履歴あり。Demo日次リセット横断用。simulated execution/position履歴も保持 |

### Public Reportの各項目の生成元

| Report表示 | 生成元 |
| --- | --- |
| 「本日約定した銘柄」 | `order_plan/2026-07-02` のitemsをベースに、同日 `broker_orders` の `executed_quantity/status` fallbackを `_matched_filled_broker_order` で照合 |
| 「Broker約定0件」 | `broker_executions/2026-07-02/executions.json` の件数 |
| 「Broker保有0件」 | `broker_positions/2026-07-02/positions.json` の件数 |
| 「現在保有中の銘柄」 | Report modelのpositions。Broker positionsが空のとき、filled orderからsynthetic demo positionsを生成し得る |
| Reconcile `PASS_WITH_BLOCKED_ITEMS` | `reconciliation_result/2026-07-02` |

### Source of Truth混在の有無

混在あり。

厳密にはPhase12-AQで許容された `broker_orders` execution fallbackが使われている。しかしPublic Reportでは、そのfallbackが「Broker-confirmed executionsではない」ことを明示しないまま「本日約定」と表示している。

さらに、Report modelは2026-07-02当日の `order_plan` をベースに行を作るため、2026-07-01 Planを元にした2026-07-02朝Submit結果とは日付sourceがずれる。結果として、2026-07-02 Order Planにも含まれる6166だけが「本日約定」として拾われ、同じ朝Submitでacceptedだった4265/4179/2962は本文の「本日約定」には出ない構図になっている。

これはRuntime stateの問題というより、Reportの表示モデルが次営業日候補用Order Planと本日Submit/Fill結果を同じ `buy_rows` に混ぜている問題に近い。

### Demo ledger / fill_events / broker_executions / broker_positions の一貫性

Reconcile上は以下のように整理されている。

- Broker executionsが0でも、broker_ordersのexecuted_quantity/statusで補完可能。
- Broker positionsが0でもDemo仕様として説明可能。
- Persistent Demo LedgerはBroker snapshotで上書きしない。
- Demo Special Fill Simulationは2026-07-02では対象外で未使用。

Runtime stateとしては説明可能。ただしReportでは以下が不十分。

- `broker_orders` fallbackと `broker_executions` の違いが人間向けに明示されていない。
- Broker positionsが空なのにsynthetic demo positionを「現在保有中」と表示し得る。
- `fill_events` が `ACCEPTED` のままなのに、Reportが `broker_orders` fallbackで `FILLED` と表示する。

修正必要性:

- 必要。Runtime stateの大改修ではなく、Report生成時のSoT分離と文言修正が最小修正候補。

## 3. Notification未着の切り分け

結論: artifact上は2026-06-30、2026-07-02とも送信成功。未着がある場合、現在のartifactだけでは配送到達までは証明できない。確認できる範囲では、設定存在、送信試行、HTTP例外なし、secret/raw保存なしまで。

### 最新notification artifact状態

`.runtime/operations/notifications/2026-07-02/notification_result.json`:

- `status=PASS`
- `line_config_present=true`
- `discord_config_present=true`
- `line_send_attempted=true`
- `line_send_executed=true`
- `discord_send_attempted=true`
- `discord_send_executed=true`
- `line.status=PASS`
- `discord.status=PASS`
- `error_type=""`
- `secret_saved=false`
- `raw_request_saved=false`
- `raw_response_saved=false`

`.runtime/operations/daily_report_refs/2026-07-02/daily_report_refs.json`:

- `send_notifications_requested=true`
- `notification_status=PASS`
- `line_send_executed=true`
- `discord_send_executed=true`

### 送信成功判定の根拠

`notifications.py` の実装では、LINE/Discordとも以下の判定。

- 必要なenvがあれば `config_present=true`
- `dry_run=false` の場合、`urllib.request.urlopen` でPOST
- 例外が出なければ `status=PASS`, `send_executed=true`
- 例外が出た場合は `FAILED_NON_FATAL`
- HTTP response bodyや配送到達結果は保存しない
- raw request / raw response / secretは保存しない

したがってartifact上のPASSは「送信先APIへのPOSTが例外なく完了した」ことを意味する。ユーザー端末やDiscordチャンネルでの到達確認までは含まない。

### launchd経由と手動実行の環境差

確認結果:

- `tools/launchd/com.aifundlab.operations.daily_report.plist` と `/Users/negishi/Library/LaunchAgents/...daily_report.plist` は一致。
- `--send-notifications` は登録済み。
- WorkingDirectoryは `/Users/negishi/work/ai-fund-lab-v2`。
- launchd plistのEnvironmentVariablesには通知用envはなく、`TACHIBANA_API_ENV=demo` のみ。
- ただしコードは `.env` をWorkingDirectoryから読み、その後 `os.environ` で上書きする。
- `.env` には `AIFUNDLAB_LINE_CHANNEL_ACCESS_TOKEN`, `AIFUNDLAB_LINE_TO_ID`, `AIFUNDLAB_DISCORD_WEBHOOK_URL` のキーが存在することを確認した。値は表示していない。

気になる点:

- `launchctl print gui/501/com.aifundlab.operations.daily_report` では `runs=0`, `last exit code=(never exited)` と表示された。
- 一方で `/tmp/aifundlab.operations.daily_report.out.log` には2026-07-02 20:05の `PASS` が残る。
- `notification_result.json` と `daily_report_refs.json` のmtimeは2026-07-02 20:19で、20:05のlaunchdログより後。

このため、2026-07-02の最終notification artifactはlaunchd 20:05実行そのものではなく、その後の手動または別経路再生成で更新された可能性がある。未着調査では「launchd実行で本当に通知送信されたか」と「手動再生成で通知送信されたか」を分ける必要がある。

### 宛先・Webhook・認証情報・配送後段の確認可能範囲

今回、新規送信やsecret表示は禁止のため、確認できたのは以下。

- `.env` に必要キーが存在する。
- artifact上は設定あり、送信試行あり、例外なし。
- raw request / raw response / secretは保存されていない。
- daily_report launchd plistはリポジトリ版と登録版が一致している。
- WorkingDirectoryは `.env` を読める場所を指している。

確認できないもの:

- LINE token / to_id の実値が正しいか。
- LINEの相手がBotをブロックしていないか。
- Discord webhookの投稿先チャンネルが期待通りか。
- LINE/Discord側で投稿が削除・抑止・権限変更されていないか。
- 配送先端末で通知表示が抑止されていないか。
- HTTP response bodyの詳細。

修正必要性:

- 実通知未着が続くなら必要。ただし最小修正は「再送」ではなく、到達確認用の非secret診断を追加すること。

## 修正が必要かどうか

| 懸念 | 判定 | 理由 |
| --- | --- | --- |
| manual_override / 600000 | 修正必要 | 最新2026-07-02 Approvalに残存し、次営業日Submit参照リスクがある |
| Public Report矛盾 | 修正必要 | Runtime stateは説明可能だが、Report上でSoTと文言が混在している |
| Notification未着 | 条件付き修正必要 | artifactはPASS。未着が事実なら配送後段・launchd/手動差分の診断強化が必要 |

## 次に行うべき最小修正案

1. Approval参照ガード
   - `approval_max_notional_source=manual_override` のApprovalを通常launchd submitが参照する場合、Report/Auditで `REVIEW_REQUIRED` にする。
   - 2026-07-02 ApprovalはDynamic方針で再評価すると `dynamic_approval_max_notional=0` のため、通常承認扱いしない。

2. Report SoT分離
   - Public Reportの「本日約定」セクションは `broker_executions` と `fill_events` を優先し、`broker_orders` fallbackを使う場合は「Broker Orders上の全部約定表示」と明記する。
   - `order_plan` 由来の翌営業日候補と、`submitted_orders` / `fill_events` / `broker_orders` 由来の本日結果を別モデルに分ける。
   - Broker positionsが0件のときsynthetic demo positionを出す場合は「Demo ledger上の推定保有」など、Broker positionsとは別表現にする。

3. Notification診断
   - 新規送信なしで、latest `notification_result`、daily_report stdout/stderr、launchctl registered state、artifact mtimeを1つの診断artifactにまとめる。
   - HTTP status codeだけを保存し、token/webhook URL/body/raw responseは保存しない。
   - launchd実行時の `.env` 読み取り結果をkey presenceだけで記録する。

## 今回は修正していないこと

- 実装変更はしていない。
- runtime artifact削除・再生成はしていない。
- launchd plist変更・bootstrap/bootoutはしていない。
- Demo追加注文はしていない。
- Production接続・Production注文はしていない。
- LINE/Discord通知の新規送信はしていない。
- secret値、token値、webhook URL、raw request、raw responseは表示・保存していない。
- AI再学習、フルバックテスト、大規模テストはしていない。
