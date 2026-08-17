# Phase30-U - 10BD Entry Quality / Large Loss / Capital Reinvestment Audit

## Primary Judgment

`PHASE30_10BD_STRATEGY_DIRECTION_MIXED_ENTRY_INTELLIGENCE_GAP_AND_CAPITAL_CONCENTRATION_QUALITY_POOR`

This is a READ-ONLY audit of:

`runtime-test-historical-extended-smoke-20260816T014640663183Z`

No Strategy, Runtime, threshold, config, model, or target run artifact was modified.

## 10BD Performance

```text
Final Equity: 939,110
Return: -6.09%
Cash: 462,710
Exposure: 50.73%
Positions: 4
completed_days: 10BD
close result: REVIEW_REQUIRED
2022-08-24 Daily PnL: -48,800
```

Daily equity path:

| Date | Equity | Daily PnL | Cash | Exposure | Positions |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2022-08-10 | 995,860 |  | 745,820 | 25.11% | 9 |
| 2022-08-12 | 1,000,700 | 4,840 | 696,190 | 30.43% | 8 |
| 2022-08-15 | 998,660 | -2,040 | 678,790 | 32.03% | 9 |
| 2022-08-16 | 986,500 | -12,160 | 819,050 | 16.97% | 7 |
| 2022-08-17 | 989,170 | 2,670 | 830,200 | 16.07% | 7 |
| 2022-08-18 | 988,830 | -340 | 794,070 | 19.70% | 8 |
| 2022-08-19 | 988,950 | 120 | 828,390 | 16.24% | 5 |
| 2022-08-22 | 989,230 | 280 | 882,910 | 10.75% | 2 |
| 2022-08-23 | 987,910 | -1,320 | 820,150 | 16.98% | 3 |
| 2022-08-24 | 939,110 | -48,800 | 462,710 | 50.73% | 4 |

## 2022-08-24 Loss Decomposition

The `-48,800 JPY` daily PnL reconciles exactly by campaign PnL delta:

| Symbol | Daily Contribution | Quantity | Entry / Avg | Valuation / Exit | Campaign PnL | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 78780 | -44,000 | 100 | 2,860 | 2,420 | -44,000 | BUY_NEW open |
| 36600 | -5,200 | 100 | 564 | 512 | -5,200 | BUY_NEW open |
| 60540 | 700 | 100 | 324 | 319 | -500 | HOLD open |
| 94320 | -280 | 1,000 | 150.4 avg | 151.3 | 900 | BUY_ADD open |
| 94340 | -20 | 0 | 151.4 avg | 151.8 exit | 40 | SELL_EXIT closed |

```text
Sum = -48,800
```

The large loss was primarily a same-day 78780 entry loss.

## 78780 Deep Dive

Entry:

```text
BUY date: 2022-08-24
Semantic: BUY_NEW
Quantity: 100
Entry price: 2,860
PIT reference / valuation price: 2,420
BUY notional: 286,000
Campaign PnL: -44,000
```

PIT Strategy Intelligence at BUY time:

| Dimension | Evidence |
| --- | --- |
| CQ | PASS |
| Trend Health | SUPPORTIVE |
| Persistence | SUPPORTIVE |
| Relative Strength | SUPPORTIVE |
| Acceleration | DECELERATING |
| Exhaustion Risk | ELEVATED_RISK |
| Reversal Risk | ELEVATED_RISK |
| Volatility Risk | ELEVATED_RISK |
| 20D momentum | +228.0% |
| 5D momentum | +43.0% |
| 1D momentum | -15.8% |
| volatility_return_std_20d | 0.130446 |
| BUY Quality | FULL_ALLOCATION_ELIGIBLE |
| Expected Edge | UNCALIBRATED |

PC / PS:

- PC requested normal target weight: `0.035714`
- One-lot fallback expanded final target to `0.244962`
- Strategy cap overshoot was applied but safety hard cap was preserved
- PS quantity delta: `100`
- Runtime intent: `BUY_NEW`

Judgment:

`78780_ENTRY_LOGIC_GAP`

The exact adverse move is not treated as future-known truth, but the BUY-time evidence already contained the Phase30-H risk pattern: strong 20D momentum, short-term reversal, deceleration, elevated exhaustion/reversal, and high volatility. Production Strategy Intelligence represented those risks descriptively, but BUY Quality / PC / PS still converted the symbol into a large one-lot position.

## Entry Quality

10BD BUY_NEW behavior is mixed-to-poor:

- Several winners existed (`70800`, `78590`, `23700`, `89180`).
- Many entries were mixed or weak at BUY time, yet still eligible.
- Large losers include `78780`, `91070`, `36600`, `93180`, `23880`, `37770`, `37820`.
- 78780 is the strongest evidence that overheated/decelerating continuation risk is not sufficiently separated from healthy continuation.

Entry classification for major loss campaigns:

| Symbol | Final PnL | Classification |
| --- | ---: | --- |
| 78780 | -44,000 | BAD_ENTRY_CANDIDATE / ENTRY_LOGIC_GAP |
| 91070 | -6,550 | ADVERSE_MOVE_NOT_CLEARLY_PREDICTABLE, later exited |
| 36600 | -5,200 | BAD_ENTRY_CANDIDATE |
| 93180 | -5,000 | GOOD/MIXED ENTRY LATER DETERIORATED, exited |
| 23880 | -2,300 | BAD_ENTRY_FAST_EXIT |
| 37770 | -2,000 | BAD_ENTRY_FAST_EXIT |
| 37820 | -2,000 | BAD_ENTRY_FAST_EXIT |

## SELL / REDUCE Quality

SELL / REDUCE remained better than entry quality:

- 93180 was reduced then exited.
- 89180 was reduced gradually and closed profitable.
- 70800, 78590, 23700, 89180 were profit-preserved or exited profitably.
- 91070 and 37820 were cut rather than allowed to compound.

Judgment:

`SELL_REDUCE_DIRECTION = IMPROVING`

This does not offset the 78780 entry problem, but it separates the defect: the largest damage came from entry and sizing, not delayed selling.

## 94320 / ADD Quality

94320 path:

```text
200 -> 400 -> 600 -> 800 -> 1000
```

| Date | Semantic | Buy Qty | Price | Trend | Relative | BUY Quality |
| --- | --- | ---: | ---: | --- | --- | --- |
| 2022-08-10 | BUY_NEW | 200 | 149.2 | WEAK | WEAK | REDUCED_ALLOCATION_ONLY |
| 2022-08-19 | BUY_ADD | 200 | 149.1 | WEAK | MIXED | REDUCED_ALLOCATION_ONLY |
| 2022-08-22 | BUY_ADD | 200 | 150.8 | MIXED | MIXED | REDUCED_ALLOCATION_ONLY |
| 2022-08-23 | BUY_ADD | 200 | 151.8 | MIXED | MIXED | REDUCED_ALLOCATION_ONLY |
| 2022-08-24 | BUY_ADD | 200 | 151.1 | SUPPORTIVE | MIXED | REDUCED_ALLOCATION_ONLY |

Final 94320 campaign PnL was `+900 JPY`. The ADD behavior is directionally consistent with concentration into a surviving campaign, but evidence quality is not clearly strong: relative strength was often WEAK/MIXED and BUY Quality stayed reduced, not full.

## Capital Reinvestment

| Date | Sell Notional | BUY_NEW Notional | ADD Notional | Cash | Exposure | PC+ | PS+ | Runtime BUY |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-08-18 | 24,500 | 60,630 | 0 | 794,070 | 19.70% | 10 | 2 | 2 |
| 2022-08-19 | 64,140 | 0 | 29,820 | 828,390 | 16.24% | 9 | 1 | 1 |
| 2022-08-22 | 84,680 | 0 | 30,160 | 882,910 | 10.75% | 11 | 1 | 1 |
| 2022-08-23 | 0 | 32,400 | 30,360 | 820,150 | 16.98% | 10 | 2 | 2 |
| 2022-08-24 | 15,180 | 342,400 | 30,220 | 462,710 | 50.73% | 7 | 3 | 3 |

The system did reinvest capital by 2022-08-24, but most of the reinvested BUY_NEW notional went to 78780. That looks less like high-quality opportunity concentration and more like lot/minimum-notional-constrained capital deployment into an executable candidate.

## Capital Concentration

`CAPITAL_CONCENTRATION_QUALITY = POOR`

Reasons:

- 78780 one-lot fallback converted a normal 3.57% target into 24.5% exposure.
- The one-lot overshoot was within safety hard cap, but risk evidence was elevated.
- ADD into 94320 was profitable but not strongly justified by relative strength.
- Strong HOLD and ADD-worthy separation remains weak.
- Minimum meaningful notional / lot feasibility appears to distort priority and size.

## Winner Preservation

`WINNER_PRESERVATION_DIRECTION = MIXED`

Positive:

- 70800 closed `+2,650`.
- 78590 closed `+1,700`.
- 89180 closed `+1,100`.
- 23700 closed `+1,000`.
- 94320 remained open `+900`.

Mixed:

- Winners were often sold/reduced rather than compounded.
- 94320 was compounded, but only modestly profitable and not consistently high-quality by CQ subdimensions.

## Loss Containment

`LOSS_CONTAINMENT_DIRECTION = MIXED`

SELL/REDUCE behavior remains improving, but loss containment failed at entry/sizing for 78780: a single same-day entry produced most of the 10BD drawdown.

## Close REVIEW_REQUIRED

`CLOSE_REVIEW_OPERATIONAL`

Close evidence:

- `final_runtime_judgment = PASS`
- `accounting_state_judgment = PASS`
- `runtime_execution_judgment = PASS`
- `blocking_reasons = []`
- review reason: `strategy_shadow_review_required_non_blocking`
- PnL reconciliation: PASS

Performance evidence is valid with non-blocking Strategy review. This is not a close Runtime defect.

## Phase30 Thesis Validation

The thesis is only partially reflected in production behavior.

The system does observe continuation quality, downside risk, reversal risk, volatility, and relative strength. But those observations are not yet decisive enough in entry sizing. 78780 shows that "strong continuation" and "overheated/decelerating reversal risk" can both be present, and production still allows a large one-lot BUY_NEW.

Expected Edge remains `UNCALIBRATED` and descriptive, which is correct contractually, but it means the system lacks calibrated payoff asymmetry to reject or resize this kind of entry.

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
ENTRY_QUALITY_DIRECTION = NOT_IMPROVING
SELL_REDUCE_DIRECTION = IMPROVING
WINNER_PRESERVATION_DIRECTION = MIXED
CAPITAL_CONCENTRATION_DIRECTION = NOT_IMPROVING
LOSS_CONTAINMENT_DIRECTION = MIXED
PHASE30_10BD_STRATEGY_DIRECTION = MIXED
```

## Implementation Authorization

`NO_IMPLEMENTATION_AUTHORIZED_BY_PHASE30-U`

## Recommended Next Task

`Phase30-V - Entry Intelligence / Overheated Momentum and One-Lot Capital Concentration Repair Design`

Do not start with threshold tuning. The repair target should first separate:

- healthy continuation vs overheated/decelerating continuation,
- descriptive downside risk vs entry veto / sizing authority,
- one-lot fallback capital concentration vs quality-adjusted sizing.
