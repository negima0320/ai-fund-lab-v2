# Phase14-E45 Submit Adapter BrokerConfigurationError Root Cause Audit

## Summary

- phase: Phase14-E45
- objective: identify the concrete pre-send `BrokerConfigurationError` root cause from E44.
- code_changed: false
- submit_reexecuted: false
- broker_write_executed: false
- production_order_executed: false
- notification_sent: false
- launchd_changed: false
- raw_request_saved: false
- raw_response_saved: false
- secret_value_output: false
- final_judgment: `PHASE14E45_BROKER_CONFIGURATION_ROOT_CAUSE_IDENTIFIED`

## Conclusion

The E44 `BrokerConfigurationError / unknown_configuration_error` was raised in
the login normalization path, before URL decrypt and before order send.

Direct raise condition:

- file: `src/ai_fund_lab_v2/broker/session.py`
- function: `normalize_login_ack`
- line: 48-49
- condition: `envelope.clmid != "CLMAuthLoginAck"`
- error: `BrokerConfigurationError("Tachibana login response was not CLMAuthLoginAck.")`

Secret-safe login-only reproduction showed:

- login HTTP request attempted: true
- login response received: true
- `clmid_is_login_ack`: false
- failure_stage: `api_error_envelope`
- api_error_number_present: true
- api_error_text_present: true
- api_error_text_classification: `present_nonempty`
- virtual_url_keys_present: false
- virtual_url_decryption_attempted: false
- virtual_url_decryption_success: false

Therefore:

- local config resolution: PASS
- demo URL/environment: PASS
- auth id file/private key/second password file presence: PASS
- login endpoint reached: PASS
- login response was not a valid `CLMAuthLoginAck`: FAIL
- URL decrypt: NOT REACHED
- account mapping: NOT REACHED
- order send: NOT REACHED

## E44 Manifest Evidence

Authoritative submit manifest:

`.runtime/runtime_state/run_manifest/2026-07-09/runtime-v2-submit-2026-07-09-20260708T222403.643587+0000.json`

Observed:

- item_count: `5`
- unique reason: `BrokerConfigurationError`
- unique configuration classification: `unknown_configuration_error`
- unique next_action: `inspect_sanitized_broker_configuration_and_rerun_submit_once_fixed`
- demo_submit_executed: `false`
- submitted_count: `0`
- raw_request_saved: `false`
- raw_response_saved: `false`
- secret_saved: `false`

## Local Pre-send Reproduction

The E44 Pending was used to reconstruct the first `RuntimeV2SubmitCommand`
without executing Submit.

Results:

- Pending state: `APPROVED`
- Pending item count: `5`
- selected item: `68970`
- Submit preflight: PASS
- adapter `_blocked_reason`: empty
- static configuration diagnostic: `configuration_ready`
- `TachibanaSecretLoader.load()`: PASS
- second password status: present/readable/nonempty
- login request shape:
  - endpoint scheme: `https`
  - endpoint host: `demo-kabuka.e-shiten.jp`
  - endpoint path: `/e_api_v4r9/auth/`
  - endpoint_is_demo: true
  - request CLMID is login request: true
  - credential_present: true
  - credential_length: 48
  - `p_no` present: true
  - `p_sd_date` present: true
- private key:
  - primary DER exists/readable
  - fallback PEM exists/readable and openssl-readable

This excludes missing local config, missing credential files, invalid demo URL,
and adapter guard failure.

## Login-only Reproduction

To avoid Submit/Broker Write, only the Tachibana demo auth login request was
executed and normalized. The raw response was not saved or printed.

Secret-safe observed classification:

```json
{
  "login_response_received": true,
  "clmid_is_login_ack": false,
  "failure_stage": "api_error_envelope",
  "api_error_number_present": true,
  "api_error_text_present": true,
  "api_error_text_classification": "present_nonempty",
  "virtual_url_keys_present": false,
  "virtual_url_decryption_attempted": false,
  "raw_response_saved": false,
  "secret_saved": false
}
```

The thrown exception is the `normalize_login_ack` CLMID guard, not decrypt.

## Runtime v2 Submit Adapter Raise Path

The Runtime v2 Tachibana Demo Submit adapter can encounter
`BrokerConfigurationError` in this sequence:

1. `settings.require_demo_environment()`
   - file: `broker/runtime_v2_demo_submit_adapter.py`
   - line: 130
   - possible raises from `broker/settings.py` line 78-81
   - E45 result: PASS

2. `TachibanaSecretLoader(settings).load()`
   - file: `broker/runtime_v2_demo_submit_adapter.py`
   - line: 131
   - possible raises from `broker/secrets.py` line 130, 136, 141, 143, 149, 151
   - E45 result: PASS

3. `auth_settings.require_private_key_file()`
   - file: `broker/runtime_v2_demo_submit_adapter.py`
   - line: 150
   - possible raise from `broker/settings.py` line 84-85
   - E45 result: PASS

4. `auth_client.login(decrypt_url=decryptor)`
   - file: `broker/runtime_v2_demo_submit_adapter.py`
   - line: 155
   - calls `broker/client.py` login then `broker/session.py` `normalize_login_ack`
   - E45 result: FAIL at login response CLMID validation

5. `TachibanaSecretLoader(auth_settings).load_second_password_value_for_demo_order_only()`
   - file: `broker/runtime_v2_demo_submit_adapter.py`
   - line: 162
   - possible raises from `broker/secrets.py` line 109, 113, 115
   - E45 result: NOT REACHED in failing submit path; local status was PASS

6. `builder.build_final_payload_with_second_password(...)`
   - file: `broker/runtime_v2_demo_submit_adapter.py`
   - line: 164
   - not a `BrokerConfigurationError` source in the audited files
   - E45 result: NOT REACHED

7. `DemoOrderBrokerTransport.request(payload)`
   - file: `broker/runtime_v2_demo_submit_adapter.py`
   - line: 179
   - order send boundary
   - E45 result: NOT REACHED; `send_started=false`

## Session / Settings / Secrets / Crypto Raise Inventory

### Settings

- `BrokerSettings.require_auth_id`
  - `settings.py` line 70-74
  - missing auth id
- `BrokerSettings.require_demo_environment`
  - `settings.py` line 78-81
  - non-demo environment or non-demo base URL
- `BrokerSettings.require_private_key_file`
  - `settings.py` line 84-85
  - private key path not resolved

### Secrets

- `TachibanaSecretLoader.load_second_password_value_for_demo_order_only`
  - `secrets.py` line 109
  - second password not configured/not ready
  - `secrets.py` line 113
  - second password unreadable
  - `secrets.py` line 115
  - second password empty
- `TachibanaSecretLoader._resolve_private_key_file`
  - `secrets.py` line 130
  - neither private key file nor local config path
- `TachibanaSecretLoader._read_auth_id_file`
  - `secrets.py` line 136
  - auth id missing
  - `secrets.py` line 141
  - auth id file unreadable
  - `secrets.py` line 143
  - auth id file empty
- `TachibanaSecretLoader._require_regular_file`
  - `secrets.py` line 149
  - required file absent
  - `secrets.py` line 151
  - required file inaccessible

### Session / Login Ack

- `normalize_login_ack`
  - `session.py` line 48-49
  - response CLMID is not `CLMAuthLoginAck`
  - E45 actual root cause
- `normalize_login_ack`
  - `session.py` line 50-51
  - login ack result is not success
- `_require_kinsyouhou_midoku_read`
  - `session.py` line 70-71
  - unread contract document flag
- `_decrypt_required`
  - `session.py` line 75-79
  - required virtual URL field missing
  - line 88
  - URL decrypt failed
  - line 90
  - decrypt returned empty value
- `_sanitize_decrypted_https_url`
  - `session.py` line 100-107
  - decrypted URL empty/invalid/non-demo
- `_strip_decrypted_url`
  - `session.py` line 132-135
  - null/control/non-printable decrypted URL
- `_validate_session_urls`
  - `session.py` line 154-162
  - decrypted session URL validation failure

### Crypto

- `OpenSslRsaOaepDecryptor.__call__`
  - `crypto.py` line 59
  - all decrypt attempts failed
- `_decrypt_with_cryptography`
  - `crypto.py` line 75
  - cryptography backend unavailable
  - line 83
  - invalid key format
  - line 91
  - encrypted URL decrypt failed
- `_decode_ciphertext`
  - `crypto.py` line 105
  - encrypted URL not valid base64
- `_decrypt_with_openssl`
  - `crypto.py` line 242
  - invalid key format
  - line 246
  - openssl decrypt failed

## Root Cause Classification

E44 failed at:

`adapter.submit -> auth_client.login -> normalize_login_ack -> CLMID guard`

Root cause category:

`login_ack_api_error_envelope`

Not root cause:

- `missing_auth_id_file`
- `missing_private_key_file`
- `missing_second_password_file`
- `missing_local_config`
- `invalid_demo_url`
- `demo_environment_mismatch`
- `login_endpoint_missing`
- `decrypt_failed`
- `account_mapping_missing`

The login endpoint is reachable, but the response is an API error envelope
rather than a login ack containing virtual session URLs.

## Proposed Fixes / Improvements

No code was changed in E45. Recommended follow-up only:

1. Extend E43 diagnostic classification:
   - add `login_response_not_login_ack`
   - add `login_api_error_envelope`
2. Include secret-safe login ack diagnostic in the manifest:
   - `clmid_is_login_ack`
   - `failure_stage`
   - `api_error_number_present`
   - `api_error_text_present`
   - `api_error_text_classification`
   - `virtual_url_keys_present`
   - `virtual_url_decryption_attempted`
3. Refine `next_action`:
   - for `login_api_error_envelope`: `check_tachibana_auth_id_contract_status_or_api_error_text`
4. Keep raw response and API error text values out of the manifest unless
   explicitly redacted/classified.

## Prohibited Actions Check

- Submit retry: not executed
- Broker order write: not executed
- Production order: not executed
- Notification real send: not executed
- launchd/plist change: not executed
- Runtime body change: not performed
- secret value output: not performed
- raw request/response save: not performed

## Final Judgment

`PHASE14E45_BROKER_CONFIGURATION_ROOT_CAUSE_IDENTIFIED`
