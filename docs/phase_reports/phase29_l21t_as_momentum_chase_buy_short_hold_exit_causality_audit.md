# Phase29-L21T-AS - Momentum Chase BUY / Short-Hold Exit Causality Audit

## Primary Judgment

`MULTI_CAUSAL_ENTRY_EXIT_QUALITY_GAP_CONFIRMED`

This was a read-only Phase29 audit.  Phase30 was not entered.

The anchor cases do not prove a simple rule that the Strategy always buys the
highest short-term momentum names and immediately exits them because momentum
decays.  They do show a multi-causal entry/exit quality gap:

- `78780` and `53800` had extreme long-lookback momentum before entry.
- `78780 2022-08-24` had very high 5BD and 20BD pre-entry momentum, but its
  1BD momentum had already turned down.
- `78780 2022-08-31` and `53800 2022-09-06` were not short-term momentum highs;
  both had negative 1BD/3BD/5BD pre-entry momentum but remained extreme 20BD
  momentum names.
- All three exited after one completed business day by PM `EXIT` with
  `hard_stop_current_return`, not by a direct `momentum_decay` reason.
- `78780` also has the AQ execution-price / Safety-basis gap: fill price was
  materially above the reference close used by sizing authority.

## Scope

| Field | Value |
| --- | --- |
| Task ID | `Phase29-L21T-AS` |
| Target Run | `runtime-test-historical-extended-smoke-20260814T054658313415Z` |
| Available sample | `72` filled actual `BUY_NEW` entries |
| Runtime mutation | `NO` |
| Strategy / Runtime / Config / Model / Threshold changed | `NO` |
| fresh-run / resume / replay / recovery / long Historical | `NO` |

The sample is filled actual `BUY_NEW` rows with positive `actual_notional`,
using AO per-entry evidence plus read-only Runtime evidence.

## Anchor Cases

### 78780 / 2022-08-24

| Field | Value |
| --- | ---: |
| reference price | `2,420` |
| fill price | `2,860` |
| previous close | `2,872.5` |
| gap previous close to fill | `-0.435%` |
| fill vs reference close | `+18.182%` |
| pre-entry 1BD return | `-15.753%` |
| pre-entry 3BD return | `+4.423%` |
| pre-entry 5BD return | `+42.984%` |
| pre-entry 10BD return | `+81.273%` |
| pre-entry 20BD return | `+228.002%` |
| volume momentum vs prior 5BD avg | `-16.279%` |
| realized return | `-5.594%` |
| forward 5BD / 10BD / 20BD | `-5.579% / -5.888% / -19.731%` |

Same-day candidate percentiles:

```text
1BD return: 2.4th percentile
5BD return: 97.6th percentile
20BD return: 100th percentile
gap previous close to fill: 28.6th percentile
volume momentum: 61.9th percentile
```

Interpretation:

```text
Long-lookback momentum chase / late-entry risk: YES
Previous-close-to-fill gap chase: NO
Reference-to-fill authority gap: YES
```

The `2,420 -> 2,860` difference is not a previous-close gap.  It is the
difference between the same-day reference close and the fill/open-area price.
Even if bought near `2,420`, the 5BD and 20BD forward returns from the reference
close were negative, so the issue is not only fill price.  It is entry timing /
selection plus execution-price deviation.

Exit:

```text
holding_days = 1
exit_action = EXIT
exit_reason = hard_stop_current_return|profit_retention_break
dominant_cause = EXIT_BY_HARD_STOP
gross_realized_pnl = -16,000
```

### 78780 / 2022-08-31

| Field | Value |
| --- | ---: |
| reference price | `2,285` |
| fill price | `2,525` |
| previous close | `2,487.5` |
| gap previous close to fill | `+1.508%` |
| fill vs reference close | `+10.503%` |
| pre-entry 1BD return | `-8.141%` |
| pre-entry 3BD return | `-23.770%` |
| pre-entry 5BD return | `-5.579%` |
| pre-entry 10BD return | `+35.007%` |
| pre-entry 20BD return | `+135.567%` |
| volume momentum vs prior 5BD avg | `-63.315%` |
| realized return | `-9.505%` |
| forward 5BD / 10BD / 20BD | `-0.328% / +1.969% / -33.479%` |

Same-day candidate percentiles:

```text
1BD return: 9.8th percentile
3BD return: 2.4th percentile
5BD return: 24.4th percentile
20BD return: 100th percentile
gap previous close to fill: 73.2nd percentile
volume momentum: 24.4th percentile
```

This was a separate `BUY_NEW` campaign, not ADD.  The immediate short-term
momentum was already weak, while 20BD momentum remained extreme.  The most
likely issue is late entry into a fading prior winner, with execution price
above reference worsening the outcome.

Exit:

```text
holding_days = 1
exit_action = EXIT
exit_reason = hard_stop_current_return
dominant_cause = EXIT_BY_HARD_STOP
gross_realized_pnl = -24,000
```

### 53800 / 2022-09-06

| Field | Value |
| --- | ---: |
| reference price | `2,020` |
| fill price | `2,250` |
| previous close | `2,272.5` |
| gap previous close to fill | `-0.990%` |
| fill vs reference close | `+11.386%` |
| pre-entry 1BD return | `-11.111%` |
| pre-entry 3BD return | `-20.000%` |
| pre-entry 5BD return | `-29.861%` |
| pre-entry 10BD return | `-23.048%` |
| pre-entry 20BD return | `+87.037%` |
| volume momentum vs prior 5BD avg | `-56.944%` |
| realized return | `-5.556%` |
| forward 5BD / 10BD / 20BD | `-4.084% / -21.782% / -34.777%` |

Same-day candidate percentiles:

```text
1BD return: 4.7th percentile
3BD return: 2.3rd percentile
5BD return: 2.3rd percentile
20BD return: 97.6th percentile
gap previous close to fill: 53.5th percentile
volume momentum: 44.2nd percentile
```

This is not a short-term momentum chase at entry.  It is more consistent with
buying a long-lookback prior winner after short-term deterioration had already
started.

Exit:

```text
holding_days = 1
exit_action = EXIT
exit_reason = hard_stop_current_return
dominant_cause = EXIT_BY_HARD_STOP
gross_realized_pnl = -12,500
```

## Run-Level Momentum Groups

### Pre-Entry 5BD Momentum Terciles

| Group | Sample | Avg 5BD Pre | Avg Holding Days | Exit <=1BD | Exit <=3BD | Realized Return | Fwd 5BD | Fwd 10BD | Fwd 20BD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| HIGH | `23` | `+24.986%` | `3.32` | `21.739%` | `60.870%` | `-4.624%` | `-4.054%` | `-8.916%` | `-11.907%` |
| MID | `24` | `-0.033%` | `4.14` | `20.833%` | `33.333%` | `-0.383%` | `-2.120%` | `+0.472%` | `-1.486%` |
| LOW | `25` | `-11.372%` | `2.96` | `52.000%` | `64.000%` | `-5.314%` | `-4.678%` | `-4.974%` | `-5.765%` |

Pre-5BD high momentum does not have the highest 1BD exit rate.  It does have
the worst average 20BD forward return among the three terciles.

### Entry Gap Terciles

| Group | Sample | Avg Gap | Avg Holding Days | Exit <=1BD | Exit <=3BD | Realized Return | Fwd 20BD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| HIGH | `23` | `+11.398%` | `2.67` | `43.478%` | `73.913%` | `-6.884%` | `-11.680%` |
| MID | `24` | `+0.133%` | `3.06` | `33.333%` | `54.167%` | `-0.335%` | `-2.527%` |
| LOW | `25` | `-1.632%` | `4.50` | `20.000%` | `32.000%` | `-3.897%` | `-4.974%` |

The gap result is stronger than the 5BD momentum result: high entry-gap entries
show higher short-exit rates and worse forward returns.

## Hypotheses

| Hypothesis | Judgment |
| --- | --- |
| H1: high momentum has higher short-EXIT rate | `MIXED`; not true for 5BD, more visible for 3BD/gap |
| H2: high momentum has worse forward return | `SUPPORTED` for 5BD/20BD/gap groups |
| H3: high momentum is fine but Exit is too early | `NOT_PRIMARY` |
| H4: Entry/Exit momentum churn | `PARTIAL`; anchors exit by hard stop, gap/pre3 groups show churn-like behavior |
| H5: Entry selection overall weak | `SUPPORTED` in this partial filled sample |

## Causality Separation

| Cause | Evidence |
| --- | --- |
| Selection weakness | `YES`, especially long-lookback prior winners after short-term deterioration |
| Late entry | `YES` for anchors |
| Execution fill high | `YES` for `78780`; AQ already confirmed Safety basis gap |
| Exit too early | `INSUFFICIENT`; anchors exited after hard-stop losses |
| Re-entry / campaign churn | `YES` for `78780` separate new campaign one week later |
| Sizing | `YES`, AQ showed high-notional one-lot concentration boundary gap |

## Artifacts

```text
reports/phase29_l21t_as_momentum_chase_buy_short_hold_exit_causality_audit/summary.json
reports/phase29_l21t_as_momentum_chase_buy_short_hold_exit_causality_audit/per_entry.csv
reports/phase29_l21t_as_momentum_chase_buy_short_hold_exit_causality_audit/group_summary.csv
```

## Next Step

Do not implement a new momentum exclusion gate from this audit.

Recommended separate work:

```text
1. Repair/design execution-price Safety boundary from AQ.
2. After the post-AM long-horizon run completes, perform Strategy research on
   late-entry prior-winner risk, entry-gap risk, and re-entry churn.
```
