# Phase32-AX — Mixed SELL Review Fresh-Run Contract Repair

## Objective

Repair the Phase32-AW correctness defect where a normal fresh-run
`morning -> sell_planning` path could not progress when one Pending contained:

- unresolved/review-required SELL item,
- independent feasible SELL item,
- optional reviewed BUY items.

Target recurrent boundary:

- run: `runtime-test-historical-extended-smoke-20260831T003243720082Z`
- date: `2023-10-11`
- stage: `sell_planning`
- prior first reason: `historical_safety_temporal_authority_missing`

No Strategy, PM, PC, PS, threshold, weight, ranking, SELL rule, BUY_ADD/G129, KI-004, KI-006, or Winner Retention semantic was changed.

## Root Cause Repaired

Phase32-AW confirmed that Phase32-AA was working: unresolved Corporate Action SELL `50280` was no longer leaking to Submit as approved. It was materialized in Pending as `REVIEW_REQUIRED`.

The remaining defect was the absence of a normal fresh-run contract for mixed SELL review:

`50280 REVIEW_REQUIRED SELL`
plus
`92460 feasible PASS SELL`
plus optional reviewed BUY items

caused Pending to be classified as `AUTHORITY_UNKNOWN_REVIEW`, with:

- `approved_item_ids = []`
- `approved_sell_item_ids = []`
- `review_required_sell_item_ids = [50280 item]`
- `sell_continuation_allowed = false`

Historical Safety temporal authority then rejected daily neutral safety and sell_planning halted before canonical sell planning/submit handling could separate the unrelated items.

## Repair Implemented

### 1. Pending Review-Scope Authority

Added explicit scope:

`MIXED_SELL_ITEM_SCOPED_REVIEW`

Contract:

- reviewed SELL items remain reviewed and must not submit,
- reviewed BUY items remain reviewed and must not submit,
- independent PASS SELL items are the only executable subset,
- no BUY item is promoted under this scope,
- old `BUY_ITEM_SCOPED_REVIEW` behavior is preserved,
- a reviewed SELL inside old BUY-only scope still fail-closes as before.

### 2. Pending Promotion

`attach_approval_link()` now classifies Planning Submit Feasibility output as `MIXED_SELL_ITEM_SCOPED_REVIEW` only when:

- at least one SELL item is blocked/review-required,
- at least one independent SELL item is PASS,
- the blocked items have explicit authority and violated policy source,
- the approved subset is restricted to PASS SELL items.

For the 2023-10-11 shape this means:

- `50280` remains `REVIEW_REQUIRED`,
- `92460` becomes the only approved/executable SELL,
- reviewed BUY rows remain unapproved and unsubmitted.

### 3. Historical Safety / Data Readiness

Historical Safety temporal authority already delegates to Pending review-scope authority. By adding the explicit mixed SELL scope and allowing sell continuation only for that scope, same-day Historical neutral authority can resolve for the separated executable SELL subset while unresolved items remain fail-closed.

Genuine missing safety authority outside the accepted scope still fails closed.

### 4. Submit Orchestration

Submit partial-submission evidence now supports both:

- `BUY_ITEM_SCOPED_REVIEW_PARTIAL_PASS_SUBMISSION`
- `MIXED_SELL_ITEM_SCOPED_REVIEW_PARTIAL_PASS_SELL_SUBMISSION`

Submit behavior:

- only `approved_item_ids` are submitted,
- under mixed SELL review, approved items are restricted to PASS SELL items,
- reviewed BUY and reviewed SELL items are emitted as `NOT_SUBMITTED` / `REVIEW_REQUIRED`,
- reviewed SELL cannot leak into Submit because it is not approved and Submit preflight rejects overlap between approved and reviewed IDs,
- existing BUY-only reason strings were preserved for compatibility.

### 5. Corporate Action Freshness

`materialize_corporate_action_adjustment_authority()` no longer reuses an existing `.runtime/runtime_state/corporate_action_adjustments/<date>/<symbol>.json` only because it exists.

Existing authority is reused only when it matches current event evidence:

- schema version,
- business date,
- symbol,
- current event source artifact path,
- current event source artifact hash,
- adjustment factor,
- effective date.

If it does not match, the authority is regenerated from the current run-scoped event evidence. `evaluate_corporate_action_adjustment_authority()` also reports source artifact/hash mismatches when stale authority reaches evaluation.

This repairs the stale cross-run lineage found by AW, where fresh-run 20260831 evidence carried a 20260830 Corporate Action source path.

## Files Changed

- `src/ai_fund_lab_v2/runtime_v2/pending/review_scope_authority.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/promotion.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/corporate_action_adjustment.py`
- `tests/runtime_v2/test_phase30_ak9r27_pending_review_scope_authority.py`
- `tests/runtime_v2/test_phase30_ak9r28_historical_safety_temporal_authority.py`
- `tests/runtime_v2/test_phase31_a5_executable_membership_guard.py`
- `tests/runtime_v2/test_phase17_bv8_historical_submit_pit_universe_authority.py`
- `tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py`
- `docs/phase_reports/phase32_ax_mixed_sell_review_fresh_run_contract_repair.md`

Existing unrelated working-tree changes were not reverted.

## Focused Validation

### AX direct reproduction tests

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/runtime_v2/test_phase31_a5_executable_membership_guard.py::test_phase32_ax_mixed_review_sell_scope_preserves_independent_pass_sell \
  tests/runtime_v2/test_phase30_ak9r27_pending_review_scope_authority.py::test_phase32_ax_mixed_sell_review_allows_independent_pass_sell_only \
  tests/runtime_v2/test_phase30_ak9r28_historical_safety_temporal_authority.py::test_phase30_ak9r28_shadow_cases_classified_without_unexplained_mismatch \
  tests/runtime_v2/test_phase17_bv8_historical_submit_pit_universe_authority.py::test_phase32_ax_corporate_action_authority_rejects_stale_cross_run_lineage

14 passed
```

This includes the target 2023-10-11 shape:

- `50280`-like unresolved CA SELL remains `REVIEW_REQUIRED`,
- `92460`-like PASS SELL remains independently executable,
- reviewed BUY item remains unsubmitted,
- stale cross-run CA authority lineage is regenerated from current event evidence.

### Main focused regression

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/runtime_v2/test_phase30_ak9r27_pending_review_scope_authority.py \
  tests/runtime_v2/test_phase30_ak9r28_historical_safety_temporal_authority.py \
  tests/runtime_v2/test_phase31_a5_executable_membership_guard.py \
  tests/runtime_v2/test_phase17_bv8_historical_submit_pit_universe_authority.py \
  tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py \
  tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py \
  tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py \
  tests/runtime_v2/test_phase17_k_runtime_test_runner.py \
  -k 'phase32_ae or phase32_ac_partial_submit or phase32_ax or ak9r27 or ak9r28 or phase31_a5 or phase32_aa or phase31_f1w or phase17_bv8 or phase17_x or phase17_ag'

88 passed, 44 deselected, 60 warnings
```

Warnings are pre-existing `DeprecationWarning` messages from `position_management/producer.py` around empty array truth-value checks.

### G129 / BUY_ADD / KI-006 / Winner Retention adjacent focused regression

```text
PYTHONPATH=src python3 -m pytest -q \
  tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py \
  -k 'g129 or buy_add or phase32_s or phase32_x or zero'

15 passed, 43 deselected
```

## 2023-10-11 Focused Reproduction Result

Non-long focused reproduction was performed through unit/regression fixtures using the 2023-10-11 shape and symbols:

- `50280` unresolved Corporate Action SELL,
- `92460` independent feasible SELL,
- reviewed BUY item.

Result:

- `50280` remains `REVIEW_REQUIRED`,
- `92460` is the only executable SELL subset,
- reviewed BUY remains blocked/unsubmitted,
- Historical safety temporal authority accepts only the explicit mixed scope,
- reviewed SELL cannot leak to Submit,
- stale cross-run CA lineage is regenerated/rejected.

No fresh-run, resume, replay, recover, or long Historical run was executed by Codex.

## Current 650BD Run Resume Safety

Read-only re-audit of:

`runtime-test-historical-extended-smoke-20260831T003243720082Z`

Findings:

- run status: `HALT`
- `next_job = 2023-10-11:sell_planning`
- no `daily/2023-10-11/submit` artifacts exist,
- no `daily/2023-10-11/execution` artifacts exist,
- no submit/execution side effect exists in target-day evidence,
- current pre-repair Pending evidence still has:
  - `state = REVIEW_REQUIRED`
  - `review_scope = AUTHORITY_UNKNOWN_REVIEW`
  - `approved_item_ids = []`
  - `approved_sell_item_ids = []`
  - `review_required_sell_item_ids = [50280 item]`
  - `50280 = REVIEW_REQUIRED`
  - `92460 = REVIEW_REQUIRED / feasibility PASS / BLOCKED_BY_BATCH_REVIEW`

Classification:

`RESUME_REQUIRES_CANONICAL_REGENERATION`

Reason:

The halted run has no 2023-10-11 Submit or Execution side effects, so the completed 252BD are not contaminated. However, the existing Pending was materialized before AX and lacks the new mixed SELL review scope and approved `92460` subset. A plain resume from the stale Pending is not the canonical proof path. The safe operator path is to regenerate the 2023-10-11 Pending/sell_planning boundary under repaired source, or use an existing canonical recovery/replay path that does exactly that without duplicating side effects.

## Required Final Answers

- `ROOT_CAUSE_REPAIRED`: YES.
- `MIXED_SELL_REVIEW_CONTRACT_IMPLEMENTED`: YES. `MIXED_SELL_ITEM_SCOPED_REVIEW` added.
- `50280_REMAINS_REVIEW_REQUIRED`: YES. Unresolved CA SELL remains reviewed and is not approved.
- `92460_CAN_PROGRESS_INDEPENDENTLY`: YES, when its own authority is PASS and Pending is regenerated under AX source.
- `REVIEWED_BUYS_REMAIN_BLOCKED`: YES. Reviewed BUY items remain unapproved and unsubmitted.
- `STALE_CROSS_RUN_CA_LINEAGE_REPAIRED`: YES. Existing CA authority reuse now requires current event source path/hash/factor/effective-date match; otherwise regenerated or rejected.
- `FAIL_CLOSED_BEHAVIOR_PRESERVED`: YES. Old BUY-scope reviewed SELL still fails closed; genuine missing/unknown authority still fails closed; reviewed CA SELL cannot submit.
- `FOCUSED_REGRESSION_RESULT`: PASS. `88 passed, 44 deselected`; G129/BUY_ADD adjacent `15 passed, 43 deselected`.
- `2023_10_11_FOCUSED_REPRODUCTION_RESULT`: PASS via non-long focused fixtures for `50280` + `92460` mixed SELL review shape. No long Historical run executed.
- `CURRENT_650BD_RUN_RESUME_CLASSIFICATION`: `RESUME_REQUIRES_CANONICAL_REGENERATION`.
- `ANY_STRATEGY_BEHAVIOR_CHANGE`: NO.
- `ANY_PRODUCTION_SEMANTIC_CHANGE`: YES, narrowly in Runtime control semantics: explicit mixed SELL review now allows unrelated PASS SELL submission while keeping reviewed items blocked. Strategy semantics are unchanged.
- `FINAL_JUDGMENT`: `PHASE32_AX_MIXED_SELL_REVIEW_FRESH_RUN_CONTRACT_REPAIRED_RESUME_REQUIRES_CANONICAL_REGENERATION`

## Next Operator Action

Do not plain-resume the current 650BD run from the stale pre-AX Pending. Use a canonical focused regeneration/replay path for `2023-10-11` under the repaired source, then resume only after that path confirms:

- regenerated Pending has `review_scope = MIXED_SELL_ITEM_SCOPED_REVIEW`,
- `50280` is `REVIEW_REQUIRED`,
- `92460` is approved/executable,
- no reviewed BUY/SELL item is submitted,
- no duplicate order exists.

Codex did not execute that mutating action in AX.

## Final Judgment

`PHASE32_AX_MIXED_SELL_REVIEW_FRESH_RUN_CONTRACT_REPAIRED_RESUME_REQUIRES_CANONICAL_REGENERATION`
