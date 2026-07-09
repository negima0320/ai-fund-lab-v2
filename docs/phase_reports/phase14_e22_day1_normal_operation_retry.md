# Phase14-E22 Day1 Normal Operation Retry

## Summary

Phase14-E22 reran the Day1 Demo operation through the normal Runtime v2 path:

Morning -> Pending -> Submit -> Demo Broker -> Execution ReadOnly -> Ledger -> Asset -> Reconcile -> Runtime Report -> Public Report -> Audit.

Final judgment: `PHASE14E22_REVIEW_REQUIRED`

The retry proved that the E19 issue-code normalization and the normal Submit pipeline are now working against Tachibana Demo:

- Morning generated a fresh approved Pending plan.
- Submit Job consumed the fresh Pending plan.
- Demo Broker Submit executed for all 5 Pending items.
- All 5 broker responses were classified as `ACCEPTED`.
- Broker response evidence showed `p_errno=0` and `sResultCode=0` for all 5 items.
- Broker OrderList ReadOnly later returned all 5 orders as `全部約定`.
- Ledger order records were appended.
- Runtime/Public Report and Audit artifacts were generated.

However, the Execution Job ended in `REVIEW_REQUIRED`:

- `CLMOrderList` returned 5 filled orders.
- Position evidence included the 5 accepted symbols.
- Cash / buying power evidence was present.
- Order detail / execution detail fetch failed for all 5 orders.
- Execution manifest recorded `snapshot_status=FAILED_BROKER_READONLY_FETCH`.
- Execution manifest recorded `reconcile_status=REVIEW_REQUIRED`.

Therefore E22 is not classified as a full operation PASS. It is a successful normal Submit retry with accepted Demo orders, followed by a normal Runtime v2 safety stop during Execution ReadOnly.

## Prohibited Actions

| Action | Result |
| --- | --- |
| Production order | Not executed |
| Production Broker API Write | Not executed |
| Notification actual send | Not executed |
| launchd change | Not executed |
| Phase9 Runtime | Not used |
| Test-only path | Not used |
| Recovery-only path | Not used |
| Special recovery code | Not used |

## Morning Job

Command:

`python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --mode demo --job morning --business-date 2026-07-08 --feature-date 2026-07-07 --submit-enabled false --notification-mode payload-only ...`

Manifest:

`.runtime/runtime_state/run_manifest/2026-07-08/runtime-v2-morning-2026-07-08-20260708T062219.982874+0000.json`

Result:

- exit_code: `0`
- Pending path: `.runtime/pending_order_plan/pending_order_plan.json`
- pending_plan_id: `pending-order-plan-c395bc29294719ec`
- state: `APPROVED`
- target_session_date: `2026-07-08`
- consumed: `false`
- items: `5`
- approval: linked

Pending symbols:

| Runtime Symbol | Side | Quantity |
| --- | --- | --- |
| `65220` | BUY | 100 |
| `78780` | BUY | 100 |
| `68970` | BUY | 100 |
| `63270` | BUY | 100 |
| `45910` | BUY | 100 |

## Submit Job

Command:

`python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --mode demo --job submit --business-date 2026-07-08 --submit-enabled true --notification-mode payload-only ...`

Manifest:

`.runtime/runtime_state/run_manifest/2026-07-08/runtime-v2-submit-2026-07-08-20260708T062328.649239+0000.json`

Result:

- exit_code: `0`
- stage: `runtime_v2_submit_pipeline`
- stage_status: `PASS`
- demo_submit_executed: `true`
- submitted_count: `5`
- accepted_count: `5`
- rejected_count: `0`
- unknown_count: `0`
- blocked_count: `0`
- pending_consumed: `true`
- submitted_order_ids: `5`
- ledger orders appended: `5`

## Broker Submit Evidence

All five Runtime symbols were normalized at the broker request boundary. Raw request / raw response / secret values were not saved.

| Runtime Symbol | Broker Issue Code | Normalization Rule | Broker Result |
| --- | --- | --- | --- |
| `65220` | `6522` | `JQUANTS_5CHAR_TRAILING_ZERO_TO_BROKER_4CHAR` | ACCEPTED |
| `78780` | `7878` | `JQUANTS_5CHAR_TRAILING_ZERO_TO_BROKER_4CHAR` | ACCEPTED |
| `68970` | `6897` | `JQUANTS_5CHAR_TRAILING_ZERO_TO_BROKER_4CHAR` | ACCEPTED |
| `63270` | `6327` | `JQUANTS_5CHAR_TRAILING_ZERO_TO_BROKER_4CHAR` | ACCEPTED |
| `45910` | `4591` | `JQUANTS_5CHAR_TRAILING_ZERO_TO_BROKER_4CHAR` | ACCEPTED |

Redacted broker response classification for every item:

- `p_errno=0`
- `sResultCode=0`
- `business_classification=ACCEPTED`
- `order_number_present=true`
- `result_code_present=true`
- `warning_code_value=0`

## Pending / Ledger / Current

After Submit:

- Pending state: `CONSUMED`
- Pending consumed: `true`
- submitted_order_ids_count: `5`
- ledger_order_rows: `15` immediately after Submit
- latest submit ledger statuses: `ACCEPTED`, `ACCEPTED`, `ACCEPTED`, `ACCEPTED`, `ACCEPTED`

After Execution ReadOnly:

- ledger_order_rows: `20`
- latest execution readonly order statuses: `filled`, `filled`, `filled`, `filled`, `filled`
- ledger_positions_count: `17`
- ledger_cash_count: `2`

Current SoT remained the Demo Operation SoT:

- cash: `1,000,000`
- buying_power: `1,000,000`
- market_value: `0`
- total_equity: `1,000,000`
- positions: `[]`
- source: `phase14e8_demo_operation_initial_state`

This is expected under the Demo Broker Capability policy: Demo broker cash / reset positions are evidence, not the Runtime Asset Current SoT.

## Execution Job

Command:

`python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --mode demo --job execution --business-date 2026-07-08 --submit-enabled false --notification-mode payload-only ...`

Manifest:

`.runtime/runtime_state/run_manifest/2026-07-08/runtime-v2-execution-2026-07-08-20260708T062359.076458+0000.json`

Snapshot:

`.runtime/runtime_state/broker_readonly/2026-07-08/tachibana_snapshot.json`

Result:

- exit_code: `20`
- final_state: `REVIEW_REQUIRED`
- stage: `runtime_v2_execution_readonly_pipeline`
- stage_status: `REVIEW_REQUIRED`
- orderlist_readonly_connected: `true`
- execution_reflection_connected: `true`
- ledger_connected: `true`
- asset_connected: `true`
- asset_current_written: `false`
- snapshot_status: `FAILED_BROKER_READONLY_FETCH`
- orders_count: `5`
- positions_count: `12`
- executions_count: `0`
- ledger_orders_appended: `5`
- ledger_positions_appended: `11`
- ledger_cash_appended: `0`
- reconcile_status: `REVIEW_REQUIRED`
- reconcile_findings: `13`

## Broker OrderList ReadOnly Evidence

Broker OrderList returned the five submitted orders as filled:

| Broker Issue Code | Side | Quantity | Executed Quantity | Remaining Quantity | Status |
| --- | --- | --- | --- | --- | --- |
| `4591` | buy | 100 | 100 | 0 | 全部約定 |
| `6327` | buy | 100 | 100 | 0 | 全部約定 |
| `6897` | buy | 100 | 100 | 0 | 全部約定 |
| `7878` | buy | 100 | 100 | 0 | 全部約定 |
| `6522` | buy | 100 | 100 | 0 | 全部約定 |

Position evidence included the five accepted symbols:

- `4591`: quantity `100`, available_quantity `100`
- `6327`: quantity `100`, available_quantity `100`
- `6522`: quantity `100`, available_quantity `100`
- `6897`: quantity `100`, available_quantity `100`
- `7878`: quantity `100`, available_quantity `100`

Cash / buying power evidence:

- broker cash_available: `19,949,120`
- broker buying_power: `19,949,120`

These broker values were not copied into Runtime Current SoT because `mode=demo` capability treats broker cash and reset positions as evidence-only.

## Execution Detail Gap

Execution detail fetch failed for all 5 orders:

- detail_attempted_count: `5`
- detail_success_count: `0`
- detail_failure_count: `5`
- failure_stage: `order_detail_response`
- classification: `FAILED_BROKER_READONLY_FETCH`

This is the immediate reason the Execution Job returned `REVIEW_REQUIRED` despite Broker OrderList showing all 5 orders as filled.

## Reports

Generated artifacts:

- `reports/runtime_v2/2026-07-08/runtime_report.json`
- `reports/runtime_v2/2026-07-08/runtime_report.md`
- `reports/public/runtime_v2/2026-07-08/public_report.md`
- `reports/public/runtime_v2/latest.md`
- `reports/public/runtime_v2/latest.json`
- `reports/runtime_v2/2026-07-08/audit_result.json`
- `reports/runtime_v2/2026-07-08/notification_payload.json`

Public Report summary:

- Runtime mode: `demo`
- Runtime state: `CURRENT_STATE_LOADED`
- Cash: `JPY 1,000,000`
- Buying power: `JPY 1,000,000`
- Holdings: no active Runtime Current positions
- Order statuses: `accepted=5`, `filled=5`, `rejected_or_unknown=10`
- Reconcile: `PASS`
- Audit: `PASS`

Operational note:

The Public Report is generated from Runtime Current / Ledger artifacts and remains redaction-safe. The authoritative operational outcome for E22 is still the Execution manifest final state: `REVIEW_REQUIRED`.

## Acceptance Review

| Acceptance Item | Result |
| --- | --- |
| New Morning executed | PASS |
| New Pending generated | PASS |
| E17 consumed Pending not reused | PASS |
| Submit Job executed through normal Runtime v2 path | PASS |
| Demo Broker Submit executed | PASS |
| Broker ACCEPT/REJECT evidence recorded | PASS |
| accepted_count recorded | PASS: `5` |
| rejected_count recorded | PASS: `0` |
| sResultCode recorded | PASS: `0` for all accepted items |
| Broker OrderList ReadOnly executed | PASS |
| OrderList confirmed filled orders | PASS |
| Ledger updated | PASS |
| Asset Current not overwritten by Demo broker reset values | PASS |
| Runtime/Public Report generated | PASS |
| Audit generated | PASS |
| Notification actual send avoided | PASS |
| Production order avoided | PASS |
| launchd unchanged | PASS |
| Morning to Report fully PASS without REVIEW_REQUIRED | FAIL: Execution returned `REVIEW_REQUIRED` |

## Next Required Work

1. Review whether `CLMOrderListDetail` failure should remain a hard Execution ReadOnly failure when `CLMOrderList + Position + Cash` evidence is present and consistent.
2. Reconcile the mismatch between Execution manifest `reconcile_status=REVIEW_REQUIRED` and the generated Runtime/Public Report `Reconcile=PASS`.
3. Decide whether Demo Capability should treat filled OrderList + Position evidence as sufficient to clear REVIEW_REQUIRED for Demo operations.
4. Keep Current SoT at the 1,000,000 JPY Demo Operation baseline unless Asset writer policy is explicitly updated.

## Final Judgment

`PHASE14E22_REVIEW_REQUIRED`

