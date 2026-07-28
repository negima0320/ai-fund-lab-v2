# Phase22-QC Strategy Status Contract Separation and Calculation Output Preservation Repair

## Executive Summary

Primary Judgment:

`PHASE22_QC_STATUS_CONTRACT_SEPARATION_REPAIRED_INPUT_MATERIALIZATION_REPAIR_REQUIRED`

Phase22-QC repaired the status contract mixing identified in Phase22-QB. Producer calculation result, validation status, artifact lifecycle, runtime consumer eligibility, human review status, and downstream calculation eligibility are now represented as separate fields on Strategy artifacts.

No Runtime Switch was performed. No broker connection or write was performed. No production or demo submit was performed. No new Historical Runtime test was executed.

## Root Cause

The previous contract collapsed `artifact_lifecycle_status=DRAFT` and `runtime_consumer_eligibility=NOT_ELIGIBLE` into source compatibility status `SOURCE_NOT_ELIGIBLE`. Downstream producers interpreted that as calculation ineligibility, causing REVIEW_REQUIRED propagation and unresolved targets to be represented as numeric zero.

## Canonical Status Contract

QC preserves these fields as independent axes:

- `producer_result_status`
- `producer_calculation_completed`
- `validation_status`
- `artifact_lifecycle_status`
- `runtime_consumer_eligibility`
- `human_review_status`
- `downstream_calculation_eligibility`
- `decision_resolution`
- `direct_reason_codes`
- `propagated_reason_codes`
- `lifecycle_reason_codes`
- `consumer_eligibility_reason_codes`

Lifecycle and consumer ineligibility continue to block production consumption, but do not by themselves invalidate shadow calculation.

## Before/After

Before:

- DRAFT / NOT_ELIGIBLE was folded into `SOURCE_NOT_ELIGIBLE`.
- Downstream artifacts received `upstream_review_required:SOURCE_NOT_ELIGIBLE`.
- Unresolved `target_position_count` became `0`.
- Unresolved `target_gross_exposure_ratio` became `0.0`.

After:

- Producer REVIEW maps to `SOURCE_REVIEW_REQUIRED`.
- Producer PASS with DRAFT / NOT_ELIGIBLE remains `COMPATIBLE_NOT_CONNECTED` for shadow reads.
- Production decision remains disabled.
- Unresolved numeric decisions are represented as `null` with `UNRESOLVED`.

## Artifact-by-Artifact Changes

Portfolio Policy:

- Runtime consumer ineligibility no longer forces producer REVIEW when calculation inputs are otherwise compatible.
- Status separation fields added.

Market Context / Corporate Event:

- Status separation fields added so Evidence Index pointers resolve for every Strategy artifact.
- Existing Corporate Event PARTIAL behavior is preserved.

Position Management:

- Portfolio Policy compatibility now distinguishes lifecycle-only ineligibility from producer review.
- Technical feature and Corporate Event blockers are preserved.

Portfolio Construction:

- Portfolio Policy and Position Management compatibility now avoid lifecycle-only `SOURCE_NOT_ELIGIBLE` propagation.
- Status separation fields added.

Capital Deployment:

- Portfolio Construction / Policy / PM compatibility now separates producer review from runtime consumer ineligibility.
- Status separation fields added.

Runtime Planning:

- Lifecycle and runtime consumer ineligibility are separated from producer calculation result.
- Runtime write, pending write, submit generation, and switch remain disabled.

Dynamic Position Count:

- Unresolved target count now emits `target_position_count=null`.
- Added `target_position_count_resolution=UNRESOLVED`.

Dynamic Cash Exposure:

- Unresolved cash and exposure targets now emit `null`.
- Added target resolution fields.

Position Sizing:

- Propagates unresolved DPC/DCE targets as `null`.
- Keeps configured safety-cap violation distinct from produced position overweight violations.

## Numeric Zero vs Unresolved Contract

`0` and `0.0` are now reserved for resolved explicit-zero decisions, such as true hard risk-off, emergency brake, market-closed/no-deployment, or zero investable candidates.

Unresolved decisions use `null` with `UNRESOLVED`.

## Source Reason Decomposition

The repaired taxonomy includes:

- `SOURCE_CALCULATION_INVALID`
- `SOURCE_VALIDATION_REVIEW_REQUIRED`
- `SOURCE_LIFECYCLE_DRAFT`
- `SOURCE_RUNTIME_CONSUMER_NOT_ELIGIBLE`
- `SOURCE_HUMAN_REVIEW_REQUIRED`
- `SOURCE_INPUT_MISSING`
- `SOURCE_PIT_INVALID`

Shadow calculation may continue for lifecycle draft, runtime consumer not eligible, and human review required. It must stop for calculation invalid, input missing, or PIT invalid.

## Shadow Calculation Eligibility

New field:

`downstream_calculation_eligibility`

Observed values:

- `CALCULATION_ALLOWED`
- `CALCULATION_ALLOWED_WITH_REVIEW`
- `CALCULATION_NOT_ALLOWED`

## Production Consumer Isolation

Production remains isolated:

- `artifact_lifecycle_status=DRAFT`
- `runtime_consumer_eligibility=NOT_ELIGIBLE`
- `active_runtime_consumer_eligibility=NO`
- `runtime_switch_performed=false`
- production fixture loading remains forbidden

## Observability

`strategy_evidence_index.json` now maps `status_contract_separation` pointers for each Strategy artifact.

## Synthetic Validation

Synthetic validation evidence is recorded in:

`reports/phase22_qc_strategy_status_contract_separation_and_calculation_output_preservation_repair/synthetic_validation.json`

Cases covered:

- PASS producer with DRAFT / NOT_ELIGIBLE remains shadow-readable.
- Producer REVIEW maps to `SOURCE_REVIEW_REQUIRED`.
- DPC unresolved count is null.
- DCE unresolved exposure is null.
- Position Sizing propagates unresolved targets without produced safety-cap violation.

## Test Results

PASS:

- `python3 -m compileall src/ai_fund_lab_v2/strategy`
- `python3 -m pytest tests/strategy` -> 138 passed
- targeted runtime/system-status tests -> 20 passed

## Remaining Blockers

Remaining blockers are intentionally preserved:

- QD: Price Volatility, Technical Features, and portfolio policy config lineage materialization.
- QE: Corporate Event PARTIAL coverage policy.

No fake default values were introduced.

## Operator Validation Requirements

After QD repair, operator should run historical shadow validation and confirm:

- Evidence index includes `status_contract_separation`.
- Unresolved numeric targets remain null.
- Explicit zero decisions are only emitted when explicitly resolved.
- Runtime Switch remains blocked until closure criteria are satisfied.

## Phase22 Closure Eligibility

Phase22 closure remains blocked.

QC repaired the status contract mixing, but input materialization and Corporate Event coverage review are still required before Phase22 closure or Phase23 handoff.

## Recommended Next Task

Recommended next task:

`Phase22-QD — Strategy Shadow Input Materialization Repair`
