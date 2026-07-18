# Phase18-B — Common PIT Dataset Rebuild Pipeline Implementation

## Judgment

`PHASE18_B_COMMON_DATASET_PIPELINE_IMPLEMENTATION_COMPLETE`

Phase18-B implemented the AI Lifecycle v2 SoT-compliant Common PIT Dataset Rebuild Pipeline for Candidate and Opportunity datasets. The scope was kept to dataset rebuild only. Training, Champion / Challenger, Promotion, Registry accepted update, Runtime switch, BUY restart, and Broker write were not implemented or executed.

## Source Material Confirmed

- `docs/02_architecture/ai_lifecycle_v2.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/phase_reports/phase18_a_common_pit_dataset_rebuild_pipeline_existing_implementation_audit_and_plan.md`

Phase18-A classifications were preserved:

- Candidate: Phase4-BC / Phase4-BD / Phase4-BE reused through an adapter.
- Opportunity: Phase5-D join/leakage core plus Phase5P 32-feature contract reused through an adapter.
- Phase9-L1: not promoted to Opportunity Dataset; only source authority / cutoff / audit concepts were reflected.

## Implemented Components

| Component | Implementation |
|---|---|
| Common Dataset Rebuild Entrypoint | `src/ai_fund_lab_v2/ai_lifecycle/dataset_rebuild.py` |
| Candidate Adapter | `src/ai_fund_lab_v2/ai_lifecycle/adapters.py` |
| Opportunity Adapter | `src/ai_fund_lab_v2/ai_lifecycle/adapters.py` |
| Source Authority Resolver | `src/ai_fund_lab_v2/ai_lifecycle/source_authority.py` |
| Label-safe Cutoff Resolver | `src/ai_fund_lab_v2/ai_lifecycle/cutoff.py` |
| Dataset Bundle Writer | `src/ai_fund_lab_v2/ai_lifecycle/bundle.py` |
| Schema / PIT / Leakage / Quality / Lineage Validators | `src/ai_fund_lab_v2/ai_lifecycle/validators.py` |
| Dataset Hash Generator | `src/ai_fund_lab_v2/ai_lifecycle/bundle.py` |
| Atomic Publisher | `src/ai_fund_lab_v2/ai_lifecycle/bundle.py` |
| Failure Artifact Writer | `src/ai_fund_lab_v2/ai_lifecycle/bundle.py` |

## Bundle Contract

Successful publication is blocked unless all files exist:

- `dataset.parquet`
- `dataset_metadata.json`
- `feature_schema.json`
- `target_schema.json`
- `lineage.json`
- `data_quality.json`
- `date_coverage.json`
- `drop_reasons.csv`
- `hash_manifest.json`
- `status.json`

Failure path writes only temporary artifacts plus a failure artifact under reports. The final bundle directory is not created when validation or adapter execution fails.

## Acceptance Evidence

| Acceptance | Evidence |
|---|---|
| Candidate Dataset Bundle生成PASS | `tests/ai_lifecycle/test_phase18b_common_pit_dataset_rebuild.py::test_candidate_adapter_writes_complete_bundle` |
| Opportunity Dataset Bundle生成PASS | `tests/ai_lifecycle/test_phase18b_common_pit_dataset_rebuild.py::test_opportunity_adapter_candidate_source_ref_and_bundle` |
| Schema Validation PASS | `status.json` validation evidence asserted in tests |
| PIT Validation PASS | label-safe cutoff validation asserted in Candidate bundle test |
| NO_LEAKAGE_PASS | leakage evidence asserted as `NO_LEAKAGE_PASS` |
| Row Uniqueness PASS | Candidate keys `target_date + code`; Opportunity keys `target_date + code + candidate_source_ref` |
| Dataset Metadata生成PASS | `dataset_metadata.json` required fields asserted |
| Lineage生成PASS | source authority evidence hashes asserted |
| Hash Manifest生成PASS | idempotency test compares dataset/schema hashes |
| Atomic Publish PASS | bundle writer publishes only after required files and validations pass |
| Failure Path PASS | invalid path-like `candidate_source_ref` blocks final publish and writes failure artifact |
| Idempotency PASS | same input produces same `dataset_hash`, `schema_hash`, and `dataset_version` |

## Verification

Command:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase18b_pycache python3 -m pytest tests/test_phase4bc_long_history_feature_regeneration.py tests/test_phase4bd_long_history_label_regeneration.py tests/test_phase4be_long_history_dataset_rebuild.py tests/opportunity_ai/test_phase5d_opportunity_dataset_builder.py tests/ai_lifecycle/test_phase18b_common_pit_dataset_rebuild.py
```

Result:

```text
24 passed
```

## Non-Execution Confirmation

The implementation emits explicit metadata flags confirming:

- `training_executed=false`
- `promotion_performed=false`
- `runtime_switch_performed=false`
- `broker_write_executed=false`

No Registry accepted update, Runtime cutover, BUY restart, or Broker write path was added.
