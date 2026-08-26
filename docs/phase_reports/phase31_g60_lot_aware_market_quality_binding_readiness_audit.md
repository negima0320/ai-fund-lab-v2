# Phase31-G60 — Lot-Aware Compatibility & Market Quality Binding Readiness Audit

## Primary Judgment

PHASE31_G60_AUTHORITATIVE_ACTIVATION_BLOCKED_BY_LOT_AWARE_PRIORITY_INVERSION

Do not proceed to multi-allocation authoritative activation / Position Sizing
binding yet.

## Scope

This was a READ-ONLY audit. No Strategy implementation, Position Sizing
consumer, Runtime trading behavior, fixture, fresh run, resume, replay, or long
Historical execution was performed.

G59 `canonical_multi_allocation_deployment_set.v1` remained
`SHADOW_NON_AUTHORITATIVE`.

## Target Evidence

Primary source run:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260822T174358377089Z`

Lot-aware compatibility window:

- `2022-10-03` through `2022-10-19`
- Source artifacts: `strategy_eod_shadow/portfolio_construction.json`,
  `strategy_eod_shadow/position_sizing.json`,
  `strategy_eod_shadow/portfolio_policy.json`,
  `strategy_eod_shadow/market_context.json`

Market Quality / Risk Pacing window:

- `2023-03-23` through `2023-07-28`
- Source artifacts: `strategy_eod_shadow/market_context.json`,
  `strategy_eod_shadow/portfolio_policy.json`

## Method

For lot-aware compatibility, G60 applied current G56/G59 semantics in memory to
existing PIT artifacts and projected each shadow security allocation into same-
date Position Sizing constraints:

- portfolio value
- reference price
- trading unit / 100-share lot basis
- current weight
- single-security cap
- safety / effective maximum position weight

The projection did not write artifacts and did not create orders.

For Market Quality, G60 reconstructed current Market Quality / Risk Pacing from
same-date PIT market metrics and saved threshold policy, following the G36/G58
READ-ONLY precedent. Historical PnL and later returns were not used.

## A. Lot-Aware Compatibility Result

Window summary:

- Dates evaluated: `12`
- Shadow security allocation rows: `126`
- Executable after lot conversion: `31`
- Zero quantity after lot conversion: `95`
- Dates with at least one executable allocation: `12`
- Dates with multiple executable allocations: `11`
- Dates where all shadow allocations collapsed to zero: `0`
- Capital conservation status: `PASS` on `12 / 12`
- Cap violations: `0`
- PS behavior change count: `0`
- Runtime order change count: `0`
- Future input count: `0`
- Historical outcome input count: `0`

Opportunity type coverage:

- `NEW_BUY`: `121` allocation rows
- `ADD`: `5` allocation rows
- `REENTRY`: `0` observed rows

ADD lot compatibility:

- ADD rows: `5`
- ADD executable rows: `5`
- ADD zero rows: `0`

REENTRY lot compatibility:

- No REENTRY rows were observed in the audited PIT window, so real-PIT REENTRY
  lot compatibility remains not observed.

## A1. Blocking Finding — Priority Inversion After Lot Conversion

The key blocker is not total zero-collapse. It is priority inversion.

In all `12 / 12` audited dates, at least one top-3 G59 shadow allocation became
zero quantity after 100-share lot conversion, while a lower-ranked allocation
remained executable.

Examples:

| Date | Top allocation zeroed by lot | First executable lower rank |
| --- | --- | --- |
| `2022-10-03` | rank 1 `58200`, rank 2 `41920` | rank 3 `76470` |
| `2022-10-05` | rank 1 `39060`, rank 3 `58200` | rank 2 `76920` |
| `2022-10-07` | rank 1 `39060`, rank 3 `36000` | rank 2 `76920` |
| `2022-10-17` | rank 1 `39060`, rank 2 `78780`, rank 3 `92270` | rank 5 `17570` |
| `2022-10-19` | rank 1 `39060`, rank 3 `78780` | rank 2 `76920` |

Representative cause:

- `39060` repeatedly had shadow allocation weight around `0.021` to `0.037`,
  but one 100-share lot required roughly `0.875` to `0.890` portfolio weight in
  the audited account size and price basis.
- Lower-priced symbols could convert to one lot while higher-ranked candidates
  could not.

This means the G59 evidence is not yet ready to bind directly into Position
Sizing. A production binding would need an explicit lot-aware compatibility
layer that preserves relative capital priority after discrete lot conversion,
or explicitly terminalizes / residualizes unexecutable allocations before
passing them to Position Sizing.

## A2. Lot-Aware Acceptance

EXECUTABLE_MULTI_SECURITY_AFTER_LOT = YES

VALID_ALLOCATION_TO_ZERO_QUANTITY_COLLAPSE = NO at daily aggregate level

VALID_ALLOCATION_TO_ZERO_QUANTITY_ROW_RATE = `95 / 126 = 75.40%`

STRONGER_EDGE_PRIORITY_AFTER_LOT = NOT_PRESERVED

CAPITAL_CONSERVATION = PASS

ADD_REENTRY_LOT_COMPATIBILITY = PARTIAL

PS_BEHAVIOR_CHANGE_COUNT = 0

RUNTIME_ORDER_CHANGE_COUNT = 0

## B. Market Quality Classification Sanity Result

Window:

- `2023-03-23` through `2023-07-28`
- Dates evaluated: `88`

Market Quality distribution:

- `RECOVERY_CONFIRMATION_INCOMPLETE`: `24`
- `SHORT_TERM_BREADTH_BREAKDOWN`: `20`
- `HEALTHY_EXPANSION`: `19`
- `CONFLICTED_MARKET_STRUCTURE`: `17`
- `SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH`: `7`
- `HEALTHY_RECOVERY`: `1`

Risk Pacing distribution:

- `CAUTIOUS_DEPLOYMENT`: `44`
- `GRADUAL_REDEPLOYMENT`: `24`
- `NORMAL_DEPLOYMENT`: `20`

Transition count:

- `39`

Normal deployment dates included:

- `2023-04-12`
- `2023-04-14` through `2023-04-20`
- `2023-04-28`
- `2023-05-08` through `2023-05-10`
- `2023-06-14` through `2023-06-22`
- `2023-06-30`
- `2023-07-03` through `2023-07-04`

Gradual redeployment dates included:

- `2023-03-24`
- `2023-03-27`
- `2023-03-29`
- `2023-03-31`
- `2023-04-03`
- `2023-04-13`
- `2023-04-21`
- `2023-04-24`
- multiple June and late-July recovery dates

## B1. Market Quality Interpretation

Market Quality did not collapse into a permanent cautious state.

The reconstructed PIT timeline shows:

- healthy market evidence can map to `NORMAL_DEPLOYMENT`
- recovery-incomplete evidence can map to `GRADUAL_REDEPLOYMENT`
- weak / conflicted evidence can map to `CAUTIOUS_DEPLOYMENT`
- transitions occur in both directions

This is sufficient architecture sanity for Market Quality as a capital pacing
sensor. It is not behaving as a downside-only defensive signal.

## B2. Market Quality Acceptance

MARKET_QUALITY_UPSIDE_SENSITIVITY = PRESENT

MARKET_IMPROVEMENT_CAN_INCREASE_DEPLOYMENT = YES

PERMANENT_CAUTIOUS_COLLAPSE = NO

MARKET_QUALITY_DOWNSIDE_ONLY_SENSOR = NO

PROFIT_ENGINE_SUPPRESSION_RISK = ACCEPTABLE_FOR_BINDING

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_STRATEGY_INPUT_COUNT = 0

## Overall Acceptance

Lot-aware readiness is not accepted for authoritative binding.

Market Quality binding readiness is accepted.

Overall:

AUTHORITATIVE_ACTIVATION_READY = NO

ROOT_BLOCKER =
LOT_AWARE_PRIORITY_INVERSION_AFTER_DISCRETE_100_SHARE_CONVERSION

## Required Constraints

G59_SHADOW_AUTHORITATIVE = NO

POSITION_SIZING_CONNECTED = NO

RUNTIME_TRADING_BEHAVIOR_CHANGED = NO

CANDIDATE_RANKING_CHANGED = NO

CANDIDATE_ELIGIBILITY_CHANGED = NO

MARKET_QUALITY_HARD_GATE_CREATED = NO

THRESHOLD_OR_WEIGHT_TUNING = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

## Next

Do not proceed to authoritative activation.

Next task should design and validate a lot-aware allocation-to-sizing
compatibility layer before any production binding. The layer should preserve
G59 relative priority through discrete lot conversion, handle residual capital
explicitly, and remain non-authoritative until it passes real-PIT sanity.
