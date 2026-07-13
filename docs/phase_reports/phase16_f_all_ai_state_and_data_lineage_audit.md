# Phase16-F All AI Model State, Training Range, Input Range, and Runtime Usage Audit

## Scope

- Prefix: `Phase16-F`
- Work name: `All AI Model State, Training Range, Input Range, and Runtime Usage Audit`
- Audit mode: read-only prerequisite audit
- Runtime / AI changes: not executed
- Retraining / inference / backtest / simulation: not executed
- J-Quants API calls: not executed

This audit inspected the current Runtime v2 AI entry points, stored model artifacts, training summaries, feature/data lineage manifests, and historical-data evidence that affect whether Phase16 Historical Runtime Test can start with frozen AI state.

## Final Judgment

`PHASE16_F_AI_MODEL_FREEZE_PREREQUISITES_REQUIRED`

The active Runtime AI state can be identified, but Phase16 Historical Runtime Test should not start yet because the AI freeze prerequisites are not fully satisfied:

- No single Model Freeze Manifest exists for Candidate, Opportunity, and Position Management AI.
- Opportunity Runtime has a model/metrics consistency risk: Runtime default model is Phase5-P, while the producer fallback training metrics path is Phase5-E when no metrics path is supplied.
- Position Management AI has no external model artifact; its frozen state must be represented by code and adapter hashes.
- Candidate long-history derived artifacts exist, but the currently referenced canonical raw/normalized parquet files no longer contain the same long-history range asserted by older manifests.
- 2021 response JSON files exist, but 2021 is not currently consolidated in the canonical normalized parquet inspected during this audit.

## AI Inventory

| Runtime AI / AI-like component | Classification | Runtime use | Audit result |
|---|---:|---|---|
| Candidate AI | AI model | Produces buy candidate decisions from candidate feature artifacts | Confirmed |
| Opportunity AI | AI model | Ranks selected candidates for buy opportunity planning | Confirmed with metrics-path gap |
| Position Management AI | AI-like deterministic policy | Produces hold/add/reduce/exit decisions from Current, opportunity, and feature inputs | Confirmed as code-policy, no pickle model |
| Policy / Safety / Submit Guard | Rule and policy layer | Runtime guards and approval controls | Not classified as AI model |
| Capital Allocation AI historical modules | Legacy / validation modules | Not found on Runtime v2 mainline audited here | Not a Phase16 Runtime AI prerequisite unless reconnected |

## Runtime Loaded Artifact Consistency

| Component | Runtime entry point | Runtime artifact / default | Consistency |
|---|---|---|---|
| Candidate AI | `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py` | `.runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl` | Consistent with Candidate model manifest and training summary |
| Opportunity AI | `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py` | `reports/opportunity_ai/phase5p/models/opportunity_model.pkl` | Model path confirmed; metrics fallback can drift to Phase5-E unless CLI supplies Phase5-P metrics |
| Position Management AI | `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py` | `src/ai_fund_lab_v2/position_management_ai/inference.py` policy code | No model artifact path; freeze must hash code and adapter |

Runtime buy-AI producer resolves Candidate and Opportunity model paths at runtime and loads the pickle artifacts. Runtime Position Management producer calls `run_position_management_inference` and does not expose a model path argument.

## Candidate AI State

| Item | Value |
|---|---|
| Role | Candidate selection score producer |
| Runtime model path | `.runtime/candidate_ai/models/phase4bf_formal_candidate_model.pkl` |
| Model sha256 | `2ea75d14d3fe36828512d8e1fb0ac482798690c6594f22029c4d5b63c7fd6a02` |
| Model manifest | `.runtime/candidate_ai/models/phase4bf_formal_candidate_model_manifest.json` |
| Manifest sha256 | `e64e15efc9da10b7b19039ff3ed2841f122a625cf46d7dbaa7d65385ee27e56c` |
| Model type | `lightgbm.LGBMClassifier` |
| Model phase | `Phase4-BF` |
| Training dataset | `.runtime/candidate_ai/datasets/phase4be_long_history_dataset_2021-06-14_2026-05-15.parquet` |
| Training target period | `2021-06-14` to `2026-05-15` |
| Stored feature period | `2021-06-14` to `2026-06-12` |
| Stored label period | `2021-06-14` to `2026-05-15` |
| Stored data period | `2021-06-14` to `2026-05-15` in joined training dataset |
| Runtime inference input | `.runtime/operations/feature_artifacts/<business-date>/candidate_features.parquet` |
| Existing Runtime feature artifact dates observed in previous Phase16 audit context | `2026-07-06`, `2026-07-07`, `2026-07-08`, `2026-07-10` |
| Feature schema | `candidate_feature_schema_v1`; 13 feature columns |
| Feature lookback evidence | 60-day momentum / moving average style feature set; first trainable target date recorded as `2021-09-09` in long-history normalization summary |
| Retraining status | Runtime mainline does not retrain; stored model was trained once in Phase4-BF |
| Backtest contamination | No evidence in manifests; leakage audits report OK and backtest/trading flags are false |

Candidate feature columns frozen in the model manifest:

```text
feature__liquidity_avg_volume_20d
feature__missing_flags_insufficient_history
feature__missing_flags_price
feature__missing_flags_volume
feature__price_momentum_return_20d
feature__price_momentum_return_5d
feature__price_momentum_return_60d
feature__trend_close_over_ma_20d
feature__trend_ma_20_60_ratio
feature__trend_ma_5_20_ratio
feature__volatility_return_std_20d
feature__volume_momentum_ratio_1d_20d
feature__volume_momentum_ratio_5d
```

Candidate training summary reports:

- dataset rows: `4,970,227`
- feature columns: `13`
- label columns: `8`
- train rows: `3,581,207`
- validation rows: `1,022,775`
- test rows: `366,245`
- random split: `false`
- future column used as feature: `false`
- label column used as feature: `false`
- leakage audit status: `OK`

Candidate dataset manifest reports split counts with a train-row value that does not match the training summary (`3,341,627` vs `3,581,207`). This does not prove leakage, but it is a freeze-manifest prerequisite gap because the canonical accepted training split metadata is not singular.

## Opportunity AI State

| Item | Value |
|---|---|
| Role | Opportunity ranking / buy decision score producer |
| Runtime model path | `reports/opportunity_ai/phase5p/models/opportunity_model.pkl` |
| Model sha256 | `140e350bd9b12bf0c595184587fa2a3bd74236e4bdf1818df481022980dd6acd` |
| Preferred Phase5-P metrics path | `reports/opportunity_ai/phase5p/training/opportunity_training_metrics.json` |
| Preferred metrics sha256 | `8428f2327e77374743f69e2ebc956a97a9d718880ef2acfc26571f94d9fd9511` |
| Runtime fallback metrics path if omitted | `reports/opportunity_ai/phase5e/opportunity_training_metrics.json` |
| Fallback metrics sha256 | `3416d82a904609b1f1dec2112f1990ca537665b25ab73d63120dea353ee41fc4` |
| Training dataset | `reports/opportunity_ai/phase5p/opportunity_dataset_with_market_sector.parquet` |
| Training / stored target period | `2021-09-08` to `2026-05-15` |
| Runtime inference input | Runtime Candidate output and `.runtime/operations/feature_artifacts/<business-date>/opportunity_feature_input.parquet` |
| Feature schema | 32 feature columns in Phase5-P metrics |
| Retraining status | Runtime mainline does not retrain; stored model was trained in Phase5-P package using Phase5-E trainer metadata |
| Backtest contamination | Market-sector audit reports leakage OK, future feature count 0, and trade/backtest/portfolio feature count 0 |

Opportunity Phase5-P training metrics report:

- dataset rows: `56,995`
- train rows: `40,559`
- validation rows: `12,106`
- test rows: `4,330`
- feature columns: `32`
- label columns: `14`
- backtest/broker/paper trading flags: `false`

Known gap:

- The Phase5-P model is the Runtime default, but if `--opportunity-training-metrics-path` is omitted, Runtime producer passes Phase5-E metrics to inference. Because Phase5-E metrics describe a different model path, dataset, and feature-column count, Phase16 freeze should require an explicit Phase5-P metrics path or an implementation fix before historical execution.
- Phase5-P market-sector completion summary records `sector_master_historical_as_of_available=false` and a `2026-06-01` sector snapshot proxy. This is a known point-in-time limitation for historical inference.

## Position Management AI State

| Item | Value |
|---|---|
| Role | Position decision producer: hold / add / reduce / exit |
| Runtime model path | Not applicable; no pickle/model artifact path exists |
| Frozen implementation | `src/ai_fund_lab_v2/position_management_ai/inference.py` |
| Implementation sha256 | `31fb8630fa1edb281a5e7067ec89677f98f564f21a5c2c5f09f938a5795b2c85` |
| Runtime adapter | `src/ai_fund_lab_v2/runtime_v2/position_management/producer.py` |
| Runtime adapter sha256 | `6ffa7da2b91f5fd5cfa76aa4c487e6e6cf5e1293ba929fe374abd61aaadb7d1b` |
| Model version constant | `position_management_policy_phase6a_v1` |
| Feature version constant | `position_management_feature_v1` |
| Training period | Not applicable; deterministic policy, no training artifact |
| Runtime input period | Depends on Current state, opportunity artifact, and position feature artifact for the business date |
| Stored fixture inference period | `2026-06-12` |
| Stored real-data validation period | `2026-04-21` to `2026-05-13` |
| Retraining status | Not applicable; no retraining path in Runtime mainline |
| Backtest contamination | PM feature audit forbids future/backtest/paper-trading/cash/portfolio/order/broker terms as model features; stored audits report OK |

Position Management is an AI-like policy component, but not a trainable model artifact in the inspected Runtime. Historical freeze must therefore include source-code hashes and the runtime adapter hash.

## 2021 Data Location and Data Lineage

### Derived 2021+ artifacts confirmed

| Artifact | Rows | Period | Status |
|---|---:|---|---|
| `.runtime/candidate_ai/features/phase4bc_long_history_features_2021-06-14_2026-06-12.parquet` | `5,066,399` | `2021-06-14` to `2026-06-12` | Present |
| `.runtime/candidate_ai/labels/phase4bd_long_history_labels_2021-06-14_2026-05-15.parquet` | `4,970,227` | `2021-06-14` to `2026-05-15` | Present |
| `.runtime/candidate_ai/datasets/phase4be_long_history_dataset_2021-06-14_2026-05-15.parquet` | `4,970,227` | `2021-06-14` to `2026-05-15` | Present |
| `reports/opportunity_ai/phase5p/opportunity_dataset_with_market_sector.parquet` | `56,995` | `2021-09-08` to `2026-05-15` | Present |

### Raw / normalized source evidence

The long-history manifests point to:

- `.runtime/data/raw/jquants/equities_bars_daily/manifest.json`
- `.runtime/data/raw/jquants/equities_bars_daily/responses/`
- `.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet`

Historical response JSON fragments, including 2021 dates, are present under:

```text
.runtime/data/raw/jquants/equities_bars_daily/responses/
```

However, the currently inspected canonical parquet files do not match the long-history period asserted by the older manifests:

| Current canonical parquet | Inspected period | Rows | Result |
|---|---|---:|---|
| `.runtime/data/raw/jquants/equities_bars_daily/data.parquet` | `2026-06-01` to `2026-06-26` | `88,930` | Does not contain 2021 |
| `.runtime/data/raw_normalized_real_runtime/jquants/equities_bars_daily/data.parquet` | `2026-06-01` only | `4,231` | Does not contain 2021 |

Data lineage result:

`CONFIRMED_WITH_SOURCE_GAP`

The derived AI training datasets and feature tables preserve 2021+ historical rows, and 2021 raw response JSONs are present. But the current canonical raw/normalized parquet files at the manifest-referenced paths appear overwritten or truncated relative to the long-history manifests. Phase16 should not treat 2021 raw/normalized canonical lineage as fully reproducible until this is reconciled or explicitly frozen as a known immutable derived-dataset dependency.

## Runtime Mainline and Acceptance Shortcut Audit

Historical Runtime Test target mainline:

```text
Market -> Feature -> Candidate -> Opportunity -> Policy -> Safety -> Planning -> Pending -> Submit Guard -> Broker -> Execution -> Ledger -> Current -> Runtime State -> Runtime Report
```

Runtime v2 AI connection evidence:

- Candidate and Opportunity AI are connected through Runtime buy-AI producer and use feature artifacts under `.runtime/operations/feature_artifacts/<business-date>/`.
- Position Management Runtime producer reads Runtime Current state and Runtime artifacts, then emits Runtime state artifacts.
- Acceptance fixtures and dry-run scripts exist in the repository for earlier phases, but the inspected Runtime mainline entry points are separate from those fixture scripts.

Mainline result:

`READY_WITH_FREEZE_GAPS`

The mainline can route through AI producers without using acceptance fixtures, but Phase16 execution should wait until freeze manifest and model/metrics consistency gaps are closed.

## Look-Ahead and Backtest Contamination

| Component | Evidence | Result |
|---|---|---|
| Candidate AI | Model/training manifests separate feature and label columns; leakage status OK; future/label features false; backtest/trading false | No contamination evidence found |
| Opportunity AI | Phase5-P market-sector audit reports leakage OK, future feature count 0, trade/backtest/portfolio feature count 0 | No contamination evidence found; sector snapshot proxy remains a historical point-in-time gap |
| Position Management AI | Feature audit rejects future/backtest/paper-trading/cash/portfolio/order/broker terms; stored audits OK | No contamination evidence found for stored policy inputs |

Backtest contamination result:

`NO_EVIDENCE_FOUND_WITH_KNOWN_LINEAGE_GAPS`

## Retraining and Scheduler Status

Runtime v2 mainline inspection found no evidence that Candidate, Opportunity, or Position Management retraining is invoked as part of daily Runtime operation. The repository contains training and validation scripts from earlier phases, but they are not the Runtime mainline.

The architecture documents also keep `launchd` / autonomous operation outside the currently approved Runtime scope. This audit did not inspect user-level OS scheduler state outside the repository; external LaunchAgent/crontab status remains `UNKNOWN`.

## Model Freeze Readiness

| Freeze item | Status | Evidence / gap |
|---|---|---|
| Candidate model path and hash | READY | Runtime default and hash confirmed |
| Candidate training period | IMPLEMENTATION_REQUIRED | Period can be reconstructed, but split metadata has conflicting train row counts |
| Candidate feature schema | READY | 13 model feature columns confirmed |
| Opportunity model path and hash | READY | Runtime default and hash confirmed |
| Opportunity metrics path | IMPLEMENTATION_REQUIRED | Runtime fallback can point to Phase5-E metrics |
| Opportunity feature schema | READY_WITH_GAP | 32 Phase5-P features confirmed; sector snapshot proxy is a historical gap |
| Position Management model identity | IMPLEMENTATION_REQUIRED | No model artifact; freeze manifest must hash implementation and adapter |
| 2021 raw/normalized data source | IMPLEMENTATION_REQUIRED | Derived datasets present; canonical parquet source range inconsistent |
| Runtime loaded artifact consistency | IMPLEMENTATION_REQUIRED | Opportunity metrics-path gap blocks full consistency |
| Backtest contamination | READY_WITH_GAP | No contamination evidence found; lineage gaps remain |
| External scheduler retraining prevention | UNKNOWN | Repository mainline clean; OS scheduler not audited |

Model Freeze readiness:

`NOT_READY`

## Unknowns

- Accepted production status of the Candidate model is not singularly recorded; Candidate model manifest has `production_model_promoted=false` while Runtime uses the model path.
- Candidate training split date boundaries are not recorded in a single accepted freeze artifact.
- Candidate dataset manifest and training summary disagree on train-row count.
- Opportunity Runtime metrics path can drift unless explicitly set.
- Opportunity Phase5-P market-sector features use a 2026 snapshot proxy for historical rows.
- Position Management AI lacks a model artifact; no freeze format exists for code-policy hashes.
- Current canonical raw/normalized J-Quants parquet files do not contain the 2021+ range referenced by long-history manifests.
- External OS scheduler / LaunchAgent / crontab state was not audited.

## Required Prerequisites Before Phase16 Historical Runtime Test

1. Create a Model Freeze Manifest that records Candidate, Opportunity, and Position Management AI identities, hashes, feature schemas, training/data periods, and accepted runtime paths.
2. Fix or require explicit Opportunity Phase5-P training metrics path for Runtime historical execution.
3. Decide and record the accepted Candidate model status despite `production_model_promoted=false`.
4. Reconcile 2021 raw/normalized canonical data lineage, or freeze the existing derived datasets as the accepted immutable historical AI input lineage with clear non-rebuildability caveat.
5. Represent Position Management AI freeze as source-code hash plus runtime-adapter hash.
6. Record scheduler/retraining prohibition evidence for the actual execution environment before running Phase16.

## Classification

| Target | Classification |
|---|---|
| Candidate AI state | READY_WITH_GAPS |
| Candidate training range | IMPLEMENTATION_REQUIRED |
| Candidate input data range | IMPLEMENTATION_REQUIRED |
| Candidate runtime usage | READY |
| Opportunity AI state | READY_WITH_GAPS |
| Opportunity training range | READY_WITH_GAPS |
| Opportunity input data range | READY_WITH_GAPS |
| Opportunity runtime usage | IMPLEMENTATION_REQUIRED |
| Position Management AI state | READY_WITH_GAPS |
| Position Management training range | NOT_APPLICABLE |
| Position Management input data range | UNKNOWN |
| Position Management runtime usage | READY_WITH_GAPS |
| Runtime loaded artifact consistency | IMPLEMENTATION_REQUIRED |
| 2021 data location | READY_WITH_GAPS |
| Data lineage | IMPLEMENTATION_REQUIRED |
| Backtest contamination | READY_WITH_GAPS |
| Model Freeze readiness | IMPLEMENTATION_REQUIRED |
| Replay readiness | IMPLEMENTATION_REQUIRED |

## Next Prefix

`Phase16-G`

Recommended next work: implement only the missing prerequisites for AI Model Freeze and data-lineage consistency. Do not start Reset, Historical Runtime Test, simulation, retraining, model switching, or replay until the freeze audit passes.

