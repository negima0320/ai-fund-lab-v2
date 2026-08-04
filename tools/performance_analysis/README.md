# Phase26-I Performance Analysis Toolkit

This toolkit builds run-scoped, post-hoc performance reports for Human Review,
Performance Improvement, Observability, and Phase Comparison.

It reads only Runtime Test evidence under:

```text
reports/runtime_tests/runs/<run-id>/
```

It must not be used as input to Strategy, BUY Quality, Portfolio Policy,
Position Sizing, Planning, Safety, or Submit. Historical PnL, portfolio
performance, and drawdown are diagnostic outputs only.

## Output

Every CLI writes the shared report directory:

```text
reports/runtime_tests/runs/<run-id>/performance_report/
```

Generated files:

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

## CLIs

| CLI | Purpose |
|---|---|
| `01_summary.py` | Summary metrics: return, annualized return, final equity, PF, win rate, drawdown, holding days, cash/invested ratios |
| `02_trade_history.py` | Execution list with date, side, symbol, quantity, price, amount, campaign |
| `03_trade_with_quality.py` | Trade list enriched with Quality action, score, adjustment, rank, opportunity score, PnL, holding days |
| `04_symbol_statistics.py` | Symbol-level campaign count, win rate, PF, average PnL, holding days, re-entry count |
| `05_quality_statistics.py` | FULL / REDUCED / REVIEW / REJECT attribution |
| `06_rank_statistics.py` | Rank-level count, win rate, PF, average PnL |
| `07_equity_curve.py` | Daily cash, market value, total equity |
| `08_drawdown.py` | Drawdown path and max drawdown summary |
| `09_profit_factor.py` | Gross profit/loss, PF, win rate, average win/loss, payoff ratio, expectancy |
| `10_cash_exposure.py` | Daily cash ratio, invested ratio, position count, and descriptive stats |
| `11_holding_period.py` | Campaign-level entry, exit, holding days, winner/loser |
| `12_reentry_analysis.py` | Symbol-level entry/exit/re-entry counts, interval, PnL |

## Examples

```bash
python3 tools/performance_analysis/01_summary.py \
  --run-id runtime-test-historical-smoke-20260804T065614902857Z
```

```bash
python3 tools/performance_analysis/05_quality_statistics.py \
  --run-id runtime-test-historical-smoke-20260804T065614902857Z
```

```bash
python3 tools/performance_analysis/12_reentry_analysis.py \
  --run-id runtime-test-historical-smoke-20260804T065614902857Z \
  --json
```

## Metric Notes

- Return = final total equity - initial equity.
- Annualized Return uses the elapsed calendar days in the run-scoped equity curve.
- Profit Factor = gross realized gains / absolute gross realized losses.
- Drawdown is derived from the run-scoped daily total equity curve.
- Holding period is campaign-based and uses run-scoped fill dates.
- Open campaigns are retained with `Closed=false`; realized PF and win rate use closed campaigns.
- Missing evidence is not filled from `.runtime` or external data.
