# Phase14-E23 Execution Acceptance Policy Fix

## Summary

Phase14-E23 fixed the Runtime v2 Execution ReadOnly acceptance policy so that `CLMOrderListDetail` / order detail evidence is optional, matching the Phase14-D10 evidence policy.

Final judgment: `PHASE14E23_EXECUTION_ACCEPTANCE_POLICY_FIXED`

The E22 evidence was re-evaluated without any additional Submit:

- Broker Submit evidence: `accepted_count=5`
- Broker OrderList evidence: all 5 orders were `全部約定`
- Position evidence: all 5 accepted BUY symbols had quantity evidence
- Cash / buying power evidence: present
- Current SoT: not overwritten by Demo broker cash / positions
- Detail API evidence: unavailable, now classified as optional warning

Execution acceptance now passes when OrderList + Position + Cash are consistent, even if order detail fetch fails.

## Prohibited Actions

| Action | Result |
| --- | --- |
| Additional Submit | Not executed |
| Production order | Not executed |
| Production Broker API Write | Not executed |
| Notification actual send | Not executed |
| launchd change | Not executed |
| Phase9 Runtime | Not used |
| Phase9 Writer | Not used |
| `.runtime/demo` Current path | Not used |
| Raw request / raw response / secret保存 | Not saved |

## Implementation

Updated Runtime v2 Execution ReadOnly policy:

- `OrderList` is required execution evidence.
- Filled orders must be fully filled:
  - `order_status=filled`
  - `filled_quantity > 0`
  - `remaining_quantity = 0`
- BUY fills require matching Position evidence.
- Cash / buying power evidence is required.
- `CLMOrderListDetail` is not required.
- Detail failure becomes:
  - `order_detail_required=false`
  - `order_detail_status=OPTIONAL_FAILED`
  - `execution_acceptance_warnings=["order_detail_optional_missing"]`
- If OrderList / Position / Cash evidence is missing or inconsistent, Execution remains `REVIEW_REQUIRED`.
- Demo broker cash / positions are recorded as evidence only and do not overwrite Runtime Asset Current SoT.

Updated files:

- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py`
- `tests/runtime_v2/test_phase14e23_execution_acceptance_policy.py`

## Manifest Details

The Execution ReadOnly pipeline now records:

- `orderlist_readonly_connected`
- `positions_evidence_connected`
- `cash_evidence_connected`
- `order_detail_required`
- `order_detail_status`
- `execution_acceptance_status`
- `execution_acceptance_reason`
- `execution_acceptance_warnings`

E22 re-evaluation result:

| Field | Value |
| --- | --- |
| status | `PASS` |
| snapshot_status | `FAILED_BROKER_READONLY_FETCH` |
| orders_count | `5` |
| executions_count | `0` |
| positions_count | `12` |
| cash_present | `true` |
| asset_current_written | `false` |
| reconcile_status | `PASS_WITH_WARNINGS` |
| reconcile_findings | `13` |
| order_detail_required | `false` |
| order_detail_status | `OPTIONAL_FAILED` |
| execution_acceptance_status | `PASS` |
| execution_acceptance_reason | `orderlist_position_cash_evidence_accepted` |

The raw snapshot status remains visible as `FAILED_BROKER_READONLY_FETCH`, but Runtime v2 acceptance no longer treats detail-only failure as fatal when the required evidence set is complete.

## E22 Evidence Re-evaluation

E22 Broker OrderList evidence:

| Broker Issue Code | Side | Quantity | Executed Quantity | Remaining Quantity | Status |
| --- | --- | ---: | ---: | ---: | --- |
| `4591` | buy | 100 | 100 | 0 | 全部約定 |
| `6327` | buy | 100 | 100 | 0 | 全部約定 |
| `6897` | buy | 100 | 100 | 0 | 全部約定 |
| `7878` | buy | 100 | 100 | 0 | 全部約定 |
| `6522` | buy | 100 | 100 | 0 | 全部約定 |

Matching Position evidence:

- `4591`: quantity `100`
- `6327`: quantity `100`
- `6522`: quantity `100`
- `6897`: quantity `100`
- `7878`: quantity `100`

Cash / buying power evidence:

- broker cash_available: present
- broker buying_power: present

Current SoT after re-evaluation:

- cash: `1,000,000`
- buying_power: `1,000,000`
- market_value: `0`
- total_equity: `1,000,000`
- positions: `[]`
- source: `phase14e8_demo_operation_initial_state`

## Report / Public Report / Audit

The policy warning is now preserved as an INFO Ledger event and appears in derived reports.

Ledger event:

- event_type: `order_detail_optional_missing`
- severity: `INFO`
- message: Order detail evidence was optional and unavailable; OrderList, Position, and Cash evidence were used for execution acceptance.

Generated reports:

- `reports/runtime_v2/2026-07-08/runtime_report.json`
- `reports/runtime_v2/2026-07-08/runtime_report.md`
- `reports/public/runtime_v2/2026-07-08/public_report.md`
- `reports/public/runtime_v2/latest.md`
- `reports/runtime_v2/2026-07-08/audit_result.json`

Public Report now includes:

- `detail_optional_missing is acceptable when OrderList, Position, and Cash evidence are consistent.`
- `order_detail_optional_missing warning recorded; execution acceptance used OrderList, Position, and Cash evidence.`

Audit JSON also includes the same safe notes.

## Acceptance Review

| Acceptance Item | Result |
| --- | --- |
| CLMOrderListDetail失敗だけではREVIEW_REQUIREDにしない | PASS |
| OrderListで全部約定ならExecution evidenceとして使う | PASS |
| Position evidenceでBUY保有確認 | PASS |
| Cash / buying_power evidence確認 | PASS |
| Detail failureをwarning/audit noteとして残す | PASS |
| OrderList / Position / Cash不足時はREVIEW_REQUIRED | PASS |
| Demo Broker cash/positionsをCurrent SoTへ上書きしない | PASS |
| E22状態を追加Submitなしで再評価 | PASS |
| Runtime/Public ReportにExecution warning反映 | PASS |
| AuditにExecution warning反映 | PASS |
| tests/runtime_v2 PASS | PASS: `326 passed` |
| Production注文なし | PASS |
| Notification実送信なし | PASS |

## Verification

Commands:

- `python3 -m pytest tests/runtime_v2/test_phase14e21_execution_readonly_pipeline.py tests/runtime_v2/test_phase14e23_execution_acceptance_policy.py tests/runtime_v2/test_phase14e6_runtime_v2_public_report_output.py` -> `6 passed`
- `python3 -m pytest tests/runtime_v2` -> `326 passed`

E22 re-evaluation used the existing snapshot:

- `.runtime/runtime_state/broker_readonly/2026-07-08/tachibana_snapshot.json`
- `.runtime/runtime_state/broker_readonly/2026-07-08/snapshot_report.json`

No Broker Submit or Broker Write was executed during E23.

## Final Judgment

`PHASE14E23_EXECUTION_ACCEPTANCE_POLICY_FIXED`

