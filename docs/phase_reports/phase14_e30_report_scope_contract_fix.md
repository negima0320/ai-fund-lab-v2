# Phase14-E30 Runtime v2 Report Scope Contract Fix

## Summary

Phase14-E30 fixed the Report scope ambiguity found in E27.

Final judgment: `PHASE14E30_REPORT_SCOPE_CONTRACT_FIXED`

Before E30, Runtime/Public Report could display cumulative Ledger orders in a way that looked like the current day's operation result. That made these scopes easy to confuse:

- Current holdings
- Today's operation result
- Current run result
- Cumulative Ledger history
- Pending / Approval state
- Warnings / Audit / Notification status

E30 separates these scopes in Runtime Report JSON, Public Report Markdown, `latest.md`, `latest.json`, and notification payload summary.

No additional Submit was executed. No Production order, Notification actual send, launchd change, Phase9 Runtime, Phase9 writer, Current modification, raw request/response/secret persistence, or Demo Broker 20M cash copy was performed.

## Report Scope Contract

| Scope | Meaning | Source |
| --- | --- | --- |
| Current Portfolio | Current SoT only | `.runtime/persistent_ledger/state.json` |
| Today's Operation Summary | Latest Pending/run-related business-date operation result | Pending + Ledger records filtered by business_date and current pending context |
| Current Run Summary | Latest runtime state/run metadata if available | `.runtime/runtime_state/current_state.json` |
| Ledger History Summary | Cumulative historical Ledger records only | `.runtime/persistent_ledger/*.jsonl` |
| Pending / Approval | Current Pending state and approval counts | `.runtime/pending_order_plan/pending_order_plan.json` |
| Warnings / Known Gaps | Operational warnings and known optional evidence notes | Ledger events + report policy |
| Notification | Payload-only/send status | generated notification payload artifact |

## Before Report Problem

The old Public Report showed aggregate order counts as plain `Orders` / `BUY / SELL Result`. Since these values came from cumulative `orders.jsonl`, old rejected attempts could be misread as today's or current-run rejects.

The concrete E30 case:

- Current accepted operation: 5 accepted / 5 filled
- Historical rejected attempts: 10
- Old report risk: cumulative rejected history could be interpreted as today's rejection

## After Report Sections

Public Report now renders:

1. `Current Portfolio`
2. `Current Holdings`
3. `Today's Operation Summary`
4. `Current Run Summary`
5. `Ledger History Summary`
6. `Pending / Approval`
7. `Reconcile / Audit`
8. `Warnings / Known Gaps`
9. `Notification`
10. `Operations Memo`

Runtime Report uses the same scope model and also includes today's scoped order table internally.

## Existing Artifact Regeneration

E30 regenerated reports from fixed Current SoT only:

- `reports/runtime_v2/2026-07-08/runtime_report.md`
- `reports/runtime_v2/2026-07-08/runtime_report.json`
- `reports/runtime_v2/2026-07-08/notification_payload.json`
- `reports/runtime_v2/2026-07-08/audit_result.json`
- `reports/public/runtime_v2/2026-07-08/public_report.md`
- `reports/public/runtime_v2/2026-07-08/public_report.json`
- `reports/public/runtime_v2/latest.md`
- `reports/public/runtime_v2/latest.json`

## Current Portfolio Summary

| Field | Value |
| --- | ---: |
| cash | 949,000 |
| buying_power | 949,000 |
| market_value | 979,800 |
| total_equity | 1,928,800 |
| position_count | 5 |

Holdings:

- `6522` quantity 100
- `7878` quantity 100
- `6897` quantity 100
- `6327` quantity 100
- `4591` quantity 100

Current Portfolio is sourced only from Current SoT.

## Today's Operation Summary

For business date `2026-07-08`, scoped to the current consumed Pending and execution-readonly fill evidence:

| Field | Value |
| --- | ---: |
| accepted_count | 5 |
| rejected_count | 0 |
| blocked_count | 0 |
| unknown_count | 0 |
| filled_count | 5 |

Execution acceptance: `PASS`

Review required: `false`

## Current Run Summary

Current runtime state artifact contains:

- run_id: present
- job: `unknown`
- exit_code: `unknown`
- final_state: `CURRENT_STATE_LOADED`

The unknown job/exit_code values are reported as current-run metadata availability, not as failure.

## Ledger History Summary

Cumulative Ledger history is now only displayed under Ledger History:

| Field | Value |
| --- | ---: |
| cumulative_orders | 20 |
| cumulative_executions | 0 |
| cumulative_positions_records | 17 |
| cumulative_cash_records | 2 |
| cumulative_rejected_history | 10 |

The 10 historical rejects are not shown as Today's rejection.

## Pending / Approval Summary

| Field | Value |
| --- | --- |
| state | `CONSUMED` |
| target_session_date | `2026-07-08` |
| consumed | `true` |
| approved_item_count | `5` |
| submitted_order_ids_count | `5` |

IDs are summarized as counts/presence flags in public output.

## Warning Summary

| Warning | Value |
| --- | --- |
| optional_order_detail_missing | `true` |
| notification_payload_only | `true` |
| demo_broker_reset_evidence_ignored | `true` |
| valuation_confidence_warning | `false` |
| report_scope_warning | `false` |

## Notification

Notification remains payload-only:

- payload_generated: `true`
- send_executed: `false`
- LINE: `send-disabled`
- Discord: `send-disabled`

The notification payload now includes `scoped_summary` with Current Portfolio, Today's Operation, Current Run, Ledger History, Pending / Approval, and Warnings.

## Redaction Scan

Public Report redaction scan: `PASS`

Forbidden markers checked include raw request/response, broker internal IDs, order IDs, pending item IDs, ledger record IDs, hashes, `.runtime/demo`, Phase9, demo ledger, and stack traces.

## Code Changes

Changed:

- `src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py`
- `tests/runtime_v2/test_phase14e6_runtime_v2_public_report_output.py`

Generated/updated:

- Runtime report artifacts under `reports/runtime_v2/2026-07-08/`
- Public report artifacts under `reports/public/runtime_v2/2026-07-08/`
- `reports/public/runtime_v2/latest.md`
- `reports/public/runtime_v2/latest.json`

## Verification

Targeted tests:

```text
PYTHONPYCACHEPREFIX=/tmp/phase14e30_pycache python3 -m pytest tests/runtime_v2/test_phase14e6_runtime_v2_public_report_output.py tests/runtime_v2/test_phase14e8_demo_broker_capability_evaluation_capital_fix.py
```

Result:

```text
13 passed
```

Runtime v2 full tests:

```text
PYTHONPYCACHEPREFIX=/tmp/phase14e30_pycache python3 -m pytest tests/runtime_v2
```

Result:

```text
329 passed
```

Report regeneration:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase14e30_pycache python3 -c '...generate_public_report_from_current(...)'
```

Result:

- Redaction scan: `PASS`
- Latest Markdown/JSON updated
- Notification payload generated, send not executed

## Acceptance Review

| Acceptance Item | Result |
| --- | --- |
| Report Scope Contract明文化 | PASS |
| Current / Today / Run / Ledger History分離 | PASS |
| Public ReportでCurrent holdings正しく表示 | PASS |
| 累積LedgerをToday resultとして誤表示しない | PASS |
| latest.md / latest.jsonへ反映 | PASS |
| Redaction scan PASS | PASS |
| tests/runtime_v2 PASS | PASS |
| 追加Submitなし | PASS |
| Production注文なし | PASS |
| Notification実送信なし | PASS |

## Final Judgment

`PHASE14E30_REPORT_SCOPE_CONTRACT_FIXED`
