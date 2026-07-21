# Phase19-AD-U2-A Dataset-to-Split Foundation

## Final Judgment

```text
PHASE19_AD_U2_A_DATASET_FOUNDATION_PASS
```

Supporting:

```text
COMMON_PIT_DATASET_CONTRACT_PASS
LABEL_SAFE_CONTRACT_PASS
DATA_SUFFICIENCY_CONTRACT_PASS
ROLLING_SPLIT_CONTRACT_PASS
NO_RUNTIME_MUTATION_PASS
NO_BROKER_WRITE_PASS
```

Not declared:

```text
AD_U2_COMPLETE
AD_U3_READY
BUY_READY
PRODUCTION_READY
ACCEPTED_GENERATION_CREATED
RUNTIME_TRANSITION_COMPLETE
```

## Current Dataset Pipeline

Current call graph is confirmed in:

```text
reports/phase19_ad_u2_a_dataset_to_split_foundation/current_dataset_pipeline.json
```

Observed flow:

```text
J-Quants raw data
  -> raw collections: daily_quotes, listed_issues, trading_calendar, fins_summary
  -> canonical normalized daily quotes
  -> Common PIT Dataset bundle
  -> label-safe PIT/leakage validation
  -> training-time split_definition.json
```

Current Common PIT Dataset artifacts:

```text
.runtime/ai_lifecycle/datasets/candidate_ai/candidate_dataset_c8de026d3ea8aa4d
.runtime/ai_lifecycle/datasets/opportunity_ai/opportunity_dataset_fbadc8091a31486d
```

Current Opportunity dataset:

```text
target_date_min: 2021-09-08
target_date_max: 2026-05-15
row_count: 56995
label_safe_cutoff: 2026-06-04
latest_trading_date: 2026-06-26
```

Current split is still training-time fixed policy:

```text
.runtime/ai_lifecycle/training/opportunity_ai/opportunity_training_phase18h_1081babc49b5d26b/split_definition.json
train_end: 2024-12-02
```

## Current-to-Target Gap

Gap matrix:

```text
reports/phase19_ad_u2_a_dataset_to_split_foundation/current_to_target_gap_matrix.json
```

Summary:

| Area | Classification | Result |
| --- | --- | --- |
| Raw J-Quants market data | REUSE_WITH_EXTENSION | Existing raw sources and manifests can feed revision evidence. |
| Canonical normalized quotes | REUSE_WITH_EXTENSION | Existing normalized parquet is usable but must be bound to dataset revision lineage. |
| Corporate action | REUSE_WITH_EXTENSION | Adjusted quote fields exist; explicit integrity remains a later review dimension. |
| Common PIT Dataset bundle | REUSE_WITH_EXTENSION | Existing bundle is retained; revision metadata and lineage validation added. |
| Label-safe availability | REUSE_WITH_EXTENSION | Existing cutoff/PIT/leakage validators are reused through a sufficiency input contract. |
| Data sufficiency | NEW | Standalone evaluator added. |
| Rolling split | MIGRATE | Current fixed training split remains; versioned split contract added for Generation input. |
| Runtime mutation boundary | REUSE_AS_IS | No runtime mutation performed. |

## Dataset Lineage

Implemented:

```text
DatasetRevisionMetadata
load_dataset_revision_from_bundle
validate_dataset_lineage
```

Evidence:

```text
reports/phase19_ad_u2_a_dataset_to_split_foundation/dataset_lineage_inventory.json
reports/phase19_ad_u2_a_dataset_to_split_foundation/dataset_contract.json
```

The revision metadata records:

```text
dataset_identity
dataset_revision
component
dataset_path
dataset_hash
schema_hash
row_count
target_date_min
target_date_max
label_safe_cutoff
source_lineage_hash
previous_dataset_revision
```

## Label-safe

Implemented:

```text
evaluate_label_safe_availability
```

Contract:

```text
dataset_max_not_after_cutoff
dataset_not_after_latest_trading_date
target_horizon_business_days
```

Current actual label-safe result:

```text
PASS
```

Evidence:

```text
reports/phase19_ad_u2_a_dataset_to_split_foundation/label_safe_contract.json
```

## Data Sufficiency

Implemented:

```text
DataSufficiencyPolicy
evaluate_data_sufficiency
NO_RETRAIN_INSUFFICIENT_NEW_DATA
```

Required gates:

```text
dataset_revision
label_safe_availability
minimum_incremental_business_days
minimum_incremental_rows
schema_compatibility
dataset_lineage_continuity
```

Decision values:

```text
SUFFICIENT
INSUFFICIENT
REVIEW_REQUIRED
```

Current actual decision:

```text
INSUFFICIENT
NO_RETRAIN_INSUFFICIENT_NEW_DATA
```

Reason:

```text
Current Common PIT Dataset is label-safe, but AD-U2-A does not have a new accepted dataset revision chain or minimum incremental data evidence.
```

Evidence:

```text
reports/phase19_ad_u2_a_dataset_to_split_foundation/data_sufficiency_contract.json
```

## Rolling Split

Implemented:

```text
build_versioned_rolling_split_contract
validate_versioned_split_contract
```

Minimum fields:

```text
split_id
dataset_revision
train_start
train_end
validation_start
validation_end
policy_version
schema_hash
```

The contract is explicitly:

```text
generation_input_artifact: true
runtime_consumed: false
```

Evidence:

```text
reports/phase19_ad_u2_a_dataset_to_split_foundation/rolling_split_contract.json
```

## Failure Injection

Covered:

```text
Dataset missing
Dataset hash mismatch
Label-safe unavailable
Insufficient new data
Split schema mismatch
Dataset lineage discontinuity
```

Evidence:

```text
reports/phase19_ad_u2_a_dataset_to_split_foundation/failure_injection_results.json
tests/ai_lifecycle/test_phase19_ad_u2_a_dataset_to_split_foundation.py
```

## Regression

Command:

```text
python3 -m pytest tests/ai_lifecycle/test_phase19_ad_u2_a_dataset_to_split_foundation.py tests/ai_lifecycle/test_phase18b_common_pit_dataset_rebuild.py tests/ai_lifecycle/test_phase18d_training_pipeline.py tests/ai_lifecycle/test_phase19_ad_u1_b_bootstrap_generation.py tests/ai_lifecycle/test_phase19_ad_u1_c_bootstrap_compatibility.py tests/runtime_v2/test_phase19_ad_u1_a_accepted_generation_resolver.py
```

Result:

```text
36 passed, 2 sklearn convergence warnings in Phase18-D fixture training
```

Additional U2-A unit rerun:

```text
7 passed
```

Evidence:

```text
reports/phase19_ad_u2_a_dataset_to_split_foundation/test_results.json
```

## Changed files

U2-A implementation:

```text
src/ai_fund_lab_v2/ai_lifecycle/dataset_to_split.py
tests/ai_lifecycle/test_phase19_ad_u2_a_dataset_to_split_foundation.py
docs/phase_reports/phase19_ad_u2_a_dataset_to_split_foundation.md
reports/phase_reports/phase19_ad_u2_a_dataset_to_split_foundation.json
reports/phase19_ad_u2_a_dataset_to_split_foundation/
docs/01_requirements/phase_roadmap.md
```

AD-U1 files remain present from the previous slice and are not reverted.

Evidence:

```text
reports/phase19_ad_u2_a_dataset_to_split_foundation/changed_files.json
```

## Evidence

```text
reports/phase19_ad_u2_a_dataset_to_split_foundation/current_dataset_pipeline.json
reports/phase19_ad_u2_a_dataset_to_split_foundation/dataset_lineage_inventory.json
reports/phase19_ad_u2_a_dataset_to_split_foundation/dataset_contract.json
reports/phase19_ad_u2_a_dataset_to_split_foundation/label_safe_contract.json
reports/phase19_ad_u2_a_dataset_to_split_foundation/data_sufficiency_contract.json
reports/phase19_ad_u2_a_dataset_to_split_foundation/rolling_split_contract.json
reports/phase19_ad_u2_a_dataset_to_split_foundation/current_to_target_gap_matrix.json
reports/phase19_ad_u2_a_dataset_to_split_foundation/failure_injection_results.json
reports/phase19_ad_u2_a_dataset_to_split_foundation/non_mutation_evidence.json
reports/phase19_ad_u2_a_dataset_to_split_foundation/test_results.json
reports/phase19_ad_u2_a_dataset_to_split_foundation/changed_files.json
reports/phase19_ad_u2_a_dataset_to_split_foundation/final_judgment.json
reports/phase_reports/phase19_ad_u2_a_dataset_to_split_foundation.json
```

## Remaining AD-U2 work

Remaining work before AD-U2 can close:

```text
Materialize an actual new dataset revision chain when new label-safe data exists.
Expand corporate action integrity from partial adjusted-field evidence into explicit sufficiency evidence.
Bind versioned split contracts to the future Generation assembly input.
Keep Candidate training, Opportunity training, Calibration, Accepted Decision, Runtime pointer, BUY restart, and Broker write prohibited until their later slices.
```
