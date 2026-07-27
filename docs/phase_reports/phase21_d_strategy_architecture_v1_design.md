# Phase21-D Strategy Architecture v1 Design

## Executive Summary

```text
PHASE21_D_STRATEGY_ARCHITECTURE_DESIGN_COMPLETE_WITH_OPEN_DECISIONS
```

AI Fund Lab v2のStrategy Layer最上位SoTとして、`docs/02_architecture/strategy_architecture_v1.md` を作成した。Phase21-DではProduction Strategyコード、Runtimeコード、Config値、Accepted Generation、Training、Calibration、長時間Historical Runを変更していない。

Phase21-B/CでRuntime Acceptanceが回復したため、Phase21-DではStrategy Architecture Designへ戻り、Phase22実装とPhase23検証のContractを整備した。

## Current Architecture Inventory

Inventoryは次に集約した。

```text
docs/02_architecture/strategy_architecture_v1.md
```

棚卸し対象:

- Candidate AI
- Opportunity AI
- Position Management AI
- Market Features
- Market Context相当
- Morning Planning
- Capital Deployment
- ADD Consumer
- Sell Planning
- Pending Composition
- Submit
- Safety
- Ledger
- Current
- Performance Observability
- Benchmark
- Sector
- Artifact Registry

## Target Architecture

Target component map:

```text
J-Quants PIT Data
  -> Feature Layer
  -> Market Context Engine
  -> Candidate AI
  -> Opportunity AI
  -> Portfolio Policy Engine
  -> Position Management AI
  -> Portfolio Construction
  -> Capital Deployment
  -> Runtime Planning
  -> Safety / Submit / Execution
```

RuntimeはStrategy判断を再計算しない。SafetyはStrategyを最適化しない。Performance EvidenceはRuntime / Training / Calibration入力にしない。

## Design Decisions

| Decision | 結論 |
|---|---|
| Market Context | 独立Engineとする |
| Portfolio Manager用語 | 論理的総称に限定し、実体ComponentはPortfolio Policy Engine / Position Management AI / Portfolio Constructionへ分離 |
| PMとPortfolio Policy | Position Management AIとPortfolio Policy Engineを分離Artifact候補とする |
| Target Portfolio | Phase22採用候補とする |
| Dynamic Position Count owner | Portfolio Policy |
| Target Cash Ratio owner | Portfolio Policy |
| 20% cash | dynamic targetの標準baseline候補。hard floorではない |
| 5銘柄固定 | Phase22 targetでは撤廃方針 |
| 850,000円固定上限 | Phase22 targetではStrategy target / Safety hard limitへ分離 |
| Strategy / Safety | Strategy targetとSafety hard limitを分離 |
| BUY / ADD | intentは分離し、Portfolio Constructionで統合評価 |
| Experiment | Single-change、multi-regime、out-of-period必須 |

## Open Decisions

| Decision | 必要Evidence |
|---|---|
| Position Sizing具体式 | controlled experiment |
| Benchmark Authority | benchmark data source / PIT authority |
| Sector Authority | sector mapping coverage |
| Market Context閾値 | multi-regime diagnostic |
| volatility計算窓 | PIT stability |
| minimum holding period | holding attribution |
| cooldown | churn / duplicate analysis |
| Safety absolute cash floor | Safety review |

Open Decisionは暗黙決定していない。

## Documents Created

- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/03_ai_design/market_context_design.md`
- `docs/03_ai_design/portfolio_manager_policy_design.md`
- `docs/03_ai_design/capital_deployment_design.md`
- `docs/01_requirements/strategy_performance_acceptance_contract.md`
- `docs/01_requirements/strategy_experiment_contract.md`
- `docs/phase_reports/phase21_d_strategy_architecture_v1_design.md`
- `reports/phase21_d_strategy_architecture_v1_design/phase21_d_evidence.json`

## Documents Updated

- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/01_requirements/phase_roadmap.md`

## Runtime Impact

```text
NO_RUNTIME_CODE_CHANGE
```

Runtimeの責務境界は明確化したが、Runtime実装は変更していない。

## Strategy Code Impact

```text
NO_STRATEGY_CODE_CHANGE
```

PM threshold、Opportunity ranking、Candidate ranking、max_positions、max_exposure、target_investment_ratio、cash_buffer、position sizing値は変更していない。

## Data Boundary Confirmation

Strategy / Training / Feature authorityはJ-Quants由来PIT dataである。5BD / 245BD / Performance EvidenceはPost-hoc diagnostic専用であり、Runtime / Training / Calibration入力にしない。

## Phase22 Readiness

Phase22実装順序:

1. Market Context Artifact
2. Portfolio Policy Artifact
3. Capital Deployment Contract refactor
4. Dynamic Position Count
5. Target Cash Ratio
6. Position Sizing
7. PM Context integration
8. Regime-aware HOLD / ADD / REDUCE / EXIT
9. Portfolio Construction
10. Evidence / Metrics
11. Regression

## Remaining Gaps

- Market Context具体閾値は未決定
- Benchmark / Sector authorityは未実装
- Position Sizing具体式は未決定
- Dynamic Position Countは設計済みだが未実装
- Target Portfolio方式は採用候補であり未実装

## Prohibited Operations Confirmation

```text
Production Code Changed: NO
Runtime Code Changed: NO
Config Values Changed: NO
Accepted Generation Changed: NO
Training Executed: NO
Calibration Changed: NO
Long Historical Run Executed: NO
Artifact Acceptance Changed: NO
```
