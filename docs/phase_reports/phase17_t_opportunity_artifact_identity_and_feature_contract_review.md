# Phase17-T Opportunity Artifact Identity and Feature Contract Review

Prefix: `Phase17-T`
Work Name: `Opportunity Artifact Identity and Feature Contract Review`

Final judgment:

```text
PHASE17_T_OPPORTUNITY_PATH_ONLY_MISMATCH_CLOSED_FEATURE_CONTRACT_REVIEW_REQUIRED
```

## Summary

Phase17-T investigated the 2026-07-06 Historical Morning stop from:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260714T220656958171Z/
```

The original stop was:

```text
buy_ai_status=HALT
buy_ai_reason=opportunity_metrics_model_path_mismatch
```

Classification:

| Contract Item | Classification | Finding |
|---|---|---|
| Opportunity Runtime Producer model path vs metrics model path | Path-string-only mismatch | Metrics referenced `reports/opportunity_ai/phase5p/models/opportunity_model.pkl`; Runtime loaded Registry accepted copy under `.runtime/artifacts/.../model.pkl`. |
| Opportunity Model Hash | Same artifact identity | Both paths hash to `140e350bd9b12bf0c595184587fa2a3bd74236e4bdf1818df481022980dd6acd`. |
| Opportunity Training Metrics Hash | Same artifact identity | Registry metrics and original training metrics both hash to `8428f2327e77374743f69e2ebc956a97a9d718880ef2acfc26571f94d9fd9511`. |
| Opportunity Model Version | Same version | `opportunity_model_phase5e_v1`. |
| Registry Accepted Artifact | Preserved | Runtime still resolves `OPPORTUNITY_AI_SET` through Registry; no Historical-only override was added. |
| Artifact Provenance | Preserved | Formal copied artifacts remain Registry authority; legacy path is accepted only when SHA-256 proves identical content. |
| Opportunity Feature Contract | Real schema mismatch remains | Accepted Opportunity model/metrics require market/sector features not present in current Runtime Feature Artifact. |

## Implementation

Updated:

```text
src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py
tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py
```

The Opportunity metrics validator now treats a metrics-embedded legacy model path as the same artifact only when:

1. the path is the same as the Runtime-loaded Registry path, or
2. the metrics-embedded path exists and its SHA-256 equals the Runtime-loaded model SHA-256, or
3. metrics carries an explicit model hash equal to the Runtime-loaded model SHA-256.

Different hashes still fail closed with `opportunity_metrics_model_path_mismatch` or `opportunity_metrics_model_hash_mismatch`. This is common Runtime behavior and applies equally to Demo, Historical, and Production.

The validator also writes `metrics_model_path_authority` and `metrics_model_path_hash` into `metrics_validation` evidence.

## Recheck

Re-executed the 2026-07-06 Historical Morning CLI for the target run. The original HALT no longer occurs.

New result:

```text
exit_code=20
final_state=REVIEW_REQUIRED
buy_ai_reason=opportunity_feature_schema_mismatch
```

Evidence:

```text
.runtime/runtime_state/run_manifest/2026-07-06/runtime-v2-morning-2026-07-06-20260714T222009.316540+0000.json
.runtime/runtime_state/buy_ai/2026-07-06/opportunity_rankings.json
```

The Opportunity metrics validation now records:

```text
status=PASS
metrics_model_path_authority=legacy_metrics_path_content_matches_runtime_model
model_hash=140e350bd9b12bf0c595184587fa2a3bd74236e4bdf1818df481022980dd6acd
metrics_model_path_hash=140e350bd9b12bf0c595184587fa2a3bd74236e4bdf1818df481022980dd6acd
```

## Remaining Blocker

The remaining blocker is not a path issue.

Accepted Opportunity model / metrics require these missing Runtime input columns:

```text
feature__market_breadth_20d
feature__market_breadth_5d
feature__market_downtrend_context
feature__market_downtrend_flag
feature__market_ma_5_20_ratio
feature__market_return_20d
feature__market_return_5d
feature__market_risk_flag
feature__market_volatility_20d
feature__sector_breadth_20d
feature__sector_momentum_flag
feature__sector_rank_20d
feature__sector_return_20d
feature__sector_return_5d
feature__sector_weak_flag
feature__stock_vs_sector_return_20d
```

The current accepted Feature Artifact schema for Opportunity input supplies the price / trend / volume / missing-flag columns, but not these market / sector context columns.

Therefore the remaining stop is a real contract mismatch between:

```text
Opportunity Model / Opportunity Metrics / Opportunity Feature Schema
    vs
Runtime Feature Artifact / Opportunity Runtime Producer input
```

It must not be bypassed by Historical-only defaults, null fills, or feature fabrication. A common authority closure is required for Demo, Historical, and Production.

## Verification

Passed:

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase17_t_pycache python3 -m pytest -q \
  tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py::test_phase17t_legacy_metrics_model_path_with_same_sha256_is_accepted \
  tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py::test_phase17t_legacy_metrics_model_path_with_different_sha256_still_halts \
  tests/runtime_v2/test_phase17_s_json_serialization.py

PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase17_t_pycache python3 -m py_compile \
  src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py
```

Result:

```text
6 passed
py_compile PASS
```

## Operations Not Performed

- No Historical-only relaxation
- No Feature Artifact mutation
- No Opportunity model retraining
- No Registry mutation
- No Acceptance mutation
- No Trading State reset / rollback / restore
- No Submit
- No Execution
- No Demo submit
- No Production access
