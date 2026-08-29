# Phase32-BW — Winner Concentration vs Tail Deployment Contribution Audit

## Executive Summary

This was a READ-ONLY performance characterization of Post-BV run
`runtime-test-historical-extended-smoke-20260828T230436594098Z`.

Audited coverage snapshot:

```text
2022-10-03 through 2022-12-15
completed business days = 51
initial equity = 1,000,000
ending equity = 1,099,730
total return = +99,730 / +9.97%
```

The artifact evidence does not support the hypothesis that 94320 / 94340 were
positive winner-concentration contributors during this audited window. Both
named campaigns were net negative by `2022-12-15`. The ADD-active symbol set was
also net negative. The broad one-lot tail, despite high churn and many losers,
was net positive and supplied most of the run's profit.

This is performance characterization only. No historical outcome was used for
parameter selection, and no production code, config, threshold, model, runtime
state, fresh-run, resume, replay, or backtest was changed or run.

## Run Identity

| Field | Value |
| --- | --- |
| Run | `runtime-test-historical-extended-smoke-20260828T230436594098Z` |
| Start | `2022-10-03` |
| Coverage end used | `2022-12-15` |
| Completed business days | 51 |
| Final valuation artifact | `daily/2022-12-15/current_valuation_refresh/valuation_projection.json` |
| Final holdings/PnL source | `daily/2022-12-15/strategy/portfolio_policy.json` current portfolio summary |

## Contribution Reconciliation

The symbol-level performance reconstruction uses run artifacts only:

- realized contribution: `execution/realized_slices.json`
- open contribution: final current-position `unrealized_pnl`
- trade classification: chronological `execution/fills.json`

The reconstruction reconciles to final equity:

| Measure | Amount |
| --- | ---: |
| Realized slice PnL | 2,280.83 |
| Final unrealized PnL | 97,449.17 |
| Total reconstructed PnL | 99,730.00 |
| Ending equity minus initial equity | 99,730.00 |

## Winner Concentration: 94320 / 94340

### Campaign Contribution

| Symbol | Campaign Result | Realized PnL | Unrealized PnL | Total PnL | Final Qty |
| --- | ---: | ---: | ---: | ---: | ---: |
| 94320 | Open, reduced | -7,189.17 | -4,820.83 | -12,010.00 | 500 |
| 94340 | Closed / EXIT | -1,220.00 | 0.00 | -1,220.00 | 0 |
| Combined | Mixed lifecycle | -8,409.17 | -4,820.83 | -13,230.00 | 500 |

Through the available window, the 94320 / 94340 concentration bucket diluted
portfolio profit rather than contributing positively.

### Quantity Progression

94320 actual fills:

| Date | Action | Quantity | Notional | Price |
| --- | --- | ---: | ---: | ---: |
| 2022-10-05 | NEW | +100 | 15,940 | 159.4 |
| 2022-10-07 | ADD | +300 | 47,340 | 157.8 |
| 2022-10-12 | ADD | +300 | 47,760 | 159.2 |
| 2022-10-20 | ADD | +300 | 48,360 | 161.2 |
| 2022-10-21 | ADD | +100 | 16,420 | 164.2 |
| 2022-10-28 | ADD | +100 | 16,230 | 162.3 |
| 2022-12-06 | REDUCE | -300 | 45,000 | 150.0 |
| 2022-12-08 | REDUCE | -200 | 29,840 | 149.2 |
| 2022-12-09 | REDUCE | -200 | 30,000 | 150.0 |

94340 actual fills:

| Date | Action | Quantity | Notional | Price |
| --- | --- | ---: | ---: | ---: |
| 2022-10-03 | NEW | +100 | 14,460 | 144.6 |
| 2022-10-05 | ADD | +300 | 44,550 | 148.5 |
| 2022-10-06 | ADD | +300 | 44,340 | 147.8 |
| 2022-12-07 | EXIT | -700 | 102,130 | 145.9 |

### Decision-Time ADD Evidence

The ADD decisions were supported by PIT authority evidence at decision time, but
that evidence did not translate into positive realized/unrealized performance by
the coverage end.

Representative accepted ADD evidence:

| Symbol | Date | Lots | Value Range | Evidence Shape |
| --- | --- | ---: | ---: | --- |
| 94320 | 2022-10-07 | 3 | 0.6414 -> 0.6239 | high rank, quality around 0.80, headroom diminishing lot by lot |
| 94320 | 2022-10-12 | 3 | 0.6701 -> 0.6526 | opportunity 0.4255, quality 0.7468, positive requalification component |
| 94320 | 2022-10-20 | 3 | 0.5670 -> 0.5491 | positive ADD evidence, diminishing headroom |
| 94320 | 2022-10-21 | 1 | 0.6008 | lot #2/#3 blocked by cap after BT-style cap propagation |
| 94340 | 2022-10-05 | 3 | 0.4477 -> 0.4314 | accepted before later adverse outcome was knowable |
| 94340 | 2022-10-06 | 3 | 0.5225 -> 0.5063 | accepted with improved requalification component |

The correct characterization is not “94320/94340 were winners and should have
received more capital.” It is: ADD authority successfully concentrated capital
where decision-time evidence ranked it highly, but this sample's resulting
ADD-active campaigns were negative.

## Tail Positions

The broad one-lot tail was noisy but net positive.

| Group | Symbols | Total PnL | Realized | Unrealized | Winners | Losers |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Tail excluding 94320/94340 | 82 | +96,470 | +10,690 | +85,780 | 39 | 33 |
| 100-share first-lot tail | 82 | +96,470 | +10,690 | +85,780 | 39 | 33 |
| Non-ADD symbols | 81 | +101,140 | +10,690 | +90,450 | 39 | 32 |

Top positive tail contributors:

| Symbol | Total PnL | Contribution Type |
| --- | ---: | --- |
| 97310 | +34,700 | open unrealized |
| 92270 | +32,200 | realized |
| 78860 | +22,700 | realized |
| 99840 | +21,500 | open unrealized |
| 92420 | +11,100 | realized |
| 15180 | +9,400 | open unrealized |
| 66320 | +8,400 | open unrealized |
| 30820 | +8,000 | open unrealized |

Largest negative tail contributors:

| Symbol | Total PnL |
| --- | ---: |
| 21380 | -12,700 |
| 78780 | -10,250 |
| 45750 | -7,600 |
| 37790 | -6,700 |
| 45840 | -5,900 |
| 41920 | -5,700 |
| 73560 | -4,800 |
| 58200 | -4,670 |

### Churn / Short-Hold Turnover

Closed-lot holding duration from run fills:

| Origin | Closed Lots | Same Day | Next Day | 2-5BD | 6-20BD | >20BD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| NEW | 72 | 0 | 25 | 35 | 10 | 2 |
| REENTRY | 1 | 0 | 0 | 1 | 0 | 0 |
| ADD | 6 | 0 | 0 | 0 | 0 | 6 |

Tail NEW deployment clearly creates churn: 60 of 72 closed NEW lots exited
within 5 business days. However, the aggregate tail contribution was positive,
so this run does not show tail positions as the primary profit drag.

## ADD Contribution

ADD-active symbols:

| Group | Symbols | Total PnL | Realized | Unrealized | Winners | Losers | ADD Notional |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| All ADD-active symbols | 3 | -17,900 | -8,409.17 | -9,490.83 | 0 | 3 | 320,140 |
| ADD-active excluding 94320/94340 | 1 | -4,670 | 0.00 | -4,670.00 | 0 | 1 | 55,140 |

The ADD-active set was negative through `2022-12-15`. This is not evidence that
ADD should be removed or tuned by hindsight, but it does mean this run does not
support statement A, “ADD improvement is actually contributing to portfolio
profit,” for the audited window.

## Capital Competition And Cash

Across the audited window:

| Accepted Type | Accepted Count | Accepted Notional |
| --- | ---: | ---: |
| NEW_FIRST_LOT | 115 | 5,572,540 |
| REENTRY_FIRST_LOT | 1 | 71,010 |
| ADD_NEXT_LOT | 31 | 493,770 |
| Authorized Cash allocation | n/a | 4,502,225 |

Cash optionality was first-class in the artifact, but it usually behaved as
residual optionality rather than a strong competitor:

| Cash Metric | Count |
| --- | ---: |
| Cash accepted optionality days | 8 |
| Days with budget/cash exhaustion style stop | 26 |
| Cash winner days | 2022-11-17, 2022-11-25, 2022-11-28, 2022-11-29, 2022-11-30, 2022-12-02, 2022-12-05, 2022-12-06 |

Late-November high exposure is explained by the combination of:

- `portfolio_policy.cash_reserve_ratio = 0.0`;
- `target_gross_exposure_ratio = 1.0`;
- Cash value remaining low relative to accepted securities when deployable
  securities existed;
- budget being allocated to available NEW first-lot targets until no feasible
  candidate remained;
- after 2022-11-25, Cash was accepted only because no deployable securities were
  accepted, but the remaining Cash notional was already small.

High-exposure late-November / early-December days:

| Date | Equity | Cash | Exposure | Positions | Authority Accepted | Cash Disposition |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| 2022-11-21 | 1,050,480 | 58,460 | 94.43% | 11 | NEW 2 | securities beat Cash |
| 2022-11-22 | 1,061,530 | 63,660 | 94.00% | 10 | NEW 1 | securities beat Cash |
| 2022-11-24 | 1,071,720 | 12,960 | 98.79% | 11 | NEW 1 | securities beat Cash |
| 2022-11-25 | 1,086,640 | 12,960 | 98.81% | 11 | none | Cash accepted optionality |
| 2022-11-28 | 1,087,160 | 12,960 | 98.81% | 11 | none | Cash accepted optionality |
| 2022-11-29 | 1,084,420 | 31,760 | 97.07% | 10 | none | Cash accepted optionality |
| 2022-11-30 | 1,090,430 | 31,760 | 97.09% | 10 | none | Cash accepted optionality |
| 2022-12-01 | 1,096,350 | 8,360 | 99.24% | 11 | NEW 1 | securities beat Cash |
| 2022-12-02 | 1,094,580 | 8,360 | 99.24% | 11 | none | Cash accepted optionality |

Cash optionality is therefore material as an exposure/risk-shaping behavior, but
the audited performance drag was not unused Cash. The portfolio was profitable
while highly exposed; the weak-Cash issue is mainly a risk/optionality concern.

## Comparative Interpretation

| Hypothesis | Judgment | Evidence |
| --- | --- | --- |
| A. ADD improvement contributed to portfolio profit | Not supported in this window | ADD-active symbols total -17,900 |
| B. Tail NEW deployment diluted winner profit | Not supported as primary drag | 100-share tail total +96,470 despite churn |
| C. Cash optionality is weak | Supported as exposure behavior | Cash reserve 0%, target exposure 100%, late Nov exposure 94-99% |
| D. ADD itself is over-large loss source | Partially supported | ADD-active set negative, but sample is only 3 symbols and hindsight tuning is forbidden |
| E. Mixed | Supported | Tail profitable, ADD-active negative, Cash weak as optionality |

Primary performance drag by artifact evidence:

```text
ADD-active concentrated campaigns, especially 94320 / 94340, plus individual
tail losers; not broad one-lot tail deployment in aggregate.
```

## Recommendation

Do not tune thresholds, marginal-value weights, share counts, or Cash policy
from this performance window. The sample shows that ADD/common-frontier machinery
is operational and should be preserved structurally, but it does not prove ADD
profit contribution in this run.

The next step should be a READ-ONLY semantic audit of why ADD-active candidates
with high decision-time value later became negative, separating:

- valid decision-time evidence that simply lost ex post;
- possible ADD evidence scale mismatch versus NEW;
- whether Cash optionality should require a separate design review as a
  risk/optionality authority, not a hindsight return knob.

## Final Judgments

PHASE32_BW_COVERAGE_END = 2022-12-15

PHASE32_BW_WINNER_CONCENTRATION_CONTRIBUTION = NEGATIVE

PHASE32_BW_TAIL_POSITION_CONTRIBUTION = POSITIVE

PHASE32_BW_ADD_CONTRIBUTION = NEGATIVE

PHASE32_BW_CASH_OPTIONALITY_MATERIAL = YES

PHASE32_BW_LATE_NOV_HIGH_EXPOSURE_PRIMARY_CAUSE = cash_reserve_ratio_0_target_gross_exposure_1_low_cash_value_and_security_deployment_until_no_feasible_candidate_remaining

PHASE32_BW_PRIMARY_PERFORMANCE_DRAG = ADD_ACTIVE_CONCENTRATED_CAMPAIGNS_94320_94340_AND_72730_NOT_TAIL_NEW_AGGREGATE

PHASE32_BW_ADD_IMPROVEMENT_PRESERVE = YES

PHASE32_BW_PRODUCTION_REPAIR_JUSTIFIED = PARTIAL

PHASE32_BW_LONG_RUN_CONTINUE = YES

PHASE32_BW_NEXT_STEP = READ_ONLY_ADD_EVIDENCE_SCALE_AND_CASH_OPTIONALITY_SEMANTIC_AUDIT_WITHOUT_HISTORICAL_OUTCOME_PARAMETER_SELECTION
