# Phase15-BU Demo Broker Write Post-Send Execution Evidence Review

## Executive Summary

Final judgment:

```text
EXECUTION_EQUIVALENT_READY_DEMO_ONLY
```

Phase15-BT's Tachibana Demo broker write is accepted as Demo-only execution-equivalent evidence. The authority is not `CLMOrderListDetail`; that detail endpoint still fails. The authority is the combined evidence:

- Broker submit response: `ACCEPTED`
- Request hash match: `sha256:56ebea4e14ffe7369f133260645720c49303711b74c21960973e833016b37f70`
- Order List: `6501 SELL 100`, `全部約定`, `executed_quantity=100`, `remaining_quantity=0`
- Position Inventory: `6501 200 -> 100`
- Cash / Buying Power: fresh Broker API evidence
- Browser confirmation reported by the operator: full fill, 100 shares, remaining 0, position 100

This closes the Phase15-BT blocker for Demo acceptance. It does not authorize Production fallback and does not perform Execution Normalization, Ledger Append, Current Apply, Notification Send, or any new Broker Write.

## Root Cause

Execution Detail failure classification:

```text
DEMO_API_UNSUPPORTED
```

Evidence:

| Item | Value |
|---|---|
| API | `CLMOrderListDetail` |
| Request parameter | `sOrderNumber` |
| Order hash | `order_b80b43eeb157caa8` |
| Login / session | `PASS` |
| Order List | `PASS` |
| Position List | `PASS` |
| Cash / Buying Power | `PASS` |
| Detail failure stage | `order_detail_response` |
| Response code present | `true` |
| Response code zero | `false` |
| Safe error class | `BrokerResponseEnvelope` |

The ReadOnly retry command was executed after BT and still failed only at `CLMOrderListDetail`:

```bash
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --mode demo --job broker_readonly_refresh --business-date 2026-07-13 --submit-enabled false --notification-mode payload-only --runtime-root .runtime_acceptance_phase15_demo_reinit --reports-root reports/phase_reports/phase15_bu/runtime_v2_readonly_retry --public-reports-root reports/phase_reports/phase15_bu/public_runtime_v2_readonly_retry --manifest-root .runtime_acceptance_phase15_demo_reinit/runtime_state/run_manifest --log-root .runtime_acceptance_phase15_demo_reinit/runtime_state/logs
```

Retry result:

| Item | Value |
|---|---|
| exit_code | `20` |
| snapshot_status | `FAILED_BROKER_READONLY_FETCH` |
| refresh_status | `REVIEW_REQUIRED` |
| data_origin | `BROKER_API` |
| fixture_used | `false` |
| mock_used | `false` |
| broker_write_executed | `false` |
| execution_processing_executed | `false` |
| ledger_appended | `false` |
| current_position_apply_executed | `false` |

Because raw order numbers and raw responses are intentionally not saved, `REQUEST_PARAMETER_ERROR`, `ENDPOINT_SELECTION_ERROR`, and `ORDER_ID_MAPPING_ERROR` cannot be fully eliminated. However, the stable success of Order List / Position / Cash plus repeated detail-only non-zero response makes `DEMO_API_UNSUPPORTED` the operational root cause for Phase15-BU.

## Order List Authority

Order List has the following authority:

| Authority | Status | Reason |
|---|---|---|
| Order Accepted Evidence | `PASS` | Broker submit returned `ACCEPTED`, and Order List shows the submitted order hash. |
| Order Status Evidence | `PASS` | `status=全部約定`. |
| Execution-equivalent Evidence | `PASS_DEMO_ONLY` | `executed_quantity=100`, `remaining_quantity=0`, corroborated by Position difference and Cash/Buying Power evidence. |
| Execution Detail Evidence | `FAIL` | `CLMOrderListDetail` returned a non-zero response. |

Order List alone is not sufficient for Current apply. It becomes Demo-only execution-equivalent only when combined with the position difference and the BT request/authorization hash.

## Position Difference Authority

Position Inventory authority:

| Check | Result |
|---|---|
| Before quantity | `200` |
| After quantity | `100` |
| Difference | `-100` |
| SELL quantity | `100` |
| Quantity difference matches SELL | `PASS` |
| Same broker order matched | `PASS` |
| Open conflicting order | `NONE` |
| Demo reset detected | `false` |
| Fresh Broker API evidence | `PASS` |

The position difference is accepted as corroboration, not as standalone execution evidence.

## Price Authority

The prices must not be mixed:

| Price | Value | Authority | Use |
|---|---:|---|---|
| Execution Price | `100 JPY` | Operator browser confirmation | Demo-only execution-equivalent normalization candidate. |
| Market Price | `4700 JPY` | Broker Position Inventory / valuation evidence | Valuation only. |
| Valuation Price | `4700 JPY` | Broker Current valuation field | Current valuation only, not execution price. |
| Demo Price | `100 JPY` | Tachibana Demo browser execution screen | Demo-only accepted fill price. |

Execution Normalization must not use `4700 JPY` as the execution price for this fill. In BV, normalization may proceed only if the Demo fallback contract explicitly accepts the attested browser execution price `100 JPY` as Demo-only fill price, or if a machine-readable supported execution detail appears.

## Session Translation

Runtime and Broker dates differ:

| Field | Value |
|---|---|
| Runtime target session | `2026-07-13` |
| Runtime business date | `2026-07-13` |
| Broker order datetime | `20260712100459` |
| Broker order date | `2026-07-12` |
| Browser order time | `2026-07-12 10:04 JST` |
| Execution date | `2026-07-12` |

Demo session translation contract:

```text
DEMO_SESSION_TRANSLATION_CONTRACT
```

For Tachibana Demo acceptance only, a Sunday Broker accept/execution timestamp may map to the Runtime target session when all of the following are true:

- The human authorization explicitly names the target session.
- Request hash matches.
- Broker submit is accepted.
- Order List confirms full fill.
- Position Inventory confirms the quantity impact.
- The report marks the evidence as Demo-only and not production-equivalent.

This translation is not valid for Production.

## Evidence Authority Decision

Selected option:

```text
B
Order List + Position difference establishes execution-equivalent evidence
```

Rejected options:

| Option | Reason |
|---|---|
| A: Execution Detail mandatory | Too strict for Tachibana Demo acceptance when Order List, Position, Cash, and browser evidence agree; also contradicts existing Runtime execution-equivalent design. |
| C: Order List only | Insufficient because full-fill status must be corroborated. |
| D: Position difference only | Insufficient because position change must link to the submitted broker order. |
| E: Evidence insufficient | Rejected for Demo because independent evidence sources agree. |

## Demo Fallback Contract

Contract:

```text
DEMO_ORDERLIST_POSITION_EXECUTION_EQUIVALENT_FALLBACK_V1
```

Scope:

```text
Tachibana Demo acceptance only
```

Required conditions:

| Condition | BT/BU Status |
|---|---|
| Broker Write success | `PASS` |
| Request Hash match | `PASS` |
| Order Number / order hash match | `PASS` |
| Order List `全部約定` | `PASS` |
| Executed Quantity match | `PASS` |
| Remaining Quantity zero | `PASS` |
| Position difference match | `PASS` |
| Open Order none or same filled order only | `PASS` |
| Business Date consistency or Demo Session Translation | `PASS` |
| Fresh Evidence | `PASS` |
| Fallback reason recorded | `PASS` |

Fallback reason:

```text
CLMOrderListDetail is unavailable in the Demo ReadOnly path while independent Broker API Order List, Position Inventory, Cash/Buying Power, and operator browser confirmation agree on full fill and quantity impact.
```

## Production Boundary

The Demo fallback must not be promoted to Production.

Production requires one of:

- Broker-supported machine-readable execution detail.
- Formal production execution report contract.
- Explicit production-grade reconciliation contract approved before use.

For Production, Order List + Position difference can be supporting evidence, but not the sole authority for execution price or final ledger/current application.

## Runtime Submit Path

BT used:

```text
RuntimeV2TachibanaDemoSubmitAdapter(dry_run=false).submit
```

Assessment:

- Acceptable only for BT's explicitly authorized, single Demo broker write boundary.
- Do not keep the direct adapter route as the normal Runtime path.
- Production and normal Demo Submit must return to the regular Submit Pipeline.
- BV may consume the BU execution-equivalent authority, but must still pass through the normal Execution Normalization / Ledger / Current acceptance path.

## Pending State

Current pending state:

| Field | Value |
|---|---|
| state | `SUBMITTED` |
| consumed | `false` |
| current_updated | `false` |
| resubmit_allowed | `false` |

Assessment:

```text
VALID_UNTIL_EXECUTION_NORMALIZATION_AND_LEDGER_APPLY
```

The Pending state is correct. The order was submitted and accepted, but Execution Normalization and Current Apply have not happened, so the Pending must not be treated as consumed yet.

## Prohibited Action Audit

| Action | Performed |
|---|---|
| New Broker Write | `false` |
| ReSubmit | `false` |
| Auto Cancel | `false` |
| Execution Normalization | `false` |
| Ledger Append | `false` |
| Current Apply | `false` |
| Notification Send | `false` |
| Production Write | `false` |
| Existing `.runtime` mutation | `false` |

## Regression

Regression test:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase15bu_demo_broker_write_post_send_execution_evidence_review.py
```

Coverage:

- Execution Detail failure remains isolated to `CLMOrderListDetail`.
- Order List full-fill evidence is present.
- Position difference matches `SELL 100`.
- Demo fallback conditions pass.
- Production applicability is false.
- Pending remains `SUBMITTED` and unconsumed.
- Current Apply / Ledger Append / Execution Normalization / Notification remain false.
- New Broker Write and ReSubmit remain false.

## Artifacts

| Artifact | Path |
|---|---|
| Markdown report | `docs/phase_reports/phase15_bu_demo_broker_write_post_send_execution_evidence_review.md` |
| JSON report | `reports/phase_reports/phase15_bu_demo_broker_write_post_send_execution_evidence_review.json` |
| Authority evidence | `reports/phase_reports/phase15_bu/execution_evidence_authority.json` |
| ReadOnly retry report | `reports/phase_reports/phase15_bu/runtime_v2_readonly_retry/2026-07-13/runtime_report.json` |
| ReadOnly retry public report | `reports/phase_reports/phase15_bu/public_runtime_v2_readonly_retry/2026-07-13/public_report.json` |
| Latest broker snapshot | `.runtime_acceptance_phase15_demo_reinit/runtime_state/broker_readonly/2026-07-13/tachibana_snapshot.json` |

## Remaining Blockers

No blocker remains for Demo-only execution-equivalent acceptance.

Blocked until BV:

- Execution Normalization
- Ledger Append
- Current Apply
- Notification

## Next Prefix

Recommended next prefix:

```text
Phase15-BV
Execution Normalization Ledger and Current Apply Acceptance
```
