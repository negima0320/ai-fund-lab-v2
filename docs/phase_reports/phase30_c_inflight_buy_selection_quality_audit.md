# Phase30-C In-Flight BUY Selection Quality Audit

Primary Judgment:

```text
PHASE30_C_INFLIGHT_BUY_SELECTION_AUDIT_PRELIMINARY_STOCK_SELECTION_AND_EVENT_RISK_GAPS_FOUND_HOLD_SELL_SEPARATION_REQUIRED
```

Task ID: `Phase30-C`

Status:

```text
COMPLETE
READ-ONLY IN-FLIGHT AUDIT
NO TARGET RUN MUTATION
NO STRATEGY / RUNTIME / CONFIG / MODEL / THRESHOLD CHANGE
NO STOP / RESUME / CLOSE / REPAIR OF RUNNING HISTORICAL
NO IMPLEMENTATION AUTHORIZED
```

## Audit Boundary

Target run:

```text
runtime-test-historical-extended-smoke-20260815T061857447380Z
```

Authoritative audit snapshot:

```text
run_state.status: RUNNING
latest_authoritative_completed_date: 2023-04-05
completed_business_days: 160
latest snapshot equity: 1,166,620 JPY
latest snapshot cash: 310,220 JPY
latest snapshot market value: 856,400 JPY
latest snapshot exposure: 73.41%
```

`daily/2023-03-31` and later artifacts may exist while the run is in flight.
This audit uses only dates in `run_state.completed_business_days` at the
snapshot time. The running run was not stopped, resumed, closed, repaired, or
written to.

Machine-readable evidence:

```text
reports/phase_reports/phase30_c_inflight_buy_selection_quality_audit.json
```

## Evidence Classes

This audit separates:

```text
A. PIT Runtime Evidence
   Runtime artifacts available on or before the BUY date.

B. External Contemporaneous Evidence
   Public information available at the time but not proven Runtime input.

C. Future Outcome Attribution
   Post-BUY outcome used only for attribution, not as decision-time input.
```

## BUY Inventory

Completed-window BUY inventory:

```text
BUY fills: 137
BUY_NEW: 74
BUY_ADD: 16
REENTRY: 47
unique BUY symbols: 74
total BUY notional: 5,560,900 JPY
```

Semantics are taken from campaign events where available. A new campaign for a
previously traded symbol is classified as `REENTRY`.

## Objective Selection Quality

### Momentum Quality

The strongest separator observed is not the BUY Quality score itself; it is
the trajectory classification and volatility context.

```text
Winner campaigns > +10,000 JPY:
  count: 3
  trajectory: HEALTHY_CONTINUATION 1, MIXED_OR_UNRESOLVED 2
  avg quality score: 0.736945
  avg opportunity rank: 6.67

Loser campaigns < -10,000 JPY:
  count: 5
  trajectory: MIXED_OR_UNRESOLVED 5
  avg quality score: 0.754535
  avg opportunity rank: 5.00

Immediate adverse campaigns:
  count: 4
  trajectory: MIXED_OR_UNRESOLVED 3, HEALTHY_CONTINUATION 1
  avg quality score: 0.756400
```

Interpretation:

```text
BUY Quality score and rank did not separate winners from losers.
MIXED_OR_UNRESOLVED trajectory appears overrepresented among losers.
```

### Entry Timing

Several losses were not simply "bad companies." They were buys after very
large prior moves where PIT evidence already showed deceleration or unresolved
trajectory. `78780` is the clearest example.

### Liquidity / Microstructure

The clearest structural weakness is repeated very-low-price exposure:

```text
93180: 2-6 JPY price level, 100-share lot notional 200-600 JPY
37770: 28 JPY
21640: 65.8 JPY
33580: 85.8 JPY
37820: 78-83 JPY
```

These were technically tradable, but structurally poor for a 1M JPY portfolio:
high tick sensitivity, large share quantities, and fragile price increments.
This is not a recommendation for an arbitrary new minimum price; it is evidence
that current Runtime quality semantics underweight low-price microstructure.

### Corporate / Event Risk

Runtime PIT listed-info for `93180` contained:

```text
CoName: アジア開発キャピタル
Market: スタンダード
current_listed: true
```

It did not prove consumption of special-alert / supervision / delisting-risk
state.

External public contemporaneous evidence shows that JPX had designated 9318 as
a security on alert on 2021-08-07, before all observed Phase30-C `93180` BUYs.
JPX later continued the designation on 2022-09-28, designated the issue as
supervision under examination on 2023-02-07, and decided delisting on
2023-03-29. These later events are not decision-time evidence for earlier
BUYs, but the original alert designation was already public before the
2022-08-10 first BUY.

Source URLs:

```text
https://www.jpx.co.jp/news/1023/20210806-12.html
https://www.jpx.co.jp/news/1023/20220928-12.html
https://www.jpx.co.jp/news/1023/20230206-11.html
https://www.jpx.co.jp/news/1023/20230329-11.html
```

This is a real research/design gap:

```text
AVAILABLE_PUBLICLY_AT_THE_TIME_BUT_NOT_PROVEN_RUNTIME_INPUT
```

## Worst Selection Candidates

Ranked by PIT concern, not by eventual loss:

| Rank | Symbol | Company | Date | PIT concern | Outcome |
| ---: | --- | --- | --- | --- | ---: |
| 1 | 93180 | アジア開発キャピタル | 2023-02-06 | public alert gap, 3 JPY, mixed momentum, high vol | -9,000 |
| 2 | 93180 | アジア開発キャピタル | 2022-08-10 | public alert gap, 6 JPY, mixed momentum, high vol | -5,000 |
| 3 | 93180 | アジア開発キャピタル | 2022-09-26 | public alert gap, 5 JPY, mixed momentum, high vol | -4,300 |
| 4 | 93180 | アジア開発キャピタル | 2023-02-16 | public alert gap, 2 JPY, mixed momentum, high vol, ADD followed | -4,100 |
| 5 | 37770 | FHTホールディングス | 2022-08-18 | 28 JPY, mixed momentum, high vol, rank 23 | -2,000 |
| 6 | 21640 | 地域新聞社 | 2022-09-13 | 65.8 JPY, mixed momentum, high vol, rank 19 | -1,050 |
| 7 | 33580 | ワイエスフード | 2022-10-13 | 85.8 JPY, mixed momentum, high vol | -2,160 |
| 8 | 37820 | ディー・ディー・エス | 2022-08-15 | 78 JPY, mixed momentum, high vol | -2,000 |

`93180` dominates the objective selection-quality concern because it combines
public event/listing risk, very low price, repeated REENTRY, and high volatility.

## Reasonable Entries That Later Failed

Some losses were less clearly bad stock selection:

| Symbol | Company | Entry | PIT profile | Outcome |
| --- | --- | --- | --- | ---: |
| 42640 | セキュア | 2023-02-21 | HIGH quality, rank 4, mixed trajectory | -16,800 |
| 92540 | ラバブルマーケティンググループ | 2022-10-14 | HIGH quality, rank 7, mixed trajectory | -16,500 |
| 78860 | ヤマト・インダストリー | 2022-11-07 | HIGH quality, rank 8, mixed trajectory | -13,800 |

These are not proven "bad companies" from PIT evidence. They look more like
momentum-entry / adverse-move cases, with HOLD/SELL follow-up still needing
separate evaluation.

## 93180 Deep Dive

Identity:

```text
Code: 93180 / 9318
Company: アジア開発キャピタル
English: Asia Development Capital Co.Ltd.
Market in Runtime listed-info: スタンダード
```

Campaigns through `2023-04-05`:

```text
campaigns: 10
BUY/ADD events: 12
REENTRY campaigns: 9
ADD events: 2
total deployed notional: 302,700 JPY
max quantity in a campaign: 16,400 shares
realized PnL total: -11,700 JPY
best campaign: +7,100 JPY
worst campaign: -9,000 JPY
```

Runtime knew:

```text
current_listed: true
market: スタンダード
very low price: 2-6 JPY
trajectory often MIXED_OR_UNRESOLVED
quality scores often HIGH / FULL or REDUCED allocation eligible
```

Runtime did not prove it consumed:

```text
JPX security-on-alert state
special caution / alert designation
supervision designation risk
delisting risk path
```

Conclusion:

```text
93180 is the strongest EVENT_RISK_CANDIDATE and BAD_ENTRY_CANDIDATE.
The earliest public alert designation predates the first observed BUY.
This is not hindsight from the 2023 delisting; the material public-risk signal
already existed at the time of the 2022 BUYs.
```

## 78780 Deep Dive

Identity:

```text
Code: 78780 / 7878
Company: 光・彩
English: Kohsai Co.,Ltd.
Market in Runtime listed-info: スタンダード
```

BUY:

```text
date: 2022-08-24
quantity: 100
price: 2,860
notional: 286,000 JPY
campaign PnL: -16,000 JPY
MAE: -44,000 JPY
exit: 2022-08-25 at 2,700 JPY
```

PIT Runtime evidence:

```text
quality_action: FULL_ALLOCATION_ELIGIBLE
quality_score: 0.777044
quality_band: HIGH
opportunity_rank: 3
trajectory: MIXED_OR_UNRESOLVED
trajectory_status: PASS_WITH_REDUCTION
1D momentum: -15.75%
3D momentum: +4.42%
5D momentum: +42.98%
10D momentum: +81.27%
20D momentum: +228.00%
1D-vs-5D delta: -58.74pp
5D-vs-20D delta: -185.02pp
20D volatility: 13.04%
rolling median traded value 20D: 510.2M JPY
```

External public scan found a July 2022 shareholder-benefit abolition notice, but
no JPX supervision / alert / delisting-risk source was found for `7878` in the
same way as `9318`.

Conclusion:

```text
78780 was not primarily an event-risk failure from available evidence.
It was an entry-timing / overheated-momentum failure candidate: very strong
20D/10D/5D momentum but negative 1D momentum and large deceleration were already
visible PIT. Runtime classified trajectory as MIXED_OR_UNRESOLVED yet still
allowed FULL allocation because the momentum trajectory component had zero
weight in the BUY Quality score.
```

## Winner vs Loser Comparison

What appears different:

```text
Losers were all MIXED_OR_UNRESOLVED at Entry.
Immediate adverse cases were mostly MIXED_OR_UNRESOLVED.
Very-low-price names appear in worst PIT risk cases.
Public event risk is concentrated in 93180.
```

What does not separate:

```text
BUY Quality score does not separate winners from losers.
All material winner and loser cohorts were quality_band HIGH.
Opportunity rank does not separate winners from losers; losers had better
average rank than winners in this snapshot.
```

This suggests that relative model rank and aggregate BUY Quality score are
insufficient as standalone stock-selection quality controls.

## Entry vs HOLD / SELL Diagnosis

Campaign classification counts:

```text
BAD_ENTRY_CANDIDATE: 46
ADVERSE_MOVE_NOT_CLEARLY_PREDICTABLE: 43
NO_MAJOR_DEFECT_SIGNAL: 26
GOOD_ENTRY_POOR_PROFIT_RETENTION: 6
ADD_TIMING_CANDIDATE: 2
EVENT_RISK_CANDIDATE: 10
```

Interpretation:

```text
Stock-selection quality is a real issue, but not the only issue.
There is also meaningful evidence of profit-retention / HOLD-SELL timing
questions, especially where MFE was positive and later surrendered.
```

Strong MFE giveback examples:

| Symbol | Company | MFE | Final PnL | Giveback |
| --- | --- | ---: | ---: | ---: |
| 83060 | 三菱UFJFG | 42,740 | 15,280 | 27,460 |
| 47600 | アルファ | 29,700 | 5,400 | 24,300 |
| 99840 | ソフトバンクG | 25,480 | 2,650 | 22,830 |
| 42630 | サスメド | 15,700 | 4,700 | 11,000 |

These are not primarily bad-stock examples. They point to HOLD/SELL/profit
retention review.

## Exposure Context

High exposure alone is not judged defective. The relevant question is whether
incremental exposure was deployed into strong opportunities.

At the audit snapshot the run had recovered from the user-observed March drawdown:

```text
2023-03-23 user-observed equity: 899,090 JPY
2023-04-05 authoritative snapshot equity: 1,166,620 JPY
```

This reinforces why Phase30-C must not stop the run due to in-flight weakness.
The audit found stock-selection concerns, but the same incomplete run later
showed a large recovery.

## External Contemporaneous Risk Gap

Runtime actually consumed:

```text
J-Quants listed issue identity / market / current_listed
technical features
opportunity rank / uncalibrated relative score
Buy Quality
Portfolio fit
liquidity proxy
Market Context
Corporate Event artifact
```

Public information available at the time but not proven Runtime input:

```text
9318 JPX security-on-alert designation from 2021-08-07
```

Future information:

```text
2023-02-07 supervision designation for 9318
2023-03-29 delisting decision for 9318
post-BUY campaign PnL / MFE / MAE
```

The public-information gap should be treated as a Phase30 research/design gap,
not as an automatic Runtime defect and not as authorization to change Strategy.

## Phase30 Implications

Evidence ranking:

1. Corporate/Event eligibility problem: strong for `93180`.
2. Entry timing problem: strong for `78780` and mixed-trajectory losers.
3. Stock-selection quality problem: moderate-to-strong, concentrated in low-price / event-risk / mixed-momentum names.
4. HOLD/SELL timing problem: moderate, especially MFE giveback cohort.
5. ADD timing problem: limited but real, mainly `93180` repeated ADD/REENTRY.
6. Capital allocation problem: moderate; some large notional went into mixed trajectory names, but high exposure alone is not proven defective.

## Implementation Authorization

```text
NO IMPLEMENTATION AUTHORIZED BY PHASE30-C
```

## Recommended Next Step

```text
CONTINUE CURRENT 977BD RUN
```

Do not stop the run merely because this audit found Strategy weaknesses. The
next research step should be read-only: after the run finishes, evaluate whether
the same stock-selection / event-risk / entry-timing signals persist across the
full 977BD baseline.
