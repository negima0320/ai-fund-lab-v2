# Phase31-G78 — COMPARABLE_MARGINAL Internal Quality Separability Audit

## PRIMARY_JUDGMENT

PHASE31_G78_COMPARABLE_MARGINAL_INTERNAL_SEPARABILITY_PARTIAL_CONFIRMED

Target run:

`runtime-test-historical-extended-smoke-20260823T140946562431Z`

Completed snapshot used:

- completed business days = `210`
- latest completed business date = `2023-08-08`

No code, config, threshold, weight, run state, fresh-run, resume, replay, or
Historical execution was changed or performed. G74 repair was not applied to
this running run.

## Evidence Basis

READ-ONLY completed-date artifacts:

- `daily/<date>/execution/fills.json`
- `daily/<date>/strategy/runtime_planning.json`
- `daily/<date>/strategy/portfolio_construction.json`
- `daily/<date>/strategy/portfolio_policy.json`
- `daily/<date>/strategy/position_sizing.json`
- `daily/<date>/strategy/market_context.json`
- `daily/<date>/current_valuation_refresh/valuation_projection.json`

BUY_NEW lots were reconstructed from fills and Runtime Planning intent. BUY_ADD
was excluded. Historical outcome was used only for cohort characterization and
economic attribution, not for production decision correctness or parameter
selection.

## COMPARABLE_MARGINAL Window Summary

| Window | CM BUY_NEW | PnL | EARLY_LOSER | SHORT_WINNER | DURABLE_WINNER | DURABLE_LOSER | Median Rank | Median Confidence | Median Score | Median Allocation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline 2022-10 -> 2023-02 | 134 | +196,600 | 45 | 40 | 31 | 17 | 22.0 | 0.58 | -0.449 | 3.76% |
| Profit Burst 2023-03-15 -> 2023-04-06 | 25 | +490,710 | 7 | 12 | 4 | 1 | 30.0 | 0.42 | -0.382 | 9.32% |
| Recovery 2023-04-25 -> 2023-05-30 | 37 | +124,780 | 12 | 8 | 9 | 6 | 37.0 | 0.28 | -0.456 | 4.26% |
| Plateau 2023-05-31 -> 2023-08-08 | 69 | -90,670 | 28 | 22 | 8 | 8 | 35.0 | 0.32 | -0.499 | 4.41% |

Core conclusion:

`COMPARABLE_MARGINAL = BAD` is false. Profit Burst was almost entirely
COMPARABLE_MARGINAL and highly profitable. The issue is internal quality
separability within the marginal class, especially in the plateau.

## Audit A — Plateau Winner vs Early Loser

### EARLY_LOSER

Plateau COMPARABLE_MARGINAL early losers:

- count = `28`
- PnL = `-153,630`
- median rank = `40.5`
- median score = `-0.504`
- median confidence = `0.21`
- median quality score = `0.534`
- median construction priority = `44`
- median allocation weight = `5.22%`
- median initial notional = `87,405`
- median reference price = `827`
- median lot / equity = `4.87%`

Distribution:

- entry state = `CONTINUATION_WITH_CAUTION 28 / 28`
- entry action = `BUY_NEW_REDUCED_ONLY 28 / 28`
- momentum = `MIXED_OR_UNRESOLVED 23`, `HEALTHY_CONTINUATION 5`
- relative strength = `MIXED 14`, `SUPPORTIVE 11`, `WEAK 3`
- Market Quality = `HEALTHY_EXPANSION 9`,
  `RECOVERY_CONFIRMATION_INCOMPLETE 8`,
  `CONFLICTED_MARKET_STRUCTURE 7`,
  `SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH 2`,
  `SHORT_TERM_BREADTH_BREAKDOWN 2`

Largest examples:

| Symbol | Buy Date | Exit Date | BD Held | PnL | Rank | Score | Confidence | MQ |
|---:|---|---|---:|---:|---:|---:|---:|---|
| 70330 | 2023-07-04 | 2023-07-07 | 4 | -28,000 | 42 | -0.618 | 0.18 | HEALTHY_EXPANSION |
| 92410 | 2023-06-13 | 2023-06-14 | 2 | -27,000 | 28 | -0.423 | 0.46 | CONFLICTED_MARKET_STRUCTURE |
| 70460 | 2023-06-19 | 2023-06-21 | 3 | -24,500 | 33 | -0.468 | 0.36 | HEALTHY_EXPANSION |
| 40750 | 2023-06-20 | 2023-06-26 | 5 | -21,000 | 36 | -0.462 | 0.30 | HEALTHY_EXPANSION |

### DURABLE_WINNER Control

Plateau COMPARABLE_MARGINAL durable winners:

- count = `8`
- PnL = `+70,230`
- median rank = `14.5`
- median score = `-0.241`
- median confidence = `0.73`
- median quality score = `0.712`
- median construction priority = `22.5`
- median allocation weight = `5.25%`
- median initial notional = `87,300`
- median reference price = `633`
- median lot / equity = `3.82%`

Distribution:

- entry state = `CONTINUATION_WITH_CAUTION 8 / 8`
- entry action = `BUY_NEW_REDUCED_ONLY 8 / 8`
- momentum = `MIXED_OR_UNRESOLVED 7`, `HEALTHY_CONTINUATION 1`
- relative strength = `MIXED 6`, `SUPPORTIVE 2`
- Market Quality = `SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH 3`,
  `SHORT_TERM_BREADTH_BREAKDOWN 2`, `HEALTHY_EXPANSION 1`,
  `CONFLICTED_MARKET_STRUCTURE 1`, `RECOVERY_CONFIRMATION_INCOMPLETE 1`

Winner examples:

| Symbol | Buy Date | Exit/Open | BD Held | PnL | Rank | Score | Confidence | MQ |
|---:|---|---|---:|---:|---:|---:|---:|---|
| 40520 | 2023-06-15 | 2023-07-14 | 22 | +29,600 | 5 | +0.065 | 0.92 | HEALTHY_EXPANSION |
| 77090 | 2023-06-27 | 2023-07-07 | 9 | +10,100 | 15 | -0.139 | 0.72 | SHORT_TERM_BREADTH_BREAKDOWN |
| 74530 | 2023-07-20 | open | 14 | +12,330 | 25 | -0.531 | 0.52 | CONFLICTED_MARKET_STRUCTURE |
| 37780 | 2023-06-28 | 2023-07-18 | 14 | +4,900 | 8 | +0.011 | 0.86 | SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH |

EARLY_LOSER_VS_DURABLE_WINNER_SEPARABILITY = PARTIAL

Reason:

Rank, score, confidence, quality score, and construction priority show strong
directional separation. But common state labels do not: both groups are
`COMPARABLE_MARGINAL`, `BUY_NEW_REDUCED_ONLY`, and
`CONTINUATION_WITH_CAUTION`. Momentum also overlaps.

## Audit B — Profit Burst vs Plateau

Profit Burst COMPARABLE_MARGINAL:

- count = `25`
- PnL = `+490,710`
- median rank = `30`
- median score = `-0.382`
- median confidence = `0.42`
- median quality score = `0.585`
- median allocation weight = `9.32%`
- median reference price = `1,211`
- median lot / equity = `9.12%`

Plateau COMPARABLE_MARGINAL:

- count = `69`
- PnL = `-90,670`
- median rank = `35`
- median score = `-0.499`
- median confidence = `0.32`
- median quality score = `0.559`
- median allocation weight = `4.41%`
- median reference price = `648`
- median lot / equity = `3.94%`

PROFIT_BURST_VS_PLATEAU_MARGINAL_QUALITY_SHIFT = PRESENT

MARGINAL_CLASS_SEMANTICS_STABLE_BUT_INTERNAL_QUALITY_SHIFTED = YES

Reason:

The coarse class remained COMPARABLE_MARGINAL, but internal evidence shifted
toward lower rank, lower score, lower confidence, lower quality score, and lower
allocation intensity. The weaker plateau performance is not explained by the
class label alone.

## Audit C — Same-Quality Temporal Comparison

Same-quality bins used only existing evidence dimensions:

- rank band
- confidence band
- opportunity score band
- entry state
- momentum state

No composite score was created.

Representative matched bins:

| Quality Bin | Profit Burst n / PnL / Early / Durable | Plateau n / PnL / Early / Durable |
|---|---:|---:|
| rank 1-20, confidence high, score mild, caution, mixed momentum | 2 / +9,000 / 0 / 0 | 10 / +31,600 / 4 / 3 |
| rank 21-35, confidence high, score mild, caution, mixed momentum | 5 / +20,000 / 1 / 1 | 2 / +13,890 / 0 / 0 |
| rank 21-35, confidence mid, score mild, caution, mixed momentum | 4 / +15,300 / 2 / 1 | 4 / -34,600 / 2 / 0 |
| rank 21-35, confidence mid, score weak, caution, mixed momentum | 2 / -1,500 / 1 / 0 | 7 / -20,500 / 2 / 0 |
| rank 36+, confidence low, score weak, caution, mixed momentum | 3 / +9,800 / 1 / 0 | 21 / -37,940 / 11 / 1 |

SAME_QUALITY_TEMPORAL_FOLLOW_THROUGH_DETERIORATION = YES

Reason:

Several comparable bins deteriorated in plateau even when rank/confidence/score
band, entry state, and momentum state were held roughly similar. This does not
prove a new rule, but it means market/candidate interaction remains unresolved:
the same broad decision-time quality was less reliable in the plateau.

MARKET_ENVIRONMENT_INTERACTION_REMAINS = YES

Reason:

Plateau failures occurred even under `HEALTHY_EXPANSION`, while durable winners
also occurred under cautious / breadth-breakdown states. Coarse Market Quality
state alone does not discriminate, but temporal follow-through changed enough
that market environment x candidate interaction should remain in scope.

## Audit D — Weak Marginal Economic Cost

Weak subgroup characterization, not a proposed threshold:

`confidence < 0.5 AND rank > 25`

Plateau COMPARABLE_MARGINAL weak subgroup:

- count = `48`
- net PnL = `-164,100`
- early losers = `22`
- early loss PnL = `-145,040`
- gross loss = `-177,940`
- positive contribution count = `18`
- positive contribution = `+13,840`
- durable winners = `1`
- durable winner PnL = `+500`

Avoidable-loss characterization:

`Avoided Loss - Winner Opportunity Cost = 145,040 - 13,840 = 131,200`

This is not a production cutoff. It is evidence that existing fields contain
economically material weak-marginal separability, while still preserving the
warning that some winners live inside the same broad region.

Alternative narrower subgroup:

`confidence < 0.5 AND rank > 25 AND momentum = MIXED_OR_UNRESOLVED`

- count = `35`
- net PnL = `-118,340`
- early losers = `17`
- early loss PnL = `-127,340`
- positive contribution = `+11,800`
- durable winners = `1`
- durable winner PnL = `+500`
- avoided-loss net of positive opportunity cost = `115,540`

Credible-marginal contrast subgroup:

`confidence >= 0.5 OR rank <= 20`

- count = `21`
- net PnL = `+73,430`
- early losers = `6`
- early loss PnL = `-8,590`
- positive contribution = `+112,720`
- durable winners = `7`
- durable winner PnL = `+69,730`
- gross loss = `-39,290`

WEAK_MARGINAL_ECONOMIC_LOSS_MATERIAL = YES

WINNER_OPPORTUNITY_COST_MATERIAL = YES

Reason:

The weak subgroup contains material avoidable gross loss, but the broader
COMPARABLE_MARGINAL class contains major winners. Blanket exclusion or single
rank/confidence cutoffs would damage the Profit Engine.

## Audit E — Allocation Intensity

| Subgroup | Count | Median Allocation | Median Initial Notional | Median Lot / Equity | Median Budget | Median Cash Allocation |
|---|---:|---:|---:|---:|---:|---:|
| Weak marginal: confidence < 0.5 and rank > 25 | 48 | 4.16% | 69,481 | 3.28% | 0.383 | 0.197 |
| Weak marginal + mixed momentum | 35 | 4.00% | 66,978 | 3.21% | 0.383 | 0.195 |
| Credible marginal: confidence >= 0.5 or rank <= 20 | 21 | 5.43% | 90,443 | 5.42% | 0.385 | 0.083 |

WEAK_MARGINAL_OVERALLOCATION_EVIDENCE = PARTIAL

Reason:

Weak marginal positions were not larger than credible marginal positions on
median. However, the weak group still consumed material capital repeatedly:
48 buys at median `4.16%` allocation and median notional about `69k`. The issue
is not one oversized bet; it is repeated allocation to weak marginal evidence.

## Audit F — Existing Evidence Sufficiency

MARGINAL_INTERNAL_QUALITY_DIFFERENTIATION = PRESENT

EXISTING_EVIDENCE_SUFFICIENT_FOR_CAPITAL_SELECTIVITY = PARTIAL

NEW_FEATURE_REQUIRED = UNPROVEN

Reason:

Existing fields already separate a profitable credible-marginal region from a
material weak-marginal loss region:

- rank
- confidence
- opportunity score
- quality score
- construction priority
- allocation weight / notional
- Market Quality / Risk Pacing context

But the separation is not clean enough to become a direct rule. Winner
opportunity cost is material, and similar quality bins performed differently
between profit burst and plateau. Additional architecture work should first
examine capital allocation semantics and temporal interaction using the existing
fields before claiming a new indicator is required.

## Required Judgment

MARGINAL_INTERNAL_QUALITY_DIFFERENTIATION = PRESENT

EARLY_LOSER_VS_DURABLE_WINNER_SEPARABILITY = PARTIAL

PROFIT_BURST_VS_PLATEAU_MARGINAL_QUALITY_SHIFT = PRESENT

SAME_QUALITY_TEMPORAL_FOLLOW_THROUGH_DETERIORATION = YES

MARKET_ENVIRONMENT_INTERACTION_REMAINS = YES

WEAK_MARGINAL_ECONOMIC_LOSS_MATERIAL = YES

WINNER_OPPORTUNITY_COST_MATERIAL = YES

WEAK_MARGINAL_OVERALLOCATION_EVIDENCE = PARTIAL

EXISTING_EVIDENCE_SUFFICIENT_FOR_CAPITAL_SELECTIVITY = PARTIAL

NEW_FEATURE_REQUIRED = UNPROVEN

CODE_CHANGED = NO

RUN_MODIFIED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

MARKET_QUALITY_CHANGED = NO

COMPARABLE_MARGINAL_BLANKET_EXCLUSION = NO

RANK_CUTOFF_CREATED = NO

CONFIDENCE_CUTOFF_CREATED = NO

SHARE_PRICE_CUTOFF_CREATED = NO

FIXED_HOLDING_PERIOD_CREATED = NO

NEW_FEATURE_CREATED = NO

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0

## Highest-Value Next Investigation

Capital allocation semantics: determine whether existing evidence can shift
weak-marginal candidates toward smaller exploratory allocation or optional Cash
while preserving credible COMPARABLE_MARGINAL winners, without introducing a
blanket exclusion, rank cutoff, confidence cutoff, share-price cutoff, or new
indicator.
