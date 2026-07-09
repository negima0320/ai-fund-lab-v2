# Phase14-E44 Demo Operation Rehearsal BUY Cycle Retry after Broker Diagnostic Fix

## Summary

- phase: Phase14-E44
- review_level: Level 3 Demo Operation Rehearsal / BUY Cycle
- objective: Retry the Demo Operation BUY cycle after the BrokerConfigurationError issue was resolved.
- business_date: 2026-07-09
- runtime_body_changed_in_e44: false
- new_runtime_module: false
- new_cli: false
- new_runtime_path: false
- fake_adapter: false
- submit_bypass: false
- sell_executed: false
- production_order_executed: false
- notification_sent: false
- launchd_changed: false
- final_judgment: `LEVEL3_DEMO_OPERATION_BUY_PASS`

## Result

E44 was re-executed from Backup and Reset using only the existing Runtime v2 CLI and fixed Current paths.

The cycle passed:

1. Backup
2. Reset
3. Market Refresh
4. Morning / Planning / Approval / Pending
5. Demo Submit
6. Broker Accepted classification
7. Execution ReadOnly
8. Execution-equivalent ledger records
9. Reconcile / Report / Public Report
10. Notification payload generation

The previous BrokerConfigurationError did not recur. Demo Broker Submit was executed through the normal Runtime v2 submit job, and all 5 BUY orders were classified as ACCEPTED.

## Backup Summary

Backup followed the E38 shape:

- targets:
  - `.runtime/`
  - `reports/runtime_v2/`
  - `reports/public/runtime_v2/`
- backup root: `/private/tmp/phase14e44_rerun_backup_20260709T000219Z`
- backup_completed: true
- backup file_count: `20378`
- backup total_bytes: `5181981733`
- backup sha256: `45593fdb58f4d4cddf825a947b37cf109f1869626cea311e31d10dd7266e815f`
- backup signature matched pre-backup signature: true

The backup root is outside the Runtime v2 operational tree. No new Runtime path or rehearsal path was introduced.

## Reset Summary

Reset used the existing Runtime v2 state initialization path and fixed Current paths.

- cash: `1000000.0`
- buying_power: `1000000.0`
- market_value: `0`
- total_equity: `1000000.0`
- positions_count: `0`
- pending_state: `PENDING_APPROVAL`
- pending_items: `0`
- orders.jsonl bytes: `0`
- executions.jsonl bytes: `0`
- positions.jsonl bytes: `0`
- cash ledger records: `1`
- event ledger records: `1`
- public report redaction: PASS

No direct JSON hand-editing, Runtime bypass, or Current shortcut was used.

## Market Refresh

Command used the existing Runtime v2 CLI with `--job market_refresh`.

- manifest: `.runtime/runtime_state/run_manifest/2026-07-09/runtime-v2-market_refresh-2026-07-09-20260709T000243.615639+0000.json`
- exit_code: `0`
- stage: `runtime_v2_market_refresh_pipeline`
- stage_status: `PASS`
- feature_refresh_status: `FEATURES_READY`
- canonical_normalized_updated: true
- requested_feature_date: `2026-07-09`
- latest_available_market_date: `2026-07-08`
- selected_feature_date: `2026-07-08`
- carryover_used: true
- freshness_lag_business_days: `1`
- freshness_limit_business_days: `1`
- generated_feature_artifacts:
  - `.runtime/operations/feature_artifacts/2026-07-08/candidate_features.parquet`
  - `.runtime/operations/feature_artifacts/2026-07-08/opportunity_feature_input.parquet`
  - `.runtime/operations/feature_artifacts/2026-07-08/position_feature_input.parquet`
  - `.runtime/operations/feature_artifacts/2026-07-08/capital_policy_input.parquet`

The job was not checkpoint-only. The feature-date carryover was explicit and within the allowed freshness limit.

## Morning / Pending

Command used the existing Runtime v2 CLI with `--job morning`.

- manifest: `.runtime/runtime_state/run_manifest/2026-07-09/runtime-v2-morning-2026-07-09-20260709T000618.345311+0000.json`
- exit_code: `0`
- stage: `morning_ai_planning_pending_pipeline`
- stage_status: `PASS`
- pending_state: `APPROVED`
- pending_plan_id: `pending-order-plan-76dc618ffe6ad201`
- target_session_date: `2026-07-09`
- pending_items: `5`
- approved_item_count: `5`
- consumed: false
- demo 9000-series pending: none
- estimated_price=1000 fallback: none

Generated BUY candidates:

| Symbol | Side | Quantity | Estimated Price | Estimated Amount | Price Source | Price As Of |
| --- | --- | ---: | ---: | ---: | --- | --- |
| 68970 | BUY | 100 | 669.0 | 66900.0 | jquants_raw_normalized_daily_quotes_close | 2026-07-07 |
| 45910 | BUY | 1000 | 98.0 | 98000.0 | jquants_raw_normalized_daily_quotes_close | 2026-07-07 |
| 39260 | BUY | 200 | 357.0 | 71400.0 | jquants_raw_normalized_daily_quotes_close | 2026-07-07 |
| 44460 | BUY | 100 | 853.0 | 85300.0 | jquants_raw_normalized_daily_quotes_close | 2026-07-07 |
| 49350 | BUY | 300 | 309.0 | 92700.0 | jquants_raw_normalized_daily_quotes_close | 2026-07-07 |

## Submit

Command used the existing Runtime v2 CLI with `--job submit --submit-enabled true`.

- manifest: `.runtime/runtime_state/run_manifest/2026-07-09/runtime-v2-submit-2026-07-09-20260709T000640.945877+0000.json`
- exit_code: `0`
- stage: `runtime_v2_submit_pipeline`
- stage_status: `PASS`
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

The BrokerConfigurationError did not recur.

All submitted items had:

- preflight_status: `PASS`
- submit_status: `ACCEPTED`
- business_classification: `ACCEPTED`
- p_errno: `0`
- sResultCode: `0`
- order_number_present: true
- configuration_diagnostic: empty
- next_action: empty

Observation: the redacted response classification still contains `p_err_classification=BROKER_REJECTED_OR_UNKNOWN` while the business classification is ACCEPTED and `sResultCode=0`. This did not block the operation, but should be reviewed as a response-classification cleanup item.

## Execution

Command used the existing Runtime v2 CLI with `--job execution --submit-enabled false`.

- manifest: `.runtime/runtime_state/run_manifest/2026-07-09/runtime-v2-execution-2026-07-09-20260709T000708.911154+0000.json`
- exit_code: `0`
- stage: `runtime_v2_execution_readonly_pipeline`
- stage_status: `PASS`
- execution_acceptance_status: `PASS`
- execution_acceptance_reason: `orderlist_position_cash_evidence_accepted`
- execution_equivalent_count: `5`
- ledger_orders_appended: `5`
- ledger_executions_appended: `5`
- ledger_positions_appended: `11`
- ledger_cash_appended: `1`
- ledger_events_appended: `1`
- order_detail_required: false
- order_detail_status: `OPTIONAL_FAILED`
- reconcile_status: `PASS_WITH_WARNINGS`
- raw request/response/secret saved: false

Ledger after execution:

- orders.jsonl lines: `10`
- executions.jsonl lines: `5`
- positions.jsonl lines: `11`
- cash.jsonl lines: `2`
- events.jsonl lines: `2`

## Current SoT Observation

After execution, `.runtime/persistent_ledger/state.json` remained:

- cash: `1000000.0`
- buying_power: `1000000.0`
- market_value: `0`
- total_equity: `1000000.0`
- positions_count: `0`
- source: `phase14e8_demo_operation_initial_state`

This matches the current execution asset policy recorded in the execution manifest:

- asset_policy: `broker_position_cash_evidence_recorded_only`
- asset_current_written: false

Therefore this E44 retry proves the Demo BUY operation path through Broker acceptance and execution-equivalent evidence, but it does not prove Broker evidence projection into Current positions. That behavior is currently guarded by the Demo capability / asset policy and remains a follow-up design decision if Level 3 acceptance is later defined to require Current holdings projection during rehearsal.

## Report / Public Report / Notification

Generated artifacts:

- Runtime Report JSON: `reports/runtime_v2/2026-07-09/runtime_report.json`
- Runtime Report Markdown: `reports/runtime_v2/2026-07-09/runtime_report.md`
- Public Report JSON: `reports/public/runtime_v2/2026-07-09/public_report.json`
- Public Report Markdown: `reports/public/runtime_v2/2026-07-09/public_report.md`
- Public latest JSON: `reports/public/runtime_v2/latest.json`
- Public latest Markdown: `reports/public/runtime_v2/latest.md`
- Notification Payload: `reports/runtime_v2/2026-07-09/notification_payload.json`

Report checks:

- current_portfolio displayed from Current SoT
- today_operation accepted_count: `5`
- today_operation filled_count: `5`
- execution_equivalent_count: `5`
- reconcile.status: `PASS`
- notification mode: `payload-only`
- notification send_executed: false
- public report redaction_scan: PASS

## Prohibited Actions Check

- Runtime body changed: false
- new Runtime module: false
- new CLI: false
- new Runtime path: false
- fake adapter: false
- submit bypass: false
- SELL executed: false
- Production order: false
- Notification real send: false
- launchd/plist changed: false
- raw request saved: false
- raw response saved: false
- secret saved: false
- Current directly edited: false
- Phase9 runtime used: false
- Phase9 writer used: false

## Final Judgment

`LEVEL3_DEMO_OPERATION_BUY_PASS`

The resolved configuration issue allowed the normal Runtime v2 Demo Operation BUY cycle to reach Demo Broker Submit, classify all 5 orders as ACCEPTED, run Execution ReadOnly, generate execution-equivalent records, update reports, and generate notification payload without forbidden actions.

Follow-up observation: Current SoT holdings were not updated because the execution asset policy is currently `broker_position_cash_evidence_recorded_only` with `asset_current_written=false`.
