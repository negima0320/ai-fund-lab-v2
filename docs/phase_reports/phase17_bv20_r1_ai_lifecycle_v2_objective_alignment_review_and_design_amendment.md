# Phase17-BV20-R1 AI Lifecycle v2 Objective Alignment Review and Design Amendment

## Executive Summary

Phase17-BV20-R1 reviewed `docs/02_architecture/ai_lifecycle_v2.md` against the AI Fund Lab v2 operating objective: Japanese cash equities, initial capital JPY 1,000,000, minimal operator time, autonomous daily operation, continuous opportunity capture, loss suppression, target capital deployment near 80%, and long-term return objective near +50%.

The review confirmed that AI Lifecycle v2 must be more than a safety-only MLOps contract. The common SoT was amended to require three separate readiness axes:

- Safety / Integrity
- Predictive Validity
- Operational Utility

The +50% return objective is not a direct single-model promotion PASS/FAIL criterion. It is allocated across Model, Strategy, and Portfolio responsibility layers. However, a design that permanently suppresses BUY opportunities while passing safety checks is not sufficient.

Final design status:

```text
AI_LIFECYCLE_V2_IMPLEMENTATION_READY
MODEL_LIFECYCLE_INCOMPLETE
```

The SoT is ready for BV21+ implementation phases, but the lifecycle is not implemented end to end yet.

## SoT Updated

Updated common architecture SoT:

```text
docs/02_architecture/ai_lifecycle_v2.md
```

This is not Phase17-only documentation. Future AI lifecycle phases must update and reference this file as the shared authority.

## Objective Alignment Amendments

Added `System Objective Alignment` to make the operating objective explicit:

- Japanese cash equities only
- cash-only operation
- initial evaluation capital JPY 1,000,000
- minimal operator workload
- autonomous daily operation
- continuous opportunity discovery
- loss suppression
- target deployment near 80%
- long-term return objective near +50%

The SoT now distinguishes:

- Model responsibility: predictive ranking, calibration, edge evidence
- Strategy responsibility: sizing, turnover, costs, eligibility, capital deployment
- Portfolio responsibility: cash deployment, concentration, drawdown, realized return

## Freshness Formula Review

BV20-R1 found that a raw `decision_date - training_dataset_max_date > 20bd` BUY block would double-count the Opportunity label horizon and could block a correctly updated 20bd target model.

The SoT now separates:

- `source_data_age_business_days`
- `feature_data_age_business_days`
- `label_safe_cutoff`
- `dataset_lag_business_days`
- `model_training_lag_business_days`
- `model_acceptance_age_business_days`

Required formulas:

```text
dataset_lag_business_days = label_safe_cutoff - training_dataset_max_date
model_training_lag_business_days = label_safe_cutoff - model_training_cutoff
model_acceptance_age_business_days = decision_date - model_accepted_at
```

Candidate AI and Opportunity AI may have different target horizons. Rule-based PM and Safety policy engines must not inherit trainable model age semantics.

## Model Health vs Market No-Opportunity

The SoT now separates:

```text
MODEL_UNHEALTHY
MARKET_NO_OPPORTUNITY
```

`positive_count=0` or `top1_score<=0` alone is not enough to classify model failure.

Composite classification now considers:

- artifact/schema/hash integrity
- model freshness
- dataset lag
- feature drift
- Candidate population drift
- prediction distribution drift
- historical baseline deviation
- all-negative persistence

All-negative with no hard freshness/drift/integrity failure can classify as `MARKET_NO_OPPORTUNITY`; all-negative plus hard failure blocks BUY.

## Monitoring Availability Contract

Daily Runtime gates may only depend on metrics available at decision time.

Immediate / unlabeled monitoring:

- artifact integrity
- model age / training lag
- dataset lag
- source freshness
- feature PSI
- Candidate population drift
- prediction distribution
- positive rate
- top1 score
- all-negative count

Delayed / labeled monitoring:

- realized return
- rank correlation
- top-k realized return
- hit rate
- calibration error
- score bucket monotonicity
- downside

Delayed metrics are required for lifecycle and promotion review, but not as direct same-day Runtime gates before labels exist.

## Promotion Readiness Layers

The SoT now defines three promotion evidence layers.

Layer A: Safety / Integrity

- no leakage
- schema/hash/lineage PASS
- PIT PASS
- consumer compatibility
- BV14 market-status compatibility
- BV15 expected-edge eligibility compatibility
- freshness PASS

Layer B: Predictive Validity

- Champion comparison
- Spearman / Kendall
- score bucket monotonicity
- positive score precision
- top-k realized return
- downside
- regime stability
- calibration

Layer C: Operational Utility

- positive candidate coverage
- NO BUY day ratio
- expected trade opportunity frequency
- expected capital deployment
- turnover
- transaction cost
- cost-adjusted edge
- concentration
- cash stagnation risk

Operational Utility is evidence, not forced BUY.

## BUY AI Compatibility Contract

The review selected:

```text
Option A: Atomic BUY AI Bundle
```

Candidate AI and Opportunity AI must not be switched independently for BUY Runtime. Runtime must resolve one compatible BUY AI bundle containing Candidate, Opportunity, compatibility evidence, joint bundle hash, and rollback bundle reference.

This prevents:

```text
new Candidate model + old Opportunity model trained on old Candidate population
```

## Retrain Cadence Semantics

`WEEKLY_RETRAIN` now means weekly lifecycle eligibility evaluation, not weekly model replacement.

The SoT separates:

- weekly eligibility check
- dataset rebuild eligibility
- Challenger train eligibility
- validation / promotion eligibility
- authority acceptance

Normal no-error outcomes include unchanged dataset, Challenger not better than Champion, operational utility insufficient, promotion not approved, and Champion retained while freshness/drift gates pass.

## Failure Blast Radius

The SoT now clarifies that BUY AI failures should block BUY without unnecessarily disabling SELL/current-state/report operations when their independent dependencies pass.

Safety policy failures remain scope-specific and fail-closed.

## Completion Definition

The SoT now states that AI Lifecycle v2 is complete only when the end-to-end control-plane path is proven:

```text
dataset / policy evidence
-> train or policy validation
-> promotion readiness
-> authority acceptance
-> Registry / bundle discovery
-> Runtime next-job use
-> rollback / revoke
```

Individual model, metrics, or Registry artifacts are insufficient.

## All AI Applicability

The design applies to:

- Candidate AI
- Opportunity AI
- Position Management AI / policy adapter
- Safety / Safety Policy Engine
- future trainable, rule-based, policy, or hybrid AI components

Trainable freshness and retrain semantics apply only to trainable components. Rule-based PM and Safety use policy evidence, semantic regression, policy freshness, and authority acceptance.

## Prohibited Operations Confirmation

Not performed:

- implementation
- dataset rebuild
- train / retrain
- model generation
- calibrator fitting
- promotion
- Registry update
- Runtime change
- Runtime Test
- LaunchAgent change
- J-Quants fetch
- broker write
- order submit
- external notification
- `.runtime` manual edit

## Evidence

Evidence files:

```text
reports/phase17_bv20_r1_ai_lifecycle_v2_objective_alignment_review_and_design_amendment/summary.json
reports/phase17_bv20_r1_ai_lifecycle_v2_objective_alignment_review_and_design_amendment/objective_alignment_matrix.json
reports/phase17_bv20_r1_ai_lifecycle_v2_objective_alignment_review_and_design_amendment/freshness_formula_review.json
reports/phase17_bv20_r1_ai_lifecycle_v2_objective_alignment_review_and_design_amendment/model_health_market_state_contract.json
reports/phase17_bv20_r1_ai_lifecycle_v2_objective_alignment_review_and_design_amendment/monitoring_availability_contract.json
reports/phase17_bv20_r1_ai_lifecycle_v2_objective_alignment_review_and_design_amendment/operational_utility_contract.json
reports/phase17_bv20_r1_ai_lifecycle_v2_objective_alignment_review_and_design_amendment/buy_ai_compatibility_contract.json
reports/phase17_bv20_r1_ai_lifecycle_v2_objective_alignment_review_and_design_amendment/retrain_cadence_review.json
reports/phase17_bv20_r1_ai_lifecycle_v2_objective_alignment_review_and_design_amendment/component_blast_radius.json
reports/phase17_bv20_r1_ai_lifecycle_v2_objective_alignment_review_and_design_amendment/completion_definition.json
reports/phase17_bv20_r1_ai_lifecycle_v2_objective_alignment_review_and_design_amendment/evidence_inventory.json
reports/phase_reports/phase17_bv20_r1_ai_lifecycle_v2_objective_alignment_review_and_design_amendment.json
```

## Final Judgment

```text
AI_LIFECYCLE_V2_IMPLEMENTATION_READY
```

BV21+ may proceed as implementation phases. The lifecycle itself remains:

```text
MODEL_LIFECYCLE_INCOMPLETE
```
