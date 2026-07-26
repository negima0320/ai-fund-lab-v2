# Phase20-BI Production/Historical Feature Lookback Contract

## Summary

Final status:

```text
PHASE20_BI_FEATURE_LOOKBACK_CONTRACT_FIXED
```

The 2026-03-24 Historical run did not fail because the acquired long-run OHLCV source was missing. It failed because the Historical as-of logical input was materialized from the short operations canonical OHLCV view, whose earliest date was 2026-02-16. Candidate Feature generation therefore received only about 25 trading dates for 2026-03-24 and correctly marked every row as `insufficient_lookback`.

The fix makes Historical runtime market refresh require the common Phase20-BB feature lookback contract before feature generation. If `.runtime/operations` has sufficient history, it remains the source. If it does not, a validated read-only acquisition staging source is selected, including its matching J-Quants Trading Calendar. If no source satisfies the contract, Historical as-of fails closed before Candidate / Opportunity / PM consume incomplete features.

No PM threshold, model, runtime decision logic, candidate feature formula, broker path, training, calibration, or Accepted Generation was changed.

## Evidence

Failed run:

```text
runtime-test-historical-extended-smoke-20260723T115437756316Z
```

Observed failure:

```text
2026-03-24 morning HALT
buy_ai_reason = candidate_feature_rows_empty
candidate_review_reason = candidate_feature_rows_empty
opportunity_review_reason = candidate_dependency_review_required
```

Failed feature artifact:

```text
.runtime/operations/feature_artifacts/2026-03-24/candidate_features.parquet
row_count = 4310
universe_eligible true = 0
missing_flags_insufficient_history true = 4310
data_start_date mode = 2026-02-16
```

Source comparison:

| Stage | Earliest | Latest | Trading dates | Symbols | Judgment |
| --- | ---: | ---: | ---: | ---: | --- |
| Acquisition normalized OHLCV | 2021-08-02 | 2026-07-14 | 1211 | 4977 | Source has sufficient history |
| Operations canonical normalized OHLCV | 2026-02-16 | 2026-07-14 | 101 | 4375 | Insufficient for 2026-03-24 feature lookback |
| Failed Historical logical OHLCV | 2026-02-16 | 2026-03-24 | 25 | 4310 | Insufficient logical input |

Root cause:

```text
HISTORICAL_ASOF_LOGICAL_INPUT_USED_SHORT_OPERATIONS_CANONICAL_BEFORE_FEATURE_LOOKBACK_SOURCE_SELECTION
```

## Contract

Authority:

```text
src/ai_fund_lab_v2/runtime_v2/market_data_bootstrap.py
REQUIRED_LOOKBACK_BUSINESS_DAYS = 61
```

The requirement is 61 trading observations because Candidate features include a 60-day return that needs both `t` and `t-60`.

Feature lookback evidence is now attached to Historical as-of resolution:

```text
feature_lookback_coverage.target_date
feature_lookback_coverage.required_lookback_business_days
feature_lookback_coverage.selected_source_role
feature_lookback_coverage.selected_normalized_ohlcv_path
feature_lookback_coverage.selected_trading_calendar_path
candidate_sources[].trading_calendar_lookback.required_history_start_date
candidate_sources[].trading_calendar_lookback.available_business_day_count
candidate_sources[].blocked_reasons
```

Trading day authority uses J-Quants Trading Calendar with `HolDiv == "1"` as business days. Future leakage remains blocked by materializing only rows whose date is `<= business_date`.

## Implementation

Changed files:

```text
src/ai_fund_lab_v2/runtime_v2/historical_support/asof.py
src/ai_fund_lab_v2/runtime_v2/market_refresh/pipeline.py
tests/runtime_v2/test_phase17_l_historical_asof_and_evidence_isolation.py
```

Behavior:

1. Historical market refresh calls `materialize_historical_logical_inputs(..., require_feature_lookback=True)`.
2. The resolver evaluates the operations canonical OHLCV against the common 61-business-day feature lookback requirement.
3. If operations canonical is short, it scans saved acquisition staging sources under `.runtime/market_data_acquisition/runs`.
4. A source is selectable only when normalized OHLCV is duplicate-free, J-Quants-derived, free of training/future columns, and has Trading Calendar lookback coverage.
5. The selected source is written as run-scoped logical input with `Date <= business_date`; physical source files are not mutated.
6. If no source passes, resolution returns `HALT / historical_feature_lookback_insufficient`.

## Probe Result

Read-only resolver probe for `2026-03-24`:

```text
status = PASS
reason = historical_asof_view_ready
selected_source_role = acquisition_staging
selected_normalized_ohlcv_path = .runtime/market_data_acquisition/runs/jquants-acquisition-20210802-20260714-bh/raw_normalized/jquants/equities_bars_daily/data.parquet
selected_trading_calendar_path = .runtime/market_data_acquisition/runs/jquants-acquisition-20210802-20260714-bh/raw/jquants/trading_calendar/data.parquet
required_history_start_date = 2025-12-19
available_business_day_count = 61
```

Short isolated Feature Refresh probe using the selected logical input:

```text
feature_refresh_status = FEATURES_READY
candidate_rows = 4918
candidate_universe_eligible_rows = 3738
logical_history_start = 2021-08-02
logical_history_end = 2026-03-24
future_rows_after_2026-03-24 = 0
```

This directly closes the observed `candidate_feature_rows_empty` failure mode for the Bull campaign start date without changing feature formulas or forcing eligibility.

## Why Prior Tests Missed It

Existing Historical as-of tests verified future row exclusion and run-scoped evidence, but they did not require feature lookback coverage before feature generation. Existing bootstrap tests verified warmup sufficiency for the operations canonical source, but Historical runtime did not use that contract when selecting the source for as-of logical input.

New regression coverage verifies:

```text
short operations canonical + sufficient acquisition source -> acquisition_staging selected
no source with required lookback -> fail closed
future rows after business_date -> excluded from logical input
pipeline Historical mode -> requires feature lookback
```

## Validation

Executed:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase17_l_historical_asof_and_evidence_isolation.py
PYTHONPYCACHEPREFIX=/private/tmp/pycache PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase20_bb_runtime_market_data_bootstrap.py
PYTHONPYCACHEPREFIX=/private/tmp/pycache PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase20_bh_historical_trading_calendar_business_day_authority.py
PYTHONPYCACHEPREFIX=/private/tmp/pycache PYTHONPATH=src:. python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/historical_support/asof.py src/ai_fund_lab_v2/runtime_v2/market_refresh/pipeline.py
python3 -m json.tool reports/phase_reports/phase20_bi_feature_lookback_contract.json
python3 -m json.tool reports/phase20_bi_feature_lookback_contract/probe_summary.json
git diff --check -- <BI changed files>
```

Result:

```text
8 passed
4 passed
7 passed
py_compile PASS
json validation PASS
git diff --check PASS
```

Executed short probe only:

```text
Historical as-of resolver for 2026-03-24
Feature Refresh against /private/tmp logical input
```

Not executed:

```text
20BD Historical Run
Bull/Bear/Range campaign runs
Broker connection
Training
Calibration
Full backtest
Accepted Generation change
```

## User Re-run Command

After this fix, the Bull campaign can be retried as a new run:

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src:.

python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --date-from 2026-03-24 \
  --date-to 2026-04-20 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Expected early checks:

```text
historical_asof_view.feature_lookback_coverage.status = PASS
selected_source_role = acquisition_staging unless operations canonical is bootstrapped
candidate_feature_rows > 0
universe_eligible_rows > 0
no future rows after business_date in logical input
```
