# Phase16-Q Artifact Inventory Gap Classification

## Summary

- Prefix: `Phase16-Q`
- Work: `Artifact Inventory Gap Classification and Acceptance Readiness Review`
- Final judgment: `PHASE16_Q_GAPS_CLASSIFIED`
- Implementation performed: none
- Runtime / path / artifact generation performed: none

Phase16-P identified three gaps. This phase classifies their nature using existing code, reports, and current `.runtime` evidence only.

## Gap1: Candidate Decision Artifact

- Classification: `PRODUCER_NOT_EXECUTED`
- Expected path: `.runtime/runtime_state/buy_ai/2026-07-10/candidate_decisions.json`
- Actual path: `.runtime/runtime_state/buy_ai/2026-07-10/` exists, but `candidate_decisions.json` is absent.
- Producer: `ai_fund_lab_v2.runtime_v2.buy_ai.producer.produce_buy_ai_decisions()`
- Consumer: Opportunity AI and audit.
- Retention: designed as run-scoped decision evidence under `.runtime/runtime_state/buy_ai/<business_date>/`; no cleanup code for this path was found in the inspected Runtime paths.
- Cleanup evidence: no Runtime cleanup path targeting `candidate_decisions.json` was found.
- Run condition: `run_daily_operation.py` calls `produce_buy_ai_decisions()` only when `args.job == "morning"` and `exit_code == EXIT_SUCCESS` after the data-readiness gate.

Evidence:

- `src/ai_fund_lab_v2/runtime_v2/buy_ai/producer.py` creates `artifact_dir = root / "runtime_state" / "buy_ai" / business_date` and writes `candidate_decisions.json`.
- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py` gates the buy-AI producer behind `args.job == "morning" and exit_code == EXIT_SUCCESS`.
- `.runtime/runtime_state/run_manifest/2026-07-10/runtime-v2-morning-2026-07-10-20260710T011051.828366+0000.json` shows `job=morning`, `exit_code=70`, `final_state=HALT`, `generated_artifacts={}`.
- Later `sell_hold_review_only_morning` manifests show `buy_path_executed=false`, so they are not expected to generate BUY decision artifacts.

Conclusion: the expected path is correct, but the relevant producer did not execute successfully for the inspected run. This is not a path discovery gap and not proven to be a retention cleanup gap.

## Gap2: Opportunity Decision Artifact

- Classification: `PRODUCER_NOT_EXECUTED`
- Expected path: `.runtime/runtime_state/buy_ai/2026-07-10/opportunity_rankings.json`
- Actual path: `.runtime/runtime_state/buy_ai/2026-07-10/` exists, but `opportunity_rankings.json` is absent.
- Producer: `ai_fund_lab_v2.runtime_v2.buy_ai.producer._produce_opportunity_artifact()` via `produce_buy_ai_decisions()`
- Consumer: `load_ai_planning_signals_from_opportunity_artifact()` converts rankings to `AIPlanningSignal`; Morning Planning receives those signals and embeds `buy_ai_context` into `order_plan.json`.
- Retention: designed as run-scoped decision evidence under `.runtime/runtime_state/buy_ai/<business_date>/`; no cleanup code for this path was found in the inspected Runtime paths.
- Cleanup evidence: no Runtime cleanup path targeting `opportunity_rankings.json` was found.
- Run condition: Opportunity artifact production depends on Candidate artifact production and the same `morning && EXIT_SUCCESS` gate.

Evidence:

- `producer.py` writes `opportunity_rankings.json` in the same buy-AI artifact directory.
- `_produce_opportunity_artifact()` reads `candidate_decisions.json`, `opportunity_feature_input.parquet`, Opportunity model, and metrics, then writes `opportunity_rankings.json`.
- `load_ai_planning_signals_from_opportunity_artifact()` reads `rankings` and creates `AIPlanningSignal` rows for Planning.
- `morning_pipeline.py` returns `buy_ai_opportunity_artifact_missing` when `ai_signals is None`, confirming Planning expects Opportunity output or equivalent passed signals.
- The inspected 2026-07-10 morning manifest halted before generated artifacts were recorded; sell-hold review-only runs explicitly did not execute the buy path.

Conclusion: Opportunity decision absence is downstream of the buy-AI producer not executing successfully. It is not classified as path discovery or retention.

## Gap3: Corporate Action

- Classification: `DESIGN_EXTENSION_REQUIRED`
- Current evidence: Raw daily quotes and normalized OHLCV contain adjusted price/volume fields (`AdjFactor`, `AdjO`, `AdjH`, `AdjL`, `AdjC`, `AdjVo`) and normalization prefers adjusted fields when available.
- Standalone table evidence: no dedicated `.runtime/data/raw/jquants/corporate_actions/data.parquet` was found.
- Current design status: partial. Adjusted OHLCV supports split/reverse-split adjusted price continuity, but standalone stock split / reverse split / delisting event auditability is not established.

Evidence:

- `reports/phase_reports/phase16_g_canonical_historical_data_source_audit.json` records `stock_split=PARTIAL_IN_DAILY_QUOTES_ADJUSTED_FIELDS`, `reverse_split=PARTIAL_IN_DAILY_QUOTES_ADJUSTED_FIELDS`, `standalone_store_found=false`, and `gap=No dedicated corporate action event table found`.
- `docs/phase_reports/phase16_g_canonical_historical_data_source_audit.md` states normalized OHLCV uses adjusted fields but event auditability is incomplete without a standalone or historical listed/corporate action source.
- `src/ai_fund_lab_v2/data_quality/normalization.py` and `src/ai_fund_lab_v2/data_store/schema.py` define adjusted fields as normalization inputs.

Conclusion: the current design can operate partially through adjusted OHLCV, but Acceptance requires an explicit design decision: adjusted OHLCV only, or a standalone corporate-action event source. This is not classified as a direct implementation bug because the required source-of-truth contract is not yet finalized.

## VALIDATED to ACCEPTED Readiness

### Candidate

- Hash: model and manifest hashes exist; artifact-set hash candidate exists.
- Schema: model manifest / training / validation JSON schema hashes exist; pickle model schema is not structurally introspectable and needs review acceptance.
- Producer: Candidate training acceptance and Runtime buy-AI producer are identified.
- Consumer: Candidate Model Loader and Opportunity AI are identified.
- Artifact Set: manifest candidate is `VALIDATED`.
- Evidence: training summary and validation evidence exist.
- Regression: acceptance needs consumer-path regression proving logical registration does not change Candidate scoring.
- Review: requires human approval of model, manifest, training evidence, validation evidence, and Runtime decision-output contract.

### Opportunity

- Hash: model, Phase5-P metrics, training evidence, validation evidence, and artifact-set hash candidate exist.
- Schema: metrics/training/validation schema hashes exist; pickle model requires review acceptance.
- Producer: Opportunity training acceptance and Runtime buy-AI producer are identified.
- Consumer: Opportunity Model Loader, Opportunity Metrics Loader, and Morning Planning are identified.
- Artifact Set: manifest candidate is `VALIDATED`.
- Evidence: Phase5-P metrics and validation evidence exist.
- Regression: acceptance needs confirmation that Phase5-P metrics are bound to the accepted model and that the Phase5-E fallback is removed or explicitly rejected by Registry lookup.
- Review: requires model/metrics pair review and fallback behavior review before `ACCEPTED`.

### Position Management

- Hash: code-policy and Runtime adapter source hashes exist; artifact-set hash candidate exists.
- Schema: no separate model schema; acceptance is code-policy based.
- Producer: PM code acceptance and Runtime PM adapter are identified.
- Consumer: PM Producer and sell planning are identified.
- Artifact Set: manifest candidate is `VALIDATED`.
- Evidence: PM Runtime decision artifact exists for 2026-07-10.
- Regression: acceptance needs PM decision parity checks before/after logical registration.
- Review: requires code-policy review, adapter review, and decision-output contract review.

### Capital Allocation

- Hash: policy config hash and policy manifest hash candidate exist.
- Schema: policy JSON schema hash exists.
- Producer: human/policy acceptance.
- Consumer: Planning and Submit Guard.
- Artifact Set: policy manifest candidate is `VALIDATED`.
- Evidence: policy file exists and Planning embeds `CapitalAllocationSignal` evidence.
- Regression: acceptance needs proof that policy loading, Planning, Pending, and Submit Guard behavior remain unchanged.
- Review: requires policy owner approval and explicit decision on whether standalone Capital Allocation Decision Artifact is required later.

## Implementation Bug Review

- Candidate Decision Artifact gap: no producer bug proven; classified as `PRODUCER_NOT_EXECUTED`.
- Opportunity Decision Artifact gap: no producer bug proven; classified as `PRODUCER_NOT_EXECUTED`.
- Corporate Action gap: no direct implementation bug proven; classified as `DESIGN_EXTENSION_REQUIRED`.
- Noted runtime evidence: the inspected 2026-07-10 morning run halted with an unexpected missing-column error before buy-AI artifact generation. That explains the absence for this run, but this phase does not fix or retest it.

## Design Change Review

- Candidate / Opportunity decision paths: no design change required for path definition; current path is confirmed.
- Corporate Action: design decision is required before ACCEPTED status. The system must explicitly choose adjusted OHLCV-only handling or define a standalone corporate-action event source.
- Artifact acceptance: design/implementation work remains required for formal Registry production, ACCEPTED status promotion, logical ID startup resolution, and consumer migration.

## Next Prefix

Recommended next prefix: `Phase16-R`

Recommended scope: acceptance criteria hardening and review plan only, unless the user explicitly authorizes implementation. Do not proceed to Registry implementation, artifact generation, Runtime changes, Simulation, Reset, or Historical Test from Phase16-Q.
