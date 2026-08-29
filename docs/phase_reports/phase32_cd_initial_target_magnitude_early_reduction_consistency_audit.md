# Phase32-CD — Initial Target Magnitude / Early Reduction Consistency Audit

## Executive Summary

Run audited: `runtime-test-historical-extended-smoke-20260829T021541366158Z`.

Available coverage inspected: 2022-10-03 through 2022-11-09. `run_state.json` still reports `RUNNING`; this audit only used already-materialized artifacts and did not resume, replay, backtest, or change production code/config.

Post-CC restored NEW/REENTRY target magnitude into actual path. The observed large initial share counts are mostly not high-conviction overweight allocations. They are usually 2.5-4.0% PC target weights converted into many 100-share lots because the symbols have very low reference prices.

The semantic inconsistency is therefore not simply “PC buys too many shares.” It is that PC can authorize multi-lot reduced/caution entries in weak regimes, while PM then begins REDUCE/EXIT within 1-5 business days using sell-side evidence that is often valid but sometimes very sensitive: repeated `risk_increased_but_trend_not_broken` reductions occur even when strategy intelligence continuation/downside fields still show `PASS` and campaign relative return is 0% to roughly -3.7%.

Overall judgment: `MIXED`, with a PC/PM semantic scale mismatch candidate. PC target magnitude currently means “PC-admitted target weight capitalized into executable lots under budget/cash/cap mechanics,” not pure conviction. PM post-entry management uses a different short-horizon deterioration scale.

## Evidence Scope

Artifacts read:

- `daily/*/strategy/portfolio_construction.json`
- `daily/*/strategy/marginal_capital_frontier_authority.json`
- `daily/*/strategy/position_sizing.json`
- `daily/*/strategy/runtime_planning.json`
- `daily/*/strategy/position_management.json`
- `daily/*/strategy/buy_quality_decisions.json`
- `daily/*/strategy/technical_features.json`
- `daily/*/strategy/market_context.json`

No production files or runtime state were modified.

## Early Reduction Rate

Across available coverage:

- Positive `BUY_NEW` planned rows: 77
- Large `BUY_NEW` planned rows with later held quantity >= 1000 shares: 9 rows
- Large held planned rows with REDUCE/EXIT within 5BD: 9/9 = 100.0%
- Unique large held campaigns represented by those rows: 5
- Unique large held campaigns with REDUCE/EXIT within 5BD: 5/5 = 100.0%

The unique large held campaigns are represented by `89180`, `76470`, `17570`, `37770`, and `93180`. `33500` is slightly below the 1000-share cutoff at 900 shares but shows the same early REDUCE/EXIT pattern.

PM early REDUCE/EXIT rows with campaign age <= 5BD across all symbols: 71 rows.

Reason-code distribution:

- `strategy_intelligence_sell_side_evidence_connected`: 71
- `risk_increased_but_trend_not_broken`: 39
- `trend_and_opportunity_broken`: 17
- `pm_discrete_control_persistent_deterioration_exit`: 9
- `hard_stop_current_return`: 6
- `peak_drawdown_warning`: 4
- `weak_hold_score`: 4
- `profit_retention_break`: 3

## Campaign Trace

| Symbol | Entry Used | Qty | Lots | Target W | Price | Rank | Quality | Opp | Entry State | Regime | T+1..T+5 PM | Diagnosis |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|
| 89180 | 2022-10-03 | 3700 | 37 | 3.36% | 9.0 | 25 | 0.585 | -0.339 | CONTINUATION_WITH_CAUTION | BEAR | 2022-10-04 EXIT: `hard_stop_current_return`, rel=-10.0% | Evidence deteriorated sharply; large share count is low-price mechanics |
| 76470 | 2022-10-04 | 1400 | 14 | 4.00% | 28.0 | 25 | 0.610 | -0.368 | CONTINUATION_WITH_CAUTION | RANGE | 2022-10-05/06/07 REDUCE: `risk_increased_but_trend_not_broken`, rel 0.0% to -3.57% | PM sensitivity / PC-PM scale mismatch candidate |
| 33500 | 2022-10-05 | 900 | 9 | 3.68% | 40.5 | 22 | 0.629 | -0.404 | CONTINUATION_WITH_CAUTION | RANGE | 2022-10-06/07/11 REDUCE, 2022-10-12 EXIT: `trend_and_opportunity_broken` | Same pattern below 1000 shares |
| 17570 | 2022-10-26 | 1600 | 16 | 3.85% | 24.0 | 35 | 0.562 | -0.575 | CONTINUATION_WITH_CAUTION | RECOVERY | 2022-10-27/28 REDUCE, 2022-10-31 EXIT: `weak_hold_score` | Weak entry evidence and fast PM unwind |
| 37770 | 2022-10-31 | 1200 | 12 | 3.23% | 27.0 | 43 | 0.499 | -0.849 | HEALTHY_CONTINUATION_ENTRY | BULL | 2022-11-01 HOLD, then repeated REDUCE from 2022-11-02 | PM sensitivity despite BULL entry context |
| 93180 | 2022-10-28 | 1100 | 11 | 3.70% PC target, 0.43% accepted | 4.0 | 4 | 0.773 | 0.065 | CONTINUATION_WITH_CAUTION | RECOVERY | HOLD through 2022-11-01, EXIT 2022-11-02: `trend_and_opportunity_broken` | Stronger selection signal, but later PM exit |
| 94320 | 2022-10-05 | 200 | 2 | 3.68% | 159.1 | 1 | 0.803 | 0.366 | CONTINUATION_WITH_CAUTION | RANGE | HOLD, then ADD on strong continuation | Maintained control |
| 94340 | 2022-10-03 | 200 | 2 | 3.36% | 144.1 | 3 | 0.766 | 0.240 | CONTINUATION_WITH_CAUTION | BEAR | HOLD then repeated ADD on strong continuation | Maintained control |

Notes:

- `17570` had an earlier 2022-10-13 positive BUY_NEW plan, but no held quantity appeared in subsequent PS state; the live campaign appears from the 2022-10-26 entry.
- `93180` had larger planned quantities on 2022-10-25 through 2022-10-27, but the live held position appears as 1100 shares after the 2022-10-28 accepted BF target. The PC target magnitude authority for 2022-10-28 resolved 9400 shares, while common budget competition accepted only 11 lots.

## Target Magnitude Meaning

Observed PC target magnitude is a composite of:

- PC production admission: mostly `BUY_NEW_REDUCED_ONLY` and `CONTINUATION_WITH_CAUTION` for the early-reduced examples.
- Buy Quality and rank: early-reduced examples often have mediocre rank and negative opportunity scores; maintained controls have rank 1/3 and positive opportunity scores.
- Allocation/budget mechanics: target weights around 2.5-4.0% are admitted and then expanded lot-by-lot by the common frontier.
- Lot mechanics: low reference prices create large share counts from modest notional weights.
- Regime/risk context: several large entries occur in BEAR/RANGE/RECOVERY with caution states.
- Cash/budget competition: CC does not automatically consume the full PC target quantity; BF accepted lots can be materially below PC hard upper authority.

Therefore, `PC target magnitude != pure conviction`.

It more accurately means:

`PC-admitted target weight / executable quantity magnitude, bounded by budget/cash/cap and represented as lots for capital competition`.

## PC vs PM Semantic Consistency

Consistency evidence:

- Severe early failures have clear PM evidence. `89180` exits at T+1 with `hard_stop_current_return` and -10.0% campaign relative return.
- `33500` transitions from repeated REDUCE to EXIT as `trend_and_opportunity_broken` appears.
- Maintained controls `94320` and `94340` have high rank, positive opportunity, positive expected edge, and PM HOLD/ADD decisions.

Inconsistency evidence:

- Several REDUCE decisions fire while `strategy_intelligence_continuation_quality_status = PASS` and `strategy_intelligence_downside_risk_status = PASS`.
- Repeated `risk_increased_but_trend_not_broken` reductions occur at 0.0% relative return for `76470`, `17570`, and other early rows.
- PC allows multi-lot reduced/caution entry in weak regimes, while PM can immediately classify the same campaign as defensive/caution and start reducing.
- PC target magnitude captures entry-time allocation magnitude, but PM does not appear to consume or normalize against the entry admission class or intended hold horizon.

## Maintained vs Early-Reduced Controls

Maintained controls:

- `94320`: rank 1, opportunity 0.3656, quality 0.8033, 2 entry lots, PM HOLD/ADD.
- `94340`: rank 3, opportunity 0.2403, quality 0.7659, 2 entry lots, PM HOLD/ADD.

Early-reduced examples:

- `89180`: rank 25, opportunity -0.3390, quality 0.5853, 37 entry lots, BEAR.
- `76470`: rank 25, opportunity -0.3678, quality 0.6096, 14 entry lots, RANGE.
- `17570`: rank 35, opportunity -0.5746, quality 0.5624, 16 entry lots, RECOVERY.
- `37770`: rank 43, opportunity -0.8494, quality 0.4995, 12 entry lots, BULL, but PM reduced after one hold day.

The strongest separator is not share count. It is entry evidence quality/opportunity/rank plus whether the symbol had persistent positive continuation after entry.

## Diagnosis

Classification for “1000+ shares then REDUCE in 1-3BD”:

- A. Evidence genuinely worsened: YES for hard-stop / trend-broken cases such as `89180`, `33500`, and `93180`.
- B. Entry target magnitude too strong: PARTIAL. In weight terms most entries are not extreme, but caution/reduced-only entries can still become many lots and substantial operational exposure in weak regimes.
- C. PM REDUCE too sensitive: PARTIAL. Repeated REDUCE at 0.0% to mild negative relative return with continuation/downside still PASS suggests the sell-side scaler is more sensitive than the entry magnitude semantic.
- D. PC and PM use different semantic scales: YES / PARTIAL. PC uses entry admission + target-weight/lot/budget semantics; PM uses short-horizon campaign deterioration and risk severity without clearly preserving PC entry conviction/hold-horizon context.
- E. MIXED: YES.

## Defect / No-Defect Judgment

No evidence found that CC itself violates target magnitude restoration. CC appears to be doing what CB designed: it preserves PC target magnitude and converts it into lots under common budget competition.

The candidate production defect is upstream/downstream semantic consistency:

- PC permits sizable multi-lot capital deployment for low-ranked, negative-opportunity, caution/reduced-only NEW entries.
- PM can then begin immediate defensive reductions without a shared semantic bridge explaining why an entry large enough for many lots should be rapidly unwound.

This is not a performance-tuning conclusion. It is a decision-time semantic-contract mismatch.

## Recommendation

Production repair is justified in design/audit form before any tuning:

- Define the semantic meaning of PC initial target magnitude by entry admission class.
- Add a PC-to-PM post-entry contract that materializes entry conviction, admission class, intended holding tolerance, and initial-risk budget.
- Audit whether PM REDUCE should distinguish “newly entered caution position behaving as expected” from “fresh deterioration beyond entry premise.”
- Do not change thresholds, weights, or use future PnL to select parameters.

## Final Judgments

PHASE32_CD_PC_TARGET_MAGNITUDE_SEMANTIC = PC-admitted target weight / executable quantity magnitude capitalized by lot mechanics and bounded by budget/cash/cap; not pure conviction.

PHASE32_CD_EARLY_REDUCTION_RATE = unique large held NEW campaigns 5/5 = 100.0%; large planned held rows 9/9 = 100.0%; all PM age<=5BD REDUCE/EXIT rows = 71.

PHASE32_CD_ENTRY_PM_SEMANTIC_CONSISTENCY = PARTIAL

PHASE32_CD_PRIMARY_DIAGNOSIS = MIXED: PC target magnitude restoration is working, but PC entry magnitude and PM early reduction use different decision-time semantic scales, especially for caution/reduced-only low-price entries.

PHASE32_CD_PC_INITIAL_SIZING_OVERAGGRESSIVE = PARTIAL

PHASE32_CD_PM_REDUCE_OVERSENSITIVE = PARTIAL

PHASE32_CD_PRODUCTION_REPAIR_JUSTIFIED = PARTIAL

PHASE32_CD_NEXT_STEP = Design a narrow PC-entry-to-PM-management semantic bridge: preserve CC magnitude, but materialize entry admission class / initial conviction / expected hold tolerance so PM can distinguish expected early noise from true post-entry deterioration without threshold or PnL tuning.
