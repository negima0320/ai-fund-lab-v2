# Phase23-S: Corporate Event Source Authority Connection and Materialization

## Primary Judgment

`PHASE23_S_PARTIAL_SOURCE_CONNECTION_CORPORATE_EVENT_COVERAGE_GAP_REMAINS`

## Secondary Judgment

- `FINANCIAL_STATEMENTS_FINS_SUMMARY_CONSUMER_CONNECTED`
- `THREE_STATE_SYMBOL_COVERAGE_MATERIALIZED`
- `CORPORATE_ACTIONS_AND_EARNINGS_SCHEDULE_SOURCE_UNAVAILABLE_DESIGN_DECISION_REQUIRED`
- `NOT_READY_FOR_OPERATOR_PRODUCTION_EQUIVALENT_10BD_RERUN`

## 1. Primary Judgment

Phase23-S partially connected Corporate Event Source Authority. The producer now resolves J-Quants `fins_summary` as the Financial Statements source path and materializes symbol-scoped three-state coverage. The target real data still does not have full Corporate Event coverage, so 10BD is not ready.

## 2. Direct Source Gap

Remaining direct gaps:

- `.runtime/operations/jquants/raw/jquants/fins_summary/data.parquet` is not materialized.
- `earnings_schedule` source/fetcher/schema was not found in the repo.
- `corporate_actions` source/fetcher/schema was not found in the repo.

## 3. Corporate Event Required Source Contract

Corporate Event remains a PIT fact authority only. It does not decide BUY/SELL, target count, exposure, sizing, lot rounding, Pending, Submit, or Broker Write.

The required source contract is recorded in `corporate_event_required_source_contract.json`.

## 4. J-Quants Source Capability

Confirmed existing J-Quants capabilities:

- Daily Quotes: fetcher/raw/schema/normalizer exist; not a Corporate Event fact source.
- Listed Issues: fetcher/raw/schema exist; Corporate Event parser connected.
- Trading Calendar: fetcher/raw/schema exist; coverage source connected.
- Fins Summary: fetcher/raw schema exists; Corporate Event consumer path connected in this task.

Not found:

- Earnings Schedule fetcher/source/schema.
- Corporate Actions fetcher/source/schema.

## 5. Source Connection / Materialization Classification

- Listed Issues: `SOURCE_AVAILABLE_CONNECTED`
- Trading Calendar: `SOURCE_AVAILABLE_CONNECTED`
- Daily Quotes: `SOURCE_AVAILABLE_CONNECTED_NOT_CORPORATE_EVENT_FACT_SOURCE`
- Financial Statements / Fins Summary: `FETCHER_EXISTS_NOT_MATERIALIZED_CONSUMER_CONNECTED_IN_PHASE23_S`
- Earnings Schedule: `SOURCE_NOT_AVAILABLE_DESIGN_DECISION_REQUIRED`
- Corporate Actions: `SOURCE_NOT_AVAILABLE_DESIGN_DECISION_REQUIRED`

## 6. PIT Date Authority

- Listed Issues availability: `Date` / `target_date` / `provider_effective_date <= business_date`
- Fins Summary availability: `DiscDate` / `DisclosedDate <= business_date`
- Financial period end is descriptive, not availability authority.
- Corporate Actions and Earnings Schedule must use announcement/available-at fields if later added.

## 7. Raw / Canonical / As-of Pipeline

Implemented/confirmed path:

`Raw J-Quants parquet -> business-date as-of filtering -> Corporate Event Authority`

No network fetch was run. No broker write was performed.

## 8. Three-state Semantics

The artifact now exposes:

- `KNOWN_EVENT`
- `KNOWN_NO_EVENT`
- `UNKNOWN_DUE_TO_MISSING_COVERAGE`

Missing coverage is not treated as no-event.

## 9. Symbol-scoped Coverage

Validation artifact: `reports/phase23_s_corporate_event_source_authority_connection_and_materialization/validation_artifacts/corporate_event_2026-07-06.json`

Observed on `2026-07-06`:

- status: `REVIEW_REQUIRED`
- coverage: `PARTIAL`
- symbol facts: `4437`
- unknown symbols: `4437`

## 10. Downstream Propagation

Downstream was not forced to PASS. Because real Corporate Event coverage remains partial, current downstream compatibility still formally propagates review. The new symbol coverage is available for a later scoped-consumer contract repair, but no unsafe relaxation was introduced.

## 11. Quantity Resolution Result

Quantity remains not ready for the target run because Corporate Event source authority remains partial. Position Sizing was not forced, and the active target run was not resumed or modified.

## 12. Phase23-P/Q/R Regression

Preserved:

- Historical Evaluation Authority fixed run-start contract
- Production-common daily scheduler
- Phase23-R consumer observability fields
- Broker Write false
- Runtime Switch false
- J-Quants network fetch false

## 13. Short Validation

- compile: PASS
- targeted regression: `50 passed in 3.02s`
- JSON validation: PASS
- long Runtime / 10BD / network fetch / Broker Write: not run

## 10BD Gate

`NOT_READY_FOR_OPERATOR_PRODUCTION_EQUIVALENT_10BD_RERUN`
