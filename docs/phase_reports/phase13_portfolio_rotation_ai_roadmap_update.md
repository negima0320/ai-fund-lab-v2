# Phase13 Portfolio Rotation AI Roadmap Update

## Summary

Phase13 was added to the roadmap as a future design and validation phase:

```text
Phase13
Portfolio Rotation AI / Position Management v2 Design
```

This update is documentation-only.

No implementation, runtime change, AI retraining, backtest rerun, Broker API connection, Demo order, Production order, Production Unlock, or LINE send was performed.

## Motivation

Phase12-H found that SELL / Exit integration has mixed results:

```text
SELL integrated 1 year:
annualized_return 17.6736%
max_drawdown -24.7342%

SELL integrated 5 year:
annualized_return 51.2017%
max_drawdown -21.5802%
```

Before / After:

```text
1 year:
72.588% -> 17.6736%
material degradation

5 year:
31.2197% -> 51.2017%
improvement
```

SELL quality:

```text
SELL after 20 business days > +5%:
60 cases

SELL after 20 business days < -5%:
143 cases

estimated avoided loss:
about 1,146,749 JPY
```

Phase12-H judgement:

```text
SELL_INTEGRATION_NEEDS_CALIBRATION_BEFORE_PRODUCTION_REVENUE_CLAIM
```

The result suggests that a holding-only exit decision is not enough. AI Fund Lab also needs to evaluate whether capital should stay in the current holding or rotate into a higher expected-value candidate.

## Updated Roadmap

Updated:

- `docs/01_requirements/phase_roadmap.md`

Added Phase13:

```text
Portfolio Rotation AI / Position Management v2 Design
```

Purpose:

```text
Compare current holdings and new candidates on the same expected-value axis,
and decide whether capital should rotate into higher expected-value names.
```

Phase13 is not a commitment to a new AI. It is a design-review phase to decide the appropriate responsibility boundary.

## Created Design

Created:

- `docs/03_ai_design/portfolio_rotation_ai_design.md`

The design defines:

```text
Purpose
Difference from Position Management AI
Difference from Opportunity AI
Difference from Capital Allocation
Allowed / forbidden input candidates
Output candidates
ROTATE definition
Evaluation design
Risks
Phase13-A to Phase13-E work plan
Non-goals
Open questions
```

## Existing Design Notes

Updated with Phase13 notes:

- `docs/03_ai_design/position_management_ai_design.md`
- `docs/03_ai_design/capital_allocation_design.md`

These are non-destructive notes only. They do not change the existing responsibilities.

## Phase13 Positioning

Phase13 asks:

```text
Is this holding still worth capital?

Should the system rotate into a new candidate?

Which action maximizes expected value:
HOLD / ROTATE / REDUCE / EXIT?
```

Potential scope:

```text
holding scoring
new candidate scoring
expected-value spread comparison
rotation candidate generation
ROTATE as a sell reason
portfolio-level constraints
responsibility separation from Capital Allocation
backtest evaluation after design approval
```

## Guardrails

Forbidden:

```text
AI retraining as part of this update
Backtest result used for learning
Broker Snapshot / Paper Ledger / PnL / cash / portfolio state / Safety Result / Audit Result used for AI training
LLM investment decision automation
margin trading
leverage
Production order
Demo order
LINE send
```

## Phase12 Continuity

Phase12 continues.

Phase13 is a future design phase and does not stop:

```text
Demo Read-only work
Demo Order Wire design/review
30 business day Demo operation validation
Production Runtime readiness work
```

## Verification

Verification performed:

```text
JSON validation
lightweight document review
```

No code tests or backtests were required because this was documentation-only.

## Final Status

```text
PHASE13_PORTFOLIO_ROTATION_AI_ROADMAP_UPDATE_COMPLETE
IMPLEMENTATION_NOT_CHANGED
RUNTIME_NOT_CHANGED
PHASE12_CONTINUES
```
