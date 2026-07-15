# Phase17-AK Position Management Leakage Audit Runtime Integration Closure

## Final Judgment

`PHASE17_AK_PM_LEAKAGE_AUDIT_RUNTIME_INTEGRATION_ACCEPTED`

Frozen Run `runtime-test-historical-smoke-20260715T063047874126Z` was not modified, resumed, or rerun. No `runtime_test.py run/resume/reset/rollback/backup/close` command was executed.

## Root Cause

Classification:

- B. Runtime-safe Field Misclassified as Leakage
- E. Schema Normalization Bug
- F. Producer-to-Audit Contract Bug
- H. Stale Legacy Leakage Rule

The frozen Day2 SELL Planning blocker was:

```text
position management review required: BLOCKED_BY_LEAKAGE_AUDIT
```

The concrete triggered rule was the PM leakage audit's generic forbidden-term match:

```text
FORBIDDEN_FEATURE_TERMS contains "broker"
```

The concrete triggered field was:

```text
feature__broker_issue_code
```

Frozen audit evidence showed:

```json
{
  "leakage_audit_status": "ERROR",
  "forbidden_feature_column_count": 1,
  "forbidden_feature_columns": ["feature__broker_issue_code"],
  "joined_row_count": 5,
  "output_count": 0
}
```

This was a false positive. `broker_issue_code` in the Runtime PM feature artifact is a symbol identity alias, not a broker snapshot, broker API payload, future outcome, paper ledger PnL, test verdict, audit verdict, order, cash, or portfolio signal.

## Implemented Runtime Contract

The PM leakage audit now uses field classification:

- `metadata_only`
- `operational_state`
- `model_feature`
- `forbidden_training_signal`
- `forbidden_future_signal`
- `forbidden_runtime_signal`

Valid metadata-only fields include Runtime identity, schema/source/path evidence, dates, and `broker_issue_code`. They may exist in evidence/artifacts without blocking inference, but they are not treated as model features.

Valid operational state includes current positions, entry/current prices, holding days, average price, unrealized return, peak return, and valuation date when temporal authority has already accepted them.

The audit still fails closed for:

- future-dated `as_of_date`
- future returns and labels
- realized future return
- backtest outcomes
- paper ledger or paper trading PnL
- test/audit verdicts as model features
- runtime-test identity as a model feature
- broker/order/cash/portfolio signals as model features
- malformed numeric model features

The same contract applies to Production, Demo, and Historical. No Historical-only pass branch was added.

## PM Decision Result

Readonly probe using the Day2 PM inputs with output redirected to `/private/tmp`:

- input positions: 5
- joined rows: 5
- leakage audit: OK
- decision_count: 5
- HOLD: 3
- REDUCE: 2
- EXIT: 0
- ADD: 0

Focused no-exit regression:

- input positions: 5
- decision_count: 5
- HOLD: 5
- REDUCE: 0
- EXIT: 0
- ADD: 0

This confirms that `decision_count=0` is not the normal contract for READY PM inputs with current positions. It is valid only for no-position, blocked input, or explicit no-action scopes.

## Horizontal Audit

BUY components:

- Candidate AI leakage audit remains fail-closed; AK did not relax candidate model leakage checks.
- Opportunity AI and BUY Opportunity to PM contract remain schema/role/date validated.
- Capital allocation remains unchanged; cash/portfolio fields are still forbidden as PM model features.
- BUY order planning does not use runtime-test identity as permission.

PM / SELL components:

- PM input builder can use Current operational state as valid runtime input.
- PM producer now lets READY inputs reach inference when only metadata-only fields are present.
- SELL decision artifacts receive generated HOLD/REDUCE/EXIT rows after leakage PASS.
- SELL Planning accepts HOLD-only/no-exit as no-signal Pending without Submit.

Current / Ledger / Broker:

- Current positions and valuations are operational runtime state.
- Broker snapshot/raw broker payloads remain forbidden model features.
- `broker_issue_code` as symbol identity metadata is allowed.
- Paper ledger realized PnL remains forbidden as model feature.

Runtime modes:

- Production, Demo, and Historical share the same PM leakage contract.
- Mode differences remain limited to external effects, broker write, simulation fill, notification delivery, and temporal authorities.

Temporal scopes:

- Previous-close Morning valuation remains valid through temporal authority.
- Future `as_of_date` still fails closed.
- Submit, Execution, Current Valuation apply, external notification, and J-Quants fetch were not executed in AK.

## Registry

Resolver result:

- accepted_set: `control.position_management.accepted_set@sha256-8c87f91911b03e75`
- path: `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- hash: `d08d854266f6822f322a7947fd7deb20a2906d2a56806d030e2618114bdcaa4b`
- accepted_event_id: `event-6e086331-b8f7-4ca1-b4d7-bb23e6676cec-8ea13c0b06fa837f`
- resolver: PASS

AK changed the leakage audit dependency, not the accepted PM producer source file. Registry JSON was not manually edited and no stale accepted adapter mismatch was introduced.

## Verification

AK focused:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_ak_pm_leakage_audit_runtime_contract.py
14 passed
```

Phase6 + AK:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_ak_pm_leakage_audit_runtime_contract.py tests/position_management_ai/test_phase6a_position_management_baseline.py tests/position_management_ai/test_phase6b_position_feature_builder.py
23 passed
```

Related regression:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_ak_pm_leakage_audit_runtime_contract.py tests/position_management_ai/test_phase6a_position_management_baseline.py tests/position_management_ai/test_phase6b_position_feature_builder.py tests/runtime_v2/test_phase17_aj_buy_opportunity_pm_contract.py tests/runtime_v2/test_phase17_ad_position_feature_current_authority.py tests/runtime_v2/test_phase17_af_day2_morning_temporal_authority.py tests/runtime_v2/test_phase17_ag_day2_sell_planning_integration.py tests/runtime_v2/test_phase17_ah_pm_adapter_registry_identity_guard.py tests/runtime_v2/test_phase17_b1i_b_pm_adapter_authority.py tests/runtime_v2/test_phase15ap_position_management_input_contract.py tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py tests/runtime_v2/test_phase17_x_historical_sell_planning_authority.py tests/runtime_v2/test_phase17_w_historical_morning_capability.py tests/artifact_registry/test_phase16av_runtime_lookup_adapter.py tests/runtime_v2/test_phase16av_registry_consumer_cutover.py
116 passed
```

Additional final checks:

- `py_compile`: PASS
- `git diff --check`: PASS
- JSON validation: PASS

## Evidence

- `reports/phase17_ak_pm_leakage_audit_runtime_integration_closure/root_cause.json`
- `reports/phase17_ak_pm_leakage_audit_runtime_integration_closure/triggered_rule_evidence.json`
- `reports/phase17_ak_pm_leakage_audit_runtime_integration_closure/field_classification_contract.json`
- `reports/phase17_ak_pm_leakage_audit_runtime_integration_closure/before_after_contract.json`
- `reports/phase17_ak_pm_leakage_audit_runtime_integration_closure/cross_component_audit.json`
- `reports/phase17_ak_pm_leakage_audit_runtime_integration_closure/cross_mode_audit.json`
- `reports/phase17_ak_pm_leakage_audit_runtime_integration_closure/temporal_audit.json`
- `reports/phase17_ak_pm_leakage_audit_runtime_integration_closure/pm_decision_generation_evidence.json`
- `reports/phase17_ak_pm_leakage_audit_runtime_integration_closure/registry_resolution.json`
- `reports/phase17_ak_pm_leakage_audit_runtime_integration_closure/verification_summary.json`
- `reports/phase17_ak_pm_leakage_audit_runtime_integration_closure/prohibited_action_audit.json`

