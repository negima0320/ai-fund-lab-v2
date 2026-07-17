# AI Fund Lab vNext 開発ロードマップ

---

# 1. このドキュメントの目的

本ドキュメントは、

```text
AI Fund Lab vNext
```

の開発順序を定義する。

---

目的は、

```text
何を作るべきか

今どこにいるのか

次に何を作るべきか
```

を明確にすることである。

---

# 2. 開発方針

vNextでは、

```text
投資哲学

↓

要件定義

↓

システム設計

↓

AI設計

↓

実装

↓

検証

↓

運用
```

の順番を守る。

---

禁止。

```text
とりあえずAI作る
```

---

# 3. 現在地

完了済み。

```text
README

docs/README

00_vision/investment_philosophy

00_vision/v1_to_v2_transition_requirements

01_requirements/system_requirements

01_requirements/success_metrics

01_requirements/phase_roadmap

02_architecture/system_architecture

02_architecture/broker_integration_design

02_architecture/safety_guard_design

03_ai_design/candidate_ai_design

03_ai_design/opportunity_ai_design

03_ai_design/position_management_ai_design

03_ai_design/capital_allocation_design
```

---

現在

```text
設計フェーズ
```

完了。

---

# 4. Phase1

## Data Foundation

目的

```text
市場データ基盤構築
```

---

実装対象

```text
J-Quants接続

Market Data Store

Feature Builder基盤
```

---

完了条件

```text
日次データ取得

保存

再取得

更新
```

可能。

---

Acceptance Criteria

データ管理

```text
取得日を保存する

対象日を保存する

銘柄コードを保存する
```

重複防止

```text
同日再取得で重複しない
```

障害対応

```text
取得失敗をログに残す

欠損をログに残す
```

データ分離

```text
Raw Data

Feature Data

Future Label Data
```

を分離する。

セキュリティ

```text
APIキーをGit管理しない
```

---

# 5. Phase2

## Broker Foundation

目的

```text
証券会社接続
```

---

実装対象

```text
立花証券接続

Broker Sync

Portfolio State
```

---

完了条件

```text
残高取得

保有株取得

注文一覧取得
```

可能。

---

# 6. Phase3

## Safety Foundation

目的

```text
事故防止
```

---

実装対象

```text
Safety Guard

ログ

監査基盤
```

---

完了条件

```text
異常検知

停止
```

可能。

---

# 7. Phase4

## Candidate AI vNext

目的

```text
上昇候補抽出
```

---

問い

```text
どの銘柄にモメンタムが発生しているか？
```

---

成功条件

```text
候補品質向上
```

---

# 8. Phase5

## Opportunity AI vNext

目的

```text
期待値順位付け
```

---

問い

```text
どの銘柄を買うべきか？
```

---

成功条件

```text
平均trade edge向上
```

---

# 9. Phase6

## Position Management AI vNext

目的

```text
保有判断
売却判断
追加判断
縮小判断
```

---

問い

```text
保有継続か？

売却か？

追加か？

縮小か？
```

---

成功条件

```text
profit_retention改善
```

---

# 10. Phase7

## Capital Allocation Engine

目的

```text
資金配分
```

---

実装

```text
均等配分
```

から開始。

---

AI化しない。

---

# 11. Phase8

## Order Manager

目的

```text
発注
```

---

実装

```text
新規注文

売却注文

取消

約定確認
```

---

# 12. Phase9

## 30営業日Paper Trading / Unified Daily Operation Validation

目的

```text
Daily Paper Trading Validation

修正版ロジックで30営業日の日次AI運用を継続し、
Unified Runner / Ledger / Report / Trackerの安定性を確認する
```

---

構成

```text
Paper Ledger運用

20:00 launchd自動実行

J-Quants market refresh

canonical normalized update

feature refresh

daily inference

pending order作成

virtual fill

ledger valuation

Blog Report v4

30BD tracker

non-business-day skip

pending dedup

trading calendar guard

score saturation fix

phase9 bugfixes
```

統合対象

```text
Candidate

Opportunity

Position

Capital Allocation

Order Manager

Paper Ledger

Human Review / Auto Approval for Paper Trading

Safety status / no-live-order guard
```

統合。

---

完了条件

```text
30営業日Paper Trading完走

Unified Runner安定

Blog Report安定

Ledger/Tracker整合

Broker注文なし

実売買なし

重大バグ解消

Phase10に進むためのreadiness report作成
```

注意

```text
Phase9の30営業日テストは継続する

Phase9の結果はPhase10/Phase11の設計にフィードバックする
```

---

# 13. Phase10

## Tachibana Securities API Connection

目的

```text
立花証券e支店APIと接続し、
実売買前のBroker Integrationを進める
```

---

注意

```text
立花証券口座開設完了後に開始する

初期は必ずread-only / dry-run / sandbox相当から開始する

Phase10中の本番発注は原則禁止

Safety Layerなしでは実売買しない
```

---

想定スコープ

```text
1. 立花証券API認証情報管理

2. secrets管理

3. login/logoutまたはセッション管理

4. read-only疎通確認

5. account snapshot取得

6. positions取得

7. orders/history取得

8. market price / realtime quote取得

9. API response schema保存

10. Broker Snapshot保存

11. Tachibana Broker Adapter実装

12. Paper Ledgerとのreconciliation

13. dry-run order plan → broker order plan変換

14. 実発注禁止ガード

15. no-live-order audit
```

---

許可

```text
read-only API接続

価格取得

口座情報取得

保有銘柄取得

注文履歴取得

dry-run order validation

broker adapterのmock / dry-run

APIレスポンス保存

audit / pytest
```

禁止

```text
実買い注文

実売り注文

信用取引

unlock_trade

発注API実行

自動売買

Safety Layer未実装状態での本番売買

secretsの平文コミット
```

完了条件

```text
Tachibana read-only接続PASS

account/positions/orders/history snapshot取得PASS

realtime quote取得PASS

secrets管理PASS

order APIが明示的に禁止されていること

no-live-order audit PASS

Paper LedgerとBroker Snapshotのreconciliation設計完了

Phase11 Safety Layerに進める状態
```

---

# 14. Phase11

## Safety Layer / Emergency Brake

目的

```text
実運用前に、AI判断とは独立したSafety Layerを追加する

AIがどの銘柄を買いたいと言っても、
Safety Layerが危険と判断したら、
新規買い停止・保有縮小・売却候補化・全停止を行えるようにする
```

---

重要方針

```text
Safety LayerはAI判断とは独立したルールベース安全装置

人間は解除判断に使わず、解除条件もできるだけ自動化する

ただし実売買を伴う解除・売却はPhase12以降で慎重に扱う
```

---

想定スコープ

### 14.1 個別銘柄ブレーキ

```text
購入価格から -7% で警告

購入価格から -10% で売却候補

購入価格から -15% で強制売却候補

立花証券APIのリアルタイム価格で監視する設計

gap down時も検知できるようにする

約定保証はしないが、検知時に最短で売却判断へ回す
```

### 14.2 新規買い停止ブレーキ

発動条件例

```text
portfolio equityがpeak比 -5%

TOPIX / 日経平均が20日線割れ

保有銘柄の過半数が含み損

直近N営業日の損益が連続マイナス

market breadth悪化

data quality異常

stale price

API異常

Ledger/Broker不整合
```

発動時

```text
新規買い停止

pending buy cancel / block

保有銘柄は個別ルールで評価継続
```

### 14.3 緊急停止ブレーキ

発動条件例

```text
portfolio equityがpeak比 -10%

初期資金比 -10%

保有銘柄の半数以上が -7%超

Broker/Ledger不整合

price feed異常

order reconciliation異常

APIレスポンス異常

実売買安全境界違反
```

発動時

```text
新規買い停止

pending order停止

実発注停止

人間通知

必要に応じて売却候補生成

ただし即全売却は慎重に扱う
```

### 14.4 自動解除条件

```text
peak比DD -10%で緊急停止

peak比DD -5%以内まで回復

かつ 5営業日継続

TOPIX/日経平均が20日線上に回復

data quality正常

API正常

Ledger/Broker一致

pending/order不整合なし
```

解除時

```text
新規買い再開

pending order許可

ただし解除直後はposition size縮小から再開してもよい
```

### 14.5 Safety State Machine

状態例

```text
NORMAL

BUY_SUSPENDED

REDUCE_ONLY

EMERGENCY_STOP

RECOVERY_WATCH
```

遷移例

```text
NORMAL → BUY_SUSPENDED

BUY_SUSPENDED → RECOVERY_WATCH

RECOVERY_WATCH → NORMAL

BUY_SUSPENDED → EMERGENCY_STOP

EMERGENCY_STOP → RECOVERY_WATCH
```

### 14.6 Safety Report

毎日以下を出す。

```text
safety_state

triggered_rules

解除条件進捗

individual stop candidates

portfolio drawdown

market regime

data quality

broker reconciliation

allowed actions

blocked actions
```

---

許可

```text
Safety Layer設計

Safety State Machine実装

Paper Trading上でのSafety simulation

read-only broker data利用

realtime quote read-only監視

sell candidate generation

buy suspension

pending order block

audit / pytest
```

禁止

```text
Safety Layer未完成状態での本番自動発注

unlock_trade

無条件の全売却

人間承認なしの実売却

実売買

secrets平文保存
```

完了条件

```text
Safety State Machine PASS

-10% individual stop検知PASS

buy suspension PASS

emergency stop PASS

auto recovery PASS

Safety Report PASS

Paper TradingでSafety動作確認

Broker read-only / realtime quote連携確認

no-live-order audit PASS

Phase12以降の実運用準備に進める状態
```

---

# 15. Phase12

## Demo Full Operation Validation / Live Trading Readiness

目的

```text
Phase10のBroker接続とPhase11のSafety Layerを前提に、
Production Runtimeと同じ運用フローをDemo環境で検証し、
30営業日安定運用できることを確認する
```

---

条件

```text
Phase9 30営業日Paper Trading結果確認

Phase10 Tachibana read-only接続PASS

Phase11 Safety Layer PASS

no-live-order audit PASS

人間承認フロー確認

安全性確認
```

Phase12-H時点の重要な評価結果。

```text
SELL統合後 1年:
annualized_return 17.6736%
max_drawdown -24.7342%

SELL統合後 5年:
annualized_return 51.2017%
max_drawdown -21.5802%

1年:
72.588% -> 17.6736%
大幅悪化

5年:
31.2197% -> 51.2017%
改善

SELL後20営業日で+5%超:
60件

SELL後20営業日で-5%超下落:
143件

推定回避損失:
約1,146,749円

判定:
SELL_INTEGRATION_NEEDS_CALIBRATION_BEFORE_PRODUCTION_REVENUE_CLAIM
```

Phase12は継続する。

```text
Demo Read-only

Demo Order Wire設計/承認

30営業日Demo運用

Production注文禁止
```

は止めない。

---

# 16. Phase13

## Runtime Architecture v2 Rebuild

Status:

```text
COMPLETE_WITH_HANDOFF
```

目的

```text
Phase12.5で発覚したRuntime状態管理の混線を解消する。

AIの銘柄選定、購入判断、Safety投資判断は原則変更しない。

Current State / History / Derived を分離し、
Persistent Ledgerを本線Current Stateとして接続し、
Pending PlanをSubmit唯一のSource of Truthとして完成させる。
```

Phase12.5最終判定。

```text
REVIEW_REQUIRED / CLOSED_FOR_REDESIGN
```

Phase13で扱う主問題。

```text
AI層ではなくRuntime層の問題。

order_plan/YYYY-MM-DD が履歴とSubmit対象を兼ねていた。

approval_artifact/YYYY-MM-DD が証跡とCurrent判定を兼ねていた。

約定、現在保有、現金、買付余力が永続Current Stateとして確立されていない。

demo_ledger と persistent_ledger の責務が重複している。

Report / Notification が本日Submit実績と次回Planを混同した。

launchd通し運用テストを再開するには、RuntimeのSoT固定が必要。
```

Phase13の必須項目。

```text
Current State / History / Derived の定義固定

Runtimeでは日付を実行対象の主キーにしない

日付はHistory / Evidenceの属性として扱う

Submit対象は pending_order_plan/pending_order_plan.json のみ

order_plan/YYYY-MM-DD は History / Evidence 扱い

approval_artifact/YYYY-MM-DD は History / Evidence 扱い

Pending Plan Phase D
  SUBMITTED
  CONSUMED
  EXPIRED
  stale SUBMITTING
  consume/archive
  再Submit禁止

Persistent Ledger本線接続

orders / executions / positions / cash / events の永続化

Daily Planの保有、SELL候補、max_positions判定を
persistent_ledger/state.json へ寄せる

Approvalのcurrent exposure、cash、buying power判定を
persistent_ledger/current state へ寄せる

Report / Notification の現在資産、保有、現金表示を
persistent_ledger へ寄せる

Reconcile / Audit のCurrent State参照を明示する

demo_ledger を legacy 化する

Broker Orders fallback はDemo限定、review_required付きにする

ProductionではBroker Orders fallbackによる保有確定を禁止する

Broker Positions / Broker Executions が正規SoTである方針を維持する

launchd再開前にAcceptance Testを必須にする

通し運用テストはPhase13完了後に行う

Production注文は禁止を継続する
```

Current State固定path。

```text
pending_order_plan/current

persistent_ledger/state

runtime_state/current
```

History保存方針。

```text
Historyは日付、run_id、plan_idで保存する

通常RuntimeはHistoryから実行対象を自動選択しない

Historyは証跡、監査、再生成、hash検証のために読む

HistoryからCurrent Stateへの昇格は明示条件を満たす場合だけ行う
```

再実行方針。

```text
Submit / Broker order は二重実行防止を最優先する

Submit済み、送信中、結果不明の pending_plan_id は再Submit禁止

POST_SEND_UNKNOWN は再送しない

POST_SEND_UNKNOWN は Broker ReadOnly 確認へ進める

Market Refresh は冪等再実行可能にする

Feature Refresh は冪等再実行可能にする

Report は冪等再実行可能にする

Audit は冪等再実行可能にする

Daily Plan は再実行可能にする

ただし Daily Plan の pending昇格は明示条件を満たす場合のみ

Approval は同一 plan hash に対してのみ再実行可能にする

Notification は delivery ledger で二重送信を防ぐ
```

再実行設計の目的。

```text
運用中にエラーが起きても、
Submit / Broker order 以外は安全にリカバリできるRuntimeにする。

Submit / Broker order はリカバリより二重発注防止を優先する。
```

Phase13でやらないこと。

```text
AI銘柄選定モデルの変更

Candidate AIの再設計

Opportunity AIの再設計

Safety投資判断ロジックの変更

AI再学習

フルバックテスト

Production注文

launchd自動運用再開
```

ただし、Runtime接続確認に必要な軽量テストは許可する。

Acceptance Criteria。

```text
Current State / History / Derived の分類表が確定している

Submitがpending_order_plan以外をSubmit対象にしない

Pending Planのconsume lifecycleが実装されている

persistent_ledger/state.json が現在保有、現金、買付余力の参照元になっている

Daily Plan / Approval / Report / Notification / Reconcile / Audit が
Current State参照元を明示している

demo_ledger が本線SoTではなくlegacy artifact扱いになっている

Broker Positions / Executions pipelineの診断が完了している

Demo fallback projectionを使う場合は必ずreview_requiredを残す

Productionではfallback projectionをCurrent State確定に使わない

Report / Notification が本日Submit実績、約定確認、現在保有、次回Planを混同しない

launchd再開前Acceptance TestがPASSする
```

Phase13へ持ち越す既知課題。

```text
Replacement Policy / Portfolio Rotation AI は未実装。

ただし、これはRuntime Architecture v2のCurrent Stateが確定してから扱う。

保有銘柄と新規候補のスコア比較、
Replacement edge margin、
minimum holding days、
turnover上限、
max_positions厳格制御、
SELL_FIRST_BUY_AFTER_FILL方針は、
Runtime SoT確定後の設計課題とする。
```

---

# 16.1 Phase14

## Runtime v2 Operation Integration / Broker ReadOnly Rehearsal

Status:

```text
REVIEW_REQUIRED / CLOSED_FOR_PHASE15_RUNTIME_REVIEW
```

Phase14はComplete扱いにしない。

目的

```text
Phase13で完成したRuntime Architecture v2とRuntime v2 skeletonを、
実運用統合へ進める。

最初はBroker ReadOnly adapter contractと実ReadOnlyデータでのManual Rehearsalを行う。
```

推奨開始点。

```text
Phase14-A: Runtime v2 Production/Demo Integration Plan

または

Phase14-A: Runtime v2 Broker ReadOnly Manual Rehearsal
```

推奨順序。

```text
Phase14-A:
Broker ReadOnly adapter contract / real readonly rehearsal

Phase14-B:
Runtime v2 manual operation rehearsal with real readonly data

Phase14-C:
Submit Runtime design / approval gate

Phase14-D:
Notification Send design / delivery ledger integration

Phase14-E:
launchd Runtime v2 re-enable plan

Phase14-F:
Production readiness audit
```

Phase14開始時点で継続禁止。

```text
Production注文

自動Submit

Broker API Write

Notification send

launchd自動運用

Backtest実行

Simulation実行
```

Phase14でProduction注文を許可済みとして扱わない。Production注文、Broker API Write、Notification send、launchd再開、plist新規作成は、それぞれ明示フェーズとAcceptanceを経てから扱う。

Phase13-Z2 handoff note。

```text
Phase13 Runtime Architecture v2 Rebuild は COMPLETE_WITH_HANDOFF。

Runtime v2 skeleton と Acceptance Dry Run は完了済み。

Phase14 は既存定義どおり Runtime v2 Operation Integration / Broker ReadOnly Rehearsal として開始する。

新しいPhase14は作成しない。

Phase14最初の作業は Broker ReadOnly実統合、Runtime v2実データManual Rehearsal、Production Readiness、Submit Runtime接続判断、Notification Send判断、launchd再開条件整理とする。
```

Phase14終了時点の扱い。

```text
Runtime v2 Demo Operation Rehearsal はBUY経路を大きく前進させた。

Market Refresh、Morning、Pending、Submit、Broker Accepted、Execution、
Current Projection、Report、Notification Payload、SELL Planning CLI connection
までは到達した。

ただし、Submit Guard / max_order_amount=100000 の設計契約違反疑い、
Capital Allocation契約との不整合、BUY/SELL notional guard契約未確定、
SELL liquidation未完、Blog未確認、Notification実送信未確認、
Regression設計不備が残った。

したがってPhase14は完了ではなく、
REVIEW_REQUIRED / CLOSED_FOR_PHASE15_RUNTIME_REVIEW
として閉じる。
```

---

# 16.2 Phase15

## Runtime Contract Full Re-Review

Status:

```text
CLOSED_WITH_OPERATIONAL_BOUNDARIES
```

最重要目的。

```text
Phase15はRuntime実装継続フェーズではない。

Runtime Contract Full Re-Reviewとして、
RuntimeとRuntime Review品質を全面再レビューする。

Runtimeを安心して任せられる状態にする。

ChatGPTレビュー品質を改善し、
設計契約・実装・Runtime証拠を一致させる。
```

目的。

```text
Runtime設計契約の全面レビュー

実装契約との照合

CLI通常経路レビュー

Current / Broker / Report / Notification整合確認

Regression Review

Capital Deployment Contract Review

Submit Guard Contract Review

SELL Contract Review

Runtime Acceptance再定義
```

開始条件。

```text
Phase14 Postmortem完了

Runtime Architecture v2 更新済み

Regression観点更新済み

既存PASS判定リセット済み
```

PASS判定基準。

```text
以下が一致して初めてPASSとする。

設計契約

実装

CLI通常経路

Runtime Manifest

Current SoT

Broker ReadOnly

Report

Notification

Regression
```

Phase15レビュー規則。

```text
Runtime Evidence First Rule:
推測でPASS / FAIL / 原因を断定しない。
確認可能なRuntime artifact、Broker状態、Current SoT、manifest、ledger、reportを優先する。

Evidence Request Rule:
証拠不足の場合は、Operatorへ必要最小限の確認コマンドを1〜2個ずつ提示する。
大量のコマンドを一度に要求しない。

No Guess Rule:
Runtime状態を推測しない。
取得した証拠だけでレビューする。
```

完了条件。

```text
BUY Runtime Complete

SELL Runtime Complete

Blog Runtime Complete

Notification Runtime Complete

Capital Deployment Contract Complete

Runtime Full Acceptance PASS
```

Phase15でProduction注文を許可済みとして扱わない。Production注文、Broker API Write、Notification real send、launchd自動運用は、それぞれ明示フェーズとAcceptanceを経てから扱う。

Phase15-CA closure。

```text
Runtime v2 Completion:
COMPLETE

Phase15:
COMPLETE_WITH_OPERATIONAL_BOUNDARIES

Production Ready:
NOT_READY

Broker-connected Operational Readiness:
NOT_READY_FOR_CONTINUOUS_OPERATION

Phase16 Readiness:
PHASE16_READY_WITH_CONDITIONS

Final Judgment:
RUNTIME_V2_COMPLETE_PHASE15_CLOSED_WITH_OPERATIONAL_BOUNDARIES
```

Phase15でAcceptance済み。

```text
Runtime Architecture v2
Temporal / Freshness Contract
Safety authority
Pending lifecycle
Normal Submit Pipeline
Normal Execution Processor
Ledger Writer
Current Projector
Current Apply
Runtime State
Report / Public Report / Blog Markdown / Notification Payload
BUY-origin transition
BUY→SELL Round Trip in simulation
Tachibana Demo SELL broker write evidence
```

Phase15完了後もProduction Readyではない。

```text
実Broker BUY→SELL
Broker-connected multi-day
Notification Delivery
Production credentials
Production order enablement
Production account reconciliation
Monitoring / Recovery / Runbook
```

はPhase15完了条件ではなく、Operational Boundary / Production Enablementとして残す。

次フェーズは新Runtime作成ではなく、受け入れ済みRuntime v2を固定Engineとして使う。ただしPhase16-AからPhase16-Gまでの監査により、本番運用へ進むためにはHistorical Runtime Test専用ではない恒久的な運用データ基盤を完成させる必要が確認された。

```text
Phase16:
Operational Data Foundation

Japanese:
運用データ基盤整備

Subtitle:
Canonical Data, Feature, AI Artifact, and Runtime Input Foundation

Phase17:
Historical Runtime v2 Performance Test
```

Phase16開始位置。

```text
Current Prefix:
Phase16-I Operational Data Foundation Purpose and Goal Definition

Phase16 Purpose:
Production、Demo、Paper、Historicalが同一のCanonical Data Contract、Feature Producer、Feature Schema、AI Artifact、AI Decision Contract、Runtime v2 Mainlineを利用できる恒久的な運用データ基盤を完成させる。

Japanese Purpose:
運用データ基盤整備

Top-Level System Purpose:
AI Fund Lab v2の最上位目的は、安心・安全に継続運用できる日本株自動売買システムを作り、最終的にProduction運用すること。

Return Target:
年率50%

Priority:
安全性
↓
正確性
↓
継続運用性
↓
監査可能性
↓
説明可能性
↓
収益性

Prohibited for Return Improvement:
収益向上のために安全性を下げる
収益向上のためにRuntime Authorityを曖昧にする
収益向上のためにCanonical Data Contractを破る
バックテスト結果へ過剰適合する

Runtime Policy:
Runtime v2を固定Engineとして使用する。

Runtime Root:
通常Runtime root `.runtime` を使用する。

Runtime Paths:
通常固定Pathを使用する。

Phase16-specific Runtime Root:
PROHIBITED

Phase16-specific Current / Ledger / Pending / Mainline:
PROHIBITED

Historical Performance Test:
PROHIBITED in Phase16

Historical Runtime Test Position:
Historical Runtime Testは目的ではなく、本番運用へ進むための品質確認手段の一つである。

Operational Data Foundation Scope:
Phase16で整備するデータ基盤は、
Historical Runtime Test専用ではない。

Production、Demo、Paper、Historicalが
共通利用するOperational Data Foundationである。

Historical Runtime Testは、
本番運用へ進むための品質確認手段の一つである。

Performance Improvement / Revenue Optimization:
PROHIBITED in Phase16

Canonical Data Policy:
Production / Demo / Paper / Historicalが同一のCanonical Data Contract、同一Feature Producer、同一Feature Schema、同一AI Artifact、同一AI Decision Contract、同一Runtime v2 Mainlineを使用できる状態を完成させる。

Historical-only / Backtest-only / Phase16-only Source of Truth:
PROHIBITED

Canonical Logical Layers:
J-Quants Raw
↓
Canonical Market Data
↓
Canonical Feature Producer
↓
Feature Artifact
↓
Candidate AI / Opportunity AI / Position Management
↓
AI Decision Artifact
↓
Policy / Safety / Planning / Pending / Submit / Execution / Ledger / Current / Report

Phase Artifact Promotion:
PROHIBITED without explicit migration design and acceptance.

Phase-numbered artifacts:
phase4*
phase5*
phase6*
phase9*

must be classified as Training Artifact, Historical Evidence, Accepted Model Artifact, Legacy Artifact, or Canonical Candidate before use.

.runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet:
Content is confirmed as Canonical normalized OHLCV.
Permanent path remains migration-design required because the path is phase-numbered.

AI Retraining:
PROHIBITED

Prohibited AI Actions:
Candidate retraining
Opportunity retraining
PM change
Threshold optimization
Feature change
Backtest-result tuning
Model switch

Allowed AI Freeze Actions:
Model Freeze Manifest
Runtime loaded path freeze
Model hash recording
Feature schema hash recording
Opportunity metrics path freeze
PM code-policy hash freeze

Backtest Result Feedback:
PROHIBITED

Tachibana API / Demo Trading / Production Trading:
OUT_OF_SCOPE

Public Blog / LINE / Discord:
OUT_OF_SCOPE

Runtime Internal Report:
REQUIRED

Historical Simulated Broker:
REQUIRED

Deferred Phase17 Improvement Targets:
Candidate AI
Opportunity AI
Position Management AI
Feature
Policy
Safety
Capital Allocation

Runtime Core Bug Policy:
Phase16 readinessでRuntime Core bugがEvidence付きで見つかった場合のみ、
Performance改善とは分離してRuntime修正として扱う。

Initial Runtime Reset:
Reset / Backup / Restore mechanism is REQUIRED by a reviewed post Phase16-O implementation phase.
Execution reset is performed before Phase17-A, not during Phase16-H.

Final Production Preparation Reset:
REQUIRED after Phase17 historical test evidence preservation.

Runtime Bug Fix:
ALLOWED_ONLY_WITH_EVIDENCE

Runtime Bug Fix Required Evidence:
Contract unchanged
Authority unchanged
State transition unchanged
Normal mainline unchanged
Default behavior unchanged
Performance logic unchanged
If any item is NO, stop as design change.
```

Phase16新工程。

```text
Phase16-H Scope Revision and Canonical Data Foundation
Phase16-I Operational Data Foundation Purpose and Goal Definition
Phase16-J Operational Data Architecture Contract
Phase16-K AI Artifact Registry and Capital Allocation Contract Design
Phase16-L Artifact Physical Path, Registry Integration, and Migration Sequence Design
Phase16-M Operational Data Foundation Executive Architecture Review
Phase16-N Executive Architecture Review Minor Amendment Closure
Phase16-O Operational Lifecycle, State Reset Boundary, and Environment Transition Contract
Post Phase16-O Reviewed Sequence TBD: Canonical Market Data Foundation
Post Phase16-O Reviewed Sequence TBD: Calendar / Listed / Corporate Action Foundation
Post Phase16-O Reviewed Sequence TBD: Feature Producer Connection from Canonical Data
Post Phase16-O Reviewed Sequence TBD: AI Model and Policy Freeze
Post Phase16-O Reviewed Sequence TBD: Operational Backup / Reset / Restore
Post Phase16-O Reviewed Sequence TBD: Historical Broker Boundary
Post Phase16-O Reviewed Sequence TBD: Point-in-time Guard
Post Phase16-O Reviewed Sequence TBD: Operational Data Foundation Readiness Acceptance
Phase16 Final Review and Phase17 Handoff
```

Phase16完了条件。

```text
Operational Data Architecture Contract accepted
Canonical Raw SoT確定
Canonical Normalized SoT確定
Trading Calendar Source accepted
Listed Issues Source accepted
Corporate Action方針確定
Canonical Feature Producer接続
Feature Schema unchanged and accepted
AI / Policy Freeze Manifest accepted
AI Artifact Registry Contract accepted
Registry Event Schema accepted
Acceptance Report Schema accepted
Regression Evidence Schema accepted
Validation Result Schema accepted
Review Approval Schema accepted
Lifecycle transition validation accepted
Model / Metrics Artifact Set accepted
PM Code Policy freeze contract accepted
Capital Allocation Contract accepted
Decision Artifact hash contract accepted
Silent fallback prohibited
Permanent Artifact Path Contract accepted
Registry Integration Contract accepted
Artifact Migration Sequence accepted
Backward Compatibility accepted
Rollback accepted
Regression Gate accepted
Legacy Artifact Policy accepted
Runtime input boundary accepted
Backup / Reset / Restore完成
Historical Broker境界完成
Point-in-time Guard完成
Phase artifact dependency removed from Runtime inputs
No Phase16-specific active Runtime root
No Historical-specific Canonical Source
No AI retraining
No Runtime design change
Historical Runtime Readiness Acceptance PASS
Phase17 Handoff complete
```

Phase16-A〜Gの扱い。

```text
Phase16-A Initial Historical Runtime Test Design
Phase16-B Prerequisite Audit
Phase16-C Temporal Bug Audit
Phase16-D Temporal Bug Fix
Phase16-E Prerequisite Re-Audit
Phase16-F AI State and Data Lineage Audit
Phase16-G Canonical Historical Data Audit
```

これらはPhase16方針変更のEvidenceとして保持する。

Phase17。

```text
Phase17 Purpose:
Historical Runtime Acceptance
+
Runtime v2 BUY/SELL/Execution/Ledger/Valuation検証
+
Opportunity AI BUY eligibility defect investigation
+
AI Lifecycle未完成問題の発見
+
AI Lifecycle v2共通Architecture設計

Status:
PARTIAL_ACCEPTANCE / HANDOFF_COMPLETE

Final Judgment:
PHASE17_HISTORICAL_RUNTIME_ACCEPTANCE_PARTIAL
PHASE17_AI_LIFECYCLE_DESIGN_COMPLETE
PHASE18_IMPLEMENTATION_REQUIRED
REVIEW_REQUIRED

Primary Run:
runtime-test-historical-extended-smoke-20260716T230100525117Z

Period:
2026-06-29 through 2026-07-10

Business Days:
10

Job Records:
80

Pass-like:
80

Non-pass:
0

Important Boundary:
80/80 job completion proves Historical scheduler/no-action Runtime continuity.
It does not complete BUY / Fill / Hold / SELL full-path acceptance because BUY count was 0.

Phase17 Metrics:
Runtime Integrity
Historical state transition integrity
Artifact resolution / fail-closed behavior
BUY eligibility contract validity
Opportunity model output distribution
AI Lifecycle completeness
Runtime no-action correctness
```

Phase17到達点。

```text
Historical Runtime Scheduler / No-action Path:
PASS

Runtime v2 artifact resolution / fail-closed:
PASS

Candidate AI Runtime execution:
PASS

Opportunity AI Runtime execution:
PASS

BV14 Market Status BUY Guard:
PASS

BV15 Opportunity BUY Eligibility:
PASS

BUY lifecycle:
NOT_ACCEPTED / NOT_EXERCISED

Position Management with actual positions:
NOT_ACCEPTED / NOT_EXERCISED

SELL lifecycle:
NOT_ACCEPTED / NOT_EXERCISED

AI Lifecycle v2 architecture:
DESIGN_COMPLETE / IMPLEMENTATION_READY

AI Lifecycle v2 implementation:
NOT_IMPLEMENTED

Formal Opportunity model:
STALE / NOT_PROMOTION_READY

BUY:
REMAINS_BLOCKED
```

Phase17で判明したAI Lifecycle gap。

```text
TRAINING_PIPELINE_PARTIAL
AUTO_RETRAIN_NOT_READY
REGISTRY_PARTIAL
MODEL_LIFECYCLE_INCOMPLETE
DATASET_PIPELINE_BLOCKED
```

Phase17未完了事項はPhase18へ移管する。

```text
最新PIT Dataset Rebuild Pipeline
Candidate / Opportunity共通Dataset Lifecycle
train / retrain pipeline
Champion / Challenger formal evaluation
Promotion Readiness
Atomic BUY AI Bundle packaging
Authority-approved Registry promotion
Runtime freshness gate
Runtime drift gate
weekly lifecycle scheduler
lifecycle observability
rollback / revoke acceptance
End-to-End AI Lifecycle Acceptance
新accepted BUY AI BundleでのHistorical Runtime Test
BUY / Fill / Hold / SELL full-path acceptance
```

Opportunity AI設計の扱い。

```text
Current Decision:
Opportunity AI design is provisionally retained.

Redesign Condition:
Only if current specification fails after fresh PIT dataset reconstruction and formal retraining/revalidation.

Prohibited:
Do not relax BV15 thresholds.
Do not ignore no_buy_reason.
Do not force Top-N BUY.
Do not redesign Opportunity target before Phase18-B/C evidence.
```

AI Lifecycle v2 SoT。

```text
docs/02_architecture/ai_lifecycle_v2.md
```

Phase18。

```text
Phase18 — AI Lifecycle v2 Implementation and End-to-End Acceptance

Japanese:
AI Lifecycle v2 実装・統合受入

Status:
PLANNED / READY_TO_START

Scope:
Candidate AI
Opportunity AI
Position Management AI / Policy Adapter
Safety Policy Engine
future AI onboarding contract

Purpose:
AI Fund Lab v2の全AIコンポーネントについて、
データまたはPolicy Evidence更新、
Dataset rebuild、
retrainまたはPolicy validation、
Champion/Challenger評価、
Promotion readiness、
Authority acceptance、
Registry切替、
Runtime freshness/drift gate、
scheduler、
monitoring、
rollbackまでを、
docs/02_architecture/ai_lifecycle_v2.md に従って
安全・再現可能・監査可能に実装する。

Important:
PM and Safety are currently Policy / Rule-based lifecycle components.
Do not apply Candidate / Opportunity trainable retrain semantics to PM or Safety unless their trainable design is formally added to the AI Lifecycle v2 SoT.
```

Phase18実装ロードマップ。

```text
Phase18-A — Common PIT Dataset Rebuild Pipeline
Candidate PIT Dataset
Opportunity PIT Dataset
label-safe cutoff
source authority
schema
lineage
data quality
leakage audit
idempotency
versioned dataset artifact

Phase18-B — Training / Validation / Challenger Pipeline
Candidate Challenger
Opportunity Challenger
time-series split
validation
test
recent holdout
Champion comparison
calibration
regime evaluation
reproducibility

Phase18-C — Promotion Readiness and Atomic BUY AI Bundle
Safety / Integrity
Predictive Validity
Operational Utility
Candidate / Opportunity compatibility
Atomic BUY AI Bundle
promotion request
rollback metadata

Phase18-D — Registry Promotion Operator
Authority review
ARTIFACT_ACCEPTED
atomic Registry update
materialized index
previous Champion retention
revoke / rollback
idempotency

Phase18-E — Runtime Freshness and Drift Gates
source freshness
dataset lag
model training lag
model acceptance age
feature drift
Candidate population drift
prediction drift
MODEL_UNHEALTHY
MARKET_NO_OPPORTUNITY
BUY BLOCK / REVIEW_REQUIRED
SELL continuity

Phase18-F — Weekly Lifecycle Scheduler and Observability
weekly eligibility check
label-safe readiness
locks
retry
timeout
no overlap
status artifacts
operator reports
alerts
no automatic self-promotion

Phase18-G — Full AI Component Lifecycle Coverage
Candidate AI lifecycle
Opportunity AI lifecycle
PM policy lifecycle
Safety policy lifecycle
future AI onboarding
failure blast radius
policy freshness
semantic regression

Phase18-H — End-to-End AI Lifecycle Acceptance
dataset rebuild
train / validation
promotion readiness
authority rehearsal
Registry acceptance rehearsal
Runtime next-job discovery
freshness / drift gates
rollback rehearsal
failure cases

Phase18-I — Historical Runtime Re-Acceptance
new accepted Atomic BUY AI Bundle
fresh Historical Runtime Test
BUY
Submit
Fill
Ledger
Current
Valuation
PM
SELL
Report
Notification
```

Phase18開始条件。

```text
docs/02_architecture/ai_lifecycle_v2.md accepted as SoT
BV20-R1 objective alignment complete
Phase17 final handoff accepted
BUY remains blocked
no Runtime model switch pending
no unreviewed Registry promotion pending
existing formal artifact set remains unchanged
```

Phase18完了条件。

```text
latest label-safe dataからCandidate/Opportunity datasetを再構築可能
dataset reproducibility / idempotency PASS
no leakage PASS
formal retraining / validationを再現可能
Champion / Challenger comparison PASS
Operational Utility評価可能
Atomic BUY AI Bundle生成可能
authority-approved Registry promotion可能
Runtimeがnext-job boundaryでbundleを発見
freshness / drift gateがscope別に動作
stale modelでBUY BLOCK
MARKET_NO_OPPORTUNITYとMODEL_UNHEALTHYを区別
SELL continuity PASS
weekly scheduler / monitoring PASS
rollback / revoke rehearsal PASS
Candidate / Opportunity / PM / Safety lifecycle coverage PASS
Historical RuntimeでBUYからSELLまでのfull pathを再Acceptance

Final Judgment Candidates:
AI_LIFECYCLE_V2_IMPLEMENTATION_COMPLETE
ALL_AI_LIFECYCLE_COVERAGE_PASS
ATOMIC_BUY_AI_BUNDLE_ACCEPTED
RUNTIME_FRESHNESS_DRIFT_GATES_PASS
WEEKLY_LIFECYCLE_OPERATIONAL
ROLLBACK_ACCEPTANCE_PASS
HISTORICAL_RUNTIME_FULL_PATH_PASS
PHASE18_COMPLETE
```

Phase18禁止事項。

```text
Runtime/training jobによるself-promotion禁止
Registry accepted eventの無承認書き込み禁止
CandidateとOpportunityの独立切替禁止
manual model path edit禁止
BV15 threshold relaxation禁止
no_buy_reason無視禁止
Top-N強制BUY禁止
Paper Ledger / Broker Snapshot / PnL / bought情報の学習利用禁止
future information leakage禁止
backtest結果の学習利用禁止
本番broker write禁止
本番注文禁止
```

Phase19。

```text
Broker-connected Continuous Operation Test / Production Enablement

Scope:
立花証券Demo
毎日運用
Broker-connected multi-day
Notification Delivery
Recovery
Monitoring
Production credentials
Production account reconciliation
Production Broker Write
Emergency operation
Production runbook
Production unlock
```

---

# 17. フェーズ進行ルール

次へ進める条件。

---

必須

```text
成功条件達成
```

---

禁止

```text
未完成のまま次へ進む
```

---

# 17. AI追加ルール

新AI追加条件。

---

必須

```text
役割

入力

出力

成功条件

失敗条件
```

定義。

---

追加理由

```text
Annual Return改善との関係
```

説明必須。

---

# 18. 凍結ルール

vNext初期版では作らない。

---

```text
Position Management AIとは別の追加PM系AI

Exit AI

Downside AI

複雑なAllocation AI

ニュースAI

SNS分析AI

LLM判断AI

レバレッジ

信用取引
```

---

理由

```text
まずはコア戦略を成立させる
```

---

# 19. 完成条件

vNext完成とは、

```text
AIが動く
```

ことではない。

---

以下を満たすこと。

```text
理由を説明できる

監査できる

停止できる

運用できる

信頼できる
```

---

# 20. 最終原則

迷ったら確認する。

```text
今やろうとしていることは

ロードマップ上で必要か？
```

---

必要でないなら、

実装しない。

---

vNextは、

```text
実装主導
```

ではなく、

```text
設計主導
```

で進める。
