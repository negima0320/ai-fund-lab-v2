# Phase31-G125 — Decision-Time Winner Differentiation / Durability Research Audit

## PRIMARY_JUDGMENT

G125_EARLY_POST_ENTRY_WINNER_SEPARATION_CONFIRMED_READY_FOR_DECISION_AUDIT

## Scope

- Task type: READ-ONLY RESEARCH AUDIT
- Phase: Phase31
- Primary run: `runtime-test-historical-extended-smoke-20260825T135619843503Z`
- Evidence window: `2023-03-01` through latest completed valued August evidence
- Unit of analysis: actual BUY_NEW resulting campaign
- Code/config/feature/threshold/weight/score changed: NO
- Fresh-run/resume/replay/long Historical executed: NO
- Run state mutated: NO

Historical outcome is used only to label post-hoc descriptive cohorts. No
outcome-derived field, threshold, score, rule, or production parameter is
proposed or selected in G125.

## Source Basis

Read and used:

- `docs/phase_reports/phase31_g120_post_g119_long_horizon_performance_capital_characterization.md`
- `docs/phase_reports/phase31_g121_campaign_level_add_identity_winner_scaling_audit.md`
- `docs/phase_reports/phase31_g122_campaign_lifecycle_add_event_history_materialization_repair.md`
- `docs/phase_reports/phase31_g123_post_g122_validation_and_april_structural_break_entry_contract.md`
- `docs/phase_reports/phase31_g124_recurring_april_structural_break_data_evidence_opportunity_diagnostic.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`

Implementation artifacts were interpreted after the SoT boundaries were fixed:
Candidate/Opportunity Ranking is relative PIT evidence; Strategy Intelligence is
not action authority; PM owns existing-position actions; Portfolio Construction
owns allocation/target weight; Position Sizing owns quantity; Runtime does not
re-decide capital priority.

## Cohort Boundaries

The cohort labels are non-production descriptive buckets, aligned with earlier
Phase31 characterization language:

| Cohort | G125 descriptive rule |
|---|---|
| `DURABLE_WINNER` | campaign duration `>= 6` business days and final/observed campaign relative return `> 0` |
| `SHORT_LIVED_WINNER` | campaign duration `<= 5` business days and return `> 0` |
| `EARLY_FAILURE` | campaign duration `<= 5` business days and return `< 0` |
| `ORDINARY` | all remaining BUY_NEW campaigns, including longer negative/flat and immature open campaigns |

These boundaries are not a production rule.

```text
COHORT_BOUNDARIES_USED_FOR_PRODUCTION = NO
```

## Decision-Time Evidence Inventory

For each BUY_NEW campaign, G125 joined the opened business date / symbol to
existing same-date artifacts:

- `strategy/buy_quality_decisions.json`
- `strategy/portfolio_construction.json`
- `strategy/position_sizing.json`
- `strategy/runtime_planning.json`
- `strategy/market_context.json`
- `strategy/portfolio_policy.json`
- `execution/fills.json`
- latest `positions/position_campaigns.json`

Captured fields include Candidate/Opportunity rank and score, component scores,
BUY Quality band/action, Entry Admission state/action, PC selection tier,
marginal-capital / opportunity quality class, Market Quality, Risk Pacing,
regime, breadth/trend, budget, target weight, quantity, reference price,
lot-feasibility, campaign duration, MFE/giveback, and PM/PC state transitions
at +1/+2/+3/+5BD.

```text
DECISION_TIME_EVIDENCE_INVENTORY_COMPLETE = YES
```

## Cohort Counts

Actual BUY_NEW resulting campaign count in fixed windows:

| Window | Total | Durable Winner | Short-Lived Winner | Early Failure | Ordinary |
|---|---:|---:|---:|---:|---:|
| MARCH | 27 | 5 | 9 | 8 | 5 |
| APRIL | 28 | 3 | 5 | 12 | 8 |
| MAY | 27 | 7 | 5 | 8 | 7 |
| JUNE | 30 | 6 | 9 | 11 | 4 |
| JULY | 32 | 9 | 6 | 12 | 5 |
| AUGUST | 26 | 7 | 6 | 9 | 4 |

```text
MARCH_DURABLE_WINNER_COUNT = 5
POST_APRIL_HIGH_SCORE_NON_DURABLE_COUNT = 33
```

`POST_APRIL_HIGH_SCORE_NON_DURABLE_COUNT` uses the non-production high-score /
high-rank definition: rank `<= 10` or entry score at/above the monthly entry
population upper quartile.

## March Durable Winner Profile

| Entry | Symbol | Rank | Score | BQ score / band | Entry state | MQ | Risk Pacing | Regime | Qty | Duration | Return | MFE / giveback |
|---|---:|---:|---:|---|---|---|---|---|---:|---:|---:|---:|
| 2023-03-01 | 31750 | 34 | -0.4559 | 0.5663 / MEDIUM | CONTINUATION_WITH_CAUTION | CONFLICTED | CAUTIOUS | BULL | 100 | 21 | +4.20% | +5.91% / 2.10% |
| 2023-03-02 | 60260 | 29 | -0.4082 | 0.6002 / MEDIUM | CONTINUATION_WITH_CAUTION | HEALTHY_EXPANSION | NORMAL | BULL | 100 | 8 | +2.66% | +4.82% / 2.17% |
| 2023-03-15 | 70660 | 30 | -0.3236 | 0.5853 / MEDIUM | CONTINUATION_WITH_CAUTION | BREADTH_BREAKDOWN | CAUTIOUS | RANGE | 100 | 14 | +12.23% | +16.30% / 4.17% |
| 2023-03-15 | 72710 | 22 | -0.2110 | 0.6408 / MEDIUM | CONTINUATION_WITH_CAUTION | BREADTH_BREAKDOWN | CAUTIOUS | RANGE | 100 | 9 | +2.28% | +6.85% / 4.57% |
| 2023-03-16 | 43880 | 4 | +0.2951 | 0.7812 / HIGH | CONTINUATION_WITH_CAUTION | BREADTH_BREAKDOWN | CAUTIOUS | RANGE | 100 | 17 | +19.49% | +29.32% / 23.53% |

March durable Winners are not simply "top ranked / high score" entries. Four of
five are rank `> 10`, and four of five have negative uncalibrated opportunity
scores. This is a serious anti-overfit warning against score/rank-only filters.

## Post-April High-Score Non-Durable Examples

Complete count: `33`. Representative rows:

| Entry | Symbol | Cohort | Rank | Score | BQ score / band | Entry state | MQ | Risk | Regime | Duration | Return | MFE / giveback |
|---|---:|---|---:|---:|---|---|---|---|---|---:|---:|---:|
| 2023-04-14 | 45860 | EARLY_FAILURE | 10 | -0.2667 | 0.7385 / HIGH | CONTINUATION_WITH_CAUTION | HEALTHY_EXPANSION | NORMAL | BULL | 3 | -3.57% | -3.57% / 0.00% |
| 2023-04-14 | 94340 | ORDINARY | 6 | -0.1440 | 0.7781 / HIGH | CONTINUATION_WITH_CAUTION | HEALTHY_EXPANSION | NORMAL | BULL | 8 | -0.20% | +1.12% / 1.32% |
| 2023-04-17 | 67310 | ORDINARY | 2 | +0.1178 | 0.7973 / HIGH | CONTINUATION_WITH_CAUTION | HEALTHY_EXPANSION | NORMAL | BULL | 3 | 0.00% | 0.00% / 0.00% |
| 2023-05-02 | 77190 | EARLY_FAILURE | 6 | -0.0134 | 0.7588 / HIGH | CONTINUATION_WITH_CAUTION | RECOVERY_INCOMPLETE | GRADUAL | RECOVERY | 5 | -6.25% | -1.56% / 4.69% |
| 2023-05-25 | 30410 | ORDINARY | 2 | +0.3736 | 0.7967 / HIGH | CONTINUATION_WITH_CAUTION | NARROWING | CAUTIOUS | RANGE | 7 | -14.42% | +1.34% / 15.77% |
| 2023-05-29 | 59550 | ORDINARY | 11 | -0.0699 | 0.7254 / HIGH | HEALTHY_CONTINUATION_ENTRY | BREADTH_BREAKDOWN | CAUTIOUS | BULL | 8 | -12.17% | +36.52% / 48.70% |
| 2023-06-13 | 48910 | EARLY_FAILURE | 16 | -0.1547 | 0.7007 / MEDIUM | HEALTHY_CONTINUATION_ENTRY | CONFLICTED | CAUTIOUS | BULL | 3 | -14.57% | -14.57% / 0.00% |
| 2023-06-15 | 59550 | ORDINARY | 3 | +0.1616 | 0.7971 / HIGH | CONTINUATION_WITH_CAUTION | HEALTHY_EXPANSION | NORMAL | BULL | 7 | -6.00% | +6.00% / 12.00% |
| 2023-07-10 | 72350 | EARLY_FAILURE | 30 | -0.4844 | 0.5557 / MEDIUM | HEALTHY_CONTINUATION_ENTRY | BREADTH_BREAKDOWN | CAUTIOUS | RANGE | 3 | -0.18% | -0.18% / 0.00% |

The high-score non-durable group contains both immediate failures and longer
giveback/late-exit style cases. That argues against a single entry filter.

## Evidence Field Comparison

Durable Winner versus non-durable descriptive distributions:

| Evidence field | Durable Winner distribution | Non-durable distribution | Overlap | Separation strength | Stable across months |
|---|---|---|---|---|---|
| Rank | n=37 median 30, IQR 22-40 | n=133 median 32, IQR 21-39 | High | NONE | NO |
| Opportunity score | median -0.4559, IQR -0.5228 to -0.3604 | median -0.4476, IQR -0.5244 to -0.3181 | High | NONE | NO |
| BUY Quality score | median 0.5698, IQR 0.5159-0.6408 | median 0.5645, IQR 0.5254-0.6623 | High | NONE | NO |
| Relative opportunity component | median 0.3732, IQR 0.2606-0.4734 | median 0.3458, IQR 0.2612-0.4934 | High | WEAK | NO |
| Signal reliability | median 0.5032, IQR 0.3706-0.6256 | median 0.5134, IQR 0.4216-0.6460 | High | NONE | NO |
| Execution feasibility | median 0.6597, IQR 0.6475-0.7044 | median 0.6475, IQR 0.6475-0.6701 | High | WEAK | PARTIAL |
| Momentum component | median 0.5000, IQR 0.5000-1.0000 | median 0.5000, IQR 0.5000-1.0000 | High | NONE | NO |
| Market modifier | median 0.7114, IQR 0.6785-0.7817 | median 0.7015, IQR 0.6760-0.7817 | High | NONE | NO |
| Breadth | median 0.5489, IQR 0.4831-0.6369 | median 0.5580, IQR 0.4703-0.6379 | High | NONE | NO |
| Target weight | median 5.26%, IQR 3.58%-8.52% | median 5.21%, IQR 3.00%-9.97% | High | NONE | NO |
| Reference price | median 688, IQR 417-1133 | median 645, IQR 289-1338 | High | NONE | NO |

Post-March only, the same result holds: durable Winners and non-durable entries
overlap heavily at entry across rank, score, quality, market context, and
quantity evidence.

```text
ENTRY_CONFIRMATION_SEPARATION = WEAK
```

## Score Decomposition

Median component comparison:

| Group | n | Score | BQ score | Rel opp | Signal | Exec feas | Momentum | Market mod | Breadth | Trend |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| March durable Winners | 5 | -0.3236 | 0.6002 | 0.3737 | 0.5542 | 0.6475 | 0.5000 | 0.6928 | 0.5073 | 0.0111 |
| March non-Winners | 22 | -0.3822 | 0.6025 | 0.4048 | 0.5746 | 0.6475 | 0.5000 | 0.6785 | 0.4772 | 0.0041 |
| Post-April durable Winners | 32 | -0.4778 | 0.5632 | 0.3517 | 0.4522 | 0.6634 | 1.0000 | 0.7127 | 0.5563 | 0.0171 |
| Post-April high-score non-durable | 33 | -0.2578 | 0.7007 | 0.5911 | 0.6970 | 0.6475 | 0.5000 | 0.7015 | 0.5489 | 0.0146 |

Ranked post-April high-score drivers:

1. `relative_opportunity_quality`
2. `signal_reliability`
3. `quality_score` aggregation
4. `market_context_quality_modifier`
5. `momentum_trajectory_quality` for a subset, but not consistently

```text
POST_APRIL_HIGH_SCORE_DRIVER =
relative_opportunity_quality > signal_reliability > quality_score >
market_context_quality_modifier > momentum_trajectory_quality
```

Post-April high-score non-durable candidates receive stronger entry scores than
post-April durable Winners. The high score is not durability evidence by itself.

## Rank Calibration

| Period | BUY_NEW campaigns | Top-10 entries | Durable Winners in Top-10 | Top-10 durable rate |
|---|---:|---:|---:|---:|
| MARCH | 27 | 3 | 1 | 33.33% |
| POST-MARCH | 143 | 16 | 3 | 18.75% |

Rank distribution:

- March durable Winners: `1` top-10, `4` rank > 10.
- Post-March durable Winners: `3` top-10, `29` rank > 10.
- Post-March early failures: `3` top-10, `49` rank > 10.

```text
TOP_RANK_WINNER_CONCENTRATION_PRE = 33.33%
TOP_RANK_WINNER_CONCENTRATION_POST = 18.75%
RANK_CALIBRATION_SHIFT = PARTIAL
```

The issue is not simply that top rank became useless after April. Top rank is a
weak durable-Winner discriminator throughout the inspected population.

## Entry Confirmation Quality

Entry-state distributions:

| Field | Durable Winners | Non-durable |
|---|---|---|
| Entry state | `CONTINUATION_WITH_CAUTION 29`, `HEALTHY_CONTINUATION_ENTRY 8` | `CONTINUATION_WITH_CAUTION 117`, `HEALTHY_CONTINUATION_ENTRY 16` |
| PC selection tier | `CAUTION_CONTINUATION 35`, `HIGH_QUALITY_CONTINUATION 2` | `CAUTION_CONTINUATION 127`, `HIGH_QUALITY_CONTINUATION 6` |
| Marginal capital value | `ELIGIBLE_COMPARABLE 28`, `ELIGIBLE_STRONG 8` | `ELIGIBLE_COMPARABLE 110`, `ELIGIBLE_STRONG 16` |
| Opportunity quality class | `COMPARABLE_MARGINAL 28`, `COMPARABLE_HIGH 6`, `STRONG 2` | `COMPARABLE_MARGINAL 110`, `COMPARABLE_HIGH 10`, `STRONG 6` |

Existing entry confirmation evidence overlaps too much to support a safe
entry-only rejection rule.

```text
ENTRY_CONFIRMATION_SEPARATION = WEAK
```

## Immediate Post-Entry Transitions

At +1/+2/+3/+5BD, using each respective date's then-available PM/PC evidence:

| Offset | Durable Winner states | Early Failure states | Interpretation |
|---|---|---|---|
| +1BD | `HELD_SUPPORTIVE 33`, `REDUCE 2`, `ADD 2` | `REDUCE 33`, `HELD_SUPPORTIVE 27` | Early failures already show large REDUCE signal mass. |
| +2BD | `HELD_SUPPORTIVE 33`, `ADD 2`, `REDUCE 2` | `EXIT 33`, `HELD_SUPPORTIVE 16`, `REDUCE 11` | Stronger separation: over half of early failures already EXIT. |
| +3BD | `HELD_SUPPORTIVE 30`, `ADD 3`, `REDUCE 4` | `HELD_SUPPORTIVE 31`, `REDUCE 11`, `EXIT 13`, `MISSING 5` | Mixed, but failure signal persists. |
| +5BD | `HELD_SUPPORTIVE 31`, `ADD 1`, `REDUCE 4`, `EXIT 1` | `HELD_SUPPORTIVE 40`, `MISSING 19`, `EXIT 1` | By definition many early failures are already closed/missing. |

The key evidence separation appears after entry, especially at +1/+2BD, rather
than at the entry decision itself.

```text
EARLY_POST_ENTRY_SEPARATION = MODERATE
```

## Post-April Loss Classes

For post-March losing campaigns:

| Loss class | Count |
|---|---:|
| EARLY_FAILURE | 52 |
| LATE_EXIT | 12 |
| LEGITIMATE_STOP | 10 |

No `SYSTEM_CAUSED` loss bucket was confirmed in G125.

```text
POST_APRIL_LOSS_CLASS_COUNTS =
EARLY_FAILURE 52
LATE_EXIT 12
LEGITIMATE_STOP 10
```

## Winner-Side Opportunity Cost

Simple field screens were tested only as anti-overfit diagnostics. They are not
proposed filters.

| Potential filter field | Failures potentially avoided | Durable Winners potentially lost | March durable Winners lost | Winner PnL at risk estimate | Net direction |
|---|---:|---:|---:|---:|---|
| require rank <= 10 | 68 | 33 | 4 | 241,500 | Unfavorable |
| require quality band HIGH | 67 | 33 | 4 | 241,500 | Unfavorable |
| require positive opportunity score | 75 | 33 | 4 | 241,500 | Unfavorable |
| require HEALTHY_CONTINUATION_ENTRY | 67 | 29 | 5 | 265,930 | Unfavorable |
| require ELIGIBLE_STRONG | 67 | 29 | 5 | 265,930 | Unfavorable |
| exclude BULL | 36 | 17 | 2 | 165,730 | Unfavorable |
| require momentum component = 1.0 | 47 | 19 | 5 | 167,330 | Unfavorable |
| require relative opportunity >= 0.6 | 65 | 32 | 4 | 236,800 | Unfavorable |

Every simple entry-side condition that removes many failures also removes a
large share of durable Winners. This is the central G125 overfit warning.

## BULL vs RANGE Conditional Comparison

Durable Winners occur in both BULL and RANGE:

- Durable Winners: `BULL 17`, `RANGE 14`, `RECOVERY 3`, `CORRECTION 3`.
- Non-durable: `BULL 54`, `RECOVERY 36`, `RANGE 27`, `CORRECTION 14`, `BEAR 2`.

Regime conditions affect the opportunity environment, but entry evidence does
not show a clean regime-conditional Winner discriminator.

```text
WINNER_DIFFERENTIATION_REGIME_DEPENDENT = PARTIAL
```

## Market-Wide Uplift Hypothesis

The stronger hypothesis is not score compression; it is that post-April high
scores may be driven by transient/common strength rather than durable
idiosyncratic strength. Existing artifacts expose market modifier, breadth,
trend, relative-opportunity, and signal components, but they do not provide a
clean already-authoritative idiosyncratic-vs-common decomposition.

Observed:

- Post-April high-score non-durable entries have high relative-opportunity and
  signal-reliability medians.
- Market modifier, breadth, and trend do not separate them from durable Winners.
- Some non-durable BULL entries show high score and high BQ evidence, but
  durable Winners also occur in BULL.

```text
EXISTING_EVIDENCE_SUPPORTS_TRANSIENT_COMMON_UPLIFT = INCONCLUSIVE
```

Do not create a new relative-strength or market-adjusted feature from G125.

## ADD Interaction

Pre-G122 archaeological PM ADD alignment:

| Cohort | Campaign count | Campaigns with later PM ADD | Total PM ADD intents |
|---|---:|---:|---:|
| DURABLE_WINNER | 37 | 3 | 28 |
| SHORT_LIVED_WINNER | 40 | 0 | 0 |
| EARLY_FAILURE | 60 | 0 | 0 |
| ORDINARY | 33 | 4 | 7 |

PM ADD is sparse, but when it appears it is concentrated more in durable or
longer-lived campaigns than in early failures. This suggests PM has some Winner
recognition signal, but G122 means current-system ADD history must be
revalidated in a Post-G122 run.

```text
PM_ADD_INTENT_WINNER_ALIGNMENT = MODERATE
```

## Selection vs Retention

Entry evidence does not reliably separate durable Winners from non-durable
entries. However, early post-entry PM/PC evidence separates many failures by
+1/+2BD. Some non-durable longer campaigns also show meaningful MFE followed by
large giveback, e.g. 59550 and 30410 examples.

```text
POST_APRIL_PRIMARY_EDGE_LEAK = G
SELECTION_VS_RETENTION_PRIMARY = MIXED
```

`G = mixture`: false-positive entries, early failure handling, winner scaling,
and giveback/retention all contribute. The most actionable current evidence is
the +1/+2BD early post-entry separation.

## Existing Evidence Sufficiency

Entry evidence alone is insufficient. Existing evidence appears more useful
after the first one or two business days, when failure campaigns begin emitting
REDUCE/EXIT or deterioration-consistent states while durable Winners mostly
remain held/supportive.

```text
EXISTING_EVIDENCE_WINNER_DIFFERENTIATION = EARLY_HOLD_SUFFICIENT
```

This is not a production implementation claim. It means the next audit should
examine whether existing early post-entry evidence is already consumed correctly
by PM/PC/Runtime, without adding new features or tuning thresholds.

## Philosophy Conformance

The current system participates in confirmed strength and does not simply buy
only top score/rank. That preserved March Winners that rank/score filters would
have removed. However, post-April false positives and early failures are not
cleanly handled at entry, and current ADD/retention conclusions are limited by
pre-G122 campaign-history archaeology.

```text
WINNER_DIFFERENTIATION_PHILOSOPHY_CONFORMANCE = PARTIAL
```

## Mandatory Defect Gate

G125 did not find an authority/consumer defect where existing entry evidence
clearly says one action and PM/PC/PS/Runtime take another. It found a research
result: entry evidence is too overlapping, while early post-entry evidence is
more separable.

```text
MANDATORY_REPAIR_FOUND = NO
RESEARCH_REQUIRED = YES
```

## Required Judgments

```text
DECISION_TIME_EVIDENCE_INVENTORY_COMPLETE = YES
MARCH_DURABLE_WINNER_COUNT = 5
POST_APRIL_HIGH_SCORE_NON_DURABLE_COUNT = 33
POST_APRIL_HIGH_SCORE_DRIVER =
relative_opportunity_quality > signal_reliability > quality_score >
market_context_quality_modifier > momentum_trajectory_quality
RANK_CALIBRATION_SHIFT = PARTIAL
ENTRY_CONFIRMATION_SEPARATION = WEAK
EARLY_POST_ENTRY_SEPARATION = MODERATE
WINNER_DIFFERENTIATION_REGIME_DEPENDENT = PARTIAL
EXISTING_EVIDENCE_SUPPORTS_TRANSIENT_COMMON_UPLIFT = INCONCLUSIVE
POST_APRIL_PRIMARY_EDGE_LEAK = G
PM_ADD_INTENT_WINNER_ALIGNMENT = MODERATE
SELECTION_VS_RETENTION_PRIMARY = MIXED
EXISTING_EVIDENCE_WINNER_DIFFERENTIATION = EARLY_HOLD_SUFFICIENT
WINNER_DIFFERENTIATION_PHILOSOPHY_CONFORMANCE = PARTIAL
MANDATORY_REPAIR_FOUND = NO
RESEARCH_REQUIRED = YES
FUTURE_INFORMATION_USED_FOR_PRODUCTION_DECISION = NO
PERFORMANCE_USED_TO_SELECT_PRODUCTION_PARAMETER = NO
COHORT_BOUNDARIES_USED_FOR_PRODUCTION = NO
```

## Next Task

Exactly one recommended next task:

```text
PHASE31_G126_EARLY_POST_ENTRY_FAILURE_DECISION_CONSUMPTION_AUDIT
```

Scope should be READ-ONLY. It should inspect whether existing +1/+2BD
PM/Strategy Intelligence/PC evidence for early failures is consumed in a way
that matches the Strategy philosophy, without adding a BUY filter, minimum
holding period, score threshold, Market Quality change, or new feature.

## Final Decision

G125_EARLY_POST_ENTRY_WINNER_SEPARATION_CONFIRMED_READY_FOR_DECISION_AUDIT
