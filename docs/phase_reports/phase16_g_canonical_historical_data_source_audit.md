# Phase16-G Canonical Historical Data Source of Truth Audit

## Scope

- Prefix: `Phase16-G`
- Work name: `Canonical Historical Data Source of Truth Audit`
- Audit mode: read-only
- Data regeneration: not executed
- Feature regeneration: not executed
- J-Quants API fetch: not executed
- Runtime / AI changes: not executed
- Historical Simulation / Reset: not executed

This audit separates three concepts:

- `Canonical Data`: formally configured or code-defined J-Quants-derived data sources.
- `Runtime Data`: the data paths that Runtime v2 currently reads during normal operation.
- `Historical Runtime Simulation Data`: the data set required to replay historical dates without using Phase4/5/6 training artifacts as Source of Truth.

## Final Judgment

`PHASE_ARTIFACT_DEPENDENCY_FOUND`

Canonical J-Quants historical OHLCV exists for 2021 onward, but Runtime v2 Historical Simulation cannot yet be composed entirely from canonical data through the current Runtime mainline. The current Runtime v2 market refresh path reads `.runtime/operations/jquants/...`, which is recent operational data only. If Phase16 were started without additional canonical historical source wiring, it would be forced toward Phase4/5/6 artifacts such as `phase4be_long_history_dataset` or `phase5p` datasets, which is explicitly forbidden.

## Executive Summary

| Area | Formal / actual path | Period | Status |
|---|---|---:|---|
| Formal raw daily quotes | `.runtime/data/raw/jquants/equities_bars_daily/responses/` | `2021-06-14` to `2026-06-12` | Confirmed |
| Formal normalized daily quotes | `.runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet` | `2021-06-14` to `2026-06-26` | Confirmed |
| Runtime v2 operational raw daily quotes | `.runtime/operations/jquants/raw/jquants/equities_bars_daily/data.parquet` | `2026-02-16` to `2026-07-10` | Runtime current path, not full historical |
| Runtime v2 operational normalized daily quotes | `.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet` | `2026-02-16` to `2026-07-10` | Runtime current path, not full historical |
| Formal trading calendar config | `.runtime/data/raw/jquants/trading_calendar/data.parquet` | `2026-03-02` to `2026-06-28` | Not historical enough |
| Runtime v2 trading calendar | `.runtime/operations/jquants/raw/jquants/trading_calendar/data.parquet` | `2026-02-16` to `2026-07-10` | Not historical enough |
| Formal listed issues config | `.runtime/data/raw/jquants/listed_issues/data.parquet` | `2026-06-01` to `2026-06-26` | Not historical enough |
| Runtime v2 listed issues | `.runtime/operations/jquants/raw/jquants/listed_issues/data.parquet` | `2026-07-06` to `2026-07-10` | Not historical enough |
| Corporate actions | daily quotes adjusted OHLCV / `AdjFactor`; no standalone store | OHLCV period only | Partial |
| Runtime feature artifacts | `.runtime/operations/feature_artifacts/<date>/` | observed `2026-07-06`, `2026-07-07`, `2026-07-08`, `2026-07-10` | Runtime accepted input, not historical canonical |

## A. Formal Raw Data

### Confirmed formal raw daily quotes

| Item | Evidence |
|---|---|
| Storage | `.runtime/data/raw/jquants/equities_bars_daily/responses/` |
| Config key | `config/phase9_data_sources.yaml`: `raw_daily_quotes` |
| Producer | `scripts/run_phase9j3_rebuild_canonical_normalized_daily_quotes.py` consumes this raw response root; historical fetch scripts also wrote this location |
| Consumer | Phase9 canonical normalized rebuild script |
| Period | response JSON file names cover `2021-06-14` to `2026-06-12` |
| File count | `1,305` response JSON files |
| 2021 count | `145` response JSON files, `2021-06-14` to `2021-12-31` |
| Manifest | `.runtime/data/raw/jquants/equities_bars_daily/manifest.json` reports endpoint `/v2/equities/bars/daily`, raw output path, and 1,305 completed requests |

### Supplemental raw table

| Item | Evidence |
|---|---|
| Path | `.runtime/data/raw/jquants/equities_bars_daily/data.parquet` |
| Hash | `d6f39cd96710eb34bb7cde8b7e22e57e08a0a42ed9cf3e0b1fa693b4697f439f` |
| Period | `2026-06-01` to `2026-06-26` |
| Rows | `88,930` |
| Classification | Canonical supplemental recent raw table, not the full historical raw source |

### Runtime v2 operational raw

| Item | Evidence |
|---|---|
| Path | `.runtime/operations/jquants/raw/jquants/equities_bars_daily/data.parquet` |
| Hash | `b9f67ae5e67d0764d011e6530ef88842d9b891f964a49325960535f4b103f6bd` |
| Period | `2026-02-16` to `2026-07-10` |
| Rows | `440,085` |
| Producer | `src/ai_fund_lab_v2/operations/market_refresh.py` calls `run_market_data_refresh` with `raw_output_root = <operations_root>/jquants/raw` |
| Consumer | Runtime v2 market diagnostics and feature refresh path |
| Classification | Runtime Data, not full Historical Simulation canonical source |

## B. Formal Normalized Data

### Confirmed canonical normalized daily quotes

| Item | Evidence |
|---|---|
| Path | `.runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet` |
| Config key | `config/phase9_data_sources.yaml`: `normalized_daily_quotes` |
| Hash | `4d02647fc11d5a2855f9993203fe2cb9b32d553cd1192dfc5c03690bdb40201f` |
| Period | `2021-06-14` to `2026-06-26` |
| Rows | `5,108,552` |
| Unique target dates | `1,232` |
| Unique codes | `4,991` |
| Producer | `scripts/run_phase9j3_rebuild_canonical_normalized_daily_quotes.py` |
| Consumer | Phase9 feature refresh, Phase9 daily reports, training dataset safety scripts, legacy paper trading runner |
| Manifest | `.runtime/phase9/canonical_data/normalized_daily_quotes/normalize_manifest.json` |
| Manifest status | `CANONICAL_NORMALIZED_READY` |
| Manifest source | raw responses plus supplemental raw table |

This is the only inspected normalized OHLCV artifact that is both explicitly configured as canonical and contains 2021+ data.

### Runtime v2 operational normalized daily quotes

| Item | Evidence |
|---|---|
| Path | `.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet` |
| Hash | `c0f9b435e4a951dca1c97a3712571586b9028ace6747328fd7e6e69cfecc479d` |
| Period | `2026-02-16` to `2026-07-10` |
| Rows | `418,281` |
| Producer | `src/ai_fund_lab_v2/operations/market_refresh.py` via `run_market_data_refresh` |
| Consumer | Runtime v2 `run_feature_refresh` through `daily_quotes_path=<operations_root>/jquants/raw_normalized/.../data.parquet` |
| Classification | Runtime Data, not sufficient for 2021 Historical Simulation |

## C. Trading Calendar

| Candidate | Path | Period | Producer / Consumer | Classification |
|---|---|---:|---|---|
| Formal config calendar | `.runtime/data/raw/jquants/trading_calendar/data.parquet` | `2026-03-02` to `2026-06-28` | Configured in `phase9_data_sources`; used by calendar/readiness helpers | Canonical config, insufficient historical range |
| Runtime v2 operational calendar | `.runtime/operations/jquants/raw/jquants/trading_calendar/data.parquet` | `2026-02-16` to `2026-07-10` | Runtime market refresh output | Runtime Data, insufficient historical range |

Calendar Source priority in `runtime_temporal_freshness_contract.md` is J-Quants calendar, JPX calendar, repository canonical calendar, then fallback weekday calendar. The inspected persisted J-Quants calendar does not cover 2021.

## D. Listed Issues

| Candidate | Path | Period | Producer / Consumer | Classification |
|---|---|---:|---|---|
| Formal config listed data | `.runtime/data/raw/jquants/listed_issues/data.parquet` | `2026-06-01` to `2026-06-26` | Configured in `phase9_data_sources`; consumed by feature refresh/universe gate | Canonical config, insufficient historical range |
| Runtime v2 operational listed data | `.runtime/operations/jquants/raw/jquants/listed_issues/data.parquet` | `2026-07-06` to `2026-07-10` | Runtime market refresh output; copied to `feature_refresh/<date>/jquants/listed_issues/listed_info_for_feature.parquet` | Runtime Data, insufficient historical range |

Runtime feature generation uses the latest listed snapshot at or before `target_data_until`. Because persisted listed issue data is recent only, 2021 universe membership and delisting status cannot be reconstructed from canonical listed data alone.

## E. Corporate Action

| Item | Evidence | Result |
|---|---|---|
| Stock split / reverse split adjustment | Raw daily quotes include `AdjFactor`, `AdjO`, `AdjH`, `AdjL`, `AdjC`, `AdjVo`; normalized OHLCV uses adjusted fields when available | Partial canonical source in OHLCV |
| Standalone corporate action table | No dedicated persisted `corporate_action`, `stock_split`, `reverse_split`, or `delisting` canonical store found | Missing |
| Delisting | Listed issue master and candidate universe gate can represent current listed status, but historical listed data is not available for 2021 | Missing for historical replay |
| Adjustment consumer | `data_quality.normalization.normalize_daily_quotes` and related tests prefer adjusted fields | Confirmed |

Corporate Action status:

`PARTIAL`

Historical Simulation can use adjusted OHLCV values where daily quotes provide them, but split/reverse split/delisting event auditability is not complete without a standalone or historical listed/corporate action source.

## F. Runtime Feature Source

Runtime v2 market refresh calls:

```text
run_runtime_v2_market_refresh_pipeline
  -> run_operations_market_refresh
  -> run_market_data_refresh(raw_output_root=<operations>/jquants/raw,
                             normalized_output_root=<operations>/jquants/raw_normalized)
  -> run_feature_refresh(daily_quotes_path=<operations>/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet,
                         listed_info_path=<operations>/feature_refresh/<business_date>/jquants/listed_issues/listed_info_for_feature.parquet,
                         feature_output_root=<operations>/feature_artifacts)
```

Runtime feature output paths:

```text
.runtime/operations/feature_artifacts/<feature-date>/candidate_features.parquet
.runtime/operations/feature_artifacts/<feature-date>/opportunity_feature_input.parquet
.runtime/operations/feature_artifacts/<feature-date>/position_feature_input.parquet
.runtime/operations/feature_artifacts/<feature-date>/capital_policy_input.parquet
```

Therefore Runtime Feature Source currently uses Runtime operational normalized data, not the Phase9 canonical historical normalized path.

## G. Runtime AI Input

| AI | Runtime input path | Producer | Classification |
|---|---|---|---|
| Candidate AI | `.runtime/operations/feature_artifacts/<feature-date>/candidate_features.parquet` | Runtime v2 feature refresh | Accepted Runtime Input |
| Opportunity AI | Candidate runtime artifact plus `.runtime/operations/feature_artifacts/<feature-date>/opportunity_feature_input.parquet` | Runtime buy-AI producer and feature refresh | Accepted Runtime Input |
| Position Management AI | Runtime Current plus `.runtime/operations/feature_artifacts/<feature-date>/position_feature_input.parquet` and Opportunity artifact | Runtime Current / feature refresh / buy-AI producer | Accepted Runtime Input |

AI input status for Historical Simulation:

`NOT_READY_FROM_CANONICAL_ONLY`

Runtime AI can read accepted Runtime feature artifacts, but 2021 Runtime feature artifacts do not exist and must not be substituted with Phase4/5/6 training artifacts.

## Phase Artifact Classification

| Artifact family | Representative path | Classification | Source of Truth decision |
|---|---|---|---|
| Phase4 long-history raw/fetch reports | `reports/candidate_ai/full_range/phase4*_summary.json` | Historical Report / Evidence | Not Canonical Source |
| Phase4 long-history feature table | `.runtime/candidate_ai/features/phase4bc_long_history_features_2021-06-14_2026-06-12.parquet` | Training Artifact | Not Accepted Runtime Input |
| Phase4 long-history labels | `.runtime/candidate_ai/labels/phase4bd_long_history_labels_2021-06-14_2026-05-15.parquet` | Training Artifact | Not Accepted Runtime Input |
| Phase4-BE long-history dataset | `.runtime/candidate_ai/datasets/phase4be_long_history_dataset_2021-06-14_2026-05-15.parquet` | Training Artifact | Not Canonical Source |
| Phase4-BF Candidate model | `.runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl` | Accepted Runtime Model, not data source | Model freeze input only |
| Phase5-D/I/P opportunity datasets | `reports/opportunity_ai/phase5*/**/opportunity_dataset*.parquet` | Training Artifact / Historical Report | Not Canonical Source |
| Phase5-P Opportunity model | `reports/opportunity_ai/phase5p/models/opportunity_model.pkl` | Accepted Runtime Model, not data source | Model freeze input only |
| Phase6 PM reports and fixtures | `reports/position_management_ai/phase6*` | Training/validation fixture or report | Not Canonical Source |
| Runtime feature artifacts | `.runtime/operations/feature_artifacts/<date>/*.parquet` | Accepted Runtime Input | Accepted for that runtime date only, not Canonical Source |
| Phase9 canonical normalized | `.runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet` | Canonical Source by config and manifest | Canonical normalized OHLCV, despite phase-numbered directory |

### phase4be_long_history_dataset decision

`phase4be_long_history_dataset` is a training dataset, not a formal Historical Runtime input.

Evidence:

- Path lives under `.runtime/candidate_ai/datasets/`.
- Producer is `scripts/build_phase4be_long_history_dataset.py`.
- It joins Phase4 feature and label tables and contains train/validation/test split metadata.
- Candidate model training summary references it as a training dataset.
- Runtime v2 buy-AI producer does not read this dataset; it reads `candidate_features.parquet` from Runtime feature artifacts.

It must not be promoted to Source of Truth for Phase16 Historical Runtime Simulation.

## Runtime Source of Truth Chain

### Current Runtime v2 operational chain

```text
J-Quants API or existing operational files
  -> .runtime/operations/jquants/raw/jquants/*
  -> .runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet
  -> .runtime/operations/feature_artifacts/<feature-date>/*.parquet
  -> Candidate / Opportunity / PM Runtime producers
  -> .runtime/runtime_state/*
```

This chain is valid for recent Runtime operation but does not contain a 2021 historical range.

### Canonical historical chain found in repository

```text
.runtime/data/raw/jquants/equities_bars_daily/responses/
  -> scripts/run_phase9j3_rebuild_canonical_normalized_daily_quotes.py
  -> .runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet
```

This chain confirms 2021+ OHLCV canonical normalized data, but Runtime v2 Historical Simulation does not yet read it as its feature source.

### Required Phase16 historical chain

```text
Canonical Raw
  -> Canonical Normalized
  -> Historical Runtime Feature Artifacts
  -> Candidate / Opportunity / PM Runtime AI Input
  -> Runtime State
```

The chain is not fully wired today because the Runtime feature producer reads operational normalized data and recent listed/calendar sources.

## 2021 Data Evidence

| Check | Result |
|---|---|
| 2021 raw exists | Yes, response JSON files exist |
| 2021 raw location | `.runtime/data/raw/jquants/equities_bars_daily/responses/` |
| 2021 raw file count | `145` response JSON files |
| 2021 raw period | `2021-06-14` to `2021-12-31` |
| 2021 canonical normalized exists | Yes |
| 2021 canonical normalized location | `.runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet` |
| 2021 canonical normalized period | starts `2021-06-14` |
| Current Runtime v2 operational normalized contains 2021 | No |
| Current canonical listed contains 2021 | No |
| Current canonical trading calendar contains 2021 | No |
| Standalone corporate action 2021 source | Not found |

Reconstruction audit:

- `2021 Raw -> Normalized`: likely reproducible from response JSONs through the existing canonical rebuild script; not executed.
- `Normalized -> Feature`: possible in code for OHLCV-derived features, but current Runtime v2 path is not wired to the Phase9 canonical historical normalized file and listed/calendar historical prerequisites are missing.
- `Feature -> AI`: Runtime AI can consume Runtime feature artifacts, but 2021 Runtime feature artifacts do not exist and Phase4/5/6 training artifacts must not be substituted.

## Historical Runtime Simulation Input Readiness

| Required input | Canonical-only readiness | Gap |
|---|---|---|
| OHLCV | Ready with path gap | 2021+ canonical normalized exists, but Runtime v2 feature source does not read it by default |
| Trading Calendar | Not ready | Persisted calendar is recent only |
| Listed Issues | Not ready | Persisted listed issue master is recent only |
| Corporate Action | Partial | Adjusted OHLCV exists; standalone event source missing |
| Candidate Feature | Not ready | 2021 Runtime feature artifacts not present |
| Opportunity Feature | Not ready | 2021 Runtime feature artifacts not present |
| PM Feature | Not ready | Depends on historical Current plus feature artifacts |
| AI Input | Not ready | Runtime AI inputs must be generated from canonical feature artifacts, not Phase training datasets |

## Missing Data / Canonicalization Required

1. Define a Phase16 Historical Runtime canonical source contract that points Runtime feature generation to canonical historical normalized OHLCV without using Phase4/5/6 artifacts.
2. Provide or reconstruct canonical historical Trading Calendar for the simulation window.
3. Provide or reconstruct canonical historical Listed Issues snapshots for point-in-time universe and delisting handling.
4. Decide corporate action Source of Truth: adjusted OHLCV only, or a standalone split/reverse-split/delisting event table.
5. Generate Historical Runtime Feature Artifacts from canonical data only, with feature-date scoped manifests and hashes.
6. Prohibit `phase4be_long_history_dataset`, Phase5 datasets, and Phase6 fixtures as Simulation Source of Truth.

## Classification

| Target | Classification |
|---|---|
| Formal Raw Data | `CANONICAL_SOURCE_CONFIRMED` |
| Formal Normalized Data | `CANONICAL_SOURCE_CONFIRMED` |
| Runtime v2 operational data | `CANONICAL_SOURCE_CONFIRMED_WITH_GAPS` |
| Trading Calendar | `CANONICAL_SOURCE_REVIEW_REQUIRED` |
| Listed Issues | `CANONICAL_SOURCE_REVIEW_REQUIRED` |
| Corporate Action | `CANONICAL_SOURCE_REVIEW_REQUIRED` |
| Runtime Feature Source | `PHASE_ARTIFACT_DEPENDENCY_FOUND` |
| Runtime AI Input | `PHASE_ARTIFACT_DEPENDENCY_FOUND` |
| 2021 Raw existence | `CANONICAL_SOURCE_CONFIRMED` |
| 2021 Canonical normalized existence | `CANONICAL_SOURCE_CONFIRMED` |
| Historical Simulation canonical-only readiness | `PHASE_ARTIFACT_DEPENDENCY_FOUND` |

## Next Prefix

`Phase16-H`

Recommended next work: implement or define the minimal canonical Historical Runtime Data Source contract and missing historical calendar/listed/corporate-action prerequisites. Do not regenerate data, run Historical Simulation, Reset, or use Phase4/5/6 artifacts as Source of Truth until this passes.

