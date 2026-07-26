# Phase20-BT 5BD Post-Fix Zero-Trade Regression

## Executive Judgment

Primary Judgment:

```text
PHASE20_BT_PHASE20_BS_FIX_NOT_APPLIED_TO_RUNTIME_PATH
```

Secondary Judgment:

```text
PHASE20_BT_PRICE_RESOLUTION_STILL_BROKEN
```

The 5BD post-BS run still used the operations canonical price path:

```text
.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet
```

It did not use the Run-scoped Historical logical as-of input. Therefore the run remained `price_missing_all` for all 5 days.

## Target Run

```text
runtime-test-historical-extended-smoke-20260725T102921751066Z
```

Period:

```text
2022-09-01 to 2022-09-07
```

Run result:

```text
completed_business_days = 5 / 5
runtime_judgment = PASS
BUY execution = 0
SELL execution = 0
PM decision = 0
Position Campaign = 0
final_equity = 1,000,000
```

## Daily BUY Funnel

| Date | Planning input | Price missing | BUY plan | BUY execution | Recorded price source |
|---|---:|---:|---:|---:|---|
| 2022-09-01 | 4 | 4 | 0 | 0 | operations canonical |
| 2022-09-02 | 4 | 4 | 0 | 0 | operations canonical |
| 2022-09-05 | 3 | 3 | 0 | 0 | operations canonical |
| 2022-09-06 | 3 | 3 | 0 | 0 | operations canonical |
| 2022-09-07 | 3 | 3 | 0 | 0 | operations canonical |

First zero-producing stage:

```text
price_missing_all = 5
```

Planning reason:

```text
NO_SIGNAL:no_affordable_candidates_with_reliable_price = 5
```

## Historical Logical Input Check

The Run-scoped Historical logical manifests exist for all 5 days:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260725T102921751066Z/daily/<DATE>/market_refresh/inputs/historical_asof/<DATE>/logical_input_manifest.json
```

After the BT fix, the resolver selects:

| Date | Fixed resolver business-date rows |
|---|---:|
| 2022-09-01 | 4,057 |
| 2022-09-02 | 4,075 |
| 2022-09-05 | 4,062 |
| 2022-09-06 | 4,032 |
| 2022-09-07 | 4,044 |

This proves the remaining issue was not missing Historical market data. It was path resolution.

## Root Cause

Phase20-BS connected Morning Planning to Historical logical input, but the implementation searched:

```text
.runtime/operations/market_refresh/inputs/historical_asof/<DATE>/logical_input_manifest.json
```

Actual runtime_test materializes the logical input under the Run-scoped evidence root:

```text
reports/runtime_tests/runs/<RUN_ID>/daily/<DATE>/market_refresh/inputs/historical_asof/<DATE>/logical_input_manifest.json
```

Because the BS resolver did not inspect `runtime_test_evidence_root`, it failed to find the manifest and fell back to operations canonical OHLCV.

## Bull Comparison

Bull reference:

```text
runtime-test-historical-extended-smoke-20260724T064819643722Z
```

Bull had:

```text
price_missing_sum = 0
buy_plan_item_sum = 59
BUY execution = 5
```

The first divergence remains BUY Planning price resolution. Bull used operations canonical too, but Bull dates are in 2026 and were present in operations canonical. The 2022 target dates were not.

## Fix

Changed:

```text
src/ai_fund_lab_v2/runtime_v2/planning/morning_pipeline.py
tests/runtime_v2/test_phase14e15_morning_ai_planning_pending_connection.py
```

Implementation:

- Historical Morning Planning now checks `environment_capability_context.runtime_test_evidence_root`.
- It resolves Run-scoped logical manifest first.
- It then reads `logical_paths.normalized_ohlcv`.
- Production/Demo continue using operations canonical.
- If a Historical manifest exists but is malformed, non-PASS, or lacks `normalized_ohlcv`, it remains fail-closed.
- No threshold, Candidate, Opportunity, Capital, PM, Submit, Broker, Accepted Generation, or Strategy logic was changed.

## Regression

Focused regression:

```text
test_phase20_bs_historical_morning_uses_logical_asof_price_source
```

The test places the Historical logical input only under a Run-scoped evidence root and verifies Morning Planning selects it.

## Evidence

```text
reports/phase20_bt_5bd_post_fix_zero_trade_regression/daily_funnel.json
reports/phase20_bt_5bd_post_fix_zero_trade_regression/bull_comparison.json
reports/phase20_bt_5bd_post_fix_zero_trade_regression/root_cause_trace.json
reports/phase_reports/phase20_bt_5bd_post_fix_zero_trade_regression.json
```

## User Revalidation Command

Codex did not execute a 5BD fresh run.

```bash
cd /Users/negishi/work/ai-fund-lab-v2

PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --business-days 5 \
  --start-date 2022-09-01 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Expected confirmation:

```text
planning_evidence.price_source_path = reports/runtime_tests/runs/<RUN_ID>/daily/<DATE>/market_refresh/inputs/historical_asof/<DATE>/raw_normalized/jquants/equities_bars_daily/data.parquet
price_missing_count < planning_input_count
```

Whether BUY plans become positive after price resolution depends on retained Strategy signals, eligibility, affordability, and capital allocation.

## Phase20 Closure

```text
PENDING_USER_REVALIDATION
```

Phase20 should not close until the 5BD user rerun confirms the Run-scoped Historical price source is recorded in `planning_evidence.json`.
