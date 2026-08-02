# Phase24-IM Corporate Action Adjustment Authority Runtime Materialization and Consumer Wiring Audit

## 1. Primary Judgment

`PHASE24_IM_AUTHORITY_MATERIALIZATION_AND_CONSUMER_WIRING_REPAIRED_SHORT_VALIDATION_PASS_OPERATOR_RESUME_REQUIRED`

## 2. Executive Summary

Phase24-IL added the Corporate Action Adjustment Authority consumer, but the Runtime Submit path did not materialize the authority before consumers ran. Submit Guard also called the evaluator with `event_evidence=None`, so it reported `corporate_action_event_status=NOT_DETECTED` and `corporate_action_adjustment_authority_status=PASS`.

HistoricalSubmitAdapter independently read raw PIT OHLCV and detected `AdjFactor=0.3333333333333333`, so it reported `IMPACT_DETECTED` and `REVIEW_REQUIRED`. This was a consumer wiring defect and materialization gap, not a Corporate Action Guard defect.

## 3. Target Runtime Evidence

- Run: `runtime-test-historical-extended-smoke-20260801T223117629647Z`
- Business date: `2023-10-04`
- Job: `submit`
- Symbol: `65730`
- Side / quantity: `SELL 200`
- Current quantity: `200`
- Broker available quantity: `200`
- Pending quantity: `200`
- Pending price: `808.0`
- Pending price_as_of: `2023-09-05`
- Current valuation_as_of: `2023-10-03`

Raw PIT evidence:

- source: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260801T223117629647Z/daily/2023-10-04/market_refresh/inputs/historical_asof/2023-10-04/raw/jquants/equities_bars_daily/data.parquet`
- source hash: `df0f88639ec34edb9fbb84d9748e1369ff005fd4984f23e201a3f7c62f302bdc`
- 2023-10-04 `65730` row: `AdjFactor=0.3333333333333333`, `C=795.0`, `AdjC=795.0`

Machine snapshot:

`reports/phase24_im_corporate_action_adjustment_authority_runtime_materialization_and_consumer_wiring_audit/runtime_evidence_snapshot.json`

## 4. Authority Producer

Phase24-IL had an evaluator but no materializing producer. Phase24-IM establishes:

- producer: `materialize_corporate_action_adjustment_authority`
- module: `src/ai_fund_lab_v2/runtime_v2/corporate_action_adjustment.py`
- artifact path: `.runtime/runtime_state/corporate_action_adjustments/<business_date>/<symbol>.json`
- unit of materialization: business date + normalized symbol
- consumer: Submit Guard and HistoricalSubmitAdapter

The producer writes a fail-closed authority artifact for impacted events even when event type or already-applied status is unresolved. This removes the previous `missing` ambiguity without converting unknown corporate actions into PASS.

## 5. Materialization Classification

Pre-repair classification:

`PRODUCER_NOT_CALLED`

Secondary:

`CONSUMER_LOOKUP_PATH_MISMATCH`

Submit Guard did not use the PIT Corporate Action event evidence and therefore could not look up or materialize the same authority used by the adapter.

## 6. Consumer Wiring

Pre-repair:

```text
Submit Guard:
  NOT_DETECTED / PASS

HistoricalSubmitAdapter:
  IMPACT_DETECTED / REVIEW_REQUIRED
```

Post-repair:

```text
Submit pipeline
  -> HistoricalSubmitAdapter.corporate_action_event_evidence
  -> materialize_corporate_action_adjustment_authority
  -> Submit Guard evaluator
  -> HistoricalSubmitAdapter evaluator
```

Both consumers resolve the same authority path and hash for impacted historical submit items.

## 7. Temporal Authority

The event effective date equals the submit business date: `2023-10-04`. Current valuation is from `2023-10-03`, and Pending price lineage is older than the event impact. Current / Broker / Pending quantities are all `200`, but there is no accepted evidence proving whether `200` is pre-adjustment or post-adjustment quantity for the 2023-10-04 impact.

Therefore:

- `already_applied_status`: `UNKNOWN`
- `quantity_reconciliation_status`: `REVIEW_REQUIRED`
- `price_reconciliation_status`: `REVIEW_REQUIRED`

## 8. Quantity Reconciliation

`AdjFactor=0.3333333333333333` alone is not used to infer the legal event type or quantity conversion direction. The Runtime requires a PIT event-type authority and adjustment application lineage before allowing submit.

Unknown event type, unknown application state, mixed quantity basis, and double-adjustment risk remain fail-closed.

## 9. Root Cause

Primary root cause:

`corporate_action_authority_producer_not_called_before_submit_guard`

Secondary root cause:

`submit_guard_missing_canonical_corporate_action_event_evidence`

## 10. Recommended Next Task

`Phase24-IN Operator Resume Corporate Action Runtime Validation`
