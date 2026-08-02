# Phase24-A0 BU Post-repair Close Runtime Revalidation Entry Gate Preparation

## 1. Primary Judgment

`PHASE24_A0_ENTRY_GATE_PREPARATION_REVIEW_REQUIRED`

BU Close Authority contract itself is readable and internally consistent, but the Operator runtime entry gate is not yet `OPERATOR_RUNTIME_READY` because the current canonical `plan` preflight for the recommended 2022-07-01 to 2022-07-14 10BD window returns `PLAN_REVIEW_REQUIRED`.

Observed preflight blockers are source/readiness and baseline review items, not a BU Close classification regression:

- `baseline_compatibility_status=REVIEW_REQUIRED`
- `strategy_shadow.operator_ready=false`
- `strategy_shadow.source_preflight.judgment=NOT_ELIGIBLE_SOURCE_COVERAGE`
- root blockers include `market_coverage`, `listed_coverage`, `corporate_event_coverage`, `candidate_generation_readiness`, `opportunity_generation_readiness`, and `sector_coverage`

No Runtime execution, fresh-run, resume, Broker Write, Runtime Switch, J-Quants fetch, Strategy parameter change, or code repair was performed.

## 2. Reviewed Documents

- `docs/phase_reports/phase23_to_phase24_chatgpt_handoff.md`
- `docs/phase_reports/phase23_final_summary_and_phase24_handoff.md`
- `docs/phase_reports/phase23_bv_phase21_design_conformance_full_architecture_runtime_evidence_closure_review.md`
- `docs/phase_reports/phase23_bu_close_authority_strategy_shadow_review_classification_repair.md`
- `docs/phase_reports/phase23_bt_2022_10bd_full_completion_close_review_required_audit.md`
- `docs/01_requirements/phase_roadmap.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/03_operations/runtime_test_command_guide.md`
- `scripts/runtime_test.py`
- `tests/runtime_v2/test_phase23_j_strategy_authority_gate.py`

## 3. BU Repair Contract Summary

Phase23-BU added Close Authority classification in `scripts/runtime_test.py`:

- `_production_planning_authority_gate_status()`
- `_strategy_shadow_blocks_operational_close()`
- `_strategy_review_status()`
- `_strategy_shadow_close_review_classification()`
- `_close_authority_classification()`

`close_command()` now writes these fields into `final_summary.json`:

- `operational_status`
- `strategy_review_status`
- `final_runtime_judgment`
- `close_authority_judgment`
- `close_authority_classification`
- `strategy_shadow_review_required`
- `strategy_shadow_close_classification`
- `production_planning_judgment`
- `trading_state_judgment`
- `accounting_state_judgment`
- `runtime_execution_judgment`

The key contract is:

```text
Trading / Accounting / Runtime execution / Production Planning / Historical Authority non-PASS
  -> final_runtime_judgment is non-PASS

Non-mutating Strategy Shadow REVIEW_REQUIRED only
  -> final_runtime_judgment = PASS
  -> operational_status = PASS
  -> strategy_review_status = REVIEW_REQUIRED
```

## 4. Canonical Close State Model

Close owner:

```text
scripts/runtime_test.py::close_command()
```

Close flow:

```text
load run_state
-> validate_command()
-> PM fatal evidence check
-> final_state_snapshot
-> update_run_strategy_shadow_indexes()
-> _strategy_planning_authority_run_summary()
-> _runtime_halt_summary()
-> validate_historical_evaluation_authority()
-> _close_authority_classification()
-> write final_summary.json
```

Exit code mapping in `close_command()`:

```text
status PASS -> 0
status REVIEW_REQUIRED or BLOCK -> 10
```

General runner exit code constants:

```text
0  PASS
10 REVIEW_REQUIRED
20 BLOCKED
30 HALT
40 VALIDATION_FAILURE
70 PRECONDITION_FAILURE
80 TEST_INVALID
90 INTERNAL_ERROR
```

## 5. Operational / Trading / Accounting / Strategy Review Separation

| Axis | Canonical field | Owner / source | PASS condition |
|---|---|---|---|
| Operational completion | `operational_status`, `runtime_execution_judgment`, `run_state.status` | `close_command()`, `run_state.json` | run state is `COMPLETED` or formally handled `HALT`, and final runtime judgment is PASS |
| Trading state | `trading_state_judgment` | `validate_command()` result through `_close_authority_classification()` | validation exit code is `0`, no PM fatal evidence |
| Accounting state | `accounting_state_judgment` | `validate_command()` result through `_close_authority_classification()` | validation exit code is `0`, no PM fatal evidence |
| Production planning | `production_planning_judgment` | `_strategy_planning_authority_run_summary()` | no broker write, no runtime switch, authority status not BLOCK/REVIEW |
| Strategy review | `strategy_review_status` | `_strategy_review_status()` | `PASS`, `REVIEW_REQUIRED`, `BLOCK`, or `NOT_EVALUATED`; preserved separately from operational status |
| Strategy Shadow review | `strategy_shadow_review_required`, `strategy_shadow_close_classification` | `strategy_shadow_summary.json`, daily strategy artifacts | non-mutating review is recorded; mutation or production-consumer conflict remains blocking |

## 6. Strategy Shadow Non-mutating Verification

Plan evidence and existing run evidence identify Strategy Shadow as non-mutating:

```text
execution_order = after_daily_runtime_jobs
mutation_policy = read_only_no_pending_ledger_current_registry_or_accepted_generation_mutation
active_runtime_consumer_eligibility = NO
runtime_switch_performed = false
```

Existing 2022-07-14 run evidence:

```text
strategy_shadow_judgment = REVIEW_REQUIRED
runtime_mutation_performed = false
broker_write_performed = false
runtime_switch_performed = false
runtime_judgment = UNCHANGED_BY_STRATEGY_SHADOW
reason = existing_pending_conflict:23880
```

BU tests preserve negative cases:

- Strategy Shadow `BLOCK` remains blocking.
- Strategy Shadow `REVIEW_REQUIRED` marked as active production consumer remains blocking.
- Production planning `REVIEW_REQUIRED` remains non-PASS.
- Trading validation non-PASS remains non-PASS.

## 7. Canonical Runtime Command

Recommended revalidation target remains the BT/BV comparable window:

```text
2022-07-01 to 2022-07-14
10 business days
initial cash = 1,000,000 JPY
profile = historical-smoke
```

Canonical Operator command after preflight blockers are resolved:

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src

python3 scripts/runtime_test.py fresh-run \
  --profile historical-smoke \
  --date-from 2022-07-01 \
  --date-to 2022-07-14 \
  --business-days 10 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

Rationale:

- Same dates as the Phase23-BT/BV evidence.
- Includes BUY_NEW, BUY_ADD / PM ADD, SELL_EXIT, carry-forward positions, cash debit/credit, ledger append, realized PnL, current valuation.
- Specifically targets the original 2022-07-14 Strategy Shadow `existing_pending_conflict:23880` Close scenario.

1BD/short fixture is sufficient for the unit-level BU contract, but not sufficient for Phase24 entry revalidation because it does not prove the full BT trading/accounting lifecycle and consumed pending conflict recurrence.

## 8. Preflight Commands and Requirements

Read-only preflight commands:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --help
PYTHONPATH=src python3 scripts/runtime_test.py plan \
  --profile historical-smoke \
  --date-from 2022-07-01 \
  --date-to 2022-07-14 \
  --business-days 10 \
  --json
PYTHONPATH=src python3 scripts/runtime_test.py run-status --profile historical-smoke --json
PYTHONPATH=src python3 scripts/runtime_test.py system-status --profile historical-smoke --scope readiness --json
PYTHONPATH=src python3 scripts/runtime_test.py system-status --profile historical-smoke --scope data --json
PYTHONPATH=src python3 scripts/runtime_test.py system-status --profile historical-smoke --scope ai --json
```

Preflight requirements:

- Accepted Generation resolves with `accepted_generation_readiness.status=PASS`.
- `plan.window_resolution_status=PASS`.
- `plan.request_conformance_status=PASS`.
- Historical logical source materialization must be available for all requested business dates.
- Market Context source must resolve PIT.
- Corporate Event source must resolve PIT or explicit approved exception evidence must be present.
- Calendar authority must cover all dates.
- Valuation authority must cover fill/valuation dates.
- No active run blocks `fresh-run`.
- Output run id must be new.
- Existing `.runtime` state must be compatible or fresh-run reset must establish a clean state.
- Production/Demo broker/write configuration must not be used.

Current preflight result:

```text
plan status = PLAN_REVIEW_REQUIRED
exit_code = 10
baseline_compatibility_status = REVIEW_REQUIRED
strategy_shadow.operator_ready = false
strategy_shadow.source_preflight.judgment = NOT_ELIGIBLE_SOURCE_COVERAGE
```

This must be reviewed before Operator executes the 10BD fresh-run.

## 9. Expected Artifacts

| Artifact | Canonical path | Producer | Consumer | Confirmation fields | Expected value | Evidence role |
|---|---|---|---|---|---|---|
| Run state | `reports/runtime_tests/runs/<run_id>/run_state.json` | Runtime Test runner | close, summarize, reviewer | `status`, `completed_business_days`, `current_step`, `halted_at` | `COMPLETED`, 10 dates, no halt | Required |
| Plan | `reports/runtime_tests/runs/<run_id>/plan.json` | `plan_command()` | run, reviewer | `requested_start_date`, `requested_end_date`, `requested_business_days`, `resolved_business_dates`, `strategy_shadow` | 2022-07-01/2022-07-14/10 | Required |
| Fresh-run summary | `reports/runtime_tests/runs/<run_id>/fresh_run_summary.json` | `fresh_run_command()` | reviewer | `status`, `exit_code`, `steps`, `failed_step`, `run_id` | PASS if full chain closes PASS | Required |
| Final summary / close summary | `reports/runtime_tests/runs/<run_id>/final_summary.json` | `close_command()` | summarize, reviewer | BU Close fields listed above | see Section 10 | Required |
| Run-level Strategy Shadow | `reports/runtime_tests/runs/<run_id>/strategy_shadow_summary.json` | `update_run_strategy_shadow_indexes()` | close, summarize | `strategy_shadow_judgment`, `review_required_dates`, `runtime_mutation_performed` | PASS or non-mutating REVIEW_REQUIRED | Required |
| Daily Strategy Shadow | `reports/runtime_tests/runs/<run_id>/daily/<date>/strategy/strategy_shadow_summary.json` | Strategy shadow job | run-level shadow summary | `runtime_mutation_performed`, `runtime_judgment`, `active_runtime_consumer_eligibility` | no mutation, not active production consumer | Required |
| Runtime planning shadow | `reports/runtime_tests/runs/<run_id>/daily/2022-07-14/strategy/runtime_planning.json` | Strategy shadow job | strategy trace, reviewer | `producer_result_status`, `validation_status`, `reason_codes` | PASS or REVIEW_REQUIRED with explicit reasons | Required |
| Morning planning authority | `reports/runtime_tests/runs/<run_id>/daily/<date>/morning/strategy_planning_authority_evidence.json` | morning Runtime | close planning summary | `status`, `planning_consumer_eligibility`, `broker_write_performed`, `runtime_switch_performed` | PASS or NO_ORDER_AUTHORIZED, no write/switch | Required |
| Pending order artifact | `reports/runtime_tests/runs/<run_id>/final_state_snapshot/pending_order_plan/pending_order_plan.json` and daily Pending evidence | Runtime pending pipeline | submit, execution, reviewer | `state`, `items`, `origin_run_id`, policy hashes | final consumed/empty as expected | Required |
| Fill artifact | `reports/runtime_tests/runs/<run_id>/daily/<date>/execution/fills.json` | execution job | ledger/current update | fill side, symbol, quantity, price | BT trade inventory reproduced or explained | Required |
| Ledger append evidence | `reports/runtime_tests/runs/<run_id>/daily/<date>/execution/ledger_append_evidence.json` | execution job | accounting review | append status, cash/position effects | PASS | Required |
| Final Current / Ledger | `reports/runtime_tests/runs/<run_id>/final_state_snapshot/persistent_ledger/state.json` | close snapshot | reviewer | cash, positions, realized/unrealized PnL, total equity | reconciled | Required |
| Current valuation | `reports/runtime_tests/runs/<run_id>/daily/<date>/current_valuation_refresh/valuation_apply_evidence.json` | valuation job | accounting review | valuation status, market value | PASS | Required |
| HALT summary | `final_summary.halt_summary` and run evidence if halted | runner | reviewer | `status`, `halted_business_date`, `root_reason` | `NOT_HALTED` for PASS | Required if non-PASS |
| System status | command output or evidence from `system-status` | `system_status_command()` | reviewer | scope judgments, readiness | context-specific PASS/REVIEW | Supporting |

## 10. Expected Status Fields

Expected successful BU revalidation with non-mutating Strategy Shadow review:

```text
final_summary.status = PASS
final_summary.final_runtime_judgment = PASS
final_summary.final_judgment = PASS
final_summary.operational_status = PASS
final_summary.close_authority_judgment = PASS
final_summary.trading_state_judgment = PASS
final_summary.accounting_state_judgment = PASS
final_summary.runtime_execution_judgment = PASS
final_summary.production_planning_judgment = PASS
final_summary.strategy_review_status = REVIEW_REQUIRED or PASS
final_summary.strategy_shadow_review_required = true or false
final_summary.strategy_shadow_close_classification = NON_MUTATING_STRATEGY_SHADOW_REVIEW_NON_BLOCKING or PASS
final_summary.halt_summary.status = NOT_HALTED
```

If Strategy Shadow review does not recur:

```text
strategy_review_status = PASS
strategy_shadow_review_required = false
strategy_shadow_close_classification = PASS
```

If only Strategy Shadow review recurs:

```text
strategy_review_status = REVIEW_REQUIRED
strategy_shadow_review_required = true
strategy_shadow_close_classification = NON_MUTATING_STRATEGY_SHADOW_REVIEW_NON_BLOCKING
final_runtime_judgment = PASS
operational_status = PASS
```

## 11. Expected Exit Codes

| Case | Close status | Process exit code | Notes |
|---|---|---:|---|
| Full PASS | `PASS` | `0` | Expected if all operational axes pass, including Strategy Shadow PASS |
| Operational PASS + non-mutating Strategy Shadow REVIEW_REQUIRED only | `PASS` | `0` | BU target contract |
| Production planning REVIEW_REQUIRED | `REVIEW_REQUIRED` | `10` | Still non-PASS |
| Trading/accounting validation non-PASS | `REVIEW_REQUIRED` | `10` | Operational PASS cannot be claimed |
| Strategy Shadow BLOCK or production-consumer conflict | `BLOCK` via final summary, close command returns non-PASS code `10` | `10` | Classification is blocking even though close exit uses REVIEW code for non-PASS |
| Runner BLOCKED | `BLOCKED` | `20` | Runner-level fail-closed precondition |
| HALT during run | `HALT` | `30` | Fresh-run stops before close if step fails |
| Precondition failure | `PRECONDITION_FAILURE` | `70` | Missing run, invalid state, active run conflict |

## 12. PASS / REVIEW_REQUIRED / FAIL Criteria

PASS:

- Requested 10 business days all completed.
- No early HALT.
- Trading state PASS.
- Accounting state PASS.
- Runtime execution PASS.
- Production planning PASS.
- Cash / Ledger / Position / Valuation reconciled.
- Strategy Shadow did not mutate Pending, Ledger, Current, Registry, Accepted Generation, Broker, or Runtime Switch state.
- Strategy Review is preserved independently when present.
- Close fields show operational status is not overwritten by non-mutating Strategy Shadow review.
- Exit code matches status contract.

REVIEW_REQUIRED:

- Any current preflight returns `PLAN_REVIEW_REQUIRED` or source coverage review before Operator run.
- Operational / Trading / Accounting pass but production planning is not PASS.
- Operator evidence is incomplete.
- Strategy Shadow review reason is present but classification cannot prove non-mutating / non-production-consumer status.

For Phase24 entry, `Operational PASS + Strategy Shadow REVIEW_REQUIRED only` is acceptable as PASS if `final_runtime_judgment=PASS` and the BU separation fields are present.

FAIL / REPAIR_REQUIRED:

- Runtime HALT.
- Trading/accounting inconsistency.
- Cash / Ledger / Position quantity mismatch.
- Shadow mutates Production Pending, Ledger, Current, Broker, Registry, Accepted Generation, or Runtime Switch state.
- Shadow review overwrites operational status.
- `final_runtime_judgment`, `operational_status`, and exit code disagree.
- Future/latest fallback, zero fill, silent fallback, forced PASS, or authority fail-open is observed.

## 13. Operator Execution Procedure

Do not run until the current `PLAN_REVIEW_REQUIRED` preflight is reviewed.

1. Confirm no active run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py run-status --profile historical-smoke --json
```

2. Confirm plan/preflight:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py plan \
  --profile historical-smoke \
  --date-from 2022-07-01 \
  --date-to 2022-07-14 \
  --business-days 10 \
  --json
```

3. If and only if preflight is accepted by ChatGPT/Operator review, run:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-smoke \
  --date-from 2022-07-01 \
  --date-to 2022-07-14 \
  --business-days 10 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

4. Submit evidence listed in Section 14.

5. If the run returns non-PASS, do not rerun repeatedly. Preserve the run id and submit evidence.

## 14. Evidence Submission Checklist

Operator should provide:

- `run_id`
- exact command
- start/end date
- requested business day count
- completed business day count
- process exit code
- `run-status --json` output
- `system-status --scope runtime --json` output
- `system-status --scope readiness --json` output
- `final_summary.json`
- `fresh_run_summary.json`
- `run_state.json`
- `plan.json`
- `strategy_shadow_summary.json`
- `daily/2022-07-14/strategy/strategy_shadow_summary.json`
- `daily/2022-07-14/strategy/runtime_planning.json`
- `daily/2022-07-14/morning/strategy_planning_authority_evidence.json`
- final state snapshot manifest and `persistent_ledger/state.json`
- final pending snapshot
- execution fills and ledger append evidence for trade days
- current valuation evidence for final day
- HALT summary if any
- error/warning list

## 15. Risks / Gaps

- Current 2022-07-01 to 2022-07-14 `plan` preflight returns `PLAN_REVIEW_REQUIRED`. This blocks `OPERATOR_RUNTIME_READY` for this task.
- Two read-only `plan` checks created ignored run-plan evidence under `reports/runtime_tests/runs/`; no Runtime jobs were executed.
- Existing target run `runtime-test-historical-smoke-20260730T211110605880Z` was closed before BU and lacks the new BU fields in `final_summary.json`.
- BU evidence includes a static reproduction of the Close classification, but not a fresh Operator 1BD/10BD runtime rerun after BU.
- 1BD would prove the Close code path only; 10BD is still recommended for lifecycle-comparable Phase24 entry evidence.

## 16. Runtime Execution Prohibition Confirmation

Not executed:

- 1BD / 10BD / 20BD / 60BD / 200BD / 1y / 3y Runtime
- `fresh-run` actual run
- `run`
- `resume`
- Broker Write
- Runtime Switch
- J-Quants fetch
- Production/Demo submit
- Strategy/performance parameter change
- code repair

Executed read-only / short checks:

| Command | Result | Scope |
|---|---|---|
| `PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --help` | exit 0 | CLI option confirmation |
| `PYTHONPATH=src python3 scripts/runtime_test.py close --help` | exit 0 | CLI option confirmation |
| `PYTHONPATH=src python3 scripts/runtime_test.py system-status --help` | exit 0 | CLI option confirmation |
| `PYTHONPATH=src python3 scripts/runtime_test.py plan --profile historical-extended-smoke --date-from 2022-07-01 --date-to 2022-07-14 --business-days 10 --json` | exit 10 | read-only plan; `PLAN_REVIEW_REQUIRED` |
| `PYTHONPATH=src python3 scripts/runtime_test.py plan --profile historical-smoke --date-from 2022-07-01 --date-to 2022-07-14 --business-days 10 --json` | exit 10 | read-only plan; `PLAN_REVIEW_REQUIRED` |

## 17. Recommended Next Action

ChatGPT should review the `PLAN_REVIEW_REQUIRED` preflight and decide whether this is:

```text
PRE_RUN_BASELINE_REVIEW_EXPECTED_BEFORE_FRESH_RUN
```

or

```text
PHASE24_A0_ENTRY_GATE_BLOCKED_REPAIR_REQUIRED
```

Do not proceed to Operator 10BD until the preflight status is explicitly accepted or repaired.
