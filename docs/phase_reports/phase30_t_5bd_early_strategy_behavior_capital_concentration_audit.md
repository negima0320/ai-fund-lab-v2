# Phase30-T - 5BD Early Strategy Behavior / Capital Concentration Audit

## Primary Judgment

`EARLY_STRATEGY_BEHAVIOR_MIXED_LOSS_CONTAINMENT_IMPROVING_CAPITAL_CONCENTRATION_NOT_YET_WORKING`

This is a read-only audit of:

`runtime-test-historical-extended-smoke-20260816T014640663183Z`

No Strategy, Runtime, config, threshold, model, or target run artifacts were modified.

## 5BD Performance

| Date | Equity | Cash | Exposure | Positions |
| --- | ---: | ---: | ---: | ---: |
| 2022-08-10 | 995,860 | 745,820 | 25.11% | 9 |
| 2022-08-12 | 1,000,700 | 696,190 | 30.43% | 8 |
| 2022-08-15 | 998,660 | 678,790 | 32.03% | 9 |
| 2022-08-16 | 986,500 | 819,050 | 16.97% | 7 |
| 2022-08-17 | 989,170 | 830,200 | 16.07% | 7 |

5BD end state:

```text
Equity = 989,170
Return = -1.08%
Cash = 830,200
Exposure = 16.07%
Positions = 7
```

## Exposure Drop Root Cause

The exposure drop from `32.03%` to roughly `16%` is multi-causal:

- Intentional SELL / EXIT dominated on 2022-08-15 to 2022-08-17.
- 93180 exited after the PM reason moved to `trend_and_opportunity_broken`.
- 89180 was repeatedly reduced under `peak_drawdown_warning` / sell-side evidence while preserving a residual winner.
- Replacement candidates existed, but many were `BUY_WAIT` or failed PS lot/minimum-notional conversion.
- Phase30-S handoff did not recur: PC/PS were production-consumable and Runtime BUY intent appeared when PS produced positive quantity.

SELL cash was not fully reinvested because PC positive replacement candidates did not become executable PS quantities often enough, especially by 2022-08-17.

## 93180

Quantity path:

```text
6600 -> 6600 -> 5000 -> 0
```

PIT evidence:

- 2022-08-10: BUY_NEW, CQ PASS, trend SUPPORTIVE, relative MIXED, Downside Risk PASS.
- 2022-08-12: HOLD with `downside_risk_contained`, `strategy_intelligence_hold_worthiness_pass`, `trend_continuation`.
- 2022-08-15: REDUCE with `risk_increased_but_trend_not_broken`.
- 2022-08-16: EXIT with `trend_and_opportunity_broken`; Runtime planned `SELL_EXIT` for 5,000 shares.

Judgment: the exit looks like loss containment, not panic churn. Campaign PnL ended at `-5,000 JPY`.

## 89180

Quantity path:

```text
2700 -> 2100 -> 1100 -> 900 -> 500
```

PIT evidence:

- 2022-08-10: BUY_NEW, CQ PASS, trend MIXED, relative WEAK, Downside Risk PASS.
- 2022-08-12: REDUCE with `risk_increased_but_trend_not_broken`.
- 2022-08-15: REDUCE with `peak_drawdown_warning`.
- 2022-08-16: REDUCE with sell-side evidence connected.
- 2022-08-17: REDUCE with `peak_drawdown_warning`; residual position preserved.

Judgment: `SELL_REDUCE_BEHAVIOR_IMPROVING`. The strategy reduced exposure while retaining a profitable residual. Campaign PnL ended at `+1,500 JPY`.

## Current HOLD Quality

As of 2022-08-17:

| Symbol | Qty | PM | CQ | Trend | Relative | PnL |
| --- | ---: | --- | --- | --- | --- | ---: |
| 23230 | 300 | REDUCE | PASS | WEAK | MIXED | 540 |
| 23700 | 500 | HOLD | PASS | SUPPORTIVE | SUPPORTIVE | 1,500 |
| 36640 | 300 | REDUCE | PASS | WEAK | MIXED | 500 |
| 78590 | 100 | HOLD | PASS | SUPPORTIVE | SUPPORTIVE | 2,000 |
| 89180 | 500 | REDUCE | PASS | SUPPORTIVE | MIXED | 1,500 |
| 94320 | 200 | HOLD | PASS | WEAK | WEAK | 0 |
| 94340 | 100 | HOLD | PASS | MIXED | WEAK | 180 |

The strongest HOLD evidence is in `23700` and `78590`. Several remaining positions are not clean winners; they are being reduced or held because downside evidence is contained, lot/min-notional constraints limit executable reduction, or PM still has hold-worthiness evidence.

## ADD / Capital Concentration

Existing-position ADD did not materially function in the first 5BD.

The only explicit PM ADD observed was `94320` on 2022-08-12:

- PM reasons: `strong_trend_continuation`, `opportunity_rank_still_high`, `no_loss_averaging`
- PC final target preserved the existing baseline
- `accepted_incremental_weight = 0`
- PS `quantity_delta_candidate = 0`
- Runtime action: `NO_ACTION`

So the strategy is holding some winners, but not yet concentrating additional capital into them. New BUY_NEW allocation worked earlier in the window, but post-SELL reinvestment weakened sharply.

## Replacement Funnel

| Date | BUY_NEW Candidates | BUY_WAIT | PC Positive | PS Positive Qty | Runtime BUY Intent | BUY Fills |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-08-10 | 25 | 16 | 18 | 9 | 9 | 9 |
| 2022-08-12 | 22 | 8 | 13 | 3 | 3 | 3 |
| 2022-08-15 | 18 | 15 | 11 | 2 | 2 | 2 |
| 2022-08-16 | 19 | 12 | 11 | 1 | 1 | 1 |
| 2022-08-17 | 22 | 9 | 7 | 0 | 0 | 0 |

On 2022-08-17, all 7 PC-positive replacement candidates had `quantity_delta_candidate = 0` with `minimum_meaningful_notional_diagnostic_unmet`. Examples:

- 66190: target notional about 151k vs minimum meaningful notional about 235k
- 99840: target notional about 108k vs minimum meaningful notional about 148k

This is not Phase30-S recurrence. It is a capital concentration / lot feasibility boundary.

## Cash Judgment

`MULTI_CAUSAL`

83% cash is partly justified by intentional exits/reduces and weak replacement conversion. It is not automatically a failure. But it is also not fully healthy: strong or acceptable candidates existed, yet the system did not concentrate enough capital into executable replacement or ADD quantities.

## Loss Attribution

Campaign PnL sum equals the 5BD equity loss of `-10,830 JPY`.

Main negative contributors:

- 91070: `-6,550`
- 93180: `-5,000`
- 23880: `-2,300`
- 37820: `-2,000`

Main positive contributors:

- 78590: `+2,000`
- 23700: `+1,500`
- 89180: `+1,500`

The loss source is mixed: some bad entries / normal adverse moves were cut quickly, while winner holding and partial profit capture helped offset losses.

## Production Integrity

```text
PHASE30_P_STRATEGY_MIGRATION_PRESERVED = YES
ONE_PRODUCTION_STRATEGY_AUTHORITY_PATH = YES
LEGACY_STRATEGY_PATH_REINTRODUCED = NO
PHASE30_S_HANDOFF_DEFECT_RECURRENCE = NO
Expected Edge = UNCALIBRATED
```

## Direction Flags

```text
LOSS_CONTAINMENT_DIRECTION = IMPROVING
WINNER_HOLD_DIRECTION = IMPROVING
CAPITAL_CONCENTRATION_DIRECTION = NOT_IMPROVING
SELL_REDUCE_DIRECTION = IMPROVING
EARLY_STRATEGY_DIRECTION = MIXED
```

5BD is not enough for final performance judgment.

## Implementation Authorization

`NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30-T`

## Recommended Next Action

Continue the 10BD run. After 10BD completes, review whether capital concentration remains blocked by PC target-weight distribution versus lot/minimum-notional feasibility. If a repair is authorized later, isolate it as:

`Phase30-U - PC Lot-Aware Capital Concentration / ADD Incremental Allocation Audit`
