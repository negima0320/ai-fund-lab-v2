# Phase32-BD - Run-Scoped Feature-Date Resume Entry-Gate Read-Only Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260831T003243720082Z`
- Current continuation point: `2023-10-12:data_readiness`
- Phase mode: READ-ONLY audit.
- Commands not executed in BD: `runtime_test resume`, resume dry-run, recover, replay, fresh-run, or any mutating runtime command.
- Source/config changes in BD: none.
- 2023-10-11 replay/alteration: none.

## Current Authoritative Run State

From `run_state.json`:

- `status`: `HALT`
- `next_job`: `2023-10-12:data_readiness`
- halted job: `data_readiness`
- halted exit code: `20`
- completed tail: `... 2023-10-06, 2023-10-10, 2023-10-11`
- `2023-10-12` is not completed.
- `2023-10-12/submit` does not exist.
- `2023-10-12/execution` does not exist.

2023-10-11 must remain preserved. BD found no reason to replay or alter 2023-10-11, and no evidence that 92460 should be touched.

## Recorded Entry-Gate Failure

The failed actual resume attempt from Phase32-BC returned:

`PRECONDITION_FAILURE`

with:

`plan entry gate failed`

for business date:

`2023-10-12`

Failed checks:

- `run_scoped_contract_authority_present`
- `run_scoped_contract_source_normal`
- `run_scoped_status_pass`
- `run_scoped_selected_feature_date_present`
- `run_scoped_selected_matches_plan`
- `run_scoped_selected_matches_profile_expected`

The plan-side feature-date evidence for 2023-10-12 was:

- `source`: `runtime_test_plan_schedule_expectation`
- `authority_status`: `NOT_YET_MATERIALIZED`
- `feature_date_authority_source`: `not_yet_materialized_plan_expectation`
- `reason`: `feature_date_contract_not_yet_materialized_plan_expectation_only`
- `selected_feature_date`: `2023-10-12`
- `contract_materialized`: `false`

## Resume Gate Contract

`resume_command` validates source baseline first, then loads the original `plan.json`, then calls:

`validate_plan_entry_gate(..., resume=True)`

before entering the job loop.

For resume, `_resume_day_classification` marks:

- completed days as `COMPLETED`
- the halted day as `FAILED`

Then `validate_plan_entry_gate` applies `_resume_feature_date_checks` to both `COMPLETED` and `FAILED` days.

For any such day, it requires `_run_scoped_feature_date_contract_evidence(...)` to find materialized run-scoped evidence with:

- source/authority equivalent to `normal_feature_date_contract`
- `status=PASS`
- non-empty `selected_feature_date`
- selected date matching the plan/profile expectation.

This check occurs before the failed job is retried.

## Expected Run-Scoped Feature-Date Authority

The expected authority is not the plan's schedule expectation. It is a materialized feature-date contract sourced from Runtime evidence, discoverable by `_find_feature_date_contract_evidence`.

The resolver recognizes a nested object only when it has:

- `feature_date_authority_source` or `contract_source` equal to `normal_feature_date_contract` / `materialized_feature_date_contract`
- non-empty `selected_feature_date`

The preferred search order is:

1. `daily/<date>/data_readiness/data_readiness.json`
2. `daily/<date>/market_refresh/runtime_manifest.json`
3. `daily/<date>/morning/runtime_manifest.json`
4. `daily/<date>/morning/morning_manifest.json`
5. `daily/<date>/strategy/input_manifest.json`
6. selected nested JSON evidence under the daily directory.

## Why Authority Was Missing

For the original failed resume precondition, 2023-10-12 was halted at `data_readiness`. At that boundary, the normal data-readiness artifact may not yet exist or may not be authoritative because the failed job has not completed.

The preceding `market_refresh/runtime_manifest.json` does contain feature-date-like fields:

- `selected_feature_date=2023-10-12`
- `feature_date_contract_path=.runtime/operations/feature_date_contract/2023-10-12.json`
- generated feature artifact paths

But it does not expose the specific normalized field required by `_find_feature_date_contract_evidence`:

`feature_date_authority_source=normal_feature_date_contract`

Therefore, when `data_readiness.json` is absent or not usable, the resolver cannot promote market-refresh evidence into run-scoped feature-date authority, even though the market-refresh job had already materialized the underlying `.runtime/operations/feature_date_contract/2023-10-12.json`.

In short:

`market_refresh` materialized enough real PIT feature-date evidence for the next Runtime job, but `runtime_test resume` could not discover it in the strict run-scoped evidence shape it requires before retrying the failed `data_readiness` job.

## Does Resume Check Too Early?

Yes, for this halt shape.

The gate treats a halted `data_readiness` day as a `FAILED` day that must already have run-scoped materialized feature-date authority before it may enter the same `data_readiness` job. But `data_readiness` itself is one of the normal places that writes the discoverable authority shape.

This creates a circular precondition:

1. Resume cannot retry `2023-10-12:data_readiness` until run-scoped feature-date authority is discoverable.
2. The most preferred discoverable run-scoped authority for the day is normally written by `2023-10-12:data_readiness`.
3. The available predecessor evidence, `market_refresh/runtime_manifest.json`, is not normalized enough for the resolver to accept.

That is a runtime_test resume orchestration defect, not a Strategy or Runtime correctness defect.

## Current Evidence Inconsistency

At BD audit time, `reports/runtime_tests/runs/.../daily/2023-10-12/data_readiness/data_readiness.json` exists and contains:

- `feature_date_authority_source=normal_feature_date_contract`
- `selected_feature_date=2023-10-12`
- `status=PASS`
- Pending component shown as `READY` / `pending_slot_empty`

A read-only direct evaluation of `_run_scoped_feature_date_contract_evidence` now returns a valid evidence object from that file.

However, the authoritative run state still says:

- `status=HALT`
- `next_job=2023-10-12:data_readiness`

and the live `.runtime/pending_order_plan/pending_order_plan.json` still contains the prior-day `MIXED_SELL_ITEM_SCOPED_REVIEW` residual Pending.

Therefore BD does not treat the current `data_readiness.json` as sufficient acceptance that the target run advanced. It is inconsistent with the run state and live runtime root. The safe conclusion is that the originally reported resume entry-gate failure was real, and the target run still must not be considered progressed past `2023-10-12:data_readiness` without a canonical resume/recovery action.

## Root Cause

Root cause:

`runtime_test resume` requires run-scoped materialized feature-date authority for the failed `data_readiness` day before retrying that same `data_readiness` job, but the existing discovery path cannot accept the already-completed `market_refresh` evidence because it lacks the normalized `feature_date_authority_source=normal_feature_date_contract` shape.

This is a resume orchestration / evidence-normalization boundary defect.

It is not:

- a Strategy semantic issue,
- a PM/PC/PS issue,
- a 92460 execution issue,
- a market data PIT correctness failure,
- a reason to replay 2023-10-11,
- evidence that a fresh-run is required.

## PIT Safety Impact

PIT safety impact: LOW if repaired narrowly.

The gate's intent is valid: resume must not use plan expectations as authority for completed or failed dates. The defect is not that the system is too strict about PIT authority; it is that the runner has no non-circular way to recognize the materialized authority from `market_refresh` when the failed job is `data_readiness`.

The minimal repair must preserve:

- no use of plan expectation as authority,
- no future-date feature selection,
- selected feature date must match the materialized contract,
- no carryover unless explicitly accepted by the feature-date contract,
- no replay of 2023-10-11,
- no duplicate 92460 side effect.

## Minimal Future Repair Boundary

Narrow repair options, in preferred order:

1. Normalize `market_refresh/runtime_manifest.json` output so it includes a discoverable run-scoped feature-date authority object with `feature_date_authority_source=normal_feature_date_contract`, `selected_feature_date`, `requested_feature_date`, `status`, `reason`, and contract path/hash.
2. Or extend `_run_scoped_feature_date_contract_evidence` to accept the existing `runtime_v2_market_refresh_pipeline` stage details only when they are backed by an existing materialized `.runtime/operations/feature_date_contract/<date>.json` with `status=PASS` and matching selected date.
3. Or special-case resume entry gate for `FAILED` days whose failed job is `data_readiness`, allowing the job command's own `resolve_run_job_command` materialized contract resolution to serve as the pre-entry authority, while still rejecting plan-expectation-only evidence.

The first option is the cleanest because it makes market refresh publish the run-scoped authority shape that resume already knows how to consume.

## Current Run Recoverability

- Safe continuation point: `2023-10-12:data_readiness`
- Same-run continuation remains possible: YES, after a narrow runtime_test resume entry-gate repair or canonical evidence-normalization repair.
- Replay 2023-10-11 required: NO.
- Recover/replay current 2023-10-11 required: NO.
- Fresh-run required: NO by current evidence.
- Preserve 92460 exactly as-is: YES.

The current run should not be resumed manually around the gate by ad-hoc state edits. The next repair should make the existing `runtime_test resume` path canonically accept the already-materialized 2023-10-12 feature-date authority without relying on plan expectation.

## Required Final Judgment Answers

- `ROOT_CAUSE`: `runtime_test resume` checks run-scoped feature-date authority for the failed `2023-10-12:data_readiness` day before retrying `data_readiness`, but the predecessor `market_refresh` evidence is not discoverable in the normalized authority shape; the plan remains `NOT_YET_MATERIALIZED`.
- `RUNTIME_TEST_RESUME_ORCHESTRATION_VS_RUNTIME_CORRECTNESS`: runtime_test resume orchestration / evidence-normalization defect.
- `PIT_SAFETY_IMPACT`: no confirmed PIT contamination; fail-closed behavior is conservative. Future repair must not use plan expectation as authority.
- `SAFE_CONTINUATION_POINT`: `2023-10-12:data_readiness`.
- `SAME_RUN_CONTINUATION_POSSIBLE`: YES, after canonical entry-gate/evidence-normalization repair.
- `FRESH_RUN_REQUIRED`: NO.
- `REPLAY_2023_10_11_REQUIRED`: NO.
- `PRESERVE_92460`: YES.
- `BD_CODE_OR_STATE_CHANGE`: NO.

## Final Judgment

`PHASE32_BD_RUN_SCOPED_FEATURE_DATE_RESUME_ENTRY_GATE_ROOT_CAUSE_IDENTIFIED`

The current blocker is not the Phase32-BC Pending lifecycle repair and not Runtime trading correctness. It is a runtime_test resume entry-gate circularity for a day halted at `data_readiness`: the gate demands run-scoped materialized feature-date authority before running the job that normally publishes the preferred discoverable authority, while refusing to recognize the already-materialized market-refresh contract evidence because it lacks the normalized authority field.

The safe continuation point remains `2023-10-12:data_readiness`. Same-run continuation should remain possible after a narrow resume entry-gate/evidence-normalization repair. Fresh-run is not required by BD evidence.
