# Phase32-CA - NEW Conviction / Target-Weight Semantic Preservation Audit

## Executive Summary

This was a READ-ONLY artifact audit of Post-BZ run
`runtime-test-historical-extended-smoke-20260829T011806584578Z`.

At audit time the available strategy coverage was 19 business days:
`2022-10-03` through `2022-10-28`. The run was still marked `RUNNING`; this
report uses the artifact snapshot available when inspected and does not stop,
resume, replay, backtest, or mutate the run.

Finding: NEW selection/admission evidence is partially preserved after BV/BZ,
but NEW target-weight magnitude is only partially preserved. Every nonzero
NEW/first-lot PS output in the inspected window is `100` shares. For high-priced
symbols, that one lot often preserves the PC target notional. For lower-priced
symbols, however, the current common frontier collapses a multi-lot PC target
into a single first lot. The exact compression boundary is the active
`NEW_FIRST_LOT` marginal frontier / BF aggregated target surface, not PS
arithmetic or Runtime mapping.

In short: the system is still able to identify PC-admitted NEW candidates, but
for a material subset it cannot convert the original PC target-weight magnitude
into initial multi-lot capital. ADD now has repeated lot machinery; NEW does not.

## Required Inputs

Read:

- `docs/phase_reports/phase32_bu_post_bt_new_allocation_semantic_drift_audit.md`
- `docs/phase_reports/phase32_bv_new_reentry_production_admission_semantic_restoration.md`
- `docs/phase_reports/phase32_bz_add_admission_bf_only_authority_narrow_repair.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`

Relevant SoT boundary:

- Portfolio Construction owns target allocation / target weight.
- Position Sizing converts accepted target allocation into notional and discrete quantity.
- Position Sizing and Runtime must not reinterpret rank, quality, opportunity, or target weight.
- Under BG/BF, Position Sizing consumes BF aggregated targets as the switched PC-to-PS target authority.

## Run Identity

| Field | Value |
| --- | --- |
| Target run | `runtime-test-historical-extended-smoke-20260829T011806584578Z` |
| Source commit in run state | `887a3361eed9f46dccfa6b5b04cb8bb7ee83aa59` |
| Run state at audit | `RUNNING` |
| Snapshot coverage | `2022-10-03` to `2022-10-28` |
| Characterized strategy days | 19 |
| Production changes in this task | None |

## Aggregate NEW / First-Lot Metrics

The audit compared PC-positive first-lot rows against the current active
frontier and Position Sizing outputs.

| Metric | Value |
| --- | ---: |
| PC-positive NEW/first-lot target rows | 78 |
| Unique PC-positive symbols | 58 |
| Sum PC-positive target weight | 7.359765 |
| Accepted authority first-lot targets | 56 |
| Unique accepted symbols | 48 |
| Sum accepted authority weight | 2.843321 |
| PS nonzero first-lot rows | 56 |
| Unique PS nonzero symbols | 48 |
| Actual PS first-lot notional | 2,853,660 |
| Quantity distribution | `100 shares: 56` |
| 100-share first-lot rate | 100.0% |

For the accepted rows, the actual notional/PC target-notional ratio was:

| Ratio bucket | Accepted rows |
| --- | ---: |
| >= 95% target notional preserved | 39 |
| 80-95% | 0 |
| 50-80% | 0 |
| < 50% target notional preserved | 17 |

The accepted rows with <50% preservation are all cases where the PC target could
support multiple lots, but the active frontier accepted only one first-lot
increment.

## Target-Weight Distribution

| PC Target Weight Bucket | PC Positive | Authority Accepted | PS Nonzero | 100-Share Rows | Compressed <50% | Avg Accepted Notional Ratio |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| <=2% | 2 | 2 | 2 | 2 | 0 | 0.9964 |
| 2-5% | 32 | 32 | 32 | 32 | 17 | 0.6193 |
| 5-10% | 10 | 10 | 10 | 10 | 0 | 1.0069 |
| 10-15% | 12 | 10 | 10 | 10 | 0 | 1.0045 |
| 15%+ | 22 | 2 | 2 | 2 | 0 | 0.9964 |

The 100-share dominance is real in share terms, but not uniformly a notional
compression defect. The high-weight accepted names tend to be high-priced
symbols where one lot is already close to the PC target notional. The semantic
loss is concentrated in the 2-5% target-weight band with low-priced symbols.

## Day-Level Summary

| Date | PC+ Rows | PC+ Weight | Accepted Rows | Accepted Weight | PS Nonzero | PS Notional | Compressed Rows | Cash | Exposure | Positions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-10-03 | 9 | 0.7367 | 8 | 0.4359 | 8 | 435,880 | 4 | 578,990 | 42.9% | 8 |
| 2022-10-04 | 7 | 0.7734 | 5 | 0.3528 | 5 | 358,000 | 0 | 468,340 | 53.6% | 8 |
| 2022-10-05 | 6 | 0.5644 | 4 | 0.0647 | 4 | 65,340 | 3 | 535,450 | 46.8% | 8 |
| 2022-10-06 | 7 | 0.6102 | 5 | 0.1806 | 5 | 181,870 | 0 | 419,610 | 58.3% | 12 |
| 2022-10-07 | 6 | 0.5859 | 4 | 0.2789 | 4 | 280,810 | 1 | 321,330 | 68.1% | 10 |
| 2022-10-11 | 1 | 0.1954 | 0 | 0.0000 | 0 | 0 | 0 | 490,360 | 51.1% | 7 |
| 2022-10-12 | 1 | 0.1807 | 0 | 0.0000 | 0 | 0 | 0 | 442,600 | 55.6% | 7 |
| 2022-10-13 | 4 | 0.3888 | 3 | 0.1513 | 3 | 150,700 | 1 | 516,300 | 47.8% | 7 |
| 2022-10-14 | 3 | 0.4019 | 1 | 0.0071 | 1 | 6,980 | 1 | 647,800 | 35.0% | 6 |
| 2022-10-17 | 3 | 0.3896 | 1 | 0.0144 | 1 | 14,400 | 0 | 631,900 | 36.5% | 7 |
| 2022-10-18 | 5 | 0.3855 | 4 | 0.1852 | 4 | 184,320 | 1 | 477,280 | 51.9% | 8 |
| 2022-10-19 | 4 | 0.4076 | 3 | 0.2084 | 3 | 206,940 | 1 | 307,580 | 69.3% | 9 |
| 2022-10-20 | 2 | 0.2631 | 1 | 0.0068 | 1 | 6,800 | 1 | 300,980 | 70.0% | 10 |
| 2022-10-21 | 4 | 0.4084 | 3 | 0.2499 | 3 | 250,700 | 1 | 337,320 | 66.1% | 10 |
| 2022-10-24 | 6 | 0.3103 | 6 | 0.2930 | 6 | 291,690 | 1 | 209,820 | 79.0% | 12 |
| 2022-10-25 | 3 | 0.2552 | 2 | 0.0845 | 2 | 84,340 | 1 | 194,220 | 80.8% | 11 |
| 2022-10-26 | 3 | 0.3110 | 2 | 0.1609 | 2 | 162,500 | 0 | 231,070 | 77.4% | 9 |
| 2022-10-27 | 4 | 0.1916 | 4 | 0.1690 | 4 | 172,390 | 1 | 78,970 | 92.3% | 11 |
| 2022-10-28 | 0 | 0.0000 | 0 | 0.0000 | 0 | 0 | 0 | 55,880 | 94.5% | 10 |

Low exposure is linked to NEW sizing/admission in early days, especially where
PC-positive weight is much larger than accepted first-lot weight. It is not the
only driver: cap blocks, Cash/budget sequence stops, exits, and available
candidate mix also contribute.

## Representative Traces

### 2022-10-03 - High Notional Preserved

| Symbol | PC Target | Authority Gap | PS Qty | Price | Notional Ratio | Rank | Quality | Interpretation |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 58200 | 0.174670 | 0.174670 | 100 | 1,746.7 | 1.000 | 23 | 0.598170 | One lot is the full PC target notional |
| 92420 | 0.137500 | 0.137500 | 100 | 1,375.0 | 1.000 | 21 | 0.615140 | One lot preserves target magnitude |
| 83060 | 0.064800 | 0.064800 | 100 | 648.0 | 1.000 | 20 | 0.612652 | One lot preserves target magnitude |

These are 100-share NEW positions, but not capital-compressed.

### 2022-10-03 - Multi-Lot PC Target Compressed to One Lot

| Symbol | PC Target | PC Requested Lots | PC Executable Qty | Authority Gap | PS Qty | Price | Notional Ratio | Rank | Quality |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 37820 | 0.033636 | 4 | 400 | 0.006800 | 100 | 68.0 | 0.202 | 6 | 0.716582 |
| 89180 | 0.033636 | 37 | 3,700 | 0.000900 | 100 | 9.0 | 0.027 | 25 | 0.585257 |
| 76470 | 0.033636 | 12 | 1,200 | 0.002700 | 100 | 27.0 | 0.080 | 26 | 0.576307 |
| 94340 | 0.033636 | 2 | 200 | 0.014410 | 100 | 144.1 | 0.428 | 3 | 0.765860 |

In each case PC had a positive target and PC lot evidence reported multiple
executable lots. The active authority candidate was nevertheless a single
`NEW_FIRST_LOT` with `increment_quantity = 100`; BF passed that one-lot target
to PS, and PS consumed it correctly.

### High PC Target Not Accepted

High PC target rows that did not become BF targets were mostly guardrail or
competition outcomes, not PS compression:

| Date | Symbol | PC Target | Price | Requested Lots Approx | Authority Disposition | Rank | Quality |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: |
| 2022-10-06 | 70640 | 0.2379 | 2,395.0 | 0.99 | `INFEASIBLE_CAP_BLOCKED` | 12 | 0.711756 |
| 2022-10-20 | 44490 | 0.2343 | 2,345.0 | 1.00 | `INFEASIBLE_CAP_BLOCKED` | 41 | 0.479261 |
| 2022-10-05 | 70640 | 0.2328 | 2,352.5 | 0.99 | `INFEASIBLE_CAP_BLOCKED` | 12 | 0.707282 |
| 2022-10-04 | 93600 | 0.1999 | 2,029.0 | 0.99 | `INFEASIBLE_CAP_BLOCKED` | 9 | 0.717944 |
| 2022-10-03 | 93600 | 0.1911 | 1,911.0 | 1.00 | `INFEASIBLE_CAP_BLOCKED` | 10 | 0.690580 |

Across all PC-positive rows not accepted by the authority:

| Disposition | Count |
| --- | ---: |
| `INFEASIBLE_CAP_BLOCKED` | 17 |
| `REJECTED_BY_STRONGER_MARGINAL_CAPITAL_VALUE` | 5 |

## Exact Compression Boundary

The first quantity/magnitude divergence for compressed rows is:

```text
PC target_weight / PC lot evidence
-> canonical_marginal_capital_frontier_authority.v1 NEW_FIRST_LOT candidate
-> accepted_incremental_weight = one_lot_weight
-> BF aggregated PS target
-> PS converts accepted one-lot target to 100 shares
-> Runtime maps PS quantity without recalculation
```

PS is not recomputing or shrinking the target; it consumes the BF target. Runtime
is also not shrinking the quantity. The compression occurs because the current
common frontier has repeated lots for ADD but only one first-lot candidate for
NEW/REENTRY.

## Selection vs Capital Conversion

This audit separates two questions:

1. Can the system identify acceptable NEW candidates?
2. Can it translate that conviction into initial capital size?

The answer to the first is mostly yes: after BV, legacy-zero NEW promotion is
blocked and PC-positive first-lot admission is visible. Authority accepted 56
first-lot targets from 78 PC-positive rows, while rejected rows had explicit cap
or stronger-alternative dispositions.

The answer to the second is partial/no for multi-lot NEW: selected low-priced
NEW candidates can be compressed to one lot even when PC target weight and PC
lot evidence support a larger initial allocation. This is not a performance
claim; it is a decision-time semantic preservation issue.

## Defect / No-Defect Judgment

No defect was found in PS arithmetic, Runtime mapping, Cash resolver, BZ ADD
admission, REDUCE/EXIT, or Safety/Risk Pacing from this audit.

The semantic gap is in the production authority shape:

- ADD has repeated marginal lots.
- NEW/REENTRY has only a first-lot candidate.
- Therefore PC target-weight magnitude for NEW/REENTRY can be truncated before
  PS sees it.

Production repair is justified as a design/authority repair candidate, not as
threshold tuning and not as historical-performance optimization. The likely
repair boundary is to preserve PC-owned first-lot admission while adding a
PC-owned, budget-bounded multi-lot or target-magnitude preservation contract for
NEW/REENTRY where existing PC target weight and lot evidence already authorize
more than one lot.

## Final Judgments

PHASE32_CA_NEW_SELECTION_SIGNAL_PRESERVED = PARTIAL

PHASE32_CA_PC_TARGET_WEIGHT_MAGNITUDE_PRESERVED = PARTIAL

PHASE32_CA_NEW_100_SHARE_DOMINANCE = 56/56 PS nonzero first-lot rows were 100 shares; economically, 39/56 accepted rows preserved >=95% of PC target notional while 17/56 compressed below 50%.

PHASE32_CA_HIGH_CONVICTION_ONE_LOT_COMPRESSION = NO for accepted >=5% PC target rows; YES for medium 2-5% PC target rows where low price made PC evidence multi-lot but BF accepted only one lot.

PHASE32_CA_PRIMARY_COMPRESSION_BOUNDARY = NEW_FIRST_LOT marginal authority candidate / BF aggregated target generation uses a single 100-share first-lot increment; PS and Runtime consume that target without recomputing.

PHASE32_CA_LOW_EXPOSURE_LINKED_TO_NEW_SIZING = PARTIAL

PHASE32_CA_PRODUCTION_REPAIR_JUSTIFIED = PARTIAL

PHASE32_CA_NEXT_STEP = Design a narrow PC-owned NEW/REENTRY target-magnitude preservation or repeated first-lot expansion contract, using existing PC target weight and PIT lot evidence, while preserving BV admission, BZ ADD PASS-only admission, Cash/budget competition, cap/Safety/Risk Pacing, and without performance-based tuning.
