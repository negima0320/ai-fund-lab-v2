# Phase12 Final Summary and Phase13 Handoff

## Status

`PHASE12_FINAL_SUMMARY_AND_PHASE13_HANDOFF_COMPLETE`

Phase12は完了とする。

今回の作業は総括とhandoff資料作成のみ。実装、Demo注文、Production注文、Notification送信、AI再学習、Backtest、launchctl操作、raw request / raw response / secret保存、Phase9変更は実施していない。

## 1. Phase12の目的

Phase12の目的は、Production Runtimeと同じ運用フローを立花証券Demo環境で実際に回せる状態へ持っていくことだった。

主目的:

- Tachibana Demo運用の完全自動化
- Production-equivalent Runtime
- launchdによる完全自動運用
- Daily Operations Runtime
- Demo Broker Integration
- Notification
- Daily Report

Phase12の最終方針は、DemoとProductionの違いを必要最小限に閉じることだった。

## 2. Phase12で実装したもの

時系列の主要成果は以下。

### Phase12-A / B / C

- Demo Full Operation設計
- Operations CLIのProduction向け命名整理
- Phase専用CLI名を廃止
- thin CLI + `src/ai_fund_lab_v2/operations/` 実装構成へ整理
- Demo / Production分岐をOperations層へ散らさず、Broker Adapter / Config境界へ閉じる設計を確認

### Phase12-D / E

- Operations Daily Runtimeの最小実装
- `.runtime/operations/` artifact rootを確立
- Phase9 Paper Tradingとの並行稼働を保護
- 1営業日リハーサル
- Daily manifest / report / audit / ledger系の最小運用基盤を整備

### Phase12-F / G / H

- SELL / Exit Integration Audit
- BUY / SELL / Exit LogicをOperations Runtimeへ接続
- SELL統合込みBacktest評価
- Exit Adapter / Position Managementの接続状態を確認

### Phase12-I / J / K / L / M

- Demo Broker Read-only Integration
- J-Quants / Demo Broker read-only mainline integration
- Feature freshness / Ledger reconciliation修正
- Daily Report stale artifact修正
- Longer lookback refreshでBUY signalを確認

### Phase12-N / O / P / Q

- Demo Wire Unlock Preflight Review
- Minimal Demo Order Wire Execution
- 第二暗証番号設定後のDemo wire retry
- BUY / SELL lifecycle wire execution確認

### Phase12-R / S / T / U / V / W / X / Y

- Broker request sequence調査
- Persistent Demo Ledger方針追加
- RequestSequenceManager追加
- 第二暗証番号request-side codec修正
- CLMKabuNewOrder request / response schema調査
- Tachibana codec completion
- Broker issue code normalizer実装
- `92560 -> 9256` のBroker Issue Code変換
- Demo BUY accepted確認

### Phase12-Z / AA / AB

- Demo BUY Fill Monitoring
- Matched Opposite Order Fill Test
- Demo 9000-series Special Fill Simulation
- Broker-confirmed fill不可のDemo特性をSimulationで扱う方針を確立

### Phase12-AC / AE / AF

- Full Automatic Demo Daily Operation launchd setup
- Weekday-only schedule hardening
- Report / Audit実行順序整理
- Market Calendar Awareness
- Market Closed Safe Skip

### Phase12-AH / AI / AJ / AK

- BUY candidate countをProduction-equivalentへ修正
- Notification delivery / Demo-Production parity audit
- Daily Report writer品質修正
- Phase9 v4 blog writer復元
- public_report / blog_draft / safety_reportを人間向けブログ品質へ戻す

### Phase12-AL / AM / AN / AO

- Market Calendar false closed bug修正
- 2026-07-01再生成と2026-07-02朝submit参照先確認
- Production-equivalence Final Gap Audit
- Source of Truth matrix固定
- Operation Flow Integrity Guard
- Daily Report prerequisite guard

### Phase12-AP / AQ / AR / AS

- Partial Submit BLOCKED_ITEM reason修正
- `remaining_approval_budget_insufficient` をartifactへ明示
- Reconcile REVIEW_REQUIRED root cause修正
- Approval Max Notional設計確認
- 固定 `600000` を廃止
- Dynamic Approval Max Notionalを85% Exposure Ruleへ整合
- Demoでは立花Demo口座2000万円ではなく、評価資金100万円を基準にする設計へ修正

## 3. Phase12で見つかった重大バグ

Phase12では、設計だけでは見えなかった実運用系の問題が多数見つかった。

- BUY件数が暫定 `max_items=1` のまま残っていた
- Market Calendarが2026-07-01営業日を `market_closed=true` と誤判定した
- Approval Max Notionalが固定 `600000` の暫定値だった
- 翌朝submitの日付解決が、前営業日Order Plan / Approval運用とずれていた
- ReportがOrder PlanとSubmitted Ordersを混同した
- Daily ReportがPhase9 v4品質からデグレし、内部ログ風になった
- launchd plist更新後の再読み込みが運用上の手動作業として残った
- Notificationがpayload生成止まり、または設定状態の可視化が不十分だった
- Partial Submitでitem単位BLOCK理由がartifactに残らなかった
- Partial Submit後にFill / Safety / Reconcileが理由不明BLOCKへ連鎖した
- ReconcileがDemo仕様として説明可能な状態を `REVIEW_REQUIRED` にしていた
- Daily Report prerequisite guardが不足し、不完全operation dayでも通常レポートに見え得た
- Broker issue codeでJ-Quants/internal codeをそのまま注文へ渡していた
- Tachibana Demoの日次リセットにより、Broker snapshotだけでは複数日Demo履歴を保持できないことが判明した

## 4. 修正済み一覧

### BUY件数

修正前:

- BUY候補が1件に制限される暫定挙動が残っていた

修正後:

- Production-equivalentに `max_buy_orders_per_day=5` を使用
- Demoだけ1件に減らす差分を廃止

### Market Calendar

修正前:

- 2026-07-01が休場扱いになり、Daily Plan / Approval / Submitが停止した

修正後:

- J-Quants trading calendar / fallback calendarの扱いを修正
- 2026-06-30、2026-07-01、2026-07-02は営業日としてPASS
- 土日はMarket Closed Safe Skip

### Date Resolution

修正前:

- 2026-07-02朝submitがどの日付のOrder Planを参照するか曖昧だった

修正後:

- 朝submitは `submit_run_date` と `order_plan_source_date` を分離
- 2026-07-02朝は2026-07-01 Order Plan / Approvalを参照することを確認

### Source of Truth

修正前:

- Order Plan、Submitted Orders、Broker Orders、Fill、Positions、Reportの境界が混ざり得た

修正後:

- Source of Truth matrixを固定
- Order Planは翌営業日候補
- Submitted OrdersはBrokerへ送信した注文
- Broker Ordersは受付状態
- Broker Executionsは約定
- Broker Positionsは現在保有
- Reportは各SoTから生成

### Daily Report

修正前:

- 技術ログ寄り、表中心、dict / repr直出し、BUY理由欠落があった

修正後:

- Phase9 v4 writerをベースに復元
- 文章 + 箇条書き中心
- Candidate Top50 / Top5 / AI総括 / 注意書きを復元
- Demo運用状況、Safety、Reconcile、Audit、Notificationを末尾に自然文で追加

### Broker Integration

修正前:

- CLMKabuNewOrder codec、second password mapping、request sequence、response normalization、issue code mappingに穴があった

修正後:

- RequestSequenceManager追加
- 第二暗証番号codec修正
- CLMKabuNewOrder request / response schema調査とnormalizer補強
- Broker Issue Code Normalizer追加
- `92560 -> 9256` の境界変換を実装
- Demo BUY accepted確認

### Persistent Demo Ledger

修正前:

- Demo Brokerの日次リセットにより、前日注文・約定・保有履歴が消えたように見え得た

修正後:

- Demo Broker Snapshotは当日観測値
- Persistent Demo Ledgerは複数日Demo運用履歴
- Broker snapshotで過去Demo ledgerを全量上書きしない方針を確立

### Partial Submit / Reconcile

修正前:

- 2393が `BLOCKED_ITEM` になった理由がartifactに残らなかった
- Reconcileが `SYSTEM_EMERGENCY_STOP` / `REVIEW_REQUIRED` に連鎖した

修正後:

- `block_reason=remaining_approval_budget_insufficient` を明示
- `blocked_items[]` を埋める
- Partial Submitは `PARTIAL_PASS_WITH_ITEM_BLOCKS`
- Reconcileは説明可能なDemo partial状態を `PASS_WITH_BLOCKED_ITEMS` と扱う

### Dynamic Approval Max

修正前:

- `approval.max_notional=600000` がDemo Auto Approvalの暫定固定値として残っていた

修正後:

- 固定600000を通常運用から廃止
- `approval_max_notional = min(equity_basis * 0.85 - current_exposure, available_cash, capital_allocation_budget)`
- Demoでは評価資金100万円を使い、立花Demo口座2000万円で上書きしない
- current exposure 0なら `approval_max_notional=850000`
- 2026-07-02相当の5候補合計810,700円はApproval予算上PASS

## 5. 現在のRuntime状態

直近確認ベース:

```text
Market Refresh
PASS

Daily Plan
PASS

Approval
PASS / APPROVED
approval_max_notional=850000
approval_max_notional_source=dynamic_max_exposure

Submit
PASS / PARTIAL_PASS_WITH_ITEM_BLOCKS
2026-07-02 actual history: accepted 4, blocked item 1

Broker
PASS
Demo Broker order accepted path confirmed

Fill Monitor
PASS
Demo 9000-series special fill handled by simulation when applicable

Safety Monitor
PASS

Reconcile
PASS_WITH_BLOCKED_ITEMS

Operation Audit
PASS

Daily Report
PASS

Notification
PASS in configured environment / current handoff did not send notifications
```

補足:

- 2026-07-02のsubmitted_ordersは履歴として4件accepted、1件blockedを維持している
- Phase12-ASでは追加注文禁止だったため、2393の追加発注はしていない

## 6. DemoとProduction差分

最終的に許可する差分は以下だけ。

```text
Demo Special Fill
Persistent Demo Ledger
TACHIBANA_API_ENV=demo
Production Order Disabled
```

これ以外はProductionと同一設計を目指す。

Demo固有:

- 9000-seriesなどBroker-confirmed fillがDemoで成立しないケースは、Demo Special Fill Simulationでライフサイクル確認する
- Tachibana Demoの日次リセットに対して、Persistent Demo Ledgerで複数日運用履歴を保持する
- Demoの評価資金は100万円。立花Demo口座の2000万円は評価資金に使わない

Production固有:

- Production注文は引き続きdisabled
- Production UnlockはPhase12では行っていない
- ProductionではBroker actual equity / buying powerをApproval Maxのequity / cash basisに使う

## 7. Phase12で得られた知見

- Source of Truthをartifact単位で固定しないと、Order Planを本日注文や約定と誤表示する
- Runtime Acceptance Testは設計段階ではなく、実運用artifactを使って継続的に必要
- launchdはplist作成だけでは不十分で、再コピー・再読み込み・環境変数確認まで運用手順に含める必要がある
- Market Calendarは運用停止に直結するため、営業日/休場日のテストが必須
- Demo BrokerはProductionと違い、日次リセット・特殊約定挙動があるため、Persistent Demo LedgerとSimulationの境界設計が必要
- Daily Reportは単なるartifact dumpではなく、人間が毎日読む運用ブログとしてwriter品質を守る必要がある
- Approvalは固定金額ではなく、equity / exposure / cash / capital allocationと接続する必要がある
- Partial successは異常ではない。item単位の理由を残し、全体statusを不透明なBLOCKにしないことが重要

## 8. Phase13へ持ち越す課題

### High

- Runtime Acceptance Testの体系化
  - Market Refresh -> Daily Plan -> Approval -> Submit -> Fill -> Reconcile -> Report -> Notificationを1本で検証する
  - Source of Truth混在、date resolution、stale artifactを継続監査する
- Daily Report内部のSource of Truth完全統一
  - AI総括、Broker件数、Submitted Orders、Fill、Positionsの整合をさらに強化する
- Capital Allocation AI / Portfolio Rotation AIのOperations本線接続
  - Phase12ではcandidate countとApproval budgetを整えたが、full capital allocation integrationは未完
- Notification実送信の最終確認
  - 設定済み環境でのLINE / Discord送信は可能だが、Production-equivalent final acceptanceとして明示的確認が必要

### Medium

- Broker Executions / PositionsのDemo仕様整理
  - Demoでexecutions/positionsが空になるケースをAcceptance Testへ組み込む
  - Broker-confirmed fillとDemo Special Fill Simulationの表示・監査境界をさらに明確化する
- launchd更新漏れ防止
  - plist変更後のcopy/reload checklistをrelease手順化する
- Daily Report Candidate Top50 / feature detail mapping
  - 一部指標未取得時の説明は改善済みだが、feature artifactから取れる指標はさらに拾う余地がある

### Low

- Historical artifactのstatus表現整理
  - 修正前のBLOCK / REVIEW_REQUIRED artifactをsupersededとしてより見やすく扱う
- Demo matched opposite order testの再実行
  - Demo Special Fillで代替可能だが、Broker-confirmed matched fillは将来の確認項目として残る
- Operation docsのさらなる整理
  - Phase12で増えたrunbook / audit / report資料をPhase13冒頭で統合してもよい

## 9. 現在の完成度

| Area | Evaluation | Notes |
| --- | --- | --- |
| AI | Mostly Complete | BUY / SELL / Exitは接続済み。Portfolio Rotation / Capital Allocation本線接続はPhase13課題。 |
| Broker | Mostly Complete | Demo read-only / order submit / codec / issue code normalizerは実装済み。Demo fill特殊性はSimulationで扱う。 |
| Operations | Completed | Daily Operations RuntimeとCLI群は稼働可能。 |
| Runtime | Mostly Complete | launchd構成、date resolution、market calendar、SoTは整備済み。Acceptance Test体系化はPhase13へ。 |
| Safety | Completed | Fail Closed / Default Deny / MAX_EXPOSURE / System Guardとして機能。 |
| Approval | Completed | Dynamic Approval Maxに修正済み。manual overrideは明示時のみ。 |
| Capital Allocation | Needs Improvement | candidate countとbudget guardは整備済み。AI allocation本線接続は未完。 |
| Daily Report | Mostly Complete | Phase9 v4品質へ復元。内部SoT完全統一と指標拡張は継続課題。 |
| Notification | Mostly Complete | payload / send path / launchd optionは整備済み。最終実送信acceptanceはPhase13へ。 |
| Monitoring | Mostly Complete | Fill / Safety / Reconcile / Auditは稼働。Acceptance Test化が必要。 |
| Production Readiness | Mostly Complete | DemoとProduction差分は限定済み。Production Unlock前のfinal acceptanceが必要。 |

## 10. Phase13への推奨方針

Phase13では、追加機能を急ぐより、Production-equivalent Runtimeを継続運用できる状態へ固めることを優先する。

推奨順:

1. Runtime Acceptance Test整備
   - Phase12で見つかった漏れは、ほぼ実運用artifactの組み合わせで発生した
   - Phase13では1営業日flowをfixture / live-safe dry-runで毎回検証できるようにする

2. Portfolio Rotation AI / Capital Allocation AI接続
   - Phase12-ASでApproval Maxは85% Exposureへ整合した
   - 次は「どの5件を、いくらずつ、既存保有とどう入れ替えるか」をAI/Allocationとして本線接続する

3. Daily Report / Notificationのfinal acceptance
   - Blog qualityは復元済み
   - Phase13ではSoT整合と通知実送信結果のacceptanceを固定する

4. Demo 30営業日Stable Operation
   - Production Unlock前に、Demoで30営業日連続運用できることを確認する
   - 特にMarket Calendar、launchd、Notification、Reconcile、Approval expiryを監視する

5. Production Unlock Design
   - Phase12ではProduction Order Disabledを維持した
   - Production Unlockは別設計・別承認・別監査として扱う

## Final Judgement

```text
PHASE12_COMPLETE
PHASE13_READY_FOR_RUNTIME_ACCEPTANCE_AND_PORTFOLIO_ROTATION_DESIGN
PRODUCTION_ORDER_EXECUTION_REMAINS_BLOCKED
```
