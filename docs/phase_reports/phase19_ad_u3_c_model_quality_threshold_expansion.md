# Phase19-AD-U3-C Model Quality Threshold Expansion

## Final Judgment

```text
PHASE19_AD_U3_C_MODEL_QUALITY_THRESHOLD_PACKAGE_READY
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

## Candidate Threshold Options

Candidate has three expanded options:

```text
CONSERVATIVE
BALANCED
PERMISSIVE
```

Balanced candidate thresholds:

```text
minimum_training_rows: 1,000,000
minimum_validation_rows: 250,000
minimum_training_business_days: 500
minimum_validation_business_days: 120
minimum_distinct_issues: 2,000
minimum_positive_labels: 50,000
minimum_negative_labels: 500,000
minimum_class_ratio: 0.03
minimum_feature_coverage: 0.90
maximum_missing_ratio: 0.10
maximum_constant_feature_ratio: 0.10
maximum_invalid_numeric_ratio: 0.0
```

Suggested additional Balanced review guards:

```text
minimum_test_business_days: 20
minimum_recent_holdout_business_days: 15
minimum_test_rows: 50,000
minimum_recent_holdout_rows: 50,000
minimum_validation_positive_labels: 25,000
minimum_validation_negative_labels: 250,000
unexpected_constant_feature_count: 0
critical_feature_missing: false
```

## Opportunity Threshold Options

Opportunity has three expanded options:

```text
CONSERVATIVE
BALANCED
PERMISSIVE
```

Balanced opportunity thresholds:

```text
minimum_training_rows: 20,000
minimum_validation_rows: 5,000
minimum_training_business_days: 500
minimum_validation_business_days: 120
minimum_distinct_issues: 1,000
minimum_positive_labels: 5,000
minimum_negative_labels: 5,000
minimum_class_ratio: 0.10
minimum_feature_coverage: 0.95
maximum_missing_ratio: 0.05
maximum_constant_feature_ratio: 0.20
maximum_invalid_numeric_ratio: 0.0
```

Suggested additional Balanced review guards:

```text
minimum_test_business_days: 20
minimum_recent_holdout_business_days: 15
minimum_test_rows: 1,000
minimum_recent_holdout_rows: 750
minimum_validation_positive_labels: 2,000
minimum_validation_negative_labels: 2,000
unexpected_constant_feature_count: 0
critical_feature_missing: false
```

## Current Margin Analysis

Balanced margin highlights:

Candidate:

```text
training rows: 3,496,880 observed / 1,000,000 threshold
validation rows: 934,105 observed / 250,000 threshold
positive labels: 336,118 observed / 50,000 threshold
negative labels: 3,160,762 observed / 500,000 threshold
missing ratio: 0.05900997 observed / 0.10 maximum
distinct issues: 4,588 observed / 2,000 threshold
```

Opportunity:

```text
training rows: 39,563 observed / 20,000 threshold
validation rows: 11,063 observed / 5,000 threshold
positive labels: 17,858 observed / 5,000 threshold
negative labels: 21,705 observed / 5,000 threshold
missing ratio: 0.0 observed / 0.05 maximum
distinct issues: 1,895 observed / 1,000 threshold
constant feature ratio: 0.09375 observed / 0.20 maximum
```

Both components also pass the Conservative option on current bootstrap data. This shows the Balanced values were not tuned merely to the current observed values.

## Threshold Evidence Basis

Every threshold is classified by evidence basis:

```text
ALGORITHM_REQUIREMENT
DATASET_STRUCTURE
LABEL_DISTRIBUTION
TEMPORAL_COVERAGE
ISSUE_COVERAGE
SCHEMA_COMPLETENESS
CALIBRATION_STABILITY
VALIDATION_STABILITY
OPERATIONAL_SAFETY
```

No threshold uses:

```text
Backtest profit
Annual return achieved
Runtime PnL
Paper PnL
Broker result
Portfolio value
```

## Missingness Assessment

Definition:

```text
missing feature cells / rows / feature_count
```

Scope:

```text
features only
identifiers excluded
targets excluded
before model training
before any imputation
```

Candidate training missing feature ratio:

```text
0.05900997
```

Candidate missingness is concentrated in price/volume-derived history features at:

```text
0.07671296 per affected feature
```

This is consistent with observed history gaps and should not be blocked by a zero-missing policy. The recommended policy keeps an overall component-specific maximum and proposes future per-feature / critical-feature guards.

Opportunity training missing feature ratio:

```text
0.0
```

## Constant Feature Assessment

Opportunity training constant features:

```text
feature__missing_flags_insufficient_history
feature__missing_flags_price
feature__missing_flags_volume
```

All are constant `False` in the current training window and classified as:

```text
EXPECTED_CONSTANT
```

They are missing-flag features and can be constant when no missingness is present. Non-whitelisted constant features should trigger review or block through `unexpected_constant_feature_count`.

## Label Sufficiency Assessment

Candidate:

```text
positive ratio: 0.096119
positive labels: 336,118
negative labels: 3,160,762
```

Candidate is imbalanced but not one-sided. It needs a component-specific minority-class guard.

Opportunity:

```text
positive ratio: 0.451381
positive labels: 17,858
negative labels: 21,705
```

Opportunity is much more balanced. Candidate class-ratio thresholds should not be blindly reused.

## Business-Day / Row / Issue Coverage

Business days, rows, and issue coverage are separate guards:

```text
business days: temporal diversity
rows: sample quantity
distinct issues: universe diversity
```

One cannot substitute for another.

## Bootstrap / Retraining Quality Boundary

Bootstrap:

```text
absolute first-generation quality floor
```

Retraining:

```text
same absolute quality floor
incremental trigger values out of scope
```

U3-C does not decide:

```text
minimum incremental label-safe business days
minimum incremental rows
minimum incremental labels
new issue coverage trigger
```

These remain:

```text
OUT_OF_SCOPE_RETRAINING_TRIGGER_POLICY
```

## Balanced Recommendation Audit

Recommended policy:

```text
BALANCED_WITH_COMPONENT_OVERRIDES
```

Reason:

Balanced leaves material margin under current data, accounts for Candidate all-universe imbalance and nonzero historical missingness, accounts for Opportunity's smaller but more balanced second-stage data, and avoids performance leakage.

## Human Review Comparison

Human-readable comparison:

```text
reports/phase19_ad_u3_c_model_quality_threshold_expansion/model_quality_human_review_comparison.md
```

Machine-readable comparison:

```text
reports/phase19_ad_u3_c_model_quality_threshold_expansion/model_quality_human_review_comparison.json
```

## Recommended Concrete Policy

Expanded draft:

```text
reports/phase19_ad_u3_c_model_quality_threshold_expansion/model_quality_policy_draft_expanded.json
```

Status:

```text
DRAFT_REVIEW_REQUIRED
```

The draft cannot authorize training.

## Human Decision Required Items

Expanded Human Review package:

```text
reports/phase19_ad_u3_c_model_quality_threshold_expansion/model_quality_policy_human_review_expanded.json
```

Current state:

```text
reviewer: null
decision: HUMAN_REVIEW_REQUIRED
reviewed_policy_hash: null
```

## Prohibited Performance Input Audit

PASS.

Thresholds were based on dataset structure, temporal coverage, issue coverage, label distribution, schema completeness, calibration stability, validation stability, and operational safety.

No threshold was based on realized returns, backtest profit, Runtime PnL, Paper PnL, Broker state, cash, holdings, selected/bought outcome, or portfolio value.

## Training Execution Status

PASS.

No execution:

```text
Candidate fit
Opportunity fit
Calibration fit
Prediction
Backtest
Unified Generation
Accepted Decision
Runtime pointer
BUY restart
Broker write
```

## Non-Mutation

PASS.

```text
Runtime unchanged
Trading State unchanged
Broker write 0
```

## Failure Injection

PASS.

FI-1 through FI-12 were recorded. Current-value thresholding triggers review, performance leakage blocks, Candidate-to-Opportunity unconditional threshold reuse requires review, unexplained Candidate missingness is invalid, unreviewed Opportunity constants require review, one-sided labels block, invalid numerics block, existing defaults are not auto-promoted, draft policy cannot authorize training, Codex is not reviewer, and Runtime/Broker remain unchanged.

## Regression

Regression evidence is recorded in:

```text
reports/phase19_ad_u3_c_model_quality_threshold_expansion/regression_results.json
```

## Evidence Paths

Evidence directory:

```text
reports/phase19_ad_u3_c_model_quality_threshold_expansion/
```

Summary:

```text
reports/phase_reports/phase19_ad_u3_c_model_quality_threshold_expansion.json
```

## Remaining Risks

The expanded Model Quality Policy remains unapproved. Training must not start until the user approves or revises the concrete thresholds.

## Next Step

```text
PHASE19_AD_U3_MODEL_QUALITY_HUMAN_DECISION_REQUIRED
```

The user should approve, reject, or modify the expanded Model Quality Policy package.
