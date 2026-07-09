# Phase14-E47 Runtime v2 Execution -> Current Projection Runtime Connection Fix

## Summary

- phase: Phase14-E47
- objective: Connect Runtime v2 Execution PASS to Runtime-owned Current SoT projection.
- code_changed: true
- current_changed_by_validation: true
- submit_executed: false
- sell_executed: false
- production_order_executed: false
- notification_sent: false
- launchd_changed: false
- phase14_dedicated_path: false
- demo_dedicated_runtime_branch: false
- fake_adapter_added: false
- final_judgment: `PHASE14E47_EXECUTION_CURRENT_PROJECTION_CONNECTED`

## Problem

E46 identified the stopping point:

`Ledger -> runtime_owned_fill_projection`

Before E47, `run_execution_readonly_pipeline(...)` wrote Order / Execution / Position / Cash evidence to Ledger, created `execution_equivalent` records, and returned PASS, but did not call E25's `project_runtime_owned_fills_to_current(...)`.

As a result, `.runtime/persistent_ledger/state.json` stayed at:

- cash: `1000000`
- positions: `[]`
- source: `phase14e8_demo_operation_initial_state`

even after Broker ACCEPTED / filled evidence existed.

## Implementation

Updated:

- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/ledger/models.py`
- `src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`
- `tests/runtime_v2/test_phase14e23_execution_acceptance_policy.py`
- `tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py`

### Execution -> Current Connection

After execution acceptance and ledger append, the regular execution pipeline now calls:

`project_runtime_owned_fills_to_current(...)`

only when the execution pipeline status is PASS.

Projection behavior:

- Uses accepted Runtime submit ledger records.
- Uses matching Ledger Position evidence.
- Uses execution-equivalent cash effects.
- Writes only fixed Current path:
  - `.runtime/persistent_ledger/state.json`
- Does not copy Broker Demo account-wide cash.
- Does not copy unrelated Demo broker positions.
- Works through the common Runtime-owned projection component, not a Phase14-specific branch.

If projection fails after Execution PASS, the execution result becomes `REVIEW_REQUIRED` instead of silently leaving Current unchanged.

### Manifest Fields

Execution stage details now include:

- `asset_current_written`
- `asset_policy`
- `runtime_owned_projection_status`
- `runtime_owned_projection_reason`
- `projected_position_count`
- `projected_cash`
- `projected_market_value`
- `projected_total_equity`
- `projected_runtime_owned_symbols`
- `excluded_broker_position_symbols`
- `source_ledger_records`

### Submit Ledger business_date

`LedgerOrderRecord` now includes `business_date`, and submit ledger records set it from `pending.target_session_date`.

This keeps Report's Today Operation scoped to business date rather than wall-clock `created_at`, which matters in tests and future operation when a job runs around date boundaries.

## Runtime Validation

Ran the existing Runtime v2 execution CLI without additional Submit:

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache \
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job execution \
  --business-date 2026-07-09 \
  --submit-enabled false \
  --notification-mode payload-only \
  --stop-on-review-required \
  --stop-on-blocked
```

Result:

- exit_code: `0`
- manifest:
  - `.runtime/runtime_state/run_manifest/2026-07-09/runtime-v2-execution-2026-07-09-20260709T005902.226667+0000.json`
- production order: not executed
- notification actual send: not executed
- launchd/plist: unchanged

Execution manifest result:

- status: `PASS`
- execution_acceptance_status: `PASS`
- execution_equivalent_count: `20`
- asset_policy: `runtime_owned_fill_projection`
- asset_current_written: `true`
- runtime_owned_projection_status: `PASS`
- runtime_owned_projection_reason: `runtime_owned_fills_projected_to_current`
- projected_position_count: `5`
- projected_cash: `312400.0`
- projected_market_value: `1659600.0`
- projected_total_equity: `1972000.0`
- projected_runtime_owned_symbols:
  - `6897`
  - `4591`
  - `3926`
  - `4446`
  - `4935`
- excluded_broker_position_symbols:
  - `6501`
  - `6502`
  - `9984`
  - `6504`
  - `6505`
  - `9001`

The projected values reflect the existing repeated rehearsal ledger state at validation time. The important E47 acceptance point is that Runtime-owned symbols were projected and unrelated Demo broker positions/cash were not copied.

## Current SoT After Validation

`.runtime/persistent_ledger/state.json`:

- source: `runtime_v2_runtime_owned_fill_projection`
- cash: `312400.0`
- buying_power: `312400.0`
- market_value: `1659600.0`
- total_equity: `1972000.0`
- positions_count: `5`

Positions:

| Symbol | Quantity | Average Price | Market Value | Source |
| --- | ---: | ---: | ---: | --- |
| `6897` | 400 | 102 | 271200 | runtime_v2_runtime_owned_fill_projection |
| `4591` | 4000 | 101 | 340000 | runtime_v2_runtime_owned_fill_projection |
| `3926` | 800 | 101 | 282400 | runtime_v2_runtime_owned_fill_projection |
| `4446` | 400 | 102 | 352000 | runtime_v2_runtime_owned_fill_projection |
| `4935` | 1200 | 101 | 414000 | runtime_v2_runtime_owned_fill_projection |

Current metadata:

- broker_cash_copied: `false`
- unrelated_demo_positions_copied: `false`
- cash_policy: `runtime_evaluation_capital_plus_runtime_owned_execution_cash_effect`
- position_policy: `runtime_submit_accepted_and_orderlist_filled_and_ledger_position_matched`

## Report / Public Report / Notification

After the execution job regenerated derived artifacts:

- Runtime Report current_portfolio position_count: `5`
- Public Report current_portfolio position_count: `5`
- `reports/public/runtime_v2/latest.json` position_count: `5`
- Public redaction scan: PASS
- Notification payload mode: `payload-only`
- Notification send_executed: `false`

## Next Planning Read Path

Next Planning reads fixed Current SoT:

- `src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py`
  - reads `.runtime/persistent_ledger/state.json`
- `src/ai_fund_lab_v2/runtime_v2/planning/sell_pipeline.py`
  - reads `.runtime/persistent_ledger/state.json`

Therefore the newly projected holdings are available to BUY/SELL planning consumers through the canonical Current path.

## Tests

Targeted tests:

- `python3 -m pytest tests/runtime_v2/test_phase14e21_execution_readonly_pipeline.py tests/runtime_v2/test_phase14e23_execution_acceptance_policy.py tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py`
  - `3 passed`

Additional impacted tests:

- `python3 -m pytest tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py tests/runtime_v2/test_phase14e23_execution_acceptance_policy.py tests/runtime_v2/test_phase14e17_submit_pipeline_connection.py`
  - `8 passed`

Full Runtime v2 tests:

- `python3 -m pytest tests/runtime_v2`
  - `349 passed`

## Acceptance Mapping

| Acceptance | Result |
| --- | --- |
| Execution -> Ledger -> Current connected in regular Runtime path | PASS |
| E44/E45 BUY evidence can update Current positions | PASS |
| Report/Public Report reads updated Current | PASS |
| Notification payload reads updated Current summary | PASS |
| Next Planning can read Current holdings | PASS |
| Demo unrelated broker positions are excluded | PASS |
| Demo broker cash is not copied | PASS |
| Phase14-specific path not added | PASS |
| Demo-only Runtime branch not added | PASS |
| Fake adapter not added | PASS |
| Current direct edit not used | PASS |
| Production order not executed | PASS |
| Notification actual send not executed | PASS |
| launchd/plist not changed | PASS |
| tests/runtime_v2 PASS | PASS |

## Notes

The validation state contains multiple repeated BUY rehearsal fills from previous E44/E45 work. E47 intentionally did not reset or edit Current by hand. The projection result therefore reflects the existing Runtime-owned ledger history at the moment the fixed execution job was rerun.

## Final Judgment

`PHASE14E47_EXECUTION_CURRENT_PROJECTION_CONNECTED`
