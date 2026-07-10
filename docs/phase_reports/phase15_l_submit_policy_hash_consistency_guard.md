# Phase15-L Submit Policy Hash Consistency Guard

## Status

`PHASE15L_SUBMIT_POLICY_HASH_CONSISTENCY_GUARD_COMPLETE`

Phase15-L closes the Phase15-K Option B gap by checking that the Capital Deployment Policy evidence approved with Pending matches the active policy loaded at Submit time.

## Implementation Summary

Implemented:

- Added canonical Capital Deployment Policy hash functions.
- Expanded Morning / OrderPlan / Pending policy evidence to include the canonical hash fields.
- Submit now compares:
  - Pending policy version / source / hash
  - Approval policy version / source / pending policy hash
  - active Submit policy version / source / hash
- Policy mismatch blocks before broker preflight / submit.
- Missing Pending policy evidence blocks before broker preflight / submit.
- Missing Approval policy evidence blocks before broker preflight / submit.
- Submit result / stage details / CLI manifest now include policy consistency evidence.
- Existing BUY / SELL Submit Guard policy regression remains intact.
- SELL Planning can carry Capital Deployment Policy evidence into Pending / Approval when the policy object is supplied.

## Changed Files

Code:

- `src/ai_fund_lab_v2/runtime_v2/policy/capital_deployment.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/models.py`
- `src/ai_fund_lab_v2/runtime_v2/planning/planner.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/models.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/promotion.py`
- `src/ai_fund_lab_v2/runtime_v2/pending/reader.py`

Tests:

- `tests/runtime_v2/test_phase15l_submit_policy_hash_consistency_guard.py`
- `tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py`
- `tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py`
- `tests/runtime_v2/test_phase14e19_submit_issue_code_normalization.py`
- `tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py`

Report:

- `docs/phase_reports/phase15_l_submit_policy_hash_consistency_guard.md`
- `reports/phase_reports/phase15_l_submit_policy_hash_consistency_guard.json`

## Hash Target Fields

The active policy hash is computed from stable JSON with sorted keys and no secret / broker raw data.

Hash target:

```text
policy_version
policy_source
evaluation_capital
target_investment_ratio
cash_buffer
max_exposure
max_position_weight
max_positions
min_order_amount
max_buy_order_amount
max_sell_liquidation_amount
buy_notional_policy
sell_liquidation_policy
manual_review_threshold
```

`policy_source` is intentionally included. A policy moved or replaced under a different source must be reviewed instead of silently treated as identical.

## Match Behavior

If Pending / Approval / active Submit policy evidence match:

```text
policy_consistency_status=PASS
policy_mismatch_reason=""
```

Submit Guard continues to the existing BUY / SELL guard and preflight checks.

## Mismatch Behavior

If any policy evidence differs:

```text
status=REVIEW_REQUIRED
demo_submit_executed=false
submitted_count=0
accepted_count=0
pending_consumed=false
```

Broker preflight and broker submit are not called.

## Missing Evidence Behavior

If Pending policy evidence is missing:

```text
policy_consistency_status=REVIEW_REQUIRED
policy_mismatch_reason=missing_policy_evidence
```

If Approval policy evidence is missing:

```text
policy_consistency_status=REVIEW_REQUIRED
policy_mismatch_reason=missing_approval_policy_evidence
```

Both cases stop before Broker boundary.

## Manifest Fields

Submit result / manifest now includes:

```text
policy_consistency_status
pending_policy_version
pending_policy_source
pending_policy_hash
approval_policy_version
approval_policy_source
approval_pending_policy_hash
active_policy_version
active_policy_source
active_policy_hash
policy_mismatch_reason
policy_mismatch_manual_review_required
```

`active_policy_hash` is also included in `submit_guard_policy`.

## Tests

Executed:

```text
python3 -m pytest tests/runtime_v2/test_phase15l_submit_policy_hash_consistency_guard.py
python3 -m pytest tests/runtime_v2/test_phase14e19_submit_issue_code_normalization.py tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py tests/runtime_v2/test_phase14e11_daily_operation_scheduler.py tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py tests/runtime_v2/test_phase15l_submit_policy_hash_consistency_guard.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py
python3 -m pytest tests/runtime_v2/test_phase15l_submit_policy_hash_consistency_guard.py tests/runtime_v2/test_phase15k_morning_policy_propagation_hidden_policy_removal.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase15h_capital_deployment_policy.py tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py tests/runtime_v2/test_phase14e36_feature_date_contract_carryover_policy.py tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py tests/runtime_v2/test_phase14e19_submit_issue_code_normalization.py tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py tests/runtime_v2/test_phase14e11_daily_operation_scheduler.py tests/runtime_v2/test_phase13_p_pending_models.py tests/runtime_v2/test_phase13_p_pending_consume.py
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/policy/capital_deployment.py src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py src/ai_fund_lab_v2/runtime_v2/planning/models.py src/ai_fund_lab_v2/runtime_v2/planning/planner.py src/ai_fund_lab_v2/runtime_v2/pending/models.py src/ai_fund_lab_v2/runtime_v2/pending/promotion.py src/ai_fund_lab_v2/runtime_v2/pending/reader.py src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py
python3 -m json.tool reports/phase_reports/phase15_l_submit_policy_hash_consistency_guard.json
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

```text
PHASE15L_SUBMIT_POLICY_HASH_CONSISTENCY_GUARD_COMPLETE
```
