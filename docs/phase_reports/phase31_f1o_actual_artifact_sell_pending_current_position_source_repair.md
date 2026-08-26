# Phase31-F1O — Actual-Artifact SELL Pending Current-Position Source Propagation Repair

## PRIMARY_JUDGMENT

PHASE31_F1O_ACTUAL_ARTIFACT_CURRENT_POSITION_PROPAGATION_REPAIRED_REGRESSION_PASS

## Required Output

ROOT_CAUSE = CURRENT_POSITION_SOURCE_MISMATCH

IMPLEMENTATION_STATUS = IMPLEMENTED

REPAIR_CALL_SITE = `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`, `run_sell_planning_pending_pipeline`, non-executable quantity / no-executable-quantity branch that returns `_write_no_signal_pending(...)` with `reason=REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY`.

CURRENT_POSITION_AUTHORITY = `.runtime/persistent_ledger/state.json` loaded once by `run_sell_planning_pending_pipeline` into canonical `asset_state`, then filtered into `current_positions`.

ACTUAL_RESUME_PATH_CURRENT_POSITIONS_CONNECTED = YES

ACTUAL_PATH_93600_REGRESSION = PASS

MISSING_CURRENT_POSITION_FAIL_CLOSED = PASS

F1L_EQUIVALENCE_CONTRACT_CHANGED = NO

F1F_ESCALATION_SEMANTICS_CHANGED = NO

F1I_HISTORY_BRIDGE_CHANGED = NO

NEW_POSITION_FALLBACK_AUTHORITY_CREATED = NO

DUPLICATE_PENDING_CREATED = NO

GENUINE_CONFLICT_FAIL_CLOSED = PASS

FUTURE_INFORMATION_USED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

FOCUSED_TEST_RESULTS = PASS; 84 passed

PY_COMPILE = PASS

GIT_DIFF_CHECK = PASS

RESUME_AFTER_F1O = SAFE

NEXT_TASK_RECOMMENDATION = Phase31-F1P focused acceptance / resume readiness. Do not retry resume before F1O acceptance.

## Authority

Read:

- `docs/phase_reports/phase31_f1n_actual_resume_sell_pending_idempotency_activation_audit.md`
- `docs/phase_reports/phase31_f1l_same_day_equivalent_sell_pending_idempotency_repair.md`
- `docs/phase_reports/phase31_f1k_post_f1i_fresh_run_sell_planning_halt_root_cause_audit.md`

F1N is the direct root-cause authority for this repair. It confirmed that the actual pending was economically equivalent and EXIT-lineage-resolvable, but the F1L helper saw an empty `current_positions` map on the actual non-executable REDUCE no-action path.

## Implementation

Changed:

- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py`
- `docs/phase_reports/phase31_f1o_actual_artifact_sell_pending_current_position_source_repair.md`

No Strategy, PM SELL semantic, F1F escalation, F1I bridge, threshold, pending equivalence contract, fresh-run, resume, replay, or long Historical change was made.

## Exact Repair

The repair is input propagation only.

Before F1O, the no-selected-decision path passed:

```text
existing_buy_pending
existing_buy_pending_reason
add_result
pre_sell_pending_snapshot
current_positions
```

but the actual non-executable quantity branch did not pass those inputs when calling `_write_no_signal_pending(...)`.

F1O now passes the same canonical inputs from the non-executable quantity branch:

```text
existing_buy_pending
existing_buy_pending_reason
add_result
pre_sell_pending_snapshot
current_positions
```

The helper still receives current positions only from its caller. It does not perform hidden position lookup.

NEW_POSITION_FALLBACK_AUTHORITY_CREATED = NO

## Current Position Authority

The current position authority remains:

```text
.runtime/persistent_ledger/state.json
-> _load_asset_state(...)
-> asset_state.positions
-> current_positions = positive-quantity positions keyed by symbol
```

The focused actual-path regression materializes:

- symbol: `93600`
- current quantity: `100`
- pending SELL quantity: `100`
- pending lineage: `SELL_EXIT`

The F1L helper now sees `current_position_quantity = 100.0` in that path.

CURRENT_POSITION_AUTHORITY = `.runtime/persistent_ledger/state.json`

## Contract Preservation

F1L equivalence semantics were not broadened.

Still required:

- same business date/session
- approved active pending
- unconsumed
- exactly one approved SELL
- no BUY
- supported item state
- matching symbol
- quantity equal to full current position quantity
- EXIT-equivalent lineage
- no partial-fill marker

Missing current position remains not equivalent.

F1L_EQUIVALENCE_CONTRACT_CHANGED = NO

## Actual-Artifact-Shaped Regression

Added:

`test_phase31_f1o_actual_path_non_executable_reduce_reuses_equivalent_sell_exit_pending`

Scenario:

```text
current position: 93600 quantity 100
existing same-day approved pending: SELL 93600 quantity 100, source_decision_type SELL_EXIT
incoming SELL path: PM/Runtime REDUCE, reduce_intensity LIGHT
quantity contract: REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY
executable sell quantity: 0
```

Expected and observed:

- result status: `PASS`
- reason: `IDEMPOTENT_EXISTING_PENDING:SAME_DAY_EQUIVALENT_SELL_PENDING_REUSED`
- pending composition model: `SAME_DAY_EQUIVALENT_SELL_PENDING_IDEMPOTENCY`
- pending composition status: `PASS`
- pending equivalence status: `EQUIVALENT`
- resolution action: `REUSE_EXISTING_PENDING`
- original pending preserved: `true`
- duplicate pending created: `false`
- current position quantity seen by helper: `100.0`
- pending file unchanged
- no `REVIEW_REQUIRED`

ACTUAL_PATH_93600_REGRESSION = PASS

## Missing Position Fail-Closed

Added:

`test_phase31_f1o_missing_current_position_still_fail_closed`

Scenario:

```text
current positions contain 68360 only
active pending contains SELL_EXIT 93600 quantity 100
incoming REDUCE decision references 93600
```

Expected and observed:

- result status: `REVIEW_REQUIRED`
- original pending preserved
- no same-day equivalence evidence created
- pending file unchanged

MISSING_CURRENT_POSITION_FAIL_CLOSED = PASS

## Genuine Conflict Preservation

Existing focused F1L tests continue to cover:

- quantity mismatch
- multiple active SELL items
- different session
- BUY pending semantics
- REDUCE-vs-EXIT exposure mismatch

Existing SELL reconciliation and BUY/Pending suites passed unchanged.

GENUINE_CONFLICT_FAIL_CLOSED = PASS

## F1F / F1I Preservation

F1O did not touch Strategy, PM, F1F semantic state, or F1I history bridge code.

Focused F1F/F1I tests passed:

- `tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py`
- `tests/strategy/test_phase31_f1i_prior_unrepresentable_reduce_bridge.py`

F1F_ESCALATION_SEMANTICS_CHANGED = NO

F1I_HISTORY_BRIDGE_CHANGED = NO

CANONICAL_SELL_STATES_CHANGED = NO

## Static Resume Path Revalidation

Without executing resume:

```text
actual resumed sell_planning
-> run_sell_planning_pending_pipeline
-> load canonical current position state
-> build current_positions
-> REDUCE quantity contract resolves non-executable / no executable quantity
-> _write_no_signal_pending(..., current_positions=current_positions)
-> F1L same-day equivalent SELL pending helper
-> 93600 full-position equivalence can resolve
-> PASS / REUSE_EXISTING_PENDING
```

ACTUAL_RESUME_PATH_CURRENT_POSITIONS_CONNECTED = YES

## Resume Readiness

RESUME_AFTER_F1O = SAFE

Reason:

- The actual failed predicate was current position missing inside the helper.
- F1O connects the canonical current position map to the actual failing path.
- The halted run had not reached 2022-09-07 submit/execution.
- The active pending is same-day, approved, single SELL, quantity 100, EXIT-lineage-resolvable.
- F1O does not create duplicate pending/order/fill behavior.

Resume still should be accepted in a separate F1P readiness/acceptance step before the user retries it.

## Regression Results

Commands:

```bash
python3 -m pytest tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py -q
python3 -m pytest tests/runtime_v2/test_phase28_d3_sell_pending_reconciliation.py -q
python3 -m pytest tests/runtime_v2/test_phase21_b_pending_composition_add_consumer.py -q
python3 -m pytest tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py -q
python3 -m pytest tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py tests/strategy/test_phase31_f1i_prior_unrepresentable_reduce_bridge.py -q
```

Results:

- F1L/F1O same-day SELL pending idempotency: 10 passed
- existing SELL pending reconciliation: 10 passed
- BUY/Pending safety: 28 passed
- Runtime SELL quantity/materialization: 22 passed
- F1F/F1I preservation: 14 passed

FOCUSED_TEST_RESULTS = PASS; 84 passed

Compile:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py
```

PY_COMPILE = PASS

GIT_DIFF_CHECK = PASS

## Final Questions

1. actual non-executable REDUCE branchにcurrent_positionsを渡せたか？
   - Yes.
2. 93600を100株保有としてhelperが認識できるか？
   - Yes. The actual-path regression observes `current_position_quantity = 100.0`.
3. actual-path fixtureでIDEMPOTENT reuseまで通るか？
   - Yes. It returns `PASS` / `IDEMPOTENT_EXISTING_PENDING` / `REUSE_EXISTING_PENDING`.
4. F1L contract自体を広げず修理できたか？
   - Yes. Only caller-side evidence propagation changed.
5. position fallback authorityを新設していないか？
   - No.
6. genuine conflictは従来どおり止まるか？
   - Yes.
7. F1F/F1I SELL semanticsを完全に維持しているか？
   - Yes.
8. 修理後、既存HALT runを安全にresumeできるか？
   - SAFE, pending F1P focused acceptance / resume readiness.
