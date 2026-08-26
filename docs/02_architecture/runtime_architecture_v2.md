# Runtime Architecture v2 システム設計書

作成日: 2026-07-07

## 1. 目的

Runtime Architecture v2 は、AI Fund Lab v2 の日次運用を安全に制御するための Runtime システム設計である。

Runtime は AI の投資判断ロジックではない。Runtime は、AI と周辺システムが出した判断、計画、承認、Broker 状態を、現在状態と照合しながら、正しい順序で、二重実行なく運用する制御層である。

Runtime は年 50% 運用目標を直接達成する AI ではない。年 50% 目標に向けた銘柄選定、優先順位付け、資金配分、リスクテイク方針は Candidate AI、Opportunity AI、Position Management AI、Capital Allocation、Risk Policy / Safety の責務である。

Strategy Layerの最上位SoTは次である。

```text
docs/02_architecture/strategy_architecture_v1.md
```

RuntimeはStrategy Architecture v1が出すMarket Context、Portfolio Policy、Portfolio Construction、Capital Allocation、Execution Intentを、Authority、Lifecycle、Safety、Pending、Submit、Ledger、CurrentのContractに従って処理する。RuntimeはMarket Context、target cash ratio、dynamic position count、position sizing、ranking、HOLD / ADD / REDUCE / EXIT判断を再計算しない。

ただし Runtime は、Capital Allocation / Risk Policy が設計上許容した攻めた資金配分を、Runtime 内の隠れ固定値で阻害してはならない。Runtime の責務は、明示された資金投入方針、Safety 条件、Broker 制約、承認状態に従って、資金を安全かつ設計どおり市場へ投入し、約定後の Current を正しく更新することである。

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
- Runtime は保有銘柄数、注文金額上限、現金バッファ、投資率を暗黙値として持たない。これらは Capital Deployment Contract / Risk Policy として明示される。
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

Phase31-B10 以降、BUY_NEW / BUY_ADD の増分資本競争には
Portfolio Construction 所有の次の Production-common authority を用いる。

```text
MARGINAL_CAPITAL_VALUE_AUTHORITY
```

Runtime Planning はこの canonical Strategy order を消費し、
BUY reserved-cash feasibility / Pending order plan construction へ保持する。
Runtime Planning / Pending は BUY_NEW と BUY_ADD の投資選好を再計算・再ランキングしない。

この authority は BUY ordering のみを変える。SELL は BUY marginal
capital competition から独立して扱われ、reviewed/pruned BUY が valid
SELL をブロックしてはならない。

変更しないもの:

```text
PM ADD semantics
Expected Edge thresholds
Incremental Investment Value thresholds
Opportunity Cost thresholds
Market Context logic
normal Strategy cap
Safety hard cap
winner headroom
Submit
Execution
SELL logic
```

Runtime は銘柄数の固定上限を持たない。購入候補の幅は Candidate AI / Opportunity AI / Position Management AI / Capital Allocation / Safety の判断に委ねる。Capital Allocation が結果として 5 銘柄、10 銘柄、20 銘柄などに絞ることはあり得るが、それは Runtime の固定ルールではない。

### 3.1 Capital Deployment Contract

Runtime v2 は、資金をどれだけ市場へ投入するかを隠れ固定値で決めない。資金投入方針は Capital Allocation / Risk Policy / Safety の明示 contract として扱う。

Capital Deployment Contract は、少なくとも以下を定義する。

| 項目 | 意味 | Runtime の扱い |
| --- | --- | --- |
| 目標投資率 | 評価資産のうち市場へ投入する目標比率 | Runtime は暗黙値を持たず、明示 policy を読む |
| 現金バッファ | 最低限残す現金または買付余力 | Submit Guard は明示 policy に基づいて確認する |
| 最大 1 銘柄比率 | 1 銘柄へ投入可能な最大比率 | Capital Allocation の出力と Submit Guard の確認条件を一致させる |
| 最大保有銘柄数 | 保有銘柄数の上限 | Runtime 固定値ではなく Risk Policy として明示する |
| 最小注文金額 | 注文を出す最低 notional | 小さすぎる注文を止める場合は manifest に理由を出す |
| 最大注文金額 | 注文を出す最大 notional | hidden default 禁止。BUY / SELL 別に意味を定義する |
| BUY notional guard | 新規 exposure を増やす注文の金額 guard | Capital Allocation、cash、buying_power、exposure、price、lot size と整合させる |
| SELL liquidation guard | Runtime-owned exposure を減らす注文の guard | Current quantity、Broker available quantity、対象銘柄、明示 liquidation policy を確認する |
| Safety 停止条件 | REVIEW_REQUIRED / BLOCKED / HALT 条件 | Runtime は Safety 結果を上書きせず、状態遷移へ反映する |

これらの policy は、Runtime の暗黙値、旧 Runtime 由来の固定値、fixture 値、テスト用 default として扱ってはならない。Runtime は active Capital Deployment Policy を manifest / report / audit に出力し、Operator が「なぜその注文金額・保有銘柄数・現金バッファになったか」を確認できるようにする。

最大保有銘柄数を設ける場合も、Runtime は `max_positions=5` のような旧 Runtime 思想を暗黙に復活させない。`max_positions` は Risk Policy / Capital Deployment Contract の一部として明示し、以下を manifest に出す。

```text
active_max_positions
max_positions_source
current_position_count
planned_position_count
max_positions_decision
max_positions_reason
```

Runtime が年 50% 目標を直接保証することはないが、明示された Capital Deployment Contract に基づく資金投入を、Runtime 内の未定義 guard で過度に保守化してはならない。

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

#### Human Review / Human Approval / Promotion Candidate Boundary

Human Review と Human Approval は別の authority である。

Human Review は、Safety `REVIEW_REQUIRED` などの状態に対して、SELL/HOLD 評価や人間向けReview evidenceを生成してよいかを判断する。Human Review は Submit 許可ではない。Human Review artifact が `SELL_HOLD_REVIEW_REQUIRED` であっても、Broker Write、Submit、Approval Apply、Authoritative Pending mutation を許可しない。

Human Approval は、どの具体的な issue code、side、quantity、review item を Authoritative Submit Pending 候補へ昇格してよいかを item 単位で判断する。Human Approval artifact は、source Human Review、Safety event、Review Pending hash、review item hash、policy hash、safety decision id、期限、取消状態を持つ。

Review Pending は review evidence であり、Submit source ではない。Review Pending は次を維持する。

```text
submit_allowed=false
broker_write_allowed=false
authoritative_submit_pending=false
```

Review Pending と Human Approval から直接 `pending_order_plan/pending_order_plan.json` を更新してはならない。まず `pending_promotion_candidate/YYYY-MM-DD/<candidate_id>.json` を生成し、以下を検証する。

- Review Pending schema / hash
- source Human Review id
- source Safety event id
- approval status / expiration / revocation
- approved item ids / quantities / side / review item hash
- policy hash
- Safety action scope
- Current freshness
- Broker evidence freshness
- Pending current slot is `EMPTY`
- duplicate promotion absence

Promotion Candidate は no-apply evidence である。`apply_requested=false` / `apply_executed=false` の Candidate は Authoritative Submit Pending ではない。

Authoritative Submit Pending Apply は別の明示Scopeでのみ実行できる。Apply review scope では `authoritative_pending_apply_candidate/YYYY-MM-DD/<candidate_id>.json` を生成できるが、これは dry-run evidence であり `pending_order_plan/pending_order_plan.json` ではない。Apply Candidate は Producer、Input Artifact、Output Artifact、Authority、Apply Preconditions、Apply Request、Apply Execution、Idempotency、Atomicity、Backup、History、Rollback、Expiration、Revocation、Audit、Consumer を明示する。

Authoritative Pending へ実Applyする直前には、Human Approval、Promotion Candidate hash、Approval hash、Review Pending hash、Policy hash、Safety Decision、Current State、Broker Evidence、Pending Slot、Target Session、Expiration、Revocation を再検証する。`Safety Decision` が Submit / Broker Write を許可していない場合、Apply Candidate は `READY_BUT_SAFETY_BLOCKED` になり、`apply_allowed=false`、`apply_requested=false`、`apply_executed=false`、`authoritative_pending_mutated=false` を維持する。注文条件が Review / Approval evidence から決定できない場合は `REVIEW_REQUIRED_BEFORE_AUTHORITATIVE_APPLY` として残し、Runtime が注文条件を推測しない。

将来の実Applyは atomic でなければならない。全itemを一括で Authoritative Pending に反映できない場合、元の Pending Slot を保持し、success history を書かず、current pointer を更新しない。再実行時は同一 Apply Candidate、同一 Approval、同一 pending_plan_id の二重消費を防ぎ、failure 後の retry は直前再検証を必須とする。

Apply 時も Submit は実行しない。Submit は引き続き `pending_order_plan/pending_order_plan.json` のみを source とし、`state=APPROVED`、Human Approval linkage、policy / safety / broker / current guards を通過した場合にのみ Submit Runtime へ進める。

Safety-blocked Apply / Submit path is an accepted safe terminal review path, not an abnormal runtime crash. If a valid Review, Human Approval, Promotion Candidate, and Apply Candidate meet structural preconditions but Safety says `sell_submit=BLOCKED` or `broker_write=BLOCKED`, Runtime must classify the result as `EXPECTED_SAFETY_BLOCK` / `BLOCKED_BY_SAFETY` and keep:

```text
apply_executed=false
authoritative_pending_mutated=false
submit_attempted=false
broker_client_called=false
broker_write_performed=false
pending_consumed=false
execution_created=false
current_mutated=false
notification_sent=false
```

Human Approval cannot override Safety. A blocked attempt may write audit evidence, but it must not consume Human Approval, Promotion Candidate, Apply Candidate, Review Pending, Authoritative Pending, or Pending Item.

Order condition authority is separate from Safety authority. Runtime scaffolding must not infer `order_type` or `price_condition` from implementation defaults. If Policy, Human Approval, Submit Pending Producer, and Broker capability evidence do not define order conditions, Submit Guard must block with `ORDER_CONDITION_AUTHORITY_CONTRACT_REQUIRED` or an equivalent review-required reason before the Broker client boundary.

Normal Submit Acceptance must not reuse an existing Safety-blocked runtime root such as the current 4591 evidence root. It requires an isolated acceptance root or equivalent fully isolated fixture where Safety, Pending, Current, Broker Evidence, Approval, order conditions, and target session are internally consistent.

The formal order-condition authority split is defined in:

```text
docs/02_architecture/runtime_submit_order_condition_authority_contract.md
```

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

##### Broker Snapshot Only Refresh

Runtime Acceptance Step0 may require fresh Broker Evidence without executing the Execution Runtime. For this case Runtime defines a snapshot-only ReadOnly producer:

```text
broker_readonly_refresh
```

This producer writes only:

```text
.runtime/runtime_state/broker_readonly/<business_date>/tachibana_snapshot.json
.runtime/runtime_state/broker_readonly/latest.json
```

It must not:

- submit or cancel broker orders
- append persistent ledger records
- classify executions into Runtime-owned fills
- mutate Current Position
- mutate Pending
- apply Approval

Broker Snapshot is an evidence input for Safety, Data Readiness, Submit guard, and Reconcile. It is not the authoritative Runtime-owned Current and must not be used to silently replace `persistent_ledger/state.json`.

Broker Evidence has two independent readiness dimensions:

- Producer / freshness readiness: the snapshot-only job ran and produced fresh read-only evidence.
- Authenticity / account alignment readiness: the payload is distinguishable as Broker API vs fixture/mock/unknown, and Runtime-owned positions are reconciled to the intended broker account scope.

Nested `source="mock"` values, fixture payloads, or unknown account identity must not be treated as Safety-ready Broker Evidence. Runtime records `data_origin`, `fixture_used`, `mock_used`, `authenticity_status`, and `account_alignment_status` separately from freshness.

#### Feature Refresh Runtime

Runtime Feature Refresh is the formal producer for Candidate, Opportunity, and Position Management feature artifacts used by Runtime Acceptance.

Candidate features must be generated from market history and include long-history features and missing flags required by the formal model contract. Opportunity artifacts are unprefixed; consumers map to model-level `feature__...` names exactly once. PM feature input must read Runtime Current and emit one row per Runtime-owned position when Current has positions. A zero-row PM artifact is valid only when Current has no positions and the artifact carries `no_position_reason`.

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
- 書く Current State: `persistent_ledger/orders.jsonl`、`persistent_ledger/executions.jsonl`、`persistent_ledger/positions.jsonl`、`persistent_ledger/cash.jsonl`、`persistent_ledger/events.jsonl`、`persistent_ledger/state.json`。
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
- 読む Current State: `persistent_ledger/state.json`、`persistent_ledger/positions.jsonl`、`persistent_ledger/cash.jsonl`、`persistent_ledger/executions.jsonl`。
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
- 入力: `persistent_ledger/state.json`、`pending_order_plan/pending_order_plan.json`、`persistent_ledger/orders.jsonl`、`persistent_ledger/executions.jsonl`、`persistent_ledger/positions.jsonl`、`persistent_ledger/cash.jsonl`、`persistent_ledger/events.jsonl`、History / Evidence links、reconciliation_result。
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

Runtime Safety Decision preserves legacy `block_buy`, `block_sell`, and `block_submit` booleans for existing consumers, but these booleans are not sufficient as the formal action contract. Safety Runtime must also expose action-scope permissions for BUY inference/planning, SELL/HOLD review generation, submit, auto sell, human review, and Broker Write.

For `INDIVIDUAL_CRASH / HIGH_RISK_REVIEW`, the event remains valid. Runtime does not alter thresholds or remove the affected symbol. New BUY and Broker Write are blocked; automatic SELL submit is blocked; Human Review and SELL/HOLD review generation may be allowed for review output.

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

`runtime_state/current_state.json` は Runtime Operation State のみを表す authoritative artifact とする。Asset Current ではない。

Contract:

```text
schema_version=runtime_v2_operation_state_v1
role=authoritative_runtime_operation_state
producer=runtime_state_refresh
```

この artifact は Runtime の状態、Safety state、生成時刻、対象 business date、環境を保持する。保有、現金、買付余力、総資産、Pending submit target は保持しない。これらの SoT は引き続き `persistent_ledger/state.json` と `pending_order_plan/pending_order_plan.json` である。

Safety Evaluation と Data Readiness は、この artifact を required Runtime Operation evidence として扱う。missing / stale / legacy role / invalid state は `REVIEW_REQUIRED`、invalid JSON は `HALT` とする。

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
persistent_ledger/cash.jsonl
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
persistent_ledger/cash.jsonl
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
| 現金履歴 | `persistent_ledger/cash.jsonl` | 現金、買付余力、資産評価の履歴 |
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

Runtime-owned execution ledger が全売却後に `positions=[]`、`current_positions_unknown=false`、`current_position_status=READY`、`no_position=true`、`no_position_reason=current_has_no_runtime_owned_positions`、`position_state_as_of`、`temporal_status=READY`、`review_required=false` を持つ場合、その Current Position Authority は `READY_EMPTY` である。これは legacy / broker confirmation field である `current_state_confirmed_empty=false` だけを理由に `UNKNOWN` へ降格してはならない。

Position Feature consumer は以下を分離する。

```text
NON_EMPTY_READY: positions is a non-empty list, authority ready, PM feature rows required
READY_EMPTY: positions=[], no_position=true, authority ready, 0-row Position Feature is valid, PM inference is NOT_REQUIRED
UNKNOWN: missing/corrupt/stale/conflicting authority, PM consumer REVIEW_REQUIRED
```

`READY_EMPTY` は保有数 0 の正常状態であり、架空の Position Feature row、dummy symbol、0株注文、または PM inference 強制実行を生成しない。Ledger 欠損、JSON不正、`positions` 欠損/型不正、`current_positions_unknown=true`、`review_required=true`、Temporal不整合、empty/non-empty metadata conflict は引き続き fail-closed とする。

### 10.1 Current Writer Contract

Runtime v2 の Current Object は Single Writer Rule に従う。各 Current は必ず 1 つの writer component だけを持ち、Reconcile、Report、Audit は Current Writer にならない。

| Current | Writer | Reader | Writer 禁止 Component |
| --- | --- | --- | --- |
| `runtime_state/current_state.json` | Runtime State Runtime | Runtime Orchestrator, Report Builder, Audit Runtime | Reconcile, Report, Audit, Submit 以外のBroker連携 |
| `pending_order_plan/pending_order_plan.json` | Pending Runtime | Approval Runtime, Submit Runtime, Report Builder | Planning, Approval, Reconcile, Report, Audit |
| `persistent_ledger/orders.jsonl` | Ledger Runtime | Reconciliation Runtime, Report Builder, Audit Runtime | Reconcile, Report, Audit |
| `persistent_ledger/executions.jsonl` | Ledger Runtime | Reconciliation Runtime, Report Builder, Audit Runtime | Reconcile, Report, Audit |
| `persistent_ledger/positions.jsonl` | Ledger Runtime | Current State Reader, Report Builder, Audit Runtime | Reconcile, Report, Audit |
| `persistent_ledger/cash.jsonl` | Ledger Runtime | Current State Reader, Report Builder, Audit Runtime | Reconcile, Report, Audit |
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

`EMPTY` の扱い:

- `state/status == EMPTY`、`active_pending == false`、注文 item 数 0 の Pending Slot は、注文を消費しない No-Action terminal である。
- `EMPTY` Slot は Submit 対象の注文 Authority ではないため、`environment`、`target_session_date`、`intended_submit_date`、`safety_context`、Runtime Test identity を必須にしない。
- Reset 直後の canonical `EMPTY` Slot と、当日 Planning 結果 0 件の `EMPTY` Slot は、Submit で `NO_ACTION` として正常完了できる。
- `EMPTY` Slot に item または approved item id が存在する場合、または `active_pending == true` の場合は矛盾した Pending として fail-closed する。
- Active / carry-forward Pending を Submit で消費する場合は、従来どおり environment、business date、session date、Safety、Approval、Runtime Test identity の整合性を検証する。

Pending Composition Contract:

- Submit authority は引き続き `pending_order_plan/pending_order_plan.json` の単一 Current Slot である。
- BUY Planning が当日有効な BUY Pending を生成した後、SELL Planning が `NO_SIGNAL` になった場合、SELL Planning は有効な既存 BUY Pending を `EMPTY` で上書きしてはならない。
- SELL Planning が SELL item を生成し、同じ target session の有効な BUY Pending が存在する場合、Runtime は BUY item と SELL item を 1 つの Composite Pending Plan に合成して canonical slot へ書く。
- Composite Pending Plan は item 単位の `pending_item_id` で重複を排除し、最終 item set 全体に対する approval linkage を持つ。
- Separate BUY/SELL Pending slot、History artifact 直接 Submit、Submit による複数 Pending 探索は禁止する。

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

### 12.2 Phase14 追補: Submit Guard / Capital Allocation / SELL Liquidation Contract

Phase14-E51 から E54 で、通常 Submit path に残っていた hidden fixed cap が SELL liquidation を BLOCK し、Capital Allocation 契約との不整合が判明した。これを Runtime Architecture v2 の設計契約として以下に追補する。

#### Submit Guard は Capital Allocation を隠れ固定値で上書きしない

Submit Guard は非冪等な Broker Write の直前に安全性を確認する責務を持つが、Planning / Capital Allocation が作った注文意図を、設計書にない固定値で静かに上書きしてはならない。

特に、`max_order_amount=100000` のような注文金額 guard は以下を満たす場合のみ使用できる。

- 設計契約上の意味が明文化されている。
- BUY / SELL のどちらに適用されるかが明文化されている。
- 値の取得元、初期値、runtime mode 差分、manual review 条件が明文化されている。
- Submit manifest / report / audit に active policy として出力される。
- 通常 CLI submit path の regression test で検証される。

これらを満たさない金額 cap は hidden cap とみなし、Runtime v2 の正規 Submit Guard として使ってはならない。

Submit Guard は `active_amount_policy` として、実際に使用した注文金額 policy を manifest / report に出力する。出力されない amount policy は Runtime v2 の有効な guard として扱わない。

#### BUY notional guard と SELL liquidation guard を同一扱いにしない

BUY は新規 exposure を増やす処理である。BUY guard は少なくとも以下を確認する。

- Capital Allocation が意図した注文金額。
- Current cash / buying_power。
- max exposure / max position weight / Safety 制約。
- price source、lot size、Broker 制約。

SELL liquidation は Runtime-owned exposure を減らす処理である。SELL guard は少なくとも以下を確認する。

- SELL source が Current SoT の Runtime-owned position であること。
- 売却数量が Current quantity 以下であること。
- 売却数量が Broker available quantity 以下であること。
- Broker-only position を売却対象にしていないこと。
- 価格、数量、単位、Broker issue code が Submit boundary で正規化されていること。

BUY と SELL に同一 notional guard を適用する場合は、その設計根拠、適用条件、例外、manual review 条件、manifest fields、regression tests を本設計書または後続 contract に明記しなければならない。明記されていない場合、BUY notional guard を SELL liquidation にそのまま適用してはならない。

SELL liquidation を止める条件は、原則として以下に限定する。

- Current quantity を超過している。
- Broker available quantity が不足している。
- SELL source が Runtime-owned Current position ではない。
- Broker-only / Demo対象外 / 対象外銘柄を売ろうとしている。
- 明示された SELL liquidation policy に違反している。
- Safety / Operation Guard が REVIEW_REQUIRED、BLOCKED、HALT を返している。

SELL liquidation は exposure を減らす処理であるため、BUY 用の注文金額上限だけを理由に機械的に止めてはならない。高額 SELL を止める場合は、SELL liquidation policy として明示し、manual review、分割売却、数量縮小、BLOCK のどれにするかを設計上定義する。

#### SELL liquidation source

SELL liquidation の唯一の source は `persistent_ledger/state.json` にある Runtime-owned Current position である。

以下は SELL source ではない。

- Broker ReadOnly にだけ存在する position。
- Demo Broker の日次 reset や外部操作で見える position。
- `broker_positions`、`broker_orders`、report、audit、phase artifact から推測した position。
- Runtime-owned であることを ledger / current で確認できない position。

Broker-only position は Reconcile / Review evidence であり、Runtime v2 が自動売却してはならない。

#### Submit Guard active policy manifest

Submit Runtime は、Submit preflight の結果だけでなく、実際に使った guard policy を manifest / audit に secret-safe に出力する。

最低限、以下を記録する。

```text
guard_policy_version
active_amount_policy
side
estimated_amount
capital_allocation_amount
max_buy_order_amount
max_sell_liquidation_amount
target_investment_ratio
cash_buffer
max_position_weight
max_positions
notional_guard_source
quantity_guard_source
current_position_source
broker_available_quantity_checked
guard_decision
guard_reason
manual_review_required
```

未定義の policy で BLOCK した場合は `REVIEW_REQUIRED` または `BLOCKED` として止め、Operator がどの契約により止まったか判断できるようにする。

### 12.3 Phase15-B 追補: Purpose-Based Runtime Control Contract

Phase15-A で定義した AI Fund Lab v2 の最終目的は以下である。

```text
年間50%の利益を目指し、安心・安全に自動売買を継続できる運用システムを実現すること
```

Runtime v2 はこの目的を直接達成する AI ではない。しかし Runtime v2 は、AI / Capital Allocation / Safety / Broker / Current / Report / Notification を接続する制御中枢であるため、Runtime が隠れ保守化・隠れ停止・隠れ資金配分変更を行うと、AI Fund Lab v2 の目的そのものを阻害する。

したがって Runtime v2 は、以下を設計上の禁止事項として扱う。

- `max_order_amount=100000` のような Runtime 内固定注文金額上限。
- `max_positions=5` のような Runtime 内固定保有銘柄数上限。
- Runtime 独自の cash buffer。
- Runtime 独自の target investment ratio / max exposure / 投資率制限。
- BUY と SELL を同じ notional guard で止める設計。
- Capital Allocation が出力した資金配分を Submit Guard が後段で再決定または上書きする構造。
- fixture、test default、legacy helper default、CLI default を production / demo operation policy として暗黙採用すること。

これらが必要な場合は Runtime 固有の default ではなく、Capital Deployment Contract / Risk Policy / Safety / Broker constraint として明示し、manifest / report / audit / regression に出力する。

#### Capital Deployment は Runtime の判断ではない

年率 50% を目指す運用では、資金投入は過度に保守化されてはならない。一方で、Runtime が攻めた資金投入を独自判断で作ってもならない。

Runtime の責務は、明示された Capital Deployment Contract を安全に実行することである。以下は Runtime が決める値ではなく、Capital Allocation / Risk Policy / Safety / Broker constraint の明示 contract として入力される。

- target investment ratio
- cash buffer
- max exposure
- max position weight
- position sizing
- buying power usage
- order size
- rebalance / replacement
- position count
- SELL-first / BUY-after-fill

Runtime はこれらを読み、以下を確認する。

- policy source が存在する。
- policy version / effective date / runtime mode が manifest に残る。
- Planning / Pending / Approval / Submit Guard の単位と意味が一致する。
- Submit Guard が資金配分を再計算していない。
- policy 不足時は hidden default で補完せず `REVIEW_REQUIRED` とする。

#### 保有銘柄数 Contract

Runtime は保有銘柄数の固定上限を持たない。

以下のような値を Runtime 内 default として持つことは禁止する。

```text
max_positions = 5
```

保有銘柄数上限を使う場合は、Risk Policy / Capital Deployment Contract として明示し、少なくとも以下を manifest / report / audit に出力する。

```text
active_max_positions
max_positions_source
max_positions_policy_version
current_position_count
planned_position_count
post_trade_position_count
max_positions_decision
max_positions_reason
manual_review_required
```

Runtime は銘柄数を理由に AI / Capital Allocation / Safety の出力を機械的に捨てない。銘柄数制限に抵触する場合は、Planning / Capital Allocation / Replacement Policy 側で解決するのか、Submit 側で `REVIEW_REQUIRED` として止めるのかを manifest に明示する。

#### 注文金額上限 Contract

Runtime は固定の注文金額上限を持たない。

BUY の注文金額上限を設ける場合は、少なくとも以下から導出する。

- evaluation capital
- target investment ratio
- cash buffer
- max exposure
- max position weight
- buying power
- price
- lot size
- broker constraint
- safety result

SELL の注文金額上限を設ける場合は BUY とは別 contract とする。SELL は原則として Runtime-owned exposure を減らす処理であり、BUY 用の notional cap だけで止めてはならない。

Submit Guard が注文を止める場合は、以下を manifest / report / audit に出力する。

```text
violated_policy
violated_policy_source
violated_policy_version
side
planning_amount
capital_allocation_amount
submit_estimated_amount
guard_decision
guard_reason
manual_review_required
should_have_been_blocked_at_planning
blocked_at_submit_reason
```

#### BUY / SELL Guard Separation

BUY は新規リスク投入であり、SELL はリスク低減である。

BUY Guard は、Capital Allocation が意図した exposure 増加が、cash / buying_power / target investment ratio / max exposure / max position weight / price / lot size / Broker constraint / Safety result と一致していることを確認する。

SELL liquidation は、以下で制御する。

- Runtime-owned Current position
- Current quantity
- Broker available quantity
- Broker issue code normalization

#### Phase24-HT Planning Submit Feasibility Preflight

Phase24-HT adds a Planning-side deterministic preflight before Pending can become `APPROVED`.

Lifecycle:

```text
Planning
  -> Planning Submit Feasibility Preflight
  -> Pending
  -> Submit Guard
  -> Broker boundary
```

The preflight uses the same canonical Runtime authorities as Submit Guard for deterministic BUY feasibility:

```text
CapitalDeploymentPolicy
Runtime Current / Persistent Ledger
Safety decision
Pending duplicate / reservation evidence
```

The canonical hard exposure authority remains:

```text
current_exposure = sum(Runtime Current positions[].market_value)
remaining_exposure = active CapitalDeploymentPolicy.max_exposure - current_exposure
BUY feasible = current_exposure + planned BUY estimated_amount <= active CapitalDeploymentPolicy.max_exposure
```

Phase24-ID extends this from item-only feasibility to approved Pending-batch
feasibility.  Planning Submit Feasibility and Submit Guard must evaluate the
approved Pending item set as one ordered feasibility set before the
broker/adapter boundary.  BUY items reserve cash, buying_power, exposure, and
a new position slot when the symbol is not already held.  Later BUY items must
see the reserved state left by earlier BUY items in the same Pending plan.
SELL items remain exposure-reducing liquidation actions, but same-day SELL
proceeds or exposure reductions are not pre-credited to BUY feasibility unless
a later explicit contract approves that behavior.

Failure behavior:

```text
aggregate cash / buying_power / exposure / max_positions violation
  -> REVIEW_REQUIRED before APPROVED Pending or before Submit adapter boundary
  -> no broker submit attempt for the invalid batch
  -> Submit Guard remains the final hard guard and revalidates independently
```

Runtime-owned fill projection must not clamp an invalid negative cash result
into PASS.  If replayed fills produce cash or buying_power below zero under
the cash authority, the projection is REVIEW_REQUIRED and must materialize the
raw projected value for reconciliation.

Planning must not advance an order to `APPROVED Pending` when deterministic Submit feasibility is known to fail. The failed item remains non-submittable and the Pending lifecycle becomes `REVIEW_REQUIRED`.

Submit Guard remains the final hard guard and repeats all checks. Planning preflight evidence is advisory proof for Pending approval and never bypasses Submit Guard.

#### Phase24-HV BUY Review / SELL Continuation Scope

Phase24-HV separates item-scoped BUY review from independent SELL continuation.

`REVIEW_REQUIRED` must be classified with a structured review scope:

```text
BUY_ITEM_SCOPED_REVIEW:
  A BUY item is non-submittable, but the reason does not invalidate
  independent Position Management, SELL Planning, or SELL Submit authority.

PORTFOLIO_SCOPED_REVIEW:
  Portfolio-wide risk, construction, cash, exposure, or authority conflict
  may invalidate BUY and SELL continuation.

GLOBAL_SAFETY_REVIEW:
  Safety, broker write, runtime environment, emergency stop, or global
  operation authority requires fail-closed behavior for BUY and SELL.

AUTHORITY_UNKNOWN_REVIEW:
  Missing, corrupt, ambiguous, stale, or mismatched authority requires
  fail-closed behavior until reviewed.
```

Pending must expose item-side status separately from the legacy lifecycle state:

```text
buy_items_status
sell_items_status
plan_overall_status
approved_buy_item_ids
approved_sell_item_ids
review_required_buy_item_ids
review_required_sell_item_ids
review_scope
review_scope_source
review_scope_reason
sell_continuation_allowed
```

Legacy `state=REVIEW_REQUIRED` remains valid, but consumers must not assume it means every side is globally blocked. A BUY item with `BUY_ITEM_SCOPED_REVIEW` must never be submitted, must not be promoted back to `APPROVED`, and must not be silently removed from evidence.

Position Management / SELL Planning may continue only when all of the following are true:

```text
review_scope = BUY_ITEM_SCOPED_REVIEW
approved BUY ids are empty for blocked BUY items
same-business-date Historical Safety authority is valid or resolvable
Current / Persistent Ledger position authority is READY
PM authority is valid
SELL Planning inputs are complete
no portfolio-wide, global safety, or authority-unknown blocker exists
the BUY review reason does not invalidate SELL risk handling
```

Historical Daily Neutral Safety Authority may be used for SELL continuation only when Safety itself is not in review, the Pending review is structurally classified as `BUY_ITEM_SCOPED_REVIEW`, and SELL has independent valid authority. Missing Safety, business-date mismatch, policy mismatch, corrupt Pending, ambiguous review scope, portfolio-wide review, global safety review, or unknown authority remain fail-closed.

Submit remains item-boundary hard validation:

```text
BUY REVIEW_REQUIRED -> not submitted
SELL APPROVED -> Submit Guard revalidates -> submitted only if final guard PASS
```

Failure behavior:

```text
PASS:
  Pending may become APPROVED when approval evidence is otherwise valid.

REVIEW_REQUIRED:
  Pending must not become APPROVED.
  Evidence must include violated policy, source, version, current exposure,
  remaining exposure, planned amount, and reason.

HALT:
  Reserved for missing or structurally invalid canonical authority after its
  expected materialization point, or for a Safety decision requiring halt.
```

Mode behavior:

```text
Historical:
  Uses historical Runtime Current / Persistent Ledger and historical Safety
  authority; no historical-only policy branch.

Demo:
  Uses demo Runtime Current / Persistent Ledger and demo Safety/Broker
  read-only evidence where applicable.

Production:
  Uses production Runtime Current / Persistent Ledger, production Safety, and
  broker boundary evidence where applicable.
```
- Safety / Operation Guard
- explicit SELL liquidation policy

SELL liquidation は Broker-only position、report 由来 position、日付別 artifact から推測した position、Runtime-owned であることを Current / Ledger で確認できない position を対象にしてはならない。

#### Capital Allocation と Submit Guard の境界

Runtime は Capital Allocation の出力を後段で勝手に変更しない。

Submit Guard は Broker Write 直前の安全確認であり、資金配分の再決定ではない。Submit Guard ができることは以下に限定する。

- Pending / Approval / policy source の整合を確認する。
- Broker Write 前に明示 policy 違反を検出する。
- Current / buying_power / Broker available quantity / duplicate submit を確認する。
- 違反時に `REVIEW_REQUIRED`、`BLOCKED`、`HALT` として止める。
- なぜ止めたかを manifest / report / audit に出す。

Submit Guard がしてはならないことは以下である。

- Capital Allocation amount を hidden cap で縮小する。
- BUY 用 cap を SELL liquidation に流用する。
- Planning が出した注文を、設計にない現金温存・銘柄数・注文金額 policy で silent block する。
- `tests pass` だけを理由に policy source 不明の guard を正規化する。

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
persistent_ledger/cash.jsonl
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
persistent_ledger/cash.jsonl
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
- Runtime は年 50% 運用目標を直接達成する AI ではないが、Capital Allocation / Risk Policy が決めた資金配分を隠れ固定値で阻害しないことが明記されている。
- Capital Deployment Contract として、目標投資率、現金バッファ、最大 1 銘柄比率、最大保有銘柄数、最小注文金額、最大注文金額、BUY/SELL 別 notional guard、Safety 停止条件を明示 policy として扱うことが定義されている。
- Phase15-A の目的に基づき、Runtime が隠れ保守化・隠れ停止・隠れ資金配分変更によって AI Fund Lab v2 の目的を阻害してはならないことが明記されている。
- target investment ratio、cash buffer、max exposure、position sizing、buying power usage、order size、rebalance / replacement、position count、SELL-first / BUY-after-fill は Runtime の判断ではなく明示 contract として扱うことが明記されている。
- Runtime が `max_positions` を隠れ固定値として持たず、設定する場合は Capital Deployment Contract / Risk Policy として manifest に出力することが明記されている。
- Runtime が固定注文金額上限を持たず、BUY 上限は evaluation capital、target investment ratio、cash buffer、max exposure、max position weight、buying_power、price、lot size、broker constraint、safety result から導出することが明記されている。
- Submit Guard が Capital Allocation を hidden fixed cap で上書きしてはならないことが明記されている。
- `max_order_amount` のような注文金額 guard は設計契約、manifest、test で明示されなければならないことが明記されている。
- BUY notional guard と SELL liquidation guard を同一扱いにしないこと、統一する場合は設計根拠を明記することが定義されている。
- SELL liquidation の source は Runtime-owned Current position のみであり、Broker-only position を売却対象にしないことが明記されている。
- Submit Guard の active policy を manifest / audit に出力することが明記されている。
- Submit Guard が止める場合、違反 policy、policy source、BUY/SELL区分、manual review required、Planning側で防ぐべきかSubmit側で止めるべきかを manifest / report / audit に出すことが明記されている。
- Demo / Production を保存先ではなく metadata で分けることが明文化されている。
- Broker Orders fallback が Demo 限定であり、Production の現在保有確定に使わないことが明文化されている。
- `demo_ledger/` の legacy 化方針が明文化されている。
- Report / Notification / Audit が Derived / Evidence 層であり、Runtime Current 入力ではないことが明文化されている。
- Phase15 Review Rule として Runtime Evidence First Rule、Evidence Request Rule、No Guess Rule、Review Level 区別、PASS誤認禁止が明記されている。
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
- BUY over 100,000 JPY amount policy test through the regular CLI submit path
- SELL liquidation over 100,000 JPY amount policy test through the regular CLI submit path
- Capital Allocation -> Pending -> Submit Guard contract alignment test
- Capital Deployment Contract -> Capital Allocation -> Pending -> Submit Guard alignment test
- `max_positions` policy manifest and enforcement test
- CLI regular submit path amount policy test
- Submit Guard active policy manifest test
- Broker-only position is never selected as SELL source test
- Runtime-owned Current position is the only SELL liquidation source test

`tests pass` は必要条件であり、単独の Acceptance 条件ではない。Runtime v2 の実装受け入れには、以下を同時に満たす必要がある。

- 設計契約に一致している。
- Input / Output / Consumer の schema、単位、意味が一致している。
- 通常 CLI path で検証されている。
- Manifest / Current / Ledger / Report / Audit に証跡が残っている。
- fake adapter や test-only path の結果を Runtime 本線成功として扱っていない。

Review level は以下を明示する。

| Level | 名称 | 意味 | 制限 |
| --- | --- | --- | --- |
| Level 1 | Component PASS | Component 単体の Input / Output / Consumer が合う | fake / fixture 使用可。本番 Runtime 成功とは呼ばない |
| Level 2 | Flow PASS | BUY / SELL / Notification など Flow 単位で通常 Runtime 経路を確認する | fake adapter 不可。必要に応じ Demo Broker ReadOnly / Submit 証跡を要求する |
| Level 3 | Full Runtime PASS | Market Refresh / Morning / Submit / Execution / Current / Report / Notification まで通常 Runtime で通す | 運用開始前や重大契約変更後に要求する |

### 22.3 Phase15 Review Rule

Phase15 以降、Runtime v2 のレビューは以下の原則で行う。

#### Runtime Evidence First Rule

Runtime 状態を推測で判断しない。確認可能な場合は、Runtime artifact、Runtime Manifest、Broker ReadOnly、Current SoT、Persistent Ledger、Report、Notification payload / delivery ledger、Regression result を優先する。

#### Evidence Request Rule

証拠が不足している場合、修正指示を出す前に Operator へ必要最小限の確認コマンドを提示する。大量のコマンドを一度に要求しない。1〜2個の確認結果を見て、次の確認または判断へ進む。

#### No Guess Rule

`PASS`、`FAIL`、原因、Runtime 状態を推測で断定しない。

レビュー順序は以下とする。

```text
Runtime Evidence
↓
Review
↓
Judgment
```

#### PASS 誤認禁止

以下はいずれも単独では Acceptance ではない。

- `tests pass`
- `Broker Accepted`
- `Report generated`
- `Payload generated`
- manifest generated
- fake adapter PASS
- fixture PASS
- test-only path PASS

`Broker Accepted` は Broker が注文を受け付けた証拠であり、Runtime が Capital Allocation / Safety / Current / Report / Notification と整合している証拠ではない。

`Report generated` は Report artifact が生成された証拠であり、Report が Current / Today / Run / Ledger History を意味的に正しく分離している証拠ではない。

`Payload generated` は Notification payload が生成された証拠であり、Notification delivery、delivery ledger、二重送信防止、送信結果 audit が正しく機能した証拠ではない。

Phase15 の Runtime PASS は、以下の一致が確認された場合のみ宣言できる。

```text
Design Contract
↓
Implementation
↓
CLI Regular Path
↓
Runtime Manifest
↓
Broker Evidence
↓
Current SoT
↓
Report
↓
Notification
↓
Regression
```

## 22.4 Phase15-X Runtime Reality Rule / Demo-Production Boundary Contract

Phase15-X 以降、Runtime v2 は Demo 環境で検証する場合でも Production Reality を基準に設計する。

### Runtime Reality Rule

```text
Runtimeは常にProduction Realityを基準として設計する。

Demo環境の制約はRuntime仕様ではなく、
Broker Environment / Broker Capability / Broker Evidenceとして扱う。

Demo専用Runtime、Phase専用Runtime、Fake Runtime、
Demo専用Current、Demo専用Ledger、Demo専用Policyは作らない。

Demo / Productionの差異はBroker LayerまたはCapability Layerで表現し、
Runtime Coreの制御契約は共通に保つ。
```

Runtime Core は以下を Demo / Production 共通の制御契約として扱う。

```text
Policy
↓
Safety
↓
Planning
↓
Pending
↓
Approval
↓
Submit Guard
↓
Broker Boundary
↓
Execution
↓
Ledger
↓
Current
↓
Report
↓
Notification
```

Demo のログイン可能時間、注文・約定可能時間、メンテナンス、約定不可銘柄、日次リセット、Production との差異は Runtime Core の hidden branch にしない。これらは Broker Environment / Broker Capability / Broker Evidence として manifest / report / notification に証跡化し、必要に応じて `REVIEW_REQUIRED` にする。

### Demo / Production Boundary Contract

| Layer | Responsibility | Demo Handling | Production Handling |
| --- | --- | --- | --- |
| Runtime Core | Policy / Safety / Planning / Pending / Approval / Submit Guard / Ledger / Current / Report / Notification の制御契約 | Production Reality と同じ契約で動かす | 同じ契約で動かす |
| Broker Environment | 接続先、mode、endpoint、ログイン時間、注文時間、メンテナンス状態 | `broker_environment=demo` として証跡化する | `broker_environment=production` として証跡化する |
| Broker Capability | 約定可否、銘柄制約、数量制約、利用可能 API、口座状態差分 | Demo 制約を capability として表現する | Production capability として表現する |
| Broker Evidence | Broker ReadOnly snapshot、available quantity、window status、API error classification | Demo 制約による `production_equivalent=false` / `review_required=true` を明示する | Production equivalent evidence を要求する |
| Acceptance | Runtime の設計契約一致確認 | Demo 差異を理由に Runtime PASS を水増ししない | Production unlock は別 gate とする |

許可される Demo / Production 差異表現は以下に限定する。

```text
broker_environment=demo
broker_mode=demo
broker_capability
production_equivalent=false
review_required=true
broker evidence classification
```

禁止する実装パターンは以下である。

- `if demo:` による特別な売買ロジック
- `if phase15:` による特別な Runtime 経路
- `demo_current.json`
- `demo_ledger.json` を Runtime v2 の本線 SoT として使うこと
- Demo 専用 Policy / Safety / Submit / Execution
- Demo でだけ通る Current projection
- Demo でだけ通る Report
- Demo 制約を避ける Runtime bypass

### Demo API Error Triage

Demo Runtime Review で Broker API エラーが発生した場合、いきなり Runtime bug と断定しない。一次切り分けは以下の順で行う。

```text
1. Broker login window
2. Broker order/execution window
3. Broker maintenance
4. Demo-specific execution restriction
5. Demo reset / account state reset
6. Broker capability mismatch
7. Runtime bug
8. Broker API behavior change
```

この triage 結果は Broker Evidence として保持し、Runtime Core の hidden policy や Demo 専用分岐で吸収しない。

### Required Broker Environment Evidence

Demo Runtime Review では、最低限以下を manifest / report の対象 evidence とする。

```text
broker_environment
broker_mode
broker_capability
login_window_status
order_window_status
maintenance_status
demo_execution_restriction_detected
demo_reset_detected
production_equivalent
review_required
```

これらは Runtime Core の分岐条件ではなく、Broker Boundary の証跡である。`production_equivalent=false` または source が不明な場合は、Runtime が正常に止まったことを Acceptance 対象にし、正常に売買継続したことを PASS にしない。

## 22.5 Phase15-Y Non-Trading-Day Demo Acceptance Override

Phase15-Y では、Demo Runtime Evidence Review 中に限り、非営業日でも Demo Acceptance 用の evidence 取得を継続できる明示 CLI option を定義する。

```text
--allow-non-trading-day-demo
```

この option は Runtime Core の営業日判定を削除・緩和するものではない。Production Reality を基準にした Runtime Reality Rule を維持し、Demo の非営業日 API 利用可能性を Broker Environment / Broker Capability / Broker Evidence として扱うための、Operator 手動実行専用の acceptance override である。

### Contract

| Case | Expected Runtime Decision | Evidence |
| --- | --- | --- |
| `--mode production --allow-non-trading-day-demo` | `BLOCKED` | `reason=non_trading_day_demo_override_forbidden_in_production` |
| `--mode demo` / 非営業日 / override なし | `REVIEW_REQUIRED` or `BLOCKED` | `reason=non_trading_day` |
| `--mode demo` / 非営業日 / override あり | Demo Acceptance scope only | `non_trading_day_demo_override=true`, `production_equivalent=false` |
| 営業日 / override あり | 通常営業日動作 | `non_trading_day_demo_override=false` or `not_applicable` |

### Required Evidence

Runtime Manifest / Report / Notification payload は、override が評価された場合に以下を保持する。

```text
trading_day
business_day
market_open
non_trading_day_demo_override
override_source
override_reason
production_equivalent
acceptance_scope
```

非営業日 override が有効な実行は以下として扱う。

```text
DEMO_ACCEPTANCE_OVERRIDE
```

これは Full Runtime PASS ではない。Production Equivalent でもない。Demo Evidence Review 用の補助であり、Production 運用可能性を意味しない。

### Constraints

- Production では絶対に有効化しない。
- Demo でも default は無効であり、非営業日は通常停止する。
- launchd / autonomous operation では使わない。
- Runtime v2 launchd plist に `--allow-non-trading-day-demo` を追加しない。
- Demo 専用 Runtime / Current / Ledger / Policy / Submit / Execution は作らない。

## 22.6 Runtime Temporal / Freshness Contract

Runtime v2 の日時、鮮度、営業日、市場データ更新、Current 評価基準は、正式 Source of Truth として以下に定義する。

```text
docs/02_architecture/runtime_temporal_freshness_contract.md
```

Runtime Architecture v2 は、単一の `as_of` や `artifact_date == business_date` だけで freshness を判定しない。以下を必ず分離する。

```text
runtime_business_date
latest_expected_trading_date
latest_available_market_date
market_data_as_of
feature_date
broker_snapshot_at
position_state_as_of
valuation_as_of
last_execution_date
safety_generated_at
safety_expires_at
pending_target_session_date
artifact_generated_at
```

特に Current は、Position State と Valuation State を分けて扱う。

```text
position_state_as_of
valuation_as_of
last_execution_date
last_reconciled_at
source_market_date
updated_at
```

旧来の単純契約:

```text
Current.as_of == business_date
```

は廃止または互換 fallback に限定する。約定がない日は Position State が前営業日のままでも正常であり得る。一方、Market Evidence が更新済みで Current valuation が更新されていない場合は valuation freshness の問題として扱う。

Runtime v2 は、No-Fill / Valuation-Only の正規 Producer を必要とする。この Producer は Runtime-owned position だけを対象に評価価格を更新し、Broker-only position を Current へ混入させず、quantity / average_price を変更しない。

Market / Quote Evidence も正式 contract として扱う。

```text
.runtime/runtime_state/market/<market_date>/market_evidence.json
```

この artifact は `runtime_business_date`、`market_date`、`latest_expected_trading_date`、`latest_available_market_date`、`quotes`、`market_summary`、`provider_status`、`data_not_yet_available`、`stale` を持つ。J-Quants の当日データがまだ配信されていない状態は、即 `STALE` ではなく `DATA_NOT_YET_AVAILABLE` として分類する。

Data Readiness、Safety、Report、Notification は Temporal / Freshness Contract を共通参照し、以下のような component status を出す。

```text
market_freshness_status
feature_freshness_status
current_position_status
current_valuation_status
broker_snapshot_status
safety_temporal_status
pending_temporal_status
```

これにより、非営業日、祝日、配信前、約定なし、Broker Snapshot のみ当日、Demo reset などを Runtime Core の hidden branch ではなく、明示 Evidence として扱う。

## 23. 禁止事項

## Phase17-G 追補: Submit Guard Environment Matrix

Runtime v2 Submit Guard は、Demo 専用 guard ではなく、Runtime Environment Matrix を確認する正規 guard として扱う。

| runtime environment | pending environment | run type | broker environment | adapter | broker write | external delivery |
|---|---|---|---|---|---:|---:|
| `demo` | `demo` | `DEMO` | `tachibana_demo` | Demo submit adapter | true | environment policy に従う |
| `historical` | `historical` | `HISTORICAL` | `historical_simulated` | `HistoricalSubmitAdapter` | false | false |
| `production` | `production` | `PRODUCTION` | `tachibana_production` | Production submit adapter | explicit production acceptance required | production policy に従う |

Environment Matrix は Submit Guard の先頭で確認する。Matrix 不一致、adapter 不一致、`broker_write` 不一致、`external_delivery` 不一致、または Historical の `business_date` / `evaluation_time` 欠落は fail closed とする。

`broker_write=false` は Runtime Submit / Execution / Ledger / Current の通常 mainline を停止する意味ではない。外部 Broker API への write delivery を禁止する意味であり、Historical では `HistoricalSubmitAdapter` と `HistoricalExecutionSnapshotProvider` が Runtime v2 の通常 Submit Guard、Execution Processor、Ledger、Current Apply に接続する。

Historical は Runtime v2 の正式 environment である。ただし Current / Ledger / Pending / Runtime State は mode-rooted path へ分岐しない。Current object path は通常 `.runtime/...` に固定し、`--mode historical` と environment evidence で実行境界を識別する。

Phase17-G の Historical Fill Model は 5BD Historical Runtime Smoke Test 用の最小実行仮定である。Market order は対象営業日の Canonical OHLCV `Open` を fill price とし、PIT manifest hash、Listed Issues PIT universe、Corporate Action no-impact guard、duplicate submit evidence、cash / quantity guard を必須 evidence とする。Fees、tax、slippage、partial fill、long-term performance 用の厳密 execution model は 20BD 以降の別 acceptance とする。

## Phase23-P 追補: Historical Evaluation Accepted Generation Authority

Historical Runtime Test は、Production-common Runtime chain を変更せず、run開始時に現在Human Accepted済みのRuntime-consumable Accepted Generationを1件固定して評価する。

Production / Demo Runtime のAccepted Generation Authorityは従来どおり `business_date` 時点のPIT Authorityであり、次を維持する。

```text
accepted_at <= business_date
effective_from <= business_date
```

Historical Runtime Evaluationでは、Accepted Generationの `accepted_at` / `effective_from` をhistorical business dateへ比較しない。代わりに `reports/runtime_tests/runs/<run_id>/historical_evaluation_authority.json` に保存されたrun-start fixed authorityをRun全体で使用する。

Historicalの日次PIT判定対象は以下に限定する。

```text
Market Data
Financial Data
Corporate Event
Feature
Calendar
```

禁止事項:

- Historical専用Strategy
- Historical専用AI判断
- Historical専用Accepted Generation差し替え
- latest fallback
- future market / financial / corporate event / feature data
- run中のAccepted Generation切替
- Accepted日時改ざん
- Broker Write
- Runtime Switch

Historical final summaryは `evaluation_mode`、`training_cutoff`、`evaluation_period`、`training_overlap` を保持する。training overlapがある場合は `STRICT_OOS` と表示してはならない。

## Phase23-Q 追補: Production-common Daily Scheduler Environment Alignment

Runtime v2 daily operation scheduler / CLI は Historical 専用schedulerを新設せず、同一entrypointで `production`、`demo`、`historical` を扱う。

正式entrypoint:

```text
python -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation
```

Historical Runtime Test runner はこのentrypointへ次を渡す。

```text
--mode historical
--broker-environment historical_simulated
--business-date <historical business date>
--evaluation-time <explicit evaluation time>
--notification-mode payload-only
--market-refresh-allow-api-fetch false
--runtime-test-run-id <run_id>
--runtime-test-evidence-root reports/runtime_tests/runs/<run_id>
--historical-evaluation-authority reports/runtime_tests/runs/<run_id>/historical_evaluation_authority.json
```

Historical `market_refresh` は外部fetchを行わず、historical business dateに束縛された既存canonical / PIT inputを解決する。必要なhistorical inputが欠損する場合は、`historical_asof_authority_invalid`、`physical_source_missing`、`historical_market_input_missing` 等の具体的reasonでfail closedし、Demo-only scheduler guardで停止してはならない。

Production / Demo のscheduler安全条件は維持する。Production submitはscheduler rehearsalからBroker Writeを許可せず、別途Production acceptance boundaryを必要とする。

## Phase19-AV 追補: AI Status Inspection

Runtime Test `ai-status` は Runtime Authority を変更するコマンドではなく、COMMITTED Accepted Generation と Runtime Readiness を確認する read-only operational observability command である。

確認対象:

```text
COMMITTED Accepted Generation pointer
Accepted Generation Manifest
Candidate / Opportunity model, scaler, calibration binding
Dataset lineage
Versioned split
Latest J-Quants
Latest BUY feature
Eight-part freshness taxonomy
Runtime lifecycle gate
Legacy fallback absence
Broker access absence
```

`ai-status` は Authority Resolver の結果を表示するだけであり、`latest`、mtime、legacy fallback、manual path、promotion candidate を Runtime authority として選択してはならない。`--write-evidence` は監査レポートを `reports/runtime_tests/ai_status/<run_id>/` に保存するだけで、Accepted Generation pointer、authority history、Current、Pending、Ledger、Safety、Broker、BUY/SELL state を変更してはならない。

Structural issue は BLOCK、統計 Drift のみは REVIEW_REQUIRED として扱う。統計 Drift の REVIEW_REQUIRED は BUY 自動停止ではなく、Human monitoring / review の信号である。

## Phase19-AX 追補: System Status

Runtime Test `system-status` は、日次運用開始前に実行する正式な read-only system health command である。通常運用の推奨入口は `system-status` とし、`ai-status` は AI Artifact Inspection 専用に位置付ける。

`system-status` は以下を一度に確認する。

```text
Data
AI
Runtime
Runtime State
Broker Layer
Overall
```

Broker Layer の Broker Connection は、このコマンド内では外部接続を実行しない。`NOT_PERFORMED` を明示し、Broker credential access、Broker API access、Broker write、notification send は禁止する。

`system-status` の標準出力は日次運用向けの compact operator overview とする。少なくとも Inspection Context、分離された status judgments、主要な Data freshness、Runtime execution/current-state status、Accepted Generation age（秒・時・日など単位付き）、重要 findings、最終 scoped judgment を表示する。完全な human inspection report は `--scope full` または `--full` alias で明示的に要求する。

`system-status` は `--scope overview|data|ai|runtime|broker|readiness|lineage|components|full` を受け付け、1 invocation につき単一 scope のみを選択する。`--json` は選択 scope に対応する v2 fields（`scope`、`inspection_context`、`status_summary`、`findings`、`sections`）を出力し、既存consumer互換のため top-level `system_status_report` に従来の full legacy report を保持する。

Full scope では Runtime Stage、Pre-run Readiness、Day1 Start Permission、Active Component Inventory、Data Sources、Datasets、Runtime Features、AI Models、AI Data Window Summary、Decision Subsystems、Accepted Generation / Authority、Runtime State、Broker Layer、Freshness Matrix、Findings、Non-mutation Guarantee、Exit Code を表示する。Candidate は evaluated_symbols と candidate_output_count を分離し、Opportunity は input_candidate_count、ranking_count、top20_count を分離して表示する。

Phase19-BE 以降、`system-status` の human inspection report は AI input lineage を JSON と同じ粒度で表示しなければならない。Candidate / Opportunity それぞれについて、training dataset revision、dataset artifact / manifest path、source authority、source earliest/latest date、source row/symbol count、schema/content hash、Training / Calibration / Validation / Test / Recent Holdout split window statistics、recent holdout non-use、calibration / validation independence を表示する。Runtime input lineage は pre-run では計画契約として表示し、target-date feature / inference が未生成の場合は空欄ではなく `NOT_YET_MATERIALIZED` を用いる。

Phase19-BF 以降、`system-status` は Runtime の全運用Component監査を含む。Market Refresh、Feature Refresh、Candidate AI、Opportunity AI、Lifecycle Monitoring、Safety、BUY Planning、SELL Planning、Approval、Submit Guard、Execution Guard、Ledger Update、Reporting、Notification までのRuntime chainを表示し、各Componentの責務、Authority、Implementation、Input/Output Artifact、Input Components、Input/Output Business Date、Configuration Status、Runtime Status、Inspection Status、J-Quants依存有無を human / JSON の両方へ出す。Repository上の運用Componentが未監査の場合は `COMPONENT_NOT_INSPECTED` / `REVIEW_REQUIRED` とし、PASSしてはならない。

Phase19-BG 以降、`system-status` の status semantics は完全に分離する。`implementation_status`、`configuration_status`、`authority_resolution_status`、`inspection_status`、`target_date_execution_status`、`runtime_result_status` は別フィールドであり、PRE_RUNで対象日処理が未実行のComponentをRuntime結果PASSとして表示してはならない。J-Quants依存は `DIRECT` / `INDIRECT` / `NONE` と dependency path / direct input artifacts / reason で示す。Historical source coverage の最新日と Runtime consumer cutoff date は別概念であり、sourceが対象日より未来まで存在しても consumer cutoff が対象日で future rows consumed がない限り異常ではない。

Runtime State Safety は Safety Decision artifact の実行タイミングを区別する。対象 business date の Runtime route がまだ開始していない場合、`.runtime/runtime_state/safety/latest_safety_decision.json` の missing は `PRE_RUN_NOT_MATERIALIZED` / `NOT_YET_APPLICABLE` として扱い、これだけで Day1 開始を止めない。対象 business date の Safety または Morning route が実行済みなのに artifact がない場合は `POST_RUN_MATERIALIZATION_MISSING` / `BLOCK` とする。artifact が存在する場合は expected business date と artifact business date の一致を確認し、不一致は `REVIEW_REQUIRED` とする。

Pre-run artifact semantics are stage-aware. Runtime Features、Candidate/Opportunity Inference、AI Lifecycle Gate、Runtime Baseline/Freshness target-date decision、BUY Planning、SELL Planning、Approval、Submit、Execution、Reporting、Notification は、それぞれの expected generation stage 前なら `NOT_YET_APPLICABLE` とし、stage 通過後も欠落している場合だけ `POST_STAGE_MATERIALIZATION_MISSING` / `BLOCK` とする。`system-status` は COMMITTED Accepted Generation の authority、model artifact、scaler、calibration、hash、read-only loader validation と、target-date feature/inference artifact の有無を混同してはならない。

Historical freshness is coverage-based. Historical mode では `required_through_date`、`available_through_date`、`missing_required_business_days`、`coverage_ahead_business_days` を分離し、target date より先までデータがある状態を lag と呼ばない。Temporal Guard は Runtime consumer input が target business date より未来の行を利用しないことを別途検証する。

`system-status` の PASS は `inspection_context` 内でのみ有効である。Historical isolated pre-run の PASS は Production/Demo current-data readiness、Broker connectivity readiness、BUY_READY、PRODUCTION_READY、Autonomous Operation Complete を意味しない。これらは `environment_readiness` で `NOT_EVALUATED`、`NOT_PERFORMED`、または `PROHIBITED` として分離表示する。

Historical Runtime Test 完了後に active run が存在せず、最新の compatible closed run が inspected runtime root と一致する場合、`system-status` は `HISTORICAL_POST_RUN` context を表示する。この場合の target business date は profile の `date_from` ではなく closed run の最終 completed business date である。Ledger / Current / Pending / Runtime Feature / AI inference / Lifecycle / Safety の日付比較は同一 context に揃え、Day1 と Day5 を混在させて `TEMPORAL_STATE_CONTAMINATION` としてはならない。ただし実際に target business date より未来の consumer state を参照した場合、または closed run の Safety authority が欠落・不一致の場合は fail-closed を維持する。

Broker Layer は truthfulness-first で表示する。Broker Configuration と Submit Guard Configuration が PASS でも、Broker Connectivity Check、Credential Access、Broker Write が未実施なら `NOT_PERFORMED` / `PROHIBITED` とし、aggregate は `CONFIGURATION_PASS_CONNECTIVITY_NOT_PERFORMED` のように誤解できない値にする。

Phase19-BW 以降、Runtime execution judgment と AI Model Health judgment は独立して表示する。Model Health が統計 drift 等で `REVIEW_REQUIRED` の場合も、Runtime Consumer / BUY impact / SELL impact が PASS/NONE であれば Runtime execution を `REVIEW_REQUIRED` に格下げしてはならない。Model Health finding には trigger、classification、metric、threshold、policy、observed、BUY impact、SELL impact、Runtime impact を含める。

Historical post-run context では、closed run evidence、final completed business date、target-date exact-match artifact を authority とする。成功済みrun後に retention 対象外の transient feature artifact が存在しないことは Target-period Data Sufficiency の BLOCK ではない。Position runtime feature は target-date feature rows と final post-run positions を別 authority として扱い、target-date時点で position rows が0である temporal isolation と、run完了後に ledger/current にpositionが残る状態を混同してはならない。2099 fixture artifact や future fixture directory は Runtime freshness / target-date resolution に使用してはならない。

`system-status` の Evidence 書き込みは `reports/runtime_tests/system_status/<run_id>/` に限定する。Current、Pending、Ledger、PM、Safety、Accepted Generation pointer、authority history、Runtime transition history、Broker state を変更してはならない。

## Phase24-HY Opportunity Rank Consumer Contract

Runtime Planning receives opportunity-backed Strategy lineage from Portfolio Construction and Position Sizing. The canonical opportunity rank owner is the Runtime BUY AI Opportunity Ranking Producer, with `opportunity_buy_rank` semantics materialized as `buy_rank` in `.runtime/runtime_state/buy_ai/<business_date>/opportunity_rankings.json`.

The Strategy adapter must map opportunity rows as follows:

```text
opportunity_rankings.json row
  buy_rank / opportunity_buy_rank
    -> opportunity_buy_rank
    -> Portfolio Construction input_opportunity_rank
    -> Position Sizing opportunity_buy_rank
    -> Runtime Planning opportunity_buy_rank
    -> Pending lineage when an item is generated
```

For opportunity rows, Runtime consumers must not substitute `candidate_rank`, candidate model rank, adapter index, artifact array order, or recomputed rank. Missing, invalid, or conflicting opportunity rank authority is `REVIEW_REQUIRED` and row-consumer rejection. This is a lineage and consumer alignment repair only; it does not change Opportunity Ranking production, eligibility, Portfolio Policy, Position Sizing policy, PM, Submit Guard, max exposure, cash buffer, or order quantities.

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
- 既存 Runtime / 旧処理 / 既存 helper を、設計契約と Input / Output / Consumer を確認せずに無批判に流用する。
- 旧処理を参考にしたにもかかわらず、どの契約を継承しないかを明記しない。
- 旧 Runtime の安全 guard、注文金額 cap、保有銘柄数 cap、銘柄フィルタ、停止条件を、Runtime v2 の設計契約レビューなしに持ち込む。
- test-only module、phase-only branch、demo-only branch、Runtime bypass を Runtime v2 の正規成功証跡として扱う。
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
- `max_positions`、目標投資率、現金バッファ、最大 1 銘柄比率、最小注文金額、最大注文金額を Runtime の暗黙値として扱う。
- Capital Allocation の意図を、設計契約にない hidden fixed cap で Submit 直前に上書きする。
- BUY notional guard を、設計根拠なしに SELL liquidation guard として流用する。
- SELL liquidation を BUY の注文金額上限だけで機械的に止める。
- Broker-only position を Runtime-owned SELL liquidation の対象にする。
- `tests pass`、manifest 生成、Broker Accepted、Report 生成のいずれか単独を Runtime v2 Acceptance として扱う。
- `POST_SEND_UNKNOWN` を自動再送で解決する。
- raw request、raw response、secret、session、URL、口座識別子を保存する。

## Phase24-IL Corporate Action Adjustment Authority

Corporate Action Adjustment Authority is the Runtime v2 contract that proves an impacted symbol is safe to submit after a quantity/price adjustment event. It is a Production/Demo/Historical common authority and is not a Historical-only bypass.

Submit and historical simulated submit must keep the Corporate Action Guard fail-closed. `AdjFactor != 1` or any equivalent impact signal is not sufficient to pass. An impacted item may pass only when a Runtime-owned adjustment authority proves:

- event type is resolved by PIT authority and is not inferred from `AdjFactor` alone
- effective date and source artifact hash match the submit business date input
- future data was not used
- ledger, current, pending, and submit quantities are on the same adjusted basis
- SELL submit quantity is positive and does not exceed adjusted Runtime-owned or broker-available quantity
- the same event has not been applied twice across resume/retry

Missing, unresolved, stale, mixed pre/post adjustment quantity, source hash mismatch, future snapshot use, or double-adjustment risk is fail-closed as `REVIEW_REQUIRED` or `BLOCK` before broker boundary. Submit Guard thresholds, Strategy, PM, Position Sizing, Capital Deployment policy, and order quantities are not changed by this authority.

## Phase26-G Adaptive BUY Quality Runtime Propagation Contract

Runtime v2 consumes, verifies, and propagates Adaptive BUY Quality lineage; it does not recompute BUY Quality.

Canonical Strategy specification:

```text
docs/02_architecture/adaptive_buy_quality_authority.md
```

The canonical artifact is `buy_quality_decision.v1`, produced by the Production Strategy BUY Quality Resolver. It must be PIT-bound to the same business date, Accepted Generation, Opportunity row, and temporal authority used by the BUY planning chain.

Runtime propagation:

```text
BUY Quality Artifact
  -> Portfolio Construction
  -> Position Sizing
  -> Runtime Planning
  -> Pending Item
  -> Approval Artifact
  -> Submit Guard Evidence
  -> Order
  -> Fill Observability
  -> Trade Attribution
```

Minimum propagated fields:

```text
quality_decision_id
quality_score
quality_band
quality_action
quality_reason_codes
component_scores
quality_policy_version
source_opportunity_id
```

Failure contract:

- missing required quality decision for BUY positive allocation is fail-closed before Pending/Submit boundary
- `quality_action=REVIEW_REQUIRED` does not cross broker or simulated broker boundary as BUY
- `quality_action=REJECT` produces no BUY item
- source hash, opportunity row, Accepted Generation, or temporal mismatch is `REVIEW_REQUIRED` or `BLOCK`
- Submit Guard may verify lineage/status but must not recompute Quality
- Production, Demo, and Historical use the same propagation contract; no historical-only bypass

## Phase27-D1 Canonical Position Decision and BUY_ADD Runtime Contract

Phase27-D1 defines the common Strategy-side position lifecycle and canonical decision contract that Runtime v2 consumes. The detailed SoT is:

```text
docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md
```

Phase27-D1R refines the Runtime-facing contract by requiring Runtime Planning to consume `position_sizing_plan.v1` and produce `runtime_position_plan.v1` without mutating upstream intent, target portfolio, or sizing artifacts.

Runtime v2 remains an execution system. It must not decide Momentum Continuation, Opportunity ranking, Portfolio membership, target weight, target notional, Position Sizing, HOLD / ADD / REDUCE / EXIT, Incremental Investment Eligibility, or cash deployment posture.

Runtime Planning consumes Strategy quantity candidates and maps them to executable intent:

```text
no current position + positive quantity_delta_candidate -> BUY_NEW
current position + positive quantity_delta_candidate -> BUY_ADD
current position + zero quantity_delta_candidate -> NO_ACTION
current position + negative partial quantity_delta_candidate -> SELL_REDUCE
current position + full negative quantity_delta_candidate -> SELL_EXIT
```

`HOLD` and `NO_ACTION` must remain semantically separate:

- `HOLD` is a Strategy / PM decision that an existing position should remain open.
- `NO_ACTION` is Runtime / Planning no-order output after zero or non-executable delta.

Runtime artifacts should preserve lineage back to the canonical position decision when available:

```text
position_decision_id
position_campaign_id
quality_decision_id
opportunity_id
pending_item_id
order_plan_item_id
```

BUY_ADD may be executable only through the canonical chain:

```text
PM ADD
  -> Canonical Position Decision
  -> Portfolio Construction
  -> Position Sizing
  -> positive quantity_delta_candidate
  -> Runtime Planning BUY_ADD
  -> Formal Planning
  -> Pending
  -> Approval
  -> Submit
  -> Execution
```

The legacy `sell_pipeline -> add_consumer -> pm_add_order_plan -> pending` path is not canonical BUY_ADD decision authority after Phase27-D1. If retained during migration, it may operate only as a compatibility adapter / observability bridge that cannot independently create ADD decisions, quantities, or Pending while canonical BUY_ADD authority is active.

Phase27-D1R adds explicit legacy migration acceptance: legacy pending production count, quantity authority count, and submit authority count must be zero before retirement is accepted; canonical and legacy duplicate keys must be zero; and Production, Demo, and Historical caller inventories must be complete.

Production, Demo, and Historical must use the same Runtime mapping and ADD mutual-exclusion contract. Historical-only bypasses, run-specific ADD behavior, and direct PM ADD-to-Pending generation are prohibited.

Phase27-D2-C freezes the retained legacy adapter state as `NON_DECISION_COMPATIBILITY`. The compatibility artifact is `legacy_pm_add_compatibility.v1`; it may record that the legacy path would have been invoked, but it must publish `decision_effect = NONE`, `quantity_authority = NONE`, `pending_authority = NONE`, `approval_authority = NONE`, `submit_authority = NONE`, and `telemetry_only = true`. The legacy adapter must not resolve ADD-specific cash exposure, position sizing, lot rounding, Pending, Approval, Submit, Fill Projection, or Ledger authority.

The canonical/legacy ADD dedup key is `run_id, business_date, symbol, position_campaign_id, decision_id`. Duplicate legacy compatibility records, lineage mismatches, or any overlap where legacy and canonical records both claim executable ADD authority must produce `REVIEW_REQUIRED` or an explicit block. Fail-open behavior is prohibited.

Phase27-D2-D adds `position_sizing_plan.v1` as a shadow Strategy artifact that carries existing-position quantity delta candidates. Runtime Planning must not consume this artifact in D2-D. `BUY_ADD`, `BUY_NEW`, Pending, Approval, Submit, Execution, Fill Projection, and Ledger behavior remain unchanged until a later Runtime integration phase explicitly connects `position_sizing_plan.v1`.

Phase27-D2-E connects `position_sizing_plan.v1` to Runtime Planning as canonical quantity delta input. Runtime Planning remains a mapper only:

```text
position_sizing_plan.v1.quantity_delta_candidate
  -> Runtime Planning planning_intent
```

When canonical quantity delta exists, Runtime Planning must not use PM action fallback on the same row. PM ADD / REDUCE / EXIT / HOLD may be used only in legacy compatibility scope when canonical `position_sizing_plan.v1` is absent. A row with canonical sizing lineage but missing delta plus PM fallback evidence must resolve to `REVIEW_REQUIRED` or `BLOCK`; it must not silently produce an executable order.

Canonical mapping:

```text
no current position + positive delta -> BUY_NEW
current position + positive delta -> BUY_ADD
current position + zero delta -> NO_ACTION
current position + negative delta and target_quantity_candidate > 0 -> SELL_REDUCE
current position + negative delta and target_quantity_candidate = 0 -> SELL_EXIT
```

Runtime Planning must not recalculate Ranking, Momentum, Quality, Opportunity, Incremental Eligibility, PM decision, Portfolio target weight, Position Sizing formula, cash policy, Safety, Submit, or Execution. It records `canonical_quantity_source`, `canonical_quantity_delta_priority`, `pm_fallback_used`, and `pm_fallback_scope` so duplicate authority can be audited.

## Phase30 Final Amendment: Runtime Authority Ownership

Phase30 closed the Production / Demo / Historical common Runtime authority
architecture as conformant. The following contracts are permanent Runtime
architecture rules, not Phase-local test exceptions.

### Canonical Pending Review Scope Authority

`runtime_v2.pending.review_scope_authority` owns only Pending review-scope
semantics:

- structural validity
- lifecycle review scope
- executable and reviewed item membership
- item-scoped review versus batch-level failure semantics
- partial submit eligibility
- sell continuation eligibility
- reviewed items must not submit

It does not own cash, quantity, Strategy cap, Safety hard cap, broker
feasibility, valuation, PM intent, Portfolio Construction allocation, or
Position Sizing.

Consumers must not infer executable subsets from top-level `REVIEW_REQUIRED`
or diagnostic reason strings. They must consume the canonical reviewed and
executable item sets. Reviewed BUY items remain fail-closed for BUY execution.
Reviewed SELL items remain fail-closed for SELL execution. A reviewed BUY must
not block an otherwise valid SELL when the canonical scope explicitly allows
SELL continuation.

### Historical Safety Temporal Authority

`runtime_v2.historical_support.safety_temporal_authority` owns the shared
Historical Safety and temporal binding result consumed by Data Readiness,
Sell Planning, Submit Data Readiness, Execution, Current Valuation, and Pending
Lifecycle. It consumes Pending review-scope authority but must not reconstruct
Pending item membership, cash, quantity, PM, sizing, or valuation semantics.

Historical-only temporal shortcuts, date-specific bypasses, and fail-open
fallbacks are prohibited. Stage-specific temporal validation remains valid when
it validates a distinct responsibility, such as market evidence date, execution
terminal evidence, or current valuation quote date.

### Runtime Guard Taxonomy

`runtime_v2.guard_taxonomy` owns typed classification of Runtime review and
block evidence. Supported guard classes include:

```text
MARKET_PORTFOLIO_SAFETY
EXECUTION_SAFETY
DATA_INTEGRITY_SAFETY
INTERNAL_SYSTEM_CONSISTENCY
ITEM_SCOPED_REVIEW
BATCH_LEVEL_FAILURE
```

Diagnostic reason text may remain in artifacts for human investigation, but
business semantics must be carried by typed fields such as guard class, guard
code, scope, affected side, affected item ids, batch-blocking flag,
recoverability, system-defect flag, canonical owner, and consumer action.

`INTERNAL_SYSTEM_CONSISTENCY` is fail-closed and must not be represented as
normal market risk, opportunity scarcity, cash scarcity, or investment Safety.

### Legitimate Multi-Layer Validation Principle

Phase30 centralization does not mean every check moves to one component. The
rule is narrower: the same business decision must not have multiple owners.
Distinct validation responsibilities may remain multi-layered.

Valid multi-layer checks include:

- symbol-level order amount feasibility
- aggregate batch cash feasibility
- broker buying power
- Strategy deployable budget validation
- Safety hard-cap validation
- canonical quantity equality validation
- stage-specific temporal validation
- post-fill accounting reconciliation

Invalid duplication includes downstream consumers resizing Strategy quantity,
reclassifying item-scoped Pending review as batch failure, deriving BUY/SELL
side semantics from reason strings, or collapsing distinct cash meanings into
one generic authority.

### Runtime Orchestration Order

The real Runtime order must preserve producer-before-consumer authority:

```text
market_refresh
-> runtime_state_refresh
-> pending_lifecycle_pre_data_readiness_when_required
-> runtime_data_readiness_gate
-> historical_safety_authority
-> morning candidate / PM / Strategy / Pending generation
-> sell_planning
-> submit data readiness / submit guard / submit
-> execution
-> pending consume / terminalization
-> current state apply
-> current valuation
-> day completion
```

Lifecycle logic may be invoked by orchestration, but orchestration must not
reimplement lifecycle decisions. Pending lifecycle remains the authority for
whether stale residual reviewed BUY state expires, remains active, or fails
closed.

### Cash Semantics Separation

Runtime must keep these cash meanings distinct:

- Strategy deployable budget
- Portfolio Construction residual allocation budget
- Current cash and buying power
- Pending reserved notional
- Submit aggregate cash
- broker buying power
- post-fill cash

Planning and Submit may both validate cash or buying power, but they must
validate their own boundary using the selected upstream authority. They must
not collapse the above meanings into a single generic cash authority or reuse
same-day SELL proceeds before those proceeds are materialized into Current or
broker authority.

### Final Phase30 Architecture Gate

At Phase30 closure:

```text
FINAL_RUNTIME_AUTHORITY_ARCHITECTURE_STATUS = CONFORMANT
DUPLICATE_DECISION_INVALID_COUNT = 0
REVIEW_SCOPE_CONFORMANCE_GAP_COUNT = 0
NONCANONICAL_BATCH_ESCALATION_COUNT = 0
SYSTEM_GUARD_MISCLASSIFIED_AS_NORMAL_SAFETY_COUNT = 0
QUANTITY_REDECISION_LOCATION_COUNT = 0
CASH_AUTHORITY_CONFORMANCE_GAP_COUNT = 0
TEMPORAL_AUTHORITY_CONFORMANCE_GAP_COUNT = 0
INVALID_BUY_SELL_COUPLING_COUNT = 0
PRODUCER_BEFORE_CONSUMER_VIOLATION_COUNT = 0
TEST_FIDELITY_GAP_COUNT = 0
REMAINING_LATENT_CRITICAL_COUNT = 0
REMAINING_LATENT_HIGH_COUNT = 0
```

The accepted final validation run is
`runtime-test-historical-extended-smoke-20260817T222423827667Z`, which completed
25 requested business days from `2022-08-10` through `2022-09-14` with no
mid-run HALT and final pending state `EMPTY`. Its close-level
`REVIEW_REQUIRED` was a non-mutating Strategy shadow validation condition, not
a Runtime, authority, Safety, data, accounting, or trading-state defect.

## Phase31-G136 High-Resolution Capital Value Runtime Boundary

The permanent architecture SoT for future high-resolution marginal capital
value and portfolio-wide capital rotation is:

```text
docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md
```

Runtime remains a consumer. Future high-resolution Capital Value or Portfolio
Rotation evidence must not cause Runtime to recompute Candidate ranking, Cash
preference, target weights, discrete quantity, HOLD / ADD / REDUCE / EXIT
actions, or rotation decisions. Runtime may only consume the canonical
Strategy, Portfolio Construction, Position Sizing, Pending, Submit, Safety, and
Execution authorities at their defined boundaries.
