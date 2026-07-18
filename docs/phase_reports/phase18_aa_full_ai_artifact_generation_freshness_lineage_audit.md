# Phase18-AA Full AI Artifact Generation, Freshness, and Lineage Audit

- Run ID: `phase18aa-full-ai-artifact-generation-freshness-lineage-audit-20260717T000000Z`
- Primary Judgment: `PHASE18_AA_SYSTEMIC_AI_STALENESS_CONFIRMED`
- Secondary Judgment: `PHASE18_AA_RUNTIME_RESOLVER_MISMATCH_CONFIRMED, PHASE18_AA_SPLIT_DESIGN_REMEDIATION_REQUIRED`

## Summary

- Candidate and Opportunity Promotion Candidate models both use current Common PIT Dataset bundles but their predictive train split ends at `2024-12-02`.
- Runtime legacy model paths do not hash-match the Phase18 Promotion Candidate model artifacts.
- PM, Safety, and Capital Allocation are current policy/rule/optimization authorities in the SoT, not trainable model freshness subjects.

## Stale Components

- `Candidate AI` `candidate_training_da0855d123ed1bed`: `STALE_MODEL` train_end=`2024-12-02` hash=`2bd16011bd3ecfa4cb2a452c11dfeb9cdfe5958be31ccd6d3d3944e125246eb5`
- `Opportunity AI` `opportunity_training_phase18h_1081babc49b5d26b`: `STALE_MODEL` train_end=`2024-12-02` hash=`c4ffc6ea1b1aad31986cf0a2ef2cf104c6106d5f7c90cf524aa216b67db6cbb6`
- `Candidate AI` `sha256-2ea75d14d3fe3682`: `RUNTIME_RESOLVER_MISMATCH` train_end=`2026-06-13` hash=`2ea75d14d3fe36828512d8e1fb0ac482798690c6594f22029c4d5b63c7fd6a02`
- `Opportunity AI` `sha256-140e350bd9b12bf0`: `RUNTIME_RESOLVER_MISMATCH` train_end=`2026-06-14` hash=`140e350bd9b12bf0c595184587fa2a3bd74236e4bdf1818df481022980dd6acd`

## Runtime Models

- Candidate runtime legacy hash: `2ea75d14d3fe36828512d8e1fb0ac482798690c6594f22029c4d5b63c7fd6a02`
- Candidate promotion hash: `2bd16011bd3ecfa4cb2a452c11dfeb9cdfe5958be31ccd6d3d3944e125246eb5`
- Candidate hash match: `False`
- Opportunity runtime legacy hash: `140e350bd9b12bf0c595184587fa2a3bd74236e4bdf1818df481022980dd6acd`
- Opportunity promotion hash: `c4ffc6ea1b1aad31986cf0a2ef2cf104c6106d5f7c90cf524aa216b67db6cbb6`
- Opportunity hash match: `False`

## Dataset / Model / Metadata Matrix

- candidate: dataset_max=`2026-05-15`, model_train_end=`2024-12-02`, label_safe_cutoff=`2026-06-04`
- opportunity: dataset_max=`2026-05-15`, model_train_end=`2024-12-02`, label_safe_cutoff=`2026-06-04`

## Phase18 Audit Gap

- Promotion Candidate predictive model train end as freshness authority
- Dataset latest date versus actual model train end distinction
- Runtime legacy resolver model hashes versus Promotion Candidate model hashes
- Accepted Atomic BUY AI Bundle absence as independent runtime authority blocker
- Cross-component artifact generation inventory beyond Candidate/Opportunity training bundles

## Recommended Scope

- Retraining: `Candidate AI, Opportunity AI`
- Regeneration: `Opportunity calibration, Runtime baseline, freshness metadata, promotion/authority evidence after retraining`
- Reauthorization: `Atomic BUY AI Bundle, Registry Promotion Candidate, Accepted Authority event after readiness passes`
- Split redesign required: `True`

## Non-Mutation Confirmation

- retraining_performed: `False`
- split_changed: `False`
- dataset_rebuilt: `False`
- calibration_refit: `False`
- baseline_regenerated: `False`
- promotion_candidate_updated: `False`
- registry_accepted_event_created: `False`
- registry_index_updated: `False`
- runtime_accepted_state_created: `False`
- runtime_resolver_changed: `False`
- cutoff_overwritten: `False`
- freshness_threshold_relaxed: `False`
- forced_buy: `False`
- broker_write: `False`
- production_runtime_executed: `False`
- historical_fresh_run_executed: `False`

## Validation

- read_only: `PASS`
- model_pickle_not_loaded: `PASS`
- missing_evidence_fail_closed: `PASS`
- pytest: `PASS`
- compile: `PASS`
- json_validation: `PASS`

## Final

`PHASE18_AA_SYSTEMIC_AI_STALENESS_CONFIRMED`
