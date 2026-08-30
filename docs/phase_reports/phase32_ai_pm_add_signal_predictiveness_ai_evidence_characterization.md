# Phase32-AI — PM ADD Signal Predictiveness + AI Evidence Characterization

## Scope

- Trusted run: `runtime-test-historical-extended-smoke-20260830T081425790243Z`
- Trusted window: `2022-10-03` through `2023-10-10`
- Business days used: `252`
- Mode: READ-ONLY characterization

No code, config, runtime state, Strategy design, comparator design, threshold, weight, ADD tier, Cash policy, BQ, Risk Pacing, PC, PS, Runtime, resume, recover, replay, fresh-run, or long Historical action was performed.

Forward outcomes in this report are explicitly:

```text
POST_HOC_DIAGNOSTIC_ONLY
```

They were not used to choose features, thresholds, weights, Production rules, or future Strategy parameters.

## Executive Summary

PM ADD contains meaningful decision-time strength information, but it is mostly a state signal rather than a fresh incremental-capital timing signal.

Key findings:

- PM ADD signals: `118`
- unique ADD campaigns: `11`
- contiguous campaign ADD episodes: `35`
- material evidence-state micro-episodes: `106`
- PM ADD state/change classification: `103 STATE_DOMINANT`, `15 MIXED`, `0 CHANGE_DOMINANT`
- AH classes: `1 CLEAR_INCREMENTAL_OPPORTUNITY`, `10 PLAUSIBLE_INCREMENTAL_OPPORTUNITY`, `107 HOLD_STRENGTH_ONLY`
- actual BUY_ADD fills: `9`

PM ADD is stronger than ordinary HOLD at decision time:

| Field | PM ADD Avg | PM HOLD Avg |
| --- | ---: | ---: |
| PM action score | `0.811` | `0.521` |
| BQ score | `0.740` | `0.637` |
| BQ rank | `2.59` | `16.36` |
| unrealized return | `20.1%` | `11.4%` |
| 5D momentum | `7.6%` | `3.5%` |
| 20D momentum | `42.0%` | `29.3%` |

But PM ADD does not independently establish positive next-lot value. Source and artifacts show PM ADD is driven by continuation/rank/no-loss evidence, while ADD investment evidence and Strategy Intelligence decide whether that can become an executable ADD candidate.

Final classification:

```text
MIXED
```

with primary branch:

```text
Branch D — mixed, led by PM_ADD_IS_MOSTLY_HOLD_STRENGTH plus limited downstream filtering/bridge issues.
```

## A — 118 PM ADD Signal Reconstruction

All 118 PM ADD decisions shared the same PM reason-code pattern:

```text
strong_trend_continuation
opportunity_rank_still_high
no_loss_averaging
```

PM ADD BQ distribution:

| BQ Action / Band | Count |
| --- | ---: |
| `FULL_ALLOCATION_ELIGIBLE / HIGH` | `45` |
| `REDUCED_ALLOCATION_ONLY / MEDIUM` | `31` |
| `REDUCED_ALLOCATION_ONLY / HIGH` | `24` |
| `BUY_WAIT / BUY_WAIT` | `18` |

Strategy Intelligence entry states:

| SI Entry Action / State | Count |
| --- | ---: |
| `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION` | `99` |
| `NO_ADD / OVERHEATED_DECELERATING_ENTRY` | `18` |
| `ADD_ALLOWED / HEALTHY_CONTINUATION_ENTRY` | `1` |

Final disposition:

| Disposition | Count |
| --- | ---: |
| HOLD-converted before PC | `19` |
| PC ADD competitor present | `99` |
| PC selected / Runtime-positive ADD | `11` |
| actual BUY_ADD fill | `9` |
| PC daily ADD winner | `0` |

Primary decision-time classification:

| AH Intent Class | Count |
| --- | ---: |
| `CLEAR_INCREMENTAL_OPPORTUNITY` | `1` |
| `PLAUSIBLE_INCREMENTAL_OPPORTUNITY` | `10` |
| `HOLD_STRENGTH_ONLY` | `107` |

Fields not available as canonical evidence for all rows were treated as:

```text
NOT_AVAILABLE_IN_CANONICAL_EVIDENCE
```

No unavailable AI field was invented.

## B — AI / Intelligence Inputs Behind ADD

Actual PM ADD is driven by a mix of model/scored evidence and deterministic rules around that evidence.

| Input | Classification | Evidence / Role |
| --- | --- | --- |
| PM action score / add score | `DIRECT_PM_INPUT` | PM ADD trigger uses `add_score >= 0.72`. |
| opportunity rank | `DIRECT_PM_INPUT` | PM ADD trigger uses `buy_rank <= 5`. |
| current return / no-loss | `DIRECT_PM_INPUT` | PM ADD trigger uses `current_return > 0.0`. |
| downside risk score | `DIRECT_PM_INPUT` | PM has `add_downside_risk_contained`; risk also affects EXIT/REDUCE. |
| trend continuation score | `DIRECT_PM_INPUT` | feeds add score / continuation trigger. |
| expected edge score | `DIRECT_PM_INPUT / INDIRECT_PM_INPUT` | used in PM scoring and expected-edge trace, but ADD trace says incremental value is not separately proven. |
| Candidate AI / opportunity rankings | `INDIRECT_PM_INPUT` | opportunity rank and runtime opportunity score originate in candidate/opportunity evidence. |
| Buy Quality | `INDIRECT_PM_INPUT / PC_ONLY` | PM records correlate with BQ, but BQ is mainly downstream PC/PS evidence. |
| Strategy Intelligence continuation/entry evidence | `STRATEGY_INTELLIGENCE_INPUT` | can convert PM ADD to HOLD or allow ADD_REDUCED/ADD_ALLOWED. |
| campaign state / prior ADD count | `STRATEGY_INTELLIGENCE_INPUT` | `prior_add_history_limits_incremental_add` blocked the 19 `76470` cases. |
| Market regime / Market Quality | `STRATEGY_INTELLIGENCE_INPUT / PC_ONLY` | visible in SI and Cash/Risk context, not standalone PM ADD trigger. |
| Risk Pacing | `PC_ONLY` | affects PC interaction and Cash preference. |
| learned/model-produced score | `DIRECT_PM_INPUT` for PM score; `INDIRECT_PM_INPUT` for Candidate/BQ scores | Scores are not calibrated probabilities. |

Answer:

```text
WHAT_DOES_THE_AI_ACTUALLY_CONTRIBUTE_TO_PM_ADD
```

The AI/scoring stack contributes a strength/rank/continuation state signal. It does not yet contribute a separately proven executable next-lot marginal capital value.

## C — ADD Episodes

The 118 PM ADD signals should not be treated as 118 independent opportunities.

Two useful episode counts were computed:

| Episode Definition | Count | Meaning |
| --- | ---: | --- |
| contiguous campaign ADD episodes | `35` | same campaign, consecutive business-day ADD streaks |
| material evidence-state micro-episodes | `106` | same campaign plus unchanged coarse BQ/SI/continuation/risk state |

The decision answer uses:

```text
35 unique contiguous ADD episodes
```

because this best represents repeated ADD periods while avoiding day-level overcounting.

Longest consecutive ADD streaks:

| Campaign / Symbol | ADD Signals | Max Consecutive BD Streak |
| --- | ---: | ---: |
| `pc-925de11083435873-99840-0001 / 99840` | `18` | `18` |
| `pc-8b52b4c89fd002ad-76470-0001 / 76470` | `25` | `12` |
| `pc-f6f650ff3364b80b-94320-0001 / 94320` | `15` | `12` |
| `pc-df47de7d57274254-43880-0001 / 43880` | `12` | `8` |
| `pc-f3bd989f40c52bdf-94340-0001 / 94340` | `6` | `6` |

Conclusion:

```text
ARE_118_PM_ADDS_MOSTLY_REPEATED_STATE_OR_FRESH_EVENTS: REPEATED_STATE
```

## D — POST_HOC_DIAGNOSTIC_ONLY Forward Outcome Characterization

The following outcomes are diagnostic only.

### PM ADD vs HOLD

| Group | +1BD Mean / Median / Pos | +5BD Mean / Median / Pos | +20BD Mean / Median / Pos | MFE20 Mean / Median | MAE20 Mean / Median |
| --- | --- | --- | --- | --- | --- |
| PM ADD `n=118` | `-1.28% / 0.00% / 39.0%` | `+0.97% / 0.00% / 34.7%` | `-4.86% / -4.72% / 22.9%` | `+16.25% / +5.42%` | `-13.52% / -8.38%` |
| PM HOLD `n=1729` | `-0.03% / 0.00% / 44.3%` | `-0.24% / 0.00% / 47.1%` | `+0.62% / -0.38% / 44.7%` | `+13.39% / +5.99%` | `-9.50% / -5.90%` |

PM ADD had higher average MFE20 but worse 20BD median/positive-rate and worse MAE than HOLD. This supports “volatile strong state,” not reliable incremental timing.

### Signal-Level Filled vs Non-Filled ADD

| Group | +5BD Mean / Median / Pos | +20BD Mean / Median / Pos | MFE20 Mean / Median | MAE20 Mean / Median |
| --- | --- | --- | --- | --- |
| Filled ADD `n=9` | `-1.06% / 0.00% / 0.0%` | `+1.94% / +1.49% / 66.7%` | `+4.69% / +3.70%` | `-3.05% / -3.70%` |
| Non-filled ADD `n=109` | `+1.13% / 0.00% / 37.6%` | `-5.42% / -5.62% / 19.3%` | `+17.20% / +6.34%` | `-14.38% / -9.10%` |

PC/Runtime/fill filtering appears to reduce downside and improve 20BD continuation in this sample, but the filled sample is only 9 and cannot justify tuning.

### Episode-Level View

For the 35 contiguous episode starts:

| Metric | Result |
| --- | --- |
| +5BD | mean `+0.51%`, median `0.00%`, positive-rate `40.0%` |
| +20BD | mean `-4.00%`, median `-3.70%`, positive-rate `22.9%` |
| MFE20 | mean `+24.82%`, median `+10.05%` |
| MAE20 | mean `-18.11%`, median `-10.51%` |

Episodes show large upside optionality but also large downside, again suggesting state strength without precise incremental timing.

## E — AH Intent Class Diagnostic Comparison

POST_HOC_DIAGNOSTIC_ONLY:

| AH Class | Count | +5BD Mean / Median / Pos | +20BD Mean / Median / Pos | MFE20 Mean / Median | MAE20 Mean / Median |
| --- | ---: | --- | --- | --- | --- |
| `CLEAR_INCREMENTAL_OPPORTUNITY` | `1` | `0.00% / 0.00% / 0.0%` | `0.00% / 0.00% / 0.0%` | `+3.70% / +3.70%` | `-3.70% / -3.70%` |
| `PLAUSIBLE_INCREMENTAL_OPPORTUNITY` | `10` | `-1.22% / -0.85% / 0.0%` | `+1.42% / +1.88% / 70.0%` | `+4.30% / +3.60%` | `-3.37% / -2.84%` |
| `HOLD_STRENGTH_ONLY` | `107` | `+1.18% / 0.00% / 38.3%` | `-5.49% / -5.62% / 18.7%` | `+17.48% / +6.36%` | `-14.56% / -9.16%` |

AH classes separate downstream risk more than short-term upside. Plausible/clear incremental rows had much lower MAE and better +20BD positive-rate, but sample sizes are too small for Production parameter decisions.

## F — Filled 9 vs Rejected / Non-Filled ADDs

Decision-time evidence for filled ADDs:

| Filled ADD Class | Count |
| --- | ---: |
| `STRONG_INCREMENTAL_ADD_CASE` | `1` |
| `PLAUSIBLE_INCREMENTAL_ADD_CASE` | `8` |

Filled ADDs had stronger downstream PC evidence than rejected ADDs:

- all 9 had PC `COMPARABLE_MARGINAL`;
- all had incremental value `POSITIVE`;
- all had accepted incremental weight > 0;
- 8 were still `CASH_PREFERRED`, so fill does not mean final daily ADD winner.

POST_HOC_DIAGNOSTIC_ONLY, filled ADDs had better +20BD and lower MAE than non-filled ADDs, but weaker +5BD. This is:

```text
PARTIAL_ENRICHMENT
```

not causal proof.

## G — Missed ADD Opportunity Search

Across PM HOLD rows, broad existing ADD-like evidence was common:

- broad HOLD candidates with SI ADD-like state and top-5 rank: `141`

Strict existing-evidence fresh-strength candidates:

Criteria used:

- PM action was HOLD;
- Strategy Intelligence entry action was `ADD_ALLOWED` or `ADD_REDUCED_ONLY`;
- BQ band was `HIGH`;
- opportunity rank `<= 5`;
- current position had positive unrealized return;
- existing SI continuation state showed supportive or accelerating evidence.

Strict candidates:

| Symbol | Count |
| --- | ---: |
| `54010` | `6` |
| `77760` | `5` |
| `21340` | `4` |
| `40520` | `2` |
| `43880` | `1` |
| `37780` | `1` |
| total | `19` |

Representative examples:

| Date | Symbol | Rank | BQ | Return | SI State | PM Reasons |
| --- | --- | ---: | --- | ---: | --- | --- |
| `2023-03-01` | `54010` | `3` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `+15.3%` | `ADD_ALLOWED / HEALTHY_CONTINUATION_ENTRY` | HOLD continuation |
| `2023-06-16` | `40520` | `5` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `+8.6%` | `ADD_ALLOWED / HEALTHY_CONTINUATION_ENTRY` | HOLD/profit-retention evidence |
| `2023-06-14` | `21340` | `2` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `+32.0%` | `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION` | HOLD/profit-retention evidence |
| `2023-07-05` | `37780` | `5` | `FULL_ALLOCATION_ELIGIBLE / HIGH` | `+19.8%` | `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION` | HOLD continuation |

Conclusion:

```text
DID_PM_MISS_EXISTING_FRESH_STRENGTH_EVENTS: YES, LIMITED / CANDIDATE_ONLY
```

Existing artifacts contain HOLD rows with ADD-like SI/BQ/rank/positive-return states. This does not prove they should have been ADD, but it shows PM ADD is not the only place where current evidence records renewed or supportive continuation.

## H — State vs Change Analysis

PM ADD classification:

| Class | Count |
| --- | ---: |
| `STATE_DOMINANT` | `103` |
| `MIXED` | `15` |
| `CHANGE_DOMINANT` | `0` |
| `INSUFFICIENT_EVIDENCE` | `0` |

Most common continuation-state tuples include `DECELERATING` or `MIXED` acceleration while persistence/trend/relative strength remain supportive. This means PM ADD mostly detects a strong current state, not a fresh acceleration event.

Conclusion:

```text
PM_ADD_IS_STATE_DOMINANT
```

## I — AI Predictive Content

Exploratory, POST_HOC_DIAGNOSTIC_ONLY separators:

| Feature / Evidence | Semantically Intended? | PIT? | Already Used? | Current Downstream Treatment |
| --- | --- | --- | --- | --- |
| BQ high/full allocation | `YES` | `YES` | `YES` | Used, but compressed into PC quality/action states |
| opportunity rank top-5 | `YES` | `YES` | `YES` | Direct PM trigger; not calibrated marginal value |
| Strategy Intelligence `ADD_ALLOWED` / `HEALTHY_CONTINUATION_ENTRY` | `YES` | `YES` | `YES` | Can be overridden by PM/HOLD or ADD history gates |
| prior ADD count | `YES`, risk/control | `YES` | `YES` | Blocks repeated incremental ADD after 5 events |
| supportive persistence/trend | `YES` | `YES` | `YES` | Often HOLD-strength; not enough for next-lot timing |
| acceleration state | `YES` | `YES` | `PARTIAL` | Often `MIXED`/`DECELERATING`; limited fresh-event signal |

No feature is recommended as a Production rule in AI. The strongest future-design candidates are semantically pre-existing, PIT-safe evidence types: SI ADD_ALLOWED/ADD_REDUCED, BQ action/band, opportunity rank, prior ADD count, and explicit acceleration/renewed-strength states.

## J — `76470` Deep Dive

`76470` produced:

- PM ADD signals: `25`
- actual ADD fills: `5`
- later PM ADDs blocked before PC: `19`
- campaign: `pc-8b52b4c89fd002ad-76470-0001`

Timeline:

| Date | Prior ADD Count | BQ | Rank | SI State | PC Treatment | Fill | POST_HOC +20BD |
| --- | ---: | --- | ---: | --- | --- | --- | ---: |
| `2022-11-28` | `0` | Full/High | `2` | `ADD_ALLOWED / HEALTHY_CONTINUATION_ENTRY` | PC ADD present, `INSUFFICIENT` | no | `0.0%` |
| `2022-11-29` | `0` | Full/High | `3` | `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION` | `COMPARABLE_MARGINAL / DEPLOY_ELIGIBLE` | yes | `0.0%` |
| `2022-11-30` | `1` | Full/High | `2` | `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION` | `COMPARABLE_MARGINAL / CASH_PREFERRED` | yes | `+3.7%` |
| `2022-12-01` | `2` | Full/High | `2` | same | `COMPARABLE_MARGINAL / CASH_PREFERRED` | yes | `0.0%` |
| `2022-12-02` | `3` | Full/High | `2` | same | `COMPARABLE_MARGINAL / CASH_PREFERRED` | yes | `+7.7%` |
| `2022-12-06` | `4` | Full/High | `2` | same | `COMPARABLE_MARGINAL / CASH_PREFERRED` | yes | `+7.4%` |
| `2022-12-07` onward | `5` | mostly High, one BUY_WAIT | rank `1-2` | `ADD_REDUCED_ONLY / CONTINUATION_WITH_CAUTION` | converted to HOLD before PC | no | mixed, later deteriorating |

After the 5th ADD, later PM ADD signals did not show a clearly new decision-time fresh-strength regime. They were mostly persistent rank/continuation/no-loss states with increasing risk votes at times. The block was driven by prior ADD history, and the evidence does not prove those blocked signals were genuinely refreshed incremental opportunities.

Answer:

```text
ARE_PRIOR_ADD_HISTORY_LIMITS_BLOCKING_GENUINELY_REFRESHED_EVIDENCE: NOT_PROVEN
```

## K — Other Major ADD Campaigns

| Symbol | PM ADD Count | Episodes | Fills | Characterization |
| --- | ---: | ---: | ---: | --- |
| `99840` | `18` | `17` material / 1 long contiguous streak | `0` | persistent HOLD-strength; BQ often BUY_WAIT/reduced; PC mostly insufficient/blocked |
| `94320` | `15` | `15` material / long contiguous periods | `1` | state-dominant top-rank signal; only 2 plausible incremental rows |
| `67310` | `15` | `13` material | `0` | persistent reduced-allocation medium-quality ADD consideration; not fresh acceleration |
| `43880` | `12` | `12` material | `0` | repeated high/medium BQ with PC insufficient/blocked; mostly state |
| `21340` | `9` | `7` material | `0` | high BQ/top rank, but PC insufficient/blocked; HOLD fresh-strength candidates also existed |

These campaigns reinforce the same pattern: PM ADD often persists as state strength; downstream evidence decides whether any incremental deployment is valid.

## L — PM ADD Predictive Information

Separate conclusions:

| Question | Classification | Rationale |
| --- | --- | --- |
| PM ADD state signal | `STRONG` | PM ADD rows are much stronger than HOLD in action score, BQ, rank, current return, and momentum. |
| PM ADD forward predictive signal | `WEAK_TO_MODERATE` | POST_HOC: higher MFE but worse 20BD median and positive-rate than HOLD. |
| PM ADD incremental-capital signal | `WEAK / NOT_ESTABLISHED` | Only 1 clear and 10 plausible incremental opportunities out of 118. |

## M — Downstream Filtering Enrichment

POST_HOC_DIAGNOSTIC_ONLY:

| Stage | Count | +5BD Mean / Median / Pos | +20BD Mean / Median / Pos | MFE20 Mean / Median |
| --- | ---: | --- | --- | --- |
| PM ADD | `118` | `+0.97% / 0.00% / 34.7%` | `-4.86% / -4.72% / 22.9%` | `+16.25% / +5.42%` |
| PC ADD present | `99` | `+1.32% / 0.00% / 36.4%` | `-5.08% / -5.36% / 23.2%` | `+17.45% / +4.41%` |
| PC selected | `11` | `-1.10% / -0.62% / 0.0%` | `+1.29% / +1.49% / 63.6%` | `+4.25% / +3.70%` |
| Runtime positive | `11` | same as PC selected | same as PC selected | same |
| Fill | `9` | `-1.06% / 0.00% / 0.0%` | `+1.94% / +1.49% / 66.7%` | `+4.69% / +3.70%` |

Classification:

```text
PARTIAL_ENRICHMENT
```

Filtering improves downside and 20BD positive-rate in the small selected/fill sample, but it does not enrich near-term +5BD continuation. Sample size is too small for causal conclusions.

## N — Root-Cause Classification

Applicable classifications:

- `PM_ADD_IS_MOSTLY_HOLD_STRENGTH`
- `PM_ADD_HAS_INCREMENTAL_PREDICTIVE_VALUE` only as `WEAK_TO_MODERATE` state/continuation signal, not next-lot timing
- `PM_ADD_MISSES_FRESH_STRENGTH_EVENTS` as `LIMITED / CANDIDATE_ONLY`
- `DOWNSTREAM_FILTERING_IMPROVES_ADD_QUALITY` as `PARTIAL_ENRICHMENT`
- `DOWNSTREAM_FILTERING_DISCARDS_USEFUL_ADD_EVIDENCE` as `UNCONFIRMED`; not proven as primary
- `MIXED`

Primary:

```text
MIXED
```

## O — Decision Gate Before Design

Recommended next branch:

```text
Branch D — mixed
```

Priority order:

1. Clarify PM ADD intent semantics: separate HOLD-strength, ADD-consideration, and executable incremental ADD candidate.
2. Audit existing SI/BQ HOLD fresh-strength candidates before changing PM rules.
3. Keep downstream filtering as a separate enrichment/control layer; do not bypass prior ADD history or Cash/risk controls without decision-time justification.
4. Only after the above, consider a read-only shadow design for marginal capital value.

No comparator design or Production parameter recommendation is made in Phase32-AI.

## Required Final Answers

1. `HOW_MANY_UNIQUE_ADD_EPISODES_EXIST_WITHIN_THE_118_SIGNALS`: `35` contiguous campaign episodes; `106` material evidence-state micro-episodes.
2. `ARE_118_PM_ADDS_MOSTLY_REPEATED_STATE_OR_FRESH_EVENTS`: `MOSTLY_REPEATED_STATE`.
3. `WHAT_AI_OR_INTELLIGENCE_INPUTS_ACTUALLY_DRIVE_PM_ADD`: PM add score, opportunity rank, current return/no-loss, trend/continuation score, downside risk, expected-edge score, Candidate/Opportunity rankings, plus downstream SI/BQ/PC evidence.
4. `DO_PM_ADD_SIGNALS_SHOW_POST_HOC_FORWARD_CONTINUATION`: `WEAK_TO_MODERATE`; higher MFE but weak 20BD median/positive-rate.
5. `DO_CLEAR_PLAUSIBLE_HOLD_STRENGTH_CLASSES_SEPARATE_OUTCOMES`: `PARTIAL`; plausible/clear rows show lower downside and better +20BD rate, but sample is tiny.
6. `DID_THE_9_FILLED_ADDS_OUTPERFORM_REJECTED_ADDS`: `PARTIAL`; filled rows had better +20BD and lower MAE, worse +5BD, sample `n=9`.
7. `DOES_DOWNSTREAM_FILTERING_ENRICH_ADD_SIGNAL_QUALITY`: `PARTIAL_ENRICHMENT`.
8. `DID_PM_MISS_EXISTING_FRESH_STRENGTH_EVENTS`: `YES_LIMITED_CANDIDATE_ONLY`; 19 strict HOLD candidates had existing SI/BQ/rank/positive-return fresh-strength evidence.
9. `IS_PM_ADD_STATE_DOMINANT_OR_CHANGE_DOMINANT`: `STATE_DOMINANT` (`103/118`).
10. `DOES_PM_ADD_HAVE_INCREMENTAL_CAPITAL_TIMING_VALUE`: `WEAK / NOT_ESTABLISHED`.
11. `WHAT_HAPPENED_IN_76470_AFTER_THE_FIRST_5_ADDS_AT_DECISION_TIME`: PM kept emitting ADD from rank/continuation/no-loss state, but SI prior-add-history gating converted it to HOLD before PC; no clearly refreshed incremental evidence was proven.
12. `ARE_PRIOR_ADD_HISTORY_LIMITS_BLOCKING_GENUINELY_REFRESHED_EVIDENCE`: `NOT_PROVEN`.
13. `IS_THE_MAIN_PROBLEM_PM_SIGNAL_QUALITY, DOWNSTREAM_FILTERING, OPPORTUNITY_SCARCITY, OR_MIXED`: `MIXED`, led by PM signal semantics and limited downstream enrichment/bridge effects.
14. `IS_ANY_DESIGN_WORK_JUSTIFIED_YET`: `YES`, but only intent-taxonomy / read-only characterization design, not comparator activation or parameter tuning.
15. `WHAT_IS_THE_NEXT_HIGHEST_VALUE_ACTION`: define a read-only PM ADD intent taxonomy using existing PIT evidence to distinguish `HOLD_STRENGTH`, `ADD_CONSIDERATION`, and `EXECUTABLE_INCREMENTAL_ADD_CANDIDATE`, then classify existing artifacts before any Strategy change.

Final judgment:

```text
PHASE32_AI_PM_ADD_SIGNAL_IS_STATE_STRENGTH_WITH_LIMITED_INCREMENTAL_TIMING_VALUE
```
