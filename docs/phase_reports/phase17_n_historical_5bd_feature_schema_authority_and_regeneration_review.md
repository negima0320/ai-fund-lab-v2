# Phase17-N Historical 5BD Feature Schema Authority and Regeneration Review

Prefix: `Phase17-N`  
Work Name: `Historical 5BD Feature Schema Authority and Regeneration Review`  
Final Judgement: `PHASE17_N_POINT_IN_TIME_REGENERATION_REQUIRED`

## 1. Scope

Phase17-N reviewed why the 5BD Historical Runtime Clean Rerun is correctly blocked before Runtime execution.

No Feature regeneration, Trading State mutation, Registry promotion, Acceptance mutation, Reset, Rollback, Restore, Submit, Execution, J-Quants fetch, Demo, or Production access was executed.

The frozen failed run remains frozen:

```text
runtime-test-historical-smoke-20260714T040238998774Z
```

## 2. Documents and Evidence Read

Required Phase17-M/L and Phase16 acceptance, registry, AI integrity, runtime temporal, historical runtime, operational data, runtime test, and AI artifact contracts were reviewed. The generated read audit is:

```text
reports/phase17_n_historical_5bd_feature_schema_authority_and_regeneration_review/read_audit.json
```

Primary evidence files created in this review:

```text
reports/phase17_n_historical_5bd_feature_schema_authority_and_regeneration_review/artifact_provenance.json
reports/phase17_n_historical_5bd_feature_schema_authority_and_regeneration_review/candidate_schema_comparison.json
reports/phase17_n_historical_5bd_feature_schema_authority_and_regeneration_review/opportunity_schema_comparison.json
reports/phase17_n_historical_5bd_feature_schema_authority_and_regeneration_review/accepted_schema_authority.json
reports/phase17_n_historical_5bd_feature_schema_authority_and_regeneration_review/producer_consumer_contract_diff.json
reports/phase17_n_historical_5bd_feature_schema_authority_and_regeneration_review/regeneration_feasibility.json
reports/phase17_n_historical_5bd_feature_schema_authority_and_regeneration_review/migration_feasibility.json
reports/phase17_n_historical_5bd_feature_schema_authority_and_regeneration_review/ai_integrity_impact.json
reports/phase17_n_historical_5bd_feature_schema_authority_and_regeneration_review/five_bd_feature_window_audit.json
reports/phase17_n_historical_5bd_feature_schema_authority_and_regeneration_review/registry_impact.json
reports/phase17_n_historical_5bd_feature_schema_authority_and_regeneration_review/decision_matrix.json
reports/phase17_n_historical_5bd_feature_schema_authority_and_regeneration_review/validation_results.json
```

## 3. Artifact Provenance

### 2026-07-06

| Artifact | Hash | Created At | Producer Classification | Version / Feature Set |
|---|---:|---|---|---|
| `candidate_features.parquet` | `7c71b58db665861eb9dee6d63e734ccf5f47073a8ee5578a0b8c0fc7e8bc2432` | `2026-07-06T09:35:56+00:00` | old producer alias schema artifact | `phase9_candidate_features_v1`, `candidate_feature_builder_mock` |
| `opportunity_feature_input.parquet` | `8337a87f3137b2d89d278d87ccde5273162e7a5e4ec03c031baa464c47016fa2` | `2026-07-06T09:35:56+00:00` | old producer prefix schema artifact | `phase9_opportunity_feature_input_v1` |
| `position_feature_input.parquet` | `7ac704412efacc121dd4b6c9a19db25665b371345d3dd9366c39caf111a5223c` | n/a | old producer artifact | n/a |
| `capital_policy_input.parquet` | `fc2a4c36f2813db63047f7dd0d06cc8ea370ed084d70716b7f6b8fafd88d3cb7` | `2026-07-06T09:35:56+00:00` | old producer artifact | `phase9_capital_policy_input_v1` |

Manifest hashes:

- `feature_refresh_detail.json`: `091009f70ba5ffe05fa66b47dd313ec74d6e33f67b39056c2c9943022a92a80c`
- `latest_features.json`: `96a25246844f8f4bf5a4d1e78b46451e86e9f5151d0cdd6eb2698490cc2f2fe2`

### 2026-07-07

| Artifact | Hash | Created At | Producer Classification | Version / Feature Set |
|---|---:|---|---|---|
| `candidate_features.parquet` | `f791c72e02856ff2b21c4536b7659a4c93d4071424909d86724dc7bb4bf3708e` | `2026-07-08T21:26:12+00:00` | old producer alias schema artifact | `phase9_candidate_features_v1`, `candidate_feature_builder_mock` |
| `opportunity_feature_input.parquet` | `864e1b7e7507841b4e5ebb884957a9b2d4179c24b3afbc0ce24b9ab39cefa95e` | `2026-07-08T21:26:12+00:00` | old producer prefix schema artifact | `phase9_opportunity_feature_input_v1` |
| `position_feature_input.parquet` | `0f6b936c395e31f0ad15455921f43c788dd8625dd28842517fe5aff92e15c4dd` | n/a | old producer artifact | n/a |
| `capital_policy_input.parquet` | `02ca93db05ca2f9ebe2579f395079c3e109961a7f7ea52691f3b9f8823e47ab5` | `2026-07-08T21:26:12+00:00` | old producer artifact | `phase9_capital_policy_input_v1` |

Manifest hashes:

- `feature_refresh_detail.json`: `8b896c044e7460d31fff06fe029ff352078847a3c39e777132e06e30227e500e`
- `latest_features.json`: `3b5fa2612e6bb50597950b620f727fc1042a7b83ee111f4a30f5c386d75d4a8c`

## 4. Accepted Schema Authority

Registry Accepted Feature Schema:

```text
.runtime/artifacts/features/shared/schema/2026-07-10/sha256-83f34c493f00cd17/feature_schema.json
```

Hash:

```text
83f34c493f00cd17e5bd36b4650dc245673da90dc287704cf423cd03628bc818
```

The accepted schema defines actual Candidate and Opportunity required columns. Both require:

```text
target_date
code
liquidity_avg_volume_20d
missing_flags_insufficient_history
missing_flags_price
missing_flags_volume
price_momentum_return_20d
price_momentum_return_5d
price_momentum_return_60d
trend_close_over_ma_20d
trend_ma_20_60_ratio
trend_ma_5_20_ratio
volatility_return_std_20d
volume_momentum_ratio_1d_20d
volume_momentum_ratio_5d
```

Authority finding:

- Registry materialized index marks `features.shared.accepted_set` as accepted and runtime-use eligible.
- Compatibility evidence for the accepted set is `READY`.
- The older artifact set manifest / lineage evidence still contains `VALIDATED` and `runtime_use_eligible=false` wording. This is an authority caveat, but the materialized index plus compatibility evidence is the current resolver-facing authority.
- Runtime consumer currently hardcodes required columns in `src/ai_fund_lab_v2/runtime_v2/market_refresh/consumer_readiness.py`, but those hardcoded columns align with the accepted schema and current producer output.

## 5. Producer / Consumer Contract

Current formal producer:

```text
src/ai_fund_lab_v2/paper_trading/feature_refresh.py
```

Current producer source hash:

```text
8d0f22f8cde3d4eac76f329e9bb3fc6bdf2f75fe651cee818107d8cac1cb787f
```

Current consumer:

```text
src/ai_fund_lab_v2/runtime_v2/market_refresh/consumer_readiness.py
```

Current consumer source hash:

```text
489720a4c20b2ced2c18832a4fdb0734f68921ea95ce19e8d53dd29e95ec3c5e
```

Finding:

- Current producer covers all current consumer required Candidate columns.
- Current producer covers all current consumer required Opportunity columns.
- Opportunity artifact contract is unprefixed; Runtime maps to model-level `feature__...` once.
- Consumer correction is not the right resolution because accepted schema, current producer, and current consumer are aligned.

## 6. Candidate Schema Comparison

For both 2026-07-06 and 2026-07-07, Candidate artifacts are missing:

```text
missing_flags_insufficient_history
missing_flags_price
missing_flags_volume
price_momentum_return_60d
trend_ma_20_60_ratio
trend_ma_5_20_ratio
volume_momentum_ratio_1d_20d
```

`missing_flags_insufficient_lookback` exists in the old artifact and is an alias candidate for `missing_flags_insufficient_history`, but the artifact is still missing multiple required calculated values. This is not a rename-only issue.

The missing values require formal calculation from PIT OHLCV/listed inputs, especially:

- `price_momentum_return_60d`
- `trend_ma_5_20_ratio`
- `trend_ma_20_60_ratio`
- `volume_momentum_ratio_1d_20d`
- `missing_flags_price`
- `missing_flags_volume`

## 7. Opportunity Schema Comparison

For both 2026-07-06 and 2026-07-07, Opportunity artifacts contain prefixed old columns:

```text
feature__price_momentum_return_5d
feature__price_momentum_return_20d
feature__volume_momentum_ratio_5d
feature__volatility_return_std_20d
feature__trend_close_over_ma_20d
feature__liquidity_avg_volume_20d
```

Current accepted/runtime artifact schema requires unprefixed columns. Prefix normalization would be deterministic only for the overlapping subset. It cannot produce the missing required values:

```text
missing_flags_insufficient_history
missing_flags_price
missing_flags_volume
price_momentum_return_60d
trend_ma_20_60_ratio
trend_ma_5_20_ratio
volume_momentum_ratio_1d_20d
```

Therefore full deterministic migration is not valid.

## 8. 5BD Window Consistency

| Business Date | Contract Status | Selected Feature Date | Carryover | Current Consumer Schema Status |
|---|---|---:|---:|---|
| 2026-07-06 | `REVIEW_REQUIRED` | 2026-07-06 | false | Candidate/Opportunity `REVIEW_REQUIRED` |
| 2026-07-07 | `MISSING` materialized contract | 2026-07-07 | false | Candidate/Opportunity `REVIEW_REQUIRED` |
| 2026-07-08 | `PASS` | 2026-07-07 | true | Selected artifact still `REVIEW_REQUIRED` by current consumer schema |
| 2026-07-09 | `PASS` | 2026-07-08 | true | Selected artifact still `REVIEW_REQUIRED` by current consumer schema |
| 2026-07-10 | `PASS` | 2026-07-10 | false | Candidate/Opportunity `READY` |

Important: 2026-07-08 and 2026-07-09 carryover contracts are `PASS` because carryover artifacts exist within the freshness limit. They still point to old-schema selected artifacts. For Phase17 5BD readiness, schema compatibility must be evaluated on the selected artifacts, not only the contract status.

## 9. Regeneration Feasibility

Formal PIT regeneration is feasible as a plan, but was not executed.

Required source authority:

```text
.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet
```

Hash:

```text
c0f9b435e4a951dca1c97a3712571586b9028ace6747328fd7e6e69cfecc479d
```

Physical source summary:

- Physical max date: `2026-07-10`
- Logical 2026-07-06 as-of row count: `401497`
- Future rows excluded for 2026-07-06 as-of: `16784`
- Symbols with 61 rows until 2026-07-06: `4223`

The regeneration phase must use Phase17 Historical as-of derived input or equivalent per-date logical cutoff evidence. The default `.runtime/data/raw_normalized/...` root is not sufficient by itself because it ends at 2026-06-26.

Listed Issues PIT evidence exists for both target dates:

- 2026-07-06: `.runtime/operations/feature_refresh/2026-07-06/jquants/listed_issues/listed_info_for_feature.parquet`, hash `bddf92ab13b619a88f6cae11fe47d74d27512169dea0fa6ef19729ec7f5a1338`
- 2026-07-07: `.runtime/operations/feature_refresh/2026-07-07/jquants/listed_issues/listed_info_for_feature.parquet`, hash `2f8947fe0515d56a58f1c552001a934a71f5add6428fbbb116b9891fbbdf2530`

Regeneration constraints:

- Must not use 2026-07-08 or later rows when regenerating 2026-07-06 or 2026-07-07 logical artifacts.
- Must not use Paper Ledger, PnL, broker snapshot, selected/bought outputs, cash/portfolio value, backtest result, or test result.
- Must write new artifacts under new paths / instances; overwrite is prohibited.

## 10. Migration Feasibility

Full deterministic migration is not feasible.

Reason:

- Candidate has one alias-only issue, but also lacks calculated features.
- Opportunity has prefix-only overlap, but also lacks calculated features and missing flags.
- Filling required columns with default/null values would be a semantic mutation and is prohibited.

## 11. Registry and Acceptance Impact

If Phase17-O performs PIT regeneration, it must:

- Generate new artifact instances for 2026-07-06 and 2026-07-07.
- Preserve old artifacts as non-runtime-eligible evidence.
- Validate against `runtime_v2_feature_contract_v1`.
- Create formal manifest/hash/schema/lineage evidence.
- Register immutable registry events.
- Update materialized index/checkpoint only after acceptance.
- Ensure Runtime resolver selects the accepted regenerated artifacts.
- Roll back through registry event/checkpoint selection; no partial Candidate-only or Opportunity-only restore.

## 12. AI Integrity

AI integrity remains maintainable.

Finding:

- Feature regeneration is not AI retraining.
- No accepted Candidate/Opportunity model artifact needs retraining if feature semantics remain the accepted semantics.
- Regeneration must remain J-Quants only.
- No silent fallback, future data, test result, broker state, ledger, PnL, or portfolio value may be used.

If feature semantics change, AI compatibility review is required. Phase17-N found no need to change semantics.

## 13. Decision Matrix

| Option | Result | Reason |
|---|---|---|
| A. Formal Acceptance Only | Reject | 2026-07-06/07 artifacts do not satisfy accepted/current schema. |
| B. Deterministic Migration | Reject | Rename/prefix normalization is insufficient; missing feature values require calculation. |
| C. Point-in-time Regeneration | Select | Current producer, accepted schema, and consumer contract align; stale artifacts must be regenerated from PIT inputs. |
| D. Consumer Contract Correction | Reject | Consumer is aligned with accepted schema/current producer. |
| E. Design/Data Gap | Reject | No schema design gap found; PIT source and missing-history policy are available. |

## 14. Acceptance Gates

| Gate | Status |
|---|---|
| `ARTIFACT_PROVENANCE_COMPLETE` | PASS |
| `CANDIDATE_SCHEMA_DIFF_COMPLETE` | PASS |
| `OPPORTUNITY_SCHEMA_DIFF_COMPLETE` | PASS |
| `ACCEPTED_SCHEMA_AUTHORITY_IDENTIFIED` | PASS |
| `PRODUCER_CONTRACT_IDENTIFIED` | PASS |
| `CONSUMER_CONTRACT_IDENTIFIED` | PASS |
| `NO_FUTURE_DATA` | PASS for review; regeneration must prove per-date cutoff |
| `NO_FORBIDDEN_SOURCE` | PASS for review |
| `MIGRATION_FEASIBILITY_DETERMINED` | PASS |
| `REGENERATION_FEASIBILITY_DETERMINED` | PASS |
| `AI_COMPATIBILITY_IMPACT_DETERMINED` | PASS |
| `REGISTRY_IMPACT_DEFINED` | PASS |
| `NO_FEATURE_MUTATION_DURING_PHASE17_N` | PASS |
| `NO_TRADING_STATE_MUTATION` | PASS |

## 15. Final Judgement

```text
PHASE17_N_POINT_IN_TIME_REGENERATION_REQUIRED
```

Recommended Next Prefix:

```text
Phase17-O
```

Recommended Work Name:

```text
Historical 5BD Feature Artifact Point-in-time Regeneration
```
