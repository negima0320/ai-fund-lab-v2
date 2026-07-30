# Phase23-Z: Earnings Calendar Current-Snapshot-Only Exception Contract and Corporate Event Gate Alignment

## Primary Judgment

```text
PHASE23_Z_EARNINGS_CALENDAR_ONLY_CURRENT_SNAPSHOT_EXCEPTION_IMPLEMENTED_SHORT_VALIDATION_PASS
```

## Phase23 Status

```text
PHASE23_CONTINUES
```

Phase23 closure, Phase24 handoff, Runtime Switch, Broker Write, and long-horizon Runtime Test were not performed.

## Exception Scope

Historical Corporate Event validation now has one explicit approved exception:

```text
authority_type = CURRENT_SNAPSHOT_CALENDAR_ONLY
exception_scope = earnings_scheduled_date_only
source_name = jquants_earnings_schedule
purpose = earnings_event_window
```

The exception is limited to J-Quants Earnings Calendar scheduled-date avoidance. It does not permit current snapshot use for market data, financial statements, listed issues, corporate actions, candidate/opportunity inputs, position management, portfolio state, broker snapshots, Accepted Generation, or any other Runtime input.

## Source Field Audit

Current operations source:

```text
.runtime/operations/jquants/raw/jquants/earnings_calendar/data.parquet
```

Observed columns:

```text
Date, Code, CoName, FY, SectorNm, FQ, Section, pagination_page,
fetched_at, target_date, code, business_key, source, endpoint
```

`Date` is treated as the scheduled-date column. `target_date` and `fetched_at` are retained as snapshot metadata. Consumer logic does not propagate company name, fiscal period, sector, section, publication date, financial metrics, or disclosure contents into Runtime event facts.

## Consumer Restriction

The Corporate Event producer consumes only:

```text
Code
scheduled date
snapshot target date
snapshot fetched_at
source hash/reference
```

Earnings Calendar events use:

```text
event_type = EARNINGS_ANNOUNCEMENT
reason_code = earnings_calendar_scheduled_date_current_snapshot_exception
```

The event source reference is snapshot-scoped and schedule-only.

## Historical Behavior

For historical business date `D`, the producer reads the latest materialized Earnings Calendar snapshot and checks whether the scheduled date is within the earnings avoidance window. It does not reject the row solely because `snapshot_target_date` or `snapshot_fetched_at` is after `D`.

Artifacts disclose:

```text
earnings_calendar_historical_pit_compliant = false
approved_non_pit_calendar_exception_used = true
```

## Non-Calendar PIT Preservation

No non-calendar PIT rule was relaxed. `fins_summary` still uses disclosure-date PIT filtering, `listed_issues` still rejects future source rows, and `latest_fallback_used=false` remains required for non-calendar inputs.

## Coverage Semantics

With a valid Earnings Calendar snapshot and scheduled-date column:

```text
earnings_calendar_coverage = AVAILABLE
overall_coverage_status = AVAILABLE
```

This is not a claim that the earnings calendar is historical PIT-compliant. It is an approved current-snapshot calendar-only authority.

## Known State Semantics

Scheduled date inside the event window becomes `KNOWN_EVENT`. When source coverage is available and no scheduled event applies to a symbol, the symbol may become `KNOWN_NO_EVENT`. Missing or partial non-calendar required coverage still prevents forced no-event conversion.

## Event Window

No pre-existing code-level earnings avoidance parameter was found. Phase23-Z fixed the producer contract to:

```text
calendar_days_before = 3
calendar_days_after = 1
```

This is recorded in `earnings_calendar_authority.event_window` and used only for the schedule-only exception.

## Artifact Metadata

Corporate Event artifacts now include:

```text
earnings_calendar_authority
earnings_calendar_authority_type
earnings_calendar_snapshot_target_date
earnings_calendar_snapshot_fetched_at
earnings_calendar_historical_pit_compliant
earnings_calendar_exception_scope
approved_non_pit_calendar_exception_used
non_calendar_future_leakage_used
non_calendar_latest_fallback_used
```

## Guardrail

The guardrail permits current snapshot use only when:

```text
source == earnings_calendar
field in scheduled-date aliases
purpose == earnings_event_window
```

Forbidden future content columns such as financial metrics trigger `earnings_calendar_forbidden_future_columns_present` and keep the producer in `REVIEW_REQUIRED`.

## 10BD Calendar Validation

Producer-only Corporate Event validation was run for:

```text
2026-07-06..2026-07-17
```

All 10 business-date artifacts returned `PASS`. For the current `2026-07-29` snapshot, no earnings scheduled date fell inside the 7/06..7/17 event window, so `earnings_calendar_event_count=0` for all 10 dates. Known/known-no-event states are explainable from available listed, fins, and calendar authority, with `unknown_count=0`.

## Daily Refresh Contract

Production operations must refresh `earnings_calendar` daily, record snapshot target date, `fetched_at`, row count, hash, manifest, and promoted operations path. Missing or stale scheduled-date snapshot metadata is `REVIEW_REQUIRED`.

Performance evidence using this exception must show:

```text
earnings_calendar_authority = CURRENT_SNAPSHOT_CALENDAR_ONLY
calendar_pit_compliant = false
all_other_inputs_pit_compliant = true
```

## Operations Runbook Updates

Updated:

```text
docs/03_operations/jquants_data_operations_runbook.md
docs/03_operations/runtime_test_command_guide.md
```

## Evidence

Evidence directory:

```text
reports/phase23_z_earnings_calendar_current_snapshot_only_exception_contract_and_gate_alignment/
```

Machine report:

```text
reports/phase_reports/phase23_z_earnings_calendar_current_snapshot_only_exception_contract_and_gate_alignment.json
```

## Short Validation

```text
py_compile PASS
Corporate Event unit/regression: 17 passed
Targeted J-Quants/Corporate Event regression: 57 passed
Broader J-Quants/Corporate Event regression: 93 passed
Corporate Event producer-only 10BD calendar validation: PASS
JSON validation: PASS
```

## 10BD Gate

```text
READY_FOR_10BD_OPERATOR_RERUN_REVIEW
```

This is not `10BD_READY`, `PRODUCTION_READY`, or `RUNTIME_SWITCH_READY`. Operator evidence review is still required before any Runtime Test rerun.
