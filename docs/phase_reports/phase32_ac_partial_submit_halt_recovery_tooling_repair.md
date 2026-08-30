# Phase32-AC Partial Submit HALT Recovery Tooling Repair

## Scope

- Target run shape: partial submit success plus later approved item block plus `HALT` at Submit
- Actual motivating run: `runtime-test-historical-extended-smoke-20260830T081425790243Z`
- Target date: `2023-10-11`
- Source identity inspected during repair: `4ff63ba05a0012c60fce50741a946eed672f8990`
- Codex did not execute recovery, replay, resume, fresh-run, or long Historical against the target run.

## Root Cause

Phase32-AB confirmed that existing recovery tooling had a lifecycle coverage gap:

- `recover-failed-execution` required `run_state.next_job == <date>:execution` and whole Pending state `CONSUMED`.
- `recover-stale-pending` required `run_state.next_job == <date>:sell_planning` and no target-date Ledger rows.
- The target shape was `run_state.next_job == 2023-10-11:submit`, Pending state `REVIEW_REQUIRED`, one consumed/accepted item (`92460`), one approved but blocked item (`50280`), reviewed BUY items, one target-date order row, and no execution/current rows.

Therefore no canonical tooling existed for:

`partial submit success + later item block + submit HALT`

## Repair Performed

Added explicit command:

`recover-partial-submit`

The command is intentionally separate from `recover-failed-execution` so execution-boundary recovery semantics remain narrow.

The new command:

- validates Historical mutation context;
- requires `HALT` at `<business-date>:submit`;
- requires previous completed day Current to remain coherent;
- requires mixed same-day Pending state `REVIEW_REQUIRED`;
- requires at least one `CONSUMED` Pending item with matching accepted order and historical broker evidence;
- requires at least one approved not-submitted item with canonical Submit guard block evidence;
- requires target-date executions/positions/cash/events rows to be absent;
- preserves accepted order rows and historical broker evidence;
- retires the mixed Pending slot to `EMPTY` with preservation/replay metadata;
- rewinds `run_state.next_job` to the requested scoped replay boundary, normally `morning`;
- records `scoped_partial_submit_recovery` and recovery evidence under the run's recovery directory.

## Accepted Item Preservation

The repair does not delete or rewrite the accepted `92460` order row. It also does not remove historical broker accepted evidence.

Replay duplicate prevention is delegated to the existing Submit authority:

`pending_item_existing_submission_reconciliation`

That path reconciles a regenerated Pending item against existing accepted Ledger/historical-broker evidence by pending plan id, pending item id, symbol, side, quantity, and order id before broker preflight or adapter submit. Existing focused Submit tests verify retry does not create a duplicate order or broker submit call.

## Files Changed

- `scripts/runtime_test.py`
  - Added parser/dispatch for `recover-partial-submit`.
  - Added partial-submit recovery plan builder, preconditions, evidence preservation, Pending retirement, and run_state rewind.
- `tests/runtime_v2/test_phase17_k_runtime_test_runner.py`
  - Added 2023-10-11 actual-shaped fixture and focused tests for dry-run, actual recovery, idempotent/fail-closed rerun, and broker mismatch rejection.
- `docs/02_architecture/runtime_test_specification.md`
  - Added scoped partial submit recovery contract.
- `docs/03_operations/runtime_test_command_guide.md`
  - Added operator command documentation and command inventory row.

## Why This Is Canonical

This is not a hash bypass, manual state edit, or partial restore. It is a formal Runtime Test recovery command with dry-run, confirmation flags, explicit preconditions, recovery evidence, and fail-closed ambiguity handling.

Accepted external/simulated submit evidence is preserved and reconciled. Unaccepted items are regenerated from the scoped replay boundary under current Planning/Pending/Submit semantics, including Phase32-AA corporate-action authority.

## Strategy Semantic Change

NO.

No Candidate selection, Opportunity logic, BUY/SELL/ADD thresholds, weights, Cash policy, Risk Pacing, Phase32-S, Phase32-X, G129, or PM Strategy semantics were changed.

## Focused Validation

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile scripts/runtime_test.py tests/runtime_v2/test_phase17_k_runtime_test_runner.py
```

Result: PASS.

```bash
python3 -m pytest -q tests/runtime_v2/test_phase17_k_runtime_test_runner.py -k 'phase32_ac or l21t_q3b or l21t_q1b or stale_pending_recovery'
```

Result: `11 passed, 37 deselected`.

```bash
python3 -m pytest -q tests/runtime_v2/test_phase17_k_runtime_test_runner.py
```

Result: `48 passed`.

```bash
python3 -m pytest -q tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py::test_phase31_f1w_partial_submit_reconciles_existing_items_and_submits_missing_once tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py::test_phase31_f1y_existing_sell_reconciliation_precedes_available_quantity_guard
```

Result: `2 passed`.

```bash
python3 -m pytest -q tests/runtime_v2/test_phase31_a5_executable_membership_guard.py tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py
```

Result: `32 passed`.

```bash
python3 -m pytest -q tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_submit_uses_order_increment_not_position_scope_delta tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_true_order_increment_mismatch_still_reviews tests/runtime_v2/test_phase31_g30_authority_lineage.py::test_phase32_c_pending_provenance_mismatch_fails_closed
```

Result: `3 passed`.

```bash
python3 -m pytest -q tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py tests/strategy/test_phase32_x_recoverable_deterioration_episode.py
```

Result: `28 passed`.

```bash
python3 -m pytest -q tests/strategy/test_phase29_l21k_prior_exit_materialization.py::test_phase32_h_prior_exit_context_uses_strict_prior_pm_exit_detail tests/strategy/test_phase29_l21k_prior_exit_materialization.py::test_phase32_j_prior_exit_context_can_join_by_pm_decision_id_when_sell_campaign_missing tests/strategy/test_phase29_l21k_prior_exit_materialization.py::test_phase32_p_date_only_reentry_rows_are_enriched_with_canonical_prior_context tests/strategy/test_phase29_l21k_prior_exit_materialization.py::test_phase32_p_actual_strategy_entrypoint_materializes_rejected_reentry_prior_context tests/strategy/test_phase29_l21k_prior_exit_materialization.py::test_phase32_l_83060_actual_path_reentry_provenance_reaches_final_result tests/strategy/test_phase29_l21k_prior_exit_materialization.py::test_phase32_j_reentry_recovery_failure_does_not_become_safety_block tests/strategy/test_phase29_l21k_prior_exit_materialization.py::test_phase32_j_prior_context_insufficiency_does_not_become_safety_block tests/strategy/test_phase29_l21k_prior_exit_materialization.py::test_phase32_j_genuine_safety_block_remains_fail_closed tests/strategy/test_phase29_l21k_prior_exit_materialization.py::test_phase32_j_broker_and_corporate_statuses_stay_separate_from_safety
```

Result: `8 passed, 1 skipped`.

```bash
python3 -m pytest -q tests/runtime_v2/test_phase26_step6_submit_guard_authority.py tests/runtime_v2/test_phase30_q2_listing_transition_corporate_action_authority.py
```

Result: `21 passed`.

```bash
python3 -m pytest -q tests/runtime_v2/test_phase17_bv8_historical_submit_pit_universe_authority.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py
```

Result: `27 passed`.

## Regression Assessment

- Existing failed-execution recovery: PASS
- Existing stale-pending recovery: PASS
- Replay command surface: unchanged
- Submit idempotency / existing item reconciliation: PASS
- Same-day sell Pending idempotency: PASS
- Phase32-AA corporate-action authority: PASS
- Phase32-S ADD acceleration: PASS through focused regression
- Phase32-X winner retention: PASS through focused regression
- Phase32-C provenance: PASS through focused regression
- Phase32-L/P/Q REENTRY provenance: PASS through focused regression
- G129 BUY_ADD: PASS
- KI-004 safety/broker/corporate-action separation: PASS
- KI-006 zero ADD preservation: PASS through Phase32-S focused regression

## Same-Run Continuation Contract

After operator-applied recovery and scoped replay:

- same `run_id` is preserved;
- completed days through `2023-10-10` remain valid;
- `2023-10-11` is replayable from `morning`;
- accepted `92460` submit evidence is reconciled, not resubmitted;
- `50280` is expected to regenerate under Phase32-AA as `REVIEW_REQUIRED` before Submit;
- resume should be dry-run checked before confirmed continuation.

Fresh-run required: NO, unless later replay/resume evidence reveals new contamination.

## Exact Next Operator Action

Dry-run first:

```bash
RUN_ID=runtime-test-historical-extended-smoke-20260830T081425790243Z
PYTHONPATH=src python3 scripts/runtime_test.py recover-partial-submit \
  --profile historical-extended-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id "$RUN_ID" \
  --business-date 2023-10-11 \
  --rewind-to-job morning \
  --expected-pending-plan-id pending-strategy-plan-historical-2023-10-11-f650d7dcd8b7c7d7 \
  --dry-run \
  --json
```

If dry-run passes, apply recovery:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py recover-partial-submit \
  --profile historical-extended-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id "$RUN_ID" \
  --business-date 2023-10-11 \
  --rewind-to-job morning \
  --expected-pending-plan-id pending-strategy-plan-historical-2023-10-11-f650d7dcd8b7c7d7 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

Then replay the recovered day:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py replay-recovered-day \
  --profile historical-extended-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id "$RUN_ID" \
  --business-date 2023-10-11 \
  --jobs morning,sell_planning,submit,execution \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

Then inspect resume readiness:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py resume \
  --profile historical-extended-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id "$RUN_ID" \
  --dry-run \
  --json
```

## Final Judgment

`PHASE32_AC_PARTIAL_SUBMIT_HALT_RECOVERY_TOOLING_REPAIRED`
