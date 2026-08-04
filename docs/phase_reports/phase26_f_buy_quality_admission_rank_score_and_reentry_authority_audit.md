# Phase26-F BUY Quality Admission, Rank/Score Consumption, and Re-entry Authority Audit

Primary Judgment:

`PHASE26_F_BUY_ADMISSION_SIZING_AND_REENTRY_AUTHORITY_GAPS_CONFIRMED`

対象Run:

`runtime-test-historical-smoke-20260804T005103762479Z`

このTaskではRuntime実装、Strategy判断値、Submit Guard、Safety、Candidate、Opportunityを変更していない。fresh-run、resume、1BD/3BD/10BD/100BD Historical Testも実行していない。

## Primary Root Cause

低Rankまたは低い正の`expected_edge_score`がBUYされた主因は、Production-common BUY admissionが現在「finiteかつ`expected_edge_score > 0`、かつ明示`no_buy_reason`なし」を満たすことを最低条件としており、正のscoreをさらに校正済み品質として判定するBUY Quality Admission Authorityが存在しないこと。

`target_position_count`撤去後に固定件数制限は戻っていない。一方で、その空白を埋める正式な品質Admissionやscore-sensitive allocation authorityも存在しないため、低い正のscoreはBUY候補として通過し得る。

## Score Semantics

`expected_edge_score`はOpportunity Ranking Authorityが出す`runtime_opportunity_score`であり、銘柄間の相対Opportunity signalである。設計SoT上、これはtarget weight、target notional、allocation quality score、BUY確定、Submit許可ではない。

対象RunのOpportunity artifactsでは`calibration_applied=false`が観測された。したがって、`0.007477`や`0.002294`のような小さい正値を、校正済み期待収益率や承認済み品質スコアとして扱うEvidenceはない。

## Consumer Findings

- Rank Consumer: Portfolio Construction、Position Sizing、Runtime Planningに`opportunity_buy_rank` lineageとして伝播している。固定Rank N件制限は観測されない。
- Score Consumer: Opportunity Eligibilityで非finite/非正値を落とす。低い正値を落とす正式閾値は観測されない。
- Allocation Quality Consumer: Position Sizingは`allocation_quality_score`欠落を`REVIEW_REQUIRED`として記録するが、target weight authority pathでは`quality_adjustment=1.0`で進む。
- Sizing Consumer: BUY notionalは固定notionalではなく、current equity、target exposure/cash、single-name cap、price、lot roundingの結果として説明される。
- Market Context Consumer: Market ContextはPortfolio Policy経由でexposure/cash側に効く。score閾値やRank上限としては観測されない。
- Re-entry Consumer: `93180`はEXIT後に新しいcampaign idで再BUYされている。cooldown契約や過去PnLをStrategy入力にする契約は観測されない。

## Observability Limitation

Execution fillと同日Strategy artifactの突合では、日次Strategy snapshotが実行後状態を保持しているため、BUY済みsymbolは`newly_filled_portfolio_member`としてzero-delta化されている。数量は`.runtime/runtime_state/strategy_planning/<business_date>/order_plan.json`とExecution fillから確認した。

Execution fill側の`source_decision_id`および`order_plan_item_id`は`MISSING`で、これは今回の主因ではないが、次のobservability repair候補である。

## Evidence Outputs

詳細Evidence:

`reports/phase26_f_buy_quality_admission_rank_score_and_reentry_authority_audit/`

主要結果:

- BUY executions: 26
- SELL executions: 45
- `expected_edge_score < 0.05`のBUY: 7
- `opportunity_buy_rank > 3`のBUY: 14
- BUY 26件すべてで`allocation_quality_score_missing`
- `target_position_count_decision_authority`: `DEPRECATED_METADATA_ONLY`
- invalid `target_position_count` decision consumer: 0

## Regression

- compile: PASS
- unit: PASS, `103 passed in 2.35s`
- artifact read validation: PASS, 11 JSON files and 5 CSV files readable
- fresh-run: NOT_RUN

## Safety

- target_position_count reintroduced: false
- fixed Rank N limit added: false
- fixed Score threshold added: false
- Submit Guard weakened: false
- Safety weakened: false
- Validation weakened: false
- fallback added: false
- historical-only branch added: false
- test result used as Strategy input: false
- Paper Ledger used as Strategy input: false
- future information used: false

## Recommended Next Task

Production-common BUY Quality Admission / Allocation Quality Authority repairを次Taskとして設計する。固定Rank N、根拠なし固定Score threshold、cooldown、Historical専用分岐は追加せず、PIT入力のみで品質AdmissionとSizing感応度のAuthorityを正式化する。
