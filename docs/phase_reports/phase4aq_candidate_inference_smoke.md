# Phase4-AQ Candidate Inference Smoke

## Purpose

Phase4-AQ runs the first Candidate AI inference smoke test.

It loads the Phase4-AP smoke model, scores the latest `target_date` feature table, and generates a top-50 candidate list. This phase checks inference pipeline connectivity only. Candidate score quality is not evaluated here.

## Scope

Phase4-AQ performs:

- smoke model artifact load
- latest target_date feature row load
- `universe_eligible = true` filtering
- feature-only model input construction
- `candidate_score` calculation
- candidate top-50 output
- inference leakage audit

Phase4-AQ does not perform:

- production model adoption
- formal Candidate Quality Audit
- backtest
- trading
- Paper Trading
- Broker integration
- promotion
- reader switch
- order execution

## Inputs

Model inputs:

```text
.runtime/candidate_ai/models/phase4ap_candidate_smoke_model.pkl
.runtime/candidate_ai/models/phase4ap_candidate_smoke_manifest.json
```

Feature input:

```text
latest target_date Candidate feature table
```

The current expected latest target_date is:

```text
2026-05-29
```

Only `universe_eligible = true` rows are scored.

## Output Schema

Each candidate row includes:

```text
candidate_score
candidate_rank
candidate_reason
excluded_reason
feature_snapshot_id
model_version
audit_flags
```

`candidate_score` is not a buy signal. `candidate_rank` is not a purchase priority. They are only smoke outputs for candidate extraction.

## Leakage Guard

The inference input must use only feature columns.

Forbidden as model input:

```text
future_return_*
future_max_return_*
future_max_drawdown_*
top_decile_*
downside_bad_*
momentum_candidate_label
label__*
```

## Outputs

Runtime outputs:

```text
.runtime/candidate_ai/inference/
.runtime/candidate_ai/candidates/
```

Report artifacts:

```text
reports/candidate_ai/full_range/phase4aq_candidate_inference_smoke_summary.json
reports/candidate_ai/full_range/phase4aq_candidate_inference_smoke_top50.json
reports/candidate_ai/full_range/phase4aq_candidate_inference_smoke_top50.csv
reports/phase_reports/phase4aq_candidate_inference_smoke_audit.json
docs/phase_reports/phase4aq_candidate_inference_smoke_audit.md
```

## Readiness

Success readiness:

```text
READY_FOR_CANDIDATE_OUTPUT_AUDIT_SMOKE
```

This means inference smoke completed and candidate artifacts were generated. It does not mean the model or candidates are production-ready.

## Next Phase

The next phase is Phase4-AR Candidate Output Audit Smoke.

Phase4-AR should audit candidate list schema, responsibility boundaries, top-50 count, reason coverage, and absence of trading or purchase decision semantics.
