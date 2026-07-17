# Phase17-BV17 Opportunity AI Formal Model Revalidation and Calibration Root Cause Investigation

## Executive Summary

Phase17-BV17 revalidated the formal Opportunity AI model after Phase17-BV16 found that every Runtime candidate from `2026-06-29` through `2026-07-10` had `expected_edge_score <= 0`.

This was an investigation-only phase. No AI retraining, calibrator persistence, model/metrics/schema update, Registry refresh, Runtime code change, Runtime Test run/resume/reset/rollback/close, `.runtime` manual edit, J-Quants fetch, broker write, order submit, or notification was executed.

Root cause:

```text
Formal Opportunity model has stale/insufficiently current absolute calibration for the Runtime candidate population after the Phase5P cutoff; Runtime connection is valid; BV15 remains valid; retraining/revalidation is required before BUY can resume.
```

Final classifications:

```text
MODEL_RANKING_PERFORMANCE_VALID
MODEL_ABSOLUTE_CALIBRATION_DRIFTED
STRUCTURAL_MODEL_DECAY
CANDIDATE_POPULATION_DRIFT
TARGET_CONTRACT_VALID
RETRAIN_REQUIRED
TARGET_REDESIGN_NOT_REQUIRED
FORMAL_MODEL_STALE
BV15_CONTRACT_VALID
BUY_REMAINS_BLOCKED
BUY_REENABLE_CRITERIA_DEFINED
REVIEW_REQUIRED
```

## Evidence Scope

Primary artifacts:

- `.runtime/runtime_state/buy_ai/2026-06-29..2026-07-10/opportunity_rankings.json`
- `reports/opportunity_ai/phase5p/opportunity_dataset_with_market_sector.parquet`
- `reports/opportunity_ai/phase5p/training/opportunity_training_audit.json`
- `reports/opportunity_ai/phase5p/training/opportunity_training_metrics.json`
- `reports/opportunity_ai/phase5p/quality/opportunity_quality_by_split.csv`
- `.runtime/artifacts/ai/opportunity/model/formal_opportunity_model/sha256-140e350bd9b12bf0/model.pkl`
- `.runtime/artifacts/ai/opportunity/metrics/formal_opportunity_metrics/sha256-8428f2327e773747/metrics.json`
- `.runtime/artifacts/ai/opportunity/schema/formal_opportunity_schema/sha256-8428f2327e773747/feature_schema.json`
- `.runtime/phase9/canonical_data/normalized_daily_quotes/data.parquet`
- `.runtime/operations/jquants/raw_normalized/jquants/equities_bars_daily/data.parquet`

PIT note: Phase5P labels are existing historical labels with `target_date_split_separated=true`. Runtime realized returns were joined read-only from existing local J-Quants-derived quote parquet. Runtime 20bd realized returns are unavailable because local quotes end at `2026-07-14`.

## Model Contract

Formal model:

- model version: `opportunity_model_phase5e_v1`
- model hash: `140e350bd9b12bf0c595184587fa2a3bd74236e4bdf1818df481022980dd6acd`
- metrics hash: `8428f2327e77374743f69e2ebc956a97a9d718880ef2acfc26571f94d9fd9511`
- feature count: `32`
- training created at: `2026-06-14T01:22:38+00:00`
- dataset target range: `2021-09-08` to `2026-05-15`
- first Runtime replay date: `2026-06-29`
- gap from dataset max date to Runtime start: `45` days
- weekly retrain evidence found: `false`
- Registry recency gate evidence found: `false`

The training target remains `label__expected_edge_label_20d` in `src/ai_fund_lab_v2/opportunity_ai/training.py:18`.

## Target Label Contract

`src/ai_fund_lab_v2/opportunity_ai/dataset_builder.py:260-266` defines:

```text
risk_adjusted_future_return_20d =
  0.60 * clipped future_return_20d
  + 0.30 * clipped future_max_return_20d
  - 0.30 * clipped abs(future_max_drawdown_20d)
  - 0.20 * downside_bad_20d

expected_edge_label_20d = risk_adjusted_future_return_20d
```

This target is conservative by design. In Phase5P all rows, raw `label__future_return_20d` has positive rate `0.487236`, while `label__expected_edge_label_20d` has positive rate `0.462269` and mean `-0.062618`. The equality of expected-edge and risk-adjusted return is intentional in current code, not a discovered implementation mismatch.

Classification: `TARGET_CONTRACT_VALID`, with operational zero-threshold review still required before production BUY re-enable.

## Prediction Distribution Timeline

The formal model was re-applied to the Phase5P dataset and compared with Runtime v2 Opportunity rankings.

Key change points:

- Phase5P dataset date range: `2021-09-08` to `2026-05-15`
- last positive formal-model prediction date in available Phase5P/Runtime evidence: `2026-05-13`
- first Runtime v2 replay date: `2026-06-29`
- Runtime dates with positive predictions: `[]`
- Runtime all-negative dates: `2026-06-29` through `2026-07-10`

Runtime v2 daily means:

- `2026-06-29`: mean `-0.104585`, top1 `-0.064170`
- `2026-07-06`: mean `-0.156691`, top1 `-0.118392`
- `2026-07-10`: mean `-0.115165`, top1 `-0.047424`

Supplemental evidence: `reports/phase17_bv17_opportunity_formal_model_revalidation_and_calibration_root_cause_investigation/prediction_distribution_timeseries.csv`.

## Ranking Performance

On Phase5P all rows, the model retains positive ranking signal:

- 20bd Pearson: `0.232702`
- 20bd Spearman: `0.273186`
- 20bd Kendall: `0.185267`

Phase5P 20bd rank buckets:

- rank 1 mean realized return: `0.156906`, hit rate `0.651794`
- rank 1-5 mean realized return: `0.094833`, hit rate `0.599475`
- rank 1-20 mean realized return: `0.057755`, hit rate `0.548119`
- rank 21-50 mean realized return: `0.006261`, hit rate `0.446463`

Recent Phase5P degradation:

- `2026-04` 20bd Spearman: `0.043492`
- `2026-05` 20bd Spearman: `-0.037450`

Runtime read-only attribution:

- Runtime 5bd rank 1-5 mean return: `0.112912`, hit rate `0.484848`
- Runtime 5bd rank 1-20 mean return: `0.013181`, hit rate `0.297101`
- Runtime 10bd rank 1-20 mean return: `-0.034116`, hit rate `0.394737`

Interpretation: historical ranking performance is real, but current Runtime evidence is too short and mixed to justify BUY re-enable. The recent 2026 spring deterioration supports formal model staleness/revalidation risk.

## Score Buckets And Sign

Phase5P 20bd score buckets are monotonic:

- `score <= -0.10`: mean realized 20bd `-0.039018`, hit rate `0.334982`
- `-0.10 < score <= -0.05`: mean `0.013640`, hit rate `0.456507`
- `-0.05 < score <= -0.02`: mean `0.057227`, hit rate `0.568901`
- `-0.02 < score <= 0`: mean `0.094535`, hit rate `0.643144`
- `score > 0`: mean `0.142932`, hit rate `0.725010`

The positive bucket is meaningful in historical validation, but recall is low:

- 20bd precision: `0.725010`
- 20bd recall: `0.126936`
- balanced accuracy: `0.540594`

This confirms the model is conservative: positive predictions are relatively high quality, but many realized winners are scored non-positive.

## Calibration

Against raw realized 20bd return, the model is systematically conservative:

- decile 1 mean predicted `-0.179774`, mean realized `-0.060198`
- decile 10 mean predicted `0.056303`, mean realized `0.137668`

Against risk-adjusted 20bd target, calibration is closer:

- decile 1 mean predicted `-0.179774`, mean realized risk-adjusted `-0.188647`
- decile 10 mean predicted `0.056303`, mean realized risk-adjusted `0.068712`

Interpretation: the model is better calibrated to the conservative risk-adjusted target than to raw return. However, the Runtime period has all scores below zero, so a calibrator-only fix is not sufficiently proven. A calibrator would need formal PIT training/validation and no-leakage evidence before Runtime use; none was created in this phase.

Classification: `MODEL_ABSOLUTE_CALIBRATION_DRIFTED`, `CALIBRATION_ONLY_CANDIDATE` not sufficiently supported.

## Candidate Population Drift

Candidate score and rank distributions are broadly stable, but regime and feature distributions changed.

Phase5P all:

- candidate score mean `0.714031`
- 20d momentum mean `0.034200`
- volatility mean `0.043867`
- market return 20d mean `0.009472`
- market breadth 20d mean `0.512224`
- market risk flag mean `0.486762`

Runtime `2026-06-29..2026-07-10`:

- candidate score mean `0.716579`
- 20d momentum mean `-0.014286`
- volatility mean `0.051518`
- market return 20d mean `0.023765`
- market breadth 20d mean `0.660983`
- market risk flag mean `0.100000`

The input population is not a pure schema drift, but the Runtime candidate distribution differs from Phase5P and from recent 2026-04/05 in momentum, volatility, breadth, and market risk context. This supports `CANDIDATE_POPULATION_DRIFT`, not a Runtime wiring defect.

## Market Regime

Phase5P ranking signal exists in both market downtrend and uptrend regimes, stronger in downtrend:

- Phase5P downtrend 20bd Spearman: `0.345818`
- Phase5P uptrend 20bd Spearman: `0.217218`

Runtime regime attribution is limited:

- Runtime downtrend 5bd count `49`, Spearman `-0.105714`
- Runtime uptrend 5bd count `299`, Spearman `-0.072873`
- Runtime 20bd count `0`

The 10bd Runtime window is insufficient to isolate market regime as the sole cause. It does show that current PIT evidence does not prove ranking survival.

## Answers To Required Questions

1. **When did the model stop producing positive scores?**  
   In available formal-model evidence, the last positive date is `2026-05-13`. Runtime v2 starts on `2026-06-29` and has no positive dates.

2. **Is this only the 10 business day phenomenon?**  
   No. Phase5P late May also has very sparse/no positives. The exact gap between `2026-05-16` and `2026-06-28` is not covered by available formal inference artifacts.

3. **Is there continued degradation since spring 2026?**  
   Yes. Phase5P monthly 20bd Spearman drops to `0.043492` in `2026-04` and `-0.037450` in `2026-05`.

4. **Does ranking performance remain?**  
   Historically yes across Phase5P all rows; recent windows weaken materially.

5. **Did positive predictions lead to profit?**  
   Historically yes. Phase5P `score > 0` has 20bd mean return `0.142932` and hit rate `0.725010`.

6. **Did top-ranked negative predictions rise anyway?**  
   Sometimes. Runtime rank 1-5 5bd mean return is positive, but 10bd rank 1-20 is negative and sample size is limited.

7. **Is the zero threshold statistically valid?**  
   It is contractually valid and historically high precision. It is conservative and low recall, so threshold acceptance must be part of formal model validation.

8. **Is there downward bias?**  
   Yes against raw return. It is less severe against the risk-adjusted target.

9. **Can calibration alone fix it?**  
   Not proven. Calibration-only remains a candidate but cannot be accepted without formal PIT calibrator validation.

10. **Is retraining required?**  
    Yes before BUY re-enable. The formal model is stale for current Runtime use.

11. **Is target redesign required?**  
    Not proven. The current target is valid but conservative; redesign requires a separate formal target review.

12. **Is Candidate population drift a cause?**  
    Yes, as a contributing factor. Runtime candidate features differ in momentum, volatility, breadth, and market risk context.

13. **Is market regime a cause?**  
    Contributing but not sole cause. Runtime evidence is too short to isolate it.

14. **Is the formal model too old?**  
    Yes for production BUY enablement. Dataset ends `2026-05-15`, Runtime replay starts `2026-06-29`, and no weekly retrain/recency gate evidence was found.

15. **Was weekly retrain implemented?**  
    No evidence found in inspected metadata/artifacts.

16. **Is Runtime model selection correct?**  
    Yes. BV16 confirmed model/metrics/schema match and no feature missing/double-prefix.

17. **Should BV15 remain?**  
    Yes. `expected_edge_score <= 0` must remain BUY-ineligible.

18. **Should BUY remain blocked?**  
    Yes.

19. **Next minimal safe work?**  
    Formal Opportunity model retraining/revalidation and calibration study using PIT Runtime-compatible features after the Phase5P cutoff.

20. **BUY re-enable quantitative conditions?**  
    Defined in `buy_reenable_acceptance_criteria.json`: sufficient PIT dates, positive candidate sample size, top-k realized return/hit-rate lift, positive rank correlation, bounded calibration error, market-regime coverage, Registry PASS, no-leakage PASS, and BV14/BV15 PASS.

## Insufficient Evidence

- Runtime 20bd realized returns are unavailable from local quotes ending `2026-07-14`.
- No formal weekly retrain policy artifact was found in inspected metadata.
- Calibration methods were assessed diagnostically only; no calibrator was trained, saved, or applied.
- Target redesign is not proven necessary, but target zero-threshold operational meaning requires formal review.

## Supplemental Evidence

- `reports/phase17_bv17_opportunity_formal_model_revalidation_and_calibration_root_cause_investigation/prediction_distribution_timeseries.csv`
- `reports/phase17_bv17_opportunity_formal_model_revalidation_and_calibration_root_cause_investigation/prediction_distribution_change_points.json`
- `reports/phase17_bv17_opportunity_formal_model_revalidation_and_calibration_root_cause_investigation/prediction_vs_realized_return.csv`
- `reports/phase17_bv17_opportunity_formal_model_revalidation_and_calibration_root_cause_investigation/score_bucket_performance.csv`
- `reports/phase17_bv17_opportunity_formal_model_revalidation_and_calibration_root_cause_investigation/rank_bucket_performance.csv`
- `reports/phase17_bv17_opportunity_formal_model_revalidation_and_calibration_root_cause_investigation/calibration_by_decile.csv`
- `reports/phase17_bv17_opportunity_formal_model_revalidation_and_calibration_root_cause_investigation/calibration_diagnostics.json`
- `reports/phase17_bv17_opportunity_formal_model_revalidation_and_calibration_root_cause_investigation/regime_performance.csv`
- `reports/phase17_bv17_opportunity_formal_model_revalidation_and_calibration_root_cause_investigation/candidate_population_drift.csv`
- `reports/phase17_bv17_opportunity_formal_model_revalidation_and_calibration_root_cause_investigation/target_label_distribution.csv`
- `reports/phase17_bv17_opportunity_formal_model_revalidation_and_calibration_root_cause_investigation/model_age_and_training_contract.json`
- `reports/phase17_bv17_opportunity_formal_model_revalidation_and_calibration_root_cause_investigation/retrain_vs_calibration_decision_matrix.json`
- `reports/phase17_bv17_opportunity_formal_model_revalidation_and_calibration_root_cause_investigation/buy_reenable_acceptance_criteria.json`
- `reports/phase17_bv17_opportunity_formal_model_revalidation_and_calibration_root_cause_investigation/evidence_inventory.json`
- `reports/phase_reports/phase17_bv17_opportunity_formal_model_revalidation_and_calibration_root_cause_investigation.json`

## Prohibited Operations Confirmation

Not executed:

- AI retraining
- calibrator training/saving
- `model.pkl` / `metrics.json` / `feature_schema.json` modification
- formal Registry refresh
- Runtime code modification
- BV15 threshold change
- no-buy reason bypass
- Top-N forced BUY
- Runtime Test run/resume/reset/rollback/close
- Frozen Run edit
- `.runtime` manual edit
- Ledger/Pending/Current edit
- J-Quants fetch
- broker/Tachibana write
- production/demo order
- external notification

## Final Judgment

```text
REVIEW_REQUIRED
```

BUY remains blocked. The next safe phase is formal Opportunity model retraining/revalidation and calibration review, not a Runtime eligibility relaxation.
