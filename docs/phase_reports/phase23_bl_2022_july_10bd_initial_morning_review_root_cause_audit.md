# Phase23-BL 2022 July 10BD Initial Morning REVIEW_REQUIRED Root Cause Audit

## Primary Judgment

```text
PHASE23_BL_2022_INITIAL_MORNING_REVIEW_AUDIT_COMPLETE
```

## Classification

Primary classifications:

```text
HISTORICAL_DATA_COVERAGE_GAP
PIT_AUTHORITY_FAILURE
MARKET_CONTEXT_INPUT_GAP
CORPORATE_EVENT_INPUT_GAP
PM_FEATURE_INPUT_GAP
PRODUCTION_CONTRACT_VIOLATION
```

Primary severity:

```text
BLOCKING_HISTORICAL_COVERAGE
```

## Direct Reason

Failure Run `runtime-test-historical-smoke-20260730T082859880393Z` stopped on `2022-07-01:morning`.

```text
Morning runtime_manifest.exit_code = 10
reason = morning pipeline blocked: strategy_runtime_planning_blocked
runtime_test aggregate exit_code = 30
completed_days = []
```

Morning reached Strategy Planning Authority, but Pending generation was blocked because Runtime Planning was `BLOCK`.

```text
planning_evidence.status = BLOCKED
planning_evidence.reason = strategy_runtime_planning_blocked
runtime_planning.producer_result_status = BLOCK
```

## Lowest-Level Reason

The lowest direct strategy blockers are not Submit, Pending, Quantity, or BK post-exec mapping. They are upstream source/PIT failures in Strategy producers:

```text
market_context.producer_result_status = BLOCK
reason_codes = [benchmark_coverage_insufficient, future_source_row_rejected]

corporate_event.producer_result_status = BLOCK
reason_codes = [corporate_event_source_coverage_incomplete, future_financial_statements_row_rejected, future_listed_issues_row_rejected]

technical_features / price_volatility = REVIEW_REQUIRED
reason_codes = [INSUFFICIENT_OBSERVATIONS, PARTIAL_SYMBOL_COVERAGE]
```

`source_manifest.json` classifies `market_context` and `corporate_event` as direct source/PIT blockers. Runtime Planning and Strategy Planning Authority then propagate `upstream_block:SOURCE_BLOCKED`.

## 2022 vs 2026 First Difference

The known-good `runtime-test-historical-smoke-20260730T080901510234Z` on `2026-07-06` has:

```text
market_context = PASS
corporate_event = PASS
technical_features = PASS
portfolio_policy onward = PASS
morning exit_code = 0
```

The first material difference is at `Market Context` / `Corporate Event`, before Portfolio Policy, Position Management, Portfolio Construction, Position Sizing, and Runtime Planning.

## Historical Coverage Finding

Run-scoped historical input for 2022 exists:

```text
run-scoped quotes: 2021-08-02 .. 2022-07-01
run-scoped listed issues: 2022-07-01
run-scoped trading calendar: 2021-08-02 .. 2022-07-01
```

But the failing Strategy artifacts bind to canonical operations paths:

```text
.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet
  available = 2026-02-16 .. 2026-07-14

.runtime/operations/jquants/raw/jquants/listed_issues/data.parquet
  available = 2026-07-06 .. 2026-07-15
```

Therefore 2022 PIT rows are absent from the Strategy producer source path even though the run-scoped historical-asof source is available. This is a Production-common source binding gap, not a reason to bypass review.

## Model / Generation

`historical_evaluation_authority.json` is `PASS` and fixes accepted generation `phase19_aq_accepted_generation_641e6e313543f013` at run start. The evaluation mode is `CURRENT_ACCEPTED_RUNTIME_ON_HISTORICAL_DATA`. 2022 overlaps training cutoff, so it is not `STRICT_OOS`, but this is not the direct Morning blocker.

## Previous Blockers

Recurring or related reasons present:

```text
target_weight_authority_unresolved = present
review_required_quantity_authority = present
```

They are downstream/propgated symptoms after the upstream source/PIT block. BK's `portfolio_membership_unresolved` is absent.

## Repair Recommendation

Create Phase23-BM for a Production-common historical input/source binding repair:

```text
Historical As-of materialization
-> Strategy source resolver / Source Manifest
-> Market Context, Corporate Event, Technical Features, Price Volatility producers
```

Do not add a 2022-only branch, latest fallback, current snapshot, future model usage, zero-fill, or review bypass.

## Rerun Readiness

```text
READY_FOR_2022_10BD_RERUN = NO
READY_FOR_REPAIR = YES
```

No Runtime rerun, fresh-run, resume, Broker Write, Runtime Switch, J-Quants fetch, code change, or test change was performed in this audit.
