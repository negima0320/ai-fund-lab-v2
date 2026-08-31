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

Phase29-L21T-AH clarifies the active Runtime contract:

```text
runtime_opportunity_score = canonical score field
expected_edge_score = deprecated compatibility alias
expected_return = deprecated compatibility alias, not economic return unless
  explicit calibrated economic metadata says otherwise
```

When `calibration_applied=false` and `economic_units_available=false`,
`runtime_opportunity_score` is an `uncalibrated_relative_model_score`.  Its sign
is not an absolute BUY_NEW authority.  A value `<= 0` must not by itself reject
a BUY_NEW candidate before BUY Quality, Portfolio Construction, Position
Sizing, lot/safety, and Submit feasibility evaluate the candidate.

An absolute economic zero boundary is allowed only when the score authority
explicitly states calibrated economic units:

```text
calibration_applied = true
economic_units_available = true
semantic_role = calibrated economic expected return / edge
```

`below_opportunity_top20` is ranking metadata / diagnostic shortlist evidence
for uncalibrated opportunity artifacts.  It is not a hard BUY_NEW eligibility
rejection by itself, and `top20` membership is not automatic BUY permission.

Phase29-L21T-AK completes this contract at the Portfolio Construction consumer:

```text
Portfolio Construction must consume the canonical opportunity score metadata:

canonical_score_field
score_semantic_role
calibration_applied
economic_units_available
```

When the active contract is:

```text
canonical_score_field = runtime_opportunity_score
score_semantic_role = uncalibrated_relative_model_score
calibration_applied = false
economic_units_available = false
```

Portfolio Construction must not use `runtime_opportunity_score <= 0`,
`non_positive_expected_edge_score`, or standalone `below_opportunity_top20` as
absolute BUY_NEW hard rejection authority.  They remain relative ranking /
diagnostic metadata and may still affect documented relative competition through
existing Buy Quality and Portfolio Construction reasoning.

Hard no-buy reasons remain authoritative.  A combined reason such as
`below_opportunity_top20|high_downside_risk_score|non_positive_expected_edge_score`
must still block because `high_downside_risk_score` is independently hard.
Missing or malformed semantic metadata must not fail open.  A future calibrated
economic artifact may use an economic zero boundary only when calibration and
economic units are explicit.

Phase29-L21T-AM fixes the Production-common adapter boundary for this contract:

```text
Opportunity source artifact
-> Runtime / Strategy adapter source summary
-> Portfolio Construction
```

When the Opportunity source artifact contains the four canonical score semantic
fields, the runtime adapter must preserve them in the Portfolio Construction
source-summary contract:

```text
canonical_score_field
score_semantic_role
calibration_applied
economic_units_available
```

The adapter must not strip source-present metadata at consumer boundaries.  It
also must not infer, fabricate, or silently default semantic metadata from the
score value, score field name, reason codes, or score sign.  Explicit boolean
values such as `calibration_applied=false` and `economic_units_available=false`
are meaningful authority values and must not be converted to missing values.

If the Opportunity source artifact truly lacks required semantic metadata, or
the metadata is malformed / unsupported, Portfolio Construction must remain
fail-closed and must not assume uncalibrated relative semantics.

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

## 6. Canonical ADD Marginal Capital Competition Shadow Contract

Phase31-G113 adds `canonical_add_marginal_capital_competition.v1` as a
Portfolio Construction owned SHADOW / NON-AUTHORITATIVE evidence contract.

This contract answers a narrower question than PM ADD eligibility:

```text
Is the next executable ADD increment the best current use of marginal capital
relative to NEW_BUY, other ADD, Cash, and residual optionality?
```

Authority boundaries:

| Responsibility | Owner |
|---|---|
| PM ADD intent and ADD eligibility inputs | POSITION_MANAGEMENT |
| ADD investment evidence inputs | existing canonical ADD evidence |
| marginal ADD capital competition | PORTFOLIO_CONSTRUCTION |
| discrete quantity authority | POSITION_SIZING |
| executable order consumption | Runtime |

G113 status:

```text
schema_version = canonical_add_marginal_capital_competition.v1
authority = SHADOW
authority_status = SHADOW_NON_AUTHORITATIVE
authoritative_allocation_changed = false
feeds_position_sizing = false
feeds_runtime_planning = false
feeds_submit = false
feeds_execution = false
```

The shadow frontier must include:

- eligible NEW_BUY candidates from the final PC security frontier;
- eligible ADD candidates;
- Cash as a first-class competitor;
- residual optionality as an explicit non-security capital state.

ADD candidates are represented as executable marginal increments rather than as
one indivisible requested block. Each increment must preserve hypothetical
position-size state:

```text
pre_increment_quantity
post_increment_quantity
pre_increment_weight
post_increment_weight
remaining_strategy_headroom
remaining_safety_headroom
```

The shadow output may classify increments as:

```text
ADD_MARGINAL_PREFERRED
COMPARABLE_MARGINAL
CASH_MARGINAL_PREFERRED
SAFETY_TERMINAL
LOT_INFEASIBLE
INSUFFICIENT_EVIDENCE
```

`CASH_PREFERRED_PARTICIPATION_VALID` is not equivalent to
`ADD_MARGINAL_CAPITAL_BEATS_CASH`. It means reduced security participation is
allowed under the Cash-preferred participation contract; it does not prove that
the next ADD increment strictly dominates Cash.

No G113 shadow field may use future return, later campaign outcome, Historical
PnL, Paper Ledger performance, MFE/MAE, or selected/bought outcome as a scoring
input. G113 introduces no production threshold, weight, performance-fitted
penalty, or tuned allocation parameter.

Phase31-G50 binding clarification:

Portfolio Construction owns the canonical final capital winner and selected
deployment set. Position Sizing owns only discrete notional / quantity
conversion for rows admitted by that selected deployment set. Pre-binding
`target_weight`, old portfolio members, rank, or candidate membership may not
create an incremental BUY/ADD/re-entry quantity after the canonical capital
competition has selected Cash or another security.

If the canonical deployment set has `CASH_OPTIONALITY` as final winner, the
incremental security sizing input set is empty. Position Sizing may still
preserve existing HOLD baselines and size PM-owned SELL/REDUCE/EXIT paths, but
it must emit zero positive BUY/ADD quantity for defeated securities. If the
canonical deployment set selects a security, only selected set members may
produce positive incremental quantity. Runtime Planning then maps the already
bound Position Sizing output; it must not regenerate BUYs from pre-binding
targets.

```text
PC_FINAL_CAPITAL_WINNER_OWNER = PORTFOLIO_CONSTRUCTION
CANONICAL_DEPLOYMENT_SET_OWNER = PORTFOLIO_CONSTRUCTION
POSITION_SIZING_CAPITAL_WINNER_AUTHORITY = NO
PRE_BINDING_TARGET_CAN_CREATE_INCREMENTAL_QUANTITY = NO
RUNTIME_PLANNING_REINTRODUCES_DEFEATED_SECURITY = NO
LINEAGE_PERSISTENCE_IS_NOT_DECISION_BINDING = YES
```

Phase31-G53 multi-allocation refinement:

The G50 executable-binding principle remains permanent, but `SINGLE` is no
longer the general capital-allocation semantic. Portfolio Construction must
bind Position Sizing through a canonical executable allocation object; however,
that object may authorize multiple securities plus Cash in the same business
date.

Portfolio Policy owns the `incremental_capital_budget_envelope`. Portfolio
Construction owns allocation of that envelope across `NEW_BUY`, `ADD`,
eligible re-entry-as-`NEW_BUY`, and Cash. Position Sizing receives the
authorized allocation rows and converts them to lot-aware quantities. Position
Sizing must not choose economic winners, reinterpret candidate rank, override
Cash allocation, or re-open defeated allocations.

The migrated canonical object is a multi-allocation deployment set:

```text
canonical_multi_allocation_deployment_set.v1
```

Required semantic contents:

```text
business_date
owner = PORTFOLIO_CONSTRUCTION
budget_envelope_owner = PORTFOLIO_POLICY
allocation_cardinality = MULTI_ALLOCATION
authorized_security_allocations[]
authorized_cash_allocation
candidate_local_allocation_evidence[]
bootstrap_cash_state
lot_reconsideration_policy
residual_cash_policy
future_information_used = false
historical_outcome_used = false
```

`authorized_security_allocations[]` may include multiple `NEW_BUY`, `ADD`, and
eligible re-entry rows. `authorized_cash_allocation` may coexist with those
security allocations. Cash may also receive all authorized marginal capital
when no deployment is justified.

Phase31-G81 opportunity-aware security/Cash partition:

`market_candidate_cash_interaction.interaction_result = CASH_PREFERRED` is
binding interaction evidence, but it is not by itself the final allocation
action after Phase31-G86. Portfolio Construction must run a PC-owned
participation-vs-deferral resolution before final publication:

```text
CASH_PREFERRED
-> PC participation-vs-deferral resolution
-> CASH_PREFERRED_PARTICIPATION_VALID or CASH_PREFERRED_DEFER
```

Rows resolved to `CASH_PREFERRED_DEFER` must not be published as positive
security allocations. Their requested security increment remains visible as
`cash_preferred_security_deferrals[]` with zero authorized security weight, and
the deferred budget remains available to `authorized_cash_allocation` /
explicit Cash. Rows resolved to `CASH_PREFERRED_PARTICIPATION_VALID` may
preserve reduced security allocation with explicit reason lineage and Cash
coexistence. This preserves optional Cash as an economic competitor instead of
treating Cash as a residual after weak security rows have already consumed the
budget.

This does not create a blanket `COMPARABLE_MARGINAL` exclusion. Under
deployment contexts where the canonical interaction is `DEPLOY_ELIGIBLE` or
`SELECTIVE_COMPETITION`, marginal/high/strong security rows may still receive
positive allocation. The partition is driven only by the canonical
decision-time interaction result.

Phase31-G90 refines the aggregate resolver contract: same-quality-class
frontier is a priority signal, not an exclusive admission gate. Portfolio
Construction must not resolve `NOT_ON_FRONTIER` to weak-tail deferral by
itself. Multiple participation-valid `CASH_PREFERRED` rows may coexist when
same-date PIT row evidence and aggregate capital competition support reduced
participation. Aggregate control must still keep optional Cash as a first-class
destination and may defer weaker or contextually dominated rows without adding
fixed rank, confidence, score, exposure, position-count, or aggregate-weight
thresholds.

Phase31-G97 residual reconsideration authoritative binding:

`REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION` is non-terminal residual
capital evidence. It must re-enter PC-owned canonical capital competition, but
reconsideration is candidate re-entry only and is not positive security
authorization. Reconsidered rows remain subject to the existing G90
participation-vs-deferral resolver, stronger-security competition, ADD
competition, optional Cash, capital budget, lot feasibility,
concentration/caps, and Safety terminal boundaries.

Portfolio Construction owns this reconsideration binding. Position Sizing
continues to own discrete quantity and must not reinterpret rank, score,
target notional, residual Cash, or reconsideration lineage as a new capital
priority decision. Runtime Planning remains a mapper and must not redecide
capital priority.

Phase31-G99 makes the G97 -> G61 lot-context boundary explicit. A G97
authoritative residual-reconsideration row that enters
`canonical_multi_allocation_deployment_set.security_allocations[]` must carry
the same canonical lot-sizing context used by ordinary canonical security
allocation rows: decision-time reference price, trading/lot unit,
portfolio-value basis, current position basis, and cap/concentration context
where available from existing authorities. Portfolio Construction may only
propagate existing authoritative context; it must not synthesize lot data,
invent quantity, or hardcode a lot assumption when canonical context is
available. If that context remains genuinely missing, G61 remains fail-closed.

```text
REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION_TERMINAL = NO
RESIDUAL_RECONSIDERATION_OWNER = PORTFOLIO_CONSTRUCTION
RESIDUAL_RECONSIDERATION_IS_AUTHORIZATION = NO
RESIDUAL_RECONSIDERATION_G90_BYPASS = NO
RESIDUAL_RECONSIDERATION_LOT_CONTEXT_PROPAGATION_OWNER = PORTFOLIO_CONSTRUCTION
RESIDUAL_RECONSIDERATION_SYNTHETIC_LOT_CONTEXT = NO
POSITION_SIZING_RECONSIDERATION_AUTHORITY = NO
RUNTIME_RECONSIDERATION_AUTHORITY = NO
```

Phase31-G83 bootstrap-aware Cash preference partition:

`CASH_PREFERRED` must be interpreted together with the canonical Cash state.
In `RESIDUAL_OPTIONALITY_CASH` / already-deployed contexts, G81/G86 weak-tail
protection remains binding: a Cash-preferred weak-tail increment receives zero
authorized security weight and its requested increment returns to optional
Cash. Non-bootstrap `CASH_PREFERRED` rows are not automatically weak-tail;
they require PC-owned participation-vs-deferral resolution using existing
row-level, opportunity-set, aggregate, Cash, and budget evidence.

In `EMPTY_OR_NEAR_EMPTY_PORTFOLIO_BOOTSTRAP`, Cash preference is not
automatically a zero-security decision when the authoritative budget envelope
also carries `EXPLORATION_PARTICIPATION_RISK_PRESERVED`,
`PROFIT_ENGINE_PRESERVATION_CONTEXT`, complete PIT evidence, and selected
valid opportunities. In that bootstrap context, Portfolio Construction may
materialize the existing reduced accepted security increment while preserving
Cash as the preferred destination for unallocated budget. This creates no
fixed BUY count, fixed exposure target, rank cutoff, confidence cutoff, share
price cutoff, new score, or Historical-return-tuned parameter.

```text
BOOTSTRAP_CASH_PREFERRED_CAN_PRESERVE_REDUCED_PARTICIPATION = YES
CASH_PREFERRED_INTERACTION_ACTION_SEPARATED = YES
PC_PARTICIPATION_DEFERRAL_AUTHORITY = YES
RESIDUAL_CASH_PREFERRED_WEAK_TAIL_SECURITY_WEIGHT = 0 after CASH_PREFERRED_DEFER
CAPITAL_BUDGET_REMAINS_MAXIMUM = YES
FORCED_BOOTSTRAP_BUY = NO
FIXED_BOOTSTRAP_EXPOSURE = NO
```

Lot infeasibility is row-scoped before it is day-scoped. If one authorized
allocation cannot be materialized into a valid lot, residual capital may be
reconsidered by Portfolio Construction across remaining valid allocations and
Cash. Lot failure must not automatically collapse the entire day's allocation
unless the residual/reconsideration contract proves no valid executable
allocation remains.

```text
GENERAL_CAPITAL_WINNER_CARDINALITY = MULTI_ALLOCATION
CAPITAL_ALLOCATION_PROBLEM_TYPE = HYBRID_MULTI_SECURITY_CAPITAL_BUDGET_ALLOCATION
CAPITAL_BUDGET_ENVELOPE_OWNER = PORTFOLIO_POLICY
MULTI_ASSET_CAPITAL_ALLOCATION_OWNER = PORTFOLIO_CONSTRUCTION
POSITION_SIZING_REMAINS_QUANTITY_OWNER = YES
POSITION_SIZING_SELECTS_ECONOMIC_WINNERS = NO
CANONICAL_MULTI_ALLOCATION_SEQUENCE_DEFINED = YES
MULTI_ALLOCATION_LOT_RECONSIDERATION_DEFINED = YES
CASH_PARTIAL_ALLOCATION_SUPPORTED = YES
CASH_WINNER_TAKES_ALL_REQUIRED = NO
SINGLE_DEPLOYMENT_SET_MIGRATION_CLASS = MIGRATE
G50_EXECUTABLE_BINDING_PRINCIPLE_PRESERVED = YES
LINEAGE_BINDING_DISTINCTION_PRESERVED = YES
DOWNSTREAM_CAPITAL_REDECISION_ALLOWED = NO
```

## 5.1 Marginal Capital Value Authority

Phase31-B10 promotes Alternative C into the Production-common Strategy contract:

```text
MARGINAL_CAPITAL_VALUE_AUTHORITY
```

Owner:

```text
Portfolio Construction
```

Scope:

```text
already-eligible BUY_NEW
already-positive-increment BUY_ADD
```

This authority defines canonical marginal-capital priority across BUY_NEW and
BUY_ADD incremental capital competitors.  It is an ordering authority only.  It
does not change PM ADD semantics, Expected Edge thresholds, Incremental
Investment Value thresholds, Opportunity Cost thresholds, Market Context logic,
normal Strategy cap, Safety hard cap, winner headroom, SELL logic, Submit, or
Execution.

Allowed PIT evidence is limited to existing Production-visible Strategy fields,
including Expected Edge, same-campaign trajectory, Incremental Investment Value,
Opportunity Cost, opportunity rank, ADD-worthiness / entry admission evidence,
Market Context, current campaign/position state, current/target weight,
concentration/headroom, accepted increment, and lot feasibility.

Forbidden inputs:

```text
future price
future return
future PnL
fill outcome
Historical outcome
later market movement
post-hoc regime or campaign labels
```

Semantic classes:

```text
BLOCKED_OR_NOT_ELIGIBLE
ELIGIBLE_WEAK
ELIGIBLE_COMPARABLE
ELIGIBLE_STRONG
REVIEW_REQUIRED
COMPARISON_INSUFFICIENT
```

Rules:

- BUY_ADD label alone must not increase priority.
- BUY_NEW label alone must not increase priority.
- Strong NEW may outrank weak ADD.
- Strong ADD may outrank weaker or comparable NEW when PIT lifecycle evidence supports it.
- If comparison evidence remains insufficient, Portfolio Construction preserves the existing deterministic stable order and emits explicit insufficiency evidence instead of inventing a score.
- Equal priority candidates preserve deterministic stable order.

Evidence must expose:

```text
canonical_marginal_capital_priority_index
marginal_capital_value_class
marginal_capital_value_authority
comparison_reason_codes
source_evidence
future_information_used=false
legacy_priority_fallback_active=false
```

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

## 16. Phase30 Final PC / PS Quantity Authority Amendment

Phase30 closed the PC / PS discrete executable quantity contract as a
Production-common authority boundary.

Canonical executable quantity lineage:

```text
Portfolio Construction discrete executable quantity
-> Position Sizing consumption
-> Runtime Planning quantity delta
-> Pending quantity contract / item quantity
-> Submit equality validation
-> submitted order / fill
```

Portfolio Construction owns final Strategy allocation and discrete executable
quantity after lot feasibility, remaining-budget comparison, Strategy soft-cap
handling, Safety hard-cap preservation, and residual capital priority have been
resolved. Position Sizing consumes that canonical quantity. Runtime Planning
maps the quantity delta. Pending carries the quantity. Submit validates
consistency and execution safety. Execution and Ledger record fills and cash
effects.

Downstream components must not resize or re-decide Strategy allocation when PC
has emitted a valid canonical discrete executable quantity authority and PS has
consumed it.

`selected_position_amount` is not final discrete executable quantity authority.
It may remain a diagnostic fail-closed fallback only when canonical discrete
quantity authority is absent, invalid, stale, malformed, or inconsistent. It
must not overrule a valid PC-authorized and PS-consumed discrete quantity.

Strategy soft-cap and Safety hard-cap have different meanings:

- Strategy soft cap is a Portfolio Construction allocation constraint.
- Safety hard cap is a fail-closed execution and portfolio safety boundary.
- A discrete-lot Strategy soft-cap overshoot may be valid only when PC
  explicitly authorizes it and Safety hard cap preservation is proven.
- Missing, malformed, or unsafe overshoot authority remains fail-closed.

Final-PC remaining-budget comparison must use the already resolved canonical
discrete executable lot requirement when that authority is present and coherent.
It must not compare against the earlier draft continuous target in a way that
rejects an otherwise budget-feasible canonical executable lot.

This amendment does not create forced investment, a fixed exposure target, a
new BUY filter, a new ADD filter, or a Historical-only Strategy path. Cash may
remain undeployed when no eligible, lot-feasible, Safety-valid, authority-clean
opportunity exists.

## 17. Phase31-G102 Residual Reconsideration Item-Scoped Quantity Authority

Phase31-G102 extends the Phase30 discrete executable quantity boundary to
G97/G99 residual reconsideration rows.

When a G97/G99 positive reconsideration row has passed canonical G61 lot-aware
compatibility as `LOT_EXECUTABLE_COMPATIBLE`, Portfolio Construction must
materialize the same item-scoped discrete executable quantity authority that
ordinary BUY_NEW / BUY_ADD rows carry:

```text
phase29_l19_lot_resolution.pc_positive_executable_quantity_authority
  .authority_type = PORTFOLIO_CONSTRUCTION_DISCRETE_EXECUTABLE_QUANTITY_AUTHORITY
  .status = PASS
  .final_allocated_quantity = canonical G61 executable quantity
  .ps_must_consume_canonical_quantity = true
  .future_information_used = false
```

Position Sizing must consume that authority without re-deciding capital
priority, Runtime Planning must preserve the quantity lineage, Pending must
embed it in `quantity_contract.position_sizing_authority`, and Submit must
validate it through the existing item-scoped
`canonical_discrete_quantity_submit_authority`.

This does not weaken Submit. Submit must not infer discrete quantity authority
from PS quantity, Runtime planned quantity, G97 provenance, or aggregate PC
allocation alone. Missing, malformed, date-mismatched, quantity-mismatched,
lot-infeasible, Cash-deferred, or Safety-terminal reconsideration evidence
remains fail-closed and must not produce a PASS authority.

Phase31-G104 clarifies the Submit consumer contract for the G102 item-scoped
authority.  Submit may treat:

```text
lot_overshoot_reason =
G102_G97_G99_ITEM_SCOPED_PC_DISCRETE_QUANTITY_AUTHORITY
```

as a resolved discrete-quantity reason only when the complete item-scoped
authority invariants are valid: `pc_positive_executable_quantity_authority`
has `status=PASS`, the expected PC authority type, `future_information_used=false`,
`ps_must_consume_canonical_quantity=true`, a positive `final_allocated_quantity`,
and the Pending item quantity, PS final quantity, `final_allocated_quantity`,
`executable_quantity_delta`, and `preflight_executable_quantity_delta` all match.
The semantic type must be `BUY_NEW`, `REENTRY`, or `BUY_ADD`; Strategy cap and
Safety hard cap preservation must both be proven true; one-lot feasibility must
be `PASS`; and the embedded G61 lot-aware compatibility context must be
canonical, PC-owned, `LOT_EXECUTABLE_COMPATIBLE`, non-synthetic, and free of
future or Historical outcome inputs.  The reason string alone is never
sufficient.  Any missing or contradictory invariant remains `REVIEW_REQUIRED`.

G102 does not change Market Quality, Risk Pacing, Candidate ranking, ADD
semantics, Safety, PS quantity ownership, Runtime priority, thresholds, scores,
or exposure targets.

## 18. Phase31-G115 ADD Marginal Capital Competition Authority

Phase31-G115 promotes the G113 ADD marginal competition evidence into a staged
Portfolio Construction authority:

```text
canonical_add_marginal_capital_competition_authority.v1
```

Portfolio Construction owns ADD marginal frontier comparison, Cash/residual
participation semantics, and staged ADD increment authorization. Position
Management remains the ADD intent and ADD eligibility owner. Position Sizing
remains the discrete quantity owner. Runtime Planning, Pending, Submit, and
Execution consume the PS-bound quantity and must not re-decide ADD capital
priority.

The G115 binding is staged. A PM `ADD` plus canonical positive ADD investment
evidence may authorize one executable ADD increment at a time. A requested ADD
block must not be treated as a single all-or-nothing capital winner. Each ADD
increment carries its own classification, lot context, pre/post quantity and
weight, budget before/after, Cash/residual semantics, and future/Historical
input flags. `ADD_MARGINAL_PREFERRED` authorizes one executable increment and
then requires recomputation before another increment may be authorized.
`COMPARABLE_MARGINAL` may receive residual/shoulder participation through the
same staged one-increment boundary, but never a full requested block solely
because PM requested ADD. `INSUFFICIENT_EVIDENCE`, `LOT_INFEASIBLE`,
`SAFETY_TERMINAL`, and `CASH_MARGINAL_PREFERRED` remain fail-closed for the ADD
increment while the existing HOLD position is preserved.

NEW_BUY remains in the marginal frontier as a normalized competitor for
comparison, but G115 does not mutate Candidate ranking, NEW_BUY eligibility,
Market Quality, Risk Pacing, Safety, thresholds, weights, or Runtime priority.
Submit remains a feasibility and equality validator only.

## 19. Phase31-G119 PC Final Discrete Authority / PS Consistency

After Portfolio Construction completes final lot-aware allocation, its positive
discrete executable quantity authority is the final Strategy capital allocation
authority consumed by Position Sizing.

When a final PC row carries all of the following:

```text
phase29_l19_lot_resolution.final_allocated_quantity > 0
phase29_l19_lot_resolution.pc_positive_executable_quantity_authority.status = PASS
phase29_l19_lot_resolution.pc_positive_executable_quantity_authority.ps_must_consume_canonical_quantity = true
```

Position Sizing must consume that final PC quantity authority and must not
revive an earlier or stale `cash_winner=true` /
`DEFEATED_BY_CANONICAL_CAPITAL_COMPETITION` deployment-set state to zero the
row. Earlier Market Candidate Cash / deployment-set evidence remains input and
diagnostic context once PC final allocation has selected the security.

The final PC selected row must remain internally coherent:

- positive final target weight and final allocated quantity
- `pc_positive_executable_quantity_authority.status = PASS`
- `ps_must_consume_canonical_quantity = true`
- deployment-set sizing eligibility selected by final PC authority, not
  defeated by capital competition
- no contradictory Cash-winner binding for the selected row

This precedence does not override Safety, valid hard-cap failure, malformed or
missing authority, genuine lot infeasibility, Submit feasibility, or execution
availability. Rows that finish PC final allocation with zero quantity, invalid
authority, Cash-deferred state, or legitimate infeasibility remain zero and
fail-closed.

G119 does not change the G115 staged ADD marginal authority. ADD increments
still require the staged marginal contract, one-increment authorization,
recompute semantics, and existing fail-closed handling.

## 20. Phase31-G136 High-Resolution Capital Value SoT Reference

The permanent SoT for future high-resolution marginal capital value and
portfolio-wide rotation is:

```text
docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md
```

This is an architecture contract only. It does not implement
`canonical_high_resolution_marginal_capital_value.v1` or
`canonical_portfolio_rotation_opportunity_cost.v1`.

Current Portfolio Construction already owns NEW_BUY / BUY_ADD / Cash capital
competition. G136 does not redefine that as new behavior. It records the future
capability extension that Portfolio Construction-owned Capital Value Authority
may later evaluate the next executable increment with higher semantic
resolution, while preserving Candidate AI, PM, Market Quality, Risk Pacing,
Safety, Position Sizing, and Runtime ownership boundaries.

Existing HOLD capital is not merged into the current NEW_BUY / BUY_ADD / Cash
execution frontier by this reference. Portfolio-wide rotation must remain a
future staged capability that depends on high-resolution marginal capital value
and PM-owned REDUCE / EXIT action authority.

## 21. Phase32-AR Current ADD Graduation Baseline

Phase32-AR records that the current accepted ADD / graduation execution baseline
is:

```text
persistent eligibility + PC/PS/G129 per-order authority
```

Portfolio Construction may observe persistent ADD / incumbent strength
eligibility, but that observation is not capital entitlement and is not a
Production Graduation Episode state. Every actual BUY_ADD still requires:

1. Portfolio Construction capital allocation authority;
2. Position Sizing discrete executable quantity authority;
3. Runtime / Submit consumption of the G129 order-increment authority.

Persistent strength must not bypass Cash, NEW competition, Risk Pacing, Buy
Quality, no-loss averaging, concentration / headroom, lot feasibility, prior
ADD safeguards, Safety, broker, or corporate-action gates. Position Sizing must
continue to emit discrete quantity from current PC authority only, and Runtime
must not re-decide priority or quantity.

Known current limitation:

```text
REPLACE_HEAVY_HYBRID / WEAK_WINNER_GRADUATION / STARTER_SATURATION
NO_CORRECTNESS_DEFECT_CONFIRMED
```

This is a performance architecture limitation, not a correctness defect. It
does not authorize changing BUY_NEW sizing, ADD/HOLD/REDUCE/EXIT, Cash, Risk
Pacing, thresholds, weights, caps, PC, PS, Runtime, or accepted artifacts.
