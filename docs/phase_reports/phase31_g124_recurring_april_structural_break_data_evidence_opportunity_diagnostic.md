# Phase31-G124 — Recurring April Structural Break / Data-Evidence Opportunity Diagnostic

## PRIMARY_JUDGMENT

G124_RECURRING_APRIL_DIAGNOSTIC_NEEDS_NARROWER_EVIDENCE

## Scope

- Task type: READ-ONLY DIAGNOSTIC
- Phase: Phase31
- Primary immutable evidence run: `runtime-test-historical-extended-smoke-20260825T135619843503Z`
- Comparable completed run artifacts available in this workspace: `1`
- Code/config/threshold/score/weight changed: NO
- Fresh-run/resume/replay/long Historical executed: NO
- Run state mutated: NO

G124 used existing completed artifacts only. Historical outcome was used for
characterization of the recurring-April hypothesis, not for production parameter
selection.

## Source Basis

Read and used:

- `docs/phase_reports/phase31_g120_post_g119_long_horizon_performance_capital_characterization.md`
- `docs/phase_reports/phase31_g121_campaign_level_add_identity_winner_scaling_audit.md`
- `docs/phase_reports/phase31_g122_campaign_lifecycle_add_event_history_materialization_repair.md`
- `docs/phase_reports/phase31_g123_post_g122_validation_and_april_structural_break_entry_contract.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/phase_reports/phase30_final_summary_and_phase31_handoff.md`

Current SoT boundaries preserved:

- Candidate / Opportunity score is PIT relative ranking evidence, not direct
  BUY, target-weight, or quantity authority.
- Strategy Intelligence and Campaign lifecycle are evidence authorities; G122
  changes current-system campaign ADD history semantics.
- PM owns existing-position directional ADD/HOLD/REDUCE/EXIT action intent.
- Market Quality is capital pacing context, not a hard BUY gate.
- Risk Pacing and capital budget are Portfolio Policy deployment-intensity
  authorities.
- Portfolio Construction owns allocation / target weight.
- Position Sizing owns discrete quantity.
- Runtime must not re-decide capital priority.
- PIT / temporal authorities keep business date, feature date, market date,
  strict-prior/current state, valuation date, and freshness distinct.

## Evidence Runs

| Run ID | Artifact status | Completed evidence range | Use in G124 |
|---|---|---|---|
| `runtime-test-historical-extended-smoke-20260825T135619843503Z` | Completed immutable daily artifacts available | `2022-10-03` through `2023-09-01` daily directory evidence; 2023-09-01 lacks valuation/equity in the inspected completed set | Primary diagnostic run |
| `runtime-test-historical-extended-smoke-20260825T135219034700Z` | `PRECONDITION_FAILURE`, `completed_business_day_count = 0` | none | Not comparable |

```text
COMPARABLE_RECURRING_BREAK_RUN_COUNT = 1
```

The operator-observed recurrence is plausible and consistent with prior reports,
but this workspace contains only one comparable completed immutable run artifact
for direct G124 calculation. Therefore G124 can characterize the April break in
the primary run, but cannot prove recurrence across multiple artifact runs.

## Structural Window Performance

Fixed windows were used; no date optimization was performed.

| Window | Dates | BD | Start equity | End equity | Return | Peak | Trough | Avg exposure | Avg cash |
|---|---|---:|---:|---:|---:|---|---|---:|---:|
| PRE | 2023-03-01 to 2023-03-31 | 22 | 1,263,300 | 1,436,830 | +13.74% | 2023-03-31 / 1,436,830 | 2023-03-14 / 1,225,280 | 73.29% | 354,045 |
| TRANSITION | 2023-04-03 to 2023-04-28 | 20 | 1,455,470 | 1,327,650 | -8.78% | 2023-04-10 / 1,479,100 | 2023-04-21 / 1,299,890 | 46.80% | 724,250 |
| POST_1 | 2023-05-01 to 2023-05-31 | 20 | 1,331,710 | 1,378,580 | +3.52% | 2023-05-30 / 1,384,630 | 2023-05-15 / 1,293,850 | 61.26% | 514,866 |
| POST_2 | 2023-06-01 to 2023-06-30 | 22 | 1,341,730 | 1,401,020 | +4.42% | 2023-06-19 / 1,457,310 | 2023-06-01 / 1,341,730 | 72.21% | 388,629 |
| POST_3 | 2023-07-03 to 2023-07-31 | 20 | 1,414,630 | 1,405,480 | -0.65% | 2023-07-19 / 1,425,190 | 2023-07-27 / 1,400,560 | 77.89% | 312,246 |
| POST_4 | 2023-08-01 to 2023-08-31 | 22 valued days | 1,418,710 | 1,462,540 | +3.09% | 2023-08-31 / 1,462,540 | 2023-08-03 / 1,391,670 | 79.51% | 289,798 |

Primary-run April pattern:

- Strong March accumulation exists.
- April peak occurs at `2023-04-10`.
- April drawdown is large and fast.
- May/June recover materially but do not make a new ATH by June.
- July is sideways/slightly negative.
- August improves and approaches the April ATH but remains below the `2023-04-10`
  peak in the inspected valued artifacts.

```text
APRIL_STRUCTURAL_PATTERN_RECURRENCE = RUN_SPECIFIC
```

`RUN_SPECIFIC` here means "confirmed in the primary run only"; recurrence
requires another comparable completed artifact run.

## Raw Data / PIT Continuity

Representative actual source-manifest checks:

| Date | Candidate | Opportunity | Market quotes | PIT validation | Latest fallback | Future rows |
|---|---|---|---|---|---|---:|
| 2023-03-16 | PASS / business-date valid | PASS / business-date valid | PASS / max source date 2023-03-16 | PASS | false | 0 |
| 2023-04-14 | PASS / business-date valid | PASS / business-date valid | PASS / max source date 2023-04-14 | PASS | false | 0 |
| 2023-06-16 | PASS / business-date valid | PASS / business-date valid | PASS / max source date 2023-06-16 | PASS | false | 0 |

Market refresh / feature refresh representative checks:

| Date | Market data until | Latest listed info | Latest normalized quotes | Feature refresh |
|---|---|---|---|---|
| 2023-03-16 | 2023-03-16 | 2023-03-16 | 2023-03-16 | `FEATURES_READY` |
| 2023-04-14 | 2023-04-14 | 2023-04-14 | 2023-04-14 | `FEATURES_READY` |
| 2023-06-16 | 2023-06-16 | 2023-06-16 | 2023-06-16 | `FEATURES_READY` |

Market Quality and Risk Pacing evidence completeness:

| Window | Market Quality completeness | Risk Pacing completeness |
|---|---|---|
| PRE | COMPLETE on 22/22 | COMPLETE on 22/22 |
| TRANSITION | COMPLETE on 20/20 | COMPLETE on 20/20 |
| POST_1 | COMPLETE on 20/20 | COMPLETE on 20/20 |
| POST_2 | COMPLETE on 22/22 | COMPLETE on 22/22 |
| POST_3 | COMPLETE on 20/20 | COMPLETE on 20/20 |
| POST_4 | COMPLETE on 22/23; one incomplete/unvalued final day | COMPLETE on 22/23; one incomplete/unvalued final day |

No April step-change raw data defect or PIT temporal discontinuity was found in
the inspected artifacts. Source-manifest `strategy_decision_trace` /
`strategy_shadow_summary` component entries were consistently `MISSING` across
all windows and therefore are not an April-specific break signal.

```text
RAW_DATA_STRUCTURAL_BREAK = NO
PIT_TEMPORAL_STRUCTURAL_BREAK = NO
EVIDENCE_AVAILABILITY_BREAK = NO
```

## Candidate / Opportunity Differentiation

Daily `buy_quality_decisions` and PC member evidence show the opportunity
frontier changes materially after March.

| Window | Avg candidate rows | Avg top score | Avg median score | Avg top1-top5 spread | Avg top1-top10 spread |
|---|---:|---:|---:|---:|---:|
| PRE | 50.0 | 0.2971 | -0.3738 | 0.0803 | 0.1650 |
| TRANSITION | 50.0 | 0.2510 | -0.3806 | 0.1082 | 0.2754 |
| POST_1 | 50.0 | 0.3856 | -0.3518 | 0.1542 | 0.3559 |
| POST_2 | 50.0 | 0.4649 | -0.3563 | 0.2593 | 0.3683 |
| POST_3 | 50.0 | 0.4785 | -0.4850 | 0.2931 | 0.5293 |
| POST_4 | 47.8 | 0.3709 | -0.4692 | 0.1647 | 0.3820 |

This does not look like score compression after April. Top-vs-rest separation
generally increases in POST windows. However, higher apparent top-score
differentiation does not automatically translate into durable Winner creation.
The better supported statement is:

- The candidate frontier's distribution shifts after April.
- The issue is not a simple "all scores compressed by market uplift" pattern.
- Current evidence still may be weak at distinguishing durable cross-sectional
  Winners from market-wide or short-lived strength, but that requires a narrower
  decision-time Winner differentiation study.

Quality-class counts from PC were dominated by `CAUTION_CONTINUATION`, with
`COMPARABLE_MARGINAL` rising in some POST windows and stronger classes appearing
more often in July/August:

| Window | Main PC quality-class observations |
|---|---|
| PRE | `CAUTION_CONTINUATION 786`, `COMPARABLE_MARGINAL 119`, `REJECT 34`, `STRONG 1` |
| TRANSITION | `CAUTION_CONTINUATION 794`, `COMPARABLE_MARGINAL 59`, `REJECT 51` |
| POST_1 | `CAUTION_CONTINUATION 755`, `REJECT 73`, `COMPARABLE_MARGINAL 47` |
| POST_2 | `CAUTION_CONTINUATION 848`, `COMPARABLE_MARGINAL 83`, `REJECT 49` |
| POST_3 | `CAUTION_CONTINUATION 681`, `COMPARABLE_MARGINAL 118`, `COMPARABLE_HIGH 22`, `STRONG 11` |
| POST_4 | `CAUTION_CONTINUATION 834`, `COMPARABLE_MARGINAL 122`, `COMPARABLE_HIGH 7`, `STRONG 4` |

```text
CANDIDATE_DIFFERENTIATION_STRUCTURAL_SHIFT = PARTIAL
MARKET_WIDE_UPLIFT_DIFFERENTIATION_HYPOTHESIS = NOT_SUPPORTED
```

The hypothesis is `NOT_SUPPORTED` in its score-compression form. A weaker
hypothesis, "existing evidence may not separate durable Winners well after
April", remains research-worthy.

## RANGE Winner Episode vs Weak Episodes

| Episode | Dates | Return | Avg exposure | MQ distribution | Risk Pacing | Avg top score | Avg median score | BUY_NEW fills | Runtime BUY / ADD | PM ADD |
|---|---|---:|---:|---|---|---:|---:|---:|---:|---:|
| RANGE_STRONG | 2023-03-15 to 2023-03-23 | +12.76% | 74.18% | `SHORT_TERM_BREADTH_BREAKDOWN 4`, `CONFLICTED 2` | `CAUTIOUS 6` | 0.3720 | -0.3310 | 15 | 15 / observed planning ADD present | 7 |
| BULL_WEAK_1 | 2023-04-12 to 2023-04-20 | -4.35% | 52.18% | `HEALTHY_EXPANSION 6`, `RECOVERY_INCOMPLETE 1` | `NORMAL 6`, `GRADUAL 1` | 0.2074 | -0.4150 | 15 | 15 / observed planning ADD present | 3 |
| BULL_WEAK_2 | 2023-05-11 to 2023-05-18 | -3.98% | 37.85% | `CONFLICTED 4`, `SHORT_TERM_NARROWING 2` | `CAUTIOUS 6` | 0.4734 | -0.3453 | 9 | 9 / observed planning ADD present | 6 |
| BULL_WEAK_3 | 2023-06-13 to 2023-06-27 | -0.70% | 67.34% | `HEALTHY_EXPANSION 7`, `CONFLICTED 2`, `BREADTH_BREAKDOWN 2` | `NORMAL 7`, `CAUTIOUS 4` | 0.4544 | -0.3622 | 17 | 17 / observed planning ADD present | 24 |

Decision-time difference:

```text
RANGE_VS_BULL_PRIMARY_DECISION_TIME_DIFFERENCE =
March's strongest realized episode occurred despite defensive/CAUTIOUS market
context because a small set of positions/candidates converted into concentrated
Winners. Later healthy/BULL-like windows still produced BUYs and high top
scores, but did not convert as efficiently into durable concentrated Winners;
the difference is not Market Quality hard gating, raw data availability, or
PIT freshness. It is most consistent with opportunity/Winner differentiation
and retention/scaling quality needing a narrower decision-time audit.
```

## Market Quality Continuity

Market Quality labels and raw completeness are not April-defective. The
environment does shift: April transitions through recovery/incomplete, breadth
breakdown, healthy expansion, and a final healthy-recovery day. POST months
remain mixed rather than permanently bullish.

| Window | Market Quality counts | Risk Pacing counts |
|---|---|---|
| PRE | `CONFLICTED 6`, `HEALTHY_EXPANSION 6`, `BREADTH_BREAKDOWN 6`, `RECOVERY_INCOMPLETE 4` | `CAUTIOUS 12`, `NORMAL 6`, `GRADUAL 4` |
| TRANSITION | `BREADTH_BREAKDOWN 7`, `HEALTHY_EXPANSION 6`, `RECOVERY_INCOMPLETE 4`, `CONFLICTED 1`, other 2 | `CAUTIOUS 9`, `NORMAL 7`, `GRADUAL 4` |
| POST_1 | `CONFLICTED 6`, `RECOVERY_INCOMPLETE 4`, `BREADTH_BREAKDOWN 4`, `HEALTHY_EXPANSION 3`, `NARROWING 3` | `CAUTIOUS 13`, `GRADUAL 4`, `NORMAL 3` |
| POST_2 | `HEALTHY_EXPANSION 8`, `RECOVERY_INCOMPLETE 6`, `CONFLICTED 3`, `BREADTH_BREAKDOWN 3`, `NARROWING 2` | `CAUTIOUS 8`, `GRADUAL 6`, `NORMAL 8` |
| POST_3 | `RECOVERY_INCOMPLETE 7`, `BREADTH_BREAKDOWN 6`, `CONFLICTED 4`, `HEALTHY_EXPANSION 2`, `NARROWING 1` | `CAUTIOUS 11`, `GRADUAL 7`, `NORMAL 2` |
| POST_4 | `BREADTH_BREAKDOWN 10`, `RECOVERY_INCOMPLETE 7`, `CONFLICTED 4`, `NARROWING 1` plus one incomplete final day | `CAUTIOUS 15`, `GRADUAL 7` plus one incomplete final day |

```text
MARKET_QUALITY_DATA_DEFECT = NO
MARKET_QUALITY_ENVIRONMENT_SHIFT = YES
```

## PM Action Behavior

PM action distribution by fixed windows:

| Window | HOLD | ADD | REDUCE | EXIT |
|---|---:|---:|---:|---:|
| PRE | 135 | 23 | 30 | 45 |
| TRANSITION | 53 | 14 | 24 | 33 |
| POST_1 | 103 | 18 | 26 | 29 |
| POST_2 | 104 | 41 | 37 | 35 |
| POST_3 | 149 | 20 | 27 | 33 |
| POST_4 | 167 | 20 | 30 | 32 |

April has a clear defensive/turnover shift: more EXIT/REDUCE relative to HOLD
than March. June has the highest ADD-intent count, so the post-April issue is
not "PM never asks for ADD."

```text
PM_ACTION_STRUCTURAL_SHIFT = YES
```

## ADD Insufficiency Diagnostic

This is defect archaeology on pre-G122 artifacts only. It must not be treated as
current-system truth because G122 changed campaign ADD history materialization.

| Window | PM ADD intents | Insufficient / unknown / fail-closed | Rate | Dominant observed cause bucket |
|---|---:|---:|---:|---|
| PRE | 23 | 19 | 82.61% | Market/Candidate or upstream ADD evidence state |
| TRANSITION | 14 | 10 | 71.43% | Market/Candidate or upstream ADD evidence state |
| POST_1 | 18 | 6 | 33.33% | Market/Candidate or upstream ADD evidence state |
| POST_2 | 41 | 24 | 58.54% | Market/Candidate or upstream ADD evidence state |
| POST_3 | 20 | 12 | 60.00% | Market/Candidate or upstream ADD evidence state |
| POST_4 | 20 | 13 | 65.00% | Market/Candidate or upstream ADD evidence state |

```text
ADD_INSUFFICIENT_RATE_PRE = 82.61%
ADD_INSUFFICIENT_RATE_TRANSITION = 71.43%
ADD_INSUFFICIENT_RATE_POST = 33.33% to 65.00%, depending on month
ADD_INSUFFICIENT_PRIMARY_CAUSES =
1. Market/Candidate or upstream ADD evidence state
2. Expected-edge / incremental-value unknown or fail-closed fields
3. Other canonical context not separable from pre-G122 aggregate strings without a narrower producer-level audit
ADD_EVIDENCE_DATE_DEPENDENT_BREAK = PARTIAL
```

The ADD insufficiency problem is not April-exclusive; it exists before April and
persists later. This supports G123's instruction to recompute ADD insufficiency
from a Post-G122 run before making current-system claims.

## Capital Deployment Structure

| Window | BUY_NEW fills | Runtime BUY plans | Runtime BUY_ADD plans | Cash-winner days | Avg exposure | Avg cash |
|---|---:|---:|---:|---:|---:|---:|
| PRE | 37 | 86 | 3 | 15 | 73.29% | 354,045 |
| TRANSITION | 36 | 45 | 3 | 13 | 46.80% | 724,250 |
| POST_1 | 32 | 47 | 12 | 16 | 61.26% | 514,866 |
| POST_2 | 34 | 73 | 16 | 14 | 72.21% | 388,629 |
| POST_3 | 36 | 74 | 8 | 11 | 77.89% | 312,246 |
| POST_4 | 33 | 61 | 6 | 18 | 79.51% | 289,798 |

April is under-deployed relative to March and later windows. Post-April
sideways behavior is not persistent under-deployment: exposure returns to
70-80% in June-August while equity remains below the April ATH for much of the
period. This points away from Market Quality hard gating and toward
opportunity/Winner conversion quality, ADD scaling, and retention.

```text
POST_APRIL_CAPITAL_PATTERN = MISALLOCATION
```

`MISALLOCATION` means "capital continued to deploy but did not create/retain
enough durable Winner contribution"; it does not mean a confirmed authority
defect.

## Winner Creation / Scaling / Retention

Primary observations:

- PRE creates strong concentrated gains in March.
- POST continues to create new campaigns and deploy capital, but the conversion
  into durable, concentrated Winners weakens relative to March's burst.
- PM ADD exists after April, including 41 ADD intents in June, but actual
  same-campaign ADD history is pre-G122-defective and must be revalidated
  post-G122.
- April drawdown includes high REDUCE/EXIT pressure and low average exposure.
- Later high exposure with sideways equity suggests retention/scaling quality
  and candidate durability are more material than pure under-deployment.

```text
POST_APRIL_WINNER_CREATION = WEAKER
POST_APRIL_WINNER_SCALING = INCONCLUSIVE
POST_APRIL_PROFIT_RETENTION_ISSUE = PARTIAL
```

Scaling is `INCONCLUSIVE` because G122 invalidates pre-G122 campaign ADD
history as current-system evidence.

## Portfolio Convergence

Month-end holding sets in the primary run:

| Date | Holding count | Holding overlap with prior month |
|---|---:|---:|
| 2023-03-31 | 5 | n/a |
| 2023-04-28 | 8 | 1 symbol, Jaccard 0.083 |
| 2023-05-31 | 10 | 1 symbol, Jaccard 0.059 |
| 2023-06-30 | 9 | 2 symbols, Jaccard 0.118 |
| 2023-07-31 | 12 | 1 symbol, Jaccard 0.050 |
| 2023-08-31 | 13 | 3 symbols, Jaccard 0.136 |

Within the primary run, there is no strong month-end same-symbol convergence.
The operator-observed cross-run convergence cannot be verified without another
completed comparable run artifact in this workspace.

```text
POST_APRIL_PORTFOLIO_CONVERGENCE = PARTIAL
CONVERGENCE_CAUSE = INCONCLUSIVE
```

## Defect Versus Market Reality

Material findings by class:

| Finding | Class |
|---|---|
| Primary run has strong March, April drawdown, and post-April ATH non-recovery/plateau tendency | K / mixed |
| No raw data, PIT, freshness, or Market Quality evidence missingness break around April | not a mandatory defect |
| Candidate score distribution changes but does not simply compress | E / candidate differentiation weakness |
| Market Quality environment shifts but is not a data defect or hard BUY gate | A / genuine market-opportunity shift, with F not confirmed as defect |
| PM action distribution shifts defensively in April | A/I mixed; needs retention audit only if Post-G122 reproduces |
| ADD insufficiency exists across windows but pre-G122 evidence is not current-system truth | G / ADD evidence issue, archaeological only |
| Post-April capital redeploys but does not produce March-like durable concentration | A/E/I mixed |

No mandatory repair boundary is confirmed from the available G124 evidence.

```text
PRIMARY_STRUCTURAL_BREAK_CLASS = K
```

`K` is selected because the best supported explanation is mixed: genuine
environment/opportunity shift plus candidate/Winner differentiation weakness and
pre-G122 ADD observability limitations. Mandatory raw-data, PIT, or propagation
defects were not confirmed.

## Philosophy Conformance

PRE behavior:

- BUY participation captured confirmed strength during the March burst.
- Market Quality did not block profitable participation.
- Runtime materially followed Strategy authority.

POST behavior:

- BUYs and capital deployment continued.
- Cash was not a permanent hard gate.
- Winner creation/durability weakened.
- ADD scaling cannot be judged as current-system behavior until Post-G122 run
  evidence exists.

```text
PRE_APRIL_PHILOSOPHY_CONFORMANCE = PASS
POST_APRIL_PHILOSOPHY_CONFORMANCE = PARTIAL
```

## Mandatory Defect Gate

Confirmed mandatory defects in this G124 evidence:

- raw data missingness: NO
- temporal/PIT defect: NO
- producer/consumer evidence disconnect: NO
- authority propagation defect: NO

```text
MANDATORY_REPAIR_FOUND = NO
RESEARCH_REQUIRED = YES
```

Research is required because the remaining issue is decision-time
cross-sectional Winner differentiation / durability after April, and because
recurrence across multiple completed runs was not artifact-proven in this
workspace.

## Required Judgments

```text
APRIL_STRUCTURAL_PATTERN_RECURRENCE = RUN_SPECIFIC
RAW_DATA_STRUCTURAL_BREAK = NO
PIT_TEMPORAL_STRUCTURAL_BREAK = NO
EVIDENCE_AVAILABILITY_BREAK = NO
CANDIDATE_DIFFERENTIATION_STRUCTURAL_SHIFT = PARTIAL
MARKET_WIDE_UPLIFT_DIFFERENTIATION_HYPOTHESIS = NOT_SUPPORTED
MARKET_QUALITY_DATA_DEFECT = NO
MARKET_QUALITY_ENVIRONMENT_SHIFT = YES
PM_ACTION_STRUCTURAL_SHIFT = YES
ADD_EVIDENCE_DATE_DEPENDENT_BREAK = PARTIAL
POST_APRIL_CAPITAL_PATTERN = MISALLOCATION
POST_APRIL_WINNER_CREATION = WEAKER
POST_APRIL_WINNER_SCALING = INCONCLUSIVE
POST_APRIL_PROFIT_RETENTION_ISSUE = PARTIAL
POST_APRIL_PORTFOLIO_CONVERGENCE = PARTIAL
CONVERGENCE_CAUSE = INCONCLUSIVE
PRIMARY_STRUCTURAL_BREAK_CLASS = K
PRE_APRIL_PHILOSOPHY_CONFORMANCE = PASS
POST_APRIL_PHILOSOPHY_CONFORMANCE = PARTIAL
MANDATORY_REPAIR_FOUND = NO
RESEARCH_REQUIRED = YES
FUTURE_INFORMATION_USED_FOR_PRODUCTION_DECISION = NO
PERFORMANCE_USED_TO_SELECT_PRODUCTION_PARAMETER = NO
```

## Next Task

Exactly one recommended next task:

```text
PHASE31_G125_DECISION_TIME_WINNER_DIFFERENTIATION_DURABILITY_RESEARCH_AUDIT
```

Scope should be READ-ONLY. It should compare March durable Winners against
post-April BUY_NEW / ADD candidates using only decision-time PIT evidence and
must include Winner-side opportunity cost so that any later filter/research idea
does not silently remove valid March-style Winners.

Do not implement a BULL filter, RANGE preference, score threshold, share-price
threshold, Market Quality tuning, or allocation weight change from G124.

## Final Decision

G124_RECURRING_APRIL_DIAGNOSTIC_NEEDS_NARROWER_EVIDENCE
