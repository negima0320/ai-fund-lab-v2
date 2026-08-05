# Phase27-D1 Momentum Follow Position Lifecycle and Canonical Decision Architecture Design

## 1. Scope

Phase27-D1 produced the formal design SoT for Momentum Follow / Momentum Rotation position lifecycle and canonical decision architecture.

This was documentation-only work.

```text
Implementation Change: false
Runtime Change: false
Strategy Logic Change: false
Historical Execution: PROHIBITED_NOT_EXECUTED
```

## 2. Primary Judgment

```text
PHASE27_D1_MOMENTUM_FOLLOW_CANONICAL_DECISION_DESIGN_COMPLETE_WITH_OPEN_GATES
```

The design is complete, but implementation entry is step-gated because BUY_ADD architecture repair must be proven before performance logic, momentum thresholds, or incremental eligibility thresholds are changed.

## 3. Supporting Judgments

```json
{
  "investment_philosophy": "FROZEN",
  "buy_add_architecture_repair": "DESIGN_READY",
  "canonical_position_decision": "DESIGN_READY",
  "momentum_continuation": "FOUNDATION_READY",
  "incremental_investment_eligibility": "REQUIRES_CALIBRATION",
  "implementation_entry": "STEP_GATED"
}
```

## 4. Evidence Reflected

- No forced BUY count observed.
- No fixed slot-fill behavior observed.
- No forced cash deployment observed.
- No-BUY and cash retention are valid Strategy results.
- Clear disregard of stronger executable candidates was not observed.
- Re-entry losses were material, but Re-entry alone was not proven as root cause.
- Higher-ranked candidate dropout was dominated by existing-holding zero-delta cases.
- 7 of 25 BUYs were WEAK or RELATIVE_ONLY under incremental eligibility diagnosis.
- BUY Quality is allocation eligibility/scaling authority, not explicit BUY-versus-cash authority.
- PM emitted ADD/HOLD/REDUCE/EXIT, including 145 ADD decisions.
- Executable BUY_ADD was not observed.
- Runtime PM ADD did not resolve into canonical Portfolio Construction in the observed run.
- Legacy add_consumer/sell_pipeline ADD path remains active.
- Canonical BUY_ADD authority and legacy ADD authority are split.

## 5. Design Decisions

- Investment style is frozen as Momentum Follow / Momentum Rotation.
- Long-term annual return target is +50%, with aggressive/high-risk capital posture for 1,000,000 JPY starting capital.
- Profit alone is not an EXIT reason.
- Fast loss control remains required.
- Cash is residual and no fixed cash ratio target is introduced.
- BUY_NEW, ADD, HOLD, REDUCE, EXIT, and NO_ACTION are formalized.
- HOLD is active Strategy/PM intent; NO_ACTION is execution result.
- PM ADD is not a BUY order.
- BUY_ADD must pass PM -> Canonical Position Decision -> Portfolio Construction -> Position Sizing -> Runtime Planning -> Formal Planning -> Pending -> Approval -> Submit.
- Legacy add_consumer/sell_pipeline ADD is recommended for retirement, with a compatibility non-decision bridge during migration.
- Incremental Investment Eligibility is separated from BUY Quality and relative ranking.
- Momentum Continuation is introduced as PIT-only foundation, initially shadow.
- Production, Demo, and Historical must share the same implementation contract.

## 6. Deliverables

Main design document:

```text
docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md
```

Common SoT amendments:

- `docs/02_architecture/strategy_architecture_v1.md`
- `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/adaptive_buy_quality_authority.md`

Machine-readable outputs:

- reports/phase27_d1_momentum_follow_position_lifecycle_and_canonical_decision_architecture_design/summary.json
- reports/phase27_d1_momentum_follow_position_lifecycle_and_canonical_decision_architecture_design/investment_philosophy.json
- reports/phase27_d1_momentum_follow_position_lifecycle_and_canonical_decision_architecture_design/position_lifecycle_contract.json
- reports/phase27_d1_momentum_follow_position_lifecycle_and_canonical_decision_architecture_design/canonical_position_decision_schema.json
- reports/phase27_d1_momentum_follow_position_lifecycle_and_canonical_decision_architecture_design/decision_authority_matrix.json
- reports/phase27_d1_momentum_follow_position_lifecycle_and_canonical_decision_architecture_design/buy_add_repair_design.json
- reports/phase27_d1_momentum_follow_position_lifecycle_and_canonical_decision_architecture_design/legacy_add_disposition.json
- reports/phase27_d1_momentum_follow_position_lifecycle_and_canonical_decision_architecture_design/momentum_continuation_contract.json
- reports/phase27_d1_momentum_follow_position_lifecycle_and_canonical_decision_architecture_design/incremental_investment_eligibility_contract.json
- reports/phase27_d1_momentum_follow_position_lifecycle_and_canonical_decision_architecture_design/portfolio_construction_contract.json
- reports/phase27_d1_momentum_follow_position_lifecycle_and_canonical_decision_architecture_design/position_sizing_contract.json
- reports/phase27_d1_momentum_follow_position_lifecycle_and_canonical_decision_architecture_design/cash_no_buy_contract.json
- reports/phase27_d1_momentum_follow_position_lifecycle_and_canonical_decision_architecture_design/reentry_whipsaw_boundary.json
- reports/phase27_d1_momentum_follow_position_lifecycle_and_canonical_decision_architecture_design/observability_requirements.json
- reports/phase27_d1_momentum_follow_position_lifecycle_and_canonical_decision_architecture_design/implementation_workstreams.json
- reports/phase27_d1_momentum_follow_position_lifecycle_and_canonical_decision_architecture_design/implementation_sequence.json
- reports/phase27_d1_momentum_follow_position_lifecycle_and_canonical_decision_architecture_design/testing_validation_plan.json
- reports/phase27_d1_momentum_follow_position_lifecycle_and_canonical_decision_architecture_design/controlled_experiment_contract.json
- reports/phase27_d1_momentum_follow_position_lifecycle_and_canonical_decision_architecture_design/degression_prevention_contract.json
- reports/phase27_d1_momentum_follow_position_lifecycle_and_canonical_decision_architecture_design/open_questions.json
- reports/phase27_d1_momentum_follow_position_lifecycle_and_canonical_decision_architecture_design/test_results.json

## 7. Open Gates

- Implement BUY_ADD authority repair before performance experiments.
- Prove canonical BUY_ADD contract with targeted tests before long historical tests.
- Introduce momentum continuation foundation in shadow mode before granting decision authority.
- Calibrate incremental investment eligibility via controlled experiments.
- User, not Codex, runs 10BD/100BD/1-year/long historical validations.

## 8. Validation

Only documentation generation and JSON load validation are in scope for this task. Fresh-run, resume, Historical, 10BD, 100BD, and long regression were not executed.
