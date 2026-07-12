# Phase15-BT Explicit Demo Broker Write Execution with Final Pre-Send Gate

## Executive Summary

Phase15-BT executed exactly one Tachibana Demo broker write for the explicitly authorized acceptance scenario.

Final judgment:

```text
DEMO_BROKER_WRITE_ACCEPTED
```

The broker submit adapter returned `ACCEPTED` and the immediate post-send broker Order List confirmed the `6501` SELL order as `全部約定` with `executed_quantity=100` and `remaining_quantity=0`. The post-send broker Position Inventory also confirmed `6501 quantity=100` and `available_quantity=100`, matching the expected demo acceptance impact from `200 -> 100`.

Execution detail ReadOnly evidence remains incomplete: post-send `broker_readonly_refresh` ended with `FAILED_BROKER_READONLY_FETCH` because order-detail execution fetch failed. Therefore, no Execution Normalization, Ledger Append, Current Apply, or Notification Send was performed.

## Scope Boundary

Allowed and performed:

- User Authorization artifact generation.
- Final pre-send gate.
- One Tachibana Demo broker write for `6501 SELL 100 MARKET DAY`.
- Immediate post-send ReadOnly confirmation.
- Isolated acceptance pending state update to `SUBMITTED`.
- Evidence and report generation.

Explicitly not performed:

- Second send or resend.
- Auto cancel.
- Execution Normalization.
- Ledger Append.
- Current Apply.
- Notification Send.
- Production Write.
- Existing `.runtime` mutation.

## User Authorization

Artifact:

```text
.runtime_acceptance_phase15_demo_reinit/runtime_state/user_authorization/2026-07-13/phase15bt_user_authorization.json
```

Authorization details:

| Field | Value |
|---|---|
| authorization_source | `current_conversation_explicit_approval` |
| explicit_approval_text | `デモ環境なので、この内容でBroker Writeを進めてよい。` |
| environment | `demo` |
| issue_code | `6501` |
| side | `SELL` |
| quantity | `100` |
| order_type | `MARKET` |
| price_condition | `MARKET` |
| limit_price | `null` |
| time_in_force | `DAY` |
| target_session | `2026-07-13` |
| broker_write_authorized | `true` |
| production_write_authorized | `false` |
| expires_at | `2026-07-13T15:00:00+09:00` |
| request_hash | `sha256:56ebea4e14ffe7369f133260645720c49303711b74c21960973e833016b37f70` |

## Final Pre-Send Gate

Artifact:

```text
.runtime_acceptance_phase15_demo_reinit/runtime_state/demo_broker_write_execution/2026-07-13/final_pre_send_gate.json
```

Gate status:

```text
PASS
```

All required checks passed:

| Check | Result |
|---|---|
| demo_login_session | `true` |
| broker_send_window | `true` |
| target_session_valid | `true` |
| broker_snapshot_fresh | `true` |
| quantity_ge_100 | `true` |
| available_quantity_ge_100 | `true` |
| open_sell_order_conflict_none | `true` |
| open_opposite_side_order_conflict_none | `true` |
| safety_unexpired | `true` |
| safety_sell_submit_allowed | `true` |
| safety_broker_write_allowed_for_acceptance | `true` |
| safety_block_submit_false | `true` |
| pending_approved | `true` |
| pending_unconsumed | `true` |
| approval_unexpired_unrevoked | `true` |
| request_hash_matches_authorization | `true` |

Temporal audit:

| Field | Value |
|---|---|
| business_date | `2026-07-13` |
| target_session_date | `2026-07-13` |
| intended_submit_date | `2026-07-13` |
| authorized_at | `2026-07-12T01:27:39.676485+00:00` |
| created_at_is_not_send_authority | `true` |
| created_at_metadata_only | `2026-07-13` |
| updated_at_metadata_or_expiry | `2026-07-13T15:00:00+09:00` |

## Fresh Pre-Send Broker Evidence

Command:

```bash
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --mode demo --job broker_readonly_refresh --business-date 2026-07-13 --submit-enabled false --notification-mode payload-only --runtime-root .runtime_acceptance_phase15_demo_reinit --reports-root reports/phase_reports/phase15_bt/runtime_v2_pre_send --public-reports-root reports/phase_reports/phase15_bt/public_runtime_v2_pre_send --manifest-root .runtime_acceptance_phase15_demo_reinit/runtime_state/run_manifest --log-root .runtime_acceptance_phase15_demo_reinit/runtime_state/logs
```

Result:

| Item | Value |
|---|---|
| exit_code | `0` |
| broker_readonly_snapshot_status | `PASS_WITH_WARNINGS` |
| broker_readonly_refresh_status | `READY` |
| data_origin | `BROKER_API` |
| fixture_used | `false` |
| mock_used | `false` |
| session_status | `PASS` |
| open_orders_count | `0` |
| executions_count | `0` |
| 6501 quantity | `200` |
| 6501 available_quantity | `200` |

## Safety Authority

Safety authority at pre-send gate:

| Field | Value |
|---|---|
| sell_submit | `ALLOWED` |
| broker_write | `ALLOWED_FOR_ACCEPTANCE` |
| block_submit | `false` |
| safety_unexpired | `true` |

The safety decision permitted this explicit demo acceptance broker write only. It did not authorize production write or any automatic sell flow.

## Request Hash

The request hash matched BS final request review and BT user authorization:

```text
sha256:56ebea4e14ffe7369f133260645720c49303711b74c21960973e833016b37f70
```

## Broker Write

Submit route:

```text
RuntimeV2TachibanaDemoSubmitAdapter(dry_run=false).submit
```

The runtime submit pipeline was intentionally not used because it would continue into ledger/current-adjacent processing that was outside the BT safety boundary.

Result:

| Item | Value |
|---|---|
| broker_client_call_count | `1` |
| broker_write_count | `1` |
| broker_client_called | `true` |
| submit_attempted | `true` |
| submit_result_status | `ACCEPTED` |
| broker_response_classification | `ACCEPTED` |
| broker_api_called | `true` |
| submitted | `true` |
| accepted | `true` |
| broker_order_id_hash | `sha256:b80b43eeb157caa8a56c14684356cbbd0b9cddebc05905a49059f72e4861d153` |
| raw_request_saved | `false` |
| raw_response_saved | `false` |
| secret_saved | `false` |

Broker response classification:

| Field | Value |
|---|---|
| business_classification | `ACCEPTED` |
| order_number_present | `true` |
| p_errno | `0` |
| sResultCode | `0` |
| result_code_present | `true` |
| result_code_zero | `true` |
| warning_code_present | `true` |
| warning_code_value | `0` |
| warning_code_zero | `true` |

## Immediate Post-Send ReadOnly

Command:

```bash
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --mode demo --job broker_readonly_refresh --business-date 2026-07-13 --submit-enabled false --notification-mode payload-only --runtime-root .runtime_acceptance_phase15_demo_reinit --reports-root reports/phase_reports/phase15_bt/runtime_v2_post_send --public-reports-root reports/phase_reports/phase15_bt/public_runtime_v2_post_send --manifest-root .runtime_acceptance_phase15_demo_reinit/runtime_state/run_manifest --log-root .runtime_acceptance_phase15_demo_reinit/runtime_state/logs
```

Result:

| Item | Value |
|---|---|
| exit_code | `20` |
| snapshot_status | `FAILED_BROKER_READONLY_FETCH` |
| reconciliation classification | `ORDER_AND_POSITION_CONFIRMED_EXECUTION_DETAIL_REVIEW_REQUIRED` |
| read_only_data_origin | `BROKER_API` |
| order_list_confirmed | `true` |
| execution_detail_status | `FAIL` |
| execution_detail_failure_count | `1` |
| executions_count | `0` |

Order List evidence:

| Field | Value |
|---|---|
| issue_code | `6501` |
| side | `sell` |
| quantity | `100` |
| status | `全部約定` |
| executed_quantity | `100` |
| remaining_quantity | `0` |
| order_datetime | `20260712100459` |
| expire_date | `20260712` |
| broker_order_id_hash_from_order_list | `order_b80b43eeb157caa8` |

Position evidence:

| Field | Value |
|---|---|
| 6501 quantity | `100` |
| 6501 available_quantity | `100` |
| 6501 market_value | `470000` |
| cash_available | `17704424` |
| buying_power | `20009824` |

## Pending State

Artifact:

```text
.runtime_acceptance_phase15_demo_reinit/pending_order_plan/pending_order_plan.json
```

After the accepted broker write, the isolated acceptance pending state was updated to:

| Field | Value |
|---|---|
| state | `SUBMITTED` |
| consume.consumed | `false` |
| consume.submitted_order_ids | `[]` |
| consume.ledger_order_record_ids | `[]` |

This is not Execution Pending consumption and does not imply ledger/current application.

## Runtime Mutation Audit

BT used the isolated runtime root:

```text
.runtime_acceptance_phase15_demo_reinit
```

Existing `.runtime` was not mutated. Hashes remained:

| Artifact | SHA-256 |
|---|---|
| `.runtime/pending_order_plan/pending_order_plan.json` | `84075f23cc6d1c5ae227de1bfe4a213221aefd131fdadb395058755601ac2c77` |
| `.runtime/runtime_state/safety/latest_safety_decision.json` | `c4c1019497fc47b245ad92f21b0b06d59abe32e449f026eb0f9b0aed112faeb7` |
| `.runtime/persistent_ledger/state.json` | `add4f37373c6f7331b6894b29322ffd39a6a0c911086150427d57a2ddb442b0f` |

BT mutation flags:

| Item | Performed |
|---|---|
| Broker Write | `true` |
| Execution Normalization | `false` |
| Ledger Append | `false` |
| Current Apply | `false` |
| Notification Send | `false` |
| Existing `.runtime` mutation | `false` |
| Production Write | `false` |

## Evidence Artifacts

Primary artifacts:

| Artifact | Path |
|---|---|
| Markdown report | `docs/phase_reports/phase15_bt_explicit_demo_broker_write_execution.md` |
| JSON report | `reports/phase_reports/phase15_bt_explicit_demo_broker_write_execution.json` |
| User Authorization | `.runtime_acceptance_phase15_demo_reinit/runtime_state/user_authorization/2026-07-13/phase15bt_user_authorization.json` |
| Final pre-send gate | `.runtime_acceptance_phase15_demo_reinit/runtime_state/demo_broker_write_execution/2026-07-13/final_pre_send_gate.json` |
| Submit manifest | `.runtime_acceptance_phase15_demo_reinit/runtime_state/demo_broker_write_execution/2026-07-13/phase15bt_submit_manifest.json` |
| Post-send reconciliation | `.runtime_acceptance_phase15_demo_reinit/runtime_state/demo_broker_write_execution/2026-07-13/post_send_readonly_reconciliation.json` |
| Public post-send reconciliation copy | `reports/phase_reports/phase15_bt/post_send_readonly_reconciliation.json` |
| Pre-send runtime report | `reports/phase_reports/phase15_bt/runtime_v2_pre_send/2026-07-13/runtime_report.json` |
| Post-send runtime report | `reports/phase_reports/phase15_bt/runtime_v2_post_send/2026-07-13/runtime_report.json` |
| Broker snapshot | `.runtime_acceptance_phase15_demo_reinit/runtime_state/broker_readonly/2026-07-13/tachibana_snapshot.json` |

## Regression

Regression assertions are covered by:

```text
tests/runtime_v2/test_phase15bt_explicit_demo_broker_write_execution.py
```

Confirmed conditions:

- User authorization exists and matches the approved request hash.
- Final pre-send gate is `PASS`.
- Broker write count is exactly `1`.
- Broker response is `ACCEPTED`.
- Post-send Order List confirms the `6501 SELL 100` order.
- Post-send Position Inventory confirms `6501 quantity=100`.
- Pending state is `SUBMITTED` but not consumed.
- Execution Normalization, Ledger Append, Current Apply, and Notification Send are false.
- Existing `.runtime` hash values are preserved.

## Remaining Blocker

```text
EXECUTION_DETAIL_READONLY_REVIEW_REQUIRED
```

The broker accepted the order and Order List/Position evidence confirms the accepted order impact. However, execution detail ReadOnly fetch failed, so Execution Normalization and Current Apply remain blocked until the execution evidence path is reviewed.

## Next Prefix

Recommended next prefix:

```text
Phase15-BU Demo Broker Write Post-Send Execution Evidence Review
```

Purpose:

- Reconcile Order List `全部約定` evidence with Execution Detail fetch failure.
- Decide whether Order List plus Position Inventory is sufficient for acceptance-only fill evidence.
- Keep Execution Normalization, Ledger Append, Current Apply, and Notification Send blocked until evidence authority is explicitly closed.
