# Phase32-BF — Equity Profit-Retention / Drawdown Mechanism READ-ONLY Characterization

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260831T003243720082Z`
- Snapshot inspected: 2026-09-01 05:46:38 JST
- Run state at snapshot: `RUNNING`
- Current continuation point at snapshot: `2024-04-19:strategy_shadow_generation`
- Completed evidence used: 380 completed business days, `2022-10-03` through `2024-04-18`
- Source commit recorded by run plan: `ff1d23157cced619c5820898f8317a7440e6092c`
- Source dirty: YES, as recorded in run subprocess traces and local git status

This is a READ-ONLY characterization. No code, config, model, threshold, runtime state, Pending, Ledger, recovery, replay, resume, or fresh-run operation was changed or executed.

Historical Equity/PnL was used only to identify episodes and measure economic impact. Causal interpretation below is based on decision-time PIT artifacts such as `market_context.json`, `position_management.json`, fills, realized slices, current valuation projections, and run-scoped evidence.

## Evidence Method

Daily Equity was calculated from completed-day `current_valuation_refresh/valuation_projection.json`:

`Equity = cash + new_total_market_value`

Position-level valuation was read through the `current_valuation_manifest.json` `history_path` where available. Economic attribution used:

- position market-value change,
- signed fill cash effects,
- realized slice evidence for completed exits,
- PM decision-time fields such as `canonical_sell_state`, `pm_severity`, `reason_codes`, `strategy_intelligence_current_campaign_relative_return`, `strategy_intelligence_observed_giveback`, `continuation_quality_status`, and `downside_risk_status`.

The audit explicitly avoids treating final outcome, future return, future regime, future MFE/MAE, or hindsight as decision input.

## Equity Coverage

- First measured Equity: `1,012,350` on `2022-10-03`
- Last measured Equity in completed evidence: `1,559,280` on `2024-04-18`
- Highest measured Equity: `1,762,140` on `2024-02-29`
- Net completed-window gain: `+546,930`
- Material giveback threshold used for characterization: drawdown >= `50,000` or >= `4%`

## Material Giveback Episodes

Eight material peak-to-trough episodes were found.

| ID | Peak -> Trough | Equity | Giveback | Drawdown | Duration | Regime mix | Position count |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| E1 | 2024-02-29 -> 2024-03-15 | 1,762,140 -> 1,504,100 | 258,040 | 14.64% | 11BD | BULL 11, RANGE 1 | 12 -> 10; min/max 7/12 |
| E2 | 2023-04-06 -> 2023-05-19 | 1,671,890 -> 1,422,290 | 249,600 | 14.93% | 28BD | BULL 16, RECOVERY 7, BEAR 2, CORRECTION 2, RANGE 2 | 5 -> 6; min/max 4/14 |
| E3 | 2023-06-19 -> 2023-08-17 | 1,688,380 -> 1,455,190 | 233,190 | 13.81% | 41BD | BULL 15, RANGE 11, RECOVERY 10, CORRECTION 6 | 12 -> 11; min/max 7/17 |
| E4 | 2023-10-03 -> 2023-12-20 | 1,694,010 -> 1,585,850 | 108,160 | 6.38% | 53BD | BEAR 20, RANGE 14, BULL 11, RECOVERY 6, CORRECTION 3 | 5 -> 6; min/max 3/12 |
| E5 | 2024-01-18 -> 2024-02-16 | 1,719,700 -> 1,635,060 | 84,640 | 4.92% | 20BD | BULL 16, RANGE 4, RECOVERY 1 | 5 -> 9; min/max 3/10 |
| E6 | 2023-03-06 -> 2023-03-14 | 1,233,220 -> 1,168,620 | 64,600 | 5.24% | 6BD | BULL 6, RANGE 1 | 13 -> 7; min/max 7/14 |
| E7 | 2023-03-28 -> 2023-03-29 | 1,460,700 -> 1,402,100 | 58,600 | 4.01% | 1BD | RANGE 1, RECOVERY 1 | 9 -> 9 |
| E8 | 2022-11-09 -> 2022-11-14 | 1,106,880 -> 1,055,230 | 51,650 | 4.67% | 3BD | BULL 3, RECOVERY 1 | 10 -> 9; min/max 9/13 |

## Economic Damage Attribution

### E1: 2024-02-29 -> 2024-03-15

- Negative economic contribution total: about `-295,840`
- Top1: `55950` `-86,500` / 33.5% of drawdown
- Top3: `55950`, `55860`, `66590` = `-170,700` / 66.2% of drawdown
- Dominant mechanism: weak starter losses plus existing Winner giveback.
- NEW entries during deterioration: 10 BUY_NEW fills.
- ADD losses: one BUY_ADD fill, `66590` on `2024-03-15`.
- Representative evidence:
  - `55950`: BUY_NEW on `2024-03-07` at 4,170, EXIT on `2024-03-11` at 3,305. PM had HOLD on `2024-03-08` with return `-3.96%`, then EXIT on `2024-03-11` with `hard_stop_current_return`.
  - `55860`: BUY_NEW on `2024-03-13` at 2,413, EXIT on `2024-03-15` at 1,850. PM had HOLD on `2024-03-14` with return `-6.09%`, then EXIT with `hard_stop_current_return` and `profit_retention_break`.
  - `66590`: PM observed very large campaign returns and giveback: return `55.2%` on `2024-02-29`, return `32.8%` / observed giveback `74.1%` by `2024-03-07`, yet the canonical sell state often remained `HEALTHY_OR_RECOVERING`; BUY_ADD was still executed on `2024-03-15`.

Classification: `WEAK_STARTER_ACCUMULATION`, `WINNER_PROFIT_RETENTION_LATE`, `LATE_EXIT`, limited `BAD_ADD`, and BULL-period candidate dilution.

### E2: 2023-04-06 -> 2023-05-19

- Negative economic contribution total: about `-399,130`
- Top1: `59350` `-176,000` / 70.5% of drawdown
- Top3: `59350`, `51890`, `60220` = `-269,250` / 107.9% of drawdown, offset by winners elsewhere.
- Dominant mechanism: concentrated Winner giveback plus many short-lived starters.
- NEW entries during deterioration: 43 BUY_NEW fills.
- ADD fills during episode: 0.
- Representative evidence:
  - `59350`: BUY_NEW on `2023-03-22` at 1,844, EXIT on `2023-04-20` at 3,730. This remained profitable, but PM observed `profit_retention_break` and `EXIT_GRADE` as early as `2023-03-27` and again `2023-03-30`; on `2023-04-06` return was still about `159.8%` with observed giveback `33.3%`, then by EXIT observed giveback reached about `98.7%`.
  - `51890`: BUY_NEW on `2023-04-10`, EXIT on `2023-04-17`, realized `-47,750`.
  - `60220`: BUY_NEW on `2023-04-11`, PM REDUCE on `2023-04-12`, EXIT on `2023-04-13`, realized `-45,500`.

Classification: `WINNER_PROFIT_RETENTION_LATE`, `WEAK_STARTER_ACCUMULATION`, `LATE_EXIT`, and BULL candidate churn.

### E3: 2023-06-19 -> 2023-08-17

- Negative economic contribution total: about `-364,230`
- Top1: `67310` `-200,000` / 85.8% of drawdown
- Top3: `67310`, `21340`, `40750` = `-243,000` / 104.2% of drawdown, offset by gains elsewhere.
- Dominant mechanism: concentrated campaign giveback and delayed full exit; plus many NEW entries and exits.
- NEW entries during deterioration: 58 BUY_NEW fills.
- ADD fills during episode: 0, though PM emitted repeated ADD intents for some existing winners.
- Representative evidence:
  - `67310`: BUY_NEW on `2023-04-21`, EXIT on `2023-08-18`. PM repeatedly alternated REDUCE/HOLD/ADD signals from April through August while `profit_retention_break` and `EXIT_GRADE` were visible on multiple dates. The old adjusted-basis pitfall is not used here as a valuation defect claim; the point is decision-time PM evidence showed repeated profit-protection and deterioration states before final EXIT.
  - `40750`: BUY_NEW on `2023-06-20`, PM REDUCE by `2023-06-23`, EXIT by `2023-06-26`, realized `-21,000`.
  - `21340`: strong prior campaign return existed, but giveback reached over `52.9%` by EXIT on `2023-07-07`.

Classification: `WINNER_PROFIT_RETENTION_LATE`, `LATE_EXIT`, `WEAK_STARTER_ACCUMULATION`, `EXPOSURE_TOO_HIGH_FOR_REALIZED_COHESION`.

### E4: 2023-10-03 -> 2023-12-20

- Negative economic contribution total: about `-269,400`
- Top1: `74770` `-29,900` / 27.6% of drawdown
- Top3: `74770`, `59660`, `90820` = `-83,400` / 77.1% of drawdown
- Dominant mechanism: broad starter churn under BEAR/RANGE regime mix, not one single Winner failure.
- NEW entries during deterioration: 78 BUY_NEW fills.
- ADD fills during episode: 0.
- Representative evidence:
  - `74770`: BUY_NEW on `2023-10-02`, REDUCE on `2023-10-04`, EXIT on `2023-10-05`; realized slice showed `-52,400`.
  - `59660`: BUY_NEW on `2023-10-03`, REDUCE on `2023-10-11`, EXIT on `2023-10-12`; PM observed deterioration but exited after the drawdown had already started.

Classification: `WEAK_STARTER_ACCUMULATION`, `LATE_EXIT`, `BULL_CANDIDATE_DILUTION` only weakly; BEAR/RANGE lifecycle dominates.

### Smaller Material Episodes

- E5 `2024-01-18 -> 2024-02-16`: broad starter loss, including `36590` and `69420`; BULL-heavy but not pure exposure failure.
- E6 `2023-03-06 -> 2023-03-14`: several profitable or near-flat positions deteriorated before EXIT; PM REDUCE/EXIT arrived after observable giveback on `48840`, `92520`, `39450`, `29700`.
- E7 `2023-03-28 -> 2023-03-29`: one-day drop dominated by `59350`, while PM moved to ADD on the same day after prior `EXIT_GRADE` / `profit_retention_break` evidence had appeared.
- E8 `2022-11-09 -> 2022-11-14`: `99840` stayed in ADD with positive campaign return while short-lived starters and exits contributed losses.

## BULL Drawdown Focus

BULL is materially present in large giveback windows, but BULL itself is not sufficient as the causal explanation.

Regime-day aggregate over completed evidence:

| Regime | Days | Sum Equity Delta | Avg Delta | Negative days | Avg exposure | Avg positions |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BULL | 170 | -14,260 | -84 | 78 | 0.740 | 10.7 |
| RANGE | 74 | +575,680 | +7,780 | 31 | 0.679 | 9.1 |
| RECOVERY | 62 | +238,120 | +3,841 | 25 | 0.711 | 10.2 |
| BEAR | 50 | -45,580 | -912 | 27 | 0.516 | 7.6 |
| CORRECTION | 23 | -207,030 | -9,001 | 12 | 0.662 | 8.8 |

Interpretation:

- BULL appears in six of eight material giveback episodes, including E1, E2, E3, E5, E6, and E8.
- However, BULL days overall are near-flat, not strongly negative.
- Profitable retained windows also contain many BULL days.
- The more plausible BULL-related mechanism is candidate dilution and starter churn under broad opportunity, not a simple “BULL is bad” rule.

## Exposure and Position Count

High exposure alone is not supported as the root cause.

Exposure buckets:

| Exposure bucket | Days | Sum Equity Delta | Avg Delta | Negative-day rate |
| --- | ---: | ---: | ---: | ---: |
| > 75% | 181 | +126,800 | +701 | 43% |
| 50% to 75% | 115 | +541,760 | +4,711 | 44% |
| <= 50% | 83 | -121,630 | -1,465 | 54% |

Position-count buckets:

| Position count bucket | Days | Sum Equity Delta | Avg Delta | Negative-day rate |
| --- | ---: | ---: | ---: | ---: |
| >= 12 | 112 | +637,790 | +5,695 | 35% |
| 7 to 11 | 203 | -75,820 | -373 | 50% |
| <= 6 | 64 | -15,040 | -235 | 52% |

Interpretation:

- High exposure and high position count can compound damage when cohesion deteriorates, but they are also present in strong gain-retention periods.
- The defect-like opportunity is not “lower exposure always”; it is exposure remaining high or capital being redeployed while realized cohesion and retention evidence have weakened.

## Positive Controls: Gain Retained

Comparable gain-retained periods exist and often include BULL/high-exposure conditions:

- `2023-02-20 -> 2023-03-22`: +169,160 over 20BD, max drawdown from start about 18,450; BULL/RANGE mix, average exposure about 0.82, average positions 13.5.
- `2023-02-27 -> 2023-03-28`: +282,020 over 20BD, max drawdown from start about 10,060; BULL/RANGE mix, average exposure about 0.80, average positions 12.2.
- `2023-03-10 -> 2023-04-10`: +416,250 over 20BD, max drawdown from start about 20,660; RANGE/RECOVERY/BULL mix, average exposure about 0.74, average positions 9.0.
- `2023-05-22 -> 2023-06-19`: +241,990 over 20BD, max drawdown from start about 2,500; BULL/RECOVERY mix, average exposure about 0.82, average positions 10.0.
- `2023-08-17 -> 2023-09-14`: +189,680 over 20BD, high exposure and position count; gains were retained over this window before later deterioration.
- `2023-12-15 -> 2024-01-18`: +127,630 over 20BD, low exposure about 0.34 and fewer positions.

Distinguishers observed:

- Gain-retained windows tolerate high exposure when PM deterioration is not persistent across major holdings or when broad positive offsets absorb starter churn.
- Giveback windows show either one dominant winner/campaign giving back after `profit_retention_break`, or many fresh starters entering and exiting quickly while regime is not uniformly supportive.
- `profit_retention_break`, `peak_drawdown_warning`, `EXIT_GRADE`, `PERSISTENT_DETERIORATION`, and observed giveback are already present in the PIT evidence; the issue is how forcefully they affect capital retention / de-risking authority.

## Mechanism Classification

| Mechanism | Evidence-backed classification | Notes |
| --- | --- | --- |
| `WINNER_PROFIT_RETENTION_LATE` | HIGH | Strong in E2/E3 and present in E1/E6/E7/E8. Existing PM evidence observed profit-retention breaks before final economic giveback was fully realized. |
| `WEAK_STARTER_ACCUMULATION` | HIGH | Strong in E1/E2/E3/E4/E5. Many BUY_NEW entries during deterioration quickly became REDUCE/EXIT or realized losses. |
| `LATE_EXIT` | HIGH | PM often emitted REDUCE/EXIT after deterioration was visible, but the campaign had already absorbed material giveback. |
| `BULL_CANDIDATE_DILUTION` | MEDIUM | BULL gives many candidates and many starters, but BULL also appears in retained-gain controls. The defect is candidate dilution under weak separation/cohesion, not BULL itself. |
| `EXPOSURE_TOO_HIGH_FOR_REALIZED_COHESION` | MEDIUM | Exposure alone is not bad; exposure while cohesion/retention evidence weakens is suspect. |
| `BAD_ADD` | LOW to MEDIUM | Executed ADD losses are not broad in the biggest episodes. PM ADD intent remains relevant because repeated ADD/HOLD can preserve exposure to campaigns whose profit-retention evidence is already deteriorating. |
| `REENTRY_CHURN` | LOW / not primary in inspected largest episodes | Not the dominant damage source in top episodes from completed evidence. |
| `SYNCHRONIZED_MARKET_SHOCK` | MEDIUM for E1/E6; LOW as full explanation | Some episodes are market-synchronized, but PIT evidence often showed item-level deterioration before final EXIT. |
| `LEGITIMATE_STRATEGY_VARIANCE` | PARTIAL | Some giveback is unavoidable for winner capture; however, repeated PIT-visible profit-retention breaks make the whole pattern not purely variance. |
| `VALUATION_ARTIFACT` | NOT_SUPPORTED as primary | Current valuation uses adjusted-basis authority and completed valuation projections. No new evidence reopened Phase32-Y measurement correctness. |

## Improvement Opportunity Ranking

1. HIGH: Profit-retention escalation using existing PM evidence
   - Evidence strength: high.
   - Supporting episodes: E1/E2/E3/E6/E7/E8.
   - Economic magnitude: largest two single-campaign givebacks exceed `176,000` and `200,000`.
   - Winner false-rejection risk: high, because many retained-gain controls also have high exposure and strong winners.
   - Existing features: yes. `profit_retention_break`, `observed_campaign_mfe`, `observed_giveback`, `EXIT_GRADE`, `peak_drawdown_warning`, `pm_severity`, and `persistence_state` already exist.
   - New feature required: not for first design pass.

2. HIGH: Starter throttle when fresh BUY_NEW cohort quality is failing
   - Evidence strength: high.
   - Supporting episodes: E1/E2/E3/E4/E5.
   - Economic magnitude: many short-lived realized losses, especially `55950`, `55860`, `60220`, `51890`, `40750`, `74770`, `69420`, `36590`.
   - Winner false-rejection risk: medium, because this targets starter cohort behavior rather than mature winners.
   - Existing features: likely yes, via Entry Quality, candidate rank/separation, BUY_WAIT state, market context, and recent starter failure evidence.
   - New feature required: likely no for a shadow/minimum design; possibly yes for robust cohort-level confidence later.

3. MEDIUM: Portfolio-level cohesion gate
   - Evidence strength: medium.
   - Supporting episodes: E1/E2/E3/E5.
   - Economic magnitude: high in large drawdowns, but positive controls show high exposure can be productive.
   - Winner false-rejection risk: medium to high.
   - Existing features: market context, breadth, position count, exposure, PM action distribution, starter churn.
   - New feature required: maybe not initially; a shadow aggregate of existing signals is enough to test.

4. MEDIUM: Candidate dilution / Top1-Top3 separation shadow
   - Evidence strength: medium.
   - Supporting episodes: BULL-heavy E1/E2/E3/E5/E6/E8.
   - Economic magnitude: material but mixed with strong retained BULL controls.
   - Winner false-rejection risk: medium.
   - Existing features: candidate rank and quality evidence appear present, but this audit did not fully reconstruct every candidate list separation.
   - New feature required: UNCONFIRMED; a read-only candidate-separation study should precede production design.

5. LOW to MEDIUM: ADD-specific de-risking
   - Evidence strength: lower for executed ADD, stronger for PM ADD intent.
   - Supporting episodes: E1, E7, E8, and PM-intent patterns around `67310`.
   - Economic magnitude: smaller than BUY_NEW churn and late winner retention.
   - Winner false-rejection risk: high if applied bluntly.
   - Existing features: yes.
   - New feature required: no.

## Required Final Answers

1. `MATERIAL_GIVEBACK_EPISODE_COUNT`: `8`
2. `LARGEST_GIVEBACK_EPISODES`: E1 `2024-02-29 -> 2024-03-15` `-258,040`; E2 `2023-04-06 -> 2023-05-19` `-249,600`; E3 `2023-06-19 -> 2023-08-17` `-233,190`.
3. `PRIMARY_ECONOMIC_DAMAGE_SOURCES`: concentrated Winner/campaign giveback in `59350` and `67310`; weak starter losses in `55950`, `55860`, `60220`, `51890`, `40750`, `74770`, `69420`, `36590`; broad churn in the 2023-10 to 2023-12 episode.
4. `IS_DAMAGE_CONCENTRATED_OR_BROAD`: mixed. E2/E3 are highly concentrated; E1/E4/E5 are broader with Top3 explaining about 66% to 77% of drawdown before offsets.
5. `IS_BULL_MATERIALLY_ASSOCIATED_WITH_GIVEBACK`: YES, but not as a standalone cause. BULL appears in many giveback windows, yet BULL days overall were roughly flat and many retained-gain controls were also BULL-heavy.
6. `IS_HIGH_EXPOSURE_ITSELF_THE_CAUSE`: NO. High exposure days had positive aggregate Equity delta in completed evidence; the suspect condition is high exposure plus weakening cohesion/profit-retention evidence.
7. `IS_WEAK_STARTER_ACCUMULATION_SUPPORTED`: YES / HIGH.
8. `IS_WINNER_PROFIT_RETENTION_LATE_SUPPORTED`: YES / HIGH.
9. `IS_LATE_EXIT_SUPPORTED`: YES / HIGH.
10. `IS_BAD_ADD_SUPPORTED`: PARTIAL. Executed ADD is not the broad primary loss source, but PM ADD/HOLD intent can preserve exposure despite profit-retention break evidence.
11. `IS_CANDIDATE_DILUTION_SUPPORTED`: MEDIUM. Supported as a BULL/churn hypothesis, not yet enough for a threshold.
12. `WAS_DETERIORATION_VISIBLE_IN_EXISTING_PIT_EVIDENCE`: YES for major inspected cases. Evidence included `profit_retention_break`, `EXIT_GRADE`, `PERSISTENT_DETERIORATION`, `peak_drawdown_warning`, and rising observed giveback before or during material loss.
13. `GAIN_RETAINED_VS_GIVEN_BACK_DISTINGUISHERS`: retained periods had high exposure only when winner/cohort evidence stayed cohesive or offsets remained broad; given-back periods showed concentrated winner giveback and/or many fresh starters failing quickly while PM evidence already showed deterioration.
14. `TOP_IMPROVEMENT_OPPORTUNITIES`: profit-retention escalation; starter throttle under failing fresh cohort; portfolio cohesion gate; candidate-separation shadow; ADD-intent de-risking.
15. `IS_NEW_FEATURE_REQUIRED`: NO for the first evidence-backed design pass; existing PIT evidence appears sufficient for shadow/minimum experiments. New research may be needed later for robust candidate/cohort separation.
16. `IS_PRODUCTION_CHANGE_JUSTIFIED_NOW`: NO. This phase is characterization only; the evidence justifies a bounded design/shadow phase, not direct Production parameter changes.
17. `FINAL_JUDGMENT`: `PHASE32_BF_EQUITY_PROFIT_RETENTION_DRAWDOWN_MECHANISM_CHARACTERIZED_PROFIT_RETENTION_AND_WEAK_STARTER_CHURN_SUPPORTED_NO_PRODUCTION_CHANGE`

## NO CHANGE Confirmation

- Code change: NO
- Config/model/threshold change: NO
- Runtime state mutation: NO
- Resume/recover/replay/fresh-run: NO
- Production decision feature using historical Equity/PnL: NO
- Future information used for decision causality: NO

