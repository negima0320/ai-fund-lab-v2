# Position Management Decision-Time Authority and Trace Contract

Status: Phase20-S accepted observability contract

This contract closes the Phase20-R Position Management observability gap without changing PM thresholds, score formulas, decision order, quantity ratios, Runtime actions, submitted orders, AI training, or calibration.

## Contract Version

```text
runtime_v2_pm_decision_trace_contract_v1
```

Runtime PM emits a decision trace artifact:

```text
.runtime/runtime_state/position_management/<business_date>/position_management_decision_trace.json
```

`position_management_decisions.json` keeps its legacy fields and adds trace references / embedded trace fields for observability. Existing consumers must continue to read `decision`, `reason`, `runtime_action`, `runtime_sell_quantity`, and `runtime_quantity_authority` without behavior changes.

## Decision-Time Price Authority

PM decision-time position state authority is Runtime Current, materialized by the PM producer into:

```text
.runtime/runtime_state/position_management/<business_date>/current_holdings_snapshot.csv
```

`position_feature_input.parquet` / `.csv` may contain operational position-state copies such as `current_price`, `current_return`, or `quantity`, but those copies are non-canonical for PM position-state scoring. They are retained only as observability copies and must be compared against the canonical holding snapshot when present.

| Value | Canonical Source Artifact | Source Field | As-of / Market Date | Formula | Freshness | Missing Behavior |
|---|---|---|---|---|---|---|
| `average_price` | Runtime Current -> `current_holdings_snapshot.csv` | `entry_price` from `current.positions[].average_price` | `pm_current_as_of`; valuation date from `pm_valuation_as_of` | copied as numeric | Current must be fresh for business date or valid carryover authority | REVIEW_REQUIRED |
| `current_price` | Runtime Current -> `current_holdings_snapshot.csv` | `current_price`, fallback `price`; if absent and `market_value/quantity` available, derived with evidence | `pm_valuation_as_of` / `pm_current_as_of` | copied or `market_value / quantity` | Current valuation must be READY / VALID_CARRYOVER or historical empty authority | REVIEW_REQUIRED unless derivation is explicit |
| `current_return` | `current_holdings_snapshot.csv` | `current_return` | same as `current_price` | `(current_price / average_price) - 1` | same as `current_price` | REVIEW_REQUIRED if inputs missing |
| `peak_return` | Runtime Current; feature context fallback only when Current lacks value and contract records derivation | `peak_return` | position-state date | copied | Current or explicit feature-context derivation must be available | REVIEW_REQUIRED |
| `drawdown_from_peak` | PM inference/trace derived from canonical position state | derived | decision business date | `current_return - peak_return` | derived only after canonical values pass | REVIEW_REQUIRED if canonical inputs missing |
| `market_value` | Runtime Current; trace derives if needed | `market_value` or derived | valuation date | `quantity * current_price` | same as `current_price` | REVIEW_REQUIRED if neither source nor derivation inputs exist |
| `holding_days` | Runtime Current; feature context fallback only when Current lacks value and contract records derivation | `holding_days` | position-state date | copied integer | Current or explicit feature-context derivation must be available | REVIEW_REQUIRED |

## Artifact Relationship

| Artifact | Role | Canonical / Derived Semantics |
|---|---|---|
| `current_holdings_snapshot.csv` | PM position-state input created from Runtime Current | Canonical for `quantity`, `average_price`, `current_price`, `current_return`, `peak_return`, `market_value`, `holding_days` |
| `position_feature_input.parquet` | PM technical feature input from Feature Refresh / Market Feature pipeline | Canonical for technical features only; position-state fields inside it are non-canonical observability copies |
| `position_management_opportunity_context.csv` | PM-readable Opportunity/Risk context | Canonical PM context for `expected_edge_score`, `buy_rank`, `downside_risk_score`, `risk_guard_status` after Runtime contract validation |
| `position_management_inference.parquet` | PM policy score/action output | Canonical for `hold_score`, `exit_score`, `reduce_score`, `add_score`, and selected action before Runtime payload normalization |
| `position_management_decision_trace.json` | Decision-time trace artifact | Canonical observability record for authority, position state, technical features, scores, triggers, dominant cause, and confidence semantics |
| `position_management_decisions.json` | Runtime PM decision artifact consumed by Sell Planning | Canonical Runtime decision handoff; includes legacy fields and embedded trace metadata |
| Run-scoped `pm_decisions.json` | Runtime Test observability snapshot | Derived copy from Runtime PM decision artifact; no post-hoc outcome fields |

## Decision Trace Required Fields

Each trace row must include:

Input authority:

- `symbol`
- `business_date`
- `feature_business_date`
- `price_market_date`
- `holding_snapshot_ref`
- `feature_snapshot_ref`
- `opportunity_context_ref`
- `source_opportunity_ref`
- `current_source_ref`
- `generation_id`

Position state:

- `quantity`
- `average_price`
- `current_price`
- `current_return`
- `peak_return`
- `drawdown_from_peak`
- `market_value`
- `unrealized_pnl`
- `holding_days`

Opportunity / Risk:

- `expected_edge_score`
- `buy_rank`
- `downside_risk_score`
- `risk_guard_status`

Technical features:

- `price_momentum_return_5d`
- `price_momentum_return_20d`
- `trend_close_over_ma_20d`
- `trend_ma_5_20_ratio`
- `volume_momentum_ratio_5d`
- `volatility_return_std_20d`

Score components:

- `trend_score`
- `opportunity_score`
- `profit_score`
- `risk_penalty`
- `hold_score`
- `exit_score`
- `reduce_score`
- `add_score`

Trigger booleans:

- EXIT: `hard_stop_current_return`, `profit_retention_break`, `trend_and_opportunity_broken`, `risk_guard_status_bad`, `exit_score_high`, `weak_hold_score`
- REDUCE: `high_downside_risk`, `peak_drawdown_warning`, `reduce_score_threshold`, `weak_hold_score_threshold`, `trend_or_opportunity_alive`
- ADD: `strong_trend_continuation`, `opportunity_rank_still_high`, `no_loss_averaging`, `add_downside_risk_contained`
- HOLD: `trend_continuation`, `positive_expected_edge`, `downside_risk_contained`, `fallback_hold`

Decision result:

- `decision_type`
- `dominant_cause`
- `secondary_causes`
- `decision_reason_codes`
- `legacy_reason`
- `selected_action_score`
- `confidence_semantics`

## Reason Codes

The legacy broad reason `risk_increased_but_trend_not_broken` may remain in `reason` for backward compatibility, but trace must split the actual dominant cause into one of:

- `REDUCE_BY_WEAK_HOLD_SCORE`
- `REDUCE_BY_REDUCE_SCORE_THRESHOLD`
- `REDUCE_BY_HIGH_DOWNSIDE_RISK`
- `REDUCE_BY_PEAK_DRAWDOWN_WARNING`
- `REDUCE_BY_RISK_INCREASED_BUT_TREND_NOT_BROKEN`

HOLD must be distinguishable as:

- `HOLD_BY_STRONG_CONTINUATION`
- `HOLD_BY_PARTIAL_CONTINUATION`
- `HOLD_BY_FALLBACK`

EXIT must preserve implementation order and distinguish:

- `EXIT_BY_HARD_STOP`
- `EXIT_BY_PEAK_DRAWDOWN`
- `EXIT_BY_TREND_AND_EDGE_BREAK`
- `EXIT_BY_RISK_GUARD`
- `EXIT_BY_EXIT_SCORE_HIGH`
- `EXIT_BY_WEAK_HOLD_SCORE`

## Phase27-D5 Expected Edge Reason Code Review

Phase27-D5 defines reason codes as explanations of PM Expected Edge reasoning. Reason codes are not independent Action Authority and must not be consumed as standalone BUY/HOLD/SELL decisions by Runtime Planning, Submit, Safety, monitoring, or training shortcuts.

Design classification:

| Reason code | Classification | Contract meaning |
|---|---|---|
| `trend_continuation` | KEEP | Continuation evidence supporting Expected Edge adequacy. |
| `positive_expected_edge` | REVIEW | Compatibility code for positive edge; future contract should prefer explicit Expected Edge adequacy wording. |
| `downside_risk_contained` | KEEP | Risk-contained evidence supporting HOLD/ADD. |
| `risk_increased_but_trend_not_broken` | RENAME | Broad fallback; future trace should split the actual risk/weakening trigger. |
| `peak_drawdown_warning` | KEEP | Risk Review / weakening evidence for REDUCE or EXIT review. |
| `trend_and_opportunity_broken` | KEEP | Expected Edge deterioration and continuation break evidence for EXIT. |
| `profit_retention_break` | RENAME | Peak-drawdown/profit-retention risk evidence; not simple profit-taking authority. |
| `hard_stop_current_return` | KEEP | Loss-containment / severe risk evidence for EXIT. |

Profit-related reason codes must be interpreted as Risk Review evidence. Profit alone must not create `EXIT` or `REDUCE`.

## Phase27-D6-B Reason Semantics Compatibility Repair

Phase27-D6-B implements the D5 reason semantics repair as an additive compatibility layer. It does not change PM action classification, action priority, score formula, thresholds, quantity intent, Runtime Planning, Pending, Submit, Safety, Execution, or Ledger.

Runtime PM decision artifacts and decision trace artifacts keep legacy reason fields readable:

```text
reason
decision_reason_codes
legacy_reason
legacy_decision_reason_codes
```

They also add canonical semantic metadata:

```text
reason_semantics_contract_version = phase27_d6b_pm_reason_semantics_v1
canonical_decision_reason_codes
reason_aliases
expected_edge_semantics
expected_edge_status
expected_edge_contract_status
```

Reason alias contract:

| Legacy reason | Canonical reason | Compatibility | Action effect |
|---|---|---|---|
| `profit_retention_break` | `peak_drawdown_profit_retention_risk` | `LEGACY_ALIAS` | `NONE` |
| `risk_increased_but_trend_not_broken` | `expected_edge_risk_deterioration` or cause-specific risk code when already evidenced | `LEGACY_ALIAS` | `NONE` |
| `positive_expected_edge` | `expected_edge_adequate` | `LEGACY_ALIAS` | `NONE` |
| `trend_and_opportunity_broken` | `trend_and_expected_edge_broken` | `LEGACY_ALIAS` | `NONE` |
| `trend_continuation` | `trend_continuation` | `CANONICAL` | `NONE` |
| `downside_risk_contained` | `downside_risk_contained` | `CANONICAL` | `NONE` |
| `peak_drawdown_warning` | `peak_drawdown_warning` | `CANONICAL` | `NONE` |
| `hard_stop_current_return` | `hard_stop_current_return` | `CANONICAL` | `NONE` |

Unknown legacy reasons must be preserved as `UNKNOWN:<legacy_reason>` in canonical metadata and must not silently map to another cause.

`profit_retention_break` must not be interpreted as simple profit-taking. It is a peak-drawdown / profit-retention risk-review signal. `risk_increased_but_trend_not_broken` remains readable as a legacy alias, but canonical metadata must avoid inventing causes that are not already present in trigger evidence.

## Phase27-D6-C HOLD / REDUCE / EXIT Boundary Trace Semantics

Phase27-D6-C defines how trace semantics should explain the HOLD / REDUCE / EXIT boundary. This is observability and design semantics only; it must not change action classification, priority, score formula, thresholds, quantity intent, Runtime Planning, Pending, Submit, Safety, Execution, or Ledger.

Trace relationship:

| Canonical reason / status | Boundary interpretation |
|---|---|
| `expected_edge_adequate` / `ADEQUATE` | HOLD evidence. Expected Edge remains sufficient for active campaign continuation. |
| `expected_edge_risk_deterioration` / `DETERIORATING` | REDUCE candidate evidence when campaign optionality remains. |
| `peak_drawdown_profit_retention_risk` | Risk Review evidence. It is not profit-taking authority. |
| `trend_and_expected_edge_broken` | EXIT evidence when continuation and Expected Edge are broken. |
| `hard_stop_current_return` / `RISK_OVERRIDE` | Severe risk / loss-containment evidence that may justify full close. |

Required trace non-overclaim:

- Do not describe `profit_retention_break` or `peak_drawdown_profit_retention_risk` as simple profit-taking.
- Do not describe Trend alone as EXIT authority.
- Do not describe REDUCE as deletion, full invalidation, or mandatory EXIT.
- Do not describe Safety as Expected Edge optimizer.

## Phase27-D6-D HOLD / EXIT Boundary Implementation Trace Semantics

Phase27-D6-D allows trace rows to show a HOLD decision with both:

```text
expected_edge_adequate
peak_drawdown_profit_retention_risk
```

This means Expected Edge remains adequate after Risk Review. It must not be interpreted as profit-taking, EXIT suppression, or Safety override.

Trace consumers must preserve:

```text
decision = HOLD
runtime_action = NO_SELL_ORDER
runtime_sell_quantity = 0
```

for this case. The canonical risk reason remains observability evidence and does not create quantity, pending, submit, or execution authority.

Phase27-D6-E adoption review confirms that D6-D trace consumers must preserve this semantics with adoption status `ADOPTED_WITH_LIMITATIONS`. Same-context `EXIT -> HOLD` rows are valid only when decision-time position state is comparable and severe full-close evidence is absent. Cross-run path-dependent differences must not be reinterpreted as direct D6-D reason-code authority.

## Phase32-BQ Lot-Blocked REDUCE Reconsidered FULL EXIT Trace Semantics

Phase32-BQ defines a narrow production materialization path for PM `REDUCE` decisions whose partial quantity is unrepresentable only because of discrete-lot granularity. This path does not rewrite the PM decision trace as a native `EXIT`.

Trace and downstream observability must distinguish:

```text
native PM EXIT
```

from:

```text
PM REDUCE
-> REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT
-> PM_REDUCE_LOT_BLOCKED_RECONSIDERED_FULL_EXIT
-> ordinary downstream SELL_EXIT
```

Required BQ lineage fields:

- `source_pm_action = REDUCE`;
- `source_pm_decision_id`;
- original PM reason and reduce intensity;
- original REDUCE quantity contract;
- `reconsidered_action = FULL_EXIT`;
- `reconsideration_reason = PM_REDUCE_LOT_BLOCKED_RECONSIDERED_FULL_EXIT`;
- BO PIT evidence provenance and artifact hash when materialized;
- campaign / position campaign id;
- `runtime_invented_exit = false`.

This is a Strategy materialization authority, not a Runtime, Submit, Execution, Ledger, or broker authority. Reason codes remain explanatory unless this explicit BQ authority is present and passes. Profit cushion is contextual profit-protection evidence; it is not standalone HOLD or EXIT authority and does not introduce new thresholds, weights, models, features, or score formulas.

## Confidence Semantics

The legacy `confidence` field is not a calibrated probability.

Runtime PM must expose:

```text
confidence_semantics = selected_action_score_not_calibrated_probability
action_score = selected action score
selected_action_score = selected action score
```

`confidence` remains as a compatibility alias for the selected action score. Consumers must not interpret it as win probability, success probability, or calibrated uncertainty.

## Runtime Behavior Compatibility

The trace contract is observability-only.

It must not change:

- EXIT threshold
- REDUCE threshold
- HOLD threshold
- score formula
- decision order
- REDUCE intensity thresholds
- Sell Planning quantity authority
- Runtime action
- submitted orders

Regression tests must verify that adding trace fields leaves `decision`, `runtime_action`, `runtime_sell_quantity`, and Sell Planning consumer output unchanged for the same input.

## Threshold Review Gate

This contract makes future threshold review observable. It does not authorize threshold change.

Threshold changes remain prohibited until a later Experiment phase explicitly defines:

- baseline run
- experiment run
- comparison metrics
- acceptance criteria
- rollback criteria
