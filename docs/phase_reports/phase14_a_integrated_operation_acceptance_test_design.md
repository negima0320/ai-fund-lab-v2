# Phase14-A Integrated Operation Acceptance Test Design

作成日: 2026-07-07

## Status

```text
PHASE14A_DESIGN_ONLY
```

本資料は Phase14-A の設計資料である。本フェーズでは実装変更、テスト実行、Broker API 呼び出し、Submit、注文、約定確認、通知送信、launchd / plist 変更、Backtest / Simulation、AI 再学習は行わない。

## 1. Phase14 全体の再定義

Phase14 は、Phase13 引き継ぎ時に候補として示された Broker ReadOnly Rehearsal だけではない。

Phase14 は、これまで構築してきた以下の統合受け入れテストである。

```text
AI
Safety
Runtime v2
Broker Integration
Pending
Demo Submit
Broker Status Sync
Execution Reflection
Ledger
Asset
Reconcile
Report
Notification Payload
Audit
Manual Operation
```

Phase13 では Runtime v2 の設計、skeleton、Current / History / Derived 分離、Single Writer Rule、Legacy Runtime Isolation、Acceptance Dry Run までが完了した。一方で、Phase13 では Submit、Broker 注文、Demo / Production 注文、通知送信、launchd 再開、Backtest / Simulation、AI 再学習は実行していない。

したがって Phase14 は、Runtime v2 が実運用に近い手順で破綻なく動くかを確認する Integrated Operation Acceptance Test として定義する。

Phase14 では立花証券 API のデモ環境を使う。Demo Submit、Demo 注文、Demo 約定確認は検証対象に含めてよい。ただし Production 注文、本番 Broker API Write、実資金運用は絶対に禁止する。

## 2. Phase14-A の目的

Phase14-A の目的は、実装前に通し運用テストの設計、範囲、許可事項、禁止事項、Acceptance Criteria、段階計画を固定することである。

Phase14-A では次を決める。

- Phase14 を Integrated Operation Acceptance Test として扱う。
- Demo 環境で許可する操作と、本番環境で禁止する操作を分離する。
- Runtime v2 の原則を通し運用テストでも維持する。
- Demo Submit を扱う段階と、その前提条件を明確にする。
- 異常時に REVIEW_REQUIRED または BLOCKED へ止まる条件を明確にする。
- Phase14-B 以降のテスト段階を定義する。

Phase14-A では次を行わない。

- コード変更
- テスト実行
- Broker API 呼び出し
- Demo Submit 実行
- Demo 注文
- Production 注文
- 通知送信
- launchd / plist 変更

## 3. Phase14 で許可すること

Phase14 では、明示された段階と Acceptance を満たす範囲で、以下を許可対象に含める。

- Demo Broker connectivity / capability preflight
- Demo Broker ReadOnly sync
- Demo Submit
- Demo 注文
- Demo 約定確認
- Demo order status sync
- Runtime v2 manual operation
- Current State Read
- Market Refresh
- Feature Refresh
- AI inference
- Planning
- Approval
- Pending promotion / lifecycle
- Execution Reflection
- Ledger Update
- Asset Update
- Reconcile
- Report
- Notification Payload 生成
- Audit
- Manual Review
- 必要最小限の軽量テスト

Demo Submit / Demo 注文は、Production 注文の解禁ではない。Demo 環境の能力確認および Runtime v2 の統合受け入れテストとしてのみ扱う。

## 4. Phase14 で禁止すること

Phase14 では、明示的に別フェーズで解除されるまで、以下を禁止する。

- Production 注文
- 本番 Broker API Write
- 実資金運用
- Production endpoint への注文系到達
- Production credential を使った注文系処理
- launchd 完全自動運用再開
- plist 新規作成、削除、差し替え
- Notification 実送信
- LINE / Discord / 外部通知の送信
- AI 再学習
- Full Backtest
- Simulation
- 既存 Legacy Runtime を Runtime v2 正規フローとして復活させること
- Broker Submit の不明結果を自動再送で解決すること
- CONSUMED Pending を再 Submit すること

Notification は Phase14-A 設計上、Payload 生成までを対象とする。実送信は別フェーズの明示 Acceptance 後に扱う。

## 5. End-to-End Flow 設計

Phase14 の標準 End-to-End Flow は以下とする。

```text
1. Market Refresh
2. Feature Refresh
3. Current State Read
4. AI inference
5. Planning
6. Approval
7. Pending
8. Demo Submit
9. Demo Broker Status Sync
10. Execution Reflection
11. Ledger Update
12. Asset Update
13. Reconcile
14. Report
15. Notification Payload
16. Audit
17. Manual Review
```

### 5.1 Market Refresh

市場データを更新し、Runtime v2 の後続処理に必要な market / feature 入力の鮮度を確認する。

Acceptance では、Market Refresh の成否、対象 business date、入力 source、欠損、再実行可能性を evidence として残す。

### 5.2 Feature Refresh

AI inference に必要な特徴量を更新する。

Feature Refresh は再実行可能処理として扱う。Feature 欠損や freshness 不足は、推測で補完せず REVIEW_REQUIRED または BLOCKED へ送る。

### 5.3 Current State Read

Runtime v2 は Current を固定 Path から読む。

主な Current は以下である。

```text
runtime_state/current_state.json
pending_order_plan/pending_order_plan.json
persistent_ledger/state.json
notification_delivery/delivery_ledger.jsonl
```

History や Derived artifact から Current を推測しない。

### 5.4 AI inference

Candidate AI、Opportunity AI、Position Management AI、Capital Allocation、Safety の出力を受け取る。

Runtime は AI 判断ロジックを持たない。Runtime は AI 出力を運用可能な順序と状態遷移へ載せる。

### 5.5 Planning

AI 出力、Current State、Safety Signal、Capital Allocation をもとに Order Plan を生成する。

Planning は Submit ではない。Planning artifact は History / Evidence であり、Submit 対象ではない。

### 5.6 Approval

Demo Submit 前に Approval を必須とする。

Approval は plan hash、pending hash、business date、runtime mode、environment、承認者、承認時刻、承認対象を明示する。

Approval がない場合、Submit は BLOCKED とする。

### 5.7 Pending

Submit 対象は `pending_order_plan/pending_order_plan.json` のみに固定する。

Pending は lifecycle を持つ。APPROVED の Pending だけが Demo Submit 候補になれる。CONSUMED、CANCELLED、EXPIRED、POST_SEND_UNKNOWN 扱いの Pending は再 Submit してはならない。

### 5.8 Demo Submit

Demo Submit は Phase14 の検証対象に含める。ただし、以下の条件を満たす場合に限る。

- environment が demo である。
- Production endpoint ではないことを preflight で確認できる。
- Production credential を注文系処理に使っていない。
- Approval が成立している。
- Submit 対象が Pending である。
- 二重送信 guard を通過している。
- Safety が system fault を検知していない。
- Manual Operation として実行される。

Demo Submit は非冪等処理である。失敗時、通信断、結果不明、応答不明は POST_SEND_UNKNOWN として扱い、自動再送しない。

### 5.9 Demo Broker Status Sync

Demo Submit 後は、Demo Broker ReadOnly で注文状態、約定状態、保有、現金、買付余力を確認する。

Broker を source of truth とし、Runtime / Ledger / Asset は Broker evidence と照合する。

### 5.10 Execution Reflection

Broker Order と Broker Execution から fill 状態を分類する。

BrokerOrder は Asset SoT ではない。Execution、Position、Cash evidence を経由して Ledger / Asset へ反映する。

### 5.11 Ledger Update

Ledger は注文、約定、保有、現金、イベントを分離して記録する。

同一 execution の二重 append を防止する。POST_SEND_UNKNOWN、partial fill、filled order without position などは evidence として残し、必要に応じて REVIEW_REQUIRED へ送る。

### 5.12 Asset Update

`persistent_ledger/state.json` を Asset Current SoT とする。

Asset は LedgerPosition、LedgerCash、Broker Position、Broker Cash / Buying Power evidence から構築する。BrokerOrder だけから Asset を作らない。

### 5.13 Reconcile

Pending、Broker Orders、Broker Executions、Ledger、Asset、Cash / Buying Power を照合する。

不整合は隠さず、REVIEW_REQUIRED または BLOCKED として扱う。

### 5.14 Report

Report は Derived artifact である。

Report は Current と Evidence を分離して表示する。Report を Current State として扱わない。Report から Submit 可否を推測しない。

### 5.15 Notification Payload

Notification Payload は生成のみ対象とする。

Delivery dedup key、payload hash、channel、business date、target を確認する。Notification 実送信は Phase14 の禁止事項に含め、別フェーズで扱う。

### 5.16 Audit

Audit は Evidence であり、Submit source ではない。

Audit は Current / History / Derived 境界、Single Writer Rule、Production 禁止、Demo environment 固定、secret / raw response 保存禁止、二重送信防止、Legacy Runtime Isolation を確認する。

### 5.17 Manual Review

異常、結果不明、不整合、stale data、system fault、approval mismatch は Manual Review に送る。

Manual Review では Broker 状態を正とし、自動復旧、自動再送、自動 Production 移行を行わない。

## 6. Runtime v2 で守る原則

Phase14 の統合受け入れテストでも、Phase13 で固定した Runtime v2 原則を維持する。

- Current / History / Derived を分離する。
- Current は固定 Path から読む。
- Current Object は Single Writer Rule に従う。
- Pending だけが Submit 対象である。
- `persistent_ledger/state.json` が Asset Current SoT である。
- BrokerOrder は Asset SoT ではない。
- Execution / Position / Cash evidence を経由して Asset を作る。
- POST_SEND_UNKNOWN は自動再送禁止である。
- CONSUMED Pending は再 Submit 禁止である。
- Runtime は AI 判断ロジックを持たない。
- Runtime は 5 銘柄固定制御を持たない。
- Runtime は銘柄数ではなく、資金、買付余力、Broker 制約、Safety 制約、重複注文防止を制御する。
- Missing / Unknown を Empty 扱いしない。
- Report は Derived である。
- Notification は Payload 生成までであり、send は別責務である。
- Audit は Evidence であり、Submit source ではない。
- Legacy Runtime workflow を Runtime v2 正規フローに戻さない。

## 7. テスト段階案

### Phase14-B: Demo Broker Connectivity / Capability Preflight

目的:

```text
Demo Broker への接続能力、環境固定、注文系能力、禁止経路遮断を確認する。
```

対象:

- Demo endpoint 確認
- Production endpoint deny 確認
- Demo credential / required secret presence の安全確認
- ReadOnly capability
- Demo order capability preflight
- forbidden CLMID / production write path deny
- secret / raw response redaction

この段階では原則として注文しない。Demo Submit 実行条件が満たせるかを確認する。

### Phase14-C: Runtime v2 Dry-run with Real Current State

目的:

```text
実 Current State と Broker ReadOnly evidence を使い、Submit 直前まで Runtime v2 flow を確認する。
```

対象:

- Market Refresh
- Feature Refresh
- Current State Read
- AI inference
- Planning
- Approval prepare
- Pending promotion
- Demo Submit preflight
- Broker ReadOnly sync
- Reconcile dry-run
- Report / Notification Payload / Audit

この段階では Demo Submit しない。

### Phase14-D: Demo Submit Single-order Guarded Test

目的:

```text
Manual Approval 済み Pending から、Demo 環境で単一注文を一度だけ Submit できることを確認する。
```

条件:

- environment=demo
- Production endpoint deny PASS
- Approval PASS
- Pending APPROVED
- duplicate submit guard PASS
- Safety system fault なし
- order size は検証用の最小限
- Manual Operation として実行

確認:

- Demo 注文が 1 回だけ送信される。
- 同一 Pending の二重送信が防止される。
- Submit 結果不明時に POST_SEND_UNKNOWN へ止まり、自動再送しない。
- Production 注文は発生しない。

### Phase14-E: Demo Execution Reflection / Ledger / Asset Test

目的:

```text
Demo Broker ReadOnly で注文状態・約定状態を確認し、Ledger / Asset へ正しく反映できることを確認する。
```

対象:

- Demo order status sync
- Demo execution / partial fill / no fill classification
- Ledger append / dedup
- Position / Cash / Buying Power evidence
- Asset state build
- BrokerOrder not Asset SoT guard
- Reconcile
- Report
- Audit

### Phase14-F: Full Manual Operation Rehearsal

目的:

```text
Market Refresh から Audit / Manual Review まで、人間操作を含む 1 日分の統合運用を確認する。
```

対象:

- 全 End-to-End Flow
- Manual approval
- Demo Submit
- Demo Broker sync
- Ledger / Asset / Reconcile
- Report / Notification Payload / Audit
- REVIEW_REQUIRED / BLOCKED handling

Notification 実送信はしない。

### Phase14-G: Multi-day Operation Rehearsal

目的:

```text
複数 business date にまたがって Current、History、Pending、Ledger、Asset、Report が破綻しないことを確認する。
```

対象:

- Day N Pending / Submit / Ledger / Asset
- Day N+1 Current State Read
- consumed pending no-resubmit
- open order carry-over
- partial fill carry-over
- cash / buying power carry-over
- report / audit continuity

### Phase14-H: Production Readiness Review

目的:

```text
Production 注文禁止を維持したまま、Production readiness の条件だけを監査する。
```

対象:

- Demo rehearsal 結果
- Production endpoint deny
- production credential handling
- manual approval policy
- safety / emergency stop
- broker divergence handling
- launchd 再開条件
- notification send 条件
- rollback / recovery
- operator runbook

Phase14-H は Production 注文の実行フェーズではない。Production 解禁には別途明示的な承認と Acceptance が必要である。

## 8. Acceptance Criteria

Phase14 Integrated Operation Acceptance Test の Acceptance Criteria は以下とする。

### Environment / Production Prohibition

- Demo 環境のみであることを確認できる。
- Production endpoint に注文系処理が到達しない。
- Production credential を注文系処理に使わない。
- 本番 Broker API Write が発生しない。
- 実資金運用が発生しない。
- Production 注文は禁止されたままである。

### Submit / Approval / Pending

- Pending 以外から Submit しない。
- Submit 前に Approval が必須である。
- Approval は plan hash / pending hash / business date / environment と一致する。
- Demo 注文が二重送信されない。
- POST_SEND_UNKNOWN は自動再送されない。
- CONSUMED Pending は再 Submit されない。

### Broker / Execution / Ledger / Asset

- 注文状態を Broker ReadOnly で確認できる。
- 約定状態を Broker ReadOnly で確認できる。
- Broker を source of truth として扱う。
- BrokerOrder のみから Asset を作らない。
- Execution / Position / Cash evidence から Ledger / Asset が作られる。
- Ledger append が重複排除される。
- `persistent_ledger/state.json` が Asset Current SoT として扱われる。

### Runtime v2 Boundary

- Current / History / Derived が分離されている。
- Current は固定 Path から読まれる。
- Single Writer Rule が破られない。
- Report は Derived として扱われる。
- Notification は Payload 生成のみで、実送信されない。
- Audit は Submit source にならない。
- Legacy Runtime が正規フローとして復活しない。

### Reconcile / Safety / Manual Review

- Reconcile で不整合を検知できる。
- cash / buying_power / position / order / execution mismatch を隠さない。
- stale broker snapshot は REVIEW_REQUIRED または BLOCKED になる。
- unknown severe error は fail closed になる。
- 異常時は REVIEW_REQUIRED または BLOCKED へ止まる。
- Manual Review は Broker 状態を正として確認する。

### Evidence / Security

- raw response を保存しない。
- virtual URL を保存しない。
- auth id、private key、second password を保存しない。
- account id、order id、execution id の plaintext を保存しない。
- Evidence は監査可能であり、秘密情報を含まない。
- AI 再学習、Full Backtest、Simulation は実行されない。

## 9. Phase14-A の完了条件

Phase14-A の完了条件は以下とする。

- 本設計資料を作成する。
- Phase14 を Integrated Operation Acceptance Test として再定義する。
- Phase14 で許可することを明記する。
- Phase14 で禁止することを明記する。
- End-to-End Flow を明記する。
- Runtime v2 で守る原則を明記する。
- Phase14-B 以降の段階計画を明記する。
- Acceptance Criteria を明記する。
- 実装変更を行わない。
- テスト実行を行わない。
- Broker API 呼び出しを行わない。
- 注文を行わない。
- 通知送信を行わない。
- launchd / plist 変更を行わない。

## 10. Final Decision

```text
PHASE14A_DESIGN_ONLY_COMPLETE
```

理由:

- Phase14 を Broker ReadOnly Rehearsal だけではなく Integrated Operation Acceptance Test として再定義した。
- Demo Submit / Demo 注文 / Demo 約定確認を Phase14 の検証対象として明示した。
- Production 注文、本番 Broker API Write、実資金運用を絶対禁止として明記した。
- Runtime v2 の Current / History / Derived 分離、Single Writer Rule、Pending only Submit、Asset Current SoT、POST_SEND_UNKNOWN 自動再送禁止、CONSUMED 再 Submit 禁止を維持した。
- Phase14-B 以降の段階計画と Acceptance Criteria を定義した。
- 本フェーズでは設計のみを行い、実装変更、テスト実行、Broker API 呼び出し、注文、通知送信、launchd / plist 変更は行っていない。
