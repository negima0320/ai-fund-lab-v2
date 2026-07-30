# Phase23-AK Quality Score Authority Contract Repair

## 1. Primary Judgment

`PHASE23_AK_QUALITY_SCORE_AUTHORITY_CONTRACT_REPAIR_SHORT_VALIDATION_PASS`

## 2. Root Cause

`PORTFOLIO_CONSTRUCTION_SCORE_FIELD_TO_POSITION_SIZING_QUALITY_AUTHORITY_CONTRACT_MISMATCH_FORCES_ALL_ALLOCATIONS_TO_ZERO`

AJで確認された `input_score` → `opportunity_score` の境界不一致を、Production-commonのQuality Authority Contractとして修正した。

## 3. Producer Contract

Portfolio Construction now emits canonical `quality_score` when a numeric upstream score exists. It also emits `quality_score_authority` with source field, source decision ID, source artifact class, and candidate/opportunity references.

Legacy `input_score` is preserved for existing attribution. Missing upstream score is not converted into canonical zero quality.

## 4. Consumer Contract

Position Sizing consumes quality through `resolve_quality_score()`.

- Canonical field: `quality_score`
- Legacy aliases: `input_score`, `opportunity_score`
- Priority: canonical, then supported alias
- Missing: `REVIEW_REQUIRED`, fail-closed `QUALITY_UNAVAILABLE`
- Invalid: `REVIEW_REQUIRED`
- Conflict: `REVIEW_REQUIRED`

## 5. Canonical Quality Field

`quality_score` is the canonical per-symbol quality authority field. It is numeric in `[0, 1]` and participates in Position Sizing quality multiplier calculation only when resolved.

## 6. Legacy Alias

`input_score` and `opportunity_score` are supported aliases. Alias use is explicit in `quality_resolution.legacy_alias_used`; it is not a silent fallback.

## 7. Conflict Rules

If supported quality fields are present with different numeric values, Position Sizing records `quality_score_field_conflict` and keeps `target_notional=0`.

## 8. Quality Resolver

`resolve_quality_score()` returns resolved quality, authority, resolution status, source field, alias flag, review reason, lineage, observed fields, and conflict flag.

## 9. Quality Propagation

Resolved quality now propagates to quality multiplier and positive target notional. True missing quality still produces `QUALITY_UNAVAILABLE` and fail-closed zero notional.

AJ-style input_score reproduction produced positive target notional count: `10`.

## 10. Runtime Planning Propagation

Synthetic positive Position Sizing output propagated to Runtime Planning as:

- `planning_intent`: `BUY_NEW`
- `order_side_intent`: `BUY`
- `quantity_status`: `RESOLVED_EXECUTABLE`

## 11. Decision Trace

Position Sizing items now include `quality_score`, `quality_authority`, and `quality_resolution`.

## 12. Regression

Targeted regression passed: `49 passed in 1.79s`.

## 13. Modified Files

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `tests/strategy/test_phase22_e_portfolio_construction.py`
- `tests/strategy/test_phase22_j_position_sizing.py`

## 14. Short Validation

- `py_compile`: PASS
- targeted pytest: PASS
- isolated reproduction: PASS

## 15. Existing Run Preservation

Target run hash preservation: `True`.

## 16. Remaining Gaps

- Trading unit authority remains a separate non-primary gap from AJ; this task did not formalize listed-issue trading unit consumption.
- Full 1BD Runtime validation was intentionally not executed.

## 17. Next Operator Action

Submit Phase23-AK evidence for review. After review, operator can run 1BD validation; do not run 10BD until 1BD evidence is accepted.
