# Phase32-CE — NEW Production Admission Quality / Rank Semantic Audit

## Executive Summary

Run audited: `runtime-test-historical-extended-smoke-20260829T021541366158Z`.

Available coverage inspected: 2022-10-03 through 2022-11-09, using existing artifacts only. No production code/config/runtime state was changed, and no fresh run, resume, replay, or backtest was executed.

Primary finding: candidate eligibility and production deployability are only partially separated for `BUY_NEW`.

The system does preserve a formal deployability boundary: most `BUY_NEW` candidate rows do not receive positive target weight. However, once PC assigns positive `target_weight`, the active production admission seen by the frontier is effectively:

```text
membership_intent = ADD_CANDIDATE
target_weight > 0
target_weight_resolution.status = PASS
```

This admits many low-rank / negative-opportunity / caution rows into real capital deployment. More importantly, `target_weight_resolution.adjustments` show that Adaptive Buy Quality often reduces target weight, but downstream budget reconciliation / lot-aware final reallocation restores the full pre-quality/base weight. That weakens the semantic distinction between “candidate remains valid” and “deploy production NEW capital at this magnitude.”

## Architecture Baseline

Relevant SoT points:

- Adaptive BUY Quality must evaluate whether a BUY opportunity is trustworthy and allocation-capable, using PIT opportunity, market context, signal reliability, execution feasibility, and portfolio fit.
- Candidate AI is an opportunity producer, not the owner of portfolio capital allocation.
- `runtime_opportunity_score` is signful relative evidence, but negative uncalibrated score is not an absolute rejection authority by itself.
- PC owns target membership and `target_weight`.
- Position Sizing must not reinterpret opportunity score to decide membership or target weight.
- Marginal capital authority asks whether the next executable increment of scarce capital is valuable versus alternatives and Cash.

Therefore, low rank or negative uncalibrated opportunity score need not be a hard reject. But if such rows deploy capital, the artifact chain must preserve why they are production-deployable and at what reduced magnitude.

## Aggregate NEW Admission

Across available coverage:

- Total `BUY_NEW` PC rows: 939
- Positive PC `target_weight` NEW rows: 122
- PS-positive NEW rows: 87

This means candidate-to-deployability separation exists at a coarse level: 817/939 `BUY_NEW` rows did not receive positive PC target weight. The concern is the semantics of the 122 positive target rows and 87 PS-positive rows.

### Positive PC Target Rows

Rank bucket distribution:

| Rank bucket | Count | Avg target weight | Negative opportunity | Caution/reduced |
|---|---:|---:|---:|---:|
| 1-10 | 36 | 6.948% | 25 | 35 |
| 11-20 | 28 | 11.384% | 28 | 27 |
| 21-30 | 24 | 7.263% | 24 | 24 |
| 31+ | 34 | 8.839% | 34 | 20 |

Other distributions:

- Entry state: `CONTINUATION_WITH_CAUTION` 106, `HEALTHY_CONTINUATION_ENTRY` 16
- Entry action: `BUY_NEW_REDUCED_ONLY` 106, `BUY_NEW_ALLOWED` 16
- Regime: RANGE 45, BULL 31, BEAR 22, RECOVERY 21, CORRECTION 3
- Negative opportunity score: 111/122
- Rank >20: 58/122
- Caution/reduced admission: 106/122

### PS-Positive NEW Rows

Rank bucket distribution:

| Rank bucket | Count | Avg target weight | Avg PS qty | Negative opportunity | Caution/reduced |
|---|---:|---:|---:|---:|---:|
| 1-10 | 29 | 4.158% | 1110.3 | 18 | 28 |
| 11-20 | 19 | 7.696% | 105.3 | 19 | 18 |
| 21-30 | 20 | 6.213% | 445.0 | 20 | 20 |
| 31+ | 19 | 5.147% | 300.0 | 19 | 15 |

Other distributions:

- Entry state: `CONTINUATION_WITH_CAUTION` 81, `HEALTHY_CONTINUATION_ENTRY` 6
- Entry action: `BUY_NEW_REDUCED_ONLY` 81, `BUY_NEW_ALLOWED` 6
- Negative opportunity score: 76/87
- Rank >20: 39/87
- Caution/reduced admission: 81/87

This is material low-rank/caution production admission.

## Representative Evidence Chains

### Maintained / Stronger Controls

`94320`, 2022-10-05:

- Rank 1, opportunity 0.3656, quality 0.8033
- Buy Quality: `REDUCED_ALLOCATION_ONLY`, band HIGH
- Entry: `BUY_NEW_REDUCED_ONLY`, `CONTINUATION_WITH_CAUTION`, sufficient evidence
- Market: RANGE / `CONFLICTED_MARKET_STRUCTURE` / WEAK breadth
- Momentum/trend: 5D momentum 3.38%, close/MA20 1.0233
- PC target weight: 3.68%
- BF/PS: 2 lots, 200 shares
- Frontier first-lot capital value: 0.7517; beats Cash
- Production admission reason: `pc_first_lot_positive_target_weight_admitted`

This row has low-risk admission concerns because rank, opportunity, quality, and trend evidence are all comparatively strong even though entry class is reduced/caution.

`94340`, 2022-10-03:

- Rank 3, opportunity 0.2403, quality 0.7659
- Buy Quality: `FULL_ALLOCATION_ELIGIBLE`, band HIGH, but PC entry still `BUY_NEW_REDUCED_ONLY`
- Market: BEAR / `SHORT_TERM_BREADTH_BREAKDOWN` / WEAK breadth
- Momentum/trend: 5D momentum -3.09%, close/MA20 0.9637
- PC target weight: 3.3636%
- BF/PS: 2 lots, 200 shares
- Frontier first-lot capital value: 0.5722; beats Cash
- Production admission reason: `pc_first_lot_positive_target_weight_admitted`

This row is defensible primarily because rank and opportunity remain strong despite weak market/trend context.

### Low-Rank / Caution Production Deployments

`89180`, 2022-10-03:

- Rank 25, opportunity -0.3390, quality 0.5853
- Buy Quality: `REDUCED_ALLOCATION_ONLY`, band MEDIUM
- Entry: `BUY_NEW_REDUCED_ONLY`, `CONTINUATION_WITH_CAUTION`
- Market: BEAR / `SHORT_TERM_BREADTH_BREAKDOWN` / WEAK breadth
- Momentum/trend: 1D -10.0%, 5D -10.0%, close/MA20 0.8911
- PC target weight: 3.3636%
- BF/PS: 37 lots, 3700 shares, due to 9.0 reference price
- Frontier first-lot capital value: 0.4038; opportunity component clamps to 0.0, rank component 0.04, but quality/headroom/requalification keep it above Cash
- Production admission reason: `pc_first_lot_positive_target_weight_admitted`
- T+1 PM: EXIT with `hard_stop_current_return`

`76470`, 2022-10-04:

- Rank 25, opportunity -0.3678, quality 0.6096
- Buy Quality: `REDUCED_ALLOCATION_ONLY`, band MEDIUM
- Entry: `BUY_NEW_REDUCED_ONLY`, `CONTINUATION_WITH_CAUTION`
- Market: RANGE / `CONFLICTED_MARKET_STRUCTURE` / WEAK breadth
- Momentum/trend: 1D 3.70%, 5D -3.45%, close/MA20 1.0054
- PC target weight: 4.0%
- BF/PS: 14 lots, 1400 shares
- Frontier first-lot capital value: 0.4089; opportunity component clamps to 0.0, rank component 0.04
- Production admission reason: `pc_first_lot_positive_target_weight_admitted`
- T+1 onward PM: repeated REDUCE with `risk_increased_but_trend_not_broken`

`17570`, 2022-10-26:

- Rank 35, opportunity -0.5746, quality 0.5624
- Buy Quality: `REDUCED_ALLOCATION_ONLY`, band MEDIUM
- Entry: `BUY_NEW_REDUCED_ONLY`, `CONTINUATION_WITH_CAUTION`
- Market: RECOVERY / `RECOVERY_CONFIRMATION_INCOMPLETE` / NEUTRAL breadth
- Momentum/trend: 5D 4.35%, close/MA20 1.0835
- PC target weight: 3.8462%
- BF/PS: 16 lots, 1600 shares
- Frontier first-lot capital value: 0.3950; opportunity component clamps to 0.0, rank component 0.0286
- Production admission reason: `pc_first_lot_positive_target_weight_admitted`
- T+1/T+2 PM: REDUCE at 0.0% campaign relative return; T+3 EXIT by `weak_hold_score`

`37770`, 2022-10-31:

- Rank 43, opportunity -0.8494, quality 0.4995
- Buy Quality: `REDUCED_ALLOCATION_ONLY`, band LOW
- Entry: `BUY_NEW_ALLOWED`, `HEALTHY_CONTINUATION_ENTRY`
- Market: BULL / `HEALTHY_EXPANSION` / STRONG breadth
- Momentum/trend: 1D 3.85%, 5D 12.5%, close/MA20 1.0976
- PC target weight: 3.2258%
- BF/PS: 12 lots, 1200 shares
- Frontier first-lot capital value: 0.3780; opportunity component clamps to 0.0, rank component 0.0233
- Production admission reason: `pc_first_lot_positive_target_weight_admitted`
- T+1 PM HOLD, then repeated REDUCE from T+2

This row demonstrates that favorable market/trend context can combine with low Buy Quality / low rank / negative opportunity to produce `BUY_NEW_ALLOWED`.

## Target-Weight Resolution Semantic Gap

For the low-rank examples, target resolution shows an important inconsistency:

| Symbol | PC target | Buy Quality post-quality target | Final/lot target | Observation |
|---|---:|---:|---:|---|
| 89180 | 3.3636% | 1.9686% | 3.3636% | Quality reduction not preserved into final target |
| 76470 | 4.0000% | 2.4384% | 4.0000% | Quality reduction not preserved |
| 17570 | 3.8462% | 2.1632% | 3.8462% | Quality reduction not preserved |
| 37770 | 3.2258% | 1.6113% | 3.2258% | Quality reduction not preserved |
| 94320 | 3.6800% | 2.9561% | 3.6800% | Reduction weakened but row still strong |
| 94340 | 3.3636% | 3.3636% | 3.3636% | No effective quality reduction |

The artifact chain records `ADAPTIVE_BUY_QUALITY_AUTHORITY` reduction, but `PORTFOLIO_CONSTRUCTION_INCREMENTAL_BUDGET_RECONCILIATION` and `PORTFOLIO_CONSTRUCTION_LOT_AWARE_FINAL_REALLOCATION` restore the base target weight for many rows.

This is the clearest candidate defect:

```text
Buy Quality says reduced allocation.
PC target resolution records the reduction.
Final deployable target frequently returns to pre-quality/base weight.
```

## Candidate vs Deployability Separation

Separation status: PARTIAL.

PASS evidence:

- Only 122/939 `BUY_NEW` PC rows received positive target weight.
- Only 87/939 became PS-positive.
- BV still blocks legacy zero-target NEW rows from BF/PS promotion.

FAIL/PARTIAL evidence:

- Positive target rows include 58/122 rank >20 and 111/122 negative opportunity scores.
- PS-positive rows include 39/87 rank >20 and 76/87 negative opportunity scores.
- 81/87 PS-positive rows are `BUY_NEW_REDUCED_ONLY`.
- Frontier `production_admission` uses positive target weight as admission, not the richer rank/opportunity/quality class.
- Capital value clamps negative opportunity to 0.0, but quality/headroom/requalification can still beat Cash even for rank 25/35/43 rows.
- Target-weight quality reductions are not consistently preserved into final deployable target magnitude.

## Classification

A. Low rank but other strong PIT evidence exists: PARTIAL. This is true for selected controls like `94320` and partly for `37770` trend/regime context, but not generally for the low-rank negative-opportunity caution rows.

B. Reduced/caution admission is too broad: YES. `BUY_NEW_REDUCED_ONLY` accounts for 81/87 PS-positive NEW rows.

C. Rank/opportunity is weakly handled in admission: YES / PARTIAL. Rank/opportunity influence quality/value, but they do not prevent production deployability once PC target weight is positive. Negative opportunity is clamped to 0 in frontier value rather than represented as an explicit caution/deployability boundary.

D. Candidate eligibility leaks into Production deployability: PARTIAL. Coarse separation exists, but `candidate_eligible` plus positive target-weight resolution is enough for many weak/caution rows to pass.

E. PC target allocation and Entry Quality semantic are inconsistent: YES. Quality reductions are recorded but frequently not preserved into final deployable target weight.

F. MIXED: YES.

## Recommendation

Production repair is justified, but should be narrow and semantic-contract based:

- Do not add a rank cutoff or raw opportunity-score threshold.
- Restore target-weight resolution consistency so Adaptive Buy Quality reductions are not overwritten by later budget/lot stages unless an explicit PC authority says why.
- Separate `candidate_eligible` from `production_deployable_new_admission` in PC artifacts.
- Make frontier production admission consume an explicit PC deployability class, not only `target_weight > 0`.
- Preserve CC multi-lot target magnitude for rows that are truly PC-deployable.

## Final Judgments

PHASE32_CE_LOW_RANK_NEW_ADMISSION_MATERIAL = YES

PHASE32_CE_CAUTION_REDUCED_ADMISSION_MATERIAL = YES

PHASE32_CE_CANDIDATE_VS_DEPLOYABILITY_SEPARATION = PARTIAL

PHASE32_CE_RANK_OPPORTUNITY_SEMANTIC_PRESERVED = PARTIAL

PHASE32_CE_ENTRY_QUALITY_PC_SEMANTIC_CONSISTENCY = NO

PHASE32_CE_PRIMARY_DIAGNOSIS = MIXED: candidate rows are coarsely separated from deployment, but reduced/caution NEW admission is broad, low-rank negative-opportunity rows receive positive PC targets, and Adaptive Buy Quality target reductions are often overwritten before final deployable target magnitude.

PHASE32_CE_PRODUCTION_REPAIR_JUSTIFIED = YES

PHASE32_CE_NEXT_STEP = Narrow design/repair for explicit NEW production deployability and target-weight resolution preservation: keep candidates visible, preserve CC multi-lot magnitude, but require final PC deployable NEW target to retain Buy Quality/rank/opportunity semantics rather than relying on positive target_weight alone.
