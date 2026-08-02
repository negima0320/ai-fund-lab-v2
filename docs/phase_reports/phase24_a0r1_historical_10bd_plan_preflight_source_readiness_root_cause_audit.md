# Phase24-A0R1 Historical 10BD Plan Preflight Source Readiness Root Cause Audit

## 1. Executive Summary

Primary Judgment: `PHASE24_A0R1_MULTIPLE_ROOT_CAUSES_CONFIRMED_REPAIR_REQUIRED`

Phase24-A0R1 found two separate issues that were conflated by the A0 entry-gate result:

1. The direct cause of the observed `PLAN_REVIEW_REQUIRED` exit was `baseline_compatibility_status=REVIEW_REQUIRED`.
   The shared `.runtime` state still represented the previous historical 10BD run's final day (`2022-07-14`), while the new plan requested a window starting on `2022-07-01`. The plan also used a new run id, so pending/safety metadata from the previous run was treated as foreign residue.

2. The source readiness blockers under `strategy_shadow.source_preflight.root_blockers` are not explained by the previous run close state alone.
   The preflight checks inspect shared `.runtime` canonical source inventory and pre-existing daily Buy-AI outputs before the run. Phase23-BT's successful 10BD execution instead used run-scoped `historical_asof` logical input manifests generated during daily `market_refresh`, and candidate/opportunity outputs were runtime-generated artifacts. That means the current preflight contract is using false preconditions for Historical 10BD Operator approval.

Therefore, the current standalone plan is not Operator-executable as-is. A repair or explicit contract revision is required before granting Operator approval for another Historical 10BD run.

## 2. Scope And Non-Goals

Scope:
- Audit A0 `PLAN_REVIEW_REQUIRED` root cause.
- Classify six source readiness blockers.
- Compare current plan evidence with Phase23-BT successful run evidence.
- Determine whether previous close residue, stale `.runtime` state, source materialization gaps, or preflight contract regression is responsible.

Non-goals:
- No Runtime execution.
- No fresh-run or resume.
- No Broker Write.
- No Runtime Switch.
- No J-Quants fetch.
- No source regeneration.
- No code, schema, fixture, or strategy edits.

## 3. Evidence Sources Read

- `docs/phase_reports/phase24_a0_bu_post_repair_close_runtime_revalidation_entry_gate_preparation.md`
- `reports/phase_reports/phase24_a0_bu_post_repair_close_runtime_revalidation_entry_gate_preparation.json`
- Phase23 final handoff and Phase23-BV/BT/BU reports.
- Phase23-BM/BO/BQ/BS reports.
- Architecture SoT and Runtime command guide.
- `scripts/runtime_test.py`
- `src/ai_fund_lab_v2/strategy/historical_source_foundation.py`
- A0 plan artifact:
  `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T225905720225Z/plan.json`
- Phase23-BT target run artifacts:
  `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T211110605880Z/`

## 4. Commands Executed

| Command | Exit | Purpose | Mutation |
|---|---:|---|---|
| `PYTHONPATH=src python3 scripts/runtime_test.py run-status --profile historical-smoke --json` | 0 | Confirm active Runtime state | Read-only |
| `PYTHONPATH=src python3 scripts/runtime_test.py system-status --profile historical-smoke --scope runtime --json` | 10 | Inspect runtime-level system status | Read-only |
| `PYTHONPATH=src python3 scripts/runtime_test.py list-runs --json` | 0 | Confirm target run and plan-only runs | Read-only |
| `rg`, `sed`, `jq`, `find` reads against reports and source files | 0 | Inspect plan/final/run/source manifests and command implementation | Read-only |

Carried-over A0 evidence:
- A0 previously ran `plan` for `historical-smoke` and `historical-extended-smoke`.
- The relevant A0 plan persisted evidence under `reports/runtime_tests/runs/runtime-test-historical-smoke-20260730T225905720225Z/plan.json`.
- No A0R1 Runtime run/fresh-run/resume was executed.

## 5. Previous Run Close State

Target run: `runtime-test-historical-smoke-20260730T211110605880Z`

| Evidence | Value |
|---|---|
| `run_state.status` | `COMPLETED` |
| Completed business dates | `2022-07-01` through `2022-07-14`, 10 business days |
| `run_state.current_step` | `null` |
| `run_state.next_job` | empty |
| `final_summary.status` | `REVIEW_REQUIRED` |
| `final_summary.closed_at` | `2026-07-30T21:26:16.786796Z` |
| Halt state | `NOT_HALTED` |
| BU close contract fields | absent, because the run predates Phase23-BU close repair |
| Classification | `PREVIOUS_RUN_CLOSED_WITH_NON_BLOCKING_REVIEW` |

Interpretation:
- The previous run is not active.
- It did close and preserve final-state hashes, but with `REVIEW_REQUIRED`, not clean `PASS`.
- Because it predates BU, absence of BU fields is expected and should not be treated as evidence of a new close repair failure.

## 6. Current Runtime State

`run-status --profile historical-smoke --json` reported:

| Field | Value |
|---|---|
| `run_status` | `IDLE` |
| `active_test_run` | empty |
| Current business date | `2022-07-14` |
| Runtime state business date | `2022-07-14` |
| Pending state | `CONSUMED` |
| Pending origin run id | `runtime-test-historical-smoke-20260730T211110605880Z` |
| Positions count | `3` |

Conclusion:
- No active/stuck Runtime run exists.
- Stale shared Runtime trading state does exist for the purpose of planning a fresh `2022-07-01` window from the same `.runtime` root.
- This stale state is sufficient to explain `baseline_compatibility_status=REVIEW_REQUIRED`.

## 7. Direct Cause Of `PLAN_REVIEW_REQUIRED`

The A0 plan artifact reports:

| Field | Value |
|---|---|
| Plan run id | `runtime-test-historical-smoke-20260730T225905720225Z` |
| Requested window | `2022-07-01` to `2022-07-14` |
| Business days | 10 |
| Window resolution | resolved all 10 requested dates |
| `baseline_compatibility_status` | `REVIEW_REQUIRED` |
| Plan status | `PLAN_REVIEW_REQUIRED` |

Mismatch reasons:
- `current_state_date_future`
- `ledger_date_future`
- `pending_foreign_runtime_test_run_id`
- `pending_safety_business_date_future`
- `pending_target_date_future`

Direct cause:
- `scripts/runtime_test.py` computes plan status as `PASS` only when both baseline compatibility and window resolution pass.
- Window resolution passed.
- Baseline compatibility did not pass because `.runtime` still reflected `2022-07-14` final state while the new plan requested `2022-07-01` as its start date and had a new run id.

## 8. Source Preflight Result

A0 plan `strategy_shadow.source_preflight`:

| Field | Value |
|---|---|
| `judgment` | `NOT_ELIGIBLE_SOURCE_COVERAGE` |
| `operator_ready` | `false` |
| Root blockers | `candidate_generation_readiness`, `corporate_event_coverage`, `listed_coverage`, `market_coverage`, `opportunity_generation_readiness`, `sector_coverage` |
| Missing sources | `candidate_daily_output_missing`, `daily_quotes_coverage_starts_after_required_start`, `daily_quotes_required_warmup_insufficient`, `listed_information_coverage_starts_after_required_start`, `opportunity_daily_output_missing` |

Important distinction:
- This source preflight did not directly cause `PLAN_REVIEW_REQUIRED`.
- It still matters because Operator approval must not ignore `operator_ready=false`.

## 9. Root Blocker Table

| Root blocker | Current producer | Current evidence | Phase23-BT comparison | Classification | Repair required |
|---|---|---|---|---|---|
| `market_coverage` | `build_historical_strategy_preflight` coverage check over `.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet` | `BOOTSTRAP_REQUIRED`; coverage starts `2026-02-16`, required `2022-07-01`; warmup insufficient | Phase23-BT daily strategy used run-scoped `historical_asof` normalized OHLCV; PIT validation passed; latest fallback false | `G PREFLIGHT_CONTRACT_REGRESSION`; `E FRESH_RUN_GENERATED_ARTIFACT_FALSE_PRECONDITION` | Yes |
| `listed_coverage` | Coverage check over `.runtime/operations/jquants/raw/jquants/listed_issues/data.parquet` | `NOT_ELIGIBLE_SOURCE_COVERAGE`; coverage starts `2026-07-06`, required `2022-07-01` | Phase23-BT daily strategy used run-scoped `historical_asof` listed issues; source record passed | `G`; `E` | Yes |
| `corporate_event_coverage` | Corporate event/source inventory derived from listed/corporate optional source availability | `NOT_ELIGIBLE_SOURCE_COVERAGE`; corporate actions/earnings/financial statements unavailable; listed coverage also invalid | Phase23-BT manifests treated corporate actions/earnings/financial as missing optional records while PIT source validation still passed | `G`; `E`; `H DOCUMENTED_NON_BLOCKING_GAP` for optional corporate sources | Yes, for blocking semantics; not necessarily for optional data materialization |
| `sector_coverage` | Listed issue sector-column availability and PIT coverage | `NOT_ELIGIBLE_SOURCE_COVERAGE`; driven by listed source coverage | Phase23-BT used run-scoped listed issues and sector materialization path passed strategy source authority | `G`; `E` | Yes |
| `candidate_generation_readiness` | `_daily_output_readiness` scan of `.runtime/runtime_state/buy_ai/*/candidate_decisions.json` | `NOT_ELIGIBLE_SOURCE_COVERAGE`; `candidate_daily_output_missing` | Phase23-BT target plan had the same pre-run blocker, but execution generated daily candidate decisions during runtime flow | `E`; `G` | Yes |
| `opportunity_generation_readiness` | `_daily_output_readiness` scan of `.runtime/runtime_state/buy_ai/*/opportunity_rankings.json` | `NOT_ELIGIBLE_SOURCE_COVERAGE`; `opportunity_daily_output_missing` | Phase23-BT target plan had the same pre-run blocker, but execution generated daily opportunity rankings during runtime flow | `E`; `G` | Yes |

## 10. Previous Run State Table

| Question | Answer | Evidence |
|---|---|---|
| Is there an active run? | No | `run-status` returned `IDLE`, empty `active_test_run` |
| Did the target run complete 10BD? | Yes | `run_state.status=COMPLETED`; completed dates `2022-07-01` to `2022-07-14` |
| Did close produce clean PASS? | No | `final_summary.status=REVIEW_REQUIRED` |
| Was the run halted? | No | `halt_summary.status=NOT_HALTED` |
| Did it leave shared `.runtime` at final day? | Yes | current and runtime state business date `2022-07-14` |
| Is pending state active? | No | pending state `CONSUMED`; `pending_active=false` in plan baseline matrix |
| Does pending metadata belong to the new A0 plan run id? | No | pending origin run id is previous target run |
| Classification | `B STALE_RUNTIME_STATE` plus non-active previous close residue | Baseline compatibility mismatch reasons |

## 11. Phase23-BT Comparison Table

| Item | Phase23-BT successful run | A0 current plan | Interpretation |
|---|---|---|---|
| Target window | `2022-07-01` to `2022-07-14` | `2022-07-01` to `2022-07-14` | Same 10BD window |
| Target run plan source preflight | `operator_ready=false`; same root blockers observed | `operator_ready=false`; same root blockers observed | Source blockers are not new A0-only evidence |
| Daily strategy source authority | `historical_asof_source_authority` | Not available at plan time | Runtime uses run-scoped historical manifests generated during daily flow |
| Run-scoped logical manifests | Present under `daily/<date>/market_refresh/inputs/historical_asof/<date>/logical_input_manifest.json` | Not yet generated before run | Current preflight checks for artifacts before their producer runs |
| Latest fallback | `false` | Not applicable to plan preflight | Phase23-BT did not rely on latest fallback |
| PIT validation | `PASS` in daily `source_manifest.json` | `NOT_ELIGIBLE_SOURCE_COVERAGE` in preflight | Preflight contract disagrees with runtime source authority |
| Candidate/opportunity outputs | Generated during daily runtime execution | Required as pre-existing files by preflight | False precondition |
| Accepted generation | `phase19_aq_accepted_generation_641e6e313543f013` | Accepted generation readiness `PASS` | No accepted-generation mismatch found |

## 12. Accepted Generation Audit

Current accepted bundle:
- `accepted_generation_id=phase19_aq_accepted_generation_641e6e313543f013`
- `transaction_state=COMMITTED`
- Aggregate hash observed in `.runtime/runtime_state/accepted_buy_ai_bundle.json`

A0 plan:
- `accepted_generation_readiness=PASS`

Conclusion:
- No accepted generation mismatch was found.
- The source readiness blockers are not caused by accepted generation drift.

## 13. Runtime Command Contract Findings

`plan_command`:
- Builds a plan.
- Adds baseline compatibility.
- Persists a plan artifact.
- Returns `PLAN_REVIEW_REQUIRED` unless baseline compatibility and window resolution are both `PASS`.
- Does not use `strategy_shadow.operator_ready` as the direct plan exit determinant.

`build_plan`:
- Embeds `build_historical_strategy_preflight` output under `strategy_shadow.source_preflight`.
- Sets `strategy_shadow.operator_ready` from source preflight.

`fresh_run_command`:
- Builds a preview plan before reset.
- Actual confirmed fresh-run performs status, backup, reset, plan, run, validate, and close.
- Therefore stale baseline state in a standalone plan may be cleared by a confirmed fresh-run reset, but the source preflight false-precondition problem remains unless repaired or formally reclassified.

## 14. Classification Against Required Root-Cause Codes

| Code | Applies? | Notes |
|---|---|---|
| A `REAL_SOURCE_MISSING` | Partial only | Shared `.runtime` canonical 2022 sources are missing, but Phase23-BT proved run-scoped historical sources can satisfy runtime strategy source authority. |
| B `STALE_RUNTIME_STATE` | Yes | Direct cause of baseline compatibility review and plan exit 10. |
| C `PREVIOUS_RUN_CLOSE_STATE_RESIDUE` | Partial | Previous run was closed/non-active, but left final shared runtime state and foreign pending/safety metadata for a new plan. |
| D `ACCEPTED_GENERATION_MISMATCH` | No | Accepted generation readiness passed; bundle is committed. |
| E `FRESH_RUN_GENERATED_ARTIFACT_FALSE_PRECONDITION` | Yes | Candidate/opportunity and run-scoped historical manifests are expected runtime outputs, not pre-run static prerequisites. |
| F `OBSOLETE_FIXTURE_OR_PROFILE` | Not proven | No direct obsolete fixture/profile evidence was found. |
| G `PREFLIGHT_CONTRACT_REGRESSION` | Yes | Preflight reads shared canonical/latest-ish inventory instead of the Historical run-scoped source authority used by the successful runtime path. |
| H `DOCUMENTED_NON_BLOCKING_GAP` | Yes, limited | Optional corporate events/earnings/financial statements were missing in BT while strategy source PIT still passed. |
| I `EXPECTED_REVIEW_BEFORE_OPERATOR_APPROVAL` | Yes | Current `operator_ready=false` means approval cannot be granted without repair or explicit contract revision. |
| J `UNKNOWN_REQUIRES_MORE_EVIDENCE` | No | Available evidence is sufficient for this audit decision. |

## 15. Direct Cause Versus Primary Root Cause

Direct cause of `PLAN_REVIEW_REQUIRED`:
- `B STALE_RUNTIME_STATE`, because shared `.runtime` remained at `2022-07-14` and pending/safety metadata belonged to the previous target run while the A0 plan used a new run id for a `2022-07-01` start.

Primary root cause for source readiness blockers:
- `G PREFLIGHT_CONTRACT_REGRESSION` plus `E FRESH_RUN_GENERATED_ARTIFACT_FALSE_PRECONDITION`.
- The source preflight is asking for shared canonical data and pre-existing daily outputs that are either generated run-scoped during the historical daily flow or already accepted as non-blocking optional gaps.

Overall audit root cause:
- Multiple root causes exist because the plan status and the source readiness blockers are produced by different mechanisms.

## 16. Repair Requirement

Repair is required before Operator approval.

Minimum repair or contract revision must address:
- How Historical plan preflight should account for run-scoped `historical_asof` source materialization.
- Whether candidate/opportunity daily outputs should be pre-run blockers, or represented as runtime-generated downstream artifacts.
- How standalone plan baseline compatibility should be interpreted when a previous completed run left `.runtime` at a future date and a confirmed fresh-run reset would occur before actual plan/run execution.
- Whether optional corporate event/earnings/financial gaps remain documented non-blocking gaps rather than root blockers.

No repair was performed in A0R1.

## 17. Operator 10BD Executability

Operator 10BD is not executable from this A0R1 state.

Reasons:
- Current canonical A0 plan status is `PLAN_REVIEW_REQUIRED`.
- Current source preflight has `operator_ready=false`.
- The source readiness blockers are not yet repaired or formally reclassified as non-blocking in the plan contract.
- A0R1 explicitly did not run fresh-run/resume/runtime execution.

## 18. Risks If Ignored

If Operator approval is granted without repair or explicit contract revision:
- The plan gate may remain noisy and fail to distinguish stale shared runtime state from true source readiness.
- Historical preflight may continue to block on artifacts generated only after `market_refresh` or daily strategy jobs.
- Optional corporate data gaps could be incorrectly promoted into hard blockers.
- A future run could be approved by institutional memory rather than executable, machine-checkable gate evidence.

## 19. Next Task

Recommended next task:

`Phase24-A0R2 Historical Plan Preflight Contract Repair And Clean-Baseline Planning Gate`

Task objective:
- Repair or formally revise the Historical plan preflight contract so it matches the proven Phase23-BT runtime source authority.
- Separate stale shared `.runtime` baseline review from true source materialization gaps.
- Re-run only the approved short plan/readiness checks after repair, still without Operator Runtime execution unless explicitly authorized.

## 20. Final Judgment

Primary Judgment: `PHASE24_A0R1_MULTIPLE_ROOT_CAUSES_CONFIRMED_REPAIR_REQUIRED`

Final answer:
- Previous run close state: completed and closed with non-blocking `REVIEW_REQUIRED`; not active.
- `.runtime` stale state: yes, final `2022-07-14` shared runtime state remains and directly caused baseline compatibility review.
- Direct cause of `PLAN_REVIEW_REQUIRED`: baseline compatibility mismatch, not the source preflight blockers.
- Primary source readiness root cause: preflight contract regression and false pre-run artifact prerequisites.
- Accepted generation mismatch: not found.
- Repair required: yes.
- Operator 10BD executable: no.
