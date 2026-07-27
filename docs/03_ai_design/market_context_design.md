# Market Context Design

作成日: 2026-07-27

## 1. 位置付け

Market Context Engineは、Strategy Architecture v1の一部であり、当日時点までの市場状態を要約する。未来予測Engineではない。

Corporate Event AuthorityはMarket Contextとは別Componentである。Market Contextは市場全体の状態を要約し、Corporate Event Authorityは銘柄別の上場状態、決算予定、業績修正、配当修正、TOB、株式分割・併合等のPIT事実を提供する。

上位SoT:

```text
docs/02_architecture/strategy_architecture_v1.md
```

## 2. 目的

Market Contextは、Portfolio Policy、Position Management、Portfolio Constructionに対して、市場全体の姿勢をreason付きで提供する。

目的:

- market trendの把握
- market breadthの把握
- volatility regimeの把握
- sector dispersionの把握
- Strategy aggressiveness / defensive postureの補助
- Performance attributionでのregime分類

## 3. 非目的

Market Contextは以下をしない。

- 将来return予測
- 特定銘柄のBUY/SELL直接決定
- PM判断の上書き
- Safety hard limit決定
- Broker実行判断
- Historical Run損益の利用
- 銘柄別Corporate Event事実の最終評価
- 上場廃止、決算跨ぎ、TOBを理由にした個別銘柄BUY/SELL判断

## 4. 入力Authority

使用可能:

- J-Quants価格
- J-Quants出来高
- J-Quants Listed Issues
- Trading Calendar
- J-Quants由来Feature
- 当日時点までの市場・sector統計

禁止:

- Historical Run損益
- Backtest結果
- Paper Ledger
- Portfolio PnL
- 約定結果
- Future Return
- 将来Market Regime
- MFE / MAE
- Test合否

## 5. 初期Output Schema候補

```yaml
schema_version: strategy_market_context.v1
business_date: 2026-07-27
as_of: 2026-07-27T08:30:00+09:00
feature_date: 2026-07-24
trend_regime: BULL
trend_strength: 0.72
market_breadth: STRONG
volatility_regime: NORMAL
sector_dispersion: MODERATE
confidence: 0.68
uncertainty: MODERATE
artifact_lifecycle_status: DRAFT
source_authority_status: VALID
producer_result_status: PASS
runtime_consumer_eligibility: NOT_ELIGIBLE
reason_codes:
  - BROAD_MARKET_MOMENTUM
source_artifacts:
  - runtime_feature_market_snapshot
source_hashes: []
temporal_safety:
  point_in_time: true
  future_leakage_used: false
```

`authority_status: ACCEPTED` は使用しない。`ACCEPTED` はArtifact Acceptance Contract上のRegistry lifecycle statusとして予約される。

## 6. Regime Taxonomy

Market Contextは単一の巨大な `market_regime` enumではなく、軸別に表現する。

| Axis | Values | 同時成立 |
|---|---|---|
| `trend_regime` | `BULL`, `BEAR`, `RANGE`, `RECOVERY`, `CORRECTION` | 1つだけ |
| `volatility_regime` | `HIGH`, `NORMAL`, `LOW` | 1つだけ |
| `market_breadth` | `STRONG`, `NEUTRAL`, `WEAK` | 1つだけ |
| `sector_dispersion` | `HIGH`, `MODERATE`, `LOW` | 1つだけ |

異なる軸は同時成立可能である。例として `trend_regime=BULL` かつ `volatility_regime=HIGH` は有効である。閾値や計算窓は本Taskでは決めない。

## 7. 欠損・低confidence処理

| 状態 | 扱い |
|---|---|
| source artifact missing | `REVIEW_REQUIRED` |
| invalid schema | `BLOCK` |
| source hash mismatch | `BLOCK` |
| stale feature date | `REVIEW_REQUIRED` |
| low confidence | valid artifactとしてneutral / defensive Policyへ遷移可能 |
| conflicting signals | `REVIEW_REQUIRED`。valid artifactとして扱う場合もconflict reason必須 |

暗黙fallbackは禁止する。

missing sourceをneutralとして暗黙補完しない。Neutral / Defensive Policyを使う場合は、そのPolicyが正式Accepted Authorityとして存在することを条件にする。

## 8. Consumer Contract

Consumers:

- Portfolio Policy
- Portfolio Construction
- Position Management
- Performance Attribution

Market Contextは判断材料として渡す。個別銘柄Momentum、Opportunity、Safetyを機械的に上書きしない。

Corporate Event factsが必要な場合、ConsumerはCorporate Event Authorityを参照する。Market ContextはCorporate Event Authorityを代替しない。

## 9. Phase22実装単位

1. read-only Market Context Artifact schema
2. J-Quants PIT input resolver
3. deterministic feature calculation
4. confidence / uncertainty fields
5. Portfolio Policy consumer fixture
6. no-leakage tests
7. artifact acceptance / registry integration

## 10. Open Decisions

| Decision | Status | 必要Evidence |
|---|---|---|
| TOPIX等benchmarkを入力に含めるか | OPEN_DESIGN_DECISION | J-Quants/外部Benchmark authority |
| sector mapping authority | OPEN_DESIGN_DECISION | Listed Issues/sector source coverage |
| trend_strength閾値 | OPEN_DESIGN_DECISION | multi-regime historical diagnostic |
| volatility計算窓 | OPEN_DESIGN_DECISION | PIT feature stability |
