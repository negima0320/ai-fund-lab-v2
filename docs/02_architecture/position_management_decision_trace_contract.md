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
