# Phase32-CG — Pre-Phase32 vs Current Final Investment Decision Semantic Delta Audit

## Executive Summary

This was a READ-ONLY audit comparing final investment decision semantics between the pre-common-frontier Production-shaped baseline and the current Post-CC / Pre-CF-implementation Production path.

No production code, config, threshold, model, runtime state, fresh run, resume, replay, or backtest was changed or executed.

Baseline selected:

```text
runtime-test-historical-extended-smoke-20260828T000823285458Z
```

Current run:

```text
runtime-test-historical-extended-smoke-20260829T021541366158Z
```

Common audited coverage with execution artifacts in both runs:

```text
2022-10-03 through 2022-11-14, 29 business days
```

Primary conclusion: final BUY decision semantics drifted, but not as a simple old-good/current-bad rollback case. The current path preserves important Phase32 gains: explicit BF switched target authority, NEW/REENTRY multi-lot magnitude preservation, ADD PASS-only/BF-only semantics, and common capital competition. However, the Adaptive Buy Quality target reduction bug exists in both old and current paths. CE/CF therefore remain justified: the missing repair is not restoring the old path wholesale, but preserving the Buy Quality-adjusted target ceiling through the current CC/BF architecture.

## Baseline Selection

The selected old baseline is the accepted local Production-shaped comparison run used by Phase32-BU as the old Production comparison:

```text
runtime-test-historical-extended-smoke-20260828T000823285458Z
```

Selection reason:

- It starts at the same historical date, `2022-10-03`.
- It has completed artifacts covering the full current comparison window.
- It predates the active BG/BF common marginal frontier consumer switch that became the Production target source.
- It was already used in Phase32-BU as the old Production comparison for NEW allocation drift.
- The selection is based on authority/path comparability, not return, PnL, or hindsight outcome.

The baseline still contains shadow/common-frontier observability artifacts in some places, but its Production final target/PS path is the pre-switch Production-shaped behavior for the comparison requested here.

## Required Source Context

Reviewed:

- `phase32_cf_adaptive_buy_quality_target_authority_preservation_design.md`
- `phase32_ce_new_production_admission_quality_rank_semantic_audit.md`
- `phase32_cd_initial_target_magnitude_early_reduction_consistency_audit.md`
- `phase32_ca_new_conviction_target_weight_semantic_preservation_audit.md`
- `phase32_bu_post_bt_new_allocation_semantic_drift_audit.md`
- `adaptive_buy_quality_authority.md`
- `portfolio_construction_and_position_sizing_contract.md`
- `high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`

Architecture baseline:

- Candidate eligibility is not BUY authorization.
- PC owns target membership and target weight.
- Buy Quality owns allocation quality/action and the allocation adjustment.
- PS converts PC target authority to quantity; PS must not reinterpret rank/opportunity.
- Cash is a valid allocation outcome.
- Phase32 common frontier should compare marginal capital, but should not erase upstream PC/Buy Quality target authority.

## Aggregate Decision Metrics

| Metric | Old baseline | Current |
|---|---:|---:|
| Common coverage | 29BD | 29BD |
| PC BUY_NEW rows | 1,159 | 1,164 |
| Positive PC target rows | 133 | 125 |
| PS-positive rows | 337 | 282 |
| BUY fills | 71 | 65 |
| Unique BUY symbols | 61 | 60 |
| Actual BUY notional | 4,159,840 | 3,982,770 |
| Average cash | 277,372 | 315,638 |
| Average exposure | 73.60% | 68.67% |
| Ending cash on 2022-11-14 | 214,440 | 229,710 |
| Ending exposure on 2022-11-14 | 79.75% | 76.78% |

The current run is not simply broader than old over the 29BD window. It buys fewer total rows and less notional, while still materially changing which rows and magnitudes are selected.

## Buy Decision Classification

Classification over common PC/fill symbol-days:

| Class | Count |
|---|---:|
| BOTH_BUY | 32 |
| OLD_ONLY_BUY | 39 |
| CURRENT_ONLY_BUY | 33 |
| BOTH_NO_BUY | 1,413 |

BOTH_BUY magnitude classification:

| Magnitude class | Count |
|---|---:|
| SAME_MAGNITUDE | 26 |
| OLD_LARGER | 1 |
| CURRENT_LARGER | 5 |

This is material final decision drift: 72 symbol-days are one-sided buys, and 6 shared buy symbol-days changed quantity.

## Rank / Quality / Admission Distribution

Positive PC target rank distribution:

| Rank bucket | Old | Current |
|---|---:|---:|
| 1-10 | 32 | 40 |
| 11-20 | 29 | 28 |
| 21-30 | 39 | 24 |
| 31+ | 33 | 33 |

Buy Quality action distribution among positive PC targets:

| Action | Old | Current |
|---|---:|---:|
| REDUCED_ALLOCATION_ONLY | 132 | 124 |
| FULL_ALLOCATION_ELIGIBLE | 1 | 1 |

Entry admission among positive PC targets:

| Entry action / state | Old | Current |
|---|---:|---:|
| BUY_NEW_REDUCED_ONLY | 118 | 110 |
| BUY_NEW_ALLOWED | 15 | 15 |
| CONTINUATION_WITH_CAUTION | 118 | 110 |
| HEALTHY_CONTINUATION_ENTRY | 15 | 15 |

Opportunity sign among positive PC targets:

| Opportunity sign | Old | Current |
|---|---:|---:|
| Negative | 125 | 110 |
| Non-negative | 8 | 15 |

Interpretation:

- Low-rank / negative-opportunity / caution deployability is not solely a Phase32 common-frontier artifact; old Production already admitted many reduced/caution rows.
- Current shifted distribution somewhat toward rank 1-10 and non-negative opportunity, but still materially deploys `REDUCED_ALLOCATION_ONLY`.
- Candidate-vs-deployability separation remains only partial in both eras.

## Target Weight / Quantity Distribution

Positive PC target weight distribution:

| Metric | Old | Current |
|---|---:|---:|
| Min target weight | 1.3558% | 1.5560% |
| Average target weight | 6.7810% | 8.3119% |
| Max target weight | 22.1267% | 23.7854% |

PS positive quantity distribution:

| Quantity bucket | Old | Current |
|---|---:|---:|
| 100 | 241 | 163 |
| 101-300 | 46 | 38 |
| 301-1000 | 40 | 51 |
| 1000+ | 10 | 30 |

Interpretation:

- Current CC/BF path materially reduced 100-share dominance and restored more multi-lot target magnitude.
- That is a KEEP semantic from Phase32-CC.
- The remaining defect is that the restored magnitude is bounded by the pre-quality/base PC target, not consistently by the Buy Quality-adjusted target.

## Buy Quality Reduction Preservation

Among positive PC target rows:

| Metric | Old | Current |
|---|---:|---:|
| Reduced Buy Quality rows | 132 | 124 |
| Reduced rows re-expanded above post-quality target | 109 | 96 |
| Re-expansion rate | 82.6% | 77.4% |

Answer to the most important target-resolution questions:

1. Buy Quality reduction re-expansion existed in OLD: YES.
2. OLD did not reliably preserve `REDUCED_ALLOCATION_ONLY` through final quantity: NO.
3. CURRENT also does not reliably preserve it: NO.
4. Therefore CF is not a rollback-to-old repair; CF is a semantic-preservation repair needed in both paths, now targeted at the current CC/BF authority.

## Daily Cash / Exposure Snapshot

| Date | Old BUY | Old BUY notional | Old cash | Old exposure | Old positions | Current BUY | Current BUY notional | Current cash | Current exposure | Current positions |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022-10-03 | 7 | 504,470 | 495,530 | 51.1% | 7 | 7 | 488,570 | 511,430 | 49.5% | 7 |
| 2022-10-04 | 3 | 329,150 | 296,700 | 71.7% | 7 | 5 | 328,100 | 484,980 | 52.0% | 8 |
| 2022-10-05 | 2 | 163,880 | 222,620 | 79.2% | 7 | 3 | 96,530 | 486,350 | 51.7% | 9 |
| 2022-10-06 | 4 | 141,780 | 80,840 | 92.5% | 10 | 5 | 239,840 | 438,670 | 56.4% | 10 |
| 2022-10-07 | 1 | 35,100 | 79,440 | 92.5% | 10 | 3 | 344,880 | 179,790 | 82.1% | 11 |
| 2022-10-11 | 0 | 0 | 338,340 | 67.6% | 8 | 0 | 0 | 423,740 | 57.7% | 9 |
| 2022-10-12 | 2 | 30,560 | 335,080 | 67.5% | 7 | 1 | 47,760 | 398,180 | 60.0% | 8 |
| 2022-10-13 | 2 | 49,770 | 719,260 | 30.2% | 5 | 2 | 61,210 | 549,170 | 44.5% | 7 |
| 2022-10-14 | 5 | 275,200 | 444,060 | 57.3% | 10 | 2 | 134,700 | 442,970 | 55.4% | 7 |
| 2022-11-14 | 1 | 105,500 | 214,440 | 79.8% | 11 | 1 | 105,500 | 229,710 | 76.8% | 9 |

Cash semantics drift is PARTIAL. Current keeps more cash on average and is not blindly deploying more, but the reason differs: budget-bounded BF target competition and post-BZ/BV filtering, not the old PC/PS final target path.

## Day-0 End-to-End Trace

On 2022-10-03, both runs produced 7 BUY fills.

| Symbol | Class | Old qty | Current qty |
|---|---|---:|---:|
| 33700 | BOTH_BUY | 100 | 100 |
| 37820 | BOTH_BUY | 400 | 400 |
| 58200 | CURRENT_ONLY_BUY | 0 | 100 |
| 83060 | BOTH_BUY | 100 | 100 |
| 89180 | BOTH_BUY | 3,700 | 3,700 |
| 92420 | BOTH_BUY | 100 | 100 |
| 93600 | OLD_ONLY_BUY | 100 | 0 |
| 94340 | BOTH_BUY | 200 | 200 |

Day-0 conclusion:

- Candidate / Buy Quality / PC target-resolution evidence was materially stable for shared rows.
- Current did not reproduce the earlier Post-BT 11-fill breadth after BV/BZ/CC; it returned to 7 day-0 fills.
- Final symbol choice still drifted: `58200` replaced `93600`.
- Current Day-0 notional was slightly lower: 488,570 vs 504,470.

## Required Symbol Target Resolution Trace

| Symbol / date | Run | Rank | Opportunity | BQ action | Base target | BQ adjusted | Final PC target | Lot qty | Actual BUY |
|---|---|---:|---:|---|---:|---:|---:|---:|---:|
| 89180 / 2022-10-03 | Old | 25 | -0.3390 | REDUCED | 3.3636% | 1.9686% | 3.3636% | 3,700 | 3,700 |
| 89180 / 2022-10-03 | Current | 25 | -0.3390 | REDUCED | 3.3636% | 1.9686% | 3.3636% | 3,700 | 3,700 |
| 76470 / 2022-10-04 | Old | 25 | -0.3678 | REDUCED | 3.8333% | 2.3368% | 3.8333% | 1,300 | 0 |
| 76470 / 2022-10-04 | Current | 25 | -0.3678 | REDUCED | 4.0000% | 2.4384% | 4.0000% | 1,400 | 1,400 |
| 17570 / 2022-10-26 | Old | 35 | -0.5746 | REDUCED | 3.8462% | 2.1632% | 0.0000% | 0 | 0 |
| 17570 / 2022-10-26 | Current | 35 | -0.5746 | REDUCED | 3.8462% | 2.1632% | 3.8462% | 1,600 | 1,600 |
| 37770 / 2022-10-31 | Old | 43 | -0.8494 | REDUCED | 2.9412% | 1.4691% | 2.9412% | 1,100 | 0 |
| 37770 / 2022-10-31 | Current | 43 | -0.8494 | REDUCED | 3.2258% | 1.6113% | 3.2258% | 1,200 | 1,200 |
| 94320 / 2022-10-05 | Old | 1 | 0.3656 | REDUCED | 3.4074% | 2.7371% | 3.4074% | 200 | 200 |
| 94320 / 2022-10-05 | Current | 1 | 0.3656 | REDUCED | 3.6800% | 2.9561% | 3.6800% | 200 | 200 |
| 94340 / 2022-10-03 | Old | 3 | 0.2403 | REDUCED* | 3.3636% | 3.3636% | 3.3636% | 200 | 200 |
| 94340 / 2022-10-03 | Current | 3 | 0.2403 | REDUCED* | 3.3636% | 3.3636% | 3.3636% | 200 | 200 |

`94340` has `REDUCED_ALLOCATION_ONLY` label on 2022-10-03, but the quality adjustment is 1.0, so there is no actual target reduction to preserve on that day.

Trace conclusions:

- For 89180, both OLD and CURRENT show the same semantic defect: Buy Quality says 1.9686%, final deployable target returns to 3.3636%.
- For 76470, 17570, and 37770, current actual BUY differs from old, but the quality-reduction re-expansion pattern is visible in the target resolution itself.
- For 94320, the row is higher rank/stronger opportunity, but reduced allocation is still not preserved as the final target ceiling.
- For 94340, no quality reduction existed at Day-0 because the adjustment was 1.0.

## Primary Divergence Boundary

The primary divergence boundary is:

```text
PC target-weight resolution / lot-aware final reallocation
-> CC/BF target magnitude authority
-> PS switched target consumption
```

More specifically:

- OLD already allowed later PC stages to re-expand above Adaptive Buy Quality post-quality targets.
- CURRENT keeps that defect and then feeds the restored/base magnitude into CC multi-lot/BF authority.
- CC correctly preserves target magnitude, but the upstream magnitude being preserved is not always the Buy Quality-authorized magnitude.
- BF/BG switched authority changes final symbol-day selection relative to old by budget-bounded common competition.

Candidate AI itself is not the primary divergence point: ranks/opportunity/Buy Quality evidence for traced rows were materially comparable across runs.

## Semantic Classification

| Old semantic | Status | Current handling | Judgment |
|---|---|---|---|
| Candidate row remains observable even if not bought | PRESERVED | KEEP | Candidates remain visible. |
| PC owns final target membership/weight | PARTIALLY_MIGRATED | REPAIR | BF is now switched target source; PC admission/quality ceilings must be explicit inputs. |
| Adaptive Buy Quality reduces allocation | PARTIALLY_MIGRATED | REPAIR | Reduction is recorded but not reliably preserved to final target in either path. |
| Legacy zero target blocks NEW deployability | PARTIALLY_MIGRATED | KEEP / REPAIR | BV restored this boundary, but deployability class should be explicit. |
| Legacy PC/PS final symbol selection | INTENTIONALLY_REPLACED | MERGE_WITH_OLD | Common frontier replaces old ordering; keep only semantic authorities, not old symbols as labels. |
| One-lot / discrete PS quantity conversion | PRESERVED | KEEP | PS arithmetic remains authority for quantity conversion. |
| NEW/REENTRY target magnitude beyond one lot | ACCIDENTALLY_LOST before CC, restored by CC | KEEP | CC fixed one-lot compression and should remain. |
| ADD PASS-only/BF-only authority | New Phase32 semantic | KEEP | BZ repair should remain. |
| Common NEW/REENTRY/ADD/Cash capital competition | New Phase32 semantic | KEEP | Keep, but feed quality-bounded deployable targets. |
| Cash as valid residual / competitor | PARTIALLY_MIGRATED | KEEP / REPAIR | Current keeps more average cash; semantics should remain explicit and authority-owned. |

## Answers To Required Questions

1. Buy Quality reduction re-expansion was present in OLD: YES, 109/132 reduced positive-target rows re-expanded above the post-quality target.
2. OLD did not reliably preserve reduced allocation to final quantity: NO.
3. OLD and CURRENT candidate-to-deployable boundary differ because CURRENT uses BF switched target authority and common budget competition; OLD uses legacy PC/PS final target flow.
4. OLD's exact final symbol selection authority is intentionally replaced by common frontier, but old PC/Buy Quality target ceilings were not fully preserved as explicit hard bounds.
5. OLD initial sizing authority was legacy PC target resolution plus lot-aware PS conversion. CURRENT is PC target magnitude -> CC multi-lot -> BF aggregate -> PS.
6. Cash semantics drifted partially: CURRENT keeps more cash on average and lower exposure, but via BF budget competition rather than old target allocation mechanics.
7. Accidentally lost / not yet migrated semantics: Buy Quality-adjusted target magnitude as a hard final deployable ceiling.
8. KEEP semantics from Phase32: CC multi-lot target magnitude restoration, ADD PASS-only/BF-only authority, effective cap propagation, budget-bounded common frontier, explicit no legacy fallback.

## Defect / No-Defect Judgment

Defect confirmed: Adaptive Buy Quality target reduction is not preserved as a hard final deployable target ceiling in either OLD or CURRENT.

Phase32 migration did not create the original quality re-expansion defect, but it made the defect more important because the current architecture is better at preserving and consuming target magnitude. When the wrong magnitude survives, CC/BF can faithfully propagate the wrong upper bound.

The correct repair is the Phase32-CF design:

```text
candidate_eligible != production_deployable_new
final NEW/REENTRY deployable target <= Buy Quality-adjusted target
CC lot expansion <= quality-authorized target quantity
```

## Final Judgments

PHASE32_CG_OLD_BASELINE_RUN = runtime-test-historical-extended-smoke-20260828T000823285458Z

PHASE32_CG_COMMON_COVERAGE = 2022-10-03 through 2022-11-14, 29 business days

PHASE32_CG_FINAL_BUY_DECISION_DRIFT = YES

PHASE32_CG_TARGET_MAGNITUDE_DRIFT = PARTIAL

PHASE32_CG_BUY_QUALITY_REDUCTION_PRESERVED_OLD = NO

PHASE32_CG_BUY_QUALITY_REDUCTION_PRESERVED_CURRENT = NO

PHASE32_CG_CANDIDATE_DEPLOYABILITY_BOUNDARY_DRIFT = PARTIAL

PHASE32_CG_CASH_ALLOCATION_SEMANTIC_DRIFT = PARTIAL

PHASE32_CG_PRIMARY_DIVERGENCE_BOUNDARY = PC target-weight resolution / lot-aware final reallocation into CC/BF target magnitude authority and PS switched target consumption

PHASE32_CG_OLD_SEMANTICS_ACCIDENTALLY_LOST = Buy Quality-adjusted target magnitude as an enforceable final deployable ceiling was not preserved; legacy PC final symbol selection was intentionally replaced and should not be restored as a hindsight label

PHASE32_CG_CURRENT_SEMANTICS_TO_KEEP = CC NEW/REENTRY multi-lot target magnitude preservation; ADD PASS-only/BF-only authority; budget-bounded common NEW/REENTRY/ADD/Cash competition; effective Strategy/Safety cap propagation; explicit no legacy fallback

PHASE32_CG_CURRENT_SEMANTICS_TO_REPAIR = Make Buy Quality-adjusted NEW/REENTRY target magnitude the hard upper bound before incremental budget reconciliation, lot-aware final reallocation, CC lot expansion, BF aggregation, and PS consumption

PHASE32_CG_CF_IMPLEMENTATION_STILL_JUSTIFIED = YES

PHASE32_CG_PRODUCTION_REPAIR_JUSTIFIED = YES

PHASE32_CG_NEXT_STEP = Implement Phase32-CF narrowly: materialize candidate-vs-deployability separation and enforce the Buy Quality-authorized target ceiling through PC target resolution, CC multi-lot expansion, BF validation, and PS-bound target consumption.
