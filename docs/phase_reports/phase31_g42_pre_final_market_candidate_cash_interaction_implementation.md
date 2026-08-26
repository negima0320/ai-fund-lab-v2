# Phase31-G42 - Pre-Final Market x Candidate x Cash Interaction Implementation

## Scope

Task type: IMPLEMENTATION - CAPITAL COMPETITION AUTHORITY MIGRATION.

G42 implements the G39 Slice G42 pre-final interaction path in Portfolio
Construction. It moves Market Quality / Risk Pacing / Opportunity Quality /
Cash interaction ahead of final semantic capital winner output, while preserving
the authority boundaries established by G38-G41.

Changed files:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `tests/strategy/test_phase31_g42_market_candidate_cash_interaction.py`
- `tests/strategy/test_phase22_e_portfolio_construction.py`
- `docs/phase_reports/phase31_g42_pre_final_market_candidate_cash_interaction_implementation.md`

G42 did not change Position Sizing, PM / SELL, BUY eligibility, Safety,
Runtime capital re-decision, configuration, thresholds, parameters, fixtures,
fresh-run, resume, replay, Historical rerun, or long Historical.

## Inputs Read

- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/phase_reports/phase31_g37_risk_pacing_binding_candidate_comparison_effectiveness_root_cause_audit.md`
- `docs/phase_reports/phase31_g38_economically_binding_risk_pacing_market_candidate_cash_interaction_architecture_refinement.md`
- `docs/phase_reports/phase31_g39_opportunity_quality_true_cash_competition_implementation_planning.md`
- `docs/phase_reports/phase31_g40_opportunity_quality_producer_reachable_continuum_implementation.md`
- `docs/phase_reports/phase31_g41_true_cash_competitor_evidence_framework_implementation.md`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- `src/ai_fund_lab_v2/strategy/portfolio_policy.py`
- `src/ai_fund_lab_v2/strategy/market_context.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`

## Primary Judgment

`PHASE31_G42_PRE_FINAL_MARKET_CANDIDATE_CASH_INTERACTION_IMPLEMENTED_ACCEPTED`

Portfolio Construction now materializes `market_candidate_cash_interaction.v1`
after authoritative Risk Pacing, canonical Opportunity Quality, and canonical
Cash evidence are available, and before publishing the final semantic capital
competition winner. The previous late Risk Pacing target-weight mutation path
is demoted to compatibility evidence only and no longer independently changes
member target weights.

G42 is an authority/order migration with limited possible economic behavior
change. It does not fully activate the G43 CAUTIOUS / GRADUAL / PRESERVE
binding matrix.

## Pre-G42 Decision Order Inventory

Pre-G42 order:

```text
candidate eligibility / quality evidence
-> legacy marginal class compatibility
-> target / selection / accepted weight
-> late Risk Pacing competitor decision
-> Cash residual evidence
-> lot feasibility / reconsideration evidence
-> final no-deployable / winner evidence
```

G37 defect confirmed:

`PRE_G42_RISK_PACING_APPLICATION_STAGE = AFTER_SELECTION_TOO_LATE`

The late Risk Pacing path could zero a target after selection, but it could not
participate in candidate-vs-cash scoring before the security winner was formed.

## Implementation Summary

G42 adds one canonical interaction stage:

```text
market_candidate_cash_interaction.v1
```

The stage consumes:

- Risk Pacing evidence from Portfolio Policy,
- Market Quality lineage through Risk Pacing component evidence,
- canonical Opportunity Quality from `MARGINAL_CAPITAL_VALUE_AUTHORITY`,
- canonical Cash competitor evidence from Portfolio Construction,
- ADD competitor evidence already present in PC,
- re-entry admitted candidate fields as ordinary NEW_BUY competitor context,
- current portfolio / accepted-weight context.

It does not recompute Market Quality, Risk Pacing, Opportunity Quality, alpha,
or discrete quantity. Position Sizing remains the quantity authority.

Implemented interaction result classes:

- `DEPLOY_ELIGIBLE`
- `SELECTIVE_COMPETITION`
- `CASH_PREFERRED`
- `FAIL_CLOSED`
- `BLOCKED`

The root capital competition evidence now exposes:

- `market_candidate_cash_interaction`
- `capital_competition_winner_type`
- `capital_competition_winner_symbol`
- `capital_competition_winner_reason_codes`
- `defeated_competitor_summary`

## Late Risk Pacing Demotion

`_apply_authoritative_risk_pacing_to_members` now preserves
`risk_pacing_competition_decision` as compatibility evidence and records:

- `compatibility_evidence_only = True`
- `late_decision_authority_active = False`
- `legacy_late_risk_pacing_decision_authority_count = 0`

It no longer zeroes `target_weight`, `accepted_incremental_weight`,
`accepted_buy_new_weight`, or lot-aware accepted weights. The canonical pre-final
interaction is the place where Risk Pacing evidence can affect semantic capital
winner output.

## Acceptance Matrix

| Requirement | Result |
| --- | --- |
| `PRE_G42_DECISION_ORDER_INVENTORY_COMPLETE` | YES |
| `PRE_G42_RISK_PACING_APPLICATION_STAGE` | AFTER_SELECTION_TOO_LATE |
| `CANONICAL_PRE_FINAL_INTERACTION_IMPLEMENTED` | YES |
| `MARKET_CANDIDATE_INTERACTION_STAGE` | BEFORE_FINAL_CAPITAL_WINNER |
| `INTERACTION_CONSUMES_AUTHORITATIVE_EVIDENCE_ONLY` | YES |
| `CANONICAL_COMPETITOR_SET_IMPLEMENTED` | YES |
| `CASH_PRESENT_BEFORE_SECURITY_WINNER` | YES |
| `CANONICAL_OPPORTUNITY_QUALITY_USED_BY_INTERACTION` | YES |
| `LEGACY_MARGINAL_CLASS_USED_AS_INTERACTION_AUTHORITY` | NO |
| `CANONICAL_INTERACTION_RESULT_CLASSES_IMPLEMENTED` | YES |
| `NORMAL_STRONG_SECURITY_DEPLOYMENT_PRESERVED` | YES |
| `NORMAL_COMPARABLE_MARGINAL_DEPLOYMENT_PRESERVED` | YES |
| `NORMAL_WEAK_VALID_NOT_HARD_BLOCKED` | YES |
| `INSUFFICIENT_INCREMENTAL_DEPLOYMENT_FAIL_CLOSED` | YES |
| `BLOCKED_CANNOT_WIN` | YES |
| `CASH_ONLY_AFTER_SECURITY_FAILURE` | NO |
| `CASH_IS_PRE_FINAL_COMPETITOR` | YES |
| `PRE_INTERACTION_SECURITY_WINNER_LOCKED` | NO |
| `PRE_RISK_PACING_DECISION_IRREVERSIBILITY` | NO |
| `MULTI_COMPETITOR_PRE_FINAL_INTERACTION` | YES |
| `ADD_INCLUDED_IN_PRE_FINAL_INTERACTION` | YES |
| `NEW_BUY_INCLUDED_IN_PRE_FINAL_INTERACTION` | YES |
| `REENTRY_SEPARATE_INTERACTION_RULE_CREATED` | NO |
| `CANONICAL_FINAL_CAPITAL_WINNER_OUTPUT_IMPLEMENTED` | YES |
| `SECOND_CAPITAL_WINNER_AUTHORITY_COUNT` | 0 |
| `POSITION_SIZING_AUTHORITY_CHANGED` | NO |
| `POSITION_SIZING_QUANTITY_RECOMPUTED_BY_PC` | NO |
| `PM_SELL_SEMANTICS_CHANGED` | NO |
| `BUY_ELIGIBILITY_SEMANTICS_CHANGED` | NO |
| `SAFETY_AUTHORITY_CHANGED` | NO |
| `RUNTIME_CAPITAL_REDECISION_CREATED` | NO |
| `MARKET_QUALITY_RECOMPUTED_IN_PC` | NO |
| `RISK_PACING_RECOMPUTED_IN_PC` | NO |
| `OPPORTUNITY_QUALITY_RECOMPUTED_IN_PC` | NO |
| `G42_PRODUCTION_BEHAVIOR_CHANGE_CLASS` | LIMITED_DECISION_CHANGE |
| `FULL_RISK_PACING_BINDING_MATRIX_ACTIVATED` | NO |
| `G43_REQUIRED` | YES |
| `NORMAL_REACHABILITY_PROVEN` | YES |
| `CASH_WINNER_REACHABILITY_PROVEN` | YES |
| `ADD_NEW_BUY_CASH_REACHABILITY_PROVEN` | YES |
| `FUTURE_INPUT_COUNT` | 0 |
| `HISTORICAL_OUTCOME_INPUT_COUNT` | 0 |
| `PAPER_LEDGER_INPUT_COUNT` | 0 |
| `AUDIT_RESULT_INPUT_COUNT` | 0 |
| `MFE_MAE_INPUT_COUNT` | 0 |
| `OUTCOME_DERIVED_DECISION_RULE_COUNT` | 0 |
| `STRATEGY_INTERACTION_LINEAGE_IMPLEMENTED` | YES |
| `LEGACY_LATE_RISK_PACING_DECISION_AUTHORITY_COUNT` | 0 |
| `LEGACY_CASH_WINNER_OVERRIDE_COUNT` | 0 |
| `LEGACY_CLASS_CAN_CHANGE_CANONICAL_WINNER` | NO |

## Defect Progress

`G37_AFTER_SELECTION_TOO_LATE_DEFECT_ADDRESSED = YES`

`CASH_AS_RESIDUAL_ONLY_DEFECT_ADDRESSED = YES`

`COMPARABLE_AND_STRONG_COMPLETE_G43_BINDING = NO`

`G42_AUTHORITY_MIGRATION_COMPLETE = YES`

G42 removes the irreversible late target mutation surface and establishes the
pre-final competitor set. Full CAUTIOUS / GRADUAL / PRESERVE semantic tuning is
left to G43.

## Validation

Focused tests:

```text
python3 -m pytest tests/strategy/test_phase31_g42_market_candidate_cash_interaction.py
```

Result:

```text
6 passed
```

Focused regression:

```text
python3 -m pytest tests/strategy/test_phase31_g42_market_candidate_cash_interaction.py tests/strategy/test_phase31_g41_cash_competitor_evidence.py tests/strategy/test_phase31_g40_opportunity_quality_continuum.py tests/strategy/test_phase31_b4_marginal_capital_value_shadow.py tests/strategy/test_phase31_b6_marginal_capital_shadow_bridge.py tests/strategy/test_phase31_b8_pending_cash_causality_bridge.py tests/strategy/test_phase31_b10_alternative_c_marginal_capital_priority.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_c_portfolio_policy.py tests/strategy/test_phase22_l_market_context_resolution.py tests/strategy/test_phase30_j_strategy_intelligence.py tests/strategy/test_phase31_g4_pm_severity_persistence.py tests/strategy/test_phase31_g8_pm_severity_action_mapping.py tests/strategy/test_phase22_j_position_sizing.py -k 'not real'
```

Result:

```text
306 passed, 9 deselected
```

Python compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py tests/strategy/test_phase31_g42_market_candidate_cash_interaction.py
```

Result:

```text
PASS
```

Diff hygiene:

```text
git diff --check -- src/ai_fund_lab_v2/strategy/portfolio_construction.py tests/strategy/test_phase31_g42_market_candidate_cash_interaction.py tests/strategy/test_phase22_e_portfolio_construction.py docs/phase_reports/phase31_g42_pre_final_market_candidate_cash_interaction_implementation.md
```

Result:

```text
PASS
```

## Required Output

`PRIMARY_JUDGMENT = PHASE31_G42_PRE_FINAL_MARKET_CANDIDATE_CASH_INTERACTION_IMPLEMENTED_ACCEPTED`

`PRE_G42_DECISION_ORDER_INVENTORY_COMPLETE = YES`

`PRE_G42_RISK_PACING_APPLICATION_STAGE = AFTER_SELECTION_TOO_LATE`

`CANONICAL_PRE_FINAL_INTERACTION_IMPLEMENTED = YES`

`MARKET_CANDIDATE_INTERACTION_STAGE = BEFORE_FINAL_CAPITAL_WINNER`

`INTERACTION_CONSUMES_AUTHORITATIVE_EVIDENCE_ONLY = YES`

`CANONICAL_COMPETITOR_SET_IMPLEMENTED = YES`

`CASH_PRESENT_BEFORE_SECURITY_WINNER = YES`

`CANONICAL_OPPORTUNITY_QUALITY_USED_BY_INTERACTION = YES`

`LEGACY_MARGINAL_CLASS_USED_AS_INTERACTION_AUTHORITY = NO`

`CANONICAL_INTERACTION_RESULT_CLASSES_IMPLEMENTED = YES`

`NORMAL_STRONG_SECURITY_DEPLOYMENT_PRESERVED = YES`

`NORMAL_COMPARABLE_MARGINAL_DEPLOYMENT_PRESERVED = YES`

`INSUFFICIENT_INCREMENTAL_DEPLOYMENT_FAIL_CLOSED = YES`

`BLOCKED_CANNOT_WIN = YES`

`CASH_IS_PRE_FINAL_COMPETITOR = YES`

`MULTI_COMPETITOR_PRE_FINAL_INTERACTION = YES`

`CANONICAL_FINAL_CAPITAL_WINNER_OUTPUT_IMPLEMENTED = YES`

`SECOND_CAPITAL_WINNER_AUTHORITY_COUNT = 0`

`G42_PRODUCTION_BEHAVIOR_CHANGE_CLASS = LIMITED_DECISION_CHANGE`

`FULL_RISK_PACING_BINDING_MATRIX_ACTIVATED = NO`

`G43_REQUIRED = YES`

`FUTURE_INPUT_COUNT = 0`

`HISTORICAL_OUTCOME_INPUT_COUNT = 0`

`PAPER_LEDGER_INPUT_COUNT = 0`

`AUDIT_RESULT_INPUT_COUNT = 0`

`MFE_MAE_INPUT_COUNT = 0`

`OUTCOME_DERIVED_DECISION_RULE_COUNT = 0`

`LEGACY_LATE_RISK_PACING_DECISION_AUTHORITY_COUNT = 0`

`LEGACY_CASH_WINNER_OVERRIDE_COUNT = 0`

`LEGACY_CLASS_CAN_CHANGE_CANONICAL_WINNER = NO`

`FOCUSED_TEST_RESULTS = PASS`

`PY_COMPILE = PASS`

`GIT_DIFF_CHECK = PASS`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`REPLAY_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

## Next Task Recommendation

Proceed to G43 to define and activate the full CAUTIOUS / GRADUAL / PRESERVE
binding matrix over the now-canonical pre-final Market x Candidate x Cash
interaction path.
