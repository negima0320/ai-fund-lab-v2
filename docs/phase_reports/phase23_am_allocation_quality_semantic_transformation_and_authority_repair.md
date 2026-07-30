# Phase23-AM Production-common Allocation Quality Semantic Transformation and Authority Repair

## Primary Judgment

`PHASE23_AM_ALLOCATION_QUALITY_SEMANTIC_AUTHORITY_REPAIR_SHORT_VALIDATION_PASS`

## Design Authority Decision

Phase23-AM separates Raw Opportunity Signal, Allocation Quality, and Allocation Decision / Weight.

- Raw producer: Opportunity Ranking Authority, surfaced by Portfolio Construction as `runtime_opportunity_score` with lineage.
- Allocation Quality producer: no existing implicit Production-common authority was found in the reviewed SoT; `allocation_quality_score` must be supplied by explicit allocation-quality authority.
- Portfolio Construction: preserves raw opportunity signal and membership lineage; it does not promote raw score into quality.
- Position Sizing: consumes only `allocation_quality_score` / explicit legacy allocation-quality `quality_score` for quality multiplier.

## Raw Opportunity Score Contract

`runtime_opportunity_score` is finite numeric and signful. Negative values are valid raw opportunity signals and are not schema errors. `input_score` and `opportunity_score` are legacy/raw attribution fields only, not allocation-quality aliases.

## Allocation Quality Contract

Canonical field: `allocation_quality_score`.

Range: finite numeric `[0,1]`.

Authority: `allocation_quality_authority` with `output_semantics=allocation_quality_score`.

Missing / invalid / conflict behavior remains fail-closed: `QUALITY_UNAVAILABLE`, `target_notional=0`, `REVIEW_REQUIRED`.

## Semantic Transformation Authority

No new numeric transformation was introduced. The following remain rejected: clamp, absolute value, score shifting, sigmoid, current-day min-max, percentile rank, negative-to-zero, and validator relaxation only.

## Negative Score Handling

Negative `runtime_opportunity_score` now remains valid raw lineage. It does not trigger `invalid_quality_score:<index>` and is not silently converted to positive quality.

## Legacy Alias Separation

`input_score` and `opportunity_score` are no longer consumed as quality aliases. They can appear in raw resolution as legacy attribution only. `quality_score` is accepted only as legacy allocation-quality when its authority declares allocation-quality semantics.

## Portfolio Construction Validation

Portfolio Construction now validates raw opportunity score separately from allocation quality:

- raw: finite numeric, signful allowed, authority required when present
- allocation quality: finite `[0,1]`, authority and semantics required
- legacy `quality_score` emission from Portfolio Construction is forbidden

## Position Sizing Propagation

Position Sizing decision rows now include:

- `runtime_opportunity_score`
- `runtime_opportunity_score_authority`
- `runtime_opportunity_score_resolution`
- `allocation_quality_score`
- `allocation_quality_authority`
- `allocation_quality_resolution`
- `quality_adjustment`
- `target_notional`

## Model Health Dependency

`MODEL_HEALTH_REVIEW_REQUIRED` / `BASELINE_CURRENT_SEMANTICS_MISMATCH` remains a supporting gap, not the direct AM blocker. AM does not repair model health; it prevents raw model score semantics from being misused as allocation quality.

## No Forced BUY Confirmation

Zero-capacity policy still produces `RESOLVED_ZERO_ALLOCATION`, `target_notional=0`. BUY count is not an acceptance condition.

## Short Validation

- Targeted Portfolio Construction / Position Sizing: `42 passed in 1.80s`
- Compile: PASS with `PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache_phase23am`
- Expanded Strategy regression: `67 passed in 2.20s`
- Long Runtime / 1BD / 10BD / 20BD: not executed

## Existing Run Preservation

- target hash preserved: `true`
- compare hash preserved: `true`
- artifact mutation detected: `false`
- reclassification performed: `false`

## Created / Updated Files

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `tests/strategy/test_phase22_e_portfolio_construction.py`
- `tests/strategy/test_phase22_j_position_sizing.py`
- `tests/strategy/test_phase22_pr_dynamic_capacity_asset_proportionality.py`
- `docs/phase_reports/phase23_am_allocation_quality_semantic_transformation_and_authority_repair.md`
- `reports/phase_reports/phase23_am_allocation_quality_semantic_transformation_and_authority_repair.json`
- `reports/phase23_am_allocation_quality_semantic_transformation_and_authority_repair/`

## Remaining Gaps

A formal Production-common allocation-quality transformation formula is still not defined. AM intentionally does not invent one. If the runtime source lacks `allocation_quality_score`, Position Sizing remains fail-closed.

## Runtime Rerun Readiness

`READY_FOR_1BD_RUNTIME_VALIDATION = YES` after ChatGPT Evidence Review.

Phase23-AM did not execute a runtime rerun.

## Next Operator Action

Submit Phase23-AM evidence for ChatGPT review, then operator may run 1BD validation. 10BD remains out of scope for Codex in this task.
