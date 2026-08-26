# Phase31-G75 — Post-Peak Profit Retention Causality Audit

## PRIMARY_JUDGMENT

PHASE31_G75_POST_PEAK_RETENTION_CAUSALITY_CONFIRMED

Target run:

`runtime-test-historical-extended-smoke-20260823T140946562431Z`

Audit window:

- ATH baseline: `2023-04-06`
- latest completed day used: `2023-07-19`
- audited post-ATH valuation days: `71`

No code, config, threshold, weight, run state, fresh-run, resume, replay, or
Historical execution was changed or performed. G74 repair was not applied to
this running run.

## Measurement Gate

MEASUREMENT_INTEGRITY = PASS

Evidence basis:

- `daily/<date>/current_valuation_refresh/valuation_projection.json`
- `daily/<date>/execution/fills.json`
- `daily/<date>/execution/realized_slices.json`
- `daily/<date>/strategy/portfolio_policy.json`
- `daily/<date>/strategy/portfolio_construction.json`
- `daily/<date>/strategy/position_sizing.json`
- `daily/<date>/strategy/runtime_planning.json`
- `daily/<date>/strategy/market_context.json`

Valuation status for all 71 audited dates:

- `status = READY`
- `projection_status = PASS`
- `valuation_refresh_precondition_status = PASS`
- temporal authority = `current_valuation_business_date_projection`
- recursive checked Strategy artifact future flags = `0`

Equity basis:

`equity = valuation_projection.cash + valuation_projection.new_total_market_value`

No measurement anomaly was found that blocks Strategy causality characterization.

## Period Summary

| Period | Dates | Equity | PnL | Return | Avg / Median Exposure | BUY fills | SELL fills | Realized GP | Realized GL | PF |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Defensive / drawdown | 2023-04-06 -> 2023-04-25 | 1,906,910 -> 1,609,030 | -297,880 | -15.62% | 46.34% / 43.44% | 23 | 23 | 357,470 | -172,750 | 2.07 |
| Redeployment / recovery | 2023-04-25 -> 2023-05-30 | 1,609,030 -> 1,743,080 | +134,050 | +8.33% | 50.53% / 52.91% | 36 | 29 | 105,130 | -79,800 | 1.32 |
| High-exposure plateau | 2023-05-30 -> 2023-07-19 | 1,743,080 -> 1,671,160 | -71,920 | -4.13% | 70.33% / 74.10% | 61 | 81 | 218,320 | -222,410 | 0.98 |

Post-ATH net result:

- `2023-04-06 equity = 1,906,910`
- `2023-07-19 equity = 1,671,160`
- net from ATH = `-235,750`
- current drawdown from ATH = `-12.36%`

The system did recover from the 2023-04-21 trough but did not retake the
2023-04-06 ATH.

## Period Attribution

### 1. Defensive / Drawdown: 2023-04-06 -> 2023-04-25

Primary character:

ATH giveback and valuation deterioration dominated. The period had positive
realized PnL, but total equity still fell sharply.

- start equity = `1,906,910`
- end equity = `1,609,030`
- period PnL = `-297,880`
- trough = `1,596,740` on `2023-04-21`
- realized gross profit = `357,470`
- realized gross loss = `-172,750`
- realized net = `+184,720`
- implied unrealized / valuation change = `-482,600`
- average cash = `897,508`
- median cash = `941,180`
- exposure range = `12.17%` to `84.21%`
- BUY_NEW runtime plans = `32`
- BUY_ADD runtime plans = `0`
- PM ADD intents = `0`
- SELL_EXIT runtime plans = `22`

Market Quality / Risk Pacing:

- Market Quality: `HEALTHY_EXPANSION 6`, `SHORT_TERM_BREADTH_BREAKDOWN 3`,
  `RECOVERY_CONFIRMATION_INCOMPLETE 3`,
  `SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH 1`
- Risk Pacing: `NORMAL_DEPLOYMENT 6`, `CAUTIOUS_DEPLOYMENT 4`,
  `GRADUAL_REDEPLOYMENT 3`
- valid opportunity dates = `13 / 13`
- security allocation dates = `11 / 13`
- Market Quality hard BUY gate count = `0`

Interpretation:

This was not a clean "Market Quality over-defense stopped buying" period.
The larger effect was post-ATH profit giveback / valuation decline while the
portfolio was still exposed early in the drawdown, followed by exits that raised
cash after damage had already occurred.

### 2. Redeployment / Recovery: 2023-04-25 -> 2023-05-30

Primary character:

Redeployment occurred and produced a partial recovery, but not enough to regain
the ATH.

- start equity = `1,609,030`
- end equity = `1,743,080`
- period PnL = `+134,050`
- peak = `1,743,080` on `2023-05-30`
- realized net = `+25,330`
- implied unrealized / valuation change = `+108,720`
- average exposure = `50.53%`
- median exposure = `52.91%`
- exposure max = `79.23%`
- BUY fills = `36`
- SELL fills = `29`
- BUY_NEW runtime plans = `39`
- BUY_ADD runtime plans = `0`
- PM ADD intents = `0`

Market Quality / Risk Pacing:

- Market Quality: `CONFLICTED_MARKET_STRUCTURE 6`,
  `SHORT_TERM_BREADTH_BREAKDOWN 5`, `RECOVERY_CONFIRMATION_INCOMPLETE 4`,
  `HEALTHY_EXPANSION 3`, `SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH 3`,
  `HEALTHY_RECOVERY 1`
- Risk Pacing: `CAUTIOUS_DEPLOYMENT 14`, `NORMAL_DEPLOYMENT 4`,
  `GRADUAL_REDEPLOYMENT 4`
- valid opportunity dates = `22 / 22`
- security allocation dates = `19 / 22`
- multi-security allocation dates = `10`
- Cash + securities coexistence dates = `19`
- Market Quality hard BUY gate count = `0`

Interpretation:

Capital was redeployed. Recovery was real but incomplete. The evidence does not
support a direct hard-gate suppression theory; it supports a more mundane and
more important finding: redeployed capital did not form enough durable winners
to replace the early April giveback.

### 3. High-Exposure Plateau: 2023-05-30 -> 2023-07-19

Primary character:

Exposure was high, BUY_NEW activity was high, and capital remained active, yet
PF fell to approximately break-even. This is the cleanest evidence that
post-peak stagnation was not caused by lack of deployment alone.

- start equity = `1,743,080`
- end equity = `1,671,160`
- period PnL = `-71,920`
- trough = `1,635,030` on `2023-06-26`
- realized gross profit = `218,320`
- realized gross loss = `-222,410`
- realized net = `-4,090`
- implied unrealized / valuation change = `-67,830`
- average exposure = `70.33%`
- median exposure = `74.10%`
- exposure max = `93.16%`
- BUY fills = `61`
- SELL fills = `81`
- BUY_NEW runtime plans = `102`
- BUY_ADD runtime plans = `1`
- PM ADD intents = `10`

Market Quality / Risk Pacing:

- Market Quality: `SHORT_TERM_BREADTH_BREAKDOWN 10`, `HEALTHY_EXPANSION 10`,
  `RECOVERY_CONFIRMATION_INCOMPLETE 7`, `CONFLICTED_MARKET_STRUCTURE 5`,
  `SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH 3`
- Risk Pacing: `CAUTIOUS_DEPLOYMENT 18`, `NORMAL_DEPLOYMENT 10`,
  `GRADUAL_REDEPLOYMENT 7`
- valid opportunity dates = `35 / 35`
- security allocation dates = `31 / 35`
- multi-security allocation dates = `27`
- Cash + securities coexistence dates = `31`
- strong-stock / cautious-market participation count = `17`
- Market Quality hard BUY gate count = `0`
- candidate rank mutation count = `0`
- Runtime capital-priority redecision count = `0`

Interpretation:

This is candidate / entry quality and profit-retention weakness under active
deployment, not an exposure starvation phase. The system was buying and holding
meaningful exposure, but new capital did not compound.

## Realized Contributor Snapshot

Realized PnL by symbol, from `execution/realized_slices.json`.

### Defensive / Drawdown

Top realized positives:

| Symbol | Realized PnL |
|---:|---:|
| 59350 | +213,200 |
| 67310 | +100,000 |
| 66560 | +23,000 |
| 79970 | +6,300 |
| 69270 | +6,000 |

Top realized negatives:

| Symbol | Realized PnL |
|---:|---:|
| 51890 | -47,750 |
| 60220 | -45,500 |
| 41660 | -38,400 |
| 39610 | -9,600 |
| 77190 | -9,600 |

The period's realized net was positive, so realized exits alone do not explain
the equity drawdown. The gap is valuation/giveback.

### Redeployment / Recovery

Top realized positives:

| Symbol | Realized PnL |
|---:|---:|
| 49370 | +41,200 |
| 72140 | +39,900 |
| 76010 | +5,600 |
| 60160 | +4,530 |
| 14380 | +4,300 |

Top realized negatives:

| Symbol | Realized PnL |
|---:|---:|
| 62310 | -32,700 |
| 44380 | -14,900 |
| 73570 | -7,800 |
| 65620 | -5,900 |
| 61730 | -3,400 |

### High-Exposure Plateau

Top realized positives:

| Symbol | Realized PnL |
|---:|---:|
| 71160 | +44,600 |
| 93410 | +37,900 |
| 40520 | +29,600 |
| 88900 | +28,400 |
| 43950 | +26,600 |

Top realized negatives:

| Symbol | Realized PnL |
|---:|---:|
| 30410 | -38,900 |
| 70330 | -28,000 |
| 36670 | -27,800 |
| 92410 | -27,000 |
| 70460 | -24,500 |

## Churn Characterization

Short-hold approximation used fills by symbol to pair sells with prior buys;
realized PnL comes from canonical `realized_slices`.

| Period | 2-5BD sell count | Net realized PnL | Winners | Losers |
|---|---:|---:|---:|---:|
| Defensive / drawdown | 18 | +21,070 | 9 | 9 |
| Redeployment / recovery | 18 | +50,100 | 5 | 12 |
| High-exposure plateau | 54 | -89,020 | 24 | 28 |

Plateau churn is material locally: many short-hold exits occurred, and the net
effect was negative. However, it is not the only post-peak cause; the ATH gap
was already large before the plateau.

## ADD Characterization

This run predates G74 repair and must not be reinterpreted as if G74 were active.

Post-peak ADD evidence:

- PM ADD intents after 2023-04-06 = `10`
- Runtime BUY_ADD plans after 2023-04-06 = `1`
- BUY_ADD fills after 2023-04-06 = `1`
- 2023-05-31 `30410` was the single successful ADD path.
- Repeated 2023-06 `40520` ADD intents remained upstream zero-delta /
  fail-closed before PS/Runtime.

ADD_UNDERUTILIZATION_MATERIAL = UNPROVEN

Reason:

ADD underuse is structurally visible and likely relevant to winner amplification,
but this READ-ONLY audit cannot assign counterfactual PnL to unexecuted ADDs.
G74 should be validated only in a separate fresh-run after the current run
completes.

## Causal Answers

MARKET_QUALITY_OVER_DEFENSE = NO

Evidence:

- Market Quality hard BUY gate count = `0`
- valid opportunity dates were present throughout all post-ATH periods
- security allocations continued on most dates
- strong-stock / cautious-market participation occurred in the plateau
- Runtime capital-priority redecision count = `0`

REDEPLOYMENT_OCCURRED = YES

Evidence:

- redeployment/recovery BUY fills = `36`
- plateau BUY fills = `61`
- median exposure rose from `52.91%` in recovery to `74.10%` in plateau
- plateau max exposure reached `93.16%`

REDEPLOYMENT_EFFECTIVE = NO

Reason:

Redeployment recovered part of the drawdown but did not recover the ATH, and the
subsequent high-exposure period produced `-71,920` with realized PF `0.98`.

CANDIDATE_QUALITY_DETERIORATION = YES

Reason:

The plateau had high exposure, 61 BUY fills, 102 BUY_NEW runtime plans, 31/35
security-allocation dates, and no Market Quality hard gate, yet net PnL was
negative. That points to post-peak entry / candidate follow-through quality.

SHORT_HOLD_CHURN_MATERIAL = YES

Reason:

Plateau 2-5BD realized churn contributed `-89,020` and 54 short-hold sell
events. It is a material secondary cause.

WINNER_RETENTION_FAILURE_MATERIAL = YES

Reason:

The defensive period had positive realized net PnL but total equity fell
`-297,880`; the implied valuation/giveback component was approximately
`-482,600`. This is the largest single post-ATH damage bucket.

ADD_UNDERUTILIZATION_MATERIAL = UNPROVEN

Reason:

ADD underutilization is visible, but exact PnL materiality requires a later
fresh-run with G74 active.

CONCENTRATED_LOSER_EFFECT_MATERIAL = YES

Reason:

Concentrated realized losers were present in every phase, especially plateau
symbols `30410`, `70330`, `36670`, `92410`, and `70460`. These were not large
enough alone to explain the entire ATH gap, but they explain why high exposure
did not compound.

## Top 5 Causes

1. ATH giveback / valuation deterioration immediately after 2023-04-06:
   `-297,880` equity impact through 2023-04-25, despite `+184,720` realized net.
   The implied valuation/giveback bucket is approximately `-482,600`.

2. High-exposure redeployment failed to compound:
   2023-05-30 -> 2023-07-19 had median exposure `74.10%`, 61 BUY fills, and
   102 BUY_NEW runtime plans, but equity fell `-71,920` and realized PF was
   `0.98`.

3. Candidate / entry follow-through deterioration:
   valid opportunity and security-allocation dates remained high, but realized
   winners and losers nearly offset in plateau; this is not explained by
   Market Quality gating.

4. Short-hold churn in the plateau:
   54 approximate 2-5BD sell events with `-89,020` realized net.

5. ADD underutilization in the pre-G74 run:
   only 10 PM ADD intents and 1 Runtime BUY_ADD post-ATH. Materiality is
   unproven without a separate G74-active fresh-run, but it is the clearest
   structural amplification weakness.

## Required Judgment

POST_PEAK_PRIMARY_CAUSE =
ATH_GIVEBACK_AND_VALUATION_DETERIORATION_FOLLOWED_BY_INEFFECTIVE_REDEPLOYMENT

POST_PEAK_SECONDARY_CAUSES =
CANDIDATE_ENTRY_FOLLOW_THROUGH_WEAKNESS,
SHORT_HOLD_CHURN,
CONCENTRATED_LOSER_EFFECT,
PRE_G74_ADD_UNDERUTILIZATION_STRUCTURAL_WEAKNESS

MARKET_QUALITY_OVER_DEFENSE = NO

REDEPLOYMENT_OCCURRED = YES

REDEPLOYMENT_EFFECTIVE = NO

CANDIDATE_QUALITY_DETERIORATION = YES

SHORT_HOLD_CHURN_MATERIAL = YES

WINNER_RETENTION_FAILURE_MATERIAL = YES

ADD_UNDERUTILIZATION_MATERIAL = UNPROVEN

CONCENTRATED_LOSER_EFFECT_MATERIAL = YES

MEASUREMENT_INTEGRITY = PASS

CODE_CHANGED = NO

RUN_MODIFIED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

MARKET_QUALITY_CHANGED = NO

THRESHOLD_WEIGHT_TUNING = NO

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0

## Highest-Value Next Investigation

Investigate post-peak BUY_NEW entry quality and early-failure mechanics in the
high-exposure plateau, especially why many valid allocated opportunities from
2023-05-30 onward became short-hold exits or offsetting realized losers despite
Market Quality not acting as a hard BUY gate.
