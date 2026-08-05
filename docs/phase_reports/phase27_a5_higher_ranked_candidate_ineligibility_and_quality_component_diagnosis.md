# Phase27-A5 — Higher-ranked Candidate Ineligibility and Quality Component Diagnosis

## 1. Scope

Task ID: Phase27-A5

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
PHASE27_A5_INELIGIBILITY_DIAGNOSIS_COMPLETE_MULTI_STAGE_INTERACTION_IDENTIFIED
```

Dominant improvement target:

```text
MULTI_STAGE_INTERACTION
```

Scope:

```text
Observed Quality / Portfolio Construction Funnel Only
```

Full candidate-universe superiority is not claimed because the complete full candidate universe is not available as run-scoped canonical evidence.

## 2. Safety Boundary

This task did not change Runtime, Strategy, Candidate, Opportunity, BUY Quality, Portfolio Policy, Portfolio Construction, Position Sizing, Planning, Submit, Safety, PM, Exit, or Re-entry logic.

No fresh-run, resume, historical rerun, 100BD rerun, or long regression was executed.

All outputs are post-hoc human-review evidence only and are not Strategy inputs.

## 3. Generated Artifacts

Generator:

```text
tools/phase27_analysis/phase27_a5_generate_ineligibility_diagnosis.py
```

Output directory:

```text
reports/phase27_a5_higher_ranked_candidate_ineligibility_and_quality_component_diagnosis/
```

Generated files:

```text
summary.json
higher_ranked_candidate_ineligibility.csv
higher_ranked_candidate_ineligibility.json
quality_component_attribution.csv
quality_component_attribution.json
quality_action_transition_analysis.csv
quality_action_transition_analysis.json
top_ranked_candidate_dropout.csv
top_ranked_candidate_dropout.json
zero_weight_diagnosis.csv
zero_weight_diagnosis.json
zero_quantity_diagnosis.csv
zero_quantity_diagnosis.json
daily_high_cash_causal_attribution.csv
daily_high_cash_causal_attribution.json
focus_case_audits.json
full_quality_underperformance_decomposition.json
hypothesis_judgments.json
root_cause_separation.json
evidence_limitations.json
test_results.json
```

## 4. Method

The analysis used Phase27-A4's frozen BUY Decision Validity trace as the entry point and expanded every higher-ranked candidate for all 25 actual BUYs.

Classification order:

1. Determine higher-ranked candidate ineligibility from PIT evidence.
2. Separate Quality, Portfolio Construction, Position Sizing, Existing Position, Pending, Submit, and Execution stages.
3. Freeze dropout and ineligibility classifications.
4. Attach post-hoc performance only after classifications are fixed.

Future PnL was not used to classify ineligibility.

## 5. Higher-ranked Candidate Ineligibility

A4 contained 25 actual BUYs. A5 expanded 63 higher-ranked candidate rows above those BUYs.

Higher-ranked ineligibility classes:

| Class | Count |
|---|---:|
| ZERO_WEIGHT_EXISTING_POSITION_NO_DELTA | 40 |
| QUALITY_REJECTED | 11 |
| ALREADY_BOUGHT | 5 |
| ZERO_QUANTITY_LOT_CONSTRAINT | 4 |
| QUALITY_REDUCED_BUT_NOT_SELECTED | 3 |

The dominant observed reason is not "stronger available candidate ignored." It is existing-position / duplicate / zero-delta state among higher-ranked candidates. This supports A4's finding that lower-ranked BUYs were often fallback selections after higher-ranked candidates became non-incremental or ineligible inside the observed funnel.

## 6. Quality Component Attribution

All 5,000 Quality decisions were decomposed.

Derived dominant limiting component counts:

| Dominant Limiting Component | Count |
|---|---:|
| RELATIVE_OPPORTUNITY | 3915 |
| MULTI_CAUSAL | 369 |
| PORTFOLIO_FIT | 366 |
| EXECUTION_FEASIBILITY | 248 |
| MARKET_CONTEXT | 95 |
| SIGNAL_RELIABILITY | 7 |

This is diagnostic attribution only. The derived limiter is not Runtime logic and is not a Strategy input.

Quality Reject was usually consistent with low relative-opportunity evidence and explicit reject/no-buy reason strings. Top-ranked opportunities were not excessively rejected as the primary explanation for lower-rank BUYs.

## 7. Top-3 Dropout

Rank 1 to Rank 3 candidates across 100 business days produced 300 tracked rows.

Top-3 final dropout stages:

| Stage | Count |
|---|---:|
| PORTFOLIO_CONSTRUCTION | 203 |
| QUALITY | 38 |
| SUBMIT | 25 |
| POSITION_SIZING | 23 |
| NOT_DROPPED | 11 |

Rank 1 dropout reasons:

| Rank 1 Reason | Count |
|---|---:|
| EXISTING_POSITION_ZERO_DELTA | 84 |
| OTHER_EXPLICIT | 8 |
| ZERO_QUANTITY | 5 |
| QUALITY_REJECT | 3 |

The most visible top-ranked dropout mechanism is existing-position zero-delta / duplicate-current-position handling, not Quality Reject alone.

## 8. Zero-weight Diagnosis

All zero-weight rows were diagnosed separately from zero-quantity rows.

Zero-weight classifications:

| Classification | Count |
|---|---:|
| VALID_QUALITY_EXCLUSION | 4559 |
| VALID_EXISTING_POSITION_ZERO_DELTA | 283 |

No architecture defect evidence was raised from zero-weight rows. Many zero-weight rows are direct propagation of Quality Reject. The non-reject zero-weight population is primarily existing-position / duplicate-current-position zero-delta evidence.

## 9. Zero-quantity Diagnosis

All zero-quantity rows were diagnosed separately from zero-weight rows.

Zero-quantity classifications:

| Classification | Count |
|---|---:|
| UPSTREAM_ZERO_WEIGHT_PROPAGATION | 4842 |
| VALID_BELOW_ONE_LOT | 60 |
| VALID_MINIMUM_NOTIONAL_FAILURE | 2 |

Position Sizing-specific removal exists, but most zero quantity is not a sizing defect. It is upstream zero-weight propagation from Quality or Portfolio Construction. One-lot and minimum-notional cases are separated from capital constraint; no material capital-constraint class was observed.

## 10. High Cash Causal Attribution

Daily high-cash attribution was generated for all 100 business days.

Primary cash attribution classes:

| Primary Class | Days |
|---|---:|
| MULTI_CAUSAL | 68 |
| EXISTING_POSITION_ZERO_DELTA | 32 |

High cash is partially aligned with higher-ranked dropout, but the evidence does not support a single-cause explanation. It combines defensive policy / market context, Quality filtering, Portfolio Construction filtering, and existing-position zero-delta conditions.

Correlation is not presented as causation.

## 11. FULL Quality Underperformance Decomposition

FULL underperformance remained negative after isolating 93180 and Re-entry effects.

Required FULL slices:

| Slice | BUY Count | PnL | PF | Win Rate |
|---|---:|---:|---:|---:|
| FULL initial-entry only | 12 | -53,440 | 0.5326 | 0.2727 |
| FULL re-entry only | 8 | -76,970 | 0.1800 | 0.2857 |
| FULL excluding 93180 | 16 | -50,910 | 0.5664 | 0.2857 |
| FULL excluding all re-entry | 12 | -53,440 | 0.5326 | 0.2727 |
| FULL excluding 93180 and all re-entry | 11 | -38,540 | 0.6124 | 0.3000 |

FULL performance by dominant limiting/supporting component:

| Component Class | BUY Count | PnL | PF |
|---|---:|---:|---:|
| EXECUTION_FEASIBILITY | 10 | -56,310 | 0.4475 |
| PORTFOLIO_FIT | 3 | -54,370 | 0.1721 |
| MULTI_CAUSAL | 4 | -30,300 | 0.1560 |
| MARKET_CONTEXT | 2 | -4,730 | 0.0000 |
| RELATIVE_OPPORTUNITY | 1 | 15,300 | n/a |

This points to component-combination association rather than a single Quality component failure. Samples are small, and all performance findings remain post-hoc.

## 12. Focus Case Findings

### 93180 campaign 0006

Selected candidate:

```text
93180 / Rank 6 / Re-entry
```

Higher-ranked candidates were classified as zero-weight existing-position/no-delta, zero-quantity lot constraint, and Quality Reject. Dropout evidence was consistent within the observed funnel. The selected candidate was materially weaker by Opportunity Score, but the stronger candidates were not observed as executable replacements. Post-hoc outcome: -80,000.

### 93180 campaign 0004

Selected candidate:

```text
93180 / Rank 1 / Re-entry
```

No higher-ranked observed-funnel candidate existed. This remains the cleanest valid Re-entry case. Post-hoc outcome: +38,900.

### 76920 campaign 0002

Selected candidate:

```text
76920 / Rank 6 / Re-entry
```

Higher-ranked candidates included one already-bought candidate, zero-weight existing-position/no-delta rows, one zero-quantity lot-constraint row, and one Quality Reject. The nearest stronger candidate gap was within A4's diagnostic near-tie threshold. Post-hoc outcome: +9,990.

### 76920 campaign 0003

Selected candidate:

```text
76920 / Rank 2 / Re-entry
```

Rank 1 was a zero-weight existing-position/no-delta row with a very small score gap. The fallback was evidence-consistent within the observed funnel. Post-hoc outcome: -4,770.

Additional focus cases are included in `focus_case_audits.json`, including Quality Reject, zero-weight, zero-quantity, existing-position zero-delta, and normal Rank 1 BUY examples.

## 13. Hypothesis Judgments

| Hypothesis | Judgment |
|---|---|
| H-A5-1 Higher-ranked candidates were primarily dropped for explicit and evidence-consistent eligibility reasons | PARTIALLY_CONFIRMED |
| H-A5-2 BUY Quality excessively rejected otherwise strong top-ranked opportunities | REJECTED |
| H-A5-3 Portfolio Construction zero-weight behavior excessively removed otherwise executable high-ranked candidates | PARTIALLY_CONFIRMED |
| H-A5-4 Position Sizing zero-quantity behavior excessively removed otherwise executable high-ranked candidates | PARTIALLY_CONFIRMED |
| H-A5-5 Existing-position zero-delta / NO_ACTION explains a material share of higher-ranked ineligibility | CONFIRMED |
| H-A5-6 High cash was materially caused by higher-ranked dropout and lack of executable replacements | PARTIALLY_CONFIRMED |
| H-A5-7 FULL underperformance is associated with identifiable Quality component combinations | PARTIALLY_CONFIRMED |
| H-A5-8 Lower-ranked BUYs were generally justified fallbacks after evidence-consistent dropout | PARTIALLY_CONFIRMED |
| H-A5-9 Dominant target | MULTI_STAGE_INTERACTION |

## 14. Root Cause Separation

Cause areas were kept separate:

| Cause Area | Evidence Strength | Confidence | Architecture Defect Evidence |
|---|---|---|---|
| BUY Quality | HIGH | MEDIUM | false |
| Portfolio Construction | HIGH | MEDIUM | false |
| Position Sizing | HIGH | MEDIUM | false |
| Existing Position State | HIGH | MEDIUM | false |
| Lot / Minimum Notional | HIGH | MEDIUM | false |
| Capital Availability | MEDIUM | MEDIUM | false |
| Market Context / Portfolio Policy | MEDIUM | MEDIUM | false |
| Execution / Authority / Safety | MEDIUM | MEDIUM | false |

No explicit architecture defect evidence was identified. The evidence supports a multi-stage interaction diagnosis centered on existing-position zero-delta, Portfolio Construction filtering, Position Sizing propagation/lot effects, and Quality filtering.

## 15. Evidence Limitations

Full candidate universe claims remain prohibited.

Some Portfolio Construction, Position Sizing, and Runtime Planning reasons are coarse reason strings. These were not expanded by inference.

Available cash, minimum notional, and lot metadata are partially present, so capital impact is only partially quantified.

Post-hoc performance is attached only after PIT dropout and ineligibility classifications are fixed.

## 16. Validation

Validation results:

```text
py_compile: PASS
generator_execution: PASS
JSON output load validation: PASS
CSV output validation: PASS
quality_component_rows: 5000 / 5000
A4 BUY trace count: 25 / 25
future outcome used for ineligibility: false
.runtime read: false
fresh-run / historical rerun executed: false
```

## 17. Final Decision

```text
PHASE27_A5_INELIGIBILITY_DIAGNOSIS_COMPLETE_MULTI_STAGE_INTERACTION_IDENTIFIED
```

This decision does not authorize Quality Reject relaxation, Quality weight changes, Portfolio Construction priority changes, zero-weight rule changes, sizing increases, minimum-notional changes, Rank cutoffs, cash ratio changes, or Re-entry restrictions.
