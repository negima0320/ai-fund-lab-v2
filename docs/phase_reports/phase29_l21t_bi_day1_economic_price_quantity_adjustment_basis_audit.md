# Phase29-L21T-BI — Day1 Economic Price / Quantity Adjustment Basis Consistency Audit

## Task

- Task ID: Phase29-L21T-BI
- Mode: READ-ONLY audit
- Target run: `runtime-test-historical-extended-smoke-20260815T015141544126Z`
- Date: `2022-08-10`
- Phase: Phase29 continued; Phase30 not entered

No Strategy, Runtime, Config, Model, or Threshold change was made. No fresh-run, resume, replay, recovery, or target run mutation was performed.

## Primary Judgment

`PRICE_QUANTITY_ADJUSTMENT_BASIS_MISMATCH`

The observed Day1 equity jump is not investment performance. It is caused by applying raw-basis prices to quantities that were created from adjusted-basis execution/fill prices.

## Day1 Reconciliation

| Item | Value |
| --- | ---: |
| Initial cash / equity | `1,000,000.0` |
| BUY notional | `254,180.0` |
| SELL notional | `0.0` |
| Final cash | `745,820.0` |
| Observed holdings market value | `1,105,450.0` |
| Observed total equity | `1,851,270.0` |
| Observed return | `+85.127%` |
| Consistent-basis holdings market value | `250,040.0` |
| Consistent-basis total equity | `995,860.0` |
| Basis mismatch excess equity | `855,410.0` |

The observed `+851,270.0` unrealized gain is approximately the raw/adjusted basis jump, not a market profit.

## Symbol Findings

| Symbol | Qty | Fill Price | Raw C | Adj Close | BH Price | Observed MV | Consistent MV | Excess |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 23700 | 500 | 72.0 | 71.0 | 71.0 | 71.0 | 35,500.0 | 35,500.0 | 0.0 |
| 23880 | 100 | 169.0 | 151.0 | 151.0 | 151.0 | 15,100.0 | 15,100.0 | 0.0 |
| 45710 | 100 | 203.0 | 199.0 | 199.0 | 199.0 | 19,900.0 | 19,900.0 | 0.0 |
| 66590 | 400 | 102.0 | 98.0 | 98.0 | 98.0 | 39,200.0 | 39,200.0 | 0.0 |
| 76470 | 1100 | 26.0 | 26.0 | 26.0 | 26.0 | 28,600.0 | 28,600.0 | 0.0 |
| 89180 | 2700 | 10.0 | 10.0 | 10.0 | 10.0 | 27,000.0 | 27,000.0 | 0.0 |
| 93180 | 6600 | 6.0 | 6.0 | 6.0 | 6.0 | 39,600.0 | 39,600.0 | 0.0 |
| 94320 | 200 | 149.2 | 3744.0 | 149.8 | 3744.0 | 748,800.0 | 29,960.0 | 718,840.0 |
| 94340 | 100 | 151.4 | 1517.5 | 151.8 | 1517.5 | 151,750.0 | 15,180.0 | 136,570.0 |

`94320` and `94340` explain the abnormal Day1 equity jump.

## 94320

- Current quantity: `200`
- Quantity provenance: `runtime_v2_runtime_owned_fill_projection`
- Execution price: `149.2`
- Raw Open / Close: `3730.0 / 3744.0`
- Adjusted Open / Close: `149.2 / 149.8`
- Raw/adjusted close ratio: `24.9933`
- BH accepted price: `3744.0`
- Observed market value: `748,800.0`
- Consistent adjusted-basis market value: `29,960.0`
- Basis mismatch excess: `718,840.0`

The fill price exactly matches the adjusted open, not the raw open. Therefore the runtime-owned quantity is adjusted-basis. Applying raw close to that quantity overstates market value by about 25x.

## 94340

- Current quantity: `100`
- Quantity provenance: `runtime_v2_runtime_owned_fill_projection`
- Execution price: `151.4`
- Raw Open / Close: `1513.5 / 1517.5`
- Adjusted Open / Close: `151.4 / 151.8`
- Raw/adjusted close ratio: `9.9967`
- BH accepted price: `1517.5`
- Observed market value: `151,750.0`
- Consistent adjusted-basis market value: `15,180.0`
- Basis mismatch excess: `136,570.0`

The fill price matches adjusted open, not raw open. Applying raw close to the adjusted-basis quantity overstates market value by about 10x.

## Required Judgment

- BH raw economic price selection is correct: NO, not for the current runtime quantity basis
- Current quantity basis is raw-compatible: NO
- Price/quantity basis mismatch confirmed: YES
- 94320 contributes materially to +85% equity: YES
- 94340 contributes materially: YES
- Other symbols affected: NO for material mismatch on Day1; their raw/adjusted closes are equal
- Corporate Action quantity normalization involved: YES, the mismatch is adjustment-basis related
- BH implementation repair required: YES

## Root Cause

`PRICE_QUANTITY_ADJUSTMENT_BASIS_MISMATCH`

BH prevented adjusted analytical prices from being consumed silently, but it selected raw close as the universal economic valuation price. Day1 evidence shows the runtime-owned quantities and execution prices are already on the adjusted basis for split-adjusted symbols. Therefore valuation must not simply switch price to raw unless the corresponding quantity is raw-basis too.

The correct repair target is the price/quantity basis contract. Current valuation must use a price basis compatible with runtime-owned quantity basis, or quantity must carry authoritative basis/provenance and be normalized before valuation.

## Artifacts

- `reports/phase29_l21t_bi_day1_economic_price_quantity_adjustment_basis_audit/summary.json`
- `reports/phase29_l21t_bi_day1_economic_price_quantity_adjustment_basis_audit/symbol_basis_reconciliation.csv`
- `reports/phase29_l21t_bi_day1_economic_price_quantity_adjustment_basis_audit/day1_equity_contribution.csv`
- `reports/phase29_l21t_bi_day1_economic_price_quantity_adjustment_basis_audit/adjustment_factor_trace.csv`

## Validation

- `summary.json` parse: tracked in final validation
- `py_compile` for audit script: tracked in final validation
- `git diff --check`: tracked in final validation
- Runtime mutation: none
- Strategy mutation: none
- Fresh-run / resume / replay / recovery: not executed

## Recommended Next Action

Implement:

`Phase29-L21T-BJ — Current Valuation Price / Quantity Adjustment Basis Contract Repair`

The repair should define and enforce a production-common basis contract across execution price, runtime-owned quantity, Current valuation price, Corporate Action handling, and market evidence. It should not choose raw or adjusted by symbol-specific rule.
