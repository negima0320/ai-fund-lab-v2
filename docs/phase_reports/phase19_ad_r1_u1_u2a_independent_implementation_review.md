# Phase19-AD-R1 U1 / U2-A Independent Implementation Review

## Final Judgment

```text
PHASE19_AD_R1_PASS_AFTER_CORRECTIVE_FIX
PHASE19_AD_U2_CONTINUATION_READY
```

Not declared:

```text
AD_U2_COMPLETE
AD_U3_READY
BUY_READY
PRODUCTION_READY
ACCEPTED_GENERATION_CREATED
RUNTIME_TRANSITION_COMPLETE
AUTONOMOUS_OPERATION_COMPLETE
```

## Review scope

Reviewed:

```text
AD-U1 Bootstrap and Authority Unification
AD-U2-A Dataset-to-Split Foundation
```

Status entering this review:

```text
AD-U1: PHASE19_AD_U1_COMPLETE_SAFE_EMPTY_STATE
AD-U2-A: PHASE19_AD_U2_A_DATASET_FOUNDATION_PASS
AD-U2: NOT_COMPLETE
AD-U3: NOT_READY
```

This review used code, call graph, artifact schema, tests, and generated evidence. Existing Phase reports were not accepted as proof without checking implementation and runtime artifacts.

Evidence:

```text
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/review_scope.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/architecture_to_implementation_matrix.json
```

## Critical / High findings

```text
None
```

Medium findings were corrected inside AD-R1:

```text
AD-R1-001 Label-safe business-day horizon and per-symbol label availability guard
AD-R1-002 Dataset revision bytes binding and self-cycle rejection
AD-R1-003 Versioned split policy hash / embargo / future-boundary validation
```

Remaining low limitation:

```text
AD-R1-004 Corporate Action integrity remains partial and must not be treated as fully accepted.
```

Evidence:

```text
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/findings.json
```

## Authority review

Result:

```text
PASS
```

Normal BUY path:

```text
run_daily_operation.py morning job
-> produce_buy_ai_decisions
-> resolve_accepted_generation
-> AcceptedGenerationResolution
-> accepted generation member artifact paths
-> Candidate / Opportunity producers
```

If the accepted generation pointer is missing or non-`COMMITTED`, BUY produces no signals and blocks before legacy artifact resolution.

Additional AD-R1 test proves Lifecycle Gate receives the same `AcceptedGenerationResolution` instance created by the BUY producer:

```text
test_phase19_ad_r1_lifecycle_gate_receives_same_resolution_instance
```

Evidence:

```text
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/runtime_authority_call_graph.json
```

## Legacy reachability

Result:

```text
PASS_WITH_LIMITATION
```

Normal `.runtime` BUY path does not reach:

```text
CANDIDATE_AI_SET
OPPORTUNITY_AI_SET
manual candidate_model_path
manual opportunity_model_path
promotion_candidates
latest / mtime selection
```

Explicit model paths remain allowed only for isolated non-default test roots. AD-R1 added a normal-runtime test proving explicit model paths do not bypass the accepted generation resolver when `runtime_root=.runtime`.

Evidence:

```text
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/legacy_reachability_review.json
```

## Accepted vs COMMITTED separation

Result:

```text
PASS
```

AD-U1 Bootstrap materialization can create an accepted manifest and accepted decision, but keeps:

```text
runtime_transition_state = NOT_COMMITTED
runtime_pointer_written = false
```

Runtime authority is separate and requires:

```text
runtime_state/accepted_buy_ai_bundle.json
transaction_state = COMMITTED
```

Evidence:

```text
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/accepted_vs_committed_semantics.json
```

## Safe Empty State review

Result:

```text
PASS_WITH_LIMITATION
```

Accepted Generation absent:

```text
BUY planning: blocked before planning
BUY signals: empty
BUY pending creation: none
BUY submit: blocked by no pending BUY
SELL: lifecycle gate does not block SELL
Current / valuation / safety / report: not mutated by AD-U1 / AD-U2-A validators
```

Limitation: full end-to-end notification semantics under every mode remain covered by existing Runtime paths, not newly re-run as production execution in AD-R1.

Evidence:

```text
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/safe_empty_state_runtime_review.json
```

## Bootstrap integrity

Result:

```text
PASS
```

Verified:

```text
canonical stable JSON hashing
aggregate_hash excludes only aggregate_hash itself
hash covers generation, dataset lineage, split, members, calibration, validation, runtime baseline, freshness, policy versions, source commit, effective_from
human review binds reviewed_hash to current generation hash
reviewer and APPROVE decision required
accepted manifest remains NOT_COMMITTED
atomic_write_json uses temp file, fsync, and replace
```

Evidence:

```text
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/bootstrap_hash_and_review_integrity.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/bootstrap_compatibility_generality.json
```

## Dataset revision integrity

Result:

```text
PASS_AFTER_CORRECTIVE_FIX
```

Corrective fixes:

```text
validate_dataset_revision_binding
revision_not_self_referential
policy_hash in DataSufficiencyPolicy
```

`dataset_hash` is now independently rechecked against actual `dataset.parquet` bytes when validating a loaded bundle revision.

Evidence:

```text
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/dataset_revision_integrity_review.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/revision_chain_integrity_review.json
```

## Label-safe review

Result:

```text
PASS_AFTER_CORRECTIVE_FIX
```

Corrective fixes:

```text
Trading Calendar business-day horizon check
target_horizon_business_days binding
per-symbol unavailable label row guard
```

Current actual Opportunity dataset still evaluates label-safe as `PASS` when formal J-Quants trading calendar dates are supplied.

Evidence:

```text
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/label_safe_business_day_review.json
```

## Data Sufficiency review

Result:

```text
PASS_AFTER_CORRECTIVE_FIX
```

Policy logic is explicitly:

```text
minimum_incremental_business_days AND minimum_incremental_rows
```

Current actual decision remains:

```text
INSUFFICIENT
NO_RETRAIN_INSUFFICIENT_NEW_DATA
```

Reason: there is no new accepted/evaluated dataset revision chain and no minimum incremental data evidence in AD-U2-A.

Evidence:

```text
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/data_sufficiency_review.json
```

## Rolling Split review

Result:

```text
PASS_AFTER_CORRECTIVE_FIX
```

Corrective fixes:

```text
policy_hash
embargo_business_days
target_horizon_business_days
trading_calendar_identity
embargo gap validation
validation_end <= label_safe max
generation_input_artifact = true
runtime_consumed = false
```

Limitation: AD-U2-A validates the versioned split contract. Rolling boundary computation from a newly materialized dataset revision remains later AD-U2 work.

Evidence:

```text
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/rolling_split_integrity_review.json
```

## Corporate Action gap

Result:

```text
PASS_WITH_LIMITATION
```

AD-U2-A did not claim full Corporate Action acceptance. The current basis is adjusted quote lineage and `REUSE_WITH_EXTENSION`.

Still required later:

```text
split adjustment
reverse split
merger
stock transfer
delisting
code change
adjustment factor revision
point-in-time availability
restatement
```

Evidence:

```text
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/corporate_action_gap_review.json
```

## Non-mutation

Result:

```text
PASS
```

AD-R1 hashed the Runtime state files before and after resolver / validator calls. Hashes matched.

Confirmed:

```text
broker_write_count = 0
runtime_pointer_written = false
accepted_generation_created = false
```

Evidence:

```text
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/non_mutation_evidence.json
```

## Corrective fixes

Code:

```text
src/ai_fund_lab_v2/ai_lifecycle/dataset_to_split.py
```

Tests:

```text
tests/ai_lifecycle/test_phase19_ad_u2_a_dataset_to_split_foundation.py
tests/runtime_v2/test_phase19_ad_u1_a_accepted_generation_resolver.py
```

No training, calibration, dataset materialization, Accepted Decision, Runtime pointer, BUY restart, or Broker write was executed.

## Tests / Regression

Additional review tests:

```text
21 passed
```

Final regression command:

```text
python3 -m pytest tests/runtime_v2/test_phase19_ad_u1_a_accepted_generation_resolver.py tests/ai_lifecycle/test_phase19_ad_u1_b_bootstrap_generation.py tests/ai_lifecycle/test_phase19_ad_u1_c_bootstrap_compatibility.py tests/ai_lifecycle/test_phase19_ad_u2_a_dataset_to_split_foundation.py tests/ai_lifecycle/test_phase18b_common_pit_dataset_rebuild.py tests/ai_lifecycle/test_phase18d_training_pipeline.py
```

Result:

```text
43 passed, 2 sklearn convergence warnings in Phase18-D fixture training
```

Syntax:

```text
py_compile PASS with PYTHONPYCACHEPREFIX=/tmp
```

Evidence:

```text
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/additional_test_results.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/regression_results.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/test_quality_review.json
```

## Changed files

Evidence:

```text
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/changed_files.json
```

AD-R1 files:

```text
docs/phase_reports/phase19_ad_r1_u1_u2a_independent_implementation_review.md
reports/phase_reports/phase19_ad_r1_u1_u2a_independent_implementation_review.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/
```

Corrective fix files:

```text
src/ai_fund_lab_v2/ai_lifecycle/dataset_to_split.py
tests/ai_lifecycle/test_phase19_ad_u2_a_dataset_to_split_foundation.py
tests/runtime_v2/test_phase19_ad_u1_a_accepted_generation_resolver.py
```

## Evidence paths

```text
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/review_scope.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/architecture_to_implementation_matrix.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/runtime_authority_call_graph.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/accepted_vs_committed_semantics.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/legacy_reachability_review.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/safe_empty_state_runtime_review.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/bootstrap_hash_and_review_integrity.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/bootstrap_compatibility_generality.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/dataset_revision_integrity_review.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/revision_chain_integrity_review.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/label_safe_business_day_review.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/data_sufficiency_review.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/rolling_split_integrity_review.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/corporate_action_gap_review.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/non_mutation_evidence.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/test_quality_review.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/additional_test_results.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/regression_results.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/findings.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/changed_files.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/ad_u2_continuation_decision.json
reports/phase19_ad_r1_u1_u2a_independent_implementation_review/final_judgment.json
reports/phase_reports/phase19_ad_r1_u1_u2a_independent_implementation_review.json
```

## AD-U2 continuation decision

```text
PHASE19_AD_U2_CONTINUATION_READY
```

Remaining AD-U2 work:

```text
materialized new dataset revision chain
explicit corporate action sufficiency acceptance
rolling boundary generation from current dataset revision
```
