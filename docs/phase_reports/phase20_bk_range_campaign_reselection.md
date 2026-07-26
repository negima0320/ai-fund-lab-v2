# Phase20-BK Corporate Action Non-impact Range Campaign Reselection

## Status

```text
PHASE20_BK_RANGE_CAMPAIGN_RESELECTION_COMPLETE
```

## Scope

This phase reselects a formal RANGE / sideways 20BD campaign period for Phase20 cross-regime comparison after the previous RANGE run halted on a supported Corporate Action fail-closed guard.

No Runtime logic, PM logic, Candidate Producer, Opportunity, Safety, threshold, Accepted Generation, broker path, training, calibration, 20BD fresh run, resume, Bull rerun, Bear rerun, or Range rerun was executed or changed.

## Sources Reviewed

- `docs/phase_reports/phase20_bj_corporate_action_guard_and_runtime_continuation_contract.md`
- `docs/phase_reports/phase20_bi_feature_lookback_contract.md`
- `docs/phase_reports/phase20_pm_cross_regime_validation_plan.md`
- `docs/phase_reports/phase20_y_pm_cross_regime_validation_campaign.md`
- `docs/phase_reports/phase20_ba_cross_regime_campaign_reselection.md`
- `docs/02_architecture/runtime_test_specification.md`
- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/01_requirements/phase_roadmap.md`
- `scripts/analyze_pm_cross_regime.py`
- `reports/phase_reports/phase20_pm_cross_regime_candidate_periods.json`

## Authority

Market regime classification uses the existing Phase20-T/Y contract:

```text
market_return_proxy = equal_weight_mean_symbol_close_to_close_return
RANGE = abs(period_return) <= 0.018 and high_low_range <= 0.055
LOW_VOLATILITY = realized_volatility <= 25th percentile
```

The previous Phase20-Y RANGE period, `2026-04-10` to `2026-05-13`, remains market-regime valid but is no longer usable as the main completed 20BD RANGE baseline because run `runtime-test-historical-extended-smoke-20260724T000054969857Z` halted at `2026-04-22:submit` on Corporate Action impact evidence for `60850`.

Feature lookback and historical as-of authority are evaluated with the Phase20-BI resolver using `require_feature_lookback=True`.

Corporate Action pre-check uses raw J-Quants OHLCV `AdjFactor != 1.0` inventory from:

```text
.runtime/market_data_acquisition/runs/jquants-acquisition-20210802-20260714-bh/raw/jquants/equities_bars_daily/data.parquet
```

## Candidate Summary

| Candidate | Start | End | BD | Regime | Return | Volatility | High-low range | Outcome 20BD end | CA rows | Warmup | Judgment |
|---|---|---|---:|---|---:|---:|---:|---|---:|---|---|
| `BK-RANGE-001` | `2022-08-01` | `2022-08-29` | 20 | RANGE, LOW_VOLATILITY | 1.52% | 0.57% | 2.92% | `2022-09-28` | 0 | PASS | RECOMMENDED |
| `BK-RANGE-002` | `2022-04-26` | `2022-05-27` | 20 | RANGE, SHARP_DROP_AND_REBOUND | 0.39% | 0.91% | 3.79% | `2022-06-24` | 0 | PASS | ACCEPTABLE_SECONDARY |
| `BK-RANGE-003` | `2023-08-01` | `2023-08-29` | 20 | RANGE | 0.47% | 0.60% | 3.77% | `2023-09-27` | 0 | PASS | ACCEPTABLE_SECONDARY |
| `BK-RANGE-004` | `2023-07-31` | `2023-08-28` | 20 | RANGE | 0.72% | 0.61% | 3.53% | `2023-09-26` | 0 | PASS | ACCEPTABLE_SECONDARY |

Recommended formal RANGE period:

```text
start_date = 2022-08-01
end_date = 2022-08-29
business_days = 20
candidate_id = BK-RANGE-001
```

Selection rationale:

- It satisfies the Phase20-T/Y RANGE rule and also has LOW_VOLATILITY classification.
- It has 20BD post-period outcome coverage.
- It has Phase20-BI feature lookback authority PASS.
- It has Historical as-of authority PASS and listed-issues snapshot authority PASS at the start date.
- It has no raw J-Quants `AdjFactor != 1.0` rows inside the 20BD campaign window.
- It does not overlap the existing Bull or Bear campaign windows.

## Candidate Details

### BK-RANGE-001

```text
start_date = 2022-08-01
end_date = 2022-08-29
business_days = 20
period_return = 0.01518717
realized_volatility = 0.00566714
high_low_range = 0.02918489
breadth = 0.46346378
largest_decline = -0.01080625
largest_rebound = 0.01233781
outcome_business_days_available = 947
outcome_20bd_end_date = 2022-09-28
```

Authority:

```text
historical_asof_status = PASS
feature_lookback_status = PASS
selected_source_role = acquisition_staging
required_history_start_date = 2022-05-06
available_business_day_count = 61
listed_issues_snapshot_date = 2022-08-01
listed_issues_snapshot_age_days = 0
listed_issues_content_hash_verified = true
```

Corporate Action pre-check:

```text
AdjFactor != 1.0 rows in campaign window = 0
CA impact risk = LOW_FROM_AVAILABLE_ADJFACTOR_INVENTORY
```

### BK-RANGE-002

```text
start_date = 2022-04-26
end_date = 2022-05-27
business_days = 20
period_return = 0.00390747
realized_volatility = 0.00909406
high_low_range = 0.03788410
breadth = 0.46743306
largest_decline = -0.01761697
largest_rebound = 0.01774838
outcome_business_days_available = 1011
outcome_20bd_end_date = 2022-06-24
```

Authority:

```text
historical_asof_status = PASS
feature_lookback_status = PASS
selected_source_role = acquisition_staging
required_history_start_date = 2022-01-27
available_business_day_count = 61
listed_issues_snapshot_date = 2022-04-26
listed_issues_snapshot_age_days = 0
listed_issues_content_hash_verified = true
```

Corporate Action pre-check:

```text
AdjFactor != 1.0 rows in campaign window = 0
CA impact risk = LOW_FROM_AVAILABLE_ADJFACTOR_INVENTORY
```

### BK-RANGE-003

```text
start_date = 2023-08-01
end_date = 2023-08-29
business_days = 20
period_return = 0.00465814
realized_volatility = 0.00596880
high_low_range = 0.03768105
breadth = 0.47250346
largest_decline = -0.01185932
largest_rebound = 0.00761610
outcome_business_days_available = 701
outcome_20bd_end_date = 2023-09-27
```

Authority:

```text
historical_asof_status = PASS
feature_lookback_status = PASS
selected_source_role = acquisition_staging
required_history_start_date = 2023-05-08
available_business_day_count = 61
listed_issues_snapshot_date = 2023-08-01
listed_issues_snapshot_age_days = 0
listed_issues_content_hash_verified = true
```

Corporate Action pre-check:

```text
AdjFactor != 1.0 rows in campaign window = 0
CA impact risk = LOW_FROM_AVAILABLE_ADJFACTOR_INVENTORY
```

## Rejected / Not Recommended Periods

### Previous RANGE Run-E

```text
period = 2026-04-10 to 2026-05-13
market_regime_status = RANGE-valid as Phase20-Y secondary RANGE
runtime_status = HALT at 2026-04-22:submit
ca_rows_in_window = 12
known_halt_symbol = 60850
known_halt_date = 2026-04-22
judgment = NOT_RECOMMENDED_FOR_MAIN_RANGE_20BD_BASELINE
```

This period is valid Corporate Action safe-halt evidence, but not a completed 20BD RANGE comparison baseline.

### Phase20-T Run-C

```text
period = 2026-06-02 to 2026-06-29
market_regime_status = RANGE
outcome_20bd_coverage = FAIL under current data ending 2026-07-14
ca_rows_in_window = 36
judgment = NOT_RECOMMENDED_FOR_THIS_CAMPAIGN
```

## Limitations

- Candidate Feature artifacts for the newly selected old-date starts were not generated in this phase. The evidence is resolver-level lookback and authority PASS, not a fresh feature artifact run.
- The recommended RANGE period is in 2022, while the completed Bull and Bear campaign runs are in 2026. Execution setup is comparable, but calendar-year market context is not identical.
- Current regenerated market-proxy classification over the long acquisition-normalized source is affected by Corporate Action scale discontinuities in 2026. Therefore the selected recommendation relies on the existing Phase20-T/Y classification contract and raw AdjFactor inventory rather than post-hoc PM outcomes.
- `AdjFactor == 1.0` does not prove all possible corporate events are absent. It is the available accepted proxy for this phase.

## User Execution Command

Codex did not execute this command.

```bash
cd /Users/negishi/work/ai-fund-lab-v2
export PYTHONPATH=src:.
python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --business-days 20 \
  --start-date 2022-08-01 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

Expected checks:

```text
Historical as-of authority PASS
feature_lookback_coverage.status PASS
candidate_feature_rows > 0
universe_eligible rows > 0
PM HALTなし
Corporate Action Guard HALTなし
completed_days = 20
```

## Cross-Regime Analysis Command

After the new RANGE run completes, replace `<NEW_RANGE_RUN_ID>`:

```bash
PYTHONPATH=src python3 scripts/analyze_pm_cross_regime.py analyze-runs \
  --run-id runtime-test-historical-extended-smoke-20260723T215847198556Z \
  --run-id runtime-test-historical-extended-smoke-20260723T225746889854Z \
  --run-id <NEW_RANGE_RUN_ID> \
  --output-json reports/phase_reports/phase20_y_pm_cross_regime_campaign_analysis.json
```

## Acceptance

```text
RANGE_CANDIDATES_RESELECTED = PASS
AT_LEAST_THREE_RANGE_CANDIDATES_EVALUATED = PASS
RECOMMENDED_RANGE_PERIOD_SELECTED = PASS
CORPORATE_ACTION_PRECHECK_COMPLETED = PASS
FEATURE_LOOKBACK_AUTHORITY_PASS = PASS
OUTCOME_20BD_COVERAGE_PASS = PASS
NO_RUNTIME_LOGIC_CHANGED = PASS
LONG_RUNNING_HISTORICAL_TEST_NOT_EXECUTED = PASS
USER_REVALIDATION_COMMANDS_READY = PASS
```

Final judgment:

```text
PHASE20_BK_RANGE_CAMPAIGN_RESELECTION_COMPLETE
```
