# Phase18-F — Opportunity Training Pipeline Redesign

- Run ID: `phase18f-opportunity-training-redesign-20260717T000000Z`
- Final judgment: `PHASE18_F_CHALLENGER_IMPROVED_NOT_PROMOTION_READY`
- Opportunity design judgment: `OPPORTUNITY_DESIGN_REUSE_RECOMMENDED`
- Selected spec: `{'model_name': 'standardized_ridge', 'window_name': 'recent_weighted', 'calibration_name': 'platt_like'}`
- Formal Challenger: `.runtime/ai_lifecycle/training/opportunity_ai/opportunity_training_phase18f_6cb9e62013a27d54`

## Fixed Contracts

- Target: `label__expected_edge_label_20d`
- Feature: `32 feature contract`
- Candidate connection: `candidate_source_ref`
- BUY eligibility: `BV15`
- Runtime BUY condition changes: `False`

## Selected Challenger Evidence

- Recent Spearman: `0.201712`
- Recent Top5 mean realized return: `0.109683`
- Recent Top20 mean realized return: `0.090403`
- Recent positive coverage: `0.176389`
- Recent no-buy ratio: `0.0`
- Recent calibration error: `0.255966`
- Cash stagnation risk: `LOW`

## Improvement vs Current Challenger

- Spearman delta: `0.274689`
- Top5 delta: `0.139161`
- Top20 delta: `0.085741`
- Positive coverage delta: `0.176389`
- No-buy ratio delta: `-1.0`

## Acceptance

- formal_challenger_generated: `PASS`
- current_improved: `PASS`
- recent_holdout_improved: `PASS`
- operational_utility_improved: `PASS`
- positive_coverage_improved: `PASS`
- no_buy_ratio_improved: `PASS`
- calibration_improved: `PASS`
- training_pipeline_pass: `PASS`
- reproducibility_pass: `PASS`
- registry_unchanged: `PASS`
- runtime_unchanged: `PASS`
- buy_not_restarted: `PASS`

## Non-Mutation

- Registry accepted update: `False`
- Runtime switch: `False`
- BUY restart: `False`
- Broker write: `False`

## Evidence

- Experiments: `reports/phase18_f_opportunity_training_pipeline_redesign/phase18f-opportunity-training-redesign-20260717T000000Z/experiment_results.json`
- Ranked experiments: `reports/phase18_f_opportunity_training_pipeline_redesign/phase18f-opportunity-training-redesign-20260717T000000Z/ranked_experiments.json`
- JSON report: `reports/phase_reports/phase18_f_opportunity_training_pipeline_redesign.json`
