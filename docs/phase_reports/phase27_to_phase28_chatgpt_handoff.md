# Phase27 to Phase28 ChatGPT Handoff

## Role

Use this handoff to start Phase28. Do not implement before reading the required documents below and confirming Phase28-A scope.

## Phase27 Closed

```text
Primary Judgment: PHASE27_CLOSED_WITH_FIRST_PERFORMANCE_EXPERIMENT_ADOPTED_PHASE28_READY
Final Status: CLOSED_WITH_ADOPTED_PERFORMANCE_IMPROVEMENT_AND_KNOWN_COMPARABILITY_LIMITATIONS
D6-D Adoption: APPROVED_WITH_LIMITATIONS
Phase28 Entry: APPROVED
```

## Required Reading Order

1. `docs/phase_reports/phase27_to_phase28_chatgpt_handoff.md`
2. `docs/phase_reports/phase27_final_summary_and_phase28_handoff.md`
3. `docs/phase_reports/phase27_d6e_d6d_100bd_before_after_causal_attribution_and_adoption_review.md`
4. `docs/02_architecture/strategy_architecture_v1.md`
5. `docs/02_architecture/momentum_follow_position_lifecycle_and_canonical_decision_architecture.md`
6. `docs/02_architecture/position_management_decision_trace_contract.md`
7. `docs/02_architecture/portfolio_construction_and_position_sizing_contract.md`
8. `docs/02_architecture/runtime_architecture_v2.md`
9. `docs/phase_reports/phase27_a9_canonical_buy_add_authority_unification_and_legacy_consumer_disposition_design_review.md`
10. `docs/phase_reports/phase27_d6a_pm_implementation_gap_audit.md`
11. `docs/01_requirements/phase_roadmap.md`

## Phase28 First Task

```text
Phase28-A ADD Baseline and Incremental Investment Evidence Audit
```

Phase28-A is read-only. It must audit current ADD decisions, ADD outcomes, ADD execution, ADD zero-delta causes, Rank1 existing positions, ADD quantity, concentration, capital use, and ADD-after HOLD/EXIT behavior.

## Non-negotiable Rules

- Do not add new Action Authority.
- Do not change HOLD / EXIT philosophy in Phase28-A.
- Do not change BUY_NEW, ADD, Sizing, Runtime Planning, Pending, Submit, Safety, Execution, Model, Training, or Calibration in Phase28-A.
- Do not run fresh-run, resume, 100BD, 1-year, or long Historical tests from Codex.
- Missing metrics must not be zero-filled.
- Performance result is post-hoc attribution and never Strategy input.

## Phase28 Goal

Move from:

```text
winning positions are held correctly
```

to:

```text
additional capital is allocated correctly to winning positions only when incremental portfolio Expected Value improves
```
