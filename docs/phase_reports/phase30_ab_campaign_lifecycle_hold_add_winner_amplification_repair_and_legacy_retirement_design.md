# Phase30-AB - Campaign Lifecycle / HOLD-ADD Winner Amplification Repair and Legacy Retirement Design

Task ID: `Phase30-AB`

Boundary:

```text
DESIGN_ONLY
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AB
NO IMPLEMENTATION AUTHORIZED BY_PHASE30_AB
NO_NEW_AI
NO_MODEL_RETRAINING
NO_THRESHOLD_TUNING
NO_EXPECTED_EDGE_CALIBRATION
NO_ENTRY_ADMISSION_CHANGE
NO_REENTRY_CHANGE
NO_SELL_REDUCE_EXIT_REDESIGN
NO_HISTORICAL_OUTCOME_FIT
```

## Primary Judgment

```text
PHASE30_AB_CANONICAL_CAMPAIGN_LIFECYCLE_HOLD_ADD_REPAIR_DESIGN_COMPLETE
PHASE30_AC_IMPLEMENTATION_READY = YES
ONE_CANONICAL_PRODUCTION_PATH_DESIGNED = YES
DUPLICATE_CAMPAIGN_AUTHORITY_DESIGN = NO
```

Phase30-AA found a Production pre-action utilization gap, not a need for new
data, new AI, or parameter tuning. The repair should connect existing campaign
lifecycle and observed-position state into the single Production path so HOLD,
Profit Protection, ADD, and winner amplification can use existing PIT evidence.

## Canonical Campaign Authority

Canonical campaign truth remains:

```text
positions/position_campaigns.json
```

This artifact must be materialized for the pre-action Production decision path
before Strategy Intelligence, PM, Portfolio Construction, and Position Sizing
consume it. It is not replaced by a second campaign ledger.

Required open-campaign fields:

- `position_campaign_id`
- `symbol`
- `campaign_status`
- `opened_business_date`
- `campaign_age_business_days`
- `entry_thesis_state`
- `current_quantity`
- `average_price`
- `current_valuation_price`
- `current_campaign_relative_return`
- `observed_campaign_mfe`
- `observed_giveback`
- `buy_history_summary`
- `add_history_summary`
- `reduce_history_summary`
- `sell_history_summary`
- source references for Current, Ledger, PIT price, and prior campaign state
- temporal safety flags, including `future_information_used = false`

`positions/position_campaigns.json` owns campaign identity, opened date, and
ADD/REDUCE history. Strategy Intelligence consumes these facts and may derive
interpretation evidence, but it must not create or persist an independent
campaign identity.

## Pre-action PIT Connection

The pre-action path must use state knowable at the business-date decision time:

```text
prior completed campaign lifecycle state
+ Ledger executions strictly before the current decision cut
+ Current position / valuation state available at decision time
+ PIT prices observed no later than the decision-date market-data boundary
-> positions/position_campaigns.json pre-action decision snapshot
-> strategy/strategy_intelligence.json
-> PM / PC / PS / Runtime Planning
```

Forbidden inputs:

- same-day future executions
- EOD-only reconstruction first known after decisions
- future MFE / MAE
- future giveback
- final campaign outcome
- Historical run result or audit judgment

EOD shadow evidence may be used only to verify that the same facts were
recoverable from Production authorities. It must not be copied into pre-action
Strategy artifacts.

## HOLD Design

HOLD remains an active PM decision. Strategy Intelligence provides evidence; PM
remains Action Authority.

The repaired PM consumer should be able to inspect structured HOLD-worthiness
evidence:

- campaign age and opened date
- current campaign-relative return
- embedded/current return
- observed campaign MFE
- observed giveback from observed peak
- Continuation Quality state and deterioration
- Downside Risk state and risk rise
- Relative Strength
- ADD/REDUCE history
- Profit Protection evidence

HOLD means current PIT evidence still justifies keeping capital deployed. It is
not merely absence of an EXIT trigger. Missing canonical campaign authority for
an open position must be explicit review / insufficient evidence, not silent
HOLD inertia.

## ADD / Winner Amplification Design

The design preserves:

```text
HOLD-worthy != ADD-worthy
```

ADD must answer whether incremental capital is justified now. The ADD evidence
contract should combine existing data:

- incremental Continuation Quality
- current Downside Risk
- Relative Strength
- campaign maturity
- current campaign-relative return
- observed MFE / giveback
- prior ADD count and ADD spacing/history
- REDUCE history
- current exposure
- opportunity cost versus BUY_NEW, genuine REENTRY, and Cash
- no-loss-averaging evidence
- one-lot feasibility and Phase30-W admission state

Target lifecycle:

```text
healthy winner
-> HOLD
-> continued evidence
-> ADD-worthy
-> incremental capital
-> winner amplification
```

This is not an ADD-count increase target. Weak survivors must not receive
capital only because they survived, and long campaign age alone must not
authorize ADD.

## Profit Protection

Profit Protection is evidence, not action authority and not a fixed
take-profit rule.

PM should consume the structured `profit_protection_evidence` details:

- embedded return
- observed campaign MFE
- observed giveback
- CQ deterioration connection
- Downside Risk rise connection
- future peak / future MFE flags

Interpretation:

- healthy profit with low giveback can support HOLD and possible ADD review;
- meaningful profit plus deterioration and rising risk should stop ADD and
  provide REDUCE evidence;
- thesis break remains EXIT evidence under existing PM semantics.

## Authority Ownership

| Fact / decision | Canonical owner |
| --- | --- |
| Campaign identity | `positions/position_campaigns.json` |
| Campaign opened date / age | `positions/position_campaigns.json` |
| ADD / REDUCE history | `positions/position_campaigns.json` |
| Current quantity / valuation / basis | Current / Ledger / valuation authority |
| MFE / giveback | Campaign observed-state producer derived from canonical campaign + PIT prices / Current |
| CQ / Downside Risk / Relative Strength | Strategy Intelligence |
| HOLD action | Position Management |
| ADD action | Position Management directional intent, then PC/PS executable conversion |
| Target allocation | Portfolio Construction |
| Quantity | Position Sizing |
| Safety | Safety |

One owner per fact is mandatory. Shared evidence must not become shared action
authority.

## Legacy Inventory Summary

```text
KEEP = 8
MIGRATE = 6
DEPRECATE_DURING_MIGRATION = 7
REMOVE_AFTER_MIGRATION = 5
```

Major KEEP targets:

- canonical `positions/position_campaigns.json`
- Current / Ledger position and valuation authority
- Strategy Intelligence CQ / Risk / Relative Strength evidence producer
- PM action authority
- Portfolio Construction allocation authority
- Position Sizing quantity authority
- Phase30-W Entry Admission and one-lot admission
- Phase30-Z REENTRY genuine recovery contract

Major MIGRATE targets:

- Strategy Intelligence campaign consumption from missing/EOD-only to
  pre-action canonical campaign snapshot
- PM HOLD / Profit Protection consumer from broad status-only use to structured
  evidence use
- PC ADD / winner-amplification evidence from score-only emphasis to lifecycle
  + quality + opportunity-cost evidence
- ADD bridge campaign-continuation checks to canonical lifecycle facts
- residual reallocation comparator to include lifecycle/ADD-worthiness evidence
- tests and fixtures to require canonical campaign identity for held positions

Major DEPRECATE targets:

- EOD-only campaign reconstruction used as a proxy for pre-action decisions
- symbol-only fallback campaign references
- PM broad `strategy_intelligence_hold_worthiness_pass` from status alone
- CQ-only `strategy_intelligence_add_not_worthy_hold`
- score-only ADD opportunity comparator as sole arbiter
- current-only MFE/giveback fallback without canonical campaign provenance
- schemas/docs that allow held campaign identity to remain silently partial

Major REMOVE targets after migration:

- pre-action references to same-day EOD campaign reconstruction
- duplicate lifecycle persistence outside canonical owner
- obsolete tests permitting missing open-campaign identity
- obsolete docs treating campaign partiality as acceptable for held positions
- shadow-only action aliases if they imply an alternate action path

Machine-readable inventory:

```text
reports/phase_reports/phase30_ab_legacy_lifecycle_inventory.json
```

## Retirement Plan

Implementation sequence for Phase30-AC:

1. Materialize the pre-action canonical campaign lifecycle authority before
   Strategy Intelligence.
2. Connect Strategy Intelligence lifecycle context and Profit Protection details
   to that authority.
3. Migrate PM HOLD / Profit Protection consumption to structured evidence.
4. Migrate PC ADD / winner-amplification and residual reallocation evidence to
   canonical lifecycle fields.
5. Migrate tests and schemas to require canonical campaign identity for held
   positions.
6. Remove old fallback / adapter / heuristic paths once reference counts are
   zero.
7. Run post-removal regression.

Required retirement gates:

```text
DUPLICATE_CAMPAIGN_AUTHORITY = NO
LEGACY_CAMPAIGN_FALLBACK_REFERENCE_COUNT = 0
OBSOLETE_HOLD_ADD_HEURISTIC_REFERENCE_COUNT = 0
ONE_PRODUCTION_CAMPAIGN_LIFECYCLE_PATH = YES
```

No "just in case" legacy path is retained. Git history is the rollback
mechanism.

## Regression Design

Phase30-AC should include at least:

- Winner HOLD: healthy campaign + low giveback -> HOLD possible.
- Winner ADD: healthy mature campaign + strong incremental evidence -> ADD
  possible.
- Weak Survivor: HOLD-worthy but weak incremental evidence -> HOLD / NO_ADD.
- Giveback: large observed MFE + material giveback + deterioration -> Profit
  Protection evidence.
- Repeated ADD: prior ADD history recognized; unlimited ADD prevented.
- Campaign Identity: BUY -> HOLD -> ADD -> REDUCE preserves one canonical
  campaign.
- REENTRY: new campaign identity and Phase30-Z contract preserved.
- SELL Independence: SELL / REDUCE / EXIT unaffected by BUY-side state.
- PIT Safety: no future or EOD-only state reaches pre-action artifacts.

## Preserved Improvements

```text
PHASE30_W_ENTRY_ADMISSION_PRESERVED = YES
PHASE30_W_ONE_LOT_ADMISSION_PRESERVED = YES
PHASE30_Z_REENTRY_PRESERVED = YES
SELL_REDUCE_EXIT_SEMANTICS_PRESERVED = YES
BUY_SELL_INDEPENDENCE_PRESERVED = YES
PHASE30_P_SINGLE_STRATEGY_AUTHORITY_PATH_PRESERVED = YES
PHASE30_S_QUANTITY_HANDOFF_PRESERVED = YES
EXPECTED_EDGE = UNCALIBRATED
```

## Leakage

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
```

## New AI / Model

```text
NEW_AI_CREATED = NO
PRODUCTION_MODEL_RETRAINED = NO
MODEL_WEIGHTS_CHANGED = NO
ACCEPTED_GENERATION_CHANGED = NO
```

## Implementation Authorization

```text
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AB
NO IMPLEMENTATION AUTHORIZED BY_PHASE30_AB
```

## Recommended Next Task

```text
Phase30-AC - Campaign Lifecycle / HOLD-ADD Winner Amplification Repair Implementation and Legacy Retirement
```
