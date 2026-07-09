# Phase14-E48 Runtime v2 Demo Operation Rehearsal BUY Acceptance Validation

## Summary

- phase: Phase14-E48
- review_level: Level 3 Demo Operation Rehearsal / BUY Acceptance
- objective: Validate BUY cycle from 1,000,000 JPY / no Runtime Current positions through Execution -> Current -> Report -> Notification -> Next Planning.
- runtime_changed_in_e48: false
- new_runtime_module: false
- new_cli: false
- new_runtime_path: false
- fake_adapter: false
- submit_bypass: false
- current_direct_edit: false
- sell_executed: false
- production_order_executed: false
- notification_sent: false
- launchd_changed: false
- final_judgment: `LEVEL3_DEMO_OPERATION_BUY_REVIEW_REQUIRED`

## Executive Result

E48 confirmed that the E47 Runtime connection works:

`Execution -> Ledger -> runtime_owned_fill_projection -> Current -> Report/Public Report -> Notification Payload -> Next Planning`

All downstream consumers read the same Current positions after Execution.

However, E48 cannot be accepted as a clean BUY 1-cycle acceptance because Broker Demo still contained previous same-symbol rehearsal positions. The Runtime reset returned `.runtime` Current to 1,000,000 JPY / positions empty, but it did not and cannot reset Broker Demo holdings. Execution ReadOnly then saw aggregate Broker positions for the same five Runtime-owned symbols and projected those aggregate quantities into Current.

Therefore:

- Data flow connection: PASS
- Clean single-cycle BUY acceptance: REVIEW_REQUIRED

## Backup Summary

Backup followed the E38 shape.

- backup root: `/private/tmp/phase14e48_buy_acceptance_20260709T020548Z/backup`
- targets:
  - `.runtime/`
  - `reports/runtime_v2/`
  - `reports/public/runtime_v2/`
- backup_match: true
- file_count: `20511`
- total_bytes: `5184704210`
- sha256: `a8657f1840c5e3a99cc609f3314343219b55f7c6771f00362347274e5f21a8f7`

No new Runtime path or rehearsal path was created.

## Reset Summary

Reset used existing Runtime v2 initialization/writers, not direct JSON editing.

Observed reset state:

- cash: `1000000.0`
- buying_power: `1000000.0`
- market_value: `0`
- total_equity: `1000000.0`
- positions_count: `0`
- source: `phase14e8_demo_operation_initial_state`
- pending state: `PENDING_APPROVAL`
- pending items: `0`
- ledger orders: `0`
- ledger executions: `0`
- ledger positions: `0`
- ledger cash records: `1`
- ledger event records: `1`
- public report redaction: PASS

## Market Refresh Summary

Manifest:

- `.runtime/runtime_state/run_manifest/2026-07-09/runtime-v2-market_refresh-2026-07-09-20260709T020615.806789+0000.json`

Result:

- exit_code: `0`
- stage: `runtime_v2_market_refresh_pipeline`
- status: `PASS`
- feature_refresh_status: `FEATURES_READY`
- selected_feature_date: `2026-07-08`
- carryover_used: true
- freshness_lag_business_days: `1`

Market Refresh was not checkpoint-only.

## Morning / Pending Summary

Manifest:

- `.runtime/runtime_state/run_manifest/2026-07-09/runtime-v2-morning-2026-07-09-20260709T021150.059000+0000.json`

Result:

- exit_code: `0`
- stage: `morning_ai_planning_pending_pipeline`
- status: `PASS`
- pending_plan_id: `pending-order-plan-faa37c48f1867a67`
- pending state: `APPROVED`
- target_session_date: `2026-07-09`
- pending items: `5`
- approved items: `5`
- consumed: false
- price_source present: true
- estimated_price=1000 fallback: not observed
- Demo 9000-series pending: not observed

Pending items:

| Symbol | Side | Quantity | Estimated Price | Estimated Amount | Price Source | Price As Of |
| --- | --- | ---: | ---: | ---: | --- | --- |
| `68970` | BUY | 100 | 669.0 | 66900.0 | jquants_raw_normalized_daily_quotes_close | 2026-07-07 |
| `45910` | BUY | 1000 | 98.0 | 98000.0 | jquants_raw_normalized_daily_quotes_close | 2026-07-07 |
| `39260` | BUY | 200 | 357.0 | 71400.0 | jquants_raw_normalized_daily_quotes_close | 2026-07-07 |
| `44460` | BUY | 100 | 853.0 | 85300.0 | jquants_raw_normalized_daily_quotes_close | 2026-07-07 |
| `49350` | BUY | 300 | 309.0 | 92700.0 | jquants_raw_normalized_daily_quotes_close | 2026-07-07 |

## Submit Summary

Manifest:

- `.runtime/runtime_state/run_manifest/2026-07-09/runtime-v2-submit-2026-07-09-20260709T021214.295668+0000.json`

Result:

- exit_code: `0`
- stage: `runtime_v2_submit_pipeline`
- status: `PASS`
- demo_submit_executed: true
- submitted_count: `5`
- accepted_count: `5`
- rejected_count: `0`
- unknown_count: `0`
- blocked_count: `0`
- pending_consumed: true
- raw_request_saved: false
- raw_response_saved: false
- secret_saved: false

All 5 pending BUY items were sent through the regular Runtime v2 submit path and classified as ACCEPTED.

## Execution Summary

Manifest:

- `.runtime/runtime_state/run_manifest/2026-07-09/runtime-v2-execution-2026-07-09-20260709T021242.073661+0000.json`

Result:

- exit_code: `0`
- stage: `runtime_v2_execution_readonly_pipeline`
- status: `PASS`
- execution_acceptance_status: `PASS`
- execution_equivalent_count: `25`
- ledger_orders_appended: `25`
- ledger_executions_appended: `25`
- ledger_positions_appended: `11`
- ledger_cash_appended: `1`
- ledger_events_appended: `1`
- asset_policy: `runtime_owned_fill_projection`
- asset_current_written: true
- runtime_owned_projection_status: `PASS`
- runtime_owned_projection_reason: `runtime_owned_fills_projected_to_current`
- projected_position_count: `5`
- projected_cash: `140500.0`
- projected_market_value: `2047500.0`
- projected_total_equity: `2188000.0`
- reconcile_status: `PASS_WITH_WARNINGS`

Excluded Broker Demo positions:

- `6501`
- `6502`
- `9984`
- `6504`
- `6505`
- `9001`

This proves unrelated Demo broker positions were not copied.

## Current Summary

Current after Execution:

- source: `runtime_v2_runtime_owned_fill_projection`
- cash: `140500.0`
- buying_power: `140500.0`
- market_value: `2047500.0`
- total_equity: `2188000.0`
- positions_count: `5`
- review_required: false

Current positions:

| Symbol | Quantity | Average Price | Market Value |
| --- | ---: | ---: | ---: |
| `3926` | 1000 | 101 | 351000 |
| `4446` | 500 | 102 | 435500 |
| `4591` | 5000 | 101 | 410000 |
| `4935` | 1500 | 101 | 513000 |
| `6897` | 500 | 102 | 338000 |

Current metadata:

- broker_cash_copied: false
- unrelated_demo_positions_copied: false
- cash_policy: `runtime_evaluation_capital_plus_runtime_owned_execution_cash_effect`
- position_policy: `runtime_submit_accepted_and_orderlist_filled_and_ledger_position_matched`

## Report Summary

Runtime Report:

- path: `reports/runtime_v2/2026-07-09/runtime_report.json`
- current position_count: `5`
- accepted_count: `5`
- filled_count: `25`
- execution_equivalent_count: `25`
- reconcile.status: `PASS`

Public Report:

- path: `reports/public/runtime_v2/2026-07-09/public_report.json`
- position_count: `5`
- redaction_scan: PASS

Latest Public Report:

- path: `reports/public/runtime_v2/latest.json`
- position_count: `5`
- redaction_scan: PASS

## Notification Summary

Notification payload:

- path: `reports/runtime_v2/2026-07-09/notification_payload.json`
- mode: `payload-only`
- send_executed: false
- position_count: `5`

No LINE / Discord / webhook delivery was executed.

## Broker ReadOnly Summary

Runtime-owned projected symbols:

- `6897`
- `4591`
- `3926`
- `4446`
- `4935`

Broker ReadOnly positions for those symbols:

| Symbol | Quantity | Average Price | Market Value |
| --- | ---: | ---: | ---: |
| `3926` | 1000 | 101 | 351000 |
| `4446` | 500 | 102 | 435500 |
| `4591` | 5000 | 101 | 410000 |
| `4935` | 1500 | 101 | 513000 |
| `6897` | 500 | 102 | 338000 |

Current positions match Broker ReadOnly positions for the projected Runtime-owned symbols.

## Next Planning Current Read

Read checks:

- Morning planning `_load_asset_state(.runtime/persistent_ledger/state.json)` positions_count: `5`
- SELL planning `_load_asset_state(.runtime/persistent_ledger/state.json)` positions_count: `5`
- cash read by both: `140500.0`

This confirms Next Planning consumers can read the projected Current holdings from fixed Current path.

## Consistency Matrix

| Check | Result |
| --- | --- |
| Current positions vs Runtime Report positions | PASS |
| Current positions vs Public Report positions | PASS |
| Current positions vs latest.json positions | PASS |
| Current positions vs Notification payload positions | PASS |
| Current positions vs Broker ReadOnly projected-symbol positions | PASS |
| Next Planning reads Current positions | PASS |

## Acceptance Matrix

| Acceptance | Result | Notes |
| --- | --- | --- |
| Backup PASS | PASS | External `/private/tmp` backup, no Runtime backup path created. |
| Reset PASS | PASS | Current 1,000,000 / positions 0 / ledger empty. |
| Market Refresh PASS | PASS | Feature artifacts ready with explicit carryover. |
| Morning PASS | PASS | Pending APPROVED with 5 BUY items. |
| Submit PASS | PASS | Demo Broker submit executed through regular Runtime path. |
| Broker Accepted PASS | PASS | 5 accepted / 0 rejected / 0 unknown. |
| Execution PASS | PASS | Execution ReadOnly accepted OrderList + Position + Cash evidence. |
| Current update PASS | PASS | Current source changed to `runtime_v2_runtime_owned_fill_projection`. |
| Report update PASS | PASS | Report/Public/latest show 5 holdings. |
| Notification payload PASS | PASS | Payload-only, no send. |
| Next Planning Current read PASS | PASS | Morning/SELL planning loaders see 5 positions. |
| Runtime changed in E48 | PASS | No code changes performed in E48. |
| Prohibited actions | PASS | No SELL, Production order, Notification send, launchd change, fake adapter, bypass, or Current direct edit. |
| Clean single-cycle acceptance | REVIEW_REQUIRED | Broker Demo retained previous same-symbol positions, so projected quantities are aggregate Broker positions rather than only this cycle's order quantities. |

## Review Required Reason

E48 started Runtime Current from 1,000,000 JPY / positions empty, but Broker Demo itself still held previous same-symbol rehearsal positions. Because E47 projection matches Runtime-owned symbols against latest Broker Position evidence, the projected Current holdings became the aggregate Broker quantities for those symbols.

This means E48 proves:

- Execution -> Current -> Report -> Notification -> Next Planning data flow is connected.
- Runtime excludes unrelated Broker positions and does not copy Broker cash.
- Derived artifacts are internally consistent.

But E48 does not prove a clean single BUY cycle from an actually empty Broker position state.

To mark Level3 BUY as fully accepted, the next validation should start from a Broker state where the target symbols are not already held, or should first run a controlled SELL/cleanup cycle and then rerun BUY acceptance.

## Prohibited Actions Check

- runtime_changed_in_e48: false
- new_runtime_module: false
- new_cli: false
- new_runtime_path: false
- fake_adapter: false
- submit_bypass: false
- current_direct_edit: false
- sell_executed: false
- production_order_executed: false
- notification_sent: false
- launchd_changed: false
- raw_request_saved: false
- raw_response_saved: false
- secret_saved: false
- Phase9 runtime used: false
- Phase9 writer used: false

## Final Judgment

`LEVEL3_DEMO_OPERATION_BUY_REVIEW_REQUIRED`
