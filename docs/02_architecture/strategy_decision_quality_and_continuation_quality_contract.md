# Strategy Decision Quality and Continuation Quality Contract

作成日: 2026-08-15

## 1. Authority and Scope

本書は、AI Fund Lab v2のStrategy Decision Qualityを評価・改善するためのArchitecture-level research contractである。

本書は [Strategy Architecture v1](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/strategy_architecture_v1.md) の下位仕様として扱う。Phase30-Dのphase reportに閉じず、今後のStrategy研究、long-horizon attribution、BUY / ADD / HOLD / REDUCE / EXIT品質監査で参照する。

本書の主題は、次の問いである。

```text
Does this stock, given everything legitimately knowable now, still have a
relatively strong case for continuing upward from here?
```

この問いを暫定的に次の概念で表す。

```text
Continuation Quality / Forward Edge
```

## 2. Non-Implementation Boundary

本書は仕様・研究契約であり、実装許可ではない。

本書だけでは以下を変更しない。

- Strategy logic
- Runtime behavior
- Config
- Model
- Threshold
- Safety policy
- BUY Quality
- BUY_WAIT
- ADD
- HOLD
- REDUCE
- EXIT
- Current clean 977BD Historical run

本書は、Phase30-Dの次の境界をArchitecture-levelに昇格する。

```text
NO STRATEGY REDESIGN IMPLEMENTED
NO STRATEGY / RUNTIME / CONFIG / MODEL / THRESHOLD CHANGE
NO SAFETY / BUY QUALITY / BUY_WAIT / ADD / HOLD / REDUCE / EXIT CHANGE
NO IMPLEMENTATION AUTHORIZED
```

## 3. Motivation

Phase30-Aは、clean 20BD測定のintegrityを確認した。20BD損失はvaluation / basis contaminationではなく、実際のStrategy outcomeだった。

Phase30-Cは、in-flight 977BD runの途中スナップショットとして、BUY selection quality、entry timing、event eligibility、profit retentionの課題候補を示した。ただし、977BD runは未完了であり、Phase30-Cだけでthresholdやproduction behaviorを変更してはならない。

Phase30-Dは、孤立したBUY threshold調整やSELL timing調整ではなく、Strategy Decision Qualityをより根本から見直す研究方向を定義した。

本書はその研究方向を、phase reportではなく継続参照可能な仕様として固定する。

## 4. Definitions

### Good Stock

AI Fund Lab v2における"good stock"は、単に過去に上がった銘柄ではない。

Research definition:

```text
A good stock is a stock whose current PIT-observable state suggests that future
upward continuation has relatively favorable probability, magnitude,
persistence, and risk-adjusted economic value compared with available
alternatives.
```

この定義はresearch definitionであり、現行systemが正しく推定できているとは仮定しない。

### Continuation Quality

Continuation Qualityは、当日Point-in-Timeで正当に利用可能な情報から見て、その銘柄の上昇継続 thesis がどれだけ健全・持続的・経済的に魅力的かを評価する研究概念である。

Continuation Qualityは次を直接意味しない。

- 直近return
- momentumの強さだけ
- BUY Quality scoreだけ
- Opportunity rankだけ
- current profitだけ
- cash availability
- forced exposure

### Forward Edge

Forward Edgeは、Continuation Qualityをexpected value寄りに表現した呼称である。

Forward Edgeは、銘柄間のrelative opportunity comparisonと、既存positionを続けるべきかどうかの判断を接続するための研究概念である。

### Expected Edge Calibration

Formal Expected Edge Calibrationは、期待return、downside risk、hold horizon、confidence、turnover costなどを明示的に推定・検証するより厳密な将来設計である。

Continuation Qualityは、Expected Edge Calibrationそのものではない。Continuation Qualityは、その前段として、上昇継続 thesis の品質を統一的に監査・研究するための概念である。

## 5. Core Principles

Strategy researchは、次の区別を明示する。

```text
Stocks that have risen strongly
```

と

```text
Stocks that are likely to continue rising from the current PIT state
```

は同じではない。

Phase30以降の研究は、「もっと買う」「もっと早く売る」より前に、次を評価する。

```text
How should the system determine whether a stock is still a high-quality
forward opportunity from the current PIT state?
```

原則:

- Point-in-Timeで利用可能な情報だけを使う。
- Future labelsはoffline評価にだけ使い、runtime inputにしない。
- 20BDまたはincomplete 160BD evidenceから恒久thresholdを作らない。
- Contaminated historical runsをtuning authorityにしない。
- Cashはvalid outcomeであり、固定full deploymentを目的にしない。
- Position countは結果であり、固定銘柄数を目的にしない。
- Performance improvementのためにAction Authorityを増やさない。

## 6. Lifecycle Unification

Continuation Qualityは、BUY、ADD、HOLD、ADD stop、profit protection、REDUCE、EXITを別々の小手先ルールとして扱わず、同じforward-looking thesisの lifecycle として監査するための概念である。

Lifecycle questions:

| Stage | Research question |
|---|---|
| BUY_NEW | Is this no-position candidate already a high-quality forward opportunity? |
| ADD | Is incremental capital still justified versus alternatives and current exposure? |
| HOLD | Does the existing position still have sufficient continuation quality? |
| ADD STOP | Is the position worth holding, but no longer worth additional capital? |
| Profit Protection | Has continuation quality deteriorated enough that embedded profit requires risk review? |
| REDUCE | Has risk/reward weakened enough to reduce exposure while preserving optionality? |
| EXIT | Has the continuation thesis broken or become insufficient? |

This does not create new action authority. PM and Portfolio Construction authority boundaries remain governed by Strategy Architecture v1.

## 7. Candidate State Progression

Continuation Quality research may use a conceptual state progression for analysis.

```text
HEALTHY_WINNER
  -> STRONG_BUT_DECELERATING
  -> TOPPING_RISK
  -> BREAKDOWN
```

These states are research vocabulary only. They are not runtime enums, thresholds, or action triggers unless separately specified, implemented, and validated.

## 8. Architecture Placement

Continuation Quality belongs between eligibility/event facts and expected edge / opportunity comparison.

Target conceptual flow:

```text
Universe
  -> Eligibility / Event Risk Gate
  -> Continuation Quality
  -> Expected Edge / Opportunity Comparison
  -> Portfolio Construction
  -> Position Management
  -> Runtime Planning
  -> Strategy Planning Authority
  -> Safety / Submit / Execution
```

Corporate Event Authority remains a fact authority. It provides PIT facts such as listing state, supervision/alert status candidates, earnings schedule, corporate actions, TOB, and other material events. It does not independently decide BUY, ADD, HOLD, REDUCE, EXIT, target weight, or runtime execution.

Event / eligibility risk should not be hidden inside a generic continuation score when it represents a disqualifying or review-required fact. The architecture should preserve a visible upstream gate.

## 9. Relationship To Existing Contracts

This contract does not supersede the following closed contracts.

- Strategy Architecture v1 remains the top-level Strategy SoT.
- PM remains Strategy Action Authority for existing-position directional actions.
- Portfolio Construction remains Target Portfolio Decision Authority.
- Runtime Planning remains a pure mapper from Strategy intent and quantity candidates into runtime execution intent.
- Strategy Planning Authority materializes Pending after validation; it does not re-optimize Strategy.
- Safety blocks or reviews dangerous intent; it does not optimize expected edge.
- BUY/SELL independence remains preserved.
- Production, Demo, and Historical must share common Strategy contracts unless explicitly versioned.
- Missing authority must fail closed.

Continuation Quality is therefore an upstream research contract for better evidence, not a shortcut around authority boundaries.

## 10. Candidate Research Inputs

The current system is not assumed to have a complete Continuation Quality model.

Candidate research dimensions include:

- momentum persistence
- momentum acceleration / deceleration
- breakout quality
- volume confirmation
- volatility and drawdown risk
- recent reversal pressure
- distance from moving averages
- gap / overheated move risk
- earnings and material event proximity
- listing, supervision, alert, delisting, and eligibility facts
- sector / market context alignment
- liquidity and tradability
- campaign age and current profit path
- MFE / MAE profile for offline evaluation

These are candidate research dimensions, not approved runtime inputs by themselves.

## 11. Long-Horizon Research Dataset

After the clean 977BD Historical run completes, Strategy Decision Quality research should build a PIT-respecting dataset.

Recommended units:

- `symbol x decision_date`
- `campaign x decision_date`
- `BUY fill x forward horizon`
- `ADD candidate x forward horizon`
- `HOLD / REDUCE / EXIT decision x forward horizon`

Recommended offline labels:

- 1BD / 3BD / 5BD / 10BD / 20BD forward return
- MFE
- MAE
- drawdown from post-entry peak
- giveback after unrealized profit
- time to peak
- time to loss threshold candidate
- final campaign PnL
- turnover and opportunity cost proxy

Labels are for evaluation only. They must not become runtime features.

## 12. Redesign Gate

No Continuation Quality implementation should proceed until all of the following are satisfied.

1. Clean 977BD baseline completes.
2. Phase30-C style stock-level audit is expanded to the full run.
3. BUY_NEW, BUY_ADD, REENTRY, HOLD, REDUCE, and EXIT outcomes are separated.
4. Event / eligibility defects are separated from market-price continuation defects.
5. Candidate features are evaluated with PIT availability.
6. Proposed rules are tested against turnover, drawdown, exposure, concentration, and Safety regression.
7. The implementation target is mapped to the correct Authority boundary before code changes.

## 13. Current Operational Rule

The next operational action remains:

```text
CONTINUE CURRENT CLEAN 977BD HISTORICAL
```

Until the clean long-horizon run and follow-up attribution are complete, this contract authorizes documentation, audit design, and dataset planning only.

## 14. Source Reports

This contract promotes the Phase30-D thesis into Architecture-level documentation and should be read with:

- [Phase30-A Post-BL Clean 20BD Integrity and Performance Attribution](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase30_a_post_bl_clean_20bd_integrity_and_performance_attribution.md)
- [Phase30-B Clean Long-Horizon Baseline Preparation](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase30_b_clean_long_horizon_baseline_preparation.md)
- [Phase30-C In-Flight BUY Selection Quality Audit](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase30_c_inflight_buy_selection_quality_audit.md)
- [Phase30-D Strategy Research Direction and Continuation Quality Thesis](/Users/negishi/work/ai-fund-lab-v2/docs/phase_reports/phase30_d_strategy_research_direction_and_continuation_quality_thesis.md)

## 15. Phase30-I Durable Extension

Phase30-I extends this research contract into a durable Production-common
Strategy Intelligence architecture.

The canonical extension documents are:

- [Strategy Intelligence Architecture v1](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/strategy_intelligence_architecture_v1.md)
- [Strategy Intelligence Data Contract v1](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/strategy_intelligence_data_contract_v1.md)
- [Strategy Intelligence Regression Contract v1](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/strategy_intelligence_regression_contract_v1.md)

Phase30-I refines the earlier `Continuation Quality / Forward Edge` research
language into three distinct concepts:

```text
Continuation Quality
Downside Risk
Expected Edge / Opportunity Cost
```

These concepts must not be collapsed into one opaque score. Continuation
Quality remains the structured evidence for the health and persistence of the
upward thesis. Downside Risk separately represents probabilistic adverse
movement and failure risk. Expected Edge separately represents relative
economic merit versus alternatives, including Cash.

Phase30-I also freezes this design boundary:

```text
Shared intelligence != Shared action authority
```

Continuation Quality, Downside Risk, and Expected Edge may be shared evidence
for BUY_NEW, BUY_ADD, REENTRY, HOLD, REDUCE, and EXIT interpretation, but they
do not become Action Authority. PM and Portfolio Construction authority
boundaries remain governed by Strategy Architecture v1.

Implementation remains unauthorized until a later task explicitly implements a
shadow-first Production-common evidence producer and passes the regression and
Winner Preservation gates defined by the Phase30-I architecture documents.
