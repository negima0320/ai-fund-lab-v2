# Phase31-G138 - March-April Profit Formation / Strategy Causality Audit

## Final Decision

`G138_STRONG_PERFORMANCE_CONFIRMED_BUT_CAUSALITY_PARTIAL_FOLLOWUP_REQUIRED`

The March-April profit formation in the current run is real at the aggregate
valuation / cashflow level and is explainable by a small set of large winning
campaigns plus broad capital deployment. The evidence supports Strategy-causal
contribution from opportunity identification, capital deployment, and winner
retention.

However, the audit does not fully close the higher-resolution capital-value
causality question. The run shows that the current coarse architecture captured
major winners despite the known resolution limitation, but it does not prove
that high-resolution marginal value / rotation research is unnecessary. Those
remain future shadow-research candidates rather than mandatory near-term repair.

## Scope

Task type: READ-ONLY causality audit.

Target run:

`runtime-test-historical-extended-smoke-20260825T235520054579Z`

Primary window:

`2023-03-01` through `2023-04-28`

Completed immutable artifacts audited:

- completed run dates available: `154`, from `2022-10-03` through `2023-05-19`
- primary audited dates: `42`, from `2023-03-01` through `2023-04-28`

No code, config, threshold, weight, model, fresh-run, resume, replay, long
Historical, or run mutation was performed.

## Source Basis

Required documents read:

- `docs/02_architecture/high_resolution_marginal_capital_value_and_portfolio_rotation_architecture.md`
- `docs/phase_reports/phase31_g137_high_resolution_capital_value_architecture_ambiguity_hardening.md`
- `docs/phase_reports/phase31_g136_high_resolution_capital_value_rotation_permanent_architecture_sot_materialization.md`
- `docs/phase_reports/phase31_g135_high_resolution_marginal_value_portfolio_rotation_design_readiness_audit.md`
- `docs/phase_reports/phase31_g134_capital_value_resolution_loss_root_cause_localization_audit.md`
- `docs/phase_reports/phase31_g133_bull_internal_opportunity_quality_capital_allocation_behavior_audit.md`
- `docs/phase_reports/phase31_g129_buy_add_actual_path_narrow_repair.md`

Relevant permanent SoT constraints preserved:

- Candidate AI remains opportunity intelligence, not capital allocation owner.
- Market Quality remains capital pacing context, not a hard BUY gate.
- Portfolio Policy owns capital budget.
- Portfolio Construction owns capital allocation.
- Position Sizing owns discrete quantity.
- Runtime consumes executable decisions and must not re-decide capital priority.
- High-resolution marginal value and portfolio rotation remain future
  architecture capabilities; G137 explicitly clarified that no single scalar is
  mandated and that desirability must remain separated from feasibility.

## Measurement Gate

Observed equity path:

| Date | Equity | Cash | Market Value | Exposure | Positions | Valuation status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 2023-03-01 | 1,206,160 | 261,380 | 944,780 | 78.33% | 13 | PASS |
| 2023-03-15 | 1,256,490 | 519,400 | 737,090 | 58.66% | 7 | PASS |
| 2023-03-22 | 1,422,620 | 336,680 | 1,085,940 | 76.33% | 11 | PASS |
| 2023-04-06 | 1,776,470 | 907,760 | 868,710 | 48.90% | 5 | PASS |
| 2023-04-07 | 1,693,630 | 560,760 | 1,132,870 | 66.89% | 6 | PASS |
| 2023-04-28 | 1,677,640 | 396,810 | 1,280,830 | 76.35% | 9 | PASS |

Valuation integrity over the 42 primary dates:

| Check | Result |
| --- | ---: |
| Valuation projection PASS dates | 42 / 42 |
| Position valuation rows | 354 |
| Quantity basis | 354 `ADJUSTED` |
| Valuation quote status | 354 `FRESH_CURRENT_QUOTE` |
| Corporate-action ambiguity status | 354 `CLEAR` |
| Stale authority flags | 0 material stale rows observed |
| Daily equity delta vs symbol contribution reconstruction max error | 0 yen |
| Primary-window reconstructed contribution | +480,490 yen |
| Primary-window equity delta | +480,490 yen |

Measurement conclusion:

The March-April profit is not explained by an observed valuation discontinuity,
stale quote bridge, unresolved corporate action, or cash/position accounting
break. Security-level attribution is complete at the daily mark-to-market +
trade-cashflow level, but campaign-level decision causality remains partial for
some fills whose source type is recorded as `MISSING`.

## Period Attribution

| Window | Dates | Days | Start basis equity | End equity | PnL | Return | Avg exposure | Fills BUY / SELL |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| March | 2023-03-01 to 2023-03-31 | 22 | 1,197,150 | 1,618,860 | +421,710 | +35.23% | 80.2% | 31 / 39 |
| April to 28 | 2023-04-03 to 2023-04-28 | 20 | 1,618,860 | 1,677,640 | +58,780 | +3.63% | 74.8% | 29 / 27 |
| Profit burst | 2023-03-15 to 2023-04-06 | 16 | 1,230,320 | 1,776,470 | +546,150 | +44.39% | 75.0% | 24 / 25 |
| Drawdown | 2023-04-07 to 2023-04-18 | 8 | 1,776,470 | 1,635,640 | -140,830 | -7.93% | 78.4% | 10 / 6 |
| Recovery tail | 2023-04-19 to 2023-04-28 | 8 | 1,635,640 | 1,677,640 | +42,000 | +2.57% | 73.8% | 16 / 17 |

The gain is concentrated in the 2023-03-15 to 2023-04-06 profit burst, then
partially given back after 2023-04-07. The recovery tail was positive but did
not reclaim the 2023-04-06 high by 2023-04-28.

## Security-Level PnL Attribution

Top positive symbol contributions in the primary window:

| Symbol | Contribution | Realized PnL observed |
| --- | ---: | ---: |
| 59350 | +188,600 | +188,600 |
| 67310 | +100,000 | +100,000 |
| 44440 | +84,000 | +84,000 |
| 70720 | +43,900 | +42,200 |
| 64240 | +41,300 | +41,300 |
| 68980 | +34,700 | +34,700 |
| 95560 | +26,000 | 0 |
| 66560 | +23,000 | +23,000 |
| 40110 | +17,000 | +17,000 |
| 43880 | +16,200 | +16,200 |

Top negative symbol contributions:

| Symbol | Contribution | Realized PnL observed |
| --- | ---: | ---: |
| 51890 | -57,000 | -57,000 |
| 60220 | -18,200 | -18,200 |
| 50320 | -15,000 | -15,000 |
| 38100 | -14,700 | -14,700 |
| 61670 | -13,500 | -13,500 |
| 77190 | -11,100 | -11,100 |
| 48920 | -10,300 | -10,300 |
| 43340 | -10,100 | -10,100 |
| 41660 | -9,900 | -9,900 |
| 73570 | -7,800 | -7,800 |

Interpretation:

- Profit formation is `FEW_WINNER_DOMINATED`.
- `59350` alone explains a large part of the profit burst and also the largest
  one-day reversal.
- The top five positive contributors explain most of the primary-window gain,
  but the portfolio still had broad deployment, many BUY/SELL fills, and both
  gains and losses across the book.
- `94320` was a persistent retained position, but its 2023-03-01 to
  2023-04-28 contribution was modest: valuation moved from 600 shares at 157.0
  to 600 shares at 166.0, a +5,400 yen mark-to-market change.

## Large Day Reconciliation

Largest gain days:

| Date | Equity delta | Main symbol contributors |
| --- | ---: | --- |
| 2023-03-30 | +86,700 | 68980 +47,700; 59350 +47,100 |
| 2023-04-06 | +73,710 | 59350 +70,000 |
| 2023-03-22 | +69,540 | 44440 +28,000; 64240 +15,000; 59350 +12,800 |
| 2023-03-31 | +67,870 | 59350 +70,000 |
| 2023-04-03 | +66,870 | 59350 +70,000 |
| 2023-04-05 | +63,340 | broad gain, led by existing winners |

Largest loss days:

| Date | Equity delta | Main symbol contributors |
| --- | ---: | --- |
| 2023-04-07 | -82,840 | 59350 -90,500, partly offset by 43880 and 95560 |
| 2023-03-29 | -65,460 | broad decline before 59350/68980 rebound |
| 2023-04-04 | -46,310 | broad decline |
| 2023-04-11 | -44,660 | broad decline |
| 2023-04-12 | -44,480 | broad decline |
| 2023-04-18 | -34,280 | broad decline |

The largest gain and loss days are explainable from same-run valuation and
fill artifacts. No large loss day in the primary window was proven
system-caused. The 2023-04-07 drawdown is primarily the reversal of an actual
large winner, not an accounting artifact.

## Decision-Time Strategy Evidence

Portfolio Construction / Position Sizing / Runtime path over the 42 primary
dates:

| Metric | Count |
| --- | ---: |
| PC security allocation rows | 101 |
| G61 `LOT_EXECUTABLE_COMPATIBLE` rows | 86 |
| G61 `LOT_INFEASIBLE_RESIDUAL_REQUIRED` rows | 15 |
| PS positive quantity rows | 198 |
| Runtime/morning generated pending items | 193 |
| Morning selected symbols | 143 |
| BUY fills | 60 |
| SELL fills | 66 |

PC competitor quality classes:

| Class | Count |
| --- | ---: |
| COMPARABLE_MARGINAL | 860 |
| COMPARABLE_HIGH | 9 |
| STRONG | 2 |
| BLOCKED | 10 |
| INSUFFICIENT | 6 |

Selected PC security allocation classes:

| Class | Count |
| --- | ---: |
| COMPARABLE_MARGINAL | 96 |
| COMPARABLE_HIGH | 3 |
| STRONG | 2 |

Market-Candidate-Cash interaction:

| Result | Count |
| --- | ---: |
| FAIL_CLOSED | 712 |
| CASH_PREFERRED | 95 |
| BLOCKED | 47 |
| DEPLOY_ELIGIBLE | 31 |
| SELECTIVE_COMPETITION | 2 |

This confirms that the current system did not buy everything blindly. It kept
Cash, rejected many rows, retained lot/cap infeasibility, and still deployed
into selected securities. At the same time, most selected winners came through
the intentionally coarse `COMPARABLE_MARGINAL` path, which is why
high-resolution marginal value remains architecturally valid as a future
capability.

## Top Winner Lineage

Observed fill / campaign outline:

| Symbol | Entry / exit evidence in target run | Role |
| --- | --- | --- |
| 59350 | BUY 100 on 2023-03-22 at 1,844; SELL 100 on 2023-04-20 at 3,730 | Primary profit driver |
| 67310 | BUY 100 on 2023-04-21 at 2,000; SELL 100 on 2023-04-27 at 3,000 | Secondary, after primary burst |
| 44440 | BUY 100 on 2023-03-16 at 1,094; SELL 100 on 2023-03-22 at 1,934 | Major burst winner |
| 70720 | BUY 100 on 2023-02-28 at 1,748; SELL 100 on 2023-03-17 at 2,170 | Pre-positioned winner entering March |
| 64240 | BUY 100 on 2023-03-16 at 1,354; SELL 100 on 2023-03-23 at 1,767 | Major burst winner |
| 68980 | BUY 100 on 2023-03-30 at 2,803; SELL 100 on 2023-04-06 at 3,150 | Late burst winner |
| 94320 | Built before March; retained 600 shares through 2023-04-28 | Persistent core, small March-April PnL |

Decision-time PC samples for major winners:

| Date | Symbol | PC class | Authorized allocation weight | Notes |
| --- | --- | --- | ---: | --- |
| 2023-03-16 | 44440 | COMPARABLE_MARGINAL | 0.106169 | selected |
| 2023-03-16 | 64240 | COMPARABLE_MARGINAL | 0.122643 | selected |
| 2023-03-22 | 59350 | COMPARABLE_MARGINAL | 0.145742 | selected |
| 2023-03-30 | 68980 | COMPARABLE_MARGINAL | 0.223999 | selected |
| 2023-04-06 | 67310 | COMPARABLE_MARGINAL | 0.234913 | selected |

Plane B conclusion:

Major winners had contemporaneous selection evidence and passed the canonical
PC/G61/PS/Runtime path. The evidence is Strategy-causal at the level of actual
selection, sizing, execution, and retention. It is only partial at the level of
fine-grained "why this winner over all possible alternatives" because the
current architecture intentionally compresses many rows into coarse capital
value classes.

## Market Quality / Risk Pacing

Market Quality distribution:

| State | Dates |
| --- | ---: |
| SHORT_TERM_BREADTH_BREAKDOWN | 13 |
| HEALTHY_EXPANSION | 12 |
| RECOVERY_CONFIRMATION_INCOMPLETE | 8 |
| CONFLICTED_MARKET_STRUCTURE | 7 |
| HEALTHY_RECOVERY | 1 |
| SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH | 1 |

Risk Pacing distribution:

| State | Dates |
| --- | ---: |
| DEPLOY | 39 |
| BALANCED_DEPLOYMENT | 3 |

Behavior by Market Quality / Risk Pacing:

| Market Quality / Risk Pacing | Dates | Avg exposure | BUY fills | PC security rows | Pending generated |
| --- | ---: | ---: | ---: | ---: | ---: |
| CONFLICTED_MARKET_STRUCTURE / DEPLOY | 7 | 83.0% | 12 | 15 | 38 |
| HEALTHY_EXPANSION / DEPLOY | 12 | 85.7% | 13 | 45 | 43 |
| HEALTHY_RECOVERY / DEPLOY | 1 | 76.3% | 3 | 3 | 4 |
| RECOVERY_CONFIRMATION_INCOMPLETE / DEPLOY | 8 | 75.9% | 8 | 11 | 36 |
| SHORT_TERM_BREADTH_BREAKDOWN / BALANCED_DEPLOYMENT | 3 | 58.5% | 3 | 4 | 10 |
| SHORT_TERM_BREADTH_BREAKDOWN / DEPLOY | 10 | 71.6% | 18 | 21 | 58 |
| SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH / DEPLOY | 1 | 75.7% | 3 | 2 | 4 |

Conclusion:

Market Quality did not act as a hard BUY gate in this window. Healthy states
showed high exposure and security allocation, while weaker states still allowed
participation. The observed profit burst required favorable market realization,
but the path was not passive beta-only exposure: the book was actively
selected, traded, reduced, and exited.

## ADD / G129 Status

PM action counts in the primary window:

| Action | Count |
| --- | ---: |
| HOLD | 181 |
| REDUCE | 84 |
| ADD | 58 |
| EXIT | 33 |

G129 repaired the BUY_ADD actual path and campaign materialization contract,
but the primary-window fill artifacts are not sufficient to prove that G129
materially changed March-April scaling in this run. BUY fills exist and
campaigns are materialized, but fill source type is often generic `BUY` or
`MISSING` rather than enough to attribute large incremental scaling to repaired
BUY_ADD behavior.

Therefore:

- G129 repaired path active in architecture: yes.
- G129 material effect on observed March-April position scaling: unproven.
- Major winner capture in March-April did not depend on proving G129 material
  ADD contribution.

## High-Resolution Value / Rotation Implications

G134-G137 remain valid:

- Existing capital value resolution is coarse.
- `COMPARABLE_MARGINAL` dominates both competitor rows and selected rows.
- Current evidence does not encode a unified high-resolution next-lot marginal
  value across NEW_BUY / ADD / Cash.
- Portfolio rotation / HOLD external opportunity cost remains unimplemented.

But the March-April run does not prove an immediate mandatory repair:

- The current system captured the major winners anyway.
- The largest profit driver, `59350`, was selected by the actual production
  path before its large move.
- The biggest drawdown was a genuine winner giveback / market movement, not a
  detected capital-value implementation defect.
- No current-value resolution limitation was shown to materially block the
  major March-April winners.

Disposition:

High-resolution value and rotation should remain Phase31-adjacent future
architecture research, preferably shadow-first, but not a blocker to closing
the current mandatory repair line if no separate acceptance gate requires it.

## Plane A vs Plane B

Plane A, ex-post PnL attribution:

- March-April gain is real and reconciled.
- Profit formation was few-winner dominated.
- `59350`, `44440`, `64240`, `68980`, and later `67310` explain most of the
  visible upside.
- 2023-04-07 was mainly `59350` giveback.

Plane B, decision-time Strategy quality:

- Major winners had same-date canonical selection / allocation evidence.
- The production path deployed capital through PC, G61, PS, Runtime, Pending,
  Submit, Execution, and fills.
- Market Quality did not directly suppress BUYs.
- The current architecture still uses coarse classes; therefore detailed
  capital-value causality is partial, not fully resolved.

## Required Judgments

OBSERVED_EQUITY_PATH_VERIFIED = `YES`

PROFIT_MEASUREMENT_INTEGRITY = `PASS`

ARTIFICIAL_PNL_MATERIAL_TO_MARCH_APRIL_GAIN = `NO`

SECURITY_LEVEL_PNL_ATTRIBUTION = `COMPLETE`

PROFIT_FORMATION_CONCENTRATION = `FEW_WINNER_DOMINATED`

MAJOR_ADD_DECISIONS_WERE_STRATEGY_INTENTIONAL = `PARTIAL`

TOP_WINNER_DECISION_LINEAGE_RECONSTRUCTED = `YES`

MAJOR_WINNERS_HAD_CONTEMPORANEOUS_SELECTION_EVIDENCE = `YES`

WINNER_CROSS_SECTIONAL_DIFFERENTIATION = `MIXED`

PROFIT_WAS_PRIMARILY_EXPOSURE_DRIVEN = `PARTIAL`

PROFIT_WAS_PRIMARILY_SECURITY_SELECTION_DRIVEN = `YES`

PROFIT_WAS_PRIMARILY_WINNER_RETENTION_DRIVEN = `YES`

LARGE_GAIN_DAYS_EXPLAINED = `YES`

LARGE_LOSS_DAYS_SYSTEM_CAUSED = `NO`

PROFIT_FORMATION_MATCHES_INVESTMENT_PHILOSOPHY = `YES`

CURRENT_VALUE_RESOLUTION_MATERIALLY_BLOCKED_MAJOR_WINNERS = `NO`

CURRENT_SYSTEM_CAPTURED_MAJOR_WINNERS_DESPITE_RESOLUTION_LIMIT = `YES`

HIGH_RESOLUTION_VALUE_CURRENT_PRIORITY = `OPTIONAL_FUTURE_CAPABILITY`

ROTATION_NEED_VISIBLE_IN_MARCH_APRIL = `PARTIAL`

PORTFOLIO_ROTATION_CURRENT_PRIORITY = `OPTIONAL_FUTURE_CAPABILITY`

G129_REPAIRED_ADD_PATH_ACTIVE_IN_WINDOW = `PARTIAL`

G129_REPAIR_MATERIALLY_CHANGED_OBSERVED_POSITION_SCALING = `UNPROVEN`

MAJOR_DRAWDOWN_RESPONSE_DESIGN_CONFORMANT = `PARTIAL`

RECOVERY_WAS_INTENTIONAL_STRATEGY_EXPOSURE = `YES`

PROFIT_PERSISTENCE_STRUCTURE = `CORE_PLUS_ROTATION`

CORE_EXPANSION_WAS_PREPOSITIONED_BY_STRATEGY = `YES`

POST_G129_APRIL_STRUCTURAL_BREAK_REPRODUCED = `PARTIAL`

APRIL_WEAKNESS_CAN_BE_ATTRIBUTED_TO_G129_PRE_REPAIR_DEFECT = `UNPROVEN`

CURRENT_RUN_SUPPORTS_BLANKET_BULL_WEAKNESS_CLAIM = `NO`

CAPITAL_VALUE_RESOLUTION_LIMITATION_STILL_ARCHITECTURALLY_VALID = `YES`

OPPORTUNITY_IDENTIFICATION_CONTRIBUTED = `YES`

CAPITAL_DEPLOYMENT_CONTRIBUTED = `YES`

WINNER_RETENTION_CONTRIBUTED = `YES`

WINNER_SCALING_CONTRIBUTED = `PARTIAL`

FAVORABLE_MARKET_REALIZATION_WAS_NECESSARY = `YES`

CURRENT_STRONG_PERFORMANCE_IS_EXPLAINABLE = `YES`

CURRENT_STRONG_PERFORMANCE_IS_STRATEGY_CAUSAL = `YES`

GOOD_PERFORMANCE_FOR_RIGHT_REASONS = `PARTIAL`

UNRESOLVED_MANDATORY_PERFORMANCE_DEFECT = `NO`

CURRENT_ARCHITECTURE_CHANGE_NECESSITY = `B`

HIGH_RESOLUTION_VALUE_DISPOSITION = `SHADOW_RESEARCH_CANDIDATE`

PORTFOLIO_ROTATION_DISPOSITION = `FUTURE_OPTIONAL`

PHASE31_CLOSURE_READY = `PARTIAL`

PHASE31_CLOSURE_RECOMMENDATION = `KEEP_OPEN_FOR_CAUSALITY_FOLLOWUP`

FUTURE_INFORMATION_USED_FOR_STRATEGY_JUDGMENT = `NO`

HISTORICAL_OUTCOME_USED_FOR_PARAMETER_SELECTION = `NO`

UNSUPPORTED_COUNTERFACTUAL_USED = `NO`

PATH_DEPENDENCE_ACKNOWLEDGED = `YES`

CODE_CHANGED = `NO`

RUN_MODIFIED = `NO`

FRESH_RUN_EXECUTED = `NO`

RESUME_EXECUTED = `NO`

REPLAY_EXECUTED = `NO`

LONG_HISTORICAL_EXECUTED = `NO`

GIT_DIFF_CHECK = `PASS`

## Final Recommendation

Do not perform a mandatory near-term high-resolution marginal value or
portfolio rotation implementation solely because G134-G137 identified a coarse
resolution limitation. The current run's March-April profit is real,
explainable, and materially Strategy-causal.

Keep high-resolution value / rotation as shadow research. If Phase31 closure
requires fully separating security selection alpha from broad exposure and
winner retention in a campaign-level causal ledger, perform one focused
causality follow-up. Otherwise, no mandatory defect repair is blocking from the
G138 evidence.
