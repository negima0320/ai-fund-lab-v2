# Phase32-BV BQ FULL EXIT Campaign Identity Propagation Actual-Path Repair

## Final Judgment

`PHASE32_BV_BQ_FULL_EXIT_CAMPAIGN_IDENTITY_PROPAGATION_REPAIRED_SAME_RUN_CONTINUATION_SAFE`

## Target Run

- Run: `runtime-test-historical-extended-smoke-20260831T231046348584Z`
- Halt: `2022-10-07:sell_planning`
- Exit code: `20`
- Target symbol: `45750`
- Completed through: `2022-10-06`
- Submit/execution side effects on `2022-10-07`: `NO`

No fresh-run, resume, recover, replay, or long Historical run was executed during BV.

## Root Cause

Phase32-BU correctly identified the first canonical failure:

`MISSING_CAMPAIGN_ID`

The BQ Strategy decision was valid: `45750` was a PM `REDUCE`, raw reduce quantity `25`, executable quantity `0`, lot-blocked by `REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT`, and BO/BQ classified it as `SHADOW_FULL_EXIT` / production `FULL_EXIT`.

The defect was not BO/BQ sell semantics. The defect was an actual-path materialization gap:

`positions/position_campaigns.json` and Strategy Intelligence had canonical campaign `pc-1c231f87db41dc41-45750-0001`, but the Runtime PM producer did not propagate that campaign into `.runtime/runtime_state/position_management/2022-10-07/position_management_decisions.json`. `SellExitDecision` was then built from the runtime PM artifact without `position_campaign_id`, so BQ promotion fail-closed before ordinary `SELL_EXIT` order-plan materialization.

## First Bad Boundary

`Runtime PM producer decision payload materialization`

Specifically:

`current run positions/position_campaigns.json -> position_management_decisions.json -> SellExitDecision`

The canonical campaign existed upstream, but was missing from the PM runtime handoff.

## Canonical Authority

The selected authority is explicit run-scoped current-date campaign evidence:

`reports/runtime_tests/runs/<run_id>/daily/<business_date>/positions/position_campaigns.json`

The repair accepts it only when:

- artifact `business_date` matches the PM decision date
- artifact/run binding matches the current runtime test run when provided
- row-level run binding does not conflict
- exactly one open campaign identity exists for the symbol
- no `future_information_used` flag is present

No symbol-only ID generation, no stale cross-run acceptance, no future evidence, and no campaign fabrication was added.

## Repair Performed

- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
  - Added optional `runtime_test_evidence_root` and `runtime_test_run_id`.
  - Reads run-scoped `positions/position_campaigns.json` as campaign authority.
  - Propagates `position_campaign_id`, `campaign_id`, and `campaign_identity_authority` into each PM decision payload.
  - Fails closed as `REVIEW_REQUIRED` for stale/cross-run/malformed/ambiguous campaign authority.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
  - Passes runtime-test evidence root/run id into PM producer for both `morning` and `sell_planning`.
- `tests/runtime_v2/test_phase15ap_position_management_input_contract.py`
  - Added actual-path BV fixture: PM producer -> no-order `REDUCE` -> BQ `FULL_EXIT` -> ordinary `SELL_EXIT`.
  - Added cross-run and ambiguous-campaign fail-closed tests.
- `scripts/phase32_bv_pm_authority_acceptance_repair.py`
  - Canonical PM Runtime Adapter authority acceptance wrapper.

Existing Phase32-BT `sell_pipeline.py` changes remain intact: FULL_EXIT promotion still requires complete campaign authority and still rejects genuine missing/mismatched campaign identity.

## PM Authority Synchronization

Because `producer.py` is the accepted-current-path PM Runtime Adapter, BV created a new formal accepted PM set through the existing canonical registry acceptance/index/checkpoint path.

- New active PM set: `control.position_management.accepted_set@sha256-9ddf78380b426d8f`
- Accepted `RUNTIME_ADAPTER` source hash: `661607eed78087590b06c9058fe7338f3b048711197af0737a4d7b8d5cda86a9`
- Executing `producer.py` source hash: `661607eed78087590b06c9058fe7338f3b048711197af0737a4d7b8d5cda86a9`
- Registry event log: `PASS`
- Registry index: `PASS`
- Registry checkpoint: `PASS`
- Runtime resolver: `PASS`
- Genuine mismatch fail-close: `PASS`

This was not a manual hash patch and did not weaken hash validation.

## Target Run Read-Only Continuation Assessment

Current target evidence shows:

- `run_state.next_job = 2022-10-07:sell_planning`
- no `2022-10-07/submit` evidence directory
- no `2022-10-07/execution` evidence directory
- 45750 current campaign in `positions/position_campaigns.json`: `pc-1c231f87db41dc41-45750-0001`
- 45750 Strategy Intelligence lifecycle campaign: `pc-1c231f87db41dc41-45750-0001`
- existing stale PM runtime artifact lacked campaign, explaining the halt

Under the repaired source, `sell_planning` will rerun PM producer for `2022-10-07`, read the same run-scoped campaign authority, and hand BQ a complete `SellExitDecision`. Same-run continuation is safe from:

`2022-10-07:sell_planning`

No 2022-10-07 rewind, replay, fresh-run, or duplicate-preservation step is required based on current evidence.

## Focused Validation

PASS:

- `PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase15ap_position_management_input_contract.py -k 'phase32_bv'`
  - `3 passed`
- `PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py -k 'phase32_bq or phase32_bt or 45750'`
  - `11 passed`
- `PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase15ap_position_management_input_contract.py tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py`
  - `41 passed`
- `PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_submit_uses_order_increment_not_position_scope_delta tests/runtime_v2/test_phase24_ht_planning_submit_feasibility.py::test_phase31_g129_buy_add_true_order_increment_mismatch_still_reviews`
  - `2 passed`
- `PYTHONPATH=src python3 scripts/phase32_bv_pm_authority_acceptance_repair.py`
  - `PHASE17_B1I_B_PM_ADAPTER_AUTHORITY_ACCEPTED`

## Strategy Semantics

- BO semantics changed: `NO`
- BQ full-exit eligibility changed: `NO`
- PM reason logic changed: `NO`
- SELL/REDUCE thresholds changed: `NO`
- model/features/weights changed: `NO`
- profit cushion changed: `NO`
- G129 BUY_ADD regression: `NO`
- BT non-promoted BO HOLD/INSUFFICIENT behavior preserved: `YES`

## Required Final Answers

1. `ROOT_CAUSE_REPAIRED`: `YES`
2. `BQ_FULL_EXIT_CAMPAIGN_IDENTITY_PROPAGATION_REPAIRED`: `YES`
3. `45750_CAN_MATERIALIZE_ORDINARY_SELL_EXIT`: `YES`
4. `PM_PRODUCER_CAMPAIGN_PROPAGATION_FIXED`: `YES`
5. `RUNTIME_PM_ARTIFACT_CAMPAIGN_ID_FIXED`: `YES`
6. `SELL_EXIT_DECISION_HANDOFF_CAMPAIGN_ID_FIXED`: `YES`
7. `NO_NEW_CAMPAIGN_GENERATED`: `YES`
8. `NO_SYMBOL_ONLY_ID_LOOKUP`: `YES`
9. `NO_STALE_CROSS_RUN_AUTHORITY`: `YES`
10. `NO_FUTURE_EVIDENCE_USED`: `YES`
11. `MISSING_CAMPAIGN_FAIL_CLOSED`: `YES`
12. `CAMPAIGN_MISMATCH_FAIL_CLOSED`: `YES`
13. `STALE_CAMPAIGN_FAIL_CLOSED`: `YES`
14. `BO_HOLD_NON_PROMOTED_BEHAVIOR_PRESERVED`: `YES`
15. `BO_INSUFFICIENT_NON_PROMOTED_BEHAVIOR_PRESERVED`: `YES`
16. `BQ_FULL_EXIT_SEMANTICS_CHANGED`: `NO`
17. `SELL_REDUCE_THRESHOLDS_CHANGED`: `NO`
18. `PM_REASON_LOGIC_CHANGED`: `NO`
19. `PROFIT_CUSHION_CHANGED`: `NO`
20. `G129_REGRESSION`: `NO`
21. `FOCUSED_REGRESSION_RESULT`: `PASS`
22. `ACTUAL_PATH_45750_FIXTURE_RESULT`: `PASS`
23. `PM_RUNTIME_ADAPTER_AUTHORITY_SYNCHRONIZED`: `YES`
24. `ACCEPTED_PM_GENERATION_SELECTED`: `control.position_management.accepted_set@sha256-9ddf78380b426d8f`
25. `ACCEPTED_RUNTIME_ADAPTER_HASH`: `661607eed78087590b06c9058fe7338f3b048711197af0737a4d7b8d5cda86a9`
26. `HASH_VALIDATION_BYPASSED`: `NO`
27. `FAIL_CLOSED_BEHAVIOR_PRESERVED`: `YES`
28. `TARGET_RUN_SUBMIT_SIDE_EFFECT_PRESENT`: `NO`
29. `TARGET_RUN_EXECUTION_SIDE_EFFECT_PRESENT`: `NO`
30. `SAME_RUN_CONTINUATION_POSSIBLE_AFTER_REPAIR`: `YES`
31. `SAFE_CONTINUATION_POINT`: `2022-10-07:sell_planning`
32. `FRESH_RUN_REQUIRED`: `NO`
33. `NEXT_OPERATOR_ACTION`: run same-run resume from the current halt point
34. `RESUME_EXECUTED_BY_CODEX`: `NO`
35. `FINAL_JUDGMENT`: `PHASE32_BV_BQ_FULL_EXIT_CAMPAIGN_IDENTITY_PROPAGATION_REPAIRED_SAME_RUN_CONTINUATION_SAFE`

## Next Operator Action

```bash
RUN_ID=runtime-test-historical-extended-smoke-20260831T231046348584Z
PYTHONPATH=src python3 scripts/runtime_test.py resume \
  --run-id "$RUN_ID" \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```
