# Phase18-J — Runtime Discovery, Freshness Gate, Drift Gate and Runtime Acceptance

- Run ID: `phase18j-runtime-discovery-freshness-gate-20260717T000000Z`
- Final Judgment: `PHASE18_J_RUNTIME_DISCOVERY_ACCEPTANCE_COMPLETE`
- Runtime Decision: `PASS` / `MARKET_NO_OPPORTUNITY`
- Evidence: `reports/phase18_j_runtime_discovery_freshness_gate_acceptance/phase18j-runtime-discovery-freshness-gate-20260717T000000Z`

## Scope Guard

- Runtime Accepted Set update: not performed
- Runtime switch / submit: not performed
- BUY restart / production BUY / broker write / real order / SELL / ledger mutation: not performed
- Promotion Candidate was discovered but not adopted as Runtime Accepted Bundle

## Discovery

- Registry Discovery: `PASS`
- Runtime Discovery: `PASS`
- Bundle Resolution: `PASS`
- Accepted Joint Bundle Hash: `258bb79281a5241bd77eda35bac4fe4c9f0166a5d9e8ec597335c960248a4303`
- Promotion Candidate Runtime Accepted: `False`

## Freshness

- Freshness Gate: `PASS`
- Opportunity dataset_lag_business_days: `14`
- Opportunity model_training_lag_business_days: `14`
- Opportunity model_acceptance_age_business_days: `4`

## Drift

- Drift Gate: `PASS`
- Latest Runtime Inference: `.runtime/runtime_state/buy_ai/2026-07-10/latest_opportunity_inference.parquet`
- Positive Coverage: `0.0`
- NO BUY Ratio: `1.0`
- All Negative: `True`
- Market Classification: `MARKET_NO_OPPORTUNITY`

## Compatibility

- Runtime Compatibility: `PASS`
- Prediction Hash Match: `PASS`
- Expected Prediction Hash: `b3ff7f314ff8c4f4e5b01de2ad404e64c4426c35aa8659b49cc60ec240eaf5d7`
- Actual Prediction Hash: `b3ff7f314ff8c4f4e5b01de2ad404e64c4426c35aa8659b49cc60ec240eaf5d7`

## Failure Rehearsal

| Scenario | Runtime Decision | Fail Open | Status |
|---|---:|---:|---:|
| hash_mismatch | `BLOCK` | `False` | `PASS` |
| schema_mismatch | `BLOCK` | `False` | `PASS` |
| calibration_missing | `BLOCK` | `False` | `PASS` |
| freshness_violation | `BLOCK` | `False` | `PASS` |
| bundle_incompatibility | `BLOCK` | `False` | `PASS` |
| registry_corruption | `BLOCK` | `False` | `PASS` |
| missing_rollback_reference | `BLOCK` | `False` | `PASS` |

## Acceptance

| Item | Status |
|---|---:|
| registry_discovery | `PASS` |
| runtime_discovery | `PASS` |
| bundle_resolution | `PASS` |
| freshness_gate | `PASS` |
| drift_gate | `PASS` |
| model_unhealthy_classification | `PASS` |
| market_no_opportunity_classification | `PASS` |
| runtime_compatibility | `PASS` |
| prediction_hash_match | `PASS` |
| runtime_decision | `PASS` |
| failure_rehearsal | `PASS` |
| broker_write_not_executed | `PASS` |
| runtime_submit_not_executed | `PASS` |
| buy_not_restarted | `PASS` |
| production_unchanged | `PASS` |
