# Phase32-BA - Post-Partial-Execution Current Valuation Authority Repair

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260831T003243720082Z`
- Starting halt: `2023-10-11:current_valuation_refresh`
- Starting canonical reason: `historical_safety_temporal_authority_missing`
- Fresh run: NOT executed
- Rewind/replay of `2023-10-11` morning, sell_planning, submit, execution: NOT executed
- Strategy/config/threshold/model changes: NONE

## Root Cause Repaired

Phase32-AZ found that a valid post-partial-execution Pending shape was still rejected by current valuation Data Readiness:

- `review_scope = MIXED_SELL_ITEM_SCOPED_REVIEW`
- executable SELL `92460` already consumed
- reviewed items `50280`, `38560`, `76920` still explicitly `REVIEW_REQUIRED`
- no unconsumed executable item remained
- order/execution/current/cash for `92460` were authoritative

The first bad boundary was:

`Pending review-scope authority -> Historical Safety temporal authority current_valuation adapter`

The repair extends only current valuation residual Pending / Historical safety temporal authority. It does not alter Strategy, SELL decisions, PM/PC/PS, Submit, Execution, thresholds, ranking, or model behavior.

## Files Changed

- `src/ai_fund_lab_v2/runtime_v2/pending/review_scope_authority.py`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/safety_temporal_authority.py`
- `src/ai_fund_lab_v2/runtime_v2/data_readiness.py`
- `tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py`

## Contract Implemented

Current valuation can now treat a `MIXED_SELL_ITEM_SCOPED_REVIEW` residual as compatible only when:

- Pending structural validity is `PASS`;
- runtime mode/environment match;
- target session date equals current business date;
- approved/executable SELL items are already `CONSUMED`;
- no non-terminal unclassified item remains;
- reviewed BUY/SELL items remain `REVIEW_REQUIRED`;
- reviewed items are not approved and have no submit/fill side-effect identity;
- authoritative same-day Ledger evidence exists exactly once for consumed SELL order, execution, position transition, and cash;
- Historical simulated neutral safety contract applies through current run/profile/evidence-root binding.

The repair still fails closed for:

- malformed Pending;
- unknown review scope;
- unconsumed executable SELL;
- missing execution evidence;
- duplicate execution evidence;
- reviewed item incorrectly marked approved;
- reviewed item carrying side-effect identity;
- non-Historical environment;
- missing runtime-root Ledger evidence for the mixed SELL residual case.

## Focused Validation

Command:

```bash
PYTHONPATH=src python3 -m pytest \
  tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py \
  tests/runtime_v2/test_phase30_ak9r27_pending_review_scope_authority.py \
  tests/runtime_v2/test_phase30_ak9r28_historical_safety_temporal_authority.py \
  tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py \
  tests/runtime_v2/test_phase17_bv8_historical_submit_pit_universe_authority.py \
  tests/runtime_v2/test_phase31_a5_executable_membership_guard.py \
  tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py \
  tests/strategy/test_phase31_g119_pc_final_authority_ps_consistency.py \
  tests/strategy/test_phase31_g122_campaign_lifecycle_add_history.py \
  tests/strategy/test_phase31_g63_runtime_executable_binding.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py \
  -q
```

Result:

- `151 passed`

Added BA-focused cases:

- mixed SELL post-execution residual allows current valuation readiness;
- `50280` and reviewed BUYs remain `REVIEW_REQUIRED`;
- reviewed items do not become submittable;
- unconsumed PASS SELL blocks current valuation;
- missing execution evidence blocks current valuation;
- duplicate execution evidence blocks current valuation;
- reviewed SELL incorrectly marked approved blocks current valuation.

Existing focused regressions remained PASS, including AX/AA/AE-adjacent mixed review, safety temporal authority, executable membership, planning submit feasibility, and G129/BUY_ADD-related strategy/runtime executable bindings.

## Pre-Resume Duplicate Check

Before actual resume:

- `run_state.status = HALT`
- `run_state.next_job = 2023-10-11:current_valuation_refresh`
- Pending:
  - `pending_plan_id = pending-strategy-plan-historical-2023-10-11-84b153a169af27d4`
  - `state = REVIEW_REQUIRED`
  - `review_scope = MIXED_SELL_ITEM_SCOPED_REVIEW`
  - `sell_continuation_allowed = true`
- Item states:
  - `92460`: `CONSUMED`, approved `true`, feasibility `PASS`
  - `50280`: `REVIEW_REQUIRED`, approved `false`, feasibility `REVIEW_REQUIRED`
  - `38560`: `REVIEW_REQUIRED`, approved `false`, feasibility `REVIEW_REQUIRED`
  - `76920`: `REVIEW_REQUIRED`, approved `false`, feasibility `REVIEW_REQUIRED`
- Same-day duplicate counts for `92460`:
  - orders: `1`
  - executions: `1`
  - position transition rows: `1`
  - cash rows: `1`

Repair-time Data Readiness check:

- status: `READY`
- reason: `Proceed to requested Runtime step.`
- pending component: `READY`
- safety component: `READY`
- review reasons: `[]`
- component reasons: all empty.

Resume dry-run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resume \
  --profile historical-extended-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id runtime-test-historical-extended-smoke-20260831T003243720082Z \
  --dry-run \
  --json
```

Result:

- `DRY_RUN`
- exit code `0`
- `resume_allowed = true`

## Same-Run Resume Acceptance

Actual resume command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resume \
  --profile historical-extended-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id runtime-test-historical-extended-smoke-20260831T003243720082Z \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

Result:

- The run resumed from `2023-10-11:current_valuation_refresh`.
- `2023-10-11:current_valuation_refresh` passed.
- `2023-10-11` completed.
- `2023-10-12` was reached.
- The run later HALTed at `2023-10-12:data_readiness`, exit code `20`.

The later `2023-10-12:data_readiness` HALT is outside the BA repair boundary. It proves the BA acceptance target was reached, but the 650BD run is not currently complete.

## Current Valuation Evidence

`2023-10-11/current_valuation_refresh/runtime_manifest.json`:

- `exit_code = 0`
- `final_state = CURRENT_STATE_LOADED`
- `data_readiness_status = READY`
- `data_readiness_review_reasons = []`
- `component_reasons`: all empty
- `current_valuation_refresh_status = READY`
- `current_valuation_refresh_reason = current_valuation_ready`
- `current_valuation_refresh_artifact_path = .runtime/runtime_state/current_valuation/2023-10-11/current_valuation_refresh.json`

`2023-10-11/current_valuation_refresh/current_valuation_manifest.json`:

- `apply_executed = true`
- `apply_status = APPLIED`
- `business_date = 2023-10-11`
- candidate current valuation status: `READY`
- cash: `1141580.0`
- buying power: `1141580.0`
- market value: `506700.0`

## 92460 Preservation

`92460` state was preserved. No rewind, replay, regeneration, deletion, or resubmission of 92460 was performed.

Post-resume duplicate counts remain:

- 92460 order count: `1`
- 92460 execution count: `1`
- 92460 position transition count: `1`
- same-day cash update count: `1`

Reviewed items remain blocked:

- `50280`: not submitted
- `38560`: not submitted
- `76920`: not submitted

## Required Final Answers

- `CURRENT_VALUATION_CONTRACT_REPAIRED`: YES.
- `92460_STATE_PRESERVED`: YES.
- `MIXED_REVIEW_RESIDUAL_ACCEPTED_FOR_VALUATION`: YES, only after consumed executable SELL has matching one-time Ledger evidence.
- `REVIEWED_ITEMS_REMAIN_BLOCKED`: YES.
- `FAIL_CLOSED_BEHAVIOR_PRESERVED`: YES.
- `FOCUSED_REGRESSION_RESULT`: PASS, `151 passed`.
- `PRE_RESUME_DUPLICATE_CHECK`: PASS; 92460 order/execution/position transition/cash counts were each `1`.
- `RESUME_EXECUTED`: YES.
- `CURRENT_VALUATION_REFRESH_PASSED`: YES.
- `2023_10_11_COMPLETED`: YES.
- `2023_10_12_REACHED`: YES.
- `CURRENT_RUN_STATUS`: `HALT` at `2023-10-12:data_readiness`, exit code `20`.
- `FRESH_RUN_REQUIRED`: NO by BA evidence.
- `FINAL_JUDGMENT`: `PHASE32_BA_POST_PARTIAL_EXECUTION_CURRENT_VALUATION_REPAIRED_2023_10_12_REACHED`

