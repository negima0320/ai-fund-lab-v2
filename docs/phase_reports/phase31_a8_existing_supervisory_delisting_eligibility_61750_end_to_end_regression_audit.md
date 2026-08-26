# Phase31-A8 — Existing Supervisory / Delisting Eligibility Authority 61750 End-to-End Regression Audit

## PRIMARY_JUDGMENT

`61750` did not pass Candidate / BUY because target-run PIT evidence contained a positive supervisory / delisting-risk fact that was ignored. At the actual BUY decision date, the target run's canonical PIT J-Quants listed-issues artifact contained `61750` as currently listed on Standard market with product category `011`, but it did not contain any supervisory, special-alert, caution, delisting-scheduled, or listing-termination field.

The precise root cause is therefore not a 61750-specific consumer bypass of present supervisory evidence. It is a broader Corporate/Event eligibility authority gap: the repository has a partial Runtime BUY market-status guard that can consume explicit status fields if they exist, but the current PIT source foundation for this run only materialized J-Quants `/v2/equities/master` listed membership fields. Strategy Intelligence then reported `eligibility.status = PASS` and `event_coverage_status = AVAILABLE` for `61750`, even though symbol-level event coverage was `UNKNOWN` and no supervision / delisting-risk authority was present. Under the current Strategy Intelligence SoT, missing alert / supervision / delisting-warning coverage must be recorded as a gap, not converted to safe eligibility.

A6/A7 remain locally correct: the 2022-12-16 Current Valuation hard stop was legitimate. A8 finds that the held-position state was upstream avoidable only if a family-wide supervisory / delisting-risk source authority or missing-coverage review contract had existed before the 2022-08-17 BUY.

## TARGET_SYMBOL

`61750`

## FIRST_BUY_DATE

`2022-08-17`

Evidence:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260818T015851711672Z/daily/2022-08-17/execution/fills.json`

## FIRST_BUY_QUANTITY

`100`

## FIRST_BUY_NOTIONAL

`89,700 JPY`

The fill evidence has:

```text
side = BUY
symbol = 61750
quantity = 100.0
execution_price = 897.0
gross_notional.value = 89700.0
```

## FIRST_BUY_DECISION_ARTIFACT

Primary decision lineage:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260818T015851711672Z/daily/2022-08-17/strategy/buy_quality_decisions.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260818T015851711672Z/daily/2022-08-17/strategy/strategy_intelligence.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260818T015851711672Z/daily/2022-08-17/strategy/portfolio_construction.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260818T015851711672Z/daily/2022-08-17/strategy/runtime_planning.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260818T015851711672Z/daily/2022-08-17/morning/planning_evidence.json`

## FIRST_BUY_FILL_ARTIFACT

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260818T015851711672Z/daily/2022-08-17/execution/fills.json`

## SUPERVISORY_DELISTING_AUTHORITY_EXISTS

`PARTIAL`

Existing paths:

| Path | Classification | Semantics |
| --- | --- | --- |
| `src/ai_fund_lab_v2/runtime_v2/market_status/buy_eligibility.py` | `CANONICAL_PARTIAL` | Production-common new-BUY guard. Blocks symbols absent from PIT listed snapshot, explicit `current_listed=false`, explicit delisting / supervision / ineligible status, or explicit delisting date. |
| Historical listed issues snapshots | `CANONICAL_PARTIAL` | `src/ai_fund_lab_v2/runtime_v2/historical_support/listed_issues_snapshots.py` resolves latest snapshot not after business date. |
| Strategy listed-info propagation | `CANONICAL_PARTIAL` | Strategy / BUY Quality / PC carry `code`, `market`, `product_category`, `security_type`, `current_listed`. |
| Strategy Intelligence Corporate/Event eligibility | `CANONICAL_DESIGN_PARTIAL_IMPLEMENTATION` | Current SoT says supervision / alert / special caution / delisting pending are disqualifying or review-required facts where source authority exists, and missing coverage must not become `SAFE`. Target artifact does not enforce that for this class. |

The implemented authority is sufficient for ordinary listed-membership and explicit status fields. It is not a complete supervisory / delisting-risk source authority.

## JQUANTS_SOURCE

`listed_issues` / J-Quants `/v2/equities/master`

Fetcher / materializer:

- `src/ai_fund_lab_v2/data_sources/jquants/raw_ingestion.py`
- `src/ai_fund_lab_v2/data_sources/jquants/client.py`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/listed_issues_snapshots.py`

Target-run artifact:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260818T015851711672Z/daily/2022-08-17/market_refresh/inputs/historical_asof/2022-08-17/raw/jquants/listed_issues/data.parquet
```

Target-run 61750 row fields:

```text
Date = 2022-08-17
Code = 61750
CoName = ネットマーケティング
CoNameEn = Net Marketing Co.Ltd.
S17 = 10
S17Nm = 情報通信・サービスその他
S33 = 9050
S33Nm = サービス業
ScaleCat = TOPIX Small 2
Mkt = 0112
MktNm = スタンダード
Mrgn = 2
MrgnNm = 貸借
ProdCat = 011
```

No target-run field was present for `special_supervision_status`, `supervision_status`, `market_status`, `listing_status`, `delisting_status`, `scheduled_delisting_date`, `listing_termination_date`, or equivalent.

Historical as-of reconstruction is supported for this artifact through `latest_snapshot_not_after_business_date`; target 2022-08-17 source manifest reports PIT PASS and no latest fallback.

## SUPERVISORY_INFO_PRESENT_IN_SOURCE_AT_BUY

`NO`

The source artifact had listed-membership and product/market fields only. It did not contain supervisory / alert / caution / delisting-risk fields for `61750`.

## SUPERVISORY_INFO_MATERIALIZED_AT_BUY

`NO`

The materialized Strategy BUY row carried:

```text
listed_info = {
  code: 61750,
  current_listed: true,
  market: スタンダード,
  product_category: 011,
  security_type: 011
}
```

No supervisory or delisting-risk status was materialized into `buy_quality_decisions.json`, `strategy_intelligence.json`, `portfolio_construction.json`, `position_sizing.json`, `runtime_planning.json`, or `morning/planning_evidence.json`.

## SUPERVISORY_INFO_CONSUMED_BY_CANDIDATE_ELIGIBILITY

`NO`

No such info was present to consume. Candidate / Opportunity / BUY Quality consumed listed membership, product category, market, price, volume, rank, quality, broker product category, and strategy intelligence, but not supervision / delisting-risk state.

## SUPERVISORY_INFO_CONSUMED_BY_BUY_DECISION

`NO`

The BUY decision consumed ordinary listed-info compatibility and explicit BUY eligibility when available. It did not consume a supervisory / delisting-risk fact because none was materialized.

## EXPECTED_61750_BUY_ELIGIBILITY_AT_FIRST_BUY

`REVIEW_REQUIRED`

This is the current SoT judgment, not a later-known delisting judgment.

Boundary:

- Under the older Phase17-BV14 guard alone, `61750` would be `ELIGIBLE` on 2022-08-17 because it was present in the PIT listed snapshot and no explicit status field blocked it.
- Under the current Strategy Intelligence / Corporate Event SoT, alert / supervision / special caution / delisting pending are authoritative eligibility facts where source authority exists, and missing coverage must be recorded as uncertainty/review rather than safe. The target run did not have such coverage, yet `61750` received normal PASS eligibility.

Therefore the normal Candidate / BUY PASS was not evidence-complete. The correct current-contract state is `REVIEW_REQUIRED` for missing event-risk coverage, not `INELIGIBLE` based on future outcome.

## ACTUAL_61750_BUY_ELIGIBILITY

`PASS / ELIGIBLE`

Evidence:

- `strategy/buy_quality_decisions.json`: `PIT_status = PASS`, `current_listed = true`, `quality_status = PASS`, `opportunity_buy_rank = 39`
- `strategy/strategy_intelligence.json`: `eligibility.status = PASS`, `disqualifying_facts = []`, `review_required_facts = []`
- `strategy/runtime_planning.json`: `planning_intent = BUY_NEW`, `planned_quantity = 100`, `planning_reason = position_sizing_positive_quantity_delta_maps_to_buy_new;position_sizing_quantity_candidate_resolved`
- `morning/planning_evidence.json`: `decision = INCLUDE`, `source_submit_feasibility_status = PASS`, `canonical_priority_index = 1`
- `execution/fills.json`: BUY fill executed for 100 shares.

## 61750_SUPERVISORY_STATE_AT_BUY

`UNKNOWN_NOT_MATERIALIZED`

No target-run PIT artifact on 2022-08-17 materialized supervisory / alert / caution / special-supervision state for `61750`.

## 61750_LISTING_STATE_AT_BUY

`CURRENTLY_LISTED_BY_PIT_LISTED_ISSUES`

The 2022-08-17 listed-issues row existed and was consumed as:

```text
current_listed = true
market = スタンダード
product_category = 011
security_type = 011
```

## 61750_ELIGIBILITY_STATE_AT_BUY

`ACTUAL_PASS_BUT_COVERAGE_INCOMPLETE`

The actual run treated `61750` as eligible. Under current SoT, missing supervisory / delisting-risk coverage should have prevented a normal safe PASS and produced review semantics.

## FIRST_ELIGIBILITY_GAP_LAYER

`Corporate/Event eligibility source coverage -> Strategy Intelligence eligibility materialization`

The first layer is not PM, PC, Submit, or Execution. By those stages the missing event-risk authority had already been normalized into ordinary eligibility. The earliest evidenced gap is that Strategy Intelligence treated Corporate/Event coverage as sufficient for PASS even though no supervision / delisting-risk source field was present and symbol-level event coverage was not proven safe.

## HISTORICAL_PIT_MATERIALIZATION_GAP

`NO`

The target run selected the correct PIT listed-issues snapshot for 2022-08-17, with no future snapshot and no latest fallback. The gap is not that Historical reconstruction dropped a field that was present in the run-scoped source artifact. The gap is that the source foundation for this run did not provide supervisory / delisting-risk authority, and consumers did not materialize missing coverage as review.

## TEMPORAL_BINDING_STATUS

`AMBIGUOUS`

For the available J-Quants listed-issues source, temporal binding passed:

```text
business_date = 2022-08-17
selected_as_of = 2022-08-17
future_row_rejection_count = 0
latest_fallback_used = false
```

For a supervisory / delisting-risk source, temporal binding is `AMBIGUOUS` because no such target-run source artifact exists. This audit did not use later-known delisting outcome to infer 2022-08-17 ineligibility.

## CANDIDATE_CONSUMER_GAP

`YES`

No present supervisory field was ignored. The consumer gap is that missing supervisory / alert / delisting-risk coverage was not preserved as a review-required eligibility condition.

## STRATEGY_CONSUMER_GAP

`YES`

Strategy Intelligence emitted `eligibility.status = PASS` and no review facts despite missing concrete supervision / delisting-risk authority. This is the first semantic consumer gap.

## PM_CONSUMER_GAP

`PARTIAL`

PM did not ignore present supervision data. After the BUY, PM eventually produced repeated `REDUCE` intent, but the position remained at 100 shares because the reduction was below executable lot constraints. PM had no separate listing-risk lifecycle authority proving mandatory exit or no-new-add behavior for this symbol.

## LEGACY_OR_FALLBACK_BYPASS

`NO`

No exact legacy/fallback path was found that bypassed a present canonical supervisory authority for `61750`. Target artifacts show run-scoped historical source authority, PIT PASS, no latest fallback, and ordinary Strategy/Runtime planning consumption.

## MISSING_SUPERVISORY_STATUS_FAIL_OPEN

`YES`

The failure mode is not missing listed-issues authority. That is fail-closed. The failure mode is missing supervisory / delisting-risk coverage inside an otherwise PASS listed-issues authority path. Because `/v2/equities/master` provided ordinary listing membership, the missing status class became effectively safe and `61750` flowed to normal Candidate / BUY.

## EXISTING_HOLDING_LISTING_RISK_CONSUMER_STATUS

`PARTIAL`

Observed lifecycle:

- 2022-08-17: BUY 100.
- 2022-08-18 through 2022-09-12: mostly HOLD / NO_ACTION.
- 2022-09-13 through 2022-12-16: REDUCE intent, but `REDUCE_INTENTIONAL_NO_ORDER` / `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`.
- 2022-12-15: `61750` still present in listed issues and had `KNOWN_NO_EVENT`.
- 2022-12-16: `61750` absent from listed issues; Current Valuation fail-closed.

Existing holdings are not supposed to be forced mechanically through BUY_NEW eligibility. However, there is no evidenced canonical lifecycle authority for `SUPERVISORY -> DELISTING_DECIDED -> FINAL_TRADING_PERIOD -> DELISTED` that PM/HOLD/REDUCE/EXIT consumed before valuation failed closed.

## ADD_AFTER_INELIGIBILITY_COUNT

`0`

No `61750` ADD fill was found. No `61750` planning intent after the first BUY was `BUY_ADD`; later records were HOLD or REDUCE/NO_ORDER.

## DELISTING_DECISION_TRANSITION

`NOT_MATERIALIZED`

No target-run artifact materialized a canonical 61750 lifecycle transition such as:

```text
SUPERVISORY -> DELISTING_DECIDED -> FINAL_TRADING_PERIOD -> DELISTED
```

The first canonical hard evidence inside the target run is absence from listed issues at the 2022-12-16 valuation boundary, which is too late to classify the earlier 2022-08-17 BUY as ineligible without another PIT event authority.

## A6_HALT_UPSTREAM_AVOIDABLE

`PARTIAL`

Yes, in the architectural sense: if a family-wide supervisory / delisting-risk source or missing-coverage review contract had blocked/reviewed `61750` before BUY, the 2022-12-16 held-position valuation ambiguity would not have occurred for this position.

No, in the local Runtime sense: given the actually held position and missing 2022-12-16 valuation authority, A6/A7 fail-closed behavior was correct.

## AFFECTED_SYMBOL_COUNT

`UNRESOLVED_FOR_ACTIVE_SUPERVISORY_FLAGS`

Target-run artifacts do not contain active supervisory / delisting-risk flags, so the audit cannot count symbols bought while such flags were active.

Observed family-surface context:

```text
BUY fill symbols in target run = 137
BUY fill rows in target run = 142
ADD-like planning rows = 67
```

Those are not all proven affected. They define the family surface that would require a separate source-backed eligibility audit once a supervisory / delisting-risk authority is connected.

## AFFECTED_BUY_COUNT

`UNRESOLVED_FOR_ACTIVE_SUPERVISORY_FLAGS`

## AFFECTED_ADD_COUNT

`UNRESOLVED_FOR_ACTIVE_SUPERVISORY_FLAGS`

## AFFECTED_HOLDING_COUNT

`UNRESOLVED_FOR_ACTIVE_SUPERVISORY_FLAGS`

## FAMILY_CLASSIFICATION

`MISSING_SUPERVISORY_AUTHORITY / MISSING_STATUS_FAIL_OPEN`

61750 is not proven to be a one-off consumer bypass. It belongs to the same family as the previously documented 93180-style Corporate/Event eligibility gap: public or external alert/supervision style risk may exist, but target Runtime PIT evidence does not prove a canonical source and does not force missing coverage into review.

## PRODUCTION_PATH_AFFECTED

`YES`

The affected semantics are Production-common:

- `runtime_v2.market_status.buy_eligibility` is common Runtime logic.
- Strategy BUY Quality / PC listed-info payloads carry only ordinary listed-info-compatible fields when the source only provides those fields.
- The missing coverage problem is not a Historical-only replay mutation.

Exact Production data coverage remains unresolved; if Production has no separate supervisory / delisting-risk source, the same fail-open family is active.

## ROOT_CAUSE_CLASS

`MISSING_SUPERVISORY_AUTHORITY`

Secondary classes:

- `MISSING_STATUS_FAIL_OPEN`
- `EXISTING_AUTHORITY_CONSUMER_GAP` for Strategy Intelligence missing-coverage semantics

Not primary:

- `HISTORICAL_PIT_MATERIALIZATION_GAP`
- `TEMPORAL_BINDING_GAP`
- `LEGACY_FALLBACK_BYPASS`
- `POLICY_ALLOWS_BUY_CORRECTLY`

## REGRESSION_CONFIRMED

`UNRESOLVED`

Confirmed prior contracts:

- Phase17-BV14 implemented the explicit market-status BUY guard and documented that local J-Quants listed issues did not contain special-supervision / scheduled-delisting fields unless explicitly provided.
- Current Strategy Intelligence SoT says supervision / alert / special caution / delisting pending are eligibility facts where source authority exists, and missing coverage must not become `SAFE`.
- Phase30-C / Phase30-G already documented a 93180-style alert/supervision source gap.

This A8 target does not prove a regression where an implemented 61750 supervisory field used to be consumed and is now dropped. It confirms that the broader documented Corporate/Event coverage gap is still active in the current target run.

## REPAIR_REQUIRED

`YES`

Not to special-case `61750`, and not to use future delisting outcome.

## REPAIR_DIRECTION

No implementation in A8.

Narrow family-wide repair direction:

1. Define or connect a PIT supervisory / alert / special caution / delisting-risk source authority, preferably as a Corporate/Event eligibility source separate from plain listed membership.
2. Materialize explicit coverage state per business date and symbol: `AVAILABLE`, `MISSING_COVERAGE`, `UNKNOWN`, or fact-bearing status.
3. Ensure Candidate / Strategy Intelligence emits `REVIEW_REQUIRED` or symbol-level BUY ineligibility when required event-risk coverage is missing, instead of `PASS`.
4. Preserve Phase17-BV14 no-future-leakage semantics: do not infer pre-announcement ineligibility from later delisting or disappearance.
5. Add existing-holding lifecycle semantics only after the new source authority defines what `SUPERVISORY`, `DELISTING_DECIDED`, `FINAL_TRADING_PERIOD`, and `DELISTED` mean for HOLD/REDUCE/EXIT.

## FUTURE_INFORMATION_USED_FOR_DECISION_AUDIT

`NO`

The BUY-date judgment is based on target-run 2022-08-17 PIT artifacts and current repository contracts. Later disappearance on 2022-12-16 is used only to explain downstream A6/A7 context, not to assert 2022-08-17 ineligibility.

## LONG_HISTORICAL_EXECUTED

`NO`

No fresh-run, resume, replay, or long Historical execution was performed.

## NEXT_TASK_RECOMMENDATION

`Phase31-A9 focused repair`

Scope A9 to Corporate/Event supervisory / delisting-risk authority and missing-coverage semantics. Do not implement a `61750` rule, do not use later delisting outcomes as inputs, and do not weaken the A6/A7 Current Valuation fail-closed behavior.

## Producer -> Consumer Trace

| Layer | 61750 evidence at first BUY | Judgment |
| --- | --- | --- |
| J-Quants source | `/v2/equities/master`; 2022-08-17 row present; no supervision/delisting fields | Listed membership PASS; event-risk coverage missing |
| Historical PIT materialization | run-scoped `historical_asof/2022-08-17/raw/jquants/listed_issues/data.parquet`; hash-bound; no latest fallback | PIT materialization PASS |
| Candidate / Opportunity | source candidate id `candidate-2022-08-17-61750...`; opportunity rank 39 | Candidate surface admitted |
| BUY Quality | `PIT_status=PASS`, `quality_status=PASS`, listed_info ordinary fields only | Missing coverage not blocking |
| Strategy Intelligence | `eligibility.status=PASS`, `event_coverage_status=AVAILABLE`, symbol event coverage not proven safe | First semantic gap |
| Portfolio Construction / Position Sizing | one-lot admission, target quantity 100 | Consumed already-safe upstream row |
| Runtime Planning | `BUY_NEW`, planned quantity 100 | Executable plan |
| Morning Pending / cash feasible batch | `decision=INCLUDE`, priority 1 | Pending/executable |
| Execution | BUY fill 100 @ 897 | Position opened |

## Final Questions

### 1. Should 61750 have been eligible for normal Candidate/BUY at the actual BUY date under the existing contract?

`NO`

Under the current Strategy Intelligence SoT, it should not have been a normal safe PASS. It should have been `REVIEW_REQUIRED` for missing supervisory / delisting-risk coverage. It is not proven `INELIGIBLE` from PIT evidence.

### 2. Did the system already possess the required supervisory/delisting-risk information at that time?

`NO`

The 2022-08-17 target-run source artifact did not contain that information.

### 3. If YES, where was it lost or ignored?

`NOT_APPLICABLE`

No present supervisory fact was found. The loss is source/coverage semantic: no PIT supervisory authority was materialized, and missing coverage became normal PASS.

### 4. Was the eventual 2022-12-16 valuation HALT downstream of an avoidable upstream eligibility/lifecycle gap?

`PARTIAL`

Architecturally yes if a family-wide source/coverage repair would have blocked or reviewed the 2022-08-17 BUY. Locally no: A6/A7 fail-closed was correct for the state that existed.

### 5. Is this potentially a Production-common defect rather than only a Historical-test issue?

`YES`

The source/consumer semantics are shared. Historical PIT materialization itself passed for the available listed-issues source.

### 6. Is a focused family-wide repair required?

`YES`

The repair should address supervisory / alert / special caution / delisting-risk authority and missing-coverage handling across the family, not `61750` specifically.
