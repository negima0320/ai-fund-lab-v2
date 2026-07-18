# Phase18-AB Runtime Legacy Model Provenance & AI Generation Pipeline Audit

- Run ID: `phase18ab-runtime-legacy-provenance-generation-pipeline-audit-20260718T000000Z`
- Primary Judgment: `PHASE18_AB_SYSTEMIC_AI_GENERATION_GAP_CONFIRMED`
- Secondary Judgments: `PHASE18_AB_RUNTIME_RESOLVER_REMEDIATION_REQUIRED, PHASE18_AB_FORMAL_RETRAINING_REQUIRED`

## Runtime AI In Use

- Candidate: `.runtime/artifacts/ai/candidate/model/formal_candidate_model/sha256-2ea75d14d3fe3682/model.pkl` hash=`2ea75d14d3fe36828512d8e1fb0ac482798690c6594f22029c4d5b63c7fd6a02`
- Opportunity: `.runtime/artifacts/ai/opportunity/model/formal_opportunity_model/sha256-140e350bd9b12bf0/model.pkl` hash=`140e350bd9b12bf0c595184587fa2a3bd74236e4bdf1818df481022980dd6acd`

## Promotion Candidate Difference

- Candidate runtime == promotion: `False`
- Opportunity runtime == promotion: `False`
- Promotion Candidate train end: Candidate=`2024-12-02`, Opportunity=`2024-12-02`

## Mismatch Cause

- Migration boundary/design gap: formal Registry accepted sets still point to Phase4/Phase5 legacy artifacts while Phase18 Promotion Candidate remains runtime_use_eligible=false and no accepted Atomic BUY AI Bundle state exists.

## AI Generation Pipeline

- Raw Data: automatic=`partial` gap=``
- Normalized: automatic=`partial` gap=``
- Common PIT Dataset: automatic=`manual/operator` gap=`No observed LaunchAgent that rebuilds Common PIT and chains downstream training automatically.`
- Split: automatic=`training-time only` gap=`Promotion Candidate retained stale 2024-12-02 train end after dataset update.`
- Training: automatic=`manual/operator` gap=`No production scheduler connects dataset freshness to actual retraining and artifact selection automatically.`
- Calibration: automatic=`manual/operator` gap=`Calibration is not an independent freshness update for predictive model.`
- Validation: automatic=`training-time` gap=``
- Promotion Candidate: automatic=`manual/operator` gap=`runtime_use_eligible=false; not accepted.`
- Accepted Bundle: automatic=`manual authority required` gap=`No .runtime/runtime_state/accepted_buy_ai_bundle.json.`
- Runtime Resolver: automatic=`runtime` gap=`Resolved accepted legacy set, not Phase18 Promotion Candidate Atomic BUY bundle.`
- Inference: automatic=`runtime` gap=`Lifecycle gate blocks BUY when accepted atomic evidence is missing/stale.`
- Runtime: automatic=`runtime` gap=`BUY cannot resume without fresh accepted atomic authority.`

## Latest AI Maintenance

- latest_dataset_means_latest_ai: `False`
- pipeline_complete: `False`
- automatic_parts: `runtime market refresh, runtime resolver at execution, runtime freshness/drift gate evaluation`
- manual_parts: `Common PIT Dataset rebuild, training invocation, promotion readiness review, authority approval, accepted event materialization, runtime accepted state transition`

## Retraining Decision

- retraining_required: `True`
- scope: `Candidate AI, Opportunity AI`
- next_unit_allowed_to_retrain: `True`

## Non-Mutation Confirmation

- retraining_performed: `False`
- split_changed: `False`
- dataset_changed: `False`
- calibration_refit: `False`
- promotion_candidate_changed: `False`
- registry_changed: `False`
- accepted_changed: `False`
- runtime_changed: `False`
- resolver_changed: `False`
- runtime_switch_performed: `False`
- broker_write: `False`
- historical_fresh_run: `False`
- production_runtime_executed: `False`
- model_pickle_loaded: `False`

## Validation

- read_only: `PASS`
- model_pickle_not_loaded: `PASS`
- json_validation: `PASS`
- pytest: `PASS`
- compile: `PASS`

## Final

`PHASE18_AB_SYSTEMIC_AI_GENERATION_GAP_CONFIRMED`
