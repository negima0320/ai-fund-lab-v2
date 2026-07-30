# Phase23-T: Official J-Quants Corporate Event Capability Alignment and Required Coverage Decision

## Primary Judgment

```text
PHASE23_T_IMPLEMENTATION_COMPLETE_OPERATOR_MATERIALIZATION_REQUIRED
```

## Secondary Judgment

```text
EARNINGS_CALENDAR_CONNECTED_AND_CORPORATE_ACTION_REQUIRED_OPTIONAL_SCOPE_DECIDED
```

Phase23-SのCorporate Event Source Authority gapを、公式J-Quants capabilityをPrimary Authorityとして再評価した。JPX公式J-Quants API pageは、OHLC、財務情報、上場銘柄一覧、配当、決算発表予定日、TDnet Document Dataを提供データ例として明示している。J-Quants Pro API Referenceでは、決算発表予定日・時刻情報が`PublicationDate`と`ScheduledDate`を分離し、予定日の変更履歴を削除せず追加する契約を示している。

本Phaseでは、Earnings CalendarをProduction-common Raw sourceとして追加し、Corporate Event consumerへPIT availability付きで接続した。Corporate Actions/TDnet系は、公式上は取得可能なsource familyが存在するが、現repoにはdeterministic classification契約とconsumer実装がないため、Required/Optional契約を明示してOptional scopeに留めた。

## Official Endpoint Inventory

| Endpoint | Source | Repo Status | Decision |
| --- | --- | --- | --- |
| `/v2/equities/bars/daily` | Stock Prices OHLC | Existing | Required market data |
| `/v2/equities/master` | List of Listed Companies | Existing | Required listing authority |
| `/v2/equities/earnings-calendar` | Earnings Announcement Schedule | Added | Required earnings schedule authority |
| `/v2/fins/summary` | Financial Information | Existing from Phase23-S | Required disclosure fact authority |
| `/v2/fins/details` | Pro equivalent `/v2/fins/fs_details` | Not implemented | Optional detail source |
| `/td/list` | TDnet add-on / Pro TDnet on Snowflake | Not implemented | Optional until deterministic classification exists |

## Implementation Summary

Added `earnings_calendar` to J-Quants endpoint capability, client fetcher, raw ingestion collection, fetch plan, CLI choices, raw schema validation, manifest path generation, and Corporate Event producer consumption.

Corporate Event producer now treats `jquants_earnings_schedule` as implemented when the raw file exists. It materializes `EARNINGS_ANNOUNCEMENT` scheduled events only when an availability authority (`PublicationDate`, compatible alias, `fetched_at`, or `target_date`) is present and `<= business_date`.

If availability authority is absent, the producer emits `earnings_calendar_availability_date_missing` and returns `REVIEW_REQUIRED`. Future publication rows are rejected with `future_earnings_calendar_row_rejected`; they are not consumed as events.

## Corporate Event Contract

Direct facts:

```text
listed_issues
earnings_calendar
fins_summary
```

Derived facts:

```text
daily_quotes adjusted/unadjusted differences
```

Derived facts may support adjustment awareness, but must not assert direct corporate action events unless a deterministic direct source is connected.

## PIT and Historical Boundary

Historical Runtime continues to consume pre-materialized raw/canonical artifacts only. No J-Quants network fetch is introduced for Historical runs.

PIT validation remains:

```text
availability_date <= business_date
latest_fallback_used = false
future_leakage_used = false
```

## Horizontal Audit

Corporate Event source coverage is now source-scoped:

```text
listing_status_coverage
earnings_calendar_coverage
financial_statement_coverage
stock_split_coverage
tdnet_disclosure_coverage
```

Missing coverage remains `UNKNOWN_DUE_TO_MISSING_COVERAGE`; it is not silently converted to `KNOWN_NO_EVENT`.

## Evidence

```text
reports/phase23_t_official_jquants_corporate_event_capability_alignment_and_required_coverage_decision/
```

Required evidence files were produced:

```text
official_jquants_endpoint_inventory.json
earnings_calendar_official_contract.json
earnings_calendar_repository_gap.json
corporate_action_capability_matrix.json
direct_vs_derived_event_contract.json
corporate_event_required_optional_source_decision.json
earnings_calendar_raw_canonical_pipeline.json
corporate_event_source_scoped_coverage.json
symbol_scoped_downstream_contract.json
quantity_resolution_post_contract_validation.json
operator_materialization_command.json
phase23_p_q_r_s_regression.json
short_validation_results.json
modified_files.json
```

Machine report:

```text
reports/phase_reports/phase23_t_official_jquants_corporate_event_capability_alignment_and_required_coverage_decision.json
```

## Short Validation

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_pycache python3 -m py_compile ...
PASS
```

```text
python3 -m pytest tests/test_jquants_client.py tests/test_jquants_raw_ingestion.py tests/test_fetch_jquants_daily_cli.py tests/test_schema_validation.py tests/test_jquants_api_common_fetch_policy.py tests/strategy/test_phase22_aa_corporate_event.py
59 passed
```

```text
python3 -m pytest tests/runtime_v2/test_phase23_i_strategy_planning_authority.py tests/runtime_v2/test_phase23_j_strategy_authority_gate.py tests/runtime_v2/test_phase23_l_historical_accepted_generation_entrypoint.py tests/runtime_v2/test_phase23_q_daily_scheduler_historical_mode.py tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py
16 passed
```

## 10BD Gate

```text
NOT_READY_FOR_10BD_OPERATOR_MATERIALIZATION_REQUIRED
```

Reason:

```text
Implementation is connected, but operator-owned real data materialization for earnings_calendar and fins_summary is still required before 10BD.
```

No 10BD, 20BD, 1-year, 3-year, 4-year, Broker Write, Runtime Switch, or live J-Quants fetch was executed.
