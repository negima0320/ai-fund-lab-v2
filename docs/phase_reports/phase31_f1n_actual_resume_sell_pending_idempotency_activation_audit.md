# Phase31-F1N — Actual Resume SELL Pending Idempotency Activation Audit

## PRIMARY_JUDGMENT

PHASE31_F1N_ACTUAL_RESUME_IDEMPOTENCY_INTEGRATION_DEFECT_CONFIRMED

## Required Output

TARGET_RUN_ID = runtime-test-historical-extended-smoke-20260821T014643273280Z

LATEST_RESUME_FAILURE_REASON = resume stopped again at `2022-09-07:sell_planning`; Runtime exit code `20`; sell planning reason `ACTIVE_PENDING_NOT_EMPTY:active_buy_missing;PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED`.

F1L_EQUIVALENCE_BRANCH_ENTERED = YES

F1L_EQUIVALENCE_EVIDENCE_CREATED = NO

FIRST_FAILED_EQUIVALENCE_PREDICATE = current position present / symbol matches open position; helper saw `current_positions = {}` and returned `EQUIVALENT_SELL_PENDING_CURRENT_POSITION_MISSING`.

F1L_CURRENT_POSITION_QUANTITY = MISSING_IN_F1L_HELPER; canonical runtime current source has 93600 quantity `100.0`.

SELL_EXIT_LINEAGE_RESOLUTION = PASS

SELL_EXIT_LINEAGE_SOURCE_FIELD = `source_decision_type = SELL_EXIT`; also supported by `quantity_contract.planning_intent = SELL_EXIT`, `quantity_contract.source_planning_id = rp-2022-09-07-93600-sell_exit-816e30699b8499ff`, `planning_authority_source`, and `policy_source`.

F1L_BRANCH_REACHABLE_BEFORE_REVIEW_REQUIRED = YES

RESUME_USES_F1L_CODE_PATH = YES

FIXTURE_ACTUAL_MATERIAL_DIFFERENCE_COUNT = 4

ROOT_CAUSE_CLASSIFICATION = CURRENT_POSITION_SOURCE_MISMATCH

INTEGRATION_DEFECT_CONFIRMED = YES

REPAIR_CANDIDATE = YES

IMPLEMENTATION_CHANGED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED_BY_CODEX = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

NEXT_TASK_RECOMMENDATION = Phase31-F1O focused actual-artifact idempotency repair. Do not retry resume before F1N is resolved.

## Latest Resume Failure Evidence

Read-only target:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260821T014643273280Z`

The latest resume attempt updated 2022-09-07 sell-planning artifacts at `2026-08-21T03:00:23Z`. `run_state.json` records:

- status: `HALT`
- resumed: `true`
- business date: `2022-09-07`
- job: `sell_planning`
- exit code: `20`
- next job: `2022-09-07:sell_planning`

`sell_planning_manifest.json` records:

- final state: `REVIEW_REQUIRED`
- reason: `sell planning pipeline review required: ACTIVE_PENDING_NOT_EMPTY:active_buy_missing;PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED`
- pending composition model: `PRESERVE_ACTIVE_PENDING_ON_NO_SIGNAL`
- pending composition status: `REVIEW_REQUIRED`
- selected count: `0`
- selected symbols: `["93600"]`

`pending_continuity_evidence.json` records:

- status: `REVIEW_REQUIRED`
- reason: `ACTIVE_PENDING_NOT_EMPTY:active_buy_missing;PENDING_PLAN_CONFLICT_ORIGINAL_PRESERVED`
- resolution action: `ORIGINAL_PENDING_PRESERVED`
- original pending preserved: `true`

No `same_day_sell_pending_equivalence_evidence.json` was created in the run-scoped sell-planning artifact directory.

## Actual 93600 Pending Shape

Actual pending consumed by resumed sell-planning:

- plan state: `APPROVED`
- plan created date: `2022-09-07`
- target session date: `2022-09-07`
- consumed state: `consume_consumed = false`
- item count: `1`
- approved SELL count: `1`
- BUY count: `0`
- symbol: `93600`
- side: `SELL`
- quantity: `100.0`
- item state: `CREATED`
- approved flag: `true`
- source decision type: `SELL_EXIT`
- planning intent: `SELL_EXIT`
- source planning id: `rp-2022-09-07-93600-sell_exit-816e30699b8499ff`
- planning authority source: `rp-2022-09-07-93600-sell_exit-816e30699b8499ff`
- policy source: `rp-2022-09-07-93600-sell_exit-816e30699b8499ff`
- pending item id: `strategy-c8537cd09201c855e2b4`
- quantity contract selected quantity: `100`
- quantity contract requested quantity: `-100`
- quantity contract planning binding constraint: `SELL_EXIT_REDUCE_AUTHORITY`
- quantity contract quantity status: `RESOLVED_EXECUTABLE`

The pending shape is economically equivalent to a full 93600 exit if the helper receives the current position map.

## F1L Predicate Evaluation

| Condition | Actual Value | Result | Source |
| --- | --- | --- | --- |
| same business date | plan created date `2022-09-07`; business date `2022-09-07` | PASS | pending object / manifest snapshot |
| same target session | target session date `2022-09-07` | PASS | pending object / manifest snapshot |
| plan APPROVED | state `APPROVED` | PASS | pending object / manifest snapshot |
| unconsumed | `consume_consumed = false` | PASS | pending object / manifest snapshot |
| exactly one item | item count `1` | PASS | pending object / manifest snapshot |
| exactly one approved SELL | approved SELL count `1` | PASS | pending object / manifest snapshot |
| no BUY | BUY count `0` | PASS | pending object / manifest snapshot |
| supported item state | item state `CREATED` | PASS | pending object / manifest snapshot |
| symbol matches open position | helper received empty `current_positions`; canonical ledger has 93600 | FAIL_IN_HELPER | `sell_pipeline.py` non-executable branch / ledger |
| quantity equals current position quantity | helper could not load current quantity; canonical ledger quantity is `100.0` and pending quantity is `100.0` | FAIL_IN_HELPER | helper diagnostic / ledger |
| EXIT-equivalent lineage resolves | `source_decision_type = SELL_EXIT`; `planning_intent = SELL_EXIT` | PASS_IF_REACHED | pending object |
| no partial-fill markers | state `CREATED`; no partial/fill markers | PASS | pending object |

FIRST_FAILED_EQUIVALENCE_PREDICATE = current position present / current position quantity available.

Read-only helper probe confirmed:

- with `current_positions = {}`: `NOT_EQUIVALENT`, reason `EQUIVALENT_SELL_PENDING_CURRENT_POSITION_MISSING`
- with canonical ledger positions: `EQUIVALENT`, reason `SAME_DAY_EQUIVALENT_SELL_PENDING_REUSED`, current position quantity `100.0`

## Current Position Source

Runtime manifest reports:

- PM current source: `.runtime/persistent_ledger/state.json`
- PM current as of: `2022-09-06`
- current position count: `12`
- current exposure: `993080.0`

`.runtime/persistent_ledger/state.json` contains:

- symbol: `93600`
- quantity: `100.0`
- as of: `2022-09-06`
- valuation as of: `2022-09-06`
- source: `runtime_v2_runtime_owned_fill_projection`

`strategy/runtime_planning.json` also records 93600 current position membership quantity `100.0`.

F1L_CURRENT_POSITION_QUANTITY = MISSING_IN_F1L_HELPER, not missing from canonical runtime state.

The mismatch is introduced by the actual call path: the non-executable quantity branch calls `_write_no_signal_pending(...)` without `current_positions=current_positions`.

## EXIT Lineage Resolution

The active pending has multiple EXIT lineage fields:

- item `source_decision_type = SELL_EXIT`
- item `planning_authority_source = rp-2022-09-07-93600-sell_exit-816e30699b8499ff`
- item `policy_source = rp-2022-09-07-93600-sell_exit-816e30699b8499ff`
- quantity contract `planning_intent = SELL_EXIT`
- quantity contract `source_planning_id = rp-2022-09-07-93600-sell_exit-816e30699b8499ff`

The F1L resolver searches these fields and resolves `EXIT` if reached.

SELL_EXIT_LINEAGE_RESOLUTION = PASS

SELL_EXIT_LINEAGE_SOURCE_FIELD = `source_decision_type`; corroborated by `quantity_contract.planning_intent`.

## Branch Ordering

F1L branch is reachable before the generic no-signal active-pending `REVIEW_REQUIRED` branch.

Relevant control flow:

```text
_write_no_signal_pending
-> read active pending
-> _same_day_equivalent_sell_pending_evidence
-> if EQUIVALENT: PASS / REUSE_EXISTING_PENDING
-> else generic active pending conflict: REVIEW_REQUIRED
```

In the actual failed resume, the helper returned not equivalent before any equivalence evidence file was written. The generic branch then wrote `PRESERVE_ACTIVE_PENDING_ON_NO_SIGNAL`.

F1L_BRANCH_REACHABLE_BEFORE_REVIEW_REQUIRED = YES

This is not a branch-ordering defect.

## Resume vs Fresh-Run Code Path

The resumed sell-planning subprocess used regular Runtime:

- command module: `ai_fund_lab_v2.runtime_v2.cli.run_daily_operation`
- job: `sell_planning`
- runtime execution path: `regular_runtime`
- historical replay: `true`
- resumed: `true`

The same `run_sell_planning_pending_pipeline` and `_write_no_signal_pending` code path is used. Resume did not bypass F1L. The actual path differs from the F1L fixture because it enters the non-executable REDUCE no-action branch.

RESUME_USES_F1L_CODE_PATH = YES

## Fixture vs Actual Artifact

Material differences:

1. F1L fixture used `exit_decisions=()` pure no-signal path. Actual resume had PM/Runtime SELL decisions, then all executable quantities collapsed to no-order through non-executable REDUCE handling.
2. F1L fixture no-signal call passed `current_positions` into `_write_no_signal_pending`. Actual non-executable quantity branch did not pass `current_positions`.
3. F1L fixture active pending was represented by the focused helper object only. Actual active pending carried production lineage fields and still resolved EXIT, but only after current position matching.
4. F1L fixture did not cover `REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY` plus active same-day equivalent SELL pending.

FIXTURE_ACTUAL_MATERIAL_DIFFERENCE_COUNT = 4

## Root Cause Classification

ROOT_CAUSE_CLASSIFICATION = CURRENT_POSITION_SOURCE_MISMATCH

The actual pending is economically equivalent and has valid EXIT lineage. The failure occurs because F1L helper is invoked from a call site that omits `current_positions`, so the helper cannot match 93600 to the open position and cannot prove full-exit quantity equivalence.

Secondary contributing classification:

- FIXTURE_NOT_PRODUCTION_EQUIVALENT: the focused F1L fixture did not cover the actual non-executable REDUCE no-action path.

Not supported:

- F1L_EXIT_LINEAGE_RESOLUTION_GAP: lineage resolves when reached.
- F1L_BRANCH_ORDERING_GAP: equivalence helper runs before generic conflict.
- RESUME_CODE_PATH_BYPASSES_F1L: resume uses the same Runtime sell-planning path.
- ACTUAL_PENDING_STATE_NOT_EQUIVALENT: actual pending is equivalent when canonical current positions are supplied.

## Repair Gate

REPAIR_CANDIDATE = YES

The minimal repair candidate is to propagate `current_positions` and the pre-sell snapshot into the non-executable quantity no-action branch that calls `_write_no_signal_pending` for `REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY`. Add an actual-artifact-shaped focused regression covering:

```text
PM REDUCE / discrete-lot non-executable
existing same-day approved SELL_EXIT pending
current position quantity 100
=> PASS / IDEMPOTENT_EXISTING_PENDING / REUSE_EXISTING_PENDING
```

Do not broaden equivalence semantics. The repair should only connect already-canonical current position evidence to the existing F1L predicate in the production call path.

## Final Questions

1. 実resumeでF1L branchは本当に呼ばれたか？
   - Yes. The no-signal active-pending branch reaches the F1L helper before generic `REVIEW_REQUIRED`, but no evidence file is written when the helper returns not equivalent.
2. actual pendingはF1L fixtureと何が違ったか？
   - Actual uses the non-executable REDUCE no-action path; fixture used pure `exit_decisions=()` no-signal.
3. 最初にfalseになったequivalence条件は何か？
   - Current position presence / full current-position quantity proof.
4. 93600 current quantityを100として見られているか？
   - Canonical runtime state has 100, but F1L helper saw missing because the call site passed an empty current position map.
5. SELL_EXIT lineageをactual artifactから解決できているか？
   - Yes, via `source_decision_type = SELL_EXIT` and `quantity_contract.planning_intent = SELL_EXIT`.
6. F1L branchより先に旧conflict guardが発火していないか？
   - No. The F1L branch is ordered before the generic conflict branch.
7. resume pathだけF1Lを迂回していないか？
   - No. Resume uses the same regular Runtime sell-planning path.
8. actual pendingは本当にreuse可能な同等状態か？
   - Yes, when canonical current positions are supplied.
9. F1MのRESUME_SAFE判定のどこが誤っていたか？
   - F1M assumed current positions were available to F1L in every no-action path. It missed the non-executable REDUCE call site that omits `current_positions`.
10. 次に修正すべき最小箇所はどこか？
   - The `_write_no_signal_pending` call in the non-executable quantity branch should pass `existing_buy_pending`, `existing_buy_pending_reason`, `add_result`, `pre_sell_pending_snapshot`, and `current_positions`; then add focused actual-artifact regression.
