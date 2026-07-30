# Phase23-U: Production Operations Command Runbook and Corporate Event Materialization Procedure

## 1. Primary Judgment

```text
PHASE23_U_OPERATIONS_RUNBOOK_AND_CORPORATE_EVENT_MATERIALIZATION_PROCEDURE_COMPLETE
```

## 2. Phase23 Status

```text
PHASE23_CONTINUES
```

Phase23 is not closed. No Phase23 closure material, Phase24 handoff, 10BD gate open, Runtime Switch, Broker Write, or long Runtime Test was performed.

## 3. Operations Documentation Inventory

The existing operations documentation was inventoried and classified. The permanent Operations SoT is now:

```text
docs/03_operations/README.md
```

Existing current operator documents:

```text
docs/03_operations/runtime_test_command_guide.md
docs/operations/demo_daily_operation_runbook.md
```

New permanent J-Quants runbook:

```text
docs/03_operations/jquants_data_operations_runbook.md
```

Inventory evidence:

```text
reports/phase23_u_production_operations_command_runbook_and_corporate_event_materialization_procedure/operations_documentation_inventory.json
```

## 4. Formal Operations SoT

Created:

```text
docs/03_operations/README.md
```

It separates permanent operator procedures from Phase Reports and records the update rule for future operator command changes.

## 5. J-Quants Runbook

Created:

```text
docs/03_operations/jquants_data_operations_runbook.md
```

The runbook covers purpose, scope, preconditions, authentication, source inventory, fetch procedure, Corporate Event materialization, raw storage, operations-path promotion, validation, rerun/idempotency, errors, rate limit, security, Historical usage, and update history.

## 6. Earnings Calendar Procedure

The runbook defines `earnings_calendar` as a snapshot-style endpoint:

```bash
AI_FUND_LAB_RAW_STORAGE_FORMAT=parquet python3 scripts/fetch_jquants_daily.py \
  --endpoint earnings_calendar \
  --date "$OPERATOR_BUSINESS_DATE" \
  --runtime-dir "$RUNTIME_DIR"
```

It clarifies that `--date` is retained for manifest/operator traceability; endpoint capability does not send date/code to J-Quants.

## 7. Fins Summary Procedure

The runbook defines `fins_summary` range fetch:

```bash
AI_FUND_LAB_RAW_STORAGE_FORMAT=parquet python3 scripts/fetch_jquants_daily.py \
  --endpoint fins_summary \
  --from-date "$FROM_DATE" \
  --to-date "$TO_DATE" \
  --runtime-dir "$RUNTIME_DIR"
```

The range is determined from the Runtime Test evaluation range, not only from `2026-07-06`. Existing older raw history must be retained.

## 8. Authentication And Plan

Authentication contract:

```text
JQUANTS_API_KEY
```

Settings are read from `.env` or environment variables. Secret values were not displayed or collected.

The runbook does not assume the user's J-Quants plan. It instructs the operator to confirm endpoint availability before live fetch.

## 9. Target Period

For a 10BD candidate run, use the Runtime Test plan's first and last requested business dates:

```text
FROM_DATE = first Runtime Test business date
TO_DATE   = last Runtime Test business date
```

For a 10BD starting `2026-07-06`, do not infer the whole data requirement from `2026-07-06` alone.

## 10. Idempotency And Rerun

Raw ingestion is keyed by:

```text
target_date
business_key
endpoint
```

Repeated fetches update matching raw keys and append manifest entries. Earnings Calendar schedule revisions must not be deleted to force a single current schedule.

## 11. Storage And Manifest

Raw fetch output:

```text
.runtime/data/raw/jquants/earnings_calendar/data.parquet
.runtime/data/raw/jquants/fins_summary/data.parquet
```

Operational Corporate Event consumer paths:

```text
.runtime/operations/jquants/raw/jquants/earnings_calendar/data.parquet
.runtime/operations/jquants/raw/jquants/fins_summary/data.parquet
```

Manifest:

```text
.runtime/data/raw/jquants/manifest.jsonl
```

## 12. Post-Run Validation

Runbook includes copyable commands for:

```text
CLI --help
Raw schema validation
Raw quality
Manifest latest check
row_count / min / max date inspection
hash inspection
```

## 13. Corporate Event Validation Gate

Runtime Test guide now links to:

```text
docs/03_operations/jquants_data_operations_runbook.md#corporate-event-validation-gate
```

The gate validates:

```text
earnings_calendar_coverage
financial_statement_coverage
listing_status_coverage
KNOWN_EVENT
KNOWN_NO_EVENT
UNKNOWN_DUE_TO_MISSING_COVERAGE
future publication reject
availability missing fail-closed
latest fallback false
```

10BD must not start until the gate is PASS or the symbol-scoped state is formally accepted.

## 14. Error And Recovery

The runbook documents handling for:

```text
auth failure
endpoint unavailable / plan shortage
rate limit
network timeout
schema mismatch
0 rows
partial fetch
manifest inconsistency
future availability rows
availability column missing
raw exists but consumer cannot read
```

It also documents what may be rerun and what must not be deleted.

## 15. Runtime Test Runbook Link

Updated:

```text
docs/03_operations/runtime_test_command_guide.md
```

It now requires Corporate Event materialization and validation before 10BD/20BD Runtime Test execution.

## 16. Documentation Update Rule

The following rule is active:

```text
Operator CLI/argument/materialization/runtime/recovery command changes require Operations Runbook update, Master Index update, CLI --help alignment, validation command update, and rollback/failure procedure update.
```

## 17. Short Validation

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_pycache python3 -m py_compile ...
PASS
```

```text
python3 -m pytest tests/test_show_jquants_manifest_cli.py tests/test_raw_quality_checker.py tests/test_jquants_raw_ingestion.py tests/test_fetch_jquants_daily_cli.py tests/test_schema_validation.py tests/test_jquants_api_common_fetch_policy.py
42 passed
```

CLI `--help` confirmed for:

```text
fetch_jquants_daily
show_jquants_manifest
check_jquants_raw_quality
inspect_raw_validation
build_jquants_refetch_plan
smoke_jquants_api
migrate_raw_storage
```

Dry-run checks:

```text
earnings_calendar fetch dry-run: PASS
fins_summary range dry-run: PASS_WITH_ARROW_CPU_WARNINGS_NO_NETWORK
```

JSON validation:

```text
11 files PASS
```

## 18. Not Executed

```text
J-Quants network fetch
real data materialization
10BD
20BD
1 year
3 years
4 years
Runtime Switch
Broker Write
Tachibana API
Active Run operation
credential display
```

## 19. Next Operator Action

Operator should follow:

```text
docs/03_operations/jquants_data_operations_runbook.md
```

After real `earnings_calendar` and `fins_summary` materialization, run the Corporate Event validation gate and submit the resulting Evidence for review. Until then:

```text
NOT_READY_FOR_10BD_OPERATOR_MATERIALIZATION_REQUIRED
```
