# Phase4-AX2 HTTP400 Root Cause Audit

- status: `OK`
- readiness_status: `FETCH_START_DATE_OUT_OF_RANGE`
- suspected_root_cause: `FETCH_START_DATE_OUT_OF_RANGE`
- first_failed_request: `{'target_date': '2021-03-09', 'phase': 'Phase4-AX', 'status': 'FAILED', 'endpoint': '/v2/equities/bars/daily', 'method': 'GET', 'params': {'code': None, 'date': '2021-03-09'}, 'page_count': 0, 'row_count': 0, 'error_message': 'J-Quants request failed: endpoint=/v2/equities/bars/daily status=400'}`
- failed_status_codes: `['400', 'url_error']`
- adjusted_fetch_start_date_if_needed: `2021-06-14`
- safe_to_resume: `False`

## Request Diff Summary

```json
{
  "aw_first_request_endpoint": "/v2/equities/bars/daily",
  "aw_first_request_method": "GET",
  "aw_first_request_params": {
    "code": null,
    "date": "2021-03-09",
    "pagination_key": null
  },
  "aw_generator_matches_manifest_shape": true,
  "date_format_same": true,
  "endpoint_same": true,
  "failed_request": {
    "endpoint": "/v2/equities/bars/daily",
    "error_message": "J-Quants request failed: endpoint=/v2/equities/bars/daily status=400",
    "method": "GET",
    "page_count": 0,
    "params": {
      "code": null,
      "date": "2021-03-09"
    },
    "phase": "Phase4-AX",
    "row_count": 0,
    "status": "FAILED",
    "target_date": "2021-03-09"
  },
  "method_same": true,
  "only_date_value_differs": true,
  "param_keys_same": true,
  "reference_request": {
    "endpoint": "/v2/equities/bars/daily",
    "error_message": null,
    "method": "GET",
    "page_count": 1,
    "params": {
      "code": null,
      "date": "2026-03-02"
    },
    "phase": "Phase4-AH",
    "row_count": 4439,
    "status": "SUCCESS",
    "target_date": "2026-03-02"
  }
}
```

## Calendar Analysis

```json
{
  "aw_request_count": 1374,
  "calendar_issue_explains_first_400_block": false,
  "calendar_placeholder_may_include_jp_holidays": true,
  "calendar_source": "calendar_placeholder_weekday",
  "failed_dates_all_weekdays": true,
  "http400_dates_all_weekdays": true,
  "note": "The failed HTTP400 dates form a continuous weekday block before the first successful date, so holiday mixing alone is unlikely to explain the failures."
}
```

## Recommended Fix

Regenerate the Phase4-AW request artifact with fetch_start_date=2021-06-14, remove or ignore earlier FAILED manifests, then rerun Phase4-AX. Also recompute the effective formal training start after the 60-business-day lookback gate.

## Scope Guard

- additional_fetch_executed: `False`
- resume_fetch_executed: `False`
- normalized_rebuild_executed: `False`
- feature/label/dataset/training/backtest/trading: `False`
