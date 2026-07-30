# Phase23-V: Fins Summary Materialization Silent No-Op Root Cause Investigation

## 1. Primary Judgment

```text
PHASE23_V_FINS_SUMMARY_SILENT_NOOP_REPAIRED_SHORT_VALIDATION_PASS
```

The observed operator result is explained by an empty `fins_summary` range fetch plan plus a CLI silent-success branch. The CLI now treats an empty from/to fetch plan as a visible failed precondition.

## 2. Secondary Judgment

```text
NOT_READY_FOR_10BD_FINS_SUMMARY_MATERIALIZATION_UNRESOLVED
```

No live J-Quants fetch was executed in this task. The operator still needs to materialize sufficient `trading_calendar` coverage and then materialize `fins_summary` for the intended 10BD range.

## 3. Scope

This task investigated and repaired the silent no-op behavior for:

```bash
AI_FUND_LAB_RAW_STORAGE_FORMAT=parquet python3 scripts/fetch_jquants_daily.py \
  --endpoint fins_summary \
  --from-date 2026-07-06 \
  --to-date 2026-07-17 \
  --runtime-dir .runtime
```

Broker write, Runtime Switch, active Runtime Test operations, and real J-Quants fetch were not performed.

## 4. Observed Operator Result

The operator observed:

```text
stdout empty
stderr empty
exit_code 0
no new fins_summary manifest
fins_summary parquet unchanged
```

Current local `fins_summary` raw data contains 12 rows, all for `DiscDate=2026-06-01`.

## 5. CLI Argument Flow

`scripts/fetch_jquants_daily.py` parses `--endpoint`, `--from-date`, `--to-date`, `--runtime-dir`, and `--dry-run`, then calls `build_plan(args, store)` before creating a J-Quants client.

When `from_date` and `to_date` are provided, planning is delegated to `FetchPlanBuilder(TradingCalendarService(store))`. Therefore, a range fetch depends on local `trading_calendar` raw coverage.

## 6. Endpoint Dispatch

`fins_summary` maps to:

```text
/v2/fins/summary
```

The ingestion branch calls:

```text
client.fetch_all_fins_summary(date=date, code=code, max_pages=max_pages)
```

No endpoint dispatch bug was found.

## 7. Range Planning

For `fins_summary`, `from_date` and `to_date` are planning inputs. They are converted into one planned fetch per local business day.

With current `.runtime` data, the requested range:

```text
2026-07-06..2026-07-17
```

produces:

```text
plan_count = 0
```

## 8. Trading Calendar Dependency

Current local `trading_calendar` coverage is insufficient for the requested July range:

```text
rows = 91
Date = 2026-03-02..2026-06-28
target_date = 2026-03-02..2026-06-26
```

This explains why no `fins_summary` business-day fetch item was generated for `2026-07-06..2026-07-17`.

## 9. Skip / No-Op Contract

No formal `fins_summary` skip contract was found.

Existing `fins_summary` data for another date does not skip requested business days. Existing `fins_summary` data for the same date is refetched by the CLI when the date is planned. This is now covered by targeted tests.

## 10. Request Construction

For each planned `fins_summary` business day, the request is constructed with:

```text
date = planned business date
code = optional operator argument
```

When the plan is empty, no J-Quants request is constructed. This task did not add a latest fallback, guessed date, future date, or synthetic request.

## 11. Silent Success Branch

Before repair, `main()` iterated over `plan_items` and returned `0`. If `plan_items=[]`, the loop ran zero times and the command produced no stdout, no stderr, no storage write, and no manifest append.

After repair, a from/to range with an empty plan returns:

```text
exit_code = 2
stderr contains ERROR fetch plan is empty
```

No API request, storage write, or manifest append is performed.

## 12. Manifest Contract

The manifest contract is:

```text
planned request success -> append manifest
planned request with zero rows -> append manifest with record_count=0
empty fetch plan -> non-zero exit, no manifest append
```

No synthetic `OK`, `SKIPPED`, or `NO_OP` manifest row is written for empty plan, because no materialization occurred.

## 13. Root Cause

Primary root cause:

```text
STALE_OR_INSUFFICIENT_TRADING_CALENDAR_COVERAGE_CREATED_EMPTY_FINS_SUMMARY_FETCH_PLAN
```

Secondary root cause:

```text
CLI_TREATED_EMPTY_FROM_TO_FETCH_PLAN_AS_SUCCESSFUL_NOOP
```

Not root causes:

```text
J-Quants auth failure
fins_summary endpoint dispatch failure
existing raw skip behavior
API zero-row response behavior
```

## 14. 修正内容

`scripts/fetch_jquants_daily.py` now:

- converts missing calendar authority into visible exit code `2`,
- treats empty from/to fetch plan as visible exit code `2`,
- reports endpoint, requested range, and local trading calendar coverage,
- exits before client creation when no planned fetch exists.

This preserves the existing successful fetch and zero-row fetch contracts.

## 15. Operations Runbook更新

`docs/03_operations/jquants_data_operations_runbook.md` now documents:

- `fins_summary` range planning depends on local `trading_calendar`,
- empty plan is an operator precondition failure,
- normal live success must print saved-record output,
- normal live success must append `/v2/fins/summary` manifest entries,
- latest `fins_summary` manifest validation is required.

## 16. Short Validation

Short validation passed:

```text
py_compile PASS
tests/test_fetch_jquants_daily_cli.py: 8 passed
J-Quants targeted regression set: 63 passed
current .runtime dry-run reproduction: exit_code=2 with ERROR fetch plan is empty
```

The `.runtime` dry-run was network-free and did not fetch J-Quants data.

## 17. Evidence

Evidence directory:

```text
reports/phase23_v_fins_summary_materialization_silent_noop_root_cause_investigation/
```

Files:

```text
fins_summary_cli_argument_flow.json
fins_summary_endpoint_dispatch.json
fins_summary_range_plan.json
trading_calendar_dependency_audit.json
fins_summary_skip_contract.json
fins_summary_request_construction.json
silent_success_branch_inventory.json
fins_summary_manifest_contract.json
fins_summary_existing_test_inventory.json
fins_summary_short_reproduction.json
root_cause_evidence.json
modified_files.json
short_validation_results.json
operations_runbook_update_audit.json
```

## 18. 10BD Gate

```text
NOT_READY_FOR_10BD_FINS_SUMMARY_MATERIALIZATION_UNRESOLVED
```

Next operator action is to materialize `trading_calendar` coverage for the intended range, rerun `fins_summary` materialization, validate the manifest and raw quality, then proceed to the 10BD gate review. Phase23 continues.
