# Phase32-U - Post-T Fresh-Run Day-0 Morning HALT Root-Cause Audit

## Executive Summary

The Post-T short fresh validation `runtime-test-historical-extended-smoke-20260827T032942118416Z` halted on 2022-10-03 morning before strategy planning. The first failing component is the Position Management runtime producer, specifically the accepted artifact registry identity guard for `POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER`.

Exact error:

`position management unavailable before strategy planning: artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER`

This is not a REENTRY, Cash, PC/MCC, Risk Pacing, submit, execution, broker readonly, ledger initialization, or provenance-field validation failure. The halted stage did not reach strategy planning, runtime planning, pending generation, submit, or execution.

Phase32-T causality is **YES**: Phase32-T changed `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`, which is the registered PM runtime adapter member. The artifact registry still points to accepted member hash `36f081ee0c3c9ec1b39e00ed83d01e931af8cfc0754d47303deb548dd8df04db`, while the current file hash is `96b55567877f26f12444439261c00c2afa5105d97512be2c2306283e474a14a2`.

## Run Identity

| field | value |
|---|---|
| run_id | `runtime-test-historical-extended-smoke-20260827T032942118416Z` |
| evidence path | `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T032942118416Z` |
| requested first day | 2022-10-03 |
| status | `HALT` |
| completed_days | `[]` |
| final_judgment | `HALT` |
| exit_code | `30` |
| error | `Runtime CLI stopped at 2022-10-03:morning with exit code 30` |
| final_summary.json | absent |

## Morning Stage Timeline

| stage | artifact exists | status | boundary |
|---|---:|---|---|
| market_refresh | yes | PASS / exit `0` | completed before morning |
| data_readiness | yes | READY / exit `0` | completed before morning |
| preflight / environment capability | yes | PASS | `historical_morning_capability_ready` |
| external effect audit | yes | PASS | no external effect issue |
| review / safety gate | yes | mixed evidence, final safety READY/PASS | did not cause halt |
| ledger initialization / current state | yes | initial state present | persistent ledger clean |
| candidate / opportunity readiness | yes | READY / PRE_INFERENCE_READY | model/input readiness passed |
| PM | yes | HALT | first failing boundary |
| strategy input generation | yes | NOT_EXECUTED | stage not reached |
| PC / sizing / runtime planning | yes | NOT_EXECUTED | blocked by PM HALT |
| pending generation | yes | NOT_EXECUTED | stage not reached |
| submit preparation | no substantive submit artifact | NOT_REACHED | morning stops before submit anyway |
| broker snapshots / execution | no execution snapshot for day | NOT_REACHED | execution path not reached |

Last successful boundary: `environment_capability_decision = PASS`, with market/data readiness also complete.

First failing boundary: `position_management_ai_runtime_producer = HALT`.

## Exact Failure

`daily/2022-10-03/morning/runtime_manifest.json` contains:

- `exit_code = 30`
- `pm_status = HALT`
- `pm_input_schema_status = HALT`
- `pm_reason = artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER`
- `reason = position management unavailable before strategy planning: artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER`
- `errors = [position management unavailable before strategy planning: artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER]`

`daily/2022-10-03/morning/planning_evidence.json` contains:

- `status = NOT_EXECUTED`
- `reason = position management unavailable before strategy planning: artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER`

`daily/2022-10-03/morning/pending_generation_evidence.json` contains:

- `status = NOT_EXECUTED`
- `reason = pending_generation_stage_not_reached`

`daily/2022-10-03/morning/strategy_planning_authority_evidence.json` contains:

- `status = NOT_EXECUTED`
- `reason = phase23_i_strategy_planning_authority_stage_not_reached`

No traceback or stderr was captured. The CLI returned structured HALT evidence and `stderr = ""`.

## Failing Function / Contract

FIRST_FAILING_COMPONENT:

`runtime_v2.position_management.producer`

FIRST_FAILING_FUNCTION:

`produce_position_management_decisions() -> verify_position_management_runtime_adapter_authority() -> resolve_runtime_artifact_set()`

FIRST_FAILING_CONTRACT:

Accepted Artifact Registry runtime adapter identity contract:

`POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER` member content hash must equal the executing source file hash.

Contract implementation:

- `run_daily_operation.py` calls `produce_position_management_decisions()` before formal strategy generation.
- `produce_position_management_decisions()` calls `verify_position_management_runtime_adapter_authority()`.
- `verify_position_management_runtime_adapter_authority()` requires the registry member `RUNTIME_ADAPTER`.
- `resolve_runtime_artifact_set()` computes the actual file hash and raises `RuntimeArtifactLookupHalt` when it differs from the accepted registry hash.
- The PM producer catches the halt, writes a HALT PM artifact, and returns `pm_status = HALT`.
- `run_daily_operation.py` converts that PM HALT into morning `EXIT_HALT = 30`.

## Registry Evidence

Current accepted registry member:

- artifact set: `POSITION_MANAGEMENT_POLICY_SET`
- member role: `RUNTIME_ADAPTER`
- physical path: `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- accepted content hash: `36f081ee0c3c9ec1b39e00ed83d01e931af8cfc0754d47303deb548dd8df04db`

Current file hash:

- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- actual content hash: `96b55567877f26f12444439261c00c2afa5105d97512be2c2306283e474a14a2`

The mismatch is sufficient to explain the HALT.

## Phase32-T Causality

Phase32-T modified `position_management/producer.py` to preserve actual PM provenance from `pm_decision_id`, `business_date`, and `position_campaign_id` into `SellExitDecision`. That file is the accepted `POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER` member. The registry was not refreshed after the source change.

Therefore:

- This is not caused by optional provenance fields breaking dataclass construction.
- This is not caused by JSON serialization/deserialization of ledger rows.
- This is not caused by startup/import failure.
- This is not caused by submit guard assumptions.
- This is not caused by broker readonly, normalizer, execution projection, or ledger execution paths; those stages were not reached.

Classification: Phase32-T registry-acceptance regression / artifact identity compatibility issue.

## Backward Compatibility

No evidence of constructor, schema, or optional-field compatibility failure was found in the halted run:

- CLI started and wrote structured manifests.
- Market refresh passed.
- Data readiness passed.
- Morning environment capability passed.
- The PM producer imported and executed far enough to call registry validation.
- The error is an explicit artifact member hash mismatch, not a Python exception.
- Persistent ledger `orders.jsonl` and `executions.jsonl` remain readable and empty.
- Initial `state.json` is readable with cash `1000000.0` and no positions.
- Pending slot is readable with `state/status = EMPTY`.

## State Integrity

Observed state after HALT:

| state area | observed |
|---|---|
| persistent orders | exists, `0` lines |
| persistent executions | exists, `0` lines |
| persistent state | initial cash `1000000.0`, positions `[]`, business date `2022-10-03` |
| pending order plan | `EMPTY` |
| PM artifact | HALT artifact written at `.runtime/runtime_state/position_management/2022-10-03/position_management_decisions.json` |
| strategy planning | not executed |
| pending generation | not executed |
| submit / execution | not reached |

Runtime state was partially mutated in the expected operational sense: initial/current state artifacts and a HALT PM artifact exist. Trading/accounting state was not mutated: no orders, executions, fills, or pending orders were created.

Resume safety is unresolved. The durable trading state is clean, but the run halted at Day-0 with a HALT PM artifact and no completed business days. After repair, a fresh short validation is cleaner than resume because the acceptance question is Day-0 behavior under the corrected registry identity.

## Repair Readiness

Minimal repair boundary:

Refresh formal accepted artifact registry identity for `POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER` after the Phase32-T source change, or otherwise perform the project’s established PM runtime adapter acceptance refresh workflow. Do not broaden into REENTRY, Cash, PC/MCC, Risk Pacing, submit, execution, threshold, or model changes.

Implementation is ready because the failure is exact and deterministic:

`accepted registry hash != current producer.py hash`

## Resume / Fresh-Run Recommendation

Do not resume this halted run as the primary validation. Perform the minimal registry acceptance refresh, then run a new short fresh validation. Acceptance should confirm:

- Day-0 morning no longer halts at PM runtime adapter authority.
- PM stage reaches READY/PASS or a non-registry review state.
- Strategy planning and pending generation are reached.
- Phase32-T provenance acceptance can proceed to the first actual SELL/EXIT day.

## Final Judgments

PHASE32_U_FIRST_FAILING_STAGE = 2022-10-03 morning `position_management_ai_runtime_producer`

PHASE32_U_FIRST_FAILING_COMPONENT = `runtime_v2.position_management.producer` artifact registry authority check for `POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER`

PHASE32_U_EXACT_ERROR = `position management unavailable before strategy planning: artifact member hash mismatch: POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER`

PHASE32_U_PHASE32_T_REGRESSION = YES

PHASE32_U_SCHEMA_COMPATIBILITY_DEFECT = NO

PHASE32_U_RUNTIME_STATE_MUTATED_BEFORE_HALT = PARTIAL

PHASE32_U_RESUME_SAFE = UNRESOLVED

PHASE32_U_FRESH_RUN_REQUIRED_AFTER_REPAIR = YES

PHASE32_U_MANDATORY_DEFECT = YES

PHASE32_U_PRODUCTION_REPAIR_JUSTIFIED = YES

PHASE32_U_IMPLEMENTATION_READY = YES

PHASE32_U_MINIMAL_REPAIR_BOUNDARY = formal accepted artifact registry refresh for `POSITION_MANAGEMENT_POLICY_SET:RUNTIME_ADAPTER` after Phase32-T changes to `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`

PHASE32_U_NEXT_STEP = run the PM runtime adapter formal acceptance refresh only, then start a new short fresh validation; do not change REENTRY/Cash/PC/MCC/Risk Pacing/runtime strategy logic
