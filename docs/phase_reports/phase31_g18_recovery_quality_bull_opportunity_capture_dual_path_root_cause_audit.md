# Phase31-G18 - Recovery Quality / BULL Opportunity Capture Dual-Path Root-Cause Audit

## Scope

Task type: READ-ONLY ROOT-CAUSE / MARKET-STRUCTURE / OPPORTUNITY-CAPTURE AUDIT.

Target run:

`runtime-test-historical-extended-smoke-20260822T174358377089Z`

No implementation, Strategy change, Market Context change, Portfolio Policy /
Portfolio Construction change, PM change, BUY/SELL change, ADD change,
threshold tuning, parameter tuning, production feature addition, config change,
fresh-run, resume, replay, or Historical rerun was executed.

The target run was still active during this audit. The snapshot was resolved
from canonical `run_state.json` plus completed-day `day_completion` evidence.
Partially materialized next-day artifacts were excluded.

## Prior Evidence Used

Required reports read and used:

- `docs/phase_reports/phase31_g14_post_peak_performance_deceleration_root_cause_audit.md`
- `docs/phase_reports/phase31_g15_post_peak_loser_expansion_pit_separability_audit.md`
- `docs/phase_reports/phase31_g16_production_decision_temporal_data_lineage_integrity_audit.md`
- `docs/phase_reports/phase31_g17_pit_safe_market_structure_recovery_quality_separability_audit.md`

G14/G15/G17 jointly establish that POST degradation is not explained by a simple
BUY-quality or regime-label problem. G16 establishes that the target performance
evidence remains valid and is not explained by future-information leakage.

## Snapshot

- `RUN_STATUS`: `RUNNING`
- `G18_SNAPSHOT_COMPLETED_BUSINESS_DAYS`: `194`
- `G18_SNAPSHOT_LATEST_COMPLETED_DATE`: `2023-07-14`
- next job at read time: `2023-07-18:market_refresh`
- `2023-07-18` excluded because completed-day evidence was not present

`SNAPSHOT_INTEGRITY = PASS`

## Daily Funnel Reconstruction

`DAILY_MARKET_OPPORTUNITY_PORTFOLIO_FUNNEL = MATERIALIZED_IN_REPORT`

The audit reconstructed daily evidence from `2023-02-01` through
`2023-07-14`, using existing artifacts only:

- Market: `strategy/market_context.json`
- BUY quality: `strategy/buy_quality_decisions.json`
- Runtime planning: `strategy/runtime_planning.json`
- Portfolio Construction: `strategy/portfolio_construction.json`
- Valuation/exposure/cash: `current_valuation_refresh/valuation_projection.json`
- Fills: `execution/fills.json`

Regime aggregate, `2023-02-01 -> 2023-07-14`:

| Regime | Days | Avg exposure | Avg positions | BUY fills | SELL fills | BUY plans/day | Full eligible/day | BUY_WAIT/day | Avg BUY quality | Avg 20D breadth | Avg 5D breadth |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BEAR | 3 | 32.0% | 3.3 | 4 | 4 | 1.67 | 4.67 | 14.00 | 0.498 | 23.7% | 32.1% |
| BULL | 67 | 60.0% | 8.6 | 114 | 130 | 2.75 | 4.52 | 11.28 | 0.537 | 68.4% | 57.7% |
| CORRECTION | 5 | 57.4% | 6.6 | 7 | 9 | 3.00 | 5.80 | 11.80 | 0.535 | 38.6% | 26.8% |
| RANGE | 18 | 65.6% | 7.8 | 34 | 36 | 3.50 | 5.28 | 12.72 | 0.530 | 48.3% | 36.0% |
| RECOVERY | 20 | 61.4% | 7.6 | 27 | 34 | 2.00 | 4.45 | 11.30 | 0.518 | 52.6% | 62.9% |

Interpretation:

- BULL had positive market structure on average and regular BUY opportunity
  flow, but did not guarantee full deployment.
- BUY_WAIT volume remained high even in BULL.
- BULL exposure and position count were unstable because SELL/EXIT pressure and
  downstream Portfolio Construction constraints often offset BUY availability.

## BULL Cash-Drift Episodes

Episodes were constructed descriptively, not as production thresholds:

1. BULL persisted for a meaningful sequence,
2. exposure declined materially or remained low,
3. cash rose or remained high,
4. positions fell or remained unusually low.

`BULL_CASH_DRIFT_EPISODE_COUNT = 4`

| Episode | Regime path | Start exp | Lowest exp | End exp | Start pos | Min pos | End pos | BUY fills | SELL fills | BUY plans | Full eligible | BUY_WAIT | PC dominant reasons | Classification |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 2023-02-24 -> 2023-03-13 | BULL | 89.2% | 34.7% | 34.7% | 15 | 5 | 5 | 18 | 34 | 35 | 46 | 127 | min lot exceeds safety cap / remaining budget, semantic reentry blocks | MIXED |
| 2023-04-14 -> 2023-04-20 | BULL | 31.7% | 31.1% | 31.1% | 5 | 4 | 5 | 9 | 11 | 9 | 12 | 67 | semantic reentry blocks, duplicate existing candidates, limited executable lot admission | SYSTEM_CAPTURE_FAILURE |
| 2023-05-08 -> 2023-05-18 | BULL | 73.5% | 40.9% | 49.0% | 8 | 3 | 5 | 14 | 16 | 14 | 30 | 118 | safety hard cap, reentry blocks, unsupported broker category, lot infeasibility | MIXED |
| 2023-06-12 -> 2023-07-07 | BULL | 72.4% | 15.2% | 90.2% | 10 | 2 | 10 | 30 | 29 | 43 | 114 | 232 | concentration limit, safety hard cap, reentry blocks, lot infeasibility | MIXED |

Distribution:

`BULL_LOW_EXPOSURE_JUSTIFICATION_DISTRIBUTION =
SYSTEM_CAPTURE_FAILURE: 1, MIXED: 3`

`MARKET_BREADTH_SUPPORTS_LOW_EXPOSURE = PARTIAL`

Market breadth did not generally justify low exposure across the full BULL
drift windows. However, late-June and early-July short-horizon participation
weakened materially, so some low exposure was market-structure justified inside
the longer June/July episode.

## Visible June / July Sequence

The operator-requested visible sequence was included. Selected rows:

| Date | Regime | 20D breadth | 5D breadth | 5D return | Exposure | Positions | Cash | BUY fills | SELL fills | BUY plans | Full eligible | BUY_WAIT | PC residual reason |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 2023-06-12 | BULL | 55.8% | 62.4% | +1.40% | 72.4% | 10 | 329,460 | 3 | 1 | 4 | 6 | 7 | CONCENTRATION_LIMIT |
| 2023-06-19 | BULL | 64.5% | 69.8% | +2.01% | 26.5% | 5 | 857,260 | 1 | 3 | 2 | 7 | 6 | CONCENTRATION_LIMIT |
| 2023-06-21 | BULL | 74.8% | 68.5% | +2.09% | 26.1% | 2 | 862,160 | 0 | 0 | 0 | 5 | 4 | CONCENTRATION_LIMIT |
| 2023-06-26 | BULL | 73.1% | 37.8% | -0.84% | 18.0% | 2 | 928,460 | 0 | 1 | 0 | 6 | 16 | NO_ELIGIBLE_OPPORTUNITY |
| 2023-06-27 | BULL | 73.1% | 35.1% | -1.29% | 15.2% | 2 | 962,760 | 1 | 0 | 2 | 5 | 18 | CONCENTRATION_LIMIT |
| 2023-06-28 | BULL | 82.2% | 46.8% | -0.49% | 25.6% | 3 | 851,560 | 1 | 0 | 2 | 7 | 13 | CONCENTRATION_LIMIT |
| 2023-07-06 | BULL | 71.8% | 43.9% | -0.25% | 77.2% | 9 | 263,700 | 6 | 0 | 7 | 5 | 18 | CONCENTRATION_LIMIT |
| 2023-07-07 | BULL | 64.3% | 36.0% | -0.65% | 90.2% | 10 | 113,100 | 2 | 0 | 4 | 1 | 21 | CAPITAL_BELOW_NEXT_LOT |

This sequence supports both sides:

- Path B: `2023-06-19 -> 2023-06-28` shows high cash/low exposure despite BULL
  and multiple full-eligible decisions.
- Path A risk: `2023-07-06 -> 2023-07-07` rapidly restored exposure while 5D
  breadth/return were weak, then the regime moved to RANGE on `2023-07-10`
  and CORRECTION on `2023-07-14`.

## Candidate Availability vs Deployment

Across the four BULL cash-drift episodes:

- Full-eligible BUY quality decision-days: `202`
- BUY fills: `71`
- Diagnostic qualified-but-not-deployed decision-day gap: `131`

This count is diagnostic and may include repeated symbol-days. It is not a
unique-symbol production defect count.

Dominant blocker evidence:

- `CONCENTRATION_LIMIT`
- `minimum_lot_exceeds_safety_hard_cap`
- `semantic_reentry_recovery_blocked`
- `semantic_reentry_cooldown_blocked`
- `lot_aware_infeasible_allocations_reallocated_or_cash`
- `COMPETITION_EXHAUSTED`
- `NO_ELIGIBLE_OPPORTUNITY` on specific days such as `2023-06-26`
- `CAPITAL_BELOW_NEXT_LOT` after heavy redeployment

`BULL_OPPORTUNITY_FUNNEL_DOMINANT_BLOCKER =
PORTFOLIO_CONSTRUCTION_ZERO / CONCENTRATION_AND_LOT_CONSTRAINTS_WITH_REENTRY_BLOCKS`

`UPSTREAM_OPPORTUNITY_SCARCITY = PARTIAL`

`DOWNSTREAM_CAPITAL_DEPLOYMENT_SUPPRESSION = YES`

`QUALIFIED_BUT_NOT_DEPLOYED_COUNT = 131 diagnostic decision-day opportunities`

`QUALIFIED_BUT_NOT_DEPLOYED_DOMINANT_REASON =
Portfolio Construction concentration/lot/reentry constraints`

`SYSTEM_FAILED_TO_CAPTURE_AVAILABLE_BULL_OPPORTUNITY = PARTIAL`

The evidence does not say every skipped opportunity should have been bought.
But it does show that BULL-period underdeployment was not only caused by lack of
qualified candidates.

## Re-Risk Speed Characterization

Using G17 episodes extended through the G18 snapshot, descriptive pace labels:

- `FAST`: large BUY count, sharp exposure increase, or rapid position recovery
- `MODERATE`: some redeployment without immediate full restoration
- `GRADUAL`: limited redeployment

Failed recovery pace distribution:

- `FAST`: `2` (`2023-05-29`, `2023-06-07`)
- `MODERATE`: `2` (`2023-05-08`, `2023-05-17`)
- `GRADUAL`: `1` (`2023-06-20`)

Successful recovery pace distribution:

- `FAST`: `1` (`2023-06-02`)
- `MODERATE`: `1` (`2023-04-28`)
- `GRADUAL`: `0`

`FAILED_RECOVERY_RERISK_PACE_DISTRIBUTION =
FAST:2, MODERATE:2, GRADUAL:1`

`SUCCESSFUL_RECOVERY_RERISK_PACE_DISTRIBUTION =
FAST:1, MODERATE:1, GRADUAL:0`

`FAST_RERISK_FAILURE_ASSOCIATION = WEAK`

Fast re-risk contributes to failure risk but is not sufficient by itself. The
stronger pattern is fast re-risk while short/medium structure is conflicted.

## Short-vs-Medium Structure Agreement

Existing production Market Context already records 5D return, 20D return, 5D
breadth, and 20D breadth in `metrics`. G18 used these diagnostically only.

Observed patterns:

- `SHORT_STRONG_MEDIUM_STRONG`: can succeed (`2023-04-28`) or fail
  (`2023-05-08`, `2023-06-20`), so not sufficient.
- `SHORT_WEAK_MEDIUM_STRONG`: appears in BULL cash drift and fragile BULL
  continuation (`2023-06-26`, `2023-06-27`, `2023-07-07`).
- `SHORT_STRONG_MEDIUM_WEAK/NEUTRAL`: appears in rebound episodes such as
  `2023-06-07`, where exposure restored quickly and next-5BD failed.

`SHORT_MEDIUM_STRUCTURE_INTERACTION_SEPARABILITY = MODERATE`

`FALSE_RECOVERY_DOMINANT_STRUCTURE_PATTERN =
SHORT_MEDIUM_DISAGREEMENT_WITH_FAST_OR_RESUMED_RERISK`

## Diagnostic Volume Participation

G18 did not implement production features. It did compute diagnostic-only
episode comparisons from the same PIT as-of J-Quants daily quote inputs already
materialized for Market Context.

Examples:

| Date | Context | Advancing volume share | Adv/decl volume ratio | Sector positive 5D | Sector positive 20D |
| --- | --- | ---: | ---: | ---: | ---: |
| 2023-04-28 | successful recovery | 63.8% | 1.76 | 76.5% | 88.2% |
| 2023-05-29 | failed recovery | 49.6% | 0.98 | 8.8% | 79.4% |
| 2023-06-07 | failed fast re-risk | 88.9% | 8.00 | 100.0% | 61.8% |
| 2023-06-27 | BULL cash drift | 44.3% | 0.80 | 26.5% | 100.0% |
| 2023-07-07 | BULL high exposure, weak short structure | 30.4% | 0.44 | 35.3% | 91.2% |

`MARKET_VOLUME_PARTICIPATION_PIT_DERIVABLE = YES`

`VOLUME_PARTICIPATION_DIAGNOSTIC_SEPARABILITY = WEAK`

Volume participation is feasible and informative for some fragile BULL/cash
drift days, but it is not cleanly separable across all recovery outcomes.

`PRODUCTION_FEATURE_IMPLEMENTED = NO`

## Diagnostic Sector Participation

Sector participation breadth is PIT-derivable from J-Quants listed issues plus
daily quotes. Diagnostic-only results show useful short/medium disagreement:

- `2023-05-29`: sector positive 5D `8.8%` while sector positive 20D `79.4%`
- `2023-06-27`: sector positive 5D `26.5%` while sector positive 20D `100.0%`
- `2023-07-07`: sector positive 5D `35.3%` while sector positive 20D `91.2%`

`SECTOR_PARTICIPATION_PIT_DERIVABLE = YES`

`SECTOR_PARTICIPATION_DIAGNOSTIC_SEPARABILITY = MODERATE`

This is a research candidate only. It is not a production feature.

## Regime Label vs Opportunity Reality

BULL currently means positive market direction / medium-trend state, not
guaranteed broad deployable opportunity.

Evidence:

- BULL average 20D breadth is high (`68.4%`), but 5D breadth and deployment
  quality vary materially.
- BULL has regular full-eligible decisions (`4.52/day`) and BUY plans
  (`2.75/day`), but BUY_WAIT remains high (`11.28/day`) and downstream PC
  constraints often leave cash idle.
- Late June/early July shows BULL with strong 20D breadth but weak 5D breadth,
  weak sector 5D participation, high cash, and limited deployment until a later
  fast re-risk.

`REGIME_LABEL_OVERSTATES_DEPLOYABLE_OPPORTUNITY = PARTIAL`

`BULL_OPPORTUNITY_DENSITY_STABLE = NO`

## SELL Pressure vs BUY Scarcity

BULL cash drift flow imbalance:

- `2023-02-24 -> 2023-03-13`: SELL fills `34` vs BUY fills `18`; SELL
  dominant, replacement incomplete.
- `2023-04-14 -> 2023-04-20`: SELL fills `11` vs BUY fills `9`, but exposure
  stayed low because deployment notional/constraints limited replacement.
- `2023-05-08 -> 2023-05-18`: SELL fills `16` vs BUY fills `14`, but positions
  fell from `8` to `5`; replacement did not fully maintain exposure.
- `2023-06-12 -> 2023-07-07`: SELL fills `29` vs BUY fills `30`; the mid-window
  cash drift came from SELL pressure plus slow replacement, then a later fast
  re-risk restored exposure.

`BULL_CASH_DRIFT_FLOW_IMBALANCE_CLASS = BOTH`

SELL/PM pressure and BUY replacement/deployment suppression both contribute.
This is not evidence to change SELL logic in G18.

## Winner Retention / ADD Pipeline

G14 already found winner-retention deterioration. G18 reconnects it to cash
drift:

- winners/positions are reduced or exited during BULL sequences,
- replacements exist but often remain constrained by PC, lot, concentration, or
  reentry rules,
- ADD does not materially refill exposure; accepted ADD increment was often zero
  in inspected PC reconciliation evidence,
- the system sometimes accumulates cash after exits and only later redeploys.

`POST_WINNER_RETENTION_PRIMARY_LIMITER =
PM/SELL removal plus incomplete BUY/ADD replacement under PC constraints`

`WINNER_RETENTION_CONTRIBUTES_TO_CASH_DRIFT = PARTIAL`

`ADD_PIPELINE_CONTRIBUTES_TO_STAGNATION = PARTIAL`

## Short Loser Interaction

G15's 1-5BD loser cluster aligns with G17/G18 interaction evidence:

- fragile market structure alone is not sufficient,
- fast re-risk alone is not sufficient,
- the meaningful cluster is fragile/conflicted short-vs-medium market structure
  plus rapid or resumed capital deployment.

`SHORT_LOSER_MARKET_STRUCTURE_INTERACTION = MODERATE`

`SHORT_LOSER_RERISK_INTERACTION = MODERATE`

## Two-Path Failure Matrix

| Period | Path A premature re-risk | Path B opportunity capture failure | Classification |
| --- | --- | --- | --- |
| 2023-03-31 sequence | partial | partial | A_AND_B |
| 2023-05-08 -> 2023-05-18 | yes | partial | A_AND_B |
| 2023-05-29 -> 2023-06-07 | yes | partial | A_AND_B |
| 2023-06-12 -> 2023-06-28 | partial | yes | A_AND_B |
| 2023-07-06 -> 2023-07-07 | yes | no/partial after catch-up deployment | A_ONLY |

`PREMATURE_RERISK_SUPPORTED = YES`

`BULL_OPPORTUNITY_CAPTURE_FAILURE_SUPPORTED = PARTIAL`

`BOTH_FAILURE_MODES_COEXIST = YES`

The stronger system-level diagnosis is dual-mode:

1. The system can under-deploy during valid BULL windows because downstream
   deployment constraints and replacement scarcity leave cash idle.
2. It can later re-risk quickly while short-term participation has already
   weakened, raising short-loser risk.

## DATA / EVIDENCE / PHILOSOPHY / DESIGN Separation

### DATA

Raw PIT facts available from existing J-Quants architecture:

- daily quotes with close/adjusted close and volume
- listed issue universe and sector classification
- trading calendar
- optional corporate action / disclosure sources

No external source was used.

### EVIDENCE

Legitimate contemporaneous evidence:

- Market Context 20D trend, 20D breadth, 5D return, 5D breadth, volatility,
  sector dispersion, confidence
- diagnostic-only volume participation and sector participation derived from
  PIT as-of J-Quants inputs
- BUY quality action distribution
- Runtime planning BUY/SELL intent
- Portfolio Construction residual reasons and allocation reconciliation
- fills, cash, exposure, and position count as operational state

Historical outcomes were used only for retrospective labels, not as production
evidence.

### INVESTMENT PHILOSOPHY

The system should:

- buy strength after confirmation,
- avoid catching the exact bottom,
- avoid blanket re-entry bans,
- preserve optionality in fragile recovery,
- deploy during healthy opportunity, not merely because the label is BULL,
- avoid returning to high exposure after a short bounce if participation is
  already narrowing.

### DESIGN / AUTHORITY

If pursued later:

- Premature re-risk semantics belong first to Market Context as recovery-quality
  or fragility evidence.
- Portfolio Policy / Portfolio Construction should be the consumer for risk
  pacing and capital deployment behavior.
- Opportunity capture suppression appears primarily in Portfolio Construction /
  sizing / ADD replacement mechanics, with Candidate and BUY Quality as upstream
  evidence providers.
- A second regime classifier is not recommended.

`DATA_EVIDENCE_PHILOSOPHY_DESIGN_SEPARATION = PASS`

## Repair Research Readiness

`REPAIR_RESEARCH_READINESS = C. DUAL_FAILURE_MODE_DESIGN_RESEARCH_JUSTIFIED`

This does not authorize implementation or tuning.

## Required Summary

`PRIMARY_JUDGMENT =
PHASE31_G18_DUAL_FAILURE_MODE_PREMATURE_RERISK_AND_PARTIAL_BULL_CAPTURE_FAILURE_SUPPORTED`

`TARGET_RUN_ID =
runtime-test-historical-extended-smoke-20260822T174358377089Z`

`G18_SNAPSHOT_LATEST_COMPLETED_DATE = 2023-07-14`

`G18_SNAPSHOT_COMPLETED_BUSINESS_DAYS = 194`

`RUN_STATUS = RUNNING`

`SNAPSHOT_INTEGRITY = PASS`

`BULL_CASH_DRIFT_EPISODE_COUNT = 4`

`BULL_LOW_EXPOSURE_JUSTIFICATION_DISTRIBUTION =
SYSTEM_CAPTURE_FAILURE:1, MIXED:3`

`MARKET_BREADTH_SUPPORTS_LOW_EXPOSURE = PARTIAL`

`BULL_OPPORTUNITY_FUNNEL_DOMINANT_BLOCKER =
PORTFOLIO_CONSTRUCTION_ZERO / CONCENTRATION_AND_LOT_CONSTRAINTS_WITH_REENTRY_BLOCKS`

`UPSTREAM_OPPORTUNITY_SCARCITY = PARTIAL`

`DOWNSTREAM_CAPITAL_DEPLOYMENT_SUPPRESSION = YES`

`QUALIFIED_BUT_NOT_DEPLOYED_COUNT =
131 diagnostic decision-day opportunities`

`QUALIFIED_BUT_NOT_DEPLOYED_DOMINANT_REASON =
Portfolio Construction concentration/lot/reentry constraints`

`SYSTEM_FAILED_TO_CAPTURE_AVAILABLE_BULL_OPPORTUNITY = PARTIAL`

`FAILED_RECOVERY_RERISK_PACE_DISTRIBUTION =
FAST:2, MODERATE:2, GRADUAL:1`

`SUCCESSFUL_RECOVERY_RERISK_PACE_DISTRIBUTION =
FAST:1, MODERATE:1, GRADUAL:0`

`FAST_RERISK_FAILURE_ASSOCIATION = WEAK`

`SHORT_MEDIUM_STRUCTURE_INTERACTION_SEPARABILITY = MODERATE`

`FALSE_RECOVERY_DOMINANT_STRUCTURE_PATTERN =
SHORT_MEDIUM_DISAGREEMENT_WITH_FAST_OR_RESUMED_RERISK`

`MARKET_VOLUME_PARTICIPATION_PIT_DERIVABLE = YES`

`VOLUME_PARTICIPATION_DIAGNOSTIC_SEPARABILITY = WEAK`

`SECTOR_PARTICIPATION_PIT_DERIVABLE = YES`

`SECTOR_PARTICIPATION_DIAGNOSTIC_SEPARABILITY = MODERATE`

`REGIME_LABEL_OVERSTATES_DEPLOYABLE_OPPORTUNITY = PARTIAL`

`BULL_OPPORTUNITY_DENSITY_STABLE = NO`

`BULL_CASH_DRIFT_FLOW_IMBALANCE_CLASS = BOTH`

`POST_WINNER_RETENTION_PRIMARY_LIMITER =
PM/SELL removal plus incomplete BUY/ADD replacement under PC constraints`

`WINNER_RETENTION_CONTRIBUTES_TO_CASH_DRIFT = PARTIAL`

`ADD_PIPELINE_CONTRIBUTES_TO_STAGNATION = PARTIAL`

`SHORT_LOSER_MARKET_STRUCTURE_INTERACTION = MODERATE`

`SHORT_LOSER_RERISK_INTERACTION = MODERATE`

`PREMATURE_RERISK_SUPPORTED = YES`

`BULL_OPPORTUNITY_CAPTURE_FAILURE_SUPPORTED = PARTIAL`

`BOTH_FAILURE_MODES_COEXIST = YES`

`PREMATURE_RERISK_SEMANTIC_OWNER =
Market Context primary; Portfolio Policy / Portfolio Construction consumer`

`OPPORTUNITY_CAPTURE_PRIMARY_OWNER =
Portfolio Construction / Position Sizing / ADD replacement mechanics`

`SECOND_REGIME_CLASSIFIER_RECOMMENDED = NO`

`DATA_EVIDENCE_PHILOSOPHY_DESIGN_SEPARATION = PASS`

`REPAIR_RESEARCH_READINESS =
DUAL_FAILURE_MODE_DESIGN_RESEARCH_JUSTIFIED`

`FUTURE_INFORMATION_USED_AS_PRODUCTION_INPUT = NO`

`HISTORICAL_OUTCOME_USED_TO_SELECT_PRODUCTION_THRESHOLD = NO`

`EVIDENCE_USED_AS_PRODUCTION_DATA_SOURCE = NO`

`PAPER_LEDGER_USED_AS_ALPHA_INPUT = NO`

`PERFORMANCE_RESULT_USED_AS_FEATURE = NO`

`NEW_EXTERNAL_DATA_USED = NO`

`NEW_PRODUCTION_FEATURE_IMPLEMENTED = NO`

`NEW_PRODUCTION_THRESHOLD_SELECTED = NO`

`STRATEGY_CHANGED = NO`

`MARKET_CONTEXT_CHANGED = NO`

`PORTFOLIO_POLICY_CHANGED = NO`

`PORTFOLIO_CONSTRUCTION_CHANGED = NO`

`PM_CHANGED = NO`

`BUY_LOGIC_CHANGED = NO`

`SELL_LOGIC_CHANGED = NO`

`ADD_LOGIC_CHANGED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`REPLAY_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`GIT_DIFF_CHECK = PASS`

`NEXT_TASK_RECOMMENDATION =
Design-only dual-path contract work: Market Context recovery-quality/fragility
semantics for risk pacing, plus Portfolio Construction / Position Sizing / ADD
opportunity-capture diagnostics. Do not implement or tune thresholds from this
window.`
