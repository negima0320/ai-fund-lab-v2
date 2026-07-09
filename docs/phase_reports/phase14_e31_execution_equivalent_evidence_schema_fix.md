# Phase14-E31 Runtime v2 Execution-equivalent Evidence Schema Fix

## Summary

Phase14-E31 fixed the execution evidence schema ambiguity identified in E27.

Final judgment: `PHASE14E31_EXECUTION_EQUIVALENT_SCHEMA_FIXED`

Before E31, Runtime v2 could accept execution using OrderList + Position + Cash evidence while `.runtime/persistent_ledger/executions.jsonl` remained empty when `CLMOrderListDetail` failed. That made downstream consumers unable to tell from the canonical execution ledger whether a fill had occurred.

E31 adds canonical `execution_equivalent` records to `executions.jsonl` when:

- OrderList shows full fill.
- Position evidence exists for the filled symbol.
- Cash / buying power evidence exists.
- Order detail is optional and may be missing/failed.

No additional Submit, SELL Submit, Production order, Production Broker API Write, Notification actual send, launchd change, Phase9 Runtime, Phase9 writer, Current initialization, or Demo Broker 20M cash copy was performed.

## Execution Schema Contract

Runtime v2 execution ledger records are now classified by `execution_evidence_type`.

| Type | Meaning | Source |
| --- | --- | --- |
| `broker_detail_execution` | Execution detail from Broker detail API such as `CLMOrderListDetail` | detail API evidence |
| `execution_equivalent` | Runtime canonical fill-equivalent record built from OrderList full fill + Position + Cash evidence | `CLMOrderList`, `CLMGenbutuKabuList`, `CLMZanKaiSummary`, `CLMZanKaiKanougaku` |

The E31 implementation adds `execution_equivalent`.

## Execution-equivalent Fields

Each `execution_equivalent` record includes:

- `schema_version`
- `record_type = execution`
- `execution_evidence_type = execution_equivalent`
- `business_date`
- `environment`
- `mode`
- `symbol`
- `broker_issue_code`
- `side`
- `quantity`
- `filled_quantity`
- `remaining_quantity`
- `order_status`
- `execution_status = filled`
- `price_source = position_evidence`
- `average_price`
- `market_price`
- `market_value`
- `cash_effect`
- `source_order_hash`
- `source_broker_order_hash`
- `source_position_hash`
- `evidence_refs`
- `detail_required = false`
- `detail_status`
- `review_required`
- `created_at`

Raw request, raw response, secret values, and plaintext broker IDs are not saved.

## Detail Policy

`CLMOrderListDetail` remains optional evidence.

If detail retrieval fails but OrderList + Position + Cash evidence is consistent:

- Execution Acceptance: `PASS`
- `detail_required`: `false`
- `detail_status`: `OPTIONAL_FAILED` or `OPTIONAL_EVIDENCE_MISSING`
- Ledger execution record: created as `execution_equivalent`

If Position evidence is missing, the pipeline remains `REVIEW_REQUIRED`.

## Before State

Before E31:

- `.runtime/persistent_ledger/executions.jsonl`: 0 records
- OrderList: 5 filled orders
- Position evidence: 5 Runtime-owned symbols present
- Cash / buying power evidence: present
- Report showed fills from order history but not from execution ledger

## After State

After E31 re-evaluation using saved E22/E23/E25/E30 artifacts:

- `.runtime/persistent_ledger/executions.jsonl`: 5 records
- All 5 records have `execution_evidence_type=execution_equivalent`
- Public Report shows `Execution-equivalent count: 5`
- `latest.json` includes `today_operation.execution_equivalent_count=5`
- Notification payload includes `scoped_summary.today_operation.execution_equivalent_count=5`
- Reconcile accepts `execution_equivalent` as canonical execution evidence

## Execution-equivalent Records

| Symbol | Side | Quantity | Filled | Remaining | Average Price | Market Value | Detail Status |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `4591` | BUY | 100 | 100 | 0 | 102 | 7,700 | `OPTIONAL_FAILED` |
| `6327` | BUY | 100 | 100 | 0 | 102 | 514,000 | `OPTIONAL_FAILED` |
| `6897` | BUY | 100 | 100 | 0 | 102 | 67,700 | `OPTIONAL_FAILED` |
| `7878` | BUY | 100 | 100 | 0 | 102 | 155,400 | `OPTIONAL_FAILED` |
| `6522` | BUY | 100 | 100 | 0 | 102 | 235,000 | `OPTIONAL_FAILED` |

Evidence refs:

- `CLMOrderList`
- `CLMGenbutuKabuList`
- `CLMZanKaiSummary`
- `CLMZanKaiKanougaku`

## Report Updates

Runtime/Public Report now includes:

- Today's Operation Summary:
  - `Execution-equivalent count: 5`
- Ledger History Summary:
  - `Cumulative executions/equivalent executions: 5`
  - `Execution-equivalent records: 5`

## Notification Payload Updates

Notification remains payload-only and send-disabled.

The generated notification payload now includes:

- `scoped_summary.today_operation.execution_equivalent_count = 5`
- `scoped_summary.ledger_history.execution_equivalent_count = 5`

## Reconcile Updates

Reconcile no longer treats `execution_equivalent` records as missing broker detail evidence when Broker detail executions are absent.

`execution_equivalent` is valid canonical evidence for:

- Report
- Notification
- Reconcile
- Future SELL / performance / exposure consumers

## Code Changes

Changed:

- `src/ai_fund_lab_v2/runtime_v2/ledger/models.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/ledger_projection.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/reconcile/checks.py`
- `src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py`
- `tests/runtime_v2/test_phase14e23_execution_acceptance_policy.py`
- `tests/runtime_v2/test_phase14e6_runtime_v2_public_report_output.py`

Generated/updated:

- `.runtime/persistent_ledger/executions.jsonl`
- `reports/runtime_v2/2026-07-08/runtime_report.md`
- `reports/runtime_v2/2026-07-08/runtime_report.json`
- `reports/runtime_v2/2026-07-08/notification_payload.json`
- `reports/runtime_v2/2026-07-08/audit_result.json`
- `reports/public/runtime_v2/2026-07-08/public_report.md`
- `reports/public/runtime_v2/2026-07-08/public_report.json`
- `reports/public/runtime_v2/latest.md`
- `reports/public/runtime_v2/latest.json`

## Verification

Targeted tests:

```text
PYTHONPYCACHEPREFIX=/tmp/phase14e31_pycache python3 -m pytest tests/runtime_v2/test_phase14e23_execution_acceptance_policy.py tests/runtime_v2/test_phase14e21_execution_readonly_pipeline.py tests/runtime_v2/test_phase14e6_runtime_v2_public_report_output.py
```

Result:

```text
6 passed
```

Runtime v2 full tests:

```text
PYTHONPYCACHEPREFIX=/tmp/phase14e31_pycache python3 -m pytest tests/runtime_v2
```

Result:

```text
329 passed
```

Existing artifact re-evaluation:

```text
PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/phase14e31_pycache python3 -c '...run_execution_readonly_pipeline(...saved snapshot...)'
```

Result:

- status: `PASS`
- ledger_executions_appended: `5`
- execution_equivalent_count: `5`
- order_detail_status: `OPTIONAL_FAILED`
- reconcile_status: `PASS_WITH_WARNINGS`

Report regeneration:

- Redaction scan: `PASS`
- Notification send: `false`
- Broker API called: `false`

## Acceptance Review

| Acceptance Item | Result |
| --- | --- |
| execution_equivalent schema明文化 | PASS |
| executions.jsonlに約定相当record保存 | PASS |
| OrderListDetail optional方針と矛盾しない | PASS |
| BUY/SELL両方で使えるschema | PASS |
| Reportがexecution_equivalent表示 | PASS |
| Notification payloadがexecution_equivalentを含む | PASS |
| Reconcileがexecution_equivalentを扱う | PASS |
| 追加Submitなし | PASS |
| Production注文なし | PASS |
| Notification実送信なし | PASS |
| tests/runtime_v2 PASS | PASS |

## Final Judgment

`PHASE14E31_EXECUTION_EQUIVALENT_SCHEMA_FIXED`
