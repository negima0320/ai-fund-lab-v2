# Capital Deployment Design

作成日: 2026-07-27

## 1. 位置付け

Capital Deploymentは、Strategy targetを実行可能なnotional / quantity候補へ変換する層である。PMやPortfolio Policyが直接Broker quantityを決めないよう、Strategy target、Safety hard limit、Execution feasibilityを分離する。

Corporate Event Authorityは、Portfolio Constructionが生成したStrategy Intentのsource reasonとして参照される場合がある。Capital DeploymentはCorporate Event riskを再評価してTarget Portfolioを変更しない。

上位SoT:

```text
docs/02_architecture/strategy_architecture_v1.md
```

## 2. 現行Policy

現行値:

```text
evaluation_capital=1,000,000
target_investment_ratio=0.85
cash_buffer=0.05
max_exposure=850,000
max_position_weight=0.20
max_positions=5
```

Phase21-Dではこれらの値を変更しない。

## 3. Phase22 Target Contract

Strategy Target:

- target cash ratio
- target exposure ratio
- target position count
- target position weight
- event-aware Strategy Intent

Safety Hard Limit:

- absolute minimum cash
- absolute max exposure
- absolute max single-name weight
- absolute max position count
- emergency state restrictions
- forbidden order conditions

Portfolio Risk Policy:

- target concentration tolerance
- sector concentration tolerance
- risk budget
- liquidity risk tolerance

Execution Feasibility:

- buying power
- lot size
- minimum order unit
- price availability
- current position
- pending order
- duplicate guard
- broker capability
- market/session constraint

Liquidityは、Strategy sizing input、Risk hard limit、Broker execution feasibilityで用途を分ける。Safetyはlot roundingを行わない。

## 4. Dynamic Position Count

Owner:

```text
Portfolio Policy
```

Capital Deploymentはownerではない。Capital Deploymentは、Policy targetがcash、lot、single-name、broker、pending制約を満たすか評価する。

原則:

```text
良い候補が2件なら2件
良い候補が0件なら0件
良い候補が多くてもRisk / Sector / Cash制約を超えない
```

## 5. Target Cash Ratio

Phase22初期方針:

```text
20% cash is standard baseline target, not permanent hard floor.
```

20% cashはMarket Context dynamic targetの標準baseline候補である。Safety hard floorは別Authorityで定義する。

## 6. Position Sizing

Phase22候補:

- Equal weight
- Confidence-weighted
- Volatility-adjusted
- Liquidity-adjusted
- Opportunity-score weighted
- Risk-budget weighted
- Hybrid

初期採用候補はHybridである。ただし具体式はEvidence不足のためPhase22設計内で閉じる。

責務境界:

- Portfolio Policy: target weight / confidence
- Capital Deployment: notional / quantity候補
- Safety: hard cap
- Runtime Planning / Broker adapter: Broker constraint / availability / submit feasibility

## 7. BUY / ADD / REDUCE / EXITとの関係

BUY:

- 新規positionのtarget weight差分

ADD:

- 既存positionのtarget weight増加候補

REDUCE:

- target weight低下候補

EXIT:

- target weight zero候補

現行Action-based方式は、Target Portfolio方式への移行時もStrategy Intent分類として維持できる。Runtime Execution IntentはRuntime Planningが生成する。

## 8. Failure Handling

| Failure | 扱い |
|---|---|
| insufficient cash | rejection evidence |
| lot not viable | rejection evidence |
| duplicate pending | rejection or `BLOCK` |
| max single-name weight exceeded | rejection |
| max exposure exceeded | rejection or `REVIEW_REQUIRED` |
| target weights > 100% | `BLOCK` |
| policy missing | `BLOCK` |
| Safety conflict | Safety wins |
| Corporate Event authority missing | `REVIEW_REQUIRED` before allocation if required by Strategy Intent |
| final trading date exceeded | Safety `BLOCK` |

## 9. Phase22実装単位

1. Strategy target fields追加
2. hard limit fields分離
3. dynamic position count入力
4. target cash ratio入力
5. target weight to notional
6. lot rounding evidence
7. rejection reason標準化
8. existing Phase21-B ADD lineageとの互換

## 10. Open Decisions

| Decision | Status | 必要Evidence |
|---|---|---|
| absolute minimum cash floor | OPEN_DESIGN_DECISION | Safety review |
| absolute max exposure | OPEN_DESIGN_DECISION | Risk review |
| max position count hard cap | OPEN_DESIGN_DECISION | diversification / operations review |
| initial sizing formula | OPEN_DESIGN_DECISION | controlled experiment |
