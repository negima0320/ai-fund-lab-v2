# Phase31-F1Z0 - 34940 2022-12-08 OHLCV Missing Root-Cause Audit

## PRIMARY_JUDGMENT

PHASE31_F1Z0_34940_OHLCV_MISSING_UNRESOLVED_DATA_AUTHORITY_GAP

## SYMBOL

34940

## BUSINESS_DATE

2022-12-08

## TARGET_RUN_ID

runtime-test-historical-extended-smoke-20260821T050423121340Z

## TARGET_ARTIFACTS

- raw J-Quants daily quotes: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260821T050423121340Z/daily/2022-12-08/market_refresh/inputs/historical_asof/2022-12-08/raw/jquants/equities_bars_daily/data.parquet`
- normalized daily quotes: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260821T050423121340Z/daily/2022-12-08/market_refresh/inputs/historical_asof/2022-12-08/raw_normalized/jquants/equities_bars_daily/data.parquet`
- listed issues: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260821T050423121340Z/daily/2022-12-08/market_refresh/inputs/historical_asof/2022-12-08/raw/jquants/listed_issues/data.parquet`
- trading calendar: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260821T050423121340Z/daily/2022-12-08/market_refresh/inputs/historical_asof/2022-12-08/raw/jquants/trading_calendar/data.parquet`
- corporate event: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260821T050423121340Z/daily/2022-12-08/strategy/corporate_event.json`
- submit manifest: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260821T050423121340Z/daily/2022-12-08/submit/runtime_manifest.json`

## RAW_ROW_COUNT

1

## RAW_ROW_EXACT_INSPECTION

| Field | Value |
| --- | --- |
| Date | 2022-12-08 |
| Code | 34940 |
| Open / O | NaN |
| High / H | NaN |
| Low / L | NaN |
| Close / C | NaN |
| Volume / Vo | NaN |
| TurnoverValue / Va | NaN |
| AdjustmentFactor / AdjFactor | 1.0 |
| AdjustmentOpen / AdjO | NaN |
| AdjustmentHigh / AdjH | NaN |
| AdjustmentLow / AdjL | NaN |
| AdjustmentClose / AdjC | NaN |
| AdjustmentVolume / AdjVo | NaN |
| MarketCap / MktCap | NaN |
| ExRT | None |
| UL | 0 |
| LL | 0 |
| source | jquants |
| endpoint | /v2/equities/bars/daily |
| fetched_at | 2026-08-10T10:25:09.112885+00:00 |

No suspension or per-symbol trading-status field is present in the inspected raw daily quote row.

## RAW_PRICE_FIELD_STATUS

ALL_RAW_AND_ADJUSTED_OHLC_FIELDS_MISSING_NAN

## RAW_VOLUME_STATUS

RAW_AND_ADJUSTED_VOLUME_FIELDS_MISSING_NAN

## NEIGHBORING_DATE_CONTINUITY

| Date | Raw O | Raw H | Raw L | Raw C | Raw Vo | AdjFactor | AdjO | AdjH | AdjL | AdjC | AdjVo | Normalized Row |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2022-12-05 | 970.0 | 970.0 | 944.0 | 944.0 | 600.0 | 1.0 | 194.0 | 194.0 | 188.8 | 188.8 | 3000.0 | present |
| 2022-12-06 | NaN | NaN | NaN | NaN | NaN | 1.0 | NaN | NaN | NaN | NaN | NaN | absent |
| 2022-12-07 | 940.0 | 940.0 | 940.0 | 940.0 | 100.0 | 1.0 | 188.0 | 188.0 | 188.0 | 188.0 | 500.0 | present |
| 2022-12-08 | NaN | NaN | NaN | NaN | NaN | 1.0 | NaN | NaN | NaN | NaN | NaN | absent |

## PREVIOUS_VALID_TRADING_DATE

2022-12-07

## PREVIOUS_VALID_CLOSE

188.0 normalized adjusted Close.

The same raw row has unadjusted `C = 940.0`, but the canonical normalized source used by runtime is adjusted and records `Close = 188.0`.

## LAST_VALID_VOLUME

500.0 normalized adjusted Volume.

The same raw row has unadjusted `Vo = 100.0`.

## LISTING_STATUS_20221208

LISTED

Evidence: PIT listed issues contains one 2022-12-08 row for 34940:

- `CoName = マリオン`
- `CoNameEn = Mullion Co.,Ltd.`
- `Mkt = 0112`
- `MktNm = スタンダード`
- `ProdCat = 011`
- pending item listed evidence resolves `current_listed = true`, `listed_info_pit_status = PASS`, `listed_info_resolution_status = PASS`, `listed_info_row_date = 2022-12-08`

## TRADING_ELIGIBILITY_STATUS_20221208

LISTED_ON_EXCHANGE_TRADING_DAY_BUT_SYMBOL_TRADING_STATUS_UNRESOLVED

Evidence:

- J-Quants trading calendar marks 2022-12-08 as `is_trading_day = True`, `HolDiv = 1`.
- Listed issues confirms 34940 was listed on 2022-12-08.
- The inspected listed/raw quote artifacts do not contain a per-symbol suspension or temporary non-trading field.
- Missing price is not used as proof of suspension or non-trading.

## CORPORATE_EVENT_EXPLAINS_MISSING_OHLCV

NO

Available PIT corporate-event evidence for 34940 is:

```json
{
  "available_at": "2022-12-08",
  "business_date": "2022-12-08",
  "coverage_status": "AVAILABLE",
  "event_dates": [],
  "event_status": "KNOWN_NO_EVENT",
  "event_types": [],
  "reason_codes": [],
  "security_code": "34940",
  "source_ref": "corporate_event.source_coverage"
}
```

The corporate-event artifact also reports `coverage_status = AVAILABLE`, `source_authority_status = VALID`, `decision_resolution = RESOLVED`, `event_count = 0`, and `validation_status = PASS`. No split, reverse split, merger, delisting, tender offer, stock transfer, name/code change, ex-date event, or suspension event was found for 34940 in this PIT artifact.

## JQUANTS_NAN_ROW_SEMANTICS

UNRESOLVED

Repository evidence proves that all-null price rows are accepted as raw-source-faithful no-price rows, but it does not define whether a J-Quants all-NaN daily quote row semantically means no trades, suspension, source-missing price, or another market state.

Observed schema evidence:

- `validate_records("daily_quotes", ...)` classifies an all-missing raw and adjusted OHLCV group as `VALID_NO_PRICE_ROW`.
- The classification summary includes `source_null_policy = raw_source_faithful_valid_no_price_rows_are_not_canonical_price_rows`.
- The 34940 four-row PIT-neighbor validation returned `valid_price_row_count = 2`, `valid_no_price_row_count = 2`, `partial_ohlcv_corruption_count = 0`, `invalid_numeric_row_count = 0`, `schema_corruption_count = 0`, and status `WARNING`.

This is enough to rule out local partial-field corruption, but not enough to assign external J-Quants market-state semantics.

## NORMALIZATION_DROP_REASON

valid_no_price_row_dropped_from_canonical_ohlcv

The normalizer uses adjusted fields `AdjO/AdjH/AdjL/AdjC/AdjVo` when complete, otherwise raw fields `O/H/L/C/Vo` when complete. For 34940 on 2022-12-08, both groups are all missing, so no canonical normalized row is emitted.

Focused normalization over 34940 for 2022-12-05 through 2022-12-08 returned:

- `input_record_count = 4`
- `output_record_count = 2`
- `adjusted_count = 2`
- `unadjusted_count = 0`
- `error_count = 0`
- `valid_no_price_dropped_count = 2`
- `duplicate_key_count = 0`
- sample warnings include `record=3 date=2022-12-08 code=34940 valid_no_price_row_dropped_from_canonical_ohlcv`

## NORMALIZATION_BEHAVIOR

CORRECT

Under current repo contract, the raw all-NaN row is source-valid but is not a canonical executable OHLCV price row. No evidence of schema/coercion defect, partial OHLCV corruption, duplicate key filtering, trading eligibility filtering, or adjustment-basis bug was found.

## RAW_SOURCE_INTEGRITY

PASS

Within materialized run-scoped evidence, the raw row has stable identity and lineage:

- `Date = 2022-12-08`
- `Code = 34940`
- `source = jquants`
- `endpoint = /v2/equities/bars/daily`
- `target_date = 2022-12-08`
- `pagination_page = 1`
- `fetched_at = 2026-08-10T10:25:09.112885+00:00`

The raw validator classified the all-null price row as source-valid no-price evidence rather than corruption. No local truncation, partial parse/coercion issue, duplicate target key, overwritten value, or partition/date extraction defect was found in the inspected artifacts.

This PASS is limited to local materialized artifact integrity. It does not prove the external source's market-state meaning.

## ALTERNATE_CANONICAL_SAME_DAY_PRICE_AUTHORITY

NOT_AVAILABLE

The submit adapter is bound to the run-scoped canonical normalized OHLCV path and failed 34940 with `missing or non-unique target session OHLCV row`. The 2022-12-07 planning reference close is PIT-valid for planning/reservation evidence, but it is not an approved same-day target-session execution price authority. No approved same-day alternate PIT source was found.

## HISTORICAL_SUBMIT_PRICE_AUTHORITY

HALT

Submit manifest evidence for 34940:

```json
{
  "accepted": false,
  "blocked": true,
  "pending_item_id": "strategy-5c7d2975b463ced32e60",
  "symbol": "34940",
  "side": "SELL",
  "quantity": 100.0,
  "reason": "missing or non-unique target session OHLCV row",
  "response_classification": {
    "broker_write": false,
    "historical_replay": true,
    "reason": "missing or non-unique target session OHLCV row",
    "simulation": true,
    "status": "HALT"
  }
}
```

The adapter diagnostic identifies:

- `adapter = HistoricalSubmitAdapter`
- `business_date = 2022-12-08`
- `evaluation_time = 2022-12-08T08:45:00+09:00`
- `ohlcv_path = .../raw_normalized/jquants/equities_bars_daily/data.parquet`
- `raw_ohlcv_path = .../raw/jquants/equities_bars_daily/data.parquet`

## ROOT_CAUSE_CLASSIFICATION

UNRESOLVED_DATA_AUTHORITY_GAP

Rationale:

- Not `NORMALIZATION_DEFECT`: normalization did exactly what the current schema/normalizer contract says for all-null price rows.
- Not `RAW_DATA_ACQUISITION_DEFECT`: local raw materialization is intact and schema-valid as source-faithful no-price evidence.
- Not `LISTING_CORPORATE_EVENT_STATE`: listed issues says listed, corporate-event facts say `KNOWN_NO_EVENT`, and the calendar says the exchange date was open.
- Not `MARKET_NON_TRADING_STATE` or `JQUANTS_VALID_NAN_MARKET_STATE`: repo evidence does not define the external market-state semantics of an all-NaN J-Quants daily quote row.

The remaining gap is that Runtime has no canonical same-day execution price authority and no canonical per-symbol status authority explaining why the listed symbol has an all-NaN quote row on an exchange trading day.

## DATA_REPAIR_CANDIDATE

NO

No local artifact corruption was identified. F1Z0 evidence does not justify modifying the raw row, fabricating a price, using the previous close as execution price, or changing normalization. The appropriate next work is source-semantics / per-symbol trading-status authority design, not data repair.

## FUTURE_INFORMATION_USED_FOR_DECISION

NO

Only 2022-12-08 run-scoped artifacts and PIT-safe neighboring dates through 2022-12-08 were used for decision classification.

## IMPLEMENTATION_CHANGED

NO

## FRESH_RUN_EXECUTED

NO

## RESUME_EXECUTED

NO

## REPLAY_EXECUTED

NO

## LONG_HISTORICAL_EXECUTED

NO

## GIT_DIFF_CHECK

PASS

## NEXT_TASK_RECOMMENDATION

Create a narrow design task for canonical per-symbol no-price / trading-status semantics. The task should decide how Runtime distinguishes valid no-trade or suspended-market states from unresolved source gaps for listed symbols on trading days, without adding a price fallback or changing the current fail-closed submit behavior prematurely.

Do not retry resume before the 34940 same-day execution-price authority gap is resolved.
