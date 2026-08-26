# Phase31-G133 — BULL Internal Opportunity Quality / Capital Allocation Behavior Audit

## Final Decision

`G133_BULL_INTERNAL_BEHAVIOR_EVIDENCE_RESOLUTION_LIMITATION_CONFIRMED`

## Scope

Task type: READ-ONLY characterization audit.

Primary run:

`runtime-test-historical-extended-smoke-20260825T235520054579Z`

Completed immutable artifacts audited:

`2022-10-03` through `2023-02-24`

No code, config, threshold, weight, model, fresh-run, resume, replay, long Historical, or run mutation was performed.

The requested `2023-01-23 through latest completed BULL date` window is available through `2023-02-24` in the target run. Later 2023 BULL dates are outside the completed artifact range and were not inferred.

Historical performance was not used to judge production decision quality.

FUTURE_INFORMATION_USED_FOR_PRODUCTION_JUDGMENT = `NO`

## Source Basis

Required reports read:

- `docs/phase_reports/phase31_g132_unified_capital_frontier_decision_time_value_quality_characterization.md`
- `docs/phase_reports/phase31_g131_unified_add_new_cash_marginal_capital_authority_design_acceptance.md`
- `docs/phase_reports/phase31_g130_post_g129_buy_add_vs_buy_new_decision_time_capital_competition_audit.md`
- `docs/phase_reports/phase31_g129_buy_add_actual_path_narrow_repair.md`

Relevant G115-G126 reports were used as architectural and characterization context, not as decision labels.

Architecture SoT inspected:

- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/02_architecture/strategy_intelligence_architecture_v1.md`
- `docs/02_architecture/runtime_architecture_v2.md`

G131 remains controlling:

- Cash is a first-class capital alternative.
- ADD and NEW_BUY are peer capital competitors.
- Market Quality is capital pacing context, not a hard BUY gate.
- Multi-allocation and shoulder participation are permitted.
- Strict single-winner capital allocation is not required.

## Executive Judgment

BULL_INTERNAL_BEHAVIOR_DESIGN_CONFORMANT = `PARTIAL`

The BULL path is not simply "market strong, buy everything." The artifacts show:

- PM still emits HOLD, REDUCE, EXIT, and ADD inside BULL.
- Risk Pacing can be NORMAL or CAUTIOUS while top-level regime remains BULL.
- Market Quality distinguishes `HEALTHY_EXPANSION`, `CONFLICTED_MARKET_STRUCTURE`, `SHORT_TERM_BREADTH_BREAKDOWN`, and `SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH` inside BULL.
- PC selects a subset of competitors, keeps Cash, and rejects many rows through re-entry, lot, budget, cap, or zero-increment reasons.
- BUY_NEW and BUY_ADD can coexist.

However, BULL internal capital discrimination is limited by the same evidence-resolution limitation found in G132. BULL competitors are heavily compressed into coarse states and quality classes. Across BULL dates, 954 frontier competitors collapse into 10 final states, with `reentry_opportunity_not_requalified` alone covering 290 rows. The dominant opportunity class is `COMPARABLE_MARGINAL` with 854 rows. This is enough for broad gating and participation, but not enough to prove high-resolution ordering among many BULL opportunities.

MANDATORY_REPAIR_FOUND = `NO`

No consumer defect or SoT violation was proven. The confirmed issue is an evidence-resolution limitation, not an immediate repair mandate.

## Completed Regime Population

| Regime | Days |
| --- | ---: |
| BULL | 42 |
| BEAR | 25 |
| RANGE | 17 |
| RECOVERY | 12 |
| CORRECTION | 2 |

Market Quality counts:

| Market Quality | Days |
| --- | ---: |
| CONFLICTED_MARKET_STRUCTURE | 47 |
| SHORT_TERM_BREADTH_BREAKDOWN | 19 |
| HEALTHY_EXPANSION | 16 |
| RECOVERY_CONFIRMATION_INCOMPLETE | 12 |
| SHORT_TERM_NARROWING_WITH_MEDIUM_STRENGTH | 4 |

Risk Pacing counts:

| Risk Pacing | Days |
| --- | ---: |
| CAUTIOUS_DEPLOYMENT | 70 |
| NORMAL_DEPLOYMENT | 16 |
| GRADUAL_REDEPLOYMENT | 12 |

## BULL Windows

| Window | Dates | MQ Distribution | Risk Pacing | Avg PC NEW | Avg PC ADD | Avg Security Allocations | Runtime BUY_NEW / BUY_ADD |
| --- | ---: | --- | --- | ---: | ---: | ---: | ---: |
| `2022-10-27`, `2022-10-31` to `2022-11-01` | 3 | `CONFLICTED 2`, `HEALTHY_EXPANSION 1` | `CAUTIOUS 2`, `NORMAL 1` | 23.00 | 1.33 | 3.67 | 13 / 1 |
| `2022-11-09` to `2022-12-05` | 16 | `HEALTHY_EXPANSION 7`, `CONFLICTED 6`, `BREADTH_BREAKDOWN 3` | `CAUTIOUS 9`, `NORMAL 7` | 22.25 | 1.06 | 3.13 | 42 / 5 |
| `2023-01-23` to latest completed BULL | 23 | `CONFLICTED 14`, `HEALTHY_EXPANSION 8`, `NARROWING 1` | `CAUTIOUS 15`, `NORMAL 8` | 21.04 | 1.04 | 3.35 | 87 / 4 |

The target run contains no completed BULL artifact after `2023-02-24`.

## Candidate Population

The BUY Quality artifact emits a fixed top-50 candidate decision set per completed day, so raw BULL candidate population does not expand in count.

By regime:

| Regime | Avg BUY Quality Rows | Avg PC NEW Competitors | Avg PC ADD Competitors | Avg Security Allocation Rows |
| --- | ---: | ---: | ---: | ---: |
| BULL | 50.00 | 21.64 | 1.07 | 3.29 |
| BEAR | 50.00 | 25.64 | 0.32 | 2.76 |
| RANGE | 50.00 | 23.76 | 0.88 | 2.94 |
| RECOVERY | 50.00 | 22.33 | 0.58 | 2.67 |
| CORRECTION | 50.00 | 23.50 | 1.00 | 2.50 |

BUY Quality action distribution:

| Regime | FULL_ALLOCATION_ELIGIBLE | REDUCED_ALLOCATION_ONLY | BUY_WAIT | REJECT |
| --- | ---: | ---: | ---: | ---: |
| BULL | 211 | 1142 | 395 | 352 |
| BEAR | 85 | 736 | 217 | 212 |
| RANGE | 76 | 481 | 145 | 148 |
| RECOVERY | 47 | 330 | 129 | 94 |
| CORRECTION | 10 | 50 | 28 | 12 |

BULL_CANDIDATE_POPULATION_EXPANDS = `PARTIAL`

Interpretation:

- Raw top-50 population does not expand because the artifact is fixed-width.
- BULL has more `FULL_ALLOCATION_ELIGIBLE` rows per day than BEAR, RANGE, or RECOVERY.
- PC NEW competitor count is not larger in BULL; BEAR has more PC NEW competitors on average.

BULL_CANDIDATE_DIFFERENTIATION = `MODERATE`

Rationale:

Candidate AI / BUY Quality differentiates within BULL through score, rank, quality band, quality action, momentum trajectory, and entry admission evidence. But most PC opportunity rows still compress into `COMPARABLE_MARGINAL`, limiting capital-level discrimination.

## Frontier Compression By Regime

| Regime | FRONTIER_COMPETITOR_COUNT | DISTINCT_FINAL_PRIORITY_STATES | LARGEST_IDENTICAL_PRIORITY_GROUP |
| --- | ---: | ---: | --- |
| BULL | 954 | 10 | `reentry_opportunity_not_requalified / 290 / 30.40%` |
| BEAR | 649 | 9 | `reentry_opportunity_not_requalified / 139 / 21.42%` |
| RANGE | 419 | 10 | `incremental_budget_zero_allocation / 100 / 23.87%` |
| RECOVERY | 275 | 9 | `reentry_opportunity_not_requalified / 70 / 25.45%` |
| CORRECTION | 49 | 8 | `incremental_budget_zero_allocation / 12 / 24.49%` |

Opportunity quality class by regime:

| Regime | COMPARABLE_MARGINAL | COMPARABLE_HIGH | STRONG | BLOCKED | INSUFFICIENT |
| --- | ---: | ---: | ---: | ---: | ---: |
| BULL | 854 | 45 | 23 | 25 | 7 |
| BEAR | 630 | 16 | 0 | 3 | 0 |
| RANGE | 384 | 13 | 10 | 9 | 3 |
| RECOVERY | 246 | 20 | 7 | 2 | 0 |
| CORRECTION | 48 | 0 | 0 | 1 | 0 |

BULL_FRONTIER_COMPRESSION_RELATIVE_TO_OTHER_REGIMES = `HIGHER`

Where resolution is lost:

1. BULL has the largest identical final-state group share among major regimes: `30.40%`.
2. `COMPARABLE_MARGINAL` dominates BULL: `854 / 954 = 89.52%`.
3. Many BULL rows are separated by rank/score/quality evidence upstream, but PC final treatment frequently collapses to re-entry, budget, lot, or selected buckets.
4. Within selected BULL securities, multi-allocation permits participation, but does not fully rank all marginal opportunities on a high-resolution common value scale.

This extends the G132 finding: BULL behavior has usable lineage, but capital discrimination remains coarse.

## Capital Distribution Behavior In BULL

BULL aggregate capital behavior:

| Metric | Value |
| --- | ---: |
| Avg exposure | 85.15% |
| Avg Cash | 174,394 |
| Avg position count | 12.88 |
| Avg NEW allocation weight | 18.75% |
| Avg ADD allocation weight | 0.17% |
| Runtime BUY_NEW | 142 |
| Runtime BUY_ADD | 10 |

BULL window exposure and concentration:

| Window | Avg Exposure | Avg Cash | Avg Positions | Avg Largest Weight | Avg Top-3 Weight | Avg Top-5 Weight |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `2022-10-27` to `2022-11-01` | 89.66% | 109,130 | 10.33 | 14.73% | 40.57% | 61.97% |
| `2022-11-09` to `2022-12-05` | 89.18% | 115,926 | 10.00 | 20.86% | 51.10% | 67.84% |
| `2023-01-23` to `2023-02-24` | 81.77% | 223,580 | 15.22 | 14.72% | 35.69% | 47.94% |

Capital distribution classification:

`BROADLY_DISTRIBUTED_WITH_VALID_DIFFERENTIATION`

But with a caveat:

The distribution is not pure broad buying. Cash remains material, REDUCE/EXIT continues, and not all PC competitors receive allocation. Yet the differentiation is only moderate because BULL selected and rejected rows rely heavily on coarse opportunity classes and final-state buckets.

## Winner Scaling In BULL

BULL PM action totals:

| PM Action | Count |
| --- | ---: |
| HOLD | 360 |
| REDUCE | 68 |
| EXIT | 61 |
| ADD | 45 |

Selected BULL ADD rows:

| Date | Symbol | Accepted Weight | Score | Rank | Quality Class | Incremental Value | Opportunity Cost | Best NEW Score |
| --- | --- | ---: | ---: | ---: | --- | --- | --- | ---: |
| 2022-11-01 | 94320 | 0.015397 | 0.38607446 | 1 | COMPARABLE_MARGINAL | POSITIVE / PASS | PASS | 0.13592963 |
| 2022-11-09 | 94320 | 0.014398 | 0.39720057 | 1 | COMPARABLE_MARGINAL | POSITIVE / PASS | PASS | 0.25034036 |
| 2022-11-29 | 76470 | 0.002494 | 0.31899310 | 3 | COMPARABLE_MARGINAL | POSITIVE / PASS | PASS | 0.16297291 |
| 2022-11-30 | 76470 | 0.002491 | 0.34505777 | 2 | COMPARABLE_MARGINAL | POSITIVE / PASS | PASS | 0.21260248 |
| 2022-12-01 | 76470 | 0.002499 | 0.37835760 | 2 | COMPARABLE_MARGINAL | POSITIVE / PASS | PASS | 0.23108714 |
| 2022-12-02 | 76470 | 0.002409 | 0.40651062 | 2 | COMPARABLE_MARGINAL | POSITIVE / PASS | PASS | 0.25983442 |
| 2023-01-31 | 94320 | 0.012732 | 0.28370353 | 1 | COMPARABLE_MARGINAL | POSITIVE / PASS | PASS | 0.28342238 |
| 2023-02-01 | 94320 | 0.012895 | 0.29404466 | 1 | COMPARABLE_MARGINAL | POSITIVE / PASS | PASS | 0.08643914 |
| 2023-02-15 | 54010 | 0.048828 | 0.10952641 | 3 | COMPARABLE_MARGINAL | POSITIVE / PASS | PASS | 0.10548944 |

BULL_WINNER_SCALING_ACTIVE = `YES`

BULL_WINNER_SCALING_SELECTIVE = `PARTIAL`

Rationale:

- ADD is active in BULL and repeated ADD occurs.
- Every selected BULL ADD row has PM ADD, positive incremental investment value, and opportunity-cost PASS.
- ADD frequency remains small compared with NEW_BUY.
- Selected ADD rows are all `COMPARABLE_MARGINAL`; none are represented as a high-resolution `STRONG` next-lot marginal value.

## BULL NEW_BUY Selectivity

BULL_NEW_BUY_SELECTIVITY = `MODERATE`

Evidence:

- BUY Quality differentiates BULL candidates into `FULL_ALLOCATION_ELIGIBLE`, `REDUCED_ALLOCATION_ONLY`, `BUY_WAIT`, and `REJECT`.
- PC opportunity classes include `STRONG`, `COMPARABLE_HIGH`, `COMPARABLE_MARGINAL`, `BLOCKED`, and `INSUFFICIENT`.
- Runtime BUY_NEW is a subset of the PC frontier, not the whole BULL candidate set.
- BULL still keeps Cash and can reduce exposure on individual days.

Limit:

Most BULL PC rows are `COMPARABLE_MARGINAL`, and BULL final frontier compression is higher than other regimes. Therefore selectivity is real but not strong.

## Existing-Position Behavior

BULL_CAUSES_UNINTENDED_HOLD_BIAS = `UNPROVEN`

BULL_SUPPRESSES_VALID_REDUCE_EXIT = `NO`

Evidence:

- BULL PM emits `68` REDUCE and `61` EXIT actions, so BULL does not suppress valid REDUCE/EXIT globally.
- BULL HOLD is frequent (`360`), but high HOLD count is expected when more positions exist and cannot be judged wrong from later outcomes.
- Same-date PM evidence, not the BULL label alone, controls ADD/HOLD/REDUCE/EXIT.

No later losses were used to classify earlier HOLD as wrong.

## Internal BULL Deterioration

BULL_INTERNAL_QUALITY_DIFFERENTIATION_EXISTS = `YES`

Fields/producers:

| Producer | Field examples | Role |
| --- | --- | --- |
| Market Context | `market_quality_state`, `breadth_state`, `trend_state`, `volatility_state`, component evidence | Distinguishes BULL + healthy expansion from BULL + conflicted/narrowing/breadth breakdown |
| BUY Quality | `quality_action`, `quality_band`, `quality_score`, `momentum_trajectory_action` | Candidate-level entry and quality differentiation |
| Portfolio Policy | `risk_pacing_intent`, `incremental_capital_budget_envelope` | Deployment intensity / budget envelope |
| Portfolio Construction | `canonical_opportunity_quality_class`, `within_class_allocation_evidence`, `market_candidate_cash_interaction`, final state | Capital frontier and security/Cash partition |
| Position Management | `action`, PM severity / canonical sell semantic evidence | Existing-position ADD/HOLD/REDUCE/EXIT |

BULL_INTERNAL_QUALITY_EVIDENCE_CONSUMED = `PARTIAL`

Consumed:

- Market Quality is consumed by Portfolio Policy and PC as pacing context.
- Risk Pacing appears in PC constraint evidence.
- BUY Quality / opportunity evidence appears in PC and Runtime lineage.
- PM action appears in ADD competitors and existing-position decisions.

Partial limitation:

Much of the rich upstream evidence collapses into coarse final allocation classes. Consumption exists, but high-resolution value ordering is incomplete.

## Exposure Endogeneity

BULL_EXPOSURE_IS_ENDOGENOUS_TO_OPPORTUNITY_EVIDENCE = `PARTIAL`

Evidence:

- BULL exposure varies from high deployment to cash-heavy days.
- Example: `2022-12-05` remains BULL but exposure is `71.4%` and Cash is `306,290`.
- `2023-01-27` remains BULL but exposure is `67.7%` and Cash is `395,010`.
- PM REDUCE/EXIT occurs in BULL, and PC selected row counts vary by date.

Partial limitation:

Risk Pacing and PC final allocation often produce broad participation, so exposure is not a fixed BULL target, but neither is it fully explained by high-resolution opportunity value evidence.

## BEAR Control

BEAR_SELECTIVITY_RELATIVE_TO_BULL = `SIMILAR`

BEAR has lower average exposure and fewer ADD rows, but it does not show clearly cleaner frontier discrimination:

| Metric | BULL | BEAR |
| --- | ---: | ---: |
| Days | 42 | 25 |
| Avg PC NEW | 21.64 | 25.64 |
| Avg PC ADD | 1.07 | 0.32 |
| Avg security allocations | 3.29 | 2.76 |
| Avg exposure | 85.15% | 56.22% |
| Largest identical frontier group | 30.40% | 21.42% |
| COMPARABLE_MARGINAL share | 89.52% | 97.07% |
| Runtime BUY_NEW / BUY_ADD | 142 / 10 | 105 / 5 |

BEAR appears more cash-preserving and less ADD-heavy, but not structurally superior in capital value resolution. Its lower exposure is consistent with pacing and opportunity constraints, not proof that BEAR parameters are better.

## Hypothesis Tests

H1: BULL broad uplift expands candidate population and weakens cross-sectional differentiation.

`PARTIAL`

The raw top-50 candidate population is fixed and PC NEW count does not expand. But BULL has more Full/High quality evidence and more opportunities reaching allocation, while final discrimination remains compressed.

H2: BULL frontier compression causes many heterogeneous opportunities to receive similar capital treatment.

`SUPPORTED`

BULL has the highest largest-state compression among major regimes and heavy `COMPARABLE_MARGINAL` dominance.

H3: BULL capital is spread across too many indistinguishable opportunities because existing evidence loses resolution.

`PARTIAL`

BULL capital is distributed across multiple opportunities, but not all indistinguishable rows receive capital. The confirmed issue is moderate resolution, not proven over-allocation.

H4: BULL creates unintended HOLD persistence.

`NOT_SUPPORTED`

HOLD is common, but REDUCE/EXIT remains active. No same-date evidence proves BULL label alone creates invalid persistence.

H5: BULL winner scaling is active but insufficiently selective.

`PARTIAL`

ADD is active and PIT-supported, but selected ADD rows remain `COMPARABLE_MARGINAL` and sparse relative to BUY_NEW.

H6: BEAR appears stronger because its opportunity set is naturally more selective rather than because BEAR parameters are superior.

`PARTIAL`

BEAR is more cash-preserving, but not clearly more internally discriminating. No parameter superiority conclusion is supported.

## Defect Classification

Primary classification:

`EVIDENCE_RESOLUTION_LIMITATION`

Secondary classification:

`EXPECTED_REGIME_BEHAVIOR`

No `ARCHITECTURE_DEFECT` or `CONSUMER_DEFECT` was proven in G133.

## Required Final Judgments

BULL_INTERNAL_BEHAVIOR_DESIGN_CONFORMANT = `PARTIAL`

BULL_CANDIDATE_DIFFERENTIATION = `MODERATE`

BULL_FRONTIER_COMPRESSION_RELATIVE_TO_OTHER_REGIMES = `HIGHER`

BULL_NEW_BUY_SELECTIVITY = `MODERATE`

BULL_WINNER_SCALING_ACTIVE = `YES`

BULL_WINNER_SCALING_SELECTIVE = `PARTIAL`

BULL_CAUSES_UNINTENDED_HOLD_BIAS = `UNPROVEN`

BULL_SUPPRESSES_VALID_REDUCE_EXIT = `NO`

BULL_INTERNAL_QUALITY_DIFFERENTIATION_EXISTS = `YES`

BULL_INTERNAL_QUALITY_EVIDENCE_CONSUMED = `PARTIAL`

BEAR_SELECTIVITY_RELATIVE_TO_BULL = `SIMILAR`

MANDATORY_REPAIR_FOUND = `NO`

## Narrowest Future Boundary If Follow-Up Is Desired

No G133 repair is required.

If a future task chooses to improve BULL internal discrimination, the narrowest boundary to study is:

```text
Portfolio Construction opportunity-value resolution
before final multi-allocation / PS quantity consumption
```

Constraints for any future study:

- no BULL multiplier tuning;
- no BEAR multiplier tuning;
- no fixed position-count limit;
- no fixed exposure target;
- no new BUY/SELL filter;
- no Historical return fitting;
- preserve G131 unified ADD / NEW_BUY / Cash frontier;
- preserve Cash as first-class alternative;
- preserve PM as existing-position action authority and PS as quantity owner.

## Required Flags

CODE_CHANGED = `NO`

CONFIG_CHANGED = `NO`

THRESHOLD_CHANGED = `NO`

WEIGHT_CHANGED = `NO`

MODEL_CHANGED = `NO`

FRESH_RUN_EXECUTED = `NO`

RESUME_EXECUTED = `NO`

REPLAY_EXECUTED = `NO`

LONG_HISTORICAL_EXECUTED = `NO`

RUN_MUTATED = `NO`

PHASE_ADVANCED = `NO`
