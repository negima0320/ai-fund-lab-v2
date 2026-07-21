# Phase19-BA Historical Temporal Isolation and Freshness Closure

## Final Judgment

```text
PHASE19_BA_FAIL
PHASE19_AY_DAY1_BLOCKED
```

BA reclassified the pre-Day1 state from observability-only review into a formal Historical Runtime temporal isolation failure. The target historical-smoke Day1 is `2026-07-06`, but the currently shared `.runtime` contains state and runtime artifacts whose business/as-of/input dates are after that target.

## Historical Target Period

```text
2026-07-06
2026-07-07
2026-07-08
2026-07-09
2026-07-10
```

Profile: `historical-smoke`  
Broker environment: `historical_simulated`

## Initial State Authority

The approved Day1 initial-state contract is an isolated empty Historical state, or another explicitly configured/pre-target snapshot contract. The current shared `.runtime` is not a valid implicit Day1 authority because it contains future state.

## Runtime Root Isolation

Current root inspected: `.runtime`  
Isolation result: `BLOCK`

Historical execution must use a backup/reset-created clean state or an isolated `.runtime` root. The current shared root cannot be used directly for Day1.

## Future-state Audit

Future-state reference count: `10`  
Block reason: `TEMPORAL_STATE_CONTAMINATION`

Detected future references include Persistent Ledger Current, Pending Plan transition time, Candidate/Opportunity inference results, AI lifecycle gate, and runtime feature artifacts dated `2026-07-14` or `2026-07-17` against target `2026-07-06`.

## PM / Ledger Authority

Persistent Ledger owns Current asset state. PM/runtime_state is derived operation state and cannot override a future Ledger Current for Day1 initialization. Ledger Current has a future as-of date, so Day1 remains blocked.

## Position Feature Temporal Result

Position feature remains `BLOCK` for historical Day1 semantics. `position_count=0` does not justify referencing Current authority dated after the target date.

## Data Sufficiency

Raw quotes, normalized quotes, and Listed Issues are available for the target period. This does not override temporal contamination in Runtime State.

## Freshness Expected Date

Historical mode now uses `target_business_date` as the expected freshness date source. Artifact timestamps and actual latest data dates are shown separately from expected target-date freshness.

## Inference Date Semantics

Candidate and Opportunity now expose the same fields:

```text
inference_business_date
input_feature_business_date
artifact_created_at
model_generation_id
```

Opportunity no longer reports `created_at` as an inference input business date.

## AI Generation Binding

Candidate and Opportunity individual sections now show Accepted Generation binding and runtime-loaded generation. Both resolve to `phase19_aq_accepted_generation_641e6e313543f013`.

## Feature Projection

Candidate feature projection: `PASS`  
Opportunity feature projection: `PASS`

Opportunity candidate-derived model inputs are classified as `candidate_dependency_features`, not missing runtime feature columns. Metadata columns are explicitly separated from model input features.

## Regression

```text
py_compile: PASS
pytest: 17 passed
system-status --write-evidence: exit 20 as expected for BA BLOCK
```

## Non-mutation

No Training, Calibration, Validation, Generation, Accepted Generation, Runtime pointer, BUY restart, Broker access, or Broker write was performed.

## Evidence

```text
reports/phase19_ba_historical_temporal_isolation_and_freshness_closure/
reports/phase_reports/phase19_ba_historical_temporal_isolation_and_freshness_closure.json
reports/runtime_tests/system_status/system-status-20260720T221147516688Z
```

## Next Step

Do not start AY Day1 from the current shared `.runtime`. The next corrective step is to materialize a clean Historical Day1 authority through formal backup/reset/fresh-run or an approved isolated runtime root, then rerun the BA preflight until `future_state_reference_count = 0`.
