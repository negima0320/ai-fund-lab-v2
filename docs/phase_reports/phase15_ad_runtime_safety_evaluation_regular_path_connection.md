# Phase15-AD Runtime Safety Evaluation Regular Path Connection

## Purpose

Phase15-AD connects Runtime v2 regular evidence to Phase11 Safety evaluation.

This closes the missing path:

```text
Real Runtime Evidence
↓
Safety Evaluation
↓
Phase11 Safety Report
↓
Runtime Safety Decision Producer
```

Phase15-AC already connected Phase11 Safety Report to Runtime Safety Decision. Phase15-AD adds the upstream regular-path producer for that Phase11 report.

## Implemented Scope

### Runtime Safety Evaluation Module

Added:

```text
src/ai_fund_lab_v2/runtime_v2/safety/evaluation.py
```

The module reads Runtime-owned evidence only:

- Current SoT: `.runtime/persistent_ledger/state.json`
- Orders: `.runtime/persistent_ledger/orders.jsonl`
- Executions: `.runtime/persistent_ledger/executions.jsonl`
- Runtime State: `.runtime/runtime_state/current_state.json`
- Broker ReadOnly snapshot: `.runtime/runtime_state/broker_readonly/<business_date>/*.json`
- Market/quote evidence: `.runtime/runtime_state/market/<business_date>/market_evidence.json`
- Manual stop evidence: `.runtime/safety/locks/*.json`

It builds `HourlyMonitorInput`, runs `HourlyPositionMonitor.evaluate()`, applies `EmergencyStopEvaluator`, and writes:

```text
reports/safety/phase11/<business_date>_safety_report.json
reports/safety/phase11/<business_date>_safety_report.md
```

The JSON report is enriched with:

- `schema_version=phase11_safety_report_v2`
- `expires_at`
- `input_evidence_sources`
- `input_freshness_status`
- `missing_evidence`
- `stale_evidence`
- `production_equivalent`
- Runtime regular-path source summary

### CLI Regular Path

Added Runtime CLI job:

```text
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --job safety_evaluation
```

The job writes manifest fields including:

- `safety_evaluation_status`
- `safety_evaluation_policy_version`
- `current_source`
- `current_as_of`
- `market_source`
- `market_as_of`
- `broker_snapshot_source`
- `broker_snapshot_at`
- `orders_source`
- `execution_source`
- `manual_stop_source`
- `input_freshness_status`
- `missing_evidence`
- `stale_evidence`
- `safety_report_path`
- `overall_decision`
- `next_recommended_safety_state`
- `review_required`
- `production_equivalent`

### Fail-Closed Behavior

Missing or stale evidence does not become `ALLOW`.

Current, Broker snapshot, Market evidence, Orders, Executions, Runtime State, and Manual stop evidence gaps are classified as:

```text
overall_decision=REVIEW_REQUIRED
```

Manual emergency lock maps to:

```text
overall_decision=EMERGENCY_STOP
safety_evaluation_status=HALT
```

Broker snapshot missing/stale remains `REVIEW_REQUIRED` in this Runtime evaluation path, matching Phase15-AD's requirement that missing evidence stops review progression without being misreported as implicit allow.

## Explicit Non-Use

Phase15-AD does not use Phase11 scenario-only dry-run inputs.

Not imported or called:

- `integration_dry_run`
- `PHASE11G_SCENARIOS`
- `build_phase11g_scenarios`
- `_base_monitor_input`
- `_quote`
- `_order`
- `_broker_snapshot`

Static scan result:

```text
implementation: no forbidden dependency found
tests: forbidden strings appear only as explicit regression assertions
```

## Regression Coverage

Added:

```text
tests/runtime_v2/test_phase15ad_runtime_safety_evaluation_regular_path.py
```

Coverage:

- Runtime evidence maps to valid Phase11 Safety Report
- Missing Current becomes `REVIEW_REQUIRED`
- Stale Current becomes `REVIEW_REQUIRED`
- Missing Broker snapshot becomes `REVIEW_REQUIRED`
- Missing Market evidence becomes `REVIEW_REQUIRED`
- Manual emergency lock becomes `HALT`
- BUY / SELL review scope is preserved
- CLI `safety_evaluation` then `safety_refresh` works as regular path
- No scenario dry-run dependency
- Phase11 report feeds Phase15-AC Runtime Safety Decision Producer

## Verification

Executed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase15ad_pycache python3 -m pytest -q tests/runtime_v2/test_phase15ad_runtime_safety_evaluation_regular_path.py
```

Result:

```text
10 passed
```

Executed retention:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase15ad_pycache python3 -m pytest -q tests/runtime_v2/test_phase15ac_runtime_safety_decision_producer.py tests/runtime_v2/test_phase15n_safety_operation_guard_runtime_connection.py tests/runtime_v2/test_phase15r_report_notification_reason_propagation.py tests/runtime_v2/test_phase15y_non_trading_day_demo_acceptance_override.py
```

Result:

```text
24 passed
```

Executed compile check:

```text
PYTHONPYCACHEPREFIX=/private/tmp/phase15ad_pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/safety/evaluation.py src/ai_fund_lab_v2/runtime_v2/safety/__init__.py src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py
```

Result:

```text
PASS
```

## Prohibited Actions Confirmation

Not performed:

- Morning execution
- Submit execution
- Execution job
- Broker Write
- Demo order
- Production order
- Notification real send
- launchd/plist change
- Current direct edit
- Runtime bypass creation
- Scenario dry-run Safety evidence declaration

## Remaining Acceptance Note

Phase15-AD creates the regular Safety evaluation path and validates it with fixture evidence. Runtime Acceptance still requires operator evidence for real Demo review steps before any Full Runtime PASS.

## Final Judgment

```text
PHASE15AD_RUNTIME_SAFETY_EVALUATION_REGULAR_PATH_CONNECTION_COMPLETE
```
