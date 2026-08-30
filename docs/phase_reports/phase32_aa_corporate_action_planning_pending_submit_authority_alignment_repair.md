# Phase32-AA Corporate Action Planning/Pending/Submit Authority Alignment Repair

## Scope

- Target halted run: `runtime-test-historical-extended-smoke-20260830T081425790243Z`
- Target date/stage: `2023-10-11:submit`
- Repair type: narrow Runtime authority alignment
- Execution boundary: no fresh-run, resume, replay, or long Historical executed by Codex
- Strategy changes: none

## Root Cause

Phase32-Z identified the first canonical failure at `2023-10-11:submit`: approved SELL item `strategy-b6716e1e95fc9cc0a9aa` for symbol `50280`, quantity `100`, reached Submit as `APPROVED` / `PASS_ITEM_SUBMITTABLE` even though the same-day PIT corporate-action adjustment authority was unresolved.

Submit correctly materialized:

- `corporate_action_event_status=IMPACT_DETECTED`
- `corporate_action_event_type=UNKNOWN_ADJFACTOR_IMPACT`
- `corporate_action_adjustment_factor=0.3333333333333333`
- `corporate_action_adjustment_authority_status=REVIEW_REQUIRED`
- `reason=corporate_action_event_type_or_adjustment_application_unresolved`
- `pit_validation_status=PASS`
- `future_data_used=false`

The defect was not the Submit HALT itself. Submit was the final fail-closed defense working correctly. The violated boundary was earlier:

`Runtime Planning/Pending approval -> Submit`

Pending approved a SELL that already required unresolved corporate-action review under the same Runtime-owned authority.

## Repair

Implemented a shared Historical PIT corporate-action evidence path and consumed it before Pending approval for Historical planning items.

### Contract

For Historical items, Planning/Pending now resolves the same business-date PIT `AdjFactor` corporate-action event evidence used by Submit, materializes/evaluates `Corporate Action Adjustment Authority`, and attaches the resulting authority to the pending item before planning submit feasibility membership is evaluated.

If the authority is unresolved, Pending materializes item `REVIEW_REQUIRED` with corporate-action observability fields instead of allowing the item to become `APPROVED` / `PASS_ITEM_SUBMITTABLE`.

Submit Guard remains unchanged as the final hard guard.

## Files Changed

- `src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py`
  - Added `historical_corporate_action_event_evidence(...)` as the shared PIT AdjFactor event evidence producer.
  - Kept `HistoricalSubmitAdapter.corporate_action_event_evidence(...)` on the same producer.
- `src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py`
  - Materializes/evaluates Historical corporate-action adjustment authority before Pending membership.
  - Carries status, reason, event status/type, adjustment factor, reconciliation statuses, PIT status, authority path/hash, and future-data flag into Pending item evidence.
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
  - Uses the shared Historical corporate-action evidence producer at Submit, preserving Submit's final fail-closed guard.
- `tests/runtime_v2/test_phase31_a5_executable_membership_guard.py`
  - Added Phase32-AA regressions for the 50280 AdjFactor `1/3` SELL shape, PASS SELL control, and BUY-item-scoped partial submission preservation.
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
  - Updated AE-8.4-IL to make the Planning/Pending approval boundary part of the durable corporate-action authority contract.

## Why This Is Canonical

This repair does not patch hashes, bypass validation, weaken Submit, or infer corporate-action meaning from price movement. It moves the same Runtime-owned authority earlier in the lifecycle, so Pending approval and Submit consume the same PIT corporate-action evidence and fail-closed semantics.

`AdjFactor` remains only an impact signal. Unknown event type or unresolved application lineage still requires review.

## Required 50280 Regression

Focused regression now covers:

- business date: `2023-10-11`
- symbol: `50280`
- side: `SELL`
- quantity: `100`
- PIT raw OHLCV `AdjFactor=0.3333333333333333`
- expected Pending outcome: not approved, not `PASS_ITEM_SUBMITTABLE`
- expected evidence: explicit `REVIEW_REQUIRED` before Submit
- future information: not used

Result: PASS.

## Partial Submission Semantics

BUY-item-scoped corporate-action review still permits unrelated PASS SELL continuation under the existing Pending partial-submit contract.

Unresolved SELL corporate-action authority is not BUY-item scoped; it remains eligible to block according to the existing non-BUY-scoped Pending review contract.

## Focused Validation

Commands executed:

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py tests/runtime_v2/test_phase31_a5_executable_membership_guard.py
```

Result: PASS.

```bash
python3 -m pytest -q tests/runtime_v2/test_phase31_a5_executable_membership_guard.py
```

Result: `7 passed`.

```bash
python3 -m pytest -q tests/runtime_v2/test_phase31_a5_executable_membership_guard.py tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_submit_uses_order_increment_not_position_scope_delta tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_true_order_increment_mismatch_still_reviews tests/runtime_v2/test_phase31_g30_authority_lineage.py::test_phase32_c_pending_provenance_mismatch_fails_closed
```

Result: `35 passed`.

```bash
python3 -m pytest -q tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py tests/strategy/test_phase32_x_recoverable_deterioration_episode.py tests/strategy/test_phase29_l21k_prior_exit_materialization.py::test_phase32_l_83060_actual_path_reentry_provenance_reaches_final_result
```

Result: `29 passed`.

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

An initial Strategy/KI-004 command used obsolete test names and failed at collection with `no tests ran`; the current test names were located and rerun successfully above.

## Regression Assessment

- Phase32-C provenance: PASS in focused regression
- Phase32-L campaign identity / REENTRY provenance: PASS in focused regression
- Phase32-P/Q REENTRY provenance materialization: PASS in focused regression
- Phase32-S ADD acceleration: PASS in focused regression
- Phase32-X winner retention: PASS in focused regression
- G129 BUY_ADD order-increment semantics: PASS in focused regression
- KI-004 safety/broker/corporate-action separation: PASS in focused regression
- KI-006 Buy Quality zero preservation: PASS through Phase32-S focused regression
- Submit idempotency / partial Pending: PASS in focused regression
- Submit corporate-action final guard: PASS in focused regression

## Strategy Semantic Change

NO.

No Candidate selection, Opportunity, PM Strategy semantics, BUY/SELL/ADD thresholds, weights, Cash policy, Risk Pacing, re-entry rules, G129 behavior, or Phase32-S/X Strategy mechanics were changed.

## Same-Run Recovery Classification

`RECOVER_FAILED_EXECUTION_THEN_REPLAY_THEN_RESUME`

Reason: Phase32-Z found target-date Ledger rows already exist for `2023-10-11`, so `recover-stale-pending` is not the canonical path. The operations guide says `recover-failed-execution` is the recovery path for failed execution or submit-only precommit HALT shapes, followed by `replay-recovered-day` and then resume inspection.

Fresh-run required: NO.

Same-run resume safe after repair: YES, after successful dry-run and actual scoped recovery/replay evidence. Codex did not execute recovery, replay, or resume.

Completed 252BD validity: YES. The defect starts at the `2023-10-11` submit boundary and does not contaminate trusted completed measurement through `2023-10-10`.

## Next User Action

Dry-run recovery first:

```bash
RUN_ID=runtime-test-historical-extended-smoke-20260830T081425790243Z
PYTHONPATH=src python3 scripts/runtime_test.py recover-failed-execution \
  --profile historical-extended-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id "$RUN_ID" \
  --business-date 2023-10-11 \
  --rewind-to-job morning \
  --dry-run \
  --json
```

If the dry-run passes and evidence matches expectation, apply recovery, replay the recovered day, inspect evidence, then resume:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py recover-failed-execution \
  --profile historical-extended-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id "$RUN_ID" \
  --business-date 2023-10-11 \
  --rewind-to-job morning \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json

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

PYTHONPATH=src python3 scripts/runtime_test.py resume \
  --profile historical-extended-smoke \
  --runtime-root .runtime \
  --evidence-root reports/runtime_tests \
  --run-id "$RUN_ID" \
  --dry-run \
  --json
```

Only after dry-run resume passes should the operator execute confirmed resume.

## NO CODE CHANGE Confirmation

Not applicable. Phase32-AA was a repair implementation phase, and code changes were required.

## NO Future-Information Use

Confirmed. The repair uses same business-date Historical PIT raw OHLCV evidence and the existing PIT validation fields. No future price, return, regime, MFE/MAE, final outcome, or profitability evidence was used.

## Final Judgment

`PHASE32_AA_CORPORATE_ACTION_PLANNING_PENDING_SUBMIT_AUTHORITY_ALIGNED_REPAIRED`
