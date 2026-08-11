# Phase29-L5 Long-Horizon Raw OHLCV Authority Repair

## Status

COMPLETE

ROOT CAUSE CONFIRMED

NARROW PRODUCTION-COMMON REPAIR COMPLETE

CANONICAL RAW OHLCV MATERIALIZED

SHORT REGRESSION PASS

NO STRATEGY / PM / ADD / BUY / SELL SEMANTIC CHANGE

NO MARKET-DATA ACQUISITION

NO LONG BOOTSTRAP

NO HISTORICAL EXECUTION

## Primary Judgment

PHASE29_L5_RAW_OHLCV_CANONICAL_AUTHORITY_REPAIRED_SHORT_REGRESSION_PASS_LONG_HORIZON_RETRY_READY

## Direct HALT Cause

The user 977BD Historical fresh-run halted on day 0:

```text
run_id = runtime-test-historical-smoke-20260810T151835820840Z
business_date = 2022-08-10
job = market_refresh
reason = historical_asof_authority_invalid
```

The failing authority was `raw_ohlcv`. `normalized_ohlcv`, `trading_calendar`,
and `listed_issues` were already PASS.

Before repair, canonical raw OHLCV was still short-horizon:

```text
path = .runtime/operations/jquants/raw/jquants/equities_bars_daily/data.parquet
rows = 448,964
min_date = 2026-02-16
max_date = 2026-07-14
rows <= 2022-08-10 = 0
```

Therefore the 2022-08-10 PIT logical view was empty and correctly fail-closed.

## Source Audit

The completed long-horizon acquisition staging raw source exists:

```text
path = .runtime/market_data_acquisition/runs/jquants-acquisition-20220517-20260807/raw/jquants/equities_bars_daily/data.parquet
rows = 4,504,589
min_date = 2022-05-17
max_date = 2026-08-07
duplicate Date/Code = 0
jquants_lineage_status = PASS
hash = 203fb2f0a0e388cefce53d395186fc6e44c3d63cb513c6e1a64dc4d8becc6bcc
```

The paired normalized staging source also exists and remains unchanged. API
refetch is not required.

## Contract

`raw_ohlcv` is a mandatory Historical as-of authority. It is separate from
`normalized_ohlcv` and is used as provider/raw J-Quants equities bars evidence,
including AdjFactor/corporate-action authority. The correct repair is not to
ignore raw and not to reverse-generate raw from normalized.

Classification:

```text
Historical raw authority class = L5-A RAW_OHLCV_IS_REQUIRED_CANONICAL_AUTHORITY
Root cause = L5-RC2 BOOTSTRAP_ONLY_MATERIALIZED_NORMALIZED_OHLCV
Production defect = YES
```

## Implementation

Updated:

```text
src/ai_fund_lab_v2/runtime_v2/source_authority_materialization.py
tests/runtime_v2/test_phase29_l5_raw_ohlcv_materialization.py
```

Added `materialize_raw_ohlcv_authority`, which performs:

```text
validated acquisition raw OHLCV
-> staging plan/state/final_validation gate
-> raw schema / Date-Code duplicate / lineage / coverage gate
-> byte-preserving atomic copy to canonical operations raw OHLCV
-> post-materialization inventory/hash verification
```

It fails closed for:

```text
missing source
missing staging validation artifacts
invalid raw schema
Date/Code duplicates
J-Quants lineage mismatch
coverage insufficiency
post-materialization verification mismatch
```

No Strategy, PM, ADD, BUY_NEW, SELL, REDUCE, EXIT, D61/D69, cash, concentration,
Safety, thresholds, or Accepted Generation logic was changed.

## Materialization Result

Canonical raw OHLCV after repair:

```text
path = .runtime/operations/jquants/raw/jquants/equities_bars_daily/data.parquet
rows = 4,504,589
min_date = 2022-05-17
max_date = 2026-08-07
duplicate Date/Code = 0
jquants_lineage_status = PASS
hash = 203fb2f0a0e388cefce53d395186fc6e44c3d63cb513c6e1a64dc4d8becc6bcc
```

The canonical target hash matches the staging raw source hash.

## PIT Validation

Representative Historical as-of checks now PASS:

```text
2022-08-10:
  raw_ohlcv = PASS
  raw logical rows = 255,565
  raw future rows excluded = 4,249,024
  overall = PASS

2023-04-03:
  raw_ohlcv = PASS
  normalized_ohlcv = PASS
  overall = PASS

2026-07-14:
  raw_ohlcv = PASS
  normalized_ohlcv = PASS
  overall = PASS
```

Future leakage is 0 for all checked dates.

## Regression

Passed:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase29_l5_raw_ohlcv_materialization.py
```

```text
5 passed in 0.66s
```

Passed:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase29_l5_raw_ohlcv_materialization.py tests/runtime_v2/test_phase29_l4_b_authority_materialization.py tests/runtime_v2/test_phase20_bb_runtime_market_data_bootstrap.py
```

```text
21 passed in 25.16s
```

Passed:

```bash
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase17_l_historical_asof_and_evidence_isolation.py
```

```text
13 passed in 2.34s
```

Compile passed:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache PYTHONPATH=src python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/source_authority_materialization.py src/ai_fund_lab_v2/runtime_v2/historical_support/asof.py
```

## Resume / Fresh Decision

The halted run completed zero business days and had no ledger mutations.
However, canonical source authority changed materially before day 0 completed.
Use a fresh run for a clean source baseline.

```text
RESUME ALLOWED = NO
FRESH-RUN REQUIRED = YES
```

Recommended operator command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-smoke \
  --date-from 2022-08-10 \
  --date-to 2026-08-09 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```

## Evidence

Evidence root:

```text
reports/phase29_l5_long_horizon_raw_ohlcv_authority_repair/
```

Files:

```text
raw_acquisition_source_inventory.json
raw_vs_normalized_contract.json
historical_asof_raw_authority_audit.json
root_cause.json
api_refetch_decision.json
materialization_result.json
pit_validation.json
regression_results.json
resume_fresh_decision.json
next_gate.json
```
