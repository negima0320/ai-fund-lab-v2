# Phase27-A4 — Opportunity, Quality, and Final Selection Discrimination Diagnosis

## 1. Scope

Task ID: Phase27-A4

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
PHASE27_A4_SELECTION_DISCRIMINATION_PARTIALLY_VALID_IMPROVEMENT_TARGETS_IDENTIFIED
```

Scope:

```text
Observed Quality / Portfolio Construction Funnel Only
```

Full candidate-universe superiority is not claimed. The full candidate universe is not available as complete run-scoped canonical evidence.

## 2. Safety Boundary

This task did not change Runtime, Strategy, Candidate, Opportunity, BUY Quality, Portfolio Policy, Portfolio Construction, Position Sizing, Planning, Submit, Safety, PM, Exit, or Re-entry logic.

No fresh-run, resume, historical rerun, 100BD rerun, or long regression was executed.

All outputs are post-hoc human-review evidence only and are not Strategy inputs.

## 3. Generated Artifacts

Output directory:

```text
reports/phase27_a4_opportunity_quality_and_final_selection_discrimination_diagnosis/
```

Generated files:

```text
summary.json
daily_opportunity_discrimination.csv
daily_opportunity_discrimination.json
opportunity_score_distribution.json
daily_score_gap_analysis.csv
daily_score_gap_analysis.json
near_tie_analysis.json
rank_quality_transition_matrix.csv
rank_quality_transition_matrix.json
quality_discrimination_analysis.json
portfolio_construction_decision_trace.csv
portfolio_construction_decision_trace.json
buy_decision_validity.csv
buy_decision_validity.json
focus_case_audits.json
performance_by_decision_validity.json
rank_quality_concentration_analysis.json
hypothesis_judgments.json
evidence_limitations.json
test_results.json
```

Generator:

```text
tools/phase27_analysis/phase27_a4_generate_discrimination_diagnosis.py
```

## 4. Method

The analysis first classified each BUY decision from point-in-time observed evidence only:

1. Opportunity / Quality / Portfolio Construction funnel rows were joined.
2. Each actual BUY was compared with higher-ranked candidates from the same business date.
3. Higher-ranked candidates were categorized as bought, quality-rejected, portfolio-excluded, zero-weight, zero-quantity, authority/safety-blocked, available but not selected, or unknown.
4. Decision Validity was frozen before attaching realized PnL.
5. Post-hoc performance was then compared by the frozen validity classes.

Future PnL was not used for Decision Validity classification.

## 5. Opportunity Score Discrimination

The observed funnel contained 5,000 rows: 50 ranked rows per business day over 100 business days.

Score distribution by rank bucket:

| Rank Bucket | Decisions | Mean Score | Median Score | Min | Max | BUY Count |
|---|---:|---:|---:|---:|---:|---:|
| 1 | 100 | 0.300814 | 0.272847 | 0.130736 | 0.805321 | 3 |
| 2 | 100 | 0.233203 | 0.225107 | 0.096997 | 0.453505 | 5 |
| 3 | 100 | 0.184500 | 0.188360 | 0.015400 | 0.377228 | 3 |
| 4-5 | 200 | 0.081282 | 0.069183 | -0.115936 | 0.293959 | 10 |
| 6-10 | 500 | -0.100100 | -0.100564 | -0.369811 | 0.270609 | 4 |
| 11+ | 4000 | -0.441656 | -0.458841 | -0.749739 | -0.002402 | 0 |

Opportunity Score has cross-sectional ordering: higher buckets generally have higher scores.

However, daily adjacent gaps are often compressed:

| Gap | N | Mean | Median | Min | Max |
|---|---:|---:|---:|---:|---:|
| Rank1 - Rank2 | 100 | 0.067611 | 0.065326 | 0.000281 | 0.447360 |
| Rank1 - Rank3 | 100 | 0.116314 | 0.115834 | 0.002719 | 0.507183 |
| Rank1 - Rank5 | 100 | 0.258293 | 0.240425 | 0.080417 | 0.764018 |
| Rank1 - selected BUY mean | 21 | 0.154638 | 0.121588 | 0.000000 | 0.803027 |

Judgment: Opportunity Score has partial discrimination. Rank preserves ordering, but rank distance can overstate the magnitude of Score separation.

## 6. Near-tie Analysis

Diagnostic near-tie thresholds were applied post-hoc only:

```text
Absolute Score Gap <= 0.005
Absolute Score Gap <= 0.010
Absolute Score Gap <= 0.020
Relative Score Gap <= 1%
Relative Score Gap <= 2%
Relative Score Gap <= 5%
```

Among lower-rank selected BUYs with at least one higher-ranked observed candidate:

```text
Near-tied under at least one diagnostic threshold: 9
Not near-tied: 13
```

These thresholds are diagnostic only. They are not proposed as Strategy logic.

## 7. Rank x Quality Action Matrix

Key executed cells:

| Rank Bucket | Quality Action | Decisions | BUY Count | PnL | PF | Re-entry Count |
|---|---|---:|---:|---:|---:|---:|
| 1 | REDUCED_ALLOCATION_ONLY | 97 | 3 | 152,900 | 26.4833 | 1 |
| 2 | FULL_ALLOCATION_ELIGIBLE | 36 | 5 | -89,270 | 0.0000 | 4 |
| 3 | FULL_ALLOCATION_ELIGIBLE | 27 | 3 | -16,610 | 0.5043 | 2 |
| 4-5 | FULL_ALLOCATION_ELIGIBLE | 61 | 10 | -12,730 | 0.8271 | 1 |
| 6-10 | FULL_ALLOCATION_ELIGIBLE | 38 | 2 | -11,800 | 0.0000 | 1 |
| 6-10 | REDUCED_ALLOCATION_ONLY | 29 | 2 | -70,010 | 0.1249 | 2 |

Small-sample warnings apply to most executed cells.

## 8. BUY Quality Discrimination

Quality Action results:

| Quality Action | Decisions | BUY Count | PnL | PF | Re-entry Count |
|---|---:|---:|---:|---:|---:|
| FULL_ALLOCATION_ELIGIBLE | 162 | 20 | -130,410 | 0.3737 | 8 |
| REDUCED_ALLOCATION_ONLY | 279 | 5 | 82,890 | 1.9638 | 3 |
| REJECT | 4559 | 0 | 0 | n/a | 0 |

Required separation checks:

| Slice | BUY Count | PnL | PF |
|---|---:|---:|---:|
| FULL all | 20 | -130,410 | 0.3737 |
| FULL 93180 only | 4 | -79,500 | 0.3288 |
| FULL excluding 93180 | 16 | -50,910 | 0.5664 |
| FULL re-entry only | 8 | -76,970 | 0.2539 |
| FULL excluding all re-entry | 12 | -53,440 | 0.5326 |
| REDUCED all | 5 | 82,890 | 1.9638 |
| REDUCED excluding re-entry | 2 | 114,000 | n/a |

FULL underperformance is partially concentrated in 93180 and Re-entry campaigns, but not fully explained by either exclusion. BUY Quality did operationally separate rejected candidates from buy-eligible candidates, but this sample does not prove that Quality improved post-hoc return discrimination.

## 9. Final BUY Decision Validity

All 25 actual BUYs were classified without using future performance.

| Decision Validity Class | BUY Count |
|---|---:|
| BEST_AVAILABLE_WITHIN_OBSERVED_FUNNEL | 3 |
| REASONABLE_ALTERNATIVE_WITHIN_NEAR_TIE | 9 |
| SELECTED_AFTER_HIGHER_CANDIDATES_INELIGIBLE | 13 |
| SELECTED_DESPITE_CLEARLY_STRONGER_AVAILABLE_CANDIDATE | 0 |
| INSUFFICIENT_EVIDENCE | 0 |

This rejects the claim that the system consistently selected the best available observed-funnel opportunity. It also rejects, within the observed funnel, the stronger claim that Portfolio Construction repeatedly selected clearly weaker available alternatives despite stronger eligible candidates.

Most lower-rank BUYs were explainable because higher-ranked observed candidates were already bought, zero-weight, zero-quantity, Quality rejected, or otherwise not executable in the observed Planning/Sizing path.

## 10. Post-hoc Performance by Frozen Validity Class

Performance was attached after classification.

| Decision Validity Class | BUY Count | PnL | PF | Win Rate | Re-entry Count |
|---|---:|---:|---:|---:|---:|
| BEST_AVAILABLE_WITHIN_OBSERVED_FUNNEL | 3 | 152,900 | 26.4833 | 0.6667 | 1 |
| REASONABLE_ALTERNATIVE_WITHIN_NEAR_TIE | 9 | -102,810 | 0.0886 | 0.1250 | 6 |
| SELECTED_AFTER_HIGHER_CANDIDATES_INELIGIBLE | 13 | -97,610 | 0.4435 | 0.4167 | 4 |

The best-available class performed strongly, but it contains only 3 BUYs. The near-tie class performed poorly and included 6 Re-entry campaigns. This is a post-hoc association, not a causal proof.

## 11. Focus Case Audits

### 93180 campaign 0004

Classification:

```text
BEST_AVAILABLE_WITHIN_OBSERVED_FUNNEL
```

This was a Re-entry on 2023-02-16. No higher-ranked observed-funnel candidate existed. The subsequent outcome was profitable: +38,900 over 11 holding days. Outcome was not used for classification.

### 93180 campaign 0006

Classification:

```text
SELECTED_AFTER_HIGHER_CANDIDATES_INELIGIBLE
```

This was a Re-entry on 2023-03-29 with Opportunity Rank 6 and Score 0.034897. Higher-ranked observed candidates existed, but the evidence classified them as zero-weight, zero-quantity, or Quality rejected. The nearest stronger score gap was 0.101523, which is material. The subsequent outcome was -80,000 over 2 holding days, used only post-hoc.

### 76920 campaign 0002

Classification:

```text
REASONABLE_ALTERNATIVE_WITHIN_NEAR_TIE
```

This was a Re-entry on 2023-03-02 with Opportunity Rank 6 and Score 0.038735. Higher-ranked candidates included one already bought candidate, zero-weight/zero-quantity rows, and a Quality-rejected row. The nearest stronger score gap was 0.018282, within the diagnostic 0.020 absolute near-tie threshold. The subsequent outcome was +9,990 over 1 holding day.

### 76920 campaign 0003

Classification:

```text
REASONABLE_ALTERNATIVE_WITHIN_NEAR_TIE
```

This was a Re-entry on 2023-03-06 with Opportunity Rank 2 and Score 0.190386. The Rank 1 candidate had zero weight, and the score gap was only 0.002149. The subsequent outcome was -4,770 over 2 holding days.

Additional required examples:

| Case | Campaign | Classification | Post-hoc PnL |
|---|---|---|---:|
| Successful Rank 1 BUY | pc-66d9ba285c89ec9b-30410-0001 | BEST_AVAILABLE_WITHIN_OBSERVED_FUNNEL | 120,000 |
| Unsuccessful Rank 2 BUY | pc-66d9ba285c89ec9b-93180-0003 | REASONABLE_ALTERNATIVE_WITHIN_NEAR_TIE | -60,900 |
| Successful REDUCED BUY | pc-66d9ba285c89ec9b-30410-0001 | BEST_AVAILABLE_WITHIN_OBSERVED_FUNNEL | 120,000 |
| Unsuccessful FULL BUY | pc-66d9ba285c89ec9b-93180-0006 | SELECTED_AFTER_HIGHER_CANDIDATES_INELIGIBLE | -80,000 |

## 12. Concentration Analysis

Required exclusion checks:

| Slice | BUY Count | PnL | PF |
|---|---:|---:|---:|
| Rank 2 losses excluding largest contributor | 3 | -13,370 | 0.0000 |
| Rank 6-10 excluding 93180 | 3 | -1,810 | 0.8466 |
| FULL excluding 93180 | 16 | -50,910 | 0.5664 |
| FULL excluding all Re-entry | 12 | -53,440 | 0.5326 |
| All BUY excluding 93180 | 19 | 73,080 | 1.5922 |
| All BUY excluding 93180 and 76920 | 16 | 101,370 | 2.1908 |

93180 is a material concentration driver. Removing 93180 flips all-BUY performance positive. Removing both 93180 and 76920 improves the post-hoc aggregate further. This is concentration analysis only and is not a symbol-ban recommendation.

## 13. Hypothesis Judgments

| Hypothesis | Judgment |
|---|---|
| H-A4-1 Opportunity Score has meaningful cross-sectional discrimination | PARTIALLY_CONFIRMED |
| H-A4-2 Opportunity Rank accurately represents meaningful Score separation | PARTIALLY_CONFIRMED |
| H-A4-3 Lower-rank BUYs were usually selected only when higher-ranked candidates were ineligible or near-tied | PARTIALLY_CONFIRMED |
| H-A4-4 Portfolio Construction selected clearly weaker candidates despite stronger eligible alternatives | REJECTED |
| H-A4-5 BUY Quality improved Opportunity discrimination | INSUFFICIENT_EVIDENCE |
| H-A4-6 FULL underperformance is primarily explained by symbol/Re-entry concentration rather than Quality itself | PARTIALLY_CONFIRMED |
| H-A4-7 Re-entry underperformance is partly explained by weak final selection validity | PARTIALLY_CONFIRMED |
| H-A4-8 System consistently selected the best available opportunity within observed Quality/PC funnel | REJECTED |

## 14. Root Diagnosis

The evidence supports a partial-validity diagnosis:

```text
Selection was not consistently best-available within the observed funnel.
But observed evidence did not show repeated selection of clearly weaker
available candidates despite stronger eligible alternatives.
```

Opportunity Score has meaningful ordering, but rank gaps and score gaps are not interchangeable. Lower-rank BUYs were often explainable by ineligibility or near-tie conditions. BUY Quality did not provide enough post-hoc evidence to prove improved return discrimination in this sample, especially because FULL underperformance remained negative even after excluding 93180 or all Re-entry campaigns.

The strongest observed concentration driver is 93180. Re-entry and near-tie classes also align with weak post-hoc outcomes, but this remains diagnostic correlation.

## 15. Evidence Limitations

Full candidate-universe claims are prohibited because the complete full candidate universe is not preserved as canonical run-scoped evidence.

Some higher-ranked non-buy reasons are represented by structured reason strings from Portfolio Construction, Position Sizing, and Runtime Planning artifacts. Where the evidence did not prove a specific mechanism, the output keeps the reason explicit instead of inferring.

Most executed cells are small samples. Historical PnL and performance reports are post-hoc human-review evidence only.

## 16. Validation

Validation results:

```text
py_compile: PASS
generator_execution: PASS
JSON output load validation: PASS
CSV output validation: PASS
actual BUY classifications: 25 / 25
daily discrimination rows: 5000
future outcome used for validity classification: false
.runtime read: false
fresh-run / historical rerun executed: false
```

## 17. Final Decision

```text
PHASE27_A4_SELECTION_DISCRIMINATION_PARTIALLY_VALID_IMPROVEMENT_TARGETS_IDENTIFIED
```

This decision does not authorize Rank cutoffs, Opportunity threshold changes, Quality weight changes, Quality threshold changes, Portfolio Construction priority changes, Re-entry restrictions, cash ratio changes, or sizing changes.
