# Phase31-G17 - PIT-Safe Market Structure / Recovery Quality Separability Audit

## Scope

Task type: READ-ONLY MARKET-STRUCTURE / RECOVERY-QUALITY RESEARCH AUDIT.

Target run:

`runtime-test-historical-extended-smoke-20260822T174358377089Z`

No implementation, Strategy change, Market Context change, PM change, BUY/SELL
change, threshold tuning, parameter tuning, feature addition, config change,
fresh-run, resume, replay, or Historical rerun was executed.

The target run was still active during this audit. The snapshot was resolved
from completed business-day evidence and `day_completion` markers only.
Partially written next-day artifacts were excluded.

## Prior Evidence Used

Minimum required prior reports were read and used:

- `docs/phase_reports/phase31_g14_post_peak_performance_deceleration_root_cause_audit.md`
- `docs/phase_reports/phase31_g15_post_peak_loser_expansion_pit_separability_audit.md`
- `docs/phase_reports/phase31_g16_production_decision_temporal_data_lineage_integrity_audit.md`

G14 established that POST degradation was multi-causal and primarily driven by
average loser worsening, with RECOVERY/CORRECTION loss concentration and
false-recovery/re-risking losses. G15 established weak individual loser/winner
PIT separability and found entry exposure/re-risk context more informative than
rank or BUY quality alone. G16 established that target performance evidence is
not explained by information leakage.

## Snapshot

- `RUN_STATUS`: `RUNNING`
- `SNAPSHOT_COMPLETED_BUSINESS_DAYS`: `182`
- `SNAPSHOT_LATEST_COMPLETED_DATE`: `2023-06-28`
- `next_job` at read time: `2023-06-29:market_refresh`
- `day_completion` marker present for all `182` completed days
- `2023-06-29` was not included because it did not have completed-day evidence

`SNAPSHOT_INTEGRITY = PASS`

## Canonical Recovery Episode Definition

G17 did not define episodes by future PnL.

Canonical recovery/re-risk episodes were identified from contemporaneous runtime
state only:

1. current regime or contemporaneous structure indicates market improvement:
   `RECOVERY` / `BULL`, or positive short-term breadth/return improvement,
2. the prior 1-5 business days contained a risk-off marker:
   `BEAR` / `CORRECTION`, `RANGE`, low portfolio exposure, or a local equity
   trough already visible at T0,
3. the portfolio began re-risking or renewed deployment:
   BUY/ADD activity, or a same-day/nearby exposure increase,
4. adjacent candidates within two business days were merged to avoid counting a
   single re-risk sequence multiple times.

Subsequent 1BD/3BD/5BD returns were used only for post-hoc research labeling:

- `SUCCESSFUL_RECOVERY`: positive 5BD follow-through without material near-term
  drawdown in the observed next-5BD path
- `FAILED_RECOVERY`: material 1-5BD damage or negative 5BD follow-through
- `MIXED_RECOVERY`: neither clean success nor clean failure
- `UNRESOLVED_RECOVERY`: insufficient next-5BD evidence in the active run

These labels are not production features and no threshold is recommended.

## Episode Inventory

| T0 | Label | Regime path | T0 exposure | BUY | Breadth 20D | Breadth 5D | Return 5D | Vol 20D | Worst next 5BD | Next 5BD | Churn 5BD |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2023-03-31 | MIXED | RANGE -> RECOVERY | 41.1% | 3 | 47.0% | 65.0% | +1.19% | 1.91% | -1.01% | -1.49% | 4 |
| 2023-04-13 | MIXED | BULL -> RECOVERY | 41.4% | 3 | 57.3% | 75.3% | +2.02% | 1.83% | -2.97% | -1.53% | 3 |
| 2023-04-25 | MIXED | RECOVERY -> BULL | 17.0% | 2 | 64.7% | 51.1% | -0.17% | 1.68% | -0.09% | +1.98% | 2 |
| 2023-04-28 | SUCCESSFUL | RANGE -> RECOVERY | 70.4% | 1 | 60.6% | 60.9% | +0.70% | 1.64% | +0.20% | +4.77% | 3 |
| 2023-05-08 | FAILED | RECOVERY -> BULL | 73.5% | 2 | 72.6% | 77.8% | +2.29% | 1.59% | -3.21% | -3.63% | 2 |
| 2023-05-17 | FAILED | BULL -> BULL | 45.1% | 1 | 59.5% | 47.4% | -0.11% | 1.83% | -8.17% | +0.37% | 0 |
| 2023-05-22 | MIXED | RECOVERY -> BULL | 35.1% | 1 | 60.7% | 53.1% | +0.84% | 1.84% | -0.82% | +0.43% | 2 |
| 2023-05-29 | FAILED | RANGE -> BULL | 47.2% | 6 | 54.9% | 30.6% | -1.01% | 1.88% | -3.31% | -1.41% | 4 |
| 2023-06-02 | SUCCESSFUL | CORRECTION -> RECOVERY | 54.7% | 4 | 45.5% | 52.1% | +0.69% | 1.91% | -1.79% | +2.98% | 4 |
| 2023-06-07 | FAILED | RECOVERY -> RECOVERY | 90.5% | 6 | 47.2% | 78.2% | +2.61% | 1.91% | -3.52% | -4.01% | 2 |
| 2023-06-20 | FAILED | BULL -> BULL | 29.2% | 2 | 70.8% | 68.5% | +1.89% | 1.74% | -1.49% | -2.42% | 0 |
| 2023-06-27 | UNRESOLVED | BULL -> BULL | 15.2% | 2 | 73.1% | 35.1% | -1.29% | 1.72% | n/a | n/a | 0 |

Counts:

- `RECOVERY_EPISODE_COUNT = 12`
- `SUCCESSFUL_RECOVERY_COUNT = 2`
- `FAILED_RECOVERY_COUNT = 5`
- `MIXED_RECOVERY_COUNT = 4`
- `UNRESOLVED_RECOVERY_COUNT = 1`

Reconciliation against G15:

- G15 failed sequence `2023-03-31` is present, but G17 labels it `MIXED`
  because the next-5BD path did not meet the failed-recovery post-hoc label.
- G15 failed sequence `2023-05-10` is represented by the broader G17
  `2023-05-08` recovery/re-risk episode.
- G15 failed sequence `2023-05-30` is represented by G17 `2023-05-29`.
- G15 `2023-05-18/2023-05-19` shock sequence is represented by G17
  `2023-05-17`; per G13 this remains valid performance evidence, but it is not
  treated as a production feature.

## Existing Market Structure Component Inventory

| Name | Producer | Source | PIT status | Semantic purpose | Current consumer / authority | Missing rate | Available range |
| --- | --- | --- | --- | --- | --- | ---: | --- |
| `regime_state` | `strategy.market_context` | J-Quants equal-weight market proxy | PASS | Canonical market regime taxonomy | Strategy, BUY quality, Portfolio Policy/Construction | 0/181 | all completed days |
| `trend_value` / `return_20d_equal_weight` | `strategy.market_context` | J-Quants daily quotes adjusted close | PASS | 20BD market trend | Regime mapping / Market Context | 0/181 | all completed days |
| `return_5d_equal_weight` | `strategy.market_context.metrics` | J-Quants daily quotes adjusted close | PASS | short-term market continuation diagnostic | Recorded in Market Context metrics | 0/181 | all completed days |
| `breadth_value` / `breadth_20d_positive_ratio` | `strategy.market_context` | J-Quants daily quotes adjusted close | PASS | broad trend participation | Regime quality / BUY quality modifier | 0/181 | all completed days |
| `breadth_5d_positive_ratio` | `strategy.market_context.metrics` | J-Quants daily quotes adjusted close | PASS | short-term participation diagnostic | Recorded in Market Context metrics | 0/181 | all completed days |
| `volatility_value` / `volatility_20d_equal_weight` | `strategy.market_context` | J-Quants daily quotes adjusted close | PASS | realized downside/risk proxy | Market Context / risk modifier | 0/181 | all completed days |
| `sector_dispersion` / `sector_return_20d_dispersion` | `strategy.market_context` | J-Quants listed issues sector classification + quotes | PASS | sector participation / dispersion proxy | Market Context | 0/181 | all completed days |
| `confidence` / `uncertainty` | `strategy.market_context` | coverage and metric agreement | PASS | source and internal agreement confidence | Market Context consumers | 0/181 | all completed days |
| `benchmark_coverage` | `strategy.market_context` | listed common equities with PIT quotes | PASS | source coverage and confidence input | Market Context authority | 0/181 | all completed days |
| `source_authority_status` / temporal safety | `strategy.market_context` | Historical as-of view | PASS | PIT admissibility | Runtime Strategy lineage | 0/181 | all completed days |

`EXISTING_MARKET_STRUCTURE_COMPONENT_COUNT = 10`

`EXISTING_RECOVERY_QUALITY_EVIDENCE_SUFFICIENT_FOR_RESEARCH = PARTIAL`

The existing evidence is sufficient for descriptive research, but not sufficient
for a strong production-quality recovery classifier. The episode count is small
and successful/failed cohorts overlap heavily.

## J-Quants Source Inventory

| Source name | Dataset role | Available from | PIT rule | Currently materialized | Currently used by Market Context |
| --- | --- | --- | --- | --- | --- |
| J-Quants normalized daily quotes | market proxy, 5D/20D returns, breadth, volatility | Historical as-of daily input windows; sample `2023-03-24` window `2023-02-22 -> 2023-03-24`, sample `2023-06-26` window `2023-05-29 -> 2023-06-26` | source rows `<= business_date`; future rows rejected | YES | YES |
| J-Quants listed issues | listed universe and sector classification | Historical as-of daily input windows | effective/classification date `<= business_date` | YES | YES |
| J-Quants trading calendar | business-day sequencing and source windows | Historical as-of daily input windows | calendar date `<= business_date` | YES | YES |
| J-Quants raw daily quotes | canonical acquisition/source lineage | repository operations source | as-of materialized through Historical support before use | YES | INDIRECT |
| J-Quants corporate actions | corporate-event safety and adjustment authority | optional source | effective/known date must be `<= business_date` | YES/PARTIAL by contract | NO for recovery-quality Market Context |
| J-Quants earnings schedule | corporate-event schedule | optional source; non-PIT calendar gap from G16 | not valid as recovery-quality decision explanation in this run | YES/PARTIAL by contract | NO |
| J-Quants financial statements | disclosure / financial event context | optional source | publication/disclosure date `<= business_date` | YES/PARTIAL by contract | NO |

`NEW_EXTERNAL_DATA_REQUIRED_FOR_G17 = NO`

G17 did not use JPX paid data, futures data, external index data, or any new data
source.

## Successful vs Failed Recovery Comparison

Episode-level distributions:

| Component | Successful | Failed | Overlap | Direction | Separability |
| --- | --- | --- | --- | --- | --- |
| 20D breadth | n=2, mean 53.0%, median 53.0%, range 45.5%-60.6% | n=5, mean 61.0%, median 59.5%, range 47.2%-72.6% | High | Failed often looked at least as broad | NONE |
| 5D breadth | n=2, mean 56.5%, median 56.5%, range 52.1%-60.9% | n=5, mean 60.5%, median 68.5%, range 30.6%-78.2% | High | Mixed; one clear weak 5D breadth failure | WEAK |
| 20D trend | n=2, mean +1.15%, median +1.15% | n=5, mean +2.84%, median +2.24% | High | Failed often had stronger 20D trend | NONE |
| 5D return | n=2, mean +0.69% | n=5, mean +1.13%, median +1.89% | High | Failed often had stronger short bounce | NONE |
| 20D volatility | n=2, mean 1.78% | n=5, mean 1.79% | High | No useful difference | NONE |
| confidence | n=2, mean 0.987 | n=5, mean 0.986 | High | No useful difference | NONE |
| T0 exposure | n=2, mean 62.5% | n=5, mean 57.1%, range 29.2%-90.5% | High | Failure includes both low and high exposure | WEAK |
| BUY count | n=2, mean 2.5 | n=5, mean 3.4 | Moderate | Failed episodes more often had faster deployment | WEAK |
| BUY quality mean | n=2, mean 0.595 | n=5, mean 0.625 | High | Failed looked better, not worse | NONE |
| Regime churn 5BD | n=2, mean 3.5 | n=5, mean 1.6 | High | Churn does not isolate failures | NONE |

`BEST_EXISTING_MARKET_STRUCTURE_DISCRIMINATORS =
SHORT_TERM_BREADTH_TREND_DISAGREEMENT, FAST_RERISK_BUY_COUNT, WEAK_MARKET_STRUCTURE_PLUS_FAST_RERISK_INTERACTION`

The best signals are interaction-level and qualitative. Simple 20D breadth,
20D trend, static BULL/RECOVERY label, or BUY quality do not cleanly separate
successful from failed recovery episodes.

## Breadth / Participation

Failed recoveries were not uniformly narrow. Some failed episodes had strong
20D breadth and strong 5D breadth, especially `2023-05-08`. However, the clearest
fragile failure, `2023-05-29`, had low 5D breadth (`30.6%`) despite a BULL
regime. `2023-06-07` had neutral 20D breadth but very strong 5D breadth, then
failed, suggesting a sharp bounce rather than broad persistent health.

`BREADTH_RECOVERY_SEPARABILITY = WEAK`

`NARROW_RECOVERY_FAILURE_PATTERN = PARTIAL`

Breadth is informative only when combined with path and re-risk speed. It is not
a standalone discriminator.

## Momentum Persistence

At T0, failed episodes often had stronger 5D returns than successful episodes:

- successful mean 5D return: `+0.69%`
- failed mean 5D return: `+1.13%`

This means the existing short-term return signal can identify a bounce, but not
reliably distinguish healthy continuation from fragile rebound. The more useful
observation is disagreement: a positive short bounce with weak or neutral
broader participation, or a strong short bounce followed by rapid exposure
deployment.

`MOMENTUM_PERSISTENCE_SEPARABILITY = WEAK`

## Volatility / Downside-Risk Structure

All identified episodes had `volatility_state = NORMAL`; numeric 20D volatility
overlapped tightly:

- successful mean: `1.78%`
- failed mean: `1.79%`
- mixed mean: `1.82%`

Existing 20D volatility did not flag the failed recoveries as a distinct
elevated-downside-risk state. This does not contradict G14's larger POST
downside-deviation finding; it means the current Market Context volatility
component is too coarse at episode T0 to separate false recoveries.

`VOLATILITY_RECOVERY_SEPARABILITY = NONE`

`FAILED_RECOVERY_ELEVATED_DOWNSIDE_RISK = NO`

## Regime Stability / Transition Quality

Static labels alone are not sufficient:

- failed episodes include `RECOVERY -> BULL`, `BULL -> BULL`,
  `RANGE -> BULL`, and `RECOVERY -> RECOVERY`
- successful episodes include `RANGE -> RECOVERY` and
  `CORRECTION -> RECOVERY`

Regime churn also did not isolate failures. Successful episodes had higher mean
5BD churn than failed episodes in this sample, partly because the successful
cohort includes the early-June transition sequence.

`REGIME_PATH_SEPARABILITY = WEAK`

`REGIME_CHURN_FALSE_RECOVERY_PATTERN = PARTIAL`

The useful signal is not the label path by itself. It is whether the path is
paired with fragile market structure and fast re-risking.

## Market Context Internal Agreement

The clearest agreement/disagreement evidence:

- `2023-05-29`: BULL label, but 5D breadth `30.6%`, 5D equal-weight return
  `-1.01%`, and BUY count `6`; this is a conflicted recovery/re-risk pattern.
- `2023-06-07`: RECOVERY label, 5D breadth `78.2%`, but 20D breadth only
  `47.2%`, T0 exposure `90.5%`, and BUY count `6`; this looks more like a
  fast rebound/re-risk episode than a stable broad recovery.
- `2023-04-28`: RECOVERY label with strong 20D breadth, positive 5D breadth,
  positive 5D return, normal volatility, and follow-through success.

`MARKET_CONTEXT_INTERNAL_AGREEMENT_SEPARABILITY = WEAK`

`CONFLICTED_RECOVERY_PATTERN_SUPPORTED = PARTIAL`

## Portfolio Re-Risk Speed

Failed episodes had more BUY deployment on average:

- successful mean BUY count: `2.5`
- failed mean BUY count: `3.4`
- mixed mean BUY count: `2.25`

The strongest failure episodes by interaction were:

- `2023-05-29`: BUY count `6`, exposure moved from prior risk-off state toward
  47.2%, weak 5D breadth, then worst next-5BD day `-3.31%`
- `2023-06-07`: BUY count `6`, exposure `90.5%`, neutral 20D breadth, then
  next-5BD `-4.01%`

But exposure alone is not enough: `2023-04-28` had 70.4% exposure and succeeded.

`RERISK_SPEED_SEPARABILITY = WEAK`

`FAILED_RECOVERY_FASTER_RERISK = PARTIAL`

## Market Structure x Re-Risk Interaction

Using qualitative existing states only:

- `WEAK_MARKET_STRUCTURE + FAST_RERISK`: `2` failed episodes
  (`2023-05-29`, `2023-06-07`)
- `GOOD_MARKET_STRUCTURE + FAST_RERISK`: `1` failed episode (`2023-05-08`)
- `WEAK_MARKET_STRUCTURE + SLOW_RERISK`: `1` failed episode (`2023-05-17`)
- `GOOD_MARKET_STRUCTURE + SLOW_RERISK`: `1` failed episode (`2023-06-20`)

`MARKET_STRUCTURE_RERISK_INTERACTION_SUPPORTED = PARTIAL`

`DOMINANT_FAILURE_INTERACTION_CLASS = WEAK_MARKET_STRUCTURE + FAST_RERISK`

The dominant class is meaningful but not exclusive. This supports further
Market Context / risk-adaptation research, not a direct production rule.

## Individual Candidate Quality

G17 confirms G15's finding. Candidate quality does not explain recovery failure:

- successful episode mean BUY quality: `0.595`
- failed episode mean BUY quality: `0.625`
- failed episodes often looked better by BUY quality and 20D trend than
  successful episodes

`INDIVIDUAL_CANDIDATE_QUALITY_EXPLAINS_RECOVERY_FAILURE = NO`

The primary research direction should remain Market Context / risk adaptation
and re-risk pacing, not a simple tighter BUY filter.

## Winner Preservation Control

Potentially useful discriminators overlap with successful recoveries and
winner-preserving behavior:

- strong 20D breadth would not block failures because several failures also had
  strong breadth
- weak/neutral 20D breadth plus fast re-risk catches important failures, but
  overlaps with successful `2023-06-02`
- high BUY quality would not protect the system because failed episodes often
  had higher BUY quality than successful episodes
- exposure/re-risk controls could affect winner participation if applied too
  broadly

`WINNER_PRESERVATION_RISK = MODERATE`

No production threshold should be selected from this window.

## Recovery Quality Separability Judgment

`RECOVERY_QUALITY_SEPARABILITY_JUDGMENT =
RECOVERY_QUALITY_WEAKLY_PIT_SEPARABLE_MORE_RESEARCH_REQUIRED`

G17 finds weak but real PIT-safe structure:

- individual candidate quality is weak/non-explanatory,
- static regime label is weak/non-explanatory,
- broad 20D trend/breadth can look good before failures,
- the most useful evidence is interactional:
  short-term breadth/trend disagreement, fast re-risking, and fragile Market
  Context agreement.

This justifies design research but not production tuning.

## Existing Evidence vs Missing Evidence

| Concept | Classification |
| --- | --- |
| 20D market trend | ALREADY_AVAILABLE_AND_USED |
| 20D breadth | ALREADY_AVAILABLE_AND_USED |
| 20D volatility | ALREADY_AVAILABLE_AND_USED |
| sector dispersion | ALREADY_AVAILABLE_AND_USED |
| Market Context confidence / uncertainty | ALREADY_AVAILABLE_AND_USED |
| 5D return and 5D breadth path | ALREADY_AVAILABLE_BUT_NOT_USED_FOR_RECOVERY_QUALITY |
| regime path / recent transition sequence | ALREADY_AVAILABLE_BUT_NOT_USED_FOR_RECOVERY_QUALITY |
| portfolio re-risk speed / BUY deployment count | ALREADY_AVAILABLE_BUT_NOT_USED_FOR_RECOVERY_QUALITY |
| market-structure x re-risk qualitative interaction | ALREADY_AVAILABLE_BUT_NOT_USED_FOR_RECOVERY_QUALITY |
| cross-sectional volume participation at market level | DERIVABLE_FROM_EXISTING_JQUANTS_PIT_DATA |
| advancing/declining volume confirmation | DERIVABLE_FROM_EXISTING_JQUANTS_PIT_DATA |
| sector participation breadth beyond dispersion | DERIVABLE_FROM_EXISTING_JQUANTS_PIT_DATA |
| external index/futures confirmation | NOT_CURRENTLY_DERIVABLE_WITH_ALLOWED_DATA |

`RECOVERY_QUALITY_INFORMATION_GAP_CLASS =
ALREADY_AVAILABLE_BUT_NOT_USED_FOR_RECOVERY_QUALITY_PLUS_DERIVABLE_FROM_EXISTING_JQUANTS_PIT_DATA`

## Investment Philosophy Fit

The evidence supports the philosophy-level distinction only partially:

- weak/fragile recovery: avoid assuming the bottom is in, preserve optionality,
  and avoid immediate full re-risking when recovery evidence is conflicted
- healthy recovery: allow normal re-risking when participation and persistence
  are internally consistent

This is consistent with "capture the middle of the move" and does not imply
bottom-picking or blanket re-entry bans.

`RECOVERY_QUALITY_ADAPTATION_PHILOSOPHY_SUPPORTED = PARTIAL`

## Architecture Placement

If pursued later, recovery-quality semantics should belong in Market Context as
a recovery-quality substate or confidence/fragility evidence consumed by
Portfolio Policy / Portfolio Construction for risk pacing.

It should not become a second regime classifier and should not move SELL
authority.

`RECOVERY_QUALITY_SEMANTIC_OWNER_CANDIDATE =
Market Context primary; Portfolio Policy / Portfolio Construction consumer`

`SECOND_REGIME_CLASSIFIER_RECOMMENDED = NO`

## Required Summary Output

`PRIMARY_JUDGMENT =
PHASE31_G17_RECOVERY_QUALITY_PARTIALLY_PIT_SEPARABLE_MORE_CHARACTERIZATION_REQUIRED`

`TARGET_RUN_ID =
runtime-test-historical-extended-smoke-20260822T174358377089Z`

`SNAPSHOT_LATEST_COMPLETED_DATE = 2023-06-28`

`SNAPSHOT_COMPLETED_BUSINESS_DAYS = 182`

`RUN_STATUS = RUNNING`

`SNAPSHOT_INTEGRITY = PASS`

`RECOVERY_EPISODE_COUNT = 12`

`SUCCESSFUL_RECOVERY_COUNT = 2`

`FAILED_RECOVERY_COUNT = 5`

`MIXED_RECOVERY_COUNT = 4`

`UNRESOLVED_RECOVERY_COUNT = 1`

`EXISTING_MARKET_STRUCTURE_COMPONENT_COUNT = 10`

`EXISTING_RECOVERY_QUALITY_EVIDENCE_SUFFICIENT_FOR_RESEARCH = PARTIAL`

`BEST_EXISTING_MARKET_STRUCTURE_DISCRIMINATORS =
SHORT_TERM_BREADTH_TREND_DISAGREEMENT, FAST_RERISK_BUY_COUNT, WEAK_MARKET_STRUCTURE_PLUS_FAST_RERISK_INTERACTION`

`BREADTH_RECOVERY_SEPARABILITY = WEAK`

`NARROW_RECOVERY_FAILURE_PATTERN = PARTIAL`

`MOMENTUM_PERSISTENCE_SEPARABILITY = WEAK`

`VOLATILITY_RECOVERY_SEPARABILITY = NONE`

`FAILED_RECOVERY_ELEVATED_DOWNSIDE_RISK = NO`

`REGIME_PATH_SEPARABILITY = WEAK`

`REGIME_CHURN_FALSE_RECOVERY_PATTERN = PARTIAL`

`MARKET_CONTEXT_INTERNAL_AGREEMENT_SEPARABILITY = WEAK`

`CONFLICTED_RECOVERY_PATTERN_SUPPORTED = PARTIAL`

`RERISK_SPEED_SEPARABILITY = WEAK`

`FAILED_RECOVERY_FASTER_RERISK = PARTIAL`

`MARKET_STRUCTURE_RERISK_INTERACTION_SUPPORTED = PARTIAL`

`DOMINANT_FAILURE_INTERACTION_CLASS =
WEAK_MARKET_STRUCTURE + FAST_RERISK`

`INDIVIDUAL_CANDIDATE_QUALITY_EXPLAINS_RECOVERY_FAILURE = NO`

`WINNER_PRESERVATION_RISK = MODERATE`

`RECOVERY_QUALITY_SEPARABILITY_JUDGMENT =
RECOVERY_QUALITY_WEAKLY_PIT_SEPARABLE_MORE_RESEARCH_REQUIRED`

`RECOVERY_QUALITY_INFORMATION_GAP_CLASS =
ALREADY_AVAILABLE_BUT_NOT_USED_FOR_RECOVERY_QUALITY_PLUS_DERIVABLE_FROM_EXISTING_JQUANTS_PIT_DATA`

`RECOVERY_QUALITY_ADAPTATION_PHILOSOPHY_SUPPORTED = PARTIAL`

`RECOVERY_QUALITY_SEMANTIC_OWNER_CANDIDATE =
Market Context primary; Portfolio Policy / Portfolio Construction consumer`

`SECOND_REGIME_CLASSIFIER_RECOMMENDED = NO`

`FUTURE_INFORMATION_USED_AS_PRODUCTION_INPUT = NO`

`HISTORICAL_OUTCOME_USED_TO_SELECT_PRODUCTION_THRESHOLD = NO`

`EVIDENCE_USED_AS_PRODUCTION_DATA_SOURCE = NO`

`NEW_EXTERNAL_DATA_USED = NO`

`NEW_FEATURE_IMPLEMENTED = NO`

`NEW_THRESHOLD_SELECTED = NO`

`STRATEGY_CHANGED = NO`

`MARKET_CONTEXT_CHANGED = NO`

`PM_CHANGED = NO`

`BUY_LOGIC_CHANGED = NO`

`SELL_LOGIC_CHANGED = NO`

`PERFORMANCE_TUNING_RECOMMENDED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`REPLAY_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`GIT_DIFF_CHECK = PASS`

`NEXT_TASK_RECOMMENDATION =
Design-only characterization of Recovery Quality under Market Context ownership,
using existing PIT J-Quants-derived breadth/path/participation evidence; do not
select a production threshold from this run window.`
