# Phase31-G76 — Post-Peak BUY_NEW Early-Failure Causality Audit

## PRIMARY_JUDGMENT

PHASE31_G76_POST_PEAK_BUY_NEW_EARLY_FAILURE_CAUSALITY_CONFIRMED

Target run:

`runtime-test-historical-extended-smoke-20260823T140946562431Z`

Completed snapshot used:

- completed business days = `200`
- latest completed business date = `2023-07-25`
- primary window = `2023-05-31 -> 2023-07-25`

No code, config, threshold, weight, run state, fresh-run, resume, replay, or
Historical execution was changed or performed. G74 repair was not applied to
this running run.

## Evidence Basis

BUY_NEW lots were reconstructed from completed-date runtime evidence only:

- BUY/SELL fills from `daily/<date>/execution/fills.json`
- BUY_NEW / BUY_ADD intent from `daily/<date>/strategy/runtime_planning.json`
- same-date decision evidence from:
  - `strategy/portfolio_construction.json`
  - `strategy/portfolio_policy.json`
  - `strategy/market_context.json`
  - `strategy/position_management.json`
  - `strategy/position_sizing.json`

BUY_ADD fills were excluded from the BUY_NEW cohort. Open positions were marked
using latest completed-date valuation where still open. Historical outcome was
used only for cohort characterization and PnL attribution, not for Strategy
parameter selection.

## Plateau BUY_NEW Cohorts

Primary plateau BUY_NEW lots:

- total BUY_NEW lots = `69`
- total reconstructed PnL = `-51,700`
- same-day exit count = `0`

| Cohort | Count | PnL | Average PnL |
|---|---:|---:|---:|
| NEXT_DAY_LOSER | 3 | -33,100 | -11,033 |
| EARLY_LOSER, 3-5BD | 23 | -121,700 | -5,291 |
| SHORT_WINNER, 2-5BD | 14 | +47,900 | +3,421 |
| NEXT_DAY_WINNER | 4 | +2,430 | +608 |
| DURABLE_WINNER | 10 | +76,200 | +7,620 |
| DURABLE_LOSER | 5 | -31,600 | -6,320 |
| UNRESOLVED / too recent | 10 | +8,170 | +817 |

EARLY_FAILURE_MATERIAL = YES

Combined next-day + 3-5BD early losers:

- count = `26`
- gross loss = `-154,800`

This early-loss bucket is larger than the total plateau BUY_NEW net loss,
because short winners and durable winners partly offset it.

## Decision-Time Cohort Comparison

### EARLY_LOSER + NEXT_DAY_LOSER

| Metric | Median | Min | Max |
|---|---:|---:|---:|
| Candidate rank | 39.5 | 16 | 47 |
| Runtime opportunity score | -0.517 | -0.890 | -0.155 |
| Confidence | 0.24 | 0.08 | 0.70 |
| Quality score | 0.526 | 0.476 | 0.701 |
| Allocation weight | 0.045 | 0.014 | 0.244 |

Distribution:

- Market Quality: `HEALTHY_EXPANSION 9`, `CONFLICTED_MARKET_STRUCTURE 8`,
  `RECOVERY_CONFIRMATION_INCOMPLETE 4`,
  `SHORT_TERM_BREADTH_BREAKDOWN 3`,
  `SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH 2`
- Risk Pacing: `CAUTIOUS_DEPLOYMENT 13`, `NORMAL_DEPLOYMENT 9`,
  `GRADUAL_REDEPLOYMENT 4`
- Entry state: `CONTINUATION_WITH_CAUTION 21`,
  `HEALTHY_CONTINUATION_ENTRY 5`
- Momentum: `MIXED_OR_UNRESOLVED 16`, `HEALTHY_CONTINUATION 10`
- Allocation class: `COMPARABLE_MARGINAL 21`, `COMPARABLE_HIGH 3`,
  `STRONG 2`

Largest early losses:

| Symbol | Buy Date | Exit Date | BD Held | PnL | Rank | Score | Confidence | MQ |
|---:|---|---|---:|---:|---:|---:|---:|---|
| 70330 | 2023-07-04 | 2023-07-07 | 4 | -28,000 | 42 | -0.618 | 0.18 | HEALTHY_EXPANSION |
| 92410 | 2023-06-13 | 2023-06-14 | 2 | -27,000 | 28 | -0.423 | 0.46 | CONFLICTED_MARKET_STRUCTURE |
| 70460 | 2023-06-19 | 2023-06-21 | 3 | -24,500 | 33 | -0.468 | 0.36 | HEALTHY_EXPANSION |
| 40750 | 2023-06-20 | 2023-06-26 | 5 | -21,000 | 36 | -0.462 | 0.30 | HEALTHY_EXPANSION |
| 41240 | 2023-06-07 | 2023-06-09 | 3 | -6,600 | 29 | -0.417 | 0.44 | RECOVERY_CONFIRMATION_INCOMPLETE |

### DURABLE_WINNER Control

| Metric | Median | Min | Max |
|---|---:|---:|---:|
| Candidate rank | 24.5 | 5 | 44 |
| Runtime opportunity score | -0.467 | -0.737 | +0.065 |
| Confidence | 0.53 | 0.14 | 0.92 |
| Quality score | 0.601 | 0.488 | 0.781 |
| Allocation weight | 0.052 | 0.020 | 0.128 |

Distribution:

- Market Quality: `SHORT_TERM_BREADTH_BREAKDOWN 5`,
  `SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH 4`, `HEALTHY_EXPANSION 1`
- Risk Pacing: `CAUTIOUS_DEPLOYMENT 9`, `NORMAL_DEPLOYMENT 1`
- Entry state: `CONTINUATION_WITH_CAUTION 6`,
  `HEALTHY_CONTINUATION_ENTRY 4`
- Momentum: `MIXED_OR_UNRESOLVED 5`, `HEALTHY_CONTINUATION 5`
- Allocation class: `COMPARABLE_MARGINAL 6`, `COMPARABLE_HIGH 3`, `STRONG 1`

Durable winners existed mostly in cautious pacing states. Therefore Market
Quality state alone does not explain early failure.

## Profit Burst / Recovery / Plateau Comparison

| Window | BUY_NEW Lots | PnL | Main Cohorts | Median Rank | Median Score | Median Confidence | Median Allocation |
|---|---:|---:|---|---:|---:|---:|---:|
| Profit burst, 2023-03-15 -> 2023-04-06 | 26 | +489,310 | SHORT_WINNER 11, DURABLE_WINNER 4 | 29.5 | -0.387 | 0.43 | 0.089 |
| Recovery, 2023-04-25 -> 2023-05-30 | 38 | +118,280 | DURABLE_WINNER 9, EARLY_LOSER 9 | 35.5 | -0.455 | 0.31 | 0.043 |
| Plateau, 2023-05-31 -> 2023-07-25 | 69 | -51,700 | EARLY_LOSER 23, SHORT_WINNER 14 | 37.0 | -0.504 | 0.28 | 0.041 |

PROFIT_BURST_VS_PLATEAU_ENTRY_QUALITY_DIFF = PRESENT

The plateau cohort shifted toward lower-ranked, lower-score, lower-confidence,
smaller-allocation opportunities. This did not happen because BUY was shut off;
it happened while BUY_NEW activity expanded.

## Post-Entry Sequence

For the 26 next-day / early-loss BUY_NEW lots:

At +1BD:

- `REDUCE / WEAKENING_BUT_INTACT / BUY_WAIT / FADING_PRIOR_WINNER`: `7`
- `EXIT / EXIT_GRADE`: `3`
- `REDUCE / WEAKENING_BUT_INTACT / REJECT`: `3`

At +2BD:

- `EXIT / PERSISTENT_DETERIORATION`: `8`
- `EXIT / EXIT_GRADE`: `3`
- `REDUCE / WEAKENING_BUT_INTACT`: `5`

At exit:

- PM action = `EXIT` for `26 / 26`
- SELL state = `PERSISTENT_DETERIORATION 18`, `EXIT_GRADE 8`

Interpretation:

Many losses were not simply random noise held for a normal campaign horizon.
They quickly moved into REDUCE / EXIT evidence, often through BUY_WAIT,
FADING_PRIOR_WINNER, or PERSISTENT_DETERIORATION shortly after entry.

## Avoidable Loss Classification

Decision-time weak-entry condition used for characterization:

`confidence < 0.5 AND candidate_rank > 25`

This is not proposed as a production rule. It is only used to determine whether
same-date evidence already distinguished many early losers from the winner
control group.

| Classification | Count | Gross Loss |
|---|---:|---:|
| PRE_EXISTING_WEAK_ENTRY | 22 | -146,400 |
| LEGITIMATE_EXPLORATION_LOSS | 4 | -8,400 |
| EARLY_FAILURE | included above | included above |
| THRESHOLD_CHURN | 0 distinct evidence-only bucket |
| CHURN_LOSS | included in early failure / post-entry sequence |
| MARKET_SHOCK | 0 direct single-state evidence |
| SYSTEM_CAUSED | 0 |
| INSUFFICIENT_EVIDENCE_TO_CLASSIFY | 0 |

The four early losers not classified as pre-existing weak entry were:

| Symbol | Buy Date | Exit Date | PnL | Rank | Confidence | Decision-Time Character |
|---:|---|---|---:|---:|---:|---|
| 65780 | 2023-06-07 | 2023-06-09 | -700 | 16 | 0.70 | higher confidence / rank; exploration loss |
| 48910 | 2023-06-13 | 2023-06-15 | -5,300 | 16 | 0.70 | healthy entry evidence; failed after entry |
| 24020 | 2023-06-14 | 2023-06-15 | -1,000 | 20 | 0.62 | not weak enough at decision time |
| 46570 | 2023-07-19 | 2023-07-21 | -1,400 | 22 | 0.58 | moderate evidence; failed after entry |

LEGITIMATE_EXPLORATION_LOSS_MATERIAL = NO

The legitimate exploration bucket exists, but its gross loss was only `-8,400`
inside the early/next-day loser set.

## Avoidable Loss Estimate

Decision-time identifiable weak-entry bucket:

- early / next-day loser count captured = `22 / 26`
- avoidable gross loss identified = `146,400`
- same-condition positive contribution observed = `37,160`
- same-condition positive count = `20`
- same-condition durable winners = `4`
- same-condition total net PnL = `-142,440`

Conservative estimate:

`Avoided Loss - Winner Opportunity Cost = 146,400 - 37,160 = 109,240`

This estimate is characterization only. It cannot be converted directly into a
BUY filter because the same condition also contains durable winners and short
winners. The useful finding is separability is partial but economically
material.

DECISION_TIME_LOSER_DISCRIMINATION_EXISTS = PARTIAL

Reason:

Most early losers were identifiable by low confidence and lower rank at BUY
time, but that condition is not clean enough to avoid winner opportunity cost.

## Market Quality Interaction

MARKET_QUALITY_EXPLAINS_EARLY_FAILURE = NO

Evidence:

- Early losers occurred under `HEALTHY_EXPANSION`, `CONFLICTED_MARKET_STRUCTURE`,
  and recovery / breadth-breakdown states.
- Durable winners were concentrated in `CAUTIOUS_DEPLOYMENT` and
  `SHORT_TERM_BREADTH_BREAKDOWN` / narrowing states.
- CAUTIOUS condition contained early losses, but also many durable winners:
  - early / next-day loser count = `13`
  - durable winner count = `9`
  - same-condition net PnL = positive in the audited set
- Market Quality hard BUY gate evidence was not the failure mechanism.

## System-Caused Check

SYSTEM_CAUSED_LOSS_MATERIAL = NO

Evidence:

- Runtime capital-priority redecision was not observed as the cause.
- Candidate rank mutation was not observed as the cause.
- BUY_NEW was actually materialized at high frequency.
- The failure appears in post-entry campaign behavior, not in a broken PC -> PS
  -> Runtime binding path.

## Required Judgment

POST_PEAK_BUY_NEW_QUALITY =
WEAKENED_WITH_MATERIAL_EARLY_FAILURE

EARLY_FAILURE_MATERIAL = YES

PRE_EXISTING_WEAK_ENTRY_MATERIAL = YES

LEGITIMATE_EXPLORATION_LOSS_MATERIAL = NO

THRESHOLD_CHURN_MATERIAL = NO

SYSTEM_CAUSED_LOSS_MATERIAL = NO

CANDIDATE_RANK_DISCRIMINATION_DETERIORATED = YES

DECISION_TIME_LOSER_DISCRIMINATION_EXISTS = PARTIAL

MARKET_QUALITY_EXPLAINS_EARLY_FAILURE = NO

PROFIT_BURST_VS_PLATEAU_ENTRY_QUALITY_DIFF = PRESENT

CODE_CHANGED = NO

RUN_MODIFIED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

MARKET_QUALITY_CHANGED = NO

BUY_FILTER_CREATED = NO

FIXED_MINIMUM_HOLDING_PERIOD_CREATED = NO

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0

## Highest-Value Next Investigation

Investigate candidate / entry quality separability for the low-confidence,
lower-rank plateau BUY_NEW bucket, specifically whether existing same-date
canonical evidence can distinguish avoidable weak entries from the durable
winners that share the same broad caution signals.
