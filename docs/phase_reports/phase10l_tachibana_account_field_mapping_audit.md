# Phase10-L Tachibana Account Field Mapping Audit

- status: PASS_WITH_REMAINING_API_RESPONSE_DIAGNOSIS
- created_at: 2026-06-27
- scope: account / balance field mapping only
- live_account_balance_run_count: 1
- environment: demo

## 1. Summary

Phase10-L investigated why Tachibana demo Web shows non-zero available amounts while the Broker Snapshot normalizer showed `cash_available=0` and `buying_power=0`.

Result:

```text
field_mapping_gap_found=true
field_mapping_fix_applied=true
live_account_balance_diagnosis=business_fields_missing_in_response
paper_ledger_updated=false
paper_test2_ledger_initialized=false
orders_api_called=false
executions_api_called=false
quotes_api_called=false
```

The code had a real mapping gap: `CLMZanKaiKanougaku` official response uses summary fields such as `sSummaryGenkabuKaituke`, but the normalizer only checked older/generic names such as `sGenbutuKabuKaituke` and `sKanougaku`.

After adding the official field names and v4r9 numeric mappings, the explicit demo account/balance diagnosis still returned only protocol/error keys and no business amount fields. Raw response values were not saved. This means the remaining live discrepancy is not explained by normalizer field names alone; it is now classified as `business_fields_missing_in_response`.

## 2. Official Reference Review

References checked:

- `https://www.e-shiten.jp/e_api/mfds_json_api_refference.html`
- `https://www.e-shiten.jp/e_api/mfds_json_api_ref_text.html`
- `https://www.e-shiten.jp/e_api/mfds_json_api_compress_v4r9.js`

Confirmed `CLMZanKaiKanougaku` response fields:

```text
sSummaryUpdate
sSummaryGenkabuKaituke
sSummaryNseityouTousiKanougaku
sHusokukinHasseiFlg
```

Confirmed meanings from the official reference:

```text
sSummaryGenkabuKaituke: 株式現物買付可能額
sSummaryNseityouTousiKanougaku: NISA成長投資可能額
```

Confirmed relevant v4r9 numeric mappings:

```text
CLMZanKaiKanougaku=57
CLMZanKaiSummary=60
sGenbutuKabuKaituke=382
sIPOKounyu=455
sNisaKaitukeKanougaku=578
sNseityouTousiKanougaku=582
sSinyouSinkidate=722
sSinyouSinkidateKanougaku=723
sSummaryGenkabuKaituke=743
sSummaryNisaKaitukeKanougaku=744
sSummaryNseityouTousiKanougaku=745
sSummaryUpdate=747
sSyukkin=754
sSyukkinKanougaku=766
```

## 3. Implemented Mapping Fix

Updated `src/ai_fund_lab_v2/broker/tachibana_codec.py`:

- Added official v4r9 IDs for summary buying power, withdrawal, IPO, margin, and NISA-related fields.

Updated `src/ai_fund_lab_v2/broker/normalizer.py`:

- `buying_power` now prefers `sSummaryGenkabuKaituke`.
- `withdrawable_cash` now accepts `sSyukkin` and `sSyukkinKanougaku`.
- `cash_available` for account summary now accepts withdrawal/cash fields.
- Added optional normalized fields:
  - `margin_buying_power`
  - `ipo_buying_power`
  - `nisa_growth_capacity`

Updated `src/ai_fund_lab_v2/broker/models.py`:

- Extended `BrokerBalanceSnapshot` with the optional fields above.

## 4. Key-level Diagnosis

Added account/balance key-level diagnosis in `src/ai_fund_lab_v2/broker/tachibana_account_smoke.py`.

It saves only:

```text
key name, with sensitive-looking names redacted
value type
numeric convertibility
digit length
zero / nonzero / non-numeric classification
candidate field name when matching a Web display amount
```

It does not save:

```text
raw response
raw values
account/customer id plaintext
auth id
private key
virtual URL
```

## 5. Live Demo Diagnosis

Executed once:

```text
TACHIBANA_API_READONLY_SMOKE_ENABLED=true PYTHONPATH=src python3 -m ai_fund_lab_v2.cli.tachibana_account_balance_smoke --run-demo-account-balance --report-filename phase10l_tachibana_account_field_mapping_diagnosis_result.json --source phase10l_account_field_mapping_audit
```

Result:

```text
status=PASS
executed=true
environment=demo
login=PASS
logout=PASS
account_api_called=true
balance_api_called=true
positions_api_called=false
orders_api_called=false
executions_api_called=false
quotes_api_called=false
raw_response_saved=false
```

Diagnosis summary:

```text
CLMZanKaiSummary business amount fields present=false
CLMZanKaiKanougaku business amount fields present=false
web_cash_buying_power candidate match=false
web_withdrawable_cash candidate match=false
web_ipo_buying_power candidate match=false
web_margin_buying_power candidate match=false
```

The response contained only protocol/error keys after decompression:

```text
p_err
p_errno
p_no
p_rv_date
p_sd_date
sCLMID
```

No raw values were stored, so `p_errno` / `p_err` content is not available in reports. The next diagnosis should classify the API error number without saving its value, or verify whether request parameters / endpoint assumptions for these two CLMIDs differ from the current builder.

## 6. Paper Test 2 Initial Cash Re-judgement

Current normalized live result remains:

```text
cash_available=0
buying_power=0
withdrawable_cash=0
margin_buying_power=0
ipo_buying_power=0
nisa_growth_capacity=0
```

Because the business fields were absent in the live response, this result should not be treated as a confirmed zero-balance account. It should be treated as:

```text
paper_test2_initial_cash_candidate_status=UNRESOLVED_ACCOUNT_API_BUSINESS_FIELDS_MISSING
```

Do not initialize Paper Test 2 with 0 JPY solely from this account/balance API response while the Web UI shows non-zero amounts.

## 7. Verification

Target pytest:

```text
PYTHONPATH=src python3 -m pytest tests/broker/test_broker_normalizer.py tests/broker/test_tachibana_phase10c_session_foundation.py -q
```

Result:

```text
83 passed
```

JSON validation:

```text
reports/phase_reports/phase10l_tachibana_account_field_mapping_audit.json
reports/phase_reports/phase10l_tachibana_account_field_mapping_diagnosis_result.json
```

Safety checks:

```text
secret canary: PASS
no forbidden CLMID audit: PASS
snapshot schema validation: NOT_RUN_NO_SNAPSHOT_UPDATE
```

Broker Snapshot was not refreshed in Phase10-L because the current task explicitly forbids orders / executions / quotes retrieval. Running the existing snapshot CLI would fetch those endpoints.

## 8. Result

Phase10-L fixed the official field mapping gap and added safe diagnosis. The remaining discrepancy is now narrowed to the live account/balance response shape: expected business amount fields were not returned in this run.

Recommended next step:

```text
Phase10-L2 should diagnose p_errno / p_err by classification only and verify whether CLMZanKaiSummary / CLMZanKaiKanougaku require an adjusted request shape or endpoint handling.
```
