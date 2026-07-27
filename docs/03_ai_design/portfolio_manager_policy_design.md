# Portfolio Policy Engine Design

作成日: 2026-07-27

## 1. 位置付け

Portfolio Policy Engineは、Strategy Layerが当日の投資姿勢、現金比率、exposure、position count、BUY/ADD/REDUCE/EXIT biasを出すためのPolicy artifactを生成するComponentである。

`Portfolio Manager` は実体Component名ではなく、Portfolio Policy Engine、Position Management AI、Portfolio Constructionを束ねる論理的総称としてのみ使用する。

上位SoT:

```text
docs/02_architecture/strategy_architecture_v1.md
```

## 2. 責務分離

正式な責務は以下に分離する。

Portfolio Policy Engine:

- market posture
- target cash ratio
- target exposure ratio
- minimum / target / maximum positions
- BUY permission
- ADD permission
- REDUCE bias
- EXIT bias
- sector concentration tolerance

Position Management AI:

- HOLD
- ADD
- REDUCE
- EXIT

Corporate Event Authority:

- listed status
- delisting status
- earnings schedule
- earnings release time
- forecast revision
- dividend revision
- corporate action type

Corporate Event Authorityは事実を提供するだけであり、Portfolio Policy EngineやPosition Management AIの判断を代行しない。

## 3. PMが決めないもの

- Broker quantity
- 実注文株数
- lot rounding
- final submit permission
- Safety override
- Broker availability
- fill price
- Corporate Event factの生成
- 上場廃止や決算だけによる自動売買

## 4. Portfolio Policy Output候補

```yaml
schema_version: portfolio_policy.v1
business_date: 2026-07-27
as_of: 2026-07-27T08:30:00+09:00
market_posture: AGGRESSIVE
target_cash_ratio: 0.20
target_exposure_ratio: 0.80
minimum_positions: 3
target_positions: 7
maximum_positions: 10
buy_permission: ALLOWED
add_permission: ALLOWED_WITH_POLICY
reduce_bias: LOW
exit_bias: NORMAL
sector_concentration_tolerance: NORMAL
confidence: 0.71
reason_codes:
  - BROAD_MARKET_MOMENTUM
  - STRONG_OPPORTUNITY_BREADTH
artifact_lifecycle_status: DRAFT
source_authority_status: VALID
producer_result_status: PASS
runtime_consumer_eligibility: NOT_ELIGIBLE
source_artifacts: []
source_hashes: []
```

`authority_status: ACCEPTED` は使用しない。`ACCEPTED` はArtifact Acceptance Contract上のRegistry lifecycle statusとして予約される。

## 5. HOLD / ADD / REDUCE / EXIT

HOLD:

- trend continuation
- risk許容
- opportunity deteriorationなし

ADD:

- 強い上昇継続とPortfolio余力がある場合の買い増し候補intent
- 直接注文ではない

REDUCE:

- risk上昇、peak drawdown、trend弱化、market context悪化などで一部縮小するintent
- 数量候補はCapital Deployment / Sell Planning互換経路のownership

EXIT:

- full close intent
- trend break、loss containment、重大riskなどで発生

優先順位:

```text
EXIT > REDUCE > ADD > HOLD
```

## 6. Market Contextの影響

Market ContextはPM判断のreasonとbiasに影響する。ただし、個別銘柄のMomentumやOpportunityを無条件に上書きしない。

例:

- Bull: ADD許容度上昇、HOLD期間長め
- Bear: ADD制限、REDUCE / EXIT bias上昇
- Range: 利益保護と回転を重視

## 7. Corporate Eventの影響

Corporate EventはPortfolio Policy EngineとPosition Management AIのreason、bias、risk postureに影響する。ただし、Corporate Event Authority自体は投資判断をしない。

利用可能:

- 決算跨ぎを許容するPortfolio posture
- earnings approaching時のADD抑制bias
- earnings disclosed後のpost-earnings momentum reason
- forecast revision / dividend revision reason
- delisting pendingのrisk reason

禁止:

- 決算だけで新規BUYを禁止する
- 上場廃止だけでPMが売却数量を決める
- Corporate Event Authority missingをsafe扱いする
- 新しいPM Actionを追加する

Reason候補:

- `EARNINGS_APPROACHING`
- `HOLD_THROUGH_EARNINGS_ALLOWED`
- `REDUCE_BEFORE_EARNINGS`
- `EXIT_BEFORE_EARNINGS`
- `POST_EARNINGS_MOMENTUM_CONFIRMED`
- `POST_EARNINGS_GAP_REVERSAL`
- `FORECAST_REVISION`
- `DIVIDEND_REVISION`
- `DELISTING_PENDING`

## 8. Failure Handling

| Failure | 扱い |
|---|---|
| Market Context source missing | `REVIEW_REQUIRED` |
| Market Context invalid schema | `BLOCK` |
| Market Context hash mismatch | `BLOCK` |
| Market Context low confidence | valid artifactとしてneutral / defensive Policyへ遷移可能 |
| Market Context conflicting signals | `REVIEW_REQUIRED` |
| Portfolio Policy invalid | `BLOCK` |
| target weights inconsistent | `BLOCK` |
| PM conflict | priority rule + evidence |
| Strategy / Safety conflict | Safety wins |
| ADD but current position invalid | rejection evidence |
| Corporate Event source missing | `REVIEW_REQUIRED` |
| Corporate Event hash mismatch | `BLOCK` |
| Corporate Event coverage insufficient | `REVIEW_REQUIRED` |
| Earnings datetime unknown | `REVIEW_REQUIRED` |
| Final trading date exceeded | Safety `BLOCK` |

## 9. Phase22実装単位

1. Portfolio Policy Artifact schema
2. PM decision outputへのpolicy refs追加
3. Market Context consumer
4. reason_codes / confidence
5. position decision priority tests
6. ADD / REDUCE / EXIT lineage強化
7. Corporate Event refs / reason_codes設計

## 10. Open Decisions

| Decision | Status | 必要Evidence |
|---|---|---|
| Portfolio PolicyとPM Decisionsを同一artifactにするか | OPEN_DESIGN_DECISION | implementation boundary review |
| minimum holding period value | OWNER_DECIDED_VALUE_OPEN | Position Management Policy / holding attribution |
| ADD / REDUCE cooldown values | OWNER_DECIDED_VALUE_OPEN | Position Management Policy / churn analysis |
| re-entry cooldown value | OWNER_DECIDED_VALUE_OPEN | Portfolio Construction conflict policy |
| profit protection threshold value | OWNER_DECIDED_VALUE_OPEN | Position Management Policy / post-hoc diagnostic only |
| loss containment threshold value | OWNER_DECIDED_VALUE_OPEN | Position Management Policy / post-hoc diagnostic only |
| Safety stop value | OWNER_DECIDED_VALUE_OPEN | Safety review |
| earnings event risk threshold | OWNER_DECIDED_VALUE_OPEN | Corporate Event Authority + Phase23 validation |
| delisting risk posture | OWNER_DECIDED_VALUE_OPEN | Safety / Portfolio Policy review |
