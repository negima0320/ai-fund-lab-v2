# Phase19-AD-U3-A Contract-Only Dataset Input Resolver / Training Adapter

## Final Judgment

```text
PHASE19_AD_U3_A_CONTRACT_ONLY_INPUT_RESOLVER_PASS
PHASE19_AD_U3_MODEL_QUALITY_POLICY_READY
```

Forbidden declarations were not made:

```text
CANDIDATE_TRAINING_COMPLETE
OPPORTUNITY_TRAINING_COMPLETE
UNIFIED_GENERATION_CREATED
ACCEPTED_GENERATION_CREATED
AD_U3_COMPLETE
BUY_READY
PRODUCTION_READY
RUNTIME_TRANSITION_COMPLETE
```

## Resolver Design

Implemented:

```text
src/ai_fund_lab_v2/ai_lifecycle/ad_u3_dataset_input_resolver.py
```

The resolver performs contract loading, contract validation, artifact hash validation, approved split resolution, feature/label schema resolution, prohibited input guarding, bootstrap-mode validation, and validate-only evidence materialization.

It does not train models, fit calibration, create Unified Generation, write Accepted Decision, update Runtime pointers, restart BUY, or write to Broker.

## Formal Input Authority

The only AD-U3 dataset input authority accepted by this resolver is:

```text
reports/phase19_ad_r2_ad_u2_to_ad_u3_gate_review/ad_u3_dataset_input_contract_corrected.json
```

Rejected as authority:

```text
dataset_dir direct input
dataset_path direct input
split_path direct override
latest / glob discovery
environment variable dataset injection
Phase18 DatasetAuthority alone
Runtime state
Accepted legacy component model
legacy registry
arbitrary reports artifacts
```

## Contract Validation

PASS.

Accepted contract status:

```text
PASS_AFTER_CORRECTIVE_FIX
```

The resolver validates:

```text
contract_id
contract_version
contract_status
authority
source_phase
generation_mode
bootstrap_or_retraining
candidate
opportunity
```

For each component it requires dataset revision, dataset path, dataset hash, schema hash, lineage hash, source revision, source cutoff, label-safe max, split id/path/hash, Rolling Split policy, Corporate Action policy, calendar identity, target horizon, embargo, feature schema identity, and label schema identity.

## Candidate Resolved Input

PASS.

```text
component: Candidate
dataset_revision_id: candidate_dataset_revision_policy_amended_95eedc15c17fee4e
dataset_hash: 0afdc29fc22691b0b4ccee0524ed27c04f5212b3994a39ddacd4be55b4187db6
dataset_schema_hash: d3d83d8030f7a1f69a83cd73c8a58897f92f00d09fa24e00eddd84732b0337af
split_id: split_2edb9f39d8008b10
split_hash: 93d3782ea30318ee57238b8caa1fc604a03e28e44e4ef181efda2467bceb37f7
feature_columns: 13
label_columns: 8
training_executed: false
```

## Opportunity Resolved Input

PASS.

```text
component: Opportunity
dataset_revision_id: opportunity_dataset_revision_policy_amended_e7f9478409126d8e
dataset_hash: 3258c6f8e328cd08ad8154db70bc3f24ba1423b616dd9a4a05476f1fab7a7c09
dataset_schema_hash: 0390d382c951b8001205c998fd50466978780fbf4ff34b63e4c72c4699f0a71f
split_id: split_61b5c8077880a82e
split_hash: 43bd7289662cb774f8b99fc76a9c802205565c707e2bb7c70fa7f3ce7ebc7cf1
feature_columns: 32
label_columns: 14
training_executed: false
```

## Artifact Binding Result

PASS.

The resolver recalculates and verifies:

```text
Dataset bytes hash
Dataset revision artifact hash
Dataset schema hash
Dataset lineage hash
Split artifact hash
Rolling Split Policy hash
Corporate Action Policy hash
Feature schema identity
Label schema identity
```

Path existence alone is not sufficient for PASS.

## Versioned Split Resolution

PASS.

The resolver consumes the standalone R2 split artifacts:

```text
reports/phase19_ad_r2_ad_u2_to_ad_u3_gate_review/versioned_splits/candidate_split_2edb9f39d8008b10.json
reports/phase19_ad_r2_ad_u2_to_ad_u3_gate_review/versioned_splits/opportunity_split_61b5c8077880a82e.json
```

It does not call `make_time_series_split(dataset)` and does not recompute date boundaries.

## Feature / Label Schema Result

PASS.

Candidate:

```text
feature columns: 13
label columns: 8
future feature columns: none
```

Opportunity:

```text
feature columns: 32
label columns: 14
future feature columns: none
```

`future_*` columns are allowed only in target/label schema for label-safe target use.

## Prohibited Input Guard

PASS.

The resolver rejects direct or injected paths for:

```text
Runtime state
Runtime result
Runtime PnL
Paper Ledger
Paper Trading result
Broker Snapshot
Broker positions
cash
portfolio value
selected
bought
Backtest result
Test result
Audit result
Corporate Action event feed
future adjustment
legacy accepted component
latest successful model
```

Contract-bound `.runtime/ai_lifecycle/datasets/` paths are allowed because they are bound by the R2 AD-U3 input contract and revalidated by hash.

## Bootstrap / Retraining Result

PASS.

The contract is:

```text
bootstrap_or_retraining: BOOTSTRAP
previous_generation_ref: null
```

The resolver does not require incremental revision, incremental business days, or incremental rows for bootstrap. It rejects retraining fallback through the bootstrap contract.

## Model Quality Deferred Observations

PASS.

The resolver does not guess or fill:

```text
minimum_training_rows
minimum_validation_rows
minimum_positive_labels
minimum_negative_labels
maximum_missing_ratio
```

Dry validation records observed dataset/split context only. Policy thresholds remain:

```text
policy_threshold_status: UNDECIDED
```

## Training Execution Status

PASS.

```text
Candidate training executed: false
Opportunity training executed: false
Calibration executed: false
Unified Generation created: false
Accepted Generation created: false
```

## Corrective Fixes

No corrective fix was required after implementation. This was a new AD-U3-A implementation of the R2-required resolver/adapter.

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

Broker write:

```text
0
```

## Failure Injection

PASS.

U3-A FI-1 through FI-18 passed:

```text
FI-1 dataset_dir direct input -> Rejected
FI-2 Dataset bytes changed -> BLOCK
FI-3 Dataset schema changed -> BLOCK
FI-4 Dataset lineage changed -> BLOCK
FI-5 Split bytes changed -> BLOCK
FI-6 Split recompute request -> Rejected
FI-7 Rolling Split Policy hash mismatch -> BLOCK
FI-8 Corporate Action Policy hash mismatch -> BLOCK
FI-9 Label-safe max overflow -> BLOCK
FI-10 future_* feature injection -> BLOCK
FI-11 Runtime path injection -> Rejected
FI-12 Paper / Broker / PnL path injection -> Rejected
FI-13 latest / glob discovery -> Rejected or unsupported
FI-14 Legacy fallback -> Rejected
FI-15 Previous generation forced into BOOTSTRAP -> Contract violation
FI-16 Deferred Model Quality autofill -> Rejected
FI-17 Resolver training execution -> Not performed
FI-18 Runtime / Trading mutation -> Runtime unchanged, Trading unchanged, Broker write 0
```

## Regression

PASS.

Commands:

```text
PYTHONPYCACHEPREFIX=/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/ai_lifecycle/ad_u3_dataset_input_resolver.py tests/ai_lifecycle/test_phase19_ad_u3_a_dataset_input_resolver.py
PYTHONPYCACHEPREFIX=/tmp/ai-fund-lab-v2-pycache python3 -m pytest tests/ai_lifecycle/test_phase19_ad_u3_a_dataset_input_resolver.py -q
PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/ai-fund-lab-v2-pycache python3 -m ai_fund_lab_v2.ai_lifecycle.ad_u3_dataset_input_resolver --contract reports/phase19_ad_r2_ad_u2_to_ad_u3_gate_review/ad_u3_dataset_input_contract_corrected.json --report-dir reports/phase19_ad_u3_a_contract_only_dataset_input_resolver --validate-only
PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/ai-fund-lab-v2-pycache python3 -m pytest tests/ai_lifecycle/test_phase19_ad_u3_a_dataset_input_resolver.py tests/ai_lifecycle/test_phase19_ad_u2_f_rolling_split_policy_approval.py tests/ai_lifecycle/test_phase19_ad_u2_d_corporate_action_policy_approval.py tests/ai_lifecycle/test_phase19_ad_u2_c_dataset_policy_blocker_closure.py tests/ai_lifecycle/test_phase19_ad_u2_b_dataset_revision_materialization.py tests/ai_lifecycle/test_phase19_ad_u2_a_dataset_to_split_foundation.py -q
```

Result:

```text
67 passed
```

## Evidence Paths

Evidence:

```text
reports/phase19_ad_u3_a_contract_only_dataset_input_resolver/
```

Summary:

```text
reports/phase_reports/phase19_ad_u3_a_contract_only_dataset_input_resolver.json
```

## Remaining Risks

Remaining AD-U3 work:

- Model Quality Policy thresholds are still undecided.
- Actual training must use this resolver output or a wrapper that rejects bypasses.
- Candidate / Opportunity training has not been executed.
- Unified Generation has not been created.

## Next Step

```text
PHASE19_AD_U3_MODEL_QUALITY_POLICY_READY
```

Next implementation unit should materialize Model Quality Policy before any Candidate or Opportunity training execution.
