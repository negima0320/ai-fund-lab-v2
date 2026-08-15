# Phase29-L21T-BD — 78780 Post-AV Actual BUY Path Causality Audit

## Task

Phase29-L21T-BD

Mode: READ-ONLY audit.

Phase30 was not entered. Strategy, Runtime, Config, Model, and Threshold were not changed. No fresh-run, resume, replay, or recovery was executed. The target runtime run was not mutated.

## Target

- Run: `runtime-test-historical-extended-smoke-20260814T124736137915Z`
- Business date: `2022-08-24`
- Symbol: `78780`

## Primary Judgment

`ACTUAL_FEATURE_VALUES_DIFFER_FROM_AV_ANCHOR`

More precisely: the actual artifact values match the previously cited late-entry evidence, but they do not satisfy the AV implementation's current `FADING_PRIOR_WINNER` predicate. The actual path was:

`MIXED_OR_UNRESOLVED -> PASS_WITH_REDUCTION -> BUY_ELIGIBLE -> FULL_ALLOCATION_ELIGIBLE -> BUY_NEW 100 shares`.

This is not a downstream authority bypass. BUY Quality did not emit `BUY_WAIT` for `78780` on `2022-08-24`.

## Actual Feature Evidence

Authority rows were traced from Candidate, Opportunity, and BUY Quality artifacts. Required multi-horizon features were present and propagated to BUY Quality.

| Field | Value |
| --- | ---: |
| `price_momentum_return_1d` | `-0.157528` |
| `price_momentum_return_3d` | `0.044229` |
| `price_momentum_return_5d` | `0.429838` |
| `price_momentum_return_10d` | `0.812734` |
| `price_momentum_return_20d` | `2.280022` |
| `price_momentum_return_60d` | `2.587843` |
| `volatility_return_std_20d` | `0.127143` |
| `recent_move_volatility_z_1d` | `-1.238980` |
| `recent_move_volatility_z_3d` | `0.200840` |
| `momentum_5d_vs_20d_delta` | `-1.850184` |
| `momentum_1d_vs_5d_delta` | `-0.587366` |

The values are close to the previously cited evidence:

- 5BD: `+42.984%`
- 20BD: `+228.002%`
- 1BD: `-15.753%`

The important difference is semantic, not artifact propagation: current AV logic requires `1D < 0`, `3D < 0`, and `5D < 0` for `FADING_PRIOR_WINNER`. Actual `3D` and `5D` were positive, so the classifier selected `MIXED_OR_UNRESOLVED`.

## Authority Path

Detailed row evidence is also recorded in:

`reports/phase29_l21t_bd_78780_post_av_actual_buy_path_causality_audit/authority_path.csv`

### Candidate

- Candidate rank: `5`
- Candidate score: `0.79837418`
- Candidate reason: `high_candidate_score|price_momentum_positive|long_momentum_positive|volume_momentum_positive|liquidity_available`
- Required AV feature columns: present

### Opportunity

- Buy rank: `3`
- Opportunity score: `0.04370588`
- Reason: `opportunity_top5|positive_expected_edge|candidate_prior_available|downside_risk_not_extreme`
- Required AV feature columns: present

### Adaptive BUY Quality

- `quality_status`: `PASS`
- `quality_score`: `0.777044`
- `quality_band`: `HIGH`
- `quality_action`: `FULL_ALLOCATION_ELIGIBLE`
- `momentum_trajectory_classification`: `MIXED_OR_UNRESOLVED`
- `momentum_trajectory_status`: `PASS_WITH_REDUCTION`
- `momentum_trajectory_action`: `BUY_ELIGIBLE`
- `momentum_trajectory_reason_codes`: `["momentum_trajectory_mixed_or_unresolved"]`
- `momentum_trajectory_missing_features`: `[]`

### Portfolio Construction

- `membership_intent`: `ADD_CANDIDATE`
- Semantic type: `BUY_NEW`
- `accepted_buy_new_weight`: `0.035714`
- Final lot-aware target weight: `0.245284`
- Reason included: `buy_quality_full_allocation_eligible`

### Position Sizing

- Reference price: `2420.0`
- Quantity delta: `100`
- Semantic type: `BUY_NEW`
- L19 boundary: `DISCRETE_LOT_EXCEEDS_STRATEGY_CAP_WITHIN_SAFETY_HARD_MAX`
- One-lot notional: `242000.0`
- Safety hard cap: `0.25`
- Safety preserved: `true`

### Runtime Planning

- Planning intent: `BUY_NEW`
- Planned quantity: `100`
- Planning ID: `rp-2022-08-24-78780-buy_new-e698cec75c1619f2`
- Planning reason: `position_sizing_positive_quantity_delta_maps_to_buy_new;position_sizing_quantity_candidate_resolved`

### Submit

- Submit action: `SUBMIT`
- Pending item state: `CREATED`
- Side: `BUY`
- Order type: `MARKET`
- Quantity: `100.0`
- Source decision type: `BUY_NEW`
- Planning submit feasibility: `PASS`

### Execution / Fill

- Fill side: `BUY`
- Fill quantity: `100.0`
- Execution price: `2860.0`
- Gross notional: `286000.0`
- Position campaign ID: `pc-4dc7153e8b1bc97b-78780-0001`

## Causality

The BUY was caused by the classifier's actual runtime result, not by a downstream bypass.

Current AV implementation classifies:

- `FADING_PRIOR_WINNER` only when `long_positive` and `1D`, `3D`, and `5D` are all negative.
- `RECENT_ACCELERATION_OVERHEAT` only when long momentum is positive, `1D`, `3D`, and `5D` are all positive, and recent volatility z-score is at least `2.0`.
- `HEALTHY_CONTINUATION` only when `20D`, `1D`, `3D`, and `5D` are non-negative and not overheated.
- Otherwise, `MIXED_OR_UNRESOLVED -> PASS_WITH_REDUCTION -> BUY_ELIGIBLE`.

For `78780`:

- `1D` was negative.
- `3D` and `5D` were positive.
- Recent volatility z-scores were not overheat-level positive.

Therefore, the actual classifier selected `MIXED_OR_UNRESOLVED`, not `FADING_PRIOR_WINNER`.

## Required Classification

- A. `ACTUAL_FEATURE_VALUES_DIFFER_FROM_AV_ANCHOR`: YES, relative to the focused AV fixture/expectation that made `78780` a FADING case.
- B. `TRAJECTORY_CLASSIFICATION_DEFECT`: NO, under the current implemented predicate.
- C. `BUY_WAIT_DOWNSTREAM_AUTHORITY_BYPASS`: NO.
- D. `SEMANTIC_CLASSIFICATION_MISMATCH`: NO. The path is actual `BUY_NEW`, not ADD or REENTRY.
- E. `OTHER_CONFIRMED_CAUSE`: Semantic coverage gap is likely if the intended policy is to WAIT on sharp 1D reversal after a prior winner even when 3D/5D remain positive.

## Validation

- Read-only artifact trace consistency: PASS
- `summary.json` parse: PASS
- `git diff --check`: PASS
- Runtime mutation: NO
- Strategy change: NO
- Phase30 entered: NO

## Next Step

Recommended next task:

`Phase29-L21T-BE — Momentum Trajectory FADING Semantic Coverage Correction`

Scope should be design or implementation repair only if the intended contract is to classify sharp recent deterioration of a strong prior winner as BUY_WAIT even when only the 1D leg has reversed while 3D/5D remain positive.
