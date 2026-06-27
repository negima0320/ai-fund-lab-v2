# Phase10-L3 Tachibana Account POST Transport Compatibility Diagnosis

- status: FAIL_CLOSED_POST_BODY_MODE_NOT_PRIMARY
- created_at: 2026-06-27
- scope: account / balance POST transport compatibility diagnosis only
- live_transport_diagnosis_run_count: 1
- live_post_modes_tested: 2
- environment: demo

## 1. Summary

Phase10-L3 investigated whether `CLMZanKaiSummary` / `CLMZanKaiKanougaku` returned protocol/error keys because the Python transport differed from the official browser sample POST behavior.

Result:

```text
status=FAILED_READONLY
login=PASS
logout=PASS
current_mode=json_body
alternate_mode=form_urlencoded_json_string
current_mode_business_fields_present=false
alternate_mode_business_fields_present=false
current_mode_protocol_error_present=true
alternate_mode_protocol_error_present=true
orders_api_called=false
executions_api_called=false
quotes_api_called=false
raw_response_saved=false
request_body_values_saved=false
paper_ledger_updated=false
```

The official-sample-like POST mode did not cause business amount fields to appear. This weakens `POST_BODY_MODE_MISMATCH` / `CONTENT_TYPE_MISMATCH` as the primary cause.

The current primary classification remains:

```text
primary=UNKNOWN_PROTOCOL_ERROR
candidates=UNKNOWN_PROTOCOL_ERROR, ACCOUNT_PERMISSION_OR_STATE, DEMO_API_LIMITATION
```

## 2. Official Browser Sample Review

References checked:

- `https://www.e-shiten.jp/e_api/mfds_json_api_request_post.js`
- `https://www.e-shiten.jp/e_api/mfds_json_api_com.js`
- `https://www.e-shiten.jp/e_api/mfds_json_api_sample.html`
- `https://www.e-shiten.jp/e_api/mfds_json_api_refference.html`

Official sample behavior from `mfds_json_api_request_post.js`:

```text
v4r9 request parameter is compressed
compressed JSON is parsed and stringified
$.ajax is called with type='POST'
dataType='text'
data=stringified compressed JSON
contentType is not explicitly set
```

The sample therefore sends a JSON string body, but with jQuery's default content type rather than an explicitly declared `application/json`.

Current Python default before Phase10-L3:

```text
body_mode=json_body
body=JSON string of encoded payload
Content-Type=application/json; charset=utf-8
Accept=application/json
```

Added official-sample-like mode:

```text
body_mode=form_urlencoded_json_string
body=JSON string of encoded payload
Content-Type=application/x-www-form-urlencoded; charset=UTF-8
```

No request body values were saved in reports.

## 3. Implemented Transport Diagnosis

Updated `src/ai_fund_lab_v2/broker/transport.py`:

- Added `body_mode`.
- Kept default behavior as `json_body`.
- Added `form_urlencoded_json_string`.
- Added `text_plain_json` for future controlled diagnosis.
- Added `diagnose_post_shape` to record only non-secret shape metadata:
  - body mode
  - content type
  - method
  - endpoint type
  - header names
  - encoded payload key count
  - encoded payload key names
  - body length bucket
  - whether values were saved

Updated `src/ai_fund_lab_v2/broker/tachibana_account_smoke.py`:

- Added `run_tachibana_account_transport_diagnosis`.
- Added `classify_transport_compatibility`.
- The live diagnosis uses one login/session, runs exactly two POST modes, and logs out.

Updated `src/ai_fund_lab_v2/cli/tachibana_account_balance_smoke.py`:

- Added `--run-demo-account-transport-diagnosis`.
- Default execution remains skipped without explicit flag.

## 4. Live Diagnosis

Default skip check:

```text
status=SKIPPED
executed=false
```

Explicit live diagnosis executed once:

```text
TACHIBANA_API_READONLY_SMOKE_ENABLED=true PYTHONPATH=src python3 -m ai_fund_lab_v2.cli.tachibana_account_balance_smoke --run-demo-account-transport-diagnosis --report-filename phase10l3_tachibana_account_transport_diagnosis_result.json --source phase10l3_account_post_transport_compatibility_diagnosis
```

Result:

```text
status=FAILED_READONLY
executed=true
environment=demo
run_count=2
login=PASS
logout=PASS
```

Mode 1:

```text
body_mode=json_body
content_type=application/json; charset=utf-8
business_fields_present=false
protocol_error_present=true
raw_response_saved=false
request_body_values_saved=false
```

Mode 2:

```text
body_mode=form_urlencoded_json_string
content_type=application/x-www-form-urlencoded; charset=UTF-8
business_fields_present=false
protocol_error_present=true
raw_response_saved=false
request_body_values_saved=false
```

Both modes returned only sanitized protocol/error classifications and no business amount fields.

## 5. Cause Classification

Current classification:

```text
primary=UNKNOWN_PROTOCOL_ERROR
candidates=UNKNOWN_PROTOCOL_ERROR, ACCOUNT_PERMISSION_OR_STATE, DEMO_API_LIMITATION
```

Weakened candidates:

```text
POST_BODY_MODE_MISMATCH=false
CONTENT_TYPE_MISMATCH=false
ENDPOINT_TYPE_MISMATCH=not_supported_by_current_evidence
REQUEST_SHAPE_MISSING_FIELD=false
NORMALIZER_FIELD_MAPPING=false
```

The account/balance API still reaches the endpoint and returns structured protocol keys, but not business amount fields. Since the official-sample-like POST mode did not change the response shape, the remaining likely causes are account permission/state, demo API limitation, or an unknown protocol/API precondition.

## 6. Paper Test 2 Initial Cash Re-judgement

Paper Test 2 initial cash remains unresolved:

```text
paper_test2_initial_cash_candidate_status=UNRESOLVED_ACCOUNT_API_PROTOCOL_ERROR
cash_available_confirmed=false
do_not_initialize_with_zero_from_this_result=true
```

Do not initialize Paper Test 2 with 0 JPY from this account/balance API result.

## 7. Verification

Target pytest:

```text
PYTHONPATH=src python3 -m pytest tests/broker/test_broker_normalizer.py tests/broker/test_tachibana_phase10c_session_foundation.py -q
```

Result:

```text
92 passed
```

JSON validation:

```text
reports/phase_reports/phase10l3_tachibana_account_post_transport_compatibility_diagnosis.json
reports/phase_reports/phase10l3_tachibana_account_transport_diagnosis_result.json
```

Safety checks:

```text
secret canary: PASS
no forbidden CLMID audit: PASS
production_connected=false
orders_api_called=false
executions_api_called=false
quotes_api_called=false
paper_ledger_updated=false
paper_test2_ledger_initialized=false
```

## 8. Result

Phase10-L3 shows that browser-sample-like POST body/content-type compatibility alone does not resolve the account/balance protocol error.

Recommended next step:

```text
Phase10-L4 should investigate account API preconditions and demo account permission/state without persisting p_errno value, p_err body, raw response, or account/customer identifiers.
```
