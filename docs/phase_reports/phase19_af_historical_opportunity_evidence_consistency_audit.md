# Phase19-AF — Historical Opportunity Evidence Consistency Audit

## Final Judgment

```text
PHASE19_AF_CONSISTENCY_AUDIT_COMPLETE
PHASE19_AG_HUMAN_DECISION_REQUIRED
```

Supporting judgments:

```text
PHASE19_AF_EVALUATION_CONTRACT_INCONSISTENCY_CONFIRMED
PHASE19_AF_HISTORICAL_ATTRIBUTION_GAP_CONFIRMED
PHASE19_AF_CURRENT_GENERATION_QUALITY_DEGRADATION_CONFIRMED
PHASE19_AF_NO_RUNTIME_MUTATION_PASS
PHASE19_AF_NO_BROKER_WRITE_PASS
```

This audit does not declare:

```text
PROJECT_INVALID
ALL_HISTORICAL_RESULTS_INVALID
OPPORTUNITY_ARCHITECTURE_INVALID
FORMAL_VALIDATION_PASS
GENERATION_READY
RUNTIME_READY
```

## Historical Evidence Inventory

Historical Opportunity evidence was found in Phase5-E, Phase5-H, Phase5-R, Phase17-BV17, Phase17-BV18, Phase18-E, and Phase18-F reports and JSON evidence.

The strongest pattern is:

- Phase5-H and Phase5-R measured Opportunity mainly as a selection-conditional TopN / ranking layer over CandidateTop50.
- Phase17-BV17 and BV18 preserved the expected-edge target and later 32-feature contract, but already found recent degradation and did not re-enable BUY.
- Phase18-E explicitly concluded that the current Opportunity model/training/calibration was not operationally usable.
- Phase18-F improved a challenger but still ended as `PHASE18_F_CHALLENGER_IMPROVED_NOT_PROMOTION_READY`.
- Phase19 U5 / AE measured the current corrective bootstrap artifact under formal test-window validation and found near-zero or negative Opportunity signal.

## Opportunity Role Consistency

Classification:

```text
ROLE_PARTIALLY_CHANGED
```

The conceptual role is consistent: Opportunity is the second-stage model that scores or ranks Candidate-derived buy opportunities. The evidence role changed materially. Historical phases usually judged Top5/Top10/Top20 selection performance over CandidateTop50, while Phase19 judges a contract-bound generation member through formal validation, calibration binding, split binding, and baseline diagnostics.

## Target Consistency

Classification:

```text
TARGET_IDENTICAL_WITH_EVALUATION_LABEL_DIFFERENCE
```

The target column remains:

```text
label__expected_edge_label_20d
```

The formal target semantics are continuous. However, historical reports often evaluated selected realized return, max return, hit rate, downside rate, or TopN lift in addition to the expected-edge label. Target continuity therefore does not make the evaluation contracts identical.

## Feature Consistency

Classification:

```text
FEATURES_PARTIALLY_CHANGED
```

Phase5-E used a 16-feature Opportunity model. Later formal lineage uses a 32-feature contract including Candidate, market, sector, trend, liquidity, volume, and missing-flag features. Phase19 uses that 32-feature order with a train-only StandardScaler bound as a generation artifact.

## Model Consistency

Classification:

```text
MODEL_MATERIALLY_CHANGED
```

Historical model families included Phase5 HistGradientBoosting and Phase18 standardized-ridge style challengers. Phase19 corrective bootstrap uses:

```text
sklearn_sgd_regressor
loss=squared_error
penalty=l2
StandardScaler=train-only
```

Historical model quality cannot be treated as model-identical evidence for the Phase19 corrective SGD artifact.

## Historical Evaluation Definition

Historical Opportunity evaluation primarily measured:

- CandidateTop50 to TopN selection lift
- Top5/Top10/Top20 realized future return
- hit rate / downside rate
- ranking quality such as NDCG, Spearman, and rank buckets
- runtime positive-score / no-buy diagnostics
- champion/challenger comparisons

Several historical reports explicitly recorded no promotion, no runtime switch, no broker write, no paper trading, or no production acceptance.

## Phase19 Evaluation Definition

Phase19 U5 / AE measured:

- formal test window only
- 1940 Opportunity rows across 39 business days
- Pearson / Spearman
- MAE / RMSE
- directional accuracy
- zero / mean / median baseline comparisons
- collapse / explosion / finite checks

Phase19 U5 did not execute recent holdout after the primary gate failed.

Current Phase19 Opportunity test metrics:

```text
Pearson: -0.013346777729190233
Spearman: -0.023113834309422397
Directional accuracy: 0.49948453608247423
Model beats zero baseline: false
Model beats mean baseline: false
Model beats median baseline: false
```

## Consistency Matrix

Overall classification:

```text
EVALUATION_CONTRACT_INCONSISTENCY_CONFIRMED
```

Key mismatches:

- Role concept: partial match
- Target column: match
- Target evaluation labels: partial match
- Feature contract: partial match
- Model family: mismatch
- Evaluation population: mismatch
- Evaluation windows: mismatch
- Baselines: mismatch
- Acceptance meaning: partial match
- Leakage controls: partial match, strengthened in Phase19

## Selection-Conditional Performance

Classification:

```text
SELECTION_CONDITIONAL_PERFORMANCE_NOT_EQUIVALENT_TO_FULL_SAMPLE_VALIDATION
```

Phase5-H had positive test Top5 lift versus CandidateTop50, but Top10 was weaker. Phase18-F had positive selected Top5 realized return while test Spearman remained negative. This shows that positive selected-slice outcomes and global rank/error diagnostics can diverge.

## Backtest / Paper Attribution

Classification:

```text
HISTORICAL_ATTRIBUTION_GAP_CONFIRMED
```

Phase5-H and Phase5-R explicitly record no backtest, no paper trading, no broker API execution, and no promotion. Phase17-BV18 and Phase18-F were evaluation/challenger reviews without runtime switch or broker write.

Historical operational evidence cannot be used as isolated Opportunity attribution unless it binds the same Opportunity artifact, generation contract, split, policy, runtime path, and baselines.

## Leakage Control Comparison

Classification:

```text
LEAKAGE_NOT_PRIMARY_ROOT_CAUSE_ON_AVAILABLE_EVIDENCE
```

Historical reports recorded leakage checks as OK or PASS. Phase19 has stronger hash-bound split, scaler, calibration, and artifact contracts. The available evidence points to evaluation/attribution/model/window mismatch rather than future leakage.

## Regime / Window Comparison

Classification:

```text
REGIME_AND_WINDOW_NON_TRANSFERABILITY_CONFIRMED
```

Historical signal is window-sensitive. Phase17-BV17 found broad historical 20bd Spearman around `0.273186`, but 2026-05 Spearman was already negative. Phase18-F improved recent holdout while test Spearman was negative. Phase19 AE again found negative test Spearman.

## Root Cause Classification

Primary causes:

- `AF-RC1`: evaluation contract inconsistency
- `AF-RC2`: historical attribution gap
- `AF-RC3`: current generation quality degradation

Secondary causes:

- `AF-RC4`: model and preprocessing change
- `AF-RC5`: regime/window non-transferability

## Project Impact Assessment

The audit does not invalidate the project, all historical results, or the Opportunity architecture.

The correct impact is narrower:

- Historical Opportunity evidence remains useful context.
- Historical evidence is not sufficient as Phase19 acceptance evidence.
- The current Phase19 Opportunity artifact is not ready for Unified Generation or Runtime.
- A Human Decision is required to align the Opportunity evaluation contract before proceeding.

## Human Decision Options

Option A: Correct Phase19 Opportunity evaluation contract only.

Option B: Treat current Opportunity generation as a quality failure and return to corrective model design.

Option C: Preserve the architecture but require dual evidence: global rank/error diagnostics and selection-conditional TopN utility.

Option D: Annotate historical evidence as contextual only and defer policy/model changes.

Recommended direction for review: Option C as policy direction, with Option B likely needed if the current model remains weak under the corrected dual gate.

## Non-mutation

PASS.

No Opportunity model, feature, target, policy, split, calibration, training, validation rerun, recent holdout access, dataset regeneration, backtest, paper trading, Unified Generation, Accepted Generation, Runtime transition, BUY restart, or Broker write was performed.

## Evidence Paths

```text
reports/phase19_af_historical_opportunity_evidence_consistency_audit/
reports/phase_reports/phase19_af_historical_opportunity_evidence_consistency_audit.json
```

Required evidence files:

```text
historical_opportunity_evidence_inventory.json
opportunity_role_consistency.json
opportunity_target_consistency.json
opportunity_feature_consistency.json
opportunity_model_consistency.json
historical_evaluation_definition.json
phase19_evaluation_definition.json
evaluation_consistency_matrix.json
selection_conditional_performance_audit.json
backtest_paper_attribution_audit.json
historical_leakage_control_comparison.json
regime_window_comparison.json
root_cause_classification.json
project_impact_assessment.json
human_decision_options.json
non_mutation_evidence.json
remaining_risks.json
final_judgment.json
```

## Remaining Risks

- Opportunity acceptance policy still needs a single approved contract that reconciles global rank/error and selection-conditional TopN utility.
- Current Phase19 Opportunity artifact still shows weak test signal.
- Historical attribution is not isolated enough to override formal validation.
- Window/regime transfer remains unstable.

## Next Step

```text
PHASE19_AG_HUMAN_DECISION_REQUIRED
```
