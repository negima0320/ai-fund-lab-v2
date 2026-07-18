# Phase18-A — Common PIT Dataset Rebuild Pipeline Existing Implementation Audit and Plan

## Executive Summary

Phase18-A audit scope was limited to design understanding, existing implementation inventory, dataset contract audit, gap analysis, and implementation planning. No dataset rebuild, training, model switch, Registry acceptance, Runtime BUY re-enable, broker write, order submit, or code implementation was performed as part of this audit.

Important working-tree note: previously added unapproved scratch files under `src/ai_fund_lab_v2/ai_lifecycle/` and `tests/ai_lifecycle/` were excluded from this existing-implementation audit. They are not treated as repository baseline evidence.

Primary judgment:

```text
PHASE18_A_COMMON_PIPELINE_IMPLEMENTATION_REQUIRED
```

Secondary judgments:

```text
PHASE18_A_EXISTING_PIPELINE_ADAPTER_REQUIRED
PHASE18_A_REVIEW_REQUIRED
```

Reason: Candidate and Opportunity have useful Phase4/Phase5/Phase9 building blocks, but no common AI Lifecycle v2 PIT dataset bundle pipeline currently emits the SoT-required `dataset.parquet`, metadata, schemas, lineage, quality, date coverage, drop reasons, and hash manifest with component-specific label-safe cutoff, source authority, idempotency, failure artifacts, and atomic publication.

## Documents Reviewed

- `docs/phase_reports/phase17_final_summary_and_phase18_handoff.md`
- `docs/01_requirements/phase_roadmap.md`
- `docs/02_architecture/ai_lifecycle_v2.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/phase_reports/phase17_bv14_market_status_buy_eligibility_guard.md`
- `docs/phase_reports/phase17_bv15_opportunity_buy_eligibility_contract_fix.md`
- `docs/phase_reports/phase17_bv16_opportunity_expected_edge_semantics_and_runtime_distribution_investigation.md`
- `docs/phase_reports/phase17_bv17_opportunity_formal_model_revalidation_and_calibration_root_cause_investigation.md`
- `docs/phase_reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness.md`
- `docs/phase_reports/phase17_bv19_ai_training_lifecycle_and_retraining_pipeline_audit.md`
- `docs/phase_reports/phase17_bv20_ai_lifecycle_v2_architecture_and_runtime_responsibility_design_contract.md`
- `docs/phase_reports/phase17_bv20_r1_ai_lifecycle_v2_objective_alignment_review_and_design_amendment.md`
- `docs/03_ai_design/candidate_training_data_design.md`
- `docs/03_ai_design/opportunity_ai_design.md`
- `docs/phase_reports/phase16_final_summary_and_phase17_handoff.md`
- `docs/phase_reports/phase16_k_ai_artifact_registry_and_capital_allocation_design.md`

## SoT Requirements

`docs/02_architecture/ai_lifecycle_v2.md` requires trainable dataset builders to emit:

```text
dataset.parquet
dataset_metadata.json
feature_schema.json
target_schema.json
lineage.json
data_quality.json
date_coverage.json
drop_reasons.csv
hash_manifest.json
```

Required metadata includes input artifacts, source authority, PIT business date, label-safe cutoff, schema versions, row uniqueness keys, missing/drop policy, content/schema hashes, lineage refs/hashes, builder version, and output location.

Row uniqueness required by the SoT:

```text
Candidate: target_date + code
Opportunity: target_date + code + candidate_source_ref
```

BV21 acceptance scope:

```text
Candidate and Opportunity PIT datasets
Input: canonical data, feature artifacts, label-safe cutoff
Output: dataset bundle with metadata, schemas, lineage, quality, hashes
Acceptance: no leakage, PIT date correctness, row uniqueness, coverage PASS
Forbidden: training, promotion, Runtime switch
```

## Existing Implementation Inventory

| Area | Path / Function | Component | Input | Output | Date Contract | Target Horizon | Source Authority | Current Caller / Tests | Status | Classification |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Candidate long-history feature builder | `scripts/build_phase4bc_long_history_features.py::build_phase4bc_long_history_features` | Candidate | long-history normalized quotes from `.runtime/data/raw_normalized_real_runtime/...` plus Phase4-BB summary | feature parquet/jsonl, manifest, audit, summary | `target_date=as_of_date`, past rows only, minimum 60-row lookback | none directly | `daily_quotes_normalized_real_runtime_long_history` | `tests/test_phase4bc_long_history_feature_regeneration.py` | Works for Phase4 feature generation, not common lifecycle bundle | REUSE_WITH_ADAPTER |
| Candidate long-history label builder | `scripts/build_phase4bd_long_history_labels.py::build_phase4bd_long_history_labels` | Candidate | normalized quotes plus Phase4-BC feature reference | label parquet/jsonl, manifest, audit, summary | excludes tail without 20bd horizon | 20bd | J-Quants normalized quotes | `tests/test_phase4bd_long_history_label_regeneration.py` | Useful label-safe behavior, no shared cutoff resolver | REUSE_WITH_ADAPTER |
| Candidate dataset builder | `scripts/build_phase4be_long_history_dataset.py::build_phase4be_long_history_dataset` / `build_long_history_dataset_frame` | Candidate | Phase4-BC features + Phase4-BD labels | dataset parquet/jsonl, manifest, audit, summary | inner join on `target_date, code`; fixed split cutoffs | 20bd labels from Phase4-BD | Phase4-BC/BD derived artifacts | `tests/test_phase4be_long_history_dataset_rebuild.py` | Best Candidate dataset base, but lacks SoT bundle files and latest label-safe orchestration | MERGE_INTO_COMMON_PIPELINE |
| Candidate formal training | `scripts/train_phase4bf_formal_candidate_model.py::train_phase4bf_formal_candidate_model` | Candidate | Phase4-BE dataset summary/path | model pkl, manifest, metrics summary | consumes dataset split | 20bd candidate label | Phase4-BE dataset | `tests/test_phase4bf_formal_lightgbm_training.py` | Out of Phase18-A except contract compatibility | NOT_RELEVANT for Phase18-A implementation, useful downstream |
| Opportunity dataset builder | `src/ai_fund_lab_v2/opportunity_ai/dataset_builder.py::build_opportunity_dataset_frame` | Opportunity | candidate rows, opportunity features, labels | dataset dataframe/parquet, summary, audit | drops dupes on `target_date, code`; split by fixed cutoffs | 20bd expected edge | supplied candidate/feature/label inputs | `tests/opportunity_ai/test_phase5d_opportunity_dataset_builder.py` | Strong reusable join/leakage core, but lacks candidate_source_ref uniqueness and lifecycle bundle outputs | MERGE_INTO_COMMON_PIPELINE |
| Opportunity market/sector completion | `src/ai_fund_lab_v2/opportunity_ai/market_sector_completion.py::run_market_sector_feature_completion` | Opportunity | Phase5-I dataset, Phase4-BC source features, listed issues, inference artifacts | Phase5P 32-feature dataset, model/training/quality/comparison outputs | extends existing target dates; does not extend label-safe dates | 20bd | Phase5-I + listed issues | Phase5P reports; no Phase18 common tests | Produces formal 32-feature dataset but mixes training/evaluation with dataset completion | REUSE_WITH_ADAPTER for feature attach, split responsibilities |
| Opportunity training runner | `src/ai_fund_lab_v2/opportunity_ai/training.py::train_opportunity_model` | Opportunity | dataset parquet | model, metrics, audit | consumes dataset split | target `label__expected_edge_label_20d` | supplied dataset | `tests/opportunity_ai/test_phase5e_opportunity_training.py` | Phase18-B component, not dataset rebuild | NOT_RELEVANT for Phase18-A implementation |
| Phase9 training dataset candidate generator | `src/ai_fund_lab_v2/paper_trading/training_dataset_candidate.py::build_training_dataset_candidates` | Candidate + Opportunity candidate datasets | Phase9 canonical normalized quotes, listed info, trading calendar, cutoff args | candidate/opportunity dataset candidates + manifest/audit | explicit `data_until`, `safe_train_until`, `train_until`, label horizon | 20bd | `J-Quants canonical Phase9 data only` | `tests/paper_trading/test_phase9l1_training_dataset_candidate.py` | Useful cutoff/source/audit ideas, but schema differs from accepted Candidate/Opportunity formal contracts | REUSE_WITH_ADAPTER |
| Phase9 training dataset audit | `src/ai_fund_lab_v2/paper_trading/training_dataset_audit.py::audit_training_dataset` | Generic trainable dataset audit | dataset path and source refs | audit dataclass | blocks train_until after safe_train_until and future rows | parameterized | source refs must be J-Quants/canonical | `tests/paper_trading/test_phase9l1_training_dataset_audit.py` | Reusable as common source/future-leakage audit seed | REUSE_WITH_ADAPTER |
| Runtime BUY AI artifact resolver | `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py::resolve_buy_ai_artifact_paths` | Runtime | Registry accepted sets | model/metrics/schema paths | job start authority, no training cutoff gate | n/a | Registry | `tests/runtime_v2/test_phase16av_registry_consumer_cutover.py` | Runtime selection is solid; not dataset pipeline | REUSE_AS_IS |
| Registry resolver | `src/ai_fund_lab_v2/artifact_registry/resolver.py::RegistryArtifactResolver.resolve` | Registry | event log/index/checkpoint | accepted artifact set members | accepted state authority | n/a | Registry event log/index/checkpoint | Runtime cutover tests | Solid accepted-artifact lookup, not lifecycle generation | REUSE_AS_IS |
| BV14 market status guard | `src/ai_fund_lab_v2/runtime_v2/market_status/buy_eligibility.py` | Runtime BUY eligibility | PIT listed issues / embedded authority | eligibility evidence | point-in-time, no future delisting inference | n/a | listed issues authority | `tests/runtime_v2/test_phase17_bv14_market_status_buy_eligibility_guard.py` | Relevant for later compatibility evidence, not dataset rebuild | REUSE_AS_IS downstream |
| BV15 Opportunity BUY eligibility | `src/ai_fund_lab_v2/runtime_v2/buy_ai/opportunity_eligibility.py` | Runtime BUY eligibility | Opportunity ranking artifact | BUY eligible / no-buy evidence | artifact date/hash match | 20bd expected edge semantics | Opportunity artifact | `tests/runtime_v2/test_phase17_bv15_opportunity_buy_eligibility_contract.py` | Relevant for later compatibility evidence, not dataset rebuild | REUSE_AS_IS downstream |

## Existing Artifact Evidence

Measured read-only on 2026-07-17:

| Artifact | Rows | Feature Columns | Label Columns | Date Range | Code Count | SHA256 |
| --- | ---: | ---: | ---: | --- | ---: | --- |
| `.runtime/candidate_ai/datasets/phase4be_long_history_dataset_2021-06-14_2026-05-15.parquet` | 4,970,227 | 13 | 8 | 2021-06-14..2026-05-15 | 4,780 | `17dc5324bdd4bebeb0a3e54a80a03d04759280cb615428ff15636b73c029c03f` |
| `reports/opportunity_ai/phase5p/opportunity_dataset_with_market_sector.parquet` | 56,995 | 32 | 14 | 2021-09-08..2026-05-15 | 2,323 | `f6111be4b81df27270b58d60a89f43808f27bdbbd3afff3bf4524c2537ece539` |
| `.runtime/phase9/training_dataset_candidates/2026-05-18/candidate_ai_dataset.parquet` | 4,974,436 | 6 | 3 | 2021-06-14..2026-05-18 | 4,780 | `03e8d2de7469b5fdf9d668c7f446d86e7ff4c8cea6cff0562053c26c08363b5d` |
| `.runtime/phase9/training_dataset_candidates/2026-05-18/opportunity_ai_dataset.parquet` | 4,974,436 | 6 | 4 | 2021-06-14..2026-05-18 | 4,780 | `5493128c25c17bbeae23b50e5fe86f24136b437a2a0399d3bb85f53763e9f124` |

BV18 confirms the formal Opportunity dataset hash and that raw local quotes could support a later label-safe feature date (`2026-06-16`), but Runtime-compatible Opportunity training rows stopped at `2026-05-15`.

## Candidate Dataset Contract

Current formal contract observed from design/code/artifacts:

- observation date: `target_date`
- feature as-of date: `as_of_date`, normally equal to `target_date` after daily close; future rows forbidden
- label date: future 5/10/20bd return windows generated from quote rows after `target_date`
- label horizon: 20 business days is the formal long-history training horizon
- label-safe cutoff: implemented implicitly by Phase4-BD tail exclusion; no common resolver currently computes it from trading calendar/source max date
- training cutoff / dataset max date: current formal artifact max `2026-05-15`
- symbol normalization: `code` string; formal dataset uniqueness is effectively `target_date + code`
- universe eligibility: feature rows include `universe_eligible` and `excluded_reason`, but Phase18-A needs explicit missing/drop policy artifact
- market status handling: BV14 is Runtime BUY guard; Candidate training dataset does not yet include formal lifecycle market-status compatibility evidence
- duplicate key definition: merge validates one-to-one on `target_date, code` in Phase4-BE
- missing-value handling: Phase4-BC/BE quality gates check null/constant/high-null features, but no shared `data_quality.json`
- target definition: `label__momentum_candidate_label` plus future return/top decile/downside labels for evaluation
- feature definition: Phase4-BC long-history price/volume/momentum/liquidity feature set, 13 feature columns in current artifact
- future information exclusion: tested by Phase4-BC/BD/BE and Phase4-BF leakage audits
- source authority: long-history real-runtime normalized quotes / J-Quants derived data; not yet normalized into AI Lifecycle source authority schema
- schema version: Phase4 schema/version fields exist, but no shared Phase18-A dataset schema contract

## Opportunity Dataset Contract

Current formal contract observed from design/code/artifacts:

- observation date: `target_date`
- feature as-of date: `as_of_date`, defaulted to `target_date` if missing
- label date: 20bd future return / max return / drawdown
- label horizon: 20 business days
- label-safe cutoff: BV18 defines latest local quote date minus 20 business days; current formal dataset max is `2026-05-15`, although local quotes supported label-safe max `2026-06-16`
- training cutoff / dataset max date: `2026-05-15` for Phase5P formal dataset
- symbol normalization: `code` string
- universe eligibility: inherited from candidate/opportunity feature inputs; not formalized in lifecycle bundle
- market status handling: BV14 exists in Runtime BUY path; Phase18-C/BV14 compatibility evidence is future work, not Phase18-A dataset generation
- duplicate key definition: current Phase5-D drops duplicates and joins one-to-one on `target_date, code`; SoT now requires `target_date + code + candidate_source_ref`, which is a contract gap
- missing-value handling: Phase5-D audits missing feature rate; Phase5P has quality audits, but no common `data_quality.json`
- target definition: `label__expected_edge_label_20d = label__risk_adjusted_future_return_20d`; BV16/BV17 confirm raw model prediction copies this expected edge
- feature definition: formal Runtime-compatible Phase5P has 32 feature columns
- future information exclusion: Phase5-D and Phase5-E forbidden feature audits; BV18 `NO_LEAKAGE_PASS`
- source authority: Candidate output + market/sector/listed issues/J-Quants-derived features; not yet encoded as shared source authority / lineage schema
- schema version: Phase5-D dataset version and Runtime feature schema exist; no shared Phase18-A dataset bundle schema yet

## Source Authority Findings

- Runtime accepted artifact resolution is Registry-based and fail-closed.
- Dataset source authority is fragmented:
  - Phase4-BC/BD/BE use real-runtime normalized quote artifacts and Phase4 summaries.
  - Phase5-D accepts arbitrary candidate/feature/label paths.
  - Phase5P uses Phase5-I dataset plus Phase4-BC features/listed issues.
  - Phase9-L1 requires J-Quants canonical Phase9 data only, but emits a different schema.
- No single source authority resolver currently decides which canonical data, feature artifacts, listed issues, trading calendar, and candidate lineage are valid for Phase18-A.

## Label-Safe Cutoff Findings

- Candidate labels exclude tail rows without 20bd future observations.
- Phase9-L1 explicitly accepts `data_until`, `safe_train_until`, `train_until`, and blocks `train_until > safe_train_until`.
- BV18 uses latest local trading date minus 20 business days.
- Missing: a common component-specific cutoff resolver using trading calendar and source max dates, emitted into `dataset_metadata.json` and `date_coverage.json`.

Freshness formula to preserve for Opportunity:

```text
dataset_lag_business_days = label_safe_cutoff - training_dataset_max_date
model_training_lag_business_days = label_safe_cutoff - model_training_cutoff
model_acceptance_age_business_days = decision_date - model_accepted_at
```

Do not stale-block Opportunity using only `decision_date - training_dataset_max_date`.

## PIT Correctness Findings

PASS-like existing evidence:

- Phase4-BC test confirms feature rows use past rows only and do not include future label columns.
- Phase4-BD test confirms tail rows without 20bd horizon are excluded.
- Phase5-D test confirms feature/label separation and target-date split separation.
- BV18 reports `NO_LEAKAGE_PASS` for challenger analysis.

Gaps:

- No single PIT validation artifact for Candidate/Opportunity bundles.
- Opportunity SoT uniqueness requires `candidate_source_ref`; current Phase5-D uniqueness lacks that field.
- Market status / delisted handling is Runtime BUY guard evidence, not yet dataset lifecycle compatibility evidence.

## Lineage / Schema / Hash Findings

Existing:

- Phase4/Phase5 builders write summaries, manifests, and audits.
- Registry accepted sets include model, metrics/schema, training metadata, training lineage, validation evidence, and consumer compatibility.
- Runtime verifies accepted member file hashes through Registry.

Missing for Phase18-A:

- SoT-required `dataset_metadata.json`, `feature_schema.json`, `target_schema.json`, `lineage.json`, `data_quality.json`, `date_coverage.json`, `drop_reasons.csv`, `hash_manifest.json`.
- Common schema hash/content hash generation for datasets.
- Explicit lineage refs/hashes for Candidate dataset identity and Opportunity candidate lineage.

## Leakage Findings

Existing audits are valuable:

- Candidate feature leakage: `candidate_ai.leakage_audit.audit_feature_table`
- Candidate dataset leakage: `scripts/build_phase4be_long_history_dataset.py::audit_dataset_frame`
- Opportunity dataset leakage: `opportunity_ai.dataset_builder.audit_opportunity_dataset`
- Opportunity training leakage: `opportunity_ai.training.audit_opportunity_training_dataset`
- Phase9 forbidden source/column audit: `paper_trading.training_dataset_audit.audit_training_dataset`

Gap: These are not unified into a common NO_LEAKAGE evidence artifact with component, source refs, PIT cutoff, forbidden-source checks, and failure status.

## Idempotency / Reproducibility Findings

Existing:

- Phase9-L1 has explicit safe cutoff tests.
- Phase4/Phase5 builders can be rerun and tested on fixtures.
- Runtime submit/idempotency exists, but is unrelated to dataset lifecycle.

Gaps:

- No dataset rebuild idempotency test comparing identical input hashes to identical output dataset hash.
- Existing builders write directly to final outputs, not through a common atomic tmp-to-final publication protocol.
- Failure artifacts are partial and phase-specific, not shared Phase18-A status artifacts.

## Reuse Classification Summary

REUSE_AS_IS:

- Registry resolver and Runtime accepted artifact resolver.
- BV14/BV15 Runtime guards for downstream compatibility checks.

REUSE_WITH_ADAPTER:

- Phase4-BC Candidate feature generation.
- Phase4-BD Candidate label generation.
- Phase9-L1 cutoff/source audit.
- Phase5P market/sector feature construction.

MERGE_INTO_COMMON_PIPELINE:

- Phase4-BE Candidate dataset join/leakage/quality core.
- Phase5-D Opportunity dataset join/leakage core.

DEPRECATED / NOT FOR FORMAL PHASE18-A:

- Phase-numbered direct artifact paths as lifecycle authority.
- Phase5E metrics fallback for Runtime, already prohibited.
- Phase9-L1 6-feature Opportunity dataset as a replacement for formal Phase5P 32-feature contract.

REWRITE_REQUIRED:

- Common lifecycle bundle writer.
- Label-safe cutoff resolver.
- Source authority resolver.
- Atomic output publication and idempotency hash protocol.
- Opportunity `candidate_source_ref` lineage/uniqueness.

## Gap Analysis Against AI Lifecycle v2 SoT

| Requirement | Current State | Phase18-A Gap |
| --- | --- | --- |
| canonical source authority | Fragmented Phase4/5/9 summaries and paths | Need shared resolver and source authority schema |
| component-specific label-safe cutoff | Implicit tail exclusion / Phase9 args / BV18 calculation | Need common resolver and evidence |
| PIT date correctness | Tested in pieces | Need bundle-level PIT validation |
| dataset versioning | Phase-specific versions | Need Phase18-A bundle versioning |
| dataset schema contract | Feature/label columns in summaries | Need `feature_schema.json` and `target_schema.json` |
| metadata contract | Phase-specific summaries | Need `dataset_metadata.json` |
| lineage | Phase-specific refs and Registry lineage | Need `lineage.json` with refs/hashes |
| quality report | Phase-specific audits | Need common `data_quality.json` |
| row uniqueness | Candidate one-to-one `target_date, code`; Opportunity same | Need explicit Candidate key and Opportunity `candidate_source_ref` key |
| coverage/missingness | Partial quality gates | Need shared coverage/missing/drop policy |
| source freshness | BV17/BV18 audit only | Need source freshness evidence |
| dataset hash | Some artifacts measured; not standardized | Need `hash_manifest.json` |
| idempotency | No dataset hash idempotency acceptance | Need rerun test |
| reproducibility | Manual phase scripts | Need fixture and real-artifact reproducibility tests |
| NO_LEAKAGE audit | Multiple audits | Need common status and evidence bundle |
| failure artifact | Phase-specific blocked summaries | Need shared failure/status artifact |
| atomic output publication | Not common | Need tmp output + atomic rename |
| partial output cleanup | Not common | Need failed run cleanup or quarantine |

## Phase18-A Implementation Plan

1. Common entrypoint:
   - Add a dedicated AI Lifecycle Control Plane module/CLI, e.g. `src/ai_fund_lab_v2/ai_lifecycle/dataset_rebuild.py` and `scripts/run_phase18a_pit_dataset_rebuild.py`.
   - It must not train, promote, write Registry accepted events, or switch Runtime.

2. Shared schemas:
   - Define `dataset_metadata.json`, `feature_schema.json`, `target_schema.json`, `lineage.json`, `data_quality.json`, `date_coverage.json`, `hash_manifest.json`, and status schema.
   - Include `phase: Phase18-A`, `component`, `run_id`, `label_safe_cutoff`, `source_authority`, input refs/hashes, row uniqueness keys, and forbidden operation flags.

3. Label-safe cutoff resolver:
   - Use trading calendar and source max date.
   - For 20bd targets, cutoff = latest source trading date minus 20 business dates.
   - Emit both source max date and cutoff.

4. Source authority resolver:
   - Resolve canonical J-Quants-derived normalized quotes, trading calendar, listed issues, Candidate feature artifacts, Candidate output lineage for Opportunity.
   - Fail closed on missing source refs/hashes.

5. Candidate adapter:
   - Reuse Phase4-BC/BD/BE internals or artifact inputs.
   - Output Candidate PIT dataset bundle with key `target_date + code`.
   - Preserve future label isolation and quality gates.

6. Opportunity adapter:
   - Reuse Phase5-D join/leakage core and Phase5P-compatible 32-feature feature construction.
   - Add `candidate_source_ref` to Opportunity rows and uniqueness.
   - Preserve current target: `label__expected_edge_label_20d`.

7. Validation:
   - PIT date correctness.
   - Row uniqueness.
   - Missing/drop policy.
   - Feature/label separation.
   - Forbidden source/column audit.
   - Schema hashes.
   - Dataset hash.

8. Output behavior:
   - Write to a versioned run directory under `reports/phase18_a_common_pit_dataset_rebuild_pipeline_existing_implementation_audit_and_plan/` for audit/rehearsal and later a controlled `.runtime/ai_lifecycle/...` layout.
   - Publish atomically from tmp to final.
   - On failure, write status/failure artifact and do not publish partial final dataset.

9. Test strategy:
   - Unit tests for cutoff resolver.
   - Unit tests for Candidate and Opportunity adapters using fixtures.
   - Leakage tests for forbidden feature/source columns.
   - PIT tests for source rows after cutoff.
   - Duplicate key tests.
   - Idempotency test: same inputs + same run metadata produce same dataset/content hash.
   - Failure tests: missing source, missing labels inside cutoff, schema mismatch, duplicate key.

10. Acceptance commands:
   - `PYTHONPATH=src python3 -m pytest tests/test_phase4bc_long_history_feature_regeneration.py tests/test_phase4bd_long_history_label_regeneration.py tests/test_phase4be_long_history_dataset_rebuild.py tests/opportunity_ai/test_phase5d_opportunity_dataset_builder.py tests/paper_trading/test_phase9l1_training_dataset_candidate.py -q`
   - New Phase18-A tests once implemented: `PYTHONPATH=src python3 -m pytest tests/ai_lifecycle/test_phase18a_common_pit_dataset_rebuild.py -q`
   - `PYTHONPATH=src python3 -m pytest tests/runtime_v2/test_phase16av_registry_consumer_cutover.py -q` to ensure Runtime accepted artifact lookup remains unaffected.

## Risks

- Treating Phase9-L1 Opportunity dataset as formal replacement would break the accepted 32-feature Opportunity contract.
- Rebuilding Opportunity without Candidate lineage can recreate the independent-switch problem that Atomic BUY AI Bundle is meant to prevent.
- Using `decision_date - training_dataset_max_date` as stale logic would double-count the 20bd horizon.
- Direct writes to final artifact paths can leave partial outputs after failure.
- Market status / delisting evidence must remain point-in-time; future delisting absence must not leak backward.

## Open Questions

- Exact permanent runtime layout for Phase18-A lifecycle dataset bundles.
- Whether Phase18-A should initially emit reports-only artifacts before controlled `.runtime` lifecycle artifacts.
- Exact schema hash method for dataset schemas.
- Final policy for missing required features: row drop threshold vs full dataset block.
- How to encode Candidate source lineage for Opportunity historical rows when old Candidate artifacts lack a stable `candidate_source_ref`.

## Final Judgment

```text
primary_judgment: PHASE18_A_COMMON_PIPELINE_IMPLEMENTATION_REQUIRED
secondary_judgments:
  - PHASE18_A_EXISTING_PIPELINE_ADAPTER_REQUIRED
  - PHASE18_A_REVIEW_REQUIRED
```

Existing implementation is not reuse-ready as-is. The correct next step is a common Phase18-A dataset bundle pipeline that adapts the proven Candidate/Opportunity builders, adds source authority, label-safe cutoff, lineage, schema/hash/data-quality artifacts, row uniqueness, idempotency, and failure semantics, while preserving current Opportunity target/features/BV15 and avoiding training/promotion.
