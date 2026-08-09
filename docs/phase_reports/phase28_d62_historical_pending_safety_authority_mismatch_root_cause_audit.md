# Phase28-D62 Historical Pending Safety REVIEW_REQUIRED Root Cause Audit

## Primary Judgment

```text
PHASE28_D62_HISTORICAL_PENDING_SAFETY_FALSE_POSITIVE_CONFIRMED
```

D62 is read-only. No Production Runtime, Strategy, Safety, Pending lifecycle, schema, threshold, config, runtime artifact, fresh-run, resume, or long historical execution was changed or executed.

Target run:

```text
runtime-test-historical-smoke-20260809T010010445473Z
```

## Direct Root Cause

`historical_pending_safety_authority_mismatch` is produced by:

```text
src/ai_fund_lab_v2/runtime_v2/data_readiness.py::_historical_pending_safety_authority
```

The function correctly identifies:

```text
pending_lifecycle_state = EMPTY
pending_consumed = false
no_action_terminal = true
```

but still compares EMPTY terminal pending artifacts against historical safety binding fields:

```text
environment
target_session_date
safety_context.runtime_test_run_id
safety_context.runtime_test_profile_id
safety_context.runtime_test_evidence_root
safety_context.safety_authority
safety_context.safety_business_date
safety_context.safety_decision
safety_context.safety_policy_version
safety_context.safety_source
```

That comparison is too strict for a normal EMPTY/no-action terminal slot.

## Contract Finding

Runtime v2 architecture explicitly defines the EMPTY contract:

```text
state/status == EMPTY
active_pending == false
items == []
```

as a No-Action terminal that does not consume an order. It also states that an EMPTY slot is not Submit order authority and does not require:

```text
environment
target_session_date
intended_submit_date
safety_context
Runtime Test identity
```

Contract reference:

```text
docs/02_architecture/runtime_architecture_v2.md:1075-1081
```

Therefore the observed mismatch is not a real Safety / Pending lifecycle violation for the target run. It is an observability / validation false-positive.

## Producer / Validator Chain

Producer:

```text
src/ai_fund_lab_v2/runtime_v2/data_readiness.py:2290-2396
_historical_pending_safety_authority
```

It produces:

- `pending_lifecycle_state`
- `pending_consumed`
- `no_action_terminal`
- `safety_context`
- `target_session_date`
- `sell_continuation_allowed`
- `failed_attempt_pending_retry`
- `mismatched_fields`
- `status = REVIEW_REQUIRED`
- `reason = historical_pending_safety_authority_mismatch`

Validator / consumer:

```text
src/ai_fund_lab_v2/runtime_v2/data_readiness.py:2185-2287
_pending_readiness_payload
```

For `state == EMPTY and active_pending == false`, Pending readiness returns:

```text
status = READY
reason = pending_slot_empty
```

but carries nested `historical_pending_safety_authority` evidence with `REVIEW_REQUIRED`.

Safety-side consumer:

```text
src/ai_fund_lab_v2/runtime_v2/data_readiness.py:1780-1865
src/ai_fund_lab_v2/runtime_v2/data_readiness.py:2021-2095
```

Daily neutral safety can still resolve READY for EMPTY pending via `_pending_allows_daily_neutral_safety`, while the nested pending authority evidence remains REVIEW_REQUIRED.

Propagation:

```text
_historical_pending_safety_authority
-> data_readiness components.pending.historical_pending_safety_authority
-> data_readiness components.safety.pending_safety_authority
-> data_readiness/runtime_manifest.json
-> morning/runtime_manifest.json
-> morning/morning_manifest.json
```

The same logical event is copied into multiple manifest locations.

## 100BD Frequency Classification

Logical event count:

```text
57
```

File occurrence count:

```text
342
```

All 57 logical events are Case A:

```text
CASE_A_NORMAL_EMPTY_TERMINAL_CANDIDATE = 57
CASE_B_ACTIVE_OR_CONSUMED = 0
CASE_C_FAILED_OR_INCOMPLETE_ATTEMPT = 0
CASE_D_SELL_CONTINUATION_REQUIRES_SAFETY = 0
```

Logical attribute counts:

```text
EMPTY + no_action_terminal=true = 57
pending_consumed=true = 0
incomplete_blocked_failed_attempt=true = 0
review_required_empty_unscoped_failed_attempt=true = 0
sell_continuation_allowed=true = 0
safety_context present = 56
safety_context empty = 1
safety_decision=NEUTRAL = 56
safety_decision non-NEUTRAL = 1
```

Manifest duplication:

```text
confirmed
max file copies per logical event = 6
```

This confirms the run does not contain a mixed set of real active pending safety violations under this reason. It contains repeated copies of normal EMPTY terminal false-positive evidence.

## Representative EMPTY Case

Representative target:

```text
daily/2023-04-03/data_readiness/runtime_manifest.json
```

Observed:

```text
pending_lifecycle_state = EMPTY
pending_consumed = false
no_action_terminal = true
failed_attempt_pending_retry.pending_artifact_attempt_status = EMPTY
failed_attempt_pending_retry.incomplete_blocked_failed_attempt = false
failed_attempt_pending_retry.review_required_empty_unscoped_failed_attempt = false
sell_continuation_allowed = false
safety_context = {}
target_session_date = ""
status = REVIEW_REQUIRED
reason = historical_pending_safety_authority_mismatch
```

This is Contract Case A and should not be classified as a real active Pending Safety violation.

## Final REVIEW_REQUIRED Propagation

The run final summary says:

```text
final_judgment = REVIEW_REQUIRED
runtime_status = COMPLETED
runtime_judgment = PASS
final_runtime_judgment = PASS
runtime_execution_judgment = PASS
block_rule = NO_BLOCKING_CLOSE_RULE_TRIGGERED
block_reason = ""
```

The direct close reason is:

```text
strategy_shadow_review_required_non_blocking
```

Final close evidence:

```text
close_authority_classification.review_reasons = ["strategy_shadow_review_required_non_blocking"]
strategy_review_required_dates = [
  "2023-04-25",
  "2023-05-01",
  "2023-05-17",
  "2023-06-05",
  "2023-06-07",
  "2023-06-09",
  "2023-06-23",
  "2023-08-16"
]
```

Therefore:

```text
historical_pending_safety_authority_mismatch did not directly block Runtime execution.
It is nested review/observability evidence.
The final REVIEW_REQUIRED is directly driven by strategy shadow review, not active Pending Safety.
```

It should still be repaired because it pollutes manifests with false REVIEW_REQUIRED evidence.

## BASELINE_CURRENT_SEMANTICS_MISMATCH Separation

The target run also contains:

```text
BASELINE_CURRENT_SEMANTICS_MISMATCH
```

This is a separate strategy/evaluation review family. It appears in 200 files in the existing run evidence and aligns with strategy shadow review-required close behavior. D62 does not repair it.

D62 classification:

```text
historical_pending_safety_authority_mismatch = Pending EMPTY terminal false-positive
BASELINE_CURRENT_SEMANTICS_MISMATCH = separate strategy/evaluation review cause
final REVIEW_REQUIRED = strategy shadow review_required_non_blocking
```

## Harm Assessment

BUY harm:

```text
NO_DIRECT_BUY_EXECUTION_HARM_CONFIRMED
```

Evidence:

```text
runtime_execution_judgment = PASS
final_runtime_judgment = PASS
```

SELL harm:

```text
NO_DIRECT_SELL_EXECUTION_HARM_CONFIRMED
```

Evidence:

```text
sell_continuation_allowed=true logical mismatch events = 0
```

Pending Safety harm:

```text
NO_ACTIVE_PENDING_SAFETY_WEAKENING_CONFIRMED
```

Evidence:

```text
CASE_B / CASE_C / CASE_D = 0
```

## Production-Common Defect Classification

This is a Production-common validator defect in `data_readiness.py`, observed through Historical EMPTY pending semantics.

It is not a reason to weaken Safety. The repair must be contract-aware:

- Allow only normal EMPTY/no-action terminal to avoid safety binding mismatch.
- Preserve fail-closed behavior for active Pending.
- Preserve fail-closed behavior for consumed/carry-forward Pending.
- Preserve failed/incomplete attempt retry handling.
- Preserve BUY-item-scoped SELL continuation safety requirements.

## Minimal Repair Target

Primary target:

```text
src/ai_fund_lab_v2/runtime_v2/data_readiness.py
_historical_pending_safety_authority
```

Minimal behavior:

```text
If state == EMPTY
and active_pending == false
and items == []
and pending_consumed == false
and no_action_terminal == true
and failed_attempt_pending_retry.retry_input_ineligible == false
and sell_continuation_allowed == false

then do not require safety_context, target_session_date, environment,
or Runtime Test identity binding for pending safety authority.
```

Do not modify:

- Submit Guard
- Pending writer
- BUY lifecycle
- SELL lifecycle
- Safety rules for active Pending
- schema
- config
- threshold

## Regression Candidates

Case A:

- EMPTY / inactive / no items / no safety_context / no target_session_date returns READY or neutral no-action evidence, not `historical_pending_safety_authority_mismatch`.
- EMPTY with NEUTRAL safety context remains READY.

Case B:

- APPROVED active Pending without required safety binding remains REVIEW_REQUIRED.
- CONSUMED carry-forward with mismatched business date remains REVIEW_REQUIRED.

Case C:

- BLOCKED or REVIEW_REQUIRED empty unscoped failed attempt remains handled by failed-attempt retry classification, not generic EMPTY skip.

Case D:

- BUY_ITEM_SCOPED_REVIEW with `sell_continuation_allowed=true` still requires same-business-date historical safety authority.

Manifest:

- Repeated manifest copies should not be counted as distinct logical failures.

## D63 Gate

```text
APPROVED
```

Recommended next phase:

```text
Phase28-D63 Production-common Pending Safety EMPTY-terminal Judgment Repair
```

## Deliverables

- `reports/phase28_d62_historical_pending_safety_authority_mismatch_root_cause_audit/100bd_logical_event_aggregation.json`
- `reports/phase28_d62_historical_pending_safety_authority_mismatch_root_cause_audit/file_occurrence_aggregation.json`
- `reports/phase28_d62_historical_pending_safety_authority_mismatch_root_cause_audit/representative_empty_cases.json`
- `reports/phase28_d62_historical_pending_safety_authority_mismatch_root_cause_audit/non_empty_exception_cases.json`
- `reports/phase28_d62_historical_pending_safety_authority_mismatch_root_cause_audit/producer_validator_locations.json`
- `reports/phase28_d62_historical_pending_safety_authority_mismatch_root_cause_audit/propagation_chain.json`
- `reports/phase28_d62_historical_pending_safety_authority_mismatch_root_cause_audit/baseline_current_semantics_separation.json`
- `reports/phase28_d62_historical_pending_safety_authority_mismatch_root_cause_audit/contract_references.json`
- `reports/phase28_d62_historical_pending_safety_authority_mismatch_root_cause_audit/regression_candidate_matrix.json`
- `reports/phase28_d62_historical_pending_safety_authority_mismatch_root_cause_audit/minimal_repair_scope.json`
- `reports/phase_reports/phase28_d62_historical_pending_safety_authority_mismatch_root_cause_audit.json`

## Execution Flags

```text
Implementation changed = NO
Config changed = NO
Schema changed = NO
Threshold changed = NO
Runtime mutated = NO
Resume executed = NO
Fresh run executed = NO
Long Historical executed = NO
```
