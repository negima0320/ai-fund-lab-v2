# Phase30-AK6 - Mid-Run Low-Exposure / Growth-Stagnation Attribution Audit

## Scope

Task ID: `Phase30-AK6`

Type: `READ_ONLY_PERFORMANCE_AND_CAPITAL_ATTRIBUTION_AUDIT`

Target run:

```text
runtime-test-historical-extended-smoke-20260817T014925194738Z
```

Audit window:

```text
context anchor = 2022-09-12
primary window = 2022-09-13 through 2022-09-27
```

No implementation, replay, resume, fresh run, target-run mutation, Strategy
change, Candidate change, model change, threshold change, cap change, Safety
relaxation, or historical-outcome fitting was performed.

## Primary Judgment

```text
MID_RUN_STAGNATION_PRIMARY_CLASS = CAPITAL_CONVERSION_LIMITATION
MID_RUN_STAGNATION_SECONDARY_CLASSES = [
  MARKET_DRIVEN,
  STRATEGY_DRIVEN_BUT_LEGITIMATE,
  WINNER_CONCENTRATION_INSUFFICIENT
]
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = NO
IMPLEMENTATION_REPAIR_JUSTIFIED = INSUFFICIENT_EVIDENCE
```

The low-exposure / growth-stagnation period was not caused by a single confirmed
Runtime or authority defect. Candidate supply remained broad, but capital did
not consistently convert from PC-positive intent into PS executable lots and
fills. Market context was also weak: 8 of 9 primary-window days were
`WEAK`, and 6 of 9 were `CORRECTION` or `BEAR`.

## Equity / Exposure Regime

```text
WINDOW_START_EQUITY = 1,100,280
WINDOW_END_EQUITY = 1,064,270
WINDOW_RETURN_DELTA = -3.601 percentage points
WINDOW_MAX_DRAWDOWN = -3.53%
WINDOW_AVG_EXPOSURE = 59.89%
WINDOW_MIN_EXPOSURE = 38.11%
WINDOW_MAX_EXPOSURE = 81.49%
```

| Date | Equity | Daily PnL | Return | Cash | Exposure | Positions | Market context |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2022-09-12 | 1,100,280 |  | 10.03% | 243,630 | 77.86% | 11 | `RECOVERY|NEUTRAL|NORMAL|RECOVERY` |
| 2022-09-13 | 1,088,080 | -12,200 | 8.81% | 201,450 | 81.49% | 12 | `RECOVERY|NEUTRAL|NORMAL|RECOVERY` |
| 2022-09-14 | 1,088,320 | 240 | 8.83% | 201,450 | 81.49% | 12 | `RANGE|WEAK|NORMAL|RANGE` |
| 2022-09-15 | 1,080,120 | -8,200 | 8.01% | 425,950 | 60.56% | 11 | `RANGE|WEAK|NORMAL|RANGE` |
| 2022-09-16 | 1,070,730 | -9,390 | 7.07% | 509,140 | 52.45% | 8 | `CORRECTION|WEAK|NORMAL|CORRECTION` |
| 2022-09-20 | 1,075,270 | 4,540 | 7.53% | 665,440 | 38.11% | 6 | `CORRECTION|WEAK|NORMAL|CORRECTION` |
| 2022-09-21 | 1,064,890 | -10,380 | 6.49% | 317,090 | 70.22% | 11 | `CORRECTION|WEAK|NORMAL|CORRECTION` |
| 2022-09-22 | 1,061,410 | -3,480 | 6.14% | 600,280 | 43.45% | 7 | `CORRECTION|WEAK|NORMAL|CORRECTION` |
| 2022-09-26 | 1,062,250 | 840 | 6.22% | 477,950 | 55.01% | 8 | `BEAR|WEAK|NORMAL|BEAR` |
| 2022-09-27 | 1,064,270 | 2,020 | 6.43% | 465,800 | 56.23% | 9 | `BEAR|WEAK|NORMAL|BEAR` |

## Market / Opportunity Context

```text
MARKET_CONTEXT_DISTRIBUTION = {
  RECOVERY|NEUTRAL|NORMAL|RECOVERY: 1,
  RANGE|WEAK|NORMAL|RANGE: 2,
  CORRECTION|WEAK|NORMAL|CORRECTION: 4,
  BEAR|WEAK|NORMAL|BEAR: 2
}

MARKET_OPPORTUNITY_WEAKNESS_EXPLAINS_LOW_EXPOSURE = PARTIAL
```

Market weakness explains part of the behavior because the regime deteriorated
from Recovery/Range into Correction/Bear and breadth was weak for most of the
window. It does not fully explain the low exposure because the system still
observed 112 valid BUY opportunities and 87 PC-positive BUY_NEW intents in the
primary window.

## Candidate -> BUY_NEW Funnel

```text
BUY_NEW_FUNNEL_TOTALS = {
  candidate_top50: 450,
  quality_pass: 384,
  valid_buy_opportunity: 112,
  entry_admitted: 437,
  pc_positive_buy_new: 87,
  ps_positive_buy_new: 26,
  runtime_buy_new: 26,
  buy_new_fills: 10
}
```

| Date | Top50 | Quality PASS | Entry admitted | Valid BUY opp | PC+ BUY_NEW | PS+ BUY_NEW | Runtime BUY_NEW | BUY_NEW fills |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-09-13 | 50 | 43 | 48 | 16 | 9 | 3 | 3 | 2 |
| 2022-09-14 | 50 | 43 | 48 | 13 | 7 | 1 | 1 | 0 |
| 2022-09-15 | 50 | 43 | 46 | 14 | 11 | 3 | 3 | 0 |
| 2022-09-16 | 50 | 44 | 49 | 10 | 7 | 3 | 3 | 0 |
| 2022-09-20 | 50 | 43 | 49 | 9 | 8 | 4 | 4 | 0 |
| 2022-09-21 | 50 | 43 | 44 | 11 | 10 | 5 | 5 | 5 |
| 2022-09-22 | 50 | 43 | 48 | 16 | 15 | 4 | 4 | 0 |
| 2022-09-26 | 50 | 42 | 53 | 14 | 10 | 2 | 2 | 2 |
| 2022-09-27 | 50 | 40 | 52 | 9 | 10 | 1 | 1 | 1 |

Primary drop:

```text
PC positive BUY_NEW -> PS positive BUY_NEW = 87 -> 26
PS positive BUY_NEW -> Runtime BUY_NEW = 26 -> 26
Runtime BUY_NEW -> BUY_NEW fill = 26 -> 10
```

This matches the AK1T/AK1U lineage: lot economics and executable conversion are
the dominant capital-action bottleneck after PC positive intent. Runtime did
not drop PS-positive BUY_NEW intents in this window.

## Cash Constraint Attribution

```text
CASH_PRUNED_COUNT = 2
CASH_PRUNED_NOTIONAL = 388,500
CASH_PRUNED_SYMBOL_DAYS = [
  [2022-09-13, 47600],
  [2022-09-15, 47600]
]
HIGH_CASH_DAY_CASH_PRUNED_COUNT = 1
CASH_CONSTRAINT_PRIMARY_LOW_EXPOSURE_CAUSE = PARTIAL
```

Cash pruning mattered for `47600` twice, but it was not the dominant explanation
for sustained low exposure. Several high-cash days had no cash-pruned item; on
2022-09-15 the high end-of-day cash appeared after sells, while the BUY batch
was constrained by decision-time starting cash.

## One-Lot Entry Lifecycle

Strict 100-share entry cohort through 2022-09-27:

```text
ONE_LOT_LIFECYCLE_DISTRIBUTION = {
  ONE_LOT_ONLY_EXIT: 36,
  ONE_LOT_HOLD_NO_ADD_INTENT: 7,
  ADD_INTENT_BUT_NO_CAPITALIZATION: 0,
  MULTI_LOT_WINNER: 0,
  CASH_BLOCKED_ADD: 0,
  CAP_BLOCKED_ADD: 0,
  QUALITY_NOT_STRONG_ENOUGH_FOR_ADD: 0
}
```

The strict one-lot cohort mostly remained exploratory: positions either exited
or stayed as one-lot holdings without a broad path to multi-lot capitalization.
This is not automatically a defect, because the one-lot contract only admits a
minimum executable entry; it does not promise later ADD.

## ADD Conversion Funnel

```text
PM_ADD_COUNT = 9
PC_POSITIVE_ADD_COUNT = 5
PS_POSITIVE_ADD_COUNT = 5
RUNTIME_BUY_ADD_COUNT = 5
BUY_ADD_FILL_COUNT = 2
ADD_CONVERSION_RATE_PM_TO_FILL = 0.222222
```

ADD intent existed on every primary-window day for `94320`. PC and PS converted
5 of those into positive ADD action, Runtime preserved those 5 as BUY_ADD
intents, and 2 filled: `94320` +200 shares on 2022-09-21 and +100 shares on
2022-09-26.

## 94320 Comparator

```text
WHY_94320_AMPLIFIED_WHILE_OTHERS_DID_NOT =
94320 stayed rank 1, received PM ADD intent on all 9 primary-window days,
converted to PC/PS positive ADD on 5 days, and filled BUY_ADD twice. The strict
one-lot cohort did not show the same combination of persistent ADD intent,
PC incremental target, PS executable quantity, and fill.
```

94320 quantity path in the audited span:

```text
2022-09-12: 800
2022-09-21: 1000
2022-09-26: 1100
```

This is an action-effect success comparator, not a new ranking rule. The
post-window outcome was not used as runtime input.

## Capital Fragmentation

```text
CAPITAL_FRAGMENTATION_CONFIRMED = PARTIAL
```

| Date | Positions | One-lot | Multi-lot | Median weight | Top1 | Top3 | Below 5% |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-09-13 | 12 | 10 | 2 | 5.35% | 20.98% | 42.19% | 5 |
| 2022-09-14 | 12 | 10 | 2 | 5.44% | 21.41% | 42.27% | 5 |
| 2022-09-15 | 11 | 9 | 2 | 5.51% | 11.44% | 29.37% | 5 |
| 2022-09-16 | 8 | 7 | 1 | 6.32% | 11.49% | 29.31% | 2 |
| 2022-09-20 | 6 | 5 | 1 | 6.37% | 11.65% | 27.25% | 2 |
| 2022-09-21 | 11 | 9 | 2 | 5.64% | 14.54% | 37.40% | 5 |
| 2022-09-22 | 7 | 5 | 2 | 5.65% | 14.57% | 30.41% | 3 |
| 2022-09-26 | 8 | 7 | 1 | 6.18% | 16.10% | 31.59% | 2 |
| 2022-09-27 | 9 | 7 | 2 | 5.54% | 16.02% | 31.89% | 4 |

Fragmentation is visible, but the larger issue is not raw position count. The
larger issue is weak conversion from PC positive intent into executable and
filled incremental capital during a weak market regime.

## Winner / Loser Contribution

PnL method:

```text
daily economic contribution =
current_market_value - previous_market_value + fill_cash_effect
```

This reconciles to the portfolio equity change of `-36,010 JPY`.

```text
TOP_WINNER_CONTRIBUTORS = [
  [33700, 3900],
  [73590, 3750],
  [27670, 2700],
  [27880, 1600],
  [32710, 800]
]

TOP_LOSER_CONTRIBUTORS = [
  [47600, -15400],
  [78780, -14500],
  [71380, -4140],
  [94320, -3370],
  [44150, -2900]
]

WINNER_CONCENTRATION_RATIO = 0.400722
LOSS_CONTAINMENT = PARTIAL
```

Loss was concentrated in a small number of names, especially `47600` and
`78780`. The strategy reduced exposure after losses and avoided compounding the
damage, but winners were not large enough or numerous enough to offset the
losers during the window.

## Exposure Drop Attribution

```text
LOW_EXPOSURE_DAY_ATTRIBUTION = {
  2022-09-16: MULTI_CAUSAL:SELL/EXIT_RISK_REDUCTION+LOT_CONVERSION_DOMINATED+ADD_CONVERSION_WEAKNESS,
  2022-09-20: MULTI_CAUSAL:SELL/EXIT_RISK_REDUCTION+LOT_CONVERSION_DOMINATED+RUNTIME_BUY_NO_FILL+ADD_CONVERSION_WEAKNESS,
  2022-09-22: MULTI_CAUSAL:SELL/EXIT_RISK_REDUCTION+LOT_CONVERSION_DOMINATED+RUNTIME_BUY_NO_FILL+ADD_CONVERSION_WEAKNESS,
  2022-09-26: MULTI_CAUSAL:BEAR_WEAK_MARKET+LOT_CONVERSION_DOMINATED+ADD_CONVERSION_WEAKNESS,
  2022-09-27: MULTI_CAUSAL:BEAR_WEAK_MARKET+LOT_CONVERSION_DOMINATED+ADD_CONVERSION_WEAKNESS
}
```

The 38.11% exposure trough on 2022-09-20 followed SELL/EXIT risk reduction,
weak Correction context, and multiple Runtime BUY intents that did not fill.

## Compound Capital Observation

```text
COMPOUND_CAPITAL_SCALING_OBSERVED = PARTIAL
```

Equity above 1,000,000 JPY was visible to PC/PS, and `94320` did scale from
800 to 1100 shares by two BUY_ADD fills. However, scaling was narrow rather
than broad: average exposure fell to 59.89%, BUY_NEW conversion was 10 fills
from 87 PC-positive intents, and the strict one-lot cohort did not become a
multi-lot winner cohort.

## Production Integrity

```text
AK1T_LOT_ECONOMICS_FRICTION_LINEAGE_CONSISTENT = YES
AK1U_ONE_LOT_CONTRACT_PRESERVED = YES
AK2_ZERO_TO_ONE_LOT_SCOPE_PRESERVED = YES
AK3R2B_CASH_PRUNING_OBSERVED = YES
AK3R2C1_SUBMIT_QUANTITY_HANDOFF_PRESERVED = YES
AK5R_VALUATION_CONTINUITY_SCOPE_UNCHANGED = YES
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
```

## Required Final Judgments

```text
WINDOW_RETURN_DELTA = -3.601 percentage points
WINDOW_MAX_DRAWDOWN = -3.53%
WINDOW_AVG_EXPOSURE = 59.89%
MARKET_OPPORTUNITY_WEAKNESS_EXPLAINS_LOW_EXPOSURE = PARTIAL
CASH_PRUNED_COUNT = 2
CASH_CONSTRAINT_PRIMARY_LOW_EXPOSURE_CAUSE = PARTIAL
CAPITAL_FRAGMENTATION_CONFIRMED = PARTIAL
LOSS_CONTAINMENT = PARTIAL
MID_RUN_STAGNATION_PRIMARY_CLASS = CAPITAL_CONVERSION_LIMITATION
MID_RUN_STAGNATION_SECONDARY_CLASSES = [MARKET_DRIVEN, STRATEGY_DRIVEN_BUT_LEGITIMATE, WINNER_CONCENTRATION_INSUFFICIENT]
COMPOUND_CAPITAL_SCALING_OBSERVED = PARTIAL
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = NO
IMPLEMENTATION_REPAIR_JUSTIFIED = INSUFFICIENT_EVIDENCE
```

## Deliverables

```text
docs/phase_reports/phase30_ak6_mid_run_low_exposure_growth_stagnation_attribution_audit.md
reports/phase_reports/phase30_ak6_mid_run_low_exposure_growth_stagnation_attribution_audit.json
reports/phase_reports/phase30_ak6/evidence_summary.json
```

## Recommended Next Task

```text
Phase30-AK7 - Capital Conversion / ADD Fill Effectiveness Design Audit
```

