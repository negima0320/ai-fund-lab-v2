# Phase19-AD-R2 AD-U2 to AD-U3 Dataset Input Contract Gate Review

## Final Judgment

```text
PHASE19_AD_R2_PASS_AFTER_CORRECTIVE_FIX
PHASE19_AD_U3_ENTRY_CONFIRMED
```

Supporting:

```text
AD_U3_DATASET_INPUT_CONTRACT_PASS_AFTER_CORRECTIVE_FIX
ARTIFACT_BINDING_PASS
LABEL_SAFE_AUTHORITY_PASS
CORPORATE_ACTION_BOUNDARY_PASS_WITH_FORMAL_LIMITATION
ROLLING_SPLIT_BOUNDARY_PASS
NO_RUNTIME_MUTATION_PASS
NO_BROKER_WRITE_PASS
```

Forbidden declarations were not made:

```text
AD_U3_COMPLETE
ACCEPTED_GENERATION_CREATED
BUY_READY
PRODUCTION_READY
RUNTIME_TRANSITION_COMPLETE
AUTONOMOUS_OPERATION_COMPLETE
```

## Review Scope

This review checked whether the Phase19-AD-U2 output can serve as the formal AD-U3 dataset input boundary.

Reviewed SoT:

```text
docs/02_architecture/autonomous_ai_operations_architecture.md
docs/02_architecture/runtime_architecture_v2.md
docs/01_requirements/phase_roadmap.md
```

Reviewed Phase19 AD-U1 / AD-U2 documents and evidence:

```text
docs/phase_reports/phase19_ad_u1_d_final_closure_and_ad_u2_entry_decision.md
docs/phase_reports/phase19_ad_r1_u1_u2a_independent_implementation_review.md
docs/phase_reports/phase19_ad_u2_a_dataset_to_split_foundation.md
docs/phase_reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization.md
docs/phase_reports/phase19_ad_u2_c_dataset_policy_blocker_closure.md
docs/phase_reports/phase19_ad_u2_d_corporate_action_policy_approval.md
docs/phase_reports/phase19_ad_u2_e_rolling_split_policy_evidence_review.md
docs/phase_reports/phase19_ad_u2_f_rolling_split_policy_approval.md
reports/phase19_ad_u2_f_rolling_split_policy_approval/ad_u3_dataset_input_contract.json
```

## Architecture Traceability

Architecture requires:

- Market Data to Common PIT Dataset to Label-safe Dataset to Generation.
- Every generation input to bind immutable dataset authority and immutable split authority.
- Runtime to consume only a committed Accepted Generation, not AD-U2 dataset or split artifacts.
- Training inputs to exclude Runtime, Paper, Broker, PnL, test, and audit result artifacts.

R2 evidence confirms the corrected AD-U3 input contract now binds dataset revision, dataset bytes, schema, lineage, label-safe boundary, Corporate Action policy, Rolling Split policy, and split content hashes.

## AD-U3 Input Contract Completeness

The original U2-F artifact:

```text
reports/phase19_ad_u2_f_rolling_split_policy_approval/ad_u3_dataset_input_contract.json
```

was not complete enough for AD-U3. It identified dataset revisions and split IDs, but lacked required AD-U3 binding fields such as contract id/version/status/authority/source phase, per-component dataset path, dataset content hash, schema hash, lineage hash, source cutoff, split path, split content hash, feature schema identity, and label schema identity.

Corrective fix:

```text
reports/phase19_ad_r2_ad_u2_to_ad_u3_gate_review/ad_u3_dataset_input_contract_corrected.json
```

This corrected contract is the R2-reviewed AD-U3 dataset input contract.

## Artifact Binding Result

PASS after corrective fix.

Candidate:

```text
dataset_revision_id: candidate_dataset_revision_policy_amended_95eedc15c17fee4e
dataset_content_hash: 0afdc29fc22691b0b4ccee0524ed27c04f5212b3994a39ddacd4be55b4187db6
dataset_schema_hash: d3d83d8030f7a1f69a83cd73c8a58897f92f00d09fa24e00eddd84732b0337af
split_id: split_2edb9f39d8008b10
split_content_hash: 93d3782ea30318ee57238b8caa1fc604a03e28e44e4ef181efda2467bceb37f7
```

Opportunity:

```text
dataset_revision_id: opportunity_dataset_revision_policy_amended_e7f9478409126d8e
dataset_content_hash: 3258c6f8e328cd08ad8154db70bc3f24ba1423b616dd9a4a05476f1fab7a7c09
dataset_schema_hash: 0390d382c951b8001205c998fd50466978780fbf4ff34b63e4c72c4699f0a71f
split_id: split_61b5c8077880a82e
split_content_hash: 43bd7289662cb774f8b99fc76a9c802205565c707e2bb7c70fa7f3ce7ebc7cf1
```

All referenced dataset files, dataset revision files, schema manifests, and split artifacts exist and have recorded hashes.

## Candidate Dataset / Split Result

Candidate dataset binding PASS.

Candidate split binding PASS.

Window:

```text
train: 2021-06-14 to 2024-12-02
validation: 2025-01-06 to 2025-12-01
test: 2026-01-05 to 2026-03-03
recent_holdout: 2026-04-01 to 2026-05-15
target_horizon_business_days: 20
embargo_business_days: 20
```

## Opportunity Dataset / Split Result

Opportunity dataset binding PASS.

Opportunity split binding PASS.

Window:

```text
train: 2021-09-08 to 2024-12-02
validation: 2025-01-06 to 2025-12-01
test: 2026-01-05 to 2026-03-03
recent_holdout: 2026-04-01 to 2026-05-15
target_horizon_business_days: 20
embargo_business_days: 20
```

## Label-Safe Authority Result

PASS.

Authority:

```text
computed_label_safe_cutoff + formal trading calendar + target horizon + per-symbol label availability
```

The computed label-safe cutoff is:

```text
2026-05-29
```

Both Candidate and Opportunity bind:

```text
dataset_target_date_max: 2026-05-15
unavailable_label_rows: 0
legacy_metadata_only_authority_used: false
```

The legacy metadata cutoff mismatch remains recorded but is not authority.

## Corporate Action Boundary Result

PASS_WITH_FORMAL_LIMITATION.

Approved Corporate Action policy:

```text
policy_id: phase19_ad_u2_d_corporate_action_dataset_handling
policy_hash: 2459ff93b262e0a9008cd710fc6f447f9d66dc44f8eddf07442ab30c14855c34
decision: APPROVE_WITH_FORMAL_LIMITATION
```

AD-U3 may consume only policy-bound dataset/features. It must not ingest Corporate Action event feeds directly.

## Rolling Split Boundary Result

PASS.

Approved Rolling Split policy:

```text
policy_id: phase19_ad_u2_f_rolling_split_policy_option_c_capped_expanding_hybrid
policy_hash: 4defbb1e4c5e8ef4d3ef1b3bdfdfd89782dfb7e204c8597e40a49b99df61a5e3
window_type: CAPPED_EXPANDING_HYBRID
```

R2 materialized standalone split artifacts so AD-U3 can bind split content hashes directly:

```text
reports/phase19_ad_r2_ad_u2_to_ad_u3_gate_review/versioned_splits/candidate_split_2edb9f39d8008b10.json
reports/phase19_ad_r2_ad_u2_to_ad_u3_gate_review/versioned_splits/opportunity_split_61b5c8077880a82e.json
```

AD-U3 must consume these split artifacts. It must not recompute or reinterpret split windows.

## Candidate / Opportunity Temporal Alignment

PASS.

Candidate and Opportunity share:

```text
validation window
test window
recent holdout window
label_safe_max: 2026-05-15
trading_calendar_identity
target_horizon_business_days: 20
embargo_business_days: 20
```

Candidate training starts earlier than Opportunity, which is allowed because each component uses its available history under the approved capped-expanding hybrid policy.

## Prohibited Training Input Audit

PASS_WITH_AD_U3_ADAPTER_REQUIRED.

The corrected AD-U3 input contract permits dataset and split resolution only from the contract-bound entries.

Prohibited as training inputs:

```text
Runtime state
Paper result
Broker state
PnL
Backtest result
Test result
Audit result
latest path resolution
direct runtime pointer
Corporate Action event feed
```

Dataset schema audit:

```text
Candidate feature columns: 13
Opportunity feature columns: 32
Forbidden feature column hits: none
future_* columns: target schema only, label-safe target use only
```

Loader / entrypoint audit:

```text
environment variable input injection: not found
glob/latest training input discovery: not found in training_pipeline.py
runtime_state join: not found in training_pipeline.py
reports directory training join: not found in training_pipeline.py
direct dataset_dir bypass: exists in Phase18 DatasetAuthority
recomputed split bypass: exists in Phase18 make_time_series_split(dataset)
```

Therefore the dataset schemas pass the prohibited-column audit, but existing Phase18 training code is not AD-U3-safe until wrapped by a contract-only resolver/adapter.

## Training Entrypoint Review

Direct use of the existing Phase18 training entrypoint is REVIEW_REQUIRED for AD-U3.

Findings:

- `DatasetAuthority` accepts direct `dataset_dir` / hash / schema inputs.
- `run_training_pipeline` reads `dataset.parquet` directly from `authority.dataset_dir`.
- `make_time_series_split(dataset)` recomputes the split instead of consuming the approved versioned split artifact.

AD-U3 first implementation step must add or use an AD-U3 dataset input contract resolver/adapter and reject direct dataset dirs, latest globs, runtime/broker/paper/PnL inputs, and recomputed splits.

## Bootstrap / Retraining Boundary

PASS.

The corrected contract is explicitly:

```text
bootstrap_or_retraining: BOOTSTRAP
previous_generation_ref: null
```

Bootstrap does not require previous revision delta. Retraining must later require incremental label-safe business days, incremental rows, schema continuity, and lineage continuity.

## Deferred Model Quality Policy Assessment

AD-U3 entry is confirmed, but training execution is not allowed yet.

These values remain deferred and were not guessed:

```text
minimum_training_rows
minimum_validation_rows
minimum_positive_labels
minimum_negative_labels
maximum_missing_ratio
```

AD-U3 must start with:

```text
AD_U3_DATASET_INPUT_CONTRACT_RESOLVER_OR_ADAPTER
MODEL_QUALITY_POLICY
```

## Authority Boundary

PASS.

Dataset authority:

```text
reports/phase19_ad_r2_ad_u2_to_ad_u3_gate_review/ad_u3_dataset_input_contract_corrected.json
```

Runtime authority remains:

```text
Accepted Generation Resolver only
```

Not authority:

```text
legacy registry fallback
runtime pointer direct model path
promotion candidate
latest dataset glob
Phase18 direct DatasetAuthority for AD-U3
```

## Runtime Isolation

PASS.

Runtime does not directly consume AD-U2 dataset or split artifacts. Runtime consumption remains blocked until an Accepted Generation exists and a committed runtime pointer is written in a later phase.

## Corrective Fixes

R2 corrective fixes were append-only:

```text
R2_FIX_001: Complete corrected AD-U3 Dataset Input Contract
R2_FIX_002: Standalone Candidate / Opportunity split artifacts with content hashes
```

No Accepted Decision, Runtime pointer, BUY restart, or Broker write was performed.

## Non-Mutation

PASS.

No mutation was made to:

```text
Accepted Decision
Runtime pointer
Current
Pending
Ledger
Safety
Broker
BUY state
SELL state
```

## Failure Injection

PASS.

R2 recorded FI-1 through FI-16 using contract-level negative simulation and code/evidence review:

```text
FI-1 Dataset bytes変更 -> BLOCK
FI-2 Split bytes変更 -> BLOCK
FI-3 Policy hash変更 -> BLOCK
FI-4 Draft split参照 -> Rejected
FI-5 Label-safe範囲超過 -> BLOCK
FI-6 Embargo不足 -> BLOCK
FI-7 Trading Calendar identity欠落 -> Invalid contract
FI-8 Candidate / Opportunity時間矛盾 -> BLOCK or REVIEW_REQUIRED
FI-9 Runtime pathをTraining inputへ注入 -> Rejected
FI-10 Broker / Paper / PnL列混入 -> BLOCK
FI-11 Legacy fallback -> Rejected
FI-12 Contractを回避したdataset直指定 -> Rejected
FI-13 Bootstrapにincremental revision要求 -> Contract violation detected
FI-14 RetrainingがBootstrapへfallback -> Rejected
FI-15 RuntimeがSplitを直接参照 -> BLOCK
FI-16 Review task mutation -> Runtime / Trading State unchanged; Broker write 0
```

## Regression

PASS.

Commands:

```text
PYTHONPYCACHEPREFIX=/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/ai_lifecycle/dataset_revision_materialization.py tests/ai_lifecycle/test_phase19_ad_u2_f_rolling_split_policy_approval.py
PYTHONPYCACHEPREFIX=/tmp/ai-fund-lab-v2-pycache python3 -m pytest tests/ai_lifecycle/test_phase19_ad_u2_f_rolling_split_policy_approval.py tests/ai_lifecycle/test_phase19_ad_u2_d_corporate_action_policy_approval.py tests/ai_lifecycle/test_phase19_ad_u2_c_dataset_policy_blocker_closure.py tests/ai_lifecycle/test_phase19_ad_u2_b_dataset_revision_materialization.py tests/ai_lifecycle/test_phase19_ad_u2_a_dataset_to_split_foundation.py -q
```

Result:

```text
43 passed
```

## Evidence

Evidence directory:

```text
reports/phase19_ad_r2_ad_u2_to_ad_u3_gate_review/
```

Summary:

```text
reports/phase_reports/phase19_ad_r2_ad_u2_to_ad_u3_gate_review.json
```

## Remaining Risks

Remaining AD-U3 work:

- Implement AD-U3 Dataset Input Contract resolver/adapter before training execution.
- Materialize Model Quality Policy thresholds from evidence before training acceptance.
- Preserve Corporate Action formal limitations and hard blocks.
- Keep Runtime isolated until Accepted Generation and later Runtime Transition phases.
