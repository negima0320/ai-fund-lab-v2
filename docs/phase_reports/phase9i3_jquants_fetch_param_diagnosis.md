# Phase9-I3 J-Quants Fetch Parameter Diagnosis

- judgment: PARTIAL_AVAILABLE
- requested_from_date: 2026-06-02
- requested_to_date: 2026-06-16
- latest_available_date: 2026-06-15
- data_until: 2026-06-15
- sample_single_date: 2026-06-16
- allow_api_fetch: True
- recommended_fetch_mode: per-date

## Summary

Phase9-I2 の HTTP 400 は、credential / network 全体の失敗ではなく、daily_quotes の全銘柄 range fetch に対する parameter / endpoint usage mismatch の可能性が高い。

実際の診断では、`/v2/equities/bars/daily` に `from` / `to` を指定した range fetch は HTTP 400 になった。一方で、同endpointに `date=2026-06-16` を指定した single-date fetch は HTTP 200 相当で成功し、row_count は 0 だった。

このため、Phase9 の daily_quotes 更新方式は `from/to` 一括取得ではなく、営業日ごとの `date` 単日取得を採用する。

2026-06-16 は当日であり、daily_quotes はまだ未配信の可能性がある。今回の扱いでは、2026-06-16 は `DATA_NOT_YET_AVAILABLE` 相当として `not_yet_available_dates` に記録し、即時の完全失敗とはしない。

## Checks

| name | endpoint | params | response_status | rows | classification |
| --- | --- | --- | --- | ---: | --- |
| daily_quotes_range | `/v2/equities/bars/daily` | `{"from": "2026-06-02", "to": "2026-06-16"}` | ERROR | 0 | http_400_bad_request_or_out_of_range |
| daily_quotes_single_date | `/v2/equities/bars/daily` | `{"date": "2026-06-16"}` | OK | 0 |  |
| listed_info_date | `/v2/equities/master` | `{"date": "2026-06-16"}` | OK | 4446 |  |
| trading_calendar_range | `/v2/markets/calendar` | `{"from": "2026-06-02", "to": "2026-06-16"}` | OK | 15 |  |

## Fixed Fetch Policy

- daily_quotes: `date=YYYY-MM-DD` の per-date fetch
- trading_calendar がある場合は `HolDiv=1` の営業日のみを daily_quotes fetch 対象にする
- trading_calendar が古い、または利用できない場合は暫定的に土日を除外する
- listed_info: `date=YYYY-MM-DD`
- trading_calendar: `from=YYYY-MM-DD` / `to=YYYY-MM-DD`
- requested_to_date と data_until は分離して記録する
- 末尾日の daily_quotes が 0 rows の場合は、当日未配信の可能性として `not_yet_available_dates` に記録する
- 成功日だけ raw / normalized に反映する
- 全日失敗、または単日 date 指定でも HTTP 400 が続く場合は `API_PARAM_ERROR` または `FETCH_FAILED` とする

## Per-Date Fetch Result

- fetch_mode: per-date
- status: PARTIAL_AVAILABLE
- requested_from_date: 2026-06-02
- requested_to_date: 2026-06-16
- latest_successful_daily_quotes_date: 2026-06-15
- latest_normalized_daily_quotes_date: 2026-06-15
- latest_listed_info_date: 2026-06-16
- latest_trading_calendar_date: 2026-06-16
- data_until: 2026-06-15
- not_yet_available_dates: 2026-06-16
- failed_dates: none
- unavailable_dates: none

| endpoint | status | existing_latest | fetched_rows | rows | max_date |
| --- | --- | ---: | ---: | ---: | ---: |
| daily_quotes | COMPLETED | 2026-06-01 | 44491 | 48940 | 2026-06-15 |
| listed_info | COMPLETED | 2026-06-01 | 4446 | 8895 | 2026-06-16 |
| trading_calendar | COMPLETED | 2026-06-07 | 15 | 81 | 2026-06-16 |

## Readiness

### Requested To Date

- decision_for: 2026-06-16
- readiness_status: NOT_READY
- readiness_data_until: 2026-06-15
- blocked_reasons: data_until_before_decision_for

### Latest Available Date

- decision_for: 2026-06-15
- readiness_status: READY
- readiness_data_until: 2026-06-15
- blocked_reasons: none

## Judgment

Final judgment:

```text
PARTIAL_AVAILABLE
```

理由:

- daily_quotes は 2026-06-15 まで取得・正規化できた
- 2026-06-16 は single-date fetch 自体は成功したが 0 rows であり、当日未配信として扱う
- listed_info と trading_calendar は 2026-06-16 まで取得できた
- 2026-06-15 基準では market data readiness が READY
- requested_to_date である 2026-06-16 基準では daily_quotes 未配信により NOT_READY

## Next Actions

- Phase9-J では `data_until=2026-06-15` を基準に feature artifact 再生成可否を確認する
- 2026-06-16 daily_quotes は配信後に再取得する
- Daily Operation Runner 側では requested_to_date と latest_available_date を分離して扱う
- 末尾未配信日のみであれば、latest_available_date 基準の運用可否を明示する
- `daily_quotes_normalization_status=ERROR` warning は、既存raw混在分の正規化skip由来かを追加確認する

## Safety

- secret_leakage_detected: False
- broker_order_api_called: False
- open_d_started: False
- unlock_trade_called: False
- paper_ledger_fill_executed: False
- virtual_fill_executed: False
- feature_generation_executed: False
- model_retraining_executed: False
- inference_executed: False
