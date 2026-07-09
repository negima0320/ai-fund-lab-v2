# Phase14-E43 Broker Configuration Error Diagnostics Fix

## Purpose

Phase14-E42 stopped during Submit with `BrokerConfigurationError / PRE_SEND_FAILURE`.
The previous submit manifest only recorded the exception class, so an operator
could not tell whether the next action was to fix a credential file, the demo
endpoint, a local config directory, login URL handling, or account mapping.

Phase14-E43 adds secret-safe diagnostics to the Runtime v2 submit boundary.
No Submit retry, Broker Write, Production order, notification send, or launchd
change was performed.

## Implementation

Added `ai_fund_lab_v2.broker.config_diagnostics` as a secret-safe diagnostic
helper. It emits only booleans and coarse classifications, never credential
values, raw request/response payloads, full query strings, decrypted URLs, or
secrets.

Supported classifications:

- `missing_auth_id_file`
- `missing_private_key_file`
- `missing_second_password_file`
- `missing_local_config`
- `invalid_demo_url`
- `login_endpoint_missing`
- `account_mapping_missing`
- `demo_environment_mismatch`
- `unknown_configuration_error`

Runtime v2 submit result schema now carries:

- `configuration_diagnostic`
- `next_action`

The Tachibana Demo Submit adapter attaches these fields when a guard blocks
for environment/config reasons or when a `BrokerConfigurationError` happens
before/after send. The submit pipeline propagates the fields into
`item_results`, so run manifests expose the diagnostic at the failed item
level.

## Manifest Contract

Each affected submit item can now include:

- `configuration_diagnostic.classification`
- `configuration_diagnostic.configured`
- `configuration_diagnostic.environment`
- `configuration_diagnostic.demo_base_url_present`
- `configuration_diagnostic.local_config_present`
- `configuration_diagnostic.auth_id.configured`
- `configuration_diagnostic.auth_id_file.file_exists`
- `configuration_diagnostic.auth_id_file.file_readable`
- `configuration_diagnostic.private_key_file.file_exists`
- `configuration_diagnostic.private_key_file.file_readable`
- `configuration_diagnostic.second_password_file.file_exists`
- `configuration_diagnostic.second_password_file.file_readable`
- `next_action`

The payload intentionally omits secret values and full filesystem paths.

## E42 Re-evaluation

E42 existing artifacts were re-read without Submit or Broker Write.

Findings:

- E42 manifest recorded only `reason=BrokerConfigurationError`.
- E42 manifest did not preserve the exception message or configuration
  diagnostic sub-classification.
- Existing logs did not contain additional exception detail.
- Local secret-safe static diagnostic now reports:
  - `environment=demo`
  - `demo_base_url_present=true`
  - `local_config_present=true`
  - `auth_id_file.file_exists=true`
  - `auth_id_file.file_readable=true`
  - `private_key_file.file_exists=true`
  - `private_key_file.file_readable=true`
  - `second_password_file.file_exists=true`
  - `second_password_file.file_readable=true`
  - static classification: `configuration_ready`
- `TachibanaSecretLoader.load()` passed.
- `load_second_password_value_for_demo_order_only()` passed.

Conclusion:

The E42 failure was not caused by missing local config, missing auth id file,
missing private key file, missing second password file, demo URL mismatch, or
environment mismatch. The exact lower-level sub-cause cannot be recovered from
the old E42 manifest because the adapter previously discarded the
`BrokerConfigurationError` message. With this fix, a repeat failure will be
classified as login endpoint/decrypt, account mapping, or unknown configuration
with an operator `next_action`.

The concrete E43 root cause for operator unreadability was the submit adapter
and manifest schema dropping secret-safe configuration diagnostics.

## Tests

Executed:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m pytest tests/runtime_v2
```

Result:

- `349 passed`

Focused tests added:

- `tests/runtime_v2/test_phase14e43_broker_configuration_diagnostics.py`

## Prohibited Actions Check

- Additional Submit: not executed
- Broker Write: not executed
- Production order: not executed
- Notification real send: not executed
- launchd/plist change: not executed
- Secret values printed/saved: not performed
- Raw request/response saved: not performed

## Final Judgment

PHASE14E43_BROKER_CONFIGURATION_DIAGNOSTICS_FIXED
