# Phase30-AK0 - Running 200BD Loss / Candidate-to-Capital / Valuation Integrity Attribution Audit

## Primary Judgment

```text
AUDIT_CUTOFF_DATE = 2023-09-06
COMPLETED_BUSINESS_DAYS = 265
LARGE_LOSS_VALUATION_INTEGRITY = PASS
LONG_HORIZON_HYBRID_ACTION_EFFECTIVE = YES
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = NO
RUN_RECOMMENDATION = CONTINUE_CURRENT_200BD_RUN
NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30_AK0
```

The running 200BD run was audited read-only through the completed business-day
authority captured at audit start. The target run was not stopped, resumed,
replayed, repaired, or mutated.

The dominant structure is not a valuation/accounting recurrence. The loss is
multi-causal: real economic entry losses, candidate-to-capital attrition, weak
ADD conversion for winners, and only mixed payoff asymmetry.

```text
DOMINANT_PERFORMANCE_STRUCTURE =
MULTI_CAUSAL: REAL_ECONOMIC_LOSSES + CANDIDATE_TO_CAPITAL_ATTRITION
+ INEFFECTIVE_ADD_CONVERSION + MIXED_PAYOFF_ASYMMETRY
```

## Current Run Performance Snapshot

| Metric | Value |
| --- | ---: |
| Initial equity | 1,000,000 |
| Cutoff equity | 858,340 |
| Total return | -14.17% |
| Max drawdown | -21.27% on 2023-06-01 |
| Average cash ratio | 63.48% |
| Average exposure | 36.52% |
| Median exposure | 34.26% |
| Max exposure | 76.62% |
| Final cash | 432,820 |
| Final exposure | 49.57% |

Position-count distribution:

```text
1: 13 days
2: 46 days
3: 62 days
4: 69 days
5: 28 days
6: 19 days
7: 15 days
8: 7 days
9: 6 days
```

Performance evidence was used only for attribution and audit routing.

```text
PERFORMANCE_USED_FOR_PARAMETER_SELECTION = FALSE
```

## Large Loss Day Detection

Top audited losses:

| Date | Daily PnL | Equity | Exposure | Classification |
| --- | ---: | ---: | ---: | --- |
| 2023-05-23 | -102,800 | 823,660 | 53.97% | REAL_ECONOMIC_LOSS |
| 2023-03-03 | -61,000 | 885,910 | 76.62% | REAL_ECONOMIC_LOSS |
| 2022-09-15 | -27,230 | 976,010 | 59.20% | REAL_ECONOMIC_LOSS |
| 2023-02-21 | -25,190 | 939,030 | 59.22% | REAL_ECONOMIC_LOSS |

For these days, valuation rows showed fresh current quotes, clear corporate
action ambiguity status, adjusted quantity/valuation basis alignment, and PASS
valuation price authority. Accounting reconciled at symbol net contribution
level once same-day fill cash effects were included.

## Symbol-Level PnL Decomposition

Net contribution includes market value change plus same-day execution cash
effect. This is the reconciliation basis for entry-day losses.

| Date | Main contributor | Net contribution | Evidence |
| --- | ---: | ---: | --- |
| 2023-05-23 | 67310 | -100,000 | BUY 100 @ 3,000, same-day valuation 2,000 |
| 2023-05-23 | 94320 | -1,800 | 1,200 shares, 168.2 -> 166.7 |
| 2023-05-23 | 27620 | -1,000 | 100 shares, 236 -> 226 |
| 2023-03-03 | 59350 | -61,200 | BUY 100 @ 2,652, same-day valuation 2,040 |
| 2023-03-03 | 39450 | -3,400 | 100 shares, 1,469 -> 1,435 |
| 2022-09-15 | 47600 | -23,300 | BUY 100 @ 1,735, same-day valuation 1,502 |
| 2023-02-21 | 42640 | -22,700 | BUY 100 @ 1,487, same-day valuation 1,260 |

Detailed materialized evidence:

```text
reports/phase_reports/phase30_ak0/large_loss_day_analysis.json
reports/phase_reports/phase30_ak0/symbol_pnl_decomposition.json
```

## Valuation / Accounting Integrity

```text
LARGE_LOSS_VALUATION_INTEGRITY = PASS
```

No audited large-loss day showed stale quote, missing quote, corporate-action
ambiguity, basis mismatch, or accounting reconciliation defect.

2023-05-23 / 67310 is the highest-priority sentinel. The evidence supports an
entry loss, not recurrence of the Phase29 valuation alternation defect:

```text
quantity = 100
BUY price = 3,000
valuation price = 2,000
quantity_basis = ADJUSTED
valuation_price_basis = ADJUSTED
valuation_price_authority = PASS
valuation_quote_status = FRESH_CURRENT_QUOTE
corporate_action_ambiguity_status = CLEAR
net contribution = -100,000
```

## Candidate Hybrid Long-Horizon Action Effect

```text
LONG_HORIZON_HYBRID_ACTION_EFFECTIVE = YES
```

The hybrid Candidate Top50 path remained action-effective over the cutoff
window:

| Metric | Value |
| --- | ---: |
| Candidate days materialized | 265 |
| Top50 changed days | 225 |
| Changed-day rate | 84.91% |
| Avg added symbols/day | 6.01 |
| Avg removed symbols/day | 6.01 |

No leakage flags were observed in candidate coverage evidence.

## Candidate -> Capital Funnel

Hybrid-added symbol-days reached downstream components consistently, but most
did not become actual capital.

| Stage | Count | Rate vs hybrid-added |
| --- | ---: | ---: |
| Hybrid-added symbol-days | 1,592 | 100.00% |
| Opportunity reached | 1,592 | 100.00% |
| SI / Buy Quality reached | 1,592 | 100.00% |
| PC competition reached | 1,592 | 100.00% |
| PC positive | 474 | 29.77% |
| PS positive | 138 | 8.67% |
| Runtime BUY / fill | 4 | 0.25% |

```text
HYBRID_ADDED_TO_PC_POSITIVE_RATE = 0.2977
HYBRID_ADDED_TO_BUY_FILL_RATE = 0.0025
```

Dominant blockers:

| Blocker | Count |
| --- | ---: |
| SELECTION_QUALITY_CAUTION | 1,026 |
| buy_quality_rejected / related PC reasons | 85 |
| REENTRY_OR_LIFECYCLE_CONSTRAINT | 50 |
| PRICE_TICK_RISK | 13 |
| ALLOCATION_CAP | 4 |

Interpretation: AJ2R3/AJ3B improved Candidate membership, and those candidates
do reach PC. The material bottleneck is downstream conversion from PC-positive
or PS-positive intent into executable fills, plus many hybrid-added names still
being caution/quality-reduced rather than deployable.

## Winner / Loser Structure

| Metric | Value |
| --- | ---: |
| Campaigns | 85 |
| Open / closed | 4 / 81 |
| Winners / losers | 39 / 40 |
| Win rate | 45.88% |
| Average winner | +8.43% |
| Average loser | -7.53% |
| Median winner | +5.63% |
| Median loser | -7.80% |
| Payoff ratio | 1.12 |
| Profit factor | 1.09 |

```text
PAYOFF_ASYMMETRY = MIXED
```

The payoff profile is not structurally broken, but it is not strong enough to
overcome large entry losses and low capital conversion.

## HOLD / ADD / REDUCE / EXIT Attribution

PM produced ADD frequently, but ADD did not reliably become incremental
capital:

```text
PM ADD count = 268
PC-positive ADD = 9
PS-positive ADD = 5
BUY_ADD fill = 0
```

```text
WINNER_AMPLIFICATION = INEFFECTIVE
LOSS_CONTAINMENT = PARTIAL
```

Loss containment is partial because audited losses are real and several are
entry-day losses, but no accounting or valuation defect was found. Winner
amplification is ineffective because repeated PM ADD evidence did not become
BUY_ADD fills.

## 94320 Campaign Deep Audit

```text
94320_CAMPAIGN_CLASSIFICATION = MIXED
```

94320 is not a stale loser:

```text
opened_business_date = 2022-08-10
audit_calendar_age_days = 392
quantity = 1,200
market_value = 202,920
portfolio weight = 23.64%
campaign return = +12.27%
observed MFE = +16.98%
observed giveback = 11.75 percentage points
recent PM action = ADD
CQ = PASS
Downside Risk = PASS
```

However, the campaign is not fully healthy amplification either. PM repeatedly
emits ADD with strong continuation / no-loss averaging evidence, while PC/PS
preserve baseline quantity and no BUY_ADD fill occurs. That makes 94320 a
positive long-lived winner with partial capital lock and incomplete
amplification, not a proven stale survivor.

## Long-Lived Campaign Concentration

```text
LONG_LIVED_CAMPAIGN_CAPITAL_LOCK = PARTIAL
```

Only four campaigns are open at cutoff. 94320 is the largest and oldest open
campaign, so it is the main concentration object. Its positive return argues
against a stale-survivor classification; its 23.64% weight and failed ADD
conversion argue for partial capital-lock diagnostics.

## Exposure Timing

```text
LOSS_DAY_EXPOSURE_CAUSALITY =
PRICE_DECLINE_DOMINATED; major audited loss days did not require pre-loss
exposure increase as primary explanation
```

For 2023-03-03 and 2023-05-23, exposure increased on the loss day because new
BUY fills occurred and were immediately marked below entry. The loss was not a
valuation artifact and not merely exposure-ratio math from price declines.

Key examples:

```text
2023-03-03: BUY notional 265,200; 59350 net contribution -61,200
2023-05-23: BUY notional 300,000; 67310 net contribution -100,000
```

## Market Regime Attribution

All 265 audited days were classified by existing artifacts as `BALANCED`.
Therefore this run does not provide enough internal regime variety to validate
the prior bear-conviction hypothesis.

```text
BEAR_CONVICTION_HYPOTHESIS = INSUFFICIENT
```

## Capital Utilization

```text
CAPITAL_UTILIZATION = MIXED
```

Average exposure is low at 36.52%, but PC-positive opportunities exist on
average 14.92 per day while PS-positive opportunities average only 0.64 per
day and BUY fills average 0.49 per day. This is not simply lack of candidates;
it is candidate-to-capital attrition plus lot/quality/conversion friction.

## Runtime / Authority Integrity

```text
KNOWN_RUNTIME_OR_AUTHORITY_DEFECT = NO
```

Candidate, SI, PC, PS, Runtime, valuation, accounting, and corporate-action
evidence did not show a critical authority defect requiring quarantine of the
running 200BD run.

## Leakage / Evidence Integrity

```text
FUTURE_INFORMATION_USED = FALSE
HISTORICAL_OUTCOME_USED_AS_RUNTIME_INPUT = FALSE
HISTORICAL_OUTCOME_USED_FOR_PRODUCTION_PARAMETER_SELECTION = FALSE
TEST_RESULT_USED_AS_STRATEGY_INPUT = FALSE
```

## Deliverables

```text
docs/phase_reports/phase30_ak0_running_200bd_loss_candidate_to_capital_valuation_integrity_attribution_audit.md
reports/phase_reports/phase30_ak0_running_200bd_loss_candidate_to_capital_valuation_integrity_attribution_audit.json
reports/phase_reports/phase30_ak0/large_loss_day_analysis.json
reports/phase_reports/phase30_ak0/symbol_pnl_decomposition.json
reports/phase_reports/phase30_ak0/candidate_to_capital_funnel.json
reports/phase_reports/phase30_ak0/hybrid_added_blockers.json
reports/phase_reports/phase30_ak0/campaign_payoff_analysis.json
reports/phase_reports/phase30_ak0/94320_campaign_audit.json
reports/phase_reports/phase30_ak0/long_lived_campaign_analysis.json
reports/phase_reports/phase30_ak0/exposure_timing_analysis.json
reports/phase_reports/phase30_ak0/regime_attribution.json
reports/phase_reports/phase30_ak0/capital_utilization_analysis.json
```

## Recommended Next Task

```text
Phase30-AK1 - ADD Conversion / PS Executable Capital Bridge Audit
```

Purpose: investigate why PM ADD and PC-positive evidence rarely become
PS-positive quantity and why no BUY_ADD fill materialized, without using
200BD performance to tune thresholds or weights.
