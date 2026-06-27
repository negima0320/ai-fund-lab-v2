# Phase10-L4 Tachibana Account Protocol Error Reveal

- status: ROOT_CAUSE_IDENTIFIED_P_NO_SEQUENCE
- created_at: 2026-06-27
- scope: account / balance protocol error reveal only
- live_error_reveal_run_count: 1
- environment: demo

## 1. Summary

Phase10-L4 revealed the protocol error returned by `CLMZanKaiSummary` and `CLMZanKaiKanougaku`.

Result:

```text
status=FAILED_READONLY
login=PASS
logout=PASS
p_errno_saved=true
p_err_saved=true
raw_response_saved=false
request_body_values_saved=false
orders_api_called=false
executions_api_called=false
quotes_api_called=false
paper_ledger_updated=false
```

Both account/balance CLMIDs returned:

```text
p_errno=6
p_err=引数（p_no:[1] <= 前要求.p_no:[1]）エラー。
```

This strongly identifies the root cause as a request sequence precondition failure: `p_no` is not increasing across requests in the session.

## 2. Official Reference / Sample Alignment

Official sample behavior checked:

- `mfds_json_api_com.js` keeps a shared `_p_no` counter.
- `get_no()` increments `_p_no` for each request.
- Generic `request(pi_prm)` also injects a new incremented `p_no`.
- Sample response handling treats `p_errno == "0"` as success and non-zero `p_errno` as error.

Relevant implication:

```text
p_no must be monotonically increasing across requests within the active API flow.
```

The revealed error explicitly says the current request `p_no` was not greater than the previous request `p_no`.

## 3. Live Reveal

Executed once:

```text
TACHIBANA_API_READONLY_SMOKE_ENABLED=true PYTHONPATH=src python3 -m ai_fund_lab_v2.cli.tachibana_account_balance_smoke --run-demo-account-error-reveal --report-filename phase10l4_tachibana_account_error_reveal_result.json --source phase10l4_account_protocol_error_reveal
```

Result:

```text
status=FAILED_READONLY
executed=true
environment=demo
login=PASS
logout=PASS
```

Revealed errors:

```text
CLMZanKaiSummary:
  p_errno=6
  p_err=引数（p_no:[1] <= 前要求.p_no:[1]）エラー。
  business_fields_present=false
  endpoint_type=request_url
  body_mode=json_body

CLMZanKaiKanougaku:
  p_errno=6
  p_err=引数（p_no:[1] <= 前要求.p_no:[1]）エラー。
  business_fields_present=false
  endpoint_type=request_url
  body_mode=json_body
```

Only `p_errno` and `p_err` were revealed. Raw response, auth id, private key, virtual URL, account/customer id, order number, execution id, and request body values were not saved.

## 4. Root Cause

The current client/build flow can recreate a fresh `TachibanaRequestBuilder` for each call when no explicit builder is attached:

```text
TachibanaReadOnlyClient.request_builder -> self.builder or TachibanaRequestBuilder(self.settings)
```

Because a new builder starts `sequence_no=0`, multiple live requests can be sent with `p_no=1`.

Observed impact:

```text
login request uses p_no=1
CLMZanKaiSummary also uses p_no=1
CLMZanKaiKanougaku also uses p_no=1
server rejects with p_errno=6
business fields are not returned
```

This explains why Phase10-L/L2/L3 saw only protocol/error keys despite correct CLMID, endpoint, POST mode, and field mapping.

## 5. Cause Classification

Current classification:

```text
primary=REQUEST_PRECONDITION_MISSING
candidates=REQUEST_PRECONDITION_MISSING, ACCOUNT_PERMISSION_OR_STATE
p_errno_values=6
business_fields_present=false
```

Weakened candidates:

```text
DEMO_API_LIMITATION=not_primary
POST_BODY_MODE_MISMATCH=false
CONTENT_TYPE_MISMATCH=false
NORMALIZER_FIELD_MAPPING=false
INVALID_CLMID_FOR_DEMO=false
API_SPEC_MISMATCH=false
```

## 6. Fix Proposal

Recommended Phase10-L5 fix:

```text
Make p_no monotonic across the login/session/account request flow.
```

Candidate implementation:

- Persist one `TachibanaRequestBuilder` instance per `TachibanaReadOnlyClient`.
- Or introduce a shared sequence counter/session request context used by login, account, positions, orders, executions, and quotes.
- Ensure login, logout, account/balance, and later read-only calls all consume increasing `p_no`.
- Add mock tests proving consecutive client calls emit `p_no=1`, `p_no=2`, `p_no=3`, ...
- Re-run account/balance live smoke once after the fix.

Do not change CLMID mapping or account/balance normalizer until the sequence fix is verified.

## 7. Paper Test 2 Initial Cash

Paper Test 2 initial cash remains unresolved, but the cause is now actionable:

```text
paper_test2_initial_cash_candidate_status=BLOCKED_BY_P_NO_SEQUENCE_BUG
do_not_initialize_with_zero_from_this_result=true
```

Once Phase10-L5 fixes `p_no` monotonic sequencing, account/balance read-only smoke should be retried once. If business fields appear, Paper Test 2 initial cash can be re-judged from API data.

## 8. Verification

Target pytest:

```text
PYTHONPATH=src python3 -m pytest tests/broker/test_broker_normalizer.py tests/broker/test_tachibana_phase10c_session_foundation.py -q
```

Result:

```text
96 passed
```

JSON validation:

```text
reports/phase_reports/phase10l4_tachibana_account_protocol_error_reveal.json
reports/phase_reports/phase10l4_tachibana_account_error_reveal_result.json
```

Safety checks:

```text
secret canary: PASS
no forbidden CLMID audit: PASS
raw_response_saved=false
request_body_values_saved=false
auth_id_saved=false
private_key_saved=false
virtual_url_saved=false
```

## 9. Result

Phase10-L4 identified the account/balance failure as a `p_no` sequence precondition error, not a balance field mapping problem, request shape problem, or POST content-type mismatch.

Next step:

```text
Phase10-L5: Tachibana p_no Monotonic Sequence Fix
```
