# Phase26-I Production Runtime Performance Analysis Toolkit

## Judgment

`PHASE26_I_PRODUCTION_RUNTIME_PERFORMANCE_ANALYSIS_TOOLKIT_COMPLETE`

## Primary Implementation

Added the Production-common post-hoc Performance Analysis Toolkit under:

```text
tools/performance_analysis/
```

The toolkit is for Human Review, Performance Improvement, Observability, and
Phase Comparison only. It reads run-scoped Runtime Test evidence and writes
derived reports under:

```text
reports/runtime_tests/runs/<run-id>/performance_report/
```

It does not add inputs to Strategy, BUY Quality, Portfolio Policy, Position
Sizing, Planning, Safety, or Submit.

## CLI Coverage

- `01_summary.py`
- `02_trade_history.py`
- `03_trade_with_quality.py`
- `04_symbol_statistics.py`
- `05_quality_statistics.py`
- `06_rank_statistics.py`
- `07_equity_curve.py`
- `08_drawdown.py`
- `09_profit_factor.py`
- `10_cash_exposure.py`
- `11_holding_period.py`
- `12_reentry_analysis.py`

All CLIs require `--run-id` and use `reports/runtime_tests/runs/<run-id>` by
default. `.runtime` state is not read.

## Generated Outputs

Validated on:

```text
runtime-test-historical-smoke-20260804T065614902857Z
```

Generated:

```text
performance_summary.json
trade_history.csv
trade_with_quality.csv
symbol_statistics.csv
quality_statistics.csv
rank_statistics.csv
equity_curve.csv
drawdown.csv
cash_exposure.csv
cash_exposure_statistics.csv
holding_period.csv
reentry_statistics.csv
```

Sample summary for the validation run:

```text
Return: -23,140
Return %: -2.314%
Annualized Return: -88.19136198580998%
Final Equity: 976,860
Profit Factor: 0.0
Win Rate: 0.0
Max Drawdown: -21,140
Drawdown %: -2.118236472945892%
Average Holding Days: 1.0
BUY Count: 4
SELL Count: 1
Current Positions: 3
Cash Ratio: 0.6427021272239625
Invested Ratio: 0.35729787277603753
```

The annualized return is a short-window mathematical conversion and is not a
Strategy decision input.

## Safety Boundary

- Strategy Input Added: false
- Historical Result Used As Strategy Input: false
- Paper Ledger Used As Strategy Input: false
- Future Information Used: false
- Run-scoped Only: true
- Production / Demo / Historical Compatible: true

## Regression

- compile: PASS
- unit: PASS, `2 passed`
- JSON validation: PASS
- CSV validation: PASS
- README validation: PASS
- fresh-run: NOT EXECUTED

## Phase27 Readiness

READY. Phase27 Performance Improvement can use this toolkit as the formal
post-hoc measurement surface.
