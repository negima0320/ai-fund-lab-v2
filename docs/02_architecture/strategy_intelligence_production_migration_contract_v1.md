# Strategy Intelligence Production Migration Contract v1

Created: 2026-08-16

## 1. Scope

This contract defines how Strategy Intelligence is migrated from shadow evidence
to Production-common Strategy evidence.

It is subordinate to:

- [Strategy Architecture v1](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/strategy_architecture_v1.md)
- [Strategy Intelligence Architecture v1](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/strategy_intelligence_architecture_v1.md)
- [Strategy Intelligence Data Contract v1](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/strategy_intelligence_data_contract_v1.md)
- [Strategy Intelligence Regression Contract v1](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/strategy_intelligence_regression_contract_v1.md)

Phase30-O is design-only.

```text
NO IMPLEMENTATION AUTHORIZED BY PHASE30_O
ACTUAL_TRADING_BEHAVIOR_CHANGED = NO
NEW_AI_CREATED = NO
PRODUCTION_MODEL_RETRAINED = NO
ACCEPTED_GENERATION_CHANGED = NO
```

## 2. Target Production Flow

Final Production architecture has one Strategy authority path:

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

Strategy Intelligence owns structured evidence, semantic interpretation, and
lifecycle context. It does not own order intent, target weights, quantities,
runtime mapping, submission, or Safety overrides.

## 3. Authority Boundaries

| Layer | Production authority | Strategy Intelligence role |
|---|---|---|
| Eligibility | BUY-side consumer / PC where fact-gated | source-backed facts and review status |
| Continuation Quality | action-specific consumer interpretation | evidence only |
| Downside Risk | action-specific consumer interpretation / Safety where guardrail fact exists | probabilistic risk evidence |
| Expected Edge | BUY-side / PC allocation comparison | uncalibrated relative evidence |
| Profit Protection | PM existing-position Action Authority | campaign-scoped evidence |
| Portfolio Construction | target portfolio and relative capital allocation | input evidence |
| Position Management | HOLD / ADD / REDUCE / EXIT directional actions | input evidence |
| Position Sizing | executable quantity and lot-aware sizing | no quantity authority |
| Runtime Planning | action mapping | no re-optimization |
| Safety | block/review guardrails | no performance optimization |

## 4. BUY_NEW Integration

BUY_NEW consumers must evaluate:

```text
Eligibility
+ Continuation Quality
+ Downside Risk
+ Expected Edge evidence
+ Portfolio context
```

Allowed first-generation roles:

| Evidence | Role |
|---|---|
| authoritative disqualifying fact | may block BUY |
| missing required BUY authority | review/block/BUY_WAIT according to existing consumer semantics |
| weak or incomplete CQ | may wait or reduce attractiveness |
| elevated probabilistic risk | may reduce attractiveness or require review; not automatic hard reject |
| uncalibrated Expected Edge | relative opportunity / opportunity-cost evidence only |
| stock-vs-market relative strength | first-generation formal relative-strength input |

High momentum alone is not sufficient BUY evidence. No Phase30-O threshold may be
selected from Historical outcome performance.

## 5. BUY_WAIT Integration

BUY_WAIT means:

```text
thesis remains potentially valid, but current entry timing/evidence is insufficient
```

Production migration must preserve:

- non-Pending semantics,
- next-day reevaluation,
- BUY / SELL independence,
- no Runtime halt.

BUY-side SI evidence failure must not block unrelated SELL / REDUCE / EXIT.

## 6. ADD Integration

ADD is distinct from HOLD. ADD consumers must consider:

- current CQ,
- incremental continuation quality,
- Downside Risk,
- incremental Expected Edge,
- opportunity cost,
- current exposure,
- Strategy cap,
- Safety hard cap.

Strategy Intelligence may describe incremental ADD evidence, but Portfolio
Construction and Position Sizing retain allocation and executable quantity
authority.

## 7. REENTRY Integration

REENTRY remains a semantic BUY lifecycle path with cooldown and recovery
requirements. Strategy Intelligence provides recovery, CQ, downside risk, churn,
and prior-campaign context. Blanket REENTRY bans are prohibited. REENTRY must
not be confused with BUY_ADD.

## 8. HOLD / Profit Protection / REDUCE / EXIT

HOLD means:

```text
current PIT evidence still supports keeping capital deployed in the current
canonical campaign
```

It is not merely failure to trigger SELL.

Profit Protection is PM evidence, not a sell rule. It may include observed
embedded return, observed campaign MFE, observed giveback, CQ deterioration,
Downside Risk rise, and regime deterioration. Future peak, future MFE, final
campaign outcome, and fixed take-profit thresholds are prohibited.

REDUCE / EXIT consumers must integrate multiple evidence families inside PM
authority. The following are prohibited:

- CQ alone -> SELL,
- Risk alone -> EXIT,
- automatic REDUCE -> EXIT.

## 9. Expected Edge

First-generation Expected Edge remains:

```text
calibration_status = UNCALIBRATED
economic_units_available = false
```

It may be used only as relative opportunity, allocation comparison,
incremental ADD, and opportunity-cost evidence. It must not be treated as
calibrated expected return or an absolute return threshold.

## 10. Relative Strength

First-generation Production migration may use stock-vs-market relative strength
only when PIT symbol returns and PIT market equal-weight returns are both
present.

Stock-vs-sector and sector-vs-market remain:

```text
DEFERRED_DATA_FOUNDATION
```

The missing sector foundation must not be inferred or silently substituted by
rank, BUY Quality, or runtime opportunity score.

## 11. Fail-Closed Migration

After an SI evidence family becomes mandatory for an action-specific consumer,
missing or malformed SI evidence must fail closed through explicit existing
semantics:

| Consumer side | Missing mandatory evidence behavior |
|---|---|
| BUY_NEW | BUY_WAIT, no-action, review, or block according to fact severity |
| ADD | no ADD or review; existing HOLD/SELL path remains independently evaluable |
| HOLD | PM review if current-position evidence is mandatory and missing |
| REDUCE / EXIT | evaluate SELL-side required evidence only; BUY evidence failure cannot stop SELL |
| Runtime Planning | map only authorized upstream decisions; do not re-optimize |
| Safety | preserve guardrail block/review authority |

Silent fallback to old Strategy logic is prohibited.

## 12. Migration Stages

### Stage 0: Contract Freeze

Exit criteria:

- contracts updated,
- legacy inventory complete,
- consumer authority map complete,
- no implementation or behavior change.

### Stage 1: Production Evidence Connection

Connect Strategy Intelligence artifact as Production-readable evidence while
actions remain unchanged.

Exit criteria:

- SI lineage Source -> Feature -> Artifact -> Consumer is proven,
- no action authority transfer to SI,
- no silent fallback,
- BUY / SELL independence PASS.

### Stage 2: BUY-Side Consumer Migration

Migrate BUY_NEW, BUY_WAIT, REENTRY, and BUY-side quality interpretation to SI
evidence.

Exit criteria:

- high momentum alone no longer authorizes BUY,
- Expected Edge remains uncalibrated,
- probabilistic risk not automatic hard reject,
- replaced BUY Quality interpretation references identified for retirement.

### Stage 3: Existing-Position PM Evidence Migration

Migrate HOLD, ADD, Profit Protection, REDUCE, and EXIT evidence consumption.

Exit criteria:

- PM remains Action Authority,
- HOLD-worthy and ADD-worthy are separate,
- campaign identity complete,
- CQ-only SELL and risk-only EXIT prohibited by regression.

### Stage 4: Legacy Retirement

Remove replaced consumers, compatibility adapters, schemas, configs, tests, and
docs after reference count reaches zero.

Exit criteria:

- old consumer reference count = 0,
- old fallback reference count = 0,
- obsolete config/schema/test/docs references = 0,
- post-removal regression PASS.

### Stage 5: 10BD Entry Gate

User-operated 10BD fresh Historical may start only after:

- Production Strategy Intelligence connection complete,
- replaced legacy logic removed,
- no duplicate Production authority,
- no silent fallback,
- BUY / SELL independence PASS,
- BUY_WAIT / ADD / REENTRY / HOLD / REDUCE / EXIT / NO_ACTION PASS,
- Profit Protection lifecycle PASS,
- Current/campaign authority complete,
- valuation/basis PASS,
- multi-day regression PASS,
- leakage firewall PASS,
- Production-common path confirmed.

10BD outcomes may diagnose defects or support research hypotheses, but must not
be used for post-hoc threshold tuning.

## 13. Leakage Firewall

Production migration must not consume future price, future return, future MFE,
future MAE, future regime, final campaign outcome, Historical result,
Historical PnL, Paper Ledger performance, later Winner/Loser labels, test
results, audit results, or information after the decision date.

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
```
