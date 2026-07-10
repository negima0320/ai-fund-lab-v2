# Phase15-AO Candidate / Opportunity Controlled Schema Validation

Date: 2026-07-10

## Objective

Phase15-AO adds explicit schema validation and controlled `REVIEW_REQUIRED` handling at the regular Runtime BUY AI producer boundary.

Phase15-AN made Feature Refresh consumer-ready. Phase15-AO ensures Candidate AI and Opportunity AI also fail closed if schema mismatch reaches the AI producer.

Prohibited failure patterns closed:

```text
schema mismatch
↓
raw KeyError / unexpected HALT
```

```text
missing model feature
↓
NaN added
↓
inference continues
```

## Final Judgment

```text
PHASE15AO_CANDIDATE_OPPORTUNITY_CONTROLLED_SCHEMA_VALIDATION_COMPLETE
```

## Implementation Summary

Updated:

```text
src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py
```

Implemented:

- Candidate model feature list vs `candidate_features.parquet` validation before inference.
- Candidate schema mismatch becomes fixed-path `candidate_decisions.json` with `status=REVIEW_REQUIRED`.
- Candidate dependency failure writes fixed-path `opportunity_rankings.json` with `reason=candidate_dependency_review_required`.
- Opportunity model feature list vs candidate artifact + `opportunity_feature_input.parquet` validation before inference.
- Opportunity prefix policy validation: artifact columns are unprefixed; `feature__...` artifact columns are `REVIEW_REQUIRED`.
- Opportunity missing required feature blocks before `run_opportunity_inference()`, preventing hidden `NaN` continuation in the Runtime regular path.
- BUY AI manifest now includes Candidate / Opportunity schema evidence.

Updated:

```text
src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py
```

Report evidence now includes BUY AI schema status, missing columns, review flags, and review reasons in the Candidate / Opportunity sections.

## Candidate Producer Validation

Candidate validation now compares:

```text
model_payload["feature_columns"]
↓
feature__ prefix stripped
↓
candidate_features.parquet columns
```

Validation evidence:

```text
required_columns
present_columns
missing_columns
unexpected_columns
alias_risks
schema_status
feature_date
model_version
review_required
review_reason
```

Schema mismatch output:

```text
.runtime/runtime_state/buy_ai/<business_date>/candidate_decisions.json
```

Controlled artifact fields include:

```text
status=REVIEW_REQUIRED
reason=candidate_feature_schema_mismatch
candidate_count=0
review_required=true
review_reason=candidate_feature_schema_mismatch
missing_columns=[...]
alias_risks={...}
```

## Opportunity Dependency Artifact

If Candidate is `REVIEW_REQUIRED`, Opportunity inference is not executed.

Instead, Runtime writes:

```text
.runtime/runtime_state/buy_ai/<business_date>/opportunity_rankings.json
```

with:

```text
status=REVIEW_REQUIRED
reason=candidate_dependency_review_required
ranking_count=0
rankings=[]
candidate_dependency_status=REVIEW_REQUIRED
```

This distinguishes intentional dependency stop from missing artifact.

## Opportunity Schema Validation

Opportunity validation now checks before inference:

- Candidate artifact status
- Opportunity feature artifact existence
- required model features
- present model-mapped features
- missing required features
- unexpected prefixed artifact columns
- prefix convention
- double-prefix risk

Canonical prefix contract:

```text
Artifact columns are unprefixed.
Consumer maps to model-level feature__ columns exactly once.
```

Schema mismatch output:

```text
status=REVIEW_REQUIRED
ranking_count=0
rankings=[]
review_reason=opportunity_feature_schema_mismatch
```

or:

```text
review_reason=opportunity_feature_prefix_policy_violation
double_prefix_detected=true
```

## Morning Consumer Contract

Runtime CLI already stops before Morning Planning when BUY AI returns `REVIEW_REQUIRED`.

Verified behavior:

```text
Candidate schema failure
↓
candidate_opportunity_ai_runtime_producer = REVIEW_REQUIRED
↓
final_state = REVIEW_REQUIRED
↓
morning_ai_planning_pending_pipeline is not executed
↓
no OrderPlan generated
```

## Manifest Evidence

BUY AI manifest now includes:

```text
candidate_schema_status
candidate_required_columns
candidate_present_columns
candidate_missing_columns
candidate_unexpected_columns
candidate_alias_risks
candidate_review_required
candidate_review_reason

opportunity_schema_status
opportunity_required_columns
opportunity_present_columns
opportunity_missing_columns
opportunity_unexpected_columns
opportunity_prefix_policy
opportunity_double_prefix_detected
opportunity_review_required
opportunity_review_reason
```

## Regression

Added:

```text
tests/runtime_v2/test_phase15ao_candidate_opportunity_controlled_schema_validation.py
```

Coverage:

- Candidate missing required model feature -> controlled `REVIEW_REQUIRED`
- Candidate legacy alias risk is enumerated
- Candidate raw `KeyError` does not escape
- Candidate dependency failure writes Opportunity dependency artifact
- Opportunity prefixed artifact column -> `REVIEW_REQUIRED`
- Opportunity missing required model feature -> `REVIEW_REQUIRED`
- Opportunity missing feature does not continue through hidden `NaN`
- Morning stops before Planning on BUY AI schema failure

Retention updates:

- `tests/runtime_v2/test_phase15k_morning_policy_propagation_hidden_policy_removal.py` fixture updated to satisfy Phase15-AN/AO canonical feature readiness.

## Verification

Executed:

```text
python3 -m pytest tests/runtime_v2/test_phase15ao_candidate_opportunity_controlled_schema_validation.py tests/runtime_v2/test_phase15ag_candidate_opportunity_runtime_connection.py tests/runtime_v2/test_phase15an_feature_consumer_readiness.py tests/runtime_v2/test_phase15af_position_management_runtime_connection.py tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase15r_report_notification_reason_propagation.py tests/runtime_v2/test_phase14e36_feature_date_contract_carryover_policy.py
```

Result:

```text
38 passed
```

Executed:

```text
env PYTHONPYCACHEPREFIX=/private/tmp/pycache_phase15ao python3 -m compileall src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py tests/runtime_v2/test_phase15ao_candidate_opportunity_controlled_schema_validation.py tests/runtime_v2/test_phase15k_morning_policy_propagation_hidden_policy_removal.py
```

Result:

```text
PASS
```

## Remaining Scope

Not included in Phase15-AO:

- AI model changes
- retraining
- feature value generation changes
- ranking logic changes
- Runtime Data Readiness Gate
- PM derived/defaulted field manifesting
- Pending lifecycle remediation

## Prohibited Actions Confirmation

This phase did not perform:

- AI model change
- retraining
- feature value fabrication
- required feature default supplementation
- ranking logic change
- Morning real operation execution
- Submit
- Execution
- Broker Write
- order
- Notification real send
- launchd change
- Current edit

## Completion String

```text
PHASE15AO_CANDIDATE_OPPORTUNITY_CONTROLLED_SCHEMA_VALIDATION_COMPLETE
```
