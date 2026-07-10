# Phase15-K Morning Policy Propagation / Hidden Policy Removal

## Status

`PHASE15K_MORNING_POLICY_PROPAGATION_HIDDEN_POLICY_REMOVAL_COMPLETE`

Phase15-K removed the hidden Morning Planning sizing policy and propagated Capital Deployment Policy evidence through Morning Planning, OrderPlan, Pending, and Approval.

## Implementation Summary

Implemented:

- Morning Planning now accepts `CapitalDeploymentPolicy`.
- CLI passes the loaded policy object to Morning Planning.
- CLI `--max-orders` no longer has a default `5`; when provided it is treated as an operator override capped by policy `max_positions`.
- Morning hidden `max_orders=5` removed.
- Morning hidden per-order `100_000.0` cap removed.
- Morning sizing now derives from Capital Deployment Policy:
  - `evaluation_capital`
  - `target_investment_ratio`
  - `cash_buffer`
  - `max_exposure`
  - `max_position_weight`
  - `max_positions`
  - `min_order_amount`
  - `max_buy_order_amount`
  - Current cash / buying power
  - Current exposure
- OrderPlan items now carry policy evidence.
- Pending plan and Pending items now carry policy evidence.
- Approval request/artifact now carry policy context.
- Morning manifest stage details now emit policy-use and hidden-cap-removal fields.

## Changed Files

Code:

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/models.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/planner.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/models.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/promotion.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/reader.py`
- `src/ai_fund_lab_v2/runtime_v2/approval/models.py`
- `src/ai_fund_lab_v2/runtime_v2/approval/policy.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`

Tests:

- `tests/runtime_v2/test_phase15k_morning_policy_propagation_hidden_policy_removal.py`
- `tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py`

Report:

- `docs/phase_reports/phase15_k_morning_policy_propagation_hidden_policy_removal.md`
- `reports/phase_reports/phase15_k_morning_policy_propagation_hidden_policy_removal.json`

## Morning Sizing Specification

Morning now computes planning budget from explicit policy:

```text
target_exposure = evaluation_capital * target_investment_ratio
cash_buffer_amount = evaluation_capital * cash_buffer
target_remaining = target_exposure - current_exposure
exposure_remaining = max_exposure - current_exposure
cash_capacity = available_cash - cash_buffer_amount
planning_budget = min(target_remaining, exposure_remaining, cash_capacity)
```

Per-order budget is derived as:

```text
min(
  planning_budget / effective_order_limit,
  evaluation_capital * max_position_weight,
  max_buy_order_amount if not null
)
```

There is no fixed `100_000.0` cap.

Order count is derived as:

```text
policy.max_positions - current_position_count
```

If `--max-orders` is supplied, it is treated as:

```text
operator_override_capped_by_policy_max_positions
```

It is not a Runtime hidden default.

## Pending Policy Fields

Pending plan now preserves:

```text
policy_context
policy_version
policy_source
pending_policy_hash
```

Pending item now preserves:

```text
capital_allocation_amount
policy_version
policy_source
target_investment_ratio
cash_buffer
max_exposure
max_position_weight
max_positions
max_buy_order_amount
min_order_amount
sizing_policy_reason
```

## Approval Policy Fields

Approval request/artifact now preserve:

```text
policy_version
policy_source
pending_policy_hash
```

The approval hash includes `pending_policy_hash`, so the approved policy context is part of the approval evidence.

## Submit Compatibility

Phase15-K uses Option B:

```text
Pending / Approvalにpolicy evidenceを保持し、Submit active policyとの一致比較は後続Phaseへ送る。
```

Reason:

- Phase15-I Submit already reloads explicit active policy and emits guard evidence.
- Adding mismatch blocking in this phase would change Submit acceptance behavior and needs focused regression around policy rotation and operator review.
- Phase15-K establishes the required evidence substrate first.

Recommended next step:

- Compare Pending/Approval `pending_policy_hash` with active Submit policy evidence and return `REVIEW_REQUIRED` on mismatch.

## Manifest Fields

Morning stage now emits:

```text
capital_deployment_policy_used_by_morning
morning_policy_source
morning_policy_version
morning_policy_sizing_method
morning_policy_target_investment_ratio
morning_policy_cash_buffer
morning_policy_max_exposure
morning_policy_max_position_weight
morning_policy_max_positions
morning_policy_max_buy_order_amount
morning_policy_min_order_amount
morning_order_count_source
morning_per_order_budget_source
morning_hidden_cap_removed
```

## Tests

Executed:

```text
python3 -m pytest tests/runtime_v2/test_phase15k_morning_policy_propagation_hidden_policy_removal.py
python3 -m pytest tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py tests/runtime_v2/test_phase14e36_feature_date_contract_carryover_policy.py tests/runtime_v2/test_phase15h_capital_deployment_policy.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py tests/runtime_v2/test_phase13_p_pending_models.py tests/runtime_v2/test_phase13_p_pending_consume.py
python3 -m pytest tests/runtime_v2/test_phase14e11_daily_operation_scheduler.py tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py tests/runtime_v2/test_phase14e19_submit_issue_code_normalization.py tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py src/ai_fund_lab_v2/runtime_v2/planning/models.py src/ai_fund_lab_v2/runtime_v2/planning/planner.py src/ai_fund_lab_v2/runtime_v2/pending/models.py src/ai_fund_lab_v2/runtime_v2/pending/reader.py src/ai_fund_lab_v2/runtime_v2/pending/promotion.py src/ai_fund_lab_v2/runtime_v2/approval/models.py src/ai_fund_lab_v2/runtime_v2/approval/policy.py src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py
```

Result:

```text
PASS
```

## Still Not Fixed

Intentionally left for later Phase15 subphases:

- SELL Broker ReadOnly available quantity formal connection
- Safety formal connection
- Report policy reason propagation
- Notification policy reason propagation
- Operator Review apply path
- Candidate / Opportunity AI direct execution contract
- Position Management AI -> SELL Planning formal connection
- Submit active policy vs Pending/Approval policy hash mismatch blocking

## Prohibited Actions Check

Not performed:

- Broker Write
- Demo order
- Production order
- Notification real send
- launchd / plist modification
- Current direct edit
- Runtime bypass creation
- fake adapter Full Runtime PASS declaration
- SELL Broker ReadOnly available quantity formal connection
- Safety formal connection
- Report / Notification propagation

## Final Judgment

`PHASE15K_MORNING_POLICY_PROPAGATION_HIDDEN_POLICY_REMOVAL_COMPLETE`

