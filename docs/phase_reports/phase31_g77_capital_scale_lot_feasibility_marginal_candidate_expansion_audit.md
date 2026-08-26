# Phase31-G77 — Capital Scale / Lot Feasibility / Marginal Candidate Expansion Audit

## PRIMARY_JUDGMENT

PHASE31_G77_CAPITAL_SCALE_MARGINAL_EXPANSION_CAUSALITY_CHARACTERIZED

Target run:

`runtime-test-historical-extended-smoke-20260823T140946562431Z`

Completed snapshot used:

- completed business days = `207`
- latest completed business date = `2023-08-03`

No code, config, threshold, weight, run state, fresh-run, resume, replay, or
Historical execution was changed or performed. G74 repair was not applied to
this running run.

## Evidence Basis

READ-ONLY artifacts:

- `daily/<date>/execution/fills.json`
- `daily/<date>/strategy/runtime_planning.json`
- `daily/<date>/strategy/portfolio_construction.json`
- `daily/<date>/strategy/portfolio_policy.json`
- `daily/<date>/strategy/position_sizing.json`
- `daily/<date>/strategy/market_context.json`
- `daily/<date>/current_valuation_refresh/valuation_projection.json`

BUY_NEW lots were reconstructed from fills and Runtime Planning intent. BUY_ADD
was excluded. Historical outcome was used only for cohort characterization.

## Window Summary

| Window | BUY_NEW Lots | PnL | Median Equity | Median Budget | Median Rank | Median Confidence | Median Ref Price | Median Lot Weight |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Baseline 2022-10 -> 2023-02 | 172 | +249,110 | 1,131,770 | 0.352 | 25.0 | 0.52 | 469.0 | 3.98% |
| Profit Burst 2023-03-15 -> 2023-04-06 | 26 | +489,310 | 1,435,960 | 0.551 | 29.5 | 0.43 | 1,201.0 | 8.69% |
| Recovery 2023-04-25 -> 2023-05-30 | 38 | +118,280 | 1,659,160 | 0.595 | 35.5 | 0.31 | 606.5 | 3.70% |
| Plateau 2023-05-31 -> 2023-08-03 | 82 | -72,700 | 1,663,960 | 0.376 | 35.0 | 0.32 | 646.9 | 3.91% |

Observation:

Equity grew from the baseline, but median lot weight did not keep rising after
the profit burst. The clearest post-peak shift is not high share price itself;
it is lower rank / lower confidence / more marginal-quality deployment.

## Audit A — Capital Scale

BUY_NEW decision-time capital scale:

| Window | Median Initial Notional | Median Initial Weight | Median 100-Share Lot Notional | Median Lot / Equity |
|---|---:|---:|---:|---:|
| Baseline | 48,033 | 4.10% | 46,900 | 3.98% |
| Profit Burst | 123,326 | 8.88% | 120,100 | 8.69% |
| Recovery | 69,651 | 4.26% | 60,650 | 3.70% |
| Plateau | 72,195 | 4.35% | 64,690 | 3.91% |

EQUITY_GROWTH_EXPANDS_LOT_FEASIBILITY = YES

Reason:

Equity growth reduced the relative burden of many 100-share lots versus the
early baseline, and the completed-date PC/PS artifacts show executable candidate
sets remained available post-peak. However, this is not a high-price-only
explanation, because profit burst had the highest median lot weight and still
performed strongly.

CAPITAL_SCALE_EFFECT_PRESENT = PARTIAL

Reason:

Capital scale helped make more candidates economically reachable, but the
quality deterioration is not reducible to equity scale. Recovery and plateau had
similar equity levels, while plateau quality and PnL were worse.

## Audit B — Executable Candidate Universe

Daily PC / G61 universe summary:

| Window | Dates | Median Valid Competitors | Median Lot-Executable Members | Median Allocated Securities | Median COMPARABLE_MARGINAL Allocations |
|---|---:|---:|---:|---:|---:|
| Baseline | 100 | 24.0 | 8.0 | 4.0 | 3.0 |
| Profit Burst | 16 | 24.5 | 5.0 | 4.0 | 4.0 |
| Recovery | 23 | 22.0 | 3.0 | 1.0 | 1.0 |
| Plateau | 46 | 23.0 | 4.0 | 3.0 | 2.0 |

EXECUTABLE_UNIVERSE_EXPANSION_MATERIAL = NO

Reason:

Post-peak plateau did not show a simple explosion in lot-executable count versus
baseline. Baseline median lot-executable members was `8`, while plateau was `4`.
The problem is not that the executable universe mechanically became much larger
than before; it is that the selected executable set was lower-confidence and
lower-rank than the profit burst set.

## Audit C — Marginal Candidate Expansion

BUY_NEW allocation class by window:

| Window | STRONG | COMPARABLE_HIGH | COMPARABLE_MARGINAL | Marginal Share |
|---|---:|---:|---:|---:|
| Baseline | 11 | 27 | 134 | 77.9% |
| Profit Burst | 1 | 0 | 25 | 96.2% |
| Recovery | 0 | 1 | 37 | 97.4% |
| Plateau | 6 | 11 | 65 | 79.3% |

Plateau class performance:

| Class | Count | PnL | Early / Next Losers | Early Loss PnL | Durable Winners | Durable Winner PnL |
|---|---:|---:|---:|---:|---:|---:|
| STRONG | 6 | -6,500 | 3 | -7,500 | 1 | +1,800 |
| COMPARABLE_HIGH | 11 | +10,860 | 3 | -8,400 | 4 | +25,660 |
| COMPARABLE_MARGINAL | 65 | -77,060 | 26 | -152,430 | 8 | +68,140 |

MARGINAL_CANDIDATE_SHARE_INCREASED = NO

Reason:

COMPARABLE_MARGINAL share was already very high in profit burst and recovery.
It did not increase in plateau relative to those windows.

MARGINAL_CANDIDATE_EARLY_FAILURE_MATERIAL = YES

Reason:

Plateau COMPARABLE_MARGINAL generated `26` early / next-day losers and
`-152,430` early-loss PnL. This explains most of G76's early failure bucket.

Interpretation:

The issue is not marginal class presence alone. Profit burst also bought mostly
COMPARABLE_MARGINAL and still produced strong PnL. The deterioration is within
the marginal population: plateau marginal candidates had weaker rank, confidence,
and follow-through.

## Audit D — Share Price Hypothesis

Plateau price / lot-notional by cohort:

| Cohort | Count | PnL | Median Ref Price | Median Lot Notional | Median Lot / Equity | Median Initial Weight |
|---|---:|---:|---:|---:|---:|---:|
| NEXT_DAY_LOSER | 5 | -38,200 | 1,085.0 | 108,500 | 6.59% | 6.60% |
| EARLY_LOSER | 27 | -130,130 | 809.0 | 80,900 | 4.82% | 4.88% |
| SHORT_WINNER | 17 | +51,200 | 374.0 | 37,400 | 2.20% | 3.30% |
| NEXT_DAY_WINNER | 7 | +5,430 | 529.0 | 52,900 | 3.21% | 3.22% |
| DURABLE_WINNER | 13 | +95,600 | 686.0 | 68,600 | 4.13% | 5.08% |
| DURABLE_LOSER | 9 | -48,400 | 728.0 | 72,800 | 4.40% | 4.41% |

Plateau price bands:

| Price Band | BUY_NEW Count | Early / Next Losers | Early Failure Rate | PnL |
|---|---:|---:|---:|---:|
| < 500 | 32 | 9 | 28.1% | +6,100 |
| 500-999 | 24 | 11 | 45.8% | -23,960 |
| 1000-1999 | 18 | 7 | 38.9% | -3,540 |
| >= 2000 | 8 | 5 | 62.5% | -51,300 |

HIGH_SHARE_PRICE_EARLY_FAILURE_ASSOCIATION = PRESENT

Important distinction:

This is an association, not a production threshold and not causal proof. High
share price / larger lot notional is associated with worse plateau early-failure
rates, but profit burst also held high lot weights and performed well. The
stronger causal interpretation is that high notional magnified weak-entry losses
when post-peak candidate quality was already weaker.

## Audit E — Budget Push / Optional Cash

Daily allocation behavior:

| Window | Allocation Days | Marginal Days | Marginal-Only Days | Median Marginal Security Weight | Median High/Strong Security Weight | Median Cash Allocation |
|---|---:|---:|---:|---:|---:|---:|
| Profit Burst | 16 | 16 | 15 | 35.87% | 0.00% | 6.51% |
| Recovery | 20 | 20 | 19 | 11.53% | 0.00% | 42.97% |
| Plateau | 42 | 40 | 29 | 17.37% | 0.00% | 14.21% |

Capital budget facts:

- `unallocated_residual` was `0` in all audited windows.
- Cash allocation was non-zero on nearly all marginal-allocation days.
- Plateau marginal + cash coexistence days = `40`.
- Plateau marginal-only high-quality-insufficient days = `29`.

CAPITAL_BUDGET_BEHAVES_AS_MAXIMUM = YES

Reason:

The budget is partitioned between securities and Cash, and Cash remains a valid
allocation. The artifacts do not show forced all-security deployment.

BUDGET_FILL_PRESSURE_EVIDENCE = YES

Reason:

Within the security sleeve, high-quality opportunity shortage often coincided
with COMPARABLE_MARGINAL receiving allocation. Since residual is always closed
to zero, the allocation machinery tends to express the budget fully as
securities plus Cash. This is not a hard all-cash suppression defect, but it is
evidence that marginal candidates absorb part of the deployable budget when
stronger candidates are scarce.

OPTIONAL_CASH_PRESERVED_WHEN_HIGH_QUALITY_OPPORTUNITIES_INSUFFICIENT = YES

Reason:

Cash was preserved alongside marginal allocations. Recovery median cash
allocation was `42.97%`; plateau median cash allocation was `14.21%`.

## Audit F — Quality vs Capital Scale

Plateau equity tertiles:

| Equity Tertile | BUY_NEW Count | Early Failure Rate | PnL | Median Rank | Median Confidence | Marginal Share |
|---|---:|---:|---:|---:|---:|---:|
| Low | 27 | 33.3% | +52,500 | 33.0 | 0.36 | 66.7% |
| Mid | 27 | 33.3% | +3,710 | 37.0 | 0.28 | 77.8% |
| High | 28 | 50.0% | -128,910 | 35.5 | 0.31 | 92.9% |

Plateau budget tertiles:

| Budget Tertile | BUY_NEW Count | Early Failure Rate | PnL | Median Rank | Median Confidence | Marginal Share |
|---|---:|---:|---:|---:|---:|---:|
| Low | 27 | 33.3% | -56,070 | 34.0 | 0.34 | 63.0% |
| Mid | 27 | 44.4% | +4,170 | 38.0 | 0.26 | 77.8% |
| High | 28 | 39.3% | -20,800 | 36.5 | 0.29 | 96.4% |

CAPITAL_SCALE_CONTRIBUTES_TO_POST_PEAK_PLATEAU = PARTIAL

Reason:

Higher equity tertile had the worst PnL and highest marginal share, and high
budget tertile had very high marginal share. But equity and budget do not
fully explain the result because recovery had similar equity and better net PnL,
and profit burst had larger lot weights with much better results.

## Four-Hypothesis Separation

### Hypothesis 1: High share price itself caused early failure

Judgment: PARTIAL / ASSOCIATIVE ONLY

High price bands had worse early-failure rates and losses, especially `>= 2000`
with `62.5%` early failure and `-51,300` PnL. But this does not prove price as
causal; it is likely loss magnification when weak-entry evidence is already
present.

### Hypothesis 2: Equity growth expanded lot feasibility into weaker candidates

Judgment: PARTIAL

Equity growth reduced lot weight burden, but daily lot-executable counts did not
explode versus baseline. The stronger evidence is not pure feasibility expansion
but larger ability to allocate to marginal candidates when few high-quality
candidates existed.

### Hypothesis 3: Opportunity set itself weakened post-peak

Judgment: YES

Plateau BUY_NEW had weaker median score, weaker confidence, lower rank, and
negative PnL relative to profit burst. This is the strongest explanation.

### Hypothesis 4: Capital Budget pushed weak candidates to fill deployment

Judgment: PARTIAL

Cash remained valid and present, so the system did not force all budget into
securities. However, marginal candidates frequently received allocation when
high/strong candidates were scarce, and residual was always zero. This is a
capital allocation pressure within the security sleeve, not a hard cash
suppression failure.

## Required Judgment

CAPITAL_SCALE_EFFECT_PRESENT = PARTIAL

EQUITY_GROWTH_EXPANDS_LOT_FEASIBILITY = YES

EXECUTABLE_UNIVERSE_EXPANSION_MATERIAL = NO

MARGINAL_CANDIDATE_SHARE_INCREASED = NO

MARGINAL_CANDIDATE_EARLY_FAILURE_MATERIAL = YES

HIGH_SHARE_PRICE_EARLY_FAILURE_ASSOCIATION = PRESENT

CAPITAL_BUDGET_BEHAVES_AS_MAXIMUM = YES

BUDGET_FILL_PRESSURE_EVIDENCE = YES

OPTIONAL_CASH_PRESERVED_WHEN_HIGH_QUALITY_OPPORTUNITIES_INSUFFICIENT = YES

CAPITAL_SCALE_CONTRIBUTES_TO_POST_PEAK_PLATEAU = PARTIAL

CODE_CHANGED = NO

RUN_MODIFIED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

MARKET_QUALITY_CHANGED = NO

BUY_FILTER_CREATED = NO

SHARE_PRICE_THRESHOLD_CREATED = NO

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0

## Highest-Value Next Investigation

Investigate the capital allocation semantics for COMPARABLE_MARGINAL candidates:
whether same-date evidence can distinguish "marginal but worth a small
exploratory allocation" from "marginal weak-entry that should leave more capital
in optional Cash" without creating a new BUY filter or share-price threshold.
