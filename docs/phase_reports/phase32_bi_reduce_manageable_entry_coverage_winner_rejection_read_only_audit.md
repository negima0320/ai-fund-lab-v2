# Phase32-BI — REDUCE-Manageable Entry Coverage / Winner Rejection READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260831T003243720082Z`
- Snapshot used for aggregate analysis: completed valuation evidence through `2024-04-26`
- Completed valuation days in aggregate snapshot: `386`, from `2022-10-03` through `2024-04-26`
- Source commit recorded by run plan: `ff1d23157cced619c5820898f8317a7440e6092c`

This phase is READ-ONLY. No code, config, model, threshold, runtime state, Pending, Ledger, recovery, replay, resume, fresh-run, shadow behavior, or Production behavior was executed or changed.

The target run was still running while this audit was performed. Aggregate counts are tied to the snapshot above and intentionally not updated after that point.

## Definition

The proposed rule under test is:

`if REDUCE_UNMANAGEABLE_AT_ENTRY then BUY_WAIT`

For this audit:

- `REDUCE_MANAGEABLE`: actual BUY_NEW entry quantity was at least 200 shares, so a future 100-share partial REDUCE could be represented without inventing a larger entry.
- `REDUCE_UNMANAGEABLE_AT_ENTRY`: actual BUY_NEW entry quantity was 100 shares, so any partial REDUCE smaller than full exit would be unrepresentable under the 100-share lot constraint.

The audit does not artificially increase any position to make it manageable. Executed BUY_NEW entries are treated as Strategy/Safety-valid because they passed the actual runtime execution path.

## BUY_NEW Coverage Impact

| Class | BUY_NEW campaigns | Closed | Winners | Losers | Neutral | Win rate | Realized PnL | Gains | Losses | Avg PnL | Median PnL | Avg duration |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `REDUCE_MANAGEABLE` | 115 | 114 | 42 | 60 | 12 | 36.8% | +22,920 | +184,360 | -161,440 | +201 | -200 | 5.5BD |
| `REDUCE_UNMANAGEABLE_AT_ENTRY` | 451 | 448 | 204 | 234 | 10 | 45.5% | +514,290 | +1,753,550 | -1,239,260 | +1,148 | -100 | 6.7BD |

Strict rule impact:

- Total BUY_NEW campaigns: `566`
- Rejected campaigns: `451`
- Rejected campaign percentage: `79.7%`
- Rejected BUY_NEW notional: `42,992,180`
- Total BUY_NEW notional: `48,206,670`
- Rejected notional percentage: `89.2%`

Conclusion: the strict rule would remove most of the actual Strategy BUY universe, not a narrow subset.

## Coverage by Regime

| Entry regime | BUY_NEW | Unmanageable | Rejected % | Unmanageable PnL |
| --- | ---: | ---: | ---: | ---: |
| BEAR | 93 | 75 | 80.6% | +45,920 |
| BULL | 242 | 185 | 76.4% | +122,500 |
| CORRECTION | 22 | 19 | 86.4% | -146,550 |
| RANGE | 114 | 93 | 81.6% | +477,280 |
| RECOVERY | 95 | 79 | 83.2% | +15,140 |

The unmanageable class is not confined to a bad regime. It includes large positive contribution in RANGE and positive contribution in BULL.

## Coverage by Equity Scale

| Entry equity | BUY_NEW | Unmanageable | Rejected % | Unmanageable PnL | Unmanageable losses |
| --- | ---: | ---: | ---: | ---: | ---: |
| `<1.2M` | 188 | 158 | 84.0% | +354,210 | -192,890 |
| `1.2M-1.4M` | 12 | 11 | 91.7% | +156,120 | -37,980 |
| `1.4M-1.6M` | 157 | 119 | 75.8% | +331,290 | -330,140 |
| `>=1.6M` | 209 | 163 | 78.0% | -327,330 | -678,250 |

The rule would reject most entries at every capital scale. It would be historically favorable only in the `>=1.6M` bucket, but destructive in earlier buckets where unmanageable entries produced large net gains.

## Coverage by Entry Notional Ratio

| Entry notional ratio | BUY_NEW | Unmanageable | Rejected % | Unmanageable PnL |
| --- | ---: | ---: | ---: | ---: |
| `<5%` | 334 | 220 | 65.9% | +79,260 |
| `5-10%` | 134 | 133 | 99.3% | +318,120 |
| `10-15%` | 62 | 62 | 100.0% | +334,340 |
| `15-20%` | 30 | 30 | 100.0% | -72,230 |
| `>20%` | 6 | 6 | 100.0% | -145,200 |

The strict manageability rule is much broader than a high-notional-tail filter. It rejects all 100-share winners in the profitable `5-10%` and `10-15%` buckets.

## Winner False-Rejection Risk

If all unmanageable entries had been rejected, the missed winner profit would be:

`MISSED_WINNER_PROFIT_IF_UNMANAGEABLE_ENTRIES_REJECTED = 1,753,550`

Largest missed winners:

| Symbol | Entry | Exit | PnL | Qty | Entry ratio | Notional | Duration | PM REDUCE? | Lot-blocked REDUCE? |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 59350 | 2023-03-22 | 2023-04-20 | +188,600 | 100 | 14.31% | 184,400 | 21BD | NO | NO |
| 44440 | 2023-03-16 | 2023-03-22 | +84,000 | 100 | 9.13% | 109,400 | 3BD | NO | NO |
| 62280 | 2023-12-21 | 2023-12-28 | +78,330 | 100 | 15.70% | 249,000 | 5BD | YES | YES |
| 74270 | 2023-08-07 | 2023-10-02 | +44,000 | 100 | 7.32% | 113,600 | 38BD | YES | YES |
| 47610 | 2024-04-10 | 2024-04-11 | +42,000 | 100 | 9.88% | 151,900 | 1BD | NO | NO |
| 66780 | 2023-07-06 | 2023-12-05 | +41,800 | 100 | 12.49% | 193,400 | 102BD | NO | NO |
| 64240 | 2023-03-16 | 2023-03-23 | +41,300 | 100 | 11.30% | 135,400 | 4BD | YES | YES |
| 49370 | 2023-05-08 | 2023-05-10 | +41,200 | 100 | 9.23% | 143,600 | 2BD | NO | NO |
| 72140 | 2023-05-22 | 2023-05-26 | +39,900 | 100 | 9.32% | 132,600 | 4BD | YES | YES |
| 27080 | 2023-08-23 | 2023-09-25 | +38,500 | 100 | 10.34% | 159,700 | 22BD | YES | YES |

Winner false-rejection risk is very high. Some of the strongest campaigns in the run were 100-share positions that could not support a partial REDUCE at entry.

## Avoided Loss

If all unmanageable entries had been rejected, avoided realized losses would be:

`AVOIDED_LOSS_IF_UNMANAGEABLE_ENTRIES_REJECTED = 1,239,260`

Largest avoided losers:

| Symbol | Entry | Exit | PnL | Qty | Entry ratio | Notional | Duration | PM REDUCE? | Lot-blocked REDUCE? |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 55950 | 2024-03-07 | 2024-03-11 | -86,500 | 100 | 24.33% | 417,000 | 2BD | NO | NO |
| 55860 | 2024-03-13 | 2024-03-15 | -56,300 | 100 | 14.61% | 241,300 | 2BD | NO | NO |
| 74770 | 2023-10-02 | 2023-10-05 | -52,400 | 100 | 20.93% | 347,500 | 3BD | YES | YES |
| 51890 | 2023-04-10 | 2023-04-17 | -47,750 | 100 | 18.62% | 296,500 | 5BD | YES | YES |
| 60220 | 2023-04-11 | 2023-04-13 | -45,500 | 100 | 18.69% | 300,000 | 2BD | YES | YES |
| 62310 | 2023-04-28 | 2023-05-15 | -32,700 | 100 | 13.53% | 208,700 | 8BD | YES | YES |
| 36670 | 2023-06-09 | 2023-06-19 | -27,500 | 100 | 5.37% | 80,000 | 6BD | YES | YES |
| 36590 | 2024-02-08 | 2024-02-09 | -26,150 | 100 | 17.15% | 290,200 | 1BD | NO | NO |
| 90820 | 2023-10-24 | 2023-10-25 | -25,500 | 100 | 8.54% | 141,000 | 1BD | NO | NO |
| 69420 | 2024-02-13 | 2024-02-15 | -24,500 | 100 | 8.70% | 144,500 | 2BD | YES | YES |

The avoided loss is large, but it is smaller than the missed winner profit.

## Net Historical Counterfactual Characterization

Descriptive counterfactual:

`NET_HISTORICAL_EFFECT = avoided losses - missed winner profits`

`NET_HISTORICAL_EFFECT = 1,239,260 - 1,753,550 = -514,290`

This means the strict entry-manageability rule would have been economically unfavorable over the inspected historical window before considering any redeployment of freed cash.

Important limitation:

- Freed cash redeployment is not modeled as profitable.
- Contemporaneous candidates often existed, but this audit does not use future outcomes to assume replacement winners.
- Some 100-share entries were cash-affordable at 200 shares in a rough cash sense, but the actual Strategy/Safety sizing did not justify 200 shares. Among unmanageable entries, 339 had rough cash affordability for 200 shares, but this is not authority to upsize them.

## Relationship to BH

Among `REDUCE_UNMANAGEABLE_AT_ENTRY` campaigns:

- Later PM REDUCE requested: `297`
- Later lot-blocked REDUCE occurred: `297`

BH interval relationship:

| Entry class | BH intervals | Harmful | Beneficial | Net BH consequence | Loss total | Gain total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Unmanageable at entry | 297 | 79 | 47 | -390,770 | -685,540 | +294,770 |
| Manageable at entry | 46 | 7 | 6 | +690 | -24,460 | +25,150 |

Interpretation:

- The strict rule would capture most BH harmful blocked intervals by count: `79 / 86 = 91.9%`.
- It would also reject most beneficial blocked intervals: `47 / 53 = 88.7%`.
- The net BH harm is overwhelmingly concentrated in unmanageable entries, but the same class contains many beneficial blocked cases and most of the Strategy's realized winner profit.

Therefore, entry manageability targets BH's mechanical problem, but in an overly broad and economically destructive way.

## Capital Utilization and Opportunity Cost

Rejected BUY deployment:

- Rejected BUY_NEW notional: `42,992,180`
- Total BUY_NEW notional: `48,206,670`
- Rejected deployment share: `89.2%`

This is a severe capital-utilization impact. A strict rule would leave substantially more cash idle unless another canonical redeployment mechanism exists.

Contemporaneous alternatives:

- Candidate/quality evidence existed on representative dates.
- However, the audit did not prove that alternatives were themselves REDUCE-manageable or superior without using future outcomes.
- Opportunity displacement is therefore `UNCONFIRMED/PARTIAL`, not a basis for accepting the strict rule.

## Practical Viability Judgment

Strict rule:

`if REDUCE_UNMANAGEABLE_AT_ENTRY then BUY_WAIT`

Classification: `TOO_DESTRUCTIVE_TO_BUY_UNIVERSE` and `ECONOMICALLY_UNFAVORABLE`.

Why:

- It rejects 79.7% of BUY_NEW campaigns and 89.2% of BUY_NEW notional.
- It misses `1,753,550` of winner profit.
- It produces a descriptive net historical effect of `-514,290`.
- It blocks many actual winners that never needed PM REDUCE.
- It also blocks beneficial lot-block cases where holding through the blocked REDUCE preserved gains.

Softer concepts are more appropriate:

- manageability penalty rather than hard rejection,
- high-confidence exception,
- starter-size / high-notional exception handling,
- lot-aware full-exit reconsideration only after PIT deterioration is observed,
- capital-rotation pressure tied to PM deterioration, not entry quantity alone.

## Required Final Answers

1. `TOTAL_BUY_NEW_CAMPAIGNS`: `566`
2. `REDUCE_MANAGEABLE_COUNT`: `115`
3. `REDUCE_UNMANAGEABLE_COUNT`: `451`
4. `REJECTED_BUY_PERCENTAGE`: `79.7%`
5. `MANAGEABLE_GROUP_PNL`: `+22,920`
6. `UNMANAGEABLE_GROUP_PNL`: `+514,290`
7. `UNMANAGEABLE_WINNER_COUNT`: `204`
8. `UNMANAGEABLE_LOSER_COUNT`: `234`
9. `MISSED_WINNER_PROFIT`: `1,753,550`
10. `AVOIDED_LOSS`: `1,239,260`
11. `NET_HISTORICAL_EFFECT`: `-514,290`
12. `TOP_MISSED_WINNERS`: `59350 +188,600`, `44440 +84,000`, `62280 +78,330`, `74270 +44,000`, `47610 +42,000`, `66780 +41,800`
13. `TOP_AVOIDED_LOSERS`: `55950 -86,500`, `55860 -56,300`, `74770 -52,400`, `51890 -47,750`, `60220 -45,500`, `62310 -32,700`
14. `BH_HARM_CAPTURE_RATE`: `91.9%` by harmful interval count, but with major beneficial false rejection.
15. `BH_BENEFICIAL_BLOCK_FALSE_REJECTION_RISK`: HIGH; `88.7%` of beneficial blocked intervals were also unmanageable-at-entry.
16. `CAPITAL_UTILIZATION_IMPACT`: severe; `89.2%` of BUY_NEW notional would disappear before any unproven redeployment.
17. `WOULD_MOST_CURRENT_BUYS_DISAPPEAR`: YES.
18. `STRICT_ENTRY_MANAGEABILITY_RULE_VIABLE`: NO.
19. `SOFTER_DESIGN_NEEDED`: YES.
20. `IS_PRODUCTION_CHANGE_JUSTIFIED_NOW`: NO.
21. `NEXT_RECOMMENDED_STEP`: design a PIT-only softer shadow contract that combines lot manageability with observed deterioration, high-notional starter risk, confidence exceptions, and lot-aware full-exit reconsideration; do not use entry unmanageability as a hard BUY_WAIT rule.
22. `FINAL_JUDGMENT`: `PHASE32_BI_STRICT_REDUCE_MANAGEABLE_ENTRY_RULE_TOO_DESTRUCTIVE_TO_BUY_UNIVERSE_SOFT_LOT_AWARE_DESIGN_NEEDED_NO_PRODUCTION_CHANGE`

## No Change Confirmation

- Code change: NO
- Config/model/threshold change: NO
- Runtime state mutation: NO
- Resume/recover/replay/fresh-run: NO
- Shadow or Production behavior implementation: NO
- Future information used as decision-time evidence: NO

