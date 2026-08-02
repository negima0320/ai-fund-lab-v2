# Phase24-H Performance Accounting Cost Basis Authority Repair

## 1. Executive Summary

Phase24-H repaired the Open Position Cost Basis Authority gap identified in Phase24-G.

The repair is limited to the production-common Runtime-owned fill projection path. Open position average price and cost basis are now reconstructed from canonical execution-equivalent events with moving-average inventory accounting. Existing historical artifacts were not rewritten.

Short validation passed. Long 20BD Runtime rerun remains Operator-owned.

## 2. Primary Judgment

```text
PHASE24_H_COST_BASIS_AUTHORITY_REPAIRED_SHORT_VALIDATION_PASS_RUNTIME_RERUN_REQUIRED
```

## 3. Scope and Non-Regression Constraints

Scope:

```text
Open Position Cost Basis Authority only
```

Files changed for repair:

```text
src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py
tests/runtime_v2/test_phase24_h_cost_basis_authority.py
```

No changes were made to:

```text
PM
Strategy
Opportunity Ranking
Portfolio Construction
Capital Deployment
Position Sizing
Exit Timing
Re-entry policy
Thresholds
Cash ratio
Historical source data
Existing historical run artifacts
```

Forbidden repair patterns were not used:

```text
historical-only branch
run_id-specific handling
date-specific handling
symbol-specific handling
summary-only correction
post-hoc overwrite
```

## 4. Phase24-G Accounting Gap

Phase24-G found a 51,960 yen accounting gap:

```text
final_equity - initial_equity = -64,220
reported realized_pnl + unrealized_pnl = -116,180
gap = 51,960
```

Cash, market value, and total equity reconciled:

```text
282,130 + 653,650 = 935,780
```

The gap was isolated to open-position cost basis:

```text
existing open cost basis = 711,030
execution-basis open notional = 659,070
difference = 51,960
```

## 5. Cost Basis Mutation Path Audit

Canonical mutation path:

```text
Execution / Fill
  -> Persistent Ledger
  -> Runtime Current Position
  -> Position Campaign
  -> Performance Summary
```

Transition authority:

| Transition | Cost Basis Authority | Realized PnL Authority | Unrealized PnL Authority |
|---|---|---|---|
| BUY into empty | fill quantity * fill price | N/A | market value - open cost basis |
| ADD into open | moving-average open inventory cost plus fill notional | N/A | market value - open cost basis |
| Partial SELL | remaining cost after disposed moving-average basis | sell proceeds - disposed basis | remaining market value - remaining cost |
| Full SELL | quantity 0 means cost basis 0 and average price 0 | sell proceeds - disposed basis | 0 |
| Same-symbol re-entry | new BUY notional only | closed campaign preserved | new open market value - new open cost |
| Summary materialization | Persistent Ledger current position | Persistent Ledger realized slices | Persistent Ledger current valuation |

Detailed evidence:

```text
reports/phase24_h_performance_accounting_cost_basis_authority_repair/cost_basis_mutation_path_audit.json
reports/phase24_h_performance_accounting_cost_basis_authority_repair/cost_basis_authority_matrix.json
```

## 6. Existing Run Symbol Reconstruction

Read-only reconstruction was performed from run-scoped fill observability. Existing artifacts were not modified.

Static result:

```text
open_execution_basis_notional = 659,070
canonical_open_cost_basis = 659,070
expected_open_unrealized_pnl = -5,420
closed_realized_pnl = -58,800
expected_realized_plus_unrealized = -64,220
total_return = -64,220
difference = 0
```

Symbol-level reconciliation:

| Symbol | Quantity | Existing Basis | Canonical Basis | Repaired Unrealized PnL |
|---|---:|---:|---:|---:|
| 24370 | 100 | 123,500 | 137,000 | -1,800 |
| 66590 | 1,600 | 232,000 | 166,400 | 0 |
| 94320 | 1,200 | 186,240 | 186,380 | -3,620 |
| 94340 | 1,100 | 169,290 | 169,290 | 0 |

Detailed evidence:

```text
reports/phase24_h_performance_accounting_cost_basis_authority_repair/existing_run_symbol_reconstruction.json
reports/phase24_h_performance_accounting_cost_basis_authority_repair/post_repair_static_reconciliation.json
```

## 7. Root Cause

Primary root cause:

```text
SUMMARY_CONSUMES_NON_CANONICAL_COST_BASIS
```

Runtime-owned fill projection reconstructed quantity, cash, and realized PnL from canonical execution events, but open position `average_price` was copied from the latest broker/current position snapshot. In same-symbol close and re-entry sequences, that snapshot could retain a previous campaign basis, causing Persistent Ledger current positions and final summary unrealized PnL to consume non-canonical open cost basis.

Secondary root cause:

```text
REENTRY_INHERITS_PREVIOUS_CAMPAIGN_COST_BASIS
```

Not root causes:

```text
cash accounting
fill notional
final cash
final market value
final equity
closed realized PnL
execution counts
position quantities
fees
taxes
corporate actions
deposits
withdrawals
```

Detailed evidence:

```text
reports/phase24_h_performance_accounting_cost_basis_authority_repair/root_cause_analysis.json
```

## 8. Canonical Cost Basis Contract

Contract:

```text
contract_id = phase24h_open_position_cost_basis_authority_v1
canonical_owner = Runtime-owned fill projection over canonical execution-equivalent events
inventory_accounting_method = MOVING_AVERAGE_AVERAGE_COST_POOL
```

Open position cost basis is the acquisition notional attributable to currently open quantity under moving-average inventory accounting.

Invariants:

```text
BUY into open: quantity and cost basis increase by canonical fill quantity/notional.
Partial SELL: remaining cost basis = previous cost - average cost * sold quantity.
Full SELL: quantity, cost basis, and average price reset to zero.
Same-symbol re-entry: new open basis uses new campaign acquisition only.
Unrealized PnL: current market value - canonical open cost basis.
Realized PnL: disposal proceeds - disposed moving-average basis.
```

Detailed contract:

```text
reports/phase24_h_performance_accounting_cost_basis_authority_repair/canonical_cost_basis_contract.json
```

## 9. Implementation Repair

Implementation summary:

```text
Added canonical open cost reconstruction from runtime-owned canonical execution events.
Projected Current position average_price now uses reconstructed open cost / open quantity when canonical fills exist.
Quantity/cost mismatch fails closed with REVIEW_REQUIRED.
Projection payload now materializes new_unrealized_pnl from canonical position rows.
No PM/Strategy/Ranking/Sizing/Portfolio Construction/Re-entry policy changes.
```

The repair is production-common and applies to the shared runtime-owned fill projection path.

Detailed diff summary:

```text
reports/phase24_h_performance_accounting_cost_basis_authority_repair/repair_diff_summary.json
```

## 10. Runtime Current / Ledger / Campaign Alignment

Alignment after repair:

```text
Execution-equivalent canonical events produce open quantity and open cost.
Persistent Ledger current positions consume projected canonical average price.
Runtime Current receives the same projected position row.
Position Campaign attribution remains a consumer of ledger/current basis and closed campaign state.
Performance Summary consumes Persistent Ledger current valuation.
```

Campaign materialization did not require code changes in this task. It remains attribution-facing; current open basis authority is the Persistent Ledger current position generated by runtime-owned fill projection.

## 11. Regression Test Matrix

Regression coverage added:

```text
BUY from empty
ADD into open position
Partial SELL
Full SELL
Same-symbol re-entry
Multiple close / re-entry cycles
Runtime Current / Persistent Ledger consistency
Campaign / Ledger static consistency
Phase24-G generalized failure sequence
No regression to reconciled authorities
```

Commands:

```text
python3 -m pytest tests/runtime_v2/test_phase24_h_cost_basis_authority.py -q
7 passed

python3 -m pytest tests/runtime_v2/test_phase14e25_runtime_owned_fill_projection.py tests/runtime_v2/test_phase17_bs_canonical_performance_event_contract.py -q
7 passed

python3 -m pytest tests/runtime_v2/test_phase20_l_long_run_readiness_destructive.py tests/runtime_v2/test_phase20_j_performance_observability.py tests/runtime_v2/test_phase20_k_performance_observability_consumer.py tests/runtime_v2/test_phase20_bm_run_scoped_final_performance_authority.py -q
12 passed

PYTHONPYCACHEPREFIX=/private/tmp/phase24h_pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py scripts/runtime_test.py
compile pass
```

Detailed matrix:

```text
reports/phase24_h_performance_accounting_cost_basis_authority_repair/regression_test_matrix.json
```

## 12. Static Post-Repair Reconciliation

Static reconciliation passes:

```text
final_cash = 282,130
final_market_value = 653,650
final_equity = 935,780
canonical_open_cost_basis = 659,070
expected_open_unrealized_pnl = -5,420
closed_realized_pnl = -58,800
expected_realized_plus_unrealized = -64,220
total_return = -64,220
difference = 0
existing_artifacts_modified = false
```

This confirms that the Phase24-G accounting gap is closed under the repaired canonical cost-basis contract, without rewriting the old run.

## 13. Preserved Authorities

Preserved authorities:

```text
Execution / fill notional authority
Cash movement authority
Quantity authority
Realized PnL authority
Final cash authority
Final market value authority
Final equity authority
Strategy decision authority
PM decision authority
Opportunity ranking authority
Portfolio construction authority
Capital deployment authority
Position sizing authority
Exit / re-entry decision authority
```

## 14. Remaining Gaps

Remaining observability gaps:

```text
Existing historical run artifacts still contain pre-repair basis and must not be overwritten.
Long 20BD Runtime rerun was not executed by Codex and remains Operator-owned.
Campaign observability stable source decision IDs remain partial and carried from Phase24-F/G.
```

Detailed gap list:

```text
reports/phase24_h_performance_accounting_cost_basis_authority_repair/remaining_observability_gaps.json
```

## 15. Runtime Validation Gate

Runtime validation status:

```text
NOT_RUN_USER_OWNED
```

Operator rerun command:

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src

python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --start-date 2022-07-01 \
  --business-days 20 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Rerun acceptance should compare:

```text
final_equity - initial_equity
realized_pnl + unrealized_pnl
open execution-basis notional
Persistent Ledger current cost_basis
Runtime Current average_price
Position Campaign open basis
Performance Summary unrealized_pnl
```

## 16. Recommended Next Task

```text
Phase24-HR Operator 20BD Runtime Revalidation and Accounting Acceptance Gate
```

Purpose:

```text
Run the historical-extended-smoke 20BD fresh-run under the repaired cost-basis authority and confirm that final equity, realized PnL, unrealized PnL, open basis, Runtime Current, Persistent Ledger, Position Campaign, and Performance Summary reconcile without Phase24-G accounting drift.
```

## 17. Validation Performed

Validation performed:

```text
JSON evidence validity = PASS
Targeted Phase24-H regression tests = PASS
Related runtime-owned projection and performance authority regressions = PASS
Syntax compile = PASS
Static post-repair reconciliation = PASS
20BD Runtime rerun = NOT RUN
```

## 18. Files Created or Updated

Created:

```text
docs/phase_reports/phase24_h_performance_accounting_cost_basis_authority_repair.md
reports/phase_reports/phase24_h_performance_accounting_cost_basis_authority_repair.json
reports/phase24_h_performance_accounting_cost_basis_authority_repair/
tests/runtime_v2/test_phase24_h_cost_basis_authority.py
```

Updated:

```text
src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py
docs/01_requirements/phase_roadmap.md
```
