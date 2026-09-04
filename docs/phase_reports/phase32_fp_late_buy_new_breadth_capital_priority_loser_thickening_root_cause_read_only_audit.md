# Phase32-FP Late BUY_NEW Breadth / Capital Priority / Loser Thickening Root-Cause READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260903T213011268067Z`
- Evidence root: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260903T213011268067Z`
- Freeze: `2023-08-03`, matching Phase32-FO.
- Periods:
  - EARLY: `2022-10-03` through `2023-02-28` / 100BD
  - MIDDLE: `2023-03-01` through `2023-05-31` / 62BD
  - LATE: `2023-06-01` through `2023-08-03` / 45BD
- Required references read: Phase32-FO, FC, FG/FH, FJ, FK, FL, FM/FN, Strategy / PC / MCV / Cash / opportunity-rank SoT and source references.

READ-ONLY confirmation: no Production, SHADOW, config, schema, runtime state, Pending, or Ledger mutation was performed. No fresh-run, resume, recover, or replay was executed.

Historical loser outcome is used only to characterize where losses landed. It is not used to tune or select Production features, thresholds, weights, ranks, or parameters.

## Selected Rank Semantics

`SELECTED_RANK_SEMANTIC_CONFIRMED`: YES.

The rank used in FO/FP is the canonical BUY opportunity rank:

```text
Runtime BUY AI opportunity ranking
-> opportunity_buy_rank / buy_rank
-> BQ opportunity_buy_rank
-> PC input_opportunity_rank
-> Runtime/fill joined by symbol/date
```

It is not array order, candidate model rank, PC final sort order, or final selected rank. Architecture confirms that `opportunity_buy_rank` is the canonical opportunity rank; PC preserves it as `input_opportunity_rank` and emits `opportunity_rank_preserved`. BQ explicitly includes `rank_not_used_as_fixed_n_gate`, so rank is supporting evidence, not a fixed top-N hard gate.

`CANDIDATE_RANK_INFORMATION_LOST_DOWNSTREAM`: PARTIAL. The numeric rank is preserved as lineage/metadata in PC, but final marginal capital priority is compressed into coarser MCV classes such as `ELIGIBLE_STRONG` / `ELIGIBLE_COMPARABLE` and `STRONG` / `COMPARABLE_MARGINAL`.

## BUY_NEW Rank Distribution

| Period | BUY_NEW fills | BUY_NEW notional | Median | P25 | P75 | Top5 | 6-10 | 11-20 | 21-30 | >30 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| EARLY | 191 | 10,272,390 | 15 | 10 | 23.5 | 18 / 617,900 | 36 / 1,932,620 | 69 / 3,997,580 | 33 / 1,484,440 | 35 / 2,239,850 |
| MIDDLE | 111 | 9,465,160 | 16 | 11 | 23 | 10 / 1,777,900 | 15 / 824,530 | 50 / 4,426,120 | 29 / 1,886,980 | 7 / 549,630 |
| LATE | 77 | 5,816,380 | 22 | 14 | 29 | 7 / 1,235,100 | 9 / 513,000 | 21 / 1,529,550 | 24 / 1,647,710 | 16 / 891,020 |

`EARLY_MEDIAN_BUY_NEW_RANK`: 15.

`MIDDLE_MEDIAN_BUY_NEW_RANK`: 16.

`LATE_MEDIAN_BUY_NEW_RANK`: 22.

`LATE_RANK_20PLUS_CAPITAL_SHARE`: 43.6% of BUY_NEW notional.

Judgment: Late materially buys deeper-ranked BUY_NEW candidates than MIDDLE, and the shift is capital-material.

## Top Candidate Availability When Deep Rank Was Bought

Late rank >20 BUY_NEW fills: 40.

For those 40 fills, each fill had higher-ranked PC rows above it. Across above-rank unselected rows observed in those decision contexts:

| Reason class | Count |
|---|---:|
| PC/MCV/capital competition zero or other explained PC non-selection | 444 |
| Already held / duplicate current position / no ADD increment | 419 |
| Entry/BQ block or wait | 108 |

Representative actual-path cases:

| Date | Bought | Bought rank | Higher-ranked row | Higher rank | Reason |
|---|---|---:|---|---:|---|
| 2023-06-05 | 31920 | 23 | 94320 | 1 | already held, ADD reduced-only, no increment |
| 2023-06-05 | 31920 | 23 | 30410 | 2 | BUY_NEW row, PC/MCV competition zero |
| 2023-06-05 | 31920 | 23 | 59550 | 4 | already held, ADD reduced-only, no increment |
| 2023-06-05 | 31920 | 23 | 76470 | 7 | already held, `NO_ADD` / entry block |
| 2023-07-25 | 72770 | 39 | 94320 | 1 | already held, ADD reduced-only, no increment |
| 2023-07-25 | 72770 | 39 | 76470 | 2 | already held, ADD reduced-only, no increment |
| 2023-07-25 | 72770 | 39 | 59520 | 10 | BUY_NEW selected but trimmed |

`TOP_CANDIDATES_AVAILABLE_WHEN_DEEP_RANK_BOUGHT`: YES, but not necessarily executable/fundable as independent capital competitors.

`TOP_CANDIDATES_ALREADY_HELD_OR_SATURATED`: YES. A large share of better-ranked rows were current holdings with no accepted ADD increment, or candidates that lost PC/MCV/capital competition.

## BUY_NEW vs ADD Competition

Late BUY_NEW days with ADD-like current-position candidates: 35 of 35 BUY_NEW days observed in the extraction. Typical day-level shape:

| Date | BUY_NEW fills | ADD-like current candidates | Positive ADD increments | Cash | Exposure |
|---|---:|---:|---:|---:|---:|
| 2023-06-05 | 7 | 9 | 0 | 301,060 | 82.4% |
| 2023-06-07 | 3 | 15 | 0 | 320,200 | 81.1% |
| 2023-06-12 | 5 | 11 | 0 | 291,800 | 83.2% |
| 2023-06-13 | 4 | 16 | 1 | 198,350 | 88.5% |
| 2023-06-20 | 1 | 17 | 1 | 210,500 | 88.4% |
| 2023-07-10 | 4 | 14 | 0 | 104,600 | 93.7% |
| 2023-07-25 | 2 | 16 | 0 | 51,520 | 96.9% |

`ADD_OPPORTUNITIES_EXIST_WHEN_BUY_NEW_SELECTED`: YES. Current holdings with ADD-like Entry/BQ evidence existed on most Late BUY_NEW days, but very few became positive accepted ADD increments.

`WINNER_INCUMBENT_LOSES_TO_WEAKER_BUY_NEW`: YES_BY_RANK / PARTIAL_BY_MCV. Higher-ranked incumbents frequently did not receive ADD capital while lower-ranked BUY_NEW rows did. However, MCV sometimes reclassified lower-ranked BUY_NEW as `ELIGIBLE_STRONG` when entry/continuation evidence was healthy, so this is a capital-priority semantic issue rather than a simple rank-order violation.

## Five-ADD Cap Materiality

Phase32-FK remains applicable:

- `prior_add_history_limits_incremental_add` is campaign-local, not cross-campaign security-level history.
- It is emitted by Strategy PM / PC/PS paths when same-open-campaign ADD history reaches the cap.
- FK observed 176 Strategy ADD-worthiness `NO_ADD` rows, including `76470` and `94320`, despite positive current CQ/risk/return evidence.

In this FO/FP freeze, cap reason occurrences are present in PM/PS evidence:

| Period | Reason occurrences | Days | Cap days with BUY_NEW |
|---|---:|---:|---:|
| EARLY | 114 | 57 | 51 |
| MIDDLE | 142 | 62 | 53 |
| LATE | 180 | 45 | 35 |

`FIVE_ADD_CAP_DISPLACES_CAPITAL_TO_BUY_NEW`: YES_SECONDARY_NOT_SOLE_CAUSE. It contributes to incumbents not competing for incremental capital, especially Late, but it is not unique to Late and the extracted evidence does not prove it alone explains rank-depth or loser thickening.

## BUY Quality / Entry Quality

Actual BUY_NEW fills:

| Period | BQ bands | BQ actions | Entry states | MCV classes |
|---|---|---|---|---|
| EARLY | HIGH 55, MEDIUM 105, LOW 31 | REDUCED 190, FULL 1 | CAUTION 146, HEALTHY 45 | COMPARABLE 146, STRONG 45 |
| MIDDLE | HIGH 30, MEDIUM 78, LOW 3 | REDUCED 111 | CAUTION 100, HEALTHY 11 | COMPARABLE 100, STRONG 11 |
| LATE | HIGH 21, MEDIUM 45, LOW 11 | REDUCED 76, FULL 1 | CAUTION 59, HEALTHY 18 | COMPARABLE 59, STRONG 18 |

`UPSTREAM_BUY_QUALITY_WEAKENS`: MIXED. Late rank worsens and LOW-band BUY_NEW share increases versus MIDDLE, but HIGH and MCV STRONG representation does not collapse.

`BQ_QUALITY_WEAKENS`: MIXED. The Late LOW count/share is worse than MIDDLE, but Late has more MCV STRONG and more HEALTHY entry than MIDDLE.

`ENTRY_QUALITY_WEAKENS`: NO_VS_MIDDLE / MIXED_VS_EARLY. Late has 18 HEALTHY entries out of 77 versus 11 out of 111 in MIDDLE, so the entry-state distribution does not explain the whole decay.

## PC / MCV Priority Compression

Actual evidence shows PC preserves numeric opportunity rank but final capital priority is not numeric-rank-first:

- `rank_not_used_as_fixed_n_gate` appears in BQ.
- PC members preserve `input_opportunity_rank` and `input_score`.
- MCV maps candidates into coarse classes such as `ELIGIBLE_STRONG` and `ELIGIBLE_COMPARABLE`.
- Example `2023-07-25`: `72770` had opportunity rank 39, BQ LOW, but Entry `HEALTHY_CONTINUATION_ENTRY`, MCV `ELIGIBLE_STRONG`, priority index 1, and received positive BUY_NEW allocation.
- Same day, `94320` rank 1 and `76470` rank 2 were already-held ADD-reduced-only rows with zero accepted increment.

`PC_COMPRESSES_QUALITY_DIFFERENCES`: YES.

`MCV_COMPRESSES_PRIORITY_DIFFERENCES`: YES.

`CAPITAL_PRIORITY_AUTHORITY_IDENTIFIED`: PC owns final allocation; MCV owns marginal opportunity quality/priority evidence; BQ/Entry/rank are upstream inputs; PS and Runtime must not reinterpret rank.

`CAPITAL_PRIORITY_SEMANTIC_GAP_FOUND`: YES. Current Production has lineage-valid capital priority, but not a unified fine-grained "next capital unit" comparison across BUY_NEW, ADD, Cash, and incumbent saturation.

## Cash Neutrality

`CASH_COMPETITOR_TOO_WEAK`: PARTIAL_YES_AS_DESIGN_SURFACE.

FO extraction found no filled BUY_NEW rows where Cash was the recorded blocking winner, and `cash_pref_blocked_fill` was 0. However, Phase32-FG/FH and the PC/Cash SoT show that `CASH_PREFERRED` is evidence, not a blanket hard-zero allocation. Therefore Cash often remains weaker than positive reduced participation once PC accepts a security row.

This is not a correctness defect. It is a design surface for future capital-priority work.

## Starter Position / Position Count Pressure

| Period | Avg BUY_NEW notional | Median BUY_NEW notional | Avg initial weight | Median initial weight | 100-share starters | Small <3% starters | BUY_NEW fills |
|---|---:|---:|---:|---:|---:|---:|---:|
| EARLY | 53,782 | 34,000 | 4.66% | 3.05% | 127 | 93 | 191 |
| MIDDLE | 85,272 | 57,000 | 5.69% | 3.83% | 72 | 34 | 111 |
| LATE | 75,537 | 52,320 | 4.43% | 3.07% | 55 | 36 | 77 |

`STARTER_POSITION_BREADTH_INCREASES`: YES_RELATIVE_TO_MIDDLE. Late initial weights are smaller than MIDDLE and the average position count rises to 14.49 in FO.

`POSITION_COUNT_PRESSURE_EXPLAINED`: MIXED. The main drivers are small starter sizing, weak/rare ADD materialization, broad positive BUY_NEW participation, and long-held current positions. This is not merely "many valid top opportunities"; it is breadth plus limited incumbent scaling.

## Loser Cohort by Entry Rank and Quality

Loser loss by entry-rank cohort:

| Period | Cohort | Count | Total loss | Median loss | Large losses >50k |
|---|---|---:|---:|---:|---:|
| EARLY | Top10 | 18 | -55,730 | -1,600 | 0 |
| EARLY | 11-20 | 22 | -50,960 | -1,570 | 0 |
| EARLY | 21-30 | 8 | -10,540 | -1,050 | 0 |
| EARLY | >30 | 19 | -18,370 | -820 | 0 |
| MIDDLE | Top10 | 7 | -57,320 | -2,450 | 0 |
| MIDDLE | 11-20 | 18 | -86,650 | -2,850 | 0 |
| MIDDLE | 21-30 | 9 | -32,700 | -1,900 | 0 |
| MIDDLE | >30 | 3 | -5,830 | -1,800 | 0 |
| LATE | Top10 | 5 | -120,000 | -4,400 | 1 |
| LATE | 11-20 | 5 | -13,300 | -2,500 | 0 |
| LATE | 21-30 | 5 | -37,000 | -7,000 | 0 |
| LATE | >30 | 3 | -10,000 | -3,500 | 0 |

Late loser quality groups:

| Entry PIT quality group | Count | Total loss | Median loss |
|---|---:|---:|---:|
| HIGH / CAUTION / ELIGIBLE_COMPARABLE | 6 | -121,200 | -4,000 |
| MEDIUM / CAUTION / ELIGIBLE_COMPARABLE | 5 | -18,100 | -1,200 |
| MEDIUM / HEALTHY / ELIGIBLE_STRONG | 3 | -26,100 | -5,300 |
| LOW / HEALTHY / ELIGIBLE_STRONG | 3 | -10,000 | -3,500 |
| HIGH / HEALTHY / ELIGIBLE_STRONG | 1 | -4,900 | -4,900 |

`LOSER_LOSS_CONCENTRATES_IN_DEEP_RANK_BUYS`: NO. Rank 21+ losses are material, but the single >50k Late loser is rank 2, not deep rank.

`LOSER_LOSS_CONCENTRATES_IN_WEAKER_PIT_QUALITY`: NO. Losses include high-quality and top-rank entries. The evidence points to mixed entry-quality and sizing/concentration/loss-containment effects rather than low-quality entries alone.

## Late Large Loss Deep Dive

The one LATE >50k loser through the freeze:

| Field | Value |
|---|---|
| Symbol | `67310` |
| Campaign | `pc-94c8d2d6fe075351-67310-0001` |
| BUY_NEW date | `2023-06-27` |
| Entry rank | 2 |
| BQ | HIGH / `REDUCED_ALLOCATION_ONLY` |
| Entry | `CONTINUATION_WITH_CAUTION` / `BUY_NEW_REDUCED_ONLY` |
| MCV | `ELIGIBLE_COMPARABLE` |
| Initial notional | 300,000 |
| Close date | `2023-06-30` |
| Loss | -100,000 |

Judgment: this loss cannot be attributed to deep-rank BUY_NEW. It was a high-rank, high-BQ, large starter that subsequently lost. Therefore loser thickening is not the same thing as rank-depth expansion, though both share the same broad capital-priority/loss-containment design surface.

## Same-Regime Rank / Quality

Same-regime BUY_NEW rank distribution:

| Regime | Period | Fills | Median rank | Rank20+ capital share | Quality sketch |
|---|---|---:|---:|---:|---|
| BULL | EARLY | 73 | 18 | 43.2% | HIGH 25 / MEDIUM 33 / LOW 15 |
| BULL | MIDDLE | 57 | 16 | 29.6% | HIGH 16 / MEDIUM 40 / LOW 1 |
| BULL | LATE | 40 | 22.5 | 48.0% | HIGH 12 / MEDIUM 22 / LOW 6 |
| RANGE | EARLY | 38 | 16.5 | 28.7% | HIGH 8 / MEDIUM 24 / LOW 6 |
| RANGE | MIDDLE | 21 | 18 | 21.4% | HIGH 5 / MEDIUM 16 / LOW 0 |
| RANGE | LATE | 12 | 22.5 | 62.7% | HIGH 2 / MEDIUM 8 / LOW 2 |
| RECOVERY | EARLY | 22 | 19.5 | 60.3% | HIGH 8 / MEDIUM 8 / LOW 6 |
| RECOVERY | MIDDLE | 25 | 16 | 20.8% | HIGH 5 / MEDIUM 18 / LOW 2 |
| RECOVERY | LATE | 25 | 20 | 30.5% | HIGH 7 / MEDIUM 15 / LOW 3 |

`SAME_REGIME_DEEP_RANK_BUY_INCREASES`: YES, especially BULL and RANGE.

`SAME_REGIME_QUALITY_WEAKENS`: MIXED. BULL/RANGE Late have deeper ranks and more LOW than MIDDLE, but still include HIGH and MCV STRONG rows.

## Source Transition / Run-Age Recheck

Daily source evidence:

- `2022-10-03` through `2023-05-25`: only `1f64f49...`
- `2023-05-26` through `2023-08-03`: mixed `1f64f49...` and `04ded4...`

Late subperiod split:

| Subperiod | BUY_NEW fills | Median rank | Rank20+ notional share | Bands | MCV |
|---|---:|---:|---:|---|---|
| 2023-06 | 50 | 20 | 34.0% | HIGH 15 / MEDIUM 32 / LOW 3 | STRONG 6 / COMPARABLE 44 |
| 2023-07-01 to 2023-08-03 | 27 | 25 | 60.9% | HIGH 6 / MEDIUM 13 / LOW 8 | STRONG 12 / COMPARABLE 15 |

`SOURCE_TRANSITION_CAUSAL`: UNCONFIRMED / NOT_PROVEN. Rank-depth worsens after June, and this occurs inside the mixed-source-evidence period, but no authority mismatch or correctness defect was found. Calendar/run-path evolution, holdings, and capital-priority compression are sufficient competing explanations.

`RUN_AGE_SOFT_BIAS_FOUND`: YES_CAMPAIGN_LOCAL_ADD_CAP_ONLY. No REENTRY-style stale long-lived history bias was newly found. The known same-open-campaign ADD cap remains a soft bias against incumbent scaling.

## Root-Cause Decomposition

Late BUY_NEW breadth / rank-depth:

| Cause | Judgment | Evidence |
|---|---|---|
| A. Upstream entry quality weakness | SECONDARY | Late median rank worsens and LOW share rises, but Entry/MCV STRONG do not collapse. |
| B. Top candidates already saturated | PRIMARY | Higher-ranked rows often already held and no positive ADD increment. |
| C. ADD headroom unavailable | PRIMARY | ADD-like candidates existed on Late BUY_NEW days, but positive ADD increments were rare. |
| D. Five-ADD cap displaces capital | SECONDARY | Cap reason appears repeatedly and FK proves material same-campaign cap, but not sole Late cause. |
| E. PC priority compression | PRIMARY | Numeric rank is preserved but coarse target/eligibility semantics determine capital. |
| F. MCV priority compression | PRIMARY | Rank 39 can become MCV `ELIGIBLE_STRONG` when Entry evidence is healthy. |
| G. Cash too weak | SECONDARY | Cash evidence exists but is not a blanket hard-zero competitor. |
| H. Starter breadth effect | SECONDARY | Late starter weights are smaller than MIDDLE and position count rises. |
| I. Position count policy | SECONDARY | No routine hard cap forces concentration; breadth is allowed. |
| J. Normal opportunity diversification | SECONDARY | Some breadth is valid diversification. |
| K. Source transition | NOT_SUPPORTED_AS_CAUSAL | Context present, defect not proven. |
| L. Market environment | SECONDARY | Same-regime Late rank/performance weaker; not sole explanation. |
| M. Mixed | PRIMARY OVERALL | Actual path is multi-factor. |

`PRIMARY_BREADTH_CAUSE`: top-ranked opportunity saturation/current-position non-incrementality plus PC/MCV coarse capital-priority compression, with small-starter BUY_NEW breadth as the realized allocation shape.

Loser thickening:

| Cause | Judgment |
|---|---|
| Entry quality | SECONDARY |
| Sizing | PRIMARY |
| Concentration | PRIMARY |
| Sell timing / profit protection | SECONDARY |
| Same-day gap | PRIMARY_FOR_67310_CASE |
| Market environment | SECONDARY |
| Breadth | SECONDARY |
| Mixed | PRIMARY OVERALL |

`PRIMARY_LOSER_THICKENING_CAUSE`: mixed sizing/concentration and event-gap exposure, not deep-rank BUY_NEW alone.

## Correctness / Design Judgment

- `CORRECTNESS_DEFECT_FOUND`: NO
- `CAPITAL_PRIORITY_SEMANTIC_GAP_FOUND`: YES
- `BUY_NEW_BREADTH_DESIGN_GAP_FOUND`: YES
- `LOSER_CONTAINMENT_DESIGN_GAP_FOUND`: YES
- `DESIGN_REFINEMENT_JUSTIFIED`: YES
- `PRODUCTION_REPAIR_JUSTIFIED`: NO

Interpretation: this is not a broken contract or stale authority defect. It is a Production design characteristic: fine-grained rank/quality and Cash/ADD/incumbent opportunity evidence are not yet unified into one next-capital-unit priority surface, so capital can spread laterally into BUY_NEW while strong incumbents remain non-incremental.

## Required Answer Summary

- `SELECTED_RANK_SEMANTIC_CONFIRMED`: `YES`
- `EARLY_MEDIAN_BUY_NEW_RANK`: `15`
- `MIDDLE_MEDIAN_BUY_NEW_RANK`: `16`
- `LATE_MEDIAN_BUY_NEW_RANK`: `22`
- `LATE_RANK_20PLUS_CAPITAL_SHARE`: `43.6%`
- `TOP_CANDIDATES_AVAILABLE_WHEN_DEEP_RANK_BOUGHT`: `YES`
- `TOP_CANDIDATES_ALREADY_HELD_OR_SATURATED`: `YES`
- `ADD_OPPORTUNITIES_EXIST_WHEN_BUY_NEW_SELECTED`: `YES`
- `FIVE_ADD_CAP_DISPLACES_CAPITAL_TO_BUY_NEW`: `YES_SECONDARY_NOT_SOLE_CAUSE`
- `UPSTREAM_BUY_QUALITY_WEAKENS`: `MIXED`
- `BQ_QUALITY_WEAKENS`: `MIXED`
- `ENTRY_QUALITY_WEAKENS`: `NO_VS_MIDDLE / MIXED_VS_EARLY`
- `PC_COMPRESSES_QUALITY_DIFFERENCES`: `YES`
- `MCV_COMPRESSES_PRIORITY_DIFFERENCES`: `YES`
- `CASH_COMPETITOR_TOO_WEAK`: `PARTIAL_YES_AS_DESIGN_SURFACE`
- `STARTER_POSITION_BREADTH_INCREASES`: `YES_RELATIVE_TO_MIDDLE`
- `POSITION_COUNT_PRESSURE_EXPLAINED`: `MIXED_BREADTH_PLUS_LIMITED_INCUMBENT_SCALING`
- `LOSER_LOSS_CONCENTRATES_IN_DEEP_RANK_BUYS`: `NO`
- `LOSER_LOSS_CONCENTRATES_IN_WEAKER_PIT_QUALITY`: `NO`
- `SAME_REGIME_DEEP_RANK_BUY_INCREASES`: `YES`
- `SAME_REGIME_QUALITY_WEAKENS`: `MIXED`
- `CAPITAL_PRIORITY_AUTHORITY_IDENTIFIED`: `PC_FINAL_ALLOCATION_WITH_MCV_PRIORITY_AND_BQ_ENTRY_RANK_INPUTS`
- `CANDIDATE_RANK_INFORMATION_LOST_DOWNSTREAM`: `PARTIAL_PRESERVED_AS_METADATA_COMPRESSED_AS_PRIORITY`
- `WINNER_INCUMBENT_LOSES_TO_WEAKER_BUY_NEW`: `YES_BY_RANK_PARTIAL_BY_MCV`
- `RUN_AGE_SOFT_BIAS_FOUND`: `YES_CAMPAIGN_LOCAL_ADD_CAP_ONLY`
- `SOURCE_TRANSITION_CAUSAL`: `UNCONFIRMED_NOT_PROVEN`
- `PRIMARY_BREADTH_CAUSE`: `TOP_CANDIDATE_SATURATION_PLUS_PC_MCV_PRIORITY_COMPRESSION`
- `PRIMARY_LOSER_THICKENING_CAUSE`: `MIXED_SIZING_CONCENTRATION_EVENT_GAP_NOT_DEEP_RANK_ONLY`
- `CORRECTNESS_DEFECT_FOUND`: `NO`
- `CAPITAL_PRIORITY_SEMANTIC_GAP_FOUND`: `YES`
- `BUY_NEW_BREADTH_DESIGN_GAP_FOUND`: `YES`
- `LOSER_CONTAINMENT_DESIGN_GAP_FOUND`: `YES`
- `DESIGN_REFINEMENT_JUSTIFIED`: `YES`
- `PRODUCTION_REPAIR_JUSTIFIED`: `NO`
- `NEXT_ACTION`: `E. MULTI_FACTOR_DESIGN`
- `LONG_HORIZON_VALIDATION_SAFE_TO_CONTINUE`: `YES`

PRODUCTION_CHANGED: NO
SHADOW_CHANGED: NO
TARGET_RUN_MUTATED: NO
RUNTIME_STATE_MUTATED: NO
FUTURE_OUTCOME_USED_FOR_PRODUCTION_JUDGMENT: NO

Final Judgment: `PHASE32_FP_LATE_BUY_NEW_BREADTH_IS_CAPITAL_PRIORITY_COMPRESSION_AND_INCUMBENT_NON_INCREMENTALITY_LOSER_THICKENING_IS_MIXED_NO_CORRECTNESS_DEFECT_MULTI_FACTOR_DESIGN_JUSTIFIED`
