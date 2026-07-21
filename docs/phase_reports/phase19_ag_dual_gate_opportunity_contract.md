# Phase19-AG — Dual-Gate Opportunity Evaluation Contract

## Final Judgment

```text
PHASE19_AG_DUAL_GATE_CONTRACT_COMPLETE
PHASE19_AH_IMPLEMENTATION_READY
```

Supporting:

```text
OPPORTUNITY_GLOBAL_AND_SELECTION_REQUIRED
GLOBAL_ONLY_PASS_PROHIBITED
SELECTION_ONLY_PASS_PROHIBITED
NO_GENERATION_ELIGIBILITY_WITHOUT_DUAL_PASS
NO_RUNTIME_MUTATION_PASS
NO_BROKER_WRITE_PASS
```

Forbidden declarations were not made:

```text
FORMAL_VALIDATION_PASS
UNIFIED_GENERATION_CREATED
ACCEPTED_GENERATION_CREATED
RUNTIME_READY
BUY_READY
PRODUCTION_READY
```

## Human Decision

Reviewer:

```text
user:negishi
```

Decision:

```text
APPROVE_DUAL_GATE_OPPORTUNITY_EVALUATION
```

Approved rule:

```text
Opportunity Generation Eligible
=
Global Quality Gate PASS
AND
Selection Utility Gate PASS
```

Either gate alone is insufficient.

## Global Gate

Gate ID:

```text
OPPORTUNITY_GLOBAL_QUALITY_GATE_V1
```

Purpose:

```text
AIとして壊れていないこと
```

Evaluation scope:

```text
Formal test window全体
```

Required checks:

```text
Finite
NaNなし
Infなし
Collapseなし
Explosionなし
Calibration正常
Ordering保持
Baseline比較
Correlation
Prediction distribution
```

Required outputs:

```text
PASS
FAIL
REVIEW_REQUIRED
METRIC_UNAVAILABLE
```

PASS rule:

```text
All required Global metrics are available,
artifact-bound,
finite,
and satisfy approved threshold/status policy.
```

If a required metric has no approved threshold or status rule:

```text
REVIEW_REQUIRED
Generation Eligible = false
```

AG does not invent numeric correlation, error, or baseline thresholds.

## Selection Utility Gate

Gate ID:

```text
OPPORTUNITY_SELECTION_UTILITY_GATE_V1
```

Purpose:

```text
Opportunity本来の順位付け・選定Utilityを確認する
```

Evaluation scope:

```text
Candidate通過Universe
```

Default population:

```text
CandidateTop50 / candidate_source_ref rows
```

Required TopN:

```text
Top5
Top10
Top20
```

Required historical-compatible metrics:

```text
Top5 realized return
Top10 realized return
Top20 realized return
Top-minus-bottom
Hit Rate
Downside Rate
Rank Lift
NDCG
Spearman / ranking correlation
```

Required baselines:

```text
CandidateTop50 average
candidate_rank_baseline
candidate_score_baseline
simple_rule_baseline when historical-compatible and available
champion / challenger baseline only when artifact-bound and approved
```

PASS rule:

```text
Top5, Top10, and Top20 utility metrics are computed
on the Candidate-passed universe,
required metric families are available,
leakage controls pass,
and approved threshold/status policy passes.
```

If a metric cannot be computed or lacks approved status semantics:

```text
REVIEW_REQUIRED
Generation Eligible = false
```

## Dual Gate Rule

Generation eligibility:

```text
Global Quality Gate == PASS
AND
Selection Utility Gate == PASS
```

Non-offset rules:

```text
Candidate PASS cannot offset Opportunity Global FAIL.
Candidate PASS cannot offset Opportunity Selection FAIL.
Opportunity Global PASS cannot offset Opportunity Selection FAIL.
Opportunity Selection PASS cannot offset Opportunity Global FAIL.
Runtime / Paper / Backtest profit cannot override either gate.
```

## Historical Mapping

The Selection Utility Gate uses only metric families already present in historical Opportunity evidence or current Phase19 validation evidence.

Mapping:

```text
Top5 realized return
  Phase5-H top5.selected_mean_future_return
  Phase17-BV18 rank 1-5 mean
  Phase18-F rank_1_5_performance.mean_realized_return_20d

Top10 realized return
  Phase5-H top10.selected_mean_future_return
  Phase17-BV18 rank 1-10 mean

Top20 realized return
  Phase5-H top20.selected_mean_future_return
  Phase17-BV18 rank 1-20 mean
  Phase18-F rank_1_20_performance.mean_realized_return_20d

Hit Rate
  Phase5-H win_rate_20d
  Phase17-BV18 / Phase18-F hit_rate

Downside Rate
  Phase5-H selected_downside_bad_rate
  Phase5-R downside_bad_topN_rate

Rank Lift
  Phase5-H lift_vs_candidate_top50_future_return
  Phase5-H model_minus_candidate_score_mean_future_return

NDCG
  Phase5-R ndcg@5 / ndcg@10 / ndcg@20

Correlation
  Phase5-R Spearman / Kendall
  Phase17-BV18 Pearson / Spearman / Kendall
  Phase19 AE Pearson / Spearman
```

This contract does not treat Phase5, Phase17, Phase18, and Phase19 artifacts as identical. It preserves metric semantics while requiring Phase19 artifact binding.

## Runtime Contract

Runtime may use Opportunity only through:

```text
Accepted Generation
-> Validation evidence with Global PASS and Selection PASS
-> Calibration Artifact
-> Opportunity Model
-> Opportunity Scaler
```

Runtime must reject:

```text
Global-only PASS
Selection-only PASS
REVIEW_REQUIRED
METRIC_UNAVAILABLE
Training Artifact direct use
Calibration Artifact direct use
latest / mtime / manual path fallback
component Registry fallback
hash or binding mismatch
```

AG does not create Runtime authority.

## Evidence

```text
reports/phase19_ag_dual_gate_opportunity_contract/
reports/phase_reports/phase19_ag_dual_gate_opportunity_contract.json
```

Required evidence:

```text
dual_gate_contract.json
global_gate_definition.json
selection_gate_definition.json
historical_metric_mapping.json
runtime_contract.json
remaining_risks.json
final_judgment.json
```

## Remaining Risks

AG fixes the gate structure and metric families, but does not invent numeric thresholds. AH must implement the evaluator so missing approved thresholds or missing metric semantics produce:

```text
REVIEW_REQUIRED
Generation Eligible = false
```

The current Phase19 Opportunity artifact remains a quality concern and is not made generation eligible by this contract.

## Non-mutation

No Training, Calibration, Formal Validation rerun, Model change, Feature change, Target change, Unified Generation, Accepted Generation, Runtime transition, BUY restart, or Broker write was performed.

## Next Step

```text
PHASE19_AH_IMPLEMENTATION_READY
```
