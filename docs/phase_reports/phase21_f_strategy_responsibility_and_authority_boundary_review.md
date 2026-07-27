# Phase21-F Strategy Responsibility and Authority Boundary Review

## 1. Primary Judgment

```text
PHASE21_F_STRATEGY_RESPONSIBILITY_AND_AUTHORITY_REVIEW_PASS_WITH_OPEN_DECISIONS
```

Phase21-D/Eで作成したStrategy設計資料を横断レビューし、責務、Authority、用語、Status、Failure Contractの衝突を修正した。

責務Owner未確定のblocking gapは残していない。残るOpen Decisionは、数値、閾値、式、計算窓、データsource coverageのEvidence不足であり、Phase22/23で扱う。

## 2. Reviewed Documents

- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/03_ai_design/market_context_design.md`
- `docs/03_ai_design/portfolio_manager_policy_design.md`
- `docs/03_ai_design/capital_deployment_design.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/artifact_acceptance_contract.md`
- `docs/01_requirements/strategy_performance_acceptance_contract.md`
- `docs/01_requirements/strategy_experiment_contract.md`
- `docs/01_requirements/phase_roadmap.md`
- `docs/phase_reports/phase21_d_strategy_architecture_v1_design.md`
- `docs/phase_reports/phase21_e_phase22_implementation_plan_and_acceptance.md`
- `docs/phase_reports/phase22_strategy_architecture_implementation_plan.md`
- `docs/01_requirements/phase22_strategy_implementation_acceptance_checklist.md`

Note: user request listed `docs/01_requirements/artifact_acceptance_contract.md`; actual repository file is `docs/02_architecture/artifact_acceptance_contract.md`.

## 3. Responsibility Findings

| Finding | Correction |
|---|---|
| `Portfolio Manager`が実体Componentのように見える | 論理的総称に限定。実体ComponentはPortfolio Policy Engine、Position Management AI、Portfolio Construction |
| Position Management AIとPortfolio Policyの責務が混在 | Portfolio Policy Engineはportfolio-level target / posture、PMは既存position intentへ分離 |
| Portfolio ConstructionとCapital Deploymentの出力境界が曖昧 | Portfolio ConstructionはTarget Portfolio / Strategy Intent、Capital DeploymentはAllocation Candidate |
| Execution Intent ownerがStrategy側に寄っていた | Runtime Execution Intent producerをRuntime Planningに固定 |
| Runtime duplicate guardとStrategy cooldownが混同され得る | duplicate guardはRuntime、cooldown/min-hold/profit protectionはStrategy Policy ownerへ分離 |

## 4. Authority Findings

最終的なAuthorityは以下に確定した。

| Authority | Owner |
|---|---|
| Investment Decision Authority | Strategy Authority Chain全体。ただし最終Target Portfolio決定はPortfolio Construction |
| Target Portfolio Authority | Portfolio Construction |
| Capital Deployment Authority | Capital Deployment。Target Portfolio差分をnotional / quantity candidateへ変換 |
| Execution Intent Producer | Runtime Planning |
| Safety Authority | Safety。Block / Reviewのみ。Strategy最適化はしない |
| Runtime Authority | Operation、Pending、Submit、Lifecycle、Ledger、Current、Audit |
| Broker / Execution Authority | Broker制約、注文受付、execution / fill result |

否定条件:

```text
Ranking上位 = BUYではない
PM ADD = BUYではない
Portfolio Policy ALLOWED = BUYではない
Capital Deployment feasible = Submit許可ではない
```

## 5. Terminology Findings

| Term | Final Meaning |
|---|---|
| Portfolio Manager | 論理的総称。実体Component名として使わない |
| Portfolio Policy Engine | Portfolio-level target / permission / posture owner |
| Position Management AI | 既存positionのHOLD / ADD / REDUCE / EXIT intent owner |
| Portfolio Construction | Target Portfolio Decision Authority |
| Capital Deployment | Allocation Candidate Authority |
| Runtime Execution Intent | Runtime Planningが生成する運用/Pending候補 |
| `ACCEPTED` | Artifact Acceptance Contract上のRegistry lifecycle status |

## 6. Corrected Responsibility Matrix

修正後の責務表は以下をSoTとする。

```text
docs/02_architecture/strategy_architecture_v1.md#31-strategy-responsibility-matrix
```

最低限の確定事項:

- Market Context Engineは市場状態Evidenceのみを出す
- Candidate AIは候補母集団Authority
- Opportunity AIはRanking / Expected Edge Authority
- Portfolio Policy EngineはPortfolio-level Target / Permission / Posture Authority
- Position Management AIはExisting Position Intent Authority
- Portfolio ConstructionはTarget Portfolio Decision Authority
- Capital DeploymentはAllocation Candidate Authority
- Runtime PlanningはRuntime Execution Intent / Pending Authority
- SafetyはBlock / Review Authority
- RuntimeはOperation / Lifecycle / Current / Ledger Authority
- Broker / ExecutionはBroker Execution Authority

## 7. Corrected Decision Authority Chain

```text
Market Context Evidence
  -> Portfolio Policy
  -> Candidate / Opportunity Evidence
  -> Position Management Intent
  -> Portfolio Construction Target Portfolio Decision
  -> Capital Deployment Allocation Candidate
  -> Runtime Planning Execution Intent
  -> Safety / Approval / Pending
  -> Submit / Execution
```

## 8. Status Taxonomy

`authority_status: ACCEPTED` はStrategy daily artifact statusとして使用しない。

| Status Family | Field |
|---|---|
| Artifact Lifecycle Status | `artifact_lifecycle_status` |
| Source Authority Status | `source_authority_status` |
| Producer Result Status | `producer_result_status` |
| Consumer Eligibility | `runtime_consumer_eligibility` |
| Runtime Decision Status | `runtime_decision_status` |

`ACCEPTED`を使用する場合は、Registry Artifact Lifecycle `ACCEPTED` を意味する。

## 9. Corrected Failure Contract

Market Context failure:

| Condition | Handling |
|---|---|
| source missing | `REVIEW_REQUIRED` |
| invalid schema | `BLOCK` |
| hash mismatch | `BLOCK` |
| low confidence | valid artifactとしてneutral / defensive Policyへ遷移可能 |
| conflicting signals | `REVIEW_REQUIRED`。valid artifact扱いの場合もreason必須 |

missing sourceをneutralとして暗黙補完しない。

## 10. Files Updated

- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/03_ai_design/market_context_design.md`
- `docs/03_ai_design/portfolio_manager_policy_design.md`
- `docs/03_ai_design/capital_deployment_design.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/01_requirements/phase_roadmap.md`
- `docs/phase_reports/phase21_d_strategy_architecture_v1_design.md`
- `docs/phase_reports/phase22_strategy_architecture_implementation_plan.md`

## 11. Remaining Open Decisions

Ownerは確定済みで、未確定なのは値・式・source coverageである。

| Open Decision | Owner | Type |
|---|---|---|
| Position Sizing formula | Portfolio Construction / Capital Deployment | formula |
| Market Context thresholds | Market Context Engine | threshold |
| volatility window | Market Context Engine / Capital Deployment | calculation window |
| minimum holding period value | Position Management Policy | value |
| ADD / REDUCE cooldown values | Position Management Policy | value |
| re-entry cooldown value | Portfolio Construction conflict policy | value |
| profit protection threshold value | Position Management Policy | value |
| loss containment threshold value | Position Management Policy | value |
| Safety absolute cash floor value | Safety | value |
| Benchmark source authority | Performance / Benchmark Authority | source coverage |
| Sector mapping authority | Sector Authority | source coverage |

## 12. Blocking Gaps

```text
None
```

## 13. Non-blocking Gaps

- Threshold / formula / valueはPhase22/23 Evidence待ち
- Benchmark / Sector authorityはPhase22-Jでsource coverage確認が必要
- Phase22実装時にArtifact Acceptance refreshが必要になるsource pathがある

## 14. Phase21 Next Recommendation

```text
Phase21-G Phase22 Entry Gate
```

Phase21-Gでは、Phase21-D/E/FのSoT整合、禁止事項、Artifact Acceptance境界、Phase22-A開始可否を最終確認する。

## 15. Prohibited Operations Confirmation

| Item | Result |
|---|---|
| Production Code Changed | NO |
| Runtime Code Changed | NO |
| Strategy Code Changed | NO |
| Config Changed | NO |
| PM Threshold Changed | NO |
| Candidate / Opportunity Model Changed | NO |
| Position Sizing Formula Adopted | NO |
| Market Context Threshold Adopted | NO |
| Safety Threshold Changed | NO |
| Accepted Generation Changed | NO |
| Artifact Registry Changed | NO |
| Training Executed | NO |
| Calibration Executed | NO |
| Historical Run Executed | NO |
| Backtest Executed | NO |
| Phase22 Implementation Started | NO |

