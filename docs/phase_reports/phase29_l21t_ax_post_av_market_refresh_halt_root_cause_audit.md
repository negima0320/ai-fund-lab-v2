# Phase29-L21T-AX — Post-AV Market Refresh HALT Root Cause Audit

## Task ID

Phase29-L21T-AX

## Primary Judgment

PHASE29_L21T_AX_AV_FEATURE_PRODUCER_CONSUMER_SCHEMA_MISMATCH_CONFIRMED_REPAIR_REQUIRED

Phase29 remains active. Phase30 was not entered.

## Scope

READ-ONLY audit only. No Strategy, Runtime, Config, Model, Threshold, target run,
resume, replay, recovery, or fresh-run mutation was performed.

Target run:

```text
runtime-test-historical-extended-smoke-20260814T120359040104Z
```

HALT:

- Business date: `2022-08-10`
- Stage/job: `market_refresh`
- Runtime CLI exit code: `20`
- Runtime Test exit code: `30`
- completed_days: `0`

AV BUY Quality / BUY_WAIT authority was not reached.

## Direct Error

Canonical evidence:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260814T120359040104Z/daily/2022-08-10/market_refresh/progress_latest.json
```

Direct reason:

```text
consumer_schema_review_required:candidate,opportunity
```

Status:

```text
REVIEW_REQUIRED
```

The copied runtime manifest confirms:

```text
final_state = REVIEW_REQUIRED
reason = consumer_schema_review_required:candidate,opportunity
candidate_schema_status = REVIEW_REQUIRED
opportunity_schema_status = REVIEW_REQUIRED
pm_schema_status = READY
missing_feature_artifacts = []
missing_quote_count = 0
```

## Failing Artifact / Gate

Failing gate:

```text
runtime_v2 market_refresh consumer readiness / canonical feature schema gate
```

Failing artifacts:

```text
.runtime/operations/feature_artifacts/2022-08-10/candidate_features.parquet
.runtime/operations/feature_artifacts/2022-08-10/opportunity_feature_input.parquet
```

Feature refresh itself completed:

```text
feature_generation_executed = true
feature_refresh_status = FEATURES_READY
blocked_reasons = []
row_count = 4165
future_leakage_check_status = OK
```

The halt happens after feature generation, when the runtime consumer schema gate
validates the generated candidate/opportunity artifacts.

## Missing AV Columns

The generated candidate and opportunity artifacts both lack the AV columns:

```text
price_momentum_return_1d
price_momentum_return_3d
price_momentum_return_10d
recent_move_volatility_z_1d
recent_move_volatility_z_3d
momentum_5d_vs_20d_delta
momentum_1d_vs_5d_delta
```

Observed artifact shapes:

- `candidate_features.parquet`: `4165 x 33`
- `opportunity_feature_input.parquet`: `4165 x 35`

Existing momentum columns are present:

```text
price_momentum_return_5d
price_momentum_return_20d
price_momentum_return_60d
volume_momentum_ratio_5d
volume_momentum_ratio_1d_20d
```

Therefore this is a missing-column schema mismatch, not malformed values inside
the new columns.

## Historical Source / Prior History

The historical normalized quote source used by market_refresh exists:

```text
reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260814T120359040104Z/daily/2022-08-10/market_refresh/inputs/historical_asof/2022-08-10/raw_normalized/jquants/equities_bars_daily/data.parquet
```

Observed source coverage:

- rows: `246218`
- symbols: `4165`
- dates: `2022-05-17` through `2022-08-10`
- business-date count: `61`

Sample checks:

- `78780`: 54 rows through `2022-08-10`
- `53800`: 43 rows through `2022-08-10`
- `72030`: 61 rows through `2022-08-10`

This confirms the halt is not explained by the first validation day alone. The
run has enough prior history for 1BD / 3BD / 10BD calculation for ordinary
eligible symbols, and the feature refresh warmup evidence reports sufficient
lookback where applicable.

## Producer / Consumer Mismatch

Consumer readiness was updated by AV:

```text
src/ai_fund_lab_v2/runtime_v2/market_refresh/consumer_readiness.py
```

It now requires the AV multi-horizon columns for candidate and opportunity
artifacts.

Actual market_refresh generation path for this run is:

```text
src/ai_fund_lab_v2/paper_trading/feature_refresh.py
```

Evidence from that producer:

- `OPPORTUNITY_MODEL_INPUT_COLUMNS` still lists only 5D / 20D / 60D momentum and
  volume / volatility / trend fields.
- `REQUIRED_COLUMNS["candidate"]` does not include AV 1D / 3D / 10D / z / delta
  fields.
- `_formal_feature_values()` computes only 5D / 20D / 60D momentum plus legacy
  volume / volatility / trend fields.
- `_build_opportunity_feature_input()` copies only columns in
  `OPPORTUNITY_MODEL_INPUT_COLUMNS`, so the opportunity artifact cannot contain
  AV fields until the producer contract is updated.

AV updated several feature builders, but this actual Production-common runtime
market_refresh producer remains stale relative to the new consumer schema.

## Required Judgments

- HALT canonical error / judgment: `consumer_schema_review_required:candidate,opportunity`
- Failing artifact / gate: market_refresh consumer readiness schema gate for
  candidate and opportunity feature artifacts
- Missing feature: YES
- Malformed feature: NO
- Historical feature regeneration gap: YES, in the sense that regenerated
  runtime artifacts were produced by a stale feature producer contract and lack
  AV columns
- Schema / consumer readiness mismatch: YES
- AV implementation regression: YES, scoped to incomplete producer integration
  in actual market_refresh path
- Stale fixture / stale generated artifact: PARTIAL. The generated artifact is
  stale relative to AV schema because the producer is stale, not because the
  2022-08-10 source lacks history.

## AV Causality

AV causal: YES.

The halt is caused by AV adding new required consumer columns while the actual
runtime market_refresh feature producer did not materialize those columns. This
is not caused by BUY_WAIT classification logic and not by threshold semantics.

## Repair Implication

Implementation repair is required in a separate task.

Likely repair scope:

- Update `src/ai_fund_lab_v2/paper_trading/feature_refresh.py` candidate /
  opportunity feature generation to materialize the AV multi-horizon fields.
- Preserve existing 5BD / 20BD semantics.
- Do not zero-fill missing values.
- Keep fail-closed behavior for true missing / malformed feature evidence.
- Update focused market_refresh / consumer readiness regression for actual
  runtime producer path.

## Runtime Mutation Statement

Runtime mutated by Codex: NO.

No target run resume, replay, recovery, fresh-run, or manual artifact edit was
performed.

## Recommended Next Task

Phase29-L21T-AY — Runtime Market Refresh Multi-Horizon Feature Producer
Integration Repair
