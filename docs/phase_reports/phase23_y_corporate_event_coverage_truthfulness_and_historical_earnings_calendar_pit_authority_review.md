# Phase23-Y: Corporate Event Coverage Truthfulness and Historical Earnings Calendar PIT Authority Review

## 1. Primary Judgment

```text
PHASE23_Y_COVERAGE_TRUTHFULNESS_REPAIRED_HISTORICAL_EARNINGS_PIT_GAP_REMAINS
```

Coverage artifact truthfulness was repaired. The remaining `REVIEW_REQUIRED` state is now caused by a real Historical Earnings Calendar PIT authority gap, not by stale missing-source reason codes.

## 2. Phase23継続確認

```text
PHASE23_CONTINUES
```

No Phase23 closure, Phase24 handoff, Runtime Switch, Broker Write, or 10BD execution was performed.

## 3. Promotion Evidence

Operator promotion evidence provided:

```text
earnings_calendar rows = 58, hash match = true
fins_summary rows = 506, hash match = true
```

Operations paths exist for `listed_issues`, `earnings_calendar`, and cleaned `fins_summary`.

## 4. Coverage Status / Reason Consistency

Fixed the contradiction:

```text
AVAILABLE + *_not_implemented_or_missing
```

Post-fix:

```text
listing_status_coverage = AVAILABLE, reason_codes=[]
financial_statement_coverage = AVAILABLE, reason_codes=[]
earnings_calendar_coverage = PARTIAL, reason_codes=[future_earnings_calendar_row_rejected]
```

## 5. Top-Level Reason Aggregation

Before:

```text
corporate_event_source_coverage_incomplete
future_earnings_calendar_row_rejected
jquants_corporate_actions_not_implemented_or_missing
```

After:

```text
corporate_event_source_coverage_incomplete
future_earnings_calendar_row_rejected
```

Optional corporate actions are still shown source-scoped, but are no longer a top-level blocker.

## 6. Corporate Actions Optional Contract

Phase23-T decided Corporate Actions / TDnet family is optional until deterministic classification and consumer implementation exist.

Post-fix, missing corporate actions:

```text
source-scoped = reported
top-level blocker = no
KNOWN_NO_EVENT force = no
```

## 7. Earnings Calendar Raw Authority

Operations `earnings_calendar`:

```text
row_count = 58
Date/target_date = 2026-07-29
PublicationDate column = absent
availability fallback used by repo = target_date
2026-07-06 as-of available rows = 0
future rows rejected = 58
```

## 8. Snapshot Capability

Current repo `earnings_calendar` client fetches the endpoint with no date parameter. CLI `--date` is manifest/operator trace only for this endpoint.

Official references confirm J-Quants provides earnings announcement schedules; J-Quants Pro has `publication_date` and `scheduled_date` semantics and retains revised schedule rows. The current repo endpoint and materialized snapshot do not reconstruct the `2026-07-06` as-of state.

References:

- https://www.jpx.co.jp/english/markets/other-data-services/j-quants-api/index.html
- https://jpx.gitbook.io/j-quants-pro-ja/api-reference/earnings_announcement_dates_times
- https://pro.jpx-jquants.com/datasets/7

## 9. Historical PIT Authority Decision

Decision:

```text
Case B
```

The current `2026-07-29` earnings calendar snapshot cannot be used to reconstruct `2026-07-06` PIT coverage. It must remain `PIT_COVERAGE_INCOMPLETE`.

## 10. Known Event Provenance

Post-fix event provenance:

```text
known_event_symbols = 26
events = 27
financial_statement events = 27
earnings_calendar events = 0
future known events = 0
```

All known events are from cleaned `fins_summary`; future earnings calendar rows did not become known events.

## 11. Unknown Reason Breakdown

Post-fix:

```text
unknown_symbols = 4411
known_no_event_symbols = 0
unknown reason = future_earnings_calendar_row_rejected
```

`KNOWN_NO_EVENT` remains zero because required earnings PIT coverage is incomplete.

## 12. Coverage Gate Semantics

Gate semantics clarified:

```text
required source missing -> REVIEW/MISSING
required PIT coverage incomplete -> REVIEW/PARTIAL
optional corporate_actions missing -> source-scoped nonblocking gap
future row reject -> safety behavior
KNOWN_NO_EVENT -> allowed only when required PIT coverage is complete
```

## 13. 修正内容

Updated:

```text
src/ai_fund_lab_v2/strategy/corporate_event.py
tests/strategy/test_phase22_aa_corporate_event.py
docs/03_operations/jquants_data_operations_runbook.md
docs/03_operations/runtime_test_command_guide.md
```

## 14. Corporate Event Post-Fix Validation

Generated:

```text
.runtime/reports/phase23_y_post_fix_corporate_event_2026-07-06.json
```

Result:

```text
status = REVIEW_REQUIRED
overall_coverage_status = PARTIAL
reason_codes = [corporate_event_source_coverage_incomplete, future_earnings_calendar_row_rejected]
future_leakage_used = false
latest_fallback_used = false
```

## 15. Operations Runbook更新

Updated runbooks:

```text
docs/03_operations/jquants_data_operations_runbook.md
docs/03_operations/runtime_test_command_guide.md
```

Added PIT coverage distinction, current snapshot limitation, optional corporate actions handling, future row rejection semantics, and 10BD gate caution.

## 16. Short Validation

```text
py_compile PASS
Corporate Event tests: 16 passed
targeted Corporate Event/J-Quants regression: 56 passed
broad J-Quants/Corporate Event regression: 92 passed
post-fix artifact generation PASS
```

## 17. 未実施事項

No J-Quants live fetch, 10BD, 20BD, Runtime Switch, Broker Write, Tachibana API, or future/latest snapshot fallback was performed.

## 18. 10BD Gate

```text
NOT_READY_FOR_10BD_HISTORICAL_EARNINGS_CALENDAR_PIT_AUTHORITY_GAP_REMAINS
```

## 19. 次のAction

Design or materialize a Historical Earnings Calendar PIT authority source, such as pre-collected snapshot history or a supported historical publication-date endpoint. Do not treat the current `2026-07-29` snapshot as valid for `2026-07-06`.
