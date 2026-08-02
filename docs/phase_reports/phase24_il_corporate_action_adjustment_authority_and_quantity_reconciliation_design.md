# Phase24-IL Corporate Action Adjustment Authority and Quantity Reconciliation Design

## 1. Primary Judgment

`PHASE24_IL_CORPORATE_ACTION_ADJUSTMENT_AUTHORITY_CONTRACT_COMPLETE`

## 2. Authority Contract

Corporate Action Adjustment Authority is a Production / Demo / Historical common Runtime authority. It proves that an impacted position and pending submit item are safe after a corporate action quantity or price adjustment.

It is not a strategy decision, not PM logic, not Position Sizing, and not a guard relaxation.

## 3. Canonical Authority

Canonical owner:

`Runtime Corporate Action Adjustment Authority`

Canonical artifact path:

`.runtime/runtime_state/corporate_action_adjustments/<business_date>/<symbol>.json`

Required minimum fields:

```json
{
  "schema_version": "runtime_v2_corporate_action_adjustment_authority_v1",
  "business_date": "YYYY-MM-DD",
  "symbol": "00000",
  "event_status": "PASS|REVIEW_REQUIRED|BLOCK",
  "event_type": "RESOLVED_EVENT_TYPE",
  "effective_date": "YYYY-MM-DD",
  "source_artifact_path": "...",
  "source_artifact_hash": "...",
  "pit_validation_status": "PASS",
  "future_data_used": false,
  "adjustment_factor": 1.0,
  "price_adjustment_required": true,
  "quantity_adjustment_required": true,
  "pre_adjustment_quantity": 0,
  "post_adjustment_quantity": 0,
  "ledger_adjustment_status": "PASS",
  "current_adjustment_status": "PASS",
  "pending_adjustment_status": "PASS",
  "already_applied_status": "CONFIRMED",
  "double_adjustment_detected": false,
  "lineage": {},
  "reason_codes": []
}
```

## 4. Quantity Reconciliation

For SELL submit:

```text
0 < submit_quantity
submit_quantity <= adjusted_runtime_owned_quantity
submit_quantity <= adjusted_broker_available_quantity
```

Ledger, Current, Pending, broker available, and Submit quantities must be on the same adjusted basis. Mixed pre-adjustment and post-adjustment quantities are not allowed to pass.

## 5. Price Reconciliation

Market SELL price drift alone is not a blocker, but the price lineage must not be used to justify the wrong quantity basis. Pending estimated price, Current valuation price, previous close, source_market_date, and price_as_of remain observability fields.

## 6. Idempotency

The authority must prevent duplicate application by binding:

- symbol
- effective_date
- source_artifact_hash
- adjustment_factor
- ledger adjustment identity or equivalent lineage

Resume and same-day retry must reuse the same authority or fail closed. They must not apply the same event twice.

## 7. Corporate Action Guard Connection

Corporate Action Guard can pass an impacted item only when:

- event resolved
- PIT validation `PASS`
- future data not used
- quantity reconciliation `PASS`
- Ledger / Current / Pending lineage consistent
- no double adjustment
- submit quantity valid

Missing or unresolved authority remains fail-closed.

## 8. Non-Goals

This design does not change Strategy, Ranking, Eligibility, PM decision logic, Position Sizing policy, Capital Deployment parameters, Submit Guard thresholds, max exposure, cash reserve, or target exposure.
