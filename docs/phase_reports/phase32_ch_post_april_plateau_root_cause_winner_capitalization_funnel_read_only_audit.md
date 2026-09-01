# Phase32-CH — Post-April Plateau Root-Cause / Winner Capitalization Funnel READ-ONLY Audit

Target run:

`runtime-test-historical-extended-smoke-20260831T234344371102Z`

Evidence snapshot:

- run status at inspection: `RUNNING`
- source commit recorded in run commands: `cf0a00b0271d170094aa0ce2bfbedc203c364406`
- latest completed business date used: `2023-08-16`
- completed business days used: `215`
- no mutating Runtime command was executed

This is a READ-ONLY characterization. No code, config, Production behavior, Strategy parameter, threshold, weight, Cash policy, Risk Pacing, PM/PC/PS/Runtime behavior, Pending, Ledger, resume, recover, replay, or fresh-run action was changed or executed.

## Preserved References

CH preserves the accepted conclusions from:

- `phase32_cg_growth_vs_plateau_capital_productivity_winner_capitalization_read_only_audit.md`
- `phase32_ce_single_campaign_concentration_unpredictable_loss_amplification_read_only_audit.md`
- `phase32_cf_high_notional_initial_lot_entry_tail_risk_read_only_audit.md`
- `phase32_ah_add_intent_quality_pm_pc_materialization_root_cause_audit.md`
- `phase32_ak_existing_component_add_semantic_refactor_study.md`
- `portfolio_construction_and_position_sizing_contract.md`
- `high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`

Preserved baseline:

- Growth was powered by concentrated major Winners plus successful starters and organic appreciation.
- ADD is not globally broken, but it is weak by breadth and capital share.
- PM ADD is a mixed signal: it often means strong held-position continuation, not standalone proof that the next executable lot has positive marginal value now.
- Current NEW / BUY_ADD / Cash competition exists, but `runtime_opportunity_score` is an uncalibrated relative opportunity score and not a common high-resolution marginal-yen value unit.
- No correctness repair, parameter tuning, cap change, or Production promotion is justified by historical PnL alone.

## Method

Completed-day artifacts were read from the target run only:

- daily valuation and positions: `current_valuation_refresh/current_valuation_manifest.json`
- fills: `execution/fills.json`
- Runtime PM observability: `position_management/pm_decisions.json`
- canonical Strategy PM / PC / PS: `strategy/position_management.json`, `strategy/portfolio_construction.json`, `strategy/position_sizing.json`
- candidate quality: `strategy/buy_quality_decisions.json`
- market regime: `strategy/market_context.json`

Daily symbol contribution was reconstructed as:

```text
current market value + same-day SELL proceeds - prior market value - same-day BUY notional
```

This is descriptive attribution over already-completed Runtime evidence. It is not a Production decision rule and was not used to tune any strategy.

## Structural Break

The clearest mechanism break occurs in the `2023-04-10` to `2023-04-28` transition, immediately after the March-April major Winner engine stopped dominating.

Rolling evidence:

| Window | Return | Gross gain/loss | Productive exposure | Weak exposure | BUY_NEW notional | BUY_ADD notional | PM ADD | actual ADD | top-3 positive contribution share |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| `2023-03-13` -> `2023-04-10` 20BD | +40.67% | 8.81 | 72.71% | 5.66% | 2,886,830 | 31,430 | 33 | 2 | 73.12% |
| `2023-04-03` -> `2023-04-28` 20BD | -6.79% | 0.82 | 64.89% | 9.44% | 3,793,410 | 0 | 24 | 0 | 48.26% |
| `2023-04-11` -> `2023-05-11` 20BD | +0.70% | 0.59 | 62.99% | 10.40% | 4,009,850 | 0 | 16 | 0 | 43.89% |
| `2023-06-19` -> `2023-07-14` 20BD | -1.37% | 1.53 | 58.51% | 11.07% | 3,818,990 | 0 | 27 | 0 | 53.53% |
| `2023-07-03` -> `2023-07-31` 20BD | -0.53% | 0.96 | 59.60% | 17.70% | 4,308,770 | 0 | 20 | 0 | 42.30% |
| `2023-07-19` -> `2023-08-16` 20BD | -0.68% | 1.06 | 63.14% | 17.33% | 3,788,110 | 0 | 20 | 0 | 55.79% |

`PLATEAU_STRUCTURAL_BREAK_DATE_OR_WINDOW = 2023-04-10 through 2023-04-28`

The break is not chosen from equity alone. The underlying mechanism changed at the same time:

- gross gain/loss ratio collapsed from a Growth 20BD peak of `8.81` to `0.82` and then `0.59`;
- top-3 positive contribution concentration fell from `73.12%` to the `40-50%` range;
- BUY_NEW capital continued aggressively, but BUY_ADD notional went to zero;
- productive exposure declined and weak exposure rose;
- post-April gross gains and gross losses nearly cancelled.

## Period Comparison

| Metric | Growth `2023-01-18` -> `2023-04-10` | Transition `2023-04-11` -> `2023-05-31` | Plateau `2023-06-19` -> `2023-08-08` | Post-April `2023-04-11` -> `2023-08-16` |
|---|---:|---:|---:|---:|
| Business days | 57 | 34 | 36 | 87 |
| Period return | +55.51% | +1.03% | -2.23% | +9.03% |
| Net PnL | +630,520 | +16,730 | -39,610 | +146,460 |
| Gross positive contribution | +732,950 | +288,790 | +159,200 | +576,500 |
| Gross negative contribution | -88,920 | -417,010 | -135,930 | -574,990 |
| Gross gain/loss | 8.24 | 0.69 | 1.17 | 1.00 |
| Average exposure | 83.78% | 70.21% | 75.00% | 74.81% |
| Median productive/mature exposure | 77.61% | 60.41% | 58.19% | 62.27% |
| Median weak exposure | 6.52% | 9.34% | 13.24% | 10.09% |
| Median position count | 12 | 9 | 13 | 11 |
| Median top-3 exposure | 42.24% | 42.78% | 36.12% | 38.64% |
| BUY_NEW notional | 6,205,660 | 5,885,650 | 7,338,070 | 15,293,720 |
| BUY_ADD notional | 197,060 | 0 | 0 | 0 |
| PM ADD count | 74 | 31 | 43 | 92 |
| actual BUY_ADD fill count | 7 | 0 | 0 | 0 |
| Average cash | 219,729 | 474,325 | 436,951 | 420,387 |

`POST_APRIL_CAPITAL_PRODUCTIVITY_DECLINE_CONFIRMED = YES`

Post-April did not fail because capital was idle. It repeatedly recycled capital into NEW starters while the portfolio stopped forming a small number of economically dominant Winners.

## Complete ADD Funnel

Canonical funnel:

```text
Runtime PM observability ADD
-> canonical Strategy PM action
-> PC member / ADD competitor materialization
-> PC marginal capital / target-weight decision
-> PS lot/cap feasible quantity
-> Runtime planning BUY_ADD
-> Pending / Submit / Fill
```

Growth control:

| Stage | Growth count |
|---|---:|
| PM ADD observability rows | 74 |
| PC `pm_action=ADD` members in Growth | 58 |
| actual BUY_ADD fills | 7 |
| BUY_ADD notional | 197,060 |

Growth filled ADD controls:

| Date | Symbol | Campaign | Qty | Notional | PC PM | score | rank | BQ | requested increment | lot-aware increment | PC priority | PS |
|---|---|---|---:|---:|---|---:|---:|---|---:|---:|---:|---|
| `2023-01-31` | `94320` | `pc-86b7ed8997105419-94320-0001` | 100 | 15,680 | ADD | 0.283704 | 1 | REDUCED_ALLOCATION_ONLY | 0.033333 | 0.013103 | 3 | EXECUTABLE_NOW |
| `2023-02-15` | `54010` | `pc-f925dcb3bfb464b3-54010-0001` | 100 | 58,640 | ADD | 0.109526 | 3 | FULL_ALLOCATION_ELIGIBLE | 0.029412 | 0.049312 | 1 | EXECUTABLE_NOW |
| `2023-02-16` | `54010` | `pc-f925dcb3bfb464b3-54010-0001` | 100 | 59,690 | ADD | 0.125046 | 3 | REDUCED_ALLOCATION_ONLY | 0.030303 | 0.049540 | 1 | EXECUTABLE_NOW |
| `2023-02-22` | `94320` | `pc-86b7ed8997105419-94320-0001` | 100 | 15,860 | ADD | 0.156269 | 2 | FULL_ALLOCATION_ELIGIBLE | 0.038462 | 0.012618 | 1 | EXECUTABLE_NOW |
| `2023-02-24` | `94320` | `pc-86b7ed8997105419-94320-0001` | 100 | 15,760 | ADD | 0.182150 | 1 | REDUCED_ALLOCATION_ONLY | 0.031250 | 0.012844 | 1 | EXECUTABLE_NOW |
| `2023-03-15` | `94320` | `pc-86b7ed8997105419-94320-0001` | 100 | 15,840 | ADD | 0.340918 | 1 | REDUCED_ALLOCATION_ONLY | 0.031250 | 0.012758 | 1 | EXECUTABLE_NOW |
| `2023-03-16` | `94320` | `pc-86b7ed8997105419-94320-0001` | 100 | 15,590 | ADD | 0.410467 | 1 | REDUCED_ALLOCATION_ONLY | 0.043478 | 0.012637 | 1 | EXECUTABLE_NOW |

Why Growth ADDs survived:

- canonical Strategy PM preserved `ADD`;
- PC emitted positive requested and accepted incremental weight;
- PS found one executable increment;
- Runtime consumed the PS quantity as BUY_ADD.

That full chain is absent post-April.

### Plateau 43 PM ADD Rows

The 43 Plateau PM ADD rows from CG were reproduced from `position_management/pm_decisions.json`.

Important accounting result:

- `36 / 43` are 94320 Runtime PM observability ADD rows that canonical Strategy PM converts to `HOLD`, so PC sees `pm_action=HOLD`, not ADD.
- `7 / 43` are 40520 canonical PC ADD members; all retain zero requested/lot-aware increment.
- `0 / 43` reaches PS as a positive BUY_ADD quantity.
- `0 / 43` reaches Runtime BUY_ADD / Pending / Submit / Fill.

`PLATEAU_PM_ADD_43_FULLY_ACCOUNTED_FOR = YES`

| # | Date | Symbol | Campaign | Qty | Notional | Strategy PM | PC PM | Weight | Score | Rank | BQ | Cash | Requested inc | Lot inc | First blocking boundary |
|---:|---|---|---|---:|---:|---|---|---:|---:|---:|---|---:|---:|---:|---|
| 1 | 2023-06-19 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 97,980 | HOLD | HOLD | 5.71% | 0.428662 | 1 | REDUCED_ALLOCATION_ONLY | 349,880 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 2 | 2023-06-20 | 40520 | pc-baff7a32597d9518-40520-0001 | 100 | 149,400 | ADD | ADD | 8.41% | 0.154782 | 4 | FULL_ALLOCATION_ELIGIBLE | 785,280 | 0 | 0 | PC_ADD_TARGET_WEIGHT_UNCHANGED |
| 3 | 2023-06-20 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 98,160 | HOLD | HOLD | 5.52% | 0.429590 | 1 | BUY_WAIT | 785,280 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 4 | 2023-06-21 | 40520 | pc-baff7a32597d9518-40520-0001 | 100 | 147,200 | ADD | ADD | 8.28% | 0.138027 | 5 | FULL_ALLOCATION_ELIGIBLE | 673,080 | 0 | 0 | PC_ADD_TARGET_WEIGHT_UNCHANGED |
| 5 | 2023-06-21 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 97,500 | HOLD | HOLD | 5.48% | 0.427083 | 1 | REDUCED_ALLOCATION_ONLY | 673,080 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 6 | 2023-06-22 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 98,760 | HOLD | HOLD | 5.57% | 0.447105 | 1 | REDUCED_ALLOCATION_ONLY | 487,480 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 7 | 2023-06-23 | 40520 | pc-baff7a32597d9518-40520-0001 | 100 | 141,900 | ADD | ADD | 8.07% | 0.178177 | 5 | FULL_ALLOCATION_ELIGIBLE | 566,380 | 0 | 0 | PC_ADD_TARGET_WEIGHT_UNCHANGED |
| 8 | 2023-06-23 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 99,300 | HOLD | HOLD | 5.65% | 0.499618 | 1 | REDUCED_ALLOCATION_ONLY | 566,380 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 9 | 2023-06-26 | 40520 | pc-baff7a32597d9518-40520-0001 | 100 | 145,100 | ADD | ADD | 8.37% | 0.208133 | 4 | BUY_WAIT | 919,980 | 0 | 0 | BUY_QUALITY_BLOCKS_INCREMENTAL_ADD |
| 10 | 2023-06-26 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 98,880 | HOLD | HOLD | 5.70% | 0.535711 | 1 | REDUCED_ALLOCATION_ONLY | 919,980 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 11 | 2023-06-27 | 40520 | pc-baff7a32597d9518-40520-0001 | 100 | 141,000 | ADD | ADD | 8.21% | 0.228142 | 4 | FULL_ALLOCATION_ELIGIBLE | 1,094,080 | 0 | 0 | PC_ADD_TARGET_WEIGHT_UNCHANGED |
| 12 | 2023-06-27 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 99,180 | HOLD | HOLD | 5.78% | 0.554150 | 1 | REDUCED_ALLOCATION_ONLY | 1,094,080 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 13 | 2023-06-28 | 40520 | pc-baff7a32597d9518-40520-0001 | 100 | 144,200 | ADD | ADD | 8.37% | 0.210385 | 4 | BUY_WAIT | 175,580 | 0 | 0 | BUY_QUALITY_BLOCKS_INCREMENTAL_ADD |
| 14 | 2023-06-28 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 100,440 | HOLD | HOLD | 5.83% | 0.569891 | 1 | BUY_WAIT | 175,580 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 15 | 2023-06-29 | 40520 | pc-baff7a32597d9518-40520-0001 | 100 | 141,500 | ADD | ADD | 8.10% | 0.192406 | 4 | BUY_WAIT | 112,830 | 0 | 0 | BUY_QUALITY_BLOCKS_INCREMENTAL_ADD |
| 16 | 2023-06-29 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 105,720 | HOLD | HOLD | 6.05% | 0.563352 | 1 | REDUCED_ALLOCATION_ONLY | 112,830 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 17 | 2023-06-30 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 102,720 | HOLD | HOLD | 5.82% | 0.524413 | 1 | REDUCED_ALLOCATION_ONLY | 614,320 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 18 | 2023-07-03 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 102,300 | HOLD | HOLD | 5.84% | 0.505005 | 1 | REDUCED_ALLOCATION_ONLY | 430,420 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 19 | 2023-07-04 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 102,720 | HOLD | HOLD | 5.85% | 0.490276 | 1 | REDUCED_ALLOCATION_ONLY | 757,020 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 20 | 2023-07-05 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 101,820 | HOLD | HOLD | 5.79% | 0.516076 | 1 | BUY_WAIT | 893,020 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 21 | 2023-07-06 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 101,220 | HOLD | HOLD | 5.76% | 0.549698 | 1 | BUY_WAIT | 441,420 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 22 | 2023-07-07 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 100,200 | HOLD | HOLD | 5.70% | 0.551103 | 1 | BUY_WAIT | 192,710 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 23 | 2023-07-10 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 99,720 | HOLD | HOLD | 5.66% | 0.567585 | 1 | REDUCED_ALLOCATION_ONLY | 130,010 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 24 | 2023-07-11 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 100,140 | HOLD | HOLD | 5.69% | 0.560455 | 1 | BUY_WAIT | 367,510 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 25 | 2023-07-12 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 97,800 | HOLD | HOLD | 5.56% | 0.561753 | 1 | REDUCED_ALLOCATION_ONLY | 282,310 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 26 | 2023-07-13 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 97,800 | HOLD | HOLD | 5.60% | 0.516066 | 1 | REDUCED_ALLOCATION_ONLY | 242,450 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 27 | 2023-07-14 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 97,860 | HOLD | HOLD | 5.58% | 0.506003 | 1 | BUY_WAIT | 851,320 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 28 | 2023-07-18 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 97,500 | HOLD | HOLD | 5.56% | 0.483420 | 1 | REDUCED_ALLOCATION_ONLY | 543,920 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 29 | 2023-07-19 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 96,900 | HOLD | HOLD | 5.50% | 0.441678 | 1 | REDUCED_ALLOCATION_ONLY | 88,520 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 30 | 2023-07-20 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 97,500 | HOLD | HOLD | 5.48% | 0.436130 | 1 | REDUCED_ALLOCATION_ONLY | 77,450 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 31 | 2023-07-21 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 98,160 | HOLD | HOLD | 5.57% | 0.459607 | 1 | REDUCED_ALLOCATION_ONLY | 267,630 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 32 | 2023-07-24 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 99,060 | HOLD | HOLD | 5.69% | 0.421821 | 1 | REDUCED_ALLOCATION_ONLY | 529,130 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 33 | 2023-07-25 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 100,440 | HOLD | HOLD | 5.72% | 0.424614 | 1 | REDUCED_ALLOCATION_ONLY | 179,630 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 34 | 2023-07-26 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 97,800 | HOLD | HOLD | 5.60% | 0.451381 | 1 | REDUCED_ALLOCATION_ONLY | 448,400 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 35 | 2023-07-27 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 96,480 | HOLD | HOLD | 5.54% | 0.385029 | 1 | REDUCED_ALLOCATION_ONLY | 253,500 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 36 | 2023-07-28 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 96,480 | HOLD | HOLD | 5.54% | 0.377931 | 1 | REDUCED_ALLOCATION_ONLY | 374,900 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 37 | 2023-07-31 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 96,360 | HOLD | HOLD | 5.51% | 0.363953 | 1 | REDUCED_ALLOCATION_ONLY | 258,120 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 38 | 2023-08-01 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 97,740 | HOLD | HOLD | 5.59% | 0.356361 | 1 | REDUCED_ALLOCATION_ONLY | 62,320 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 39 | 2023-08-02 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 97,380 | HOLD | HOLD | 5.58% | 0.387780 | 1 | REDUCED_ALLOCATION_ONLY | 430,520 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 40 | 2023-08-03 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 96,180 | HOLD | HOLD | 5.56% | 0.426760 | 1 | REDUCED_ALLOCATION_ONLY | 599,220 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 41 | 2023-08-04 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 95,520 | HOLD | HOLD | 5.56% | 0.396824 | 1 | REDUCED_ALLOCATION_ONLY | 489,520 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 42 | 2023-08-07 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 95,100 | HOLD | HOLD | 5.50% | 0.392160 | 2 | FULL_ALLOCATION_ELIGIBLE | 583,420 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |
| 43 | 2023-08-08 | 94320 | pc-86b7ed8997105419-94320-0001 | 600 | 96,000 | HOLD | HOLD | 5.53% | 0.401784 | 2 | FULL_ALLOCATION_ELIGIBLE | 176,970 | 0 | 0 | STRATEGY_PM_CONVERTED_TO_HOLD |

Funnel blocker count for the 43 rows:

| First blocking boundary | Count |
|---|---:|
| Strategy PM converted Runtime PM ADD to HOLD | 36 |
| PC ADD target weight unchanged | 4 |
| BUY Quality blocked incremental ADD | 3 |
| PS / Runtime / Pending / Submit defect | 0 |

`PRIMARY_ADD_FUNNEL_BLOCKER = STRATEGY_PM_CONVERTED_RUNTIME_PM_ADD_TO_HOLD_BEFORE_PC`

`SECONDARY_ADD_FUNNEL_BLOCKERS = PC_ADD_TARGET_WEIGHT_UNCHANGED, BUY_QUALITY_BLOCKS_INCREMENTAL_ADD`

This is not a Runtime BUY_ADD materialization defect. Positive BUY_ADD was not produced upstream.

## NEW vs ADD Marginal Capital Competition

Post-April actual capital destinations:

| Window | BUY_NEW | BUY_ADD | Average cash | End cash |
|---|---:|---:|---:|---:|
| `2023-04-11` -> `2023-04-24` | 2,255,550 | 0 | 333,301 | 393,640 |
| `2023-04-25` -> `2023-05-11` | 1,754,300 | 0 | 473,883 | 295,970 |
| `2023-05-12` -> `2023-05-25` | 1,242,900 | 0 | 622,760 | 300,070 |
| `2023-05-26` -> `2023-06-08` | 1,361,470 | 0 | 362,191 | 155,450 |
| `2023-06-09` -> `2023-06-22` | 1,446,900 | 0 | 358,973 | 487,480 |
| `2023-06-23` -> `2023-07-06` | 2,046,350 | 0 | 600,505 | 441,420 |
| `2023-07-07` -> `2023-07-21` | 1,937,060 | 0 | 304,383 | 267,630 |
| `2023-07-24` -> `2023-08-04` | 2,036,610 | 0 | 362,526 | 489,520 |
| `2023-08-07` -> `2023-08-16` | 1,212,580 | 0 | 341,209 | 376,830 |

`POST_APRIL_CAPITAL_TO_BUY_NEW = 15,293,720`

`POST_APRIL_CAPITAL_TO_BUY_ADD = 0`

`POST_APRIL_CAPITAL_RETAINED_AS_CASH = 420,387 average daily cash; 376,830 on 2023-08-16`

Where marginal yen went:

```text
SELL / exits released cash
-> PC allocated repeatedly to BUY_NEW starters
-> BUY_ADD received no filled capital
-> residual cash remained material but not dominant enough to explain plateau by itself
```

`ADD_VS_NEW_SCORE_SEMANTICALLY_COMPARABLE = NO`

Reason: current architecture explicitly treats `runtime_opportunity_score` as an uncalibrated relative model score, not a common high-resolution marginal-yen value unit across NEW_BUY, BUY_ADD, and Cash. PC is SoT owner of final allocation, but the current common value resolution is coarse.

`MARGINAL_CAPITAL_SEMANTIC_GAP_CONTRIBUTES_TO_PLATEAU = YES_PARTIAL`

The contribution is not that PC directly preferred NEW over many final-stage positive ADD competitors. The sharper evidence is earlier: many observed PM ADDs never become canonical ADD capital competitors, while post-April capital competition remains dominated by NEW candidates and Cash.

## Starter Replacement Loop

Post-April starter lifecycle:

| Window | Starter count | Initial notional | Closed <=5BD | Loop capital <=10BD | Loop +10BD PnL | Median closed/observed lifetime |
|---|---:|---:|---:|---:|---:|---:|
| Growth | 78 | 6,205,660 | 48 | 4,886,780 | -89,970 | 4BD |
| Post-April | 149 | 15,293,720 | 95 | 12,396,590 | -265,560 | 4BD |
| Plateau | 68 | 7,338,070 | 43 | 6,355,740 | -92,250 | 4BD |

Post-April starter follow-through from frozen BUY_NEW populations:

| Window | +3BD median / mean | +5BD median / mean | +10BD median / mean | +10BD positive rate |
|---|---:|---:|---:|---:|
| Growth | -45 / +750 | -95 / +790 | -95 / +3,597 | 44.87% |
| Post-April | -100 / -278 | -200 / -396 | -600 / -665 | 37.78% |
| Plateau | -200 / -639 | -250 / -989 | -600 / -929 | 35.48% |

The exact horizon numbers differ from CG's same-day-inclusive fixed-window table, but the direction is the same: post-April / Plateau starter follow-through is materially weaker after PIT populations are frozen.

`STARTER_REPLACEMENT_LOOP_SUPPORTED = YES`

`STARTER_REPLACEMENT_LOOP_CAPITAL = 12,396,590 post-April <=10BD recycled starter initial notional; 6,355,740 inside the fixed Plateau window`

`STARTER_REPLACEMENT_LOOP_NET_PNL = -265,560 post-April <=10BD loop PnL; -92,250 inside the fixed Plateau window`

This loop is the best-supported direct explanation for gross gain/loss cancellation.

## Candidate Availability vs Follow-Through

BQ availability:

| Window | BQ rows | FULL/HIGH | REDUCED/HIGH | REDUCED/MEDIUM | BUY_WAIT | Avg quality score |
|---|---:|---:|---:|---:|---:|---:|
| Growth | 2,850 | 223 | 155 | 1,050 | 600 | 0.5353 |
| Post-April | 4,400 | 399 | 230 | 1,349 | 1,039 | 0.5206 |
| Plateau | 1,800 | 178 | 92 | 566 | 385 | 0.5176 |

Raw candidate / BQ opportunity supply did not disappear. Plateau even has material FULL/HIGH rows. The failure is that admitted starters and held winners did not convert into durable dominant contribution.

`CANDIDATE_QUALITY_CALIBRATION_WEAKENED = YES_AS_REALIZED_FOLLOW_THROUGH_CHARACTERIZATION_NOT_AS_TUNING_AUTHORITY`

Interpretation:

- The candidate system continued to admit plausible opportunities under PIT evidence.
- Realized post-admission continuation weakened materially.
- This supports weaker market follow-through and coarse capital allocation calibration, not a direct Candidate AI correctness defect.

## Winner Capitalization Opportunity

Post-April winners / positive controls:

| Symbol | Net contribution | Positive | Negative | PM ADD rows | ADD fills | Max MV | Interpretation |
|---|---:|---:|---:|---:|---:|---:|---|
| 95650 | +71,500 | +100,000 | -28,500 | 0 | 0 | 340,500 | Organic/high-notional winner; no PM ADD authority observed |
| 71160 | +44,600 | +101,900 | -57,300 | 0 | 0 | 222,300 | Gross winner with giveback; no PM ADD |
| 49370 | +41,200 | +41,200 | 0 | 0 | 0 | 157,100 | Clean positive; no PM ADD |
| 72140 | +39,900 | +41,800 | -1,900 | 0 | 0 | 162,500 | Clean positive; no PM ADD |
| 93410 | +37,900 | +67,600 | -29,700 | 0 | 0 | 224,700 | Gross winner with giveback; no PM ADD |
| 40520 | +29,600 | +81,800 | -52,200 | 7 | 0 | 149,400 | PM ADD existed; canonical PC kept zero increment / BQ blocks |
| 88900 | +28,400 | +98,600 | -70,200 | 0 | 0 | 315,500 | Existing organic winner; no PM ADD |
| 43950 | +26,600 | +26,600 | 0 | 0 | 0 | 187,000 | Clean positive; no PM ADD |
| 94320 | +3,480 | +36,960 | -33,480 | 36 | 0 | 105,720 | PM observability ADD; canonical Strategy PM HOLD |

`WINNERS_WITH_PM_ADD_BUT_NO_FILL_COUNT = 2` (`40520`, `94320`)

`WINNERS_WITH_CAP_AND_CASH_HEADROOM_BUT_NO_ADD_COUNT = 2`

Both had cap headroom and many dates with cash available, but the canonical incremental ADD authority did not survive to a positive PS quantity. For `94320`, the first boundary is Strategy PM conversion to HOLD. For `40520`, the first boundary is PC target increment zero or BUY Quality block.

`NO_ADD_WINNER_CONTROLS_EXPLAINED = YES`

Most post-April positive controls never emitted PM ADD. That is not by itself a defect: they either won organically, were short-lived starters, lacked canonical PM ADD authority, or had no final incremental ADD evidence.

## 59350 Removal / Replacement

59350 lifecycle in this run:

- `2023-03-23`: BUY_NEW 100 shares, notional `212,200`
- `2023-04-20`: SELL_EXIT 100 shares, proceeds `373,000`
- Growth-period contribution: `+232,800`
- Post-April contribution: `-72,000`

After the 59350 exit:

| Window | SELL proceeds | BUY_NEW | BUY_ADD | Average cash | Representative NEW destinations |
|---|---:|---:|---:|---:|---|
| `2023-04-18` -> `2023-05-01` | 2,160,720 | 2,020,350 | 0 | 400,277 | 60220, 94340, 77190, 38100, 69270, 39070, 64080, 93630, 76010, 73570, 93530, 14180, 50260, 66130, 62310, 46730 |
| `2023-04-19` -> `2023-05-02` | 2,308,920 | 1,780,850 | 0 | 453,084 | 94340, 77190, 38100, 69270, 39070, 64080, 93630, 76010, 73570, 93530, 14180, 50260, 66130, 62310, 46730 |

`59350_POST_EXIT_CAPITAL_DESTINATION = BROAD_BUY_NEW_REPLACEMENT_PLUS_MATERIAL_CASH; NO_BUY_ADD`

`MAJOR_WINNER_REPLACEMENT_OCCURRED = NO`

Several post-exit buys became positive contributors, but none replaced 59350's dominant contribution concentration. Capital fragmented into many starters and cash rather than forming another dominant Winner engine.

## Gross Gain / Loss Cancellation

Contribution source attribution:

| Window | Starter gains | Starter losses | Mature gains | Mature losses |
|---|---:|---:|---:|---:|
| Growth | +1,138,170 | -504,560 | +324,390 | -313,970 |
| Post-April | +1,201,910 | -1,091,240 | +353,770 | -462,930 |
| Plateau | +331,240 | -305,980 | +136,940 | -138,930 |

`PRIMARY_GROSS_LOSS_SOURCE = POST_APRIL_STARTER_REPLACEMENT_LOOP_LOSSES_WITH_MATURE_WINNER_GIVEBACK_AS_SECONDARY`

`PRIMARY_GROSS_GAIN_SOURCE = STARTER_GAINS_PLUS_ORGANIC_MATURE_WINNERS; NOT_ADD_SCALED_POSITIONS`

This explains why gross gain/loss collapsed:

- Growth gains had dominant concentration, especially 59350 / 67310 / 44440.
- Post-April gains were broader and more offset by starter failures and mature givebacks.
- BUY_ADD contributed no post-April gross gain.

## Productive Exposure Decline

`PRODUCTIVE_EXPOSURE_DECLINE_ROOT_CAUSE = MAJOR_WINNER_ENGINE_DECAY_PLUS_REPLACEMENT_CAPITAL_FRAGMENTATION_INTO_WEAKER_STARTERS_PLUS_ZERO_POST_APRIL_ADD_CAPITALIZATION`

Decomposition:

- fewer dominant Winners remained after 59350 and the March-April engine faded;
- replacement capital went mainly into BUY_NEW, not ADD;
- post-April starters had weaker +3/+5/+10BD follow-through;
- weak exposure rose from Growth median `6.52%` to Plateau median `13.24%`;
- top-3 exposure and contribution concentration declined;
- available PM ADD observations did not become executable incremental capital.

## Root Cause Hierarchy

### Primary Root Cause

`STARTER_REPLACEMENT_CHURN_WITH_WEAK_FOLLOW_THROUGH_AFTER_MAJOR_WINNER_ENGINE_DECAY`

The strongest supported causal chain:

```text
March-April dominant Winners stopped dominating / exited / gave back
-> capital was released
-> post-April PC continued deploying large marginal yen mostly into BUY_NEW
-> new starters had weaker follow-through and short lifetimes
-> gains were broader and less dominant
-> losses from starter churn plus mature giveback cancelled gains
-> no post-April BUY_ADD capitalization emerged to build another dominant Winner
```

### Secondary Contributors

1. `WINNER_CAPITALIZATION_FUNNEL_SUPPRESSION`

   PM ADD observability remained frequent, but canonical ADD capital authority did not survive:

   - 36 Plateau rows: Runtime PM ADD -> Strategy PM HOLD;
   - 4 rows: PC ADD target unchanged;
   - 3 rows: BUY Quality blocked incremental ADD.

2. `ADD_VS_NEW_MARGINAL_CAPITAL_SEMANTIC_GAP`

   NEW / ADD / Cash do not yet share a common high-resolution marginal-yen value unit. This likely amplifies capital fragmentation, but CH does not prove a final-stage invalid NEW-over-ADD decision for the Plateau rows because most ADDs never reached that final comparison.

3. `WEAKER_MARKET_FOLLOW_THROUGH`

   BQ / candidate supply remained present, but admitted opportunities followed through less well. This is material and partly market-driven.

4. `PRODUCTIVE_EXPOSURE_DILUTION`

   Productive exposure fell, weak exposure rose, and contribution concentration collapsed.

### Symptoms

- equity plateau;
- `BUY_ADD fill count = 0`;
- higher churn;
- lower top-3 contribution share;
- larger cash average.

These are not root causes without the funnel and capital-destination trace above.

## Classification

| Mechanism | Classification | Repairability |
|---|---|---|
| Starter replacement churn with weak follow-through | `MIXED: STRATEGY_ALLOCATION_WEAKNESS + MARKET_OPPORTUNITY_REALITY` | Partly repairable by existing PC/PS/ADD shadow study; not safely fixed by direct Production tuning here |
| Strategy PM converts many PM ADD observations to HOLD | `ARCHITECTURAL_SEMANTIC_GAP / EXPECTED_FILTERING` | Repairable as semantic clarification / shadow ADD consideration, not a correctness hotfix |
| PC ADD target weight unchanged / BQ blocks | `STRATEGY_ALLOCATION_WEAKNESS / EXPECTED_FILTERING` | Potentially repairable by existing architecture, after shadow validation |
| ADD vs NEW common value gap | `ARCHITECTURAL_SEMANTIC_GAP` | Repairable inside existing PC-owned capital value architecture |
| Candidate follow-through weakened | `MARKET_OPPORTUNITY_REALITY + CALIBRATION_WEAKNESS` | Needs shadow characterization; not a correctness repair |
| Lot/cap constraints | `EXPECTED_LOT/CAP_CONSTRAINT` | Not primary in Plateau 43 rows |
| Runtime / Pending / Submit BUY_ADD path | `NOT_A_CURRENT_CAUSE` | No repair indicated by CH |

## Repairability

`ROOT_CAUSE_REPAIRABLE_INSIDE_EXISTING_ARCHITECTURE = YES_PARTIAL`

The best next step fits existing architecture:

```text
PC-owned shadow marginal capital productivity / ADD consideration study
```

It should compare marginal yen destinations among:

- scaled existing Winners;
- NEW starters;
- Cash optionality;
- existing held capital.

It should reuse existing Candidate/BQ/SI/PM/PC/PS evidence and preserve G129, KI-004, KI-006, BQ, PM SELL, caps, and Risk Pacing semantics.

`NEW_COMPONENT_REQUIRED = NO`

`NEW_MODEL_REQUIRED = NO_FOR_NEXT_SHADOW_STEP`

`NEW_FEATURE_REQUIRED = YES_SHADOW_FEATURE_OR_REPORTING_FOR_MARGINAL_CAPITAL_PRODUCTIVITY_AND_ADD_CONSIDERATION`

`PRODUCTION_CHANGE_JUSTIFIED = NO`

`SHADOW_FOLLOWUP_JUSTIFIED = YES`

## Required Final Answers

1. `LATEST_COMPLETED_DATE_USED = 2023-08-16`
2. `PLATEAU_STRUCTURAL_BREAK_DATE_OR_WINDOW = 2023-04-10 through 2023-04-28`
3. `POST_APRIL_CAPITAL_PRODUCTIVITY_DECLINE_CONFIRMED = YES`
4. `GROWTH_PM_ADD_COUNT = 74`
5. `GROWTH_BUY_ADD_FILL_COUNT = 7`
6. `POST_APRIL_PM_ADD_COUNT = 92`
7. `POST_APRIL_BUY_ADD_FILL_COUNT = 0`
8. `PLATEAU_PM_ADD_43_FULLY_ACCOUNTED_FOR = YES`
9. `PRIMARY_ADD_FUNNEL_BLOCKER = STRATEGY_PM_CONVERTED_RUNTIME_PM_ADD_TO_HOLD_BEFORE_PC`
10. `SECONDARY_ADD_FUNNEL_BLOCKERS = PC_ADD_TARGET_WEIGHT_UNCHANGED; BUY_QUALITY_BLOCKS_INCREMENTAL_ADD`
11. `ADD_VS_NEW_SCORE_SEMANTICALLY_COMPARABLE = NO`
12. `MARGINAL_CAPITAL_SEMANTIC_GAP_CONTRIBUTES_TO_PLATEAU = YES_PARTIAL`
13. `POST_APRIL_CAPITAL_TO_BUY_NEW = 15,293,720`
14. `POST_APRIL_CAPITAL_TO_BUY_ADD = 0`
15. `POST_APRIL_CAPITAL_RETAINED_AS_CASH = 420,387 average daily cash; 376,830 on 2023-08-16`
16. `STARTER_REPLACEMENT_LOOP_SUPPORTED = YES`
17. `STARTER_REPLACEMENT_LOOP_CAPITAL = 12,396,590 post-April <=10BD loop capital`
18. `STARTER_REPLACEMENT_LOOP_NET_PNL = -265,560 post-April <=10BD loop PnL`
19. `WINNERS_WITH_PM_ADD_BUT_NO_FILL_COUNT = 2`
20. `WINNERS_WITH_CAP_AND_CASH_HEADROOM_BUT_NO_ADD_COUNT = 2`
21. `NO_ADD_WINNER_CONTROLS_EXPLAINED = YES`
22. `CANDIDATE_QUALITY_CALIBRATION_WEAKENED = YES_AS_REALIZED_FOLLOW_THROUGH_CHARACTERIZATION_NOT_TUNING_AUTHORITY`
23. `PRIMARY_GROSS_LOSS_SOURCE = STARTER_REPLACEMENT_LOOP_LOSSES; MATURE_WINNER_GIVEBACK_SECONDARY`
24. `PRIMARY_GROSS_GAIN_SOURCE = STARTER_GAINS_PLUS_ORGANIC_MATURE_WINNERS; NOT_ADD_SCALED_POSITIONS`
25. `PRODUCTIVE_EXPOSURE_DECLINE_ROOT_CAUSE = MAJOR_WINNER_ENGINE_DECAY_PLUS_REPLACEMENT_CAPITAL_FRAGMENTATION_INTO_WEAKER_STARTERS_PLUS_ZERO_POST_APRIL_ADD_CAPITALIZATION`
26. `59350_POST_EXIT_CAPITAL_DESTINATION = BROAD_BUY_NEW_REPLACEMENT_PLUS_MATERIAL_CASH; NO_BUY_ADD`
27. `MAJOR_WINNER_REPLACEMENT_OCCURRED = NO`
28. `PRIMARY_ROOT_CAUSE = STARTER_REPLACEMENT_CHURN_WITH_WEAK_FOLLOW_THROUGH_AFTER_MAJOR_WINNER_ENGINE_DECAY`
29. `SECONDARY_CONTRIBUTORS = WINNER_CAPITALIZATION_FUNNEL_SUPPRESSION; ADD_VS_NEW_MARGINAL_CAPITAL_SEMANTIC_GAP; PRODUCTIVE_EXPOSURE_DILUTION; MATURE_WINNER_GIVEBACK`
30. `MARKET_REALITY_CONTRIBUTION = MATERIAL`
31. `CORRECTNESS_DEFECT_FOUND = NO`
32. `ARCHITECTURAL_SEMANTIC_GAP_FOUND = YES`
33. `STRATEGY_ALLOCATION_WEAKNESS_FOUND = YES`
34. `ROOT_CAUSE_REPAIRABLE_INSIDE_EXISTING_ARCHITECTURE = YES_PARTIAL`
35. `NEW_COMPONENT_REQUIRED = NO`
36. `NEW_MODEL_REQUIRED = NO_FOR_NEXT_SHADOW_STEP`
37. `NEW_FEATURE_REQUIRED = YES_SHADOW_FEATURE_OR_REPORTING_FOR_MARGINAL_CAPITAL_PRODUCTIVITY_AND_ADD_CONSIDERATION`
38. `PRODUCTION_CHANGE_JUSTIFIED = NO`
39. `SHADOW_FOLLOWUP_JUSTIFIED = YES`
40. `NEXT_RECOMMENDED_STEP = READ-ONLY/SHADOW PC-owned marginal capital productivity and ADD consideration study that compares scaled Winners vs NEW starters vs Cash using existing PIT Candidate/BQ/SI/PM/PC/PS evidence, without changing Production.`
41. `POST_APRIL_PLATEAU_ROOT_CAUSE = MIXED_WITH_PRIMARY_STARTER_REPLACEMENT_CHURN`
42. `FINAL_JUDGMENT = PHASE32_CH_POST_APRIL_PLATEAU_ROOT_CAUSE_IDENTIFIED_PRIMARY_STARTER_REPLACEMENT_CHURN_WITH_WEAK_FOLLOW_THROUGH_SECONDARY_WINNER_CAPITALIZATION_FUNNEL_SUPPRESSION_AND_MARGINAL_CAPITAL_SEMANTIC_GAP_SHADOW_FOLLOWUP_JUSTIFIED_PRODUCTION_CHANGE_NOT_JUSTIFIED`

## Final Judgment

`PHASE32_CH_POST_APRIL_PLATEAU_ROOT_CAUSE_IDENTIFIED_PRIMARY_STARTER_REPLACEMENT_CHURN_WITH_WEAK_FOLLOW_THROUGH_SECONDARY_WINNER_CAPITALIZATION_FUNNEL_SUPPRESSION_AND_MARGINAL_CAPITAL_SEMANTIC_GAP_SHADOW_FOLLOWUP_JUSTIFIED_PRODUCTION_CHANGE_NOT_JUSTIFIED`

