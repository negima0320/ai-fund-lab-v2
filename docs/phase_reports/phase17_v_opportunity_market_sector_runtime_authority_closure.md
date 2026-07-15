# Phase17-V Opportunity Market / Sector Feature Runtime Authority Closure

## Final Judgment

`PHASE17_V_OPPORTUNITY_RUNTIME_FEATURE_AUTHORITY_ACCEPTED`

## Summary

- Connected Runtime Opportunity feature production to the existing Market/Sector authority in `opportunity_ai.market_sector_completion`.
- Updated Consumer Readiness to validate the accepted Opportunity model input contract: 32 model columns, with 3 Candidate decision columns supplied by the Candidate artifact and 29 unprefixed columns required in `opportunity_feature_input.parquet`.
- Regenerated and promoted PIT feature artifacts for `2026-07-06`, `2026-07-07`, and `2026-07-08` without retraining the model or changing model/metrics artifacts.
- Kept the failed run `runtime-test-historical-smoke-20260714T220656958171Z` frozen; no resume/run-state mutation was performed.

## Authority Classification

- Opportunity model path: `.runtime/artifacts/ai/opportunity/model/formal_opportunity_model/sha256-140e350bd9b12bf0/model.pkl`
- Model SHA256: `140e350bd9b12bf0c595184587fa2a3bd74236e4bdf1818df481022980dd6acd`
- Model version: `opportunity_model_phase5e_v1`
- Metrics path: `.runtime/artifacts/ai/opportunity/metrics/formal_opportunity_metrics/sha256-8428f2327e773747/metrics.json`
- Metrics/model relationship: `physical_model_sha256_identity_matches; metrics legacy path is not accepted by path string alone`
- Metrics legacy model path authority: `legacy_metrics_path_content_matches_runtime_model`
- Classification: not a simple path-string match; Runtime accepts the physical model identity by SHA256/content identity.

## Regeneration / Promotion

| Feature date | Regen | Rows | Consumer | Contract | PIT listed snapshot | Eligible MS coverage |
| --- | --- | ---: | --- | --- | --- | ---: |
| 2026-07-06 | FEATURES_READY | 4370 | READY | PASS | 2026-07-06 | 1.000 |
| 2026-07-07 | FEATURES_READY | 4370 | READY | PASS | 2026-07-07 | 1.000 |
| 2026-07-08 | FEATURES_READY | 4370 | READY | PASS | 2026-07-07 | 1.000 |

## 5BD Plan

- `scripts/runtime_test.py plan --profile historical-smoke --business-days 5 --start-date 2026-07-06 --json`: `PASS` / returncode `0`.
- No `run`, `resume`, submit, execution, demo/prod trading, or external fetch was executed.

## Evidence

- Evidence directory: `reports/phase17_v_opportunity_market_sector_runtime_authority_closure`
- Machine summary: `reports/phase_reports/phase17_v_opportunity_market_sector_runtime_authority_closure.json`

| Evidence | Status |
| --- | --- |
| `consumer_readiness_model_contract.json` | `PASS` |
| `determinism_audit.json` | `PASS` |
| `feature_date_contract_5bd.json` | `PASS` |
| `forbidden_source_audit.json` | `PASS` |
| `future_data_audit.json` | `PASS` |
| `historical_regeneration.json` | `PASS` |
| `model_input_contract.json` | `PASS` |
| `pit_listed_sector_authority.json` | `PASS` |
| `producer_integration.json` | `PASS` |
| `promotion_transaction.json` | `PASS` |
| `read_audit.json` | `PASS` |
| `runner_plan.json` | `PASS` |
| `runtime_feature_contract.json` | `PASS` |
| `runtime_resolution_trace.json` | `PASS` |
| `trading_state_hash_audit.json` | `PASS` |

## Tests

- `python3 -m pytest tests/runtime_v2/test_phase17_v_opportunity_market_sector_authority.py tests/runtime_v2/test_phase15an_feature_consumer_readiness.py tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py -q` -> `19 passed`.

## Next

`Phase17-W Historical Runtime 5BD Smoke Test Clean Rerun`
