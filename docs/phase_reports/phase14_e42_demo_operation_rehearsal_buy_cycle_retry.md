# Phase14-E42 Runtime v2 Demo Operation Rehearsal BUY Cycle Retry

## Summary

- phase: Phase14-E42
- review_level: Level 3 Demo Operation Rehearsal / BUY Cycle
- objective: Retry the E39 BUY cycle after the E41 J-Quants connectivity/error classification fix.
- runtime_body_changed_in_e42: false
- new_runtime_module: false
- new_cli: false
- new_runtime_path: false
- fake_adapter: false
- submit_bypass: false
- sell_executed: false
- production_order_executed: false
- notification_sent: false
- launchd_changed: false
- final_judgment: LEVEL3_DEMO_OPERATION_BUY_BLOCKED

## Result

E42 did not complete the full BUY cycle.

The cycle passed:

1. Backup
2. Reset
3. Market Refresh
4. Morning / Planning / Approval / Pending

The cycle stopped at:

- Submit

Submit did not reach Broker write. The Runtime v2 submit pipeline stopped before send with:

- status: `BLOCKED`
- reason: `no pending items were submitted`
- item-level reason: `BrokerConfigurationError`
- item-level classification: `PRE_SEND_FAILURE`
- demo_submit_executed: `false`
- submitted_count: `0`
- accepted_count: `0`
- rejected_count: `0`
- unknown_count: `0`
- blocked_count: `5`
- Pending consumed: `false`

No additional submit was attempted after this blocker.

## Backup Summary

Backup followed the E38 shape:

- targets:
  - `.runtime/`
  - `reports/runtime_v2/`
  - `reports/public/runtime_v2/`
- backup root: `/private/tmp/phase14e42_backup_20260708T215407Z`
- backup_completed: true
- backup file_count: `20364`
- backup total_bytes: `5181774582`
- backup sha256: `5e7d49a2317e6bb3992ed1628b9f57c083eb0ea9f91a3138d4af2b6613a31496`

The backup root is outside the Runtime v2 operational tree. No new Runtime/rehearsal path was created.

## Reset Summary

Reset used existing Runtime v2 components only:

- `initialize_demo_operation_current_sot`
- `write_pending_order_plan`
- `write_runtime_state`
- `generate_public_report_from_current`

Observed reset state:

| Field | Value |
| --- | ---: |
| cash | 1000000.0 |
| buying_power | 1000000.0 |
| market_value | 0 |
| total_equity | 1000000.0 |
| positions | 0 |
| pending_state | PENDING_APPROVAL |
| pending_items | 0 |
| orders ledger | 0 |
| executions ledger | 0 |
| positions ledger | 0 |
| cash ledger | 1 |
| events ledger | 1 |

## Market Refresh Summary

Command:

```text
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job market_refresh \
  --business-date 2026-07-09 \
  --submit-enabled false \
  --notification-mode payload-only \
  --stop-on-review-required \
  --stop-on-blocked \
  --market-refresh-allow-api-fetch true
```

Result:

- exit_code: `0`
- manifest: `.runtime/runtime_state/run_manifest/2026-07-09/runtime-v2-market_refresh-2026-07-09-20260708T215439.305080+0000.json`
- status: `PASS`
- latest_available_market_date: `2026-07-08`
- requested_feature_date: `2026-07-09`
- selected_feature_date: `2026-07-08`
- carryover_used: `true`
- freshness_lag_business_days: `1`
- blocked_reasons: `[]`
- feature_refresh_executed: `true`

This confirms Market Refresh is no longer checkpoint-only and no longer blocked by the E39 `carryover_stale` state.

## Morning Summary

Command:

```text
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job morning \
  --business-date 2026-07-09 \
  --submit-enabled false \
  --notification-mode payload-only \
  --stop-on-review-required \
  --stop-on-blocked
```

Result:

- exit_code: `0`
- manifest: `.runtime/runtime_state/run_manifest/2026-07-09/runtime-v2-morning-2026-07-09-20260708T215957.130562+0000.json`
- status: `PASS`
- feature_input_missing: false
- price_source_status: `PASS`
- carryover_used: `true`
- freshness_lag_business_days: `1`

Important observation:

- Market Refresh for `2026-07-09` produced selected feature date `2026-07-08`.
- Morning for business date `2026-07-09` read feature-date contract `2026-07-08`, which selected `2026-07-07`.

This is not an immediate blocker because the Morning contract still passed freshness lag 1, but it should be reviewed as a schedule/feature-date alignment issue before the next Level 3 run.

## Pending Summary

Pending after Morning:

- state: `APPROVED`
- pending_plan_id: `pending-order-plan-d3a1d844273f2adc`
- target_session_date: `2026-07-09`
- item_count: `5`
- approved_item_count: `5`
- approval linked: true
- consumed: false
- 9000-series symbols: none

Pending items:

| Symbol | Side | Quantity | Estimated Price | Estimated Amount | Price Source | Price As Of |
| --- | --- | ---: | ---: | ---: | --- | --- |
| 68970 | BUY | 100 | 669.0 | 66900.0 | jquants_raw_normalized_daily_quotes_close | 2026-07-07 |
| 45910 | BUY | 1000 | 98.0 | 98000.0 | jquants_raw_normalized_daily_quotes_close | 2026-07-07 |
| 39260 | BUY | 200 | 357.0 | 71400.0 | jquants_raw_normalized_daily_quotes_close | 2026-07-07 |
| 44460 | BUY | 100 | 853.0 | 85300.0 | jquants_raw_normalized_daily_quotes_close | 2026-07-07 |
| 49350 | BUY | 300 | 309.0 | 92700.0 | jquants_raw_normalized_daily_quotes_close | 2026-07-07 |

Checks:

- `estimated_price=1000` fallback: not used
- price_source present: true
- price_as_of present: true
- quantity based on price/budget: true
- Demo 9000-series exclusion maintained: true

## Submit Summary

Command:

```text
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job submit \
  --business-date 2026-07-09 \
  --submit-enabled true \
  --notification-mode payload-only \
  --stop-on-review-required \
  --stop-on-blocked
```

Result:

- exit_code: `10`
- manifest: `.runtime/runtime_state/run_manifest/2026-07-09/runtime-v2-submit-2026-07-09-20260708T220023.026953+0000.json`
- final_state: `BLOCKED`
- stage: `runtime_v2_submit_pipeline`
- stage status: `BLOCKED`
- reason: `no pending items were submitted`

Submit details:

- pending source: `.runtime/pending_order_plan/pending_order_plan.json`
- pending source only: true
- state before submit: `APPROVED`
- approved items: `5`
- preflight_status: `PASS` for all 5 items
- adapter/pre-send status: `PRE_SEND_FAILURE`
- item reason: `BrokerConfigurationError`
- response classification:
  - `business_classification=PRE_SEND_FAILURE`
  - `p_err_classification=EXCEPTION_BEFORE_SEND`
  - `order_number_present=false`
  - `result_code_present=false`
- demo_submit_executed: `false`
- submitted_count: `0`
- accepted_count: `0`
- rejected_count: `0`
- unknown_count: `0`
- blocked_count: `5`
- raw_request_saved: `false`
- raw_response_saved: `false`
- secret_saved: `false`
- Pending consumed: `false`

Because the error occurred before Broker send, no Broker order was created by this E42 run.

## Broker Summary

- Broker write started: false
- Broker accepted count: 0
- Broker rejected count: 0
- Broker unknown count: 0
- Broker response: not available because the adapter failed before send
- Production endpoint reached: false
- raw request/response saved: false
- secret saved: false

Broker settings status was checked without printing secrets:

- environment: `demo`
- demo base URL: true
- auth_id_file configured: true
- private_key_file configured and exists: true
- second_password_file configured and exists: true
- local_config_path configured and exists: true
- require_demo_environment: PASS

The sanitized manifest only exposes `BrokerConfigurationError`, so the exact sub-reason remains a follow-up investigation item.

## Execution Summary

Execution job was not run after Submit BLOCKED.

Reason:

- There were no submitted order ids.
- There were no ledger order records.
- Pending remained unconsumed.
- Running execution would not validate BUY fill reflection and could obscure the actual blocker.

Execution status for E42:

- `SKIPPED_DUE_TO_SUBMIT_BLOCKED`

## Current Summary

Current after E42 stop:

- cash: `1000000.0`
- buying_power: `1000000.0`
- market_value: `0`
- total_equity: `1000000.0`
- positions: `[]`
- source: `phase14e8_demo_operation_initial_state`
- review_required: `false`

This is correct for a pre-send submit blocker: no Broker order was accepted and no asset mutation should occur.

## Ledger Summary

Ledger after E42 stop:

- orders.jsonl: `0`
- executions.jsonl: `0`
- positions.jsonl: `0`
- cash.jsonl: `1`
- events.jsonl: `1`

This is correct because no Broker write was started.

## Report Summary

Generated/updated artifacts:

- `reports/runtime_v2/2026-07-09/runtime_report.json`
- `reports/runtime_v2/2026-07-09/runtime_report.md`
- `reports/public/runtime_v2/2026-07-09/public_report.json`
- `reports/public/runtime_v2/2026-07-09/public_report.md`
- `reports/public/runtime_v2/latest.json`
- `reports/public/runtime_v2/latest.md`
- `reports/runtime_v2/2026-07-09/audit_result.json`

Report checks:

- Current Portfolio section: present
- Today's Operation Summary section: present
- Ledger History Summary section: present
- Market data freshness section: present
- Notification section: present
- Redaction scan: PASS

Known report limitation observed:

- Public report still says `Submit status: NOT_SUBMITTED_OR_NO_TODAY_RECORD`, because submit was blocked before ledger order records were written.
- The submit blocker is preserved in the run manifest, but not clearly reflected in the public report. This should be a follow-up Report scope improvement.

## Notification Summary

- notification payload generated: true
- queue/result model generated: available in payload/report artifacts
- actual send: false
- LINE status: `send-disabled`
- Discord status: `send-disabled`
- execution_equivalent_count: 0

## Prohibited Actions Check

- SELL: not executed
- Production order: not executed
- Notification real send: not executed
- launchd/plist change: not executed
- Runtime body change during E42: not executed
- new Runtime module: not created
- new CLI: not created
- new Runtime path: not created
- fake adapter: not used
- submit bypass: not used
- Current direct edit: not performed
- Phase9 Runtime: not used
- Phase9 writer: not used
- raw request/response/secret saved: false

## Blockers

1. Submit pre-send `BrokerConfigurationError`
   - All Runtime-side Pending/Approval/preflight checks passed.
   - Adapter failed before Broker send.
   - No order was submitted.
   - Exact sub-reason is not exposed by the sanitized submit manifest.

2. Feature-date alignment observation
   - Market Refresh selected 2026-07-08 for 2026-07-09.
   - Morning selected 2026-07-07 via the 2026-07-08 contract.
   - This passed freshness rules but should be clarified before another Level 3 run.

3. Public report blocker visibility
   - Submit blocker is clear in run manifest.
   - Public report does not clearly surface pre-send submit blocker.

## Final Judgment

`LEVEL3_DEMO_OPERATION_BUY_BLOCKED`

