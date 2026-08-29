# Phase32-B - Capital Conversion / BULL / Winner Capitalization Deep Audit

## Executive Summary

`Phase32-B` continued the READ-ONLY performance investigation after
`Phase32-A`, focusing on how decision-time opportunities became, or failed to
become, portfolio-moving capital.

The audit confirms a conditional BULL weakness, not a blanket BULL defect.
Plateau BULL episodes include positive controls, but also two material poor
return shapes:

- high exposure / poor return, where capital was deployed but winner/loser
  payoff asymmetry was weak;
- low exposure / poor return, where security demand and fills existed but
  explicit Cash allocation and cautious pacing held back compounding.

The strongest bottleneck is ADD capitalization. In the plateau window,
Position Management emitted `242` ADD intents across `10` symbols, but only
`60` symbol-day ADDs reached PC as considered/competing ADD rows, and only `5`
became positive PC ADD allocations, PS BUY_ADD quantities, runtime BUY_ADD
plans, and same-symbol BUY fills. The primary loss stages were:

1. `PM_ADD -> PC_ADD_CONSIDERATION`;
2. `PC_ADD_COMPETITION -> POSITIVE_ADD_ALLOCATION`.

This is a capital conversion limitation, not a G129 regression. When a positive
ADD allocation reached PS/runtime, the downstream path materialized.

The audit finds material evidence to reconsider high-resolution marginal
capital value as a future architecture candidate, and weaker but still material
evidence to reconsider portfolio rotation. Implementation remains prohibited
by this task.

## Phase32-A Inheritance

`Phase32-A` is accepted as current diagnostic evidence:

```text
PHASE32_A_MEASUREMENT_INTEGRITY = PASS
PHASE32_A_PLATEAU_CONFIRMED = YES
PHASE32_A_CANDIDATE_DISCOVERY_DEFECT = NO
PHASE32_A_POSITION_SIZING_LIMITATION_MATERIAL = NO
PHASE32_A_G129_REGRESSION = NO
PHASE32_A_MANDATORY_STRATEGY_DEFECT = NO
```

Phase32-B did not overturn these findings. It refines the causal explanation:
the plateau was amplified by capital conversion limits around ADD,
PC/MCC/Cash competition, and incumbent capital opportunity-cost representation.

## Measurement Integrity

Target run:

```text
runtime-test-historical-extended-smoke-20260825T235520054579Z
```

Audited range:

```text
2022-10-03 through 2024-02-26
343 completed business days
```

Measurement checks from Phase32-A were reused and spot-extended:

| Check | Result |
| --- | --- |
| Valuation projection | PASS on audited dates |
| Valuation apply postcondition | PASS on audited dates |
| Duplicate execution ids | 0 duplicate days |
| Temporal/future flags in canonical artifact scan | 0 positive flags |
| Plateau shape | confirmed in aggregate equity/cash/market value |

`PHASE32_B_MEASUREMENT_INTEGRITY = PASS`.

## Permanent SoT Correction

Updated:

```text
docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md
```

The document now explicitly records:

- implementation status is `NOT_IMPLEMENTED`;
- current-release status is `DEFERRED / FUTURE_OPTIONAL`;
- Phase31 designed and considered the architecture but intentionally deferred
  implementation because the accepted baseline was strong enough and no
  mandatory defect required the architecture;
- the document is a future design SoT, not an implemented current-production
  authority path;
- reconsideration requires new material evidence.

No architecture, Strategy, PC, PM, PS, Risk Pacing, Runtime, config, model, or
threshold implementation was changed.

## Spring Positive Control

Spring acceleration (`2023-03-01` to `2023-05-30`) converted opportunity into
portfolio-moving profit:

| Metric | Spring |
| --- | ---: |
| Start equity | 1,206,160 |
| End equity | 1,806,180 |
| Return | +49.75% |
| Avg exposure | 72.2% |
| BUY / SELL fills | 92 / 96 |
| BUY / SELL notional | 9,940,000 / 9,784,600 |
| Daily gains above 50k | 8 |
| Campaigns opened | 80 |
| Campaigns >= +20% | 7 |
| Campaign MFE >= +20% | 14 |

Spring top winners had both large returns and portfolio-moving entry notional:

| Symbol | Open | Close | Campaign Return | Buy Notional | Approx PnL |
| --- | --- | --- | ---: | ---: | ---: |
| 59350 | 2023-03-22 | 2023-04-20 | +104.99% | 184,400 | 193,600 |
| 67310 | 2023-04-21 | 2023-04-27 | +50.00% | 200,000 | 100,000 |
| 44440 | 2023-03-16 | 2023-03-22 | +51.19% | 109,400 | 56,000 |
| 71160 | 2023-05-11 | 2023-06-20 | +26.27% | 164,800 | 43,300 |
| 64240 | 2023-03-16 | 2023-03-23 | +30.58% | 135,400 | 41,400 |

The key positive-control pattern is not only "Spring had winners." It had
several winners with sufficient initial notional, broad enough exposure, and
large daily PnL bursts to move aggregate equity.

## BULL Episode Decomposition

Plateau BULL episodes from canonical `regime_state`:

| # | Dates | BD | Return | Max Equity | Max DD | Avg Exposure | Avg Cash | Avg Positions | Type |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 2023-06-12 to 2023-07-07 | 20 | -4.36% | 1,834,410 | -6.10% | 72.9% | 479,159 | 10.0 | TYPE_B |
| 2 | 2023-09-01 to 2023-09-27 | 18 | +3.18% | 1,873,370 | -0.70% | 75.3% | 458,307 | 13.6 | TYPE_A |
| 3 | 2023-11-17 to 2023-12-04 | 11 | +1.12% | 1,876,680 | -1.02% | 79.7% | 375,367 | 9.3 | MIXED |
| 4 | 2024-01-10 to 2024-02-07 | 21 | -0.46% | 1,880,730 | -3.97% | 41.1% | 1,083,706 | 6.0 | TYPE_C |
| 5 | 2024-02-16 to 2024-02-26 | 6 | +2.92% | 1,776,560 | 0.00% | 59.1% | 719,162 | 8.7 | TYPE_D |

Type definitions used for this analysis:

- `TYPE_A`: high exposure and >= +2% return.
- `TYPE_B`: high exposure and <= 0% return.
- `TYPE_C`: low exposure and <= 0% return.
- `TYPE_D`: low exposure and >= +2% return.

BULL episode candidate / capital evidence:

| # | Full | Reduced | High Band | Top-Q | Pre Demand | Post Sec | Auth Cash | Risk Pacing | PM ADD | PC/PS/RT ADD | ADD Fill Notional |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| 1 | 6.10 | 25.20 | 9.20 | 0.687 | 0.277 | 0.204 | 0.207 | 10 cautious / 10 normal | 35 | 4 | 26,800 |
| 2 | 6.00 | 24.06 | 8.61 | 0.769 | 0.230 | 0.135 | 0.222 | 12 cautious / 6 normal | 20 | 0 | 0 |
| 3 | 6.64 | 24.36 | 9.09 | 0.718 | 0.151 | 0.113 | 0.191 | 8 cautious / 3 normal | 14 | 0 | 0 |
| 4 | 5.29 | 24.90 | 8.48 | 0.720 | 0.141 | 0.119 | 0.555 | 12 cautious / 9 normal | 26 | 0 | 0 |
| 5 | 6.50 | 25.33 | 9.83 | 0.722 | 0.129 | 0.060 | 0.430 | 6 cautious | 6 | 0 | 0 |

## BULL Failure Mode Classification

`TYPE_A` exists: episode 2 was high-exposure / positive-return. This is a
positive control against blanket BULL weakness.

`TYPE_B` exists: episode 1 had high exposure but poor return. Its campaign
evidence shows selection/payoff/churn weakness rather than insufficient
deployment:

```text
2023-06-12 to 2023-07-07 approximate campaign PnL = +24,230
top winners: 66780, 40520, 71730, 65260
top losers: 95650, 40750, 70330, 50250
BUY notional = 4,194,850
SELL notional = 4,204,260
```

`TYPE_C` exists: episode 4 had low exposure and poor return. Here Cash
authorization was high and campaign selection was negative:

```text
2024-01-10 to 2024-02-07 approximate campaign PnL = -61,910
avg authorized Cash weight = 0.555
avg exposure = 41.1%
top loser: 55740, buy notional 440,000, campaign return -12.8%
```

Conclusion: BULL weakness is conditional and multi-mode. It is not a single
BULL-specific bug and not a blanket requirement to fully invest during BULL.

## Candidate / Opportunity Comparison

Candidate discovery did not collapse in plateau BULL:

```text
average BULL full-eligible rows ~= 5 to 6.6
average BULL reduced-eligible rows ~= 24 to 25
average BULL high-band rows ~= 8.5 to 9.8
top candidate quality ~= 0.687 to 0.769
```

The issue is downstream conversion. Stronger candidate surfaces did not
reliably become large, persistent, asymmetric winner capital.

## Capital Conversion Funnel

Analysis-only diagnostic:

```text
Capital Conversion Ratio =
positive decision-time security capital demand
-> authorized security capital
-> filled BUY capital
```

| Window | Demand Notional | Authorized Security | Filled BUY | Authorized Cash | Auth / Demand | Fill / Demand |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Spring | 27,368,301 | 15,046,037 | 9,940,000 | 23,331,577 | 0.550 | 0.363 |
| Plateau | 65,849,008 | 40,173,609 | 28,015,300 | 104,206,317 | 0.610 | 0.425 |
| Plateau BULL | 27,382,133 | 19,299,329 | 12,516,320 | 44,610,661 | 0.705 | 0.457 |

Aggregate conversion ratio was not worse in plateau. This is important: the
plateau was not caused by a simple "capital cannot get through the pipeline"
failure. The problem is which capital converted, with what payoff asymmetry,
and how little ADD capitalization occurred after positive continuation
evidence.

## NEW Conversion

NEW remained the dominant conversion channel:

| Window | NEW Authorized | NEW Positive Rows | Estimated NEW Fill |
| --- | ---: | ---: | ---: |
| Spring | 15,046,037 | 140 | 9,940,000 |
| Plateau | 40,016,696 | 427 | 27,850,000 |
| Plateau BULL | 19,272,980 | 193 | 12,489,520 |

NEW conversion was active. The later weakness is not a NEW runtime drop.

## ADD Conversion

Plateau ADD funnel:

| Stage | Symbol-Day Count | Unique Symbols | Conversion from PM ADD |
| --- | ---: | ---: | ---: |
| PM ADD | 242 | 10 | 100.0% |
| PC ADD considered | 60 | 9 | 24.8% |
| PC ADD competitor | 60 | 9 | 24.8% |
| PC positive ADD allocation | 5 | 3 | 2.1% |
| PS positive BUY_ADD | 5 | 3 | 2.1% |
| Runtime BUY_ADD | 5 | 3 | 2.1% |
| Same-symbol ADD fill match | 5 | 3 | 2.1% |

ADD notional:

| Window | PC ADD Authorized | ADD Fill Notional |
| --- | ---: | ---: |
| Spring | 0 | 0 |
| Plateau | 156,913 | 165,300 |
| Plateau BULL | 26,348 | 26,800 |

This is the cleanest capital-conversion bottleneck. ADD intent existed often,
but almost never became portfolio-moving incremental capital.

## ADD Suppression Decomposition

Primary ADD loss stages:

| Loss Stage | Count |
| --- | ---: |
| PM ADD not represented as PC ADD consideration | 182 |
| PC ADD competitor but no positive ADD allocation | 55 |

Representative PC no-allocation reasons:

- `ADD_INSUFFICIENT_EVIDENCE`
- `ADD_LOST_TO_NEW_BUY`
- `ADD_LOST_TO_CASH`
- `ADD_NOT_AVAILABLE`
- `ADD_NO_POSITIVE_DELTA`
- `REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION`

This means the ADD issue is not primarily PS, Runtime, Submit, or Fill. It is
upstream of executable quantity: PM ADD intent is often not accepted into the
capital frontier, and when it is, it frequently loses to NEW or Cash.

## Cash Competition

Cash was retained mainly through PC/MCC/Risk Pacing competition rather than
candidate absence.

Plateau:

```text
avg authorized Cash weight = 0.317
avg post-security allocation = 0.123
avg pre-demand = 0.202
avg exposure = 62.2%
```

Plateau BULL:

```text
avg authorized Cash weight = 0.430 to 0.555 in low-exposure episodes
avg post-security allocation = 0.060 to 0.119 in low-exposure episodes
```

Primary Cash sources:

- Market Quality reserve / cautious semantics;
- Risk Pacing reserve;
- MCC Cash preference / deferral;
- SELL-generated temporary Cash;
- no positive ADD quantity / no positive ADD allocation;
- residual Cash after allocation.

Cash was not primarily generated by raw candidate shortage.

## Risk Pacing

BULL + high demand + cautious + low post-security examples:

| Date | MQ | Pre | Post | Cash Alloc | Exposure | Cash | Candidate Evidence | Classification |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 2023-06-29 | SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH | 0.393 | 0.030 | 0.306 | 77.7% | 391,300 | 7 full / 28 reduced / 10 high | appropriate or unresolved; high exposure |
| 2023-07-07 | SHORT_TERM_BREADTH_BREAKDOWN | 0.301 | 0.067 | 0.338 | 68.8% | 541,860 | 1 full / 16 reduced / 2 high | possibly overconservative |
| 2023-09-12 | SHORT_TERM_BREADTH_BREAKDOWN | 0.364 | 0.067 | 0.280 | 78.5% | 400,040 | 5 full / 23 reduced / 8 high | appropriate or unresolved; high exposure |
| 2023-09-13 | SHORT_TERM_BREADTH_BREAKDOWN | 0.331 | 0.052 | 0.272 | 78.3% | 402,990 | 5 full / 27 reduced / 10 high | appropriate or unresolved; high exposure |
| 2023-09-14 | CONFLICTED_MARKET_STRUCTURE | 0.296 | 0.000 | 0.365 | 81.0% | 354,540 | 5 full / 24 reduced / 9 high | appropriate or unresolved; high exposure |

Risk Pacing materially suppressed BULL capital conversion on some days, but
most high-demand/low-post BULL examples also had already-high exposure and
weak/conflicted Market Quality. Only `2023-07-07` is a stronger
possibly-overconservative example in this read-only audit.

## PC / MCC

PC/MCC is a material bottleneck, but not necessarily a defect.

Mechanism:

```text
positive candidate/PM evidence
-> pre-demand exists
-> MCC / Cash preference / cautious market state evaluates frontier
-> PC authorizes less security weight and more Cash
-> PS/runtime only consume authorized positive quantity
```

For ADD specifically, the bottleneck is sharper:

```text
242 PM ADD
-> 60 PC ADD competitors
-> 5 positive ADD allocations
```

The evidence supports a current architecture limitation around how ADD
incremental value competes with NEW and Cash, especially under coarse
`COMPARABLE_MARGINAL` classes.

## Winner Capitalization

Plateau found winners but did not capitalize them symmetrically:

| Window | Winning Campaigns | Losing Campaigns | Avg Winner Buy Notional | Avg Loser Buy Notional | Median Winner Buy | Median Loser Buy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Spring | 39 | 41 | 119,138 | 106,018 | 104,600 | 69,700 |
| Plateau | 90 | 111 | 89,717 | 106,512 | 62,900 | 72,900 |

Plateau top winners:

| Symbol | Return | Buy Notional | Approx PnL | Max Weight | ADD |
| --- | ---: | ---: | ---: | ---: | --- |
| 65730 | +156.6% | 42,340 | 66,320 | 6.4% | none |
| 62280 | +20.9% | 249,000 | 52,000 | 16.7% | none |
| 66780 | +24.1% | 193,400 | 46,600 | 14.0% | none |
| 27080 | +26.5% | 159,700 | 42,300 | 11.0% | none |
| 21340 | +61.1% | 45,000 | 27,500 | 5.0% | 2 ADDs |

Plateau top losers:

| Symbol | Return | Buy Notional | Approx PnL | Max Weight |
| --- | ---: | ---: | ---: | ---: |
| 55740 | -12.8% | 440,000 | -56,500 | 23.5% |
| 74770 | -13.7% | 347,500 | -47,500 | 17.3% |
| 95650 | -9.6% | 347,500 | -33,500 | 19.9% |
| 69420 | -15.2% | 144,500 | -21,900 | 7.1% |
| 92460 | -6.2% | 346,500 | -21,500 | 17.8% |

The asymmetry was not sufficient. Winner initial/total notional was smaller
than loser notional in plateau, and ADD rarely increased winners.

## Winner / Loser Capital Asymmetry

The system did cut and rotate, but capital asymmetry was weak:

- Spring winners had larger average and median capital than plateau winners.
- Plateau losers had larger average and median capital than plateau winners.
- Only one plateau winner in the top set had ADD materialization (`21340`).
- The largest plateau percent winner (`65730`) was too small to move the
  portfolio.

This supports `CAPITALIZATION_FAILURE` and `ADD_FAILURE` more than raw
`DISCOVERY_FAILURE`.

## Winner Retention

Winner retention failure is partially supported, but not as the primary cause.
Plateau had winners with meaningful MFE and some positive campaigns. The
stronger evidence is that winners were not sufficiently capitalized or added
to, while losers received comparable or larger notional. This is capital
asymmetry more than a simple "sell winners too early" defect.

## Incumbent Capital

Long-lived HOLD/ADD evidence remains important. `94320` persisted from
`2022-12-15` through `2024-02-26`, with:

```text
quantity = 600
market value ~= 109,200
relative return ~= +17.23%
MFE ~= +23.16%
ADD history count = 5, latest 2023-02-24
```

Decision-time PM samples continued to show ADD evidence:

```text
strong_trend_continuation
opportunity_rank_still_high
no_loss_averaging
```

This was not irrational HOLD evidence in isolation. The limitation is that
incumbent HOLD capital is not currently represented as a portfolio-wide
competitor against NEW / ADD / Cash. Evidence supports this as a material
capital mobility constraint, but not a contract violation.

## Current Marginal Value Resolution

Current capital classes are too coarse to explain why some ADDs or NEWs should
receive portfolio-moving capital while others should not. Many relevant rows
remain in coarse classes such as `COMPARABLE_MARGINAL`, while the decisive
capital outcome depends on PC/MCC/Cash competition, residual handling, and
allocation rank.

This is materially aligned with the future high-resolution marginal capital
value problem statement, while still respecting that the future architecture is
not implemented.

## High-Resolution Architecture Reconsideration Evidence

The reconsideration gate is met at a material level:

| Gate | Result |
| --- | --- |
| Concrete current capital conversion limitation | YES |
| Reproduces across days/campaigns | YES |
| Notional/allocation material | YES |
| Not explained by PS/runtime bug | YES |
| Not explained by candidate scarcity alone | YES |
| Decision-time finer comparison would matter | YES |
| Future outcome not required for evidence | YES |

Judgment:

```text
PHASE32_B_HIGH_RESOLUTION_VALUE_RECONSIDERATION = MATERIAL_EVIDENCE
```

This is not implementation approval.

## Rotation Reconsideration Evidence

Portfolio Rotation reconsideration evidence is weaker than high-resolution
capital value evidence but still material enough for future shadow work.

The evidence:

- long-lived incumbent capital exists;
- PM HOLD/ADD can remain rational in isolation;
- NEW / ADD alternatives and Cash compete for incremental capital only;
- there is no implemented explicit HOLD external opportunity-cost authority;
- plateau shows capital mobility and asymmetry limitations.

Judgment:

```text
PHASE32_B_ROTATION_RECONSIDERATION = MATERIAL_EVIDENCE
```

This remains a future architecture candidate. No direct sell/rotation
implementation is authorized.

## Market Structure Analysis

Market structure alone partially explains the plateau:

- spring produced multiple portfolio-moving daily gains;
- plateau had no `+50k` daily gain days;
- plateau BULL included frequent `CONFLICTED_MARKET_STRUCTURE`,
  `SHORT_TERM_BREADTH_BREAKDOWN`, or narrowing states;
- campaign winners existed but were often smaller and offset by losers.

Market structure alone is not sufficient, because decision-time evidence also
shows system-side capital conversion limitations: ADD intent did not become
capital, Cash allocations were high, and winner/loser capital asymmetry was
weak.

## Security Selection vs Capitalization

| Factor | Judgment | Role |
| --- | --- | --- |
| `SELECTION_FAILURE` | partial | BULL TYPE_B and episode 4 losers show weak payoff selection |
| `CAPITALIZATION_FAILURE` | supported | strongest winner `65730` had small notional |
| `ADD_FAILURE` | supported | 242 PM ADD to 5 ADD fills |
| `RETENTION_FAILURE` | partial | not primary; evidence favors weak capitalization |
| `LOSER_OFFSET` | supported | loser notional exceeded winner notional in plateau |
| `MARKET_OPPORTUNITY_STRUCTURE` | supported | no large daily gains after spring |

## Hypothesis Matrix

| Hypothesis | Support | Causal Role | Materiality |
| --- | --- | --- | --- |
| BULL blanket weakness | NOT_SUPPORTED | NON_CAUSE | LOW |
| Conditional BULL weakness | SUPPORTED | SECONDARY_CAUSE | HIGH |
| Candidate scarcity | PARTIALLY_SUPPORTED | AMPLIFIER | MEDIUM |
| Candidate discovery failure | NOT_SUPPORTED | NON_CAUSE | LOW |
| Security selection weakness | PARTIALLY_SUPPORTED | SECONDARY_CAUSE | MEDIUM |
| Entry quality weakness | PARTIALLY_SUPPORTED | AMPLIFIER | MEDIUM |
| Winner scarcity | PARTIALLY_SUPPORTED | PRIMARY_CAUSE component | HIGH |
| Winner capitalization failure | SUPPORTED | PRIMARY_CAUSE | HIGH |
| ADD conversion limitation | SUPPORTED | PRIMARY_CAUSE | HIGH |
| Winner retention failure | PARTIALLY_SUPPORTED | AMPLIFIER | MEDIUM |
| Loser offset | SUPPORTED | SECONDARY_CAUSE | HIGH |
| Excessive churn | PARTIALLY_SUPPORTED | AMPLIFIER | MEDIUM |
| PC capital competition | SUPPORTED | SECONDARY_CAUSE | HIGH |
| MCC suppression | SUPPORTED | AMPLIFIER | MEDIUM-HIGH |
| Risk Pacing suppression | SUPPORTED | AMPLIFIER | MEDIUM-HIGH |
| Excess Cash preference | PARTIALLY_SUPPORTED | CALIBRATION_QUESTION | MEDIUM-HIGH |
| PS / lot limitation | NOT_SUPPORTED | NON_CAUSE | LOW |
| G129 regression | NOT_SUPPORTED | NON_CAUSE | LOW |
| Incumbent capital lock | PARTIALLY_SUPPORTED | SECONDARY_CAUSE | MEDIUM-HIGH |
| Marginal-value resolution limitation | SUPPORTED | SECONDARY_CAUSE | HIGH |
| Rotation absence | PARTIALLY_SUPPORTED | AMPLIFIER | MEDIUM |
| Market structure change | SUPPORTED | PRIMARY_CAUSE component | HIGH |
| Measurement artifact | NOT_SUPPORTED | NON_CAUSE | LOW |

## Root Cause Ranking

1. Winner capitalization failure  
   Mechanism: winners were found but often at too-small notional, while losers
   received comparable or larger capital. Evidence: plateau winner average
   notional `89,717` vs loser average `106,512`; `65730` returned `+156.6%`
   but had only `42,340` buy notional. Materiality: HIGH. Layer: PC / capital
   allocation / ADD capitalization. Classification: ARCHITECTURAL_LIMITATION.

2. ADD conversion limitation  
   Mechanism: PM ADD evidence rarely became capital. Evidence: `242` PM ADD
   symbol-days to `5` ADD fills; main loss at PM-to-PC consideration and PC
   positive allocation. Materiality: HIGH. Layer: PM-to-PC / PC-MCC. Classification:
   ARCHITECTURAL_LIMITATION / CALIBRATION_QUESTION.

3. Conditional BULL capital conversion weakness  
   Mechanism: BULL episodes split into high-exposure poor-return and
   low-exposure poor-return modes. Evidence: episodes 1 and 4. Materiality:
   HIGH. Layer: selection, PC/MCC, Risk Pacing. Classification:
   MARKET_ENVIRONMENT plus ARCHITECTURAL_LIMITATION.

4. PC/MCC/Cash/Risk Pacing capital suppression  
   Mechanism: positive demand frequently became Cash or low security
   allocation, especially under conflicted Market Quality. Evidence: plateau
   average authorized Cash weight `0.317`; BULL episode 4 authorized Cash
   `0.555`. Materiality: MEDIUM-HIGH. Layer: PC / MCC / Risk Pacing.
   Classification: CALIBRATION_QUESTION, not proven DEFECT.

5. Marginal-value / incumbent opportunity-cost resolution limitation  
   Mechanism: current architecture lacks high-resolution next-increment value
   and explicit HOLD capital opportunity-cost authority. Evidence: repeated
   ADD loss, coarse classes, long-lived HOLD capital, winner/loser capital
   asymmetry. Materiality: MEDIUM-HIGH. Layer: PC capital value / future
   rotation. Classification: ARCHITECTURAL_LIMITATION.

## Defect vs Limitation vs Normal Behavior

| Cause | Classification |
| --- | --- |
| Few-winner payoff not repeating | NORMAL_STRATEGY_BEHAVIOR / MARKET_ENVIRONMENT |
| Conditional BULL weakness | MARKET_ENVIRONMENT / ARCHITECTURAL_LIMITATION |
| ADD underdeployment | ARCHITECTURAL_LIMITATION / CALIBRATION_QUESTION |
| PC/MCC/Risk Pacing Cash preference | CALIBRATION_QUESTION |
| High-resolution value absence | ARCHITECTURAL_LIMITATION |
| Portfolio Rotation absence | ARCHITECTURAL_LIMITATION |
| Fill ADD attribution ambiguity | OBSERVABILITY_GAP |
| G129 actual path | NOT A DEFECT |
| Measurement | NOT A DEFECT |

No current accepted contract violation was proven.

## Improvement Candidate Layers

Priority order for future consideration:

1. `ADD Capitalization`
2. `marginal capital representation`
3. `PC / MCC`
4. `incumbent capital opportunity-cost`
5. `Portfolio Rotation`
6. `Risk Pacing` calibration observability only
7. `observability only`, especially ADD fill attribution

Do not begin implementation from this report without explicit approval.

## Required Answers

1. BULL weakness exists: yes, conditional.
2. Blanket or conditional: conditional.
3. Multiple BULL modes: yes, TYPE_B and TYPE_C plus positive controls.
4. High exposure / poor return exists: yes.
5. Low exposure / poor return exists: yes.
6. Candidate shortage primary: no.
7. Security selection primary: partial, not sole primary.
8. Winner capitalization failure: yes.
9. Winner retention failure: partial.
10. ADD conversion limitation: yes.
11. Primary ADD loss stage: PM ADD to PC consideration, then PC ADD competitor
    to positive allocation.
12. ADD underdeployment material: yes.
13. Cash retained mainly through PC/MCC/Risk Pacing and SELL-generated Cash.
14. Risk Pacing suppressed BULL conversion: yes, partially/materially.
15. Overconservative evidence: partial; most examples are unresolved because
    exposure or Market Quality justified caution.
16. PC/MCC bottleneck: yes.
17. Winner/loser capital asymmetry sufficient: no.
18. Incumbent HOLD capital mobility constraint: partial.
19. Marginal-value resolution performance ceiling: yes.
20. High-resolution reconsideration evidence: material.
21. Rotation reconsideration evidence: material, weaker than high-resolution.
22. Market structure alone explains plateau: partial.
23. System capital conversion amplified plateau: yes.
24. Improvable performance ceiling: yes.
25. First target if implementation is later approved: ADD Capitalization /
    high-resolution marginal capital representation at PC-owned capital value
    boundary.
26. Still read-only follow-up first: yes.

## Recommended Next Task

```text
Phase32-C - ADD Capitalization / Marginal Capital Value Shadow Specification
```

Scope should remain design/read-only unless explicitly approved otherwise:

- exact ADD PM-to-PC admission semantics;
- ADD vs NEW vs Cash evidence preservation;
- high-resolution marginal capital value shadow fields;
- ADD fill attribution instrumentation requirements;
- no production behavior change.

## Files Inspected

- `docs/phase_reports/phase32_a_long_horizon_performance_plateau_root_cause_deep_audit.md`
- `docs/phase_reports/phase31_final_summary_and_phase32_handoff.md`
- `docs/phase_reports/phase31_g129_buy_add_actual_path_narrow_repair.md`
- `docs/phase_reports/phase31_g138_march_april_profit_formation_strategy_causality_audit.md`
- `docs/phase_reports/phase31_g140_candidate_scarcity_vs_risk_pacing_capital_suppression_necessity_audit.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py`
- daily artifacts under
  `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T235520054579Z/`

## Commands Executed

```text
sed -n ... Phase32-B pasted request
sed -n ... high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md
git status --short
python3 - <<'PY' ... BULL episode and ADD funnel aggregation
python3 - <<'PY' ... NEW/ADD conversion and campaign asymmetry aggregation
rg -n ... source authority touchpoint
```

No tests, fresh-run, resume, replay, long Historical, full backtest, production
command, model training, or Strategy/Runtime implementation was executed.

## Final Judgments

`PHASE32_B_MEASUREMENT_INTEGRITY = PASS`

`PHASE32_B_BULL_WEAKNESS = CONDITIONAL`

`PHASE32_B_BULL_FAILURE_MODE = MULTI_MODE_TYPE_B_HIGH_EXPOSURE_POOR_RETURN_AND_TYPE_C_LOW_EXPOSURE_POOR_RETURN_WITH_TYPE_A_AND_TYPE_D_POSITIVE_CONTROLS`

`PHASE32_B_BULL_HIGH_EXPOSURE_POOR_RETURN_EXISTS = YES`

`PHASE32_B_BULL_LOW_EXPOSURE_POOR_RETURN_EXISTS = YES`

`PHASE32_B_WINNER_DISCOVERY_FAILURE = PARTIAL`

`PHASE32_B_SECURITY_SELECTION_WEAKNESS_MATERIAL = PARTIAL`

`PHASE32_B_WINNER_CAPITALIZATION_FAILURE = YES`

`PHASE32_B_WINNER_RETENTION_FAILURE = PARTIAL`

`PHASE32_B_ADD_CONVERSION_LIMITATION = YES`

`PHASE32_B_PRIMARY_ADD_LOSS_STAGE = PM_ADD_TO_PC_ADD_CONSIDERATION; PC_ADD_COMPETITION_TO_POSITIVE_ADD_ALLOCATION`

`PHASE32_B_ADD_UNDERDEPLOYMENT_PERFORMANCE_MATERIAL = YES`

`PHASE32_B_CASH_COMPETITION_MATERIAL = YES`

`PHASE32_B_RISK_PACING_BULL_SUPPRESSION_MATERIAL = PARTIAL`

`PHASE32_B_RISK_PACING_OVERCONSERVATIVE_EVIDENCE = PARTIAL`

`PHASE32_B_PC_MCC_BOTTLENECK_MATERIAL = YES`

`PHASE32_B_WINNER_LOSER_CAPITAL_ASYMMETRY_SUFFICIENT = NO`

`PHASE32_B_INCUMBENT_CAPITAL_LOCK_MATERIAL = PARTIAL`

`PHASE32_B_CURRENT_MARGINAL_VALUE_RESOLUTION_LIMITATION_MATERIAL = YES`

`PHASE32_B_HIGH_RESOLUTION_VALUE_RECONSIDERATION = MATERIAL_EVIDENCE`

`PHASE32_B_ROTATION_RECONSIDERATION = MATERIAL_EVIDENCE`

`PHASE32_B_MARKET_STRUCTURE_ALONE_EXPLAINS_PLATEAU = PARTIAL`

`PHASE32_B_SYSTEM_CAPITAL_CONVERSION_AMPLIFIED_PLATEAU = YES`

`PHASE32_B_IMPROVABLE_PERFORMANCE_CEILING_EXISTS = YES`

`PHASE32_B_MANDATORY_STRATEGY_DEFECT = NO`

`PHASE32_B_REPAIR_REQUIRED = FOLLOWUP_REQUIRED`

`PHASE32_B_REPAIR_CANDIDATE_LAYER = ADD_CAPITALIZATION; PC_MCC; MARGINAL_CAPITAL_REPRESENTATION; INCUMBENT_CAPITAL_OPPORTUNITY_COST; OBSERVABILITY`

`PHASE32_B_NEXT_STEP = Phase32-C - ADD Capitalization / Marginal Capital Value Shadow Specification`
