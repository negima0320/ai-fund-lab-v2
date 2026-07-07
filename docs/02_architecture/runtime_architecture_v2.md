# Runtime Architecture v2 システム設計書

作成日: 2026-07-07

## 1. 目的

Runtime Architecture v2 は、AI Fund Lab v2 の日次運用を安全に制御するための Runtime システム設計である。

Runtime は AI の投資判断ロジックではない。Runtime は、AI と周辺システムが出した判断、計画、承認、Broker 状態を、現在状態と照合しながら、正しい順序で、二重実行なく運用する制御層である。

中心原則は次の通り。

- Runtime は運用を制御する。AI 判断そのものは制御層に混ぜない。
- Current State / History / Derived を明確に分離する。
- Runtime Current は Phase 単位・日付単位の作業場所ではなく、役割ごとの固定 Path で管理する。
- 注文 Submit 対象は `pending_order_plan/pending_order_plan.json` のみに固定する。
- 現在保有、現金、買付余力、総資産は `persistent_ledger/state.json` を中心に管理する。
- Submit / Broker Order は非冪等処理として扱い、多重実行を禁止する。
- Market Refresh、Feature Refresh、Daily Plan、AI inference、Approval prepare、Report、Audit、Reconcile、Read-only broker sync は安全に再実行可能にする。
- Runtime Architecture v2 は既存 Runtime の改善ではなく、Runtime 制御の再設計である。
- 注文、約定、保有、資産を別概念として扱う。
- Runtime は銘柄数の固定上限を持たず、資金・買付余力・Broker 制約・Safety 制約・重複注文防止を制御する。
- Report 作成は Runtime の正式な説明責務であり、Report は Current State から生成される Derived artifact として扱う。

## 2. なぜ Phase13 で Runtime を作り直すのか

Phase12.5 までに、実運用に近い daily runtime、pending order plan、persistent ledger の部品は整備されてきた。一方で、日付別 artifact が Current 入力と履歴証跡の両方として使われる箇所が残り、Runtime 全体の source of truth が曖昧になりやすい。

特に問題となるのは次の点である。

- `order_plan/YYYY-MM-DD` が履歴でありながら Submit 対象の候補にもなり得る。
- `approval_artifact/YYYY-MM-DD` が履歴でありながら Current 承認状態の推測元にもなり得る。
- `demo_ledger/`、`broker_positions/YYYY-MM-DD`、`ledger/YYYY-MM-DD` などが現在保有や現金の参照元として混在し得る。
- 途中失敗後の再実行時に、どこまでが再実行可能で、どこからが二重実行禁止かを Runtime 全体で統一する必要がある。

Phase13 では、実装開始前に Runtime の役割、責務、状態管理、再実行性、注文多重実行禁止を再定義する。本書は Phase13 用の一時資料ではなく、今後の Runtime 実装、運用、監査、レビューで参照するシステム設計書とする。

### 2.1 既存 Runtime 制御を v2 の前提にしない

Runtime Architecture v2 は、既存 Runtime 制御の改善版ではなく、Runtime 制御の再設計である。

既存 Runtime には以下の問題があった。

```text
Current / History / Derived が混在していた
日付別 artifact を Current として扱っていた
order_plan/YYYY-MM-DD と Submit 対象が混在していた
approval_artifact/YYYY-MM-DD と Current 承認状態が混在していた
demo_ledger と persistent_ledger の責務が重複していた
Broker Orders / Executions / Positions / Holdings の流れが不完全だった
Report 上の表示と Runtime の実状態が混ざっていた
再実行可能処理と非冪等処理の境界が曖昧だった
```

したがって、既存 Runtime の制御フローを v2 の正規フローとして継承しない。既存 Runtime は legacy implementation として扱い、v2 設計は Current State、Pending Order Plan、Persistent Ledger、Runtime State Machine を中心に再定義する。

既存コードや既存フローは、以下の目的でのみ参照してよい。

```text
既存問題の確認
移行対象の把握
legacy 化対象の把握
破壊してはいけない artifact の確認
```

以下の目的では参照しない。

```text
新 Runtime の正規フローの根拠
Current State の決定方法
Submit 対象の選び方
約定後の保有確定方法
Report / Audit の Current 判定方法
```

## 3. AI / システムの役割整理

AI Fund Lab v2 の各 AI / システムは、以下の問いに答える。

| Component | 問い | 役割 |
| --- | --- | --- |
| Candidate AI | 今、市場の中で面白そうな銘柄はどれ？ | 購入対象候補の銘柄を選定する |
| Opportunity AI | 購入対象の銘柄の中で、どれを優先すべきか？ | 購入候補に順位を付ける |
| Position Management AI | この株はまだ持つべきか？ | 保有株について、継続・売却・縮小・追加などの判断材料を出す |
| Capital Allocation | お金をどう分けるか？ | 投資可能資金を各銘柄へどう配分するか決める |
| Safety | この取引は危険ではないか？ | 危険な取引、過剰なリスク、異常状態を検知し、買い停止・売買停止・Review Required などを出す |

Runtime は、これらの判断を生成するのではなく、判断結果を運用可能な順序と状態遷移に載せる。

Runtime は銘柄数の固定上限を持たない。購入候補の幅は Candidate AI / Opportunity AI / Position Management AI / Capital Allocation / Safety の判断に委ねる。Capital Allocation が結果として 5 銘柄、10 銘柄、20 銘柄などに絞ることはあり得るが、それは Runtime の固定ルールではない。

## 4. Runtime の責務

Runtime はシステム全体の制御層として、以下を統合する。

- データ取得
- 特徴量更新
- AI 実行
- 売買候補生成
- 売買計画生成
- 承認
- 注文
- 約定確認
- 保有更新
- 現金更新
- 総資産更新
- レポート
- 通知
- 監査
- 異常時停止
- リカバリ

Runtime は常に次の現在状態を把握する。

- 今、どの株を何株持っているか
- 今、現金はいくらあるか
- 今、買付余力はいくらあるか
- 今、注文予定は存在するか
- その注文予定は承認済みか
- その注文予定はすでに送信済みか
- 送信した注文は約定したか
- 約定した結果、保有と現金はどう変わったか
- 現在の総資産はいくらか

これらを日付別ファイルから推測してはならない。Runtime Architecture v2 では Current State を固定 Path で管理する。

Runtime が制御するのは銘柄数ではなく、資金、買付余力、注文可能金額、Broker 制約、Safety 制約、重複注文防止である。Runtime は 5 銘柄固定などの旧制御を継承せず、銘柄数を理由に候補を機械的に切り捨てない。

ただし、以下の制約は必ず守る。

- 上限金額以上は購入できない。
- 現金・買付余力以上は購入できない。
- Safety が禁止した注文は出せない。
- Broker が受け付けない注文は出せない。
- 最小売買単位を満たさない注文は出せない。
- 同一注文を二重に出してはいけない。

## 5. Runtime がやらないこと

Runtime は次を行わない。

- AI モデルの投資判断ロジックを内包しない。
- Candidate AI のスコア計算を Runtime 内で再実装しない。
- Opportunity AI の順位付けロジックを Runtime 内で再実装しない。
- Position Management AI の保有継続判断を Runtime 内で再実装しない。
- Safety の投資判断ルールを Runtime の注文制御に混ぜ込まない。
- 5 銘柄固定などの旧 Runtime 制御を基本要件として継承しない。
- 銘柄数を理由に AI / Capital Allocation / Safety の候補を機械的に切り捨てない。
- 日付別 History artifact から「最新っぽい」Current を推測しない。
- Derived artifact を Runtime の Current 入力にしない。
- Broker Submit の不明結果を自動再送で解決しない。

Phase13 でやらないことは次の通り。

- AI モデル変更
- Candidate AI 再設計
- Opportunity AI 再設計
- Position Management AI 再設計
- Safety 投資判断変更
- AI 再学習
- フルバックテスト
- Production 注文
- `launchd` 自動運用再開
- 実装開始

## 6. Runtime 全体フロー

Runtime Architecture v2 の標準フローは以下である。

```text
1. Market Refresh
2. Feature Refresh
3. Current State Read
   - persistent_ledger/state.json
   - pending_order_plan/pending_order_plan.json
4. AI inference
   - Candidate AI
   - Opportunity AI
   - Position Management AI
   - Capital Allocation
   - Safety
5. Daily Plan
6. Pending Order Plan promotion
7. Approval prepare
8. Human / policy approval
9. Submit preflight
10. Broker Order Submit
11. Broker ReadOnly status sync
12. Fill / execution monitoring
13. Persistent Ledger update
14. Reconcile
15. Report / Notification artifact generation
16. Audit
```

このうち、Broker Order Submit と Notification Send は非冪等処理として別扱いにする。その他の処理は、同じ入力、同じ Current State、同じ business date に対して安全に再実行できるよう設計する。

## 7. Runtime State Machine

Runtime v2 は、日次運用を以下の状態遷移として管理する。

```text
IDLE
MARKET_DATA_READY
FEATURE_READY
CURRENT_STATE_LOADED
AI_INFERENCE_DONE
DAILY_PLAN_CREATED
PENDING_PROMOTED
APPROVAL_PENDING
APPROVED
SUBMITTING
SUBMITTED
POST_SEND_UNKNOWN
MONITORING_FILL
LEDGER_UPDATED
RECONCILED
REPORT_READY
REVIEW_REQUIRED
BLOCKED
HALT
```

状態遷移の原則:

- `SUBMITTING` 以降は Broker Order の二重送信防止を最優先する。
- `POST_SEND_UNKNOWN` は自動再送禁止であり、Broker ReadOnly と Review Required へ進める。
- `SUBMITTED` は Broker への送信が記録された状態であり、再 Submit 可能状態ではない。
- `CONSUMED` は Pending Order Plan 側の状態であり、対応する Submit が完了または結果不明として処理対象から外れたことを示す。`CONSUMED` の pending plan は再 Submit してはならない。
- `REVIEW_REQUIRED` は人間確認または明示的な recovery 手順が必要な停止状態である。

| State | 意味 | 入力条件 | 出力 artifact | 次に進める状態 | 再実行可能 | 副作用 | 失敗時の遷移先 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `IDLE` | Runtime が未開始または待機中 | business date と runtime mode が決まっている | run manifest | `MARKET_DATA_READY`, `BLOCKED` | 可 | なし | `BLOCKED` |
| `MARKET_DATA_READY` | 市場データ取得が完了 | Market Refresh が成功 | market refresh artifact | `FEATURE_READY` | 可 | 外部データ read | `BLOCKED`, `REVIEW_REQUIRED` |
| `FEATURE_READY` | 特徴量更新が完了 | 市場データと feature builder 入力が揃っている | feature artifact | `CURRENT_STATE_LOADED` | 可 | なし | `BLOCKED` |
| `CURRENT_STATE_LOADED` | Current State が確認済み | `persistent_ledger/state.json` と pending plan を固定 Path から読める | current state read manifest | `AI_INFERENCE_DONE`, `REVIEW_REQUIRED` | 可 | なし | `REVIEW_REQUIRED`, `BLOCKED` |
| `AI_INFERENCE_DONE` | AI 推論が完了 | Current State が安全に読め、特徴量が有効 | AI inference artifact | `DAILY_PLAN_CREATED` | 可 | なし | `BLOCKED` |
| `DAILY_PLAN_CREATED` | 日次売買計画が作成済み | AI 出力、Capital Allocation、Safety 入力が揃っている | `daily_plan/YYYY-MM-DD`, `order_plan/YYYY-MM-DD` | `PENDING_PROMOTED`, `APPROVAL_PENDING`, `BLOCKED` | 可 | なし | `BLOCKED`, `REVIEW_REQUIRED` |
| `PENDING_PROMOTED` | Submit 候補が固定 Path に昇格済み | promotion 条件を満たす daily plan がある | `pending_order_plan/pending_order_plan.json` | `APPROVAL_PENDING` | 条件付き | Current artifact 更新 | `BLOCKED`, `REVIEW_REQUIRED` |
| `APPROVAL_PENDING` | 承認待ち | pending plan と approval request が対応している | approval request / artifact draft | `APPROVED`, `BLOCKED`, `REVIEW_REQUIRED` | 可 | なし | `REVIEW_REQUIRED` |
| `APPROVED` | Submit 可能な承認済み状態 | approval hash、plan hash、期限、対象日が一致 | approval artifact, pending approval linkage | `SUBMITTING`, `BLOCKED`, `REVIEW_REQUIRED` | 可 | なし | `BLOCKED`, `REVIEW_REQUIRED` |
| `SUBMITTING` | Broker Submit 処理中 | `APPROVED` かつ二重送信 guard を通過 | submit attempt event | `SUBMITTED`, `POST_SEND_UNKNOWN`, `REVIEW_REQUIRED` | 不可 | Broker Order Submit | `POST_SEND_UNKNOWN`, `REVIEW_REQUIRED` |
| `SUBMITTED` | Broker へ送信済み | Broker 応答または送信済み記録がある | `persistent_ledger/orders.jsonl`, submitted order history | `MONITORING_FILL`, `REVIEW_REQUIRED` | 不可 | 送信済み状態の記録 | `REVIEW_REQUIRED` |
| `POST_SEND_UNKNOWN` | Submit 後の結果不明 | Broker Submit 中に応答不明、通信断、結果未確定 | `persistent_ledger/events.jsonl` | `REVIEW_REQUIRED`, `MONITORING_FILL` | Broker ReadOnly のみ可 | なし。再 Submit 禁止 | `REVIEW_REQUIRED` |
| `MONITORING_FILL` | 約定監視中 | Submit 済み注文または結果不明注文がある | broker orders / executions / positions snapshot | `LEDGER_UPDATED`, `REVIEW_REQUIRED` | 可 | Broker ReadOnly | `REVIEW_REQUIRED` |
| `LEDGER_UPDATED` | 約定・保有・現金が Ledger に反映済み | Broker Executions / Positions / Cash が確認済み | `persistent_ledger/*.jsonl`, `state.json` | `RECONCILED` | 条件付き | Ledger append | `REVIEW_REQUIRED` |
| `RECONCILED` | Ledger と Broker / plan が照合済み | Current State と History evidence が照合可能 | `reconciliation_result/YYYY-MM-DD` | `REPORT_READY`, `REVIEW_REQUIRED` | 可 | なし | `REVIEW_REQUIRED` |
| `REPORT_READY` | Report / payload 生成完了 | Reconcile または state_unknown report 条件を満たす | reports, notification payload | `IDLE`, `REVIEW_REQUIRED` | 可 | payload 生成のみ。送信は別処理 | `REVIEW_REQUIRED` |
| `REVIEW_REQUIRED` | 人間確認が必要 | 不整合、結果不明、Current State 不明、安全停止 | review event / review queue | `IDLE`, `BLOCKED`, recovery 後の該当 state | Broker ReadOnly / Report のみ可 | なし | `HALT` |
| `BLOCKED` | 条件未充足で停止 | 入力欠損、承認不成立、guard failure | blocked manifest / event | `IDLE`, recovery 後の該当 state | 可 | なし | `HALT` |
| `HALT` | 異常停止 | 継続不可、未知状態、重大不整合 | halt event | manual recovery のみ | 不可 | なし | なし |

Pending Order Plan の `CONSUMED` は Runtime 全体 state ではなく、Submit 対象 artifact の lifecycle state である。`SUBMITTED`、`POST_SEND_UNKNOWN`、または人間が明示的に取り下げた `REVIEW_REQUIRED` の後に pending plan を `CONSUMED` にできる。`CONSUMED` は再実行時の二重 Submit 防止に使い、`CONSUMED` から `SUBMITTING` へ戻してはならない。

## 8. Runtime Component Architecture

Runtime Architecture v2 は、単一の巨大処理ではなく、複数の Runtime Component で構成される制御システムである。各 Component は、役割、入出力、Current State への読み書き、副作用、再実行性、依存関係を明確に持つ。

AI 判断そのものは Runtime Component に混ぜない。AI Execution Runtime は AI を呼び出して結果を受け取るだけであり、Candidate AI、Opportunity AI、Position Management AI、Capital Allocation、Safety の判断ロジックを Runtime 内で再実装しない。Safety Runtime / Operation Guard Runtime を置く場合も、Safety の投資判断ロジックを Runtime に移植しない。

Runtime Component Architecture は責務設計であり、既存 module 名をそのまま継承するものではない。既存 module は legacy implementation として扱い、v2 実装時に置換・隔離・再利用可否を個別判断する。Component と実装 module の対応は、Phase13-F 以降の詳細設計・実装計画で決める。

### 8.1 Component 定義

#### Runtime Orchestrator

- 役割: Runtime 全体の実行順序を制御し、各 Component を正しい順番で呼び出し、Runtime State Machine を進める。
- 入力: runtime mode、business date、run request、current runtime state、recovery / review status。
- 出力: run manifest、runtime_id、run_id、state transition record、blocked / review / halt event。
- 読む Current State: `runtime_state/current_state.json`、`persistent_ledger/state.json`、`pending_order_plan/pending_order_plan.json`。
- 書く Current State: `runtime_state/current_state.json`、`persistent_ledger/events.jsonl`。
- History / Evidence: run manifest、state transition history。
- Derived output: orchestration summary for report。
- 再実行可否: 条件付き。副作用を持つ Component の呼び出し前後の state を確認して入口を決める。
- 副作用有無: 直接の外部副作用なし。ただし Submit Runtime / Notification Runtime の呼び出しを制御する。
- 依存する Component: Current State Runtime、Runtime State Machine Runtime、Operation Guard Runtime。
- 依存される Component: すべての Runtime Component。
- やらないこと: AI 判断をしない。注文内容を独自に決めない。保有や資産を独自計算しない。

#### Market Data Runtime

- 役割: 市場データ取得・更新を管理する。
- 入力: business_date、market calendar、J-Quants / market data source。
- 出力: market data artifact、market refresh manifest。
- 読む Current State: runtime mode、market calendar state。
- 書く Current State: なし。
- History / Evidence: `market_refresh/YYYY-MM-DD`、market refresh manifest。
- Derived output: market refresh summary。
- 再実行可否: 再実行可能。
- 副作用有無: 外部データ read のみ。Submit なし。
- 依存する Component: Runtime Orchestrator。
- 依存される Component: Feature Runtime、AI Execution Runtime、Report Runtime。
- やらないこと: 投資判断しない。Submit しない。Current asset state を更新しない。

#### Feature Runtime

- 役割: AI が使う特徴量を生成・更新する。
- 入力: market data、listed info、feature config。
- 出力: feature artifacts、feature refresh manifest。
- 読む Current State: なし。
- 書く Current State: なし。
- History / Evidence: feature refresh artifact、feature manifest。
- Derived output: feature freshness summary。
- 再実行可否: 再実行可能。
- 副作用有無: なし。
- 依存する Component: Market Data Runtime。
- 依存される Component: AI Execution Runtime、Planning Runtime、Report Runtime。
- やらないこと: 銘柄を買う判断はしない。注文はしない。

#### Current State Runtime

- 役割: Runtime が実行時に読む Current State を固定 Path から取得し、欠損・古さ・不明状態を検知する。
- 入力: fixed Current State paths、runtime mode、business date。
- 出力: `current_state_read_result`、`state_missing`、`current_positions_unknown`、`cash_unknown`、`buying_power_unknown`。
- 読む Current State: `persistent_ledger/state.json`、`pending_order_plan/pending_order_plan.json`、`runtime_state/current_state.json`、`notification_delivery/delivery_ledger.jsonl`。
- 書く Current State: `runtime_state/current_state.json` の read result / state flags、必要に応じて `persistent_ledger/events.jsonl`。
- History / Evidence: current state read manifest。
- Derived output: state readiness summary。
- 再実行可否: 再実行可能。
- 副作用有無: なし。
- 依存する Component: Runtime Orchestrator。
- 依存される Component: AI Execution Runtime、Planning Runtime、Approval Runtime、Submit Runtime、Reconcile Runtime、Report Runtime、Audit Runtime。
- 重要原則: Current State 不明を保有 0 として扱わない。日付別 artifact から Current を推測しない。

#### AI Execution Runtime

- 役割: Candidate AI / Opportunity AI / Position Management AI / Capital Allocation / Safety を呼び出し、判断結果を受け取る。
- 入力: features、current positions、cash / buying power、existing pending state、safety context。
- 出力: AI inference result、candidate result、opportunity ranking、position management result、capital allocation result、safety result。
- 読む Current State: `persistent_ledger/state.json`、`pending_order_plan/pending_order_plan.json`。
- 書く Current State: なし。
- History / Evidence: AI inference artifact、safety result artifact。
- Derived output: AI decision summary for report。
- 再実行可否: 再実行可能。
- 副作用有無: なし。
- 依存する Component: Feature Runtime、Current State Runtime。
- 依存される Component: Planning Runtime、Approval Runtime、Report Runtime。
- 重要原則: AI ロジックを Runtime 内で再実装しない。AI 判断を Runtime 側で恣意的に変更しない。Runtime は AI を利用するが、AI そのものではない。

#### Planning Runtime

- 役割: AI 出力、Current State、資金制約、Broker 制約、Safety 制約を使って売買計画を作る。
- 入力: AI Execution Runtime output、`persistent_ledger/state.json`、cash / buying_power、current positions、safety result、broker constraints。
- 出力: daily_plan、order_plan history、pending promotion candidate。
- 読む Current State: `persistent_ledger/state.json`、`pending_order_plan/pending_order_plan.json`。
- 書く Current State: 条件を満たす場合のみ `pending_order_plan/pending_order_plan.json` の promotion candidate / pending state。
- History / Evidence: `daily_plan/YYYY-MM-DD`、`order_plan/YYYY-MM-DD`。
- Derived output: planning summary for report。
- 再実行可否: 再実行可能。Pending promotion は条件付き再実行。
- 副作用有無: Broker / notification 副作用なし。
- 依存する Component: AI Execution Runtime、Current State Runtime、Broker Runtime、Safety Runtime。
- 依存される Component: Approval Runtime、Report Runtime、Audit Runtime。
- 重要原則: Runtime は銘柄数の固定上限を持たない。資金・買付余力・Broker 制約・Safety 制約・重複注文防止を制御する。

#### Approval Runtime

- 役割: 売買計画を承認可能な形に整理し、承認状態を Pending Order Plan へリンクする。
- 入力: planning result、pending_order_plan、safety result、current asset state、approval policy。
- 出力: approval_request、approval_artifact、pending approval linkage。
- 読む Current State: `pending_order_plan/pending_order_plan.json`、`persistent_ledger/state.json`。
- 書く Current State: `pending_order_plan/pending_order_plan.json` の approval linkage。
- History / Evidence: `approval_request/YYYY-MM-DD`、`approval_artifact/YYYY-MM-DD`。
- Derived output: approval summary for report。
- 再実行可否: 再実行可能。
- 副作用有無: なし。
- 依存する Component: Planning Runtime、Current State Runtime、Safety Runtime、Operation Guard Runtime。
- 依存される Component: Submit Runtime、Report Runtime、Audit Runtime。
- 重要原則: `approval_artifact/YYYY-MM-DD` は History / Evidence。Submit 対象は pending_order_plan のみ。

#### Submit Runtime

- 役割: 承認済み Pending Order Plan を Broker 注文へ変換し、Submit する。
- 入力: `pending_order_plan/pending_order_plan.json`、approval linkage、current state、safety / operation guard、idempotency guard。
- 出力: submit attempt event、submitted_orders history、`persistent_ledger/orders.jsonl`、pending state update。
- 読む Current State: `pending_order_plan/pending_order_plan.json`、`persistent_ledger/state.json`、`persistent_ledger/orders.jsonl`、`runtime_state/current_state.json`。
- 書く Current State: `persistent_ledger/orders.jsonl`、`persistent_ledger/events.jsonl`、`pending_order_plan/pending_order_plan.json` state。
- History / Evidence: `submitted_orders/YYYY-MM-DD`、submit attempt record。
- Derived output: submit summary for report。
- 再実行可否: 非冪等。二重 Submit 禁止。
- 副作用有無: Broker Order Submit。Submit Runtime だけが Broker Order Submit の外部副作用を持つ。
- 依存する Component: Approval Runtime、Current State Runtime、Broker Runtime、Operation Guard Runtime。
- 依存される Component: Execution / Fill Runtime、Ledger Runtime、Reconcile Runtime、Report Runtime、Recovery / Review Runtime。
- 重要原則: `POST_SEND_UNKNOWN` は自動再送禁止。Submit 対象は pending_order_plan のみ。

#### Broker Runtime

- 役割: Broker との接続、ReadOnly 取得、注文状態取得を担当する。
- 入力: broker credentials from secure config、runtime mode、business_date、submitted order refs。
- 出力: broker account snapshot、broker orders、broker executions、broker positions、broker cash / buying power、broker readonly report。
- 読む Current State: submitted order refs from `persistent_ledger/orders.jsonl`、runtime mode。
- 書く Current State: 原則なし。Broker ReadOnly 結果は Ledger Runtime が Current へ反映する。
- History / Evidence: `broker_orders/YYYY-MM-DD`、`broker_executions/YYYY-MM-DD`、`broker_positions/YYYY-MM-DD`、broker cash snapshot。
- Derived output: broker readonly summary。
- 再実行可否: ReadOnly は再実行可能。Broker Order Submit は Submit Runtime 経由のみ。
- 副作用有無: ReadOnly は外部 read。Broker Order Submit は Submit Runtime が制御する。
- 依存する Component: Runtime Orchestrator、Submit Runtime。
- 依存される Component: Execution / Fill Runtime、Ledger Runtime、Asset Runtime、Reconcile Runtime、Recovery / Review Runtime。
- 重要原則: Production では Broker Positions / Executions / Cash を正規 SoT にする。

#### Execution / Fill Runtime

- 役割: 注文が約定したか、部分約定か、未約定か、失効かを分類する。
- 入力: submitted orders、broker orders、broker executions、broker positions。
- 出力: fill classification、execution events、review_required reasons。
- 読む Current State: `persistent_ledger/orders.jsonl`、`pending_order_plan/pending_order_plan.json`。
- 書く Current State: `persistent_ledger/events.jsonl` の fill / review event。
- History / Evidence: fill classification artifact、broker evidence links。
- Derived output: fill summary for report。
- 再実行可否: 再実行可能。execution dedup が前提。
- 副作用有無: なし。
- 依存する Component: Submit Runtime、Broker Runtime。
- 依存される Component: Ledger Runtime、Asset Runtime、Reconcile Runtime、Report Runtime。
- 重要原則: 注文と約定を混同しない。注文受付は資産ではない。約定して初めて保有になる。

#### Ledger Runtime

- 役割: 注文、約定、保有、現金、Runtime event を Persistent Ledger へ反映する。
- 入力: submitted orders、broker executions、broker positions、broker cash / buying power、fill events、manual migration、review events。
- 出力: updated Persistent Ledger、ledger append result、dedup result。
- 読む Current State: `persistent_ledger/*.jsonl`、`persistent_ledger/state.json`。
- 書く Current State: `persistent_ledger/orders.jsonl`、`persistent_ledger/executions.jsonl`、`persistent_ledger/positions.jsonl`、`persistent_ledger/cash_history.jsonl`、`persistent_ledger/events.jsonl`、`persistent_ledger/state.json`。
- History / Evidence: ledger update manifest、migration event。
- Derived output: ledger summary for report。
- 再実行可否: 条件付き。dedup key で二重反映を防止する。
- 副作用有無: Current Ledger append。外部副作用なし。
- 依存する Component: Execution / Fill Runtime、Broker Runtime、Recovery / Review Runtime、Migration Runtime。
- 依存される Component: Asset Runtime、Reconcile Runtime、Report Runtime、Audit Runtime。
- 重要原則: raw request / raw response / secret は保存しない。

#### Asset Runtime

- 役割: 現在保有、現金、買付余力、総資産を Current Asset State として整理する。
- 入力: `persistent_ledger/state.json`、broker positions、broker cash / buying power、executions、cash history。
- 出力: current positions、cash、buying power、total equity、market value、unrealized pnl、asset source summary、review_required flags。
- 読む Current State: `persistent_ledger/state.json`、`persistent_ledger/positions.jsonl`、`persistent_ledger/cash_history.jsonl`、`persistent_ledger/executions.jsonl`。
- 書く Current State: `persistent_ledger/state.json`、必要に応じて `runtime_state/current_state.json` の asset readiness。
- History / Evidence: asset state calculation manifest。
- Derived output: asset summary for report。
- 再実行可否: 再実行可能。
- 副作用有無: なし。
- 依存する Component: Ledger Runtime、Broker Runtime。
- 依存される Component: Planning Runtime、Approval Runtime、Reconcile Runtime、Report Runtime、Audit Runtime。
- 重要原則: 資産は注文ではなく約定・保有・現金から構成する。Asset State は Position と Cash が更新されないと確定しない。

#### Reconcile Runtime

- 役割: Broker 状態、Persistent Ledger、Pending Plan、Submitted Orders、Report 用情報の整合を確認する。
- 入力: `persistent_ledger/state.json`、broker orders、broker executions、broker positions、submitted_orders、pending_order_plan、history artifacts。
- 出力: reconciliation_result、broker divergence、ledger divergence、review_required reasons。
- 読む Current State: `persistent_ledger/state.json`、`persistent_ledger/orders.jsonl`、`pending_order_plan/pending_order_plan.json`。
- 書く Current State: `persistent_ledger/events.jsonl` の divergence / review event。
- History / Evidence: `reconciliation_result/YYYY-MM-DD`。
- Derived output: reconcile summary for report。
- 再実行可否: 再実行可能。
- 副作用有無: なし。
- 依存する Component: Broker Runtime、Ledger Runtime、Asset Runtime、Current State Runtime。
- 依存される Component: Report Runtime、Audit Runtime、Recovery / Review Runtime。

#### Report Runtime

- 役割: Runtime の判断、実行、約定、保有、現金、資産、Safety、Review Required を人間に説明する Report を生成する。
- 入力: `persistent_ledger/state.json`、`pending_order_plan/pending_order_plan.json`、`persistent_ledger/orders.jsonl`、`persistent_ledger/executions.jsonl`、`persistent_ledger/positions.jsonl`、`persistent_ledger/cash_history.jsonl`、`persistent_ledger/events.jsonl`、History / Evidence links、reconciliation_result。
- 出力: `reports/YYYY-MM-DD/public_report.md`、`reports/YYYY-MM-DD/internal_report.md`、`reports/YYYY-MM-DD/safety_report.md`、`daily_report_refs/YYYY-MM-DD/daily_report_refs.json`、notification payload、blog draft、LINE payload、Discord payload。
- 読む Current State: Persistent Ledger、Pending Order Plan、Runtime state。
- 書く Current State: なし。
- History / Evidence: report refs、evidence links。
- Derived output: reports、notification payload、blog draft。
- 再実行可否: 再実行可能。
- 副作用有無: payload 生成のみ。Notification Send は行わない。
- 依存する Component: Asset Runtime、Reconcile Runtime、Ledger Runtime、Planning Runtime、Approval Runtime、Submit Runtime、Execution / Fill Runtime。
- 依存される Component: Notification Runtime、Audit Runtime、Recovery / Review Runtime。
- 重要原則: Report は Runtime の説明責務。Report は Current State から生成する。Report は Derived であり、Runtime Current 入力ではない。Report は注文・約定・保有・資産を分けて表示し、source と `review_required` を明示する。

#### Notification Runtime

- 役割: Report から通知 payload を生成し、必要に応じて外部通知を送る。
- 入力: report refs、notification payload、delivery ledger、notification policy。
- 出力: notification payload、`notification_delivery/delivery_ledger.jsonl`、notification result。
- 読む Current State: `notification_delivery/delivery_ledger.jsonl`、report refs。
- 書く Current State: `notification_delivery/delivery_ledger.jsonl`。
- History / Evidence: notification result、delivery attempt record。
- Derived output: LINE payload、Discord payload、other notification payload。
- 再実行可否: payload 生成は再実行可能。Notification Send は非冪等。
- 副作用有無: LINE / Discord / other external notification send。
- 依存する Component: Report Runtime、Delivery Ledger。
- 依存される Component: Audit Runtime、Recovery / Review Runtime。
- 重要原則: payload 生成と送信を分離する。送信は非冪等。Delivery Ledger で二重送信を防ぐ。

#### Audit Runtime

- 役割: Runtime 全体が設計原則に従っているか監査する。
- 入力: current state、history artifacts、derived artifacts、runtime events、reconciliation result。
- 出力: audit_result、audit findings、review_required。
- 読む Current State: `persistent_ledger/state.json`、`runtime_state/current_state.json`、`pending_order_plan/pending_order_plan.json`。
- 書く Current State: `persistent_ledger/events.jsonl` の audit / review event。
- History / Evidence: audit result、audit evidence links。
- Derived output: audit summary for report。
- 再実行可否: 再実行可能。
- 副作用有無: なし。
- 依存する Component: Current State Runtime、Reconcile Runtime、Report Runtime、Ledger Runtime。
- 依存される Component: Recovery / Review Runtime、Runtime Orchestrator。
- 重要原則: Audit は異常検知と説明のために使う。Audit result を Submit 対象選択元にしない。

#### Recovery / Review Runtime

- 役割: `REVIEW_REQUIRED`、`POST_SEND_UNKNOWN`、`BROKER_DIVERGENCE`、`LEDGER_DIVERGENCE` などの復旧手順を管理する。
- 入力: review_required events、broker readonly result、reconciliation result、manual review decision、migration proposal。
- 出力: review queue、recovery action record、manual migration event、resolved / unresolved status。
- 読む Current State: `persistent_ledger/events.jsonl`、`runtime_state/current_state.json`、`persistent_ledger/state.json`、Delivery Ledger。
- 書く Current State: `persistent_ledger/events.jsonl`、`runtime_state/current_state.json`、必要に応じて migration proposal state。
- History / Evidence: review queue、recovery record、manual decision evidence。
- Derived output: review summary for report。
- 再実行可否: 条件付き。
- 副作用有無: manual migration apply は非冪等。Broker Order Submit は行わない。
- 依存する Component: Audit Runtime、Reconcile Runtime、Broker Runtime、Ledger Runtime、Report Runtime。
- 依存される Component: Runtime Orchestrator、Ledger Runtime、Migration Runtime。
- 重要原則: 結果不明を自動 Submit で解消しない。復旧は Broker ReadOnly、Reconcile、Manual Review、Ledger migration の順に行う。

### 8.2 Optional Control Components

#### Safety Runtime

- 役割: Safety の結果を Runtime 制御に接続し、停止、Review Required、禁止注文を Runtime State Machine に反映する。
- 入力: Safety result、current asset state、pending plan、runtime context。
- 出力: safety control decision、review_required reason。
- 読む Current State: `persistent_ledger/state.json`、`pending_order_plan/pending_order_plan.json`。
- 書く Current State: `persistent_ledger/events.jsonl`。
- 再実行可否: 再実行可能。
- 副作用有無: なし。
- 重要原則: Safety の投資判断ロジックを Runtime に再実装しない。

#### Operation Guard Runtime

- 役割: business day、market open、run lock、duplicate order guard、emergency stop などの運用 guard を管理する。
- 入力: runtime context、calendar、lock state、safety / emergency state。
- 出力: allow / block / review decision。
- 読む Current State: `runtime_state/current_state.json`、`persistent_ledger/events.jsonl`。
- 書く Current State: `runtime_state/current_state.json`、`persistent_ledger/events.jsonl`。
- 再実行可否: 再実行可能。
- 副作用有無: なし。

#### Migration Runtime

- 役割: legacy artifact から Persistent Ledger への移行提案、manual migration、migration evidence を管理する。
- 入力: legacy artifact、manual review decision、migration proposal。
- 出力: migration event、migration record、ledger append proposal。
- 読む Current State: `persistent_ledger/state.json`、`persistent_ledger/migrations.jsonl`。
- 書く Current State: `persistent_ledger/migrations.jsonl`、`persistent_ledger/events.jsonl`、承認済みの場合のみ ledger records。
- 再実行可否: dry-run は再実行可能。apply は非冪等。
- 副作用有無: manual migration apply。

#### Runtime State Machine Runtime

- 役割: Runtime state の allowed transition、invalid transition、HALT / BLOCKED / REVIEW_REQUIRED を管理する。
- 入力: current runtime state、component result、guard result。
- 出力: next state、transition record。
- 読む Current State: `runtime_state/current_state.json`。
- 書く Current State: `runtime_state/current_state.json`、`persistent_ledger/events.jsonl`。
- 再実行可否: 条件付き。
- 副作用有無: なし。

### 8.3 Component 依存関係

標準的な成功経路の依存関係:

```text
Runtime Orchestrator
↓
Market Data Runtime
↓
Feature Runtime
↓
Current State Runtime
↓
AI Execution Runtime
↓
Planning Runtime
↓
Approval Runtime
↓
Submit Runtime
↓
Broker Runtime
↓
Execution / Fill Runtime
↓
Ledger Runtime
↓
Asset Runtime
↓
Reconcile Runtime
↓
Report Runtime
↓
Notification Runtime
```

ただし、Runtime v2 は単純な一本道ではない。Broker ReadOnly、Reconcile、Report、Audit、Recovery は、異常時、再実行時、結果不明時、Review Required 時にも呼び出される。

横断的な依存:

- Runtime Orchestrator はすべての Component 呼び出しを制御する。
- Current State Runtime は Planning、Approval、Submit、Reconcile、Report、Audit の前提になる。
- Operation Guard Runtime は Submit Runtime と Notification Runtime の外部副作用前に必ず確認される。
- Audit Runtime と Recovery / Review Runtime は `REVIEW_REQUIRED`、`POST_SEND_UNKNOWN`、divergence、stale state の経路で呼び出される。
- Report Runtime は Submit 成功時だけでなく、BLOCKED、REVIEW_REQUIRED、state_unknown の場合にも説明責務を持つ。

### 8.4 Current State 依存関係

Runtime v2 の Current State 依存関係は次の通り。

```text
pending_order_plan
↓
submit attempt
↓
persistent_ledger/orders.jsonl
↓
broker_orders / broker_executions / broker_positions
↓
persistent_ledger/executions.jsonl
↓
persistent_ledger/positions.jsonl
↓
persistent_ledger/cash_history.jsonl
↓
persistent_ledger/state.json
↓
report / notification / audit
```

重要原則:

- Asset State は Position と Cash が更新されないと確定しない。
- Report は Asset State と Review flags を元に生成する。
- Notification は Report payload を元に生成するが、送信は Delivery Ledger で管理する。
- `submitted_orders` と `broker_orders` は注文状態であり、現在保有 SoT ではない。
- `persistent_ledger/state.json` が現在資産状態の中心である。

## 9. Current / History / Derived の分類

Runtime Architecture v2 では、保存物を Current / History / Derived に分ける。

Runtime が生成・判断・管理するデータを、Phase13 用ディレクトリや日付別ディレクトリだけに閉じ込めない。Phase や日付は、履歴・証跡・監査用の属性として使ってよい。ただし、Runtime が実行時に読むべき Current データは、役割ごとの固定 Path で管理する。

方針:

- Phase13 用の一時保存場所を Runtime Current として使わない。
- `YYYY-MM-DD` ディレクトリを Runtime Current として使わない。
- 日付別 artifact は History / Evidence として扱う。
- Runtime が判断・実行に使う Current データは固定 Path で管理する。
- Phase 番号は開発管理上の単位であり、Runtime の実行時 SoT ではない。
- 日付は履歴属性であり、Runtime 実行対象の主キーではない。

### Current

Current は現在の実行対象・現在状態であり、Runtime が固定 Path で読む。

例:

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

Current は Runtime の判断、承認、Submit、Reconcile、Report、Audit の基準になる。

Runtime 生成物としての Current artifacts:

```text
pending_order_plan
persistent_ledger
runtime_state/current_state
notification_delivery/delivery_ledger
```

### History

History は証跡・履歴であり、Runtime の実行対象として自動選択しない。

例:

```text
order_plan/YYYY-MM-DD
approval_artifact/YYYY-MM-DD
submitted_orders/YYYY-MM-DD
broker_orders/YYYY-MM-DD
broker_executions/YYYY-MM-DD
broker_positions/YYYY-MM-DD
reconciliation_result/YYYY-MM-DD
reports/YYYY-MM-DD
```

History は監査、説明、差分確認、再現性検証に使う。Submit 対象や現在保有の推測元として直接使ってはならない。

Runtime 生成物としての History / Evidence artifacts:

```text
order_plan/YYYY-MM-DD
approval_artifact/YYYY-MM-DD
submitted_orders/YYYY-MM-DD
broker_* /YYYY-MM-DD
reconciliation_result/YYYY-MM-DD
```

### Derived

Derived は表示・通知・監査用の派生成果物であり、Runtime の Current 入力にしない。

例:

```text
reports
daily_report_refs
notifications
audit_result
blog
LINE payload
Discord payload
```

Derived は人間や外部通知向けの表現であり、Runtime の source of truth ではない。Report は Current State から生成されるが、Report 自体は Current State ではない。

Runtime 生成物としての Derived artifacts:

```text
reports/YYYY-MM-DD
daily_report_refs/YYYY-MM-DD
notification payload
blog draft
LINE payload
Discord payload
audit_result
```

Derived は Runtime Current 入力にしない。日付別 artifact は History / Evidence または Derived として保持してよいが、Runtime Current の決定元として自動選択しない。

## 10. Current State 設計

Runtime v2 の Current State は固定 Path で管理する。

Runtime Architecture v2 では、Current State の固定 Path と原則を定義する。ただし、個別 Current State の schema、required fields、missing / stale / unknown 判定、validation policy は Phase13-F Current State Contract 詳細設計で定義する。Phase13-F に進む前に、本設計書レビューを完了させる。

Phase13-F に defer する詳細:

- 各 Current State の `schema_version`
- required fields
- optional fields
- missing 判定
- stale 判定
- unknown 判定
- confirmed empty 判定
- 各 Current State の読み書き Component 別 contract
- validation policy
- architecture test policy

| State | Path | 用途 |
| --- | --- | --- |
| Submit 対象 | `pending_order_plan/pending_order_plan.json` | 次に Submit してよい注文計画 |
| 現在保有・現金・総資産 | `persistent_ledger/state.json` | Daily Plan、Approval、Report、Reconcile、Audit の基準 |
| 注文履歴 | `persistent_ledger/orders.jsonl` | 送信済み注文、Broker order 状態、重複検知 |
| 約定履歴 | `persistent_ledger/executions.jsonl` | 約定反映、現金・保有更新の根拠 |
| 保有履歴 | `persistent_ledger/positions.jsonl` | 保有状態の履歴と source 管理 |
| 現金履歴 | `persistent_ledger/cash_history.jsonl` | 現金、買付余力、資産評価の履歴 |
| Runtime events | `persistent_ledger/events.jsonl` | REVIEW_REQUIRED、POST_SEND_UNKNOWN、migration、fallback など |
| Runtime current state | `runtime_state/current_state.json` | Runtime State Machine の現在状態 |
| Notification delivery ledger | `notification_delivery/delivery_ledger.jsonl` | Notification Send の二重送信防止 |

Current State は、日付別 artifact の探索ではなく、固定 Path の読み取りで決定する。

Current State が欠損、古い、不明、または source 不明の場合、Runtime は安全側に倒す。保有情報が読めないことを「保有 0」と解釈してはならない。

Current State 不明時の必須 flags:

```text
state_missing=true
current_state_confirmed_empty=false
current_positions_unknown=true
cash_unknown=true
buying_power_unknown=true
```

これらのいずれかが true となる場合の扱い:

- Current State が不明な場合、保有 0 として扱わない。
- Current State が不明な場合、新規 BUY 計画は `BLOCKED` または `REVIEW_REQUIRED` とする。
- Current State が不明な場合、Approval は通さない。
- Current State が不明な場合、Submit は禁止する。
- Current State が不明な場合、Report には `state_unknown` を明示する。
- source が不明、古い、または `production_equivalent=false` の場合は、Demo / Production の context に応じて `REVIEW_REQUIRED` を付ける。

`current_state_confirmed_empty=true` とできるのは、Broker Positions、Broker Cash / Buying Power、または正規 migration により「保有なし・現金確認済み」が明示的に確認された場合のみである。`persistent_ledger/state.json` が存在しない、空、古い、source 不明であることは confirmed empty ではない。

### 10.1 Current Writer Contract

Runtime v2 の Current Object は Single Writer Rule に従う。各 Current は必ず 1 つの writer component だけを持ち、Reconcile、Report、Audit は Current Writer にならない。

| Current | Writer | Reader | Writer 禁止 Component |
| --- | --- | --- | --- |
| `runtime_state/current_state.json` | Runtime State Runtime | Runtime Orchestrator, Report Builder, Audit Runtime | Reconcile, Report, Audit, Submit 以外のBroker連携 |
| `pending_order_plan/pending_order_plan.json` | Pending Runtime | Approval Runtime, Submit Runtime, Report Builder | Planning, Approval, Reconcile, Report, Audit |
| `persistent_ledger/orders.jsonl` | Ledger Runtime | Reconciliation Runtime, Report Builder, Audit Runtime | Reconcile, Report, Audit |
| `persistent_ledger/executions.jsonl` | Ledger Runtime | Reconciliation Runtime, Report Builder, Audit Runtime | Reconcile, Report, Audit |
| `persistent_ledger/positions.jsonl` | Ledger Runtime | Current State Reader, Report Builder, Audit Runtime | Reconcile, Report, Audit |
| `persistent_ledger/cash_history.jsonl` | Ledger Runtime | Current State Reader, Report Builder, Audit Runtime | Reconcile, Report, Audit |
| `persistent_ledger/events.jsonl` | Ledger Runtime | Report Builder, Audit Runtime | Reconcile, Report, Audit |
| `persistent_ledger/state.json` | Asset Runtime | Current State Reader, Pending Runtime, Approval Runtime, Submit Runtime, Report Builder | Reconcile, Report, Audit, Broker ReadOnly |
| `notification_delivery/delivery_ledger.jsonl` | Notification Runtime | Notification Runtime, Report Builder, Audit Runtime | Report, Audit, Reconcile |

Atomic update order:

```text
Ledger append
↓
Asset rebuild
↓
persistent_ledger/state.json
↓
Report
↓
Notification Payload
```

禁止する更新順序:

```text
Report -> Current更新
Reconcile -> Current更新
Audit -> Current更新
```

Reconcile Runtime の責務は `Read`、`Compare`、`Finding`、`ReviewRequired`、`Evidence` に限定する。Reconcile Runtime は Current Writer ではなく、`persistent_ledger/state.json`、`pending_order_plan/pending_order_plan.json`、または append-only ledger を直接更新しない。

## 11. Pending Order Plan 設計

注文実行対象は `pending_order_plan/pending_order_plan.json` のみに固定する。

禁止する読み方:

- `order_plan/YYYY-MM-DD` から直接 Submit する。
- `approval_artifact/YYYY-MM-DD` から直接 Submit 対象を推測する。
- 日付別 artifact から最新らしい Plan を探して Submit する。

Pending Order Plan は、Daily Plan から昇格された Current artifact である。History の `order_plan/YYYY-MM-DD` と `approval_artifact/YYYY-MM-DD` は証跡として参照されるが、Submit 対象の選択権を持たない。

Pending Order Plan には少なくとも以下の情報を持たせる。

- `pending_plan_id`
- `state`
- `environment`
- `created_at`
- `updated_at`
- `plan_created_date`
- `intended_submit_date`
- `target_session_date`
- `source_order_plan.path`
- `source_order_plan.hash`
- `approval.path`
- `approval.hash`
- `approval.status`
- `approved_item_ids`
- `approval_expires_at`
- `items`
- `submit_constraints`
- `promotion`
- `consume`
- `raw_request_saved=false`
- `raw_response_saved=false`
- `secret_saved=false`

代表的な状態は次の通り。

```text
PENDING_APPROVAL
APPROVED
SUBMITTING
SUBMITTED
CONSUMED
EXPIRED
BLOCKED
REVIEW_REQUIRED
```

Submit は `state == APPROVED` かつ対象日、承認 hash、source order plan hash、承認期限、promotion 条件を満たす場合のみ許可する。

`CONSUMED` の扱い:

- `CONSUMED` は Submit 対象として消費済みであることを示す。
- `CONSUMED` の pending plan は再 Submit してはならない。
- `SUBMITTED` になった plan は、送信済み記録と対応付けて `CONSUMED` にできる。
- `POST_SEND_UNKNOWN` の plan は、自動再送せず、Broker ReadOnly と Review Required の証跡を残したうえで `CONSUMED` または `REVIEW_REQUIRED` に固定する。
- `REVIEW_REQUIRED` の plan を再度 Submit 対象に戻すには、人間承認と新しい pending plan id が必要である。

## 12. Submit 非冪等設計

Submit / Broker Order は非冪等処理である。

原則:

- 同じ注文を二重送信してはいけない。
- 送信済み注文を再送してはいけない。
- 送信中に失敗した場合、自動再送してはいけない。
- 結果不明の場合は Broker ReadOnly 確認へ進める。
- `POST_SEND_UNKNOWN` は `REVIEW_REQUIRED` とする。

Submit 直前には、以下を確認する。

- `pending_order_plan/pending_order_plan.json` が存在する。
- `state == APPROVED` である。
- `intended_submit_date` と `target_session_date` が Submit 実行日と整合する。
- 承認 artifact の hash が pending plan に記録された hash と一致する。
- source order plan の hash が pending plan に記録された hash と一致する。
- `approved_item_ids` が pending plan の item に含まれる。
- `approval_expires_at` が有効である。
- 同じ `pending_plan_id` または item の Submit 済み記録が `persistent_ledger/orders.jsonl` に存在しない。
- Safety または Operation Guard が停止状態ではない。

Submit 後は、Broker からの結果に応じて `persistent_ledger/orders.jsonl` と `pending_order_plan` の state を更新する。ただし、結果不明時に同じ Broker Order を自動再送しない。

### 12.1 注文・約定・保有・資産の分離

Runtime Architecture v2 では、注文、約定、保有、資産を明確に分離する。

注文は、Broker へ「買いたい / 売りたい」と依頼した状態である。注文済みであっても、まだ資産ではない。注文は以下の状態を取り得る。

```text
未送信
送信中
受付済み
部分約定
全部約定
失効
取消
結果不明
```

約定は、実際に売買が成立した状態である。買い注文が約定して初めて、その銘柄は保有資産になる。売り注文が約定して初めて、その銘柄は保有資産から減る。

保有は、約定結果が反映された現在の株式ポジションである。保有は注文計画や注文受付から直接作らない。保有は Broker Executions / Broker Positions / Persistent Ledger により確定・管理する。

資産は、保有株式、現金、買付余力、未約定注文による拘束予定金額を含めた現在状態である。資産は `persistent_ledger/state.json` を中心に管理する。

原則:

- 注文は資産ではない。
- 注文受付は資産ではない。
- 買い注文は約定して初めて保有になる。
- 売り注文は約定して初めて保有から減る。
- 現在資産は注文計画や注文受付ではなく、約定・Broker Positions・Persistent Ledger で管理する。
- `submitted_orders` は注文履歴であり、現在保有の SoT ではない。
- `broker_orders` は注文状態であり、Production では現在保有確定の SoT ではない。
- `broker_executions` / `broker_positions` が保有確定の正規根拠である。
- `persistent_ledger` は約定・保有・現金変化を反映した現在資産状態を管理する。

概念上の流れ:

```text
Order
↓
Execution
↓
Position
↓
Asset State
```

Runtime artifact 上の対応:

```text
submitted_orders
↓
broker_orders
↓
broker_executions
↓
persistent_ledger/positions.jsonl
↓
persistent_ledger/state.json
```

Demo で Broker Orders fallback を使う場合も、必ず以下を付ける。

```text
source=broker_orders_fallback
review_required=true
production_equivalent=false
```

Production では Broker Orders fallback を現在保有確定に使わない。

## 13. 約定監視設計

約定監視は Broker ReadOnly を使って行う。

約定監視の役割:

- Broker Orders の状態を読む。
- Broker Executions を読む。
- Broker Positions を読む。
- Broker Cash / Buying Power を読む。
- Submit 済み注文と Broker 側状態を照合する。
- 約定、部分約定、取消、失効、結果不明を分類する。
- 約定結果を Persistent Ledger に反映する。

約定監視は再実行可能である。同じ Broker execution を複数回読んでも、`execution_key`、hash、Broker id hash などで重複排除し、保有と現金を二重更新しない。

結果が不明な場合は `events.jsonl` に `POST_SEND_UNKNOWN` または `REVIEW_REQUIRED` を記録し、自動 Submit ではなく Review / Broker ReadOnly 確認へ進める。

## 14. Persistent Ledger 設計

Persistent Ledger は Runtime v2 の Current State 中心である。

中心 Path:

```text
persistent_ledger/state.json
```

補助 Path:

```text
persistent_ledger/orders.jsonl
persistent_ledger/executions.jsonl
persistent_ledger/positions.jsonl
persistent_ledger/cash_history.jsonl
persistent_ledger/events.jsonl
persistent_ledger/migrations.jsonl
```

`state.json` は以下の参照元になる。

- Daily Plan
- Approval
- Report
- Notification
- Reconcile
- Audit

Ledger record には、環境と source を必ず持たせる。

```text
environment=demo | production
source=broker_positions | broker_executions | broker_orders_fallback | manual_migration
review_required=true | false
production_equivalent=true | false
```

Broker ID、request、response、secret、session、URL、口座識別子などの raw 情報は保存しない。必要な場合は hash 化された識別子、正規化済み summary、監査に必要な最小情報のみ保存する。

## 15. 現在保有・現金・総資産管理

現在保有、現金、買付余力、総資産は `persistent_ledger/state.json` から読む。

Runtime が管理すべき値:

- 現在保有銘柄
- 保有株数
- 平均取得単価
- 評価額
- 含み損益
- 現金
- 買付余力
- 未約定注文による拘束予定金額
- 総資産
- source
- `review_required`
- `production_equivalent`

Daily Plan と Approval は、日付別 `broker_positions/YYYY-MM-DD` や `ledger/YYYY-MM-DD` から現在状態を推測しない。Broker ReadOnly で得た最新状態は、まず Persistent Ledger に反映し、その Current State を読んで計画・承認・レポートを作る。

## 16. Demo / Production の扱い

Demo と Production は保存先ではなく metadata で分ける。

共通 storage:

```text
persistent_ledger/
pending_order_plan/
```

区別する metadata:

```text
environment=demo | production
source=broker_positions | broker_executions | broker_orders_fallback | manual_migration
review_required=true | false
production_equivalent=true | false
```

Demo は production runtime の rehearsal 環境である。Production と異なる fallback や未確定 projection を使った場合は、`production_equivalent=false` と `review_required=true` を明示する。

Production では、現在保有や現金の正規 SoT は以下である。

- Broker Positions
- Broker Executions
- Broker Cash / Buying Power

Production では Broker Orders fallback を現在保有確定に使わない。

## 17. `demo_ledger` legacy 化方針

`demo_ledger/` は Runtime v2 の本線 SoT から外す。

方針:

- 新規書き込みを止める。
- `persistent_ledger/` へ移行する。
- 既存 `demo_ledger/` は migration / fallback / historical artifact 扱いにする。
- 本線 Runtime は `persistent_ledger/` を読む。
- `demo_ledger/` を削除しない。削除や破壊的 cleanup は別途 migration 計画と監査後に行う。

移行時は `source=manual_migration`、`environment=demo`、必要に応じて `review_required=true` を付ける。

## 18. Report / Notification / Audit の位置づけ

Report、Notification、Audit は Runtime の状態を人間に説明し、運用判断を支援する Derived / Evidence 層である。

Report / Notification は Current State を読むが、Current State そのものにはならない。

Report 作成は Runtime の正式な責務である。Runtime は、AI 判断、注文、約定、保有、現金、資産、Safety、Review Required、異常状態を、人間が確認できる形に整理して Report を生成する。

Report は以下を説明する。

```text
今日 Runtime が何をしたか
どの AI 判断を使ったか
どの注文計画が作られたか
どの Pending Plan が Submit 対象だったか
承認状態はどうだったか
注文は送信されたか
注文は約定したか
約定後の保有はどうなったか
現金・買付余力・総資産はどうなったか
Safety は何を許可・禁止したか
Review Required はあるか
異常・不明・未確認状態はあるか
次に人間が確認すべきことは何か
```

Report 生成の入力:

```text
persistent_ledger/state.json
pending_order_plan/pending_order_plan.json
persistent_ledger/orders.jsonl
persistent_ledger/executions.jsonl
persistent_ledger/positions.jsonl
persistent_ledger/cash_history.jsonl
persistent_ledger/events.jsonl
History / Evidence artifact links
```

Report は `order_plan/YYYY-MM-DD` や `approval_artifact/YYYY-MM-DD` を証跡リンクとして表示してよい。ただし、それらを Current 判定元にしてはならない。

Report の出力:

```text
reports/YYYY-MM-DD/public_report.md
reports/YYYY-MM-DD/internal_report.md
reports/YYYY-MM-DD/safety_report.md
daily_report_refs/YYYY-MM-DD/daily_report_refs.json
notification payload
blog draft
LINE payload
Discord payload
```

原則:

- Report は Runtime の説明責務である。
- Report は Current State から生成する。
- Report は Current State そのものではない。
- Report を Runtime の入力にしない。
- Report 上の表示と Runtime 内部状態を混同しない。
- Report は注文、約定、保有、資産を分けて表示する。
- Report は source と `review_required` を明示する。
- Report は `persistent_ledger/state.json` と `pending_order_plan/pending_order_plan.json` を基準にする。
- Report は `order_plan/YYYY-MM-DD` や `approval_artifact/YYYY-MM-DD` を証跡としてリンクしてよい。
- Notification payload は Derived であり、Runtime の入力にしない。
- Audit result は異常検知と Review Required の説明に使うが、Submit 対象の選択元にしない。
- 通知送信は副作用であるため、Runtime v2 では生成と送信を分離する。

Notification は payload 生成と送信を分離する。

```text
notification payload generation = 再実行可能
notification send = delivery ledger により二重送信防止
```

Notification 送信は外部副作用であるため、送信履歴を固定 Path に保持する。

```text
notification_delivery/delivery_ledger.jsonl
```

Delivery Ledger には最低限以下を保持する。

- `delivery_id`
- `payload_hash`
- `channel`
- `target_date`
- `sent_at`
- `status`
- `retry_allowed`
- `review_required`

同じ `payload_hash` / `channel` / `target_date` は二重送信しない。送信結果が不明な場合は自動再送せず、`review_required=true` として扱う。再送を許可する場合も、Delivery Ledger 上で `retry_allowed=true`、前回 status、再送理由、operator または policy の根拠を残す。

## 19. Runtime 再実行設計

Runtime の処理は、外部副作用と再実行性により分類する。

冪等・再実行可能:

- Market Refresh
- Feature Refresh
- AI inference
- Daily Plan
- Approval prepare
- Broker ReadOnly
- Reconcile
- Report generation
- Audit

再実行可能処理の要件:

- 同じ入力に対して同じ artifact を再生成できる。
- 既存 artifact の上書きが必要な場合は manifest / hash / generated_at を明示する。
- Ledger 追記処理は dedup key を持つ。
- Broker ReadOnly は何度実行しても注文送信を発生させない。
- 再実行により notification send や Broker Order Submit などの外部副作用を発生させない。

非冪等処理:

- Broker Order Submit
- Notification Send
- Manual migration apply

これらは Current State、idempotency key、state transition、送信済み記録を確認し、二重実行を防止する。

条件付き再実行:

- Pending promotion
- Persistent Ledger append
- Report notification payload generation

条件付き再実行の要件:

- Pending promotion は、同じ source plan hash、target date、pending plan id の重複昇格を防ぐ。
- Persistent Ledger append は dedup key により同じ order / execution / position / cash state を二重反映しない。
- Report notification payload generation は payload hash が同一であれば再生成してよいが、送信は Delivery Ledger を通す。
- Manual migration apply は非冪等処理として扱い、dry-run、review、migration id、rollback ではなく補正記録を前提にする。

## 20. 異常時・結果不明時の扱い

異常時は安全側に倒す。

代表状態:

```text
HALT
BLOCKED
REVIEW_REQUIRED
POST_SEND_UNKNOWN
BROKER_DIVERGENCE
LEDGER_DIVERGENCE
STALE_STATE
```

扱い:

- Submit 前の不整合は `BLOCKED` または `REVIEW_REQUIRED` とする。
- Submit 後に Broker 応答が不明な場合は `POST_SEND_UNKNOWN` とし、自動再送しない。
- Broker ReadOnly で注文、約定、保有、現金の照合が取れない場合は `REVIEW_REQUIRED` とする。
- Ledger と Broker の現在状態が一致しない場合は `BROKER_DIVERGENCE` または `LEDGER_DIVERGENCE` とする。
- Current State が古い、欠損している、source が不明な場合は `STALE_STATE` または `REVIEW_REQUIRED` とする。
- `state_missing=true`、`current_positions_unknown=true`、`cash_unknown=true`、`buying_power_unknown=true` の場合は、新規 BUY、Approval、Submit を `BLOCKED` または `REVIEW_REQUIRED` にする。
- Current State 不明時の Report は、保有 0 や現金 0 ではなく `state_unknown` として出力する。

リカバリは、Broker ReadOnly、Reconcile、Manual Review、Ledger migration の順に進める。Submit の自動再送で結果不明を解消してはならない。

## 21. Phase13 実装分割案

本書作成時点では実装を開始しない。後続で実装する場合の分割案は次の通り。

1. Current State contract 固定
   - `pending_order_plan` と `persistent_ledger/state.json` を Runtime Current として明文化する。
   - History / Derived resolver を Submit path から外す。

2. Persistent Ledger mainline 接続
   - Daily Plan、Approval、Report、Reconcile、Audit が `persistent_ledger/state.json` を読むようにする。
   - `demo_ledger/` への新規書き込みを停止する。

3. Submit state machine 強化
   - `APPROVED` から `SUBMITTING`、`SUBMITTED`、`CONSUMED`、`POST_SEND_UNKNOWN` への遷移を定義する。
   - Submit 済み記録と pending consume を連動させる。

4. Broker ReadOnly reconciliation 強化
   - Orders、Executions、Positions、Cash / Buying Power を Ledger に ingestion する。
   - Demo 限定 fallback projection を source metadata 付きで扱う。

5. Report / Notification / Audit 再配線
   - Current State を基準にし、History artifact は evidence link に限定する。
   - Notification payload 生成と Notification Send を分離する。
   - Delivery Ledger で Notification Send の二重送信を防ぐ。

6. Recovery / Review Required 運用
   - `POST_SEND_UNKNOWN`、`BROKER_DIVERGENCE`、`LEDGER_DIVERGENCE` の runbook を整備する。
   - Review queue と manual migration の証跡を Ledger event として残す。

### 21.1 Phase13-E Implementation / Migration Plan

Phase13-E では、Runtime v2 を実装する前に、実装順序、移行対象、Acceptance Test、`launchd` 再開条件、Production 注文禁止を整理する。

詳細計画:

- [Phase13-E Runtime v2 Implementation / Migration Plan](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase13_runtime_v2_implementation_migration_plan.md)

Phase13-E の方針:

- 既存 Runtime 制御を v2 の正規フローとして継承しない。
- Phase13-F から Phase13-M までの実装サブフェーズに分割する。
- 最初に Current State Contract を固定する。
- `persistent_ledger`、`pending_order_plan`、`runtime_state/current_state.json`、`notification_delivery/delivery_ledger.jsonl` を中心に移行する。
- `order_plan/YYYY-MM-DD`、`approval_artifact/YYYY-MM-DD`、`submitted_orders/YYYY-MM-DD`、`broker_* /YYYY-MM-DD` は History / Evidence として扱う。
- `demo_ledger` は削除ではなく legacy isolation から始める。
- 既存 launchd plist は Runtime v2 の正規構成として継承せず、legacy 保持対象にもせず、Acceptance Test と Manual Rehearsal 完了後に後続フェーズで新規作成する。
- Acceptance Test と Manual Rehearsal が PASS するまで `launchd` 再開は禁止する。
- Phase13-E は実装計画のみであり、Submit、Broker 注文、Demo 注文、Production 注文、通知送信、既存 plist 削除、新規 plist 作成、`launchd` 再開を行わない。

### 21.2 Phase13-F 前の未決事項

Phase13-F は当初 Current State Contract 詳細設計として予定していたが、Phase13-E2 のレビュー結果により、先に Runtime Data Model Design を行った。Current State Contract 詳細設計は Phase13-G で行う。

Phase13-F Runtime Data Model Design:

- [Phase13-F Runtime Data Model Design](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase13_runtime_data_model_design.md)

Phase13-G Current State Contract Design:

- [Phase13-G Current State Contract Design](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase13_current_state_contract_design.md)

Phase13-H Runtime Transaction Design:

- [Phase13-H Runtime Transaction Design](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase13_runtime_transaction_design.md)

Phase13-I Simulation / Backtest Compatibility Design:

- [Phase13-I Simulation / Backtest Compatibility Design](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase13_simulation_backtest_compatibility_design.md)

Phase13-J Runtime v2 Implementation Readiness Review:

- [Phase13-J Runtime v2 Implementation Readiness Review](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase13_runtime_implementation_readiness_review.md)

Phase13-K Implementation Preflight Fix Plan:

- [Phase13-K Implementation Preflight Fix Plan](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase13_implementation_preflight_fix_plan.md)

Phase13-L Runtime v2 Skeleton / Path Resolver / Schema Validator:

- [Phase13-L Runtime v2 Skeleton / Path Resolver / Schema Validator](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase13_l_runtime_v2_skeleton.md)

Phase13-M Current State Runtime:

- [Phase13-M Current State Runtime](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase13_m_current_state_runtime.md)

Phase13-N Runtime State Machine / Orchestrator Skeleton:

- [Phase13-N Runtime State Machine / Orchestrator Skeleton](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase13_n_runtime_state_machine_orchestrator.md)

Phase13-O Persistent Ledger / Asset Runtime Skeleton:

- [Phase13-O Persistent Ledger / Asset Runtime Skeleton](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase13_o_persistent_ledger_asset_runtime.md)

Phase13-P Pending Order Plan Runtime:

- [Phase13-P Pending Order Plan Runtime](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase13_p_pending_order_plan_runtime.md)

Phase13-Q Broker ReadOnly Ingestion / Execution Reflection Skeleton:

- [Phase13-Q Broker ReadOnly Ingestion / Execution Reflection Skeleton](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase13_q_broker_readonly_execution_reflection.md)

Phase13-R Reconcile Runtime Skeleton:

- [Phase13-R Reconcile Runtime Skeleton](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase13_r_reconcile_runtime.md)

Phase13-S Planning / Approval Runtime v2 Skeleton:

- [Phase13-S Planning / Approval Runtime v2 Skeleton](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase13_s_planning_approval_runtime.md)

Phase13-T Report / Notification / Audit Runtime Skeleton:

- [Phase13-T Report / Notification / Audit Runtime Skeleton](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase13_t_report_notification_audit_runtime.md)

Phase13-U Runtime v2 System Review:

- [Phase13-U Runtime v2 System Review](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase13_u_runtime_v2_system_review.md)

Phase13-V Runtime v2 Minor Fixes / Architecture Guard:

- [Phase13-V Runtime v2 Minor Fixes / Architecture Guard](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase13_v_runtime_v2_minor_fixes.md)

Phase13-W Runtime v2 Integration Readiness Review:

- [Phase13-W Runtime v2 Integration Readiness Review](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase13_w_runtime_v2_integration_readiness_review.md)

Phase13-X Legacy Runtime Isolation / Writer Contract Fix:

- [Phase13-X Legacy Runtime Isolation / Writer Contract Fix](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase13_x_legacy_runtime_isolation.md)

Phase13-Y Runtime v2 Acceptance Dry Run:

- [Phase13-Y Runtime v2 Acceptance Dry Run](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase13_y_runtime_v2_acceptance_dry_run.md)

Phase13-Z Final Audit / Phase14 Handoff:

- [Phase13 Final Audit and Phase14 Handoff](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase13_final_audit_and_phase14_handoff.md)

Phase13-G で Current State Contract を詳細設計する際の入力として、Phase13-F 時点では以下を未決事項として扱った。

- Current State schema 詳細
- `runtime_state/current_state.json` schema
- `pending_order_plan` current schema finalization
- `persistent_ledger/state.json` required fields
- `notification_delivery/delivery_ledger.jsonl` schema
- confirmed empty の厳密条件
- stale 判定の時刻・business_date 基準
- Current State validation policy
- Architecture test file 配置
- legacy runtime isolation 対象 module 一覧

これらは本設計書の原則を実装 contract に落とす作業であり、Phase13-E2 では詳細設計しない。

## 22. Acceptance Criteria

Runtime Architecture v2 の受け入れ基準は、Architecture Acceptance Criteria と Future Implementation / Test Criteria に分ける。前者は本設計書で満たすべき設計基準であり、後者は Phase13-F 以降の詳細設計・実装・テストで満たすべき基準である。

### 22.1 Architecture Acceptance Criteria

- Runtime が AI 判断ロジックではなく運用制御層であることが明文化されている。
- 既存 Runtime 制御を v2 の正規フローとして継承しないことが明記されている。
- 既存 Runtime は legacy implementation として扱うことが明記されている。
- 既存コード参照の目的が、問題確認・移行対象把握・legacy 化対象把握に限定されている。
- AI / システムと Runtime の責務分離が明文化されている。
- Runtime State Machine が定義されている。
- 各状態について、入力条件・出力 artifact・再実行可否・副作用有無・失敗時遷移が定義されている。
- Runtime Component Architecture が定義されている。
- Runtime が単一の巨大処理ではなく、複数 Component で構成されることが明記されている。
- 各 Component について、役割・入力・出力・読む Current State・書く Current State・再実行可否・副作用有無・依存関係が定義されている。
- Runtime Component Architecture は責務設計であり、既存 module 名をそのまま継承するものではないことが明記されている。
- Component と実装 module の対応は Phase13-F 以降で決めることが明記されている。
- AI Execution Runtime は AI を呼び出すだけで、AI 判断ロジックを再実装しないことが明記されている。
- Submit Runtime だけが Broker Order Submit の副作用を持つことが明記されている。
- Notification Runtime は payload 生成と送信を分離し、送信は Delivery Ledger で二重送信防止することが明記されている。
- Report Runtime が Runtime の説明責務を持つことが明記されている。
- Ledger Runtime が注文・約定・保有・現金・Runtime event を Persistent Ledger へ反映することが明記されている。
- Asset Runtime が現在保有・現金・買付余力・総資産を整理することが明記されている。
- Component 間の依存関係が明記されている。
- Current State 依存関係が明記されている。
- Current / History / Derived の分類が明文化されている。
- Runtime 生成物を Phase 単位・日付単位の作業場所に閉じ込めないことが明記されている。
- Phase 番号は開発管理上の単位であり、Runtime 実行時 SoT ではないことが明記されている。
- 日付は履歴属性であり、Runtime 実行対象の主キーではないことが明記されている。
- Runtime Current は役割ごとの固定 Path で管理することが明記されている。
- History / Evidence は日付別で保持してよいが、Current 決定元として自動選択しないことが明記されている。
- Submit 対象が `pending_order_plan/pending_order_plan.json` のみに固定されている。
- 日付別 artifact から Submit 対象を推測しないことが明文化されている。
- `persistent_ledger/state.json` が現在保有、現金、買付余力、総資産の中心 Current State として定義されている。
- Current State の固定 Path と原則は本設計書で定義し、schema / required fields / missing / stale / unknown / validation policy は Phase13-F Current State Contract 詳細設計で定義することが明記されている。
- Current State 欠損時に保有 0 扱いしないことが明記されている。
- Current State 不明時、新規 BUY・Approval・Submit が `BLOCKED` または `REVIEW_REQUIRED` になることが明記されている。
- Submit / Broker Order が非冪等処理であり、多重実行禁止であることが明文化されている。
- Submit 結果不明時に自動再送せず、Broker ReadOnly と Review Required に進めることが明文化されている。
- Market Refresh、Feature Refresh、Daily Plan、AI inference、Approval prepare、Report、Audit、Reconcile、Read-only broker sync が再実行可能処理として定義されている。
- Notification 送信が非冪等処理として分類され、Delivery Ledger で二重送信防止することが明記されている。
- payload 生成と notification 送信が分離されている。
- Runtime の Report 作成責務が明文化されている。
- Report は Current State から生成される Derived artifact であることが明記されている。
- Report は Runtime Current 入力ではないことが明記されている。
- Report が注文・約定・保有・資産を分けて表示することが明記されている。
- Report が source と `review_required` を明示することが明記されている。
- 注文・約定・保有・資産が別概念として定義されている。
- 注文は資産ではなく、約定して初めて保有になることが明記されている。
- `submitted_orders` / `broker_orders` を現在保有 SoT として扱わないことが明記されている。
- `broker_executions` / `broker_positions` / `persistent_ledger` が保有確定の正規根拠であることが明記されている。
- Runtime が銘柄数の固定上限を持たないことが明記されている。
- 5 銘柄固定などの旧 Runtime 制御を継承しないことが明記されている。
- Runtime が制御するのは銘柄数ではなく、資金・買付余力・Broker 制約・Safety 制約・重複注文防止であることが明記されている。
- Demo / Production を保存先ではなく metadata で分けることが明文化されている。
- Broker Orders fallback が Demo 限定であり、Production の現在保有確定に使わないことが明文化されている。
- `demo_ledger/` の legacy 化方針が明文化されている。
- Report / Notification / Audit が Derived / Evidence 層であり、Runtime Current 入力ではないことが明文化されている。
- Phase13 design-only 期間では実装しないこと、Phase13-E2 時点では Submit、Broker 注文、Demo 注文、Production 注文、通知送信、既存 plist 削除、新規 plist 作成、`launchd` 再開を行わないことが明文化されている。

### 22.2 Future Implementation / Test Criteria

Phase13-F 以降では、以下の実装・テスト基準を満たす必要がある。

- Current State fixed path test
- No date-based Current resolution test
- No phase-based Current resolution test
- Pending-only Submit source test
- Consumed pending cannot resubmit test
- `POST_SEND_UNKNOWN` no auto-resend test
- Order is not asset test
- Execution creates position test
- Position + cash creates asset state test
- Current State unknown blocks BUY / Approval / Submit test
- Report is derived-only test
- Notification delivery dedup test
- Production `broker_orders` fallback prohibition test
- Demo `broker_orders` fallback review flag test
- Legacy runtime not used as v2 source test

## 23. 禁止事項

Runtime Architecture v2 の設計および Phase13 design-only 作業では、以下を禁止する。

- 実装変更
- Submit 実行
- Broker 注文
- Demo 注文
- Production 注文
- `launchd` 再開
- 既存 plist 削除
- 新規 plist 作成
- artifact 削除
- notification 送信
- secret 保存
- raw request 保存
- raw response 保存
- AI 再学習
- フルバックテスト

Runtime 実装フェーズに進む場合でも、以下は禁止する。

- 既存 Runtime 制御フローを v2 の正規フローとして継承する。
- 既存コードを Current State の決定方法、Submit 対象の選び方、約定後の保有確定方法、Report / Audit の Current 判定方法の根拠にする。
- Phase13 用の一時保存場所を Runtime Current として使う。
- `YYYY-MM-DD` ディレクトリを Runtime Current として使う。
- Phase 番号を Runtime 実行時 SoT として扱う。
- 日付別 artifact を Runtime 実行対象の主キーとして扱う。
- `order_plan/YYYY-MM-DD` から直接 Submit する。
- `approval_artifact/YYYY-MM-DD` から直接 Submit 対象を推測する。
- 日付別 artifact から最新らしい Plan を探して Submit する。
- Derived artifact を Current 入力にする。
- Report を Runtime Current 入力にする。
- `demo_ledger/` を本線 SoT として読み続ける。
- `submitted_orders` または `broker_orders` を現在保有の SoT として扱う。
- Production で Broker Orders fallback を現在保有確定に使う。
- 5 銘柄固定などの旧 Runtime 銘柄数制御を基本要件として継承する。
- `POST_SEND_UNKNOWN` を自動再送で解決する。
- raw request、raw response、secret、session、URL、口座識別子を保存する。
