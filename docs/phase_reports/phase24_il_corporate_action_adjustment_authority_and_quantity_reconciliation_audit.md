# Phase24-IL Corporate Action Adjustment Authority and Quantity Reconciliation Audit

## 1. Primary Judgment

`PHASE24_IL_CORPORATE_ACTION_ADJUSTMENT_AUTHORITY_IMPLEMENTED_SHORT_VALIDATION_PASS_OPERATOR_RESUME_REQUIRED`

The 2023-10-04 Historical Submit stop for `65730` is a correct fail-closed Corporate Action Guard result. The direct impact signal is J-Quants raw `equities_bars_daily` `AdjFactor=0.3333333333333333` on the submit business date. Repository evidence does not provide a standalone resolved event type, so the event type remains `UNKNOWN_ADJFACTOR_IMPACT`.

## 2. Reviewed Evidence

- Phase24-IK audit and repair reports.
- Runtime architecture and autonomous operations architecture.
- Target run: `runtime-test-historical-extended-smoke-20260801T223117629647Z`.
- Target date/job/item: `2023-10-04` / `submit` / `65730` SELL `200`.
- Raw PIT source: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260801T223117629647Z/daily/2023-10-04/market_refresh/inputs/historical_asof/2023-10-04/raw/jquants/equities_bars_daily/data.parquet`.
- Pending source: `.runtime/pending_order_plan/pending_order_plan.json`.
- Current source: `.runtime/persistent_ledger/state.json`.

Machine evidence was written to:

`reports/phase24_il_corporate_action_adjustment_authority_and_quantity_reconciliation_audit/target_case_evidence.json`

## 3. Corporate Action Reality

PIT rows for `65730` show:

| Date | AdjFactor | Raw close | Adjusted close |
|---|---:|---:|---:|
| 2023-10-02 | 1.0 | 2400.0 | 800.0 |
| 2023-10-03 | 1.0 | 2424.0 | 808.0 |
| 2023-10-04 | 0.3333333333333333 | 795.0 | 795.0 |

This is an adjustment impact signal. It is consistent with a quantity/price adjustment pattern, but the legal event type is not asserted because no accepted event-type authority was present in the reviewed evidence.

## 4. Current / Ledger / Pending Lineage

Current `65730`:

- quantity: `200`
- average price: `805.15`
- current price: `808.0`
- valuation_as_of: `2023-10-03`
- source_market_date: `2023-10-03`
- valuation_adjusted: `false`

Pending SELL `65730`:

- quantity: `200`
- estimated_price: `808.0`
- estimated_amount: `161600.0`
- price_as_of: `2023-09-05`
- price_source: `current_sot_position_valuation`
- quantity contract: `PASS` using historical simulated broker authority

No evidence proves that the 2023-10-04 adjustment was applied to Ledger, Current, Pending quantity, or Pending price lineage before Submit.

## 5. Root Cause

Primary root cause:

`corporate_action_adjustment_authority_missing`

Secondary root cause:

`corporate_action_type_unresolved`

The Corporate Action Guard was correct. The missing component was a Production Runtime common authority proving that Ledger / Current / Pending / Submit are all on the same adjusted basis and that the event has not been applied twice.

## 6. Defect Classification

| Area | Judgment |
|---|---|
| Resume-specific defect | NO |
| Production Runtime defect | YES |
| Historical Adapter defect | PARTIAL |
| Current Projection defect | YES |
| Ledger Adjustment defect | YES |
| Pending Quantity defect | YES |
| Submit Preflight defect | YES |
| Corporate Action Guard defect | NO |
| Temporal Authority defect | YES |
| Idempotency defect | YES |
| Observability gap | YES |

## 7. Required Runtime Behavior

An impacted order must not pass merely because `AdjFactor` is known. It may pass only when a Runtime-owned Corporate Action Adjustment Authority proves event resolution, PIT binding, no future data use, idempotency, and adjusted quantity reconciliation.

For the target case, the correct post-repair expectation remains fail-closed unless a valid `65730` / `2023-10-04` adjustment authority is materialized.

## 8. Recommended Next Task

`Phase24-IM Operator Resume Corporate Action Adjustment Authority Validation`

The operator should resume the historical run after the short regression, and the resume should either remain fail-closed with explicit reason codes for the unresolved target event or pass only if a valid PIT corporate action adjustment authority has been materialized.
