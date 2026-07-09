# Phase14-E25 Runtime v2 End-to-End Data Flow Contract & BUY Asset Projection Fix

## Summary

Phase14-E25 fixed the BUY Asset Projection gap found in E24 and formalized Runtime v2 End-to-End Data Flow Contracts at the edge level.

Final judgment: `PHASE14E25_RUNTIME_V2_DATA_FLOW_CONTRACT_FIXED`

Core result:

- Runtime-owned accepted BUY fills are now projected from Ledger Position evidence into fixed Current SoT.
- Demo broker account-wide cash and unrelated reset positions are not copied into Current.
- Current SoT now contains the five E22 filled symbols.
- Public Report now displays those five holdings and their valuation.
- Next Planning / Capital Allocation can read a non-empty Current position set and current exposure.

## Prohibited Actions

| Action | Result |
| --- | --- |
| Additional Submit | Not executed |
| SELL Submit | Not executed |
| Production order | Not executed |
| Production Broker API Write | Not executed |
| Notification actual send | Not executed |
| launchd change | Not executed |
| Phase9 Runtime | Not used |
| Phase9 Writer | Not used |
| `.runtime/demo` Current path | Not restored |
| Demo broker 20M cash copied to Current | Not copied |
| Unrelated Demo broker positions copied to Current | Not copied |
| Raw request / raw response / secret saved | Not saved |
| Test-only recovery path | Not created |

## Data Flow Completion Rule

From E25 onward, Runtime v2 phase completion must be judged by data-flow edges, not component existence.

Each edge has:

- input artifact / state
- output artifact / state
- required evidence
- PASS condition
- REVIEW_REQUIRED condition
- BLOCK condition
- forbidden shortcuts

Status labels:

- `PASS`: data reaches the next artifact/state with required evidence.
- `PARTIAL`: component exists but edge is incomplete, warning-only, or manually bridged.
- `FAIL`: expected data does not reach the next artifact/state.
- `NOT_IMPLEMENTED`: edge is not built.

## BUY Flow Matrix

| Edge | Input | Output | Required Evidence | Status | Notes |
| --- | --- | --- | --- | --- | --- |
| Feature -> AI / Planning | feature artifacts | AI signals / planning input | candidate/opportunity/capital/position inputs | PARTIAL | Price column missing; estimated price fallback used. |
| AI / Planning -> Pending | planning result | `.runtime/pending_order_plan/pending_order_plan.json` | AI signal, allocation, safety allow | PASS | E15/E22 connected. |
| Pending -> Approval | pending items | approval-linked pending | approval hash / approved item ids | PASS | Approval linked in E22. |
| Approval -> Submit | approved pending | RuntimeV2SubmitCommand | state APPROVED, consumed false, submit job only | PASS | E17 connected. |
| Submit -> Broker Accepted | SubmitCommand | Demo broker response | demo-only guard, issue normalization | PASS | E22 accepted 5/5. |
| Broker Accepted -> OrderList Filled | broker accepted order id | OrderList filled evidence | OrderList status filled, executed qty, remaining 0 | PASS | E22 showed 5 `全部約定`. |
| OrderList Filled -> Position / Cash Evidence | filled order | Position/Cash evidence | matching position quantity, cash/buying power evidence | PASS | E22/E23 accepted detail optional. |
| Position / Cash Evidence -> Ledger | normalized evidence | ledger orders/positions/cash/events | redacted normalized evidence | PASS | Broker Position -> Ledger Position matched. |
| Ledger -> Current SoT | accepted submit + ledger positions | `.runtime/persistent_ledger/state.json` | runtime-owned symbol match | PASS | E25 fixed. |
| Current SoT -> Public Report | state.json | public report/latest | fixed Current read, redaction scan | PASS | E25 regenerated report with 5 holdings. |
| Current SoT -> Next Planning / Capital Allocation | state.json | planning asset_state | non-empty positions, exposure values | PASS | `_load_asset_state` reads 5 positions and market_value. |

## SELL Flow Matrix

SELL is contract-fixed but not executed in E25.

| Edge | Required Contract | Status |
| --- | --- | --- |
| Current Position -> SELL Planning | Current position must exist; quantity must be known. | PARTIAL |
| SELL Planning -> Pending | Sell quantity must be <= Current quantity. | NOT_IMPLEMENTED for daily operation |
| Pending -> Approval | Manual approval required. | PASS as generic Pending/Approval contract |
| Approval -> Submit | Submit job only; duplicate guard. | PASS as generic Submit contract |
| Submit -> Broker Accepted | Runtime v2 pure submit path. | PASS from D15 for manual SELL, not daily flow |
| Broker Accepted -> OrderList Filled | OrderList status required. | PARTIAL |
| Filled -> Position / Cash Evidence | Position decreases; cash/buying power increases. | PARTIAL |
| Evidence -> Ledger | Order/position/cash records append. | PARTIAL |
| Ledger -> Current SoT | Current position reduced or removed. | NOT_IMPLEMENTED in E25 |
| Current -> Public Report / Next Planning | Report and next planning see reduced holdings. | NOT_IMPLEMENTED in E25 |

SELL rules:

- If Current Position is missing, SELL is forbidden.
- Sell quantity must not exceed Current Position quantity.
- Sell quantity must not exceed available quantity when Broker availability evidence exists.
- Full fill removes or zeroes the position.
- Partial fill reduces quantity.
- Reject leaves Current unchanged and records REVIEW_REQUIRED if needed.
- Unknown / POST_SEND_UNKNOWN never auto-resubmits.

## Execution / Reconcile Flow Matrix

| Edge | Input | Output | Status | Notes |
| --- | --- | --- | --- | --- |
| Broker OrderList -> Broker Position | OrderList filled orders | matching position evidence | PASS | E22 evidence present. |
| Broker Position -> Broker Cash | Position/cash snapshot | normalized readonly bundle | PASS | Cash evidence present. |
| Broker Evidence -> Ledger | normalized evidence | ledger JSONL | PASS | Values preserved. |
| Ledger -> Asset Projection | runtime-owned fills | Current SoT | PASS | E25 fixed. |
| Current SoT -> Reconcile | state + evidence | reconcile status | PARTIAL | Current projection fixed; demo reset reconciliation policy still warning-sensitive. |
| Reconcile -> Audit | reconcile/report | audit artifact | PASS | Audit generated; redaction scan PASS. |

## Notification Flow Matrix

Notification actual delivery remains out of E25 scope.

| Edge | Status | Notes |
| --- | --- | --- |
| Runtime Event -> Notification Payload | READY | Payload-only artifacts generated. |
| Notification Payload -> Delivery Ledger | MODEL_ONLY / PARTIAL | Delivery ledger model exists but operational send ledger not connected. |
| Delivery Ledger -> LINE Sender | NOT_IMPLEMENTED | E14 gap remains. |
| Delivery Ledger -> Discord Sender | NOT_IMPLEMENTED | E14 gap remains. |
| Sender -> Delivery Result | NOT_IMPLEMENTED | No actual sender result. |
| Delivery Result -> Audit | NOT_CONNECTED | No actual delivery audit. |

Day1 operation can continue with `notification-mode=payload-only`; actual notification delivery remains a known operation-layer gap.

## Report Flow Matrix

| Edge | Status | Notes |
| --- | --- | --- |
| Current SoT -> Runtime Report | PASS | Runtime report regenerated after projection. |
| Runtime Report -> Public Report | PASS | Public Report shows holdings and valuation. |
| Public Report -> latest.md/latest.json | PASS | latest artifacts regenerated. |
| Public Report -> Blog/external publishing | NOT_IMPLEMENTED | Phase9 writer intentionally not reused. |
| Redaction Scan | PASS | No raw request/response/secret leakage. |

## Mode Switch Flow Matrix

| Edge | Status | Notes |
| --- | --- | --- |
| mode=demo/production -> BrokerCapability | PASS | Capability auto-resolves from mode. |
| BrokerCapability -> Broker Adapter | PASS | Demo submit/readonly adapter used. |
| Broker Adapter -> Common Runtime Logic | PASS | Submit/Execution logic common; capability controls behavior. |
| Demo 9000-series block | PASS | Demo blocks 9000 series. |
| Production 9000-series allowed | PASS by unit contract | No production submit executed. |
| Demo broker reset/cash/positions -> Current | PASS | Not copied directly. |
| Production Broker SoT reflection | PARTIAL | Contract exists; production not started. |

## BUY Asset Projection Fix

Added:

- `src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py`
- `tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py`

Projection ownership rule:

1. Read accepted Runtime Submit ledger orders.
2. Extract `issue_code_normalization.broker_issue_code`.
3. Match only those symbols against latest Ledger Position evidence.
4. Exclude unrelated Demo broker positions.
5. Compute Current positions, market value, cost basis, cash, buying power, and total equity.
6. Write fixed Current path only:
   - `.runtime/persistent_ledger/state.json`

Cash policy:

- Broker Demo cash (`~20,000,000`) is evidence only.
- Runtime cash is computed as:
  - `runtime_evaluation_capital - runtime_owned_cost_basis`
- For E22/E23 evidence:
  - runtime_evaluation_capital: `1,000,000`
  - cost_basis: `51,000`
  - projected cash / buying_power: `949,000`
  - projected market_value: `979,800`
  - projected total_equity: `1,928,800`

The high total equity is inherited from Tachibana Demo Position evidence, where average price is `102` and market prices are much higher for several symbols. It is not a Runtime hard-coded valuation.

## Current SoT Before / After

Before:

| Field | Value |
| --- | --- |
| cash | 1,000,000 |
| buying_power | 1,000,000 |
| market_value | 0 |
| total_equity | 1,000,000 |
| positions | `[]` |
| source | `phase14e8_demo_operation_initial_state` |

After:

| Field | Value |
| --- | --- |
| cash | 949,000 |
| buying_power | 949,000 |
| market_value | 979,800 |
| total_equity | 1,928,800 |
| positions | 5 symbols |
| source | `runtime_v2_runtime_owned_fill_projection` |

Projected positions:

| Symbol | Quantity | Average Price | Market Value | Cost Basis | Unrealized PnL |
| --- | ---: | ---: | ---: | ---: | ---: |
| `6522` | 100 | 102 | 235,000 | 10,200 | 224,800 |
| `7878` | 100 | 102 | 155,400 | 10,200 | 145,200 |
| `6897` | 100 | 102 | 67,700 | 10,200 | 57,500 |
| `6327` | 100 | 102 | 514,000 | 10,200 | 503,800 |
| `4591` | 100 | 102 | 7,700 | 10,200 | -2,500 |

Excluded Demo broker positions:

- `6501`
- `6502`
- `9984`
- `6504`
- `6505`
- `9001`

## Public Report Result

`reports/public/runtime_v2/latest.md` now shows:

- Cash: `JPY 949,000`
- Buying power: `JPY 949,000`
- Market value: `JPY 979,800`
- Total equity: `JPY 1,928,800`
- Holdings:
  - `6522`
  - `7878`
  - `6897`
  - `6327`
  - `4591`

Redaction scan remains PASS.

## Next Planning / Capital Allocation Result

Runtime v2 Morning asset loader now reads:

- positions_count: `5`
- symbols: `6522`, `7878`, `6897`, `6327`, `4591`
- market_value: `979,800`
- cash: `949,000`
- buying_power: `949,000`
- current_positions_unknown: `false`
- cash_unknown: `false`
- buying_power_unknown: `false`

This means next Planning no longer sees Current exposure as zero. A later phase should still improve Planning itself to subtract current exposure explicitly from available allocation.

## Known Gaps

1. SELL daily operation is contract-defined but not fully implemented.
2. Notification LINE / Discord sender remains `NOT_IMPLEMENTED`.
3. Delivery ledger operational write/send result is not connected.
4. Blog/external publishing remains not implemented for Runtime v2.
5. Production Broker SoT reflection is not exercised.
6. Morning price source still falls back when feature price columns are missing.
7. Broker normalized evidence still labels live Demo evidence as `source=mock`; provenance should be clarified.

## Verification

Commands:

- `python3 -m pytest tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py tests/runtime_v2/test_phase14e23_execution_acceptance_policy.py tests/runtime_v2/test_phase14e6_runtime_v2_public_report_output.py` -> `6 passed`
- `python3 -m pytest tests/runtime_v2` -> `327 passed`

Operational checks:

- E22/E23/E24 existing artifacts were used.
- No additional Submit was executed.
- Public Report regenerated from fixed Current SoT.
- Next Planning asset loader confirmed 5 positions.

## Final Judgment

`PHASE14E25_RUNTIME_V2_DATA_FLOW_CONTRACT_FIXED`
