# Phase15 Final Summary / Runtime Acceptance Handoff

作成日: 2026-07-11

## 0. この資料の位置付け

本資料は、長期化したPhase15を次チャットへ引き継ぐための正式ハンドオフである。

これは単なる実装履歴ではない。Phase15でRuntime v2がどのように設計成熟したのか、なぜ当初のRuntime Acceptanceが止まり、何を設計契約として追加し、次にどこから再開すべきかをまとめる。

Phase15はまだ完全完了ではない。

現在の状態は以下である。

```text
Phase15-1 Runtime Reconstruction: 実質完了
Phase15-2 Runtime Acceptance: 開始済み、Step1で一度停止、その後ブロッカー修正がAZまで進行
Phase15 Complete: 未完了
```

次チャットの役割は、実装済みのRuntime v2をEvidenceで再確認し、Step0からRuntime Acceptanceを再開することである。

## 1. AI Fund Lab v2 / Phase15 / Runtimeの目的

AI Fund Lab v2の目的は以下である。

```text
年間50%の利益を目指し、
安心・安全に自動売買を継続できる運用システムを実現すること
```

Phase15の目的は以下である。

```text
Runtimeという制御システムへの信頼を確立すること
```

Runtime v2はAIではない。Runtimeは投資判断を行う場所ではなく、AI / Policy / Safety / Broker / Current / Report / Notificationを設計どおり接続し、証跡を残し、危険時に止める制御中枢である。

Runtimeの責務は以下の制御連鎖を壊さないことである。

```text
AI
↓
Capital Allocation / Capital Deployment Policy
↓
Safety
↓
Runtime
↓
Broker
↓
Execution / Ledger
↓
Current
↓
Report
↓
Notification
↓
Operator
```

Runtimeがhidden default、hidden policy、古いArtifact、未接続Component、曖昧なfreshness判定を持つと、AIやSafetyが正しくてもシステム全体が壊れる。Phase15はこの失敗を防ぐための再構築フェーズだった。

## 2. Phase15開始時点のRuntime状態

Phase14終了時点で、Runtime v2は大きく前進していた。

確認済みだったもの:

- Market Refresh
- Feature Refresh
- Morning Planning
- Pending生成
- Approval
- Submit
- Broker Accepted
- Execution
- Current Projection
- Report
- Public Report
- Notification Payload
- SELL Planning CLI接続

しかし最終運用テストでSubmit Guard Regressionが発覚した。

通常Submit経路に以下のhidden defaultが残っていた。

```text
max_order_amount = 100000
```

この値がBUY / SELL双方へ適用され、Capital Allocation契約とSELL liquidation契約を破壊していた。

そのためPhase14はCompleteではなく、以下として閉じた。

```text
REVIEW_REQUIRED / CLOSED_FOR_PHASE15_RUNTIME_REVIEW
```

Phase15開始時点の本質的な問題は、Runtimeが「動く」ように見えても、制御契約・証跡・実装・通常CLI経路が一致しているとは言えなかったことだった。

## 3. Phase15で見つかった問題

Phase15で見つかった問題は、単発のバグではなく、Runtime設計の成熟度不足だった。時系列に整理すると以下である。

| Phase | 問題 | 本質 |
|---|---|---|
| A-G | hidden `max_order_amount=100000`、BUY/SELL Guard未分離、Morning hidden cap、Active Policy Manifest不足 | RuntimeがPolicyを持ってしまい、Capital Allocation / SELL liquidationを後段で壊す危険 |
| F/Q/AE | Candidate AI、Opportunity AI、Position Management AIが通常Runtime経路に閉じていない | RuntimeがAI判断を代替していた |
| AC/AD | Safety Producer / Safety Evaluation regular pathが不足 | Safety evidenceがRuntime正式入力として閉じていなかった |
| AJ/AK | Step1 Morning AcceptanceでCandidate AI feature columns missing、Safety REVIEW_REQUIRED | Decision Chainは接続されてもData Contractが成立していなかった |
| AL/AM | Candidate / Opportunity / PM / SafetyのProducer-Schema-Artifact-Consumer不整合 | Artifact存在とConsumer Readyが混同されていた |
| AN/AO/AP | Feature schema、Opportunity prefix、PM input contract不備 | AI入力Schemaが正式契約化されていなかった |
| AQ/AS | Data Readiness Gate不足、semantic consistency不足 | Morning前にRuntime入力が実行可能か判定するGateがなかった |
| AR | stale Pending / Pending lifecycle不備 | 古いPendingが残留し、二重実行や日付混入の危険があった |
| AT/AU | `Current.as_of == business_date` という単純freshness判定の限界 | No-fill日、非営業日、配信前、市場データ遅延を区別できなかった |
| AV/AW/AX | Temporal FoundationとMarket / Quote Evidence、Broker snapshot deterministic regression | 各Componentが独自に日付・時刻・freshnessを判定していた |
| AY/AZ | Current Temporal Schemaとvaluation-only Producer不足 | Position StateとValuation Stateが混同され、約定なしの日にCurrentがstale扱いされた |

最重要の学びは以下である。

```text
Runtime Acceptanceは「Decision Chainが閉じた」だけでは足りない。

Decision Contract
Data Contract
Runtime Contract
Evidence Producer Contract
Temporal Contract

が揃って初めてRuntimeを信頼できる。
```

## 4. 問題に対する設計変更

### 4.1 Hidden PolicyをRuntimeから排除

Phase15前半では、Runtimeが勝手に資金投入量や注文上限を決めてはいけないことを明文化した。

設計変更:

- Capital Deployment Policyを明示Artifactとして導入
- `capital_deployment_demo.json` を本番基準名 `capital_deployment.json` へ整理
- BUY GuardとSELL Guardを分離
- SELL liquidationをBUY notional capで止めない
- Submit Guardは資金配分の再決定ではなく、安全確認と証跡出力に限定
- Active Policy Manifestを追加
- Policy hash consistency guardを追加

思想:

```text
RuntimeはPolicyを発明しない。
Runtimeは明示Policyを実行し、違反時は理由を出して止まる。
```

### 4.2 RuntimeがAI判断を代替しない構造へ変更

Phase15中盤では、Runtime内部でFeatureからBUY/SELL判断を生成する構造をやめ、既存AIを正式Producerとして接続した。

設計変更:

- Candidate AI -> Candidate Decision Artifact -> Opportunity AI
- Opportunity AI -> Ranking Artifact -> Morning Planning
- Position Management AI -> Position Decision Artifact -> SELL Planning
- RuntimeがBUY rankやSELL intentを独自生成しない

思想:

```text
AIが判断し、Runtimeが実行する。
RuntimeはAIのConsumerであり、AIの代替ではない。
```

### 4.3 Safetyを正式Runtime入力へ昇格

Safety placeholder allowを廃止し、Runtime Safety Decisionを正式入力にした。

設計変更:

- Safety Evaluation regular path
- Phase11 Safety Report
- Runtime Safety Decision Producer
- Missing / REVIEW_REQUIRED / BLOCKED / HALTをfail-closedで扱う
- Planning内部の擬似SafetySignalを廃止
- OrderPlan / Pending / ApprovalへSafety Contextを保持

思想:

```text
Safety evidenceがないならALLOWではない。
RuntimeはSafetyを生成しない。Safety Decisionを受け取り、保持し、伝播する。
```

### 4.4 Data Contractを正式化

Step1 Morning Acceptanceの停止により、Decision Chainだけでは足りないことが判明した。Candidate AIは接続されていたが、Feature ArtifactがFormal modelのSchemaを満たしていなかった。

設計変更:

- Runtime Data Contract Audit
- Runtime Data Contract Remediation Plan
- Canonical Feature Schema
- Candidate 13-column schema固定
- Opportunity prefix policy
- PM input contract
- Controlled schema validation
- Feature Consumer Readiness Artifact

思想:

```text
Feature Refreshの責務はArtifactを作ることではない。
Consumerが読めるArtifactであることを保証すること。
```

### 4.5 Runtime Data Readiness Gateを導入

AI ProducerやPlanningを実行する前に、必要Evidenceが揃っているかを判定するGateを追加した。

設計変更:

- `--job data_readiness`
- `--readiness-scope morning|sell_planning|submit|execution`
- Market / Feature / Candidate / Opportunity / PM / Current / Broker / Safety / Pending / Runtime EnvironmentをScope別に判定
- `READY / REVIEW_REQUIRED / HALT`
- Morning / SELL Planning前にGate接続

思想:

```text
Runtimeは実行してから壊れるのではなく、
入力が実行可能でない時点で止まる。
```

### 4.6 Pending Lifecycleを制御契約化

Pendingは一時ファイルではなく、State Machine上の重要Stateである。古いPendingが残ると二重Submitや日付混入が起きる。

設計変更:

- Pending lifecycle runner
- stale Pending検出
- consumed / expired / cancelled / empty stateの明示
- target_session_date判定
- policy / safety context保持

思想:

```text
Pendingは残ってよいArtifactではない。
Submitされるか、消費されるか、期限切れとして明示的に扱われるStateである。
```

### 4.7 Temporal / Freshness Contractを正式設計へ昇格

Phase15後半最大の転換点は、Runtime freshnessを単一の`as_of`から分解したことである。

設計変更:

- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- TemporalContext
- FreshnessStatus enum
- TemporalEvidence schema
- Market / Current / Feature / Pending / Safety freshness API
- Runtime-wide resolver
- Broker snapshot deterministic clock injection

思想:

```text
runtime_business_date
market_date
feature_date
position_state_as_of
valuation_as_of
generated_at
expires_at

は別概念である。
```

特にCurrentは以下に分離した。

```text
Position State: quantity / average_price / ownership
Valuation State: current_price / market_value / unrealized_pnl
Execution-Reconcile State: last_execution_date / last_reconciled_at
```

### 4.8 Evidence Producer Contractを追加

Data ReadinessやSafetyが必要とするEvidenceは、推測やReportからではなく正式Producerが出すべきである。

設計変更:

- Market / Quote Evidence Producer
- Current Temporal Schema Migration
- Current Valuation-Only / No-Fill Producer
- Report / NotificationへのEvidence summary伝播

思想:

```text
Evidenceが必要なら、RuntimeはEvidence Producerを持つ。
Artifactだけ存在しても、Consumerが読めなければPASSではない。
```

## 5. Runtime Evolution

Phase15最大の成果は、Runtime v2を以下の契約階層へ進化させたことである。

```text
Decision Contract
↓
Data Contract
↓
Runtime Contract
↓
Evidence Producer Contract
↓
Temporal Contract
```

### Decision Contract

AI / Policy / Safety / Broker / Operatorの判断主体を分離した。

- BUY Decision: Candidate AI -> Opportunity AI -> Morning
- SELL Decision: Position Management AI -> SELL Planning
- Safety Decision: Safety Evaluation -> Runtime Safety Decision
- Capital Deployment: explicit policy artifact
- Submit Guard: active policy / side-specific guard / evidence output

### Data Contract

Producer / Schema / Artifact / Consumerを一致させた。

- Candidate formal 13-column schema
- Opportunity prefix policy
- PM input contract
- Feature Consumer Readiness
- Controlled schema validation

### Runtime Contract

Runtimeの通常経路とState Machineを明確化した。

- Market Refresh
- Feature Refresh
- Data Readiness
- Morning
- Pending
- Approval
- Submit
- Broker boundary
- Execution
- Ledger
- Current
- Report
- Notification

### Evidence Producer Contract

Acceptanceで必要なEvidenceを正式Producer化した。

- Safety Report / Runtime Safety Decision
- Market / Quote Evidence
- Broker ReadOnly Snapshot
- Current Temporal Migration Artifact
- Current Valuation Refresh Artifact
- Data Readiness Artifact
- Pending Lifecycle Evidence

### Temporal Contract

日時・営業日・freshnessをRuntime共通契約へ統合した。

- `READY`
- `VALID_CARRYOVER`
- `DATA_NOT_YET_AVAILABLE`
- `STALE`
- `MISSING`
- `DATE_MISMATCH`
- `EXPIRED`
- `REVIEW_REQUIRED`
- `HALT`
- `NOT_REQUIRED`

## 6. 新しく追加されたArchitecture

Phase15で追加・成熟した主なArchitectureは以下である。

| Architecture | 役割 | 主要資料 / 実装 |
|---|---|---|
| Runtime Data Readiness | Morning / SELL Planning前にRuntime入力EvidenceをScope別判定する | `phase15_aq_runtime_data_readiness_gate.md`, `src/.../data_readiness.py` |
| Temporal Contract | Runtime全体の日時・freshness共通契約 | `runtime_temporal_freshness_contract.md`, `src/.../temporal/` |
| Pending Lifecycle | stale Pending / consumed / expired / emptyをStateとして扱う | `phase15_ar_pending_lifecycle_stale_pending_handling.md`, `src/.../pending/` |
| Current Temporal | CurrentをPosition State / Valuation Stateへ分離 | `phase15_ay_current_temporal_schema_migration.md`, `src/.../current_state/temporal.py` |
| Current Valuation-Only | 約定なしの日にvaluationだけを更新するNo-Fill Producer | `phase15_az_current_valuation_no_fill_producer.md`, `src/.../current_state/valuation.py` |
| Market Evidence | Market / Quote EvidenceをFeatureではなくRuntime evidenceとして生成 | `phase15_aw_market_quote_evidence_producer.md`, `src/.../market_refresh/evidence.py` |
| Safety Producer | Safety Evaluation -> Phase11 Report -> RuntimeSafetyDecision | `phase15_ac`, `phase15_ad`, `src/.../safety/` |
| BUY AI Runtime Connection | Candidate / Opportunity AIをMorning通常経路へ接続 | `phase15_ag`, `src/.../buy_ai/` |
| SELL AI Runtime Connection | Position Management AIをSELL Planning通常経路へ接続 | `phase15_af`, `src/.../position_management/` |
| Report / Notification Reason Propagation | Policy / Safety / Guard / Current理由をOperatorへ伝える | `phase15_r`, `src/.../report/`, `src/.../notification/` |
| Runtime Reality Rule | Demo差異をRuntime CoreではなくBroker Environment / Capabilityで扱う | `phase15_x_runtime_reality_rule_demo_production_boundary_contract.md` |

## 7. 現在のRuntime構成図

最新版のRuntime v2構成は以下である。

```text
Runtime CLI
↓
Temporal Context Resolver
↓
Market Refresh
  ├─ Market Evidence
  ├─ Quote Evidence
  ├─ Feature Artifacts
  └─ Feature Consumer Readiness
↓
Data Readiness Gate
  ├─ Policy
  ├─ Market / Feature readiness
  ├─ Current Temporal readiness
  ├─ Broker ReadOnly readiness
  ├─ Safety readiness
  ├─ Pending lifecycle readiness
  └─ Runtime environment readiness
↓
Safety Evaluation
↓
Runtime Safety Decision
↓
BUY Path
  ├─ Candidate AI
  ├─ Candidate Decision Artifact
  ├─ Opportunity AI
  ├─ Opportunity Ranking Artifact
  └─ Morning Planning
↓
SELL Path
  ├─ Position Management AI
  ├─ Position Decision Artifact
  └─ SELL Planning
↓
OrderPlan
↓
Pending Lifecycle
↓
Approval
↓
Submit Guard
  ├─ Policy hash consistency
  ├─ BUY guard
  ├─ SELL guard
  ├─ Broker available quantity evidence
  └─ Active Policy Manifest
↓
Broker Boundary
↓
Execution ReadOnly / Fill Evidence
↓
Ledger
↓
Current
  ├─ Current Temporal State
  └─ Current Valuation-Only / No-Fill Refresh
↓
Report
↓
Notification Payload
↓
Operator Review
```

重要な境界:

- CurrentはAsset SoTであり、Reason SoTではない。
- ReportはDerivedであり、Currentを書かない。
- Notificationはpayload-onlyであり、意思決定Sourceではない。
- Demo差異はRuntime CoreではなくBroker Environment / Broker Capability / Broker Evidenceで扱う。

## 8. 残課題

次チャットで扱うべき残課題を優先順位付きで整理する。

| Priority | 残課題 | 理由 | 推奨対応 |
|---|---|---|---|
| S | Phase15 Acceptance Step0を最新実装で再実施 | AZまでの実装後、実Runtime Evidenceの最新状態が未確認 | Step0 PreflightからSmall Batchで再開 |
| S | Market / Quote Evidence、Feature Consumer Readiness、Current Temporal / Valuation Evidenceの実Artifact確認 | Step1停止原因はData / Temporal evidence不足だった | `market_refresh`、必要なら`current_temporal_migration` dry-run、`current_valuation_refresh` dry-runをEvidenceとして確認 |
| S | Safety Evaluation / Safety Refreshのfresh evidence確認 | SafetyがREVIEW_REQUIREDならMorningへ進めない | Safety ReportとRuntime Safety Decisionを再生成・レビュー |
| S | Pending Lifecycle状態の確認 | 古いPending残留はSubmit/Planningを壊す | `pending_lifecycle` evidenceでEMPTY / EXPIRED / CANCELLEDを確認 |
| A | Data Readiness GateのStep0判定 | Acceptance再開の正門 | `data_readiness --readiness-scope morning` をレビュー |
| A | Step1 Morning Acceptance Retry | Candidate / Opportunity / Policy / Safety / Pending / Approval evidenceが通るか確認 | Step0 PASS後にのみ実施 |
| A | Broker ReadOnly freshness確認 | Submit/Sell Acceptanceにはfresh broker evidenceが必須 | Submit Review前に確認 |
| B | Operator Review apply path | REVIEW_REQUIREDの説明はあるがapply pathは未実装 | Phase16以降または後続Phaseで設計 |
| B | Recovery apply path | rerun/retryの自動State遷移は未完成 | Controlled manual rerunで運用、後続で実装 |
| B | Audit aggregator as control gate | Auditは証跡寄りで制御Gateではない | Acceptance gateにするなら別途設計 |
| C | Real notification delivery | Phase15はpayload-only | Production前にqueue/send/delivery ledgerを実装 |
| C | Production Broker Write / launchd automation | Demo Acceptanceとは別 | Production readiness Phaseで扱う |

## 9. Phase15再開位置

次チャットはPhase15-AZの続きとして、以下から開始するのが正しい。

```text
Phase15 Runtime Acceptance Step0 Retry after AZ
```

理由:

- Phase15-AJでStep1 Morning Acceptanceは一度実行されたが、Feature Schema / Safety / Pending / Temporal freshnessにより停止した。
- Phase15-AN〜AZで、それらの根本原因に対する設計・実装が追加された。
- ただしAZ後に実Runtime EvidenceでStep0を再判定していない。
- よってStep1を直接再実行してはいけない。

推奨再開シーケンス:

```text
1. Read Priority S/A docs
2. Confirm current business date / target acceptance date
3. Step0 Preflight Evidence Review
4. If gaps exist, run only the minimum producer job needed
5. Re-run Data Readiness
6. Only if Step0 READY, proceed to Step1 Morning Review
```

Small Batch原則:

```text
Operatorへ一度に大量コマンドを要求しない。
1〜2コマンドずつEvidenceを見て進む。
```

## 10. Acceptance現在位置

Phase15 Acceptanceの現在地は以下である。

| Step | Status | Notes |
|---|---|---|
| Step0 Preflight Evidence | 一度実施、GAPS_FOUND。その後AI/Policy/Safety接続でAI RetryはREADY_FOR_STEP0_RETRY。ただしAZ後の最新Evidenceでは未再実施 | 次チャットはここから再開 |
| Step1 Morning Review | 一度実行、`STEP1_MORNING_ACCEPTANCE_GAPS_FOUND` | Safety REVIEW_REQUIRED、Candidate feature schema mismatch、Pending staleで停止 |
| Step2 Pending / Approval Review | 未完了 | Step1がPending / Approvalまで到達していない |
| Step3 Submit Guard Review | 未実施 | Submit禁止のまま |
| Step4 REVIEW_REQUIRED Review | 部分的に設計・Regressionあり、Acceptanceとしては未完了 | Stepwise evidenceが必要 |
| Step5 HALT Review | 設計・Regressionあり、Acceptanceとしては未完了 | Stepwise evidenceが必要 |
| Step6 Execution / Current Review | Static / regressionあり、Acceptanceとしては未完了 | Demo evidenceが必要 |
| Step7 Report / Notification Review | Reason propagation実装済み、Acceptanceとしては未完了 | Stepwise evidenceが必要 |
| Step8 Full Demo Rehearsal | 未実施 | Step0-7 PASS後のみ |

現在のGate判定:

```text
READY_FOR_ACCEPTANCE_STEP0_RETRY_AFTER_AZ
```

これは以下を意味しない。

- Phase15 Complete
- Full Runtime PASS
- Submit許可
- Broker Write許可
- Demo注文許可
- Production注文許可
- Notification real send許可
- launchd再開許可

## 11. 読むべき資料

### Priority S

最初に読む資料。Runtime v2の正式設計Source of Truth。

```text
docs/02_architecture/runtime_architecture_v2.md
docs/02_architecture/runtime_temporal_freshness_contract.md
```

### Priority A

次に読む資料。今回作成した引き継ぎ本文。

```text
docs/phase_reports/phase15_final_summary_and_runtime_acceptance_handoff.md
```

### Priority B

Phase15の転換点を理解するための資料。

```text
docs/phase_reports/phase15_au_runtime_temporal_freshness_contract_design.md
docs/phase_reports/phase14_final_summary_and_phase15_handoff.md
docs/phase_reports/phase14_e55_runtime_architecture_v2_design_contract_amendment.md
docs/phase_reports/phase13_final_audit_and_phase14_handoff.md
```

加えて、次チャットでStep0を再開するなら以下も読む。

```text
docs/phase_reports/phase15_at_operational_evidence_refresh_sequence.md
docs/phase_reports/phase15_aq_runtime_data_readiness_gate.md
docs/phase_reports/phase15_an_canonical_feature_schema_feature_refresh_consumer_readiness.md
docs/phase_reports/phase15_ay_current_temporal_schema_migration.md
docs/phase_reports/phase15_az_current_valuation_no_fill_producer.md
```

### Priority C

必要になったら読むPhase14詳細資料。

```text
phase14_e54
phase14_e53
phase14_e52
phase14_e51
phase14_e50
phase14_e47
phase14_e46
phase14_e33
phase14_e27
phase14_d23
phase14_d25
```

## 12. 次チャット開始時に読む順番

次チャットでは、以下の順番で読むこと。

1. `docs/phase_reports/phase15_final_summary_and_runtime_acceptance_handoff.md`
2. `docs/02_architecture/runtime_architecture_v2.md`
3. `docs/02_architecture/runtime_temporal_freshness_contract.md`
4. `docs/phase_reports/phase15_z_runtime_acceptance_kickoff.md`
5. `docs/phase_reports/phase15_aj_step1_morning_acceptance_review.md`
6. `docs/phase_reports/phase15_ak_step1_blocker_root_cause_audit.md`
7. `docs/phase_reports/phase15_al_runtime_data_contract_audit.md`
8. `docs/phase_reports/phase15_an_canonical_feature_schema_feature_refresh_consumer_readiness.md`
9. `docs/phase_reports/phase15_aq_runtime_data_readiness_gate.md`
10. `docs/phase_reports/phase15_au_runtime_temporal_freshness_contract_design.md`
11. `docs/phase_reports/phase15_av_runtime_temporal_contract_foundation.md`
12. `docs/phase_reports/phase15_aw_market_quote_evidence_producer.md`
13. `docs/phase_reports/phase15_ay_current_temporal_schema_migration.md`
14. `docs/phase_reports/phase15_az_current_valuation_no_fill_producer.md`
15. `docs/phase_reports/phase15_at_operational_evidence_refresh_sequence.md`

その後、実Runtime EvidenceをSmall Batchで確認する。

## 13. 次チャットへの実務メモ

次チャットでいきなりMorningを実行しないこと。

まず確認すべきは以下である。

```text
Policy
Market / Quote Evidence
Feature Consumer Readiness
Current Temporal State
Current Valuation State
Broker ReadOnly Snapshot
Safety Report
Runtime Safety Decision
Pending Lifecycle
Data Readiness
```

Step0再開時の考え方:

- EvidenceがなければPASSしない。
- stale evidenceを日付書き換えで通さない。
- Currentを直接編集しない。
- Demo制約をRuntime Core仕様へ混ぜない。
- Notification payloadだけでOperator判断しない。
- Report generatedだけでReport PASSにしない。
- Broker AcceptedだけでRuntime PASSにしない。
- fake adapter / fixture pathをFull Runtime PASSにしない。

## 14. Phase15で生まれた新しい設計思想

Phase15以前のRuntime理解は、概ね以下の粒度だった。

```text
Runtime
↓
Morning
↓
Submit
↓
Execution
```

しかしPhase15を通じて、Runtimeは単なる実行エンジンではなく、以下5層の契約で構成される制御システムであることが判明した。

```text
Decision Contract
↓
Data Contract
↓
Runtime Contract
↓
Evidence Producer Contract
↓
Temporal Contract
```

### 14.1 Decision Contract

問題:

RuntimeがAI判断を代替していた。Candidate / Opportunity / Position Management AIは存在していたが、通常Runtime経路のProducer / Artifact / Consumerとして閉じていなかった。結果として、FeatureやCurrentからRuntime内部で判断らしきものを作る構造が残っていた。

改善:

- Candidate AI -> Candidate Decision Artifact -> Opportunity AI
- Opportunity AI -> Ranking Artifact -> Morning Planning
- Position Management AI -> Position Decision Artifact -> SELL Planning
- Safety Evaluation -> Safety Report -> Runtime Safety Decision
- Capital Deployment Policy -> Morning / Pending / Approval / Submit

今後の使い方:

Runtimeが何かを判断しているように見えたら、必ず「そのDecision Producerは誰か」「Artifactはどこか」「Consumerは誰か」を確認する。Producer / Artifact / Consumerが閉じていない判断は、Runtime正式判断として扱わない。

### 14.2 Data Contract

問題:

Decision Chainは接続されても、Consumerが読めるData Schemaが保証されていなかった。Phase15-AJではCandidate AIが正式Feature列を読めず、MorningがHALTした。これはAI接続問題ではなく、Data Contract問題だった。

改善:

- Candidate formal 13-column schemaを固定
- Opportunity prefix policyを明示
- PM input contractを定義
- Feature Consumer Readinessを追加
- Schema mismatchをhidden defaultやNaN補完で進めない

今後の使い方:

ArtifactがあるだけではPASSにしない。必ず「Consumer Readyか」を見る。Feature Refresh、Market Evidence、Broker Snapshot、Current、Safety、PendingはすべてProducer / Schema / Artifact / Consumerで確認する。

### 14.3 Runtime Contract

問題:

Runtimeが「どの順序で、どのStateを、どの証跡で進めるか」が曖昧だった。Component PASSをFlow PASSと誤認しやすく、Pending残留、Approval混入、ManifestだけPASS、ReportだけPASSの危険があった。

改善:

- Runtime State Machineを定義
- Pending Lifecycleを契約化
- Approval / Pending / Submit / Broker / Execution / Currentの境界を整理
- Report / NotificationはDerived evidenceとしてScope分離
- Stepwise Acceptanceを定義

今後の使い方:

Runtime Acceptanceでは「そのComponentが動いたか」ではなく、「前Stateから次Stateへ、設計どおりEvidence付きで遷移したか」を確認する。Stepを飛ばさない。

### 14.4 Evidence Producer Contract

問題:

SafetyやData Readinessが必要とするEvidenceが、正式Producerから出ていなかった。Market / Quote Evidence、Broker freshness、Current valuation freshnessなどが、古いArtifactや推測に依存しやすかった。

改善:

- Safety Producer
- Market / Quote Evidence Producer
- Current Temporal Migration Artifact
- Current Valuation-Only / No-Fill Producer
- Data Readiness Artifact
- Pending Lifecycle Artifact

今後の使い方:

Acceptanceで必要なEvidenceがあるなら、正式Producerを持つ。ReportやManifestの表示だけをEvidence Producerの代わりにしない。Evidence不足ならPASSではなくREVIEW_REQUIREDで止める。

### 14.5 Temporal Contract

問題:

`as_of == business_date` のような単純判定では、非営業日、データ配信前、約定なしの日、valuation-only更新、broker snapshot鮮度を正しく扱えなかった。CurrentのPosition StateとValuation Stateも混同されていた。

改善:

- Runtime Temporal / Freshness Contractを正式設計化
- TemporalContext / FreshnessStatus / TemporalEvidenceを実装
- CurrentをPosition State / Valuation State / Execution-Reconcile Stateへ分離
- Market date / latest expected / latest availableを分離
- No-fill valuation-only Producerを追加

今後の使い方:

全Componentは共通Temporal Contractを使う。各Componentが独自に日付判定を作らない。Freshnessは `READY / VALID_CARRYOVER / DATA_NOT_YET_AVAILABLE / STALE / MISSING / DATE_MISMATCH / EXPIRED / REVIEW_REQUIRED / HALT` で表現する。

## 15. Production前に見つかった重大設計問題

Phase15でProduction前に発見できた重大設計問題を以下に整理する。

| 問題 | なぜ危険だったか | どう直したか |
|---|---|---|
| RuntimeがAI判断を代行していた | Runtimeが投資判断を作ると、AIの責務・学習・説明責任が崩れる | Candidate / Opportunity / Position Management AIを正式Producerとして接続 |
| BUY / SELL Decision Chain未接続 | BUY選定やSELL判断が通常経路で証跡化されず、Componentだけ存在する状態になる | BUY AI chain、SELL PM AI chainをArtifact経由でMorning / SELL Planningへ接続 |
| Safety Producer欠落 | Evidence不足でもPlanning内placeholder allowが混入する危険 | Safety Evaluation -> Phase11 Report -> Runtime Safety Decisionへ整理し、placeholder allowを排除 |
| Data Contract欠落 | ArtifactはあるがConsumerが読めない、または古いSchemaを読む危険 | Canonical Feature Schema、Consumer Readiness、controlled schema validationを追加 |
| Feature Schema mismatch | Candidate AI正式モデルが必要な列をFeature Refreshが保証していなかった | Candidate 13列、rename policy、Opportunity prefix policyを固定 |
| Pending Lifecycle欠落 | stale Pending残留、二重Submit、target date混入が起きる | Pending Lifecycle runnerとstate contractを追加 |
| Runtime Data Readiness欠落 | Morning / SELL Planningが入力不備のまま走り、途中HALTやhidden fallbackになり得た | `data_readiness` jobとscope別Gateを追加 |
| Producerという概念の欠落 | 必要Evidenceがどこから来るか曖昧で、Report / Manifest / fixtureを証拠と誤認しやすかった | Market Evidence、Safety Decision、Current valuationなどをProducer contract化 |
| Current Freshness設計の誤り | 約定がない日にCurrent全体がstale扱いされる、または日付だけ書き換える誘惑があった | Current Temporal SchemaでPosition StateとValuation Stateを分離 |
| Temporal Contract欠落 | 営業日、配信日、生成時刻、有効期限、broker snapshot鮮度がComponentごとにばらばらだった | Runtime Temporal / Freshness ContractとTemporal Foundationを追加 |

これらはProduction後に見つかっていれば、誤発注、売却不能、過剰な資金未投入、Safety bypass、Operator誤判断につながり得た。Phase15で止まったこと自体が重要な安全成果である。

## 16. Phase15で得られた設計上の教訓

Phase15最大の成果は、バグ修正ではなくRuntime設計思想そのものが成熟したことである。Phase16以降でも以下を守る。

- RuntimeはAI判断を作らない。
- RuntimeはPolicyを発明しない。
- Producer / Artifact / Consumerを必ず対にする。
- Data Contractを必ず定義する。
- Artifact existenceをConsumer Readyと誤認しない。
- RuntimeはEvidenceだけで判断する。
- SafetyはEvidence不足なら止まる。
- REVIEW_REQUIREDは失敗ではなく、安全な停止状態である。
- Component PASSをFlow PASSと呼ばない。
- Tests PASSだけでRuntime PASSにしない。
- Broker AcceptedだけでRuntime PASSにしない。
- Report generatedだけでReport semantic PASSにしない。
- Payload generatedだけでNotification PASSにしない。
- Demo専用Runtimeを作らない。
- Runtime CoreはProduction基準で設計する。
- Demo差異はBroker Environment / Capability / Evidenceとして扱う。
- Currentを直接編集してfreshnessを満たさない。
- CurrentはAsset SoT、ReportはDerived、NotificationはOperator向け要約である。
- Temporal Contractを全Componentで共有する。
- `as_of` ひとつでfreshnessを判定しない。
- PendingはStateであり、放置可能な一時ファイルではない。
- Evidence不足時はOperatorへ最小限の確認コマンドだけ提示する。
- 新しい設計変更は正式設計資料へ反映してから実装する。

## 17. なぜPhase15は長期化したのか

Phase15が長期化した理由は、単に実装量が多かったからではない。

レビューを進めるたびに、より上位の設計レイヤーの問題が見つかったためである。

最初はSubmit Guard Regression、つまり局所バグに見えた。しかし調べると、Runtime hidden policy、BUY / SELL Guard未分離、Active Policy Manifest不足が見つかった。

次にDecision Chainを確認すると、RuntimeがAI判断を代替していた。そこでCandidate / Opportunity / Position Management AIを正式接続した。

しかしAcceptance Step1でMorningを実行すると、今度はCandidate AIがFeature Schemaを読めないことが判明した。これはDecisionの問題ではなくData Contractの問題だった。

Data Contractを直すと、Feature RefreshがArtifact生成しか保証しておらず、Consumer Readyを保証していないことが判明した。

Data Readinessを導入すると、Current freshnessやMarket / Quote EvidenceのProducerが不足していることが見えた。

Current freshnessを見直すと、`as_of == business_date` では約定なしの日や非営業日を扱えないことが判明した。

最終的に、Temporal ContractというRuntime全体の土台が必要になった。

つまりPhase15は以下のように深掘りされた。

```text
Submit bug
↓
Hidden Policy
↓
Decision Chain
↓
Data Contract
↓
Producer Contract
↓
Temporal Contract
```

これは遠回りではなく、Production前にRuntimeの土台を発見し直したプロセスだった。

## 18. 次チャット開始時の心構え

次チャットの目的は、新しいRuntimeを作ることではない。

目的は以下である。

```text
ここまで整備したRuntimeをAcceptanceで証明すること
```

優先するもの:

- Evidence
- Acceptance
- Stepwise review
- Runtime operation readiness
- Operatorが理解できるReport / Notification
- Safety stop behavior
- State / Temporal consistency

優先しないもの:

- 追加機能
- 新しいbypass
- Demo専用Runtime
- Phase専用例外
- 実装を増やしてAcceptanceを先送りすること

新しい設計変更が必要になった場合は、まず正式設計資料へ反映する。

最低限、以下へ反映する。

```text
docs/02_architecture/runtime_architecture_v2.md
docs/02_architecture/runtime_temporal_freshness_contract.md
該当phase_reports
```

次チャットでは、Phase15-AZ後の最新Runtimeに対して、Step0からEvidenceを取り直す。Step0がREADYになるまでStep1 Morningへ進まない。

## 19. Final Handoff Judgment

Phase15は、Runtime v2を「動く部品の集合」から「契約・証跡・State・Temporal freshnessで制御される中枢」へ進化させた。

最大成果は、以下の設計成熟である。

```text
Decision Contract
↓
Data Contract
↓
Runtime Contract
↓
Evidence Producer Contract
↓
Temporal Contract
```

次に必要なのは、実装追加ではなく、最新RuntimeでStep0からAcceptance Evidenceを取り直すことである。

```text
PHASE15_FINAL_SUMMARY_RUNTIME_ACCEPTANCE_HANDOFF_CREATED
READY_FOR_PHASE15_ACCEPTANCE_STEP0_RETRY_AFTER_AZ
```
