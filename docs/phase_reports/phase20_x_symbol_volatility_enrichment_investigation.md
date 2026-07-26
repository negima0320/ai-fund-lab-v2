# Phase20-X Symbol Volatility Enrichment Investigation and Repair

## Status

```text
PHASE20_X_SYMBOL_VOLATILITY_ENRICHMENT_COMPLETE
```

## Scope

Target run:

```text
runtime-test-historical-extended-smoke-20260722T215152074231Z
```

This phase investigated why Phase20-T analysis produced:

```text
decision_count = 17
symbol_volatility = null
symbol_volatility_bucket = UNKNOWN
UNKNOWN count = 17
```

No PM Runtime Adapter, PM threshold, score formula, decision order, REDUCE intensity, Sell Planning, BUY, Risk, Runtime trading behavior, Accepted Generation, Artifact Registry, Broker, Training, Calibration, Validation run, or Historical run was changed or executed.

## Root Cause

Final cause:

```text
VOLATILITY_CALCULATION_NOT_IMPLEMENTED
```

The Phase20-T analyzer only read:

```text
decision_trace.technical_features.volatility_return_std_20d
```

The target run-scoped PM decision snapshots did not contain `decision_trace` and did not contain direct volatility fields:

```text
symbol_volatility: 0
volatility: 0
realized_volatility: 0
atr: 0
atr_pct: 0
risk_volatility: 0
volatility_return_std_20d: 0
decision_trace: 0
```

However, Phase20-T design allows symbol volatility to be derived from existing J-Quants normalized OHLCV as analysis-only metadata. That fallback was missing from the analyzer.

PM Adapter change is not required.

## PM Artifact Findings

Run-scoped files inspected:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260722T215152074231Z/daily/*/position_management/pm_decisions.json
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260722T215152074231Z/daily/*/sell_planning/position_management_evidence.json
```

The PM decisions preserve:

```text
dominant_cause
reason_codes
feature_snapshot_ref
decision_type
action_score
confidence_semantics
```

They do not preserve volatility fields or embedded `decision_trace` in the run-scoped snapshot consumed by Phase20-T.

## Analyzer Repair

Changed:

```text
scripts/analyze_pm_cross_regime.py
tests/runtime_v2/test_phase20_t_pm_cross_regime_analysis.py
```

Repair behavior:

- Keep trace-first authority for `decision_trace.technical_features.volatility_return_std_20d`.
- Add top-level fallback paths for existing PM fields if future snapshots include them.
- Add market-data fallback from existing normalized J-Quants OHLCV.
- Compute 20BD close-to-close return standard deviation by symbol/date.
- Join volatility by normalized symbol and `business_date`.
- Require 20 observations.
- Emit `UNKNOWN` when market data or lookback is insufficient.
- Record source/status/observation count/future-data flag in each analysis decision.

Symbol normalization:

```text
8105 -> 81050
81050 -> 81050
8105.T -> 81050
```

Date join:

```text
business_date -> same-date volatility index
```

Future data policy:

```text
symbol_volatility uses only bars <= business_date
post_decision_outcome remains separate analysis-only future outcome metadata
```

## Market Data Availability

Source:

```text
.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet
```

Target symbols:

```text
45640
50310
66590
81050
89180
```

All target symbols were found with sufficient lookback. All 17 decisions had 20 observations for volatility.

## Reanalysis Result

Command:

```bash
PYTHONPATH=src python3 scripts/analyze_pm_cross_regime.py analyze-runs \
  --run-id runtime-test-historical-extended-smoke-20260722T215152074231Z \
  --output-json reports/phase_reports/phase20_x_post_fix_validation.json
```

Result:

```text
decision_count = 17
ADD = 4
EXIT = 3
HOLD = 5
REDUCE = 5
dominant_cause UNKNOWN = 0
reason_codes empty = 0
market_regime UNKNOWN = 0
symbol_volatility non-null = 17
UNKNOWN volatility bucket = 0
future_data_used_count = 0
```

Bucket counts:

```text
HIGH_SYMBOL_VOLATILITY = 9
MEDIUM_SYMBOL_VOLATILITY = 8
LOW_SYMBOL_VOLATILITY = 0
UNKNOWN = 0
```

## Tests

Executed:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/pycache PYTHONPATH=src \
  python3 -m pytest -q tests/runtime_v2/test_phase20_t_pm_cross_regime_analysis.py
```

Result:

```text
7 passed
```

Coverage added:

```text
symbol normalization test
date join test
volatility value extraction test
volatility bucket classification test
missing data -> UNKNOWN test
no future data usage test
```

## Acceptance

- ROOT_CAUSE_IDENTIFIED: PASS
- PM_DECISION_INGESTION_PRESERVED: PASS
- DOMINANT_CAUSE_PRESERVED: PASS
- REASON_CODES_PRESERVED: PASS
- SYMBOL_VOLATILITY_ENRICHMENT_WORKING: PASS
- VOLATILITY_BUCKET_CLASSIFICATION_WORKING: PASS
- NO_FUTURE_DATA_USAGE: PASS
- PM_LOGIC_UNCHANGED: PASS
- PRODUCER_UNCHANGED: PASS
- ACCEPTED_GENERATION_UNCHANGED: PASS
- LONG_RUNNING_HISTORICAL_TEST_NOT_EXECUTED: PASS

## Final Judgment

```text
PHASE20_X_SYMBOL_VOLATILITY_ENRICHMENT_COMPLETE
```
