# Phase19-AD-U2-B Dataset Revision and Rolling Split Materialization

## Final Judgment

```text
PHASE19_AD_U2_B_REVIEW_REQUIRED
PHASE19_AD_U2_NOT_COMPLETE
PHASE19_AD_U3_NOT_READY_INSUFFICIENT_NEW_DATA_OR_REVIEW_REQUIRED_INPUTS
```

Not performed:

```text
Candidate training
Opportunity training
Calibration
Accepted Decision
Runtime pointer
BUY restart
Broker write
```

Not declared:

```text
BUY_READY
PRODUCTION_READY
ACCEPTED_GENERATION_CREATED
RUNTIME_TRANSITION_COMPLETE
AUTONOMOUS_OPERATION_COMPLETE
```

## Dataset artifacts inspected

Inspected actual Common PIT Dataset bundles:

```text
.runtime/ai_lifecycle/datasets/candidate_ai/candidate_dataset_c8de026d3ea8aa4d
.runtime/ai_lifecycle/datasets/opportunity_ai/opportunity_dataset_fbadc8091a31486d
```

The evidence records dataset paths, dataset bytes hash, schema hash, row count, target date range, label-safe cutoff, source artifacts, trading calendar identity, listed issues identity, and previous revision status.

Evidence:

```text
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/current_dataset_artifact_inventory.json
```

## Dataset revisions materialized

Materialized first Phase19 dataset revision artifacts under:

```text
.runtime/ai_lifecycle/dataset_revisions/phase19_ad_u2_b/
```

Both Candidate and Opportunity revisions bind:

```text
dataset_hash
actual_dataset_hash
schema_hash
source_lineage_hash
target_date_min
target_date_max
label_safe_cutoff
target_horizon_business_days
policy_hash
trading_calendar_identity
listed_issues_identity
corporate_action_evidence_hash
previous_dataset_revision
```

These are bootstrap revisions because no prior materialized Phase19 dataset revision artifact exists.

Evidence:

```text
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/dataset_revision_policy.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/materialized_dataset_revisions.json
```

## Revision chain result

Result:

```text
PASS
```

The two materialized revisions are component-specific first revisions. `previous_dataset_revision = null` is allowed only as a bootstrap condition and is recorded with an explicit reason.

Failure injection covers:

```text
parent missing
self-cycle
two-node cycle
branch ambiguity
schema change without policy
bytes tamper
```

Evidence:

```text
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/dataset_revision_chain.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/dataset_revision_validation.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/failure_injection_results.json
```

## Corporate Action sufficiency

Result:

```text
PASS_WITH_LIMITATION
```

Explicitly evaluated:

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

No unknown item was treated as implicit PASS. Current evidence has adjusted price fields and listed issue history, but lacks standalone corporate action event evidence and explicit adjustment factor / code change / merger / restatement handling.

This blocks AD-U2 closure under the U2-B acceptance cases, because Corporate Action acceptance is not full `PASS`.

Evidence:

```text
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/corporate_action_sufficiency_contract.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/corporate_action_sufficiency_evidence.json
```

## Label-safe result

Result:

```text
REVIEW_REQUIRED
```

Formal J-Quants trading calendar re-evaluation found:

```text
latest_trading_date: 2026-06-26
target_horizon_business_days: 20
computed label-safe cutoff: 2026-05-29
metadata label-safe cutoff: 2026-06-04
dataset target max: 2026-05-15
```

The dataset target max itself is conservative, but the materialized metadata cutoff does not match the formal calendar-derived 20 business day cutoff. This is not accepted silently.

Evidence:

```text
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/label_safe_revalidation.json
```

## Data Sufficiency result

Result:

```text
REVIEW_REQUIRED
```

The evaluator did not force `SUFFICIENT`. The current materialized revision is a first bootstrap revision and has no previous accepted/evaluated revision comparison. Corporate Action is also `PASS_WITH_LIMITATION`, and label-safe is `REVIEW_REQUIRED`.

Evidence:

```text
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/data_sufficiency_evaluation.json
```

## Rolling Split policy

Result:

```text
REVIEW_REQUIRED_SPLIT_POLICY_MISSING
```

Known policy value:

```text
embargo_business_days = 20
target_horizon_business_days = 20
```

Missing SoT-defined values:

```text
training_window_business_days
validation_window_business_days
minimum_training_rows
minimum_validation_rows
```

Per U2-B instruction, these thresholds were not invented.

Evidence:

```text
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/rolling_split_policy.json
```

## Generated split boundaries

No valid rolling split boundaries were generated because the required split policy is incomplete.

Result:

```text
REVIEW_REQUIRED
```

Evidence:

```text
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/generated_versioned_splits.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/split_validation.json
```

## Candidate / Opportunity alignment

Result:

```text
PASS_WITH_LIMITATION
```

Candidate and Opportunity have component-specific revisions bound by a dataset input manifest. They share compatible trading calendar, listed issues, corporate action policy, and revision policy identities. They are not collapsed into a single revision ID.

Evidence:

```text
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/candidate_opportunity_dataset_alignment.json
```

## AD-U3 input contract

An AD-U3 dataset input manifest was written as a contract artifact only:

```text
generation_input_artifact = true
runtime_consumed = false
```

It binds Candidate revision, Opportunity revision, split placeholders, lineage compatibility, and policy hashes. It is not a Unified Generation and does not make AD-U3 ready.

Evidence:

```text
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/ad_u3_generation_input_contract.json
```

## Non-mutation

Result:

```text
PASS
```

Runtime and trading state hashes were unchanged. Broker write count is 0. No accepted generation, accepted decision, runtime pointer, BUY restart, or broker order was created.

Evidence:

```text
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/non_mutation_evidence.json
```

## Failure Injection

Covered:

```text
FI-1 Dataset bytes tampered
FI-2 Parent revision missing
FI-3 Revision self-cycle
FI-4 Revision two-node cycle
FI-5 Revision branch ambiguity
FI-6 Schema changed without policy
FI-7 Future corporate action leakage
FI-8 Missing delisting handling
FI-9 Label-safe per-symbol missing label
FI-10 Incremental rows but no new business day
FI-11 Split overlap
FI-12 Insufficient embargo
FI-13 Future validation end
FI-14 Split deterministic reproduction
FI-15 Partial artifact write
FI-16 AD-U2 execution non-mutation
```

Evidence:

```text
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/failure_injection_results.json
```

## Regression

Focused:

```text
28 passed
```

Full AD-U1 / U2 regression subset:

```text
50 passed, 2 sklearn convergence warnings in Phase18-D fixture training
```

Syntax:

```text
py_compile PASS with PYTHONPYCACHEPREFIX=/tmp
```

Evidence:

```text
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/test_results.json
```

## Changed files

U2-B implementation:

```text
src/ai_fund_lab_v2/ai_lifecycle/dataset_revision_materialization.py
tests/ai_lifecycle/test_phase19_ad_u2_b_dataset_revision_materialization.py
docs/phase_reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization.md
reports/phase_reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/
.runtime/ai_lifecycle/dataset_revisions/phase19_ad_u2_b/
```

Evidence:

```text
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/changed_files.json
```

## Evidence paths

```text
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/current_dataset_artifact_inventory.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/dataset_revision_policy.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/materialized_dataset_revisions.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/dataset_revision_chain.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/dataset_revision_validation.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/corporate_action_sufficiency_contract.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/corporate_action_sufficiency_evidence.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/label_safe_revalidation.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/data_sufficiency_evaluation.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/rolling_split_policy.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/generated_versioned_splits.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/split_validation.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/candidate_opportunity_dataset_alignment.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/ad_u3_generation_input_contract.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/non_mutation_evidence.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/failure_injection_results.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/test_results.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/changed_files.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/remaining_ad_u2_work.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/ad_u2_closure_decision.json
reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization/final_judgment.json
reports/phase_reports/phase19_ad_u2_b_dataset_revision_and_rolling_split_materialization.json
```

## Remaining AD-U2 work

```text
Resolve Corporate Action PASS_WITH_LIMITATION into PASS or explicit acceptance policy.
Resolve label-safe cutoff mismatch between dataset metadata and formal trading-calendar 20bd computation.
Define SoT-backed rolling split policy thresholds: training window, validation window, minimum training rows, minimum validation rows.
Regenerate/validate rolling split boundaries after policy definition.
Re-run Data Sufficiency with materialized previous/current revision comparison when a next revision exists.
```

## AD-U2 closure decision

```text
PHASE19_AD_U2_NOT_COMPLETE
```

This is Case C: `REVIEW_REQUIRED`.

## AD-U3 readiness

```text
PHASE19_AD_U3_NOT_READY_INSUFFICIENT_NEW_DATA_OR_REVIEW_REQUIRED_INPUTS
```
