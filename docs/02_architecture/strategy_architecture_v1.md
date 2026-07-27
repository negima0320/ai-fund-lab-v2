# Strategy Architecture v1

作成日: 2026-07-27

## 1. 目的と範囲

本書はAI Fund Lab v2のStrategy Layer最上位Source of Truthである。Phase21以降のStrategy設計、Phase22実装、Phase23検証、Production運用レビューでは、本書をStrategy責務と境界の基準にする。

AI Fund Lab v2の目的は、Production環境で安全・再現可能・監査可能に自律運用できる日本株AIファンドを構築し、年率+50%を目標とすることである。年率+50%は目標であり、保証ではない。

Strategy Layerの責務は、J-Quants由来のPoint-in-TimeデータとAccepted Artifact Authorityを使い、投資対象、投資姿勢、資金配分目標、Portfolio構成、HOLD / ADD / REDUCE / EXIT intentを決めることである。

Runtimeの責務は、Strategy intentを運用順序、Authority、Pending、Submit、Execution、Ledger、Current、AuditのContractに従って安全に処理することである。RuntimeはMarket Regime、Ranking、Position Count、Exposure target、Strategy fallback、Performance最適化を判断しない。

Safetyの責務は、Strategy targetを最適化することではなく、危険なintentをBlockまたはReviewすることである。Strategy targetとSafety hard limitは別のAuthorityである。

Broker / Executionの責務は、承認済みExecution intentをBroker制約と実注文Contractへ変換し、結果をLedger / Currentへ反映することである。StrategyはBroker quantity、lot rounding、availability、fill priceを直接決めない。

## 2. 投資哲学

AI Fund Lab v2の投資哲学は、日本株スイング・モメンタム投資である。

基本思想:

```text
良い企業
かつ
上昇が始まり
かつ
まだ上昇余地が残っている銘柄を発見し、
トレンド継続から利益を得る。
```

期待保有期間は概ね5から30営業日である。Phase21では投資哲学を別戦略へ変更しない。

Strategy v1の原則:

- long-only cash equity
- leverageなし
- short sellingなし
- entryはMomentum開始と上昇余地を重視する
- HOLDはTrend continuationとProfit expansionを重視する
- ADDは買い増し候補intentであり、直接注文ではない
- REDUCEはrisk低減intentであり、数量候補はCapital Deployment / Sell Planning互換経路が決める
- EXITはfull close intentである
- Loss containmentとCapital preservationを無視しない
- Market Contextは判断材料であり、個別Opportunityを機械的に上書きしない

## 3. Strategy Layer Component Map

Formal target architecture:

```text
J-Quants PIT Data
  -> Feature Layer
  -> Corporate Event Authority
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

`Portfolio Manager` は実体Component名として使用しない。使用する場合は、`Portfolio Policy Engine`、`Position Management AI`、`Portfolio Construction`を束ねる論理的総称に限定する。同じ表や同じ矢印上で、論理的総称と実体Componentを混在させない。

Current implementationは、Candidate / Opportunity / PM / Capital Deployment / Planningが分散して存在する。Phase22では一括置換せず、Market Context Artifact、Portfolio Policy Artifact、Capital Deployment Contract refactorの順で追加する。

## 3.1 Strategy Responsibility Matrix

| Component | Responsibility | Input | Output | Authority | Does Not Decide | Consumer |
|---|---|---|---|---|---|---|
| Market Context Engine | 当日時点までの市場状態を軸別に要約する | J-Quants PIT価格、出来高、Listed Issues、Trading Calendar、feature artifacts | Market Context Artifact | Market Context Evidence Authority | 個別銘柄BUY/SELL、Safety hard limit、Broker feasibility | Portfolio Policy、PM、Portfolio Construction、Performance |
| Corporate Event Authority | 銘柄別企業イベントのPIT事実を提供する | J-Quants PIT Listed Issues、announcement schedule、corporate action source candidates | Corporate Event Artifact | Corporate Event Fact Authority | BUY/SELL、HOLD/ADD/REDUCE/EXIT、Target Weight、Runtime判断 | Candidate、Opportunity、Portfolio Policy、PM、Portfolio Construction、Safety |
| Candidate AI | 投資候補母集団と候補品質を出す | J-Quants PIT features、Corporate Event facts、Accepted Generation | Candidate ranking | Candidate Universe Authority | Ranking最終採用、target weight、注文可否、決算/上場廃止だけの売却決定 | Opportunity AI、Portfolio Construction |
| Opportunity AI | 候補間のexpected edgeとranking evidenceを出す | Candidate output、Opportunity features、Corporate Event facts、Accepted Generation | Opportunity ranking | Opportunity Ranking Authority | Ranking上位をBUY確定にすること、決算跨ぎ禁止、portfolio制約判断 | Portfolio Construction、PM reference |
| Portfolio Policy Engine | Portfolio全体の投資姿勢、target cash/exposure/count、permission/biasを出す | Market Context、Corporate Event aggregate risk、Current summary、Opportunity breadth、risk evidence | Portfolio Policy Artifact | Portfolio-level Target / Permission / Posture Authority | 個別銘柄の最終組入、Broker quantity、Safety override | Portfolio Construction、Capital Deployment、PM |
| Position Management AI | 既存positionごとのHOLD/ADD/REDUCE/EXIT intentを出す | Current position、PM features、Opportunity reference、Market Context、Corporate Event facts、Portfolio Policy refs | PM Decisions Artifact | Existing Position Intent Authority | 新規銘柄選定、target portfolio全体最適化、新Action追加、株数、Submit許可 | Portfolio Construction、Sell Planning互換経路 |
| Portfolio Construction | Candidate、Opportunity、PM intent、Portfolio Policy、Corporate Event facts、Current、Pendingを統合しTarget Portfolioを決める | Rankings、PM decisions、Portfolio Policy、Corporate Event facts、Current、cash、sector、Pending | Target Portfolio、Strategy Intent | Target Portfolio Decision Authority | Broker quantity、lot rounding、buying power確定、Submit許可 | Capital Deployment |
| Capital Deployment | Target Portfolio差分をnotional / quantity候補へ変換し実行可能性を評価する | Strategy Intent、Current、cash、Pending、policy、price/lot evidence | Allocation Candidate / Capital Allocation Decision | Allocation Candidate Authority | Target Portfolio決定、Safety override、Runtime approval、Broker submit | Runtime Planning、Safety |
| Runtime Planning | Allocation CandidateをRuntime Execution Intent / Pending Candidateへ変換する | Allocation Candidate、Current、Pending、approval requirements、order condition authority | Runtime Execution Intent、Pending Candidate | Runtime Planning / Pending Authority | Ranking、PM判断、target weight、Safety判断 | Safety、Approval、Pending Composition、Submit |
| Safety | 危険なintentをBlock / Reviewする | Runtime Execution Intent、Current、Policy、Broker evidence、Safety policy | Safety decision | Safety Block / Review Authority | Strategy target最適化、lot rounding、ranking | Runtime、Submit |
| Runtime | 運用順序、Authority検証、Pending、Submit、Ledger、Current、Lifecycle、Auditを制御する | accepted authorities、Runtime state、Pending、Safety、Broker state | ordered operation、ledger/current/report | Operation / Lifecycle / Current / Ledger Authority | Strategy判断、Market Context算出、position sizing式決定 | Operator、Broker adapter、Reports |
| Broker / Execution | 承認済み注文をBroker制約と実注文Contractへ変換し結果を返す | approved Runtime order、Broker session、availability | broker order、execution/fill result | Broker Execution Authority | 投資判断、target weight、Safety policy | Runtime Ledger、Current |

## 3.2 Decision Authority Chain

Strategy Layerの最終投資意思決定は、次のAuthority chainで成立する。

```text
Market Context Evidence
  -> Corporate Event Facts
  -> Portfolio Policy
  -> Candidate / Opportunity Evidence
  -> Position Management Intent
  -> Portfolio Construction Target Portfolio Decision
  -> Capital Deployment Allocation Candidate
  -> Runtime Planning Execution Intent
  -> Safety / Approval / Pending
  -> Submit / Execution
```

重要な否定条件:

```text
Ranking上位 = BUYではない
PM ADD = BUYではない
Portfolio Policy ALLOWED = BUYではない
Corporate Event fact = 自動BUY/SELLではない
Capital Deployment feasible = Submit許可ではない
```

最終的に「どの銘柄を、どのTarget WeightでPortfolioへ組み入れるか」を決めるAuthorityは `Portfolio Construction` である。これは `Target Portfolio Decision Authority` と呼ぶ。

`Capital Deployment` はTarget Portfolioを変更しない。Capital DeploymentはTarget Portfolio差分を、notional、quantity candidate、cash feasibility、exposure feasibility、lot viability、rejection reasonへ変換する `Allocation Candidate Authority` である。

`Runtime Planning` はRuntime Execution Intent / Pending Candidateを生成する。これは運用・Pending化のAuthorityであり、StrategyのTarget Weightを再判断しない。

`Safety` はBlock / Review Authorityであり、危険なintentを止めることはできるが、より良いportfolioへ最適化しない。

`Corporate Event Authority` は事実Authorityであり、上場状態、決算予定、業績修正、配当修正、TOB、株式分割・併合などをPITで提供する。Corporate Event Authorityは投資判断を行わない。

## 3.3 Intent and Allocation Ownership

Strategy Intent:

```text
symbol
current_weight
target_weight
weight_delta
intent_type
priority
reason_codes
source_decision_refs
```

Owner:

```text
Portfolio Construction
```

Allocation Candidate:

```text
target_notional
delta_notional
quantity_candidate
lot_rounding_result
cash_feasibility
exposure_feasibility
rejection_reason
```

Owner:

```text
Capital Deployment
```

Runtime Execution Intent:

```text
side
quantity
order_condition_authority_ref
target_session
source_allocation_ref
approval_requirements
```

Owner:

```text
Runtime Planning
```

Portfolio ConstructionはBroker quantityやlot roundingを決めない。Capital DeploymentはTarget Portfolioを決めない。Runtime PlanningはRanking、PM intent、Target Weightを再計算しない。

## 3.4 Status Taxonomy

`ACCEPTED` はArtifact Acceptance Contract上のRegistry lifecycle statusとして予約する。日次生成されるStrategy decision artifactの検証状態を表すfieldに、同じ意味でない `authority_status: ACCEPTED` を使ってはならない。

| Status Family | Field | Allowed values | Meaning |
|---|---|---|---|
| Artifact Lifecycle Status | `artifact_lifecycle_status` | `DRAFT`, `VALIDATED`, `REVIEW_REQUIRED`, `ACCEPTED`, `LEGACY`, `REVOKED`, `REJECTED` | Registry Artifact Acceptance Contractのlifecycle |
| Source Authority Status | `source_authority_status` | `VALID`, `MISSING`, `STALE`, `HASH_MISMATCH`, `AUTHORITY_CONFLICT` | source artifactやsource hashのAuthority状態 |
| Producer Result Status | `producer_result_status` | `PASS`, `REVIEW_REQUIRED`, `BLOCK` | producerが日次artifact生成に成功したか |
| Consumer Eligibility | `runtime_consumer_eligibility` | `ELIGIBLE`, `NOT_ELIGIBLE`, `REVIEW_REQUIRED`, `BLOCKED` | Runtime consumerがそのartifactを読めるか |
| Runtime Decision Status | `runtime_decision_status` | `PENDING`, `APPROVED`, `REVIEW_REQUIRED`, `BLOCKED`, `SUBMITTED`, `REJECTED` | Runtime planning / approval / submit上の状態 |

Mandatory rule:

```text
Registry Artifact Lifecycle ACCEPTED
と
Daily Strategy Decision Authority Validated
を同じfield/valueで表現しない。
```

## 4. Current Architecture Inventory

| Component | Current responsibility | Implementation path | Config path | Input | Output | Authority | Current limitation | Target responsibility | Phase22 change |
|---|---|---|---|---|---|---|---|---|---|
| Candidate AI | Candidate Top候補生成 | `src/ai_fund_lab_v2/candidate_ai/` | Accepted Generation / registry | J-Quants features | Candidate ranking | Accepted AI Generation | Portfolio contextなし | 候補母集団と候補品質を提供 | Market Context / sector evidenceを入力候補に追加 |
| Opportunity AI | CandidateからOpportunity順位生成 | `src/ai_fund_lab_v2/opportunity_ai/`, runtime BUY producer | Accepted Generation / registry | Candidate output, opportunity features | Opportunity ranking | Accepted AI Generation | Ranking上位がPortfolio制約と独立 | BUY候補品質とexpected edgeを提供 | Portfolio Constructionへ正式接続 |
| Position Management AI | 既存保有のHOLD/ADD/REDUCE/EXIT | `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py` | `POSITION_MANAGEMENT_POLICY_SET` | Current, PM features, Opportunity | PM decisions | Artifact Registry accepted current path | Portfolio Policyが未分離 | Position decisionとPolicy intentを分ける | PM Policy Artifact追加 |
| Market Features | 日次特徴量生成 | `runtime_v2/market_refresh`, feature refresh系 | feature contract | J-Quants PIT | feature artifacts | J-Quants / feature date contract | Market Context Artifactなし | 市場・sector状態の入力 | Market Context Engine追加 |
| Market Context相当 | 明示Engineなし | なし | なし | なし | なし | なし | Bull/Bear/Range判断なし | 当日時点までの市場状態要約 | Artifact新設 |
| Corporate Event相当 | Runtime/Historical Guardやfeature断片のみ | standalone Strategy authorityなし | なし | Listed Issues、OHLCV AdjFactor、source候補 | no standalone event artifact | Corporate Action proxy / feature evidence | 決算予定、上場廃止予定、TOB等のStrategy Authorityなし | 銘柄別Corporate Event PIT事実Authority | Corporate Event Authority新設 |
| Morning Planning | BUY Pending生成 | `runtime_v2/planning/morning_pipeline.py` | capital policy | Opportunity ranking, Current, Safety | BUY Pending | Runtime Planning | Portfolio Constructionなし | Execution intentをPendingへ変換 | Target Portfolio入力へ対応 |
| Capital Deployment | 資金上限と注文notional制約 | `runtime_v2/policy/capital_deployment.py` | `configs/runtime_v2/capital_deployment.json` | Current, cash, policy | allocation fields | Capital Deployment Policy | 5銘柄/850,000円が固定Policy | Strategy targetとSafety hard limitを分離 | Dynamic policy contractへ拡張 |
| ADD Consumer | PM ADDをBUY Pendingへ変換 | `runtime_v2/planning/add_consumer.py` | capital policy | PM ADD, Current, cash | ADD-derived BUY Pending | Planning + Capital policy | Phase21-B最小実装 | ADD intentをPortfolio Constructionへ接続 | Target weight / policy reasonを追加 |
| Sell Planning | SELL Pending生成 | `runtime_v2/planning/sell_pipeline.py` | capital policy | PM EXIT/REDUCE, Current | SELL Pending | Current position authority | Portfolio targetとの差分売却なし | REDUCE/EXIT intentを実行可能SELLへ変換 | Target Portfolio差分へ対応 |
| Pending Composition | BUY/SELL canonical Pending合成 | `runtime_v2/pending/composition.py` | なし | existing Pending, SELL/ADD items | Composite Pending | canonical Pending | Phase21-Bで成立 | Runtime boundaryとして維持 | 変更不要、回帰必須 |
| Submit | canonical PendingのみSubmit | `runtime_v2/submit/pipeline.py` | policy, safety | `pending_order_plan/pending_order_plan.json` | broker order / ledger | Pending + Approval + Safety | Strategy判断しない | Runtime非冪等処理 | 変更不要 |
| Safety | 危険intentのBlock/Review | `runtime_v2/safety`, `safety_phase11` | safety policy | Runtime/Current/Broker evidence | Safety decision | Safety Authority | Strategy targetと混同禁止 | Hard limitとReview authority | Strategy targetとのConflict handling追加 |
| Ledger | orders/executions/positions/cash | `runtime_v2/ledger/` | なし | Submit/Execution | Persistent Ledger | Ledger SoT | Performance入力にはなるがStrategy入力禁止 | Audit/Performance authority | 変更不要 |
| Current | 現在資産状態 | `persistent_ledger/state.json` writers | なし | Ledger/Broker/Projection | Current asset state | Current SoT | Strategy学習入力禁止 | Runtime decision input | 変更不要 |
| Performance Observability | Run成績・属性分析 | `runtime_v2/ledger/performance_events.py`, reports | run evidence | Ledger/run evidence | metrics | Post-hoc diagnostic | Runtime/Training入力禁止 | Phase23評価Contract | Contract正式化 |
| Benchmark | 設計Contractあり、実データ未整備 | `performance_metric_benchmark_experiment_contract.md` | 未定 | benchmark PIT data候補 | relative return | MISSING扱い | Benchmark authority未実装 | 評価専用Benchmark | Phase23で実装 |
| Sector | sector mapping一部候補 | opportunity market sector modules | 未定 | J-Quants listed/sector候補 | sector exposure | MISSING扱い | Sector concentration未正式 | Portfolio risk / attribution | Phase22/23で整備 |
| Artifact Registry | Accepted authority | `artifact_registry/` | `.runtime/artifact_registry` | manifest/events | accepted artifacts | Registry | source変更時refresh漏れリスク | Strategy artifact authority | Acceptance checklistへ統合 |

## 5. Current State vs Target State

| Area | Current | Target | Gap | Phase22 action |
|---|---|---|---|---|
| PM | HOLD/ADD/REDUCE/EXITを出す | Position DecisionとPortfolio Policyを分離 | Policy targetなし | PM Policy Artifact |
| Market Context | 明示なし | Bull/Bear/Range等の当日状態要約 | Artifactなし | Market Context Engine |
| Corporate Event | Runtime/Historical Guardやfeature断片 | 銘柄別Corporate Event PIT事実Authority | Strategy共通Contractなし | Corporate Event Authority |
| Capital Deployment | 固定Policyでnotional制約 | Strategy target / Safety hard limit / feasibility分離 | 固定値が戦略目標とhard limitを兼ねる | Contract refactor |
| Position Count | `max_positions=5` | Dynamic Position Count | quality/opportunity breadth未考慮 | Dynamic count owner定義 |
| Cash Ratio | `target_investment_ratio=0.85`, `cash_buffer=0.05` | Target cash ratioとminimum cash floor分離 | 20% cashの意味未確定 | Phase22 default + experiment |
| Position Sizing | Planning budget / max weight中心 | Target weight -> allocation -> lot | confidence/vol/liquidity未統合 | sizing policy設計 |
| Ranking | Opportunity ranking中心 | Portfolio-aware selection | sector/cash/current連携弱い | Portfolio Construction |
| HOLD/ADD/REDUCE/EXIT | PM単体判断 | Market/Policy/Sector影響をreason化 | contextなし | PM context integration |
| Portfolio Construction | 明示なし | Target portfolio方式を候補採用 | action-basedのみ | Target portfolio artifact |
| Sector awareness | 未正式 | concentration/risk/attribution | mapping authority未整備 | sector authority設計 |
| Benchmark awareness | 評価Contractのみ | TOPIX等の相対評価 | data authority未整備 | Phase23評価 |
| Performance metrics | Phase20 contract | Phase23 acceptance contract | Strategy採用基準未統一 | requirements化 |
| Experiment contract | Phase20比較Contract | Single-change / multi-regime / out-of-period | Phase22/23境界未明確 | requirements化 |

## 6. Market Context Architecture

Market Contextは未来予測ではなく、当日時点までの市場状態の要約である。

Market Contextは単一の巨大な `market_regime` enumではなく、複数軸として表現する。

| Axis | Values | 同時成立 |
|---|---|---|
| `trend_regime` | `BULL`, `BEAR`, `RANGE`, `RECOVERY`, `CORRECTION` | 1つだけ |
| `volatility_regime` | `HIGH`, `NORMAL`, `LOW` | 1つだけ |
| `market_breadth` | `STRONG`, `NEUTRAL`, `WEAK` | 1つだけ |
| `sector_dispersion` | `HIGH`, `MODERATE`, `LOW` | 1つだけ |

異なる軸は同時成立可能である。例として、`trend_regime=BULL` かつ `volatility_regime=HIGH` は有効である。閾値や計算窓はPhase22/23のOpen Decisionであり、本書では決めない。

入力Authority:

- J-Quants価格
- 出来高
- Listed Issues
- Trading Calendar
- J-Quants由来Feature
- 当日時点までの市場・sector統計

禁止入力:

- Historical Run損益
- Backtest結果
- Paper Ledger
- Portfolio PnL
- Future Return
- 将来Market Regime
- Test合否

Output例:

```yaml
schema_version: strategy_market_context.v1
business_date: 2026-07-27
as_of: 2026-07-27T08:30:00+09:00
trend_regime: BULL
trend_strength: 0.72
market_breadth: STRONG
volatility_regime: NORMAL
sector_dispersion: MODERATE
confidence: 0.68
artifact_lifecycle_status: DRAFT
source_authority_status: VALID
producer_result_status: PASS
runtime_consumer_eligibility: NOT_ELIGIBLE
reason_codes:
  - BROAD_MARKET_MOMENTUM
source_artifacts: []
source_hashes: []
```

欠損時は暗黙fallbackしない。

| Condition | Handling |
|---|---|
| source missing | `REVIEW_REQUIRED` |
| invalid schema | `BLOCK` |
| hash mismatch | `BLOCK` |
| low confidence | valid artifactとして扱える場合のみneutral / defensive Policyへ遷移可能 |
| conflicting signals | `REVIEW_REQUIRED`。valid artifactとして扱う場合もconflict reasonを必須にする |

Neutral / Defensive Policyを使う場合は、そのPolicyが正式Accepted Authorityとして存在することを条件にする。missing sourceをneutralとして暗黙補完しない。

## 7. Corporate Event Authority Architecture

Corporate Event Authorityは、企業イベントのPIT事実を提供する。これはStrategy判断材料であり、投資判断そのものではない。

対象候補:

- listed status
- delisting status
- supervision status
- liquidation status
- final trading date
- earnings schedule
- earnings release time
- earnings disclosed
- earnings period
- forecast revision
- dividend revision
- TOB
- wholly owned subsidiary transaction
- share exchange
- stock split / reverse split
- other corporate action

入力Authority:

- J-Quants PIT Listed Issues
- J-Quants announcement / earnings schedule source候補
- J-Quants corporate action source候補
- Trading Calendar
- source artifacts / source hashes

禁止:

- 発表後データを発表前へ使う
- 決算発表時刻を無視して同日朝に発表後情報を使う
- 将来公表された上場廃止予定を過去へ適用する
- coverage不足を「イベントなし」と扱う
- missingをsafe扱いする

Earnings Contract minimum fields:

- `scheduled_earnings_date`
- `scheduled_earnings_time`
- `earnings_disclosed`
- `days_to_earnings_business`
- `forecast_revision_status`
- `dividend_revision_status`
- `source_hashes`
- `source_artifacts`
- `coverage_status`
- `temporal_safety`

Delisting Contract minimum fields:

- `listed_status`
- `delisting_announced`
- `supervision_status`
- `liquidation_status`
- `final_trading_date`
- `corporate_action_type`
- `effective_date`
- `source_hashes`
- `source_artifacts`
- `source_authority_status`

Corporate Eventは以下をしない。

- BUY判断
- SELL判断
- Portfolio判断
- HOLD / ADD / REDUCE / EXIT判断
- Runtime判断

Consumer responsibility:

| Consumer | Allowed use | Prohibited use |
|---|---|---|
| Candidate AI | 決算予定、企業イベント、上場状態を候補品質Evidenceとして使う | 決算だけで候補除外、上場廃止だけで売却決定 |
| Opportunity AI | 決算イベントrisk、post-earnings momentum、forecast revision、corporate actionをranking evidenceとして使う | 決算跨ぎ禁止、Portfolio weight決定 |
| Portfolio Policy Engine | 決算跨ぎを許容する市場/Portfolio posture、risk posture、cash postureを出す | 個別銘柄BUY/SELL、final target weight |
| Position Management AI | Corporate EventをHOLD/ADD/REDUCE/EXIT reasonとして使う | 新しいAction追加、Broker quantity決定 |
| Portfolio Construction | 新規BUY可否、Target Weight、Target Portfolio採用/除外をPortfolio全体で判断する | Broker quantity、lot rounding、Submit許可 |
| Safety | 最終売買日超過、authority欠損、hash mismatch、trading禁止をBlock / Reviewする | Strategy最適化 |
| Runtime | Authority検証、Execution、Pending、Submitを行う | 決算判断、上場廃止判断、企業イベント評価 |

PM reason候補:

- `EARNINGS_APPROACHING`
- `HOLD_THROUGH_EARNINGS_ALLOWED`
- `REDUCE_BEFORE_EARNINGS`
- `EXIT_BEFORE_EARNINGS`
- `POST_EARNINGS_MOMENTUM_CONFIRMED`
- `POST_EARNINGS_GAP_REVERSAL`
- `FORECAST_REVISION`
- `DIVIDEND_REVISION`
- `DELISTING_PENDING`

Position Management AIの正式Actionは、現時点では `HOLD`、`ADD`、`REDUCE`、`EXIT` の4つを維持する。Corporate Eventを理由に新しいActionを暗黙追加しない。

## 8. Portfolio Policy and Position Management Architecture

`Portfolio Manager` は論理的総称であり、実体Componentではない。正式な実体Componentは以下である。

Portfolio Policy Engine:

- aggressiveness
- defensive posture
- target cash ratio
- target gross exposure
- minimum / target / maximum position count
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

PMが判断しないもの:

- Broker quantity
- 実注文株数
- lot rounding
- final submit permission
- Safety override
- Broker availability
- fill price

Portfolio Policy EngineはPortfolio-level target / permission / postureを出す。Position Management AIは既存positionのintentを出す。Portfolio Constructionは両者とCandidate / Opportunity evidenceを統合してTarget Portfolioを決める。

## 9. Portfolio Policy Contract

Output例:

```yaml
schema_version: portfolio_policy.v1
business_date: 2026-07-27
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
confidence: 0.71
reason_codes:
  - BROAD_MARKET_MOMENTUM
  - STRONG_OPPORTUNITY_BREADTH
artifact_lifecycle_status: DRAFT
source_authority_status: VALID
producer_result_status: PASS
runtime_consumer_eligibility: NOT_ELIGIBLE
```

単一ラベルではなく、confidence、reason_codes、source hashesを持つ。不確実な場合は中立または防御寄りに倒す。Target値とSafety hard limitを混同しない。

## 10. Capital Deployment Architecture

現行Policy:

```text
evaluation_capital=1,000,000
target_investment_ratio=0.85
cash_buffer=0.05
max_exposure=850,000
max_position_weight=0.20
max_positions=5
```

Phase21-Dでは値を変更しない。Phase22設計では以下に分離する。

Strategy Target:

- target cash ratio
- target exposure
- target position count
- target position weight

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

Liquidityは用途を分ける。

| Use | Owner |
|---|---|
| Strategy sizing input | Portfolio Policy / Capital Deployment |
| Risk hard limit | Safety |
| Broker execution feasibility | Runtime Planning / Broker adapter |

Safetyはlot roundingを行わない。lot rounding evidenceはCapital Deploymentが候補として記録し、Runtime Planning / Broker adapterが実際のBroker制約と照合する。

20% cashの判断:

```text
採用: D. Market Context dynamic target with 20% standard baseline
```

20%はPhase22初期default baseline候補であり、Permanent fixed targetでもhard safety floorでもない。Safety floorは別Authorityで定義する。Evidence不足のため、20%をProduction恒久値として固定しない。

## 11. Dynamic Position Count

Dynamic Position CountのownerはPortfolio Policy Engineである。Capital DeploymentはPolicy targetを実行可能数量候補へ変換し、Safetyはhard capを適用する。

入力候補:

- Market Context
- Qualified Opportunity count
- Opportunity score distribution
- Candidate quality
- Sector concentration
- Liquidity
- Current portfolio
- Current cash
- Position size viability
- Single-name risk
- Correlation proxy

原則:

```text
良い候補が2件なら2件
良い候補が0件なら0件
良い候補が多くてもRisk / Sector / Cash制約を超えない
```

枠を埋めるための低品質BUYは禁止する。

## 12. Position Sizing

Phase22 initial designはHybrid方式を採用候補にする。

```text
base equal weight
+ opportunity confidence adjustment
+ volatility / liquidity adjustment
+ sector / single-name risk cap
```

責務境界:

- Portfolio Policy Engineはtarget posture / constraints / confidenceを出す
- Portfolio ConstructionがTarget Portfolio上のtarget weightを決める
- Capital Deploymentがnotionalとquantity candidateへ変換する
- Safetyがhard capを適用する
- Runtime Planning / Broker adapterがBroker制約を最後に照合する

禁止:

- PMが直接株数を決定する
- Historical PnLから銘柄別倍率を学習する
- 特定Runの勝ち銘柄へ重み付けする
- Future return imitation

## 13. Position Management Contract

HOLD:

- trend continuationが成立し、risk / opportunity deteriorationが許容範囲内のとき保有継続する

ADD:

- 強い上昇継続とPortfolio余力があるときの買い増し候補intent
- 直接注文ではない
- Portfolio Construction / Capital Deployment / Safety / Runtime Planningを通過して初めてPending Candidateになる

REDUCE:

- trend弱化、peak drawdown、risk上昇、market posture悪化などで一部縮小を示すintent
- broker quantityはPMが決めない

EXIT:

- full close intent
- trend break、loss containment、重大risk、opportunity deteriorationなどで発生する

Decision priority:

```text
EXIT > REDUCE > ADD > HOLD
```

ただしBUY/SELL conflict、duplicate pending、minimum holding period、cooldown、Safety conflictはArtifact上でreasonを残して解決する。

Policy owner:

| Policy | Owner | Notes |
|---|---|---|
| minimum holding period | Position Management Policy | 具体値はOpen Decision |
| ADD cooldown | Position Management Policy | Strategy churn抑制。Runtime duplicate guardではない |
| REDUCE cooldown | Position Management Policy | Strategy churn抑制。Runtime duplicate guardではない |
| re-entry cooldown | Portfolio Construction conflict policy | 退出後の再組入判断をTarget Portfolio conflictとして扱う |
| profit protection threshold | Position Management Policy | 具体閾値はpost-hoc diagnostic後に決める |
| loss containment threshold | Position Management Policy | Safety stopとは別 |
| Safety stop | Safety | emergency block/review authority |

Runtime duplicate guardは、同じ注文の二重生成・二重Submitを防ぐRuntime責務である。Strategy cooldownは、意思決定の過剰反転やchurnを防ぐStrategy Policy責務である。

## 14. Regime-aware Decision Design

Market Contextは判断材料であり、個別銘柄MomentumとOpportunityを上書きする万能ルールではない。

例:

| Regime | BUY | HOLD | ADD | REDUCE / EXIT | Exposure |
|---|---|---|---|---|---|
| Bull | 許容度高 | 長め | 許容 | 遅め | 高め |
| Bear | 厳選 | 短め | 制限 | 優先 | 低め |
| Range | 厳選 | 利確早め | 限定 | 回転重視 | 中程度 |

固定表を絶対ルールにしない。理由とconfidenceを必須にする。

## 15. Candidate / Opportunity / Ranking Contract

Candidate AIは投資候補母集団と候補品質を提供する。Opportunity AIは候補間の相対的Opportunity、expected edge、ranking evidenceを提供する。Corporate Event Authorityは決算予定、上場状態、業績修正、配当修正、TOB等のPIT事実を提供する。Portfolio ConstructionはRanking、Portfolio Policy、PM intent、Corporate Event facts、Risk、Sector、Cash、Current、Pendingを統合し、Target PortfolioとStrategy Intentを作る。

```text
Ranking上位 = 必ず購入
```

ではない。Portfolio Policy、Portfolio Construction、Capital Deployment、Safety、Runtime Planningを通過して初めてRuntime Execution Intent候補になる。

新規BUYとADDは別intentとして保持するが、Portfolio Constructionでは同じtarget portfolio差分として統合評価できる。

## 16. Portfolio Construction

入力:

- Portfolio Policy
- Candidate Ranking
- Opportunity Ranking
- PM Position Decisions
- Corporate Event facts
- Current Portfolio
- Cash
- Exposure
- Sector state
- Pending orders

出力:

- Target portfolio
- Target position weights
- Strategy Intent
- New BUY / ADD / REDUCE / EXIT intent classification
- Rejection reasons
- construction evidence

Target Portfolio方式はPhase22で採用候補とする。現行Action-based方式とは、Target Portfolioから差分を計算し、差分をBUY / ADD / REDUCE / EXIT intentへ落とすことで互換にする。

例:

```yaml
schema_version: target_portfolio.v1
business_date: 2026-07-27
cash_target: 0.20
positions:
  - symbol: "9432"
    current_weight: 0.08
    target_weight: 0.12
    intent: ADD
```

## 17. Runtime Boundary

Runtimeは以下をしない。

- Market Regime判断
- Corporate Event評価
- 決算判断
- 上場廃止判断
- Position Count決定
- Exposure target決定
- Ranking変更
- PM判断変更
- Strategy fallback
- Performance最適化

Runtimeの責務:

- Operation sequencing
- Authority validation
- Pending composition
- Submit
- Fill
- Ledger
- Current
- Lifecycle
- Audit
- Fail-closed

## 18. Safety Boundary

Strategy targetとSafety hard limitを分離する。

例:

```text
Strategy target exposure = 80%
Safety absolute max exposure = 90%
```

具体値はPhase22/23でEvidenceに基づき決める。SafetyはStrategyを最適化しない。Safetyは危険なIntentをBlock / Reviewする。

Corporate Eventに関するSafety例:

- final trading date exceeded -> `BLOCK`
- Corporate Event authority missing -> `REVIEW_REQUIRED`
- Corporate Event hash mismatch -> `BLOCK`
- trading prohibited -> `BLOCK`

## 19. Authority and Artifact Contract

Strategy artifacts候補:

- Market Context Artifact
- Corporate Event Artifact
- Portfolio Policy Artifact
- PM Decisions Artifact
- Portfolio Construction Artifact
- Capital Allocation / Deployment Artifact
- Runtime Execution Intent Artifact
- Performance Evaluation Artifact

各Artifactは以下を持つ。

- schema version
- business date
- as-of
- source artifacts
- source hashes
- artifact lifecycle status
- source authority status
- producer result status
- runtime consumer eligibility
- confidence
- reason codes
- provenance
- temporal safety
- lineage

Production共通source pathを変更した場合、Artifact Acceptance refreshが必要である。hash mismatchをwarning化してはならない。

## 20. Production / Demo / Historical Contract

```text
Strategy logic: common
Feature logic: common
Market Context: common
Corporate Event Authority: common
PM: common
Capital Deployment: common
Portfolio Construction: common
Runtime: common
Environment differences: Adapter only
```

Historical専用Profit logicは禁止する。
Historical専用Corporate Event logicは禁止する。環境差はAdapterのみで吸収する。

## 21. Performance Evaluation Contract

KPI候補:

- Total Return
- CAGR / annualized return
- Maximum Drawdown
- Volatility
- Sharpe-like metric
- Cash Ratio
- Cash Utilization
- Gross Exposure
- Turnover
- Position Count
- Single-name Concentration
- Sector Concentration
- Benchmark Relative Return
- Win / Loss
- Holding Period
- Profit Retention
- Profit Giveback
- ADD / REDUCE / EXIT contribution
- Market Regime attribution

Performance EvidenceはPost-hoc diagnosticであり、Runtime / Training / Calibration入力にしない。Training authorityはJ-Quants由来データのみである。

## 22. Experiment Contract

Phase23 Experimentは以下を必須にする。

- Baseline
- Variant
- Single-change principle
- Run windows
- Bull / Bear / Range
- Long-run
- Out-of-period evaluation
- Regression
- Risk metrics
- Rollback
- Acceptance / Reject / Review criteria

Returnだけで採用しない。Drawdown、cash utilization、turnover、concentration、Runtime regression、Authority、Safetyを同時に見る。

## 23. Failure Modes

| Failure | Default handling |
|---|---|
| Market Context source missing | `REVIEW_REQUIRED` |
| Market Context invalid schema | `BLOCK` |
| Market Context hash mismatch | `BLOCK` |
| Market Context low confidence | valid artifactとしてneutral / defensive Policyへ遷移可能 |
| Market Context conflicting signals | `REVIEW_REQUIRED`。valid artifactとして扱う場合もconflict reason必須 |
| Corporate Event source missing | `REVIEW_REQUIRED` |
| Corporate Event hash mismatch | `BLOCK` |
| Corporate Event coverage insufficient | `REVIEW_REQUIRED` |
| Earnings datetime unknown | `REVIEW_REQUIRED` |
| Corporate Event invalid schema | `BLOCK` |
| Corporate Event source authority conflict | `BLOCK` |
| Final trading date exceeded | `BLOCK` |
| No qualified candidates | `PASS` with no BUY |
| Too many candidates | Portfolio Constructionで選別 |
| Cash insufficient | `PASS` with rejection evidence |
| Lot not viable | `PASS` with rejection evidence |
| Sector concentration | `REVIEW_REQUIRED` またはrejection |
| Duplicate pending | `BLOCK` or rejection |
| Authority mismatch | `BLOCK` / HALT |
| Artifact hash stale | `BLOCK` / HALT |
| Current unknown | `BLOCK` |
| Portfolio Policy invalid | `BLOCK` |
| Target weights > 100% | `BLOCK` |
| Strategy / Safety conflict | Safety wins, `BLOCK` or `REVIEW_REQUIRED` |
| PM conflict | Priority rule + evidence |
| BUY / SELL conflict | Pending composition / conflict evidence |

## 24. Migration Plan

Phase22 Migrationの詳細SoT:

```text
docs/phase_reports/phase21_gb_strategy_migration_architecture_design.md
```

Phase22 Implementation Governance SoT:

```text
docs/phase_reports/phase21_gc_implementation_governance_and_phase22_entry_gate.md
```

Phase22 Cutover / Regression / Legacy Retirement SoT:

```text
docs/phase_reports/phase21_i_cutover_completeness_runtime_wiring_and_regression_preservation_audit.md
docs/phase_reports/phase21_j_legacy_retirement_authority_revocation_and_data_decommission_architecture.md
docs/phase_reports/phase21_k_final_design_freeze_phase21_closure_and_phase22_entry_approval.md
```

Phase21-K完了後、Strategy ArchitectureはDesign FreezeおよびPhase21 Closure状態とする。以降の設計変更はImplementation中のその場修正ではなく、Design Change Request、Impact Analysis、Architecture Review、Approval、Design更新、Implementationの順で扱う。

Phase22実装はProducer-firstで行う。Consumerを先に本番接続しない。

Producer-first dependency:

```text
Market Context + Corporate Event
  -> Candidate / Opportunity compatibility
  -> Portfolio Policy
  -> Position Management refs
  -> Portfolio Construction
  -> Capital Deployment
  -> Runtime Planning
  -> Safety / Runtime switch
```

Phase21-D/E時点のPhase22実装順:

1. Market Context Artifact
2. Corporate Event Artifact
3. Candidate / Opportunity compatibility
4. Portfolio Policy Artifact
5. Position Management refs
6. Portfolio Construction
7. Capital Deployment Contract refactor
8. Runtime Planning bridge
9. Dynamic Position Count
10. Target Cash Ratio
11. Position Sizing
12. Regime/Event-aware HOLD / ADD / REDUCE / EXIT
13. Evidence / Metrics
14. Regression

一括置換は禁止する。

Phase21-Kで最終固定されたPhase22-A scope:

Allowed:

```text
Market Context schema / producer / PIT source lineage / hash / status taxonomy / failure contract / bootstrap contract / read-only artifact generation / fixture consumer / produced-but-not-consumed detection / short unit, schema, contract tests
```

Prohibited:

```text
Runtime behavior switch / PM behavior change / Candidate ranking change / Opportunity ranking change / Portfolio weight change / Capital allocation change / Pending change / Submit change / Old path deletion / Long Historical Run by Codex
```

## 25. Acceptance Criteria for Phase22

Phase22実装は以下を満たす。

- Existing Regression PASS
- Runtime Contract維持
- Lifecycle維持
- Authority維持
- Safety維持
- Production / Demo / Historical共通
- J-Quants Data Boundary維持
- Duplicate order防止
- Artifact Acceptance整合
- Strategy artifact schema validation PASS
- Post-hoc performanceをRuntime/Training入力にしない
- Long-run採用前にmulti-regime評価を行う

## 26. Design Decision Records

| Decision | 採用案 | 代替案 | 理由 | Status |
|---|---|---|---|---|
| Market Context | 独立Engine | PM内部に埋め込む | Runtime非依存で監査可能にする | DECIDED |
| PMとPortfolio Policy | 分離Artifact候補 | 同一PM artifact | Position decisionと資金姿勢を分ける | DECIDED |
| Target Portfolio | Phase22採用候補 | Action-only継続 | BUY/ADD/REDUCE/EXITを一貫配分にする | DECIDED_AS_TARGET |
| Dynamic Position Count owner | Portfolio Policy | Runtime / Capital | Strategy targetでありRuntime責務ではない | DECIDED |
| Target Cash Ratio owner | Portfolio Policy | Safety / Runtime | targetとhard floorを分離する | DECIDED |
| 20% cash | dynamic targetのstandard baseline | fixed target / hard floor | Evidence不足のため恒久固定しない | DECIDED_AS_INITIAL_DEFAULT |
| 5銘柄固定 | 撤廃方針 | 維持 | quality/opportunity breadthに合わせる | DECIDED_AS_TARGET |
| 850,000円固定上限 | 撤廃方針 | 維持 | target/hard limit/feasibilityを分離する | DECIDED_AS_TARGET |
| Position Sizing | Hybrid候補 | equal only | confidence/risk/liquidityを扱う余地 | OPEN_DESIGN_DECISION |
| Market Context -> PM | reason/confidence入力 | hard rule | 個別Momentumを上書きしない | DECIDED |
| Strategy Target / Safety Limit | 分離 | 同一Policy | Safetyは最適化しない | DECIDED |
| BUY / ADD | intentは分離、Portfolio Constructionで統合評価 | 完全統合 | lineageと既存保有を保つ | DECIDED |
| Benchmark / Sector Authority | J-Quants/accepted data候補 | run evidence | Runtime入力にしない | OPEN_DESIGN_DECISION |
| Experiment Acceptance | Single-change + multi-regime | return only | 過学習防止 | DECIDED |

Open decisionsはPhase22実装前に必要Evidenceを明示して閉じる。
