# Phase4-AY Border Date Availability Audit / Fetch Start Correction

- status: `OK`
- readiness_status: `READY_FOR_LONG_HISTORY_REQUEST_REGENERATION`
- checked_date_range: `2021-06-01` to `2021-06-14`
- first_successful_date: `2021-06-14`
- first_available_trading_date: `2021-06-14`
- corrected_fetch_start_date: `2021-06-14`
- contradiction_resolved: `True`

## Date Status Report

```json
[
  {
    "available": false,
    "date": "2021-06-01",
    "http_status": 400,
    "is_weekday": true,
    "payload_keys": [],
    "request": {
      "date_format": "YYYY-MM-DD",
      "endpoint": "/v2/equities/bars/daily",
      "method": "GET",
      "params": {
        "code": null,
        "date": "2021-06-01",
        "pagination_key": null
      }
    },
    "response_message_sanitized": "Your subscription covers the following dates: 2021-06-13 ~ . If you want more data, please check other plans:https://jpx-jquants.com/#dataset",
    "row_count": 0,
    "trading_day_status": "calendar_missing_weekday",
    "weekday": "Tuesday"
  },
  {
    "available": false,
    "date": "2021-06-02",
    "http_status": 400,
    "is_weekday": true,
    "payload_keys": [],
    "request": {
      "date_format": "YYYY-MM-DD",
      "endpoint": "/v2/equities/bars/daily",
      "method": "GET",
      "params": {
        "code": null,
        "date": "2021-06-02",
        "pagination_key": null
      }
    },
    "response_message_sanitized": "Your subscription covers the following dates: 2021-06-13 ~ . If you want more data, please check other plans:https://jpx-jquants.com/#dataset",
    "row_count": 0,
    "trading_day_status": "calendar_missing_weekday",
    "weekday": "Wednesday"
  },
  {
    "available": false,
    "date": "2021-06-03",
    "http_status": 400,
    "is_weekday": true,
    "payload_keys": [],
    "request": {
      "date_format": "YYYY-MM-DD",
      "endpoint": "/v2/equities/bars/daily",
      "method": "GET",
      "params": {
        "code": null,
        "date": "2021-06-03",
        "pagination_key": null
      }
    },
    "response_message_sanitized": "Your subscription covers the following dates: 2021-06-13 ~ . If you want more data, please check other plans:https://jpx-jquants.com/#dataset",
    "row_count": 0,
    "trading_day_status": "calendar_missing_weekday",
    "weekday": "Thursday"
  },
  {
    "available": false,
    "date": "2021-06-04",
    "http_status": 400,
    "is_weekday": true,
    "payload_keys": [],
    "request": {
      "date_format": "YYYY-MM-DD",
      "endpoint": "/v2/equities/bars/daily",
      "method": "GET",
      "params": {
        "code": null,
        "date": "2021-06-04",
        "pagination_key": null
      }
    },
    "response_message_sanitized": "Your subscription covers the following dates: 2021-06-13 ~ . If you want more data, please check other plans:https://jpx-jquants.com/#dataset",
    "row_count": 0,
    "trading_day_status": "calendar_missing_weekday",
    "weekday": "Friday"
  },
  {
    "available": false,
    "date": "2021-06-05",
    "http_status": 400,
    "is_weekday": false,
    "payload_keys": [],
    "request": {
      "date_format": "YYYY-MM-DD",
      "endpoint": "/v2/equities/bars/daily",
      "method": "GET",
      "params": {
        "code": null,
        "date": "2021-06-05",
        "pagination_key": null
      }
    },
    "response_message_sanitized": "Your subscription covers the following dates: 2021-06-13 ~ . If you want more data, please check other plans:https://jpx-jquants.com/#dataset",
    "row_count": 0,
    "trading_day_status": "calendar_missing_weekend",
    "weekday": "Saturday"
  },
  {
    "available": false,
    "date": "2021-06-06",
    "http_status": 400,
    "is_weekday": false,
    "payload_keys": [],
    "request": {
      "date_format": "YYYY-MM-DD",
      "endpoint": "/v2/equities/bars/daily",
      "method": "GET",
      "params": {
        "code": null,
        "date": "2021-06-06",
        "pagination_key": null
      }
    },
    "response_message_sanitized": "Your subscription covers the following dates: 2021-06-13 ~ . If you want more data, please check other plans:https://jpx-jquants.com/#dataset",
    "row_count": 0,
    "trading_day_status": "calendar_missing_weekend",
    "weekday": "Sunday"
  },
  {
    "available": false,
    "date": "2021-06-07",
    "http_status": 400,
    "is_weekday": true,
    "payload_keys": [],
    "request": {
      "date_format": "YYYY-MM-DD",
      "endpoint": "/v2/equities/bars/daily",
      "method": "GET",
      "params": {
        "code": null,
        "date": "2021-06-07",
        "pagination_key": null
      }
    },
    "response_message_sanitized": "Your subscription covers the following dates: 2021-06-13 ~ . If you want more data, please check other plans:https://jpx-jquants.com/#dataset",
    "row_count": 0,
    "trading_day_status": "calendar_missing_weekday",
    "weekday": "Monday"
  },
  {
    "available": false,
    "date": "2021-06-08",
    "http_status": 400,
    "is_weekday": true,
    "payload_keys": [],
    "request": {
      "date_format": "YYYY-MM-DD",
      "endpoint": "/v2/equities/bars/daily",
      "method": "GET",
      "params": {
        "code": null,
        "date": "2021-06-08",
        "pagination_key": null
      }
    },
    "response_message_sanitized": "Your subscription covers the following dates: 2021-06-13 ~ . If you want more data, please check other plans:https://jpx-jquants.com/#dataset",
    "row_count": 0,
    "trading_day_status": "calendar_missing_weekday",
    "weekday": "Tuesday"
  },
  {
    "available": false,
    "date": "2021-06-09",
    "http_status": 400,
    "is_weekday": true,
    "payload_keys": [],
    "request": {
      "date_format": "YYYY-MM-DD",
      "endpoint": "/v2/equities/bars/daily",
      "method": "GET",
      "params": {
        "code": null,
        "date": "2021-06-09",
        "pagination_key": null
      }
    },
    "response_message_sanitized": "Your subscription covers the following dates: 2021-06-13 ~ . If you want more data, please check other plans:https://jpx-jquants.com/#dataset",
    "row_count": 0,
    "trading_day_status": "calendar_missing_weekday",
    "weekday": "Wednesday"
  },
  {
    "available": false,
    "date": "2021-06-10",
    "http_status": 400,
    "is_weekday": true,
    "payload_keys": [],
    "request": {
      "date_format": "YYYY-MM-DD",
      "endpoint": "/v2/equities/bars/daily",
      "method": "GET",
      "params": {
        "code": null,
        "date": "2021-06-10",
        "pagination_key": null
      }
    },
    "response_message_sanitized": "Your subscription covers the following dates: 2021-06-13 ~ . If you want more data, please check other plans:https://jpx-jquants.com/#dataset",
    "row_count": 0,
    "trading_day_status": "calendar_missing_weekday",
    "weekday": "Thursday"
  },
  {
    "available": false,
    "date": "2021-06-11",
    "http_status": 400,
    "is_weekday": true,
    "payload_keys": [],
    "request": {
      "date_format": "YYYY-MM-DD",
      "endpoint": "/v2/equities/bars/daily",
      "method": "GET",
      "params": {
        "code": null,
        "date": "2021-06-11",
        "pagination_key": null
      }
    },
    "response_message_sanitized": "Your subscription covers the following dates: 2021-06-13 ~ . If you want more data, please check other plans:https://jpx-jquants.com/#dataset",
    "row_count": 0,
    "trading_day_status": "calendar_missing_weekday",
    "weekday": "Friday"
  },
  {
    "available": false,
    "date": "2021-06-12",
    "http_status": 400,
    "is_weekday": false,
    "payload_keys": [],
    "request": {
      "date_format": "YYYY-MM-DD",
      "endpoint": "/v2/equities/bars/daily",
      "method": "GET",
      "params": {
        "code": null,
        "date": "2021-06-12",
        "pagination_key": null
      }
    },
    "response_message_sanitized": "Your subscription covers the following dates: 2021-06-13 ~ . If you want more data, please check other plans:https://jpx-jquants.com/#dataset",
    "row_count": 0,
    "trading_day_status": "calendar_missing_weekend",
    "weekday": "Saturday"
  },
  {
    "available": false,
    "date": "2021-06-13",
    "http_status": 200,
    "is_weekday": false,
    "payload_keys": [
      "data"
    ],
    "request": {
      "date_format": "YYYY-MM-DD",
      "endpoint": "/v2/equities/bars/daily",
      "method": "GET",
      "params": {
        "code": null,
        "date": "2021-06-13",
        "pagination_key": null
      }
    },
    "response_message_sanitized": "OK",
    "row_count": 0,
    "trading_day_status": "calendar_missing_weekend",
    "weekday": "Sunday"
  },
  {
    "available": true,
    "date": "2021-06-14",
    "http_status": 200,
    "is_weekday": true,
    "payload_keys": [
      "data"
    ],
    "request": {
      "date_format": "YYYY-MM-DD",
      "endpoint": "/v2/equities/bars/daily",
      "method": "GET",
      "params": {
        "code": null,
        "date": "2021-06-14",
        "pagination_key": null
      }
    },
    "response_message_sanitized": "OK",
    "row_count": 4108,
    "trading_day_status": "calendar_missing_weekday",
    "weekday": "Monday"
  }
]
```

## Request Diff

```json
{
  "checked_request": {
    "date_format": "YYYY-MM-DD",
    "endpoint": "/v2/equities/bars/daily",
    "method": "GET",
    "params": {
      "code": null,
      "date": "2021-06-01",
      "pagination_key": null
    }
  },
  "date_format_same": true,
  "endpoint_same": true,
  "method_same": true,
  "only_date_value_differs": true,
  "param_keys_compatible": true,
  "successful_reference_request_from_ad_or_ah": {
    "endpoint": "/v2/equities/bars/daily",
    "method": "GET",
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

## Root Cause

First available boundary date is later than 2021-06-01. Failed boundary messages: 2021-06-01 status=400 message=Your subscription covers the following dates: 2021-06-13 ~ . If you want more data, please check other plans:https://jpx-jquants.com/#dataset | 2021-06-02 status=400 message=Your subscription covers the following dates: 2021-06-13 ~ . If you want more data, please check other plans:https://jpx-jquants.com/#dataset | 2021-06-03 status=400 message=Your subscription covers the following dates: 2021-06-13 ~ . If you want more data, please check other plans:https://jpx-jquants.com/#dataset | 2021-06-04 status=400 message=Your subscription covers the following dates: 2021-06-13 ~ . If you want more data, please check other plans:https://jpx-jquants.com/#dataset | 2021-06-05 status=400 message=Your subscription covers the following dates: 2021-06-13 ~ . If you want more data, please check other plans:https://jpx-jquants.com/#dataset | 2021-06-06 status=400 message=Your subscription covers the following dates: 2021-06-13 ~ . If you want more data, please check other plans:https://jpx-jquants.com/#dataset | 2021-06-07 status=400 message=Your subscription covers the following dates: 2021-06-13 ~ . If you want more data, please check other plans:https://jpx-jquants.com/#dataset | 2021-06-08 status=400 message=Your subscription covers the following dates: 2021-06-13 ~ . If you want more data, please check other plans:https://jpx-jquants.com/#dataset

## Failed Manifest Quarantine Policy

Before Phase4-AZ/AX resume, exclude or move Phase4-AX FAILED manifests earlier than 2021-06-14 into a quarantine namespace so resume logic does not treat them as rerun targets.

## Scope Guard

- long_history_resume_fetch_executed: `False`
- normalized_rebuild_executed: `False`
- feature/label/dataset/training/inference/backtest/trading: `False`
- promotion_performed / reader_switch_performed: `False`
