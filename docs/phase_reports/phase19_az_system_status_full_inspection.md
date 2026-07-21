# Phase19-AZ System Status Full Inspection

## Final Judgment

```text
PHASE19_AZ_SYSTEM_STATUS_FULL_INSPECTION_COMPLETE
PHASE19_AY_MANUAL_VALIDATION_OBSERVABILITY_READY
```

Forbidden declarations were not made:

```text
BUY_READY
PRODUCTION_READY
AUTONOMOUS_OPERATION_COMPLETE
```

## Scope

`system-status` was expanded from a category-level health summary into the standard full human inspection report.

The standard command remains:

```bash
PYTHONPATH=src:. python3 scripts/runtime_test.py system-status
```

No `--detailed` option was added. The default output is the detailed report.

## Active Component Inventory

Inventory is now emitted in JSON and human output. The active trained AI models are:

```text
Candidate AI
Opportunity AI
```

Non-model active decision subsystems are also listed, including:

```text
Runtime Baseline
Freshness Evaluation
Safety Decision
Position Management
Submit Guard
```

Legacy latest/mtime model resolver is listed as inactive/retired and is not treated as active Runtime authority.

## Data Sources

The inspection now reports raw and normalized J-Quants artifacts separately.

Current observed data inventory:

```text
Raw J-Quants Daily Quotes: rows=448964, symbols=4525, latest=2026-07-14
Normalized J-Quants Daily Quotes: rows=426689, symbols=4375, latest=2026-07-14
Listed Issues: rows=22193, symbols=4444, latest=2026-07-15
```

## Datasets

Candidate and Opportunity datasets are displayed separately.

```text
Candidate dataset revision: candidate_dataset_revision_policy_amended_95eedc15c17fee4e
Candidate training rows: 3496880
Candidate symbols: 4588

Opportunity dataset revision: opportunity_dataset_revision_policy_amended_e7f9478409126d8e
Opportunity training rows: 39563
Opportunity symbols: 1895
```

Train, validation, test, label-safe cutoff, schema hash, content hash, and Accepted Generation binding are included.

## Runtime Features

Runtime Features are no longer compressed into a single BUY Feature line. Current active feature artifacts:

```text
Candidate Runtime Feature
Opportunity Runtime Feature
Position Runtime Feature
Capital Runtime Feature
```

Candidate and Opportunity feature rows are both `4375`, but their feature schemas and consumers are displayed separately.

## AI Models

Candidate and Opportunity model inspection includes model/scaler/calibration paths and hashes, feature order hash, training dataset revision, split windows, Runtime load state, latest inference date, input rows, and output counts.

Count semantics are explicit:

```text
Candidate evaluated_symbols = 4375
Candidate candidate_output_count = 50
Candidate candidate_top50_count = 50

Opportunity input_candidate_count = 50
Opportunity ranking_count = 50
Opportunity top20_count = 20
Opportunity dual_gate_status = DUAL_GATE_PASS
```

This avoids the misleading interpretation that `PASS 50` means all evaluated symbols were only 50.

## Decision Subsystems

The report now includes model-adjacent and rule/threshold subsystems:

```text
Runtime Baseline
Freshness Evaluation
Lifecycle Monitoring / Statistical Drift
Safety
Position Management
BUY Planning
SELL Planning / Continuity
Approval
Submit Guard
Execution Guard
```

Each shows input artifact, policy/version, authority, latest decision, status, BUY impact, and SELL impact.

## Authority

Accepted Generation authority is displayed with:

```text
COMMITTED Accepted Generation ID
accepted_at
aggregate hash
runtime pointer path
runtime loaded generation
resolver result
Candidate binding
Opportunity binding
Dataset binding
Baseline binding
Freshness binding
forbidden fallback count
```

Current forbidden fallback count is `0`.

## Runtime State

Runtime State is now displayed by individual artifact:

```text
Current
Pending
Ledger
PM
Safety
```

Safety uses the Phase19-AY timing-aware contract and currently reports:

```text
NOT_YET_APPLICABLE
PRE_RUN_NOT_MATERIALIZED
```

## Broker Layer

Broker API is not accessed. The report separates:

```text
Approval
Submit Guard
Execution
Broker Connection
Notification
Reporting
```

`NOT_PERFORMED` remains distinct from `PASS`.

## Freshness Matrix

Freshness Matrix currently contains 15 entries, including:

```text
Raw
Normalized
Candidate Dataset
Opportunity Dataset
Candidate Feature
Opportunity Feature
Candidate Inference
Opportunity Inference
Accepted Generation
Runtime Loaded Generation
Safety Decision
PM State
```

## Regression

```text
py_compile: PASS
pytest: 12 passed
```

Regression command:

```text
PYTHONPYCACHEPREFIX=.tmp_pycache PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase19_az_system_status_full_inspection.py tests/runtime_v2/test_phase19_ax_system_status.py tests/runtime_v2/test_phase19_ay_safety_preflight.py
```

## Non-mutation

```text
Training rerun: 0
Calibration refit: 0
Validation rerun: 0
Generation created: 0
Accepted Generation mutation: 0
Runtime pointer write: 0
Trading State mutation: 0
BUY restart: 0
Broker access: NOT_PERFORMED
Broker write: 0
```

## Evidence

```text
reports/phase_reports/phase19_az_system_status_full_inspection.json
reports/phase19_az_system_status_full_inspection/ai_system_inventory.json
reports/phase19_az_system_status_full_inspection/ai_system_inventory.md
reports/phase19_az_system_status_full_inspection/data_inventory.json
reports/phase19_az_system_status_full_inspection/dataset_inventory.json
reports/phase19_az_system_status_full_inspection/feature_inventory.json
reports/phase19_az_system_status_full_inspection/runtime_component_inventory.json
reports/phase19_az_system_status_full_inspection/full_system_status_sample.txt
reports/phase19_az_system_status_full_inspection/full_system_status_sample.json
reports/phase19_az_system_status_full_inspection/freshness_matrix.json
reports/phase19_az_system_status_full_inspection/authority_binding_audit.json
reports/phase19_az_system_status_full_inspection/regression_results.json
reports/phase19_az_system_status_full_inspection/non_mutation.json
reports/phase19_az_system_status_full_inspection/final_judgment.json
```

## Next Step

Proceed with AY manual validation using the expanded observability surface:

```text
PHASE19_AY_MANUAL_VALIDATION_OBSERVABILITY_READY
```
