# Phase20-BU Historical Submit Corporate Action Preflight Regression

## Status

```text
PHASE20_BU_HISTORICAL_SUBMIT_CORPORATE_ACTION_PREFLIGHT_REGRESSION_FIXED
```

Primary Judgment:

```text
PHASE20_BU_HISTORICAL_SUBMIT_PREFLIGHT_INPUT_DEFECT_CONFIRMED
```

Supporting judgments:

```text
PHASE20_BU_CORPORATE_ACTION_AUTHORITY_PATH_DEFECT
PHASE20_BU_CORPORATE_ACTION_GUARD_AUTHORITY_WIRING_DEFECT
PHASE20_BU_BUY_SELL_PREFLIGHT_SCOPE_CONTAMINATION_CONFIRMED
PHASE20_BU_CORPORATE_ACTION_NO_EVENT_SEMANTICS_PRESERVED
PHASE20_BU_SHORT_REGRESSION_PASS
LONG_RUNNING_HISTORICAL_TEST_NOT_EXECUTED
```

## Target

```text
run_id = runtime-test-historical-extended-smoke-20260725T233056749335Z
business_date = 2022-09-01
submit_exit_code = 10
stopped_stage = submit
```

Evidence source:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260725T233056749335Z/daily/2022-09-01/submit/runtime_manifest.json
```

## First Failing Preflight Condition

The first failing condition was:

```text
corporate_action_status = MISSING
reason = corporate action guard failed
```

The PIT universe lookup passed for all four symbols. The failure occurred after PIT universe resolution and before Historical open-price fill resolution.

## Root Cause

Historical Submit preflight did not receive the run-scoped Historical logical `raw_ohlcv` authority. The adapter therefore evaluated Corporate Action status against operations canonical raw OHLCV:

```text
.runtime/operations/jquants/raw/jquants/equities_bars_daily/data.parquet
```

That path exists, but for `2022-09-01` it has no rows for the four target symbols. The guard correctly failed closed as `MISSING`, but the authority path was wrong for Historical replay.

BT had already fixed Morning BUY Planning to use run-scoped logical normalized OHLCV. BU closes the remaining Submit preflight raw-OHLCV wiring gap.

## Item Audit

| Symbol | Side | Preflight | CA Status | PIT Result | broker_available_quantity_review_required | Quantity Branch |
|---|---|---|---|---|---:|---|
| `94320` | BUY | HALT | MISSING | symbol_found_in_pit_universe | True | broker_lot_size_and_pending_quantity |
| `93180` | BUY | HALT | MISSING | symbol_found_in_pit_universe | True | broker_lot_size_and_pending_quantity |
| `36600` | BUY | HALT | MISSING | symbol_found_in_pit_universe | True | broker_lot_size_and_pending_quantity |
| `23880` | BUY | HALT | MISSING | symbol_found_in_pit_universe | True | broker_lot_size_and_pending_quantity |

## Corporate Action Authority

Before fix:

```text
path = .runtime/operations/jquants/raw/jquants/equities_bars_daily/data.parquet
authority_type = OPERATIONS_CANONICAL_RAW_OHLCV
as_of = 2022-09-01
exists = True
hash = 42c70e9433f56591e621613f13c34027c5f8c309c8e02a0f49cbeac9a3e45500
result = MISSING_AUTHORITY_ROW for all four symbols
```

After fix:

```text
path = reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260725T233056749335Z/daily/2022-09-01/market_refresh/inputs/historical_asof/2022-09-01/raw/jquants/equities_bars_daily/data.parquet
authority_type = HISTORICAL_ASOF_RAW_OHLCV_LOGICAL_INPUT
as_of = 2022-09-01
exists = True
hash = 70062d5153b228abddcc750ee2e2f2f6ce25c9d6532067cd4e075efedb476a99
result = NO_EVENT/PASS for all four symbols
```

Run-scoped authority probe:

| Symbol | Raw Record Match Count | CA Event Match Count | AdjFactor | Guard Semantics |
|---|---:|---:|---|---|
| `94320` | 1 | 0 | [1.0] | NO_EVENT_PASS |
| `93180` | 1 | 0 | [1.0] | NO_EVENT_PASS |
| `36600` | 1 | 0 | [1.0] | NO_EVENT_PASS |
| `23880` | 1 | 0 | [1.0] | NO_EVENT_PASS |

Interpretation:

```text
Authority exists + raw row exists + AdjFactor = 1.0 -> NO_EVENT / PASS
Authority missing or target raw row missing -> MISSING_AUTHORITY / fail-closed
AdjFactor != 1.0 -> IMPACT_DETECTED / fail-closed
```

## BUY / SELL Scope

The old evidence had:

```text
broker_available_quantity_review_required = true
side = BUY
```

This did not block the BUY items because `guard_decision` remained `PASS`, but it was invalid Evidence semantics: broker available quantity is a SELL-only authority. The BUY branch now records:

```text
broker_available_quantity_source = not_applicable_buy
broker_available_quantity_review_required = false
broker_available_quantity_reason = broker available quantity is sell-only authority
```

SELL broker available quantity guard remains unchanged and covered by existing tests.

## Fix

Changed:

```text
src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py
src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py
tests/runtime_v2/test_phase17_b1i_a_historical_environment_composition.py
tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py
tests/runtime_v2/test_phase17_bv8_historical_submit_pit_universe_authority.py
```

Implementation summary:

- Historical environment composition resolves `market_refresh/inputs/historical_asof/<DATE>/logical_input_manifest.json` from the run-scoped `historical_asof_view.json` location.
- `HistoricalSubmitAdapter` receives logical `normalized_ohlcv`, `raw_ohlcv`, and `listed_issues` paths when the logical manifest exists.
- Adapter diagnostics now include the concrete submit authority paths.
- BUY submit guard evidence no longer reports SELL-only broker available quantity review as required.
- Corporate Action guard remains fail-closed for missing authority and impact events.

## Fixed Preflight Probe

Isolated adapter `preflight()` was executed only; no submit, no broker, no fresh-run.

| Symbol | Status | Fill Price | Source Price Ref |
|---|---|---:|---|
| `94320` | DRY_RUN_READY | 149.4 | `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260725T233056749335Z/daily/2022-09-01/market_refresh/inputs/historical_asof/2022-09-01/raw_normalized/jquants/equities_bars_daily/data.parquet:2022-09-01:94320:Open` |
| `93180` | DRY_RUN_READY | 6.0 | `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260725T233056749335Z/daily/2022-09-01/market_refresh/inputs/historical_asof/2022-09-01/raw_normalized/jquants/equities_bars_daily/data.parquet:2022-09-01:93180:Open` |
| `36600` | DRY_RUN_READY | 525.0 | `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260725T233056749335Z/daily/2022-09-01/market_refresh/inputs/historical_asof/2022-09-01/raw_normalized/jquants/equities_bars_daily/data.parquet:2022-09-01:36600:Open` |
| `23880` | DRY_RUN_READY | 136.0 | `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260725T233056749335Z/daily/2022-09-01/market_refresh/inputs/historical_asof/2022-09-01/raw_normalized/jquants/equities_bars_daily/data.parquet:2022-09-01:23880:Open` |

## Non-Changed Scope

No changes were made to:

```text
Candidate AI
Opportunity AI
Position Management
BUY threshold
Capital Deployment Policy
BUY quantity
BUY price
Approval Policy
Submit Guard Policy thresholds
Safety Policy
Broker implementation
Production/Demo authority
Accepted Generation
Training
Calibration
```

## Regression

Executed targeted tests:

```text
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/pycache-bu python3 -m pytest -q tests/runtime_v2/test_phase17_b1i_a_historical_environment_composition.py tests/runtime_v2/test_phase15i_submit_guard_buy_sell_policy_manifest.py tests/runtime_v2/test_phase15m_sell_broker_available_quantity_evidence.py tests/runtime_v2/test_phase17_bv8_historical_submit_pit_universe_authority.py
```

Result:

```text
33 passed
```
Additional validation:

```text
py_compile PASS
JSON validation PASS
git diff --check PASS
```


Coverage:

- Historical logical submit authority path wiring.
- Invalid Historical logical manifest does not fall back to operations canonical.
- Historical BUY no-event CA preflight PASS via existing BV8 and fixed 4-symbol probe.
- Historical target Corporate Action HALT.
- Historical missing Corporate Action authority fail-closed.
- BUY does not require SELL broker available quantity review.
- SELL broker available quantity guard preserved.
- Demo submit policy regression preserved.

## User Revalidation Command

Codex did not execute a 1BD, 5BD, 20BD, 245BD, or long Historical run.

```bash
cd /Users/negishi/work/ai-fund-lab-v2

PYTHONPATH=src python3 scripts/runtime_test.py fresh-run   --profile historical-extended-smoke   --business-days 1   --start-date 2022-09-01   --initial-cash 1000000   --confirm   --yes-i-understand-this-mutates-trading-state   --json
```

Expected confirmations:

```text
submit HistoricalSubmitAdapter.raw_ohlcv_path = reports/runtime_tests/runs/<RUN_ID>/daily/2022-09-01/market_refresh/inputs/historical_asof/2022-09-01/raw/jquants/equities_bars_daily/data.parquet
corporate_action_status no longer MISSING for the four BUY items
broker_available_quantity_review_required = false for BUY items
submitted_count > 0 if Historical fill evidence accepts all remaining preflight checks
```

## Phase20 Closure

```text
PENDING_USER_REVALIDATION_1BD_SUBMIT_CONFIRMATION
```

BU implementation and short regression are complete. Phase20 final closure should wait for the user-run 1BD Historical confirmation because Codex did not execute mutating fresh-run validation.
