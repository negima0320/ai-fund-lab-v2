# Phase30-M — Strategy Intelligence Shadow Lifecycle Validation

Task ID: `Phase30-M`

## Primary Judgment

```text
PHASE30_M_STRATEGY_INTELLIGENCE_SHADOW_LIFECYCLE_VALIDATED_CURRENT_POSITION_AUTHORITY_PARTIAL_MIGRATION_DESIGN_BLOCKED
```

Phase30-M validated the Phase30-L lifecycle-specific Strategy Intelligence
shadow semantics against broad real Production-common PIT evidence.

Lifecycle interpretation quality is broadly PASS. The remaining blocker is not
BUY_WAIT / ADD / REDUCE / EXIT contradiction. The blocker is Current / campaign
state authority completeness for production migration design.

## Validation Boundary

Source run inspected read-only:

```text
runtime-test-historical-extended-smoke-20260815T061857447380Z
```

Clean period:

```text
2022-08-10 -> 2023-10-26
```

Excluded:

```text
2023-10-27 failed valuation candidate
```

Sample:

```text
sampled business days: 299
symbol rows: 15,040
current campaign refs observed: 127
```

Generated validation-only artifacts:

```text
reports/phase_reports/phase30_m/generated_strategy_intelligence/<date>/strategy_intelligence.json
reports/phase_reports/phase30_m/validation_evidence.json
reports/phase_reports/phase30_m_strategy_intelligence_shadow_lifecycle_validation.json
```

The source Historical run directory was not mutated.

## Production Behavior

```text
ACTUAL_TRADING_BEHAVIOR_CHANGED = NO
PRODUCTION_BEHAVIOR_EQUIVALENCE = PASS
```

Hash comparison before and after validation confirmed no mutation to:

- `strategy/runtime_planning.json`
- `strategy/portfolio_construction.json`
- `strategy/position_sizing.json`
- `strategy/position_management.json`

## New AI / Model

```text
NEW_AI_CREATED = NO
PRODUCTION_MODEL_RETRAINED = NO
ACCEPTED_GENERATION_CHANGED = NO
```

No model was trained, replaced, or re-bound.

## Leakage Firewall

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
```

Observed MFE / giveback used in validation was derived only from current and
prior daily position snapshots up to each decision date. No future peak, future
return, final campaign outcome, Historical PnL, or audit/test result was used
as Strategy input.

## Current Position Authority

```text
CURRENT_POSITION_AUTHORITY_PARTIAL
```

Production-common evidence for held positions is available from:

```text
strategy/position_management.json
  runtime_current_position_adapter
  upstream_artifacts.position_lifecycle.summary.positions

positions/position_campaigns.json
  position_campaigns
```

Validated current-position fields:

- quantity: available
- average price: available
- current market value: available
- valuation basis / quantity basis: available
- observed embedded return: derivable PIT-safely
- observed MFE / giveback: derivable from prior/current snapshots

Gap:

- campaign identity / opened date is not consistently exposed through
  `strategy_intelligence.lifecycle_context`.
- 179 current rows had 5/6 field completeness because `position_campaign_id`
  was missing from the available joined current-position evidence.

This is sufficient for shadow HOLD semantic validation, but not sufficient to
start Production Authority Migration Design cleanly.

## Lifecycle Coverage

Real lifecycle cases observed:

```text
BUY_NEW: 267
BUY_WAIT: 3,348
ADD / BUY_ADD: 516
REENTRY semantic cases: 3,030
planned REENTRY evidence states: 105
HOLD: 982
REDUCE: 285
EXIT: 179
NO_ACTION / NO_ORDER: 9,216
Profit Protection OBSERVED/PARTIAL: 1,962
```

Interpretation state counts:

```text
ADD_WORTHINESS_EVIDENCE_SHADOW: 516
BUY_NEW_CANDIDATE_EVIDENCE_SHADOW: 162
BUY_WAIT_CONTEXT_SHADOW: 2,936
HOLD_WORTHINESS_OBSERVED_SHADOW: 982
INSUFFICIENT_EVIDENCE_SHADOW: 9,875
PM_EXIT_EVIDENCE_OBSERVED_SHADOW: 179
PM_REDUCE_EVIDENCE_OBSERVED_SHADOW: 285
REENTRY_EVIDENCE_SHADOW: 105
```

## BUY_NEW

```text
BUY_NEW = PASS
```

Real BUY_NEW rows materialized eligibility, CQ, Downside Risk, Relative
Strength, uncalibrated Expected Edge, lifecycle interpretation, and provenance.
Pure BUY_NEW rows did not collapse into HOLD, ADD, or REDUCE/EXIT semantics.

## BUY_WAIT

```text
BUY_WAIT = PASS
BUY_WAIT_LIFECYCLE_INTERPRETATION = PASS
```

BUY_WAIT context was preserved and did not become BUY_NEW:

```text
BUY_WAIT interpreted as BUY_NEW: 0
```

BUY_WAIT remained non-Pending and re-evaluable. BUY_WAIT + SELL_EXIT cases were
preserved as PM EXIT interpretation, proving SELL independence.

## ADD

```text
ADD = PASS
```

ADD / BUY_ADD rows were interpreted as incremental ADD-worthiness:

```text
ADD interpreted as HOLD: 0
```

`expected_edge.incremental_edge_for_add` remained descriptive and
`not_action_authority`.

## REENTRY

```text
REENTRY = PASS
```

Semantic REENTRY rows were preserved. Planned REENTRY evidence emitted:

```text
REENTRY_EVIDENCE_SHADOW
```

No blanket REENTRY ban was introduced and no REENTRY was collapsed into generic
BUY_NEW where the semantic REENTRY context was active.

## HOLD

```text
HOLD = PASS_WITH_CURRENT_AUTHORITY_LIMITATION
```

Real PM HOLD rows emitted:

```text
HOLD_WORTHINESS_OBSERVED_SHADOW
```

Observed HOLD rows included quantity, average price, current market value,
embedded return, observed MFE/giveback, CQ, Downside Risk, regime context, and
profit-protection context.

The limitation is not HOLD semantic contradiction. The limitation is incomplete
first-class campaign identity exposure in Strategy Intelligence.

## REDUCE

```text
REDUCE = PASS
REDUCE_INTERPRETED_AS_HOLD = 0
```

REDUCE rows preserved current PM REDUCE authority:

```text
PM_REDUCE_EVIDENCE_OBSERVED_SHADOW
```

## EXIT

```text
EXIT = PASS
EXIT_INTERPRETED_AS_HOLD = 0
```

EXIT rows preserved current PM EXIT authority:

```text
PM_EXIT_EVIDENCE_OBSERVED_SHADOW
```

BUY-side CQ did not overwrite PM EXIT authority.

## Profit Protection

```text
PROFIT_PROTECTION = PASS_WITH_CURRENT_AUTHORITY_LIMITATION
```

Profit Protection evidence is semantically consistent for HOLD, REDUCE, and
EXIT. It uses observed embedded return, observed high-water/MFE, observed
giveback, CQ deterioration, downside-risk rise, and regime context.

No fixed profit threshold was introduced.

Limitation: observed MFE/giveback is derivable from PIT snapshots, but is not
yet a first-class persistent Strategy Intelligence campaign-state authority.

## Daily Transition

```text
DAILY_TRANSITION = PASS
```

Multi-day transitions were observed across real campaigns. Sample symbols in
the validation evidence include:

```text
23230
23700
23880
36640
54010
66190
67310
70800
```

The validation covers BUY_NEW, HOLD, ADD, deterioration, REDUCE, EXIT, BUY_WAIT
+ SELL_EXIT, REENTRY, and NO_ACTION/NO_ORDER paths across multiple campaigns.

## CQ Transition

```text
CQ_TRANSITION = PASS
```

Real PIT feature changes produced semantic CQ changes across trend,
persistence, acceleration/deceleration, exhaustion, participation, reversal
risk, and volatility risk. No future outcome was used to judge whether the
changes were profitable.

## Relative Strength

```text
RELATIVE_STRENGTH = PARTIALLY_CONNECTED
```

All 15,040 rows connected stock-vs-market PIT relative strength:

```text
technical_features.price_momentum_return_5d / 20d
market_context.metrics.return_5d_equal_weight / return_20d_equal_weight
```

Still missing:

```text
stock_vs_sector_relative_strength_authority
sector_vs_market_symbol_join_authority
```

No fake sector mapping, opportunity-rank substitute, runtime-score substitute,
or future-return substitute was used.

## Expected Edge

```text
calibration_status = UNCALIBRATED
research_only = true
shadow_only = true
```

Expected Edge was not called expected return.

Missing components:

- calibrated payoff distribution
- calibrated expected-return units
- formal turnover consideration model
- formal opportunity-cost calibration

## Event Coverage

```text
EVENT_COVERAGE = PASS_REAL_SAMPLE_AVAILABLE_ONLY
```

The broad real sample materialized event uncertainty as `MANAGEABLE` for all
rows because the inspected real `corporate_event.json` artifacts had available
coverage. Missing-event-is-not-safe behavior remains governed by the existing
contract and focused regression, but unavailable/incomplete event coverage was
not observed in this real clean sample.

## Production Behavior Equivalence

```text
PRODUCTION_BEHAVIOR_EQUIVALENCE = PASS
```

No candidate, BUY Quality, Portfolio Construction, Position Sizing, Position
Management, Runtime Planning, Pending, Submit, Execution, Safety, valuation, or
basis artifact in the source run was changed.

## BUY / SELL Independence

```text
BUY_SELL_INDEPENDENCE = PASS
```

Real BUY_WAIT + SELL_EXIT cases were preserved as PM EXIT:

```text
BUY_WAIT + SELL_EXIT interpreted as PM_EXIT_EVIDENCE_OBSERVED_SHADOW
```

SELL / REDUCE / EXIT did not depend on BUY state.

## NO_ACTION

```text
NO_ACTION = PASS
```

NO_ACTION / NO_ORDER rows materialized Strategy Intelligence normally and did
not break runtime continuity. Cash retention remains a valid result.

## Missingness

```text
MISSINGNESS = PASS_WITH_KNOWN_GAPS
```

No silent fallback was found for:

- missing -> zero
- missing -> neutral
- missing -> safe

Sector relative strength remains an explicit data foundation gap. Current
campaign-state identity remains an explicit authority gap.

## Idempotency

```text
IDEMPOTENCY = PASS
```

Repeated generation from identical PIT inputs and identical lifecycle state
produced identical semantic payload hashes.

## Closed Contract Regression

```text
CLOSED_CONTRACT_REGRESSION = PASS
```

Focused regression:

```text
tests/strategy/test_phase30_j_strategy_intelligence.py
tests/strategy/test_phase30_l_strategy_intelligence_gap_repair.py
tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py

27 passed
```

Compile check:

```text
compileall PASS
```

Closed contracts preserved:

- BUY / SELL independence
- BUY_WAIT non-Pending
- ADD/HOLD separation
- REENTRY semantics
- lot-aware sizing unchanged
- residual recycling unchanged
- Strategy/Safety cap separation unchanged
- REDUCE lot semantics unchanged
- NO_ACTION continuity
- valuation/basis untouched
- Current/Ledger read-only
- Safety non-optimization

## Production Authority

```text
SHADOW_OUTPUT_CONNECTED_TO_PRODUCTION_ACTION_AUTHORITY = NO
PRODUCTION_AUTHORITY_MIGRATION_AUTHORIZED = NO
```

## Long Historical

```text
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

## Critical Blocker

```text
CRITICAL_BLOCKER_FOR_PRODUCTION_MIGRATION_DESIGN = YES
```

Blocker:

```text
CURRENT_POSITION_AUTHORITY_PARTIAL
```

The lifecycle semantics are stable enough, but Production Migration Design
should not start until Strategy Intelligence exposes complete current/campaign
state authority as first-class schema.

## Migration Readiness

```text
PRODUCTION_MIGRATION_DESIGN_BLOCKED
```

## Recommended Next Task

```text
Phase30-N — Strategy Intelligence Current Position Authority Gap Repair
```
