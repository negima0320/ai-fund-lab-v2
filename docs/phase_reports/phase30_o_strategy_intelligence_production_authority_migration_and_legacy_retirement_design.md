# Phase30-O — Strategy Intelligence Production Authority Migration and Legacy Retirement Design

Task ID: `Phase30-O`

## Primary Judgment

```text
PHASE30_O_STRATEGY_INTELLIGENCE_PRODUCTION_MIGRATION_AND_LEGACY_RETIREMENT_DESIGN_COMPLETE
```

## Migration Design Status

```text
PRODUCTION_MIGRATION_DESIGN_COMPLETE
```

Phase30-O is design-only. It does not authorize or perform implementation,
Strategy behavior change, Runtime behavior change, config change, model
creation, model retraining, or Accepted Generation mutation.

## Target Production Architecture

Final Production flow:

```text
PIT Source Authorities
  -> Feature Producers
  -> Strategy Intelligence
       Eligibility
       Continuation Quality
       Downside Risk
       Expected Edge evidence
       Profit Protection evidence
       Lifecycle / campaign context
  -> Action-specific consumers
       BUY-side / Portfolio Construction
       PM existing-position decisions
  -> Position Sizing
  -> Runtime Planning
  -> Strategy Planning Authority
  -> Safety
  -> Submit / Execution
```

Final target:

```text
ONE PRODUCTION STRATEGY AUTHORITY PATH
```

## Strategy Intelligence Role

Strategy Intelligence owns structured evidence, semantic interpretation, and
lifecycle context. It is not Action Authority.

Authority remains:

- Portfolio Construction: target portfolio and relative capital allocation.
- PM: HOLD / ADD / REDUCE / EXIT directional Action Authority.
- Position Sizing: executable quantity and lot-aware sizing.
- Runtime Planning: mapping only.
- Safety: guardrails only.

## BUY_NEW Integration

BUY_NEW uses Eligibility + CQ + Downside Risk + Expected Edge evidence +
Portfolio context. Authoritative disqualifying facts may block. Weak CQ or
probabilistic risk may wait, reduce attractiveness, or require review, but
probabilistic risk is not an automatic hard reject. High momentum alone must not
authorize BUY.

No Phase30-O threshold is selected from Historical outcome.

## BUY_WAIT Integration

BUY_WAIT remains:

```text
thesis remains potentially valid, but current entry timing/evidence is insufficient
```

It stays non-Pending, next-day re-evaluated, and SELL independent. BUY evidence
failure may produce BUY_WAIT/no-action/review/block for BUY-side only; it must
not stop SELL / REDUCE / EXIT.

## ADD Integration

ADD is separate from HOLD. ADD requires incremental capital justification:
current CQ, incremental CQ, Downside Risk, incremental Expected Edge,
opportunity cost, current exposure, Strategy cap, and Safety cap.

Strategy Intelligence provides evidence only. PC and Position Sizing retain
allocation and executable quantity authority.

## REENTRY Integration

Semantic REENTRY, cooldown, and recovery hurdle are preserved. Strategy
Intelligence provides recovery, CQ, Downside Risk, unresolved/churn, and prior
campaign context. Blanket REENTRY bans are prohibited. REENTRY is not BUY_ADD.

## HOLD Integration

HOLD means:

```text
current PIT evidence still supports keeping capital deployed in the current canonical campaign
```

It is not merely "SELL condition not reached." PM remains Action Authority.

## Profit Protection Integration

Profit Protection is PM evidence, not a SELL rule. It may use observed embedded
return, observed campaign MFE, observed giveback, CQ deterioration, Downside
Risk rise, and regime deterioration.

Future peak, future MFE, final campaign outcome, and fixed take-profit
thresholds are prohibited.

## REDUCE / EXIT Integration

PM integrates CQ deterioration, topping/reversal risk, profit giveback,
campaign context, event uncertainty, regime, and current-position evidence.

Prohibited:

- CQ alone -> SELL.
- Risk alone -> EXIT.
- automatic REDUCE -> EXIT.

## Expected Edge Role

Expected Edge remains:

```text
calibration_status = UNCALIBRATED
economic_units_available = false
```

It may be used for relative opportunity, allocation comparison, incremental ADD,
and opportunity-cost evidence. It must not be used as calibrated expected return
or absolute return threshold.

## Relative Strength Role

First generation may formally use stock-vs-market relative strength only.

```text
stock-vs-sector = DEFERRED_DATA_FOUNDATION
sector-vs-market = DEFERRED_DATA_FOUNDATION
```

Rank, BUY Quality, and runtime opportunity score must not be relabeled as
sector-relative strength.

## Legacy Inventory Summary

Machine-readable inventory:

```text
reports/phase_reports/phase30_o_legacy_inventory.json
```

Counts:

```text
KEEP = 11
MIGRATE = 9
DEPRECATE_DURING_MIGRATION = 6
REMOVE_AFTER_MIGRATION = 5
```

## Legacy Removal Targets

Removal targets after migration include shadow proposal aliases, old duplicated
BUY Quality interpretation, old momentum trajectory BUY_WAIT authority,
legacy-compatible PM fallback surfaces, shadow-only production blockers,
obsolete config keys, obsolete schema fields, obsolete tests, and obsolete
durable documentation sections.

## Old BUY Quality

KEEP: source summaries, accepted-generation integrity, execution feasibility,
and portfolio-fit evidence where authority remains distinct.

MIGRATE: relative opportunity, market context interpretation, and momentum
trajectory interpretation into SI Expected Edge / CQ / BUY_WAIT semantics.

REMOVE_AFTER_MIGRATION: duplicated CQ/Risk penalties and old final BUY Quality
decision semantics after consumer references reach zero.

## runtime_opportunity_score

KEEP as uncalibrated relative model score and opportunity ranking evidence.

MIGRATE consumers that treat it as Expected Edge evidence into SI
`expected_edge`. REMOVE any consumer that treats it as calibrated expected
return or absolute economic threshold.

## Old Momentum / Trajectory Logic

Momentum features remain valid inputs. Old trajectory-as-BUY_WAIT interpretation
migrates to SI CQ / BUY_WAIT semantics. Duplicate momentum penalties across
BUY Quality and SI must be removed after migration.

## Old HOLD / SELL Interpretation

Existing PM remains Action Authority, but PM evidence consumption migrates to SI
CQ/Risk/Profit Protection/campaign context. Old HOLD-as-not-SELL interpretation
and one-factor SELL interpretations are retirement targets.

## Shadow Logic

```text
strategy_intelligence_interpretation = PROMOTE_TO_PRODUCTION_EVIDENCE
proposed_decision_if_authorized = REMOVE
shadow markers = KEEP_AS_OBSERVABILITY_ONLY during migration, then replace
shadow comparison engine = KEEP_AS_OBSERVABILITY_ONLY during migration only
shadow consumer path = REMOVE
```

## Config Retirement

Inventory covers:

- `configs/strategy/regime_event_position_management.json`
- `configs/strategy/market_context.json`
- `configs/strategy/portfolio_policy.json`
- `configs/strategy/position_sizing.json`
- `configs/runtime_v2/capital_deployment.json`

Keys still owned by PC/PM/Sizing/Safety are KEEP. Duplicated Strategy
interpretation thresholds or obsolete migration toggles are removal targets
after consumer zero.

## Schema Retirement

Retirement targets include obsolete shadow aliases and replaced final-action
interpretation fields. Invariant evidence fields such as PIT boundary,
provenance, current/campaign identity, valuation/basis, and final decision trace
are KEEP.

## Adapter Retirement

Compatibility adapters may remain during migration only. After Production SI
consumers are active, adapters whose only purpose is old-to-new shadow mapping
or silent legacy fallback must be removed.

## Test Retirement

KEEP invariant tests for BUY/SELL independence, BUY_WAIT, ADD, REENTRY, HOLD,
REDUCE, EXIT, campaign identity, valuation/basis, leakage firewall, and
fail-closed behavior.

MIGRATE tests that freeze old BUY Quality or PM interpretation into SI consumer
contract tests. REMOVE tests that assert obsolete duplicate paths.

## Documentation Retirement

Historical phase reports remain as records. Durable Architecture must converge
to the current authority path and must not preserve superseded diagrams,
fallback descriptions, or shadow-only notes as current Production authority.

## Duplicate Penalty Audit

Risk families audited: volatility, microstructure, low price, liquidity,
regime, reversal, and event uncertainty.

Momentum families audited: 1D/3D/5D/10D/20D/60D momentum, trajectory,
acceleration/deceleration, and model score.

Result: duplicate evaluation is acceptable only when layers have distinct
responsibility. Same evidence cannot be penalized as Strategy quality, sizing
haircut, and Safety block without separate authority semantics.

## Fail-Closed Migration Behavior

No silent legacy fallback. Missing mandatory SI evidence causes explicit
BUY_WAIT/no-action/review/block according to action semantics. BUY-side evidence
failure cannot stop SELL-side decisions. Runtime Planning maps only authorized
upstream decisions.

## BUY / SELL Independence

BUY and SELL evidence requirements are separated by consumer. SELL / REDUCE /
EXIT must remain evaluable when BUY-side SI evidence is missing, malformed, or
BUY_WAIT.

## Migration Stages

1. Stage 0 Contract Freeze: docs/inventory/map complete; no behavior change.
2. Stage 1 Production Evidence Connection: consumers can read SI evidence while
   actions remain unchanged; lineage and no-fallback proven.
3. Stage 2 BUY-Side Migration: BUY_NEW/BUY_WAIT/REENTRY use SI evidence; old
   duplicated BUY Quality interpretations marked for retirement.
4. Stage 3 Existing-Position Migration: PM consumes SI HOLD/ADD/Profit
   Protection/REDUCE/EXIT evidence while retaining Action Authority.
5. Stage 4 Legacy Retirement: replaced consumers/fallbacks/config/schema/tests
   removed after reference count zero.
6. Stage 5 10BD Entry Gate: focused regression and user-operated fresh 10BD
   Historical readiness.

## Legacy Retirement Completion Gate

```text
new consumer implemented
-> E2E connection proven
-> focused regression PASS
-> Production authority migration
-> old consumer reference count = 0
-> old fallback reference count = 0
-> remove old implementation
-> remove obsolete config/schema/test/docs
-> post-removal regression PASS
```

## Final Production Authority Count

```text
ONE PRODUCTION STRATEGY AUTHORITY PATH
```

## New AI / Model

```text
NEW_AI_CREATED = NO
PRODUCTION_MODEL_RETRAINED = NO
ACCEPTED_GENERATION_CHANGED = NO
```

## Leakage Firewall

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
```

## Production Behavior

```text
ACTUAL_TRADING_BEHAVIOR_CHANGED = NO
```

## Implementation Authorization

```text
NO IMPLEMENTATION AUTHORIZED BY PHASE30_O
```

## 10BD Entry Gate

10BD fresh Historical may start only after Production SI connection is complete,
replaced legacy logic is removed, duplicate Production authority is absent,
silent fallback is absent, lifecycle and valuation/basis regressions pass, and
multi-day BUY_NEW / BUY_WAIT / ADD / REENTRY / HOLD / REDUCE / EXIT /
NO_ACTION coverage passes.

10BD result must not be used for post-hoc threshold tuning.

## Recommended Next Task

```text
Phase30-P — Strategy Intelligence Production Consumer Migration Implementation and Legacy Retirement
```
