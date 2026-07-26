# Phase20-Y PM Cross-Regime Validation Campaign

## Status

```text
PHASE20_Y_PM_CROSS_REGIME_VALIDATION_CAMPAIGN_READY
```

## Primary Campaign Periods

| Regime | Campaign ID | Source | Start | End | Business Days | Return | Volatility | Outcome 20BD | Readiness |
|---|---|---|---|---:|---:|---:|---:|---|---|
| BULL | `PM20Y-Run-A` | `PRIMARY_REGIME` | `2026-03-24` | `2026-04-20` | 20 | 0.05091969 | 0.01171409 | `2026-05-22` | `READY` |
| BEAR | `PM20Y-Run-B` | `PRIMARY_REGIME` | `2026-03-02` | `2026-03-30` | 20 | -0.07677402 | 0.01805827 | `2026-04-27` | `READY` |
| RANGE | `PM20Y-Run-E` | `SECONDARY_REGIME_DATA_AVAILABILITY_FALLBACK` | `2026-04-10` | `2026-05-13` | 20 | 0.00138204 | 0.00516529 | `2026-06-10` | `READY` |

## Secondary Candidates

### BULL

```text
No ready secondary candidate in current Phase20-T selected candidates.
```

### BEAR

```text
No ready secondary candidate in current Phase20-T selected candidates.
```

### RANGE

```text
No ready secondary candidate in current Phase20-T selected candidates.
```

## Selection Basis

Candidate periods are from Phase20-T market-data-only selection. PM decisions, PM outcomes, portfolio PnL, ledger, broker evidence, and post-run results were not used to choose or replace periods.

The original strongest RANGE candidate `Run-C` is retained in evaluated candidates but is not selected for the first campaign because existing OHLCV does not provide 20BD post-period coverage after `2026-06-29`. The campaign RANGE primary uses `Run-E`, which is RANGE-labeled by Phase20-T secondary regime and has sufficient 20BD post-period coverage.

## Run Independence Contract

```json
{
  "broker_environment": "historical_simulated",
  "execution_mode": "fresh-run only",
  "external_effects_allowed": false,
  "initial_cash": 1000000,
  "initial_pending": "empty",
  "initial_positions": "empty",
  "ledger_carryover_between_runs": false,
  "portfolio_carryover_between_runs": false,
  "runtime_state_carryover_between_runs": false
}
```

## User Execution Commands

### BULL

```bash
cd /Users/negishi/work/ai-fund-lab-v2

PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --business-days 20 \
  --start-date 2026-03-24 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

### BEAR

```bash
cd /Users/negishi/work/ai-fund-lab-v2

PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --business-days 20 \
  --start-date 2026-03-02 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

### RANGE

```bash
cd /Users/negishi/work/ai-fund-lab-v2

PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --business-days 20 \
  --start-date 2026-04-10 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state \
  --json
```

## Stop Conditions

- Do not start the next run unless the previous run final_judgment is PASS.
- Stop campaign on HALT, REVIEW_REQUIRED, BLOCKED, non-zero exit_code, completed_days < 20, PM HALT evidence, broker write, external delivery, Accepted Generation change, or Registry change.

## Cross-Regime Analysis Command

```bash
PYTHONPATH=src python3 scripts/analyze_pm_cross_regime.py analyze-runs \
  --run-id <BULL_RUN_ID> \
  --run-id <BEAR_RUN_ID> \
  --run-id <RANGE_RUN_ID> \
  --output-json reports/phase_reports/phase20_y_pm_cross_regime_campaign_analysis.json
```

## Analysis Dimensions

```json
{
  "action": [
    "HOLD",
    "REDUCE",
    "EXIT",
    "ADD"
  ],
  "dominant_cause_minimum": [
    "EXIT_BY_HARD_STOP",
    "REDUCE_BY_WEAK_HOLD_SCORE",
    "REDUCE_BY_PEAK_DRAWDOWN_WARNING",
    "HOLD_BY_PARTIAL_CONTINUATION",
    "ADD_BY_STRONG_TREND_AND_RANK"
  ],
  "market_regime": [
    "BULL",
    "BEAR",
    "RANGE"
  ],
  "outcome_horizons_bd": [
    1,
    5,
    10,
    20
  ],
  "symbol_volatility": [
    "LOW_SYMBOL_VOLATILITY",
    "MEDIUM_SYMBOL_VOLATILITY",
    "HIGH_SYMBOL_VOLATILITY"
  ]
}
```

## Required Metrics

- sample count
- mean return
- median return
- positive rate
- negative rate
- p25
- p75
- worst return
- best return

## Evidence Sufficiency Policy

```json
{
  "labels": {
    "INSUFFICIENT": "sample_count < 5",
    "MODERATE": "sample_count >= 15 and < 30",
    "PRELIMINARY": "sample_count >= 5 and < 15",
    "STRONG": "sample_count >= 30"
  },
  "rule": "Do not decide PM changes from single decisions or small samples.",
  "status": "ANALYSIS_LABEL_ONLY_NOT_PRODUCTION_CONTRACT"
}
```

## Acceptance

- CANDIDATE_PERIODS_VERIFIED: PASS
- BULL_PRIMARY_READY: PASS
- BEAR_PRIMARY_READY: PASS
- RANGE_PRIMARY_READY: PASS
- RUN_INDEPENDENCE_CONTRACT_DEFINED: PASS
- USER_EXECUTION_COMMANDS_READY: PASS
- CROSS_REGIME_ANALYSIS_COMMAND_READY: PASS
- ACTION_ANALYSIS_DIMENSIONS_DEFINED: PASS
- CAUSE_ANALYSIS_DIMENSIONS_DEFINED: PASS
- VOLATILITY_ANALYSIS_DIMENSIONS_DEFINED: PASS
- OUTCOME_HORIZONS_DEFINED: PASS
- EVIDENCE_SUFFICIENCY_POLICY_DEFINED: PASS
- PM_LOGIC_UNCHANGED: PASS
- ACCEPTED_GENERATION_UNCHANGED: PASS
- LONG_RUNNING_HISTORICAL_TEST_NOT_EXECUTED: PASS

## Prohibited Operations Confirmation

Codex did not execute 20BD fresh-runs, multiple Historical runs, Broker connections, Training, Calibration, PM logic changes, or Accepted Generation changes.

## Final Judgment

```text
PHASE20_Y_PM_CROSS_REGIME_VALIDATION_CAMPAIGN_READY
```
