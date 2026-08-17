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

Phase27-D3 freezes the PM performance philosophy for this Strategy SoT:

- 利益が出たこと自体をEXIT理由にしない。
- HOLDは「何もしない」ではなく、上昇トレンド継続への積極判断である。
- EXITは上昇トレンド終了、期待値低下、シグナル崩壊、急激なリスク悪化、またはSafety/Portfolio上の必要性に基づく。
- ADDは「買う候補がないから」ではなく、保有中の銘柄がなお最有力候補で、Trend ContinuingかつIncremental Value Existsの場合のみ検討する。
- REDUCEはHOLDとEXITの中間にあるrisk / weakening / partial rotation intentであり、単純な利益確定思想ではない。
- Cashは結果であって目的ではない。100万円の資金は期待値最大化資金であり、固定フルデプロイ義務ではない。
- Performance改善でBUY/HOLD/SELL Action Authorityを増やさない。

PM is the Strategy Action Authority for existing-position directional actions. Opportunity, BUY Quality, Market Context, Momentum Evidence, and Incremental Eligibility are Evidence Producers unless a later common SoT explicitly changes their authority mode. They must not independently emit BUY_NEW / ADD / HOLD / REDUCE / EXIT actions.

Phase27-D4 freezes the Expected Edge decision contract for this Strategy SoT.

Expected Edge means whether forward-looking expected value remains sufficiently attractive from Point-in-Time data. It is a Strategy concept consumed by PM; it is not the same as profit rate, trend alone, rank alone, BUY Quality alone, or cash availability.

Phase30-D promotes the Strategy Decision Quality / Continuation Quality research contract as a companion Architecture-level specification:

- [Strategy Decision Quality and Continuation Quality Contract](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/strategy_decision_quality_and_continuation_quality_contract.md)

Continuation Quality / Forward Edge is a research concept for evaluating whether a current PIT-observable upward continuation thesis remains relatively strong. It does not implement a new model, threshold, action authority, or Runtime behavior. It sits upstream of Expected Edge / Opportunity comparison as a research and audit contract.

Expected Edge is estimated from evidence including:

- Trend and momentum continuation evidence
- Opportunity score/rank evidence
- BUY Quality and signal reliability evidence
- Market Context evidence
- Portfolio Fit and concentration/risk evidence
- Execution Feasibility evidence

PM evaluates Expected Edge and decides `BUY_NEW`, `ADD`, `HOLD`, `REDUCE`, or `EXIT`. Other components provide evidence or constraints, not action decisions.

Important boundaries:

- Trend is Expected Edge evidence, not Expected Edge itself.
- Rank is Expected Edge evidence, not BUY/ADD/EXIT authority.
- BUY Quality is Expected Edge evidence, not Action Authority.
- Profit does not directly create EXIT. Profit may trigger Risk Review when a position has unusually large embedded gain, concentration, volatility, or drawdown-from-peak risk, but profit alone is not an independent sell philosophy.
- Cash is an outcome of Expected Edge, risk, sizing, and safety decisions; cash is not a reason to force BUY or ADD.

Phase27-D5 freezes the PM Expected Edge reasoning contract.

PM converts Expected Edge into Strategy action through a reasoning contract:

```text
Expected Edge Evidence
  -> PM Expected Edge Reasoning
  -> BUY_NEW / ADD / HOLD / REDUCE / EXIT
```

PM must not decide action from Trend alone, Rank alone, Profit alone, Market Context alone, or BUY Quality alone. Those are reason inputs and explanation evidence for Expected Edge.

Action boundaries without numeric thresholds:

- `BUY_NEW`: Expected Edge is sufficiently high for a no-position entry and entry evidence is coherent.
- `HOLD`: Expected Edge is maintained enough to continue the campaign. Small deterioration does not automatically become REDUCE or EXIT.
- `ADD`: Expected Edge has improved, the existing position remains a strongest opportunity, and incremental investment value exists.
- `REDUCE`: Expected Edge or risk/reward has weakened enough to reduce exposure while preserving optionality. REDUCE remains an independent action because it can express weakening/risk before full EXIT is justified.
- `EXIT`: Expected Edge has deteriorated enough that the campaign should close, or risk/Safety requires full close.

PM reason codes explain Expected Edge reasoning. They do not create separate Action Authority. Profit-related reason codes must be interpreted as Risk Review / peak-drawdown or retention-risk evidence, not simple profit-taking.

Phase27-D6-C freezes the PM HOLD / REDUCE / EXIT boundary design for this Strategy SoT.

The boundary is:

```text
Expected Edge sufficient
  -> HOLD

Expected Edge or risk/reward weakening while campaign optionality remains
  -> REDUCE candidate

Expected Edge insufficient, continuation broken, severe risk, or Safety full-close requirement
  -> EXIT
```

HOLD is an active continuation decision. A small Expected Edge decline does not automatically become REDUCE or EXIT. HOLD must be explainable as Expected Edge remaining adequate for the current campaign.

REDUCE remains a distinct review-preserved action. Its role is to reduce exposure when risk review, Expected Edge weakening, concentration, or partial-rotation evidence makes full exposure less attractive while the campaign is not yet invalid. D6-C does not remove REDUCE and does not define numeric REDUCE thresholds.

EXIT is a full close. EXIT must be based on insufficient Expected Edge, broken continuation, signal invalidation, severe risk, or Safety. Trend alone is not EXIT authority. Profit alone is not EXIT authority. Safety may block or require full close under its own hard-limit responsibility, but Safety does not optimize Expected Edge.

Profit / Risk Review contract:

- Profit alone does not produce action.
- Large embedded gain, drawdown from peak, volatility, concentration after profit expansion, or changed risk/reward may become Risk Review evidence.
- Risk Review evidence may affect Expected Edge assessment, but it is not a standalone profit-taking philosophy.

Phase27-D6-D implements the first minimal PM HOLD / EXIT boundary improvement:

```text
peak-drawdown / profit-retention risk review
AND Expected Edge remains adequate
AND no severe full-close risk is present
-> HOLD
```

This is not a profit-taking rule and not an EXIT suppression rule. Hard stop, broken trend plus insufficient Expected Edge, explicit risk guard, high downside risk, and high exit-score evidence remain full-close evidence under the existing PM contract. No new threshold, holding-day rule, profit target, stop loss, cooldown, BUY logic, ADD logic, sizing, Runtime Planning, Pending, Submit, Safety, or Execution behavior is introduced.

Phase27-D6-E adopts the D6-D boundary with limitations after 100 business-day before/after attribution review. Adoption status:

```text
D6-D HOLD / EXIT boundary: ADOPTED_WITH_LIMITATIONS
Run comparability: CONFIRMED_WITH_LIMITATIONS
Causal benefit: PARTIAL
Single-change integrity: PATH_DEPENDENT
Risk regression: NOT_OBSERVED
```

Known limitations:

- The full +81,590 JPY 100BD equity delta is not directly attributed to D6-D.
- Direct same-context D6-D benefit is partial; later ADD/HOLD/REDUCE/BUY/Execution differences are path-dependent portfolio effects.
- Baseline and After profiles differ (`historical-smoke` vs `historical-extended-smoke`) and source commits differ.
- After Run close is `REVIEW_REQUIRED` for non-mutating Strategy Shadow review; it is non-blocking but remains an adoption limitation.
- Future performance changes must not use this adoption as permission to change ADD, BUY_NEW, Sizing, Runtime Planning, Pending, Submit, Safety, or Execution.

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
  -> Runtime Planning
  -> Strategy Planning Authority
  -> Pending Order Plan
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
| Runtime Planning | Position Sizingの数量候補とPM/Portfolio Construction intentをRuntime実行intentへ写像するpure mapper | Target Portfolio、Position Sizing quantity candidate、Current、Pending、planning config | planning_intent、order_side_intent、planned_quantity、no_order_reason、planning_reason | Runtime Planning Intent Mapping Authority | Ranking、PM判断、target weight、target notional、quantity sizing、Safety判断 | Strategy Planning Authority、Safety、Approval、Pending Composition、Submit |
| Strategy Planning Authority | 必須artifact / schema / temporal / lineage / symbol-level planを検証しPendingをmaterializeする | Runtime Planning、Position Sizing、price feasibility、environment capability | order_plan、pending_order_plan、approval evidence、run-level classification | Strategy Planning Authority / Pending Materialization Authority | Strategy allocation、target weight、target notional、quantity sizing、Portfolio membership、BUY/SELL優先順位再判断 | Runtime Pending、Approval、Submit Guard |
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
  -> Position Sizing Notional / Quantity Candidate
  -> Runtime Planning Execution Intent Mapper
  -> Strategy Planning Authority Pending Materialization
  -> Safety / Approval / Pending
  -> Submit / Execution
```

重要な否定条件:

```text
Ranking上位 = BUYではない
PM ADD = BUYではない
Portfolio Policy ALLOWED = BUYではない
Corporate Event fact = 自動BUY/SELLではない
Runtime Planning feasible = Submit許可ではない
```

最終的に「どの銘柄を、どのTarget WeightでPortfolioへ組み入れるか」を決めるAuthorityは `Portfolio Construction` である。これは `Target Portfolio Decision Authority` と呼ぶ。

`Position Sizing` はTarget Portfolio差分を、target_notional、target_quantity_candidate、quantity_delta_candidate、quantity_statusへ変換するQuantity Candidate Authorityである。Capital Deploymentの旧責務のうち、target exposure再計算、target weight再調整、銘柄優先順位再計算、membership再判断は重複Strategy判断として退役する。broker-independent execution feasibilityはRuntime PlanningまたはStrategy Planning Authorityの検証責務へ統合する。

`Runtime Planning` はRuntime Execution Intent / Pending Candidateを生成するpure mapperである。これは運用intentのAuthorityであり、StrategyのTarget Weight、Target Notional、Quantity Candidateを再判断しない。

`Strategy Planning Authority` はrequired artifact presence、schema、temporal authority、lineage/hash、symbol-level planning result、execution feasibilityを検証し、pending_order_planをmaterializeする。Strategy Planning Authorityはtarget_weight、target_notional、target_quantity_candidate、quantity_delta_candidateを再計算しない。

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

Position Sizing Quantity Candidate:

```text
target_notional
target_quantity_candidate
quantity_delta_candidate
quantity_status
rounding_result
minimum_executable_notional_result
```

Owner:

```text
Position Sizing
```

Runtime Execution Intent:

```text
side
planned_quantity
order_condition_authority_ref
target_session
source_quantity_ref
approval_requirements
```

Owner:

```text
Runtime Planning
```

Portfolio ConstructionはBroker quantityやlot roundingを決めない。Position SizingはTarget Portfolioを決めない。Runtime PlanningはRanking、PM intent、Target Weight、Target Notional、Quantity Candidateを再計算しない。Strategy Planning AuthorityはRuntime Planningのplanned_quantityを検証してPending化するだけで、quantity丸めやnotionalからの数量再算出を行わない。

### 3.3.1 Portfolio Policy -> Portfolio Construction Binding

Phase23-AS後、Portfolio ConstructionはAQ Portfolio Policy artifactをTarget Weight Authorityのcanonical sourceとして直接消費する。

Required Portfolio Policy fields:

```text
target_position_count
target_gross_exposure_ratio
target_gross_exposure
cash_reserve_ratio
cash_reserve
single_name_weight_cap
deployment_posture
```

Portfolio Constructionの`target_weight_authority`は、Portfolio Policy artifact path/hash、Policy decision id、target count、gross exposure、cash reserve、single-name cap、business dateを保持する。旧Dynamic Position Count / Dynamic Cash Exposure artifactはdecision pathへ戻さず、存在してもnoncanonical observabilityまたはlegacy read-only evidenceに限定する。

Valid zeroはREVIEW_REQUIREDではない。`target_position_count=0`または`target_gross_exposure=0`で、required authorityが有効な場合は、明示zero reasonを持つ通常のzero allocation outcomeとする。

## 3.3.2 Planning Chain Contract

Phase23-AR後のPlanning chainは次をcanonical pathとする。

```text
Portfolio Construction target_weight
  -> Position Sizing target_notional / target_quantity_candidate / quantity_delta_candidate
  -> Runtime Planning planning_intent / order_side_intent / planned_quantity
  -> Strategy Planning Authority validation / pending_order_plan materialization
```

Runtime Planningのzero-state contract:

```text
quantity_delta_candidate > 0 -> BUY_NEW or BUY_ADD intent
quantity_delta_candidate < 0 -> SELL_REDUCE or SELL_EXIT intent
quantity_delta_candidate == 0 -> NO_ACTION / NO_ORDER
target_weight > 0 and target_notional > 0 and target_quantity_candidate == 0 -> NO_ORDER_MINIMUM_NOTIONAL_UNMET
missing target_weight or quantity authority -> REVIEW_REQUIRED
invalid schema / hash / date / future authority -> fail-closed
```

Optional legacy evidence、legacy quality、noncanonical Capital Deployment artifact、retired Dynamic Position Count / Dynamic Cash Exposure artifactの欠損は、canonical authorityが有効である限りMorning HALTへ昇格しない。

## 3.3.1 Opportunity Score -> Target Weight -> Position Sizing Boundary

この節はPhase23-ANで閉じた、Opportunity Ranking、Portfolio Construction、Position Sizing間の正式境界である。詳細Contractは `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md` を参照する。

### Opportunity Score Contract

`runtime_opportunity_score` は Opportunity Ranking Authority が生成する銘柄間の相対的投資機会signalである。

Contract:

```text
producer = Opportunity Ranking Authority
canonical field = runtime_opportunity_score
semantics = relative opportunity / expected edge evidence
range = finite numeric
sign = signful; negative value allowed
higher_is_better = true
PIT = business_date時点までのCandidate / Opportunity入力に限定
```

`runtime_opportunity_score` は資金配分額、target weight、allocation quality、BUY確定、Submit許可ではない。Position Sizingは `runtime_opportunity_score` をquality multiplierやweight計算の直接入力として再解釈してはならない。

Phase29-L21T-AHで、BUY_NEW eligibilityに対するscore signの意味を明確化した。

```text
runtime_opportunity_score = canonical uncalibrated relative opportunity signal
expected_edge_score = deprecated alias
expected_return = deprecated alias, not economic return unless calibrated
calibration_applied = false
economic_units_available = false
```

この状態では、`runtime_opportunity_score <= 0` またはaliasの
`expected_edge_score <= 0` だけを理由にBUY_NEWをfail-closedしてはならない。
候補はBUY Qualityの `relative_opportunity_quality`、Market Context、Signal
Reliability、Execution Feasibility、Portfolio Fit、Portfolio Construction、
Position Sizing、Lot/Safety、Submit feasibilityのProduction-common chainで評価する。

`below_opportunity_top20` はranking metadata / observability / diagnostic
shortlistであり、uncalibrated score環境ではhard BUY_NEW rejection authorityでは
ない。同様に、top20であることはBUY permissionではない。

将来formal calibrationが成立し、`calibration_applied=true` かつ
`economic_units_available=true` が明示された場合のみ、calibrated economic
expected return / edge のzero boundaryをBUY_NEW eligibilityで使える。

Phase29-L21T-AKで、同じscore semantic contractをPortfolio Construction
consumerまで拡張した。Portfolio ConstructionはOpportunityの
`canonical_score_field`、`score_semantic_role`、`calibration_applied`、
`economic_units_available`を消費し、uncalibrated relative score環境では
`runtime_opportunity_score <= 0`、`non_positive_expected_edge_score`、
standalone `below_opportunity_top20` を単独のBUY_NEW hard rejection authority
として使わない。

これはnegative score candidateの自動BUYやBUY件数固定を意味しない。
Portfolio Constructionは引き続きBuy Quality、Portfolio Policy、Market
Context、Current、Pending、hard no-buy reason、Corporate Event、Safety/lot
feasibilityへ渡るProduction-common chainに従ってtarget membershipと
target weightを決める。`high_downside_risk_score`等のhard reason、Buy
Quality `REJECT`、missing / malformed semantic metadata、future calibrated
economic negative scoreはfail-closedを維持する。

### Portfolio Construction Target Allocation Contract

Opportunity RankingをPortfolio制約へ統合し、どの銘柄をTarget Portfolioに含め、どの比率で持つかを決めるAuthorityは `Portfolio Construction` である。

Canonical fields:

```text
target_weight
target_weight_authority
target_weight_resolution
```

`target_weight` はPortfolio全体に対する対象銘柄の目標保有比率である。単位はratioであり、原則として以下を満たす。

```text
0.0 <= target_weight <= single_name_weight_cap
sum(target_weight) <= target_gross_exposure
```

余剰はcashとして保持できる。保有数やBUY件数を満たすためにweightを強制配分してはならない。eligible candidateであっても `target_weight=0`、Portfolio全体でBUY 0件、既存保有の維持または縮小は正常なStrategy outcomeであり得る。

`target_weight_authority` には最低限以下を保持する。

```text
source_opportunity_reference
portfolio_policy_reference
market_context_reference
position_count_reference
existing_position_reference
weight_method
weight_method_version
business_date
pit_status
reason_codes
```

### Portfolio Construction -> Position Sizing Boundary

Position Sizingの正式入力はPortfolio Constructionが決定した `target_weight` または同等のTarget Allocation Authorityである。Position Sizingは、Opportunity score、rank、candidate scoreを再解釈して投資対象や相対weightを決め直さない。

Position Sizing input contract:

```text
target_weight
portfolio_total_equity / investable_capital
reference_price
trading_unit
current_quantity
current_notional
current_weight
single_name_weight_cap / safety cap reference
minimum_executable_notional policy
```

`reference_price` は計画数量変換用の Market Evidence Authority / Current Valuation Authority 由来フィールドである。Position Sizingは価格を取得・推定・latest fallbackせず、PIT検証済みの `reference_price_authority` と `reference_price_resolution` を消費する。`target_weight > 0` かつ `target_notional > 0` の場合のみ価格が必須で、明示的なzero allocationでは価格欠損をReview理由にしない。

Position Sizing output contract:

```text
target_notional
target_quantity_candidate
quantity_delta_candidate
rounding_result
cash_residual_evidence
minimum_executable_notional_result
reason_codes
```

Quantity、lot rounding、cash feasibility、minimum executable notional、residual cashの処理はPosition Sizing / Capital Deployment / Runtime Planningの下流責務であり、Portfolio ConstructionはBroker quantityを決めない。

### Raw Score and Allocation Decision Separation

`runtime_opportunity_score`、`allocation_quality_score`、`target_weight`、`target_notional`、`quantity` は別Authorityである。

```text
runtime_opportunity_score = 相対Opportunity signal
allocation_quality_score = 明示Authorityがある場合のみ使える品質補助signal
target_weight = Portfolio ConstructionのTarget Portfolio決定
target_notional = Position Sizing / Capital Deploymentの金額候補
quantity = Runtime / Broker制約を含む下流候補または実行値
```

以下は禁止する。

```text
raw score clamp
absolute value
score shift
sigmoid
current-day min-max normalization
current-day percentile rank
negative-to-zero
raw score -> allocation_quality_score silent promotion
raw score -> target_weight direct substitution
forced BUY
fixed BUY count
```

### Failure and Review-required Behavior

Target Weight Authorityが生成できない場合、下流はfail-closedする。

```text
Portfolio Construction target_weight unresolved
  -> REVIEW_REQUIRED
  -> Position Sizing target_notional = 0
  -> no silent zero-as-success
  -> no forced BUY
```

負の `runtime_opportunity_score` はschema errorではない。ただし、負値を無条件にpositive qualityやpositive target weightへ変換してはならない。採用、非採用、zero weight、REVIEW_REQUIREDのいずれになるかはPortfolio ConstructionのTarget Weight Authorityとreason codeで説明する。

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

Phase23-AR後、Capital DeploymentはStrategy decision path上のstandalone public stageではない。過去の検討値・旧artifactは、互換性確認またはnoncanonical observabilityとしてのみ扱う。Canonicalな数量候補はPosition Sizingが生成し、Runtime Planningはその数量候補をexecution intentへ写像し、Strategy Planning Authorityがpending_order_planをmaterializeする。

Legacy reference policy:

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

## Phase24-HT Planning Submit Feasibility Boundary

Planning Submit Feasibility is added to the Planning Layer as execution feasibility, not Strategy decision-making.

It may read:

```text
active CapitalDeploymentPolicy
Runtime Current / Persistent Ledger
Safety decision
Pending duplicate / reservation evidence
planned BUY estimated_amount
planned SELL estimated_amount
```

It must not change:

```text
Strategy
PM
Opportunity Ranking
Portfolio Policy
Position Sizing
BUY quantity
target exposure
cash reserve
max_exposure
```

Contract:

```text
Strategy / Position Sizing may propose target notional and quantity.
Planning Submit Feasibility determines whether the proposed execution
intent can become APPROVED Pending under active Runtime hard authorities.
Submit Guard remains the final hard guard before Broker boundary.
```

Phase24-ID clarifies that Submit Feasibility is aggregate over the approved
Pending batch, not only item-scoped.  Strategy may produce several BUY intents,
but Runtime feasibility must reserve cash, buying_power, exposure, and active
max_positions across those BUY intents before the plan can become submittable.
SELL proceeds or exposure reductions are not credited to same-day BUY capacity
without a later explicit Strategy/Runtime contract.

This clarification does not alter Strategy ranking, portfolio construction,
PM, target exposure, position sizing, or generated BUY quantity.  It only
defines whether the generated execution set is feasible for the execution
boundary.

Failure behavior:

```text
PASS:
  The item may proceed to Pending approval when other approval evidence passes.

REVIEW_REQUIRED:
  The item must not be APPROVED Pending.

HALT:
  Used only for Safety halt or invalid required Runtime authority after the
  expected materialization point.
```

## Phase24-HV BUY Review / SELL Continuation Boundary

BUY item-scoped execution review is not a Strategy decision and must not mutate Strategy, PM, Ranking, Portfolio Policy, Position Sizing, target exposure, max exposure, or BUY quantity.

When Planning Submit Feasibility classifies a BUY item as non-submittable, Strategy intent remains auditable:

```text
BUY intent preserved
BUY item state = REVIEW_REQUIRED
approved BUY ids = empty
review_scope = BUY_ITEM_SCOPED_REVIEW when the violation is item-scoped
```

This scope does not authorize the BUY. It only allows Runtime consumers to determine whether independent SELL authority may continue through Position Management and SELL Planning.

SELL continuation requires separate Runtime authority:

```text
valid Current / Persistent Ledger position authority
valid PM authority
valid SELL Planning input authority
valid Safety authority
Submit Guard final revalidation
```

Portfolio-scoped, global-safety, unknown-authority, corrupt, ambiguous, or stale review remains fail-closed and must not be downgraded by Strategy.
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
| Strategy sizing input | Portfolio Policy / Position Sizing |
| Risk hard limit | Safety |
| Broker execution feasibility | Runtime Planning / Strategy Planning Authority / Broker adapter |

Safetyはlot roundingを行わない。lot rounding evidenceはPosition Sizingがquantity candidateとして記録し、Runtime Planning / Strategy Planning Authority / Broker adapterが実際のBroker制約と照合する。

20% cashの判断:

```text
採用: D. Market Context dynamic target with 20% standard baseline
```

20%はPhase22初期default baseline候補であり、Permanent fixed targetでもhard safety floorでもない。Safety floorは別Authorityで定義する。Evidence不足のため、20%をProduction恒久値として固定しない。

## 11. Dynamic Position Count

Dynamic Position CountのownerはPortfolio Policy Engineである。Phase23-AQ後、Dynamic Position Countは独立Strategy moduleではなくPortfolio Policy内部resolverである。Policy targetから実行可能数量候補への変換はPosition Sizingが担当し、Safetyはhard capを適用する。

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
- Position Sizingがnotionalとquantity candidateへ変換する
- Safetyがhard capを適用する
- Runtime Planning / Strategy Planning Authority / Broker adapterがBroker制約を最後に照合する

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
- Portfolio Construction / Position Sizing / Safety / Runtime Planning / Strategy Planning Authorityを通過して初めてPending Candidateになる

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
  -> Position Sizing
  -> Runtime Planning
  -> Strategy Planning Authority
  -> Safety / Runtime switch
```

Phase21-D/E時点のPhase22実装順:

1. Market Context Artifact
2. Corporate Event Artifact
3. Candidate / Opportunity compatibility
4. Portfolio Policy Artifact
5. Position Management refs
6. Portfolio Construction
7. Position Sizing quantity candidate contract
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

## 27. Phase24-HY Ranking Consumer Alignment

Portfolio Construction consumes BUY AI opportunity ranking as an execution input authority. The canonical semantic field is `opportunity_buy_rank`; the current Runtime BUY AI artifact materializes this value as `buy_rank` in `.runtime/runtime_state/buy_ai/<business_date>/opportunity_rankings.json`.

Strategy consumers must keep these rank semantics separate:

| Field | Meaning | Authority |
|---|---|---|
| `candidate_rank` | Candidate model order before opportunity ranking | Candidate artifact only |
| `opportunity_buy_rank` | Canonical BUY opportunity rank | Opportunity ranking artifact `buy_rank` |
| `input_opportunity_rank` | Portfolio Construction copy of `opportunity_buy_rank` | Opportunity ranking artifact row |
| `portfolio_selection_order` | Portfolio Construction target selection order | Portfolio Construction |
| `runtime_planning_order` | Runtime Planning emission/order trace | Runtime Planning |

Opportunity rows must not use `candidate_rank`, candidate model rank, adapter array index, or recomputed rank as the opportunity rank. If an opportunity row has no usable `buy_rank` / `opportunity_buy_rank`, or if rank authority fields conflict, the consumer must fail closed with `REVIEW_REQUIRED` / row rejection before Portfolio Construction selection. Candidate rows may continue to use `candidate_rank` as candidate authority, but that value is not an opportunity rank.

This contract does not change Opportunity Ranking production, `expected_edge_score`, eligibility, Portfolio Policy, Position Sizing policy, PM, Re-entry, Submit Guard, max exposure, cash buffer, or future-PnL boundaries.

## 28. Phase26-G Adaptive BUY Quality Authority

Phase26-G freezes `Adaptive BUY Quality Authority` as the Production / Demo / Historical common design for BUY admission quality and individual allocation strength. The canonical specification is:

```text
docs/02_architecture/adaptive_buy_quality_authority.md
```

Adaptive BUY Quality is produced by the Production Strategy BUY Quality Resolver and materialized as `buy_quality_decision.v1`. It evaluates:

```text
Relative Opportunity Quality
Market Context Quality Modifier
Signal Reliability
Execution Feasibility
Portfolio Fit
```

The authority may produce `BUY_ELIGIBLE`, `BUY_REDUCED_ALLOCATION`, `BUY_REVIEW_REQUIRED`, or `BUY_REJECTED`. It does not reinterpret `runtime_opportunity_score` as an expected return, target weight, target notional, allocation quality score, Submit permission, Safety hard maximum, or fixed position-count gate.

Portfolio Construction is the first Strategy consumer. Position Sizing consumes the resulting quality decision and applies documented quality adjustment only after Portfolio Construction has accepted target membership/weight. Runtime Planning maps the resulting quantity candidate; it does not recompute Quality.

Permanent constraints:

- PIT-only inputs
- no Historical Test result, Paper Ledger result, future price, or future PnL input
- no fixed Rank N limit
- no ungrounded fixed raw-score threshold
- no `target_position_count` decision reconnect
- no implicit `quality_adjustment=1.0` fallback when required quality evidence is missing
- same contract for Production, Demo, and Historical

## 29. Phase27-D1 Momentum Follow Position Lifecycle and Canonical Decision Architecture

Phase27-D1 freezes the Production / Demo / Historical common Strategy design for Momentum Follow / Momentum Rotation position lifecycle and canonical position decisions. The canonical detailed specification is:

```text
docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md
```

This specification is not a phase-local report. It is a Strategy Architecture SoT extension and must be treated as the common contract for future implementation work that touches existing-position lifecycle, BUY_ADD, HOLD / NO_ACTION semantics, incremental investment eligibility, or re-entry observability.

Phase27-D1R further refines this contract before implementation entry by splitting Canonical Position Decision into immutable staged artifacts, defining action conflict resolution, fixing legacy ADD migration acceptance, and adding implementation completeness / degression requirements. The D1R revision is part of the same common Strategy SoT and is not phase-local.

Investment philosophy:

- Long-term performance objective is annual return `+50%`; this is not a single Phase27 acceptance condition.
- Starting capital assumption is `1,000,000 JPY`.
- Risk posture is aggressive / high-risk capital, while preserving Safety, Submit Guard, PIT integrity, and architecture integrity.
- Strategy style is Momentum Follow / Momentum Rotation.
- Holding period is an outcome of momentum continuation, not a fixed target.
- Profit alone is not an EXIT reason.
- Fast loss control remains required.
- Cash is a residual result of valid decisions; no fixed cash-ratio target is introduced.

Canonical position lifecycle:

```text
NO_POSITION
  -> BUY_NEW
  -> OPEN_POSITION
  -> HOLD / ADD / REDUCE
  -> EXIT
  -> NO_POSITION
  -> Optional future BUY_NEW as Re-entry
```

Allowed canonical position decisions are:

```text
BUY_NEW
ADD
HOLD
REDUCE
EXIT
NO_ACTION
```

Decision semantics:

- `BUY_NEW` opens a new campaign for a symbol with no current position.
- `ADD` increases an existing open position only after downstream target portfolio, sizing, planning, and safety authority produce a positive executable delta.
- `HOLD` is an active Strategy / PM decision to keep an existing position open with approximately unchanged quantity.
- `REDUCE` partially shrinks an open campaign.
- `EXIT` closes the campaign.
- `NO_ACTION` is an execution / planning no-order result and is not equivalent to HOLD unless explicitly linked to a HOLD decision.

Canonical BUY_ADD chain:

```text
PM ADD
  -> Canonical Position Decision
  -> Portfolio Construction
  -> Position Sizing
  -> positive quantity_delta_candidate
  -> Runtime Planning BUY_ADD
  -> Formal Planning
  -> Pending
  -> Approval
  -> Submit
  -> Execution
```

PM ADD is directional intent only. It is not a BUY order, not quantity authority, and not Submit permission. Rank 1 alone does not imply ADD. PM ADD alone does not imply ADD. BUY_ADD must remain subject to Portfolio Construction, Position Sizing, Runtime Planning, Safety, Approval, and Submit.

Legacy ADD disposition:

- The `sell_pipeline -> add_consumer -> pm_add_order_plan -> pending` path is not the canonical Strategy ADD decision path.
- Phase27-D1 recommends final disposition `RETIRE`, with `COMPATIBILITY_ADAPTER_NON_DECISION` allowed as a migration bridge.
- The legacy path must not produce an ADD decision or quantity while canonical BUY_ADD authority is active.
- Production, Demo, and Historical must use the same ADD authority and mutual-exclusion contract.
- Phase27-D2-C fixes the migration bridge as `NON_DECISION_COMPATIBILITY`: it is telemetry only, with `decision_effect = NONE`, `quantity_authority = NONE`, `pending_authority = NONE`, `approval_authority = NONE`, and `submit_authority = NONE`.
- The compatibility contract is `legacy_pm_add_compatibility.v1`; its dedup key is `run_id, business_date, symbol, position_campaign_id, decision_id`. Duplicate keys, lineage mismatch, or canonical/legacy executable authority overlap must become `REVIEW_REQUIRED` or explicit block.

Incremental Investment Eligibility is introduced as a Strategy decision-support contract distinct from both relative ranking and Adaptive BUY Quality:

- Relative ranking answers whether a symbol is better than other candidates.
- Incremental Investment Eligibility answers whether new capital is justified now.
- Adaptive BUY Quality remains allocation eligibility / adjustment authority.

Momentum Continuation is introduced as a PIT-only foundation for HOLD / ADD / REDUCE / EXIT reasoning. Thresholds are not fixed by Phase27-D1 and must be calibrated later by controlled experiments.

Re-entry is not a separate action. It is a new `BUY_NEW` after full EXIT and must pass the same canonical chain without preferential treatment. Prior campaign PnL, Paper Ledger results, future price, historical-test performance, and audit judgments must not become Strategy inputs.

Future performance work must follow the Phase27-D1 sequence: repair BUY_ADD authority first, prove the canonical contract with targeted tests, then add observability/shadow foundations, and only then run controlled performance experiments one change at a time.

## 30. Phase29-L21T-AV Multi-Horizon Momentum Trajectory Semantics

Phase29-L21T-AV implements the AU/AU2 Production-common trajectory design as an
Adaptive BUY Quality extension for BUY_NEW. The goal is to distinguish healthy
momentum continuation from prior winners whose recent trajectory has faded and
from names whose gains are concentrated into an overheated recent move.

Technical Feature authority materializes PIT facts including 1BD / 3BD / 5BD /
10BD / 20BD momentum, recent volatility-adjusted move, and momentum deltas.
Existing 5BD / 20BD calculations remain unchanged.

Adaptive BUY Quality is the classification owner:

```text
HEALTHY_CONTINUATION
FADING_PRIOR_WINNER
RECENT_ACCELERATION_OVERHEAT
MIXED_OR_UNRESOLVED
```

`FADING_PRIOR_WINNER` and `RECENT_ACCELERATION_OVERHEAT` produce `BUY_WAIT` for
BUY_NEW. `BUY_WAIT` means temporary BUY_NEW ineligibility only: no BUY_NEW order,
no BUY Pending, no Human Review Pending, no Runtime halt, no SELL block, and
normal next-business-day reevaluation from PIT features. `HEALTHY_CONTINUATION`
does not boost allocation automatically; it allows the existing BUY Quality,
Portfolio Construction, Position Sizing, Safety, Pending, Submit, and Execution
chain to continue.

Portfolio Construction, Position Sizing, Runtime Planning, Pending, Submit, and
Execution must consume/copy the BUY Quality trajectory fields and must not
recompute trajectory classification. BUY_ADD, REENTRY, HOLD, REDUCE, and EXIT
authority remain unchanged.
