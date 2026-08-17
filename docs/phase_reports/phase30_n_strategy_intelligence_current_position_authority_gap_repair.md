# Phase30-N — Strategy Intelligence Current Position Authority Gap Repair

Task ID: `Phase30-N`

## Primary Judgment

```text
PHASE30_N_CURRENT_POSITION_CAMPAIGN_AUTHORITY_REPAIRED_MIGRATION_DESIGN_READY
```

Phase30-N repaired the Phase30-M blocker:

```text
CURRENT_POSITION_AUTHORITY_PARTIAL
```

Strategy Intelligence now exposes canonical campaign identity, opened date, and
campaign status in `lifecycle_context` using the existing Production-common
campaign authority. Trading behavior and Production Action Authority were not
changed.

## Root Cause

Phase30-M found that held-position market/current state was available, but
Strategy Intelligence did not first-class join the canonical campaign authority.
The artifact could see quantity, average price, market value, basis, and
PIT-safe observed profit state, but could not always identify:

- `position_campaign_id`
- `campaign_opened_date`
- exact campaign status

The remaining 179 partial rows were all same-day EXIT / SELL_EXIT cases. The
canonical campaign had already been closed by that day's EXIT event in
`positions/position_campaigns.json`, so active/open-only matching missed the
correct campaign identity.

## Canonical Campaign Authority

Canonical artifact:

```text
daily/<business_date>/positions/position_campaigns.json
```

Owner:

```text
Runtime position campaign observability / campaign authority
```

Owned fields:

- `position_campaign_id`
- campaign symbol
- `opened_business_date`
- `closed_business_date`
- `campaign_status`
- BUY / ADD / SELL / EXIT event history
- campaign current quantity and realized/unrealized campaign state

No new campaign ledger was created.

## Current Authority

Current-position source:

```text
strategy/position_management.json
  runtime_current_position_adapter
  upstream_artifacts.position_lifecycle.summary.positions
```

Underlying source:

```text
.runtime/persistent_ledger/state.json
```

Owned fields:

- current quantity
- average price
- current market value
- current price
- quantity basis
- valuation price basis
- valuation as-of / valuation authority

## Join Design

Strategy Intelligence joins:

```text
Current position state
  + canonical active/open campaign by symbol
```

For EXIT day only, if the canonical campaign is closed by a same-business-day
SELL/EXIT event, Strategy Intelligence may use that same-day closed campaign as
EXIT-day lifecycle context.

It must not treat that closed campaign as an open current holding on later
days.

Conflict behavior:

```text
CAMPAIGN_AUTHORITY_CONFLICT
```

is raised if multiple active canonical campaigns exist for the same symbol.

## Current Position Authority

```text
CURRENT_POSITION_AUTHORITY_COMPLETE
```

Validation boundary:

```text
Run: runtime-test-historical-extended-smoke-20260815T061857447380Z
Clean period: 2022-08-10 -> 2023-10-26
Business days: 299
Symbol rows: 15,040
```

Coverage:

```text
held rows: 1,962
campaign ID complete count: 1,962
opened-date complete count: 1,962
campaign-status complete count: 1,962
missing count: 0
```

## BUY_NEW -> HOLD

Campaign identity is created by the canonical campaign authority after BUY_NEW
execution and remains stable into HOLD.

Example from validation:

```text
94320:
2022-08-10 BUY_NEW -> campaign pc-...-94320-0001 opened 2022-08-10
2022-08-15 HOLD    -> same campaign pc-...-94320-0001
```

## ADD

ADD preserves canonical campaign identity. ADD does not create a fake new
campaign.

Validation:

```text
ADD / BUY_ADD cases: 516
ADD interpreted as HOLD: 0
ADD campaign continuity regression: PASS
```

## REDUCE / Partial SELL

REDUCE / partial SELL preserves canonical campaign identity for the remaining
position.

Validation:

```text
REDUCE cases: 285
REDUCE_INTERPRETED_AS_HOLD = 0
```

Quantity changes remain owned by Current / Runtime / Ledger. Strategy
Intelligence only references the campaign identity and current state.

## EXIT

EXIT closes the campaign according to canonical campaign authority.

Phase30-N fixed the EXIT-day boundary by recognizing same-day closed campaigns
as valid EXIT-day lifecycle context.

Validation:

```text
EXIT cases: 179
EXIT_INTERPRETED_AS_HOLD = 0
EXIT-day campaign identity complete count: 179
```

Next-day no-position rows do not keep the closed campaign as current holding
context.

## REENTRY

REENTRY follows canonical campaign authority. When canonical campaign evidence
creates a new open campaign, Strategy Intelligence uses the new campaign ID and
opened date.

Prior closed campaign MFE/giveback is not inherited as current-campaign state.

Example:

```text
23880:
2022-08-10 BUY_NEW -> pc-...-23880-0001
2022-08-12 EXIT    -> pc-...-23880-0001 CLOSED
2022-08-19 REENTRY -> pc-...-23880-0002 OPEN
```

## Profit Protection

Profit Protection remains campaign-scoped.

Observed MFE/giveback used in validation was derived only from prior/current
PIT snapshots for the same canonical campaign ID. The derivation resets when a
new REENTRY campaign ID appears.

No future peak, future MFE, final campaign outcome, or Historical PnL was used.

## Production Behavior

```text
ACTUAL_TRADING_BEHAVIOR_CHANGED = NO
PRODUCTION_BEHAVIOR_EQUIVALENCE = PASS
```

Hash comparison before/after validation confirmed no mutation to:

- `strategy/position_management.json`
- `strategy/portfolio_construction.json`
- `strategy/position_sizing.json`
- `strategy/runtime_planning.json`

## New AI

```text
NEW_AI_CREATED = NO
PRODUCTION_MODEL_RETRAINED = NO
ACCEPTED_GENERATION_CHANGED = NO
```

## Leakage Firewall

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
```

## Duplicate Authority

```text
DUPLICATE_CAMPAIGN_AUTHORITY_CREATED = NO
```

Strategy Intelligence references canonical campaign authority. It does not
create `strategy_intelligence_campaign_id` or any duplicate identity.

## Legacy Fallback

```text
LEGACY_HEURISTIC_CAMPAIGN_FALLBACK = REMOVED_FROM_COMPLETENESS_PATH
```

Lifecycle completeness no longer depends on runtime-current reference,
position id, source execution id, or first-seen sampled date as a campaign
identity substitute.

If canonical campaign evidence is missing, lifecycle context reports missing
authority rather than silently fabricating identity.

## BUY / SELL Independence

```text
BUY_SELL_INDEPENDENCE = PASS
```

BUY_WAIT + SELL_EXIT cases remain PM EXIT:

```text
BUY_WAIT_AS_BUY_NEW = 0
EXIT_AS_HOLD = 0
```

## Valuation / Basis Regression

```text
VALUATION_BASIS_REGRESSION = PASS
```

Campaign identity repair did not alter:

- quantity basis
- valuation price basis
- valuation authority
- Cash
- Equity
- Ledger

## Multi-Day Lifecycle

```text
MULTI_DAY_LIFECYCLE = PASS
```

Real clean-run validation covered:

- BUY_NEW -> HOLD
- ADD -> HOLD
- REDUCE / partial SELL continuity
- EXIT closure
- later REENTRY with new canonical campaign identity

## Idempotency

```text
IDEMPOTENCY = PASS
```

Repeated generation from identical PIT Current + campaign state produced
identical semantic payload hashes.

## Tests

```text
tests/strategy/test_phase30_j_strategy_intelligence.py
tests/strategy/test_phase30_l_strategy_intelligence_gap_repair.py
tests/strategy/test_phase30_n_strategy_intelligence_campaign_authority.py
tests/runtime_v2/test_phase22_p_strategy_shadow_wiring.py

32 passed
```

Compile check:

```text
compileall PASS
```

## Long Historical

```text
LONG_HISTORICAL_EXECUTED_BY_CODEX = NO
```

No 977BD, 100BD, 4-year, long resume, repair, close, or Historical execution
was run.

## Production Authority

```text
SHADOW_OUTPUT_CONNECTED_TO_PRODUCTION_ACTION_AUTHORITY = NO
PRODUCTION_AUTHORITY_MIGRATION_AUTHORIZED = NO
```

## Critical Blocker

```text
CRITICAL_BLOCKER_FOR_PRODUCTION_MIGRATION_DESIGN = NO
```

## Migration Readiness

```text
PRODUCTION_MIGRATION_DESIGN_READY
```

## Recommended Next Task

```text
Phase30-O — Strategy Intelligence Production Authority Migration and Legacy Retirement Design
```
