# Phase20-BQ Historical Simulated 9000-Series Submit Capability Contract Fix

## Executive Summary

Final status:

```text
PHASE20_BQ_HISTORICAL_SIMULATED_SUBMIT_CAPABILITY_FIXED
```

Supporting:

```text
PHASE20_BQ_SUBMIT_HALT_ROOT_CAUSE_CONFIRMED
PHASE20_BQ_EXECUTION_CAPABILITY_RESPONSIBILITY_SEPARATED
PHASE20_BQ_DEMO_SUBMIT_GUARD_PRESERVED
PHASE20_BQ_HISTORICAL_9000_FILL_PATH_READY
PHASE20_BQ_SHORT_REGRESSION_PASS
PHASE20_BQ_BULL_USER_RERUN_READY
```

BQ fixes the post-BP submit halt by separating Demo broker capability from Historical simulated execution capability. Candidate, Opportunity, Planning, Capital, PM, Risk, prices, quantities, safety, and Accepted Generation were not changed.

## Halted Run Evidence

Halted run:

```text
runtime-test-historical-extended-smoke-20260724T061934092894Z
```

Observed:

| Field | Value |
|---|---|
| business_date | 2026-03-24 |
| job | submit |
| exit_code | 20 |
| run_result | HALT |
| final_state | REVIEW_REQUIRED |
| mode | historical |
| broker_environment | historical_simulated |
| historical_replay | true |
| broker_write | false |
| external_delivery | false |
| submitted_count | 4 |
| blocked_count | 1 |

Source:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260724T061934092894Z/daily/2026-03-24/submit/runtime_manifest.json
```

The run was preserved as evidence. It was not resumed, deleted, or overwritten.

## Exact Submit Halt Reason

Blocked item:

| Field | Value |
|---|---|
| symbol | 94320 |
| side | BUY |
| quantity | 1000 |
| opportunity_buy_rank | 2 |
| opportunity_expected_edge_score | 0.70808099 |
| buy_eligibility | ELIGIBLE |
| safety_decision | ALLOW |
| pending_item_id | `opi-morning-run-2026-03-24-5597fa528034-runtime-v2-buy-ai-2026-03-24-20260323T233000+0000-opportunity-94320-002` |
| guard_decision | BLOCKED |
| guard_reason | `symbol not supported by broker capability` |
| violated_policy | `submit_preflight` |
| violated_policy_source | `runtime_v2_submit_preflight` |

The item passed Planning, listed-issue BUY eligibility, Opportunity BUY eligibility, and Safety. It was blocked in Submit preflight before Historical Fill.

Classification:

```text
A: Historical SimulatedにDemo Broker capabilityが誤適用された
```

## Capability Resolution Path

Code path:

```text
runtime mode = historical
↓
src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py
↓
run_submit_preflight(... broker_capability=get_broker_capability(mode) ...)
↓
src/ai_fund_lab_v2/runtime_v2/broker_adapter/capability.py
↓
get_broker_capability("historical")
↓
supports_9000_series_orders was false
↓
is_symbol_allowed_by_capability("94320", historical_capability) == false
↓
"symbol not supported by broker capability"
```

This was execution capability leakage, not an investment eligibility decision.

## Production / Demo / Historical Responsibility Matrix

| Mode | Broker Environment | Capability Source | 9000 Planning | 9000 Submit | Execution Destination |
|---|---|---|---|---|---|
| Production | tachibana_production | Production broker capability | Allowed if common checks pass | Allowed by production capability | Tachibana production broker |
| Demo | tachibana_demo | Demo broker capability | Allowed if common checks pass | Blocked fail-closed if Demo unsupported | Tachibana demo broker |
| Historical Simulated | historical_simulated | Historical simulated execution capability | Allowed if common checks pass | Allowed by simulated execution capability | Local Historical Fill evidence |

## Root Cause

Root cause:

```text
HISTORICAL_SIMULATED_EXECUTION_CAPABILITY_INHERITED_DEMO_9000_RESTRICTION
```

`get_broker_capability("historical")` had:

```text
supports_9000_series_orders = false
```

That made Historical simulated submit behave like Demo broker submit for 9000-series symbols, even though Historical does not call Tachibana and should evaluate through local Historical Fill evidence.

## Contract Judgment

Contract judgment:

```text
Historical Simulated 9000-series submit rejection was contract-inconsistent.
```

Reason:

- 9000-series is not an Asset Universe exclusion.
- Historical simulated execution does not send real broker orders.
- Demo broker limitations must remain at Demo broker submit boundary.
- Historical should preserve the common investment decision and route it to Historical Fill if price, eligibility, quantity, and safety pass.

## Implementation Change

Changed:

```text
src/ai_fund_lab_v2/runtime_v2/broker_adapter/capability.py
tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py
```

Implementation:

```text
get_broker_capability("historical").supports_9000_series_orders = true
```

This defines Historical simulated execution capability explicitly. It does not copy Demo capability and does not add Historical-only Candidate / Opportunity / Planning allow branches.

## Demo Submit Guard Preservation

Demo behavior remains unchanged:

```text
get_broker_capability("demo").supports_9000_series_orders = false
Demo + 9000-series Submit Guard => "symbol not supported by broker capability"
```

BP regression tests were rerun and passed.

## Historical Simulated Execution Safety

Verified by targeted tests:

- Historical 9000-series submit preflight is allowed.
- Historical 9000-series submit pipeline reaches `HistoricalSubmitAdapter`.
- Historical Fill evidence is generated locally.
- `broker_write` remains false.
- `external_delivery` remains false.
- Demo submit is not executed.
- Historical duplicate / idempotency tests remain green.
- Corporate Action Guard still halts target-symbol impact.
- Unsupported order type and ordinary Submit Guard constraints remain in effect.

## Unit / Regression Results

Executed short checks only:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py
9 passed
```

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py tests/runtime_v2/test_phase14e8_demo_broker_capability_evaluation_capital_fix.py tests/runtime_v2/test_phase14e13_day1_demo_submit_enable.py
17 passed
```

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase17_bv10_historical_sell_execution_projection.py tests/runtime_v2/test_phase17_bv8_historical_submit_pit_universe_authority.py
12 passed
```

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase14d3_pure_submit_path.py tests/runtime_v2/test_phase14d14_demo_sell_guarded_preflight.py tests/runtime_v2/test_phase15bo_isolated_submit_simulation.py
15 passed
```

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache PYTHONPATH=src:. python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/broker_adapter/capability.py src/ai_fund_lab_v2/runtime_v2/submit/guards.py src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py
PASS
```

```text
python3 -m json.tool reports/phase_reports/phase20_bq_historical_simulated_9000_series_submit_capability_contract_fix.json
PASS
```

```text
git diff --check
PASS
```

Long-running Bull / Range Historical runs were not executed.

## Halted Run Preservation

The halted run remains stored under:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260724T061934092894Z/
```

Read-only state evidence:

| Field | Value |
|---|---|
| backup_result | PASS |
| reset_result | PASS |
| plan_result | PASS |
| active_run_conflict | false |
| broker_write_performed | false |
| baseline_compatibility_status | PASS |
| baseline_next_operator_action | proceed |

The stopped run must not be used as a comparison run and must not be resumed.

## Bull User Rerun Command

Use a new fresh run, not resume:

```bash
cd /Users/negishi/work/ai-fund-lab-v2

PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --business-days 20 \
  --start-date 2026-03-24 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

Old comparison source:

```text
runtime-test-historical-extended-smoke-20260723T215847198556Z
final_equity = 954,880
return = -4.512%
BUY = 5
SELL = 10
```

## Range User Rerun Command

Use only after Bull PASS:

```bash
cd /Users/negishi/work/ai-fund-lab-v2

PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --business-days 20 \
  --start-date 2022-08-01 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

## Residual Risks

- Full Bull and Range performance effects are not proven until the user runs new fresh runs.
- Historical simulated 9000-series fill uses local market evidence; it is not a proof that Tachibana Demo can fill the same symbol.
- Existing stopped run remains HALT by design and should be treated only as root-cause evidence.

## Phase20 Closure Impact

BQ closes the execution-capability side of the Phase20-BO / BP 9000-series gap:

```text
Planning-stage 9000 exclusion removed in BP.
Historical simulated submit 9000 rejection removed in BQ.
Demo broker submit guard preserved.
```

Performance conclusions remain unchanged until new Bull / Range fresh-run evidence exists.

## Final Judgment

```text
PHASE20_BQ_HISTORICAL_SIMULATED_SUBMIT_CAPABILITY_FIXED
```

No Broker API call, Production order, Demo order, Training, Calibration, Accepted Generation update, PM change, Candidate change, Opportunity change, Capital change, Risk change, Bull long run, Range long run, or stopped-run resume was executed by Codex.
