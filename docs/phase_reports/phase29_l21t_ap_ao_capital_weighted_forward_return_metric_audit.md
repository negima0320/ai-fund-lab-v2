# Phase29-L21T-AP - AO Capital-Weighted Forward Return Metric Audit

## Primary Judgment

`METRIC_DEFINITION_OR_NORMALIZATION_PROBLEM_CONFIRMED`

The reported AO capital-weighted arithmetic is reproducible, and the group
denominator is normalized correctly for rows with positive `actual_notional`.
However, AO's `actual_buy_new` sample and equal-weight mean include planned-only
rows with missing `actual_notional`, while the capital-weighted metric gives
those rows zero effective weight.  Therefore the AO table compares different
effective populations and its interpretation needs correction.

This was a read-only Phase29 audit.  Phase30 was not entered.

## Scope

| Field | Value |
| --- | --- |
| Task ID | `Phase29-L21T-AP` |
| Runtime mutation | `NO` |
| Strategy / Runtime / Config / Model / Threshold changed | `NO` |
| fresh-run / resume / replay / recovery / long Historical | `NO` |
| AO script changed | `NO` |

## Formula

AO calculates capital-weighted forward return as:

```text
sum(actual_notional_i * return_horizon_i) / sum(actual_notional_i)
```

within each group.

For the reported `20BD` values:

```text
FULL    = -306,810.9388033241 / 2,789,740.0 = -10.997832730050977%
REDUCED =  -16,597.6889884619 /   408,180.0 =  -4.066267085222671%
```

Weight source is `actual_notional`, sourced from AO `per_entry.csv`
`actual_notional`, which is the execution fill gross notional.  It is not
`requested_weight`, `accepted_weight`, `lot_aware_target_weight`, or
`target_weight`.

Group normalization is `YES`: each group is normalized by that group's total
positive actual notional.  It is not normalized by whole-portfolio equity or
global portfolio notional.

## Reproduction

| Group | AO Sample | Positive Actual Notional Rows | Missing/Zero Notional Rows | Mean 20BD, AO Sample | Mean 20BD, Positive-Notional Only | Capital-Weighted 20BD |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| FULL | `64` | `41` | `23` | `+2.303%` | `-7.456%` | `-10.998%` |
| REDUCED | `35` | `31` | `4` | `+5.961%` | `-4.772%` | `-4.066%` |

This explains the apparent contradiction.  The positive equal-weight means are
not driven simply by sample count.  They are materially affected by rows that
AO labels `actual_buy_new=True` because planned quantity was positive, but that
have no fill notional and therefore zero capital-weight.

## Allocation Quality Signal

For positive actual-notional rows only, large allocation to poor performers is
supported, but only with qualification:

| Group | Negative Rows | Negative Notional Share | Negative Contribution | Positive Contribution | Net Capital-Weighted 20BD |
| --- | ---: | ---: | ---: | ---: | ---: |
| FULL | `29` | `75.034%` | `-13.402%` | `+2.404%` | `-10.998%` |
| REDUCED | `13` | `38.628%` | `-6.240%` | `+2.174%` | `-4.066%` |

So the statement "larger capital was allocated to worse performers" is a
qualified yes for the filled subset.  It should not be inferred from the AO
mean-vs-capital-weighted comparison as originally presented.

## Top FULL Loss Contributors

| Date | Symbol | Actual Notional | 20BD Return | Forward PnL Proxy | Group Contribution |
| --- | --- | ---: | ---: | ---: | ---: |
| `2022-08-31` | `78780` | `252,500` | `-33.479%` | `-84,535.01` | `-3.030%` |
| `2022-09-06` | `53800` | `225,000` | `-34.777%` | `-78,248.76` | `-2.805%` |
| `2022-08-24` | `78780` | `286,000` | `-19.731%` | `-56,431.82` | `-2.023%` |
| `2022-10-13` | `92540` | `178,200` | `-14.706%` | `-26,205.88` | `-0.939%` |
| `2022-09-05` | `41650` | `73,000` | `-28.831%` | `-21,046.75` | `-0.754%` |

## Top REDUCED Loss Contributors

| Date | Symbol | Actual Notional | 20BD Return | Forward PnL Proxy | Group Contribution |
| --- | --- | ---: | ---: | ---: | ---: |
| `2022-09-06` | `37820` | `23,000` | `-16.484%` | `-3,791.21` | `-0.929%` |
| `2022-08-10` | `23880` | `16,900` | `-19.205%` | `-3,245.70` | `-0.795%` |
| `2022-08-31` | `67860` | `10,200` | `-25.490%` | `-2,600.00` | `-0.637%` |
| `2022-10-11` | `33580` | `7,120` | `-36.161%` | `-2,574.64` | `-0.631%` |
| `2022-09-08` | `67860` | `9,900` | `-24.752%` | `-2,450.50` | `-0.600%` |

## Duplicate Entry Handling

AO treats each `business_date x symbol` event as a separate entry.  The same
symbol can appear multiple times across dates, and those entries are not
deduplicated by symbol.

This is valid if the metric is "entry-event attribution."  It is misleading if
read as unique-symbol attribution.

## Portfolio Interpretation

The AO capital-weighted value is not a portfolio return and not a portfolio
contribution to total equity.  It is a group-normalized, post-hoc, filled-entry
return proxy:

```text
group forward PnL proxy / group actual filled notional
```

It ignores non-group capital, cash, subsequent realized trading, rebalancing,
SELL/REDUCE activity, Current equity path, and overlap between repeated entries.

## Bug / Naming Assessment

| Check | Judgment |
| --- | --- |
| Calculation bug | `NO` for reported capital-weighted arithmetic |
| Denominator bug | `NO` for positive-notional rows |
| Normalization bug | `NO` for group denominator; `YES/DEFINITION` for mixed sample vs zero-weight rows |
| Duplicate counting | `NO` if entry-event attribution; misleading if unique-symbol attribution |
| Metric naming | `MISLEADING` |
| AO report interpretation | `NEEDS_CORRECTION` |

## Artifacts

```text
reports/phase29_l21t_ap_ao_capital_weighted_forward_return_metric_audit/summary.json
reports/phase29_l21t_ap_ao_capital_weighted_forward_return_metric_audit/top_contributors.csv
```

## Required Answers

| Field | Answer |
| --- | --- |
| Capital-weighted formula | `sum(actual_notional * return_20bd) / sum(actual_notional)` |
| Weight source | `actual_notional` / fill gross notional |
| Group normalization | `YES` |
| Sample-count dependency | sample count affects equal-weight mean; capital-weighted result depends on notional distribution |
| Duplicate-entry handling | same symbol across dates is counted as separate entry events |
| FULL capital-weighted 20BD | `-10.997832730050977%` |
| REDUCED capital-weighted 20BD | `-4.066267085222671%` |
| Metric calculation correct | `YES` for arithmetic |
| Metric naming correct | `NO` |
| Portfolio returnとして解釈可能 | `NO` |
| Large allocation to poor performers confirmed | `QUALIFIED YES` for filled subset |
| AO interpretation needs correction | `YES` |
| Separate repair required | `YES`, if AO artifacts/report are reused as canonical evidence |

## Next Action

Create a separate follow-up only if AO outputs are to be reused canonically:

```text
AO actual-entry definition and metric naming correction:
- split planned-only BUY_NEW rows from filled BUY_NEW rows;
- report filled-only equal-weight mean alongside capital-weighted return;
- rename capital-weighted metric to group-normalized filled-notional-weighted forward return;
- optionally add unique-symbol attribution as a separate view.
```
