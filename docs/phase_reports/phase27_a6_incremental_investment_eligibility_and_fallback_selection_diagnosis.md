# Phase27-A6 — Incremental Investment Eligibility and Fallback Selection Diagnosis

## 1. Scope

Task ID: Phase27-A6

Task Type: Observability Only / Read-only Performance Diagnosis

Baseline Run:

```text
runtime-test-historical-smoke-20260804T074611098414Z
```

Period:

```text
2023-01-04 through 2023-05-31
100 business days
```

Primary Judgment:

```text
PHASE27_A6_INCREMENTAL_ELIGIBILITY_DIAGNOSIS_COMPLETE_CURRENT_LOGIC_PARTIALLY_VALID
```

Root diagnosis:

```text
INCREMENTAL_ELIGIBILITY_NOT_EXPLICIT_AND_MULTI_STAGE_RELATIVE_FALLBACK_PROBLEM
```

Scope:

```text
Observed Quality / Portfolio Construction Funnel Only
```

Full candidate-universe superiority is not claimed.

## 2. Safety Boundary

This task did not change Runtime, Strategy, Candidate, Opportunity, BUY Quality, Portfolio Policy, Portfolio Construction, Position Sizing, Planning, Submit, Safety, PM, Exit, or Re-entry logic.

No fresh-run, resume, historical rerun, 100BD rerun, or long regression was executed.

All outputs are post-hoc human-review evidence only and are not Strategy inputs.

## 3. Generated Artifacts

Generator:

```text
tools/phase27_analysis/phase27_a6_generate_incremental_eligibility_diagnosis.py
```

Output directory:

```text
reports/phase27_a6_incremental_investment_eligibility_and_fallback_selection_diagnosis/
```

Generated files:

```text
summary.json
buy_incremental_eligibility.csv
buy_incremental_eligibility.json
fallback_status_analysis.csv
fallback_status_analysis.json
incremental_eligibility_classification.csv
incremental_eligibility_classification.json
absolute_score_daily_distribution.csv
absolute_score_daily_distribution.json
fallback_sequence_analysis.csv
fallback_sequence_analysis.json
no_buy_contract_audit.json
implicit_buy_pressure_audit.json
quality_eligibility_semantics_audit.json
fallback_vs_no_buy_daily_audit.csv
fallback_vs_no_buy_daily_audit.json
focus_case_audits.json
performance_by_incremental_eligibility.json
hypothesis_judgments.json
root_diagnosis.json
evidence_limitations.json
test_results.json
```

## 4. Method

The analysis separates:

```text
Relative Selection
```

from:

```text
Absolute / Incremental Eligibility
```

Each of the 25 actual BUYs was classified using PIT evidence only: Opportunity Score, daily observed-funnel distribution, Quality Action, Quality components, Portfolio Fit, Market Context, Portfolio Policy, existing position state, Position Sizing, and Planning evidence.

Post-hoc performance was attached only after incremental eligibility classes were fixed.

No counterfactual trade PnL was generated.

## 5. Fallback Status

Fallback status counts:

| Fallback Status | BUY Count |
|---|---:|
| PRIMARY_BEST_AVAILABLE | 3 |
| NEAR_TIE_ALTERNATIVE | 9 |
| FALLBACK_AFTER_EXISTING_POSITION_ZERO_DELTA | 6 |
| FALLBACK_AFTER_MULTIPLE_INELIGIBILITY | 7 |

No BUY was classified as a proven case of forced deployment or ignored stronger executable candidate.

Fallback sequence counts:

| Sequence | BUY Count |
|---|---:|
| 0 | 3 |
| 1 | 5 |
| 2 | 3 |
| 3+ | 14 |

The majority of BUYs were fallback or near-tie selections after one or more higher-ranked candidates had dropped out.

## 6. Incremental Eligibility

Incremental eligibility classes:

| Class | BUY Count |
|---|---:|
| MODERATE_INCREMENTAL_ELIGIBILITY | 18 |
| RELATIVE_ONLY_ELIGIBILITY | 5 |
| WEAK_INCREMENTAL_ELIGIBILITY | 2 |
| STRONG_INCREMENTAL_ELIGIBILITY | 0 |
| NO_CLEAR_INCREMENTAL_CASE | 0 |
| INSUFFICIENT_EVIDENCE | 0 |

Interpretation:

Most BUYs had a moderate PIT case for incremental investment. However, no BUY met the stricter diagnostic strong class, and 7 BUYs were weak or relative-only. The weak/relative-only group is the clearest A6 performance-improvement target, not an architecture defect.

The diagnostic classes are not Runtime thresholds and are not Strategy inputs.

## 7. Absolute Score and Daily Distribution

A6 evaluated each BUY against its same-day observed funnel:

```text
absolute opportunity score
daily mean
daily median
daily standard deviation
daily percentile
distance from rank1
distance from top3 mean
distance from eligible-candidate mean
```

Several fallback BUYs had high daily percentile but very low absolute score, including:

| Date | Symbol | Rank | Score | Percentile | Class |
|---|---:|---:|---:|---:|---|
| 2023-01-31 | 77760 | 5 | 0.037980 | 0.92 | RELATIVE_ONLY_ELIGIBILITY |
| 2023-02-10 | 54010 | 5 | 0.007477 | 0.92 | RELATIVE_ONLY_ELIGIBILITY |
| 2023-02-20 | 42640 | 4 | 0.008694 | 0.94 | RELATIVE_ONLY_ELIGIBILITY |
| 2023-03-29 | 93180 | 6 | 0.034897 | 0.90 | RELATIVE_ONLY_ELIGIBILITY |
| 2023-05-16 | 24350 | 6 | 0.002294 | 0.90 | RELATIVE_ONLY_ELIGIBILITY |

This is the core distinction A6 was designed to expose: a candidate can be high within a weak daily observed distribution while still lacking a strong absolute incremental case.

## 8. No-BUY Contract Audit

No-BUY / 0 BUY day is valid:

```text
true
```

Evidence:

- Design: `strategy_architecture_v1` states that cash residual, target_weight=0, whole-portfolio BUY 0, and maintaining existing holdings can be normal Strategy outcomes.
- Implementation: Runtime Planning and Submit contain `NO_ACTION`, `NO_ORDER`, and `NO_ORDER_AUTHORIZED` paths.
- Run evidence: 79 of 100 business days had zero executed BUY.

Audit judgments:

| Item | Judgment |
|---|---:|
| Fixed minimum BUY count exists | false |
| Fixed target position count consumer exists | false |
| Exposure target forces weak BUY | false |
| Portfolio Construction must fill available slots | false |
| Planning must emit BUY when eligible row exists | false |
| Cash holding is allowed | true |

Residual `target_position_count` and related vocabulary exists in code/docs, but the audit classified it as non-decision metadata, documentation, deprecated compatibility, or observability. No active invalid Decision Consumer was found.

## 9. Quality Eligibility Semantics

Quality Action semantics:

| Action | A6 Interpretation |
|---|---|
| FULL_ALLOCATION_ELIGIBLE | Allocation eligibility/scaling authority, not a must-buy instruction |
| REDUCED_ALLOCATION_ONLY | Reduced allocation eligibility, not proof that BUY beats cash |
| REJECT | Not usable for BUY allocation at Quality stage |

Quality Action does not represent calibrated expected return, win probability, or an explicit selected-vs-cash incremental investment authority.

Judgment:

```text
QUALITY_ACTION_IS_ALLOCATION_ELIGIBILITY_AND_SCALING_AUTHORITY_NOT_EXPLICIT_INCREMENTAL_INVESTMENT_CASE
```

## 10. Fallback vs No-BUY Daily Audit

Fallback BUY occurred on 19 business days.

Daily diagnoses:

| Daily Diagnosis | Days |
|---|---:|
| FALLBACK_SUPPORTED_BY_MODERATE_INCREMENTAL_CASE | 14 |
| FALLBACK_PRIMARILY_RELATIVE_SELECTION | 4 |
| INSUFFICIENT_EVIDENCE | 1 |

No-BUY was contractually valid on these days. The evidence does not show forced cash deployment. It does show that some fallback BUYs were primarily relative selections rather than strong standalone incremental opportunities.

## 11. Post-hoc Performance

Performance was attached after PIT classification.

| Incremental Eligibility Class | BUY Count | PnL | PF | Re-entry Count |
|---|---:|---:|---:|---:|
| MODERATE_INCREMENTAL_ELIGIBILITY | 18 | 7,690 | 1.0401 | 8 |
| RELATIVE_ONLY_ELIGIBILITY | 5 | -60,600 | 0.3810 | 1 |
| WEAK_INCREMENTAL_ELIGIBILITY | 2 | 5,390 | 2.1717 | 2 |

Required comparison:

| Group | BUY Count | PnL | PF |
|---|---:|---:|---:|
| STRONG + MODERATE | 18 | 7,690 | 1.0401 |
| WEAK + RELATIVE_ONLY + NO_CLEAR | 7 | -55,210 | 0.4614 |

This is post-hoc association only. It is not a threshold proposal.

## 12. Focus Case Findings

### 93180 campaign 0004

Rank 1 Re-entry, best available in the observed funnel. Incremental class:

```text
MODERATE_INCREMENTAL_ELIGIBILITY
```

No higher-ranked candidate existed. Post-hoc outcome: +38,900.

### 93180 campaign 0006

Rank 6 Re-entry after multiple higher-ranked candidate dropouts. Incremental class:

```text
RELATIVE_ONLY_ELIGIBILITY
```

Score was low in absolute terms even though daily percentile was high. No-BUY was contractually valid. Post-hoc outcome: -80,000.

### 76920 campaign 0002

Rank 6 Re-entry near-tie alternative. Incremental class:

```text
WEAK_INCREMENTAL_ELIGIBILITY
```

The selection was defensible as a near-tie fallback, but the independent incremental case was weak. Post-hoc outcome: +9,990.

### 76920 campaign 0003

Rank 2 Re-entry near-tie alternative. Incremental class:

```text
MODERATE_INCREMENTAL_ELIGIBILITY
```

Rank 1 was zero-weight/no-delta with a small score gap. Post-hoc outcome: -4,770.

### 30410 campaign 0001

Rank 1 initial entry, best available. Incremental class:

```text
MODERATE_INCREMENTAL_ELIGIBILITY
```

Post-hoc outcome: +120,000.

Additional focus cases are recorded in `focus_case_audits.json`.

## 13. Hypothesis Judgments

| Hypothesis | Judgment |
|---|---|
| H-A6-1 Most Fallback BUYs had independent investment eligibility | PARTIALLY_CONFIRMED |
| H-A6-2 Material share of Fallback BUYs were only relatively eligible | CONFIRMED |
| H-A6-3 Active implicit pressure to fill positions/deploy cash/backfill exists | REJECTED |
| H-A6-4 No-BUY was contractually and operationally valid | CONFIRMED |
| H-A6-5 Quality Action clearly distinguished absolute eligibility from relative preference | PARTIALLY_CONFIRMED |
| H-A6-6 Weak/relative fallback associated with Re-entry and poor post-hoc performance | PARTIALLY_CONFIRMED |
| H-A6-7 High cash was caused by lack of strong incremental opportunities rather than implementation failure | PARTIALLY_CONFIRMED |
| H-A6-8 Explicit incremental investment eligibility concept is needed | PARTIALLY_CONFIRMED |

## 14. Root Diagnosis

Supported:

```text
INCREMENTAL_ELIGIBILITY_NOT_EXPLICIT
MULTI_STAGE_RELATIVE_FALLBACK_PROBLEM
```

Rejected:

```text
RELATIVE_RANKING_SUFFICIENT
INCREMENTAL_ELIGIBILITY_ALREADY_PRESENT_AND_EFFECTIVE
IMPLICIT_DEPLOYMENT_PRESSURE
INSUFFICIENT_EVIDENCE
```

Partial:

```text
INCREMENTAL_ELIGIBILITY_PRESENT_BUT_WEAKLY_DISCRIMINATIVE
```

The current logic is partially valid: most BUYs had at least moderate PIT incremental evidence, and no active forced-deployment consumer was found. The remaining gap is performance-design, not architecture repair: the system does not expose an explicit "buy this versus hold cash" incremental eligibility concept distinct from relative candidate ranking and Quality allocation eligibility.

## 15. Evidence Limitations

Full candidate universe claims remain prohibited.

No-BUY superiority was not tested with future prices. No alternate-candidate counterfactual PnL was computed.

Incremental eligibility classes are post-hoc diagnostic labels. They are not proposed thresholds.

Some implicit-pressure findings rely on code/text search plus Phase26 closure reports; no active producer/artifact/consumer decision effect was found in the inspected evidence.

## 16. Validation

Validation results:

```text
py_compile: PASS
generator_execution: PASS
JSON output load validation: PASS
CSV output validation: PASS
actual BUY rows: 25 / 25
future outcome used for incremental classification: false
counterfactual trade PnL generated: false
.runtime read: false
fresh-run / historical rerun executed: false
```

## 17. Final Decision

```text
PHASE27_A6_INCREMENTAL_ELIGIBILITY_DIAGNOSIS_COMPLETE_CURRENT_LOGIC_PARTIALLY_VALID
```

This decision does not authorize Minimum Opportunity Score, Quality threshold changes, Rank cutoffs, Fallback BUY bans, No-BUY priority rules, cash ratio changes, sizing changes, or Re-entry restrictions.
