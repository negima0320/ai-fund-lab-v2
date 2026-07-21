# Phase19-AD-U3-B Training Lifecycle Design and Model Quality Review

## Final Judgment

```text
PHASE19_AD_U3_B_TRAINING_LIFECYCLE_DESIGN_COMPLETE
PHASE19_AD_U3_MODEL_QUALITY_HUMAN_DECISION_REQUIRED
```

Forbidden declarations were not made:

```text
MODEL_QUALITY_POLICY_APPROVED
CANDIDATE_TRAINING_COMPLETE
OPPORTUNITY_TRAINING_COMPLETE
UNIFIED_GENERATION_CREATED
ACCEPTED_GENERATION_CREATED
AD_U3_COMPLETE
BUY_READY
PRODUCTION_READY
RUNTIME_TRANSITION_COMPLETE
```

## Existing Design Inventory

Reviewed:

```text
docs/02_architecture/autonomous_ai_operations_architecture.md
docs/02_architecture/runtime_architecture_v2.md
docs/01_requirements/phase_roadmap.md
docs/phase_reports/phase19_ad_u3_a_contract_only_dataset_input_resolver.md
reports/phase19_ad_u3_a_contract_only_dataset_input_resolver/
```

Existing SoT already covered Accepted Generation authority, retraining triggers, Candidate / Opportunity generation, Calibration, Validation, Runtime accepted-only authority, and failure continuity.

## Design Gap Analysis

Gaps were found. The design existed across multiple architecture sections and phase reports, but it was not consolidated as a permanent lifecycle SoT.

Key gaps:

- Why retraining exists beyond raw accuracy improvement.
- Learning vs non-learning component boundaries.
- Bootstrap vs Retraining lifecycle and trigger separation.
- CAPPED_EXPANDING_HYBRID approximately five-year semantics.
- Dataset freshness vs Accepted Generation freshness.
- Latest PIT inference feature vs latest Accepted Generation authority.
- Model Quality Policy draft and Human Review boundary.

## Created / Updated Architecture SoT

Created:

```text
docs/02_architecture/ai_training_and_generation_lifecycle.md
```

Updated references:

```text
docs/02_architecture/autonomous_ai_operations_architecture.md
docs/01_requirements/phase_roadmap.md
```

## Why Retraining Is Required

Retraining is required to produce a reproducible Generation bound to formal Dataset Revision, approved Rolling Split, policy hashes, schema hashes, lineage hashes, label-safe authority, and validation evidence.

Legacy AI artifacts are not sufficient as new generation authority because their Dataset / Split / Policy / Schema / Lineage binding is incomplete for the Phase19 Accepted Generation architecture.

## AI Component Inventory

Learning or regenerated components:

```text
Candidate AI
Opportunity AI
Calibration artifact
Validation result
Unified Generation artifact
```

Candidate AI selects investment candidates from the eligible universe.

Opportunity AI ranks and scores Candidate outputs as buy opportunities.

Calibration is a generation member and must be bound to model hashes when learned or fitted.

Validation checks quality, leakage, bias, compatibility, and acceptance readiness.

Unified Generation binds Dataset Revision, Versioned Split, Candidate, Opportunity, Calibration, Validation, Runtime Baseline, Policy Hashes, Schema, and Lineage.

## Training / Non-Training Boundary

Non-training components:

```text
Runtime State Machine
Safety Layer
BUY / SELL Guard
Order Planning
Submit
Execution
Broker Adapter
Ledger
Current / Pending
Accepted Generation Resolver
Lifecycle Gate
```

These are implementation, rule, state, or authority components. Training must not mutate them.

## Bootstrap Lifecycle

Bootstrap flow:

```text
J-Quants
-> Common PIT Dataset
-> Label-safe Dataset
-> Dataset Revision
-> Approved Versioned Split
-> Contract-only Training Resolver
-> Candidate Training
-> Opportunity Training
-> Calibration
-> Validation
-> Unified Generation Candidate
-> Human Review / Accepted Decision
-> Accepted Generation
-> Runtime Transition
```

Bootstrap uses:

```text
previous_generation_ref = null
incremental rows not required
incremental business days not required
```

## Retraining Lifecycle

Retraining occurs only after an Accepted Generation exists.

Trigger evidence may include:

```text
minimum incremental label-safe business days
minimum incremental rows
schema continuity
lineage continuity
data health
model drift
generation age
calendar-based trigger
```

Trigger values remain policy/Human Review controlled and were not guessed in U3-B.

## Five-Year Window Semantics

The approved policy is:

```text
CAPPED_EXPANDING_HYBRID
```

Meaning:

```text
Use available approved history.
Expand while history is short.
Cap at approximately five years once enough history exists.
Derive date boundaries from the formal Trading Calendar.
```

Approximately five years is not a hardcoded fixed business-day count.

## Dataset Update / AI Update Separation

Dataset updates can create Dataset Revisions without forcing an AI Generation update.

```text
Dataset update -> Dataset Revision -> Retraining Trigger not met -> current Accepted Generation continues
```

When triggers pass:

```text
Dataset update -> Retraining Trigger met -> Generation Candidate -> Validation -> Acceptance -> Runtime Transition
```

## J-Quants to Runtime Dataflow

Permanent flow:

```text
J-Quants Raw / Normalized Data
-> Common PIT Dataset
-> Label-safe Dataset
-> Dataset Revision
-> Approved Rolling Split
-> Contract-only Training Resolver
-> Candidate / Opportunity Training
-> Calibration
-> Validation
-> Unified Generation
-> Accepted Decision
-> Accepted Generation Resolver
-> Runtime Inference
-> Order Planning
-> Submit
-> Execution
```

## Latest Data Semantics

Runtime uses the latest formal Accepted Generation, not the latest raw Dataset.

Freshness concepts are separate:

```text
Training Dataset freshness
Inference Feature freshness
Accepted Generation freshness
Runtime State freshness
Broker State freshness
```

## Failure / Rollback Contract

If retraining, calibration, validation, or acceptance fails:

```text
Do not accept the new Generation.
Do not change Runtime pointer.
Keep current Accepted Generation.
```

BUY may continue only if current Accepted Generation gates still pass. SELL, Current, Valuation, Safety, and Ledger are independently evaluated.

## Candidate Quality Statistics

Main label:

```text
label__momentum_candidate_label
```

Training evidence:

```text
business_days: 852
rows: 3,496,880
distinct_issues: 4,588
positive_labels: 336,118
negative_labels: 3,160,762
positive_ratio: 0.096119
missing_feature_ratio: 0.05900997
invalid_numeric_count: 0
constant_feature_count: 0
```

Validation evidence:

```text
business_days: 222
rows: 934,105
positive_labels: 89,240
negative_labels: 844,865
missing_feature_ratio: 0.00475074
```

## Opportunity Quality Statistics

Main label:

```text
label__opportunity_positive_20d
```

Training evidence:

```text
business_days: 793
rows: 39,563
distinct_issues: 1,895
positive_labels: 17,858
negative_labels: 21,705
positive_ratio: 0.451381
missing_feature_ratio: 0.0
invalid_numeric_count: 0
constant_feature_count: 3
```

Validation evidence:

```text
business_days: 222
rows: 11,063
positive_labels: 4,915
negative_labels: 6,148
missing_feature_ratio: 0.0
```

## Threshold Options

Three options were prepared for each component:

```text
CONSERVATIVE
BALANCED
PERMISSIVE
```

Each option includes thresholds for:

```text
minimum_training_rows
minimum_validation_rows
minimum_positive_labels
minimum_negative_labels
maximum_missing_ratio
minimum_training_business_days
minimum_validation_business_days
minimum_distinct_issues
minimum_class_ratio
minimum_feature_coverage
maximum_constant_feature_ratio
maximum_invalid_numeric_ratio
```

## Recommended Policy

Recommended option:

```text
BALANCED
```

Reason:

BALANCED passes current bootstrap evidence for both Candidate and Opportunity while avoiding overly permissive weak-data thresholds and overly conservative false blocks.

This recommendation does not approve the policy.

## Human Decision Required Items

Human Review package:

```text
reports/phase19_ad_u3_b_training_lifecycle_and_model_quality_review/model_quality_policy_human_review.json
```

Draft policy:

```text
reports/phase19_ad_u3_b_training_lifecycle_and_model_quality_review/model_quality_policy_draft.json
```

Current state:

```text
policy_status: DRAFT_REVIEW_REQUIRED
reviewer: null
decision: HUMAN_REVIEW_REQUIRED
reviewed_policy_hash: null
```

## Prohibited Performance Input Audit

PASS.

Threshold options were based on Dataset structure, Feature count, Label distribution, Component purpose, Split windows, missingness, numeric validity, and issue coverage.

Not used:

```text
Backtest result
Backtest profit
Runtime result
Runtime PnL
Paper Trading result
Paper Ledger
Broker Snapshot
Broker position
cash
portfolio value
selected
bought
PM multiplier imitation
Test result
Audit result
Future information
Corporate Action event
Future adjustment
```

The annual return goal was not used as a threshold basis.

## Non-Mutation

PASS.

```text
Training executed: false
Candidate training complete: false
Opportunity training complete: false
Calibration executed: false
Unified Generation created: false
Accepted Generation created: false
Runtime pointer written: false
Broker write executed: false
```

## Failure Injection

PASS.

FI-1 through FI-12 were recorded. Backtest/Runtime/Paper/Broker performance leakage blocks, Candidate-to-Opportunity unconditional reuse requires review, undefined missing ratio invalidates draft, one-sided label distribution triggers quality guard, default-to-policy auto-promotion is rejected, draft policy cannot authorize training, Codex is not reviewer, training is not performed, and Runtime/Broker are unchanged.

## Regression

Regression evidence is recorded in:

```text
reports/phase19_ad_u3_b_training_lifecycle_and_model_quality_review/regression_results.json
```

## Evidence Paths

Evidence directory:

```text
reports/phase19_ad_u3_b_training_lifecycle_and_model_quality_review/
```

Summary:

```text
reports/phase_reports/phase19_ad_u3_b_training_lifecycle_and_model_quality_review.json
```

## Remaining Risks

Model Quality Policy remains unapproved. Candidate training, Opportunity training, Calibration, Unified Generation, Accepted Generation, and Runtime Transition remain unexecuted.

## Next Step

```text
PHASE19_AD_U3_MODEL_QUALITY_HUMAN_DECISION_REQUIRED
```

The user must approve or revise the Model Quality Policy draft before any training execution can be authorized.
