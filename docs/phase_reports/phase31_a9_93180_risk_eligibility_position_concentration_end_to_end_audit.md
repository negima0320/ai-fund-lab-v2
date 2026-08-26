# Phase31-A9 — 93180 Asia Development Capital Risk Eligibility / Position Concentration End-to-End Audit

Status: COMPLETE
Task type: READ-ONLY ROOT-CAUSE / ELIGIBILITY / CAPITAL-ALLOCATION AUDIT

## PRIMARY_JUDGMENT

```text
PHASE31_A9_93180_POSITION_SIZE_NORMAL_BUT_SPECIAL_RISK_ELIGIBILITY_GAP_CONFIRMED
```

The target-run `93180` position was not excessive by notional / weight. The observed `8300` shares came from one `BUY_NEW` fill on 2022-08-10: `8300 @ 6 = 49,800 JPY`, about `5.02%` of post-fill equity and within Strategy `18%` / Safety `25%` caps. The large share count is explained by the 6 JPY share price and 100-share lot sizing.

The root issue is upstream eligibility evidence, not position sizing, not B10, and not ADD amplification. The target run's PIT J-Quants listed-issues source proved ordinary listed membership / product category only. It did not materialize JPX security-on-alert / special caution / supervision / delisting-risk status. Strategy Intelligence then produced `eligibility.status = PASS` even while symbol event coverage for `93180` was `UNKNOWN`. That matches the A8 family: a partial listed-status authority exists, but missing special-risk coverage is not fail-closed into review for Candidate / BUY.

FUTURE_INFORMATION_USED_FOR_DECISION_AUDIT:

```text
NO
```

LONG_HISTORICAL_EXECUTED:

```text
NO
```

## Target Run

TARGET_RUN_ID:

```text
runtime-test-historical-extended-smoke-20260820T120909096218Z
```

TARGET_RUN_MATCH_CONFIDENCE:

```text
HIGH
```

Selection evidence:

- `run_state.json`: profile `historical-extended-smoke`, start `2022-08-10`, status `RUNNING`, completed days through `2022-09-30`.
- 2022-08-10 `execution/fills.json`: `93180 BUY 8300 @ 6 = 49,800`.
- 2022-08-10 `current_valuation_refresh/valuation_projection.json`: `cash = 556,520`, `new_total_market_value = 436,280`, equity `992,800`.
- 2022-08-10 `strategy/portfolio_construction.json`: B10 `MARGINAL_CAPITAL_VALUE_AUTHORITY` present, `canonical_marginal_capital_priority_index = 3`.

Earlier local run `runtime-test-historical-extended-smoke-20260818T015851711672Z` also starts 2022-08-10, but the 20260820 run exactly matches the user's current timeline and current B10 architecture.

## Acquisition Lineage

FIRST_93180_BUY_DATE:

```text
2022-08-10
```

FIRST_93180_BUY_QUANTITY:

```text
8300
```

FIRST_93180_BUY_NOTIONAL:

```text
49,800 JPY
```

TOTAL_93180_BUY_QUANTITY_TO_2022_08_10:

```text
8300
```

TOTAL_93180_BUY_NOTIONAL_TO_2022_08_10:

```text
49,800 JPY
```

93180_QUANTITY_8300_ORIGIN:

```text
SINGLE_BUY
```

Acquisition row:

| Date | Side | Semantic | Qty | Price | Notional | Pre qty | Post qty | Campaign |
|---|---:|---|---:|---:|---:|---:|---:|---|
| 2022-08-10 | BUY | BUY_NEW | 8,300 | 6 | 49,800 | 0 | 8,300 | `pc-0a05804778085f9b-93180-0001` |

Lineage:

| Stage | Evidence |
|---|---|
| Candidate / opportunity | rank `4`, candidate order `4`, runtime opportunity score `-0.09100653` |
| Strategy Intelligence | `eligibility.status = PASS`, `entry_state = CONTINUATION_WITH_CAUTION` |
| BUY Quality | `quality_band = HIGH`, `quality_score = 0.774208`, `quality_action = FULL_ALLOCATION_ELIGIBLE` in BUY Quality; PC carries `REDUCED_ALLOCATION_ONLY` through entry admission |
| Portfolio Construction | target weight `0.05`, marginal priority `3`, class `ELIGIBLE_COMPARABLE` |
| Position Sizing / lot authority | final allocated quantity `8300`, executable lots `83`, one-lot notional `600` |
| Runtime Planning | `planning_intent = BUY_NEW`, `planned_quantity = 8300` |
| Pending / cash feasibility | `executable_quantity = 8300`, `decision = INCLUDE`, priority index `3` |
| Execution | fill quantity `8300`, execution price `6`, gross notional `49,800` |

## Concentration / Quantity

93180_MARKET_VALUE_AT_8300_SHARES:

```text
49,800 JPY
```

93180_WEIGHT_AT_8300_SHARES:

```text
5.0161% of post-fill equity
```

Calculation:

```text
cash 556,520 + market_value 436,280 = equity 992,800
49,800 / 992,800 = 0.050161
```

Decision-time target calculation:

```text
initial equity 1,000,000
x target weight 0.05
= target notional 50,000

target notional 50,000
/ reference price 6
= 8,333.33 raw shares

apply 100-share lot floor
= 8,300 final shares

8,300 x 6 = 49,800
```

93180_STRATEGY_CAP:

```text
0.18
```

93180_SAFETY_CAP:

```text
0.25
```

93180_CAP_BREACH:

```text
NO
```

CAP_AUTHORITY_STATUS:

```text
PASS
```

Applied concentration / sizing controls:

| Control | Status | Evidence |
|---|---|---|
| Strategy single-symbol cap | APPLIED / PASS | `strategy_cap_weight = 0.18`, max strategy lots `300`, cap preserved |
| Safety hard cap | APPLIED / PASS | `safety_hard_cap_weight = 0.25`, max safety lots `416`, cap preserved |
| Low-price / tick cap | APPLIED | `price_tick_risk_tier = EXTREME`, `price_tick_cap_weight = 0.05` |
| Liquidity capacity | APPLIED / PASS | rolling median traded value 20BD `28,410,900`, capacity cap weight `0.284109` |
| Minimum meaningful notional | DIAGNOSTIC_ONLY | threshold `50,000`, minimum policy lots `84`; final 83 lots = 49,800 |
| Lot boundary | APPLIED / PASS | 100-share lot, 83 lots |
| Residual reallocation | USED / NON-DEFECTIVE | `residual_destination = 93180`, `residual_recycled = true`, still target `0.05` and cap-preserving |

LOW_PRICE_SHARE_COUNT_EXPECTED:

```text
YES
```

POSITION_QUANTITY_RECONCILIATION:

```text
PASS
```

The share count looks large only because the security traded at 6 JPY. The notional was normal for the current low-price-capped target.

## Selection Evidence

93180_SELECTION_STRENGTH:

```text
MEDIUM
```

Evidence:

- Opportunity rank `4` of 50, candidate order `4`.
- BUY Quality `HIGH`, score `0.774208`.
- Relative opportunity percentile `0.94`.
- Runtime opportunity score `-0.09100653`, explicitly uncalibrated and treated as relative metadata, not an economic expected return.
- Momentum trajectory `MIXED_OR_UNRESOLVED`, not strong.
- Strategy Intelligence entry state `CONTINUATION_WITH_CAUTION`.
- Downside risk `PASS` but volatility `ELEVATED_RISK`.
- Market Context regime `BULL`.

Interpretation:

```text
93180 was selected because it ranked highly enough under the current relative
opportunity / BUY Quality / entry-admission model after ordinary listed
eligibility passed. It was not selected because of a low-price sizing defect.
The eligibility concern is the missing special-risk authority upstream.
```

Competing 2022-08-10 marginal capital candidates:

| Priority | Symbol | Opportunity rank | Intent | Target weight | Class |
|---:|---|---:|---|---:|---|
| 1 | 94320 | 1 | BUY_NEW | 0.052632 | ELIGIBLE_COMPARABLE |
| 2 | 66590 | 2 | BUY_NEW | 0.052632 | ELIGIBLE_COMPARABLE |
| 3 | 93180 | 4 | BUY_NEW | 0.050000 | ELIGIBLE_COMPARABLE |
| 4 | 23700 | 5 | BUY_NEW | 0.052632 | ELIGIBLE_COMPARABLE |
| 5 | 23880 | 8 | BUY_NEW | 0.052632 | ELIGIBLE_COMPARABLE |

## Contemporaneous Risk Classification

Target-run PIT states at first BUY and 2022-08-10:

| Field | State |
|---|---|
| 93180_SUPERVISORY_STATE | NOT_MATERIALIZED |
| 93180_CAUTION_STATE | NOT_MATERIALIZED |
| 93180_SPECIAL_TREATMENT_STATE | NOT_MATERIALIZED |
| 93180_DELISTING_RISK_STATE | NOT_MATERIALIZED |
| 93180_LISTING_STATE | LISTED / Standard market / ProdCat `011` |
| 93180_CORPORATE_EVENT_STATE | `NO_EVENT` in Strategy / Corporate Event artifact |
| 93180_GOVERNANCE_RISK_STATE | NOT_MATERIALIZED |

Raw listed source row:

```text
Date = 2022-08-10
Code = 93180
CoName = アジア開発キャピタル
CoNameEn = Asia Development Capital Co.Ltd.
MktNm = スタンダード
ProdCat = 011
MrgnNm = 信用
```

The raw and feature listed-issues artifacts contain only ordinary listed-master fields. They do not contain `special_supervision_status`, `supervision_status`, `market_status`, `listing_status`, `delisting_status`, `scheduled_delisting_date`, `listing_termination_date`, JPX security-on-alert state, or equivalent governance-risk fields.

Prior Phase30-C evidence documents public JPX alert context for 93180 predating the 2022-08-10 BUY. A9 does not use later delisting or later PnL as an eligibility reason; it uses that earlier public alert only to classify the missing source family. The target run itself did not materialize that public-risk state.

## Existing Authority Coverage

RISK_ELIGIBILITY_AUTHORITY_EXISTS:

```text
PARTIAL
```

Paths:

| Path | Classification | Semantics |
|---|---|---|
| `src/ai_fund_lab_v2/runtime_v2/market_status/buy_eligibility.py` | CANONICAL_PARTIAL | Blocks missing listed authority, absent current listing, explicit ineligible/review status fields, and explicit delisting dates. |
| Historical J-Quants listed-issues snapshots | CANONICAL_PARTIAL | PIT ordinary listed membership source. |
| Strategy listed-info propagation | CANONICAL_PARTIAL | Carries `Code`, `MktNm`, `ProdCat`, `current_listed` / product compatibility. |
| Strategy Intelligence event eligibility | CANONICAL_DESIGN_PARTIAL_IMPLEMENTATION | SoT says missing event coverage is uncertainty, not safe; target artifact still emitted ordinary PASS for 93180. |
| Public JPX alert / supervision source | NOT_MATERIALIZED | Not present as target-run PIT artifact. |

Source / consumer coverage:

| Question | Answer |
|---|---|
| RISK_INFO_PRESENT_IN_RAW_SOURCE | NO |
| RISK_INFO_PRESENT_IN_NORMALIZED_SOURCE | NO |
| RISK_INFO_MATERIALIZED_IN_ELIGIBILITY | NO |
| RISK_INFO_CONSUMED_BY_CANDIDATE | NO |
| RISK_INFO_CONSUMED_BY_BUY_DECISION | NO |

MISSING_RISK_STATUS_SEMANTIC:

```text
PASS / ELIGIBLE in the executed BUY path, despite UNKNOWN symbol event coverage
```

MISSING_RISK_STATUS_FAIL_OPEN:

```text
YES
```

Evidence:

- `strategy_intelligence.symbol_intelligence["93180"].downside_risk.event_uncertainty.symbol_coverage_status = UNKNOWN`.
- Same symbol emitted `eligibility.status = PASS`, `disqualifying_facts = []`, `review_required_facts = []`.
- Portfolio Construction consumed `strategy_intelligence_eligibility_status = PASS` and admitted a BUY_NEW target member.

## A8 Relationship

A8_FAMILY_RELATIONSHIP:

```text
SAME_MISSING_STATUS_FAIL_OPEN_FAMILY
```

The exact symbols differ, and no present target-run field was ignored for 93180. The shared family is: ordinary listed membership is PIT and partial, but supervisory / alert / special-risk coverage is absent and does not force Candidate / BUY into review.

## B10 Causality

B10_ACTIVE_ON_TARGET_RUN:

```text
YES
```

93180_MARGINAL_CAPITAL_PRIORITY:

```text
3
```

93180_MARGINAL_CAPITAL_ORDER:

```text
94320, 66590, 93180, 23700, 23880, ...
```

93180_COMPETING_CAPITAL_CANDIDATES:

```text
19 marginal-capital candidates; all observed B10 classes were ELIGIBLE_COMPARABLE on 2022-08-10.
```

B10_CAUSED_93180_ENTRY:

```text
NO
```

B10_CAUSED_93180_POSITION_SIZE:

```text
NO
```

B10 ordered already-eligible capital competitors. It did not make 93180 eligible, did not create the 5% target, and did not bypass Strategy/Safety caps. The upstream special-risk coverage gap pre-existed B10's ordering role.

## Liquidity / Tradability

PRICE_AT_SIZING:

```text
6 JPY
```

TRADABLE_UNIT:

```text
100 shares
```

LOT_NOTIONAL:

```text
600 JPY
```

TARGET_NOTIONAL:

```text
50,000 JPY
```

TARGET_WEIGHT:

```text
0.05
```

RAW_QUANTITY:

```text
8,333.33 shares
```

FINAL_QUANTITY:

```text
8,300 shares
```

RESIDUAL_REALLOCATION_USED:

```text
YES
```

LIQUIDITY_ELIGIBILITY_STATUS:

```text
PASS
```

Liquidity / tradability evidence:

- `rolling_median_traded_value_20 = 28,410,900`.
- `LIQUIDITY_CAPACITY_AUTHORITY` source: J-Quants daily bars, median `close * volume` over last 20 PIT rows.
- `liquidity_capacity_status = NORMAL`.
- `capacity_ratio = 0.00185253`.
- `broker_eligibility.status = PASS`, ProdCat `011`, current listed true.
- `one_lot_feasibility_status = PASS`.

Low-price microstructure risk was observed (`price_tick_risk_tier = EXTREME`) and reduced allocation to the current 5% cap, but it did not fail tradability.

## ADD / Winner Amplification

93180_ADD_INTENT_COUNT:

```text
0
```

93180_POSITIVE_INCREMENT_COUNT:

```text
0
```

93180_BUY_ADD_FILL_COUNT:

```text
0
```

93180_BUY_ADD_NOTIONAL:

```text
0 JPY
```

No 93180 ADD / BUY_ADD amplification occurred in the target run before the 2022-08-16 full EXIT.

## SELL / REDUCE Behavior

Post-acquisition lifecycle:

| Date | PM decision | Execution | Quantity | Price | Notional | Notes |
|---|---|---|---:|---:|---:|---|
| 2022-08-12 | HOLD | no sell | 0 | 6 | 0 | `trend_continuation`, `downside_risk_contained` |
| 2022-08-15 | REDUCE | SELL | 2,000 | 6 | 12,000 | `REDUCE_BY_WEAK_HOLD_SCORE` |
| 2022-08-16 | EXIT | SELL | 6,300 | 5 | 31,500 | `EXIT_BY_TREND_AND_EDGE_BREAK` |

The system recognized deterioration quickly after entry. This does not repair the BUY eligibility gap, but it argues against a SELL / REDUCE lifecycle defect for this campaign.

## Family-Wide Risk Audit

Because the target source foundation lacks explicit special-risk fields, every BUY in the completed target-run window lacks explicit proof of supervisory / alert / special-treatment safety.

Window:

```text
2022-08-10 through 2022-09-30 completed business days
```

AFFECTED_SYMBOL_COUNT:

```text
63
```

AFFECTED_BUY_COUNT:

```text
68
```

AFFECTED_BUY_NOTIONAL:

```text
3,858,530 JPY
```

AFFECTED_ADD_COUNT:

```text
5
```

AFFECTED_CURRENT_HOLDING_COUNT:

```text
8 as of completed day 2022-09-30
```

Family classification:

```text
SYSTEMATIC_SOURCE_COVERAGE_GAP
```

This does not mean all 63 symbols were actually special-risk securities. It means the target run did not prove a source authority capable of distinguishing special-risk from ordinary listed status for BUY eligibility.

## Production Risk / Regression / Repair

PRODUCTION_PATH_AFFECTED:

```text
YES
```

The affected path is Production-common Strategy / Runtime BUY eligibility because `buy_eligibility.py`, BUY Quality, Strategy Intelligence, Portfolio Construction, Runtime Planning, Pending, Submit, and Execution are shared Production-common code paths. If Production uses only the same J-Quants listed master fields, the special-risk coverage gap is active there too.

ROOT_CAUSE_CLASS:

```text
MISSING_STATUS_FAIL_OPEN
```

Supporting class:

```text
MISSING_SPECIAL_RISK_AUTHORITY
```

ELIGIBILITY_RISK_SEVERITY:

```text
HIGH
```

POSITION_SIZING_RISK_SEVERITY:

```text
LOW
```

B10_RISK_SEVERITY:

```text
LOW
```

REGRESSION_CONFIRMED:

```text
YES
```

Contract basis:

- `docs/02_architecture/strategy_intelligence_architecture_v1.md`: supervision / alert / special caution and authoritative delisting risk are disqualifying or review-required where source exists, and missing event data must not be converted to `SAFE`.
- A8: same family already classified as partial authority / missing-status fail-open for 61750.

REPAIR_REQUIRED:

```text
YES
```

REPAIR_DIRECTION:

```text
Phase31-A10 focused eligibility repair:
restore/materialize family-wide special-risk authority or change missing
special-risk coverage from ordinary PASS to UNKNOWN / REVIEW_REQUIRED before
Candidate / BUY admission. No symbol-specific blacklist.
```

Do not implement `if symbol == "93180": reject`. Do not use later delisting or later PnL as eligibility logic.

## Required Output Summary

TARGET_RUN_ID:

```text
runtime-test-historical-extended-smoke-20260820T120909096218Z
```

FIRST_93180_BUY_DATE:

```text
2022-08-10
```

FIRST_93180_BUY_QUANTITY:

```text
8300
```

FIRST_93180_BUY_NOTIONAL:

```text
49,800 JPY
```

93180_QUANTITY_8300_ORIGIN:

```text
SINGLE_BUY
```

93180_MARKET_VALUE_AT_8300_SHARES:

```text
49,800 JPY
```

93180_WEIGHT_AT_8300_SHARES:

```text
5.0161%
```

93180_STRATEGY_CAP:

```text
0.18
```

93180_SAFETY_CAP:

```text
0.25
```

93180_CAP_BREACH:

```text
NO
```

RISK_INFO_PRESENT_IN_RAW_SOURCE:

```text
NO
```

RISK_INFO_MATERIALIZED_IN_ELIGIBILITY:

```text
NO
```

RISK_INFO_CONSUMED_BY_CANDIDATE:

```text
NO
```

NEXT_TASK_RECOMMENDATION:

```text
Phase31-A10 focused eligibility repair
```

## Final Questions

### 1. Was 8300 shares actually excessive when measured by notional / portfolio weight?

```text
NO
```

### 2. Was 93180 legitimately eligible under the existing decision-time contract?

```text
NO
```

It was eligible under the executed partial listed-membership path, but not under the current Strategy Intelligence event-risk SoT requiring missing event coverage to remain uncertainty / review rather than ordinary safe PASS.

### 3. Did the system possess contemporaneous caution/special-risk information for 93180?

```text
NO in target-run PIT artifacts; YES as prior documented public context.
```

### 4. If risk information was missing, did the system incorrectly interpret that absence as SAFE?

```text
YES
```

### 5. Did B10 create the eligibility problem?

```text
NO
```

### 6. Did B10 materially increase the 93180 position size?

```text
NO
```

### 7. Was the 8300-share quantity explainable simply by low share price and normal target notional?

```text
YES
```

### 8. Is this a family-wide Production-common safety/eligibility issue?

```text
YES
```

### 9. Is a repair required before continuing performance work?

```text
YES
```
