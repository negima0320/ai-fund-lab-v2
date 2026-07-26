# Phase20-F Performance Improvement Candidate Identification

## Executive Summary

Phase20-F identifies future performance improvement candidates from the Phase20-E diagnosis.

Target run:

```text
runtime-test-historical-smoke-20260721T213848054826Z
```

Runtime judgment:

```text
PASS
```

Performance:

```text
Return = -4.49%
```

Final judgment:

```text
PHASE20_F_IMPROVEMENT_CANDIDATES_IDENTIFIED_WITH_EVIDENCE_GAPS
```

This phase did not implement improvements, did not run experiments, and did not change AI, Opportunity, PM, Risk, Runtime, Capital Allocation, Benchmark, Training, Calibration, Validation, or Accepted Generation.

## Required Documents Read

Read and applied:

- `docs/phase_reports/phase20_e_performance_diagnosis_and_attribution_report.md`
- `docs/phase_reports/phase20_d_trade_and_position_management_attribution_baseline.md`
- `docs/phase_reports/phase20_c_read_only_performance_baseline_extraction.md`
- `docs/02_architecture/performance_metric_benchmark_experiment_contract.md`

Contract version:

```text
phase20_b_performance_metric_contract.v1
```

## Generated Artifacts

Generated candidate artifacts:

```text
reports/phase_reports/phase20_f_performance_improvement_candidate_identification.json
reports/performance_improvement_candidates/runtime-test-historical-smoke-20260721T213848054826Z/improvement_candidates.json
reports/performance_improvement_candidates/runtime-test-historical-smoke-20260721T213848054826Z/improvement_candidates.csv
```

## Candidate Inventory Summary

| Priority | Count |
|---|---:|
| HIGH | 3 |
| MEDIUM | 6 |
| LOW | 5 |

Evidence strength distribution:

| Evidence Strength | Count |
|---|---:|
| HIGH | 3 |
| MEDIUM | 6 |
| LOW | 3 |
| INSUFFICIENT | 2 |

Runtime impact in Phase20-F:

```text
NONE
```

All candidates are identification-only. Any future implementation or experiment requires a separate approved phase and comparability contract.

## High Priority Candidates

| ID | Area | Candidate | Evidence Strength | Confidence | Runtime Impact | Priority |
|---|---|---|---|---|---|---|
| P20F-BENCH-012 | Benchmark | Add approved benchmark evidence as a future analysis dependency, not a Phase20-F benchmark introduction. | HIGH | HIGH | NONE | HIGH |
| P20F-OBS-LOT-001 | Evidence / Observability | Add stable lot/fill-level realized PnL observability as a future candidate dependency, not a strategy change. | HIGH | HIGH | NONE | HIGH |
| P20F-OBS-PM-002 | Evidence / Observability | Persist per-symbol PM decision body snapshots into run-scoped evidence for future diagnosis/experiments. | HIGH | HIGH | NONE | HIGH |

High priority is assigned to evidence foundations, not to direct strategy changes. These candidates have strong evidence that missing observability blocks reliable attribution.

## Medium Priority Candidates

| ID | Area | Candidate | Evidence Strength | Confidence | Runtime Impact | Priority |
|---|---|---|---|---|---|---|
| P20F-BUY-POL-014 | BUY Policy | Evaluate BUY execution/selection policy constraints as a future candidate. | MEDIUM | LOW | NONE | MEDIUM |
| P20F-BUY-RANK-003 | BUY Policy | Evaluate executed BUY rank coverage as a future experiment candidate. | MEDIUM | MEDIUM | NONE | MEDIUM |
| P20F-MKT-REGIME-013 | Market Regime | Add market regime attribution as a future diagnosis dependency. | INSUFFICIENT | UNKNOWN | NONE | MEDIUM |
| P20F-OPP-RANK-004 | Opportunity Ranking | Evaluate opportunity ranking score calibration/ordering as a future experiment candidate. | MEDIUM | LOW | NONE | MEDIUM |
| P20F-PM-010 | Position Management | Evaluate PM decision quality as a future candidate after decision-body observability is restored. | MEDIUM | LOW | NONE | MEDIUM |
| P20F-RISK-CAP-011 | Risk / Capital Allocation | Evaluate capital allocation/exposure sizing as a future candidate using exposure and drawdown evidence. | MEDIUM | LOW | NONE | MEDIUM |

Medium priority candidates have visible diagnostic signals, but evidence is not strong enough for direct implementation. They require comparable experiments or missing evidence closure.

## Low Priority Candidates

| ID | Area | Candidate | Evidence Strength | Confidence | Runtime Impact | Priority |
|---|---|---|---|---|---|---|
| P20F-ADD-007 | ADD Policy | Evaluate ADD policy as a future candidate only after observability is improved. | INSUFFICIENT | UNKNOWN | NONE | LOW |
| P20F-AI-SEL-005 | AI Selection | Evaluate AI selection output lineage and selected symbols as future experiment candidates only after attribution gaps close. | LOW | LOW | NONE | LOW |
| P20F-EXIT-009 | EXIT Policy | Evaluate EXIT policy as future experiment candidate after closed-position attribution improves. | LOW | LOW | NONE | LOW |
| P20F-HOLD-006 | HOLD Policy | Evaluate HOLD continuation outcomes as a future PM policy experiment candidate. | MEDIUM | LOW | NONE | LOW |
| P20F-REDUCE-008 | REDUCE Policy | Evaluate REDUCE policy as future experiment candidate after per-symbol execution attribution improves. | LOW | LOW | NONE | LOW |

Low priority does not mean irrelevant. It means current evidence is insufficient, too partial, or not causally isolated enough to prioritize before higher-confidence observability gaps.

## Candidate Evaluation Matrix

| Area | Candidate ID | Evidence | Expected Impact | Risk | Observability Gap | Additional Evidence Required |
|---|---|---|---|---|---|---|
| Benchmark | P20F-BENCH-012 | TOPIX benchmark return is `MISSING`; benchmark-relative underperformance cannot be measured. | High diagnostic impact for future interpretation; no direct Phase20-F strategy impact. | Low if read-only and contract-approved. | Benchmark-relative return and excess return missing. | Approved TOPIX source, benchmark snapshot contract, run-scoped benchmark evidence. |
| Evidence / Observability | P20F-OBS-LOT-001 | Closed realized PnL is -51,300 aggregate; per-symbol realized PnL is partial on multi-symbol SELL days. | High diagnostic impact for exact realized attribution. | Low if observability-only. | Stable lot IDs and fill-level realized PnL missing. | Lot ID contract, fill-level execution detail, per-symbol realized PnL by lot/slice. |
| Evidence / Observability | P20F-OBS-PM-002 | PM counts exist, but per-symbol PM body is missing for most 20BD dates; ADD outcomes are `MISSING`. | High diagnostic impact for PM attribution. | Low if observability-only. | PM decision body and reasons missing. | Run-scoped PM decision body, reason fields, per-symbol PM outcome schema. |
| BUY Policy | P20F-BUY-POL-014 | BUY count is 5 on 2026-06-17; rank 1 did not execute while ranks 2,3,5,6,7 did. | Unknown; requires future comparable experiment. | Medium because BUY policy changes affect exposure and comparability. | Rank 1 non-execution reason and benchmark context missing. | Eligibility detail, rank exclusion reason, comparable BUY-policy experiment. |
| BUY Policy | P20F-BUY-RANK-003 | Ranks 2/3 were non-negative/positive; ranks 5/6/7 negative by last-observed return. | Potential strategy impact if repeated in comparable runs. | Medium due to small sample and confounding. | Single 20BD sample; exact realized PnL partial. | Multiple comparable runs, benchmark/sector context, exact realized PnL. |
| Market Regime | P20F-MKT-REGIME-013 | Negative absolute return but benchmark/sector evidence missing. | Unknown until regime data exists. | Low for observability; high if used without contract. | Benchmark, sector returns, regime labels missing. | Benchmark returns, sector returns, market regime contract. |
| Opportunity Ranking | P20F-OPP-RANK-004 | Lower-ranked executed symbols were negative in this sample; rank 2/3 non-negative/positive. | Potential only after larger comparable evidence. | Medium/high inference risk. | No validation-safe rank outcome dataset. | Out-of-sample comparable runs, sector-adjusted returns, post-hoc ranking contract. |
| Position Management | P20F-PM-010 | HOLD/ADD/REDUCE/EXIT counts available; PM decision reasons missing. | Cannot quantify yet. | Medium if PM policy is changed before attribution is complete. | PM body, reasons, ADD attribution missing. | PM snapshots, reason fields, PM outcome tables. |
| Risk / Capital Allocation | P20F-RISK-CAP-011 | Average cash utilization 0.32177; drawdown period average exposure 0.45496. | Unknown-to-moderate; sizing not isolated from selection/PM/regime. | Medium/high for future strategy experiments. | No benchmark/regime context or sizing counterfactual. | Comparable sizing experiments, benchmark/regime data, sector concentration. |
| ADD Policy | P20F-ADD-007 | ADD count 9, but exact symbol rows 0 and ADD return/MFE/MAE are `MISSING`. | Cannot estimate from current evidence. | High if prioritized before evidence exists. | Per-symbol ADD assignment missing. | PM body, ADD quantities/notional, post-ADD outcome contract. |
| AI Selection | P20F-AI-SEL-005 | 3 of 5 bought symbols closed with negative last-observed return; exact per-symbol realized PnL partial. | Unknown; not isolated from other factors. | High if acted on prematurely. | Causal isolation insufficient. | Comparable experiment design, lot-level PnL, benchmark/sector context. |
| EXIT Policy | P20F-EXIT-009 | EXIT count 3; per-symbol execution price and realized PnL missing on multi-symbol days. | Unknown. | Medium/high if acted on with missing attribution. | EXIT price, realized PnL, post-sale outcome missing. | Fill-level EXIT detail, post-sale price evidence, lot-level PnL. |
| HOLD Policy | P20F-HOLD-006 | HOLD count 30; available exact HOLD rows average +2.1345% post-hoc return. | Unknown-to-moderate; exact rows do not show negative average but coverage is partial. | Medium due to partial PM body evidence. | Mixed HOLD/ADD rows partial; reasons missing. | PM decision body, exact HOLD/ADD assignment, longer comparable runs. |
| REDUCE Policy | P20F-REDUCE-008 | REDUCE count 4; only one exact execution/realized row; most rows partial. | Unknown. | Medium if grouped PnL is misread. | Multi-symbol SELL split and loss avoided/profit missed missing. | Lot/fill-level SELL attribution, post-sale evidence, counterfactual contract. |

## Priority Rationale

Priority considers both expected impact and evidence certainty.

High priority candidates are evidence infrastructure or benchmark dependencies because Phase20-E shows they block reliable attribution:

- exact realized PnL by symbol/lot
- exact PM decision/body attribution
- benchmark-relative diagnosis

Medium priority candidates are plausible future experiment areas but remain limited by sample size, benchmark/sector gaps, PM body gaps, or missing counterfactuals.

Low priority candidates are not ready for direct experiment ranking because evidence is insufficient or too partial.

## Runtime Impact

Phase20-F runtime impact:

```text
NONE
```

Candidate identification does not alter:

- AI
- Opportunity
- BUY Policy
- HOLD Policy
- ADD Policy
- REDUCE Policy
- EXIT Policy
- Position Management
- Risk
- Capital Allocation
- Runtime
- Broker
- Accepted Generation
- Training
- Calibration
- Validation

## Evidence Gap Summary

Evidence gaps repeated across candidates:

- Stable lot/fill-level realized PnL is missing.
- Per-symbol PM decision bodies and PM reasons are missing for most 20BD dates.
- Benchmark return evidence is missing.
- Sector mapping and sector return evidence are missing.
- Market regime labels are missing.
- Multi-symbol SELL per-symbol execution price and realized PnL splits are missing.
- Fee, tax, and slippage evidence is not available.
- Rank 1 non-execution reason requires deeper BUY eligibility/exclusion evidence before policy interpretation.

## Prohibited Actions Check

Not performed:

- AI change
- Opportunity change
- PM change
- Risk change
- Threshold change
- Runtime change
- Benchmark introduction
- Experiment execution
- Training
- Calibration
- Validation
- Accepted Generation change
- Broker connection
- Runtime State mutation
- Long Historical
- Full Backtest

## Validation

Validation performed:

```text
json validation
git diff --check
```

No Historical Smoke, Broker connection, Training, Calibration, Validation, full backtest, Runtime mutation, benchmark fetch, or code change was performed.

## Final Judgment

```text
PHASE20_F_IMPROVEMENT_CANDIDATES_IDENTIFIED_WITH_EVIDENCE_GAPS
```
