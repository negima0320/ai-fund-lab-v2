# Phase16-X Read-only Artifact Registry Validator Hardening

## Final Judgment

```text
PHASE16_X_READ_ONLY_VALIDATOR_HARDENING_ACCEPTED
```

Phase16-X hardened the read-only Artifact Registry Validator for pre-Artifact-Acceptance quality. The changes remain limited to validator code, validator tests, and validation evidence/report output. No Runtime, AI, Feature, Registry Writer, Index Builder, artifact status, ACCEPTED promotion, consumer path, reset, simulation, or historical test work was performed.

## Changed Files

- `src/ai_fund_lab_v2/artifact_registry/validator.py`
- `tests/artifact_registry/test_phase16x_validator_hardening.py`
- `reports/phase16_registry_validation/*`
- `docs/phase_reports/phase16_x_read_only_validator_hardening.md`
- `reports/phase_reports/phase16_x_read_only_validator_hardening.json`

`scripts/run_artifact_registry_validation.py` was not structurally changed; its CLI behavior now receives the validator-level output safety guard through `main()`.

## Contract Basis

The implementation follows:

- `docs/02_architecture/artifact_registry_validator_contract.md`
- `docs/02_architecture/artifact_registry_event_and_acceptance_evidence_contract.md`
- `docs/02_architecture/artifact_acceptance_contract.md`
- `docs/02_architecture/ai_artifact_registry_and_capital_allocation_contract.md`
- `docs/02_architecture/artifact_path_registry_integration_and_migration_contract.md`
- Phase16-W findings W-F1 through W-F6

## Hardening Summary

| Area | Result |
| --- | --- |
| Output Root Safety Guard | Implemented |
| Acceptance Evidence content validation | Implemented |
| Candidate Artifact Set validation | Implemented |
| Opportunity Artifact Set validation | Implemented |
| PM Artifact Set validation | Implemented |
| Capital Allocation Artifact Set validation | Implemented |
| Artifact criticality failure classification | Implemented |
| Phase5-E string-dependent formal detection | Removed from formal Artifact Set validator |
| Minimal Schema Checker hardening | Implemented |
| Validation Result contract | Preserved |

## Output Root Guard

Implemented in `validate_phase16_inventory()` before any output directory creation.

Rejected cases:

- `output_root == input_root`
- `output_root` under `input_root`
- `output_root` under active `.runtime`
- `output_root` under `.runtime/artifact_registry`
- `output_root` under `.runtime/artifacts`
- `output_root` under protected artifact/code roots
- symlink-resolved output path reaching forbidden roots

Failure mode:

```text
VALIDATION_ERROR
```

The CLI returns exit code `2` with an explicit safety error.

## Acceptance Evidence Validation

For `new_status=ACCEPTED` or `runtime_use_eligible=true`, the validator now reads and validates:

- Acceptance Report
- Regression Evidence
- Review Approvals

Implemented checks:

- Acceptance Report schema conformance
- `decision=ACCEPT`
- `artifact_or_set_ref` subject match
- reviewed artifact hash match
- reviewed schema hash match
- Regression Evidence schema conformance
- regression subject match
- regression `result=PASS`
- no critical parity failures
- required approval roles:
  - `HUMAN_REVIEW`
  - `ARCHITECTURE_ACCEPTANCE`
  - `REGRESSION_ACCEPTANCE`
  - `RELEASE_APPROVAL`
- approval subject match
- approval `decision=APPROVED`
- approval evidence refs present

Missing or mismatched evidence is classified as:

```text
HALT
```

DRAFT and VALIDATED subjects skip Acceptance Evidence validation unless they incorrectly set `runtime_use_eligible=true`.

## Artifact Set Validation

The formal Artifact Set validator now validates all four set types:

- `CANDIDATE_ACCEPTED_SET`
- `OPPORTUNITY_ACCEPTED_SET`
- `PM_ACCEPTED_SET`
- `CAPITAL_ALLOCATION_POLICY_SET`

Common checks:

- required member roles
- duplicate role rejection
- member content hash presence
- member schema hash presence
- member hash map consistency
- schema hash map consistency
- artifact set hash recomputation
- `runtime_use_eligible=true` requires `status=ACCEPTED`
- runtime consumer refs present

Opportunity-specific checks:

- model and metrics belong to the same set identity
- metrics are not classified as `LEGACY_ONLY`, `TRAINING_ONLY`, `LEGACY`, or `REVOKED`
- formal mismatch detection no longer depends on the literal string `phase5e`

## Criticality Classification

Physical path absence is now classified by artifact metadata:

`HALT` for runtime-critical artifacts:

- runtime-use eligible artifact
- ACCEPTED artifact
- model / metrics
- PM code policy / runtime adapter
- policy / safety
- runtime-use feature or decision input

`REVIEW_REQUIRED` for non-runtime optional evidence:

- training evidence
- validation evidence
- historical evidence
- legacy evidence
- optional audit artifacts

The classification uses `artifact_type`, `runtime_use_eligible`, `retention_class`, and `consumer_compatibility`, not path strings.

## Schema Checker Hardening

Implemented without adding external dependencies:

- `format=date-time`
- schema-valued `additionalProperties`
- nested additional properties
- `minLength`
- `minItems`

No `jsonschema` dependency was added.

## Tests

Command:

```text
python3 -m pytest -q tests/artifact_registry/test_phase16v_read_only_validator.py tests/artifact_registry/test_phase16u_schema_amendments.py tests/artifact_registry/test_inventory_helpers.py tests/artifact_registry/test_phase16x_validator_hardening.py
```

Result:

```text
41 passed
```

Coverage added:

- output root same as input
- output root under input
- output root under `.runtime`
- output root under `.runtime/artifact_registry`
- output root under `.runtime/artifacts`
- symlink to `.runtime`
- normal reports output
- valid ACCEPTED evidence
- Acceptance Report decision mismatch
- Acceptance subject mismatch
- artifact hash mismatch
- regression failure
- required approval role missing
- approval subject mismatch
- evidence path missing
- valid Candidate, Opportunity, PM, and Capital Allocation sets
- missing/duplicate members
- Opportunity model/metrics mismatch without `phase5e` string reliance
- PM adapter missing
- Capital policy/set hash mismatch
- consumer incompatibility
- runtime-critical missing path HALT
- optional evidence missing path REVIEW_REQUIRED
- invalid date-time
- schema-valued additionalProperties value mismatch

## Phase16-P Revalidation

Command:

```text
python3 scripts/run_artifact_registry_validation.py --input reports/phase16_registry_inventory --output reports/phase16_registry_validation
```

Result:

| Field | Value |
| --- | ---: |
| PASS | 1 |
| PASS_WITH_WARNINGS | 34 |
| REVIEW_REQUIRED | 0 |
| FAIL | 0 |
| HALT | 0 |
| accepted_artifact_count | 0 |
| runtime_use_eligible_count | 0 |
| protected_hash_result | UNCHANGED |
| formal_registry_path_created | false |
| formal_artifacts_path_created | false |
| event_log_writer_implemented | false |
| index_builder_implemented | false |

Validation result contract check:

```text
validation_results=35
required_field_bad_count=0
```

## Warning Classification

Primary classification of 34 `PASS_WITH_WARNINGS` results:

| Classification | Count |
| --- | ---: |
| `PHASE16_P_MIGRATION_GAP` | 33 |
| `EXPECTED_DRAFT_STATUS` | 1 |

Secondary warning message classification:

| Classification | Count |
| --- | ---: |
| `PHASE16_P_MIGRATION_GAP` | 34 |
| `MISSING_FORMAL_SCHEMA_FIELD` | 24 |
| `MISSING_ACCEPTANCE_EVIDENCE` | 2 |
| `EXPECTED_DRAFT_STATUS` | 1 |

The warning profile remains expected for Phase16-P migration evidence. No warning grants Runtime eligibility or ACCEPTED status.

## Runtime Non-impact

Required guarantees:

| Guarantee | Result |
| --- | --- |
| Runtime Contract unchanged | YES |
| Runtime Authority unchanged | YES |
| Current unchanged | YES |
| Ledger unchanged | YES |
| Pending unchanged | YES |
| Runtime State unchanged | YES |
| AI Model unchanged | YES |
| Feature Schema unchanged | YES |
| Feature calculation unchanged | YES |
| Consumer path unchanged | YES |
| CLI / config default unchanged | YES |
| Opportunity fallback unchanged | YES |
| Capital Allocation behavior unchanged | YES |

Evidence:

- Protected hash result: `UNCHANGED`
- Runtime v2 imports do not reference `artifact_registry.validator`
- No Runtime v2, AI producer, Feature producer, Planning, Pending, Submit, Current, or Ledger files were modified by Phase16-X

## Before / After Hash Result

The validator summary records before/after hashes for:

- Current
- Ledger
- Pending
- Runtime State
- Candidate model
- Candidate manifest
- Opportunity model
- Phase5-P metrics
- Phase5-E metrics
- PM code-policy
- PM adapter
- Canonical normalized OHLCV
- major Feature artifact
- major Decision artifact

All protected entries:

```text
UNCHANGED
```

## Known Gaps

Remaining by scope:

- Registry Event Log Writer is still not implemented.
- Materialized Index Builder is still not implemented.
- Formal `.runtime/artifact_registry` and `.runtime/artifacts` paths are still not created.
- Artifact Status promotion and ACCEPTED promotion are still not performed.
- Runtime integration and Runtime lookup are still not implemented.
- Full JSON Schema Draft 2020-12 meta-schema validation remains out of scope without dependency review.
- Checkpoint Validator remains future work.

## Implementation Readiness

Validator hardening is accepted for the next review stage. Artifact Acceptance can now be designed against a stronger read-only validator, but no artifact should be promoted until the explicit acceptance phase authorizes it.

Next prefix:

```text
Phase16-Y
```
