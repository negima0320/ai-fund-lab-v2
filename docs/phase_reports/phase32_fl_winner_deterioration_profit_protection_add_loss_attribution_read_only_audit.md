# Phase32-FL Winner Deterioration Profit Protection / ADD Loss Attribution READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260903T213011268067Z`
- Audit snapshot: `194` completed business days, `2022-10-03` through `2023-07-14`.
- Run status during audit: active run; this report freezes evidence at `2023-07-14` to avoid mixing moving artifacts.
- Evidence sources: `run_state.json`, daily `positions/position_campaigns.json`, `position_management/pm_decisions.json`, `strategy_eod_shadow/position_management.json`, `execution/fills.json`, and prior Phase32-FJ / Phase32-FK reports.

This was a READ-ONLY audit. No Production, SHADOW, config, schema, runtime state, Pending, Ledger, fresh-run, resume, recover, or replay mutation was executed.

Future realized prices and campaign outcomes were used only for mechanical characterization and loss/giveback attribution. They were not used to select or tune Production features, thresholds, weights, ranks, or parameters.

## Method

Winner deterioration was anchored on decision-time PM / campaign evidence, not on hindsight price decline alone. Deterioration evidence included `peak_drawdown_warning`, `profit_retention_break`, `risk_increased_but_trend_not_broken`, trend/opportunity break reasons, canonical REDUCE, and canonical EXIT evidence.

Giveback was split into:

- `Peak -> first deterioration evidence`: normal or not-yet-recognized giveback.
- `After first deterioration evidence`: avoidable-giveback candidate envelope, not proof that all of it was actually avoidable.

Daily campaign snapshots can be pre-action for same-day fills. To avoid double-counting, sell proceeds were counted only when strictly before the daily pre-action campaign valuation; same-day sell effects were attributed through execution/fill evidence.

ADD attribution is mechanical lot attribution:

```text
actual original BUY_NEW shares vs actual BUY_ADD shares
-> actual final/current value and peak contribution
```

This is not a "no-ADD world" Production counterfactual.

## Winner Deterioration Population

| Metric | Value |
|---|---:|
| Winner campaigns | 127 |
| `WINNER_WITH_DETERIORATION_COUNT` | 120 |
| Winner campaigns without observed deterioration anchor | 7 |
| ADD winner campaigns in primary winner set | 8 |

Most winners eventually produced a decision-time deterioration, REDUCE, or EXIT anchor. The evidence does not show that winner creation failed; the open question is how much profit remains after deterioration is recognized.

## Giveback Decomposition

| Metric | Value |
|---|---:|
| `PEAK_TO_DETERIORATION_GIVEBACK` | 557,427.89 |
| `POST_DETERIORATION_GIVEBACK` | 366,950.00 |
| Total measured deterioration-envelope giveback | 924,377.89 |
| `POST_DETERIORATION_GIVEBACK_SHARE` | 39.7% |

Interpretation:

- About 60.3% of measured winner giveback occurred before the first valid deterioration anchor or before a profit-protection trigger became visible in the actual decision path.
- About 39.7% occurred after deterioration evidence was available, making it the relevant envelope for profit-protection design review.
- This does not mean the whole 39.7% was avoidable; same-day information limits and normal volatility still apply.

## Deterioration Response Timeline

| Metric | Value |
|---|---:|
| First REDUCE lag median | 0BD |
| First REDUCE lag distribution | 0BD: 65, 1BD: 1, 12BD: 1 |
| EXIT lag median | 0BD |
| EXIT lag distribution | 0BD: 51, 1BD: 13, 2BD: 5, 3BD: 3, 5BD: 1, 6BD: 1, 8BD: 2, 10BD: 1, 14BD: 1, 19BD: 1 |

The median response is immediate once a REDUCE / EXIT action is actually authored. The material issue is not usually post-authoring execution lag; it is that deterioration can first appear as HOLD or as non-terminal warning evidence before full profit capture.

## Profit-Retention Warning Effectiveness

| Metric | Value |
|---|---:|
| `PROFIT_RETENTION_BREAK_COUNT` | 36 |
| `PROFIT_RETENTION_BREAK_HOLD_COUNT` | 18 |
| `PROFIT_RETENTION_BREAK_REDUCE_COUNT` | 0 |
| `PROFIT_RETENTION_BREAK_EXIT_COUNT` | 18 |

`profit_retention_break` is split between observability and terminal sell authority. Half of observed winner cases remained HOLD at the warning boundary, while half became EXIT. It was not observed as a graduated REDUCE authority in the primary winner set.

Judgment: profit-retention evidence is meaningful, but its current Production role is not consistently an effective profit-protection action. This supports a SELL/profit-protection design refinement study, not an immediate correctness repair.

## Peak-Drawdown Warning Effectiveness

| Metric | Value |
|---|---:|
| `PEAK_DRAWDOWN_WARNING_COUNT` | 49 |
| Warning action distribution | REDUCE: 49 |

`peak_drawdown_warning` has a clearer action mapping than `profit_retention_break`: all observed primary winner warnings mapped to REDUCE. The actual lot/executability layer often turns REDUCE into a material or full remaining-position sale for 100-share positions, so the problem is not simply that REDUCE orders are always too small.

## Partial REDUCE Effectiveness

| Metric | Value |
|---|---:|
| REDUCE fraction median | 100% |
| REDUCE cases with >=25% executed reduction | 118 |
| REDUCE cases with <25% executed reduction | 0 |
| `PARTIAL_REDUCE_MATERIAL_ENOUGH` | YES_FOR_EXECUTED_REDUCES / NOT_THE_PRIMARY_GAP |

For executed reductions, quantity was generally material. Many 100-share holdings are binary in practice: a REDUCE intent may become a full sell because one board lot is the executable unit. Therefore, the current evidence does not support "partial REDUCE too small" as the dominant explanation.

The more material gap is upstream: warning states can remain HOLD, and EXIT confirmation can wait for additional evidence.

## Large Post-Deterioration Giveback Cases

Representative high-envelope cases:

| Symbol | Campaign | First deterioration anchor | Action | Reason | Post-deterioration giveback | ADD campaign |
|---|---|---|---|---|---:|---|
| 59350 | `pc-066b1d25c0a578b4-59350-0001` | 2023-04-06 | HOLD | `profit_retention_break` | 176,000 | NO |
| 21340 | `pc-0774f425fe6b09c1-21340-0001` | 2023-06-19 | HOLD | `profit_retention_break` | 25,000 | YES |
| 30410 | `pc-f464...` | 2023-06-12 | HOLD | `profit_retention_break` | 22,300 | NO |
| 94670 | `pc-2d36...` | 2023-05-15 | EXIT | `trend_and_opportunity_broken` | 22,000 | NO |
| 78860 | `pc-28ef...` | 2022-12-02 | REDUCE | `peak_drawdown_warning` | 18,400 | NO |
| 39450 | `pc-9751...` | 2023-03-01 | REDUCE | `peak_drawdown_warning` | 15,400 | NO |
| 69270 | `pc-1945...` | 2023-05-11 | REDUCE | `risk_increased_but_trend_not_broken` | 15,100 | NO |
| 43880 | `pc-64642ec31e0f55ef-43880-0001` | 2023-04-07 | REDUCE | `peak_drawdown_warning` | 12,000 | YES |

The largest post-deterioration giveback case, `59350`, is non-ADD. This strongly argues against an ADD-specific root cause.

## ADD Capital Loss Attribution

| Metric | Value |
|---|---:|
| `ADD_CAMPAIGN_TOTAL_LOSS` | -46,380 |
| `NON_ADD_CAMPAIGN_TOTAL_LOSS` | -443,220 |
| `ADD_ATTRIBUTABLE_LOSS` | 30,790 |
| Original-lot attributable loss | 462,360 |
| `ADD_ATTRIBUTABLE_LOSS_SHARE` | 6.24% |
| `ADD_POSITIVE_CONTRIBUTION` | 24,630 |
| `ADD_NEGATIVE_CONTRIBUTION` | -30,790 |
| `ADD_NET_CONTRIBUTION` | -6,160 |
| ADD peak positive contribution | 51,740 |

Mechanical interpretation:

- ADD did create upside: positive and peak contribution were real.
- ADD also contributed to downside/giveback, but the loss share was small relative to original BUY_NEW capital losses.
- Net ADD contribution over the audit snapshot was slightly negative, but not large enough to explain portfolio-level giveback or loss concentration by itself.

`ADD_AMPLIFIES_GIVEBACK`: YES, mechanically, in some campaigns.

`ADD_AMPLIFIES_UPSIDE`: YES, also mechanically.

The evidence is closer to `ADD_AMPLIFIES_UPSIDE_AND_DOWNSIDE_SYMMETRICALLY` than to "ADD is the primary bad actor."

## ADD Winner vs Non-ADD Winner

| Metric | Value |
|---|---:|
| `ADD_WINNER_POST_DETERIORATION_GIVEBACK` | 42,990 across 6 cases |
| `NON_ADD_WINNER_POST_DETERIORATION_GIVEBACK` | 323,960 across 114 cases |

ADD winners have material giveback, but non-ADD winners dominate the absolute post-deterioration giveback envelope. The largest single giveback case is non-ADD.

`GIVEBACK_PROBLEM_ADD_SPECIFIC`: NO.

`SELL_PROFIT_PROTECTION_GENERAL_GAP`: YES.

## Large ADD Campaign Deep Dives

### 76470

- Campaign: `pc-86cc29266f5b880a-76470-0001`
- Opened: 2023-04-21
- Status at snapshot: OPEN
- Peak profit: approximately 20,900
- Approximate peak date: 2023-06-06
- First deterioration evidence used in this audit: 2023-06-02 REDUCE `peak_drawdown_warning`
- Approximate deterioration-date profit: -22,500 in pre-action mechanical series
- Post-deterioration giveback envelope: 0 under the audit split because deterioration appeared before the later approximate peak.
- Original-lot contribution: final/current +5,600; peak +12,000
- ADD-lot contribution: final/current -600; peak +1,900

Interpretation: 76470 confirms ADD exposure can be carried through deterioration and later positive continuation, but this specific snapshot does not show the largest post-deterioration giveback envelope. It remains important for re-ADD / ADD cap design, covered in FK.

### 94320

- Campaign: `pc-8ab721543669c35b-94320-0001`
- Opened: 2022-12-13
- Status at snapshot: OPEN
- Peak profit: approximately 17,350
- Approximate peak date: 2023-06-28
- First deterioration anchor: none observed after peak in the audit snapshot.
- Current/final profit: approximately 7,760
- Post-peak giveback characterization: approximately 9,590, but not post-deterioration because no qualifying deterioration anchor was observed.
- Original-lot contribution: final/current +2,620; peak +5,360
- ADD-lot contribution: final/current +5,140; peak +11,990

Interpretation: 94320 is evidence that ADD can improve both peak and retained profit. It is not evidence of an ADD-specific defect.

### 43880

- Campaign: `pc-64642ec31e0f55ef-43880-0001`
- Opened: 2023-03-22
- Closed: 2023-04-10
- Peak profit: approximately 57,072
- Approximate peak date: 2023-04-07
- First deterioration anchor: 2023-04-07 REDUCE `peak_drawdown_warning`
- Deterioration-date profit: approximately 30,100
- Peak-to-deterioration giveback: approximately 26,972
- Post-deterioration giveback: approximately 12,000
- Original-lot contribution: final +10,900; peak +16,900
- ADD-lot contribution: final +7,200; peak +13,200

Interpretation: 43880 shows both sides of ADD. The ADD lot remained profitable, but the campaign still gave back material profit after peak and after warning evidence. This supports general winner profit-protection refinement rather than ADD prohibition.

## Non-ADD Control Cases

### 59350

- Campaign: `pc-066b1d25c0a578b4-59350-0001`
- Opened: 2023-03-17
- Closed: 2023-04-20
- First deterioration anchor: 2023-04-06 HOLD `profit_retention_break`
- Peak profit / deterioration profit: approximately 389,200
- Final captured profit: approximately 213,200
- Post-deterioration giveback: approximately 176,000
- ADD: none

Interpretation: the largest post-deterioration giveback is non-ADD and tied to profit-retention evidence initially remaining HOLD. This is the clearest support for a general SELL/profit-protection gap.

### 67310

- Campaign: `pc-3dc0e019081df712-67310-0001`
- Opened: 2023-05-16
- Closed: 2023-05-22
- First deterioration anchor: 2023-05-19 REDUCE `risk_increased_but_trend_not_broken`
- ADD: none
- FJ showed this high-notional 100-share campaign dominated several daily PnL swings.

Interpretation: 67310 is primarily concentration / high-notional single-name exposure plus same-day information boundary. It is not ADD-specific.

## ADD Cap Isolation

FK established that `prior_add_history_limits_incremental_add` can cap further ADD after 5 same-campaign ADD events. FL does not change this cap and does not propose cap removal.

Within FL, the 5-ADD cap is not the root cause of winner giveback. It can limit further upside capitalization after a campaign has already accumulated ADD exposure, but the measured loss/giveback issue is dominated by non-ADD winners and original-lot exposure.

## Same-Day Information Boundary

The audit did not classify same-day drops as sell lateness when the morning decision could not know the later same-day price. This matters particularly for high-notional names such as 67310 and for daily campaign snapshots that are pre-action relative to same-day fills.

`SAME_DAY_UNAVOIDABLE_MOVE_DOMINANT`: PARTIAL. It explains several large daily swings, but not all post-deterioration giveback. The largest persistent signal remains profit-protection warnings that can remain HOLD or wait for stronger EXIT confirmation.

## Early vs Later Profit-Retention Shift

Primary final-winner basis:

| Period | Winners | With deterioration | ADD winners | Post-deterioration giveback | Peak-to-deterioration giveback | Action mix | Profit-retention mix | Peak-drawdown warning mix |
|---|---:|---:|---:|---:|---:|---|---|---|
| 2022-10-03 to 2023-02-28 opened campaigns | 68 | 67 | 4 | 102,650 | 262,005.66 | REDUCE 32 / EXIT 35 | EXIT 8 | REDUCE 9 |
| 2023-03-01 to 2023-07-14 opened campaigns | 59 | 53 | 4 | 264,300 | 504,072.23 | REDUCE 33 / EXIT 16 / HOLD 4 | HOLD 4 / EXIT 5 | REDUCE 4 |

Supplemental positive-peak episode basis, used only as a broader characterization:

- Early positive-peak episodes: 97; post-deterioration giveback 115,610.
- Later positive-peak episodes: 87; post-deterioration giveback 398,990.

`EARLY_LATE_PROFIT_RETENTION_SHIFT`: YES. Later opened campaigns show larger post-deterioration giveback and more profit-retention HOLD cases. This is still a characterization, not a parameter-selection basis.

## Root Cause Classification

Applicable classifications:

- `NORMAL_WINNER_VOLATILITY`: YES. A majority of measured giveback occurs before first deterioration evidence.
- `PROFIT_RETENTION_WARNING_TOO_WEAK`: YES. `profit_retention_break` is frequently HOLD and never observed as REDUCE in the primary winner set.
- `PARTIAL_REDUCE_TOO_SMALL`: NO / NOT_PRIMARY. Executed REDUCE quantities are generally material.
- `EXIT_CONFIRMATION_TOO_SLOW`: PARTIAL. Median EXIT lag is 0BD once triggered, but some campaigns show tails up to 19BD and warning-to-EXIT progression can lag.
- `ADD_AMPLIFIES_GIVEBACK`: YES, mechanically.
- `ADD_AMPLIFIES_UPSIDE_AND_DOWNSIDE_SYMMETRICALLY`: YES, best fit for ADD-specific evidence.
- `SELL_RETENTION_GENERAL_PROBLEM_NOT_ADD_SPECIFIC`: YES.
- `SAME_DAY_UNAVOIDABLE_MOVE_DOMINANT`: PARTIAL.
- `CONCENTRATION_DOMINANT`: PARTIAL, especially high-notional 100-share campaigns such as 67310.
- `MIXED`: YES.

No PIT, provenance, campaign identity, hash authority, G129 BUY_ADD, or runtime-control correctness violation was found in this audit.

## Repair Judgment

| Question | Judgment |
|---|---|
| `CORRECTNESS_DEFECT_FOUND` | NO |
| `SELL_PROFIT_PROTECTION_REFINEMENT_JUSTIFIED` | YES |
| `ADD_SPECIFIC_REFINEMENT_JUSTIFIED` | CONDITIONAL / DESIGN-ONLY |
| `PRODUCTION_REPAIR_JUSTIFIED` | NO |
| `LONG_HORIZON_VALIDATION_SAFE_TO_CONTINUE` | YES |

Rationale:

- The evidence supports a design refinement around profit-retention warning authority, deterioration confirmation, concentration-aware profit protection, and warning-to-action progression.
- It does not support an immediate Production correctness repair.
- ADD-specific restriction is not justified by this evidence alone because ADD contributed both positive and negative exposure and did not dominate losses.

## Required Answers

- `WINNER_WITH_DETERIORATION_COUNT`: 120
- `PEAK_TO_DETERIORATION_GIVEBACK`: 557,427.89
- `POST_DETERIORATION_GIVEBACK`: 366,950.00
- `POST_DETERIORATION_GIVEBACK_SHARE`: 39.7%
- `PROFIT_RETENTION_BREAK_COUNT`: 36
- `PROFIT_RETENTION_BREAK_HOLD_COUNT`: 18
- `PROFIT_RETENTION_BREAK_REDUCE_COUNT`: 0
- `PROFIT_RETENTION_BREAK_EXIT_COUNT`: 18
- `PEAK_DRAWDOWN_WARNING_COUNT`: 49
- `FIRST_REDUCE_LAG_BD`: median 0BD; distribution 0BD 65, 1BD 1, 12BD 1
- `EXIT_LAG_BD`: median 0BD; tail through 19BD
- `PARTIAL_REDUCE_MATERIAL_ENOUGH`: YES_FOR_EXECUTED_REDUCES / NOT_PRIMARY_GAP
- `ADD_CAMPAIGN_TOTAL_LOSS`: -46,380
- `NON_ADD_CAMPAIGN_TOTAL_LOSS`: -443,220
- `ADD_ATTRIBUTABLE_LOSS`: 30,790
- `ADD_ATTRIBUTABLE_LOSS_SHARE`: 6.24%
- `ADD_POSITIVE_CONTRIBUTION`: 24,630
- `ADD_NEGATIVE_CONTRIBUTION`: -30,790
- `ADD_NET_CONTRIBUTION`: -6,160
- `ADD_AMPLIFIES_GIVEBACK`: YES
- `ADD_AMPLIFIES_UPSIDE`: YES
- `ADD_WINNER_POST_DETERIORATION_GIVEBACK`: 42,990
- `NON_ADD_WINNER_POST_DETERIORATION_GIVEBACK`: 323,960
- `GIVEBACK_PROBLEM_ADD_SPECIFIC`: NO
- `SELL_PROFIT_PROTECTION_GENERAL_GAP`: YES
- `EARLY_LATE_PROFIT_RETENTION_SHIFT`: YES
- `CORRECTNESS_DEFECT_FOUND`: NO
- `SELL_PROFIT_PROTECTION_REFINEMENT_JUSTIFIED`: YES
- `ADD_SPECIFIC_REFINEMENT_JUSTIFIED`: CONDITIONAL / DESIGN-ONLY
- `PRODUCTION_REPAIR_JUSTIFIED`: NO
- `LONG_HORIZON_VALIDATION_SAFE_TO_CONTINUE`: YES

## Next Recommended Step

Open a design-only follow-up focused on profit-retention warning semantics and concentration-aware winner protection:

- clarify when `profit_retention_break` should remain observability-only vs become action authority;
- compare HOLD / REDUCE / EXIT escalation using same-day information boundaries;
- keep ADD evaluation symmetric by measuring both upside amplification and giveback amplification;
- avoid Production threshold or parameter changes until a PIT semantic contract is explicitly accepted.

## Final Judgment

`PHASE32_FL_WINNER_GIVEBACK_IS_GENERAL_PROFIT_PROTECTION_DESIGN_GAP_NOT_ADD_SPECIFIC_CORRECTNESS_DEFECT`
