# Phase31-G79 - Opportunity Set Quality / Momentum Persistence Causality Audit

## PRIMARY_JUDGMENT

PHASE31_G79_POST_PEAK_MOMENTUM_OPPORTUNITY_DETERIORATION_CAUSALITY_CONFIRMED

Target run:

`runtime-test-historical-extended-smoke-20260823T140946562431Z`

Completed snapshot used:

- completed business days = `216`
- latest completed business date = `2023-08-17`

No code, config, threshold, weight, run state, fresh-run, resume, replay, or
Historical execution was changed or performed. G74 repair was not applied to
this running run.

## Evidence Basis

READ-ONLY completed-date artifacts:

- `daily/<date>/strategy/buy_quality_decisions.json`
- `daily/<date>/strategy/portfolio_construction.json`
- `daily/<date>/strategy/portfolio_policy.json`
- `daily/<date>/strategy/market_context.json`
- `daily/<date>/strategy/runtime_planning.json`
- `daily/<date>/execution/fills.json`

BUY_NEW lots were reconstructed from completed-date fills and same-date
Runtime / PC evidence. Historical outcome was used only for cohort
characterization and PnL attribution, not for production decision correctness
or parameter selection.

## Root Cause

POST_PEAK_MOMENTUM_OPPORTUNITY_DETERIORATION_ROOT_CAUSE =
CAPITAL_ALLOCATION_WEAK_OPPORTUNITY_OVERDEPLOYMENT_WITH_MOMENTUM_PERSISTENCE_DETERIORATION

The post-peak weakness is not primarily that the top of the daily candidate set
disappeared. Daily top-candidate quality was not worse in Plateau than in
Profit Burst. The direct failure pattern is:

1. Candidate ranking still contains information.
2. Plateau BUY_NEW materialization shifted heavily toward rank `31+`,
   low-confidence, weak-score opportunities.
3. Similar broad quality bins had worse follow-through in Plateau than in
   Profit Burst.
4. On weaker-opportunity Plateau days, capital allocation did not preserve more
   optional Cash; it allocated more security weight and more marginal security
   weight than stronger-opportunity days.

This points to an allocation semantics problem under weak opportunity-set
conditions, not a blanket Market Quality defect and not a broken Candidate AI
rank ordering.

## Audit A - Opportunity Set Distribution

Daily candidate-set medians:

| Window | Dates | Valid Candidates | Top1 Score | Top3 Score | Top10 Score | Median Score | UQ Score | Score Spread | Top10 Confidence | Median Confidence | Top10 Quality | Median Quality |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline 2022-10 -> 2023-02 | 100 | 50 | +0.374 | +0.263 | +0.010 | -0.494 | -0.273 | 0.850 | 0.90 | 0.48 | 0.748 | 0.600 |
| Profit Burst 2023-03-15 -> 2023-04-06 | 16 | 50 | +0.340 | +0.271 | +0.146 | -0.386 | -0.164 | 0.724 | 0.90 | 0.49 | 0.741 | 0.586 |
| Recovery 2023-04-25 -> 2023-05-30 | 23 | 50 | +0.370 | +0.296 | -0.002 | -0.343 | -0.219 | 0.730 | 0.90 | 0.48 | 0.763 | 0.591 |
| Plateau 2023-05-31 -> 2023-08-17 | 56 | 50 | +0.444 | +0.327 | +0.028 | -0.438 | -0.204 | 0.887 | 0.89 | 0.48 | 0.759 | 0.598 |

TOP_CANDIDATE_ABSOLUTE_QUALITY_DETERIORATED = NO

OPPORTUNITY_SET_QUALITY_DETERIORATION = PARTIAL

Reason:

The upper candidate set was not lower quality in absolute terms. Plateau top1
and top3 scores were higher than Profit Burst, and top10 confidence / quality
were comparable. However, the deployed BUY_NEW cohort deteriorated sharply:

| Window | BUY_NEW Lots | Closed/Reconstructed PnL | Early Losers | Durable Winners | Median Rank | Median Score | Median Confidence | Median Quality | Median Allocation |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Profit Burst | 26 | +489,310 | 7 | 5 | 29.5 | -0.387 | 0.43 | 0.588 | 8.88% |
| Recovery | 38 | +118,280 | 12 | 11 | 35.5 | -0.455 | 0.25 | 0.549 | 4.26% |
| Plateau | 95 | -129,240 | 39 | 12 | 35.0 | -0.523 | 0.22 | 0.544 | 4.41% |

This separates H2 from H1/H4: the whole candidate set did not collapse at the
top, but the actual selected / allocated tail weakened.

## Audit B - Opportunity Set Richness

Canonical PC opportunity quality distribution remained marginal-heavy:

| Window | STRONG | COMPARABLE_HIGH | COMPARABLE_MARGINAL | Security Allocations | Cash Allocation | Security Weight | Marginal Security Weight |
|---|---:|---:|---:|---:|---:|---:|---:|
| Baseline | 0 | 1 | 22 | 4.0 | 1.31% | 23.47% | 18.44% |
| Profit Burst | 0 | 0 | 23 | 4.0 | 6.51% | 35.92% | 35.87% |
| Recovery | 0 | 0 | 21 | 1.0 | 47.04% | 10.81% | 10.81% |
| Plateau | 0 | 0 | 22 | 3.0 | 13.02% | 18.03% | 15.97% |

The coarse PC class distribution does not explain the difference by itself.
Profit Burst was also almost entirely COMPARABLE_MARGINAL and produced strong
profit. The missing distinction is not "marginal vs non-marginal"; it is how
much low-rank / low-confidence marginal evidence should receive capital when
the stronger opportunity set is scarce.

## Audit C - Same-Quality Follow-Through

Matched bins used only existing decision-time evidence:

- rank band
- confidence band
- runtime opportunity score band
- quality score band
- momentum state
- allocation class

Representative matched bins:

| Existing Evidence Bin | Profit Burst n / PnL / Early / Durable | Plateau n / PnL / Early / Durable |
|---|---:|---:|
| rank 21-35, confidence mid, score mild, quality mid, mixed momentum, COMPARABLE_MARGINAL | 7 / +38,400 / 1 / 2 | 5 / -20,710 / 3 / 0 |
| rank 36+, confidence low, score mild, quality low, mixed momentum, COMPARABLE_MARGINAL | 3 / +7,010 / 2 / 0 | 2 / -4,300 / 1 / 0 |
| rank 36+, confidence low, score weak, quality low, mixed momentum, COMPARABLE_MARGINAL | 4 / +9,000 / 1 / 0 | 23 / -60,310 / 13 / 1 |

MOMENTUM_PERSISTENCE_DETERIORATION = YES

Reason:

The largest shared weak-marginal bin expanded from `4` Profit Burst cases to
`23` Plateau cases and flipped from mildly positive to materially negative.
This confirms G78's same-quality temporal deterioration: broad same-date
quality fields remained similar, but post-entry follow-through probability was
worse in Plateau.

## Audit D - Cross-Sectional Momentum Structure

Daily momentum and quality structure:

| Window | Healthy Momentum Ratio | Mixed Momentum Ratio | HIGH Band Count | Full Allocation Eligible | Reduced Allocation Only |
|---|---:|---:|---:|---:|---:|
| Baseline | 22% | 56% | 6.0 | 4.0 | 29.0 |
| Profit Burst | 14% | 60% | 6.0 | 4.5 | 26.5 |
| Recovery | 14% | 54% | 6.0 | 4.0 | 25.0 |
| Plateau | 18% | 56% | 8.0 | 5.0 | 25.0 |

The broad momentum labels did not show an obvious collapse. Plateau even had
slightly more HIGH band / full-eligible candidates than Profit Burst. Therefore
the deterioration is not captured by the coarse momentum state alone.

Interpretation:

H3 is confirmed at outcome characterization level, but producer-level evidence
is only partial. Existing candidate fields show the weak tail and rank/confidence
structure; they do not fully materialize a canonical "momentum persistence"
authority that separates Profit Burst-like marginal candidates from Plateau-like
marginal candidates.

## Audit E - Market Quality Interaction

Same Market Quality states behaved differently across windows:

| Market Quality | Window | Dates | Top10 Score | Median Score | Cash | Security Weight | Marginal Weight | BUY_NEW PnL | Early Losers |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| CONFLICTED_MARKET_STRUCTURE | Profit Burst | 5 | +0.146 | -0.408 | 12.50% | 37.89% | 36.23% | +172,200 | 0 |
| CONFLICTED_MARKET_STRUCTURE | Plateau | 8 | -0.033 | -0.472 | 16.80% | 16.18% | 16.18% | -34,920 | 8 |
| RECOVERY_CONFIRMATION_INCOMPLETE | Profit Burst | 5 | +0.088 | -0.401 | 6.51% | 23.17% | 23.17% | -46,100 | 3 |
| RECOVERY_CONFIRMATION_INCOMPLETE | Plateau | 16 | -0.073 | -0.499 | 7.81% | 24.40% | 20.70% | -68,440 | 11 |
| SHORT_TERM_BREADTH_BREAKDOWN | Profit Burst | 6 | +0.233 | -0.321 | 3.58% | 33.88% | 33.88% | +363,210 | 4 |
| SHORT_TERM_BREADTH_BREAKDOWN | Plateau | 18 | +0.018 | -0.443 | 3.79% | 17.69% | 14.99% | +5,980 | 9 |

MARKET_QUALITY_STATE_TOO_COARSE_FOR_OPPORTUNITY_SET_QUALITY = YES

This is not the same as a Market Quality defect. Market Quality is a
portfolio-level capital pacing context. The evidence shows that within the same
MQ state, the candidate/opportunity set can be very different. The missing
materialization appears closer to Opportunity Set Quality / allocation response
than to MQ security admission.

## Audit F - Capital Allocation Response

Plateau days split by existing top10 opportunity score:

| Plateau Subset | Dates | Top10 Score | Cash Allocation | Security Weight | Marginal Security Weight | Security Count | Budget |
|---|---:|---:|---:|---:|---:|---:|---:|
| Weaker opportunity days | 28 | -0.033 | 7.94% | 24.12% | 22.13% | 3.0 | 35.93% |
| Stronger opportunity days | 28 | +0.098 | 18.01% | 15.64% | 14.21% | 2.5 | 36.24% |

CAPITAL_ALLOCATION_RESPONDS_TO_OPPORTUNITY_SET_QUALITY = NO

CAPITAL_ALLOCATION_WEAK_OPPORTUNITY_OVERDEPLOYMENT = YES

Reason:

The direction is inverted for the audited Plateau split. Weaker-opportunity
days had less Cash and more security / marginal security allocation than
stronger-opportunity days, while budget was nearly the same. This is the
cleanest producer-boundary causal evidence in G79: PC allocation has the fields
needed to see opportunity-set weakness, but the final security-vs-Cash
partition does not preserve optionality on those weaker days.

## Audit G - Candidate Ranking Health

BUY_NEW outcome by rank bucket:

| Window | Rank Bucket | Count | PnL | Early Losers | Durable Winners | Median Confidence | Median Score |
|---|---|---:|---:|---:|---:|---:|---:|
| Profit Burst | 1-10 | 2 | +313,200 | 0 | 1 | 0.94 | +0.219 |
| Profit Burst | 11-20 | 3 | +43,700 | 0 | 1 | 0.66 | -0.241 |
| Profit Burst | 21-30 | 11 | +119,900 | 2 | 2 | 0.48 | -0.350 |
| Profit Burst | 31+ | 10 | +12,510 | 5 | 1 | 0.24 | -0.481 |
| Plateau | 1-10 | 5 | +26,900 | 0 | 2 | 0.84 | -0.012 |
| Plateau | 11-20 | 12 | +18,800 | 5 | 3 | 0.66 | -0.278 |
| Plateau | 21-30 | 14 | -24,700 | 5 | 2 | 0.44 | -0.491 |
| Plateau | 31+ | 64 | -150,240 | 29 | 5 | 0.09 | -0.584 |

CANDIDATE_RANKING_STILL_DISCRIMINATIVE = YES

CANDIDATE_SELECTION_DEFECT = PARTIAL

Reason:

The ranking order still carries economic signal: Plateau rank `1-20` remained
positive while rank `31+` absorbed most of the loss. The defect is not that the
ranker lost all discrimination. The defect is that the allocation/materialization
path kept buying deep into the weak tail during Plateau.

## Required Causal Classification

| Factor | Evidence Strength | Contribution Evidence |
|---|---|---|
| CANDIDATE_SELECTION_DETERIORATION | Medium | Plateau BUY_NEW median rank/confidence deteriorated; rank `31+` = `64` lots / `-150,240` PnL. |
| OPPORTUNITY_SET_QUALITY_DETERIORATION | Partial | Top-candidate quality did not deteriorate, but selected tail and same-MQ opportunity quality did. |
| MOMENTUM_PERSISTENCE_DETERIORATION | Strong | Matched weak-marginal bins were materially worse in Plateau; same broad evidence had poorer follow-through. |
| CAPITAL_ALLOCATION_WEAK_OPPORTUNITY_OVERDEPLOYMENT | Strong | Weaker Plateau opportunity days had lower Cash and higher security/marginal security allocation. |
| MARKET_QUALITY_GRANULARITY_LIMIT | Strong | Same MQ states had materially different candidate-set quality and BUY_NEW outcomes. |
| OTHER / UNRESOLVED | Medium | No canonical producer currently isolates persistence quality beyond existing candidate/momentum fields. |

## Required Judgment

POST_PEAK_MOMENTUM_OPPORTUNITY_DETERIORATION_ROOT_CAUSE =
CAPITAL_ALLOCATION_WEAK_OPPORTUNITY_OVERDEPLOYMENT_WITH_MOMENTUM_PERSISTENCE_DETERIORATION

OPPORTUNITY_SET_QUALITY_DETERIORATION = PARTIAL

TOP_CANDIDATE_ABSOLUTE_QUALITY_DETERIORATED = NO

MOMENTUM_PERSISTENCE_DETERIORATION = YES

CANDIDATE_RANKING_STILL_DISCRIMINATIVE = YES

CANDIDATE_SELECTION_DEFECT = PARTIAL

CAPITAL_ALLOCATION_WEAK_OPPORTUNITY_OVERDEPLOYMENT = YES

MARKET_QUALITY_STATE_TOO_COARSE_FOR_OPPORTUNITY_SET_QUALITY = YES

EXISTING_EVIDENCE_CAN_DETECT_OPPORTUNITY_SCARCITY = PARTIAL

NEW_FEATURE_REQUIRED = UNPROVEN

CODE_CHANGED = NO

RUN_MODIFIED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

MARKET_QUALITY_CHANGED = NO

CANDIDATE_RANKING_CHANGED = NO

BUY_FILTER_CREATED = NO

NEW_INDICATOR_CREATED = NO

NEW_SCORE_CREATED = NO

COMPARABLE_MARGINAL_BLANKET_EXCLUSION = NO

RANK_CUTOFF_CREATED = NO

CONFIDENCE_CUTOFF_CREATED = NO

SHARE_PRICE_CUTOFF_CREATED = NO

FIXED_CASH_TARGET_CREATED = NO

HISTORICAL_PERIOD_SPECIFIC_THRESHOLD_CREATED = NO

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0

## Highest-Value Next Action

Existing-evidence capital allocation semantics repair: use the already
materialized opportunity-set quality / rank-confidence / top-vs-tail evidence
to decide security sleeve vs optional Cash more coherently on weak-opportunity
days, while preserving high-ranked COMPARABLE_MARGINAL winners and without
creating a blanket exclusion, rank cutoff, confidence cutoff, share-price
cutoff, fixed Cash target, new indicator, or Market Quality hard BUY gate.
