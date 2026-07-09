# Phase14-E6 Runtime v2 Markdown / Public Report Output Test

## Purpose

Phase14-E6 verifies that Runtime v2 can generate human-readable Markdown and Public Report artifacts from the fixed Runtime v2 Current SoT and derived Runtime v2 report inputs.

This phase does not use Phase9 writers, Phase9 daily runtime, Broker APIs, Submit, Cancel API, Notification delivery, or launchd/plist changes.

## Inputs Used

Runtime v2 fixed Current paths were used:

- `.runtime/persistent_ledger/state.json`
- `.runtime/persistent_ledger/orders.jsonl`
- `.runtime/persistent_ledger/executions.jsonl`
- `.runtime/persistent_ledger/positions.jsonl`
- `.runtime/persistent_ledger/cash.jsonl`
- `.runtime/persistent_ledger/events.jsonl`
- `.runtime/pending_order_plan/pending_order_plan.json`
- `.runtime/runtime_state/current_state.json`

The writer does not read `.runtime/phase14d*/...` as Current and rejects `.runtime/demo/...` as a Current source.

## Implementation Summary

Added Runtime v2-native Markdown/Public Report generation:

- `src/ai_fund_lab_v2/runtime_v2/report/markdown_writer.py`
- `src/ai_fund_lab_v2/runtime_v2/report/public_report_writer.py`
- `scripts/run_phase14e6_runtime_v2_public_report_output_test.py`
- `tests/runtime_v2/test_phase14e6_runtime_v2_public_report_output.py`

The writer summarizes:

- runtime mode and business date
- cash and buying power
- positions
- BUY / SELL order counts
- filled / canceled status counts
- ledger counts
- pending state
- reconcile / safety / audit status
- notification payload summary only
- `detail_optional_missing` operational note

## Generated Artifacts

Runtime report artifacts:

- `reports/runtime_v2/2026-07-07/runtime_report.md`
- `reports/runtime_v2/2026-07-07/runtime_report.json`
- `reports/runtime_v2/2026-07-07/audit_result.json`
- `reports/runtime_v2/2026-07-07/notification_payload.json`

Public report artifacts:

- `reports/public/runtime_v2/2026-07-07/public_report.md`
- `reports/public/runtime_v2/2026-07-07/public_report.json`
- `reports/public/runtime_v2/latest.md`
- `reports/public/runtime_v2/latest.json`

## Output Summary

The generated Public Report contains:

- Cash: JPY 19,999,648
- Buying power: JPY 19,999,648
- Market value: JPY 3,298,000
- Total equity: JPY 23,297,648
- Holdings: 6501, 6502, 9984
- BUY orders: 2
- SELL orders: 1
- Order statuses: canceled=1, filled=2
- Ledger records: orders=3, executions=0, positions=7, cash=1, events=1
- Reconcile: PASS
- Audit: PASS
- Notification: payload summary only, no delivery

## Redaction / Public Safety

Public report redaction scan passed.

The Public Report does not expose:

- secrets
- raw request / raw response
- plain Broker internal IDs
- `sOrderNumber`
- private key path
- second password path
- internal stack trace
- Phase9 source artifacts
- `.runtime/phase14d*/...` Current source
- `.runtime/demo/...` Current source

The internal Runtime report lists only canonical fixed Current relative paths.

## Phase9 Boundary

Phase9 writer was not used.

Phase9 daily runtime was not called.

Phase9 artifacts were not used as Runtime v2 report source.

The new writer is Runtime v2-native and reads Runtime v2 fixed Current paths only.

## Verification

Commands run:

- `python3 scripts/run_phase14e6_runtime_v2_public_report_output_test.py --business-date 2026-07-07`
- `python3 -m pytest tests/runtime_v2/test_phase14e6_runtime_v2_public_report_output.py`
- `python3 -m pytest tests/runtime_v2`

Results:

- Phase14-E6 focused tests: 4 passed
- Runtime v2 test suite: 294 passed
- Broker API calls: none
- Submit: none
- Cancel API calls: none
- Notification delivery: none
- launchd/plist changes: none

## Acceptance Criteria

- Runtime v2 Current SoTからMarkdown Reportを生成できる: PASS
- Public Reportを生成できる: PASS
- Phase9 writerを使っていない: PASS
- Phase9 daily runtimeを呼んでいない: PASS
- Phase9 artifactをsourceにしていない: PASS
- phase番号配下artifactをCurrentとして読んでいない: PASS
- `.runtime/demo/...` をCurrentとして読んでいない: PASS
- secret / raw response / broker internal idが出力されていない: PASS
- 現金 / 買付余力 / 保有銘柄 / BUY / SELL / Reconcile / Audit が人間に読める: PASS
- NotificationはPayload summaryのみで実送信していない: PASS
- Broker API呼び出ししていない: PASS
- Submitしていない: PASS
- launchd/plist変更していない: PASS
- `tests/runtime_v2` PASS: PASS

## Final Decision

PHASE14E6_MARKDOWN_PUBLIC_REPORT_OUTPUT_PASS
