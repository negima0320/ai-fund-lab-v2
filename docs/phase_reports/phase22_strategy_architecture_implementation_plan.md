# Phase22 Strategy Architecture Implementation Plan

## 1. Executive Summary

Phase22は、Phase21-Dで定義したStrategy Architecture v1をProduction / Demo / Historical共通Contractとして段階実装するフェーズである。

Phase22では一括置換を禁止し、原則として1タスク1責務変更で進める。各タスクは既存Runtime / Safety / Authority / Lifecycle / Pending Composition / ADD Consumerを壊さず、必要なArtifact AcceptanceとRollbackを持つ。

上位SoT:

```text
docs/02_architecture/strategy_architecture_v1.md
```

## 2. Phase22 Objective

目的:

- Market Context Artifactを導入する
- Corporate Event Artifactを導入する
- Candidate / Opportunity compatibilityをPortfolio Construction前に確認する
- Portfolio Policy Artifactを導入する
- Capital Deploymentの責務をStrategy target / Safety hard limit / Execution feasibilityへ分離する
- Dynamic Position Count、Target Cash Ratio、Position Sizingを段階的に導入する
- PMへMarket ContextとPortfolio Policyを接続する
- Target Portfolio / Portfolio Constructionを導入候補として実装する
- Runtime Planning Execution Intent bridgeをTarget Portfolio / Allocation後に接続する
- Phase23 Controlled Validationへ進めるためのEvidenceとRegressionを整える

Migration詳細SoT:

```text
docs/phase_reports/phase21_gb_strategy_migration_architecture_design.md
```

Implementation Governance SoT:

```text
docs/phase_reports/phase21_gc_implementation_governance_and_phase22_entry_gate.md
```

## 3. Non-goals

Phase22各タスクで禁止する共通事項:

- Historical専用Strategy分岐
- 特定Run ID専用logic
- Test PASS目的の例外
- Historical Run損益、Backtest結果、Paper Ledger、Portfolio PnLのRuntime / Training / Calibration利用
- PM threshold、Opportunity ranking、Candidate rankingの同時変更
- Returnだけでの採用
- hash check回避

## 4. Task Breakdown

### Phase22-A Market Context Artifact Foundation

| 項目 | 内容 |
|---|---|
| Objective | Market Context Artifact schemaとread-only生成基盤を作る |
| Why | Portfolio PolicyとPMが市場状態を共通Authorityで参照するため |
| Dependencies | Phase21-D |
| Inputs | J-Quants PIT価格、出来高、Listed Issues、Trading Calendar、Feature artifacts |
| Outputs | `Market Context Artifact` |
| Artifacts | `strategy_market_context.v1` |
| Authority | J-Quants PIT + source hashes |
| Production code scope | 新規Market Context producerのみ |
| Config scope | 新規schema / no Strategy value change |
| Prohibited | PM threshold変更、BUY/SELL判断変更、Runtime fallback |
| Data provenance | J-Quants PIT only |
| PIT requirements | business_date / feature_date / source_hash必須 |
| Failure modes | missing source -> REVIEW_REQUIRED、hash mismatch -> BLOCK |
| Unit tests | schema、PIT、missing source、hash validation |
| Regression tests | Runtime existing suite、Phase21-B tests |
| Artifact refresh | Production sourceをAccepted memberにする場合必要 |
| User-run validation | 1BDまたは5BDはユーザー実行。Codexは長時間Run不可 |
| Acceptance | Artifact schema PASS、no leakage、common path |
| Reject | future data、fallback、Runtime判断混入 |
| Rollback | Artifact consumerを未接続に戻す |
| Next gate | Portfolio PolicyがMarket Contextを読める |

### Phase22-AA Corporate Event Artifact Foundation

| 項目 | 内容 |
|---|---|
| Objective | Corporate Event Artifact schemaとread-only生成基盤を作る |
| Why | 上場状態、上場廃止予定、決算予定、業績修正、配当修正等をStrategy共通PIT Fact Authorityにするため |
| Dependencies | Phase21-FA / Phase21-GB |
| Inputs | J-Quants PIT Listed Issues、earnings schedule source候補、corporate action source候補、Trading Calendar |
| Outputs | `Corporate Event Artifact` |
| Artifacts | `corporate_event_authority.v1` |
| Authority | Corporate Event Fact Authority |
| Production code scope | 新規Corporate Event producerのみ |
| Config scope | schemaのみ。threshold変更禁止 |
| Prohibited | BUY/SELL判断、PM action追加、Runtime fallback |
| Data provenance | J-Quants PIT / accepted source candidates |
| PIT requirements | as_of、business_date、source_hash、coverage_status必須 |
| Failure modes | source missing -> REVIEW_REQUIRED、coverage不足 -> REVIEW_REQUIRED、hash mismatch -> BLOCK、final trading date exceeded -> BLOCK |
| Unit tests | schema、PIT、missing source、coverage、hash validation |
| Regression tests | no Runtime behavior change、Phase21-B tests |
| Artifact refresh | Production sourceをAccepted memberにする場合必要 |
| User-run validation | source-only段階では不要。Runtime switch後はユーザー実行 |
| Acceptance | Fact Authority schema PASS、no leakage、common path |
| Reject | future event leakage、missingをsafe扱い、Runtime判断混入 |
| Rollback | Artifact consumerを未接続に戻す |
| Next gate | Candidate / Opportunity compatibilityがCorporate Event factを参照可能 |

### Phase22-B Candidate / Opportunity Compatibility and Artifact Dependency Readiness

| 項目 | 内容 |
|---|---|
| Objective | Candidate / OpportunityがMarket Context / Corporate Event導入後もProducer-firstで接続可能か確認する |
| Why | Portfolio Construction前に上流AI artifact dependencyを固定するため |
| Dependencies | Phase22-A / Phase22-AA |
| Inputs | Candidate Artifact、Opportunity Artifact、Market Context Artifact、Corporate Event Artifact |
| Outputs | compatibility evidence |
| Artifacts | Candidate / Opportunity compatibility evidence |
| Authority | Accepted AI Generation + PIT source authority |
| Production code scope | compatibility / schema only |
| Config scope | model/threshold変更禁止 |
| Prohibited | Candidate/Opportunity ranking変更、training、calibration |
| Data provenance | J-Quants PIT + accepted generation |
| PIT requirements | feature_date / source hash consistency |
| Failure modes | missing dependency -> REVIEW_REQUIRED、schema/hash mismatch -> BLOCK |
| Unit tests | schema compatibility、missing dependency |
| Regression tests | Candidate/Opportunity existing behavior parity |
| Artifact refresh | source pathがaccepted memberになる場合必要 |
| User-run validation | なし。Runtime switch前 |
| Acceptance | old behavior維持、new refs trace可能 |
| Reject | Consumer先行接続、ranking drift |
| Rollback | refs未接続状態へ戻す |
| Next gate | Portfolio Policy producer |

### Phase22-C Portfolio Policy Artifact Foundation

| 項目 | 内容 |
|---|---|
| Objective | Portfolio Policy Artifactを作成する |
| Why | target cash、exposure、position count、BUY/ADD許可をPM判断から分離するため |
| Dependencies | Phase22-A / Phase22-AA / Phase22-B |
| Inputs | Market Context、Corporate Event aggregate risk、Opportunity breadth、Current summary、cash/exposure |
| Outputs | `Portfolio Policy Artifact` |
| Artifacts | `portfolio_policy.v1` |
| Authority | Market Context + Current + J-Quants-derived opportunity evidence |
| Production code scope | 新規Policy producer |
| Config scope | schemaのみ。20%は初期baseline候補として明示 |
| Prohibited | max_positions変更、max_exposure変更、cash_buffer変更 |
| Data provenance | J-Quants PIT + Current runtime authority |
| PIT requirements | source feature date一致 |
| Failure modes | invalid target weights -> BLOCK、low confidence -> defensive/review |
| Unit tests | schema、target range、reason_codes |
| Regression tests | PM artifact authority、Phase21-B |
| Artifact refresh | Production accepted source化時に必要 |
| User-run validation | user 5BD before enablement |
| Acceptance | Policy artifact valid、Runtime未変更 |
| Reject | Safety hard limitとの混同 |
| Rollback | Policy consumer未接続 |
| Next gate | PM refs and Portfolio ConstructionがPolicy targetを読める |

### Phase22-F Capital Deployment Responsibility Refactor

| 項目 | 内容 |
|---|---|
| Objective | Strategy target、Safety hard limit、Execution feasibilityを分離する |
| Why | 現行固定Policyがtargetとhard limitを兼ねているため |
| Dependencies | Phase22-E |
| Inputs | Target Portfolio / Strategy Intent、Portfolio Policy、Current、cash、Pending、Safety |
| Outputs | Capital Allocation evidence |
| Artifacts | `capital_allocation.v2`候補 |
| Authority | Portfolio Policy + Capital Deployment Policy + Safety |
| Production code scope | Capital Deployment layerのみ |
| Config scope | 既存値変更禁止。fields追加はreview |
| Prohibited | target_investment_ratio、max_exposure、max_positions変更 |
| Data provenance | Current / Policy / Safety |
| PIT requirements | business_date consistency |
| Failure modes | policy missing -> BLOCK、conflict -> REVIEW/BLOCK |
| Unit tests | responsibility separation、missing policy、conflict |
| Regression tests | Morning/Sell/Submit/Phase21-B |
| Artifact refresh | source変更時必要 |
| User-run validation | user 5BD after gate |
| Acceptance | 既存behavior互換、evidence追加 |
| Reject | implicit fallback、hard limit弱体化 |
| Rollback | v1 policy pathへ戻せる |
| Next gate | Runtime Planning Execution Intent Bridge |

### Phase22-H Dynamic Position Count

| 項目 | 内容 |
|---|---|
| Objective | minimum / target / maximum positionsをPortfolio Policy ownerで導入 |
| Why | 5銘柄固定をquality / opportunity breadthに合わせるため |
| Dependencies | Phase22-C / Phase22-F |
| Inputs | qualified opportunity count、score distribution、sector breadth、cash/exposure |
| Outputs | dynamic position count target |
| Artifacts | Portfolio Policy fields |
| Authority | Portfolio Policy |
| Production code scope | Policy / Capital consumer |
| Config scope | hard cap値変更禁止 |
| Prohibited | 枠埋め低品質BUY |
| Data provenance | J-Quants PIT opportunity evidence |
| PIT requirements | same feature date |
| Failure modes | no candidates -> PASS no BUY、too many -> selected/rejected evidence |
| Unit tests | zero/two/many candidate cases |
| Regression tests | BUY planning、ADD consumer |
| Artifact refresh | source変更時必要 |
| User-run validation | user 5BD/20BD as required |
| Acceptance | target count reason_codesあり |
| Reject | Runtimeがcount決定 |
| Rollback | fixed max policy read-only fallbackではなくprevious accepted artifact |
| Next gate | Target Cash Ratio |

### Phase22-I Dynamic Target Cash Ratio / Exposure Target

| 項目 | 内容 |
|---|---|
| Objective | target cash ratioとtarget exposure ratioをPortfolio Policyで導入 |
| Why | 20% cashをstandard baselineとしてdynamic target化するため |
| Dependencies | Phase22-H |
| Inputs | Market Context、confidence、qualified opportunity breadth、Safety |
| Outputs | target cash/exposure |
| Artifacts | Portfolio Policy fields |
| Authority | Portfolio Policy; Safety floorはSafety |
| Production code scope | Policy / Capital consumer |
| Config scope | 既存cash_buffer変更禁止 |
| Prohibited | 20%をhard floor化 |
| Data provenance | J-Quants PIT + Current |
| PIT requirements | source dates一致 |
| Failure modes | low confidence -> defensive target、Safety conflict -> Safety wins |
| Unit tests | bull/bear/range fixture |
| Regression tests | Capital / Submit guard |
| Artifact refresh | source変更時必要 |
| User-run validation | user 5BD before enabling |
| Acceptance | targetとhard floor分離 |
| Reject | Safety混同 |
| Rollback | previous accepted Policy |
| Next gate | Position Sizing |

### Phase22-J Position Sizing Foundation

| 項目 | 内容 |
|---|---|
| Objective | target weightからnotional候補への基盤を作る |
| Why | Equal/weighted/hybridをPhase23で比較可能にするため |
| Dependencies | Phase22-I |
| Inputs | Portfolio Policy、Opportunity score、volatility、liquidity、sector risk |
| Outputs | target weight / notional evidence |
| Artifacts | Capital Allocation / Portfolio Construction evidence |
| Authority | Portfolio Policy + Capital Deployment |
| Production code scope | sizing module isolated |
| Config scope | formula defaultはaccepted artifact管理 |
| Prohibited | Historical PnL weighting |
| Data provenance | J-Quants PIT only |
| PIT requirements | volatility window source recorded |
| Failure modes | notional too small -> rejection、weight sum invalid -> BLOCK |
| Unit tests | equal/confidence/lot viability fixtures |
| Regression tests | Submit quantity guard |
| Artifact refresh | source/formula change時必要 |
| User-run validation | user controlled run for Phase23 |
| Acceptance | formula evidence and rollback |
| Reject | specific-run optimized sizing |
| Rollback | previous sizing artifact |
| Next gate | Regime/Event-aware decisions |

### Phase22-D Position Management Refs and Compatibility

| 項目 | 内容 |
|---|---|
| Objective | PM decisionsへMarket Context / Corporate Event / Portfolio Policy refsを接続 |
| Why | HOLD/ADD/REDUCE/EXIT reasonを市場、企業イベント、Portfolio状態と接続するため |
| Dependencies | Phase22-C |
| Inputs | PM features、Market Context、Corporate Event、Portfolio Policy、Current |
| Outputs | PM decisions with context refs |
| Artifacts | PM Decisions Artifact |
| Authority | POSITION_MANAGEMENT_POLICY_SET + Strategy artifacts |
| Production code scope | PM adapter/producer |
| Config scope | PM thresholds変更禁止 |
| Prohibited | PM score/threshold変更 |
| Data provenance | J-Quants PIT + Current |
| PIT requirements | feature_date alignment |
| Failure modes | context source missing -> REVIEW_REQUIRED、invalid/hash mismatch -> BLOCK、low confidence -> valid artifactのみneutral/defensive可能 |
| Unit tests | context lineage, missing context |
| Regression tests | PM adapter equivalence adjusted for trace-only |
| Artifact refresh | PM Runtime Adapter Acceptance必須 |
| User-run validation | user 5BD |
| Acceptance | PM HALTなし、lineageあり |
| Reject | behavior drift without acceptance |
| Rollback | previous accepted PM set |
| Next gate | Portfolio Construction |

### Phase22-K Regime/Event-aware HOLD / ADD / REDUCE / EXIT

| 項目 | 内容 |
|---|---|
| Objective | Market ContextとCorporate EventをPM decision biasへ段階適用 |
| Why | regimeと企業イベントでHOLD/ADD/REDUCE/EXIT postureをreason化するため |
| Dependencies | Phase22-J |
| Inputs | Market Context、Corporate Event、Portfolio Policy、PM features |
| Outputs | regime/event-aware PM decisions |
| Artifacts | PM Decisions Artifact |
| Authority | PM Policy + Market Context + Corporate Event facts |
| Production code scope | PM decision policy |
| Config scope | threshold変更は単独task化 |
| Prohibited | multiple regime/event + sizing simultaneous change |
| Data provenance | J-Quants PIT |
| PIT requirements | no future regime |
| Failure modes | conflicting context -> REVIEW |
| Unit tests | regime fixtures |
| Regression tests | HOLD/ADD/REDUCE/EXIT distribution sanity |
| Artifact refresh | PM accepted set refresh |
| User-run validation | user multi-window |
| Acceptance | reason_codes, no leakage |
| Reject | future bull/bear labels |
| Rollback | previous PM policy |
| Next gate | Benchmark/Sector |

### Phase22-E Target Portfolio and Portfolio Construction

| 項目 | 内容 |
|---|---|
| Objective | Target Portfolio Artifactと差分intent生成を導入 |
| Why | BUY/ADD/REDUCE/EXITをPortfolio全体で整合させるため |
| Dependencies | Phase22-D |
| Inputs | Portfolio Policy、rankings、PM decisions、Corporate Event facts、Current、cash、sector、Pending |
| Outputs | Target portfolio、Strategy intents |
| Artifacts | `target_portfolio.v1`, `strategy_intent.v1` |
| Authority | Portfolio Construction |
| Production code scope | new construction module + planning consumers |
| Config scope | no hard value change |
| Prohibited | direct Submit、Runtime ranking変更 |
| Data provenance | J-Quants PIT + Current |
| PIT requirements | all source refs/hash |
| Failure modes | weights > 100 -> BLOCK、conflict -> REVIEW |
| Unit tests | target diff, BUY/ADD/REDUCE/EXIT mapping |
| Regression tests | Pending composition, duplicate guard |
| Artifact refresh | new source artifacts acceptance |
| User-run validation | user 5BD/20BD |
| Acceptance | action-based互換、Runtime PlanningがExecution Intent ownerであること、canonical pending維持 |
| Reject | multiple pending authorities |
| Rollback | action-based path retained until accepted cutover |
| Next gate | Capital Deployment |

### Phase22-G Runtime Planning Execution Intent Bridge

| 項目 | 内容 |
|---|---|
| Objective | Allocation ArtifactをRuntime Execution Intent / Pending Candidateへ変換するbridgeを設計・実装する |
| Why | Portfolio Construction / Capital DeploymentとRuntime Pending/Submit境界を分離するため |
| Dependencies | Phase22-F |
| Inputs | Allocation Artifact、Current、Pending、order condition authority |
| Outputs | Runtime Execution Intent、Pending Candidate |
| Artifacts | `execution_intent.v1` |
| Authority | Runtime Planning / Pending Authority |
| Production code scope | Runtime Planning bridgeのみ |
| Config scope | no hard value change |
| Prohibited | Ranking変更、PM判断変更、Target Weight再計算 |
| Data provenance | Allocation hash + Current/Pending refs |
| PIT requirements | business_date consistency |
| Failure modes | missing allocation -> REVIEW_REQUIRED、invalid/hash mismatch -> BLOCK |
| Unit tests | empty allocation、pending candidate mapping、missing dependency |
| Regression tests | Pending composition、Submit guard |
| Artifact refresh | Runtime Planning sourceをaccepted authorityにする場合必要 |
| User-run validation | user 5BD after switch |
| Acceptance | canonical pending維持、duplicate 0 |
| Reject | direct Submit、multiple pending authorities |
| Rollback | old action-based planning bridge |
| Next gate | Dynamic Position Count / Target Cash / Sizing |

### Phase22-L Benchmark / Sector Authority Integration

| 項目 | 内容 |
|---|---|
| Objective | BenchmarkとSectorのAuthorityを評価/Strategy riskへ接続 |
| Why | concentrationとrelative performanceを正式評価するため |
| Dependencies | Phase22-K |
| Inputs | J-Quants / accepted benchmark source候補、Listed Issues、sector mapping |
| Outputs | benchmark/sector evidence |
| Artifacts | Benchmark/Sector Authority Artifacts |
| Authority | accepted data source |
| Production code scope | read-only authority resolver |
| Config scope | none or schema only |
| Prohibited | missing benchmarkをzero扱い |
| Data provenance | PIT data |
| PIT requirements | mapping as-of |
| Failure modes | coverage missing -> MISSING/REVIEW |
| Unit tests | coverage, missing mapping |
| Regression tests | Performance metrics |
| Artifact refresh | source acceptance必要 |
| User-run validation | not required for source-only; long eval user-owned |
| Acceptance | MISSING handling correct |
| Reject | non-PIT mapping |
| Rollback | mark metric MISSING |
| Next gate | Performance Observability |

### Phase22-M Performance Observability Completion

| 項目 | 内容 |
|---|---|
| Objective | Phase23評価に必要なmetrics/evidenceを完備 |
| Why | Returnだけで採用しないため |
| Dependencies | Phase22-L |
| Inputs | run evidence、ledger performance events、benchmark/sector evidence |
| Outputs | Performance Evaluation Artifact |
| Artifacts | strategy_performance_evaluation.v1 |
| Authority | Post-hoc diagnostic |
| Production code scope | reporting/analysis only |
| Config scope | none |
| Prohibited | Runtime/Training入力化 |
| Data provenance | run-scoped evidence |
| PIT requirements | diagnostic separation |
| Failure modes | missing metric -> MISSING |
| Unit tests | metric status taxonomy |
| Regression tests | summarize/run authority |
| Artifact refresh | analysis source if accepted |
| User-run validation | user long-run for Phase23 |
| Acceptance | all required metric statuses present |
| Reject | missing treated as zero |
| Rollback | previous report contract |
| Next gate | Phase22 closure |

### Phase22-N Strategy Architecture Implementation Closure

| 項目 | 内容 |
|---|---|
| Objective | Phase22実装の総合ClosureとPhase23 entry判定 |
| Why | 実装完了とControlled Validation移行を分離するため |
| Dependencies | Phase22-A through M |
| Inputs | all implementation evidence |
| Outputs | Phase22 closure report, Phase23 handoff |
| Artifacts | closure evidence |
| Authority | Architecture Review + Regression |
| Production code scope | none unless final docs |
| Config scope | none |
| Prohibited | late strategy tuning |
| Data provenance | evidence refs |
| PIT requirements | no leakage audit |
| Failure modes | unresolved blocking gap -> REVIEW/BLOCK |
| Unit tests | complete targeted suite |
| Regression tests | Runtime / Strategy / Artifact suite |
| Artifact refresh | all required complete |
| User-run validation | user acceptance runs |
| Acceptance | Phase23 entry criteria met |
| Reject | open blocker hidden |
| Rollback | stop before Phase23 |
| Next gate | Phase23 |

## 5. Dependency Graph

```text
Phase22-A Market Context Artifact
Phase22-AA Corporate Event Artifact
  -> Phase22-B Candidate / Opportunity Compatibility
  -> Phase22-C Portfolio Policy Artifact
  -> Phase22-D Position Management Refs and Compatibility
  -> Phase22-E Target Portfolio and Portfolio Construction
  -> Phase22-F Capital Deployment Responsibility Refactor
  -> Phase22-G Runtime Planning Execution Intent Bridge
  -> Phase22-H Dynamic Position Count
  -> Phase22-I Dynamic Target Cash Ratio / Exposure Target
  -> Phase22-J Position Sizing Foundation
  -> Phase22-K Regime/Event-aware HOLD / ADD / REDUCE / EXIT
  -> Phase22-L Benchmark / Sector Authority Integration
  -> Phase22-M Performance Observability Completion
  -> Phase22-N Strategy Architecture Implementation Closure
```

並行可能:

- Phase22-AとPhase22-AAは並行可能。ただしCandidate / Opportunity compatibility前に両方のArtifact schemaが必要
- Benchmark / Sectorのread-only source feasibility調査はfoundation taskと並行可能
- Performance metric schema設計はBenchmark / Sector source実装前に並行可能

直列必須:

- Market Context / Corporate Event -> Candidate / Opportunity compatibility
- Candidate / Opportunity compatibility -> Portfolio Policy
- Portfolio Policy -> PM refs -> Portfolio Construction
- Portfolio Construction -> Capital Deployment -> Runtime Planning
- Runtime Planning -> Safety/Runtime switch

Artifact Acceptanceが必要な境界:

- 新規Production source pathをRuntime/Strategy authorityにする時
- PM Runtime Adapterを変更する時
- Market Context / Corporate Event / Portfolio Policy / Portfolio Constructionをaccepted authorityにする時

User-run Acceptanceが必要な境界:

- Phase22-C以降のCapital/Planning影響
- Phase22-K以降のPM decision影響
- Phase22-I Target Portfolio cutover
- Phase22-L closure

## 6. Artifact Map

| Artifact | Producer | Consumer | Phase |
|---|---|---|---|
| Market Context Artifact | Market Context Engine | Portfolio Policy / PM / Attribution | 22-A |
| Corporate Event Artifact | Corporate Event Authority | Candidate / Opportunity / Policy / PM / Construction / Safety | 22-AA |
| Candidate Artifact | Candidate AI | Opportunity / Construction | 22-B |
| Opportunity Artifact | Opportunity AI | Construction / PM reference | 22-B |
| Portfolio Policy Artifact | Portfolio Policy Engine | Capital Deployment / PM / Construction | 22-C |
| PM Decisions Artifact | PM | Sell Planning / Construction | 22-D/K |
| Target Portfolio Artifact | Portfolio Construction | Capital Deployment | 22-E |
| Allocation Artifact | Capital Deployment | Runtime Planning / Safety | 22-F/J |
| Execution Intent Artifact | Runtime Planning | Safety / Pending / Submit | 22-G |
| Benchmark / Sector Evidence | Authority resolver | Performance / Construction | 22-L |
| Performance Evaluation Artifact | Observability | Phase23 Review | 22-M |

## 7. Evidence Requirement Matrix

| Decision / Task | Evidence Question | Required Data | Current Evidence Available? | Missing Evidence | Evidence Authority | Post-hoc only? | User Command Required? | Command | Expected Output | Decision Enabled |
|---|---|---|---|---|---|---|---|---|---|---|
| Position Sizing | どの方式がrisk/return/lotに適合するか | score, volatility, liquidity, lot, concentration | partial | sector/benchmark/vol window | J-Quants PIT + post-hoc eval | evalはyes | later | Phase23 experiment | ACCEPT/REVIEW | Phase23 |
| Market Context | PITで安定生成できるか | price, volume, breadth, sector | partial | thresholds/window | J-Quants PIT | no | no initially | static/fixture | schema PASS | Phase22-A |
| Dynamic Position Count | qualified countで上限調整できるか | opportunity count, score dist, cash | partial | exclusion stats | J-Quants PIT + run diagnostic | diagnostic yes | maybe | user 5BD/20BD after impl | count evidence | Phase22-D |
| Target Cash Ratio | 20% baselineの妥当性 | cash ratio, exposure, drawdown | partial | safety floor review | Portfolio Policy + Safety | drawdown yes | later | Phase23 experiment | review result | Phase22-E/23 |
| Minimum Holding | churn抑制が必要か | holding period, PM churn | partial | controlled windows | post-hoc diagnostic | yes | later | read-only aggregation first | distribution | Phase22-H/23 |
| Cooldown | repeated ADD/REDUCEを抑えるか | repeated decisions, pending conflicts | partial | re-entry stats | post-hoc diagnostic | yes | later | read-only aggregation first | churn evidence | Phase22-H/23 |
| Benchmark Authority | TOPIX等を正式Authority化できるか | benchmark data source | no | data source/PIT | accepted data source | no | no | source audit | authority decision | Phase22-J |
| Sector Authority | sector mapping coverageは十分か | Listed Issues/sector mapping | partial | coverage report | J-Quants/accepted source | no | no | source audit | coverage status | Phase22-J |
| Safety cash floor | owner/valueをどうするか | safety review, liquidity | partial | value evidence | Safety Authority | no | no | design review | owner/value gate | Phase22-E/23 |

## 8. User-run Validation Matrix

Codexは5BD、20BD、245BD、1年、複数年Runを実行しない。

| Boundary | User-run | 目的 | Expected |
|---|---|---|---|
| Phase22-F | 5BD | Capital refactor regression | Runtime PASS, duplicate 0 |
| Phase22-G | 5BD | Runtime Planning bridge / Pending candidate validation | Pending/Submit authority維持 |
| Phase22-K | 5BD | PM regime/event context lineage | PM HALTなし |
| Phase22-N | 20BD以上 | Phase23 entry | Lifecycle PASS, findings 0 |

標準5BDコマンド例:

```bash
cd /Users/negishi/work/ai-fund-lab-v2

PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-smoke \
  --business-days 5 \
  --start-date 2022-09-01 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

## 9. Regression Strategy

各Taskで最低限:

- Unit tests for new schema / policy / failure path
- Existing Runtime regression
- Phase21-B Pending Composition / ADD Consumer regression
- Artifact Registry resolver / accepted source tests when source authority changes
- Compile
- Negative path tests
- Duplicate rerun tests when Pending/Submit can be affected

## 10. Artifact Acceptance Strategy

Artifact refreshが必要:

- Production common source pathがAccepted Artifact memberになる
- PM Runtime Adapter source変更
- Market Context / Portfolio Policy / Portfolio ConstructionをRuntime authorityにする
- Capital Deployment accepted policy sourceを変更する

直接編集禁止:

- Registry event
- checkpoint
- accepted manifest
- accepted generation pointer

## 11. Rollback Strategy

Rollback原則:

- accepted previous generationを保持する
- new consumerをfeature flagではなくaccepted authorityで切り替える
- failed taskは次Taskへ進めない
- partial artifactはRuntime authorityにしない
- Pending / Ledger / Currentをstrategy rollbackで直接改変しない

## 12. Open Decision Handling

| Open Decision | Owner | Evidence | Timing | Acceptance |
|---|---|---|---|---|
| Position Sizing formula | Portfolio Policy + Capital Deployment | Phase23 controlled experiment | Phase22-J/Phase23 | risk/return/regression |
| Benchmark Authority | Performance/Artifact Registry | source audit | Phase22-J | PIT/source coverage |
| Sector Authority | Market Context / Performance | mapping coverage | Phase22-J | coverage/missing policy |
| Market Context threshold | Market Context | stability/missingness | Phase22-A/Phase23 | no leakage |
| volatility window | Market Context / Sizing | PIT stability | Phase22-A/F | no leakage |
| minimum holding period | PM Policy | holding/churn diagnostic | Phase22-H/Phase23 | controlled experiment |
| cooldown | PM Policy | churn/re-entry diagnostic | Phase22-H/Phase23 | controlled experiment |
| Safety cash floor | Safety Authority | safety review | Phase22-E/Phase23 | Safety acceptance |

## 13. Phase23 Entry Criteria

- Phase22-L closure PASS
- All blocking open decisions classified
- Runtime / Safety / Authority regression PASS
- Artifact Acceptance complete for all runtime authorities
- User-run acceptance boundary complete
- Performance Evaluation Artifact emits required metric statuses
- Experiment Contract ready
- No known future leakage
- No Historical-only strategy logic

## 14. Risks

| Risk | Mitigation |
|---|---|
| multiple changes in one task | task gate and single-change checklist |
| Market Context overrules individual opportunity | reason/confidence only, no hard override initially |
| capital refactor weakens Safety | Strategy target / Safety hard limit separation tests |
| Target Portfolio creates duplicate orders | Pending Composition and duplicate guard regression |
| performance overfit | Phase23 multi-regime/out-of-period |
| artifact stale hash | formal acceptance checklist |

## 15. Prohibited Operations

- Productionコード変更なしでない限りTaskを開始しない
- Config値の暗黙変更禁止
- Long Historical RunをCodexが実行禁止
- Performance evidenceをTraining / Runtime入力にしない
- Accepted Artifact直接編集禁止

Phase22 implementation must follow:

```text
Design Freeze
Design Change Request
Step Acceptance Gate
Rollback Point
Runtime Switch Gate
Old Path Removal Rule
Emergency Rollback
Design Drift Prevention
```

These rules are defined in:

```text
docs/phase_reports/phase21_gc_implementation_governance_and_phase22_entry_gate.md
```

## 16. Phase21-K Final Binding

Phase21-K完了後、Phase22実装順の正式SoTは本文配置ではなくDependency順である。

```text
Phase22-A Market Context Artifact Foundation
Phase22-AA Corporate Event Artifact Foundation
Phase22-B Candidate / Opportunity Compatibility
Phase22-C Portfolio Policy Artifact Foundation
Phase22-D Position Management Refs and Compatibility
Phase22-E Portfolio Construction / Target Portfolio Foundation
Phase22-F Capital Deployment Responsibility Refactor
Phase22-G Runtime Planning / Execution Intent Bridge
Phase22-H Dynamic Position Count
Phase22-I Dynamic Target Cash Ratio / Exposure
Phase22-J Position Sizing Foundation
Phase22-K Regime / Event-aware HOLD / ADD / REDUCE / EXIT
Phase22-L Benchmark / Sector Authority Integration
Phase22-M Performance / Runtime Observability Completion
Phase22-N Strategy Architecture Implementation Closure
```

Each Phase22 task must explicitly reference:

```text
Phase21-I Step Gate
Phase21-J Retirement Plan
Regression Preservation Matrix
State Transition Matrix
Rollback Retention Matrix
Zombie Detection Matrix
```

Phase21-I Step Gates are binding:

| Gate | Binding |
|---|---|
| K-SG-01 | Market Context / Corporate Event produced-but-not-consumed detection |
| K-SG-02 | Corporate Event source authority before active consumer use |
| K-SG-03 | Target Portfolio / Strategy Intent / Allocation / Execution Intent schema, producer, fixture consumer, hash, failure, bootstrap, compatibility |
| K-SG-04 | Status / AI Status / System Status / Summarize new visibility and old path usage detection |
| K-SG-05 | Runtime switch blocked by active Pending, unresolved Approval/Review, Open Order, Partial Fill, runtime mid-step, business-day mid-cutover |
| K-SG-06 | Execution Intent to canonical Pending parity and Submit consumer acceptance |

Phase21-J Retirement Plan is binding. Old Authority is not revoked when a new producer is merely accepted. The required order is:

```text
New Authority accepted
-> New Consumer acceptance
-> Runtime switch
-> Regression PASS
-> User validation
-> Old Authority revoked
-> Old path quarantine
-> Rollback retention
-> DELETE_READY
-> separate deletion task
```

`retained_for_rollback != active_authority`.

Phase22-A allowed scope:

```text
Market Context schema
Market Context producer
PIT source lineage
hash
status taxonomy
failure contract
bootstrap contract
read-only artifact generation
fixture consumer
produced-but-not-consumed detection
short unit / schema / contract tests
```

Phase22-A prohibited scope:

```text
Runtime behavior switch
PM behavior change
Candidate ranking change
Opportunity ranking change
Portfolio weight change
Capital allocation change
Pending change
Submit change
Old path deletion
Long Historical Run by Codex
```
