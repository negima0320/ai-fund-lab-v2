# Phase30-AJ0 - Post-AI 12BD Production Action Effectiveness / Candidate Coverage Audit

Task ID: `Phase30-AJ0`

Boundary:

```text
READ_ONLY
NO_IMPLEMENTATION
NO_THRESHOLD_TUNING
NO_CANDIDATE_COUNT_CHANGE
NO_MODEL_RETRAINING
NO_TARGET_RUN_MUTATION
NO_RESUME_REPLAY
NO_HISTORICAL_OUTCOME_FIT
```

Compared runs:

```text
BEFORE = runtime-test-historical-extended-smoke-20260816T061732506648Z
AFTER  = runtime-test-historical-extended-smoke-20260816T084143736072Z
WINDOW = 2022-08-10 -> 2022-08-26, 12BD
```

Evidence:

```text
reports/phase_reports/phase30_aj0_post_ai_12bd_action_effectiveness_candidate_coverage_audit.json
reports/phase_reports/phase30_aj0/aggregate_evidence.json
reports/phase_reports/phase30_aj0/daily_diff_evidence.json
```

## Primary Judgment

```text
QUALITY_COMPARATOR_MATERIALIZED = YES
QUALITY_COMPARATOR_CHANGED_PC_COMPETITION = NO
SOFT_REJECTION_RETIREMENT_ACTION_EFFECT = NO
CANDIDATE_TOP50_CHANGED = NO
CANDIDATE_GENERATION_COVERAGE_GAP = YES
AI_PRODUCTION_ACTION_EFFECT = NO_EFFECT
12BD_IDENTICAL_BEHAVIOR_ROOT_CAUSE =
NO_UPSTREAM_CANDIDATE_DIFFERENCE_AND_PC_TARGET_RECONVERGENCE_AT_EXISTING_EQUAL_TARGETS
```

Phase30-AI reached the Production artifact path. The after-run SI artifact is
`semantic_version=1.4.0` and `producer_version=phase30_ai_selection_quality_comparator.v1`,
with `runtime_consumer_eligibility=ELIGIBLE`.

The 12BD behavior stayed identical because the upstream Candidate Top50 content
and Opportunity rank/score content stayed identical, and the new comparator did
not change action-effective PC target membership, PC target weights, PS
quantity, Runtime intent, fills, or portfolio state.

## 12BD Before / After Equality

Action-effective layer comparison:

```text
FIRST_BEHAVIORAL_DIFFERENCE_LAYER = NONE
```

Observable non-action layer comparison:

```text
STRATEGY_INTELLIGENCE_QUALITY_COMPARATOR_MATERIALIZATION = 12 / 12 days
```

Daily portfolio equality:

| Date | Equity | Cash | Exposure | Positions | Holdings / quantity equality |
|---|---:|---:|---:|---:|---|
| 2022-08-10 | 994,000 | 688,580 | 30.7264% | 9 | equal |
| 2022-08-12 | 998,740 | 762,780 | 23.6258% | 7 | equal |
| 2022-08-15 | 1,001,660 | 733,580 | 26.7636% | 8 | equal |
| 2022-08-16 | 989,880 | 786,000 | 20.5964% | 7 | equal |
| 2022-08-17 | 993,590 | 693,820 | 30.1704% | 8 | equal |
| 2022-08-18 | 987,300 | 816,600 | 17.2896% | 7 | equal |
| 2022-08-19 | 988,260 | 857,500 | 13.2313% | 4 | equal |
| 2022-08-22 | 989,100 | 852,260 | 13.8348% | 2 | equal |
| 2022-08-23 | 988,830 | 821,900 | 16.8816% | 2 | equal |
| 2022-08-24 | 990,640 | 651,910 | 34.1930% | 3 | equal |
| 2022-08-25 | 993,090 | 741,060 | 25.3784% | 3 | equal |
| 2022-08-26 | 986,720 | 741,060 | 24.8966% | 3 | equal |

All checked downstream signatures were equal:

```text
PC_TARGET_EQUAL_ALL_DAYS = YES
PS_QUANTITY_EQUAL_ALL_DAYS = YES
RUNTIME_PLANNING_EQUAL_ALL_DAYS = YES
FILLS_EQUAL_ALL_DAYS = YES
PORTFOLIO_EQUAL_ALL_DAYS = YES
```

## Candidate Top50

```text
CANDIDATE_TOP50_CHANGED = NO
```

For all 12 days:

- overlap count = 50 / 50;
- ordering difference count = 0;
- added symbols = none;
- removed symbols = none.

The source artifact hashes differ between runs because artifacts were
regenerated with run-local metadata, but the Candidate Top50 symbols and
ordering consumed by PC are identical.

## Quality Comparator Materialization

```text
QUALITY_COMPARATOR_MATERIALIZED = YES
```

12BD total tier distribution:

```text
CAUTION_CONTINUATION = 563
HIGH_QUALITY_CONTINUATION = 6
REJECT = 32
VALID_CONTINUATION = 0
INSUFFICIENT_QUALITY = 0
```

Daily tier distribution:

| Date | HIGH | VALID | CAUTION | INSUFFICIENT | REJECT |
|---|---:|---:|---:|---:|---:|
| 2022-08-10 | 0 | 0 | 49 | 0 | 1 |
| 2022-08-12 | 1 | 0 | 46 | 0 | 3 |
| 2022-08-15 | 0 | 0 | 47 | 0 | 3 |
| 2022-08-16 | 0 | 0 | 46 | 0 | 4 |
| 2022-08-17 | 1 | 0 | 45 | 0 | 4 |
| 2022-08-18 | 0 | 0 | 48 | 0 | 3 |
| 2022-08-19 | 2 | 0 | 45 | 0 | 3 |
| 2022-08-22 | 0 | 0 | 47 | 0 | 3 |
| 2022-08-23 | 1 | 0 | 47 | 0 | 2 |
| 2022-08-24 | 1 | 0 | 47 | 0 | 2 |
| 2022-08-25 | 0 | 0 | 48 | 0 | 2 |
| 2022-08-26 | 0 | 0 | 48 | 0 | 2 |

The comparator is therefore present, but overwhelmingly classifies candidates
as `CAUTION_CONTINUATION`.

## Comparator PC Effect

```text
QUALITY_COMPARATOR_CHANGED_PC_COMPETITION = NO
```

Comparator ordering signal was materialized, but no action-effective PC output
changed:

```text
PC membership changed = 0
target_weight changed = 0
```

Semantic ordering movement, before target equality re-converged:

```text
rank_up = 444
rank_down = 127
rank_same = 30
```

This movement did not affect target membership or target weights because the
existing PC allocation for these 12BD already selected the same eligible member
set and equal target-weight contract.

## Soft-Rejection Retirement Effect

```text
SOFT_REJECTION_RETIREMENT_ACTION_EFFECT = NO
```

Theoretical legacy hard-drop cohort under retired score/rank behavior:

```text
theoretical_legacy_hard_drop = 499
pc_competition_recovered = 242
positive_target = 115
ps_positive = 18
buy_fill = 18
actual_pc_ps_change_vs_before = 0
```

Interpretation:

- These score/rank soft reasons are visible in the after-run.
- However, the before-run had already preserved uncalibrated score/rank as soft
  metadata through earlier Phase29/Phase30 contracts.
- Therefore Phase30-AI did not create a new 12BD action effect from soft
  rejection retirement.

## Re-Convergence Layer

```text
RECONVERGENCE_LAYER = PC_TARGET_RECONVERGENCE
```

More precisely:

```text
NO_UPSTREAM_CANDIDATE_DIFFERENCE
SI_COMPARATOR_MATERIALIZED
PC_TARGET_MEMBERSHIP_AND_TARGET_WEIGHTS_EQUAL
PS_QUANTITIES_EQUAL
RUNTIME_INTENTS_EQUAL
FILLS_EQUAL
```

So the dominant explanation is not a Runtime defect. The new evidence arrived,
but the action-effective target portfolio did not move.

## Candidate Coverage

```text
CANDIDATE_GENERATION_COVERAGE_GAP = YES
```

12BD averages:

```text
market_healthy_proxy_count_avg = 460.250
candidate_healthy_proxy_count_avg = 10.417
candidate_capture_ratio_avg = 2.3465%
```

Daily capture:

| Date | Market healthy proxy | Candidate healthy proxy | Capture ratio |
|---|---:|---:|---:|
| 2022-08-10 | 302 | 8 | 2.6490% |
| 2022-08-12 | 429 | 8 | 1.8648% |
| 2022-08-15 | 409 | 9 | 2.2005% |
| 2022-08-16 | 374 | 11 | 2.9412% |
| 2022-08-17 | 541 | 8 | 1.4787% |
| 2022-08-18 | 714 | 12 | 1.6807% |
| 2022-08-19 | 533 | 13 | 2.4390% |
| 2022-08-22 | 533 | 11 | 2.0638% |
| 2022-08-23 | 403 | 9 | 2.2333% |
| 2022-08-24 | 335 | 12 | 3.5821% |
| 2022-08-25 | 496 | 14 | 2.8226% |
| 2022-08-26 | 454 | 10 | 2.2026% |

Top10 quality distribution over 12BD:

```text
CAUTION_CONTINUATION = 101
HIGH_QUALITY_CONTINUATION = 2
REJECT = 17
```

The center of gravity is upstream of the comparator: most market PIT healthy
proxy candidates are never surfaced into Candidate Top50. The comparator can
only compare the 50 candidates it receives.

## Candidate AI Authority

Candidate stage authority classification:

| Evidence | Classification |
|---|---|
| model score / candidate score | PRIMARY |
| candidate rank | PRIMARY |
| high candidate score reason | PRIMARY |
| volume momentum reason | SECONDARY |
| liquidity available reason | SECONDARY |
| 5D / 20D trend | SECONDARY |
| MA5 / MA20 | SECONDARY |
| participation / volume | SECONDARY |
| Continuation Quality | NOT_AVAILABLE_AT_CANDIDATE_STAGE |
| Relative Strength | NOT_AVAILABLE_AT_CANDIDATE_STAGE |
| Downside Risk | NOT_AVAILABLE_AT_CANDIDATE_STAGE |
| Entry Admission | NOT_AVAILABLE_AT_CANDIDATE_STAGE |
| Strategy Intelligence quality tier | NOT_AVAILABLE_AT_CANDIDATE_STAGE |

Candidate AI / Top50 remains the dominant upstream surface authority. Phase30-AI
did not change Candidate authority, so exact Candidate equality is expected.

## No False Conclusion

Case classification:

```text
CASE_C
Comparator materialized
Candidate Top50 unchanged
quality coverage remains narrow before comparator sees the market
```

This is not Case D: the comparator did reach Production artifacts.

This is not a confirmed Runtime defect: Runtime mapped identical PS-positive
quantity evidence into identical fills.

## Regression Check

```text
PHASE30_AI_IMPLEMENTATION_DEFECT = NO
PHASE30_AE1_ADD_CONVERSION_PRESERVED = YES
PHASE30_W_ENTRY_ADMISSION_PRESERVED = YES
PHASE30_Z_REENTRY_PRESERVED = YES
```

## Implementation Authorization

```text
NO IMPLEMENTATION AUTHORIZED BY_PHASE30_AJ0
```

## Recommended Next Task

```text
Phase30-AJ1 - Candidate AI / Top50 Market PIT Quality Surface Design Audit
```

Scope: design how the existing Candidate AI / Top50 authority should surface
market PIT quality evidence better, without adding a parallel Candidate engine,
without simply increasing Top50 count, and without fitting to Historical
outcomes.
