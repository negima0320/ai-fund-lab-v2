# Phase30-AK0R - Candidate Feature / Model Inference / Score / Top50 Historical Runtime Lineage Audit

## Primary Judgment

```text
AUDIT_CUTOFF_DATE = 2023-09-19
COMPLETED_BUSINESS_DAYS = 273
CANDIDATE_RUNTIME_LINEAGE_JUDGMENT = PASS
RUN_RECOMMENDATION = CONTINUE_CURRENT_200BD_RUN
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AK0R
```

The running 200BD run
`runtime-test-historical-extended-smoke-20260816T121454359538Z` was audited
read-only. The run progressed beyond AK0 while this audit was started, so AK0R
uses the completed business-day authority observed at AK0R audit start:
`2023-09-19`.

The central answer is:

```text
Historical Runtime does not consume a precomputed Top50 shortcut.
Historical Runtime generates daily Candidate features during market_refresh,
then morning BUY AI reads those features and runs Accepted Generation-bound
Candidate model inference to produce candidate_score, score-only rank,
semantic hybrid rank, and Top50.
```

## Required Final Judgments

```text
CANDIDATE_FEATURE_GENERATION_MODE = RUNTIME_GENERATED
CANDIDATE_SCORE_GENERATION_MODE = LIVE_RUNTIME_INFERENCE
CANDIDATE_ACCEPTED_GENERATION_AUTHORITY_COMMON = YES
CANDIDATE_SCORE_PIT_SAFE = YES
HISTORICAL_CANDIDATE_MATERIALIZATION_CLASS = PRODUCTION_EQUIVALENT
ONE_PRODUCTION_CANDIDATE_LOGIC_PATH = YES
HISTORICAL_ONLY_CANDIDATE_SELECTION_REFERENCE_COUNT = 0
HISTORICAL_ONLY_CANDIDATE_SCORE_REFERENCE_COUNT = 0
CANDIDATE_SCORE_DETERMINISM = PASS
TOP50_SELECTION_MODE = RUNTIME_FULL_POPULATION
TOP50_PRECUT_POPULATION = min 3,260 / max 3,781 / avg 3,712.86
CANDIDATE_RUNTIME_LINEAGE_JUDGMENT = PASS
```

## Candidate End-to-End Lineage

| Stage | Producer | Artifact | Consumer |
| --- | --- | --- | --- |
| PIT source | Runtime market refresh / historical as-of view | run-scoped J-Quants normalized bars and listed info | feature refresh |
| Candidate feature builder | `paper_trading.feature_refresh.run_feature_refresh` | `.runtime/operations/feature_artifacts/<date>/candidate_features.parquet` | BUY AI producer |
| Accepted Generation resolver | `runtime_v2.accepted_generation_resolver.resolve_accepted_generation` | `historical_evaluation_authority.json` + accepted generation manifest | BUY AI producer |
| Candidate inference | `runtime_v2.buy_ai.producer._produce_candidate_artifact` | `candidate_decisions.json` | Opportunity AI |
| Score generation | `generation_bound_inference.predict_generation_bound_scores` | `rows[].candidate_score` | score rank / surface |
| Score-only rank | `_produce_candidate_artifact` | `candidate_rank`, `score_only_candidate_rank` | semantic hybrid ordering |
| PIT surface | `_apply_candidate_pit_quality_surface` | `candidate_pit_quality_surface`, surface evidence | hybrid rank |
| Top50 | same Candidate producer | final 50 `rows` | Opportunity / Strategy Intelligence |

Evidence was materialized in:

```text
reports/phase_reports/phase30_ak0r/candidate_lineage_map.json
```

## Feature Generation Timing

```text
CANDIDATE_FEATURE_GENERATION_MODE = RUNTIME_GENERATED
```

For all `273` completed days:

```text
feature_refresh_executed_count = 273
feature_refresh_inference_executed_count = 0
candidate_artifact_count = 273
candidate_pass_count = 273
```

Feature refresh generates `.runtime/operations/feature_artifacts/<date>/candidate_features.parquet`
from run-scoped PIT market/listed inputs. It does not run model inference.
Model inference occurs later in BUY AI.

Sample evidence:

| Date | Feature rows | Feature target min/max | Future rows |
| --- | ---: | --- | ---: |
| 2022-08-10 | 4,165 | 2022-08-10 / 2022-08-10 | 0 |
| 2022-08-15 | 4,165 | 2022-08-15 / 2022-08-15 | 0 |
| 2023-03-03 | 4,165+ | 2023-03-03 / 2023-03-03 | 0 |
| 2023-05-23 | 4,165+ | 2023-05-23 / 2023-05-23 | 0 |
| 2023-09-19 | 4,353 | 2023-09-19 / 2023-09-19 | 0 |

The exact per-sample values are in:

```text
reports/phase_reports/phase30_ak0r/pit_temporal_samples.json
```

## Candidate Score Generation Timing

```text
CANDIDATE_SCORE_GENERATION_MODE = LIVE_RUNTIME_INFERENCE
```

Code authority:

```text
src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py
src/ai_fund_lab_v2/runtime_v2/buy_ai/generation_bound_inference.py
```

The runtime producer:

1. Resolves Accepted Generation.
2. Loads `candidate_features.parquet`.
3. Filters rows for the current `feature_date`.
4. Loads the generation-bound model and scaler.
5. Calls `predict_generation_bound_scores`.
6. Writes `candidate_score` into `candidate_decisions.json`.

The target run artifacts include `generation_bound_inference` evidence on every
completed day, including:

```text
accepted_generation_id = phase19_aq_accepted_generation_641e6e313543f013
model_file = .runtime/ai_lifecycle/training_outputs/phase19_ad_u3_k_corrective_bootstrap_7cc6dfbfbf7899fa/candidate/model.pkl
model_hash = f08273d45cddf3b41bb4f62e237f635f49a6146ef8b46bfeeb80340e17134ecb
runtime_model_hash = f08273d45cddf3b41bb4f62e237f635f49a6146ef8b46bfeeb80340e17134ecb
scaler_hash = bf5a01d7d9d39674a21faf2082d3a766f19eec17a1dad53c679b39cd4a35448b
runtime_scaler_hash = bf5a01d7d9d39674a21faf2082d3a766f19eec17a1dad53c679b39cd4a35448b
transformation_stage = accepted_generation_bound_imputer_scaler_model
legacy_fallback_used = false
manual_path_used = false
```

## Accepted Generation Authority

```text
CANDIDATE_ACCEPTED_GENERATION_AUTHORITY_COMMON = YES
```

Historical uses the same resolver and accepted generation manifest, but binds
the generation at run start via:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260816T121454359538Z/historical_evaluation_authority.json
```

This is not a historical-only model pointer. It is a run-start fixed Accepted
Generation authority that resolves the same Candidate model/scaler/hash as the
Production/Demo resolver path.

## PIT / Temporal Integrity

```text
CANDIDATE_SCORE_PIT_SAFE = YES
```

All sampled days had:

```text
feature_date = business_date
feature target_date max = business_date
feature_future_rows_gt_business_date = 0
future_information_used = false
historical_outcome_used_as_runtime_input = false
historical_outcome_used_for_production_parameter_selection = false
legacy_fallback_used = false
manual_path_used = false
```

Across all 273 completed days:

```text
future_leakage_flag_count = 0
legacy_fallback_true_count = 0
manual_path_true_count = 0
```

## Historical Materialization Classification

```text
HISTORICAL_CANDIDATE_MATERIALIZATION_CLASS = PRODUCTION_EQUIVALENT
```

The Historical run materializes daily feature and decision artifacts, but those
artifacts are generated through the same runtime Candidate producer and
Accepted Generation-bound inference contract. The materialization is not a
precomputed Top50 shortcut.

Older/offline `historical_candidate_top50` references still exist in
Opportunity training/reporting and earlier validation utilities, but the target
Historical Runtime BUY AI path does not read those artifacts.

## Production vs Historical Path

| Stage | Production | Demo | Historical | Same Authority? |
| --- | --- | --- | --- | --- |
| feature source | PIT market/listed source | same | run-scoped historical as-of PIT source | YES |
| feature builder | feature refresh | same | feature refresh during market_refresh | YES |
| Accepted Generation resolver | business-date bound ledger | same | same resolver with fixed run authority | YES |
| Candidate model | accepted generation member | same | same accepted generation member | YES |
| inference producer | BUY AI producer | same | BUY AI producer | YES |
| candidate_score | runtime inference | same | runtime inference | YES |
| PIT surface | runtime Candidate producer | same | runtime Candidate producer | YES |
| semantic hybrid ordering | runtime Candidate producer | same | runtime Candidate producer | YES |
| Top50 cut | `top_n=50` runtime cut | same | `top_n=50` runtime cut | YES |

```text
ONE_PRODUCTION_CANDIDATE_LOGIC_PATH = YES
```

## Historical-Specific Logic Search

```text
HISTORICAL_ONLY_CANDIDATE_SELECTION_REFERENCE_COUNT = 0
HISTORICAL_ONLY_CANDIDATE_SCORE_REFERENCE_COUNT = 0
```

Repo search found offline/test/doc references to `historical_candidate_top50`
and older precomputed Candidate artifacts. These are not target Runtime
authority. Runtime-source hits for `manual_model_path_used` are monitoring and
forbidden-fallback evidence fields, not historical-only candidate score logic.

Evidence:

```text
reports/phase_reports/phase30_ak0r/historical_candidate_reference_search.json
```

## Candidate Score Determinism

```text
CANDIDATE_SCORE_DETERMINISM = PASS
```

For the five required samples, Codex re-ran Accepted Generation-bound Candidate
inference read-only from the daily `candidate_features.parquet` and compared
the recomputed scores with materialized `candidate_decisions.json` Top50 rows.

| Date | Rows checked | Eligible population recomputed | Mismatches |
| --- | ---: | ---: | ---: |
| 2022-08-10 | 50 | 3,260 | 0 |
| 2022-08-15 | 50 | 3,424 | 0 |
| 2023-03-03 | 50 | 3,743 | 0 |
| 2023-05-23 | 50 | 3,759 | 0 |
| 2023-09-19 | 50 | 3,780 | 0 |

Evidence:

```text
reports/phase_reports/phase30_ak0r/candidate_score_determinism_check.json
```

## Candidate Artifact Provenance

Candidate artifacts contain sufficient core provenance:

```text
business_date
feature_date
feature_path
model_path
accepted_generation_binding
generation_bound_inference
model_hash / runtime_model_hash
scaler_hash / runtime_scaler_hash
feature_order_hash
prediction_schema
candidate_pre_cut_count
surface / semantic hybrid distributions
final_top50_symbol_order
score_only_top50_symbol_order
```

No blocking observability gap was found. One non-blocking improvement would be
to materialize a direct `candidate_score_generation_mode` field in the artifact
instead of requiring inference from `generation_bound_inference`.

## Top50 Selection Timing

```text
TOP50_SELECTION_MODE = RUNTIME_FULL_POPULATION
```

The flow is:

```text
daily candidate_features full population
-> accepted model inference for all eligible rows
-> score-only candidate_rank
-> Candidate PIT surface
-> semantic_hybrid_class ordering
-> final top_n=50 rows
```

It is not:

```text
precomputed Top50
precomputed score-only Top50
Historical-only selector
fixed Candidate list
```

## Pre-Cut Population

```text
TOP50_PRECUT_POPULATION = min 3,260 / max 3,781 / avg 3,712.86
```

Sample pre-cut populations:

| Date | Pre-cut population | Final Top50 |
| --- | ---: | ---: |
| 2022-08-10 | 3,260 | 50 |
| 2022-08-15 | 3,424 | 50 |
| 2023-03-03 | 3,743 | 50 |
| 2023-05-23 | 3,759 | 50 |
| 2023-09-19 | 3,780 | 50 |

This is architecture evidence only and was not used to propose Candidate count
changes.

## Relation to AK0

AK0's `1,592` hybrid-added symbol-days are generated from the production-equivalent
Candidate lineage confirmed here. AK0's candidate-to-capital attrition should
therefore be investigated downstream, not as a Candidate shortcut or leakage
defect.

## Runtime / Authority Judgment

```text
CANDIDATE_RUNTIME_LINEAGE_JUDGMENT = PASS
```

No critical Candidate Runtime architecture defect or leakage defect was found.

## Leakage / Evidence Integrity

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
CANDIDATE_SCORE_USES_FUTURE_DATE_DATA = FALSE
```

## 200BD Run Decision

```text
CONTINUE_CURRENT_200BD_RUN
```

Codex did not stop, resume, replay, or mutate the run.

## Deliverables

```text
docs/phase_reports/phase30_ak0r_candidate_feature_model_inference_score_top50_historical_runtime_lineage_audit.md
reports/phase_reports/phase30_ak0r_candidate_feature_model_inference_score_top50_historical_runtime_lineage_audit.json
reports/phase_reports/phase30_ak0r/candidate_lineage_map.json
reports/phase_reports/phase30_ak0r/production_historical_path_comparison.json
reports/phase_reports/phase30_ak0r/candidate_score_provenance.json
reports/phase_reports/phase30_ak0r/historical_candidate_reference_search.json
reports/phase_reports/phase30_ak0r/pit_temporal_samples.json
reports/phase_reports/phase30_ak0r/candidate_score_determinism_check.json
```

## Recommended Next Task

```text
Phase30-AK1 - ADD Conversion / PS Executable Capital Bridge Audit
```
