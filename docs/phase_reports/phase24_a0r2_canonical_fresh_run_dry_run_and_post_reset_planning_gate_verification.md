# Phase24-A0R2 Canonical Fresh-Run Dry-Run and Post-Reset Planning Gate Verification

## 1. Primary Judgment

`PHASE24_A0R2_MULTIPLE_GAPS_CONFIRMED`

Dry-run limitation, source preflight contract mismatch, and current Corporate Event entry-gate incompleteness all remain relevant. No actual Runtime execution or mutating lifecycle command was performed.

## 2. Executive Summary

`fresh-run --dry-run` succeeded for both `historical-smoke` and `historical-extended-smoke` with exit code `0`, but the implementation shows that dry-run does not execute backup, reset, or `plan_command()`. It builds a non-persisted `build_plan()` preview against the current runtime root, returns planned step statuses, and validates Plan namespace/run-id construction only.

Therefore, dry-run does not model a clean post-reset baseline and cannot prove that actual fresh-run's post-reset `plan_command()` will pass. This matches the Command Guide statement that dry-run validates Plan request construction and Runtime Test run id generation without writing plan evidence or mutating Runtime state.

The stale `.runtime` baseline detected in A0R1 is expected to be resolved by actual fresh-run's reset path because actual fresh-run executes `backup -> reset -> plan`, and reset rewrites Current/Ledger/Pending/Runtime operational state to clean initial state with logical position date set to the planned start date. However, this was not executed in A0R2.

Source preflight remains a separate blocker/review area. Current preflight still treats shared canonical Historical source coverage and pre-existing candidate/opportunity outputs as pre-run hard requirements, while Phase23-BT evidence shows actual 2022 10BD execution used run-scoped `historical_asof` manifests generated during daily `market_refresh`, and candidate/opportunity artifacts were runtime-generated downstream artifacts.

Corporate Event gate is not Operator-ready under the current Command Guide. Phase23-BT daily evidence contains Corporate Event/PIT PASS artifacts for the 2022 window, but current `.runtime/strategy_artifacts/corporate_event/` only contains 2026 dates, and the guide requires per-window Corporate Event validation artifacts and review before 10BD/20BD execution.

## 3. Reviewed Documents

- `docs/phase_reports/phase24_a0_bu_post_repair_close_runtime_revalidation_entry_gate_preparation.md`
- `docs/phase_reports/phase24_a0r1_historical_10bd_plan_preflight_source_readiness_root_cause_audit.md`
- `docs/phase_reports/phase23_to_phase24_chatgpt_handoff.md`
- `docs/phase_reports/phase23_final_summary_and_phase24_handoff.md`
- `docs/phase_reports/phase23_bv_phase21_design_conformance_full_architecture_runtime_evidence_closure_review.md`
- `docs/phase_reports/phase23_bt_2022_10bd_full_completion_close_review_required_audit.md`
- `docs/phase_reports/phase23_bu_close_authority_strategy_shadow_review_classification_repair.md`
- `docs/03_operations/runtime_test_command_guide.md`
- `docs/03_operations/jquants_data_operations_runbook.md`
- `docs/02_architecture/runtime_test_specification.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/01_requirements/phase_roadmap.md`
- `scripts/runtime_test.py`
- `src/ai_fund_lab_v2/strategy/historical_source_foundation.py`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/reset_plan.py`
- `config/runtime_tests/historical_smoke_5bd.json`
- `config/runtime_tests/historical_extended_smoke_10bd.json`
- Targeted tests under `tests/runtime_v2/`

## 4. Commands Executed

| Command | Exit | Scope | Result | Mutation |
|---|---:|---|---|---|
| `PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-smoke --date-from 2022-07-01 --date-to 2022-07-14 --business-days 10 --initial-cash 1000000 --dry-run --json` | 0 | dry-run lifecycle | `status=DRY_RUN`, `plan_result=PLANNED_NO_WRITE`, `reset_result=PLANNED_NO_MUTATION` | No Runtime/evidence mutation |
| `PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-extended-smoke --date-from 2022-07-01 --date-to 2022-07-14 --business-days 10 --initial-cash 1000000 --dry-run --json` | 0 | dry-run lifecycle/profile comparison | Same dry-run behavior as `historical-smoke` | No Runtime/evidence mutation |
| `PYTHONPATH=src python3 scripts/runtime_test.py run-status --profile historical-smoke --json` | 0 | current runtime state | `run_status=IDLE`, current date remains `2022-07-14` | Read-only |
| `test -e reports/runtime_tests/runs/<dry-run-run-id>` | 1 | evidence write check | Dry-run evidence dirs were not created | Read-only |
| `PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase18v_runtime_test_fresh_run.py::test_phase18v_fresh_run_dry_run_has_full_plan_and_no_mutation tests/runtime_v2/test_phase19_bh_fresh_run_namespace.py::test_phase19_bh_fresh_run_dry_run_validates_plan_request_contract` | 0 | targeted tests | `2 passed in 2.95s` | Test temp dirs only |
| `rg`, `sed`, `jq`, `find`, `git status --short` | 0/1 | source/evidence inspection | Implementation and existing evidence inspected | Read-only |

The dry-run commands emitted Arrow `sysctlbyname` warnings in the sandbox, but both commands completed with exit code `0`.

## 5. Current Runtime State

After dry-run:

| Field | Value |
|---|---|
| `run_status` | `IDLE` |
| `active_test_run` | empty |
| Current business date | `2022-07-14` |
| Current cash / buying power | `474680.0` / `474680.0` |
| Positions count | `3` |
| Pending state | `CONSUMED` |
| Runtime state | `CURRENT_STATE_LOADED` |
| Latest backup | `backup-historical-smoke-20260730T211101820007Z` |

Dry-run did not reset this state. This confirms dry-run does not model a post-reset `.runtime`.

## 6. Canonical Fresh-run Lifecycle

Fresh-run implementation owner: `scripts/runtime_test.py::fresh_run_command()`.

Actual fresh-run sequence:

```text
status -> backup -> reset -> plan -> run -> validate -> close
```

Actual fresh-run differs from dry-run at the key planning point:
- Dry-run calls `build_plan()` once before any reset and does not attach `baseline_compatibility`.
- Actual fresh-run performs `backup_command()`, `reset_command()`, validates reset clean-state invariant, then calls `plan_command()` against the reset runtime root.
- `plan_command()` is the function that adds `baseline_compatibility`, persists `plan.json`, and can return `PLAN_REVIEW_REQUIRED`.

## 7. Fresh-run Dry-run Result

| Profile | Requested Window | Exit | Dry-run Status | Window Resolution | Plan Behavior | Evidence Write |
|---|---|---:|---|---|---|---|
| `historical-smoke` | `2022-07-01` to `2022-07-14`, 10BD | 0 | `DRY_RUN` | `PASS`, 10 dates | `PLANNED_NO_WRITE` | No |
| `historical-extended-smoke` | `2022-07-01` to `2022-07-14`, 10BD | 0 | `DRY_RUN` | `PASS`, 10 dates | `PLANNED_NO_WRITE` | No |

Profile comparison:

| Item | `historical-smoke` | `historical-extended-smoke` | Interpretation |
|---|---|---|---|
| Configured profile business days | 5 | 10 | Extended is the config-level 10BD profile |
| Configured profile window | `2026-07-06` to `2026-07-10` | `2026-06-29` to `2026-07-10` | Both were overridden by explicit 2022 dates in dry-run |
| Phase23-BT comparable profile | Yes | No | Phase23-BT/A0 target command uses `historical-smoke` |
| Command Guide current 10BD example | Not primary example | Yes | Current generic 10BD example uses extended |
| 2022 10BD dry-run accepted count | 10 | 10 | Both resolve the requested window |
| Reset scope | Same implementation | Same implementation | No profile-specific reset difference found |
| Source preflight behavior | Same `build_plan()` path | Same `build_plan()` path | Dry-run does not expose full preflight details in summary |

Conclusion:
- For Phase23-BT comparability, `historical-smoke` remains the correct target.
- For generic current 10BD lifecycle examples, `historical-extended-smoke` is the config-level 10BD profile.
- A0R2 therefore records both, without switching the canonical BT-comparable target by inference.

## 8. Dry-run Authority And Limitations

Primary dry-run classification:

`DRY_RUN_PARTIAL_VALIDATION_ONLY`

Rationale:
- Dry-run validates command namespace, requested window resolution, run id generation, external-effect policy, and no-mutation behavior.
- Dry-run does not execute backup.
- Dry-run does not execute reset.
- Dry-run does not call `plan_command()`.
- Dry-run does not compute `baseline_compatibility`.
- Dry-run does not persist `plan.json`.
- Dry-run does not prove source preflight or Corporate Event Operator gate readiness.

Dry-run does not falsely return `PLAN_REVIEW_REQUIRED` from stale `.runtime`; it simply avoids the baseline compatibility check. That means it is not Case B exactly. It is Case C: partial validation only.

## 9. Clean Reset Contract

Reset implementation owner:
- `scripts/runtime_test.py::reset_command()`
- `scripts/runtime_test.py::apply_reset()`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/reset_plan.py`

Resettable paths include:
- `persistent_ledger/state.json`
- `persistent_ledger/orders.jsonl`
- `persistent_ledger/executions.jsonl`
- `persistent_ledger/positions.jsonl`
- `persistent_ledger/cash.jsonl`
- `persistent_ledger/events.jsonl`
- `pending_order_plan/pending_order_plan.json`
- `pending_order_plan/history`
- `runtime_state/current_state.json`
- `runtime_state/authoritative_pending_apply_candidate`
- `runtime_state/human_approval`
- `runtime_state/human_review`
- `runtime_state/historical_broker`
- `runtime_state/pending_promotion_candidate`
- `runtime_state/broker_readonly`
- `runtime_state/current_migration`
- `runtime_state/current_valuation`
- `runtime_state/data_readiness`
- `runtime_state/position_management`
- `runtime_state/safety`
- `runtime_state/run_manifest`
- `runtime_state/logs`
- `runtime_state/market`
- `runtime_state/morning_pipeline`
- `operations/feature_date_contract`
- `operations/feature_consumer_readiness`
- `operations/feature_artifacts`
- `operations/feature_refresh`
- `operations/market_refresh`
- `broker/sync_results`

Excluded prefixes include:
- `artifact_registry`
- `artifacts`
- `operations/jquants`
- `phase9/canonical_data`
- `data/raw`
- `candidate_ai`
- `opportunity_ai`
- `configs`

Actual fresh-run passes `initial_position_state_date=plan_preview.requested_start_date` into reset. For the 2022 target, reset should bind `business_date`, logical `as_of`, and `position_state_as_of` to `2022-07-01` while using wall-clock timestamps for creation/update metadata.

## 10. A0R1 Mismatch Resolution Matrix

| Mismatch | Current Cause | Reset Outcome | Post-reset Expected State | Blocking After Reset? | Evidence |
|---|---|---|---|---|---|
| `current_state_date_future` | Current ledger state business date is `2022-07-14` while requested start is `2022-07-01` | Reset rewrites `persistent_ledger/state.json` | `business_date=2022-07-01`, positions `[]`, cash/buying power `1000000` | Expected no | `apply_reset()` writes clean current with logical date |
| `ledger_date_future` | Ledger JSONL/state reflects completed prior 10BD | Reset truncates ledger JSONL files and rewrites clean state | Empty orders/executions/positions/cash/events plus clean current | Expected no | `RESETTABLE_RELATIVE_PATHS`, `apply_reset()` |
| `pending_foreign_runtime_test_run_id` | Pending metadata belongs to previous run id | Reset rewrites pending slot | `state=EMPTY`, `active_pending=false`, no previous run binding | Expected no | `apply_reset()` pending write |
| `pending_safety_business_date_future` | Safety mutable state retained from prior final date | Reset removes `runtime_state/safety` | No stale safety mutable state | Expected no | resettable path includes `runtime_state/safety` |
| `pending_target_date_future` | Pending target date from prior consumed plan | Reset rewrites pending slot | No target date / empty pending state | Expected no | `apply_reset()` pending write |

Important limit:
- A0R2 did not execute reset. These are implementation-derived expected outcomes, not fresh evidence from a real reset.

## 11. Standalone Plan Vs Fresh-run Internal Plan

Classification:

`FRESH_RUN_INTERNAL_PLAN_IS_AUTHORITATIVE`

With caveat:
- Standalone `plan` checks compatibility against the current runtime root and can reasonably return `PLAN_REVIEW_REQUIRED` when the shared root is still at a later business date.
- Actual `fresh-run` is designed to create a backup, clean reset the root, and then call `plan_command()` on the reset state.
- Therefore A0R1 standalone stale baseline review should not by itself prove actual fresh-run is impossible.
- However, actual fresh-run readiness still depends on the post-reset internal `plan_command()` and on source/Corporate Event gates.

## 12. Source Preflight Reclassification

| Source / Artifact | Producer | Generation Timing | Consumer | PIT Authority | Pre-run Required? | Current Status | Actual Operator Blocker? | Classification |
|---|---|---|---|---|---|---|---|---|
| Market coverage / OHLCV | Historical `market_refresh` creates run-scoped `historical_asof` inputs; preflight checks shared `.runtime/operations/jquants` | Run-scoped during daily runtime for BT path; static source for preflight | Strategy shadow source resolver | Run-scoped logical input manifest in BT | Shared canonical 2022 coverage should not be required if run-scoped authority is valid | Preflight `BOOTSTRAP_REQUIRED` | Contract blocker, not proven real runtime blocker | `RUNTIME_GENERATED_RUN_SCOPED_SOURCE`, `PREFLIGHT_FALSE_PRECONDITION`, `HUMAN_REVIEW_CONDITION` |
| Listed coverage | Historical `market_refresh` / logical input manifest | Run-scoped during daily runtime for BT path | Strategy shadow source resolver; sector/corporate listing facts | Run-scoped listed issues manifest in BT | Same as above | Preflight `NOT_ELIGIBLE_SOURCE_COVERAGE` | Contract blocker, not proven real runtime blocker | `RUNTIME_GENERATED_RUN_SCOPED_SOURCE`, `PREFLIGHT_FALSE_PRECONDITION`, `HUMAN_REVIEW_CONDITION` |
| Sector coverage | Derived from listed issues sector columns | With run-scoped listed issues | Strategy shadow sector source | Listed issues PIT source | Should follow listed authority | Preflight blocked by listed coverage | Contract blocker | `RUNTIME_GENERATED_RUN_SCOPED_SOURCE`, `PREFLIGHT_FALSE_PRECONDITION` |
| Corporate event coverage | Corporate Event artifact producer plus listed status fallback | Current guide requires pre-run validation artifacts per requested window | Strategy shadow / strategy source manifest | PIT validation plus approved earnings calendar exception | Yes, current guide requires gate evidence before 10BD/20BD | Current `.runtime` has 2026 artifacts only; BT has 2022 run evidence | Yes, current Operator gate blocker/review | `PRE_RUN_REQUIRED_STATIC_SOURCE`, `DOCUMENTED_OPTIONAL_SOURCE_GAP`, `HUMAN_REVIEW_CONDITION`, `TRUE_OPERATOR_BLOCKER` |
| Candidate generation readiness | Strategy/Candidate runtime path | Runtime-generated downstream artifact | Opportunity/Strategy shadow input manifest | Accepted Generation + business-date evidence | Should not require pre-existing daily output before producer runs | Preflight `candidate_daily_output_missing` | Contract blocker, not real pre-run source blocker | `RUNTIME_GENERATED_DOWNSTREAM_ARTIFACT`, `PREFLIGHT_FALSE_PRECONDITION` |
| Opportunity generation readiness | Strategy/Opportunity runtime path | Runtime-generated downstream artifact | Portfolio/Strategy shadow input manifest | Accepted Generation + business-date evidence | Should not require pre-existing daily output before producer runs | Preflight `opportunity_daily_output_missing` | Contract blocker, not real pre-run source blocker | `RUNTIME_GENERATED_DOWNSTREAM_ARTIFACT`, `PREFLIGHT_FALSE_PRECONDITION` |

## 13. Corporate Event Gate Status

Command Guide requirements before 10BD/20BD:
- Complete permanent J-Quants Corporate Event materialization / validation gate.
- Expose `earnings_calendar_authority_type=CURRENT_SNAPSHOT_CALENDAR_ONLY`.
- Expose `earnings_calendar_historical_pit_compliant=false`.
- Expose `earnings_calendar_exception_scope=earnings_scheduled_date_only`.
- Expose `non_calendar_future_leakage_used=false`.
- Expose `non_calendar_latest_fallback_used=false`.
- Generate Corporate Event artifacts for every requested business date.
- Inspect `status`, `known_event_count`, `known_no_event_count`, `unknown_count`, and source-scoped coverage.
- Do not run the 10BD Runtime Test until calendar-only validation evidence has passed review.

Current `.runtime` gate inventory:
- `.runtime/strategy_artifacts/corporate_event/2026-07-06/corporate_event.json`
- `.runtime/strategy_artifacts/corporate_event/2026-07-14/corporate_event.json`
- `.runtime/strategy_artifacts/corporate_event/2026-07-15/corporate_event.json`

No current `.runtime/strategy_artifacts/corporate_event/2022-07-01..2022-07-14` gate artifacts were found.

Phase23-BT 2022 evidence:
- Daily `strategy/corporate_event.json` exists for all 10 requested dates.
- For `2022-07-01` and `2022-07-14`, `known_event_count=0`, `known_no_event_count=4196`, `unknown_count=0`.
- `pit_validation.status=PASS`.
- `earnings_calendar_authority_type=CURRENT_SNAPSHOT_CALENDAR_ONLY`.
- `earnings_calendar_historical_pit_compliant=false`.
- `earnings_calendar_exception_scope=earnings_scheduled_date_only`.
- `future_leakage_used=false`, `latest_fallback_used=false`, `non_calendar_future_leakage_used=false`, `non_calendar_latest_fallback_used=false`.
- Source scoped coverage shows listed status coverage `AVAILABLE`, while earnings/financial/corporate action sources remain `UNKNOWN_DUE_TO_MISSING_COVERAGE` optional/missing areas.

Conclusion:
- BT proves the old run had daily Corporate Event/PIT artifacts.
- Current Operator entry gate still needs explicit 2022 window Corporate Event validation review under the current guide.
- This is a true Operator readiness blocker until accepted or regenerated/reviewed by an authorized task.

## 14. Phase23-BT Comparison

| Item | Phase23-BT Evidence | A0R2 Finding |
|---|---|---|
| Profile | `historical-smoke` | Still the BT-comparable target |
| Window | `2022-07-01` to `2022-07-14`, 10BD | Same requested dry-run window resolved for both profiles |
| Runtime source authority | Run-scoped `historical_asof_source_authority` | Dry-run does not materialize or validate this authority |
| Logical input manifests | Present under daily `market_refresh/inputs/historical_asof/<date>/logical_input_manifest.json` | Not present for new dry-run because no execution |
| Latest fallback | `false` | No new PIT validation performed in dry-run |
| Strategy source manifest | PIT `PASS`, root blockers empty per day | Current plan preflight remains stricter/different |
| Corporate Event | Daily 2022 artifacts with PIT PASS | Current guide still requires pre-run gate review before rerun |
| Candidate/opportunity | Generated during runtime flow | Current preflight treats as pre-existing missing outputs |

## 15. Operator Runtime Readiness

Operator 10BD is not ready from A0R2 state.

Reasons:
- Dry-run is only partial validation and does not prove post-reset `plan_command()` passes.
- Current standalone plan review from A0/A0R1 remains explained but unresolved as machine gate evidence.
- Source preflight contract still marks runtime-generated artifacts as missing pre-run blockers.
- Corporate Event current 2022 requested-window validation gate is not present under `.runtime/strategy_artifacts/corporate_event`.
- No actual reset, plan, run, validate, or close was executed.

## 16. Repair Requirement

Repair/review is required.

Required before Operator approval:
- Fix or formally revise Historical source preflight so run-scoped `historical_asof` source materialization is represented correctly.
- Reclassify candidate/opportunity daily outputs as runtime-generated downstream artifacts unless a true pre-run accepted generation gate is intended.
- Provide or accept explicit Corporate Event validation gate evidence for the requested 2022 10BD window.
- Optionally add a dry-run field that clearly states `post_reset_baseline_mode=not_evaluated` to avoid interpreting dry-run exit 0 as post-reset plan PASS.

## 17. Risks / Gaps

- Dry-run exit 0 can be misread as Operator readiness, but it does not evaluate baseline compatibility.
- Actual fresh-run may still fail at post-reset `plan_command()` if source preflight or another plan gate is promoted into exit status later.
- Corporate Event artifacts from BT are historical run evidence, not necessarily current entry-gate materialization evidence.
- Current `request_conformance_status` appears as top-level `NOT_PASS` in dry-run summary independent acceptance while the plan step summary has `request_conformance_status=PASS`; this is a summary-level dry-run semantics gap and should not be used as Operator PASS.

## 18. Recommended Next Action

Recommended next task:

`Phase24-A0R3 Historical Source Preflight Contract Repair And Corporate Event Entry Gate Evidence Preparation`

Objectives:
- Repair or formally revise source preflight contract.
- Produce/review 2022 requested-window Corporate Event gate evidence without running the 10BD Runtime.
- Add explicit dry-run limitation metadata if desired.
- After repair/review, run short plan/readiness checks only; do not run actual fresh-run until Operator explicitly authorizes it.

## Fresh-run Step Table

| Step | Dry-run Behavior | Actual Behavior | Mutation | Input Authority | Output | Failure Effect |
|---|---|---|---|---|---|---|
| Status | `PLANNED_READ_ONLY` | Calls `status()` | Read-only | Current runtime/evidence root | Status payload | Active run blocks actual fresh-run before backup |
| Backup | `PLANNED_NO_WRITE` | Calls `backup_command()` | Actual writes backup bundle | Resettable trading state | `reports/runtime_tests/backups/<backup_id>/` | Failure stops before reset |
| Reset | `PLANNED_NO_MUTATION` | Calls `reset_command()` | Actual mutates resettable trading state | Backup manifest + profile initial state + requested start date | Clean state and invariant | Failure stops before plan; rollback attempted on reset exception |
| Plan | `PLANNED_NO_WRITE`; `build_plan()` preview only | Calls `plan_command()` after reset | Evidence write only | Reset runtime root, profile, requested window | `plan.json`, baseline compatibility, run id | Non-PASS stops before run |
| Run | `PLANNED_NO_EXECUTION` | Calls `run_command()` | Runtime execution mutates normal historical runtime state | Persisted plan and reset root | `run_state.json`, daily evidence | HALT stops validate/close |
| Validate | `PLANNED_NO_EXECUTION` | Calls `validate_command()` | Read-only | Run state + runtime root + evidence | Validation payload | Failure skips close |
| Close | `PLANNED_NO_MUTATION` | Calls `close_command()` | Evidence write only | Validation result, run state, final state hashes | `final_summary.json` | Non-PASS finalizes as review/block exit |

## Baseline Mismatch Resolution Table

| Mismatch | Current Cause | Reset Outcome | Post-reset Expected State | Blocking After Reset? | Evidence |
|---|---|---|---|---|---|
| `current_state_date_future` | Shared current at `2022-07-14` | Current rewritten | `2022-07-01` logical date | No, expected | `apply_reset()` |
| `ledger_date_future` | Prior run ledger records | Ledger files truncated/rewritten | Empty initial ledger/current | No, expected | `RESETTABLE_RELATIVE_PATHS` |
| `pending_foreign_runtime_test_run_id` | Previous run id in pending metadata | Pending rewritten | Empty pending, no active run id | No, expected | `apply_reset()` |
| `pending_safety_business_date_future` | Prior safety mutable state | Safety path removed | No stale safety state | No, expected | resettable path |
| `pending_target_date_future` | Prior pending target date | Pending rewritten | Empty pending target | No, expected | `apply_reset()` |

## Source Gate Table

| Source / Artifact | Generation Timing | Pre-run Required? | PIT Authority | Current Status | Actual Operator Blocker? | Classification |
|---|---|---|---|---|---|---|
| Market OHLCV | Run-scoped during daily historical market refresh, with shared raw inputs as source inventory | Not as pre-existing daily run artifact | Run-scoped logical input manifest | Preflight says insufficient shared 2022 coverage | Human review / contract blocker | `RUNTIME_GENERATED_RUN_SCOPED_SOURCE`, `PREFLIGHT_FALSE_PRECONDITION` |
| Listed issues | Run-scoped during daily historical market refresh | Not as pre-existing daily run artifact if run-scoped manifest is valid | Run-scoped logical input manifest | Preflight says shared listed starts 2026 | Human review / contract blocker | `RUNTIME_GENERATED_RUN_SCOPED_SOURCE`, `PREFLIGHT_FALSE_PRECONDITION` |
| Sector | Derived from listed issues | Follows listed authority | Listed PIT source | Blocked by listed preflight | Human review / contract blocker | `RUNTIME_GENERATED_RUN_SCOPED_SOURCE`, `PREFLIGHT_FALSE_PRECONDITION` |
| Corporate Event | Entry-gate artifact/review before 10BD plus runtime daily evidence | Yes under current guide | PIT validation + earnings calendar exception | Current 2022 gate absent; BT evidence exists | Yes | `PRE_RUN_REQUIRED_STATIC_SOURCE`, `TRUE_OPERATOR_BLOCKER` |
| Candidate output | Runtime-generated downstream artifact | No, unless accepted generation resolution fails | Accepted Generation + daily runtime evidence | Preflight says daily output missing | Contract blocker | `RUNTIME_GENERATED_DOWNSTREAM_ARTIFACT`, `PREFLIGHT_FALSE_PRECONDITION` |
| Opportunity output | Runtime-generated downstream artifact | No, unless accepted generation resolution fails | Accepted Generation + daily runtime evidence | Preflight says daily output missing | Contract blocker | `RUNTIME_GENERATED_DOWNSTREAM_ARTIFACT`, `PREFLIGHT_FALSE_PRECONDITION` |

## Command Guide Conformance Table

| Requirement | Guide Statement | Implementation | Conformance | Gap |
|---|---|---|---|---|
| Fresh-run lifecycle order | `Status -> Backup -> Clean Reset -> Plan -> Run -> Validate -> Close` | Actual command executes this order | PASS | None for actual order |
| Dry-run non-mutation | Dry-run validates request/run id without plan evidence or Runtime mutation | Dry-run returned planned steps; evidence dirs absent; tests pass | PASS | None |
| Dry-run post-reset authority | Guide does not claim post-reset baseline is evaluated | Dry-run uses `build_plan()` preview and no reset | PASS | Needs clearer operator-facing limitation |
| Backup/reset scope | Backup/reset resettable trading state only; excludes data/registry/AI/config | Implementation uses resettable/excluded path constants | PASS | None found |
| Post-reset logical date | Initial empty Current binds logical date to first planned business date | Actual fresh-run passes requested start date to reset | PASS by implementation | Not executed in A0R2 |
| Corporate Event gate | Complete materialization/validation before 10BD/20BD | Current 2022 gate artifact absent in `.runtime` | NOT PASS | Gate evidence required/review required |
| Source preflight before long run | `operator_ready=false` means do not run | Current source preflight remains false in A0/A0R1 evidence | NOT PASS | Contract repair/reclassification required |
