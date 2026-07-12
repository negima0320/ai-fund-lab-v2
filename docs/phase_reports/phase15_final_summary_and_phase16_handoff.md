# Phase15 Final Summary and Phase16 Handoff

作成日: 2026-07-13

## 0. Final Status

```text
RUNTIME_V2_COMPLETE_PHASE15_CLOSED_WITH_OPERATIONAL_BOUNDARIES
```

Phase15は完了した。Runtime v2は、Phase16 Historical Runtime Paper Testで固定Engineとして使用できる状態まで到達した。

ただし、これはProduction Ready宣言ではない。実Broker BUY、実Broker BUY→SELL、Broker-connected multi-day、Notification Delivery、Production credentials、Production runbookは未完了のOperational / Production Boundaryとして残る。

## 1. Phase15開始時点

Phase15は、Phase12.5から続くRuntime再設計とPhase14 Runtime接続の後に始まった。

Phase14終了時点では、Market Refresh、Morning、Pending、Submit、Broker Accepted、Execution、Current Projection、Report、Notification Payload、SELL Planning CLI connectionまでは到達していた。しかしSubmit Guard Regressionで、通常Submit経路に隠れた固定値が残っていることが判明した。

代表例:

```text
max_order_amount = 100000
```

このhidden defaultがBUY / SELL双方に作用し、Capital Allocation ContractやSELL liquidation Contractを壊す危険があった。

Phase15開始時点の本質的課題は以下だった。

| Area | Problem |
|---|---|
| Runtime Contract | 設計契約・実装・通常CLI経路・Evidenceが一致していなかった |
| Current | Current / History / Derivedが混在し、Current authorityが弱かった |
| Pending | Submit対象が固定されず、stale Pendingや二重実行の危険があった |
| Safety | placeholder allowやSafety未接続の危険が残っていた |
| AI | Candidate / Opportunity / PM AIが正式Producerとして閉じ切っていなかった |
| Temporal | `Current.as_of == business_date` という単純freshness判定が破綻していた |
| Broker | Broker ReadOnly / Write / Demo / Simulation / Production境界が曖昧だった |
| Acceptance | 「動いた」ことと「通常MainlineがEvidence付きで安全に動く」ことが混同されていた |

## 2. Phase15の目的

Phase15の目的は、Runtimeを単なる実行スクリプト群から、AI Fund Lab v2を安全に継続運用するための制御システムへ成熟させることだった。

目的:

- Runtime Architecture v2完成
- Runtime Mainline接続
- Runtime Acceptance
- Broker接続検証
- BUY / SELL状態遷移検証
- RuntimeをProduction品質へ近づける
- 設計契約・実装・Evidence・Regressionを一致させる

Runtime v2の役割はAI判断ではない。AI、Policy、Safety、Broker、Execution、Current、Reportを正しい順序でつなぎ、危険時に止まり、証跡を残し、二重実行を防ぐ制御層である。

## 3. Runtime v2で完成したもの

| Component | Final State |
|---|---|
| Runtime State | `runtime_state/current_state.json` がCurrent pointer、Current version/hash、Execution reference、Runtime State versionを保持する |
| Current | `persistent_ledger/state.json` がCurrent authority。Position StateとValuation Stateを分離 |
| Ledger | orders / executions / positions / cash / eventsをappend-only JSONLとして管理し、dedupで二重追加を防止 |
| Pending | `pending_order_plan/pending_order_plan.json` のみがSubmit source。Plan / Itemともに`CONSUMED`へ閉じる |
| Approval | Human ReviewとHuman Approvalを分離。ApprovalはSubmit Pending promotion / apply authorityとして扱う |
| Safety | Runtime Safety Decisionを正式入力化。Missing / REVIEW_REQUIRED / BLOCKED / HALTをfail-closedで扱う |
| Execution | SimulationとDemo fallbackを区別し、Execution evidenceをLedger / Currentへ接続 |
| Broker Boundary | Demo / Simulation / Productionを分類し、Demo fallbackはProductionへ持ち込まない |
| Report | Runtime Report / Public Report / Blog Markdown / Discord Payload / LINE Payloadを生成 |
| Authority | Auto Trade、Human Review、Human Approval、Broker Write Authorization、Production Authorizationを分離 |
| Temporal Contract | business date、market date、feature date、position_state_as_of、valuation_as_of、generated_atを分離 |
| Idempotency | Submit、Execution、Ledger、Current Apply、PnL、Pending consumeの二重実行防止を確認 |

最終的に成立したMainline:

```text
Market / Feature / AI / Policy / Safety
↓
Planning
↓
Authoritative Pending
↓
Normal Submit Pipeline
↓
Execution Processor
↓
Ledger Writer
↓
Current Projector
↓
Current Apply
↓
Runtime State
↓
Runtime Report / Public Report / Blog / Notification Payload
```

## 4. Phase15で見つかった重大問題

### Current Authority

原因:

- Currentが日付別ArtifactやDerived情報と混ざりやすく、正式Source of Truthが曖昧だった。
- `Current.as_of == business_date` でfreshnessを判定していた。

修正内容:

- `persistent_ledger/state.json` をCurrent authorityとして固定。
- Current version/hash、current_pointer、Runtime State referenceを追加。
- Position StateとValuation Stateを分離。

最終状態:

```text
Current authority: ACCEPTED
Current version/hash: present
Current is restored and applied through Runtime State
```

### Execution Authority

原因:

- Demo Brokerでは`CLMOrderListDetail`が失敗し、Execution detailだけでは約定を確定できなかった。
- Order List、Position difference、Cash、Browser confirmationの役割が未整理だった。

修正内容:

- `DEMO_ORDERLIST_POSITION_EXECUTION_EQUIVALENT_FALLBACK_V1` をDemo限定Authorityとして定義。
- Production equivalentをfalseに固定。
- Normal Execution Processor経路とDemo-only fallbackを分離。

最終状態:

```text
Demo execution-equivalent: ACCEPTED_DEMO_ONLY
Normal simulation execution processor: ACCEPTED
Production fallback: NOT_ALLOWED
```

### Pending

原因:

- Review Pending、Submit Pending、Approval、Apply、Consumed状態が混同されていた。
- Planが`CONSUMED`でもItemが`CREATED`のまま残る不整合があった。

修正内容:

- Review PendingはSubmit authorityではないと明確化。
- Human Approval / Promotion Candidate / Apply Candidate / Authoritative Pendingを分離。
- Submit成功後にPlan / Itemとも`CONSUMED`へ閉じるよう修正。

最終状態:

```text
Pending Plan: CONSUMED
Pending Item: CONSUMED
Submit source: pending_order_plan/pending_order_plan.json only
```

### SELL Runtime

原因:

- SELL review、SELL planning、SELL submit、SELL executionの境界が曖昧だった。
- Safety REVIEW_REQUIRED時にSELL/HOLDレビューを進めるべきか停止すべきか未整理だった。

修正内容:

- Human Safety Reviewを導入。
- SELL/HOLD Review-only Morningを正式ScopeとしてAcceptance。
- SELL Planning、Submit Guard、Broker available quantity evidenceを整備。

最終状態:

```text
SELL/HOLD Review-only: ACCEPTED
SELL Planning / Submit simulation / Round Trip SELL: ACCEPTED_WITH_SCOPE_BOUNDARY
```

### BUY Runtime

原因:

- SELL起点の証明をBUY起点の成功として扱えなかった。
- BUY後Currentを翌営業日にPM AI / SELL/HOLDへ引き継ぐEvidenceが不足していた。

修正内容:

- BUY-origin End-to-End Acceptanceを実施。
- 7203 BUY 100 → Current → 翌日PM AI → HOLDを証明。
- BY2でSimulation分類、Current authority、Runtime State metadata、Pending Item lifecycleを閉じた。

最終状態:

```text
BUY-origin Runtime transition: ACCEPTED_WITH_CONDITIONS
BUY-origin authority cleanup: CLOSED
```

### Safety

原因:

- Safety placeholder allowや、Safety未接続時に進めてしまう危険があった。
- 4591 HIGH_RISK_REVIEWを無理に解除すべきか、運用フローに載せるべきかが未整理だった。

修正内容:

- Runtime Safety Decisionを正式Contract化。
- 4591 Human Safety Reviewを導入。
- REVIEW_REQUIREDを停止ではなくreview-only operationへ変換できるようにした。

最終状態:

```text
Safety authority: ACCEPTED
Safety event forced clear: NOT_PERFORMED
Review-only operation: ACCEPTED
```

### Broker

原因:

- mock / fixture / real Broker APIの区別が曖昧だった。
- Demo初期保有銘柄をRuntime-owned position mismatchとして扱う過剰判定があった。

修正内容:

- Broker authenticityを`data_origin=BROKER_API`で確認。
- Demo preloaded positionsを`OUT_OF_RUNTIME_OWNED_SCOPE`として分類。
- Fresh Demo reset後のEvidenceをSource of TruthにしてScenarioを再選定。

最終状態:

```text
Broker ReadOnly authenticity: ACCEPTED
Demo Broker Write: ACCEPTED_ONCE
Broker-connected continuous operation: NOT_ACCEPTED
```

### Temporal

原因:

- business_date、market_data_as_of、feature_date、position_state_as_of、valuation_as_of、generated_atが混同されていた。

修正内容:

- Runtime Temporal / Freshness Contractを作成。
- Current PositionとCurrent Valuationを分離。
- No-fill valuation-only pathを整備。

最終状態:

```text
Temporal Contract: ACCEPTED
No-fill valuation-only Current: ACCEPTED
```

### Feature / Data Contract

原因:

- Feature Artifactが存在していてもCandidate / Opportunity / PM AIが読めるとは限らなかった。

修正内容:

- Canonical Feature Schema、Feature Consumer Readiness、Data Readiness Gateを整備。

最終状態:

```text
Feature Consumer Readiness: ACCEPTED
Data Readiness Gate: ACCEPTED
```

### Production Classification

原因:

- Acceptance Simulation由来のLedger / Currentが`production_equivalent=true`として残った。

修正内容:

- Simulation sourceを分類し、`production_equivalent=false`、`acceptance_only=true`、`simulation=true`を保持。

最終状態:

```text
Simulation classification: CLOSED
Production evidence contamination: RESOLVED
```

### Mainline

原因:

- Demo Broker WriteからCurrent Applyまでは成立したが、Direct Adapter Callや専用Apply Scriptを使っており、通常Mainlineではなかった。

修正内容:

- BXでNormal Runtime Mainline接続を閉じた。
- BY/BZでBUY起点とRound Tripを通常Submit / Execution / Current Apply経路で証明した。

最終状態:

```text
Normal Runtime Mainline: ACCEPTED_WITH_CONDITIONS
```

### Notification

原因:

- Payload生成とDeliveryが混同されていた。

修正内容:

- Runtime Report、Public Report、Blog Markdown、Discord Payload、LINE PayloadをAccepted。
- Discord / LINE DeliveryはOperational Boundaryとして分離。

最終状態:

```text
Payload: ACCEPTED
Delivery: NOT_ACCEPTED
Runtime Core Blocker: false
```

## 5. Runtime Acceptanceで実施した内容

| Scope | Result | What Was Proven |
|---|---|---|
| Review-only | `STEP1_REVIEW_ONLY_READY` | Safety REVIEW_REQUIRED下でもSELL/HOLD review evidenceを生成可能 |
| SELL | `ACCEPTED_WITH_SCOPE_BOUNDARY` | SELL Planning / Submit simulation / Round Trip SELLが成立 |
| Submit | `ISOLATED_SIMULATED_SUBMIT_ACCEPTED` | APPROVED PendingからSubmit Pipelineを通し、PendingをCONSUMEDへ閉じる |
| Broker | `DEMO_BROKER_WRITE_ACCEPTED` | Tachibana Demoで6501 SELL 100を1回送信しACCEPTED |
| Execution | `EXECUTION_EQUIVALENT_READY_DEMO_ONLY` / Normal simulation accepted | Demo fallbackとNormal simulation executionを区別して接続 |
| Current | `CURRENT_APPLY_ACCEPTED_DEMO_ONLY` / BZ Current accepted | LedgerからCurrent更新、hash/version、Runtime State接続 |
| BUY | `BUY_ORIGIN_END_TO_END_ACCEPTED_WITH_CONDITIONS` | BUY→Current→翌日PM AI→SELL/HOLDが成立 |
| Round Trip | `RUNTIME_ROUND_TRIP_ACCEPTED_WITH_CONDITIONS` | BUY→SELL→Position 0→Cash復帰を証明 |
| Mainline | `NORMAL_RUNTIME_MAINLINE_CONNECTED_WITH_CONDITIONS` | Normal Submit / Execution / Ledger / Current / Reportが接続 |
| Final Review | `RUNTIME_V2_COMPLETE_PHASE15_CLOSED_WITH_OPERATIONAL_BOUNDARIES` | Runtime v2完成、Phase15完了、Production Readyとは分離 |

## 6. 実Broker Acceptance

実際に立花証券Demoで行った内容:

```text
6501 SELL 100
Order Type: MARKET
Time In Force: DAY
Broker Write Count: 1
Broker Response: ACCEPTED
Order List: 全部約定
Position: 200 -> 100
```

確認したこと:

- Demo Login / Session取得
- Broker ReadOnly Snapshot
- Open Orders
- Cash / Buying Power
- Position Inventory
- Fresh Broker Evidence
- Final Pre-Send Gate
- User Authorization
- Broker ACCEPTED
- Order List full fill
- Position change
- Demo-only Execution Evidence
- Current connection in isolated acceptance root

未実施:

```text
実Broker BUY
実Broker BUY→SELL
Continuous Broker Operation
Production Broker Write
```

実Broker SELL成功は、実Broker BUY→SELL Round Trip成功ではない。Phase15ではDemo Broker Writeを1回Acceptanceしたに留める。

## 7. Runtime Mainline

Phase15-BW時点では、Demo Broker WriteからCurrent Applyまでの実Evidenceチェーンは成立していたが、Direct Adapter Callや専用Apply Scriptを含んでいたため通常Mainlineではなかった。

Phase15-BX以降で閉じた通常Mainline:

```text
Authoritative Pending
↓
Submit Pipeline
↓
Execution Processor
↓
Ledger
↓
Current
↓
Current Apply
↓
Runtime State
↓
Report
```

最終状態:

```text
Normal Runtime Mainline:
CONNECTED_WITH_CONDITIONS
```

条件:

- Simulation boundaryでAcceptance。
- Production Writeではない。
- Broker-connected multi-dayは未実施。

## 8. BUY→SELL Round Trip

Phase15-BZで、BUY起点のRound TripをAcceptanceした。

Flow:

```text
Market
↓
Feature
↓
Candidate AI
↓
Opportunity AI
↓
Morning
↓
BUY Planning
↓
Pending
↓
Submit Simulation
↓
Execution
↓
Ledger
↓
Current
↓
翌日Current復元
↓
PM AI
↓
Acceptance Override SELL
↓
Submit Simulation
↓
Execution
↓
Ledger
↓
Current
↓
Cash復帰
```

数値:

| Field | Value |
|---|---:|
| Initial Cash | `1,000,000` |
| BUY | `7203 / 100株 / 1000円` |
| BUY Cost | `100,000` |
| Post-BUY Cash | `900,000` |
| Next-day Current Price | `1050` |
| SELL | `7203 / 100株 / 1050円` |
| SELL Proceeds | `105,000` |
| Final Cash | `1,005,000` |
| Realized PnL | `+5,000` |
| Position Count | `0` |

重要な分類:

```text
Original PM Decision: HOLD
Acceptance Override: EXIT_FOR_ROUND_TRIP_ACCEPTANCE
Production Applicable: false
Investment Performance Evidence: false
```

## 9. Runtime完成判定

```text
Runtime v2:
COMPLETE
```

理由:

- Runtime State authorityが明確。
- Current authorityが明確。
- Pending lifecycleが明確。
- Submit sourceが固定。
- Normal Submit Pipelineが存在し、Acceptance済み。
- Execution Processor、Ledger Writer、Current Projector、Current Applyが接続済み。
- BUY→SELL Round Tripが成立。
- Idempotencyが確認済み。
- Simulation / Demo / Production classificationが分離済み。
- Report / Blog / Notification Payloadが生成済み。

## 10. Phase15完成判定

```text
Phase15:
COMPLETE_WITH_OPERATIONAL_BOUNDARIES
```

Phase15の本来目的であるRuntime Architecture v2完成、Runtime Acceptance、実Broker接続検証、Mainline接続、BUY / SELL状態遷移検証、Production前境界整理は完了した。

ただしProduction運用やBroker-connected continuous operationはPhase15完了条件ではない。

## 11. Productionとの境界

| Judgment | Status | Meaning |
|---|---|---|
| Runtime v2 Complete | `COMPLETE` | Runtime CoreはPhase16固定Engineとして使用可能 |
| Phase15 Complete | `COMPLETE_WITH_OPERATIONAL_BOUNDARIES` | Runtime Acceptanceは完了、運用境界は残す |
| Production Ready | `NOT_READY` | Production credentials / account / runbook / monitoring / emergency operation未完 |
| Continuous Broker Operation | `NOT_READY` | 実Broker multi-dayとBUY→SELL未実施 |
| 5-Year Paper Test Ready | `READY_WITH_CONDITIONS` | Simulation / Historical Paper前提なら開始可能 |

Production Readyではない理由:

- Production credentials未確認。
- Production order enablement未Accepted。
- Production account reconciliation未Accepted。
- Production execution authority未Accepted。
- Production emergency operations / recovery runbook未Accepted。
- Notification Delivery未Accepted。
- Broker-connected multi-day未Accepted。

## 12. Operational Boundary

Runtime Core Blockerではないが、運用開始前に残るもの:

```text
実Broker BUY
実Broker BUY→SELL
Broker-connected Multi-Day
Notification Delivery
Monitoring
Recovery
Runbook
Production Enablement
```

Demo Reset Detection:

| Question | Judgment |
|---|---|
| Phase15必須 | `NO` |
| Phase16 Paper Test必須 | `NO` |
| Broker-connected multi-day必須 | `YES` |
| Runtime Paper Test必須 | `NO` |
| Production必須 | `NO_AS_DEMO_SPECIFIC` |

Runtime Paper TestはSimulated Broker / Historical Replayを使うため、Tachibana Demo reset問題と分離する。

## 13. Phase16

Phase16の目的:

```text
Historical Runtime Paper Test
Runtime v2を固定Engineとして利用
AI / Policy / Safety改善
収益検証
最大ドローダウン検証
勝率 / Profit Factor / Safety影響分析
再検証
```

Phase16では、Phase15でAcceptedしたRuntime v2を原則固定し、過去データ上で実運用相当の意思決定・状態遷移・Current更新・Report生成を検証する。

## 14. Phase16推奨構成

| Prefix | Work |
|---|---|
| Phase16-A | Historical Runtime Paper Test Contract |
| Phase16-B | 5営業日 Smoke |
| Phase16-C | 20営業日 Paper Test |
| Phase16-D | 1年 Runtime Paper Test |
| Phase16-E | Performance and Failure Attribution |
| Phase16-F | AI / Policy / Safety / PM / Feature Improvement |
| Phase16-G | 1年 Revalidation |
| Phase16-H | 5年 Runtime Paper Test |
| Phase16-I | Final Performance Review |

## 15. Runtime固定方針

Phase16では原則として:

```text
Runtime v2を固定Engine
```

として扱う。

改善対象:

```text
Candidate AI
Opportunity AI
Position Management AI
Feature
Policy
Safety
Capital Allocation
```

Runtime Core bugだけは別扱いとする。Historical ReplayでRuntime Coreの欠陥がEvidence付きで見つかった場合は、Performance改善ではなくRuntime bug fixとして止めて扱う。

Phase16で避けること:

- 新Runtimeを作り直す。
- Paper Test失敗をすぐRuntime Coreのせいにする。
- Acceptance Fixtureを実運用成績として扱う。
- Production / Demo Broker問題をHistorical Paper Testに混ぜる。

## 16. 最終メッセージ

Phase15は、Runtime v2を「動くRuntime」から「証拠を持って安全に進む制御システム」へ引き上げたフェーズだった。

Runtime v2は完成した。Phase15 Runtime Acceptanceは完了した。ただし、これはProduction Readyではない。

ここからは、Runtimeを作るフェーズではなく、Runtimeを固定EngineとしてAI Fund Lab v2の実力を検証するフェーズへ入る。Phase16ではHistorical Runtime Paper Testを通じて、Candidate、Opportunity、PM、Feature、Policy、Safety、Capital Allocationの改善余地を測り、収益性・リスク・継続運用品質を検証する。

Next prefix:

```text
Phase16-A Historical Runtime Paper Test Contract
```

## 17. Phase15で得られた最大の成果

Phase15最大の成果は、AI Fund Lab v2が:

```text
AIモデルを開発するプロジェクト
```

から:

```text
Runtimeを中心とした運用システム
```

へ進化したことである。

Runtime v2は、以下をEvidence付きContractで接続する制御システムとして完成した。

```text
AI
Policy
Safety
Pending
Broker
Execution
Ledger
Current
Report
```

RuntimeはAI判断を行うものではない。Runtimeは、AI判断を:

```text
安全に
再現可能に
証跡付きで
二重実行なく
運用する
```

ためのEngineである。

Phase15開始時は、Runtime、Current、Pending、Execution、Safetyの責務が曖昧で、通常Mainlineも閉じていなかった。

Phase15終了時点では:

```text
BUY
↓
Current
↓
翌日
↓
PM AI
↓
SELL
↓
Current
↓
Cash
```

まで、通常Runtime Mainlineで状態遷移が成立した。

これは、AI Fund Lab v2のRuntime基盤が完成したことを意味する。

## 18. Phase16への考え方

Phase16は:

```text
Runtimeを開発するPhase
```

ではない。

Phase16ではRuntime v2を固定Engineとして扱う。

改善対象は以下である。

```text
Candidate AI
Opportunity AI
Position Management AI
Feature
Policy
Safety
Capital Allocation
```

Runtime Coreは、Historical Runtime Paper TestでEvidence付きBugが見つかった場合のみ修正対象とする。

Performanceが悪かった場合、最初に疑うべきものは:

```text
AI
Feature
Policy
Safety
```

であり、Runtimeではない。

## 19. Git Tag推奨

Phase16開始前の基準点として、以下のようなGit Tagを付与することを推奨する。

```text
phase15-runtime-v2-complete
```

または:

```text
v2.0.0-runtime-complete
```

このTagを、Phase16 Historical Runtime Paper Test開始前の固定Runtime v2基準点とする。
