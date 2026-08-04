# Phase26-G Adaptive BUY Quality Authority Design and Architecture SoT Amendment

Primary Judgment:

`PHASE26_G_ADAPTIVE_BUY_QUALITY_AUTHORITY_DESIGN_FROZEN_IMPLEMENTATION_READY`

## Design Status

Design frozen for implementation. Phase26-G changed architecture documentation and design contracts only. Runtime, Strategy behavior, BUY admission implementation, Position Sizing implementation, Submit Guard, Safety, Candidate, and Opportunity production were not changed.

## Architecture SoT Updated

Canonical BUY Quality Specification:

`docs/02_architecture/adaptive_buy_quality_authority.md`

Updated SoT:

- `docs/02_architecture/autonomous_ai_operations_architecture.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/01_requirements/phase_roadmap.md`

## BUY Quality Definition

Adaptive BUY Quality Authority is the Production / Demo / Historical common authority that uses PIT candidate distribution, market context, signal reliability, execution feasibility, and portfolio fit evidence to decide how trustworthy and allocation-capable a BUY opportunity is.

It may output:

```text
BUY_ELIGIBLE
BUY_REDUCED_ALLOCATION
BUY_REVIEW_REQUIRED
BUY_REJECTED
```

It is not predicted return, win probability, fixed position-count control, Submit permission, Safety hard maximum, broker execution authority, or raw Opportunity score reinterpretation.

## Component Definitions

Relative Opportunity Quality:

Uses opportunity rank, raw score, daily population, percentile, robust z-score, margins, and population strength. Rank 1 alone is insufficient; weak population Rank 1 is not automatically high quality.

Market Context Modifier:

Uses continuous market evidence where available: trend, breadth, volatility, confidence, uncertainty, risk posture, sector/benchmark context. It must not duplicate Portfolio Policy exposure effects.

Signal Reliability:

Uses model confidence, feature completeness/freshness, Accepted Generation binding, temporal status, data readiness, calibration status, and population stability. `calibration_applied=false` prohibits treating raw score as expected return.

Execution Feasibility:

Uses explicit price, lot, liquidity, volume/turnover, event risk, and order feasibility evidence where available. Unavailable data is not inferred.

Portfolio Fit:

Uses current weight, sector concentration, same-symbol active campaign/pending, cash/gross exposure after BUY, single-name weight after BUY, and portfolio risk posture. It is not a fixed position-count gate.

## Composite Method

The composite output is normalized to `quality_score` in `[0.0, 1.0]`. The score is a trust/allocation-capability score under the Quality contract, not expected return or probability.

The method may initially be a transparent weighted blend, but each component must expose status, weight, input authority, missing-evidence behavior, and reason codes. Critical component failure cannot be hidden by other high scores.

## Missing Evidence Behavior

Required Quality evidence missing must not silently become `quality_adjustment=1.0`.

Critical missing/authority conflict:

```text
BUY_REVIEW_REQUIRED or BUY_REJECTED
```

Non-critical missing:

```text
explicit conservative reduction
```

Not required:

```text
neutral only with NOT_REQUIRED status
```

## BUY Admission Contract

Low positive `expected_edge_score` may pass raw Opportunity Eligibility, but it must not proceed to normal BUY allocation without Adaptive BUY Quality acceptance.

## Quality-Sensitive Sizing Contract

Current total equity remains the capital base. Quality affects individual allocation strength after Portfolio Policy exposure and Portfolio Construction target allocation are established.

Responsibility split:

- Market Context: total exposure context and confidence evidence
- Portfolio Policy: target exposure/cash posture
- Adaptive BUY Quality: individual BUY admission / allocation strength
- Portfolio Fit: concentration compatibility
- Position Sizing: notional and quantity candidate
- Safety: hard block / hard maximum

## Prohibited Inputs and Reconnects

- `target_position_count` decision consumer: false
- fixed Rank N limit added: false
- fixed raw Score threshold added: false
- Historical result input added: false
- Paper Ledger input added: false
- future information added: false
- historical-only branch added: false
- implicit missing-quality fallback added: false

## Implementation Ready

Yes. Next task:

```text
Phase26-H Production-Common Adaptive BUY Quality Authority Implementation
```

Phase26-H must implement producer-first, then consumer wiring, then propagation, then negative assertions and short regression. Long Historical validation remains user/operator-owned.
