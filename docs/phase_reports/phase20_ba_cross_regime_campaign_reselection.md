# Phase20-BA Cross-Regime Campaign Reselection

## Status

```text
PHASE20_BA_CAMPAIGN_RESELECTION_COMPLETE
```

Readiness: `NOT_READY_DATA_COVERAGE_CONSTRAINT`

## Data Coverage

```json
{
  "available_symbol_count": 4237,
  "business_day_count": 101,
  "latest_business_date": "2026-07-14",
  "oldest_business_date": "2026-02-16"
}
```

## Constraint Result

No BULL/BEAR/RANGE-complete campaign can be selected from current data while requiring 60BD warmup at run start and 20BD outcome after run end.

Eligible windows satisfying 60BD warmup, 20BD campaign, and 20BD outcome:

| Start | End | Warmup BD | Outcome BD | Labels | Return | Volatility | Candidate Rows | Eligible Proxy |
|---|---|---:|---:|---|---:|---:|---:|---:|
| `2026-05-18` | `2026-06-12` | 60 | 22 | `HIGH_VOLATILITY` | 9.4600422 | 0.01989469 | 4239 | 3807 |
| `2026-05-19` | `2026-06-15` | 61 | 21 | `HIGH_VOLATILITY` | 10.23252005 | 0.02283886 | 4211 | 3902 |
| `2026-05-20` | `2026-06-16` | 62 | 20 | `HIGH_VOLATILITY` | 10.60779664 | 0.02357644 | 4218 | 3933 |

## Selected Campaigns

- BULL: `NOT_SELECTED`
- BEAR: `NOT_SELECTED`
- RANGE: `NOT_SELECTED`

## User Execution Commands

### BULL

```bash
NOT_ISSUED: no warmup/outcome-valid candidate for this regime
```

### BEAR

```bash
NOT_ISSUED: no warmup/outcome-valid candidate for this regime
```

### RANGE

```bash
NOT_ISSUED: no warmup/outcome-valid candidate for this regime
```

## Future Leakage Contract

```json
{
  "as_of_date": "must be <= feature_date; expected same date in current historical feature refresh",
  "data_until": "must be <= feature_date; expected same date in current historical feature refresh",
  "feature_date": "must equal run business_date for each day",
  "future_ohlcv_used_for_feature": false,
  "target_date": "candidate_features.target_date must equal feature_date"
}
```

## Acceptance

- HISTORICAL_DATA_INSPECTED: PASS
- WARMUP_CONSTRAINT_ENFORCED: PASS
- OUTCOME_WINDOW_CONSTRAINT_ENFORCED: PASS
- CANDIDATE_WARMUP_CHECKED: PASS
- BULL_SELECTED: FAIL
- BEAR_SELECTED: FAIL
- RANGE_SELECTED: FAIL
- NO_HISTORICAL_RUN_EXECUTED: PASS
- CANDIDATE_PRODUCER_UNCHANGED: PASS
- PM_UNCHANGED: PASS
- SAFETY_UNCHANGED: PASS
- ACCEPTED_GENERATION_UNCHANGED: PASS

## Prohibited Operations Confirmation

Codex did not execute 20BD Historical Run, resume, BEAR Run, RANGE Run, Broker connection, Training, Calibration, model change, Candidate Producer change, PM change, Safety change, or Accepted Generation change.
