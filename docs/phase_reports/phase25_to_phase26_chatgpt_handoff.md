# Phase25 to Phase26 ChatGPT Handoff

## Current Phase

Phase25 is closed.

Current status:

`PHASE25_ARCHITECTURE_CONFORMANCE_REVIEW_COMPLETE_PHASE26_EXECUTION_READY`

## Phase25 Closure Judgment

Phase25 did not fix all problems. Phase25 completed the re-audit of Phase21-24 Architecture, confirmed Phase26 repair gaps with evidence, and fixed the repair order, dependency plan, regression order, closure contract, and user test plan.

Secondary judgments:

- `PHASE25_CLOSED_WITH_CONFIRMED_ARCHITECTURE_AND_MIGRATION_GAPS`
- `PHASE26_PRODUCTION_ARCHITECTURE_REPAIR_ENTRY_APPROVED`
- `PHASE27_PRODUCTION_EQUIVALENT_VALIDATION_PLANNED`

## Phase26 Name

`Phase26 - Production Architecture Repair, Legacy Retirement and Evaluation Readiness Restoration`

## Phase26 Objective

Repair only Phase25-confirmed gaps as Production / Demo / Historical common Runtime work, retire or reclassify old authorities and consumers, strengthen closure gates, materialize runtime decision evidence, and restore Performance Evaluation readiness.

## Permanent Rules

- Future Data禁止
- Runtime Test結果を学習入力に使用しない
- Paper Ledgerを学習入力に使用しない
- PnLを学習入力に使用しない
- selected / bought / cash / portfolio valueを学習入力に使用しない
- Safety Guardを弱めない
- Submit Guardを弱めない
- Corporate Action Guardを弱めない
- Historical専用Strategy禁止
- Production / Demo / Historical共通Runtime維持
- 固定BUY件数禁止
- 正当な0件BUYを許容
- Strategy改善禁止
- Performance tuning禁止
- Runtime PASSをArchitecture Conformance PASSとして扱わない
- Design Closure、Runtime Operability Closure、Migration Closureを区別する

## Confirmed Critical Gaps

- `P25-GAP-LEG-CAP-001`: Fixed CapitalDeploymentPolicy evaluation_capital remains active.
- `P25-GAP-LEG-POS-001`: Fixed max_positions=5 remains active Runtime position-count authority.
- `P25-GAP-LEG-EXP-001`: Fixed target/cash/exposure policy remains active cash-exposure authority.

## Confirmed High Gaps

- `P25-GAP-CAP-001`: Dynamic equity sizing coexists with fixed Runtime deployment cap.
- `P25-GAP-LEG-SCHEMA-001`: Shadow-era Strategy metadata conflicts with active Runtime consumers.
- `P25-GAP-LEG-CAP-002`: runtime_evaluation_capital remains ambiguous Current/projection capital field.

## Evidence-required Items

- Accepted Generation fallback zero across modes.
- Temporal latest-path authority classification.
- Mode authority deltas.
- Other shadow Strategy artifact consumer switches.

## Phase26 Repair Order

0. Closure / Negative Assertion Foundation
1. Capital Authority
2. Dynamic Position Count
3. Dynamic Cash / Exposure
4. Portfolio Policy / Position Sizing
5. Runtime Planning / Planning Authority
6. Submit / Submit Guard alignment
7. Current / Ledger / Broker / Projection
8. Accepted Generation / Temporal Authority
9. Observability Materialization
10. Full Migration Regression
11. Performance Evaluation Readiness

## Phase26 First Task

`Phase26-Step0 Architecture Foundation and Closure Gate Contract Implementation`

Implement common infrastructure before Capital repair:

- Closure label
- Negative assertion framework
- Claim-to-Evidence ledger
- Old-path-zero checks
- Mode parity checks
- FULL_MIGRATION_REGRESSION contract

## Mandatory Reading

- `docs/phase_reports/phase25_final_summary_and_phase26_handoff.md`
- `reports/phase_reports/phase25_final_architecture_conformance_gap_snapshot.json`
- `reports/phase_reports/phase26_repair_master_plan.json`
- `reports/phase25_final_summary_and_phase26_handoff/closure_contract.md`
- `reports/phase25_final_summary_and_phase26_handoff/phase26_entry_gate.md`
- `reports/phase25_final_summary_and_phase26_handoff/phase26_repair_order.md`
- `docs/01_requirements/phase_roadmap.md`

## Long Test Responsibility

Long Historical Tests are user/operator responsibility.

Codex may run compile, unit, schema, read-only validation, and short regression unless the user instructs otherwise.

User ladder:

`10BD -> 20BD -> 60BD -> 200BD -> 252BD`

Each gate requires its entry condition; do not run historical tests mechanically.

## Do Not Start Performance Tuning

Phase26 is repair, retirement, conformance, and readiness restoration.

Phase27 evaluates repair effects without Strategy changes.

Strategy Improvement is a Phase28-or-later candidate.

