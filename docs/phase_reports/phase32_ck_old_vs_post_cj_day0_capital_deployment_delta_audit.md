# Phase32-CK — Old vs Post-CJ Day-0 Capital Deployment Delta Audit

## Executive Summary

This was a READ-ONLY audit. No Production code, config, threshold, runtime state, fresh-run, resume, replay, or backtest was changed or executed.

OLD baseline artifacts for `runtime-test-historical-extended-smoke-20260828T000823285458Z` are not present under `reports/runtime_tests/runs`, so OLD Day-0 symbol facts are taken from `phase32_cg_pre_phase32_vs_current_final_investment_decision_semantic_delta_audit.md`. Post-CJ facts are directly read from `runtime-test-historical-extended-smoke-20260829T042305935474Z`.

Day-0 capital deployment delta is explained by the CH/CJ quality ceiling becoming binding:

- OLD bought approximately 7 symbols and carried about 51.1% exposure.
- Post-CJ bought 6 symbols and carried 11.954% BF-authorized security allocation, 11.954% refreshed market value, and 12.042% execution notional.
- The dominant delta is high-price, quality-reduced, below-one-lot candidates that OLD admitted through implicit minimum-lot rescue and Post-CJ correctly blocks with `lot_minimum_exceeds_quality_authorized_target`.
- CJ did repair the unintended 89180 / 76470 zero-collapse: both are now positive BF/PS/fill paths.
- No evidence shows a remaining PS/Runtime/BF capital suppression defect on 2022-10-03. The remaining low exposure is the natural result of enforcing the CH/CJ quality ceiling plus leaving Cash as residual optionality.

## Run Identity

| Role | Run | Artifact status |
| --- | --- | --- |
| OLD baseline | `runtime-test-historical-extended-smoke-20260828T000823285458Z` | Run directory absent locally; CG report used as authority |
| Post-CJ | `runtime-test-historical-extended-smoke-20260829T042305935474Z` | Day-0 artifacts present |

Primary date: `2022-10-03`.

## Aggregate Day-0 Comparison

| Metric | OLD baseline | Post-CJ |
| --- | ---: | ---: |
| BUY fills | 7 | 6 |
| Holdings after Day-0 | 7 | 6 |
| Exposure / security allocation | about 51.1% | 11.954% authority / 12.042% execution notional |
| BUY notional | 504,470 per CG | 120,420 executed / 119,540 authority |
| Cash | 495,530 per CG | 879,580 refreshed cash |
| BF aggregated targets | Not directly recoverable | 6 |
| PS consumed BF authority | Not directly recoverable | YES |
| Legacy fallback | Not directly recoverable | NO in Post-CJ |

Post-CJ authority facts:

- `accepted_target_count = 39` lots
- `aggregated_ps_target_count = 6` symbols
- `security_allocation_weight = 0.11954`
- `authorized_cash_allocation_weight = 0.62046`
- `capital_conservation.status = PASS`
- `marginal_capital_frontier_switch_consumption.status = PASS`
- `legacy_target_gap_fallback_used = false`
- `legacy_zero_fallback_used = false`

## Symbol-by-Symbol Day-0 Trace

OLD columns are CG-derived unless noted. Post-CJ columns are artifact-derived.

| Symbol | OLD qty | OLD approx weight / notional basis | Post-CJ PC target | Quality target | One-lot weight | One-lot / quality | Post-CJ BF/PS qty | Fill qty | First Post-CJ boundary | Reason |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 94340 | 200 | 2.882% | 3.3636% | 3.3636% | 1.441% | 0.43x | 200 | 200 | Fill | Full-equivalent; no effective quality reduction |
| 37820 | 400 | about 2.72% | 2.4103% | 2.4103% | 0.680% | 0.28x | 300 | 300 | Fill | Intended CH reduction 400 -> 300 |
| 93600 | 100 | about 19.11% | 0.0000% | 2.3228% | 19.110% | 8.23x | 0 | 0 | PC lot-aware | `lot_minimum_exceeds_quality_authorized_target` |
| 33700 | 100 | about 3.41% | 0.0000% | 2.1670% | 3.410% | 1.57x | 0 | 0 | PC lot-aware | `lot_minimum_exceeds_quality_authorized_target` |
| 83060 | 100 | about 6.48% | 0.0000% | 2.0607% | 6.480% | 3.14x | 0 | 0 | PC lot-aware | `lot_minimum_exceeds_quality_authorized_target` |
| 92420 | 100 | about 13.75% | 0.0000% | 2.0691% | 13.750% | 6.65x | 0 | 0 | PC lot-aware | `lot_minimum_exceeds_quality_authorized_target` |
| 58200 | 0 in CG OLD; 100 in Pre-CH current | 17.467% one lot | 0.0000% | 2.0120% | 17.467% | 8.68x | 0 | 0 | PC lot-aware | `lot_minimum_exceeds_quality_authorized_target` |
| 89180 | 3700 | about 3.33% | 1.9686% | 1.9686% | 0.090% | 0.05x | 2100 | 2100 | Fill | CJ restored positive quality-bounded path |
| 76470 | 0 fill in CG OLD; 1200 BF/PS target in Pre-CH | 2.70% one-lot-derived basis for 700 Post-CJ shares | 1.9385% | 1.9385% | 0.270% | 0.14x | 700 | 700 | Fill | CJ restored positive quality-bounded path |
| 33500 | 0 in CG OLD | 1.652% Post-CJ BF | 1.8760% | 1.8760% | 0.413% | 0.22x | 400 | 400 | Fill | Post-CJ different final symbol selection |
| 67860 | 0 in CG OLD | 1.600% Post-CJ BF | 1.6238% | 1.6238% | 0.800% | 0.49x | 200 | 200 | Fill | Post-CJ different final symbol selection |

Additional Post-CJ quality-ceiling blocks among Day-0 deployable candidates:

| Symbol | Quality target | One-lot weight | One-lot / quality | Reason |
| --- | ---: | ---: | ---: | --- |
| 41920 | 1.9994% | 7.880% | 3.94x | `lot_minimum_exceeds_quality_authorized_target` |
| 45750 | 1.9314% | 6.760% | 3.50x | `lot_minimum_exceeds_quality_authorized_target` |
| 91070 | 1.8345% | 7.100% | 3.87x | `lot_minimum_exceeds_quality_authorized_target` |
| 70780 | 1.8359% | 11.080% | 6.04x | `lot_minimum_exceeds_quality_authorized_target` |
| 99840 | 1.8070% | 12.453% | 6.89x | `lot_minimum_exceeds_quality_authorized_target` |
| 50250 | 1.7501% | 9.970% | 5.70x | `lot_minimum_exceeds_quality_authorized_target` |
| 82540 | 1.7260% | 3.020% | 1.75x | `lot_minimum_exceeds_quality_authorized_target` |
| 45410 | 1.7051% | 4.360% | 2.56x | `lot_minimum_exceeds_quality_authorized_target` |
| 70690 | 1.6812% | 6.325% | 3.76x | `lot_minimum_exceeds_quality_authorized_target` |
| 96100 | 1.5850% | 1.980% | 1.25x | `lot_minimum_exceeds_quality_authorized_target` |
| 44170 | 1.5373% | 17.200% | 11.19x | `lot_minimum_exceeds_quality_authorized_target` |

## End-to-End Boundary Findings

### Candidate / Buy Quality

The relevant Day-0 symbols remain candidate eligible. Most low/opportunity-negative entries are `REDUCED_ALLOCATION_ONLY`.

Post-CJ examples:

- 33700: quality target 2.1670%, one lot 3.4100%
- 83060: quality target 2.0607%, one lot 6.4800%
- 92420: quality target 2.0691%, one lot 13.7500%
- 58200: quality target 2.0120%, one lot 17.4670%
- 89180: quality target 1.9686%, one lot 0.0900%
- 76470: quality target 1.9385%, one lot 0.2700%

The key distinction is not candidate eligibility. It is whether the quality-authorized target can buy at least one trading lot without exceeding the Buy Quality ceiling.

### PC Lot-Aware Boundary

Post-CJ changed the first zero boundary for expensive reduced one-lot names to PC lot-aware admission:

`lot_minimum_exceeds_quality_authorized_target`

This is semantically intentional under CH/CJ. It prevents implicit one-lot rescue from overriding Adaptive Buy Quality.

### Common Frontier / BF

Post-CJ common frontier is healthy for names admitted by PC:

- 94340: 2 accepted lots, BF 200 shares
- 37820: 3 accepted lots, BF 300 shares
- 89180: 21 accepted lots, BF 2100 shares
- 76470: 7 accepted lots, BF 700 shares
- 33500: 4 accepted lots, BF 400 shares
- 67860: 2 accepted lots, BF 200 shares

No BF target exists for symbols blocked at PC by `lot_minimum_exceeds_quality_authorized_target`.

### PS / Runtime / Fill

PS consumed the BF authority:

`marginal_capital_frontier_switch_consumption.status = PASS`

Runtime produced BUY plans for the six BF symbols, and execution filled all six. No evidence indicates a PS or Runtime disappearance after BF.

## Exposure Delta Decomposition

Using artifact-compatible Day-0 weights:

- OLD approximate deployed weight from CG symbols and Post-CJ one-lot weights: about 51.6%
- Post-CJ BF-authorized deployed weight: 11.954%
- Explained delta: about 39.7 percentage points, matching the observed 39.1-39.7 point range depending on CG aggregate vs artifact-compatible weights.

| Component | Weight contribution | Direction | Explanation |
| --- | ---: | --- | --- |
| Below-one-lot quality-ceiling blocks | about 42.75 pp gross | Reduces Post-CJ vs OLD | 33700, 83060, 92420, 93600 bought in OLD through one-lot mechanics; Post-CJ blocks them |
| Quality target reduction on shared buys | about 2.12 pp | Reduces Post-CJ vs OLD | 37820 400 -> 300; 89180 3700 -> 2100 |
| Different final symbol selection | about -5.14 pp net offset | Raises Post-CJ vs OLD | Post-CJ adds 33500, 67860, 76470 |
| Common frontier competition | 0 pp defect-attributed | Neutral | BF accepted all PC-admitted Day-0 lots up to budget/order sequence; no unexplained BF suppression |
| Cash / budget | Residual 62.046 pp cash allocation | Consequence | Cash remains because blocked lots are not replaced by unauthorized one-lot rescue |
| Cap / Risk Pacing | 0 pp primary | Neutral | No primary cap/Risk Pacing blocker in the main delta |
| Lot rounding | about 2.12 pp within quality reduction | Reduces | Quality targets floor to executable lots, e.g. 37820 and 89180 |
| Other | immaterial / artifact limitation | Neutral | OLD per-symbol artifact details unavailable |

The delta is fully explained at the semantic level. Numerically, the approximation explains more than 100% gross because Post-CJ also selects new low-priced deployable names that partially offset the OLD high-price one-lot exposure.

## Required Questions

### 1. OLD high exposure dependency on minimum-lot rescue

Material. At least four OLD Day-0 buys depended on admitting one trading lot above the Buy Quality-authorized target: 33700, 83060, 92420, and 93600. Their combined artifact-compatible one-lot weight is about 42.75 percentage points, larger than the net OLD-vs-Post-CJ exposure delta after offsetting Post-CJ additions.

### 2. Why 33700 / 83060 / 92420 / 58200 could be bought before

CG says OLD bought 33700 / 83060 / 92420, while 58200 was not an OLD buy but was a Pre-CH current buy. In both cases, the mechanism is the same: the old path did not enforce the Adaptive Buy Quality reduced target as the final one-lot admission ceiling. Minimum-lot / final target mechanics could admit 100 shares even when one lot exceeded the quality-authorized target.

### 3. One-lot weight multiple vs Buy Quality target

- 33700: 1.57x
- 83060: 3.14x
- 92420: 6.65x
- 58200: 8.68x
- 93600: 8.23x

### 4. OLD minimum-lot rescue authority

OLD minimum-lot rescue appears IMPLICIT from the available evidence. The local OLD artifacts are absent, and CG/CI identify the behavior as target re-expansion / one-lot mechanics rather than a separate explicit PIT risk/capital authority authorizing Buy Quality ceiling override.

### 5. Is Post-CJ low exposure valid or still suppressed by another defect?

Post-CJ low exposure is semantically valid under CH/CJ for Day-0. The prior unintended suppression of 89180 / 76470 was repaired: both are now PC-positive, BF-positive, PS-positive, Runtime-positive, and filled. The remaining blocked names are blocked because their one-lot minimum exceeds the quality-authorized target.

No additional capital suppression defect is observed on Day-0. There is, however, an unresolved design question: whether reduced-but-deployable high-price entries should have an explicit PIT one-lot exception authority. That would be a new production design, not a rollback of CJ.

### 6. OLD semantics worth keeping

The KEEP-worthy OLD semantic is not the implicit override itself. The useful semantic is practical deployability for high-price, one-lot securities when the system intentionally wants exposure despite lot granularity.

To keep that idea safely, it needs a formal PIT authority that explicitly states:

- why exceeding the quality target by one lot is acceptable,
- maximum allowed overshoot,
- interaction with Risk Pacing, Cash, cap, and Buy Quality,
- and why it is not a fallback around the quality ceiling.

## Defect / No-Defect Judgment

No Day-0 Post-CJ wiring or suppression defect is observed after CJ.

Post-CJ capital deployment is much lower than OLD primarily because OLD relied on implicit minimum-lot rescue. CH/CJ intentionally removed that implicit behavior by preserving Adaptive Buy Quality as a hard upper authority. The remaining question is architectural: whether to add an explicit one-lot exception authority for high-price reduced entries.

## Final Judgments

PHASE32_CK_OLD_DAY0_EXPOSURE = about 51.1%

PHASE32_CK_POST_CJ_DAY0_EXPOSURE = 11.954% authority / 12.042% execution notional

PHASE32_CK_EXPOSURE_DELTA_EXPLAINED = approximately 100%

PHASE32_CK_MINIMUM_LOT_RESCUE_OLD_MATERIAL = YES

PHASE32_CK_MINIMUM_LOT_RESCUE_EXPOSURE_CONTRIBUTION = about 42.75 percentage points gross from OLD-bought 33700/83060/92420/93600; 58200 was Pre-CH-current-only per CG but has the same blocked semantics

PHASE32_CK_QUALITY_REDUCTION_EXPOSURE_CONTRIBUTION = about 2.12 percentage points on shared filled symbols 37820 and 89180

PHASE32_CK_SYMBOL_SELECTION_EXPOSURE_CONTRIBUTION = about -5.14 percentage points net offset from Post-CJ 33500/67860/76470 additions

PHASE32_CK_OTHER_CAPITAL_SUPPRESSION_DEFECT = NO

PHASE32_CK_OLD_MINIMUM_LOT_SEMANTIC = IMPLICIT

PHASE32_CK_POST_CJ_CAPITAL_DEPLOYMENT_SEMANTICALLY_VALID = YES

PHASE32_CK_PRODUCTION_REPAIR_JUSTIFIED = PARTIAL

PHASE32_CK_NEXT_STEP = Design-only decision on explicit PIT one-lot exception authority for reduced-quality high-price entries; do not restore implicit minimum-lot rescue or tune thresholds from historical PnL.
