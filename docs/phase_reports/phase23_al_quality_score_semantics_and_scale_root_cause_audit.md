# Phase23-AL Quality Score Semantics / Scale Contract Root Cause Audit

## Primary Judgment

`PHASE23_AL_QUALITY_SCORE_SEMANTICS_ROOT_CAUSE_CONFIRMED_REPAIR_REQUIRED`

## Direct Runtime Blocker

`PORTFOLIO_CONSTRUCTION_BLOCKED_BY_INVALID_QUALITY_SCORE`

The target run is `runtime-test-historical-smoke-20260729T224044624059Z` for business date `2026-07-06`. Morning halted with `morning pipeline blocked: strategy_runtime_planning_blocked`.

## Root Cause

Runtime BUY Opportunity producer emits `expected_edge_score` / `opportunity_score` as `runtime_opportunity_score`, with `calibration_applied=false` and `population_scope=CandidateTop50_single_business_day`. The observed score is signful and includes negative values.

Phase23-AK promoted that value through Portfolio Construction `_score()` / `_quality_score_payload()` into canonical `quality_score`, whose AK contract requires numeric `[0,1]`. Portfolio Construction validator rejected negative values at member indices `9, 12, 13, 14, 16-49`, wrote a BLOCK shadow error artifact, and that propagated to Position Sizing and Runtime Planning.

## Upstream Score Semantics

- `candidate_score`: candidate ranking / eligibility score, observed in `[0,1]`, not allocation quality.
- `opportunity_score`: copied from `expected_edge_score`; runtime opportunity score, signful, higher-is-better, not calibrated in this runtime artifact.
- `input_score`: Portfolio Construction attribution field copied from opportunity `expected_edge_score` before AK.
- `quality_score`: AK canonical allocation-quality field, expected `[0,1]`, but target run populated it from signful `expected_edge_score`.

## Expected Range

AK expected `quality_score` range: `[0,1]`.

## Observed Runtime Range

- count: `50`
- min: `-0.42747597`
- max: `0.56251442`
- mean: `-0.11013859139999999`
- median: `-0.16144174500000003`
- negative count: `38`
- greater-than-one count: `0`

## Invalid Row Pattern

`invalid_quality_score:<n>` is the 0-based `portfolio_members` index emitted by `validate_portfolio_construction_artifact()` / `_validate_member()`, not a symbol, score value, decision id, or artifact line number.

Because the target run BLOCK artifact does not materialize `portfolio_members`, member order was reconstructed from the compare run's accepted `portfolio_construction.portfolio_members` order before the AK `quality_score` validator was added.

Indices not invalid (`0-8`, `10`, `11`, `15`) are exactly the rows whose copied `expected_edge_score` is within `[0,1]`. Invalid rows are negative.

## AK Contract Validity

Judgment: `B_AND_C_WITH_SUPPORTING_D`.

- B: upstream runtime score is not wrong by itself; AK directly promoted it to quality incorrectly.
- C: `input_score`, `opportunity_score`, and `quality_score` have different semantics and should not be treated as equivalent aliases for allocation quality.
- D: calibration/normalization authority exists in lifecycle metadata, but runtime artifact has `calibration_applied=false`.

## Model Health Relationship

`MODEL_HEALTH_REVIEW_REQUIRED` / `BASELINE_CURRENT_SEMANTICS_MISMATCH` is related supporting evidence, not the direct Planning BLOCK. The direct blocker is Portfolio Construction schema validation failure.

## Lineage Integrity

Source lineage is available before block through `input_manifest` and `source_manifest`: candidate and opportunity artifacts are present and hash-bound. However, Portfolio Construction failed before materializing full member rows, so `quality_score_authority` is not present in the target portfolio artifact. The canonical value source is still identifiable from code and source artifacts: `expected_edge_score` from `opportunity_rankings.json`.

## Recommended Production-common Repair

Recommended: Option B with Option C separation.

Portfolio Construction should perform an explicit, documented semantic transformation into allocation-quality, while preserving raw `runtime_opportunity_score` / `input_score` as separate lineage fields. Raw `input_score` and `opportunity_score` should not be canonical quality aliases unless their semantics and scale are explicitly compatible.

## Rejected Repair Options

Rejected as primary repair:

- clamp / min-max / sigmoid without authority
- validator relaxation only
- dropping invalid rows
- treating negative expected edge as quality directly
- forced BUY / minimum quantity
- Historical-only branch

## Existing Run Preservation

- target hash preserved: `True`
- compare hash preserved: `True`
- artifact mutation detected: `False`
- reclassification performed: `False`

## Short Validation

Read-only validation only:

- JSON parse and artifact inventory extraction
- score distribution extraction
- invalid index reconstruction
- AK-before comparison against `runtime-test-historical-smoke-20260729T220208972293Z`
- code boundary review with `rg` / `nl`

No code repair, schema change, clamp, normalization, fresh run, 1BD rerun, 10BD/20BD, Broker Write, Runtime Switch, J-Quants fetch, or existing-run mutation was performed.

## Created / Updated Files

- `docs/phase_reports/phase23_al_quality_score_semantics_and_scale_root_cause_audit.md`
- `reports/phase_reports/phase23_al_quality_score_semantics_and_scale_root_cause_audit.json`
- `reports/phase23_al_quality_score_semantics_and_scale_root_cause_audit/`

## Remaining Gaps

- Need a formal allocation-quality transformation contract.
- Need to decide whether quality belongs in Portfolio Construction or a separate allocation-quality artifact.
- Need regression that uses signful runtime opportunity scores, not only `[0,1]` synthetic quality scores.

## Next Recommended Task

Phase23-AM: Production-common Quality Score Semantic Transformation and Allocation-Quality Authority Repair.

## Runtime Rerun Readiness

`READY_FOR_RUNTIME_RERUN = NO` until the semantic repair is implemented and short validation passes.
