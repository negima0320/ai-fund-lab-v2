# Portfolio Construction and Position Sizing Boundary Contract

作成日: 2026-07-30

## 1. Authority

本書はPhase23-ANで確定した、以下の境界Contractである。

```text
Opportunity Ranking
-> Portfolio Construction
-> Position Sizing
```

上位SoTは `docs/02_architecture/strategy_architecture_v1.md` であり、本書は同文書の `3.3.1 Opportunity Score -> Target Weight -> Position Sizing Boundary` の詳細Contractである。

## 2. Selected Responsibility Model

採用モデル:

```text
Opportunity Ranking
  -> relative opportunity signal

Portfolio Construction
  -> target membership
  -> target_weight

Position Sizing
  -> target_notional
  -> target_quantity_candidate
  -> quantity_delta_candidate
```

これはPhase23-AN Option Aである。

## 3. Runtime Opportunity Score Contract

`runtime_opportunity_score` は、銘柄間の相対的投資機会を示すOpportunity Ranking Authorityのsignalである。

Contract:

| Field | Contract |
|---|---|
| producer | Opportunity Ranking Authority |
| canonical field | `runtime_opportunity_score` |
| semantics | relative opportunity / expected edge evidence |
| value range | finite numeric |
| sign | signful; negative allowed |
| higher-is-better | true |
| ranking use | allowed as Portfolio Construction input |
| filtering use | allowed only inside Portfolio Construction with reason evidence |
| membership use | allowed as one input, not sole BUY authority |
| target weight use | allowed only through Portfolio Construction Target Weight Authority |
| Position Sizing direct use | forbidden |
| calibration dependency | lineage must disclose calibration state |
| population scope dependency | lineage must disclose population scope |
| PIT authority | business date point-in-time |

`runtime_opportunity_score` is not:

```text
allocation_quality_score
target_weight
target_notional
quantity
BUY authorization
Submit authorization
```

## 4. Target Weight Contract

Canonical fields:

```text
target_weight
target_weight_authority
target_weight_resolution
```

Semantics:

```text
target_weight = Portfolio全体に対する対象銘柄の目標保有比率
```

Range:

```text
0.0 <= target_weight <= single_name_weight_cap
sum(target_weight) <= target_gross_exposure
```

Zero is valid when supported by reason evidence.

Examples:

```text
eligible candidate but target_weight = 0
candidate excluded
existing position retained at current weight
existing position reduced
whole portfolio BUY count = 0
```

Required authority:

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

## 5. Position Sizing Input / Output Contract

Position Sizing input:

```text
target_weight
portfolio_total_equity
investable_capital
reference_price
trading_unit
current_quantity
current_notional
current_weight
single_name_weight_cap
minimum_executable_notional_policy
```

Position Sizing output:

```text
target_notional
target_quantity_candidate
quantity_delta_candidate
rounding_result
minimum_executable_notional_result
cash_residual_evidence
reason_codes
```

Position Sizing must not reinterpret `runtime_opportunity_score` to decide membership or target weight.

## 6. Existing Position Boundary

Portfolio Construction owns:

```text
target membership
target_weight
target portfolio including existing positions
ADD / REDUCE / EXIT intent classification as target portfolio delta evidence
```

Position Sizing owns:

```text
current quantity comparison
target quantity candidate
quantity delta candidate
target notional candidate
minimum executable notional review
rounding evidence
```

Position Management retains HOLD / ADD / REDUCE / EXIT intent authority for existing positions. Portfolio Construction integrates that intent into target portfolio; it does not destroy PM intent lineage.

## 7. Opportunity Score Usage

Allowed:

```text
rank ordering evidence
relative opportunity evidence
Portfolio Construction membership input
Portfolio Construction target weight input with explicit method/version/reasons
```

Forbidden:

```text
raw score -> allocation_quality_score silent promotion
raw score -> target_weight direct substitution
raw score -> Position Sizing quality multiplier
clamp
absolute value
score shift
sigmoid
current-day min-max
current-day percentile rank
negative-to-zero
test-run optimization
forced BUY
fixed BUY count
```

Negative score is valid raw evidence. It may lead to exclusion, zero target weight, review-required, or adoption only if the Portfolio Construction method and reasons justify that result.

## 8. Option Comparison

| Option | Summary | Judgment |
|---|---|---|
| A | Portfolio Construction produces target weight | Selected |
| B | Position Sizing derives weight from opportunity score | Rejected |
| C | Separate allocation-quality authority | Deferred |

Option A best matches Strategy Architecture v1: Portfolio Construction owns target portfolio and target weight, while Position Sizing converts target allocation into notional / quantity candidates.

Option B is rejected because it concentrates Strategy judgment inside Position Sizing and would require Position Sizing to reinterpret raw opportunity score.

Option C is not rejected forever, but is not mandatory for the boundary. A separate allocation-quality authority may be introduced only if it has its own approved producer, semantics, PIT lineage, and regression plan.

## 9. Design Acceptance Cases

Positive opportunity case:

```text
Opportunity Ranking emits positive runtime_opportunity_score.
Portfolio Construction decides membership and target_weight using policy/capacity/risk evidence.
Position Sizing converts target_weight to notional and quantity candidate.
```

Negative opportunity case:

```text
Negative runtime_opportunity_score is schema-valid raw evidence.
Portfolio Construction explains exclude / zero weight / review / rare adoption by method and reason codes.
Position Sizing does not reinterpret the score.
```

Zero-trade day:

```text
BUY 0 is valid when target weights or downstream executable quantities are zero with explicit reasons.
```

Existing position:

```text
Portfolio Construction decides target_weight.
Position Sizing compares current quantity/notional to target and emits delta candidate.
```

Missing target weight authority:

```text
REVIEW_REQUIRED
target_notional = 0
no silent zero success
no forced BUY
```

## 9.1 Portfolio Policy -> Portfolio Construction Authority Binding

Portfolio Construction resolves Target Weight Authority directly from the AQ Portfolio Policy artifact. The canonical Portfolio Policy fields are:

```text
target_position_count
target_gross_exposure_ratio
target_gross_exposure
cash_reserve_ratio
cash_reserve
single_name_weight_cap
deployment_posture
```

`target_gross_exposure_ratio` and `target_gross_exposure` must match when both are present. `cash_reserve_ratio` and `cash_reserve` must also match. Conflict, invalid type, business-date mismatch, missing source hash, or missing required field is fail-closed and becomes `target_weight_authority_unresolved`.

Legacy Dynamic Position Count and Dynamic Cash / Exposure artifacts are not canonical Portfolio Construction inputs after AQ. If present, they are `NON_CANONICAL_OBSERVABILITY` or `LEGACY_READ_ONLY` only and must not change target membership or target weight.

Valid zero is distinct from unresolved authority:

```text
target_position_count = 0
target_gross_exposure = 0
resolved_target_member_count = 0
```

This is a normal zero-allocation Strategy outcome, not REVIEW_REQUIRED.

## 10. Downstream Planning Chain Boundary

Phase23-AR後、Position Sizingのcanonical outputはそのままRuntime Planningへ渡される。

Canonical quantity fields:

```text
target_notional
target_quantity_candidate
quantity_delta_candidate
quantity_status
```

Runtime Planning consumes:

```text
target_quantity_candidate
quantity_delta_candidate
quantity_status
```

Runtime Planning emits:

```text
planning_intent
order_side_intent
planned_quantity
no_order_reason
planning_reason
```

Strategy Planning Authority validates `planned_quantity` and materializes `pending_order_plan`. It does not recompute quantity from target notional and price. Price evidence is used for execution feasibility and estimated amount only.

Capital Deployment is no longer a standalone canonical Strategy decision stage. Any retained Capital Deployment artifact is noncanonical observability or delayed-retirement evidence and must not change Runtime Planning output.

Position Sizing isolation:

```text
Position Sizing can compute notional/quantity from target_weight, capital, price, trading unit, and current holdings without raw opportunity score.
```

## 11. Implementation Impact

Future implementation task should update Production-common code only within this boundary:

```text
Portfolio Construction emits target_weight authority.
Position Sizing consumes target_weight authority.
Position Sizing stops treating allocation_quality_score as mandatory when target_weight authority is available.
Runtime Planning receives downstream quantity candidate only after target weight and sizing authority are valid.
```

Runtime rerun is not authorized by this design task.
