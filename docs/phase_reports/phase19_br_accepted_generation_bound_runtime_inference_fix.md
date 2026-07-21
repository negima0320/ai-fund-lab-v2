# Phase19-BR Accepted Generation-Bound Runtime Inference Fix

Status: `PHASE19_BR_ACCEPTED_GENERATION_BOUND_RUNTIME_INFERENCE_COMPLETE`

## Summary

Phase19-BQ identified that Runtime Opportunity inference was using the legacy Phase5-F unscaled inference path. Phase19-BR fixed the Runtime BUY AI producer so the normal Accepted Generation path applies the generation-bound preprocessing and StandardScaler before Candidate / Opportunity model prediction.

This is not a SELL/PM policy adjustment. No Position Management threshold, Opportunity threshold, BUY ranking policy, or Historical-only behavior was changed.

## Root Cause

Root cause:

```text
Runtime BUY AI producer resolved the Accepted Generation model path,
but then called legacy inference helpers that did not consume the
Accepted Generation-bound scaler, scaler hash, feature order, or
calibration binding.
```

Classification:

```text
Runtime defect
Contract mismatch
```

Not classified as:

```text
AI Policy defect
Test Profile limitation
No defect
```

## Contract Basis

The relevant Architecture / Contract rule is that Runtime may consume BUY AI models only through the current committed Accepted Generation, and scaler artifacts are required whenever the accepted model declares a scaled preprocessing pipeline.

The Runtime Consumer Adapter responsibility is:

- parse Accepted Generation Manifest
- load Candidate model/scaler/calibration
- load Opportunity model/scaler/calibration
- enforce feature order
- validate hashes
- fail closed on integrity/authority mismatch
- avoid legacy/latest/manual fallback

## Implementation

Added:

```text
src/ai_fund_lab_v2/runtime_v2/buy_ai/generation_bound_inference.py
```

Changed:

```text
src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py
```

The new Runtime inference path:

```text
Accepted Generation pointer
↓
Accepted Generation Manifest
↓
model hash validation
↓
scaler hash validation
↓
feature order validation
↓
model preprocessing transform
↓
generation-bound StandardScaler transform
↓
model prediction
↓
Runtime Candidate / Opportunity artifact
```

Runtime Opportunity artifacts now emit:

```text
transformation_stage = accepted_generation_bound_imputer_scaler_model
legacy_fallback_used = false
generation_bound_inference.scaler_hash = 820e17c08c9844aa953c9bcce880ffd671a900cbc3dac062eddd7dafcc6c7548
```

## Accepted Generation Evidence

Active Accepted Generation:

```text
phase19_aq_accepted_generation_641e6e313543f013
```

Opportunity model hash:

```text
48f469dddc739d85a544ddeda5682ef0f5c8b3c9ece889cdc8fe5d9f54643966
```

Opportunity scaler hash:

```text
820e17c08c9844aa953c9bcce880ffd671a900cbc3dac062eddd7dafcc6c7548
```

Candidate model hash:

```text
f08273d45cddf3b41bb4f62e237f635f49a6146ef8b46bfeeb80340e17134ecb
```

Candidate scaler hash:

```text
bf5a01d7d9d39674a21faf2082d3a766f19eec17a1dad53c679b39cd4a35448b
```

## Runtime Inference Parity

Test coverage compares Runtime generation-bound Opportunity prediction to the reference matrix:

```text
training_pipeline.transform_features
↓
generation-bound scaler.transform on scaled_feature_columns
↓
model.predict
```

Result:

```text
RUNTIME_INFERENCE_PARITY_PASS
```

## Fail-Closed Evidence

Added tests verify:

- missing scaler fails closed
- scaler hash mismatch fails closed
- feature order / required feature mismatch fails closed
- accepted Runtime producer does not use legacy fallback
- historical/demo/production-like roots share the same inference path

Result:

```text
RUNTIME_INFERENCE_FAIL_CLOSED_PASS
RUNTIME_GENERATION_ARTIFACT_VALIDATION_PASS
HISTORICAL_DEMO_PRODUCTION_INFERENCE_COMMON_PASS
```

## Runtime Smoke Evidence

Regression stages were executed in order.

Unit / contract regression:

```text
40 passed
```

Single-day Historical Smoke:

```text
run_id: runtime-test-historical-smoke-20260721T101735795573Z
business_days: 1
status: PASS
final_judgment: PASS
completed_days: 2026-07-06
```

Short Historical Smoke:

```text
run_id: runtime-test-historical-smoke-20260721T101827180122Z
business_days: 5
status: PASS
final_judgment: PASS
completed_days: 2026-07-06 through 2026-07-10
```

20BD Historical Smoke:

```text
run_id: runtime-test-historical-smoke-20260721T102119329463Z
business_days: 20
status: PASS
final_judgment: PASS
completed_days: 2026-06-17 through 2026-07-14
registry_unchanged: true
accepted_artifact_unchanged: true
broker_write_performed: false
external_delivery_performed: false
```

20BD morning runtime manifests:

```text
20 / 20 BUY AI PASS
20 / 20 Opportunity model version = phase19_aq_accepted_generation_641e6e313543f013:opportunity:48f469dddc739d85
20 / 20 transformation_stage = accepted_generation_bound_imputer_scaler_model
```

## PM Expected Edge Scale Contract

The PM side remains unchanged. The fix is upstream of PM:

```text
Opportunity Runtime inference now emits the Accepted Generation-bound model prediction scale.
PM consumes expected_edge_score without PM-side normalization or Historical-only adjustment.
```

Result:

```text
PM_EXPECTED_EDGE_SCALE_CONTRACT_PASS
```

## Decisions

Runtime behavior change:

```text
YES
```

Historical-only fix:

```text
NO
```

SELL/PM threshold adjustment:

```text
NO
```

Legacy fallback retained for Accepted Runtime path:

```text
NO
```

Regression required:

```text
YES
```

Historical Smoke rerun required:

```text
YES, completed through 20BD PASS
```

## Final Judgment

```text
PHASE19_BR_ACCEPTED_GENERATION_BOUND_RUNTIME_INFERENCE_COMPLETE
RUNTIME_OPPORTUNITY_SCALER_BINDING_PASS
RUNTIME_INFERENCE_PARITY_PASS
RUNTIME_GENERATION_ARTIFACT_VALIDATION_PASS
RUNTIME_INFERENCE_FAIL_CLOSED_PASS
HISTORICAL_DEMO_PRODUCTION_INFERENCE_COMMON_PASS
PM_EXPECTED_EDGE_SCALE_CONTRACT_PASS
```
