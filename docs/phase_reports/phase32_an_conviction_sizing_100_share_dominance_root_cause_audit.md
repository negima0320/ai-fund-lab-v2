# Phase32-AN — Conviction Sizing / 100-Share Dominance Root-Cause Deep Audit

## Executive Summary

This is a read-only audit of `runtime-test-historical-extended-smoke-20260827T093649849074Z`. During the audit the latest valuation-ready coverage advanced to `2023-12-14`; all counts below use completed daily artifacts through that date.

Primary answer to "WHY 100 SHARES?": mostly because the authoritative BUY quantity path converts already-compressed target weights into Japan round-lot quantities by flooring to 100-share units. For BUY_NEW, `82.3%` of fills are 100 shares. For REENTRY, only `30.8%` are 100 shares because some REENTRY names are low priced and therefore produce multi-lot quantities. For BUY_ADD, `100.0%` of fills are 100 shares; this is a separate structural behavior where PC final discrete executable quantity authority repeatedly authorizes one lot for ADD, and Position Sizing consumes that authority.

No mandatory sizing implementation defect was found. I found zero cases where accepted target, cash, cap, and lot feasibility implied more than 100 shares while actual path incorrectly emitted 100. The issue is architectural/research-grade rather than a production repair: conviction/rank/quality have weak direct relationship to order notional, normal target weights are compressed around low single-digit percentages, high-price stocks naturally floor to one lot, and ADD capitalization is structurally one-lot incremental.

## Run Identity / Coverage

- Run id: `runtime-test-historical-extended-smoke-20260827T093649849074Z`
- Run root: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260827T093649849074Z`
- Latest valuation-ready coverage used: `2023-12-14`
- Completed valuation-ready days: `297`
- Primary prior source: `docs/phase_reports/phase32_am_buy_new_early_failure_vs_winner_pit_divergence_deep_audit.md`
- Constraints honored: no production/config/schema/threshold/model/runtime-state mutation; no fresh-run, resume, replay, backtest, or run stop.

## Actual Sizing Architecture

Actual BUY quantity path:

1. Strategy/PC produces candidate membership, semantic BUY type, rank, quality, marginal capital value, and target weight.
2. `strategy.position_sizing.produce_position_sizing_artifact()` creates `strategy/position_sizing.json`.
3. `_size_positions()` uses active rows, target exposure, portfolio equity, dynamic position count, quality/volatility/PM intent adjustment, and caps to produce target weights and notionals.
4. `_raw_position()` converts target notional or ADD transaction delta into quantity with `_lot_quantity(..., trading_unit=100)`.
5. For selected PC discrete authority, `_apply_canonical_deployment_set_to_sizing_rows()` and `_pc_final_discrete_authority_deployment_row()` bind PC's discrete executable quantity before final PS consumption.
6. `strategy.runtime_planning` emits `planned_quantity` from `quantity_delta_candidate`.
7. `runtime_v2.planning.strategy_authority` converts the plan to order/pending items; it records `lot_rounding = already_applied_by_position_sizing`.
8. Submit/historical adapter validates positive quantity and trading unit, then fills at the target-session Open.

Code anchors:

- [position_sizing.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/strategy/position_sizing.py:426): builds lot preflight and position rows.
- [position_sizing.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/strategy/position_sizing.py:742): normalizes/caps target weights and computes target notionals from portfolio equity.
- [position_sizing.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/strategy/position_sizing.py:1485): ADD quantity delta path.
- [position_sizing.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/strategy/position_sizing.py:1578): BUY_NEW/REENTRY lot quantity path.
- [strategy_authority.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/runtime_v2/planning/strategy_authority.py:670): consumes `planned_quantity`.
- [environment.py](/Users/negishi/work/ai-fund-lab-v2/src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py:230): validates positive quantity and accepted trading unit.

The relevant policy config is [position_sizing.json](/Users/negishi/work/ai-fund-lab-v2/configs/strategy/position_sizing.json:31): minimum meaningful notional is diagnostic around JPY 50,000, tradable unit is 100 shares, and strategy max position weight is 18%.

## Quantity Distribution

| Semantic type | Fill count | 100-share fills | 100-share ratio | Median qty | Mean qty | p75 | p90 | Max |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BUY_NEW | 487 | 401 | 82.3% | 100 | 195.7 | 100 | 200 | 7100 |
| REENTRY | 13 | 4 | 30.8% | 200 | 1200.0 | 2100 | 3300 | 5000 |
| BUY_ADD | 11 | 11 | 100.0% | 100 | 100.0 | 100 | 100 | 100 |

Quantity buckets:

| Semantic type | 100 | 200 | 300 | 400-500 | 600-900 | 1000+ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BUY_NEW | 401 | 37 | 22 | 7 | 10 | 10 |
| REENTRY | 4 | 3 | 1 | 0 | 1 | 4 |
| BUY_ADD | 11 | 0 | 0 | 0 | 0 | 0 |

## Notional Distribution

| Semantic type | Median notional | Mean notional | Median notional/equity | Mean notional/equity |
| --- | ---: | ---: | ---: | ---: |
| All BUY | JPY 57,900 | JPY 84,227 | 4.05% | 5.85% |
| BUY_NEW | JPY 58,500 | JPY 85,430 | 4.12% | 5.93% |
| REENTRY | JPY 52,500 | JPY 84,527 | 3.37% | 5.52% |
| BUY_ADD | JPY 16,020 | JPY 30,577 | 1.50% | 2.40% |

100 shares is not always small. At JPY 1,000-2,000, one lot is already 6-14% of observed equity in many cases. At JPY 2,000-5,000, one lot can be 10-24% of equity. This is why several strong-looking 100-share cases are normal lot-aware outcomes, not truncation defects.

Monthly evolution:

| Month | BUY fills | Median notional | Median notional/equity | 100-share ratio |
| --- | ---: | ---: | ---: | ---: |
| 2022-10 | 49 | 35,100 | 3.31% | 77.6% |
| 2022-11 | 30 | 38,400 | 3.50% | 83.3% |
| 2022-12 | 32 | 37,300 | 3.30% | 84.4% |
| 2023-01 | 37 | 47,200 | 3.99% | 89.2% |
| 2023-02 | 38 | 50,150 | 4.14% | 86.8% |
| 2023-03 | 32 | 105,050 | 7.62% | 84.4% |
| 2023-04 | 33 | 69,300 | 4.38% | 72.7% |
| 2023-05 | 32 | 56,800 | 3.81% | 68.8% |
| 2023-06 | 37 | 57,200 | 3.73% | 78.4% |
| 2023-07 | 41 | 68,450 | 4.21% | 97.6% |
| 2023-08 | 33 | 86,370 | 5.36% | 87.9% |
| 2023-09 | 42 | 51,500 | 3.07% | 78.6% |
| 2023-10 | 38 | 58,600 | 3.54% | 81.6% |
| 2023-11 | 19 | 87,050 | 5.10% | 84.2% |
| 2023-12 | 17 | 58,500 | 3.43% | 52.9% |

## Equity Scaling

| Equity bucket | BUY fills | Median notional | Median target weight | Median qty | 100-share ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0.9-1.1M | 76 | 36,250 | 2.95% | 100 | 78.9% |
| 1.1-1.3M | 118 | 47,950 | 2.54% | 100 | 86.4% |
| 1.3-1.5M | 32 | 70,900 | 3.25% | 100 | 71.9% |
| 1.5-1.7M | 259 | 65,400 | 2.64% | 100 | 81.9% |
| 1.7M+ | 26 | 69,700 | 3.00% | 100 | 73.1% |

Judgment: `PARTIALLY_SCALES`.

Absolute notional rises from the early 35-48k range into the 65-70k range as equity grows, but the median quantity remains 100 and the 100-share ratio remains high. The first limiting authority is not runtime submit or fill; it is the combination of compressed target weights and round-lot floor in Position Sizing.

## Conviction / Allocation Relationship

Correlation against actual notional/equity:

| Signal | All BUY | BUY_NEW | REENTRY | BUY_ADD |
| --- | ---: | ---: | ---: | ---: |
| Rank | -0.009 | -0.055 | 0.291 | 0.162 |
| Runtime opportunity score | -0.023 | 0.046 | -0.274 | 0.109 |
| Quality score | -0.006 | 0.037 | -0.257 | -0.307 |
| Target weight | 0.894 | 0.940 | 0.984 | 0.873 |
| Price | 0.958 | 0.957 | 0.984 | 0.994 |

Interpretation: allocation follows target weight and price/lot mechanics, not rank or quality directly. This is expected from the current architecture because Position Sizing consumes PC target weights and discrete lot authority; it does not re-rank capital by rank/quality at runtime. However, it means candidate conviction is only weakly visible in final share quantity.

Judgment: `WEAK` conviction-to-allocation relationship.

## AM Finding Reconciliation

Phase32-AM found T0 target weight means of roughly 6.3% for BUY_NEW early failures and 6.4% for caution winners. AN explains why: target weight is dominated by PC/PS target construction, caution compression, and lot feasibility, not by realized outcome and not strongly by rank/quality. In AN's full coverage, positive BUY_NEW Position Sizing rows have normal target-weight median around `3.23%`, and filled BUY_NEW median target weight is `~3-4%` depending on equity bucket.

Classification: primarily `B. caution allocation compression` plus `C. conviction signal not reaching sizing as a strong continuous allocator` and `D. target-weight compression`.

## Strong Candidate -> 100 Shares

Representative strong-at-decision-time 100-share cases:

| Date | Symbol | Type | Rank | Quality | Score | Target wt | Normal wt | Requested wt | Accepted wt | Equity | Price | Desired notional | Pre-round qty | Rounded qty | Executable qty | Fill qty | First limiting authority |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2023-05-25 | 30410 | BUY_NEW | 2 | 0.797 | 0.374 | 8.826% | 5.556% | 5.556% | 8.826% | 1,524,450 | 1340.0 | 133,000 | 0 | 100 | 100 | 100 | LOT_SIZE_PRICE_FLOOR |
| 2022-11-01 | 94320 | BUY_ADD | 1 | 0.793 | 0.386 | 7.789% | 9.689% | 9.689% | 7.789% | 1,067,300 | 163.9 | 81,769 | 200 | 100 | 200 | 100 | PC_DISCRETE_1_LOT_ADD |
| 2023-06-20 | 99840 | REENTRY | 5 | 0.791 | 0.103 | 9.951% | 3.226% | 3.226% | 9.951% | 1,678,880 | 1632.5 | 167,280 | 0 | 100 | 100 | 100 | LOT_SIZE_PRICE_FLOOR |
| 2022-12-09 | 72730 | BUY_NEW | 3 | 0.789 | 0.231 | 1.629% | 2.778% | 2.778% | 1.629% | 1,135,210 | 179.3 | 18,470 | 100 | 100 | 100 | 100 | LOT_SIZE_PRICE_FLOOR |
| 2022-10-06 | 94340 | BUY_ADD | 2 | 0.784 | 0.240 | 2.770% | 6.342% | 6.342% | 4.149% | 1,072,100 | 147.8 | 29,600 | 200 | 100 | 200 | 100 | PC_DISCRETE_1_LOT_ADD |
| 2022-10-28 | 94320 | BUY_ADD | 1 | 0.783 | 0.397 | 6.212% | 8.352% | 8.352% | 6.212% | 1,037,300 | 162.3 | 64,950 | 200 | 100 | 200 | 100 | PC_DISCRETE_1_LOT_ADD |
| 2023-03-16 | 43880 | BUY_NEW | 4 | 0.781 | 0.295 | 9.916% | 4.546% | 2.149% | 9.916% | 1,368,740 | 1139.0 | 129,999 | 0 | 100 | 100 | 100 | LOT_SIZE_PRICE_FLOOR |
| 2023-06-15 | 40520 | BUY_NEW | 5 | 0.781 | 0.065 | 7.043% | 3.704% | 3.704% | 7.043% | 1,571,990 | 1021.0 | 111,700 | 0 | 100 | 100 | 100 | LOT_SIZE_PRICE_FLOOR |
| 2023-02-02 | 77760 | BUY_NEW | 5 | 0.780 | 0.056 | 2.806% | 3.125% | 3.125% | 2.806% | 1,210,060 | 337.0 | 33,900 | 100 | 100 | 100 | 100 | LOT_SIZE_PRICE_FLOOR |
| 2023-03-17 | 59350 | BUY_NEW | 4 | 0.780 | 0.263 | 13.867% | 2.857% | 2.857% | 13.867% | 1,404,690 | 1598.0 | 189,800 | 0 | 100 | 100 | 100 | LOT_SIZE_PRICE_FLOOR |
| 2023-02-15 | 54010 | BUY_ADD | 3 | 0.776 | 0.110 | 9.623% | 7.698% | 7.698% | 9.623% | 1,233,660 | 586.4 | 116,911 | 0 | 100 | 100 | 100 | PC_DISCRETE_1_LOT_ADD |
| 2023-11-01 | 98120 | BUY_NEW | 4 | 0.775 | 0.046 | 3.333% | 3.333% | 3.333% | 2.462% | 1,676,800 | 343.0 | 55,111 | 100 | 100 | 100 | 100 | LOT_SIZE_PRICE_FLOOR |
| 2022-11-09 | 94320 | BUY_ADD | 1 | 0.774 | 0.397 | 8.864% | 12.313% | 12.313% | 10.293% | 1,094,840 | 160.2 | 97,260 | 200 | 100 | 200 | 100 | PC_DISCRETE_1_LOT_ADD |
| 2023-06-28 | 37780 | BUY_NEW | 8 | 0.771 | 0.011 | 7.602% | 3.125% | 3.125% | 7.602% | 1,628,730 | 1112.0 | 122,399 | 0 | 100 | 100 | 100 | LOT_SIZE_PRICE_FLOOR |
| 2023-02-24 | 39450 | BUY_NEW | 6 | 0.770 | 0.003 | 10.874% | 3.030% | 2.488% | 10.874% | 1,272,850 | 1334.0 | 138,499 | 0 | 100 | 100 | 100 | LOT_SIZE_PRICE_FLOOR |
| 2022-10-12 | 94320 | BUY_ADD | 1 | 0.766 | 0.425 | 4.582% | 5.244% | 5.244% | 4.582% | 1,032,350 | 159.2 | 47,801 | 100 | 100 | 100 | 100 | PC_DISCRETE_1_LOT_ADD |
| 2023-05-29 | 24350 | BUY_NEW | 7 | 0.764 | 0.043 | 1.791% | 3.333% | 3.333% | 1.791% | 1,529,570 | 265.0 | 27,400 | 100 | 100 | 100 | 100 | LOT_SIZE_PRICE_FLOOR |
| 2022-10-06 | 65500 | BUY_NEW | 6 | 0.762 | -0.102 | 2.012% | 3.571% | 3.571% | 2.012% | 1,072,100 | 207.0 | 21,500 | 100 | 100 | 100 | 100 | LOT_SIZE_PRICE_FLOOR |
| 2022-11-04 | 94320 | BUY_ADD | 1 | 0.761 | 0.404 | 9.082% | 11.183% | 11.183% | 9.082% | 1,080,940 | 162.6 | 97,070 | 200 | 100 | 200 | 100 | PC_DISCRETE_1_LOT_ADD |
| 2022-11-14 | 78860 | BUY_NEW | 8 | 0.759 | 0.018 | 9.715% | 4.000% | 4.000% | 9.715% | 1,059,180 | 1055.0 | 105,600 | 0 | 100 | 100 | 100 | LOT_SIZE_PRICE_FLOOR |
| 2023-06-13 | 44920 | BUY_NEW | 9 | 0.758 | -0.034 | 3.231% | 3.571% | 3.231% | 2.900% | 1,587,010 | 456.0 | 52,003 | 100 | 100 | 100 | 100 | LOT_SIZE_PRICE_FLOOR |
| 2023-09-26 | 53800 | BUY_NEW | 9 | 0.754 | -0.096 | 9.937% | 3.226% | 3.226% | 9.937% | 1,673,740 | 1570.0 | 165,500 | 0 | 100 | 100 | 100 | LOT_SIZE_PRICE_FLOOR |

The key distinction: in many high-price rows, the accepted target itself only supports one 100-share lot. For ADD rows, PC/lot authority often shows a larger pre-round/executable context, but final actual ADD remains one lot.

## 200 / 300+ Positive Controls

The positive controls show that multi-lot fills occur mainly when price is low, not necessarily when conviction is high.

| Date | Symbol | Type | Qty | Price | Notional | Target wt | Rank | Quality | Pre-round qty |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2023-05-29 | 65740 | BUY_NEW | 7100 | 6.9 | 48,990 | 1.647% | 46 | 0.494 | 7100 |
| 2022-10-25 | 93180 | BUY_NEW | 6700 | 5.0 | 33,500 | 3.226% | 2 | 0.795 | 6700 |
| 2023-09-06 | 89180 | REENTRY | 5000 | 9.0 | 45,000 | 2.703% | 8 | 0.758 | 5000 |
| 2023-05-16 | 21340 | BUY_NEW | 4300 | 10.0 | 43,000 | 1.609% | 39 | 0.545 | 4300 |
| 2022-10-03 | 89180 | BUY_NEW | 3700 | 10.0 | 37,000 | 1.969% | 25 | 0.585 | 3700 |
| 2023-11-21 | 82560 | REENTRY | 3400 | 19.0 | 64,600 | 3.846% | 3 | 0.803 | 3400 |
| 2023-09-13 | 60850 | BUY_NEW | 3300 | 18.3 | 60,390 | 2.498% | 19 | 0.675 | 3300 |
| 2023-12-08 | 60850 | REENTRY | 2900 | 16.2 | 46,980 | 3.333% | 9 | 0.743 | 2900 |
| 2023-05-30 | 21340 | REENTRY | 2100 | 25.0 | 52,500 | 3.125% | 3 | 0.797 | 2100 |
| 2023-12-11 | 25860 | BUY_NEW | 1300 | 45.0 | 58,500 | 1.947% | 39 | 0.526 | 1300 |

Positive-control conclusion: 200/300/1000+ shares require low price and target notional large enough to clear multiple 100-share lots. Strong rank alone is not enough.

## Price Effect

| Price bucket | BUY fills | Median qty | Median notional | Median target wt | 100-share ratio |
| --- | ---: | ---: | ---: | ---: | ---: |
| <500 | 243 | 100 | 35,700 | 1.77% | 61.3% |
| 500-1000 | 121 | 100 | 69,100 | 2.84% | 99.2% |
| 1000-2000 | 109 | 100 | 138,500 | 5.95% | 100.0% |
| 2000-5000 | 38 | 100 | 256,500 | 10.21% | 100.0% |
| 5000+ | 0 | n/a | n/a | n/a | n/a |

Price is the dominant mechanical explanation for share count. Notional must be evaluated with quantity; share count alone exaggerates the small-position concern.

## BUY_NEW Sizing

I did not find an explicit "BUY_NEW must start as a small starter position" contract. The actual behavior is starter-like because:

- normal target weights cluster around low single-digit percentages,
- quality/caution frequently reduces target allocation,
- PC/Cash competition often leaves residual cash explicit rather than forcing deployment,
- round-lot flooring makes many valid targets exactly one lot.

Therefore the contract judgment is `PARTIAL`: no explicit starter-only rule, but actual production path behaves like starter sizing for many BUY_NEW names.

## REENTRY Sizing

REENTRY uses the same Position Sizing path, but the observed distribution is distinct:

- REENTRY fill count: `13`
- REENTRY 100-share ratio: `30.8%`
- REENTRY median quantity: `200`
- REENTRY median notional: JPY `52,500`

The distinct distribution is mostly caused by low-priced REENTRY cases and higher recovered target weights, not by a wholly separate REENTRY sizing engine. Judgment: `PARTIAL`.

## BUY_ADD Deep Dive

All actual BUY_ADD fills are one lot.

| Date | Symbol | Rank | Quality | Target wt | Normal wt | Requested wt | Accepted wt | Price | Current notional | Desired notional | Pre-round qty | PC qty | Fill qty | First limiting authority |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2022-10-06 | 94340 | 2 | 0.784 | 2.770% | 6.342% | 6.342% | 4.149% | 147.8 | 29,600 | 29,600 | 200 | 100 | 100 | PC_DISCRETE_1_LOT_ADD |
| 2022-10-12 | 94320 | 1 | 0.766 | 4.582% | 5.244% | 5.244% | 4.582% | 159.2 | 32,000 | 47,801 | 100 | 100 | 100 | PC_DISCRETE_1_LOT_ADD |
| 2022-10-12 | 94340 | 2 | 0.750 | 5.600% | 6.369% | 6.369% | 5.600% | 146.4 | 43,740 | 58,420 | 100 | 100 | 100 | PC_DISCRETE_1_LOT_ADD |
| 2022-10-13 | 94340 | 2 | 0.740 | 7.096% | 8.331% | 8.331% | 7.096% | 145.7 | 58,720 | 73,250 | 100 | 100 | 100 | PC_DISCRETE_1_LOT_ADD |
| 2022-10-28 | 94320 | 1 | 0.783 | 6.212% | 8.352% | 8.352% | 6.212% | 162.3 | 48,600 | 64,950 | 200 | 100 | 100 | PC_DISCRETE_1_LOT_ADD |
| 2022-11-01 | 94320 | 1 | 0.793 | 7.789% | 9.689% | 9.689% | 7.789% | 163.9 | 65,520 | 81,769 | 200 | 100 | 100 | PC_DISCRETE_1_LOT_ADD |
| 2022-11-04 | 94320 | 1 | 0.761 | 9.082% | 11.183% | 11.183% | 9.082% | 162.6 | 81,050 | 97,070 | 200 | 100 | 100 | PC_DISCRETE_1_LOT_ADD |
| 2022-11-09 | 94320 | 1 | 0.774 | 8.864% | 12.313% | 12.313% | 10.293% | 160.2 | 97,260 | 97,260 | 200 | 100 | 100 | PC_DISCRETE_1_LOT_ADD |
| 2023-02-15 | 54010 | 3 | 0.776 | 9.623% | 7.698% | 7.698% | 9.623% | 586.4 | 57,790 | 116,911 | 0 | 100 | 100 | PC_DISCRETE_1_LOT_ADD |
| 2023-05-31 | 59550 | 4 | 0.750 | 4.938% | 7.475% | 7.475% | 4.938% | 144.0 | 62,800 | 77,000 | 300 | 100 | 100 | PC_DISCRETE_1_LOT_ADD |
| 2023-05-31 | 30410 | 2 | 0.741 | 17.141% | 12.157% | 12.157% | 17.141% | 1385.0 | 135,800 | 267,300 | 0 | 100 | 100 | PC_DISCRETE_1_LOT_ADD |

ADD 100-share root cause: structural. Several rows show normal/pre-round context at 200 or 300 shares, yet final PC discrete authority supplies one lot. This is not a PS arithmetic defect; it is an architecture choice in the ADD capital competition / lot-aware final allocation layer.

## Winner Capitalization

Named major-winner traces from campaign/fill artifacts:

| Symbol | Campaign behavior | Capitalization observed |
| --- | --- | --- |
| 23750 | Two campaigns. First 100-share campaign closed quickly at +3.1%. Second opened 2023-10-02 with 100 shares, later closed 2023-11-08 at +111.9%, MFE +190.2%. | No ADD observed despite large later winner outcome. This is descriptive only; future return was not available at entry. |
| 65730 | 2023-08-14 campaign opened with 300 shares at 211.7, closed +156.6%, MFE +170.8%. | Larger initial quantity due lower price; no ADD observed. |
| 98120 | Two campaigns, both 100-share initial buys. 2023-11-01 campaign closed +29.4%, MFE +42.0%. | No ADD observed. |
| 94320 | 2022 campaign opened 200 shares, then ADDs of 100 shares on 2022-10-12, 10-28, 11-01, 11-04, 11-09. Later 2023 campaign opened 200 shares and remained open through coverage. | This is the strongest positive control: winner/continuation capitalization can occur, but only via repeated 100-share increments. |

Judgment: winner capitalization is `PARTIAL`. The system can add to winners, but the ADD path is one-lot incremental and sparse.

## Missed Capitalization

Decision-time ADD intent/value did exist in some cases where only one lot was added:

- `94320` repeatedly had rank 1, high quality, requested/normal weights above accepted/final weights, and ADD fills of only 100 shares.
- `59550` had pre-round quantity 300 but final fill 100.
- `30410` had target weight 17.1%, desired notional 267k, and one ADD lot of 100 shares.

This is material enough for research, but not a mandatory defect because the authoritative PC discrete quantity layer intentionally selected the final increment.

## Target-Weight Distribution / Compression

Positive Position Sizing row target weights:

| Type | Rows | Target weight median | Target weight p25/p75 | Normal target median |
| --- | ---: | ---: | ---: | ---: |
| BUY_NEW | 875 | 3.14% | 1.87% / 5.42% | 3.23% |
| REENTRY | 16 | 3.81% | 3.08% / 7.57% | 3.18% |
| BUY_ADD | 331 | 2.13% | 2.04% / 2.59% | 2.13% |

Target-weight compression is present. There are high-tail cases, but the median capital decision is low single digit. Since 100-share lots at common prices consume roughly that same notional band, final quantity often cannot exceed one lot.

## Cap Analysis

Strategy maximum position weight is 18%; safety cap is consumed independently. Cap is not the primary limiter across the full sample:

- Mandatory defect candidates: `0`.
- Most 100-share BUY_NEW/REENTRY rows are explainable by target notional divided by price and 100-share floor.
- High-price rows sometimes use one-lot / soft-cap authority because one round lot is already a large weight.
- ADD rows are limited by PC discrete one-lot authority, not by a global strategy or safety hard cap.

Judgment: `PHASE32_AN_CAP_IS_PRIMARY_LIMITER = PARTIAL`.

## Position Count Interaction

Open position count across valuation-ready days:

- Mean: `10.2`
- Median: `10`
- p90: `14`
- Max: `19`

One-lot positions:

- Mean: `7.9`
- Median: `8`
- p90: `12`
- Max: `16`

High position-count days show the pattern clearly. On 2023-09-07 there were 19 open positions, 16 one-lot positions, median position weight 2.94%, and top-3 share 28.47%. This is a broad diversification / many-one-lot posture rather than a concentrated "few strongest names" posture.

## Philosophy Alignment

Alignment judgment: `PARTIAL`.

Aligned:

- Cash remains a valid position and is not silently redeployed.
- Position Sizing preserves PC/PM authority and does not re-decide rank at runtime.
- Strong high-price candidates can receive meaningful notional even with 100 shares.
- ADD/winner capitalization exists, proven by 94320.

Not fully aligned:

- Conviction/rank/quality do not strongly scale final order notional.
- Target weights are compressed.
- ADD capitalization is structurally one-lot incremental.
- Many days hold numerous one-lot positions, diluting concentration in stronger names.

## Mandatory Defect Assessment

Mandatory defect test result: `NO`.

No row met the defect condition:

- accepted target implies >100 shares,
- sufficient cash,
- no cap/risk restriction,
- executable lot available,
- yet actual quantity incorrectly becomes 100.

The actual-path lineage is internally consistent: target/PC discrete authority -> PS lot rounding -> runtime planning quantity -> historical fill quantity.

## Research Opportunities

Research is justified, but production repair is not justified from AN alone.

Recommended research themes:

- Conviction-to-capital mapping: inspect whether rank/quality/opportunity score should affect target weight more continuously before PC final allocation.
- ADD increment sizing: evaluate whether PC final discrete authority should allow multi-lot ADD when decision-time ADD value and cash are already present.
- Position count vs concentration: characterize whether 15-19 mostly one-lot positions reduce winner capitalization.
- Equity scaling: test whether target notional should scale more explicitly with equity after 1.5M+ without forcing weak deployment.
- Winner-control protection: avoid future-return tuning; compare only decision-time ADD evidence against contemporaneous PC/PS authority.

## MA200 Inventory Note

I found no current MA200 / 200-day moving-average / equivalent long-horizon moving-average feature in the scanned production source, config, or latest strategy artifacts. The current visible trend evidence remains shorter horizon fields such as 5/20 and 20/60 style ratios. MA200 is not currently used in this sizing path.

## Final Judgments

PHASE32_AN_RUN_ID = runtime-test-historical-extended-smoke-20260827T093649849074Z

PHASE32_AN_COVERAGE_END = 2023-12-14

PHASE32_AN_BUY_NEW_FILL_TOTAL = 487

PHASE32_AN_BUY_NEW_100_SHARE_RATIO = 82.3%

PHASE32_AN_REENTRY_FILL_TOTAL = 13

PHASE32_AN_REENTRY_100_SHARE_RATIO = 30.8%

PHASE32_AN_BUY_ADD_FILL_TOTAL = 11

PHASE32_AN_BUY_ADD_100_SHARE_RATIO = 100.0%

PHASE32_AN_MEDIAN_BUY_NOTIONAL = JPY 57,900

PHASE32_AN_ORDER_NOTIONAL_EQUITY_SCALING = PARTIALLY_SCALES

PHASE32_AN_CONVICTION_ALLOCATION_RELATIONSHIP = WEAK

PHASE32_AN_STRONG_CANDIDATE_100_SHARE_CASES = 22 representative cases listed; at least 40 exist under rank <= 10 or quality >= 0.70 or target_weight >= 7%.

PHASE32_AN_100_SHARE_PRIMARY_CAUSE = I

PHASE32_AN_BUY_NEW_STARTER_POSITION_CONTRACT = PARTIAL

PHASE32_AN_REENTRY_SIZING_DISTINCT_FROM_BUY_NEW = PARTIAL

PHASE32_AN_ADD_TARGET_DELTA_MATERIAL = PARTIAL

PHASE32_AN_ADD_100_SHARE_STRUCTURAL = YES

PHASE32_AN_WINNER_CAPITALIZATION_EFFECTIVE = PARTIAL

PHASE32_AN_MISSED_WINNER_CAPITALIZATION_MATERIAL = PARTIAL

PHASE32_AN_TARGET_WEIGHT_COMPRESSION = YES

PHASE32_AN_CAP_IS_PRIMARY_LIMITER = PARTIAL

PHASE32_AN_TOO_MANY_ONE_LOT_POSITIONS = YES

PHASE32_AN_CAPITAL_ALLOCATION_PHILOSOPHY_ALIGNMENT = PARTIAL

PHASE32_AN_SIZING_IMPLEMENTATION_DEFECT = NO

PHASE32_AN_NEW_MANDATORY_DEFECT_FOUND = NO

PHASE32_AN_PRODUCTION_REPAIR_JUSTIFIED_NOW = NO

PHASE32_AN_CONVICTION_SIZING_RESEARCH_JUSTIFIED = YES

PHASE32_AN_MA200_CURRENTLY_USED = NO

PHASE32_AN_LONG_RUN_CONTINUE = YES

PHASE32_AN_NEXT_STEP = Read-only conviction-to-target-weight and ADD multi-lot research design using decision-time PC/PS evidence; no production sizing change yet.
