# Phase23-AV Historical Calendar and Temporal Authority Contract Completion

## Primary Judgment

```text
PHASE23_AV_TEMPORAL_AUTHORITY_CONTRACT_COMPLETION_SHORT_VALIDATION_PASS
```

## Supporting Judgment

```text
HISTORICAL_CALENDAR_AUTHORITY
PREVIOUS_TRADING_DATE_AUTHORITY
CURRENT_VALUATION_TEMPORAL_AUTHORITY
PIT_VALIDATION
DATA_READINESS_TEMPORAL_PASS
READY_FOR_1BD_RUNTIME_VALIDATION
```

## Scope

対象は以下のみ。

```text
Historical Trading Calendar
Previous Trading Date
Current Valuation Temporal Authority
PIT
Data Readiness Temporal Contract
```

Reference Price、Portfolio Policy、Portfolio Construction、Position Sizing、Runtime Planning、Strategy Planning Authority、Safety、Pending、Submit、Broker、AIは変更していない。

## Root Cause

Phase23-AU F3は、Historical fixture / evidenceにHistorical Trading Calendar Authorityがmaterializeされていなかった。

そのため、

```text
historical_trading_calendar_authority_missing
↓
previous_trading_date = ""
↓
current_valuation_previous_trading_date_missing
↓
current_valuation_not_ready
```

となっていた。

Production-common resolverは既に以下を正しく要求していた。

```text
Historical Calendar authority must exist
Previous trading date must be derived from calendar
No fallback to business_date / latest / current snapshot
```

したがってProduction codeへfallbackを足す修正は行わず、fixture/evidence側をProduction Contractへ揃えた。

## Repair

`tests/runtime_v2/test_phase17_ba_submit_temporal_authority_contract.py`

- Historical submit fixtureに `logical_input_manifest.json` を追加。
- `logical_paths.trading_calendar` から `trading_calendar/data.jsonl` を参照。
- Calendar rowsにprevious trading dateとbusiness dateを明示。

`tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py`

- Current valuation pre-gate fixtureにcontract calendarを追加。
- historical asof viewにも `trading_calendar` authorityを追加。

`tests/runtime_v2/test_phase15as_data_readiness_semantic_consistency.py`

- Empty current fixtureの `position_state_as_of` をfeature dateへ揃えた。
- PM feature consumerのPIT guard `current_position_state_as_of_after_feature_target_date` を解消。

Production code変更:

```text
なし
```

## Authority Contract

Historical Calendar:

```text
producer = historical logical input / historical asof / contract calendar materialization
consumer = Data Readiness operation date resolver
artifact = logical_input_manifest.json / historical_asof_view.json / trading_calendar data
failure = historical_trading_calendar_authority_missing
```

Previous Trading Date:

```text
producer = _operation_date_from_calendar_file
resolution = max(calendar business day < business_date)
consumer = _current_valuation_temporal_authority
failure = historical_trading_calendar_previous_date_missing
```

Current Valuation Temporal Authority:

```text
producer = _current_valuation_temporal_authority
inputs = business_date, previous_trading_date, valuation_as_of, source_market_date, evaluation_time
previous-day ready = previous_trading_day_close_is_latest_available_at_morning_evaluation
same-day ready = same_day_current_valuation_refresh_available / business_date_current_valuation_ready
failure = current_valuation_previous_trading_date_missing
```

## Required Questions

AV-RQ1:

Historical Calendarは `logical_input_manifest.logical_paths.trading_calendar`、`historical_asof_view.authorities.trading_calendar`、またはcontract calendar artifactからData Readinessへ渡る。

AV-RQ2:

Previous Trading Dateは `_operation_date_from_calendar_file` がauthorized calendar rowsから決定する。

AV-RQ3:

Current ValuationはPrevious Trading Dateが無い場合fail-closedする。Business date固定やlatest fallbackはしない。

AV-RQ4:

F3はreal Production code gapではなく、fixture/evidence authority materialization gapだった。Production resolverは正しくfail-closedしていた。

## Validation

```text
py_compile: PASS
Data Readiness temporal subset: 19 passed
Historical Calendar / Current Valuation targeted: 37 passed
Reference Price / Strategy Planning expanded: 49 passed
```

Runtime rerun、fresh-run、resume、1BD、10BD、20BD、Broker Write、Runtime Switch、J-Quants取得は実施していない。

## Existing Run Preservation

Required historical runs were read-only. Hash preservation evidence was generated. Existing run artifacts were not mutated.

## Deliverables

Human:

```text
docs/phase_reports/phase23_av_historical_calendar_and_temporal_authority_contract_completion.md
```

Machine:

```text
reports/phase_reports/phase23_av_historical_calendar_and_temporal_authority_contract_completion.json
```

Evidence:

```text
reports/phase23_av_historical_calendar_and_temporal_authority_contract_completion/
```

## 1BD Gate

Success criteria satisfied:

```text
Historical Calendar authority resolves
Previous Trading Date resolves
Current Valuation temporal authority resolves
PIT contract passes
Data Readiness temporal subset passes
F3 resolved
Reference Price path remains valid
Existing runs preserved
```

```text
READY_FOR_1BD_RUNTIME_VALIDATION = YES
```
