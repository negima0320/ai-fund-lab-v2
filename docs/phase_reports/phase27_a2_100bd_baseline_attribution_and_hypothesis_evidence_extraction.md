# Phase27-A2 100BD Baseline Attribution and Hypothesis Evidence Extraction

## Judgment

```text
PHASE27_A2_BASELINE_ATTRIBUTION_COMPLETE_PARTIAL_ROOT_CAUSES_IDENTIFIED
```

Task classification:

```text
Phase: Phase27
Task ID: Phase27-A2
Task Type: Observability Only / Read-only Performance Diagnosis
Parent Task: Phase27-A 100BD Baseline Attribution and Performance Diagnosis
Predecessor: Phase27-A1
Implementation Changed: false
Strategy Changed: false
Historical Test Executed: false
```

This task generated post-hoc attribution datasets from run-scoped evidence only.
It did not change Strategy, Candidate, Opportunity, BUY Quality, Portfolio
Policy, Position Sizing, Planning, Submit, Safety, PM, Exit, or Re-entry logic.
It did not run fresh-run, resume, 1BD, 3BD, 10BD, 100BD, 1 year Historical, or
long smoke.

## Inputs

Official baseline:

```text
run_id: runtime-test-historical-smoke-20260804T074611098414Z
period: 2023-01-04 through 2023-05-31
business_days: 100
```

Predecessor:

```text
docs/phase_reports/phase27_a1_100bd_evidence_inventory_and_attribution_readiness_audit.md
PHASE27_A1_EVIDENCE_INVENTORY_COMPLETE_ATTRIBUTION_READY_WITH_LIMITATIONS
```

Generator:

```text
tools/phase27_analysis/phase27_a2_generate_attribution.py
```

Safety boundary in generator:

```text
Observability Only
Post-hoc Human Review Only
Not a Strategy Input
Run-scoped Evidence Only
No .runtime Read
```

## Outputs

Output directory:

```text
reports/phase27_a2_100bd_baseline_attribution_and_hypothesis_evidence_extraction/
```

Generated required files:

```text
summary.json
baseline_metric_reconciliation.json
daily_capital_deployment_attribution.csv
daily_capital_deployment_attribution.json
opportunity_quality_selection_funnel.csv
opportunity_quality_selection_funnel.json
bought_vs_not_bought_comparison.json
rank_performance_attribution.csv
rank_performance_attribution.json
quality_performance_attribution.csv
quality_performance_attribution.json
position_sizing_efficiency.csv
position_sizing_efficiency.json
reentry_event_attribution.csv
reentry_event_attribution.json
exit_holding_attribution.csv
exit_holding_attribution.json
profit_factor_decomposition.json
drawdown_episode_attribution.json
hypothesis_judgments.json
root_cause_ranking.json
evidence_limitations.json
test_results.json
```

Output shape:

```text
daily_capital_deployment_attribution.csv: 100 data rows
opportunity_quality_selection_funnel.csv: 5000 data rows
position_sizing_efficiency.csv: 25 data rows
reentry_event_attribution.csv: 25 data rows
exit_holding_attribution.csv: 45 data rows
```

## Baseline Metric Reconciliation

Metrics match the canonical baseline within source precision.

| Metric | Observed |
|---|---:|
| Initial Equity | 1,000,000 |
| Final Equity | 984,580 |
| Equity Delta | -15,420 |
| Realized PnL | -47,520 |
| Unrealized PnL | 32,100 |
| Profit Factor | 0.8384827164270419 |
| Maximum Drawdown | -205,890 |
| Win Rate | 34.78260869565217% |
| BUY Executions | 25 |
| SELL Executions | 45 |
| Final Cash Ratio | 65.96518312376851% |
| Average Cash Ratio | 50.10779329090455% |
| Average Position Count | 3.66 |

## Attribution Findings

### Capital Deployment

Observed facts:

- All 100 business dates have a generated daily capital deployment row.
- Average cash ratio was about `50.11%`.
- Final cash ratio was about `65.97%`.
- Daily rows join Market Context, Portfolio Policy target exposure, Position
  Sizing target exposure, current cash/market value, Quality action counts,
  planned BUY notional, executed BUY notional, SELL proceeds, and sizing
  constraints.

Evidence-supported inference:

- High cash is multi-causal. The evidence supports a combination of Portfolio
  Policy / Market Context exposure posture, Quality filtering, no-action rows
  for already held names, minimum-notional constraints, and SELL proceeds not
  always redeployed.
- This is not evidence for immediately lowering cash ratio or increasing sizing.

### Opportunity / Quality / Selection Funnel

Observed facts:

- Quality decisions: `5000`.
- Quality action distribution:
  - `FULL_ALLOCATION_ELIGIBLE`: `162`
  - `REDUCED_ALLOCATION_ONLY`: `279`
  - `REJECT`: `4559`
  - `REVIEW_REQUIRED`: `0`
- Actual BUY fills: `25`.
- All BUY fill joins retain composite join confidence because the original BUY
  fills lack direct `pending_item_id`, `order_plan_item_id`, and
  `quality_decision_id`.

Evidence-supported inference:

- The funnel is suitable for Phase27-A diagnosis after Quality/PC arrival.
- It is not suitable for full candidate-universe claims because the full
  candidate universe is not copied as canonical run-scoped daily evidence.

### Rank Attribution

Bought-trade attribution by Opportunity Rank bucket:

| Rank Bucket | Decisions | Buys | Win Rate | PF | PnL | Small Sample |
|---|---:|---:|---:|---:|---:|---|
| Rank 1 | 100 | 3 | 66.67% | 26.4833 | 152,900 | true |
| Rank 2 | 100 | 5 | 0.00% | 0.0 | -89,270 | false |
| Rank 3 | 100 | 3 | 66.67% | 0.5043 | -16,610 | true |
| Rank 4-5 | 200 | 10 | 30.00% | 0.8271 | -12,730 | false |
| Rank 6-10 | 500 | 4 | 25.00% | 0.1088 | -81,810 | true |
| Rank 11+ | 4000 | 0 | N/A | N/A | 0 | true |

Evidence-supported inference:

- Rank 1 was strong in this baseline, but Rank 2 and Rank 6-10 were materially
  weak.
- Opportunity Ranking is not uniformly broken, but discrimination after Rank 1
  appears uneven.

### Quality Attribution

Bought-trade attribution by Quality Action:

| Quality Action | Decisions | Buys | Win Rate | PF | PnL |
|---|---:|---:|---:|---:|---:|
| FULL_ALLOCATION_ELIGIBLE | 162 | 20 | 25.00% | 0.3737 | -130,410 |
| REDUCED_ALLOCATION_ONLY | 279 | 5 | 60.00% | 1.9638 | 82,890 |
| REVIEW_REQUIRED / BUY_REVIEW_REQUIRED | 0 | 0 | N/A | N/A | 0 |
| REJECT | 4559 | 0 | N/A | N/A | 0 |

Evidence-supported inference:

- The evidence does not support "BUY Quality is too conservative" as stated.
- It more strongly suggests that FULL vs REDUCED quality discrimination did not
  align with realized outcome in this 100BD baseline.

### Position Sizing

Observed facts:

- `position_sizing_efficiency.csv` contains 25 actual BUY rows.
- Target-to-fill gaps are mostly explainable through Quality adjustment, lot
  rounding, reference/fill price differences, or minimum-notional mechanics.

Evidence-supported inference:

- Sizing contributed to lower deployment, but the evidence does not isolate it
  as the sole cause. Sizing consumed upstream Portfolio Policy and Quality
  decisions.

### Re-entry

Required focus symbols:

| Symbol | Entry Count | Re-entry Count | PnL |
|---:|---:|---:|---:|
| 93180 | 6 | 5 | -120,600 |
| 76920 | 3 | 2 | -28,290 |

PF decomposition:

```text
reentry_gross_profit: 65,790
reentry_gross_loss: -173,870
initial_entry_gross_profit: 180,900
initial_entry_gross_loss: -120,340
```

Evidence-supported inference:

- Re-entry losses are directly quantified and material. This is the strongest
  root-cause candidate in this A2 evidence set.
- This is not an implementation proposal for cooldown or symbol-specific rules.

### Exit / Reduce / Holding

Observed facts:

- `exit_holding_attribution.csv` contains 45 SELL rows.
- SELL rows join fills and realized slices; `source_decision_type` provides a
  coarse REDUCE/EXIT-like signal.

Limitations:

- Exact PM intent, sell action taxonomy, MFE, and MAE are not sufficiently
  available for strong exit-timing conclusions.
- Exit / Reduce is therefore partially evidenced, not fully diagnosed.

### Profit Factor

PF decomposition:

```text
gross_profit: 246,690
gross_loss: -294,210
profit_factor: 0.8384827164270419
win_rate: 34.78260869565217%
average_winner: 30,836.25
average_loser: -19,614
payoff_ratio: 1.5721550933007036
largest_winner: 30410 / +120,000
largest_loser: 93180 / -80,000
```

Direct factor classification:

```text
LOW_WIN_RATE
REENTRY_LOSS
CONCENTRATED_LARGE_LOSS
QUALITY_SELECTION
RANK_SELECTION
```

## Hypothesis Judgments

| Hypothesis | Judgment | Confidence | Root Cause Status |
|---|---|---|---|
| H1 Opportunity Rankingの識別力が弱い | PARTIALLY_CONFIRMED | MEDIUM | Evidence-supported partial factor |
| H2 BUY Qualityが保守的すぎる | REJECTED | MEDIUM | Not supported as stated |
| H3 Position Sizingが資金投入を抑えすぎる | PARTIALLY_CONFIRMED | MEDIUM | Partial factor |
| H4 Market Contextが期間中防御的だった | PARTIALLY_CONFIRMED | MEDIUM | Partial factor |
| H5 Re-entryが損失を増加させている | CONFIRMED | HIGH | Directly evidenced factor |
| H6 Exit / Reduceが利益を伸ばせていない | PARTIALLY_CONFIRMED | LOW | Targeted evidence required |
| H7 良い候補を買わず、低ランク候補を買っている | PARTIALLY_CONFIRMED | MEDIUM | H7a partial; H7b insufficient |
| H8 QualityとRankは良いがCapital Deploymentだけが弱い | REJECTED | MEDIUM | Not supported as exclusive cause |

H7 split:

```text
H7a Quality / Portfolio Construction到達後: PARTIALLY_CONFIRMED
H7b Candidate full universe全体: INSUFFICIENT_EVIDENCE
```

H7b is insufficient because the full candidate universe is not fully preserved
as canonical run-scoped daily evidence.

## Root Cause Ranking

| Rank | Root Cause Candidate | Classification | Evidence Strength | Confidence | Architecture Change Required |
|---:|---|---|---|---|---|
| 1 | Repeated re-entry losses, especially 93180 and 76920 | Performance Improvement | HIGH | HIGH | false |
| 2 | Low win rate with concentrated losses | Performance Improvement | HIGH | HIGH | false |
| 3 | Mixed Quality / Rank discrimination | Performance Improvement | MEDIUM | MEDIUM | false |
| 4 | High cash / partial deployment from policy, quality, and sell proceeds | Performance Improvement | MEDIUM | MEDIUM | false |

No Architecture Repair is justified by this A2 evidence set.

## Evidence Limitations

- BUY fill rows lack direct `pending_item_id`, `order_plan_item_id`, and
  `quality_decision_id`; composite join confidence is retained.
- Full candidate universe is not copied as canonical run-scoped daily evidence;
  no full-universe candidate-rank claim is made.
- Unbought candidates are not assigned virtual PnL; no look-ahead "would have
  won" analysis was generated.
- MFE/MAE and exact PM sell reasons are insufficient for high-confidence
  Exit/Reduce timing diagnosis.
- A2 facts are post-hoc diagnostics and must not become Strategy input.

## Validation

```text
py_compile: PASS
generator execution: PASS
JSON output validation: PASS
daily_capital_deployment_attribution rows: 100
opportunity_quality_selection_funnel rows: 5000
fresh-run / Historical rerun: NOT EXECUTED
```

## Final Decision

Phase27-A2 is complete. Partial root causes are identified, with re-entry loss
as the strongest directly quantified candidate. No immediate implementation
proposal is authorized by this task. Phase27-A evidence should be reviewed
before any Phase27-A3 or Phase27-B design work.
