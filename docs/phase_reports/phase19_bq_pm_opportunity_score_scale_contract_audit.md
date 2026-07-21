# Phase19-BQ Opportunity to Position Management Score Scale Contract Audit

- Phase: `Phase19-BQ`
- Title: `Opportunity -> Position Management Score Scale Contract Audit`
- Judgment: `CONTRACT_MISMATCH__RUNTIME_OPPORTUNITY_INFERENCE_OMITS_GENERATION_BOUND_SCALER__PM_RECEIVES_OVERSCALED_EXPECTED_EDGE`
- JSON evidence: `reports/phase_reports/phase19_bq_pm_opportunity_score_scale_contract_audit.json`

## Scope

This audit investigates whether the value named `expected_edge_score` has the same meaning, scale, and contract across:

```text
Opportunity
-> Runtime Adapter
-> Position Management
-> Decision
```

No SELL threshold, PM threshold, Runtime behavior, model artifact, or Historical-only behavior was changed.

The requested files `docs/02_architecture/runtime_contract.md` and `docs/02_architecture/position_management_contract.md` do not exist under those exact names. Equivalent contract documents were used:

- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/ai_input_output_and_artifact_contract.md`
- `docs/02_architecture/ai_generation_artifact_contract.md`
- `docs/02_architecture/ai_artifact_registry_and_capital_allocation_contract.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `docs/03_ai_design/opportunity_ai_design.md`
- `docs/phase_reports/phase17_aj_buy_opportunity_pm_contract_integration.md`
- `docs/phase_reports/phase17_bv16_opportunity_expected_edge_semantics_and_runtime_distribution_investigation.md`
- `docs/phase_reports/phase19_ad_u3_i_feature_scaling_corrective_contract.md`
- `docs/phase_reports/phase19_bp_position_management_exit_reduce_distribution_audit.md`

## Executive Finding

The current Runtime path is not score-scale contract compliant.

Opportunity `expected_edge_score` is contractually a raw regression prediction for `label__expected_edge_label_20d`, expected to behave like a decimal return-like / risk-adjusted 20 business day edge, not a probability and not a pure ranking score.

However, the active Phase19 Accepted Opportunity model is a scaler-bound SGDRegressor. The Runtime BUY Opportunity producer still calls the legacy Phase5F `run_opportunity_inference()` path, which applies only imputation / categorical encoding and does not apply the generation-bound `StandardScaler` before `model.predict`.

As a result, Runtime artifacts contain unscaled predictions in the range:

```text
11.78522441 to 20212.96186064
```

The same existing input rows, when transformed with the generation-bound scaler, produce:

```text
0.1517975577 to 0.3124888106
```

Therefore BP's `11 to 19000` distribution is a Contract mismatch, not a valid PM expected-edge scale.

## expected_edge Definition

Opportunity design says Opportunity AI ranks Candidate AI output by expected value. It is not a probability-only model and not a simple ranker.

Phase17-BV16 previously fixed the operational semantics:

- `expected_edge_score` is the raw regression prediction for `label__expected_edge_label_20d`.
- The target is decimal return-like / risk-adjusted 20 business day edge.
- It is not a percent-point integer scale.
- It is not only a relative rank.
- Positive means positive expected edge under current BUY eligibility semantics.

The current accepted Phase19 Opportunity artifact still declares:

```text
label_column = label__expected_edge_label_20d
target_kind = regression
model_family = sklearn_sgd_regressor
scaler_method = StandardScaler
```

## Opportunity Side

Opportunity Runtime inference currently does:

```text
matrix = transform_features(inference_frame, feature_columns, model_payload["preprocessing"])
scores = model_payload["model"].predict(matrix)
expected_edge_score = score
```

This path does not apply `scaler_artifact`.

The Runtime BUY producer then copies the same value into three fields:

```text
expected_edge_score = expected_edge_score
opportunity_score = expected_edge_score
expected_return = expected_edge_score
```

Runtime artifacts also state:

```text
calibration_applied = false
prediction_metric_name = opportunity_score
prediction_semantics = runtime_opportunity_score
transformation_stage = runtime_artifact_opportunity_score
```

The 20 inspected Opportunity artifacts all had `calibration_applied=false`.

## Position Management Side

PM expects `expected_edge_score` as an Opportunity continuation signal. Its implementation uses the value in these places:

- `calculate_opportunity_continuation_score`: `normalize_range(edge, -0.10, 0.20)`, clipped to `[0, 1]`.
- `classify_position_action`: `expected_edge > 0` supports REDUCE instead of EXIT in risk-warning cases.
- `classify_position_action`: `expected_edge > 0` adds `positive_expected_edge` to HOLD reason.
- `calculate_add_score`: `normalize_range(edge, 0.0, 0.20)` contributes to ADD.

This is consistent with an expected-edge value around decimal returns. It is not consistent with values in the thousands.

## Runtime Distribution

Runtime Opportunity artifact distribution across 20 business days / 1000 rankings:

| Metric | Value |
|---|---:|
| min | 11.78522441 |
| p05 | 18.0560485435 |
| median | 675.340566745 |
| mean | 2297.7138219916 |
| p95 | 11567.674724013 |
| max | 20212.96186064 |
| positive | 1000 / 1000 |
| zero | 0 |
| negative | 0 |

PM `position_management_opportunity_context.csv` distribution across 19 PASS position days / 950 context rows:

| Metric | Value |
|---|---:|
| min | 11.78522441 |
| p05 | 18.0607242345 |
| median | 673.05958863 |
| mean | 2280.416496092 |
| p95 | 11519.263276749 |
| max | 19408.60655341 |
| positive | 950 / 950 |
| zero | 0 |
| negative | 0 |

PM held-position join distribution across 95 decisions:

| Metric | Value |
|---|---:|
| min | 4522.97249933 |
| p05 | 4953.051944809 |
| median | 7067.29309122 |
| mean | 9573.1747301058 |
| p95 | 19005.628344852 |
| max | 19408.60655341 |
| positive | 95 / 95 |
| zero | 0 |
| negative | 0 |

Every Runtime artifact row satisfied:

```text
expected_edge_score == opportunity_score == expected_return
```

No scale conversion was found between Opportunity artifact and PM context.

## Scaler Contract Evidence

The Architecture contract says scaler artifacts are required whenever a model declares a scaled preprocessing pipeline, and Runtime may use a scaler only through an Accepted Generation manifest binding the matching model, scaler, feature order, and hashes.

The Phase19 feature scaling contract defines the Runtime inference path as:

```text
Accepted Generation
-> Generation-bound Imputer
-> Generation-bound Scaler
-> Generation-bound Candidate Model
-> Generation-bound Opportunity Model
```

The active accepted generation manifest binds:

```text
generation_id = phase19_aq_accepted_generation_641e6e313543f013
opportunity_model_hash = 48f469dddc739d85a544ddeda5682ef0f5c8b3c9ece889cdc8fe5d9f54643966
opportunity_scaler_hash = 820e17c08c9844aa953c9bcce880ffd671a900cbc3dac062eddd7dafcc6c7548
```

The accepted Opportunity model payload is a corrective bootstrap artifact with:

```text
component = Opportunity
corrective_bootstrap = true
label_column = label__expected_edge_label_20d
target_kind = regression
model_family = sklearn_sgd_regressor
scaler_method = StandardScaler
```

The model has small SGD coefficients, but the current Runtime path feeds unscaled high-magnitude numeric features to it.

## Transform Audit

Read-only recomputation over the same 1000 Runtime rows:

| Path | Min | Median | Mean | Max | Positive |
|---|---:|---:|---:|---:|---:|
| Runtime artifact score | 11.78522441 | 675.340566745 | 2297.7138219916 | 20212.96186064 | 1000 |
| Legacy unscaled prediction | 11.7852244114 | 675.3405667444 | 2297.7138219916 | 20212.9618606364 | 1000 |
| Contract scaled prediction | 0.1517975577 | 0.2499848172 | 0.2475867743 | 0.3124888106 | 1000 |

Maximum absolute difference:

```text
abs(Runtime artifact score - legacy unscaled prediction) <= 0.00000000499813
```

This proves the Runtime artifacts match the unscaled legacy inference path.

## Data Flow Trace

1. Opportunity Design / Training

   `expected_edge_score` is the prediction for `label__expected_edge_label_20d`. The current accepted model is scaler-bound.

2. Opportunity Runtime Inference

   `src/ai_fund_lab_v2/opportunity_ai/inference.py` calls legacy `transform_features(...preprocessing)` and then `model.predict(matrix)`. No scaler artifact is loaded or applied.

3. Opportunity Artifact

   `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py` copies the same number into `expected_edge_score`, `opportunity_score`, and `expected_return`; `calibration_applied=false`.

4. Runtime Adapter

   `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py` canonicalizes aliases and validates finite numeric values. It does not scale, clip, divide, log-transform, or calibrate the value.

5. Position Management Decision

   `src/ai_fund_lab_v2/position_management_ai/inference.py` treats `expected_edge_score` as a small expected-edge signal. With values in the thousands, `normalize_range(edge, -0.10, 0.20)` saturates to `1.0` for every held-position decision.

## Policy Impact

PM held-position impact:

```text
positive_expected_edge = 95 / 95
PM edge normalization after normalize_range(edge, -0.10, 0.20) = 1.0 / 1.0 / 1.0 min/median/max
```

Observed PM reasons:

```text
positive_expected_edge|downside_risk_contained = 79
strong_trend_continuation|opportunity_rank_still_high|no_loss_averaging; ADD is outside SELL Planning scope = 16
```

Impact by action:

- HOLD: `positive_expected_edge` appeared in every HOLD reason.
- ADD: expected edge contribution was saturated, while final ADD still also required positive current return, top-5 buy rank, and downside below 0.50.
- REDUCE: positive expected edge would route risk-warning cases toward REDUCE instead of weak-hold EXIT, but the BP window did not cross the risk-warning thresholds.
- EXIT: hard EXIT triggers still override expected edge, but `trend_and_opportunity_broken` cannot trigger when expected edge is always positive.

## Production Commonality

No Historical-only PM scale conversion was found.

The relevant Runtime path is common:

- Runtime BUY producer calls the same `_produce_opportunity_artifact`.
- PM producer accepts only `historical`, `demo`, and `production`, and uses the same PM Opportunity contract helper for all three.
- PM adapter performs alias/date/finite validation only; no environment-specific normalization branch exists.

## Classification

Runtime defect:

```text
YES.
Runtime Opportunity inference does not apply the Accepted Generation-bound Opportunity scaler before producing Runtime opportunity_rankings.json.
```

AI Policy defect:

```text
NO immediate PM threshold defect found.
PM is consistent with a decimal / normalized expected-edge input. It is not responsible for repairing upstream scale.
```

Contract mismatch:

```text
YES.
The value named expected_edge_score does not have the same scale across Opportunity Runtime output and PM expected input.
```

Test Profile limitation:

```text
PARTIAL.
The Historical Smoke exposed the mismatch, but the mismatch is production-common and not merely a Historical fixture artifact.
```

No defect:

```text
NO.
The current Opportunity -> PM score-scale contract is not valid.
```

## Fix Decision

Runtime behavior should not be changed inside this audit.

Required fix direction:

```text
Implement Accepted Generation-bound Runtime inference for Candidate / Opportunity.
Load and hash-validate generation-bound scaler and calibration artifacts.
Apply imputer -> scaler -> model in the accepted feature order.
Fail closed on missing or mismatched scaler binding.
```

Forbidden fixes:

- PM-side ad hoc normalization.
- SELL threshold changes.
- `expected_edge_score` clipping just to make PM distribute differently.
- Historical-only branch.
- Test-only fixture processing.

## Regression / Re-run

Regression targets after the Runtime inference fix:

- `tests/runtime_v2/test_phase19_bn_pm_opportunity_model_authority.py`
- `tests/runtime_v2/test_phase17_aj_buy_opportunity_pm_contract.py`
- `tests/runtime_v2/test_phase17_bv15_opportunity_buy_eligibility_contract.py`
- `tests/runtime_v2/test_phase15af_position_management_runtime_connection.py`
- `tests/runtime_v2/test_phase15ap_position_management_input_contract.py`
- New regression: Accepted-generation scaler-bound Opportunity Runtime inference parity against formal validation / calibration matrix.

Historical Smoke re-run:

```text
Required after implementing scaler-bound Runtime inference.
Not executed in this audit because no Runtime behavior was changed.
```
