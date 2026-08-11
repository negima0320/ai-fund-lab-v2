# Phase29-L2 Post-Acquisition Bootstrap Long-Horizon Readiness Recheck

Task ID: `Phase29-L2`

Status:

```text
COMPLETE
READ_ONLY SOURCE COVERAGE / BOOTSTRAP AUTHORITY AUDIT
OHLCV ACQUISITION SOURCE COMPLETE
OHLCV BOOTSTRAP TARGET COMPLETE
FRESH 979BD GATE NOT READY
NO PRODUCTION CODE CHANGE
NO RUNTIME MUTATION BY CODEX
NO HISTORICAL EXECUTION
```

Primary Judgment:

```text
PHASE29_L2_MULTI_CAUSAL_SOURCE_AUTHORITY_DEFECT_CONFIRMED_REPAIR_REQUIRED
```

## 1. Scope

Phase29-L2 audited the post-operator acquisition/bootstrap state requested by
Phase29-L. Codex did not rerun acquisition, bootstrap, resume, or the long
Historical. Codex only inspected files, code paths, evidence, parquet contents,
and ran one read-only `fresh-run --dry-run` recheck.

## 2. Acquisition Source

Inspected source:

```text
.runtime/market_data_acquisition/runs/jquants-acquisition-20220517-20260807/raw_normalized/jquants/equities_bars_daily/data.parquet
```

Result:

```text
exists:               YES
row_count:            4,328,997
min_date:             2022-05-17
max_date:             2026-08-07
unique_business_days: 1,037
duplicate Date/Code:  0
source_complete:      YES
```

All 52 acquisition state chunks are `COMPLETED`. Final acquisition
classification:

```text
ACQUISITION_SOURCE_CORRECT
```

The acquisition source did not lose historical data during final merge. No
price API refetch is required.

## 3. Bootstrap Input and Target

Bootstrap evidence reports the intended source path:

```text
.runtime/market_data_acquisition/runs/jquants-acquisition-20220517-20260807/raw_normalized/jquants/equities_bars_daily/data.parquet
```

The reported source inventory hash and row count match the inspected source.
`source_reuse_status = REUSABLE` means the explicitly supplied source passed
schema, lineage, duplicate, and coverage checks. It does not select an older
runtime source.

Inspected committed target:

```text
.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet
```

Result:

```text
row_count:            4,328,997
min_date:             2022-05-17
max_date:             2026-08-07
unique_business_days: 1,037
duplicate Date/Code:  0
target_complete:      YES
```

The committed target matches the bootstrap `merged_inventory`. Re-bootstrap is
not required for OHLCV price data.

## 4. Warmup Anomaly

Observed bootstrap evidence contained:

```text
warmup_sufficiency_judgment: BLOCK
reason:                     QUOTE_TARGET_DATE_MISSING
actual_source_earliest:      2026-02-16
actual_source_latest:        2026-07-14
```

Root cause:

```text
Bootstrap records warmup_sufficiency from build_market_data_bootstrap_plan
before _commit_bootstrap_merge replaces the target parquet. Therefore the
warmup block is stale pre-commit evidence from the old runtime target.
```

Post-commit recomputation on the actual target gives:

```text
warmup_sufficiency_judgment: PASS
reason:                     HISTORICAL_SOURCE_WARMUP_SUFFICIENT
actual_source_earliest:      2022-05-17
actual_source_latest:        2026-08-07
available_business_dates:    61
missing_warmup_days:         0
target_date_available:       true
```

Therefore:

```text
Warmup resolver defect: NO
Bootstrap post-commit evidence/readiness defect: YES
```

## 5. Why 2026-02-16 and 2026-07-14

`2026-02-16` and `2026-07-14` came from the pre-existing runtime target before
the operator bootstrap commit. They are also recorded as
`existing_runtime_earliest_date` and `existing_runtime_latest_date` in the
acquisition plan/state evidence.

The old source ending `2026-07-14` was not reused as the bootstrap input. The
bootstrap input identity points to the intended `jquants-acquisition-20220517-
20260807` source, and source hash/row count match.

## 6. Calendar Recheck

Phase29-L reported `979` business days. Phase29-L2 found that current
fresh-run planning and quote availability resolve:

```text
resolved_date_from:          2022-08-10
resolved_date_to:            2026-08-07
resolved_business_day_count: 977
request_conformance_status:  NOT_PASS
```

The discrepancy is calendar authority related. Five 2026 dates are marked as
trading days in an older raw calendar but as non-trading days in the newer
historical snapshot and have no quote rows:

```text
2026-03-20
2026-04-29
2026-05-04
2026-05-05
2026-05-06
```

The dry-run still classifies the requested window as
`REVIEW_REQUIRED / NOT_PASS`, so the `979BD` contract is not ready.

## 7. Listed Issues Recheck

The acquisition command did fetch `listed_info` into staging:

```text
.runtime/market_data_acquisition/runs/jquants-acquisition-20220517-20260807/raw/jquants/listed_issues/data.parquet
row_count: 226,051
coverage:  2022-05-31 to 2026-08-07
```

But canonical runtime operations authority remains:

```text
.runtime/operations/jquants/raw/jquants/listed_issues/data.parquet
row_count: 22,193
coverage:  2026-07-06 to 2026-07-15
```

Historical Listed Issues snapshots are also not materialized through
`2026-08-07`.

Result:

```text
Listed Issues Ready: NO
API refetch required for listed issues: NO
Materialization / bootstrap scope repair required: YES
```

## 8. Corporate Event Recheck

Corporate Event authority remains partial. Current Production can represent
no-event cases under some partial-source conditions, and corporate actions /
earnings schedule / financial statements are optional in the historical source
foundation inventory. However, Phase29-L2 cannot claim full long-horizon
Corporate Event readiness.

Result:

```text
Corporate Event Ready: PARTIAL
```

## 9. Fresh Dry-Run Recheck

Command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-smoke \
  --date-from 2022-08-10 \
  --date-to 2026-08-09 \
  --initial-cash 1000000 \
  --dry-run \
  --json
```

Result:

```text
status:                      DRY_RUN
dry_run_no_mutation:          true
resolved_date_from:           2022-08-10
resolved_date_to:             2026-08-07
resolved_business_day_count:  977
request_conformance_status:   NOT_PASS
window_resolution_status:     REVIEW_REQUIRED
historical_executed:          NO
```

The dry-run confirms the terminal date is now resolvable, but it does not
confirm the requested `979BD` gate.

## 10. Root Cause Classification

Primary classification:

```text
L2-F MULTI_CAUSAL_SOURCE_AUTHORITY_DEFECT
```

Sub-findings:

```text
OHLCV acquisition source incomplete: NO
Acquisition final merge defect:      NO
Bootstrap wrong source reused:       NO
Bootstrap target truncation defect:  NO
Warmup resolver defect:              NO
Bootstrap stale warmup evidence:     YES
Listed authority materialization gap:YES
Calendar 979 contract mismatch:      YES
```

Production defect decision:

```text
Production defect = YES
```

Affected file:

```text
src/ai_fund_lab_v2/runtime_v2/market_data_bootstrap.py
```

Affected functions:

```text
build_market_data_bootstrap_plan
execute_market_data_bootstrap
_commit_bootstrap_merge
write_bootstrap_evidence
```

Reason:

```text
Bootstrap run evidence and readiness judgment retain the pre-commit warmup
result even after the target parquet is replaced by the complete merged target.
The same bootstrap scope commits OHLCV only and does not materialize
acquisition staging listed_info / trading_calendar into canonical operations
authority.
```

Why short 100BD did not expose it:

```text
Short 100BD runs used already prepared 2026 runtime data and did not rely on
the multi-year acquisition/bootstrap handoff, 2022 warmup, or long-window
calendar/listed authority materialization.
```

## 11. Decisions

```text
API price refetch required:       NO
Listed Issues API refetch:        NO
Corporate API refetch:            UNKNOWN_NOT_PROVEN
OHLCV re-bootstrap required:      NO
Listed/calendar materialization:  YES
Additional long acquisition:      NO for price/listed staging
Fresh 979BD Ready:                NO
Gate classification:              NOT_READY_REPAIR_REQUIRED
```

Recommended next task:

```text
Repair/readiness-design for bootstrap post-commit warmup evidence,
calendar authority reconciliation, and listed/trading-calendar materialization
from completed acquisition staging. Then rerun a read-only L3 readiness gate
before any long Historical fresh-run.
```

## 12. Deliverables

```text
docs/phase_reports/phase29_l2_post_acquisition_bootstrap_long_horizon_readiness_recheck.md
reports/phase29_l2_post_acquisition_bootstrap_long_horizon_readiness_recheck/
```
