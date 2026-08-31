# Phase32-BL - Lot-Blocked REDUCE Binary Materialization SHADOW Design & Implementation

## Scope

Phase32-BL implements a SHADOW-only observation contract for:

`PM REDUCE -> PS/discrete-lot resolution -> REDUCE_UNEXECUTABLE_DUE_TO_DISCRETE_LOT -> NO_ORDER`

No fresh-run, resume, recover, replay, or long Historical run was executed. The currently running Historical run was not mutated.

This is not a production trading change. It adds diagnostic shadow evidence only.

## Root Context

Phase32-BJ showed that converting only lot-blocked REDUCE to Full EXIT had positive descriptive economics in the inspected window, but with material false-exit cost.

Phase32-BK then found partial PIT separability:

- Some lot-blocked REDUCE cases already had EXIT-side deterioration/risk evidence.
- Some had HOLD-side continuation/recovery/winner evidence.
- Existing PM semantics were still `WEAKENING_BUT_INTACT`, not PM EXIT.
- Direct production conversion was not accepted.

Therefore BL creates a shadow materialization layer to record whether a blocked partial REDUCE looks more like:

- `SHADOW_HOLD`
- `SHADOW_FULL_EXIT`
- `SHADOW_INSUFFICIENT_EVIDENCE`
- `SHADOW_NOT_APPLICABLE`

## Boundary Selected

Narrow boundary:

`strategy.unrepresentable_reduce_exit_shadow`

Reason:

- PM provenance is already available.
- PS discrete-lot representability is already known.
- Runtime planning NO_ORDER reason is already available.
- Strategy intelligence / current PIT evidence can be attached.
- Existing module already writes only `diagnostic_shadow/unrepresentable_reduce_exit_shadow.json`.

No PM, PC, PS, order planning, Pending, Submit, Execution, Position, Cash, Candidate Selection, ranking, thresholds, or model path was changed.

## Contract Added

New contract version:

`phase32_bl_lot_blocked_reduce_binary_materialization_shadow.v1`

Eligibility requires all of:

- source PM action is `REDUCE`
- representability family is `DISCRETE_LOT`
- final executable REDUCE quantity is zero
- desired REDUCE quantity is positive
- campaign provenance exists
- current quantity exists and is positive
- PIT evidence is not future-dated
- run/profile/source artifact binding is not stale or cross-run when supplied

Non-eligible cases produce `SHADOW_NOT_APPLICABLE`.

Malformed, missing-provenance, future-dated, stale, or cross-run evidence produces `SHADOW_INSUFFICIENT_EVIDENCE` with `shadow_binary_authority_status = FAIL_CLOSED`.

## Evidence Used

The shadow record uses only existing decision-time/PIT evidence:

- PM reason codes and reason-family context
- expected edge state
- trend health
- persistence
- participation quality
- relative strength
- exhaustion risk
- downside participation / reversal risk
- current campaign state and profit cushion
- recovery state
- action score as diagnostic only

Explicit exclusions:

- no future price
- no future return
- no future regime
- no MFE/MAE from the future
- no final campaign outcome
- no Historical PnL selector
- no `action_score < 0.4` production threshold

## Binary Shadow Semantics

`SHADOW_FULL_EXIT` is recorded when multiple current PIT deterioration/risk dimensions agree and no HOLD-side continuation evidence is present.

`SHADOW_HOLD` is recorded when multiple current PIT continuation/recovery dimensions support retaining the one-lot campaign and EXIT-side evidence is limited.

`SHADOW_INSUFFICIENT_EVIDENCE` is recorded when the evidence is mixed, incomplete, stale, future-dated, cross-run, or otherwise not authoritative.

Reason family is retained as context, not as a mechanical switch.

## Output Fields Added

Each decision now includes:

- `binary_materialization_contract_version`
- `run_id`
- `profile_id`
- `shadow_only`
- `shadow_binary_decision`
- `shadow_binary_eligibility_status`
- `shadow_binary_eligibility_reason`
- `shadow_binary_authority_status`
- `production_actual_action`
- `production_actual_quantity`
- `lot_block_reason`
- `semantic_evidence_used`
- `hold_side_evidence`
- `exit_side_evidence`
- `decisive_semantic_rationale`
- `action_score_decisive_authority = false`
- `historical_outcome_input_used = false`
- `shadow_order_authority = false`
- `shadow_submit_authority = false`
- `shadow_execution_authority = false`

Payload metrics now also count binary shadow outcomes.

## Files Changed

- `src/ai_fund_lab_v2/strategy/unrepresentable_reduce_exit_shadow.py`
- `tests/strategy/test_phase31_c0d_unrepresentable_reduce_exit_shadow.py`
- `docs/phase_reports/phase32_bl_lot_blocked_reduce_binary_materialization_shadow_design.md`

## Production Invariance

Production trading output is unchanged.

The implementation does not mutate:

- PM action
- PC allocation
- PS quantity
- Runtime planning
- Pending
- Submit
- Execution
- Position
- Cash

The shadow artifact continues to be diagnostic-only, with `production_consumer_count = 0` and explicit mutation flags set to false.

## Focused Validation

Commands run:

`PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/unrepresentable_reduce_exit_shadow.py`

Result: PASS.

`python3 -m pytest tests/strategy/test_phase31_c0d_unrepresentable_reduce_exit_shadow.py -q`

Result: `15 passed`.

`python3 -m pytest tests/strategy/test_phase31_c0d_unrepresentable_reduce_exit_shadow.py tests/strategy/test_phase31_g115_add_marginal_authoritative_binding.py tests/strategy/test_phase22_g_runtime_planning.py::test_phase32_f_runtime_does_not_resurrect_buy_wait_add_when_ps_delta_zero tests/strategy/test_phase32_x_recoverable_deterioration_episode.py -q`

Result: `44 passed`.

`python3 -m pytest tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py tests/runtime_v2/test_phase30_ak9r27_pending_review_scope_authority.py tests/runtime_v2/test_phase30_ak9r28_historical_safety_temporal_authority.py -q`

Result: `54 passed`.

## Regression Coverage

Validated:

- production PM/PS/runtime planning inputs remain unchanged
- executable REDUCE is not converted to shadow binary intervention
- minimum-notional NO_ORDER remains a separate unresolved family
- non-REDUCE actions are not invoked
- future-dated evidence fails closed
- missing campaign provenance fails closed
- cross-run evidence fails closed
- Phase32-S ADD acceleration tests remain PASS
- KI-006 zero ADD resurrection guard remains PASS
- Phase32-X recoverable deterioration tests remain PASS
- partial submit / current valuation / review-scope / historical safety adjacent tests remain PASS

## Required Final Answers

`ROOT_CAUSE_CHARACTERIZED`: YES. Lot-blocked PM REDUCE is a representability gap, not a PM EXIT decision.

`BINARY_SHADOW_CONTRACT_DESIGNED`: YES.

`BINARY_SHADOW_CONTRACT_IMPLEMENTED`: YES.

`PRODUCTION_PM_CHANGED`: NO.

`PRODUCTION_PC_CHANGED`: NO.

`PRODUCTION_PS_CHANGED`: NO.

`ORDER_PLANNING_CHANGED`: NO.

`PENDING_CHANGED`: NO.

`SUBMIT_EXECUTION_CHANGED`: NO.

`POSITION_CASH_CHANGED`: NO.

`SHADOW_ONLY`: YES.

`DISCRETE_LOT_ONLY`: YES for binary eligibility.

`EXECUTABLE_REDUCE_PRESERVED`: YES.

`NON_LOT_NO_ORDER_NOT_INVOKED`: YES.

`FUTURE_PNL_USED`: NO.

`ACTION_SCORE_THRESHOLD_USED`: NO. Action score is diagnostic only.

`STALE_OR_CROSS_RUN_EVIDENCE_FAILS_CLOSED`: YES.

`FOCUSED_REGRESSION_RESULT`: PASS.

`ECONOMIC_IMPROVEMENT_CLAIMED`: NO.

`READY_FOR_SHADOW_EVALUATION`: YES.

## Remaining Work

The BL shadow contract is ready for observation/materialization and later audit.

Production activation is not accepted in BL. A future phase must evaluate actual shadow outcomes against PIT-only classifications and false-exit protection before any production semantic change is considered.

## Final Judgment

`PHASE32_BL_LOT_BLOCKED_REDUCE_BINARY_MATERIALIZATION_SHADOW_IMPLEMENTED_PRODUCTION_UNCHANGED_READY_FOR_SHADOW_EVALUATION`
