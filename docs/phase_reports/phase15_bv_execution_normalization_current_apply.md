# Phase15-BV Execution Normalization Ledger and Current Apply Acceptance

## Executive Summary

Final judgment:

```text
CURRENT_APPLY_ACCEPTED_DEMO_ONLY
```

BUでAcceptanceした `DEMO_ORDERLIST_POSITION_EXECUTION_EQUIVALENT_FALLBACK_V1` をSourceとして、隔離Runtime `.runtime_acceptance_phase15_demo_reinit` にExecution Normalization、Ledger Append、Current Projection、Current Apply、Runtime State更新を実施した。

Production Sourceへの切替、新規Broker Write、ReSubmit、Auto Cancel、Notification Send、Production Write、既存 `.runtime` 変更は実施していない。

## Execution Normalization

Artifact:

```text
reports/phase_reports/phase15_bv/execution_normalization.json
```

| Field | Value |
|---|---|
| execution_id | `phase15bv-demo-execution-equivalent-6501-sell-100` |
| issue_code | `6501` |
| side | `SELL` |
| quantity | `100` |
| execution_price | `100 JPY` |
| execution_date | `2026-07-12` |
| execution_source | `DEMO_ORDERLIST_POSITION_EXECUTION_EQUIVALENT_FALLBACK_V1` |
| broker_order_hash | `sha256:b80b43eeb157caa8a56c14684356cbbd0b9cddebc05905a49059f72e4861d153` |
| request_hash | `sha256:56ebea4e14ffe7369f133260645720c49303711b74c21960973e833016b37f70` |
| execution_equivalent | `true` |
| production_equivalent | `false` |
| valuation_price | `4700 JPY` |
| valuation_price_used_as_execution_price | `false` |

Execution価格はDemo Browser Confirmationの `100 JPY` を使用した。評価価格 `4700 JPY` はExecution価格に使用していない。

## Ledger Append

Ledger files under:

```text
.runtime_acceptance_phase15_demo_reinit/persistent_ledger/
```

Appended records:

| File | Count | Record |
|---|---:|---|
| `orders.jsonl` | `1` | `ledger-order-phase15bv-6501-sell-100` |
| `executions.jsonl` | `1` | `ledger-execution-phase15bv-6501-sell-100` |
| `positions.jsonl` | `1` | `ledger-position-phase15bv-6501-after-sell` |
| `cash.jsonl` | `1` | `ledger-cash-phase15bv-after-sell` |
| `events.jsonl` | `1` | `ledger-event-phase15bv-current-apply` |

Dedup keyで二重追加を防止した。

## Current Projection

Artifact:

```text
reports/phase_reports/phase15_bv/current_projection.json
```

| Item | Before | After |
|---|---:|---:|
| 6501 quantity | `200` | `100` |
| Cash | `17,694,424` | `17,704,424` |
| Cash delta |  | `+10,000` |
| Buying power |  | `20,009,824` |
| Market value | `940,000` | `470,000` |
| Portfolio value | `18,634,424` | `18,174,424` |

Current Scope is `phase15bv_6501_acceptance_current_scope`. Demo account全体の初期保有はCurrentへコピーしていない。

## Current Apply

Current path:

```text
.runtime_acceptance_phase15_demo_reinit/persistent_ledger/state.json
```

| Field | Value |
|---|---|
| current_version | `phase15bv_current_v1` |
| current_hash | `sha256:11cadb1bdda853fee9bef405acb951a5273848b0488d3c1c6ef007e1053b8bc4` |
| position_state_as_of | `2026-07-12` |
| valuation_as_of | `2026-07-13` |
| source_market_date | `2026-07-13` |
| 6501 quantity | `100` |
| cash | `17,704,424` |
| buying_power | `20,009,824` |
| market_value | `470,000` |
| total_equity | `18,174,424` |
| production_equivalent | `false` |

Browser確認の `6501 100株` とCurrent数量は一致している。

## Runtime State

Runtime State path:

```text
.runtime_acceptance_phase15_demo_reinit/runtime_state/current_state.json
```

| Field | Value |
|---|---|
| state | `CURRENT_APPLIED` |
| runtime_state_version | `phase15bv_runtime_state_v1` |
| current_pointer | `.runtime_acceptance_phase15_demo_reinit/persistent_ledger/state.json` |
| current_version | `phase15bv_current_v1` |
| current_hash | `sha256:11cadb1bdda853fee9bef405acb951a5273848b0488d3c1c6ef007e1053b8bc4` |
| execution_reference | `phase15bv-demo-execution-equivalent-6501-sell-100` |
| runtime_state_hash | `sha256:130f5eb8f61ba0756525cbeaad2e5308238d0c30bf1d927e390e4ee4a1d5eceb` |

## Pending

Pending path:

```text
.runtime_acceptance_phase15_demo_reinit/pending_order_plan/pending_order_plan.json
```

| Field | Value |
|---|---|
| state | `CONSUMED` |
| consumed | `true` |
| consume_reason | `phase15bv_execution_normalization_ledger_current_apply_completed` |
| submitted_order_ids | `sha256:b80b43eeb157caa8a56c14684356cbbd0b9cddebc05905a49059f72e4861d153` |
| ledger_order_record_ids | `ledger-order-phase15bv-6501-sell-100` |

## Idempotency

BV apply was executed twice.

Attempt 1:

| Item | Value |
|---|---|
| status | `APPLIED` |
| ledger_records_appended | `5` |
| current_hash_changed | `true` |
| current_hash_after | `sha256:11cadb1bdda853fee9bef405acb951a5273848b0488d3c1c6ef007e1053b8bc4` |
| 6501 quantity after | `100` |
| cash after | `17,704,424` |

Attempt 2:

| Item | Value |
|---|---|
| status | `NOOP_ALREADY_APPLIED` |
| ledger_records_appended | `0` |
| idempotent | `true` |
| current_hash before | `sha256:11cadb1bdda853fee9bef405acb951a5273848b0488d3c1c6ef007e1053b8bc4` |
| current_hash after | `sha256:11cadb1bdda853fee9bef405acb951a5273848b0488d3c1c6ef007e1053b8bc4` |
| 6501 quantity after | `100` |
| cash after | `17,704,424` |

This proves:

- Ledger二重追加なし。
- Execution二重反映なし。
- Current二重更新なし。
- Position `100 -> 0` なし。
- Cash二重増加なし。

## Existing Runtime Preservation

Existing `.runtime` hashes remained:

| Path | SHA-256 |
|---|---|
| `.runtime/pending_order_plan/pending_order_plan.json` | `84075f23cc6d1c5ae227de1bfe4a213221aefd131fdadb395058755601ac2c77` |
| `.runtime/runtime_state/safety/latest_safety_decision.json` | `c4c1019497fc47b245ad92f21b0b06d59abe32e449f026eb0f9b0aed112faeb7` |
| `.runtime/persistent_ledger/state.json` | `add4f37373c6f7331b6894b29322ffd39a6a0c911086150427d57a2ddb442b0f` |

## Regression

Regression test:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase15bv_execution_normalization_current_apply.py
```

Coverage:

- Execution Price is `100`.
- Valuation Price is `4700`.
- Production equivalent remains `false`.
- Ledger has one record per target file.
- Current quantity is `100`.
- Cash / buying power / portfolio are updated.
- Runtime State points to the new Current hash.
- Second apply is idempotent.
- Notification and Broker Write remain false.

## Prohibited Action Audit

| Action | Performed |
|---|---|
| New Broker Write | `false` |
| ReSubmit | `false` |
| Auto Cancel | `false` |
| Notification Send | `false` |
| Production Write | `false` |
| Existing `.runtime` mutation | `false` |

## Remaining Blockers

None for Demo-only Current Apply acceptance.

## Next Prefix

Recommended next prefix:

```text
Phase15-BW
Runtime End-to-End Daily System Test Review
```
