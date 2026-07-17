# Phase17 Final Summary and Phase18 Handoff

## Executive Summary

Phase17 is closed as a partial Historical Runtime acceptance and AI Lifecycle design handoff phase, not as a complete production BUY/SELL lifecycle acceptance.

Phase17 confirmed that Runtime v2 can execute a 10-business-day Historical Extended Smoke without job failure across the no-action path. It also confirmed that Runtime v2 resolves accepted AI artifacts fail-closed, executes Candidate/Opportunity Runtime inference, preserves BUY eligibility guards, and maintains Historical state transitions through Submit, Execution, Ledger, Current, and Valuation jobs.

However, the accepted formal Opportunity model produced no positive expected-edge BUY candidates during the 10-business-day replay. Therefore BUY, Fill, Hold, PM-on-real-position, and SELL full-path acceptance were not exercised. Phase17 later shifted from local Runtime fixes into AI Lifecycle v2 architecture, because the BUY 0 result exposed a larger missing system: the repository had model and Registry parts, but not a complete dataset rebuild -> retrain -> validation -> promotion -> Registry -> Runtime freshness/drift lifecycle.

Final status:

```text
PHASE17_HISTORICAL_RUNTIME_ACCEPTANCE_PARTIAL
PHASE17_AI_LIFECYCLE_DESIGN_COMPLETE
PHASE18_IMPLEMENTATION_REQUIRED
REVIEW_REQUIRED
```

`REVIEW_REQUIRED` means AI Lifecycle v2 implementation and full BUY-to-SELL acceptance remain open for Phase18. It does not mean this handoff failed.

## Phase17 Purpose

Phase17 began as Historical Runtime v2 acceptance. Its intended purpose was to prove that Runtime v2 could replay historical business days with production-like authority boundaries:

- market refresh
- data readiness
- morning planning
- sell planning
- submit
- execution simulation
- ledger/current update
- current valuation
- next business day continuity

As blockers were found and fixed, Phase17 also became the phase that clarified BUY/SELL Runtime contracts, Historical point-in-time data authorities, and the AI Lifecycle gap.

Formal Phase17 position:

```text
Historical Runtime Acceptance
+
Runtime v2 BUY/SELL/Execution/Ledger/Valuation verification
+
Opportunity AI BUY eligibility defect investigation
+
AI Lifecycle incomplete-system discovery
+
AI Lifecycle v2 common architecture design
```

## Phase17 Work Summary

### Historical Runtime Acceptance Foundation

Phase17 built and hardened:

- Historical Runtime Test plan/run lifecycle
- business-date replay
- clean reset / backup / plan / run discipline
- frozen-run evidence preservation
- pending continuity
- EMPTY / no-signal Pending as a normal terminal state
- NO_ACTION Submit and Execution semantics
- historical broker authority
- historical market / listed issues / trading calendar authority
- execution projection
- ledger projection
- current valuation temporal policy
- Runtime Current updates
- feature date authority boundaries
- PM adapter authority and Registry identity
- canonical performance event semantics

### Historical Extended Smoke Result

Primary run:

```text
runtime-test-historical-extended-smoke-20260716T230100525117Z
```

Period:

```text
2026-06-29 through 2026-07-10
```

Result:

```text
business_days: 10
job_records: 80
pass_like: 80
non_pass: 0
status: COMPLETED
```

Job types, each executed 10 times:

- market_refresh
- data_readiness
- morning
- sell_planning
- submit
- execution
- runtime_state_refresh
- current_valuation_refresh

Important boundary:

```text
80/80 job completion proves Historical scheduler/no-action Runtime continuity.
It does not prove full BUY / Fill / Hold / SELL lifecycle acceptance because BUY count was 0.
```

### BUY / Opportunity Eligibility Fixes

Phase17-BV14 implemented market-status BUY eligibility:

- delisted / non-listed symbols cannot be newly bought
- point-in-time listed issues authority is used
- future delisting knowledge is not applied backward
- Submit has a final BUY market-status guard
- SELL is not blocked by the BUY-only guard

Representative evidence: runtime symbol `36810` / V-cube had no 2026-07-01 quote because the issue was delisted effective 2026-07-01. BV14 did not hard-code V-cube; it added the general point-in-time BUY eligibility guard.

Phase17-BV15 fixed Opportunity BUY eligibility:

- rank is ranking evidence, not BUY permission
- BUY requires `expected_edge_score > 0`
- BUY requires no `no_buy_reason`
- Morning and Submit both verify eligibility
- BV14 and BV15 are AND conditions
- SELL does not run BUY eligibility guards

BV15 did not retrain the model and did not alter AI output. It corrected Runtime consumption of already-present no-buy evidence.

### BUY 0 Investigation

Target run:

```text
runtime-test-historical-extended-smoke-20260716T230100525117Z
```

BV16 observed:

```text
Runtime candidate count: 500
Top20 total: 200
positive expected_edge_score: 0
negative/non-positive: 500
```

Major BV16-BV18 classifications:

```text
MODEL_OUTPUT_SEMANTICS_VALID
MODEL_METRICS_MATCH
RUNTIME_FEATURE_DRIFT_NOT_DETECTED
EXPECTED_EDGE_SIGN_OR_SCALE_VALID
BV15_CONTRACT_VALID
MODEL_ABSOLUTE_CALIBRATION_DRIFTED
STRUCTURAL_MODEL_DECAY
CANDIDATE_POPULATION_DRIFT
FORMAL_MODEL_STALE
NO_LEAKAGE_PASS
CHALLENGER_PROMOTION_NOT_READY
BUY_REMAINS_BLOCKED
```

Conclusion:

```text
Runtime connection fix is not indicated.
BV15 threshold relaxation is prohibited.
BUY remains blocked until a fresh PIT dataset / retraining / validation / promotion lifecycle produces an accepted BUY bundle with evidence.
```

### Opportunity AI Investigation

The accepted formal Opportunity model:

- uses `label__expected_edge_label_20d`
- emits raw expected edge into `expected_edge_score`
- does not have a discovered sign inversion or percent/decimal scale bug
- has matching formal model / metrics / schema authority
- is capable of positive historical predictions but produced zero positives for the 2026-06-29..2026-07-10 Runtime replay

BV17 confirmed:

- formal training dataset target range ended at `2026-05-15`
- first Runtime replay date was `2026-06-29`
- weekly retrain evidence was not found
- Registry recency gate evidence was not found
- model ranking signal exists historically but recent calibration and candidate-population fit are stale

BV18 trained/evaluated challengers under reports only, with no Registry promotion or Runtime switch. Some challengers restored positive Runtime replay scores, but promotion was not ready.

### AI Lifecycle Audit

BV19 final classifications:

```text
TRAINING_PIPELINE_PARTIAL
AUTO_RETRAIN_NOT_READY
REGISTRY_PARTIAL
MODEL_LIFECYCLE_INCOMPLETE
DATASET_PIPELINE_BLOCKED
REVIEW_REQUIRED
```

Root cause:

```text
Phase5 / Phase9 contain useful dataset/training/audit building blocks.
Runtime can safely consume accepted Registry artifacts.
But there is no complete automated and authority-mediated pipeline from latest PIT data to dataset rebuild, retrain, validation, promotion readiness, Registry acceptance, Runtime freshness/drift gate, and rollback.
```

### AI Lifecycle v2 Design

BV20 and BV20-R1 created and amended the common SoT:

```text
docs/02_architecture/ai_lifecycle_v2.md
```

The design covers:

- Runtime Data Plane
- Runtime Control Plane
- AI Lifecycle Control Plane
- Artifact Registry
- Operator / Authority
- Monitoring / Alerting

Important contracts:

- System Objective Alignment
- Safety / Predictive Validity / Operational Utility
- freshness formula separation
- `MODEL_UNHEALTHY` / `MARKET_NO_OPPORTUNITY`
- Immediate / Delayed monitoring
- Atomic BUY AI Bundle
- weekly retrain eligibility semantics
- AI failure blast radius
- Registry-mediated rollback
- BUY and SELL independent failure semantics
- end-to-end completion definition

Covered components:

- Candidate AI
- Opportunity AI
- Position Management AI / Policy Adapter
- Safety Policy Engine
- future AI components

## Phase17 Final Layered Status

```text
Historical Runtime Scheduler / No-action Path: PASS
Runtime v2 artifact resolution / fail-closed: PASS
Candidate AI Runtime execution: PASS
Opportunity AI Runtime execution: PASS
BV14 Market Status BUY Guard: PASS
BV15 Opportunity BUY Eligibility: PASS
BUY lifecycle: NOT_ACCEPTED / NOT_EXERCISED
Position Management with actual positions: NOT_ACCEPTED / NOT_EXERCISED
SELL lifecycle: NOT_ACCEPTED / NOT_EXERCISED
AI Lifecycle v2 architecture: DESIGN_COMPLETE / IMPLEMENTATION_READY
AI Lifecycle v2 implementation: NOT_IMPLEMENTED
Formal Opportunity model: STALE / NOT_PROMOTION_READY
BUY: REMAINS_BLOCKED
```

## Unfinished Items

Phase17 intentionally does not close these items:

- latest PIT Dataset Rebuild Pipeline
- Candidate / Opportunity shared Dataset Lifecycle
- train / retrain pipeline
- Champion / Challenger formal evaluation
- Promotion Readiness
- Atomic BUY AI Bundle packaging
- Authority-approved Registry promotion
- Runtime freshness gate
- Runtime drift gate
- weekly lifecycle scheduler
- lifecycle observability
- rollback / revoke acceptance
- End-to-End AI Lifecycle Acceptance
- Historical Runtime Test with new accepted BUY AI Bundle
- BUY / Fill / Hold / SELL full-path acceptance

Opportunity AI design is provisionally retained.

```text
Redesign condition:
Only if the current specification fails after fresh PIT dataset reconstruction and formal retraining/revalidation.
```

## Phase18 Purpose

Formal name:

```text
Phase18 — AI Lifecycle v2 Implementation and End-to-End Acceptance
AI Lifecycle v2 実装・統合受入
```

Purpose:

```text
AI Fund Lab v2の全AIコンポーネントについて、
データまたはPolicy Evidence更新、
Dataset rebuild、
retrainまたはPolicy validation、
Champion/Challenger評価、
Promotion readiness、
Authority acceptance、
Registry切替、
Runtime freshness/drift gate、
scheduler、
monitoring、
rollbackまでを、
共通AI Lifecycle v2 SoTに従って安全・再現可能・監査可能に実装する。
```

Scope:

- Candidate AI
- Opportunity AI
- Position Management AI / Policy Adapter
- Safety Policy Engine
- future AI onboarding contract

PM and Safety are currently policy/rule-based lifecycle components. Do not apply Candidate/Opportunity trainable retraining semantics to them unless their trainable design is first added to the SoT.

## Phase18 Roadmap

### Phase18-A — Common PIT Dataset Rebuild Pipeline

- Candidate PIT Dataset
- Opportunity PIT Dataset
- label-safe cutoff
- source authority
- schema
- lineage
- data quality
- leakage audit
- idempotency
- versioned dataset artifact

### Phase18-B — Training / Validation / Challenger Pipeline

- Candidate Challenger
- Opportunity Challenger
- time-series split
- validation
- test
- recent holdout
- Champion comparison
- calibration
- regime evaluation
- reproducibility

### Phase18-C — Promotion Readiness and Atomic BUY AI Bundle

- Safety / Integrity
- Predictive Validity
- Operational Utility
- Candidate / Opportunity compatibility
- Atomic BUY AI Bundle
- promotion request
- rollback metadata

### Phase18-D — Registry Promotion Operator

- Authority review
- `ARTIFACT_ACCEPTED`
- atomic Registry update
- materialized index
- previous Champion retention
- revoke / rollback
- idempotency

### Phase18-E — Runtime Freshness and Drift Gates

- source freshness
- dataset lag
- model training lag
- model acceptance age
- feature drift
- Candidate population drift
- prediction drift
- `MODEL_UNHEALTHY`
- `MARKET_NO_OPPORTUNITY`
- BUY `BLOCK` / `REVIEW_REQUIRED`
- SELL continuity

### Phase18-F — Weekly Lifecycle Scheduler and Observability

- weekly eligibility check
- label-safe readiness
- locks
- retry
- timeout
- no overlap
- status artifacts
- operator reports
- alerts
- no automatic self-promotion

### Phase18-G — Full AI Component Lifecycle Coverage

- Candidate AI lifecycle
- Opportunity AI lifecycle
- PM policy lifecycle
- Safety policy lifecycle
- future AI onboarding
- failure blast radius
- policy freshness
- semantic regression

### Phase18-H — End-to-End AI Lifecycle Acceptance

- dataset rebuild
- train / validation
- promotion readiness
- authority rehearsal
- Registry acceptance rehearsal
- Runtime next-job discovery
- freshness / drift gates
- rollback rehearsal
- failure cases

### Phase18-I — Historical Runtime Re-Acceptance

- new accepted Atomic BUY AI Bundle
- fresh Historical Runtime Test
- BUY
- Submit
- Fill
- Ledger
- Current
- Valuation
- PM
- SELL
- Report
- Notification

Phase18-I must not use Production broker write. Use Historical or formally approved Demo/Paper only.

## Phase18 Start Conditions

```text
docs/02_architecture/ai_lifecycle_v2.md accepted as SoT
BV20-R1 objective alignment complete
Phase17 final handoff accepted
BUY remains blocked
no Runtime model switch pending
no unreviewed Registry promotion pending
existing formal artifact set remains unchanged
```

## Phase18 Completion Conditions

Phase18 is not complete merely because individual parts exist.

Required:

```text
latest label-safe dataからCandidate/Opportunity datasetを再構築可能
dataset reproducibility / idempotency PASS
no leakage PASS
formal retraining / validationを再現可能
Champion / Challenger comparison PASS
Operational Utility評価可能
Atomic BUY AI Bundle生成可能
authority-approved Registry promotion可能
Runtimeがnext-job boundaryでbundleを発見
freshness / drift gateがscope別に動作
stale modelでBUY BLOCK
MARKET_NO_OPPORTUNITYとMODEL_UNHEALTHYを区別
SELL continuity PASS
weekly scheduler / monitoring PASS
rollback / revoke rehearsal PASS
Candidate / Opportunity / PM / Safety lifecycle coverage PASS
Historical RuntimeでBUYからSELLまでのfull pathを再Acceptance
```

Final judgment candidates:

```text
AI_LIFECYCLE_V2_IMPLEMENTATION_COMPLETE
ALL_AI_LIFECYCLE_COVERAGE_PASS
ATOMIC_BUY_AI_BUNDLE_ACCEPTED
RUNTIME_FRESHNESS_DRIFT_GATES_PASS
WEEKLY_LIFECYCLE_OPERATIONAL
ROLLBACK_ACCEPTANCE_PASS
HISTORICAL_RUNTIME_FULL_PATH_PASS
PHASE18_COMPLETE
```

Any unmet mandatory item must remain `REVIEW_REQUIRED` or an appropriate blocking status.

## Handoff Mapping

| Phase17 Evidence / Gap | Phase18 Step |
| --- | --- |
| BV19 Dataset Pipeline gap | Phase18-A |
| BV18 Challenger not promotion-ready | Phase18-B / Phase18-C |
| BV20 Atomic BUY AI Bundle design | Phase18-C / Phase18-D |
| BV20-R1 Freshness / Drift design | Phase18-E |
| BV20 Scheduler design | Phase18-F |
| All AI lifecycle coverage requirement | Phase18-G |
| AI Lifecycle completion definition | Phase18-H |
| Historical full path unexercised | Phase18-I |

## Important SoT

- `docs/01_requirements/phase_roadmap.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/ai_lifecycle_v2.md`
- `docs/03_ai_design/opportunity_ai_design.md`
- `docs/phase_reports/phase17_bv14_market_status_buy_eligibility_guard.md`
- `docs/phase_reports/phase17_bv15_opportunity_buy_eligibility_contract_fix.md`
- `docs/phase_reports/phase17_bv16_opportunity_expected_edge_semantics_and_runtime_distribution_investigation.md`
- `docs/phase_reports/phase17_bv17_opportunity_formal_model_revalidation_and_calibration_root_cause_investigation.md`
- `docs/phase_reports/phase17_bv18_opportunity_pit_retraining_challenger_validation_and_promotion_readiness.md`
- `docs/phase_reports/phase17_bv19_ai_training_lifecycle_and_retraining_pipeline_audit.md`
- `docs/phase_reports/phase17_bv20_ai_lifecycle_v2_architecture_and_runtime_responsibility_design_contract.md`
- `docs/phase_reports/phase17_bv20_r1_ai_lifecycle_v2_objective_alignment_review_and_design_amendment.md`

## Important Artifact Paths

- Historical Extended Smoke evidence: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260716T230100525117Z/`
- Run state: `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260716T230100525117Z/run_state.json`
- Formal Opportunity model: `.runtime/artifacts/ai/opportunity/model/formal_opportunity_model/sha256-140e350bd9b12bf0/model.pkl`
- Formal Opportunity metrics: `.runtime/artifacts/ai/opportunity/metrics/formal_opportunity_metrics/sha256-8428f2327e773747/metrics.json`
- Formal Opportunity schema: `.runtime/artifacts/ai/opportunity/schema/formal_opportunity_schema/sha256-8428f2327e773747/feature_schema.json`
- Phase5P Opportunity dataset: `reports/opportunity_ai/phase5p/opportunity_dataset_with_market_sector.parquet`
- AI Lifecycle SoT: `docs/02_architecture/ai_lifecycle_v2.md`

## Prohibited Operations For This Handoff

Not executed in this handoff:

- Dataset rebuild
- training / retraining
- model generation
- calibrator fitting
- Promotion
- Registry update
- Runtime model switch
- Runtime code change
- Runtime Test
- LaunchAgent change
- J-Quants fetch
- broker write
- order submit
- notification
- `.runtime` manual edit
- Ledger / Pending / Current edit

## Notes For Next ChatGPT / Codex

- Do not relax model thresholds by assumption.
- Do not decide that BUY 0 is inherently normal or abnormal without evidence.
- Separate `MODEL_UNHEALTHY` from `MARKET_NO_OPPORTUNITY` with evidence.
- Do not redesign Opportunity AI target first.
- First complete latest PIT Dataset rebuild, retraining, and validation for the current specification.
- Treat Candidate and Opportunity as an Atomic BUY AI Bundle.
- Do not let BUY freshness problems unnecessarily stop SELL.
- Do not mix Runtime responsibility with AI Lifecycle responsibility.
- Registry acceptance is Operator / Authority responsibility.
- Do not re-enable Production BUY before Phase18 completion.

## First Phase18 Step

Start with:

```text
Phase18-A — Common PIT Dataset Rebuild Pipeline
```

Phase18-A must prove that latest label-safe Candidate and Opportunity PIT datasets can be rebuilt reproducibly with schema, lineage, source authority, leakage audit, and hash evidence before any retraining or promotion work begins.
