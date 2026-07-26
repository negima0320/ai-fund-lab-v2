# Phase20-M: REDUCE Minimum Tradable Quantity Contract Correction

## 1. Executive Summary

Phase20-M corrected the REDUCE quantity contract for the minimum-tradable-unit case. A valid PM `REDUCE` decision whose deterministic Sell Planning quantity rounds to zero is now recorded as execution-feasibility `NOT_EXECUTABLE`, with no pending SELL item and Runtime continuation `PASS`.

Final judgment:

```text
PHASE20_M_RUNTIME_CONTINUITY_CORRECTED_FRESH_RUN_REQUIRED
```

## 2. Scope and Non-goals

Scope was limited to Sell Planning quantity contract semantics, pending no-order evidence, Runtime Test PM observability wording, contract documentation, and targeted regression tests.

No AI, Opportunity, PM decision policy, Risk, Capital Allocation, Broker, Accepted Generation, Training, Calibration, Validation, long historical run, full backtest, or external benchmark behavior was changed.

## 3. Source Run and Failure Evidence

Source run:

```text
runtime-test-historical-extended-smoke-20260722T070512511620Z
```

Failure point:

```text
business_date = 2026-06-18
job = sell_planning
cli exit_code = 20
final_state = REVIEW_REQUIRED
reason = sell planning pipeline review required: REVIEW_REQUIRED_REDUCE_ROUNDED_QUANTITY_ZERO
```

PM evidence for `50310`:

```text
pm_decision_id = pm-2026-06-18-50310-reduce
decision_type = REDUCE
decision_reason = risk_increased_but_trend_not_broken
decision_status = SELL_PARTIAL_POSITION_REDUCE_QUANTITY_BY_SELL_PLANNING
quantity_before = 300
```

## 4. Reviewed Documents

- `docs/02_architecture/position_management_reduce_quantity_contract.md`
- `docs/03_operations/runtime_test_command_guide.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/runtime_test_specification.md`
- `docs/phase_reports/phase20_l_long_run_readiness_destructive_review.md`

## 5. Reviewed Implementation

- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `scripts/runtime_test.py`
- `tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py`

## 6. Quantity Authority

PM owns the Strategy decision: `REDUCE`.

Sell Planning owns executable SELL quantity for REDUCE through `runtime_v2_pm_reduce_quantity_v1`.

Submit Guard remains final pre-broker validation authority for executable orders. In the corrected zero-rounded case no order reaches Submit Guard.

## 7. REDUCE Quantity Calculation

For `quantity_before=300`, `reduce_intensity=LIGHT`, and default tradable unit `100`:

```text
target_reduce_ratio = 0.25
raw_requested_quantity = 75
rounded_executable_quantity = 0
```

The PM decision remains `REDUCE`. The effective trading action is `NO_SELL_ORDER`.

## 8. Existing Review-required Contract

Before correction, `rounded_reduce_quantity <= 0` returned:

```text
status = REVIEW_REQUIRED
reason = REVIEW_REQUIRED_REDUCE_ROUNDED_QUANTITY_ZERO
final_sell_quantity = 0
```

The pipeline treated every zero final quantity as review-required, producing an empty pending plan and stopping the long run.

## 9. Root Cause

The implementation conflated a valid non-executable REDUCE feasibility outcome with a quantity-authority or calculation defect. The Strategy decision was valid and the deterministic quantity calculation was complete, but the runtime contract did not have a non-blocking representation for "valid REDUCE below minimum tradable quantity."

## 10. Corrected Contract

Corrected zero-rounded REDUCE contract:

```text
status = NOT_EXECUTABLE
reason = REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY
execution_feasibility_status = NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY
rounded_executable_quantity = 0
final_sell_quantity = 0
pending_order_generated = false
effective_action = NO_SELL_ORDER
position_quantity_after = unchanged
runtime_continuation_status = PASS
position_lifecycle_event = REDUCE_NOT_EXECUTED_MINIMUM_TRADABLE_QUANTITY
```

## 11. Execution Feasibility Semantics

`NOT_EXECUTABLE_BELOW_MINIMUM_TRADABLE_QUANTITY` is not a Strategy rewrite. It does not turn REDUCE into HOLD or EXIT. It only records that the executable SELL quantity is below the minimum tradable unit after the accepted rounding policy.

## 12. Pending / Runtime Continuity

Sell Planning now writes `non_executable_sell_decisions` evidence when all selected REDUCE decisions are valid but non-executable below the minimum tradable unit.

The pending plan remains:

```text
items = []
active_pending = false
status = EMPTY
```

The pipeline result is:

```text
status = PASS
selected_count = 0
reason = REDUCE_BELOW_MINIMUM_TRADABLE_QUANTITY
```

## 13. Position Lifecycle Impact

No execution event is created. No realized slice is created. Position quantity remains unchanged. Position campaign remains open.

Lifecycle evidence event:

```text
REDUCE_NOT_EXECUTED_MINIMUM_TRADABLE_QUANTITY
```

## 14. Observability Impact

Runtime Test PM decision snapshots now represent delegated REDUCE quantity as:

```text
quantity_requested.value = DELEGATED_TO_SELL_PLANNING
quantity_requested.status = NOT_SPECIFIED_BY_PM
```

This avoids treating PM `runtime_sell_quantity=0` as a PM request to submit a zero-share order.

## 15. Backward Compatibility

Normal REDUCE with executable rounded quantity still creates a partial SELL plan.

Full EXIT still uses the EXIT quantity contract and is unaffected.

Invalid quantity authority cases remain fail-closed:

```text
current quantity missing or non-positive
tradable unit unknown
reduce intensity unknown
negative sellable quantity
rounded quantity >= current quantity
minimum remaining quantity violation
pending SELL conflict
```

## 16. Resume / Fresh Run Decision

Decision:

```text
ABANDON_AND_FRESH_RUN_REQUIRED
```

Reason: the halted run was produced under the old quantity contract, with a persisted REVIEW_REQUIRED sell-planning manifest and empty pending evidence. Because the runtime contract implementation changed, resuming the same failed job would mix old-run evidence with corrected contract semantics. A fresh run is required for formal acceptance.

## 17. Remaining Gaps

- Symbol-level lifecycle summaries can consume `non_executable_sell_decisions` more explicitly in a later observability phase.
- The tradable unit remains the existing default constant, not a symbol-level lot-size resolver.
- Existing historical artifacts still show the old review-required reason until a fresh run is executed.

## 18. Runtime Impact

Runtime impact is limited to Sell Planning continuity for a valid, non-executable REDUCE below minimum tradable quantity. Invalid quantity cases still stop with review-required behavior.

## 19. Strategy Impact

No Strategy logic was changed. PM decision type, PM reason, REDUCE intensity, AI model output, Opportunity, Risk, and Capital Allocation policy were not changed.

## 20. Authority Impact

Authority is clarified:

```text
PM = Strategy decision
Sell Planning = executable REDUCE quantity and no-order feasibility evidence
Submit Guard = final executable order preflight
Runtime Test Observability = decision-time representation
```

## 21. Validation

Executed short targeted validation only:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase20_m_pycache python3 -m pytest -q tests/runtime_v2/test_phase19_bt_reduce_quantity_contract.py
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase20_m_pycache python3 -m pytest -q tests/runtime_v2/test_phase20_j_performance_observability.py tests/runtime_v2/test_phase20_k_performance_observability_consumer.py
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/phase20_m_pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py scripts/runtime_test.py
python3 -m json.tool reports/phase_reports/phase20_m_reduce_minimum_tradable_quantity_contract_correction.json
git diff --check
```

Result:

```text
11 passed
5 passed
py_compile PASS
json validation PASS
git diff --check PASS
```

Long historical, broker, training, calibration, validation, and full backtest were not executed.

## 22. Final Judgment

```text
PHASE20_M_RUNTIME_CONTINUITY_CORRECTED_FRESH_RUN_REQUIRED
```
