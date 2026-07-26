# Phase20-T Position Management Cross-Regime Validation Plan

## Status

PHASE20_T_PM_CROSS_REGIME_VALIDATION_PLAN_COMPLETE

## Scope

This phase prepares a validation plan only. It does not change PM thresholds, score formulas, decision order, Runtime actions, Sell Planning quantity logic, Risk logic, Opportunity logic, BUY selection, training, model artifacts, Accepted Generation, or broker logic.

No 20BD Historical Run, full smoke, broker connection, order, Production API, Demo API, or Runtime trading-state mutation was executed by Codex.

## Required Sources Reviewed

- `docs/phase_reports/phase20_position_management_design_review.md`
- `docs/phase_reports/phase20_position_management_decision_trace_and_outcome_analysis.md`
- `docs/phase_reports/phase20_position_management_authority_and_trace_closure.md`
- `docs/02_architecture/position_management_decision_trace_contract.md`
- `docs/02_architecture/position_management_feature_input_contract.md`
- `docs/02_architecture/position_management_reduce_quantity_contract.md`
- `docs/03_ai_design/position_management_ai_design.md`
- `src/ai_fund_lab_v2/position_management_ai/inference.py`
- `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py`
- `schemas/runtime_v2/position_management_decision_trace.schema.json`

## Available Data

Existing J-Quants normalized OHLCV:

```text
.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet
```

Observed coverage:

| Item | Value |
|---|---:|
| Oldest business date | 2026-02-16 |
| Latest business date | 2026-07-14 |
| Business day rows | 101 |
| OHLCV rows | 426,689 |
| Available symbols | 4,375 |
| Symbols per day min / median / max | 4,188 / 4,222 / 4,261 |
| Daily breadth calculable | yes |
| Index series found | no |

Weekday dates missing from the raw weekday calendar were treated as market holidays or non-trading days in this plan:

```text
2026-02-23
2026-03-20
2026-04-29
2026-05-04
2026-05-05
2026-05-06
```

## Market Regime Classification

No external data is fetched. Because no repository index series was found, the market proxy is built from existing normalized equities bars:

- `equal_weight_return`: mean close-to-close return across symbols
- `median_symbol_return`: median close-to-close return
- `breadth`: average positive-symbol ratio
- `realized_volatility`: standard deviation of equal-weight daily returns
- `mean_cross_sectional_volatility`: average cross-sectional return volatility
- `high_low_range`: high-low range of the cumulative market proxy
- `sharp_drop_return` and `sharp_rebound_after_drop`: 2〜5BD drop followed by 2〜10BD rebound scan

Classification thresholds are analysis-only and must not be connected to Runtime PM:

| Regime | Rule |
|---|---|
| BULL | `period_return >= 0.04` and `breadth >= 0.50` |
| BEAR | `period_return <= -0.045` and `breadth <= 0.49` |
| RANGE | `abs(period_return) <= 0.018` and `high_low_range <= 0.055` |
| HIGH_VOLATILITY | `realized_volatility >= 75th percentile` |
| LOW_VOLATILITY | `realized_volatility <= 25th percentile` |
| SHARP_DROP_AND_REBOUND | `sharp_drop_return <= -0.025` and later `sharp_rebound_after_drop >= 0.035` |

For this dataset:

- HIGH volatility threshold: `0.01461939`
- LOW volatility threshold: `0.00654634`

## Symbol Volatility Classification

Each PM decision after future runs should use decision-time trace first:

```text
decision_trace.technical_features.volatility_return_std_20d
```

Bucket proposal:

| Bucket | Rule |
|---|---|
| LOW_SYMBOL_VOLATILITY | `< 0.025` |
| MEDIUM_SYMBOL_VOLATILITY | `>= 0.025 and < 0.08` |
| HIGH_SYMBOL_VOLATILITY | `>= 0.08` |
| UNKNOWN | missing / non-finite |

This is decision-time metadata only. It must not use post-decision returns or future bars.

## Candidate Periods

The candidate periods below were selected from market data only. PM results, selected/bought symbols, broker data, portfolio PnL, paper ledger, and backtest outcomes were not used.

| Candidate | Start | End | Primary | Secondary | Return | Volatility | Largest Decline | Largest Rebound | Breadth |
|---|---|---|---|---|---:|---:|---:|---:|---:|
| Run-A | 2026-03-24 | 2026-04-20 | BULL | SHARP_DROP_AND_REBOUND | 5.09% | 1.17% | -2.54% | 2.64% | 51.52% |
| Run-B | 2026-03-02 | 2026-03-30 | BEAR | HIGH_VOLATILITY | -7.68% | 1.81% | -3.12% | 2.72% | 42.23% |
| Run-C | 2026-06-02 | 2026-06-29 | RANGE | none | -0.01% | 0.73% | -1.49% | 1.11% | 46.63% |
| Run-D | 2026-03-04 | 2026-04-01 | HIGH_VOLATILITY | none | -2.78% | 1.87% | -3.12% | 2.72% | 46.71% |
| Run-E | 2026-04-10 | 2026-05-13 | LOW_VOLATILITY | RANGE | 0.14% | 0.52% | -0.84% | 1.18% | 43.07% |
| Run-F | 2026-03-11 | 2026-04-08 | SHARP_DROP_AND_REBOUND | HIGH_VOLATILITY | 0.33% | 1.53% | -2.85% | 2.64% | 49.28% |

Detailed metrics are in:

```text
reports/phase_reports/phase20_pm_cross_regime_candidate_periods.json
```

## Runtime Test Profile and State Isolation

Code confirms the profile:

```text
historical-extended-smoke
config/runtime_tests/historical_extended_smoke_10bd.json
```

Although the config default is 10BD, the CLI accepts `--business-days 20 --start-date <START_DATE>`.

For state isolation, prefer the formal `fresh-run` command. The implementation performs the formal orchestration path:

```text
Status -> Backup -> Reset -> Plan -> Run -> Validate -> Close
```

This is safer than hand-written delete commands. Do not manually remove runtime directories. If an active run exists, use the existing runtime-test lifecycle commands rather than deleting evidence.

Run-scoped evidence is isolated under:

```text
reports/runtime_tests/runs/<RUN_ID>/
```

Historical broker writes are disabled by the profile external-effect policy:

```text
broker_write = false
tachibana_api = false
jquants_fetch = false
external_delivery = false
```

## User Run Commands

Codex did not execute these commands. They are for the user/operator.

Recommended dry-run preflight for each candidate:

```bash
cd /Users/negishi/work/ai-fund-lab-v2
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --business-days 20 \
  --start-date <START_DATE> \
  --dry-run \
  --json
```

Recommended actual fresh run for each candidate:

```bash
cd /Users/negishi/work/ai-fund-lab-v2
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --business-days 20 \
  --start-date <START_DATE> \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

Record the generated `run_id` from each fresh-run output.

Optional plan-only command when the operator wants to inspect commands before mutation:

```bash
cd /Users/negishi/work/ai-fund-lab-v2
PYTHONPATH=src python3 scripts/runtime_test.py plan \
  --profile historical-extended-smoke \
  --business-days 20 \
  --start-date <START_DATE> \
  --run-id <RUN_ID> \
  --write-evidence \
  --json
```

Candidate starts:

| Candidate | Start Date |
|---|---|
| Run-A | 2026-03-24 |
| Run-B | 2026-03-02 |
| Run-C | 2026-06-02 |
| Run-D | 2026-03-04 |
| Run-E | 2026-04-10 |
| Run-F | 2026-03-11 |

Summarize after each completed run:

```bash
cd /Users/negishi/work/ai-fund-lab-v2
PYTHONPATH=src python3 scripts/runtime_test.py summarize \
  --run-id <RUN_ID> \
  --scope full \
  --json
```

## Post-Run Cross-Regime Analysis

Read-only tool added:

```text
scripts/analyze_pm_cross_regime.py
```

Rebuild candidate periods:

```bash
cd /Users/negishi/work/ai-fund-lab-v2
PYTHONPATH=src python3 scripts/analyze_pm_cross_regime.py candidate-periods \
  --output-json reports/phase_reports/phase20_pm_cross_regime_candidate_periods.json
```

Analyze completed runs:

```bash
cd /Users/negishi/work/ai-fund-lab-v2
PYTHONPATH=src python3 scripts/analyze_pm_cross_regime.py analyze-runs \
  --run-id <RUN_A_ID> \
  --run-id <RUN_B_ID> \
  --run-id <RUN_C_ID> \
  --run-id <RUN_D_ID> \
  --run-id <RUN_E_ID> \
  --run-id <RUN_F_ID> \
  --output-json reports/phase_reports/phase20_t_pm_cross_regime_run_analysis.json
```

The tool reads run-scoped PM snapshots and existing J-Quants OHLCV. It does not start Historical runs, mutate Runtime state, connect to broker, or write post-hoc results back to Runtime decision artifacts.

For Phase20-S and later runs, `decision_trace.dominant_cause` is the preferred authority. For older snapshots without Phase20-S trace fields, the tool uses a conservative legacy fallback from existing reason codes and leaves unsupported fields as `UNKNOWN`.

## Analysis Design

After runs complete, aggregate by:

- action: HOLD / REDUCE / EXIT / ADD
- dominant cause, including zero-count expected causes
- market regime label
- symbol volatility bucket

For each group:

- count
- 1BD / 2BD / 3BD / 5BD mean
- 1BD / 2BD / 3BD / 5BD median
- positive rate
- maximum favorable excursion proxy from daily high
- maximum adverse excursion proxy from daily low

Answer these questions:

1. Does `EXIT_BY_HARD_STOP` rebound across multiple periods?
2. Is Hard Stop behavior market-regime dependent?
3. Is Hard Stop behavior symbol-volatility dependent?
4. Does `REDUCE_BY_WEAK_HOLD_SCORE` rebound across multiple periods?
5. Is `REDUCE_BY_PEAK_DRAWDOWN_WARNING` more effective than Weak Hold REDUCE?
6. Is weak `HOLD_BY_STRONG_CONTINUATION` performance a one-run artifact?
7. Is market regime enough, or is symbol-volatility adaptation also required?
8. Is there enough evidence to design Adaptive PM in Phase21?

## Phase21 Decision Criteria

Possible judgments:

- `FIXED_PM_ACCEPTABLE`
- `MARKET_REGIME_AWARE_PM_REQUIRED`
- `SYMBOL_VOLATILITY_AWARE_PM_REQUIRED`
- `MARKET_AND_SYMBOL_ADAPTIVE_PM_REQUIRED`
- `INSUFFICIENT_EVIDENCE`

Minimum criteria:

- Do not declare Adaptive PM required from one run or one symbol.
- Require at least two independent candidate periods showing the same issue.
- Prefer median and positive rate confirmation; do not rely on mean alone.
- Mark `INSUFFICIENT_EVIDENCE` when a cause has fewer than 5 decisions overall or fewer than 2 periods represented.
- Check whether results are dominated by a single outlier.
- Compare regime gaps and symbol-volatility bucket gaps separately.
- Record transaction-cost sensitivity before any later threshold experiment.
- Any Phase21 design must remain separate from Runtime PM until a later explicit experiment contract exists.

Suggested interpretation rules:

| Evidence Pattern | Judgment Candidate |
|---|---|
| No repeated adverse post-decision pattern and no regime/bucket dependency | `FIXED_PM_ACCEPTABLE` |
| Hard Stop or Hold weakness appears mainly in BEAR / HIGH_VOLATILITY / sharp rebound periods | `MARKET_REGIME_AWARE_PM_REQUIRED` |
| Hard Stop or REDUCE weakness concentrates in HIGH_SYMBOL_VOLATILITY across regimes | `SYMBOL_VOLATILITY_AWARE_PM_REQUIRED` |
| Both regime and symbol-volatility splits materially explain outcomes | `MARKET_AND_SYMBOL_ADAPTIVE_PM_REQUIRED` |
| Sample size or trace coverage is too low | `INSUFFICIENT_EVIDENCE` |

## Constraints and Limits

- The available repository OHLCV range is only 101 business days.
- No index series was found, so market regime uses an equal-weight universe proxy.
- Several candidate windows overlap; this is acceptable for planning but must be considered in final inference.
- Candidate selection used market data only, not PM outcomes.
- Symbol buckets are decision-time volatility buckets, not realized future volatility buckets.
- Candidate classification thresholds are analysis-only and must not be connected to Runtime.

## Short Validation Performed

Executed by Codex:

```text
PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m py_compile scripts/analyze_pm_cross_regime.py
PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 -m pytest -q tests/runtime_v2/test_phase20_t_pm_cross_regime_analysis.py
PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 scripts/analyze_pm_cross_regime.py candidate-periods --output-json reports/phase_reports/phase20_pm_cross_regime_candidate_periods.json
PYTHONPYCACHEPREFIX=/private/tmp/pycache python3 scripts/analyze_pm_cross_regime.py analyze-runs --run-id runtime-test-historical-extended-smoke-20260722T082906704807Z --output-json /private/tmp/phase20_t_existing_run_analysis.json
python3 -m json.tool reports/phase_reports/phase20_pm_cross_regime_candidate_periods.json
```

Results:

- compile: PASS
- unit tests: PASS, 2 tests
- candidate-period calculation: PASS
- existing-run read-only analysis smoke: PASS
- candidate JSON validation: PASS
- long-running Historical Run: NOT_EXECUTED

## Acceptance

- PM_REGIME_CLASSIFICATION_PLAN_COMPLETE: PASS
- PM_SYMBOL_VOLATILITY_CLASSIFICATION_PLAN_COMPLETE: PASS
- PM_CANDIDATE_PERIODS_SELECTED_WITHOUT_OUTCOME_LEAKAGE: PASS
- PM_HISTORICAL_RUN_COMMANDS_READY: PASS
- PM_RUN_STATE_ISOLATION_VERIFIED: PASS
- PM_CROSS_RUN_ANALYSIS_READY: PASS
- PM_PHASE21_DECISION_CRITERIA_DEFINED: PASS
- PM_THRESHOLDS_UNCHANGED: PASS
- PM_RUNTIME_BEHAVIOR_UNCHANGED: PASS
- LONG_RUNNING_HISTORICAL_TEST_NOT_EXECUTED: PASS

## Final Status

PHASE20_T_PM_CROSS_REGIME_VALIDATION_PLAN_COMPLETE
