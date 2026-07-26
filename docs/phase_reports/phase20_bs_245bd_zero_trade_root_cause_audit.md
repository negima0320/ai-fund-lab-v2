# Phase20-BS 245BD Zero-Trade Root Cause Audit

## Executive Judgment

Primary Judgment:

```text
PHASE20_BS_BUY_PLANNING_DEFECT_CONFIRMED
```

Supporting Judgments:

```text
PHASE20_BS_ZERO_TRADE_ROOT_CAUSE_IDENTIFIED
PHASE20_BS_RUNTIME_CONTRACT_DEFECT_CONFIRMED
PHASE20_BS_PRICE_AUTHORITY_DEFECT_CONFIRMED
```

Root Cause:

```text
HISTORICAL_BUY_PLANNING_PRICE_SOURCE_BYPASSED_HISTORICAL_ASOF_LOGICAL_INPUT
```

The 245BD run did not trade because Morning BUY Planning resolved BUY prices from the operations canonical OHLCV path instead of the Historical as-of logical input. The feature pipeline correctly generated 2022 feature artifacts from `acquisition_staging`, but Planning priced candidates from `.runtime/operations/jquants/raw_normalized/...`, whose retained range starts in 2026. Therefore every planning candidate in the 2022-09-01 to 2023-08-30 run had missing price evidence.

This is not PM, Candidate warmup, 9000-series submit capability, broker, or strategy-threshold behavior.

## Scope and Non-Goals

Scope:

- Target Run: `runtime-test-historical-extended-smoke-20260724T100517836437Z`
- Comparison Run: `runtime-test-historical-extended-smoke-20260724T064819643722Z`
- Evidence source: existing run-scoped artifacts only
- Fix scope: Morning Planning price authority connection only

Non-goals:

- No PM threshold change
- No Candidate / Opportunity / Capital logic change
- No Strategy redesign
- No Accepted Generation change
- No 20BD / 245BD / long historical run by Codex

## Run Facts

Target 245BD run:

| Item | Value |
|---|---:|
| Period | 2022-09-01 to 2023-08-30 |
| Completed business days | 245 |
| Runtime judgment | PASS |
| BUY plan | 0 |
| BUY execution | 0 |
| SELL execution | 0 |
| Position Campaign | 0 |
| PM decision | 0 |
| Final equity | 1,000,000 |
| Return | 0 |

Bull comparison run:

| Item | Value |
|---|---:|
| Period | 2026-03-24 to 2026-04-20 |
| Completed business days | 20 |
| BUY plan items | 59 |
| BUY execution | 5 |
| SELL execution | 9 |
| Final equity | 973,280 |

## Evidence Inventory

Available:

- `daily/*/market_refresh/feature_refresh/feature_refresh_detail.json`
- `daily/*/market_refresh/historical_asof_view.json`
- `daily/*/market_refresh/inputs/historical_asof/*/logical_input_manifest.json`
- `daily/*/morning/planning_evidence.json`
- `daily/*/morning/pending_generation_evidence.json`
- `daily/*/execution/fills.json`
- `fresh_run_summary.json`
- `final_summary.json`

Partial or not retained:

- Candidate individual PASS / REVIEW / BLOCK decisions are not retained.
- Full Opportunity ranking artifacts are referenced as `.runtime` paths and not fully copied run-scoped for all days.
- BUY submitted count is treated as `DERIVABLE_EXACT_FROM_FILL_OBSERVABILITY` in this audit.

## 245BD Daily Funnel Aggregate

| Metric | Value |
|---|---:|
| Business days | 245 |
| Candidate feature rows min | 4,264 |
| Candidate feature rows max | 4,437 |
| Candidate feature rows sum | 1,067,669 |
| BUY Planning input sum | 1,149 |
| Price missing sum | 1,149 |
| BUY plan item sum | 0 |
| BUY execution sum | 0 |
| SELL execution sum | 0 |

Key invariant:

```text
245 / 245 days:
BUY Planning input count > 0
price_missing_count == BUY Planning input count
BUY plan item count == 0
```

## Monthly Funnel Aggregate

Monthly evidence is written to:

```text
reports/phase20_bs_245bd_zero_trade_root_cause_audit/monthly_funnel.json
```

All months from 2022-09 through 2023-08 show:

```text
first_zero_producing_stage = price_missing_all
buy_plan_positive_days = 0
buy_execution_positive_days = 0
```

## First Zero-Producing Stage

```text
price_missing_all = 245 days
```

The first zero-producing stage is BUY Planning price resolution. Candidate feature rows and BUY Planning inputs exist; BUY plans become zero only after price lookup.

## Exclusion Reason Distribution

```text
NO_SIGNAL:no_affordable_candidates_with_reliable_price = 245
```

This reason is accurate at the immediate Planning level, but the underlying cause is not affordability. The candidate prices were missing because Planning read the wrong Historical price authority.

## Bull Run Comparison

First divergence:

```text
BUY Planning price resolution
```

Target 245BD:

```text
price_missing_sum = 1,149
buy_plan_item_sum = 0
buy_execution_sum = 0
```

Bull:

```text
price_missing_sum = 0
buy_plan_item_sum = 59
buy_execution_sum = 5
```

Bull succeeds because its 2026 dates exist in operations canonical OHLCV. The target 2022 dates do not, even though Historical as-of logical input contains them.

## Runtime / Data / Strategy / Evidence Responsibility

| Category | Judgment |
|---|---|
| Runtime Contract Defect | CONFIRMED |
| Data Defect | NOT CONFIRMED |
| Strategy Eligibility Too Restrictive | NOT CONFIRMED |
| Expected No-Trade Outcome | NOT CONFIRMED |
| Evidence Gap | PRESENT, non-blocking for root cause |

Data is present in Historical as-of logical input. Feature generation used it successfully. The defect is a consumer wiring gap in BUY Planning.

## Implementation Audit

Confirmed pre-fix behavior:

```text
src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py
_price_source_path(feature_root)
=> feature_root.parent / "jquants/raw_normalized/jquants/equities_bars_daily/data.parquet"
```

For Historical old-date runs this bypassed:

```text
operations/market_refresh/inputs/historical_asof/<business_date>/logical_input_manifest.json
logical_paths.normalized_ohlcv
```

Related prior fix:

```text
Phase20-BL fixed Market Evidence consumer wiring.
Phase20-BS confirms Morning BUY Planning had the same class of Historical as-of consumer gap.
```

## Required Fix or No-Fix Decision

Fix required and applied.

Changed:

```text
src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py
```

Behavior after fix:

- Historical Planning first resolves `logical_input_manifest.json:logical_paths.normalized_ohlcv`.
- Production/Demo keep the operations canonical OHLCV path.
- If the Historical logical manifest/path is absent, existing fail-closed behavior remains.
- No thresholds, scores, rankings, position logic, capital policy, broker logic, or submit logic were changed.

## Regression Requirements

Added focused regression:

```text
tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py
test_phase20_bs_historical_morning_uses_logical_asof_price_source
```

The test builds a Historical fixture where operations canonical has no price row, but Historical logical input does. Morning Planning must produce an approved BUY pending plan using the logical as-of price source.

## Remaining Gaps

- Candidate individual PASS / REVIEW / BLOCK counts are not retained.
- Full Opportunity ranking artifacts are partially referenced but not copied as complete run-scoped evidence for every day.
- A user 245BD revalidation is required to confirm end-to-end trading behavior after the fix.

## Phase20 Closure Impact

Phase20 closure should remain pending until user revalidation confirms:

```text
245BD BUY Planning no longer zeroes at price_missing_all
Historical as-of price authority is recorded in planning_evidence.json
No Runtime halt
No PM false attribution
```

## User-Run Validation Command

Codex did not execute this long run.

```bash
cd /Users/negishi/work/ai-fund-lab-v2

PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --business-days 245 \
  --start-date 2022-09-01 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Optional shorter pre-check:

```bash
cd /Users/negishi/work/ai-fund-lab-v2

PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --business-days 1 \
  --start-date 2022-09-01 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Expected evidence after rerun:

```text
planning_evidence.price_source_path = reports/runtime_tests/.../market_refresh/inputs/historical_asof/.../raw_normalized/jquants/equities_bars_daily/data.parquet
planning_evidence.price_missing_count < candidate_count
BUY plan item count may become > 0 depending on retained Strategy signals and capital rules
```

## Final Judgment

```text
PHASE20_BS_BUY_PLANNING_DEFECT_CONFIRMED
```

The 245BD zero-trade result was caused by a Runtime Planning price authority defect, not by Strategy eligibility, PM, 9000-series submit capability, or missing Historical market data.
