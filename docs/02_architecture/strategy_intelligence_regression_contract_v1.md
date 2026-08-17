# Strategy Intelligence Regression Contract v1

Created: 2026-08-16

## 1. Scope

This document defines mandatory regression and migration gates for Strategy
Intelligence implementation.

It is subordinate to:

- [Strategy Architecture v1](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/strategy_architecture_v1.md)
- [Strategy Intelligence Architecture v1](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/strategy_intelligence_architecture_v1.md)
- [Strategy Intelligence Data Contract v1](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/strategy_intelligence_data_contract_v1.md)
- [Strategy Intelligence Production Migration Contract v1](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/strategy_intelligence_production_migration_contract_v1.md)
- [Strategy Intelligence Legacy Retirement Contract v1](/Users/negishi/work/ai-fund-lab-v2/docs/02_architecture/strategy_intelligence_legacy_retirement_contract_v1.md)

No implementation is authorized by this document.

## 2. Mandatory Data Lineage Regression

Every new dimension must prove:

```text
Source
-> PIT Authority
-> Feature
-> Strategy Intelligence Artifact
-> Consumer
-> Decision influence
```

Shadow-only stages may stop at proposed decision influence, but they still must
record how the evidence would have influenced the future authorized decision.

## 3. Lifecycle Regression Coverage

### BUY Lifecycle

```text
Candidate
-> Strategy Intelligence evidence
-> BUY_NEW interpretation
-> Portfolio Construction target
-> Position Sizing
-> Runtime Planning
-> execution
-> next-day HOLD evidence
```

### ADD Lifecycle

```text
HOLD
-> ADD candidate
-> incremental CQ / downside / edge evidence
-> sizing
-> execution
-> next-day persistence
```

### SELL Lifecycle

```text
HOLD
-> deterioration evidence
-> REDUCE
-> partial SELL
-> remaining position
-> EXIT
```

Campaign identity regression:

```text
BUY_NEW
-> canonical campaign identity
-> HOLD
-> ADD using same campaign identity
-> REDUCE / partial SELL using same campaign identity for remaining position
-> EXIT closes campaign according to canonical authority
-> later REENTRY uses the canonical new campaign identity if a new campaign is created
```

The canonical identity authority is `positions/position_campaigns.json`. Strategy
Intelligence may join Current state to this authority, but it must not create a
duplicate campaign ledger or silently fall back to an invented lifecycle id.
Same-day EXIT may reference the canonical campaign closed by that day's EXIT
event for EXIT-day interpretation. Later no-position days must not treat that
closed campaign as a current holding.

### REENTRY Lifecycle

```text
EXIT
-> cooldown
-> recovery
-> REENTRY
```

### BUY_WAIT

BUY_WAIT must remain:

- non-Pending,
- temporary,
- next-day re-evaluated,
- independent from SELL,
- not a Runtime halt.

### NO_ACTION

NO_ACTION remains a valid authorized continuity path.

### Safety

Safety remains block/review guardrail only. It must not optimize Strategy
Intelligence or expected edge.

## 4. Multi-Day Transition Regression

Mandatory minimum sequence:

```text
Day 1 BUY
Day 2 HOLD
Day 3 ADD
Day 4 HOLD
Day 5 deterioration
Day 6 REDUCE
Day 7 partial position persists
Day 8 EXIT
```

Also test:

```text
BUY_WAIT while existing SELL executes
REENTRY after cooldown/recovery
no opportunity -> Cash
```

No implementation should be accepted based only on unit tests.

## 5. Closed-Contract Non-Regression

Implementation must not degrade:

- BUY / SELL independence,
- REENTRY semantics,
- BUY_WAIT,
- ADD,
- REDUCE discrete-lot semantics,
- residual capital recycling,
- lot-aware sizing,
- market context propagation,
- corporate-action handling,
- low-price risk,
- current valuation,
- price/quantity basis,
- Current / Campaign authority identity,
- Execution NO_ACTION,
- Pending lifecycle,
- Safety guardrail authority.

## 6. Winner Preservation Gate

Any future behavior-changing implementation must report:

| Metric | Requirement |
|---|---|
| severe losers avoided | measured |
| healthy Winners removed | measured |
| missed MFE | measured |
| average/median forward return | measured |
| MAE reduction | measured |
| MFE preservation | measured |
| turnover impact | measured |
| exposure impact | measured |
| concentration impact | measured |

Approval cannot be based only on MAE reduction. Broad risk vetoes must be
rejected if they remove too many healthy Winners.

## 7. Shadow Migration Regression

Shadow output must record:

```text
CURRENT_DECISION
PROPOSED_INTELLIGENCE_EVIDENCE
STRATEGY_INTELLIGENCE_INTERPRETATION
```

Shadow tests must cover:

- 78780-type exhaustion/reversal entry,
- 67310-type high-volatility negative short structure,
- 93180-type event/microstructure weakness,
- healthy Winners,
- REENTRY,
- ADD,
- HOLD,
- MFE giveback,
- REDUCE/EXIT,
- no opportunity -> Cash.

Shadow logic must call the same future Production-common evidence producers.
No permanent Historical-only Strategy stack is allowed.

## 8. Failure-Mode Analysis

| Failure mode | Mitigation |
|---|---|
| Broad risk veto removes Winners | Winner Preservation Gate; probabilistic risk, not one-factor hard block |
| High momentum mistaken for continuation | Separate persistence, reversal, exhaustion, and participation dimensions |
| Stale CQ evidence | daily PIT recomputation; freshness metadata; no latest fallback |
| Missing event data appears safe | event coverage authority and uncertainty status |
| Relative Strength missing | explicit `DATA_FOUNDATION_INSUFFICIENT` |
| Score double-counting | source provenance and dimension ownership |
| Volatility double-penalty | shared provenance across Downside Risk and sizing |
| Microstructure double-penalty | PC cap provenance linked to risk evidence |
| Regime overreaction | regime-conditioned interpretation, no Phase30-I thresholds |
| ADD reinforces late-stage Winner | incremental CQ and downside check; ADD stop state |
| HOLD becomes too sticky | HOLD-worthiness refresh and deterioration evidence |
| Profit Protection becomes premature take-profit | profit alone is not action; CQ/risk deterioration required |
| CQ becomes Action Authority | shared evidence vs action authority boundary tests |
| Expected Edge treated as calibrated return | `calibration_status: UNCALIBRATED`; economic units false |
| Shadow logic drifts from future Production logic | same producer path; no duplicate Strategy stack |

## 9. Production Authority Migration Gate

Shadow evidence may become Production decision authority only after:

1. schema stable,
2. PIT lineage proven,
3. no future leakage,
4. multi-day persistence proven,
5. Winner Preservation evaluation passed,
6. severe-loss reduction evidence,
7. closed-contract regression PASS,
8. shadow/current decision comparison understood,
9. Production-common execution path proven,
10. no Historical-only behavior.

Phase30-I does not approve migration.

Phase30-O adds the Production consumer migration and legacy retirement gate.
Strategy Intelligence may become Production evidence, but it must not become
Action Authority. Migration is not complete until:

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

Mandatory migration regressions:

- BUY_NEW,
- BUY_WAIT,
- ADD,
- REENTRY,
- HOLD,
- Profit Protection,
- REDUCE,
- partial SELL,
- EXIT,
- NO_ACTION,
- BUY_WAIT + SELL independence,
- BUY evidence missing + SELL independence,
- ADD + later REDUCE,
- EXIT + later REENTRY,
- campaign identity,
- valuation/basis,
- Current/Ledger,
- no silent legacy fallback,
- no duplicate Production Strategy authority.

## 10. Expected Edge Calibration Future Gate

Formal Expected Edge calibration requires:

- time-respecting training/calibration,
- strict separation of research labels,
- calibration stability,
- defined horizon,
- regime behavior validation,
- uncertainty/confidence intervals or equivalent,
- opportunity-cost semantics,
- turnover effects,
- no Historical result leakage,
- `calibration_applied=true`,
- `economic_units_available=true`.

Until then the contract is:

```text
EXPECTED_EDGE_RESEARCH_CONTRACT
```

not:

```text
CALIBRATED_EXPECTED_RETURN
```
