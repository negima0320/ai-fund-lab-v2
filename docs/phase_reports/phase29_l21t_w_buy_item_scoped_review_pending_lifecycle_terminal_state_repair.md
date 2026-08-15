# Phase29-L21T-W BUY_ITEM_SCOPED_REVIEW Pending Lifecycle Terminal-State Repair

## Scope

IMPLEMENTATION + FOCUSED REGRESSION.

Codex did not run fresh-run, resume-run, scoped recovery, replay, long Historical
validation, manual Pending approval, or runtime mutation for the target run.

Target run:

```text
runtime-test-historical-smoke-20260812T212155604711Z
```

Target day:

```text
2022-10-12
```

## Primary Judgment

`PHASE29_L21T_W_BUY_ITEM_SCOPED_REVIEW_PENDING_LIFECYCLE_TERMINAL_STATE_REPAIRED_FOCUSED_REGRESSION_PASS`

Required judgments:

```text
ROOT_CAUSE_CONFIRMED = YES
L21T_V_SUBMIT_NO_SUBMISSION_AUTHORITY_VALID = YES
L21T_V_EXECUTION_NO_ACTION_AUTHORITY_VALID = YES
PENDING_LIFECYCLE_TERMINALIZATION_DEFECT_CONFIRMED = YES
BUY_ITEM_SCOPED_REVIEW_NO_SUBMISSION_TERMINALIZATION_IMPLEMENTED = YES
EXISTING_FAILED_REVIEW_HISTORY_COLLISION_HANDLED = YES
BUY_BATCH_ATOMICITY_PRESERVED = YES
PARTIAL_BUY_SUBMIT_ALLOWED = NO
REVIEWED_BUY_SUBMITTED = NO
SELL_CONTINUATION_INDEPENDENCE_PRESERVED = YES
GLOBAL_OR_MALFORMED_REVIEW_FAIL_CLOSED_PRESERVED = YES
HISTORICAL_SPECIFIC_WORKAROUND_ADDED = NO
NEW_RUNTIME_TEST_COMMAND_ADDED = NO
COMMAND_GUIDE_UPDATED = NOT_REQUIRED
DIRECT_RESUME_SAFE = YES_AFTER_L21T_W_PATCH
RECOVERY_REQUIRED = NO
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Read-Only Audit

`run_state.json` showed the resumed run halted after `2022-10-12:pending_lifecycle`:

```text
status = HALT
next_job = 2022-10-12:execution
halted_at.job = pending_lifecycle
halted_at.exit_code = 20
runtime_test_job_status = HALT_PENDING_LIFECYCLE_REQUIRED_UNRESOLVED
reason = required pending_lifecycle did not reach terminal status: REVIEW_REQUIRED
```

Current Pending was a same-day scoped BUY review:

```text
pending_plan_id = pending-strategy-plan-historical-2022-10-12-8c36afa771b13ce6
state/status = REVIEW_REQUIRED
plan_overall_status = REVIEW_REQUIRED
approved_item_ids = []
review_required_buy_item_ids = [strategy-9a17b799ca59b1896fce]
review_required_sell_item_ids = []
review_scope = BUY_ITEM_SCOPED_REVIEW
sell_continuation_allowed = true
reason = reserved notional exceeds dynamic cash capacity
```

Items:

```text
65500 BUY qty 700  approved=false state=REVIEW_REQUIRED feasibility=PASS
  item_review_reason = batch_submit_blocked_by_item_scoped_review

76920 BUY qty 1200 approved=false state=REVIEW_REQUIRED feasibility=REVIEW_REQUIRED
  item_review_reason = reserved notional exceeds dynamic cash capacity
```

L21T-V downstream evidence was valid:

```text
Submit final_state = CURRENT_STATE_LOADED
Submit action = NO_SUBMISSION_REQUIRED
Submit reason = BUY_ITEM_SCOPED_REVIEW_NO_SUBMISSION_REQUIRED
submitted_count = 0
blocked_count = 0
review_required = false
halt_required = false
no_order_authority = BUY_ITEM_SCOPED_REVIEW_NO_SUBMISSION / PASS

Execution final_state = CURRENT_STATE_LOADED
Execution stage status = PASS
execution_action = NO_ACTION
reason = no_submitted_orders
submitted_order_count = 0
fill_count = 0
pending_consumed = false
pending_mutated = false
pending_terminalization_status = PENDING_LIFECYCLE_REQUIRED
```

## Root Cause

`pending_lifecycle` had no authority branch for a valid
`BUY_ITEM_SCOPED_REVIEW` Pending whose BUY batch has zero approved items and
whose Submit/Execution path has already proven no broker submission is required.

The generic lifecycle rule treated any active non-terminal state other than
`APPROVED` as unresolved operator review:

```text
REVIEW_REQUIRED -> pending_state_review_required_requires_operator_review
```

That was correct for global, malformed, unknown, unscoped, stale, or unsafe
review states, but incomplete for the L21T-V contract:

```text
BUY_ITEM_SCOPED_REVIEW + approved_item_ids=[] + Submit NO_SUBMISSION_REQUIRED
+ Execution NO_ACTION = no order can cross the broker boundary for that day
```

The resulting classification is:

```text
B / D
```

The current slot must not remain an active blocker after the day has no
submit/execution work.  The reviewed BUY evidence is preserved in history, and
the current Pending slot is terminalized to `EXPIRED` / `EMPTY`.

## Changed Files

- `src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py`
- `tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py`
- `docs/phase_reports/phase29_l21t_w_buy_item_scoped_review_pending_lifecycle_terminal_state_repair.md`

No command was added, so `docs/03_operations/runtime_test_command_guide.md` was
not changed for L21T-W.

## Authority Before / After

Before:

```text
Pending Lifecycle:
  REVIEW_REQUIRED -> operator review required
```

After:

```text
Pending Lifecycle:
  valid BUY_ITEM_SCOPED_REVIEW
  + no approved BUY/SELL item ids
  + same target_session_date
  + sell_continuation_allowed=true
  + Submit BUY_ITEM_SCOPED_REVIEW_NO_SUBMISSION / PASS
  + Execution NO_ACTION / PASS
  + no broker write
    -> EXPIRED terminal history
    -> current Pending EMPTY

All other REVIEW_REQUIRED shapes:
    -> REVIEW_REQUIRED fail-closed
```

This is Production/Demo/Historical common.  It does not approve reviewed BUY
items, does not submit the independently feasible BUY sibling, and does not
weaken broker cash or reservation protection.

## Terminal Evidence

The new lifecycle authority records:

```text
pending_plan_id
pending_state
review_scope
approved_item_ids
approved_buy_item_ids
approved_sell_item_ids
review_required_buy_item_ids
review_required_sell_item_ids
sell_continuation_allowed
submit_status
submit_no_action_reason
execution_status
execution_no_action_reason
pending_lifecycle_terminal_status
pending_lifecycle_terminal_reason
broker_write_performed
fail_open_used
partial_buy_submit_allowed
reviewed_buy_submitted
buy_batch_atomicity_preserved
```

For a successful terminalization:

```text
pending_lifecycle_terminal_status = EXPIRED
pending_lifecycle_terminal_reason = buy_item_scoped_review_no_submission_terminal
broker_write_performed = false
fail_open_used = false
partial_buy_submit_allowed = false
reviewed_buy_submitted = false
```

## Existing Failed History Collision

The target run already contains a failed pre-L21T-W lifecycle history artifact
for the same pending plan.  `_write_history()` now keeps that existing evidence
when its transition differs and writes a deterministic conflict history path for
the repaired terminal transition.

This preserves the old failure evidence while allowing the current slot to point
to the new terminal history after user-run resume.

## Fixture Results

Added:

```text
test_phase29_l21t_w_buy_item_scoped_review_no_submission_terminalizes_without_broker_write
```

Result:

```text
Pending Lifecycle status = EXPIRED
current Pending state = EMPTY
history pending_payload.review_scope = BUY_ITEM_SCOPED_REVIEW
authority status = PASS
submit_status = CURRENT_STATE_LOADED
execution_status = PASS
broker_write_performed = false
fail_open_used = false
partial_buy_submit_allowed = false
reviewed_buy_submitted = false
```

Existing failed history fixture:

```text
test_phase29_l21t_w_existing_review_history_does_not_block_repaired_terminal_history
```

Result:

```text
old REVIEW_REQUIRED history preserved
new EXPIRED history written at deterministic conflict path
current Pending history_path points to repaired terminal history
```

Negative fixtures:

```text
test_phase29_l21t_w_buy_item_scoped_review_without_sell_continuation_fails_closed
test_phase29_l21t_w_global_review_required_pending_remains_fail_closed
test_phase29_l21t_w_missing_execution_no_action_authority_fails_closed
```

Results:

```text
sell_continuation_allowed=false -> REVIEW_REQUIRED
GLOBAL_REVIEW_REQUIRED -> REVIEW_REQUIRED
missing Execution no-action evidence -> REVIEW_REQUIRED
current Pending remains active fail-closed
```

## Regression Results

L21T-W focused:

```bash
python3 -m pytest tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py -k 'l21t_w'
```

Result:

```text
5 passed, 21 deselected
```

Pending lifecycle full file:

```bash
python3 -m pytest tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py
```

Result:

```text
26 passed
```

BUY/SELL independence, Submit no-action, Execution no-action:

```bash
python3 -m pytest \
  tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py \
  tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py
```

Result:

```text
38 passed
```

Final broad focused regression: pending lifecycle, BUY/SELL independence,
Submit no-action, Execution no-action, Q1/Q1B reservation, Q2 transactionality,
Pending approval, BUY_ADD, REENTRY, SELL quantity contract, runner lifecycle
gate:

```bash
python3 -m pytest \
  tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py \
  tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py \
  tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py \
  tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py \
  tests/runtime_v2/test_phase17_k_runtime_test_runner.py \
  tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py \
  tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py \
  tests/runtime_v2/test_phase26_step4_position_sizing_authority.py \
  tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py \
  tests/strategy/test_phase22_e_portfolio_construction.py \
  tests/strategy/test_phase22_j_position_sizing.py
```

Result:

```text
336 passed
```

Compile:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-l21t-w-pycache python3 -m py_compile \
  src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py \
  tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py
```

Result:

```text
PASS
```

Whitespace:

```bash
git diff --check
```

Result:

```text
PASS
```

## Safety Preservation

BUY batch atomicity:

```text
PRESERVED
```

`approved_item_ids=[]` remains authoritative.  The feasible BUY sibling remains
not submitted when another BUY item is in scoped review.

SELL continuation independence:

```text
PRESERVED
```

L21T-M composition and L21T-U/V submit/execution no-action regressions pass.

Q1B reservation protection:

```text
PRESERVED
```

This repair does not touch reservation price/notional computation or cash
feasibility.

Q2 transactionality:

```text
PRESERVED
```

Execution no-action remains no broker write, no Ledger commit, no Current
mutation, and no completed execution misclassification.

Fail-closed:

```text
PRESERVED
```

Unknown submit risk, missing execution no-action authority, global review,
malformed scoped review, and `sell_continuation_allowed=false` remain
`REVIEW_REQUIRED`.

## Resume / Recovery

```text
DIRECT_RESUME_SAFE = YES_AFTER_L21T_W_PATCH
RECOVERY_REQUIRED = NO
PENDING_MANUAL_EDIT_REQUIRED = NO
```

The target run stopped because required lifecycle did not reach a terminal
status.  `scripts/runtime_test.py` reruns required `pending_lifecycle` when the
existing lifecycle result is not in the completion set.  After this patch, that
rerun should terminalize the valid L21T-V no-submission pending to `EXPIRED`,
empty the current Pending slot, and allow the day completion gate to proceed.

Codex did not execute the command.

Recommended operator command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resume \
  --profile historical-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id runtime-test-historical-smoke-20260812T212155604711Z \
  --dry-run \
  --json
```

If the dry-run is accepted, run the same command with:

```text
--confirm --yes-i-understand-this-mutates-trading-state --json
```

## Next Step

User should run the focused resume dry-run first and inspect
`2022-10-12/pending_lifecycle/runtime_manifest.json` plus
`2022-10-12/day_completion/day_completion_evidence.json`.

Expected post-resume evidence:

```text
pending_lifecycle_status = EXPIRED
transition_reason = buy_item_scoped_review_no_submission_terminal
current Pending state = EMPTY
day_completion status = PASS
broker_write_performed = false
fail_open_used = false
```
