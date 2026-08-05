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

## 12. Phase27-D1 Existing Position and BUY_ADD Common Contract

Phase27-D1 extends this boundary contract for Momentum Follow / Momentum Rotation existing-position lifecycle. The detailed common SoT is:

```text
docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md
```

This section applies equally to Production, Demo, and Historical. It is not a Historical-only repair and not a phase-local performance shortcut.

Phase27-D1R refines the implementation contract by requiring staged immutable artifacts: `position_intent.v1`, `target_portfolio_decision.v1`, `position_sizing_plan.v1`, and `runtime_position_plan.v1`. Portfolio Construction consumes `position_intent.v1` and produces `target_portfolio_decision.v1`; Position Sizing consumes that target decision and produces `position_sizing_plan.v1`. Neither stage may mutate an upstream artifact after publication.

Portfolio Construction must integrate all canonical position decisions into one target portfolio:

```text
BUY_NEW
ADD
HOLD
REDUCE
EXIT
NO_ACTION
```

Existing positions must be reevaluated daily. PM keeps existing-position directional intent authority, but Portfolio Construction owns target membership and target weight after integrating PM intent, Opportunity evidence, BUY Quality, Portfolio Policy, Market Context, Corporate Events, Current, Cash, and Pending.

Existing-position mapping:

| PM / Canonical Decision | Portfolio Construction meaning | Position Sizing meaning | Runtime Planning mapping |
|---|---|---|---|
| `HOLD` | Retain membership and maintain target weight | target quantity approximately equals current quantity | `NO_ACTION` when delta is zero |
| `ADD` | Retain membership and allow target weight increase when justified | positive quantity delta candidate | `BUY_ADD` |
| `REDUCE` | Retain membership with lower target weight | negative partial quantity delta candidate | sell reduce intent |
| `EXIT` | Remove target membership | full negative quantity delta candidate | sell exit intent |

`NO_ACTION` is not a Portfolio Construction substitute for HOLD reasoning. If an existing position remains in the portfolio with zero delta, the artifact must preserve the positive reason for retention or the reason that no active decision authority was available.

BUY_ADD authority:

- PM ADD is directional intent, not an order.
- Portfolio Construction must not convert PM ADD directly into Pending.
- ADD becomes executable only if Position Sizing emits a positive `quantity_delta_candidate` for a current holding and Runtime Planning maps that delta to `BUY_ADD`.
- Rank 1 alone and PM ADD alone do not justify ADD.
- Quality adjustment must not be applied twice across Portfolio Construction and Position Sizing.

Position Sizing must distinguish:

```text
total desired quantity
current quantity
quantity delta
order quantity
```

Contract formulas:

```text
target_notional_candidate = target_weight_candidate * canonical_capital_base
target_quantity_candidate = lot-rounded quantity derived from target_notional_candidate and PIT reference_price
quantity_delta_candidate = target_quantity_candidate - current_quantity
```

`canonical_capital_base` is Current Total Equity unless a later accepted common architecture contract supersedes it. Cash remains residual; Position Sizing must not create quantity merely to hit a fixed cash ratio.

## 13. Phase27-D2-D Shadow Position Sizing Plan Contract

Phase27-D2-D introduces `position_sizing_plan.v1` as a shadow-only quantity delta contract between `target_portfolio_decision.v1` and future Runtime Planning integration.

This is not the existing formal `position_sizing.v1` output and does not replace active Position Sizing, Runtime Planning, Pending, Approval, Submit, or Execution.

Required authority fields:

```text
authority_mode = SHADOW
decision_effect = NONE
runtime_connected = false
pending_decided = false
submit_decided = false
```

Existing-position mapping:

```text
PM ADD    -> positive quantity_delta_candidate or ADD_NOT_SIZED
PM HOLD   -> zero quantity_delta_candidate or HOLD_NOT_SIZED
PM REDUCE -> negative partial quantity_delta_candidate or REDUCE_NOT_SIZED
PM EXIT   -> full negative quantity_delta_candidate with target_quantity_candidate = 0 or EXIT_NOT_SIZED
```

Position Sizing Plan must not overwrite PM intent. In particular, an ADD row may not be silently converted to HOLD/zero delta, and a REDUCE row may not be silently converted to HOLD/zero delta. If the required delta cannot be sized from available evidence, the row must emit the matching `*_NOT_SIZED` status with lineage and reason codes.

Runtime meanings such as `BUY_ADD`, `BUY_NEW`, `SELL_REDUCE`, `SELL_EXIT`, Pending item IDs, Approval IDs, Submit commands, Execution IDs, and Ledger application IDs are downstream fields and are forbidden in `position_sizing_plan.v1`.

## 14. Phase27-D2-E Runtime Planning Quantity Delta Integration

Phase27-D2-E makes `position_sizing_plan.v1` the canonical Runtime Planning quantity-delta input when present. Runtime Planning does not recalculate Strategy decisions; it only maps quantity delta to runtime action.

Canonical Runtime Planning mapping:

| Position state | Canonical quantity delta | Target quantity | Runtime Planning output |
|---|---:|---:|---|
| New position | Positive | Positive | `BUY_NEW` |
| Existing position | Positive | Positive | `BUY_ADD` |
| Existing position | Zero | Current quantity | `NO_ACTION` |
| Existing position | Negative partial | Greater than zero | `SELL_REDUCE` |
| Existing position | Full negative | Zero | `SELL_EXIT` |

Authority rules:

- If canonical `quantity_delta_candidate` exists, PM fallback is disabled for that row.
- If canonical `position_sizing_plan.v1` is absent, legacy PM fallback may remain only as compatibility behavior.
- Canonical sizing lineage plus PM fallback on the same row is duplicate authority and must resolve to `REVIEW_REQUIRED` or `BLOCK`.
- Runtime Planning must preserve Portfolio Construction and Position Sizing outputs; it must not change target weight, target quantity, sizing formula, cash policy, Quality, Opportunity, Momentum, Incremental Eligibility, or PM intent.

## 15. Phase27-D3 PM Performance Philosophy Boundary

Phase27-D3 freezes PM as the Strategy Action Authority for existing-position `ADD`, `HOLD`, `REDUCE`, and `EXIT`. Portfolio Construction resolves target membership and target weight from PM intent plus evidence. Position Sizing resolves target quantity and quantity delta. Runtime Planning maps quantity delta to runtime action. None of these downstream stages may independently create PM action philosophy or convert profit, rank, quality, cash, or sizing evidence into a new BUY/HOLD/SELL decision.

Opportunity, BUY Quality, Market Context, Momentum Evidence, and Incremental Eligibility are evidence producers for PM and Portfolio Construction. They are not action producers. Profit-taking is not an adopted independent PM philosophy; profit presence may be evidence context, but it is not by itself a REDUCE or EXIT authority.
