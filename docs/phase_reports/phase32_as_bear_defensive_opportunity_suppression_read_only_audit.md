# Phase32-AS - BEAR Defensive Opportunity Suppression READ-ONLY Audit

## Scope

- Target run: `runtime-test-historical-extended-smoke-20260830T081425790243Z`
- Trusted evidence window: `2022-10-03` through `2023-10-10`
- Covered business days: 252
- Audit mode: READ-ONLY
- Source identity:
  - Current workspace HEAD at audit time: `ff1d23157cced619c5820898f8317a7440e6092c`
  - Target run evidence source commit recorded in `run_state.json`: `4ff63ba05a0012c60fce50741a946eed672f8990`, `source_dirty=true`
  - Current workspace is dirty due to prior Phase32 reports / SoT recording. This audit did not modify code, config, runtime state, run state, or trading state.

## Evidence Used

Primary evidence:

- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260830T081425790243Z/daily/*/strategy/market_context.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260830T081425790243Z/daily/*/strategy/portfolio_policy.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260830T081425790243Z/daily/*/strategy/buy_quality_decisions.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260830T081425790243Z/daily/*/strategy/portfolio_construction.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260830T081425790243Z/daily/*/current_valuation_refresh/valuation_projection.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260830T081425790243Z/daily/*/execution/fills.json`
- `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260830T081425790243Z/daily/*/positions/position_campaigns.json`

Architecture / SoT:

- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/phase_reports/phase32_ar_accepted_baseline_deferred_research_durable_sot_recording.md`

No future price, future return, later outcome, final campaign outcome, or Historical profitability was used for decision-time classification.

## Architecture Intent

The relevant SoT says:

- Market Direction is owned by Market Context.
- Market Quality is evidence, not a direct BUY decision, SELL decision, exposure target, quantity, cash target, Submit permission, or Safety override.
- Market Quality feeds Portfolio Policy Risk Pacing, then Portfolio Construction competition / allocation, then Position Sizing discrete quantity.
- `CAUTIOUS_DEPLOYMENT` means marginal deployment requires stronger contemporaneous evidence. It does not prescribe a fixed exposure.
- Risk Pacing is not a second candidate filter. It changes marginal capital preference among already valid competitors.
- Cash / Optionality is a valid capital competitor when deployment is not justified or not safely executable.
- In `CAUTIOUS_DEPLOYMENT`, `STRONG` opportunities may still win, `COMPARABLE_HIGH` may win when evidence is strong enough, while `COMPARABLE_MARGINAL` and `WEAK_VALID` may lose to Cash.

Observed BEAR behavior should therefore be classified as intended if:

- BEAR does not create a blanket BUY ban.
- Strong security opportunities can still pass through.
- Cash wins mostly against marginal, constrained, lot-infeasible, or otherwise non-deployable opportunities.
- First decisive rejection boundaries remain security / lifecycle / lot / concentration / capital competition boundaries, not hidden Market Quality or Risk Pacing rewrites.

## A - BEAR Inventory

Regime distribution over the trusted 252BD window:

| Regime | Business days |
| --- | ---: |
| BULL | 111 |
| RANGE | 46 |
| RECOVERY | 46 |
| BEAR | 33 |
| CORRECTION | 16 |

All 33 BEAR days had:

- `risk_pacing_intent = CAUTIOUS_DEPLOYMENT`
- `cash_preference_semantic = OPTIONALITY_ELEVATED`
- Market Quality either `SHORT_TERM_BREADTH_BREAKDOWN` or `CONFLICTED_MARKET_STRUCTURE`

BEAR aggregate:

| Metric | BEAR value |
| --- | ---: |
| BEAR BD count | 33 |
| Average exposure | 0.569086 |
| Median exposure | 0.560659 |
| Average cash | 535,713 JPY |
| Average candidate count | 50.00 |
| Average deployable competitor count | 3.333 |
| Median deployable competitor count | 3 |
| Average BUY_NEW consideration count | 44.848 |
| Average ADD consideration count | 0.182 |
| Actual BUY_NEW fills | 56 |
| Actual BUY_ADD fills | 2 |

BEAR daily inventory:

| Date | MQ | Exposure | Cash | Positions | Candidates | Deployable | HIGH | FULL | BUY_NEW fills | BUY_ADD fills |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 2022-10-03 | SHORT_TERM_BREADTH_BREAKDOWN | 0.510515 | 495,530 | 0 | 50 | 9 | 1 | 1 | 7 | 0 |
| 2022-10-11 | CONFLICTED_MARKET_STRUCTURE | 0.675674 | 338,340 | 11 | 50 | 2 | 4 | 3 | 0 | 0 |
| 2022-10-12 | SHORT_TERM_BREADTH_BREAKDOWN | 0.681206 | 329,400 | 11 | 50 | 2 | 3 | 3 | 1 | 1 |
| 2022-10-13 | SHORT_TERM_BREADTH_BREAKDOWN | 0.299697 | 720,780 | 12 | 50 | 6 | 1 | 1 | 1 | 1 |
| 2022-10-14 | SHORT_TERM_BREADTH_BREAKDOWN | 0.560555 | 457,410 | 12 | 50 | 5 | 5 | 4 | 4 | 0 |
| 2022-10-17 | SHORT_TERM_BREADTH_BREAKDOWN | 0.586405 | 429,250 | 16 | 50 | 3 | 5 | 4 | 2 | 0 |
| 2022-10-18 | CONFLICTED_MARKET_STRUCTURE | 0.629461 | 387,550 | 16 | 50 | 5 | 6 | 5 | 1 | 0 |
| 2022-12-20 | SHORT_TERM_BREADTH_BREAKDOWN | 0.505295 | 544,740 | 65 | 50 | 4 | 4 | 3 | 0 | 0 |
| 2022-12-21 | SHORT_TERM_BREADTH_BREAKDOWN | 0.422861 | 636,400 | 65 | 50 | 12 | 3 | 2 | 7 | 0 |
| 2022-12-22 | SHORT_TERM_BREADTH_BREAKDOWN | 0.583108 | 467,540 | 69 | 50 | 5 | 5 | 4 | 3 | 0 |
| 2022-12-23 | SHORT_TERM_BREADTH_BREAKDOWN | 0.678587 | 358,340 | 72 | 50 | 2 | 4 | 3 | 1 | 0 |
| 2022-12-26 | SHORT_TERM_BREADTH_BREAKDOWN | 0.701434 | 333,740 | 73 | 50 | 2 | 5 | 4 | 1 | 0 |
| 2022-12-27 | CONFLICTED_MARKET_STRUCTURE | 0.669159 | 371,740 | 73 | 50 | 2 | 4 | 3 | 1 | 0 |
| 2022-12-28 | CONFLICTED_MARKET_STRUCTURE | 0.485874 | 577,240 | 74 | 50 | 2 | 4 | 3 | 0 | 0 |
| 2022-12-29 | CONFLICTED_MARKET_STRUCTURE | 0.631493 | 410,340 | 74 | 50 | 5 | 4 | 3 | 4 | 0 |
| 2022-12-30 | CONFLICTED_MARKET_STRUCTURE | 0.502680 | 554,840 | 75 | 50 | 3 | 4 | 3 | 1 | 0 |
| 2023-01-04 | CONFLICTED_MARKET_STRUCTURE | 0.622199 | 420,640 | 76 | 50 | 4 | 3 | 2 | 3 | 0 |
| 2023-01-05 | SHORT_TERM_BREADTH_BREAKDOWN | 0.559516 | 488,140 | 79 | 50 | 1 | 6 | 5 | 0 | 0 |
| 2023-01-06 | CONFLICTED_MARKET_STRUCTURE | 0.560659 | 488,640 | 79 | 50 | 4 | 5 | 4 | 2 | 0 |
| 2023-01-10 | CONFLICTED_MARKET_STRUCTURE | 0.622222 | 420,320 | 80 | 50 | 3 | 5 | 4 | 2 | 0 |
| 2023-01-11 | CONFLICTED_MARKET_STRUCTURE | 0.495492 | 560,170 | 81 | 50 | 4 | 6 | 5 | 2 | 0 |
| 2023-01-12 | CONFLICTED_MARKET_STRUCTURE | 0.636824 | 403,870 | 82 | 50 | 3 | 2 | 2 | 1 | 0 |
| 2023-01-13 | CONFLICTED_MARKET_STRUCTURE | 0.608667 | 439,170 | 83 | 50 | 3 | 3 | 3 | 2 | 0 |
| 2023-01-16 | CONFLICTED_MARKET_STRUCTURE | 0.698990 | 335,470 | 84 | 50 | 2 | 5 | 4 | 1 | 0 |
| 2023-01-17 | CONFLICTED_MARKET_STRUCTURE | 0.729815 | 301,680 | 85 | 50 | 2 | 7 | 6 | 2 | 0 |
| 2023-04-05 | SHORT_TERM_BREADTH_BREAKDOWN | 0.603679 | 638,870 | 164 | 50 | 2 | 2 | 2 | 0 | 0 |
| 2023-04-06 | SHORT_TERM_BREADTH_BREAKDOWN | 0.515369 | 810,250 | 164 | 50 | 3 | 4 | 4 | 2 | 0 |
| 2023-04-07 | SHORT_TERM_BREADTH_BREAKDOWN | 0.450177 | 875,610 | 165 | 50 | 1 | 3 | 3 | 0 | 0 |
| 2023-10-03 | SHORT_TERM_BREADTH_BREAKDOWN | 0.540971 | 777,600 | 308 | 50 | 1 | 6 | 5 | 1 | 0 |
| 2023-10-04 | SHORT_TERM_BREADTH_BREAKDOWN | 0.552844 | 736,980 | 309 | 50 | 3 | 4 | 4 | 2 | 0 |
| 2023-10-05 | SHORT_TERM_BREADTH_BREAKDOWN | 0.410059 | 991,780 | 310 | 50 | 2 | 6 | 5 | 1 | 0 |
| 2023-10-06 | SHORT_TERM_BREADTH_BREAKDOWN | 0.541884 | 759,580 | 310 | 50 | 1 | 3 | 3 | 1 | 0 |
| 2023-10-10 | SHORT_TERM_BREADTH_BREAKDOWN | 0.506464 | 816,580 | 311 | 50 | 2 | 6 | 5 | 0 | 0 |

## B - Opportunity Scarcity vs Suppression

BEAR not-deployed PC member rows: 1,432.

Primary first-boundary classification:

| Primary reason | Count |
| --- | ---: |
| EXPECTED_EDGE_INSUFFICIENT | 569 |
| CONTINUATION_INSUFFICIENT | 431 |
| BQ_INSUFFICIENT | 333 |
| OTHER | 59 |
| LOST_TO_BETTER_NEW | 33 |
| CONCENTRATION_HEADROOM | 6 |
| LOT_INFEASIBLE | 1 |
| MARKET_QUALITY_SUPPRESSION | 0 |
| RISK_PACING_SUPPRESSION | 0 |
| CASH_OPTIONALITY | 0 as first decisive rejection boundary |

Interpretation:

- The dominant first boundaries are security-level or lifecycle-level: expected-edge, continuation / REENTRY, and Buy Quality.
- Cash / optionality is active every BEAR day, but the artifact evidence does not show it as the first invalidating boundary for otherwise fully deployable strong rows.
- Market Quality / Risk Pacing affects marginal capital competition, as intended, but did not appear as a standalone first decisive BUY/ADD rejection boundary in the audited BEAR rows.

Representative first-boundary examples:

| Date | Symbol | Semantic type | Rank | Evidence | First boundary |
| --- | --- | --- | ---: | --- | --- |
| 2022-10-03 | 44220 | BUY_NEW | 5 | `input_score=-0.09398367`, `quality_band=BUY_WAIT`, `opportunity_not_selected` | EXPECTED_EDGE_INSUFFICIENT |
| 2022-10-11 | 83060 | REENTRY | 9 | `reentry_trend_recovery_not_satisfied` | CONTINUATION_INSUFFICIENT |
| 2022-10-03 | 93180 | BUY_NEW | 4 | `quality_band=UNUSABLE`, `buy_quality_rejected` | BQ_INSUFFICIENT |
| 2022-10-11 | 39060 | BUY_NEW | 4 | `quality_band=HIGH`, `minimum_lot_exceeds_safety_hard_cap` | CONCENTRATION_HEADROOM |
| 2022-12-28 | 93180 | BUY_NEW | 3 | `quality_band=HIGH`, `minimum_lot_exceeds_remaining_budget` | LOT_INFEASIBLE |

## C - Strong Security / Weak Market Conflict Set

Conflict definition used existing categorical evidence only:

- BEAR regime.
- Market Quality defensive: `SHORT_TERM_BREADTH_BREAKDOWN` or `CONFLICTED_MARKET_STRUCTURE`.
- Risk Pacing: `CAUTIOUS_DEPLOYMENT`.
- Security evidence strong enough to audit:
  - `quality_band=HIGH` or `quality_action=FULL_ALLOCATION_ELIGIBLE`;
  - target member eligibility `PASS`;
  - Strategy Intelligence continuation status `PASS`;
  - Strategy Intelligence downside risk status `PASS`;
  - positive `input_score` / opportunity score;
  - no hard downside-risk reason code.

Results:

| Metric | Count |
| --- | ---: |
| Strong security rows in BEAR | 110 |
| Strong security rows selected / target-positive | 34 |
| Strong security weak-market conflicts not deployed | 76 |

First decisive block among the 76 conflict rows:

| Classification | Count |
| --- | ---: |
| SECURITY_WOULD_HAVE_FAILED_ANYWAY - REENTRY recovery/context boundary | 60 |
| SECURITY_WOULD_HAVE_FAILED_ANYWAY - BUY Quality wait | 9 |
| SECURITY_WOULD_HAVE_FAILED_ANYWAY - Safety/concentration cap | 6 |
| CAPITAL_COMPETITION_WOULD_HAVE_FAILED_ANYWAY - lot remaining budget | 1 |
| MARKET_RISK_FIRST_DECISIVE_BLOCK | 0 |
| INDETERMINATE | 0 |

Representative conflict rows:

| Date | Symbol | Type | Rank | BQ | PC / lifecycle outcome | Classification |
| --- | --- | --- | ---: | --- | --- | --- |
| 2022-10-14 | 39060 | BUY_NEW | 3 | HIGH / FULL | `minimum_lot_exceeds_safety_hard_cap` | SECURITY_WOULD_HAVE_FAILED_ANYWAY |
| 2022-12-20 | 94320 | REENTRY | 2 | HIGH / REDUCED | `reentry_trend_recovery_not_satisfied` | SECURITY_WOULD_HAVE_FAILED_ANYWAY |
| 2022-12-21 | 45410 | REENTRY | 4 | HIGH / REDUCED | `reentry_minimum_cooldown_not_satisfied` | SECURITY_WOULD_HAVE_FAILED_ANYWAY |
| 2022-12-28 | 93180 | BUY_NEW | 3 | HIGH / REDUCED | `minimum_lot_exceeds_remaining_budget` | CAPITAL_COMPETITION_WOULD_HAVE_FAILED_ANYWAY |
| 2023-01-05 | 83060 | REENTRY | 2 | HIGH / BUY_WAIT | `buy_quality_wait` | SECURITY_WOULD_HAVE_FAILED_ANYWAY |

## D - Was Market/Risk The First Decisive Block?

No.

The audited conflict set has 0 rows where Market Quality or Risk Pacing was proven to be the first decisive block. `RISK_PACING_CAUTION_STRONG_COMPETITOR_ALLOWED` appears on comparable / strong rows, meaning cautious BEAR state was consumed and recorded, but those rows then failed at REENTRY recovery, BUY_WAIT, concentration / safety cap, lot residual, or ordinary PC competition boundaries.

## E - Cash During BEAR

All 33 BEAR days had material Cash and `cash_preference_semantic=OPTIONALITY_ELEVATED`.

Cash evidence reason-code distribution:

| Reason code | BEAR days |
| --- | ---: |
| CAUTIOUS_MARKET_OPTIONALITY_ELEVATED | 33 |
| MARGINAL_OPPORTUNITY_SET | 33 |
| LOT_RESIDUAL_OPTIONALITY | 26 |
| UNAVOIDABLE_LOT_RESIDUAL | 26 |
| NO_VALID_COMPETITOR | 7 |

Cash interpretation:

- BEAR Cash is not explained by zero candidates. Each BEAR day still had 50 candidates and at least 1 deployable competitor.
- BEAR Cash is also not proven to be explained by Market/Risk first-boundary suppression of otherwise fully deployable strong opportunities.
- The canonical cash evidence says Cash won as optionality against a marginal opportunity set, residual lot constraints, or no-valid-competitor cases.

Classification:

`IS_BEAR_CASH_PRIMARILY_OPPORTUNITY_SCARCITY_OR_DEFENSIVE_SUPPRESSION = MIXED_BUT_NOT_PROVEN_OVER_SUPPRESSION`

More specifically:

- Opportunity scarcity / quality scarcity explains a large part: BEAR HIGH rate and FULL rate are materially lower than BULL/RANGE/RECOVERY.
- Defensive optionality is active every BEAR day and explains residual cash posture.
- Proven over-suppression is not established because `MARKET_RISK_FIRST_DECISIVE_BLOCK = 0`.

## F - Candidate Quality Distribution

Decision-time candidate substrate by regime:

| Regime | BD | Candidates/day | HIGH/day | FULL/day | Continuation PASS/day | Positive edge/day | Deployable/day |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BEAR | 33 | 50.00 | 4.18 | 3.48 | 39.06 | 5.67 | 3.33 |
| RANGE | 46 | 50.00 | 6.30 | 4.67 | 37.80 | 5.74 | 3.91 |
| BULL | 111 | 50.00 | 7.87 | 4.69 | 37.23 | 5.64 | 2.95 |
| RECOVERY | 46 | 50.00 | 6.39 | 3.89 | 37.52 | 5.15 | 3.13 |
| CORRECTION | 16 | 50.00 | 6.56 | 5.00 | 37.00 | 6.25 | 2.38 |

Candidate quality rates:

| Regime | HIGH rate | FULL rate | Positive-edge rate |
| --- | ---: | ---: | ---: |
| BEAR | 8.36% | 6.97% | 11.33% |
| RANGE | 12.61% | 9.35% | 11.48% |
| BULL | 15.75% | 9.39% | 11.28% |
| RECOVERY | 12.78% | 7.78% | 10.30% |
| CORRECTION | 13.13% | 10.00% | 12.50% |

Finding:

`ARE_HIGH_QUALITY_CANDIDATES_MATERIALLY_SCARCER_IN_BEAR = YES`

BEAR has materially fewer HIGH/FULL candidates than BULL, RANGE, and RECOVERY. Positive-edge counts are similar, so the scarcity is in Buy Quality / quality-adjusted deployability rather than raw positive-score availability.

## G - Selection Difficulty Comparison

Observed:

- BULL had the highest HIGH count per day, but lower deployable competitor count than BEAR in this run.
- RANGE had a higher deployable competitor count than BEAR and materially higher HIGH/FULL candidate rates.
- BEAR had fewer HIGH/FULL opportunities, yet did still deploy BUY_NEW and occasional BUY_ADD. This rules out blanket BEAR suppression.

Strong-row selected / target-positive rate:

| Regime | Strong rows | Selected strong rows | Selected rate |
| --- | ---: | ---: | ---: |
| BEAR | 110 | 34 | 30.91% |
| RANGE | 161 | 48 | 29.81% |
| BULL | 402 | 111 | 27.61% |
| RECOVERY | 142 | 33 | 23.24% |
| CORRECTION | 57 | 6 | 10.53% |

Finding:

Comparable strong security rows were not materially less likely to receive target-positive treatment in BEAR than in BULL/RANGE. The stronger evidence is that BEAR has fewer high-quality rows in the first place.

## H - Exposure Response

Regime-level exposure and capital deployment:

| Regime | Mean exposure | Median exposure | Avg cash | BUY_NEW fills | BUY_ADD fills | Target exposure avg |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BEAR | 0.569086 | 0.560659 | 535,713 | 56 | 2 | 0.740 |
| RANGE | 0.790139 | 0.808030 | 279,245 | 81 | 2 | 0.986 |
| BULL | 0.812103 | 0.855313 | 265,851 | 172 | 5 | 1.000 |
| RECOVERY | 0.807056 | 0.832182 | 274,297 | 73 | 0 | 1.000 |
| CORRECTION | 0.741005 | 0.774371 | 391,981 | 13 | 0 | 0.865 |

Finding:

BEAR Exposure is lower partly because Portfolio Policy target exposure is lower (`0.74` vs approximately `1.0` in BULL/RANGE/RECOVERY) and because Cash optionality remains elevated. This is documented defensive behavior. The evidence does not show Market/Risk silently overriding a comparable supply of strong opportunities.

## I - Cross-Regime Comparable Opportunity Cases

Using the existing categorical strong-row definition:

- BEAR strong-row selected rate: 30.91%
- RANGE strong-row selected rate: 29.81%
- BULL strong-row selected rate: 27.61%

Therefore:

`ARE_COMPARABLE_SECURITIES_TREATED_MATERIALLY_MORE_DEFENSIVELY_IN_BEAR = NO`

Important limitation:

- This is categorical artifact comparison, not a new score or simulation.
- It does not say BEAR defense is profit-optimal.
- It only says the current evidence does not prove that comparable strong securities are treated materially worse in BEAR solely because of regime/risk state.

## J - Existing Risk Pacing Intent Match

Classification:

`INTENDED_DEFENSE`

Reason:

- BEAR maps to cautious deployment and elevated optionality.
- The system still deploys BUY_NEW and BUY_ADD in BEAR.
- `STRONG` / `COMPARABLE_HIGH` opportunities can pass through cautious deployment.
- Cash competes explicitly with marginal opportunity sets.
- No fixed exposure target, fixed BUY count, or blanket BUY ban is inferred downstream.

## K - POST_HOC_DIAGNOSTIC_ONLY

No post-hoc future-return / MFE / MAE characterization was performed because the frozen decision-time classification found:

`MARKET_RISK_FIRST_DECISIVE_BLOCK = 0`

Therefore there is no canonical set of BEAR opportunities proven to be suppressed first by Market/Risk for which alpha enrichment can be meaningfully characterized under this task's rules.

`DO_POST_HOC_OUTCOMES_SHOW_ALPHA_ENRICHMENT_IN_SUPPRESSED_CASES = INSUFFICIENT_EVIDENCE / NOT_APPLICABLE`

No future outcomes were used to define quality, classify causes, or recommend parameters.

## L - False-Defense vs Correct-Defense Matrix

Decision-time matrix:

| Class | Count | Evidence |
| --- | ---: | --- |
| CORRECT_DEFENSE_WEAK_SECURITY | 1,333 | expected-edge, continuation / REENTRY, or BQ first-boundary insufficiency |
| CORRECT_DEFENSE_STRONG_SECURITY_BUT_HIGH_MARKET_RISK | 0 | no market/risk first-boundary strong cases proven |
| POSSIBLE_OVER_SUPPRESSION | 1 | 2022-12-28 `93180`, HIGH, positive score, lost at lot remaining budget after PC competition |
| CLEAR_OVER_SUPPRESSION | 0 | no row where Market/Risk first invalidated a fully deployable strong security |
| INSUFFICIENT_EVIDENCE | 98 | OTHER / lifecycle rows not suitable for over-suppression conclusion |

The one possible case is not a proven Market/Risk defect. It is a lot / residual capital case after PC competition, and does not by itself justify Production change.

## M - Materiality

Classification:

`IS_BEAR_DEFENSE_OVER_SUPPRESSION_MATERIAL = NO`

Reason:

- `MARKET_RISK_FIRST_DECISIVE_BLOCK = 0`.
- Strong-row selected rates are not lower in BEAR than BULL/RANGE.
- BEAR has materially fewer HIGH/FULL candidates, supporting real quality scarcity.
- Cash optionality is repeated across BEAR episodes, but the associated reason codes are documented and paired with marginal opportunity sets, lot residual, or no-valid-competitor evidence.

Affected days:

- Defensive optionality is present on all 33 BEAR days.
- Proven over-suppression days: 0.
- Possible non-defect residual / lot concern: 1 row, `2022-12-28 93180`.

## N - Falsification

### H0 - BEAR Exposure is low mainly because good opportunities are genuinely scarce.

Evidence for:

- BEAR HIGH rate: 8.36%, below BULL 15.75%, RANGE 12.61%, RECOVERY 12.78%, CORRECTION 13.13%.
- BEAR FULL rate: 6.97%, below BULL/RANGE/CORRECTION.
- BEAR non-deployed rows are mostly expected-edge, continuation / REENTRY, and BQ insufficiency.

Evidence against:

- BEAR still has some deployable competitors every day.
- Positive-edge candidate count is not materially lower than BULL/RANGE.

Verdict:

`SUPPORTED_BUT_NOT_COMPLETE`

### H1 - BEAR Market/Risk controls suppress a material number of otherwise strong opportunities.

Evidence for:

- Cash optionality and cautious deployment are active on all BEAR days.
- 76 strong-security / weak-market non-deployed conflicts exist under strict categorical evidence.

Evidence against:

- 0 of the 76 conflicts had Market/Risk as the first decisive block.
- Most conflicts failed REENTRY recovery/context, BUY_WAIT, concentration/safety cap, or lot residual.
- Strong-row selected rate is not worse in BEAR than BULL/RANGE.

Verdict:

`NOT_SUPPORTED_AS_MATERIAL_CURRENT_DEFECT`

### H2 - Scarcity and suppression are both material.

Evidence for:

- Quality scarcity is material.
- Defensive optionality is active.

Evidence against:

- Suppression is active as intended optionality, but not proven as first-boundary over-suppression.

Verdict:

`PARTIAL_ONLY`

### H3 - BEAR defense is appropriate, but Cash / PC capital competition creates the apparent suppression.

Evidence for:

- Cash is a first-class competitor by SoT.
- Cash evidence on all BEAR days cites `CAUTIOUS_MARKET_OPTIONALITY_ELEVATED` and `MARGINAL_OPPORTUNITY_SET`.
- BEAR deployments still occur.
- No blanket BUY ban or hidden Risk Pacing rejection is observed.

Evidence against:

- The repeated high cash posture still warrants monitoring over a longer 650BD run because BEAR episodes are only 33BD in this trusted window.

Verdict:

`BEST_EXPLANATION_WITH_H0`

## O - Decision Gate

Decision:

`BEAR_DEFENSE_MOSTLY_JUSTIFIED`

Secondary characterization:

`BEAR_OPPORTUNITY_SCARCITY_PRIMARY_WITH_INTENDED_DEFENSIVE_OPTIONALITY`

No Production change is justified by this audit.

## Required Final Answers

1. `HOW_MANY_BEAR_DAYS_EXIST`
   - 33.

2. `WHAT_IS_BEAR_AVERAGE_AND_MEDIAN_EXPOSURE`
   - Average: 0.569086.
   - Median: 0.560659.

3. `ARE_HIGH_QUALITY_CANDIDATES_MATERIALLY_SCARCER_IN_BEAR`
   - YES. BEAR HIGH rate is 8.36% vs BULL 15.75%, RANGE 12.61%, RECOVERY 12.78%.

4. `HOW_MANY_STRONG_SECURITY_WEAK_MARKET_CONFLICTS_EXIST`
   - 76 not-deployed conflicts under strict existing categorical evidence.

5. `HOW_MANY_HAVE_MARKET_RISK_AS_THE_FIRST_DECISIVE_BLOCK`
   - 0.

6. `HOW_MUCH_BEAR_CASH_IS_EXPLAINED_BY_OPPORTUNITY_SCARCITY`
   - Materially: BEAR quality scarcity and first-boundary insufficiency explain the majority of non-deployed rows. Row evidence: 1,333 / 1,432 non-deployed rows are expected-edge, continuation / REENTRY, or BQ insufficiency.

7. `HOW_MUCH_IS_EXPLAINED_BY_MARKET_RISK_SUPPRESSION`
   - Defensive optionality is present on 33 / 33 BEAR days, but proven Market/Risk first-boundary suppression is 0 rows. Therefore over-suppression amount is not proven.

8. `ARE_COMPARABLE_SECURITIES_TREATED_MATERIALLY_MORE_DEFENSIVELY_IN_BEAR`
   - NO. Strong-row selected rate is BEAR 30.91%, RANGE 29.81%, BULL 27.61%.

9. `DOES_ACTUAL_BEAR_BEHAVIOR_MATCH_ARCHITECTURE_INTENT`
   - YES, classified `INTENDED_DEFENSE`.

10. `DO_POST_HOC_OUTCOMES_SHOW_ALPHA_ENRICHMENT_IN_SUPPRESSED_CASES`
    - INSUFFICIENT_EVIDENCE / NOT_APPLICABLE. No `MARKET_RISK_FIRST_DECISIVE_BLOCK` set exists, so no post-hoc suppressed-alpha set was evaluated.

11. `IS_BEAR_DEFENSE_OVER_SUPPRESSION_MATERIAL`
    - NO.

12. `WHICH_HYPOTHESIS_H0_H3_BEST_EXPLAINS_THE_EVIDENCE`
    - H3 with H0: intended Cash / PC defensive optionality plus real BEAR high-quality scarcity.

13. `IS_ANY_CORRECTNESS_DEFECT_PRESENT`
    - NO.

14. `IS_ANY_PRODUCTION_CHANGE_JUSTIFIED`
    - NO.

15. `SHOULD_THIS_BE_REVISITED_AFTER_THE_CURRENT_650BD_LONG_RUN`
    - YES. Not because a correctness defect is proven, but because 33 BEAR days is a limited sample for repeated-episode performance characterization.

## No Change Confirmation

- NO CODE CHANGE.
- NO CONFIG CHANGE.
- NO RUNTIME STATE CHANGE.
- NO STRATEGY PARAMETER / THRESHOLD / WEIGHT / CAP CHANGE.
- NO REGIME / RISK PACING / MARKET QUALITY CHANGE.
- NO CASH / BUY_NEW / BUY_ADD CHANGE.
- NO fresh-run / resume / replay / recover / long Historical executed by Codex.
- NO future-information use in decision-time classifications.

## Final Judgment

`PHASE32_AS_BEAR_DEFENSE_MOSTLY_JUSTIFIED_NO_CORRECTNESS_DEFECT_NO_PRODUCTION_CHANGE`

Current evidence distinguishes:

- genuine opportunity scarcity: YES, material in HIGH/FULL candidate availability;
- correct defensive behavior: YES, Cash optionality and cautious deployment match SoT;
- possible over-suppression: one residual / lot case, not Market/Risk first-boundary;
- proven over-suppression: NO;
- post-hoc diagnostic evidence: NOT APPLICABLE because no Market/Risk-first suppressed set was established.
