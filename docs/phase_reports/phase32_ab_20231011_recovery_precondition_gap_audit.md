# Phase32-AB 2023-10-11 Recovery Precondition Gap Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260830T081425790243Z`
- Target command audited: `recover-failed-execution --business-date 2023-10-11 --rewind-to-job morning --dry-run`
- Audit mode: READ-ONLY
- Mutating operations not executed: recovery, replay, resume, fresh-run, rollback
- File changes in this phase: this report only

## References Read

- `docs/phase_reports/phase32_z_20231011_submit_halt_root_cause_audit.md`
- `docs/phase_reports/phase32_aa_corporate_action_planning_pending_submit_authority_alignment_repair.md`
- `docs/03_operations/runtime_test_command_guide.md`
- `docs/02_architecture/runtime_test_specification.md`
- `scripts/runtime_test.py`
- Target `run_state.json`
- Current `.runtime` Pending, Ledger, Submit manifest, historical broker evidence, and corporate-action authority evidence for `2023-10-11`

## Executive Summary

The first failed recovery precondition is:

`run_state next_job is not failed execution boundary`

Implementation requires:

`run_state.next_job == "2023-10-11:execution"`

Actual target run has:

`run_state.next_job == "2023-10-11:submit"`

A second enforced precondition also fails:

`pending is not consumed failed-attempt state`

Implementation requires current Pending state `CONSUMED`; actual Pending is mixed `REVIEW_REQUIRED`, with `92460` item `CONSUMED`, `50280` item still `APPROVED`, and two BUY items `REVIEW_REQUIRED`.

The target-date Ledger shape itself matches submit-only precommit evidence: one order row exists, and no execution/position/cash/event rows exist for `2023-10-11`.

Therefore Phase32-AA's recovery classification was too broad for the existing tool. The target state is not supported by `recover-failed-execution` as currently implemented because it is a partial submit success plus later item block at Submit, not an execution-boundary failed attempt.

## Actual 2023-10-11 State

### Run State

- `status`: `HALT`
- `next_job`: `2023-10-11:submit`
- `halted_at.business_date`: `2023-10-11`
- `halted_at.job`: `submit`
- `halted_at.exit_code`: `20`
- `halt_summary.root_reason`: `corporate_action_event_not_resolved`
- Completed business days: `252`, through `2023-10-10`
- Completed jobs on `2023-10-11`:
  - `market_refresh`: exit `0`
  - `data_readiness`: exit `0`
  - `morning`: exit `0`
  - `sell_planning`: exit `0`
  - `submit`: exit `20`
- No `2023-10-11:execution` job is present.

### Current Persistent State

- `.runtime/persistent_ledger/state.json`
- `as_of`: `2023-10-10`
- `cash`: `816580`
- `buying_power`: `816580`
- Positions:
  - `66780`: `100`
  - `59660`: `100`
  - `50280`: `100`
  - `92460`: `100`

This passes the coherent recovery boundary check against the previous completed business day.

### Pending

- Pending plan id: `pending-strategy-plan-historical-2023-10-11-f650d7dcd8b7c7d7`
- Pending state: `REVIEW_REQUIRED`
- Review scope: `BUY_ITEM_SCOPED_REVIEW`
- Sell continuation allowed: `true`
- Approved item ids:
  - `strategy-b6716e1e95fc9cc0a9aa` (`50280` SELL)
  - `strategy-24ef30251cec051aac6a` (`92460` SELL)
- Review-required BUY ids:
  - `strategy-4c1cff246933bff23312` (`38560` BUY)
  - `strategy-a92ce60a05bb6b2c9cc4` (`76920` BUY)

Item states:

| Symbol | Pending Item ID | Side | Quantity | State | Batch Submit Status | Feasibility |
|---|---|---:|---:|---|---|---|
| `50280` | `strategy-b6716e1e95fc9cc0a9aa` | SELL | `100` | `APPROVED` | `PASS_ITEM_SUBMITTABLE` | `PASS` |
| `92460` | `strategy-24ef30251cec051aac6a` | SELL | `100` | `CONSUMED` | `PASS_ITEM_SUBMITTABLE` | `PASS` |
| `38560` | `strategy-4c1cff246933bff23312` | BUY | `100` | `REVIEW_REQUIRED` | `ITEM_REVIEW_REQUIRED` | `REVIEW_REQUIRED` |
| `76920` | `strategy-a92ce60a05bb6b2c9cc4` | BUY | `400` | `REVIEW_REQUIRED` | `ITEM_REVIEW_REQUIRED` | `REVIEW_REQUIRED` |

This is a mixed partial-submit Pending state, not a whole-plan `CONSUMED` failed-attempt state.

### Ledger Rows

Target-date Ledger rows in `.runtime/persistent_ledger`:

| File | 2023-10-11 row count |
|---|---:|
| `orders.jsonl` | `1` |
| `executions.jsonl` | `0` |
| `positions.jsonl` | `0` |
| `cash.jsonl` | `0` |
| `events.jsonl` | `0` |

The sole target-date order row:

- `record_id`: `ledger-order-submit-eb4911bfbcb7f197`
- `pending_plan_id`: `pending-strategy-plan-historical-2023-10-11-f650d7dcd8b7c7d7`
- `pending_item_id`: `strategy-24ef30251cec051aac6a`
- `symbol`: `92460`
- `side`: `SELL`
- `quantity`: `100`
- `status`: `ACCEPTED`
- `dedup_key`: `runtime_v2_submit:submit-command-8d63867bd2f64d35`
- `order_id`: `b95f550a15c75dbb6de73a3ef5886b9c79d990825cc42ddddd756a4d356c8733`
- `source_decision_id`: `rp-2023-10-11-92460-sell_exit-3b430763f0529b62`
- `source_pm_decision_id`: `pm-2023-10-11-92460-reduce`

There are no execution rows for `2023-10-11`.

### Submit Evidence

Submit manifest:

- `final_state`: `REVIEW_REQUIRED`
- `exit_code`: `20`
- `reason`: `submit completed with rejected/unknown/blocked items`
- `submitted_count`: `1`
- `blocked_count`: `1`
- no-order authority: `BUY_ITEM_SCOPED_REVIEW_PARTIAL_PASS_SUBMISSION`
- submitted candidates:
  - `50280` SELL
  - `92460` SELL

Item evidence:

| Symbol | Pending Item ID | Submit Status | Guard Decision | Result |
|---|---|---|---|---|
| `92460` | `strategy-24ef30251cec051aac6a` | `PASS` | `PASS` | accepted/submitted |
| `50280` | `strategy-b6716e1e95fc9cc0a9aa` | `REVIEW_REQUIRED` | `BLOCKED` | not submitted |
| `38560` | `strategy-4c1cff246933bff23312` | item-scoped review | not submitted | expected deferred BUY |
| `76920` | `strategy-a92ce60a05bb6b2c9cc4` | item-scoped review | not submitted | expected deferred BUY |

The `50280` block is the known Phase32-Z/AA corporate-action authority failure:

- `corporate_action_event_status`: `IMPACT_DETECTED`
- `corporate_action_adjustment_factor`: `0.3333333333333333`
- `corporate_action_adjustment_authority_status`: `REVIEW_REQUIRED`
- `quantity_reconciliation_status`: `REVIEW_REQUIRED`
- `price_reconciliation_status`: `REVIEW_REQUIRED`
- `already_applied_status`: `UNKNOWN`
- `violated_policy`: `corporate_action_adjustment_authority`
- `violated_policy_source`: `.runtime/runtime_state/corporate_action_adjustments/2023-10-11/50280.json`

Historical broker evidence exists for `92460` only:

- path: `.runtime/runtime_state/historical_broker/2023-10-11/d2fb9ea564f214cfe8737a1811a41780ad26c66a5083b3b296d9adb78cbe58bf.json`
- status: `ACCEPTED`
- symbol: `92460`
- side: `SELL`
- quantity: `100`
- pending item id: `strategy-24ef30251cec051aac6a`

## Enforced Recovery Preconditions

Source: `scripts/runtime_test.py`, `build_failed_execution_recovery_plan`.

| Precondition | Actual | Classification |
|---|---|---|
| Historical mutation context accepted | command reached recovery-plan precondition phase | PASS |
| `rewind_to_job` is in `("morning", "sell_planning", "submit", "execution")` | `morning` | PASS |
| Previous completed business day boundary exists | `2023-10-10` | PASS |
| Persistent state is at previous coherent boundary | state `as_of=2023-10-10` | PASS |
| Expected recovery date matches, if supplied | not supplied | NOT_APPLICABLE |
| Expected cash matches, if supplied | not supplied | NOT_APPLICABLE |
| Expected position count matches, if supplied | not supplied | NOT_APPLICABLE |
| Run state is `HALT` | `HALT` | PASS |
| Run state `next_job` is `<business-date>:execution` | actual `2023-10-11:submit` | FAIL |
| Current Pending state is `CONSUMED` | actual `REVIEW_REQUIRED` | FAIL |
| Ledger rows match failed-execution partial mutation or submit-only precommit | orders=1, executions=0, positions=0, cash=0, events=0 | PASS |
| Failed execution has negative cash row | not failed-execution mutation | NOT_APPLICABLE |
| Expected negative cash matches, if supplied | not supplied | NOT_APPLICABLE |
| Failed execution dedup keys exist | submit-only precommit has no execution keys | NOT_APPLICABLE |
| Failed execution dedup keys are not already applied to Current | no failed execution keys | NOT_APPLICABLE |
| Recovery transaction keys computable from target rows | one order transaction key present | PASS |
| Recovery history restriction | no existing recovery dir found for this run | PASS |
| Profile/runtime-root compatibility | command reached plan preconditions; target profile is historical | PASS |

First failed precondition in implementation order:

`run_state next_job is not failed execution boundary`

Second failed precondition:

`pending is not consumed failed-attempt state`

## Why Dry-Run Returned PRECONDITION_FAILURE

The operator's dry-run was rejected because the implemented `recover-failed-execution` tool only accepts two shapes:

1. Failed execution partial mutation:
   - halted at `<date>:execution`
   - Pending whole-plan state `CONSUMED`
   - four target-date execution rows
   - negative cash evidence for the failed execution path

2. Submit-only precommit halt:
   - still halted at `<date>:execution`
   - Pending whole-plan state `CONSUMED`
   - target-date order rows exist
   - no target-date execution/position/cash/event rows

The target run has only the ledger row shape of submit-only precommit. It does not have the run-state/Pending shape required by the tool:

- actual halt boundary is `2023-10-11:submit`, not `2023-10-11:execution`
- Pending whole-plan state is `REVIEW_REQUIRED`, not `CONSUMED`
- only one item, `92460`, is consumed
- `50280` remains approved but blocked
- two BUY items remain explicitly reviewed

## Phase32-AA Classification Check

`WAS_PHASE32_AA_RECOVERY_CLASSIFICATION_INCORRECT`: YES.

Phase32-AA correctly identified that `recover-stale-pending` is inappropriate because target-date Ledger rows exist. However, it incorrectly concluded that existing `recover-failed-execution` covered the actual state.

The missing distinction is:

`submit-only precommit halt` in the current recovery tool means whole Pending consumed and run_state at execution boundary, not partial submit success followed by a blocked approved item during Submit.

## Partial Submit Tooling Support

`DOES_EXISTING_RECOVERY_TOOLING_SUPPORT_PARTIAL_SUBMIT_HALTS`: NO.

Existing tests cover:

- failed execution recovery with whole Pending `CONSUMED`
- submit-only precommit recovery with whole Pending `CONSUMED`
- stale Pending recovery with no target-date Ledger rows

No existing recovery path formally covers:

`partial submit success + later approved item block + run HALT at submit`

The missing lifecycle/recovery contract is:

- preserve or reconcile already accepted target-date order `92460`
- guarantee `92460` is never duplicated
- avoid deleting or replaying accepted external/simulated broker evidence without an accepted idempotent reconciliation contract
- regenerate/reclassify the remaining same-day Pending items under current source so `50280` becomes corporate-action `REVIEW_REQUIRED` before Submit
- replay only the safe unresolved portion or reconstruct the day with already accepted item exclusion
- leave completed days through `2023-10-10` intact

## Canonical Recovery Classification

`RECOVERY_TOOLING_GAP`

The concrete missing path is a partial submit recovery path. A future implementation may name it `PARTIAL_SUBMIT_RECOVERY_REQUIRED`, but that is not currently an existing canonical mutating procedure.

## Repair Gate

Recovery tooling repair required: YES.

Narrowest repair scope:

- Add or extend scoped recovery to recognize `HALT` at `<date>:submit` with:
  - target-date order rows present
  - no target-date execution/position/cash/event rows
  - Pending state `REVIEW_REQUIRED`
  - at least one item `CONSUMED` with accepted order evidence
  - at least one approved/not-submitted item blocked by canonical submit guard
- Preserve idempotency for already accepted `92460`:
  - do not duplicate the existing accepted order
  - either retain and mark it as already accepted for replay exclusion or formally rewind it only with explicit accepted evidence retirement and dedup-key quarantine
- Regenerate or replay the unaccepted portion under Phase32-AA so `50280` is reviewed before Submit.
- Add focused tests for partial submit HALT recovery dry-run, actual recovery, replay exclusion/idempotency, and rejection when accepted order evidence cannot be reconciled.

Strategy semantic change required: NO.

Completed 252BD validity unchanged: YES.

## Existing Paths Rejected

- `NORMAL_RESUME`: not safe. The run is halted at Submit with mixed Pending and an already accepted order. Resume would risk re-entering submit lifecycle without a formal idempotent partial-submit recovery contract.
- `RECOVER_FAILED_EXECUTION`: not supported by current preconditions.
- `RECOVER_STALE_PENDING`: not applicable because target-date Ledger rows exist.
- `FRESH_RUN_REQUIRED`: not required by this evidence alone. The gap is tooling coverage, not completed-window contamination.

## Recommended Next Operator Action

Do not run the existing recovery commands for this run yet.

Next action should be a narrow recovery-tooling repair phase for:

`partial submit success + later item block + run HALT at submit`

After that repair exists, the first operator command should be a dry-run of the new or extended canonical partial-submit recovery path. No current command is confirmed safe for this state.

## No Future Information Use

Confirmed. This audit used only run evidence, current `.runtime` state, source implementation, and documentation. No future price, future return, future regime, MFE/MAE, final campaign outcome, or historical profitability was used.

## Final Judgment

1. `WHICH_PRECONDITION_FAILED`
   - First: `run_state next_job is not failed execution boundary`.
   - Also failed: `pending is not consumed failed-attempt state`.

2. `WHY_RECOVER_FAILED_EXECUTION_DRY_RUN_RETURNED_PRECONDITION_FAILURE`
   - Because the tool requires `next_job=2023-10-11:execution` and whole Pending `CONSUMED`, while the actual run is halted at `2023-10-11:submit` with mixed partial-submit Pending.

3. `WAS_PHASE32_AA_RECOVERY_CLASSIFICATION_CORRECT`
   - NO. It correctly rejected stale-pending recovery, but incorrectly assumed `recover-failed-execution` covers this partial submit HALT shape.

4. `DOES_EXISTING_RECOVERY_TOOLING_SUPPORT_PARTIAL_SUBMIT_HALTS`
   - NO.

5. `IS_A_RECOVERY_TOOLING_REPAIR_REQUIRED`
   - YES.

6. `IS_NORMAL_RESUME_SAFE`
   - NO.

7. `IS_FRESH_RUN_REQUIRED`
   - NO, not from current evidence alone.

8. `ARE_COMPLETED_252BD_STILL_VALID`
   - YES.

9. `WHAT_IS_THE_CANONICAL_NEXT_OPERATOR_ACTION`
   - Do not run current recovery/resume commands. Implement a narrow partial-submit recovery tooling repair, then dry-run that canonical path.

`PHASE32_AB_PARTIAL_SUBMIT_RECOVERY_TOOLING_GAP_IDENTIFIED`
