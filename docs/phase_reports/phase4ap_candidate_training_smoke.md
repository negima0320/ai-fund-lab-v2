# Phase4-AP Candidate Training Smoke

## Purpose

Phase4-AP runs the first Candidate AI training smoke test.

The current real_runtime dataset only covers `2026-03-02` to `2026-04-27` after label generation, so the formal Train / Validation / Test split has no train or validation rows. Phase4-AP therefore does not perform formal model evaluation. It only confirms that the Candidate AI training pipeline can read the dataset, train on feature columns, save a model artifact, and report smoke metrics without leakage.

## Scope

Phase4-AP performs:

- dataset load
- time-ordered smoke split inside the available 2026 period
- feature-only training
- label / future leakage check
- model artifact save
- model manifest save
- smoke metrics summary

Phase4-AP does not perform:

- formal time-series evaluation
- production model adoption
- production Candidate inference
- Candidate Quality Audit pass/fail
- backtest
- trading
- Paper Trading
- Broker integration
- promotion
- reader switch

## Input

Input dataset:

```text
Phase4-AO dataset
```

Target label:

```text
label__momentum_candidate_label
```

Feature columns:

```text
feature__*
```

## Smoke Split

The smoke split is time-series only. Random split is forbidden.

The implementation sorts available `target_date` values and uses the earlier dates for `smoke_train` and later dates for `smoke_validation`.

## Leakage Guard

Feature columns must not include:

```text
future_return_*
future_max_return_*
future_max_drawdown_*
top_decile_*
downside_bad_*
momentum_candidate_label
label__*
```

Labels remain available only as `label__*` columns in the training dataset and are not used as features.

## Model Strategy

If `lightgbm` is available, Phase4-AP uses:

```text
lightgbm.LGBMClassifier
```

If `lightgbm` is unavailable, the smoke test falls back to:

```text
sklearn.HistGradientBoostingClassifier
```

Fallback is recorded in `model_type`.

## Outputs

Model outputs:

```text
.runtime/candidate_ai/models/phase4ap_candidate_smoke_model.pkl
.runtime/candidate_ai/models/phase4ap_candidate_smoke_manifest.json
```

Reports:

```text
reports/candidate_ai/full_range/phase4ap_candidate_training_smoke_summary.json
reports/phase_reports/phase4ap_candidate_training_smoke_audit.json
docs/phase_reports/phase4ap_candidate_training_smoke_audit.md
```

## Readiness

Success readiness:

```text
READY_FOR_CANDIDATE_INFERENCE_SMOKE
```

This means the training pipeline smoke test passed. It does not mean the model is production-ready.

## Next Phase

The next phase is Phase4-AQ Candidate Inference Smoke.

Phase4-AQ should use the smoke model to score the latest target_date feature table and generate a top-50 candidate list. It must not perform production promotion, backtest, or trading.
