# Phase28-D64 BASELINE_CURRENT_SEMANTICS_MISMATCH Root Cause Audit

## Primary Judgment

```text
PHASE28_D64_BASELINE_CURRENT_SEMANTICS_MISMATCH_ROOT_CAUSE_CONFIRMED
```

Mismatch classification:

```text
EVALUATION_SHADOW_DEFECT
```

Fresh 100BD Gate:

```text
CONDITIONAL
```

The next fresh 100BD can evaluate the D61 production ADD-capital repair effect, but the report must separate the known AI lifecycle baseline/current semantics review noise from active Runtime PASS/BLOCK judgment.

## Scope

Read-only root cause audit only.

No implementation, config change, schema change, threshold change, model change, Accepted Generation mutation, runtime artifact mutation, resume, fresh run, long historical run, or 100BD rerun was performed.

Target run:

```text
runtime-test-historical-smoke-20260809T010010445473Z
```

Evidence root:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260809T010010445473Z
```

## Direct Producer

The direct producer is:

```text
src/ai_fund_lab_v2/runtime_v2/ai_lifecycle_gates.py::evaluate_drift_gate
  -> _contract_compatibility
```

`evaluate_drift_gate` compares:

```text
baseline_prediction_contract
current_prediction_contract
```

with keys:

```text
prediction_metric_name
prediction_semantics
transformation_stage
calibration_applied
population_scope
```

When any compared key differs, `_contract_compatibility` emits:

```text
BASELINE_CURRENT_SEMANTICS_MISMATCH <key mismatches>
```

and `evaluate_drift_gate` materializes it as `prediction_distribution_drift / REVIEW_REQUIRED`.

## What Was Compared

Sample date:

```text
2023-04-03
```

Baseline contract from `ai_lifecycle_gate_decision.json`:

```json
{
  "prediction_metric_name": "opportunity_score",
  "prediction_semantics": "standardized_score",
  "transformation_stage": "runtime_baseline_expected_output_schema",
  "calibration_applied": true,
  "population_scope": "CandidateTop50_validation_window_aggregate"
}
```

Current Runtime contract:

```json
{
  "prediction_metric_name": "opportunity_score",
  "prediction_semantics": "runtime_opportunity_score",
  "transformation_stage": "accepted_generation_bound_imputer_scaler_model",
  "calibration_applied": false,
  "population_scope": "CandidateTop50_single_business_day"
}
```

Direct reason:

```text
BASELINE_CURRENT_SEMANTICS_MISMATCH
prediction_semantics:standardized_score!=runtime_opportunity_score;
transformation_stage:runtime_baseline_expected_output_schema!=accepted_generation_bound_imputer_scaler_model;
calibration_applied:True!=False;
population_scope:CandidateTop50_validation_window_aggregate!=CandidateTop50_single_business_day
```

The same family appears in all 100 business dates of the target run. Each inspected morning runtime manifest contains three related AI lifecycle drift/contract observations:

```text
prediction_distribution_drift / BASELINE_CURRENT_SEMANTICS_MISMATCH
feature_drift / BASELINE_CURRENT_FEATURE_SEMANTICS_MISMATCH
candidate_population_drift / BASELINE_CURRENT_POPULATION_SCOPE_MISMATCH
```

Evidence:

```text
reports/phase28_d64_baseline_current_semantics_mismatch_root_cause_audit/semantic_mismatch_matrix.json
```

## Baseline Side

Baseline evidence is produced by:

```text
src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py::_resolve_baseline
```

For this Phase19 Accepted Generation, the materialized Runtime baseline resolves through the Accepted Generation manifest and derives `prediction_semantics` from `expected_output_schema.opportunity_score`.

Observed baseline identity:

```text
accepted_bundle:7424901d02af21f8
```

Observed baseline semantics:

```text
standardized_score
runtime_baseline_expected_output_schema
calibration_applied = true
CandidateTop50_validation_window_aggregate
```

Architecture SoT says the Runtime baseline is operational health and drift comparison evidence only. It must not directly drive daily Runtime BUY decisions.

## Current Runtime Side

Current evidence is produced by:

```text
src/ai_fund_lab_v2/runtime_v2/lifecycle_evidence.py::_build_current_window_evidence
```

It reads the daily runtime Candidate/Opportunity payloads and derives the current prediction contract from the current Opportunity artifact.

Observed current Runtime Opportunity artifact:

```text
.runtime/runtime_state/buy_ai/2023-04-03/opportunity_rankings.json
```

Observed current semantics:

```text
prediction_metric_name = opportunity_score
prediction_semantics = runtime_opportunity_score
transformation_stage = accepted_generation_bound_imputer_scaler_model
calibration_applied = false
population_scope = CandidateTop50_single_business_day
```

The current artifact is bound to:

```text
Accepted Generation = phase19_aq_accepted_generation_641e6e313543f013
generation_binding_status = PASS
legacy_fallback_used = false
model_authority = Accepted Generation COMMITTED opportunity_member
model_hash_match = true
```

Evidence:

```text
reports/phase28_d64_baseline_current_semantics_mismatch_root_cause_audit/accepted_generation_and_current_binding.json
```

## Production Strategy Impact

Production Strategy affected:

```text
NO
```

Candidate Ranking affected:

```text
NO
```

PM decision affected:

```text
NO
```

D61 ADD repair affected:

```text
NO
```

Reason:

The mismatch is generated in AI lifecycle drift/observability evidence. The production Candidate/Opportunity artifacts themselves are generated with the committed Accepted Generation binding and no legacy fallback. Strategy consumers read the current runtime score semantics, not the baseline validation-window semantics.

Production Strategy sample on `2023-04-03`:

```text
Opportunity artifact status = PASS
BUY Quality status = PASS
Portfolio Construction status = PASS
Position Sizing status = PASS
```

Top symbols carried `runtime_opportunity_score` into Portfolio Construction with:

```text
authority = OPPORTUNITY_RANKING_AUTHORITY
canonical_field = runtime_opportunity_score
prediction_semantics = runtime_opportunity_score
transformation_stage = accepted_generation_bound_imputer_scaler_model
calibration_applied = false
```

Portfolio Construction explicitly validates `runtime_opportunity_score_authority.prediction_semantics == runtime_opportunity_score`. Position Sizing also fail-closes if a canonical runtime score carries a conflicting non-runtime semantic.

BUY Quality observes `calibration_applied=false` and applies the existing conservative signal reliability factor with reason:

```text
calibration_not_applied_raw_score_not_expected_return
```

That is current Runtime production behavior, not a result of the baseline/current comparator mismatch.

Evidence:

```text
reports/phase28_d64_baseline_current_semantics_mismatch_root_cause_audit/production_score_lineage_samples.json
```

## Runtime Review Propagation

Target run final evidence:

```text
final_runtime_judgment = PASS
production_planning_judgment = PASS
runtime_execution_judgment = PASS
acceptance_gate_judgment = REVIEW_REQUIRED
block_rule = NO_BLOCKING_CLOSE_RULE_TRIGGERED
```

Strategy Shadow evidence:

```text
strategy_shadow_judgment = REVIEW_REQUIRED
active_runtime_consumer_eligibility = YES
runtime_mutation_performed = false
runtime_switch_performed = false
```

D62 already separated `BASELINE_CURRENT_SEMANTICS_MISMATCH` from the Pending Safety false-positive family. D63 repaired the EMPTY-terminal Pending Safety false-positive and explicitly left this mismatch as a separate gap.

Evidence:

```text
reports/phase28_d64_baseline_current_semantics_mismatch_root_cause_audit/review_propagation_and_runtime_impact.json
```

## Root Cause

Root cause:

```text
AI lifecycle drift comparator compares unlike monitoring contracts.
```

The baseline side is a materialized Phase19 Runtime baseline contract over validation-window aggregate outputs:

```text
standardized_score
runtime_baseline_expected_output_schema
calibration_applied = true
CandidateTop50_validation_window_aggregate
```

The current side is a daily Runtime Opportunity artifact contract:

```text
runtime_opportunity_score
accepted_generation_bound_imputer_scaler_model
calibration_applied = false
CandidateTop50_single_business_day
```

Both can be valid in their own authority domains, but the drift gate currently treats this domain difference as a generic `BASELINE_CURRENT_SEMANTICS_MISMATCH` REVIEW_REQUIRED rather than a named non-blocking observability incompatibility or a like-for-like normalized drift comparison.

## Architecture Judgment

The current Runtime side follows the Strategy SoT score boundary:

```text
producer = Opportunity Ranking Authority
canonical field = runtime_opportunity_score
semantics = relative opportunity / expected edge evidence
```

The baseline side follows the Phase19 Runtime baseline role as operational health/drift evidence. Architecture SoT states the baseline must not directly drive daily Runtime BUY decisions.

Therefore this is not a Production Strategy semantic defect.

## Repair Boundary

Repair required before next D61 fresh 100BD:

```text
NO for production-effect measurement
YES for clean observability / acceptance closure
```

Minimal repair boundary:

```text
AI lifecycle baseline/current drift evidence normalization or comparator boundary
```

Candidate repair options:

1. Materialize a baseline monitoring contract that is comparable with `runtime_opportunity_score` and daily CandidateTop50 scope.
2. Teach the AI lifecycle drift gate to classify validation-window standardized baseline vs daily runtime score as a named non-blocking observability incompatibility instead of generic semantics mismatch.

Do not repair by changing:

```text
Candidate / Opportunity model inference
BUY Quality thresholds
Portfolio Construction
Position Sizing
PM
D61 ADD capital conversion
Accepted Generation artifacts
schema / config / thresholds
```

Evidence:

```text
reports/phase28_d64_baseline_current_semantics_mismatch_root_cause_audit/minimal_repair_boundary.json
```

## Final Judgment Fields

```text
Primary Judgment:
PHASE28_D64_BASELINE_CURRENT_SEMANTICS_MISMATCH_ROOT_CAUSE_CONFIRMED

Production Strategy affected:
NO

Candidate Ranking affected:
NO

PM decision affected:
NO

D61 ADD repair affected:
NO

Mismatch classification:
EVALUATION_SHADOW_DEFECT

Fresh 100BD Gate:
CONDITIONAL

Repair boundary proposal:
AI lifecycle baseline/current drift evidence normalization or comparator boundary.
Do not change production Strategy inference, PC/PS/PM, D61, thresholds, schema, config,
or Accepted Generation artifacts.
```

## Deliverables

```text
docs/phase_reports/phase28_d64_baseline_current_semantics_mismatch_root_cause_audit.md
reports/phase_reports/phase28_d64_baseline_current_semantics_mismatch_root_cause_audit.json
reports/phase28_d64_baseline_current_semantics_mismatch_root_cause_audit/
```
