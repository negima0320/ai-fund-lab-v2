# Phase30-AA - Existing Data / Component Utilization Gap Audit

Task ID: `Phase30-AA`

Boundary:

```text
READ_ONLY_AUDIT
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30-AA
NO_100BD_EXECUTION
NO_STRATEGY_RUNTIME_CONFIG_MODEL_THRESHOLD_CHANGE
NO_HISTORICAL_OUTCOME_FIT
NO_NEW_EXTERNAL_DATA_SOURCE
PHASE30_Z_REENTRY_REPAIR_UNCHANGED
```

## Primary Judgment

```text
EXISTING_DATA_COMPONENT_IMPROVEMENT_AVAILABLE = YES
```

Required judgments:

```text
SELECTION_EXISTING_DATA_UTILIZATION = PARTIAL
HOLD_EXISTING_DATA_UTILIZATION = PARTIAL
ADD_EXISTING_DATA_UTILIZATION = PARTIAL
CAPITAL_REALLOCATION_EXISTING_DATA_UTILIZATION = PARTIAL
```

The strongest remaining gap before a fresh 100BD is not a need for new AI or
new external data. It is an existing-data utilization gap around campaign
lifecycle, observed position state, HOLD-worthiness, ADD-worthiness, and capital
reallocation semantics.

## Selection

Lineage:

```text
PIT technical / market / opportunity / BUY Quality
-> Strategy Intelligence CQ / Downside Risk / Relative Strength / Entry Admission
-> strategy/strategy_intelligence.json
-> Portfolio Construction
-> membership_intent / quality_action / target_weight / one_lot_admission
-> Runtime BUY_NEW / no-action behavior
```

What is connected and effective:

- Entry Admission is connected and effective. Phase30-X/Y found zero actual
  BUY fills in BUY_WAIT / reversal BUY_WAIT.
- PC receives `entry_admission_state`, `entry_admission_action`, CQ status,
  downside risk status, relative strength state, and Expected Edge calibration
  metadata.

Remaining gap:

- Relative Strength and CQ sub-states are visible evidence, but candidate
  priority / ranking and target allocation still lean heavily on opportunity
  rank/score, BUY Quality, lot feasibility, and Entry Admission bucket.
- Negative or weak uncalibrated `runtime_opportunity_score` can still coexist
  with target allocation if Entry Admission is reduced-only rather than wait.
  Example on 2022-09-07: 47600 had `runtime_opportunity_score = -0.07839731`,
  `SUPPORTIVE` relative strength, `BUY_NEW_REDUCED_ONLY`, and target weight
  `0.175381`.

Classification:

```text
CONNECTED_NOT_ACTION_EFFECTIVE
Priority = MEDIUM
```

Selection can improve with existing SI evidence, but full Expected Edge /
payoff ranking remains `CALIBRATION_REQUIRED`.

## HOLD

Lineage:

```text
Current / Ledger / position_campaigns / PIT technical state
-> Strategy Intelligence lifecycle_context + profit_protection_evidence
-> Position Management
-> PM HOLD / UNRESOLVED / REDUCE / EXIT
-> Portfolio Construction retain/remove target
-> Position Sizing / Runtime Planning
```

What is connected:

- PM consumes Strategy Intelligence artifact as Production evidence.
- PM records CQ status, downside risk status, profit-protection status, and SI
  campaign id.

Gap:

- The PM consumer currently uses broad SI status fields. It does not consume the
  structured contents of `profit_protection_evidence`, such as embedded return,
  observed MFE, observed giveback, CQ deterioration connection, or downside risk
  rise connection.
- In the 2022-09-07 Production pre-action SI artifact, open held names such as
  94320, 27880, 36600, 67860, 93180, and 94340 had `campaign_identity_authority_status
  = PARTIAL`, no `position_campaign_id`, no opened date, and no observed
  MFE/giveback.
- The same date's EOD shadow SI did recover campaign identity and ADD history
  for 94320: campaign `pc-b7614b631128269a-94320-0001`, opened `2022-08-10`,
  ADD history count `5`. That proves the data exists in run artifacts, but is
  not available to the pre-action Production consumer path.

Classification:

```text
DATA_EXISTS_NOT_CONNECTED
CONNECTED_NOT_ACTION_EFFECTIVE
Priority = CRITICAL / HIGH
```

## ADD / Winner Amplification

Lineage:

```text
Current position + campaign identity + prior PC score baseline + CQ/Risk/Entry Admission
-> add_baseline_supply_evidence / Strategy Intelligence / PM ADD
-> Portfolio Construction add_investment_evidence
-> target_weight increase or unchanged
-> Position Sizing BUY_ADD quantity
```

What is connected:

- PC has canonical ADD bridge and `add_investment_evidence`.
- It checks expected-edge improvement, incremental investment value,
  opportunity cost, campaign continuation, no-loss averaging, concentration,
  capital, and execution feasibility.
- Phase30-W one-lot admission can block weak ADD overshoot, as seen in 94320 on
  2022-08-31.

Gap:

- ADD-worthiness is still more connected to PM ADD, score-vs-baseline,
  score-vs-BUY_NEW opportunity cost, no-loss averaging, and lot feasibility than
  to mature winner context.
- Campaign age, observed MFE, observed giveback, ADD history, and profit
  protection are either absent pre-action or not materially consumed by PC as
  ADD-worthy / no-ADD semantics.
- On 2022-09-07, 94320 was a large retained position but PC had PM `HOLD`, no
  ADD eligibility fields, and no usable campaign id in the pre-action SI path,
  while EOD shadow showed the campaign and five prior ADDs.

Classification:

```text
DATA_EXISTS_NOT_CONNECTED
CONNECTED_NOT_ACTION_EFFECTIVE
Priority = HIGH
```

This is the most direct existing-data route to improve winner amplification and
payoff asymmetry without changing Phase30-W or Phase30-Z.

## Capital Reallocation

Lineage:

```text
SELL / REDUCE released capacity
-> PC incremental budget reconciliation
-> lot_aware_final_reallocation
-> quality_adjusted_one_lot_admission
-> Position Sizing
-> Runtime Planning
```

What is connected:

- Residual recycling is active.
- one-lot admission is quality-adjusted and records Entry Admission,
  ADD-worthiness, relative opportunity state, and opportunity cost state.
- 2022-09-07 PC allocated `0.4867` residual/rebatch weight and left only
  `0.008538` cash weight with `CAPITAL_BELOW_NEXT_LOT`.

Gap:

- Candidate ordering is still primarily Entry Admission quality bucket,
  construction priority, and symbol tie-break. It does not yet compare the full
  existing SI quality stack across BUY_NEW / ADD / genuine REENTRY / Cash.
- Broader lifecycle quality is not used to prefer adding to a mature winner
  over a reduced-only BUY_NEW, except where PM already emits ADD and the ADD
  bridge passes.

Classification:

```text
CONNECTED_NOT_ACTION_EFFECTIVE
Priority = MEDIUM
```

## Existing Campaign Data

Observed existing data:

- `positions/position_campaigns.json` exists and contains open/closed
  campaigns, opened dates, events, buy/sell notional, realized/unrealized PnL,
  and event histories.
- Strategy EOD shadow can join campaign identity and ADD history.

Underused or missing pre-action:

- campaign identity
- campaign opened date / age
- ADD history
- REDUCE history
- same-campaign score baseline completeness
- observed MFE
- observed giveback
- entry thesis metadata
- prior exit/recovery context outside REENTRY

Important split:

- Campaign identity and ADD history are `DATA_EXISTS_NOT_CONNECTED`.
- Observed MFE/giveback are not materialized in the pre-action artifact; they
  are computable from existing PIT prices plus campaign identity, but require a
  Production-common producer/adapter repair. No new external data source is
  required.

## Dead / Underused Evidence

| Evidence | Classification | Current state |
| --- | --- | --- |
| Entry Admission | CONNECTED_AND_EFFECTIVE | BUY_WAIT / NO_ADD / reduced allocation works. |
| One-lot admission | CONNECTED_AND_EFFECTIVE | Blocks weak overshoot and preserves Safety hard cap. |
| Phase30-Z REENTRY recovery | CONNECTED_AND_EFFECTIVE | Repaired; do not change in AA. |
| SI lifecycle campaign id pre-action | DATA_EXISTS_NOT_CONNECTED | EOD has it; pre-action reports missing. |
| SI profit_protection details | CONNECTED_NOT_ACTION_EFFECTIVE | Status consumed, details not action-effective. |
| ADD history / campaign age | DATA_EXISTS_NOT_CONNECTED | EOD join can expose it; pre-action Action path lacks it. |
| Relative Strength | CONNECTED_NOT_ACTION_EFFECTIVE | Present, but ranking/allocation effect is limited. |
| Expected Edge economic units | CALIBRATION_REQUIRED | Remains `UNCALIBRATED`. |
| Sector relative strength | MISSING_DATA_FOUNDATION | Do not infer from rank/score. |

## Improvement Candidate Ranking

1. `CRITICAL` - Pre-action campaign lifecycle / observed-state connection
   repair.
   Existing data availability is strong because `position_campaigns.json` exists
   and EOD shadow joins it. Behavioral impact is high for HOLD, ADD, winner
   amplification, and capital reallocation.

2. `HIGH` - PM HOLD / profit-protection semantic consumption of existing SI
   fields.
   Use embedded return, observed MFE/giveback when available, deterioration
   connection, and risk-rise connection as PM evidence without changing SELL /
   REDUCE / EXIT authority.

3. `HIGH` - ADD / winner amplification worthiness bridge using existing
   lifecycle and SI evidence.
   Keep `HOLD-worthy != ADD-worthy`; improve ADD eligibility with campaign age,
   ADD history, CQ/risk, relative strength, opportunity cost, and no
   loss-averaging.

4. `MEDIUM` - Capital reallocation comparator using full SI quality stack.
   Preserve Phase30-W one-lot/residual recycling but rank marginal JPY by
   quality across BUY_NEW / ADD / genuine REENTRY / Cash.

5. `MEDIUM` - Selection ranking use of CQ / relative strength / downside risk.
   Existing data can improve relative ordering, but full forward-payoff
   optimization requires separate calibration.

## What Does NOT Need Repair

Do not repair these under Phase30-AA:

```text
Phase30-W Entry Admission
Phase30-W one-lot concentration repair
Phase30-Z REENTRY repair
SELL / REDUCE / EXIT
Loss containment
BUY / SELL independence
Phase30-P authority migration
Position Sizing concrete quantity handoff
```

## New Data Required

Not part of the existing-data repair:

- stock-vs-sector and sector-vs-market relative strength authority;
- calibrated Expected Edge in economic return / payoff units;
- optimized payoff thresholds.

These require separate data foundation or calibration work and must not be
mixed into the existing-data Production repair.

## Leakage / Integrity

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
```

Phase30-AA used Phase30-X/Y outcomes only to identify behavior gaps. It did not
turn winner/loser outcomes into production parameters.

## Implementation Authorization

```text
NO IMPLEMENTATION AUTHORIZED BY PHASE30-AA
```

## 100BD Gate

```text
100BD_ENTRY_DEFERRED_FOR_EXISTING_DATA_REPAIR
```

Reason: a high-impact existing-data gap remains before the fresh 100BD would be
the cleanest behavior validation.

## Recommended Next Task

```text
Phase30-AB - Production-Common Campaign Lifecycle / HOLD-ADD Winner Amplification Existing-Data Repair Design
```

Scope should be design-only or explicitly authorized repair design. It should
not include Expected Edge calibration, sector data foundation, Phase30-W Entry
Admission changes, Phase30-Z REENTRY changes, or SELL / REDUCE / EXIT redesign.
