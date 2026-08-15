# Phase29-L20E - Historical Pending Lifecycle Runner Integration Audit

Task ID: Phase29-L20E

Mode:

```text
READ_ONLY ROOT CAUSE AUDIT
NO SOURCE / TEST / RUNNER / RUNTIME STATE REPAIR
NO CURRENT HALTED RUN MUTATION
NO RESUME / RESUME DRY-RUN / FRESH-RUN / RUN / PENDING_LIFECYCLE COMMAND
NO LONG HISTORICAL EXECUTION
```

## Primary Judgment

```text
PHASE29_L20E_HISTORICAL_PENDING_LIFECYCLE_RUNNER_INTEGRATION_GAP_CONFIRMED_L20D_ELIGIBLE_BUT_NOT_INVOKED_REPAIR_REQUIRED
```

The L20D terminalization implementation exists and is reachable from the
Runtime v2 CLI `pending_lifecycle` job, but the Historical Runtime Test runner
does not include `pending_lifecycle` in the normal Historical business-day job
sequence. The real run therefore completed 2022-09-28 while an active
`APPROVED` Corporate Action quarantine Pending still required lifecycle work,
then halted correctly at 2022-09-29 `data_readiness`.

Root cause classification:

```text
HISTORICAL_RUNTIME_RUNNER_DOES_NOT_INVOKE_REQUIRED_PENDING_LIFECYCLE_AFTER_CA_QUARANTINE_EXECUTION = CONFIRMED
```

## Direct Real-run Symptom

Run:

```text
runtime-test-historical-smoke-20260811T090301298165Z
requested period: 2022-08-10 through 2026-08-09
initial cash: 1,000,000 JPY
status: HALT
next_job: 2022-09-29:data_readiness
completed_business_days includes: 2022-09-28
runtime CLI exit: 20
runner exit: 30
```

2022-09-28 Execution:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T090301298165Z/daily/2022-09-28/execution/pending_terminalization_evidence.json

status = PENDING_LIFECYCLE_REQUIRED
pending_read_valid = true
pending_classification = VALID
pending_plan_present = true
pending_item_count = 1
pending_consumed = false
pending_mutated = false
```

2022-09-29 Data Readiness:

```text
reports/runtime_tests/runs/runtime-test-historical-smoke-20260811T090301298165Z/daily/2022-09-29/data_readiness/data_readiness.json

overall_status = REVIEW_REQUIRED
pending_active = true
pending_slot_status = APPROVED
components.pending.status = REVIEW_REQUIRED
components.pending.reason = stale_approved_pending_exists
components.pending.stale_artifacts = ["pending"]
components.safety.reason = historical_safety_temporal_authority_missing
components.safety.pending_safety_authority.reason = historical_pending_safety_authority_mismatch
next_operator_action = run pending_lifecycle
```

Current active Pending slot at inspection time:

```text
.runtime/pending_order_plan/pending_order_plan.json

state = APPROVED
pending_plan_id = pending-strategy-plan-historical-2022-09-28-e705a57ffbdc21ef
target_session_date = 2022-09-28
item = strategy-8ae8275149ec3e547ed5 / 76920 / BUY / 2000
```

No `daily/*/pending_lifecycle/*` evidence exists in the current run, and no
`.runtime/pending_order_plan/history` file exists for this terminalization.

## Actual Historical Job Sequence

The actual configured Historical profile sequence is:

```text
market_refresh
data_readiness
morning
sell_planning
submit
execution
current_valuation_refresh
runtime_state_refresh
strategy_shadow_generation
```

Evidence:

```text
config/runtime_tests/historical_smoke_5bd.json:26-35
scripts/runtime_test.py:166-175
scripts/runtime_test.py:6156-6179
scripts/runtime_test.py:4351-4437
scripts/runtime_test.py:4438-4475
```

`strategy_shadow_generation` is not in profile `job_sequence`; it is appended
internally after the daily Runtime jobs. The 2022-09-28 run_state tail confirms
the same order, then 2022-09-29 starts with `market_refresh` and fails at
`data_readiness`.

Answer:

```text
Is pending_lifecycle automatic in normal Historical business-day sequence? NO
```

## Pending Lifecycle Integration Status

The Runtime v2 CLI has a first-class `pending_lifecycle` job:

```text
src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:96-114
src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py:387-410
```

It calls:

```text
src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py:30
run_pending_lifecycle_review(...)
```

However, the Runtime Test runner never schedules that job in `JOB_SEQUENCE` or
in `config/runtime_tests/historical_smoke_5bd.json`.

Classification:

```text
manual only in Runtime v2 CLI
missing from Historical Runtime Test automatic sequence
```

The Phase15-AR report also describes stale active `APPROVED` Pending as Data
Readiness `REVIEW_REQUIRED` with next action `run pending_lifecycle`, and shows
operator-style invocation as a separate CLI job.

## PENDING_LIFECYCLE_REQUIRED Consumer Trace

Producer:

```text
src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py:721-724
```

`_no_action_result()` initializes `ALREADY_TERMINAL`, then changes to
`PENDING_LIFECYCLE_REQUIRED` when the no-action execution authority still has
an active Pending plan with items:

```text
pending_plan_present == true
pending_item_count > 0
```

Consumers:

```text
rg -n "PENDING_LIFECYCLE_REQUIRED" src scripts tests docs/phase_reports/phase29_l20*.md
```

Current source consumers:

```text
none
```

The only non-report/test occurrence in source is the producer above.

Formal classification:

```text
PENDING_LIFECYCLE_REQUIRED_IS_OBSERVABILITY_ONLY_NO_RUNNER_CONSUMER
```

Because no runner or CLI orchestration consumes this marker, it did not trigger
pending lifecycle in the real run.

## L20D Reachability

L20D branch:

```text
src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py:117-137
```

It runs after:

```text
state == APPROVED
unknown_submit_risk == false
_historical_ca_quarantine_terminalization_authority(...) == PASS
```

Real 2022-09-28 evidence matches the strict L20D shape:

```text
mode = historical
Pending state = APPROVED
target_session_date = 2022-09-28
item count = 1
symbol = 76920
side = BUY
quantity = 2000
submit final_state = REVIEW_REQUIRED
submit exit_code = 20
submitted_count = 0
blocked_count = 1
pending_item_count = 1
submit_action = NO_SUBMIT_ATTEMPTED
broker_write = false
external_delivery = false
demo_submit_executed = false
production_order_executed = false
violated_policy = historical_corporate_action_symbol_quarantine
corporate_action_symbol_quarantine_continuation.status = COMPLETED_WITH_SYMBOL_QUARANTINE
scope = CORPORATE_ACTION_SYMBOL_ONLY
affected_symbols = ["76920"]
production_applicability = NEVER
corporate_action_run_continuation_eligibility = ALLOWED_FOR_HISTORICAL_REPLAY_ONLY
```

No evidence proves the L20D branch was invoked. No `pending_lifecycle` evidence
directory or history artifact exists.

Classification:

```text
A. L20D logic is correct and eligible, but never invoked.
```

There is no evidence for:

```text
B. invoked but ineligible
C. invoked and terminalized, then overwritten
D. another lifecycle branch gap
```

## Active Pending Writer Trace

Relevant active Pending writers in current source:

```text
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:112
src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:384-385
src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py:848-849
src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py:1054-1061
src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py:614-615
src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py:799-806
src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py:957-958
src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py:575-599
src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py:171-215
src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py:218-258
```

2022-09-28 writer trace:

```text
morning / strategy authority:
  strategy_planning_authority_evidence.json
  status = PASS
  pending_path = .runtime/pending_order_plan/pending_order_plan.json
  pending_plan_id = pending-strategy-plan-historical-2022-09-28-e705a57ffbdc21ef
  pending_commit_status = COMMITTED_CURRENT
  atomic_commit_decision = COMMIT

sell_planning:
  pending_continuity_evidence.json
  status = NO_SIGNAL
  pending_path = .runtime/pending_order_plan/pending_order_plan.json
  pending_plan_id remains pending-strategy-plan-historical-2022-09-28-e705a57ffbdc21ef

submit:
  submitted_count = 0
  blocked_count = 1
  no ledger_records write path reached for a submitted order
  pending remains APPROVED

execution:
  read-only path
  pending_mutated = false
  pending_terminalization_status = PENDING_LIFECYCLE_REQUIRED

current_valuation_refresh:
  valuation/current evidence only; no pending slot writer for this case

runtime_state_refresh:
  Runtime Operation State artifact refresh; reads/summarizes Pending, no active Pending terminalization

strategy_shadow_generation:
  read-only Runtime Test evidence job; mutation policy says no Runtime state mutation
```

Final writer that left the slot `APPROVED`:

```text
morning / strategy authority committed the active Pending; sell_planning later
preserved the same pending_plan_id. No post-execution lifecycle writer ran.
```

## Runner Completion Contract

In `run_command()`, the runner appends `completed_business_days` after all
profile jobs and the strategy shadow job complete:

```text
scripts/runtime_test.py:4351-4437
scripts/runtime_test.py:4438-4475
```

There is no check for outstanding:

```text
pending_terminalization_status = PENDING_LIFECYCLE_REQUIRED
```

and no post-day required-lifecycle stage before:

```text
run_state["completed_business_days"].append(day["business_date"])
```

Thus `completed_business_days` currently means:

```text
only core listed jobs plus strategy shadow completed under runner continuation rules
```

It does not mean:

```text
all lifecycle-required cleanup/work completed
```

Because 2022-09-28 was marked completed while `PENDING_LIFECYCLE_REQUIRED`
remained outstanding, this is a runner completion contract gap.

## Historical vs Production/Demo Difference

Runtime v2 CLI:

```text
pending_lifecycle is available for every formal mode accepted by the CLI.
```

Historical Runtime Test runner:

```text
does not schedule pending_lifecycle automatically
```

Production/Demo orchestration:

```text
not proven automatic in this audit
```

The CLI docstring describes the Runtime v2 daily operation CLI as the single
entrypoint intended for manual and launchd rehearsal operation, but this audit
found no Production/Demo runner path that automatically invokes
`pending_lifecycle` in response to `PENDING_LIFECYCLE_REQUIRED`.

Classification:

```text
manual CLI job exists across Runtime v2
Historical Runtime Test automatic sequence omits it
Production/Demo automatic lifecycle invocation = NOT_PROVEN
```

This is incompatible with unattended multi-business-day Historical validation
when a day can legally produce non-retryable, not-submitted Pending that must be
terminalized before the next business day.

## Root Cause

Exact root cause:

```text
Historical Runtime Test runner treats 2022-09-28 as complete after execution,
current valuation refresh, runtime state refresh, and strategy shadow even when
Execution explicitly emits PENDING_LIFECYCLE_REQUIRED. The runner has no
consumer for that marker and no automatic pending_lifecycle stage before the
next business day's data_readiness gate.
```

Candidate classification:

```text
HISTORICAL_RUNTIME_RUNNER_DOES_NOT_INVOKE_REQUIRED_PENDING_LIFECYCLE_AFTER_CA_QUARANTINE_EXECUTION = CONFIRMED
```

## Strategy Causality

```text
L19 causality = UNRELATED
```

This audit found no causality in:

```text
Position Sizing
Portfolio Construction
ADD
BUY_NEW
SELL
REDUCE
EXIT
Market Context
```

The failing behavior is Runtime orchestration / Pending lifecycle invocation.
Strategy produced a normal BUY Pending that was later quarantined by Submit due
Corporate Action authority.

## Regression Assessment

Evidence searched:

```text
git log -S 'pending_lifecycle' -- scripts/runtime_test.py src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py tests/runtime_v2
git log -S 'JOB_SEQUENCE' -- scripts/runtime_test.py config/runtime_tests/historical_smoke_5bd.json
git show 31aad0d / 78d0f1c / 1db2ce8 for runner sequence
```

Findings:

```text
Runtime v2 CLI pending_lifecycle job existed by Phase17.
Historical Runtime Test JOB_SEQUENCE existed without pending_lifecycle by Phase17.
Current Phase28/Phase29 runner sequence remains without pending_lifecycle.
No commit was found that removed pending_lifecycle from Runtime Test JOB_SEQUENCE.
```

Assessment:

```text
Regression confirmed: NO
Prior partial implementation: YES
Missing runner integration: YES
```

The most evidence-supported lineage is:

```text
pending_lifecycle was implemented as a manual Runtime v2 CLI job, but automatic
Runtime Test runner integration was never completed.
```

## Existing Test Coverage

Covered:

```text
tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py
  direct run_pending_lifecycle_review stale Pending behavior
  direct L20D Historical CA quarantine terminalization behavior
  next-day Data Readiness after already-terminalized slot
  CLI/report/notification manifest fields for pending_lifecycle

tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py
  execution no-action terminal evidence
  L20B Historical CA quarantine no-submitted-orders execution authority
  PENDING_LIFECYCLE_REQUIRED observability for active quarantine Pending

tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py
  stale APPROVED Pending fail-closed Data Readiness behavior

tests/runtime_v2/test_phase29_l9_historical_ca_quarantine_continuation.py
  Historical Corporate Action quarantine classifier / continuation artifact
```

Missing integration tests:

```text
automatic pending_lifecycle invocation in Runtime Test runner
execution -> pending_lifecycle ordering when PENDING_LIFECYCLE_REQUIRED is emitted
multi-day Historical CA quarantine progression through next-day Data Readiness
runner completion blocked when lifecycle work remains outstanding
completed_business_days excludes days with unresolved required lifecycle work
manual-only pending_lifecycle behavior explicitly documented as incompatible with unattended Historical, if kept
normal submitted-order lifecycle unaffected by automatic invocation
ordinary no-action EMPTY lifecycle remains ALREADY_TERMINAL / no mutation
mixed quarantine + submitted order remains fail-closed and is not whole-plan expired
Production/Demo mode safeguards if runner-level invocation is generalized
```

## Repair Required

```text
YES
```

Do not weaken:

```text
Data Readiness stale Pending detection
Corporate Action REVIEW_REQUIRED semantics
Production/Demo fail-closed behavior
unknown submit risk behavior
mixed submitted-order fail-closed behavior
```

## Recommended Repair Scope

Recommended next task:

```text
Phase29-L20F Historical Pending Lifecycle Runner Integration Repair
```

Minimum architecture-consistent scope:

```text
1. Add a formal runner-owned invocation point after execution when execution
   evidence says PENDING_LIFECYCLE_REQUIRED, or before marking the business day
   complete.

2. Invoke the existing Pending lifecycle component, not ad hoc state mutation.

3. Require the business day completion contract to verify that required
   lifecycle work is satisfied before appending completed_business_days.

4. Keep pending_lifecycle strict and fail-closed; if lifecycle result is
   REVIEW_REQUIRED, the runner must HALT/REVIEW_REQUIRED rather than suppressing
   Data Readiness safety.

5. Add integration regression tests for CA quarantine multi-day Historical and
   ordinary no-action/submitted-order preservation.
```

Ownership recommendation:

```text
Invocation owner: Runtime Test runner / end-of-day orchestration boundary.
State transition owner: Pending lifecycle component.
Detection producer: Execution.
Fail-closed next-day detector: Data Readiness.
```

Execution should not directly mutate Pending. Data Readiness should not be
weakened into a cleanup writer. The operator CLI remains useful for manual
repair/review, but requiring a human to run `pending_lifecycle` after every
Historical quarantine is incompatible with long unattended Historical
validation.

## Current Run Mutation

```text
NO
```

No current run `resume`, `resume --dry-run`, `fresh-run`, `run`,
`pending_lifecycle`, repair, rollback, reset, abandon, or state mutation command
was executed.

## Historical Executed

```text
NO
```

Only read-only inspection commands were used:

```text
git status / git log / git show / rg / find / sed / jq
```

No long Historical validation was executed by Codex in L20E.
