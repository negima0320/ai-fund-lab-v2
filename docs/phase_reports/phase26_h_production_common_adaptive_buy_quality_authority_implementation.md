# Phase26-H Production-Common Adaptive BUY Quality Authority Implementation

## Judgment

PHASE26_H_ADAPTIVE_BUY_QUALITY_AUTHORITY_IMPLEMENTED

## Primary Implementation

Implemented the Production-common Adaptive BUY Quality Authority as `buy_quality_decisions.v1` / `buy_quality_decision.v1`, produced by `Production Strategy BUY Quality Resolver`. The artifact evaluates Relative Opportunity Quality, Market Context Quality Modifier, Signal Reliability, Execution Feasibility, and Portfolio Fit, then emits one of `FULL_ALLOCATION_ELIGIBLE`, `REDUCED_ALLOCATION_ONLY`, `REVIEW_REQUIRED`, or `REJECT`.

The runtime strategy chain now materializes `daily/<business_date>/strategy/buy_quality_decisions.json` before Portfolio Construction and propagates the decision through Portfolio Construction, Position Sizing, Runtime Planning, Pending listed info, and planning quantity contract observability.

## Quality Scoring Method

The implemented `quality_score` is a normalized `0.0` to `1.0` score. It is not win probability, expected return, raw rank, or raw Opportunity score.

The score is calculated as a weighted blend:

```text
quality_score =
    0.35 * relative_opportunity_quality
  + 0.15 * market_context_quality_modifier
  + 0.25 * signal_reliability
  + 0.10 * execution_feasibility
  + 0.15 * portfolio_fit
```

Relative Opportunity Quality is based on same-day cross-sectional percentile, robust z-score, and population strength. This prevents rank 1 from automatically becoming full allocation when the whole candidate population is weak.

Market Context Quality Modifier uses market confidence, breadth, trend score, and volatility risk. It is a symbol-level quality modifier and does not duplicate Portfolio Policy exposure control.

Signal Reliability checks confidence, completeness, calibration status, Accepted Generation binding, and temporal alignment. Critical reliability conflict produces `REVIEW_REQUIRED` or `REJECT`; it is not averaged away.

Execution Feasibility uses liquidity, downside risk, and corporate-event status when available. Missing non-critical evidence is explicit conservative reduction, not silent neutral.

Portfolio Fit uses current weight, single-name room, target gross exposure reference, and same-symbol pending penalty. It is not a fixed position-count authority.

Action mapping:

| Action | Condition | Allocation adjustment |
|---|---|---:|
| `FULL_ALLOCATION_ELIGIBLE` | `quality_score >= 0.72`, `relative_opportunity_quality >= 0.65`, and no weak-population rank-1 flag | `1.0` |
| `REDUCED_ALLOCATION_ONLY` | `quality_score >= 0.45` but full-allocation conditions are not met | `clamp(quality_score, 0.25, 0.85)` |
| `REVIEW_REQUIRED` | critical evidence unavailable or conflicted | `0.0` |
| `REJECT` | no-buy evidence, non-positive/missing raw opportunity score, or score below reduced threshold | `0.0` |

Position Sizing consumes the result as:

```text
post_quality_target_weight =
    resolved_target_weight * quality_allocation_adjustment
```

The notional base remains current total equity.

## Decision Boundary

No fixed Rank N gate was added. No fixed raw score threshold was added. No fixed notional rule was added. `target_position_count` was not reconnected as a BUY admission or sizing consumer. Historical-only logic was not added.

BUY Quality can reduce or withhold a new BUY when quality evidence is weak or critical evidence is missing. Missing adaptive quality does not default to `quality_adjustment=1.0`; it resolves to `REVIEW_REQUIRED` with adjustment `0.0`.

## Existing Authority Preserved

Candidate scoring, Opportunity scoring, Market Context thresholds, Cash/Exposure authority, Safety hard maximums, Submit Guard policy, Accepted Generation binding, and Temporal Authority were not changed. Position Sizing still uses current total equity as the notional base; adaptive quality only scales the already-resolved target weight.

## Regression

- compile: PASS
- Phase26-H unit: PASS, 10 passed
- short regression: PASS, 110 passed
- manifest/closure regression: PASS, 23 passed
- fresh-run / 1BD / 3BD / 10BD / 100BD: NOT EXECUTED

## User Rerun Command

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-smoke --date-from 2022-07-01 --business-days 3
```

## Entry Readiness

READY
