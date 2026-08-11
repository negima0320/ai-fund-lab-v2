# Phase29-L3 Long-Horizon Bootstrap / Listed / Calendar Repair Design

Task ID: `Phase29-L3`

Status:

```text
COMPLETE
READ_ONLY REPAIR DESIGN / ARCHITECTURE CONTRACT DESIGN
NO IMPLEMENTATION
NO PRODUCTION CODE CHANGE
NO RUNTIME MUTATION
NO HISTORICAL EXECUTION
```

Primary Judgment:

```text
PHASE29_L3_LONG_HORIZON_DATA_AUTHORITY_REPAIR_DESIGN_COMPLETE_PHASE29_L4_READY
```

## 1. Scope

Phase29-L3 designs the Production-common Data Authority repair for the
Phase29-L2 blockers:

```text
1. Bootstrap post-commit warmup evidence defect
2. Listed Issues canonical authority materialization gap
3. Trading Calendar authority mismatch
```

No Strategy signal, performance logic, J1/J2, ADD, BUY_NEW, SELL, EXIT, REDUCE,
cash policy, concentration, Safety investment policy, model, or threshold is in
scope.

## 2. Bootstrap Repair Design

Confirmed root cause:

```text
Bootstrap run evidence/readiness retained pre-commit warmup_sufficiency from
the old canonical target, even after _commit_bootstrap_merge replaced the target
with complete 2022-05-17 to 2026-08-07 OHLCV data.
```

Required ordering:

```text
build plan
pre-commit source/schema/lineage/coverage validation
commit merged target atomically
re-read committed canonical target
verify committed target identity/hash/content/schema/coverage
evaluate post_commit_warmup_sufficiency
derive final bootstrap_readiness from post-commit authority
write final evidence
```

Evidence semantics:

```text
pre_commit_warmup_sufficiency  = diagnostic only
post_commit_warmup_sufficiency = final readiness authority
bootstrap_readiness            = PASS only after commit verification and
                                 post-commit warmup PASS
```

Recommended option:

```text
Option B — Two-Phase Bootstrap Transaction
```

Option A, a simpler post-commit recompute, is acceptable but less explicit. The
two-phase design is preferred because it separates preflight, commit,
post-commit verification, and final readiness in evidence and failure handling.

Fail-closed cases:

```text
commit failed                    -> BLOCK
target missing after commit       -> BLOCK
target hash/content mismatch      -> BLOCK
post-commit read failure          -> BLOCK
post-commit warmup failure        -> BLOCK
```

## 3. Listed Issues Materialization Design

Confirmed root cause:

```text
Acquisition staging listed_info reaches 2026-08-07, but canonical operations
listed_issues and historical snapshots are not materialized through the long
horizon end.
```

Staging source:

```text
.runtime/market_data_acquisition/runs/jquants-acquisition-20220517-20260807/raw/jquants/listed_issues/data.parquet
coverage: 2022-05-31 to 2026-08-07
```

Canonical target:

```text
.runtime/operations/jquants/raw/jquants/listed_issues/data.parquet
```

Existing PIT snapshot architecture:

```text
src/ai_fund_lab_v2/runtime_v2/historical_support/listed_issues_snapshots.py
selection_policy = latest_snapshot_not_after_business_date
future_snapshot_used / future_snapshot_selected = HALT
```

Required materialization path:

```text
validate acquisition staging listed_info
commit/merge canonical operations listed_issues
materialize historical PIT snapshots by provider Date
rebuild snapshot index/latest manifest
verify representative historical dates resolve snapshot_date <= business_date
wire Strategy source authority to the same canonical source path/snapshot
```

Critical invariant:

```text
Never copy latest/current listed_info backward across all historical dates.
Historical date T may select only listed information valid as of T.
```

Recommended option:

```text
Option B — Separate source-specific canonical materialization stage
```

This fits the existing Listed Issues snapshot resolver and keeps PIT validation
separate from OHLCV bootstrap. Extending market-data-bootstrap to materialize
OHLCV, listed_issues, and calendar all at once is more atomic, but has a larger
blast radius and mixes different authority models.

## 4. Calendar Authority Design

Confirmed mismatch:

```text
Phase29-L expected: 979 business days
Phase29-L2 dry-run: 977 business days
```

Do not force either number. The count must be derived from one canonical
Historical trading-calendar authority plus quote consistency.

Inventory classification:

```text
.runtime/operations/jquants/historical_snapshots/trading_calendar/data.parquet
  canonical historical base candidate

.runtime/market_data_acquisition/runs/jquants-acquisition-20220517-20260807/raw/jquants/trading_calendar/data.parquet
  validated staging / incremental correction candidate

.runtime/operations/jquants/raw/jquants/trading_calendar/data.parquet
  canonical operations runtime target, currently short/stale but agrees on
  disputed 2026 holidays

.runtime/data/raw/jquants/trading_calendar/data.parquet
  legacy/raw cache; contains stale HolDiv=1 for disputed holidays and must not
  be authoritative for Historical planning
```

Disputed dates:

```text
2026-03-20
2026-04-29
2026-05-04
2026-05-05
2026-05-06
```

For all five dates, acquisition staging, historical snapshot, and operations
calendar mark `HolDiv=3`; quote rows are zero. Only the older raw cache marks
them `HolDiv=1`.

Canonical SoT recommendation:

```text
Canonical Historical Calendar =
validated J-Quants historical snapshot base
+ validated staging extension/correction
+ conflict detection
+ quote consistency check
```

Expected long-horizon business-day count:

```text
977
```

This supersedes the Phase29-L provisional 979 count because newer J-Quants
calendar evidence and quote availability agree that the disputed dates are not
trading days.

## 5. Quote / Calendar Reconciliation Rule

Required deterministic rule:

```text
calendar open + quote rows > 0   -> include trading day
calendar closed + quote rows = 0 -> exclude trading day
calendar open + quote rows = 0   -> REVIEW/BLOCK, not silent drop
calendar closed + quote rows > 0 -> REVIEW/BLOCK, not silent include
calendar source conflict         -> REVIEW/BLOCK unless deterministic
                                    freshness/source precedence resolves it
                                    with evidence
```

Planner, data readiness, market refresh, and operations calendar consumers must
converge on the same canonical calendar authority rather than independently
mixing raw cache, snapshots, staging overlay, and weekday fallback.

## 6. Corporate Event Classification

Classification:

```text
NON_BLOCKING_PARTIAL_AUTHORITY
```

Rationale:

```text
Corporate Event remains PARTIAL, but current source foundation marks
corporate_actions, earnings_schedule, and financial_statements optional, and
Corporate Event can represent no-event / partial-source cases with explicit
coverage semantics. L3 should not broaden the next implementation task unless a
subsequent readiness gate proves Corporate Event is a hard blocker.
```

Do not claim full Corporate Event READY until optional sources are separately
validated/materialized.

## 7. Regression Contract

Bootstrap:

```text
L3-R1 old target incomplete + new source complete -> post-commit warmup PASS
L3-R2 source incomplete -> BLOCK
L3-R3 commit fails -> no false readiness
L3-R4 committed target hash/content differs -> BLOCK
L3-R5 exactly 61BD warmup -> PASS
L3-R6 only 60BD warmup -> BLOCK
```

Listed Issues:

```text
L3-R7 staging full coverage -> canonical materialization full coverage
L3-R8 future listed row exists physically -> earlier date does not select it
L3-R9 listed/delisted lifecycle preserved
L3-R10 missing authority remains fail-closed
L3-R11 canonical source lineage observable
```

Calendar:

```text
L3-R12 all planner/runtime consumers resolve same business-day set
L3-R13 known holiday/non-trading date excluded
L3-R14 valid trading date with quotes included
L3-R15 calendar/quote disagreement produces REVIEW/BLOCK
L3-R16 requested 2022-08-10 through 2026-08-09 resolves deterministically
```

Cross-phase non-regression:

```text
Temporal authority
Phase23 source authority
Phase24 runtime continuity
Phase26 architecture repairs
Phase28 D3 pending reconciliation
D61 / D69
Phase29-E / Phase29-G
Phase29-J1 / Phase29-J2
BUY/SELL independence
Compound Capital
```

## 8. Implementation Staging

Recommended staging:

```text
L4-A Bootstrap post-commit evidence/readiness repair
L4-B Listed/calendar canonical materialization and reconciliation
L4-C Read-only long-horizon gate recheck
```

Do not implement one large atomic L4 unless rollback simplicity is explicitly
traded off for bundle atomicity. Staging is safer because bootstrap evidence
repair is narrow, while PIT listed/calendar authority has a larger regression
surface.

## 9. Fresh Long-Horizon Entry Contract

Fresh long-horizon is not ready.

Entry requirements after future repair:

```text
OHLCV coverage PASS
61BD warmup PASS from post-commit canonical target
Listed Issues authority PASS via PIT snapshot resolver
Calendar authority PASS through one reconciled canonical SoT
Quote/calendar ambiguity count = 0
PIT validation PASS
dry-run date resolution PASS
negative source ambiguity = 0
```

Forbidden shortcuts:

```text
copy current listed state backward
silently drop calendar dates
force 979
bypass warmup
weaken PIT
add Historical-only source shortcuts
```

Current decisions:

```text
API price refetch required:  NO
Listed API refetch required: NO
OHLCV re-bootstrap required: NO
Strategy changes required:   NO
Fresh long-horizon ready:    NO
```

Recommended next task:

```text
Phase29-L4-A Bootstrap post-commit evidence/readiness repair, followed by
Phase29-L4-B Listed/calendar materialization and reconciliation.
```

## 10. Deliverables

```text
docs/phase_reports/phase29_l3_long_horizon_bootstrap_listed_calendar_repair_design.md
reports/phase29_l3_long_horizon_bootstrap_listed_calendar_repair_design/
```
