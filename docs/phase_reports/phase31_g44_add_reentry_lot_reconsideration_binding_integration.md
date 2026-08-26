# Phase31-G44 - ADD / Re-entry / Lot Reconsideration Binding Integration

## Scope

Task type: IMPLEMENTATION + AUTHORITY INTEGRATION.

G44 completes the non-NEW_BUY integration of the G40-G43 refined capital
competition architecture for:

- ADD,
- eligible re-entry,
- lot infeasibility reconsideration,
- residual capital / Cash fallback.

Changed files:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py`
- `docs/phase_reports/phase31_g44_add_reentry_lot_reconsideration_binding_integration.md`

No Position Sizing authority, PM SELL / REDUCE / EXIT semantics, Safety
authority, Runtime capital re-decision, config, threshold, parameter, fixture,
fresh-run, resume, replay, Historical rerun, or long Historical change was
made.

No new permanent architecture rule beyond G38-G43 was required.

## Inputs Read

- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/phase_reports/phase31_g38_economically_binding_risk_pacing_market_candidate_cash_interaction_architecture_refinement.md`
- `docs/phase_reports/phase31_g39_opportunity_quality_true_cash_competition_implementation_planning.md`
- `docs/phase_reports/phase31_g40_opportunity_quality_producer_reachable_continuum_implementation.md`
- `docs/phase_reports/phase31_g41_true_cash_competitor_evidence_framework_implementation.md`
- `docs/phase_reports/phase31_g42_pre_final_market_candidate_cash_interaction_implementation.md`
- `docs/phase_reports/phase31_g43_risk_pacing_economic_binding_activation.md`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- `src/ai_fund_lab_v2/strategy/position_management.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`

## Primary Judgment

`PHASE31_G44_ADD_REENTRY_LOT_BINDING_INTEGRATION_IMPLEMENTED_ACCEPTED`

ADD and eligible re-entry already use the G43 binding interaction as ADD and
NEW_BUY competitors respectively. G44 extends lot-aware final reallocation so
that, when authoritative Risk Pacing evidence is provided, candidate ordering
and skipped candidate evidence are bound to the same G43 interaction result
before lot acceptance. Cash remains present during reconsideration and can win
instead of forcing a second security deployment.

## Implementation Summary

`apply_lot_aware_final_reallocation` now accepts optional
`risk_pacing_evidence`. When provided:

- pre-lot `build_capital_competition_framework` materializes the canonical G43
  Market x Candidate x Cash interaction;
- lot candidate ordering consumes each candidate's `interaction_result`;
- `CASH_PREFERRED`, `FAIL_CLOSED`, and `BLOCKED` candidates are skipped with
  canonical G43 binding reason evidence;
- final lot evidence materializes
  `lot_reconsideration_binding_integration`;
- final capital competition is rebuilt with the same Risk Pacing evidence.

Existing calls without Risk Pacing evidence keep backward-compatible behavior.

## Path Inventories

ADD path:

```text
PM ADD intent
-> ADD worthiness / expected-edge / incremental value / opportunity cost
-> MARGINAL_CAPITAL_VALUE_AUTHORITY canonical Opportunity Quality
-> Portfolio Construction ADD competitor
-> G43 Market x Candidate x Cash interaction
-> final semantic capital winner
-> Position Sizing quantity
-> lot reconsideration if sizing evidence blocks execution
```

Re-entry path:

```text
prior exit context
-> PC re-entry semantic eligibility
-> renewed current evidence / BUY_NEW admission
-> standard BUY_NEW Opportunity Quality
-> G43 Market x Candidate x Cash interaction
-> final semantic capital winner
-> Position Sizing quantity
```

Lot reconsideration path:

```text
canonical security winner
-> Position Sizing canonical sizing evidence
-> PC-owned reconsideration
-> remaining NEW_BUY / ADD / Cash competitor set
-> same G43 binding matrix
-> final semantic winner or Cash
```

## Acceptance Results

| Requirement | Result |
| --- | --- |
| `ADD_END_TO_END_PATH_INVENTORY_COMPLETE` | YES |
| `PM_REMAINS_ADD_INTENT_OWNER` | YES |
| `PC_CREATES_ADD_INTENT` | NO |
| `ADD_CANONICAL_OPPORTUNITY_QUALITY_REQUIRED` | YES |
| `LEGACY_ADD_CLASS_USED_AS_BINDING_AUTHORITY` | NO |
| `ADD_USES_G43_BINDING_MATRIX` | YES |
| `STRONG_ADD_CAN_WIN_NORMAL` | YES |
| `STRONG_ADD_CAN_WIN_GRADUAL` | YES |
| `STRONG_ADD_CAN_WIN_CAUTIOUS` | YES_WITH_CANONICAL_SELECTIVE_RULES |
| `PRESERVE_STRONG_ADD_EXCEPTION_PATH` | YES |
| `MARGINAL_ADD_CAN_LOSE_TO_CASH_UNDER_GRADUAL` | YES |
| `MARGINAL_ADD_CAN_LOSE_TO_CASH_UNDER_CAUTIOUS` | YES |
| `WEAK_VALID_ADD_CAN_LOSE_TO_CASH` | YES |
| `ADD_AUTOMATIC_PRIORITY` | NO |
| `NEW_BUY_AUTOMATIC_PRIORITY` | NO |
| `ADD_NEW_BUY_CASH_TRUE_COMPETITION` | YES |
| `ADD_EXISTING_VALUE_EVIDENCE_REUSED` | YES |
| `NEW_ADD_ALPHA_FEATURE_CREATED` | NO |
| `REENTRY_END_TO_END_PATH_INVENTORY_COMPLETE` | YES |
| `REENTRY_ELIGIBILITY_OWNER_UNCHANGED` | YES |
| `REENTRY_ELIGIBILITY_DIRECTLY_ALLOCATES_CAPITAL` | NO |
| `REENTRY_USES_STANDARD_BUY_NEW_OPPORTUNITY_QUALITY` | YES |
| `REENTRY_USES_G43_BINDING_MATRIX` | YES |
| `REENTRY_AUTOMATIC_PRIORITY` | NO |
| `REENTRY_PERMANENT_PENALTY` | NO |
| `REENTRY_SPECIAL_CASH_RULE` | NO |
| `REENTRY_MARKET_SENSITIVITY_PROVEN` | YES |
| `POSITION_SIZING_REMAINS_QUANTITY_OWNER` | YES |
| `PC_RECOMPUTES_QUANTITY` | NO |
| `RISK_PACING_DIRECTLY_SETS_QUANTITY` | NO |
| `ZERO_QUANTITY_CANONICAL_REASON_REQUIRED` | YES |
| `UNEXPLAINED_ZERO_QUANTITY_FAIL_CLOSED` | YES |
| `PC_OWNS_LOT_RECONSIDERATION` | YES |
| `POSITION_SIZING_OWNS_RECONSIDERATION` | NO |
| `LOT_RECONSIDERATION_REUSES_G43_BINDING_MATRIX` | YES |
| `LEGACY_RESIDUAL_REALLOCATION_BYPASSES_BINDING_MATRIX` | NO |
| `CASH_PRESENT_DURING_LOT_RECONSIDERATION` | YES |
| `LOT_RECONSIDERATION_FORCES_SECURITY_DEPLOYMENT` | NO |
| `RECONSIDERATION_USES_ONLY_CURRENT_PIT_EVIDENCE` | YES |
| `RECONSIDERATION_WINNER_OWNER` | PORTFOLIO_CONSTRUCTION |
| `SECOND_RECONSIDERATION_AUTHORITY_COUNT` | 0 |
| `SECOND_DISCRETE_QUANTITY_ENGINE_CREATED` | NO |
| `FINAL_NO_DEPLOYABLE_OWNER` | PORTFOLIO_CONSTRUCTION |
| `FINAL_NO_DEPLOYABLE_PREMATURE_DECLARATION` | NO |
| `CASH_WIN_REASON_LINEAGE_COMPLETE` | YES |
| `G44_FORCES_EXISTING_POSITION_EXIT` | NO |
| `SELL_REDUCE_EXIT_SEMANTICS_CHANGED` | NO |
| `BUY_SELL_INDEPENDENCE_PRESERVED` | YES |
| `SAFETY_AUTHORITY_CHANGED` | NO |
| `MARKET_QUALITY_RECOMPUTED_OUTSIDE_OWNER` | NO |
| `RISK_PACING_RECOMPUTED_OUTSIDE_OWNER` | NO |
| `OPPORTUNITY_QUALITY_RECOMPUTED_OUTSIDE_MCV_AUTHORITY` | NO |
| `FUTURE_INPUT_COUNT` | 0 |
| `HISTORICAL_OUTCOME_INPUT_COUNT` | 0 |
| `PAPER_LEDGER_INPUT_COUNT` | 0 |
| `AUDIT_RESULT_INPUT_COUNT` | 0 |
| `MFE_MAE_INPUT_COUNT` | 0 |
| `G44_ADD_BINDING_TESTS` | PASS |
| `G44_REENTRY_BINDING_TESTS` | PASS |
| `G44_LOT_RECONSIDERATION_TESTS` | PASS |
| `PHASE28_29_LOT_REPAIR_REGRESSION` | NO |
| `G26_REENTRY_SEMANTIC_REGRESSION` | NO |
| `G27_ADD_CAPITAL_COMPETITION_REGRESSION` | NO |
| `G43_BINDING_MATRIX_BYPASS_COUNT` | 0 |
| `ADD_BINDING_INTEGRATION_COMPLETE` | YES |
| `REENTRY_BINDING_INTEGRATION_COMPLETE` | YES |
| `LOT_RECONSIDERATION_BINDING_INTEGRATION_COMPLETE` | YES |
| `RESIDUAL_CAPITAL_BINDING_BYPASS_COUNT` | 0 |
| `G44_PRODUCTION_BEHAVIOR_CHANGE_CLASS` | AUTHORITATIVE_DECISION_CHANGE |

## Synthetic Acceptance

Implemented in
`tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py`.

Covered mandatory cases:

- CAUTIOUS + STRONG ADD -> ADD can win.
- CAUTIOUS + MARGINAL ADD -> Cash wins.
- GRADUAL + COMPARABLE_HIGH ADD -> ADD selective.
- GRADUAL + MARGINAL ADD -> Cash wins.
- ADD vs stronger NEW_BUY -> NEW_BUY wins.
- strong ADD vs marginal NEW_BUY -> ADD wins.
- both marginal under CAUTIOUS -> Cash wins.
- eligible re-entry + NORMAL + valid opportunity -> deploys.
- same marginal re-entry + CAUTIOUS -> Cash wins.
- blocked re-entry evidence is blocked in the binding result.
- security A wins pre-lot -> lot infeasible -> security B wins.
- security A wins pre-lot -> lot infeasible -> Cash wins.
- ADD wins pre-lot -> lot infeasible -> NEW_BUY wins.
- ADD wins pre-lot -> lot infeasible -> Cash wins.
- no unexplained zero quantity and no second quantity authority.

## Validation

Focused G44 tests:

```text
python3 -m pytest tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py
```

Result:

```text
6 passed
```

Focused regression:

```text
python3 -m pytest tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py tests/strategy/test_phase31_g43_risk_pacing_economic_binding.py tests/strategy/test_phase31_g42_market_candidate_cash_interaction.py tests/strategy/test_phase31_g41_cash_competitor_evidence.py tests/strategy/test_phase31_g40_opportunity_quality_continuum.py tests/strategy/test_phase31_b4_marginal_capital_value_shadow.py tests/strategy/test_phase31_b6_marginal_capital_shadow_bridge.py tests/strategy/test_phase31_b8_pending_cash_causality_bridge.py tests/strategy/test_phase31_b10_alternative_c_marginal_capital_priority.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_c_portfolio_policy.py tests/strategy/test_phase22_l_market_context_resolution.py tests/strategy/test_phase30_j_strategy_intelligence.py tests/strategy/test_phase31_g4_pm_severity_persistence.py tests/strategy/test_phase31_g8_pm_severity_action_mapping.py tests/strategy/test_phase22_j_position_sizing.py -k 'not real'
```

Result:

```text
322 passed, 9 deselected
```

Python compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py
```

Result:

```text
PASS
```

Diff hygiene:

```text
git diff --check -- src/ai_fund_lab_v2/strategy/portfolio_construction.py tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py
```

Result:

```text
PASS
```

## Required Summary Output

`PRIMARY_JUDGMENT = PHASE31_G44_ADD_REENTRY_LOT_BINDING_INTEGRATION_IMPLEMENTED_ACCEPTED`

`ADD_END_TO_END_PATH_INVENTORY_COMPLETE = YES`

`PM_REMAINS_ADD_INTENT_OWNER = YES`

`PC_CREATES_ADD_INTENT = NO`

`ADD_CANONICAL_OPPORTUNITY_QUALITY_REQUIRED = YES`

`LEGACY_ADD_CLASS_USED_AS_BINDING_AUTHORITY = NO`

`ADD_USES_G43_BINDING_MATRIX = YES`

`STRONG_ADD_CAN_WIN_NORMAL = YES`

`STRONG_ADD_CAN_WIN_GRADUAL = YES`

`STRONG_ADD_CAN_WIN_CAUTIOUS = YES_WITH_CANONICAL_SELECTIVE_RULES`

`PRESERVE_STRONG_ADD_EXCEPTION_PATH = YES`

`MARGINAL_ADD_CAN_LOSE_TO_CASH_UNDER_GRADUAL = YES`

`MARGINAL_ADD_CAN_LOSE_TO_CASH_UNDER_CAUTIOUS = YES`

`WEAK_VALID_ADD_CAN_LOSE_TO_CASH = YES`

`ADD_AUTOMATIC_PRIORITY = NO`

`NEW_BUY_AUTOMATIC_PRIORITY = NO`

`ADD_NEW_BUY_CASH_TRUE_COMPETITION = YES`

`ADD_EXISTING_VALUE_EVIDENCE_REUSED = YES`

`NEW_ADD_ALPHA_FEATURE_CREATED = NO`

`REENTRY_END_TO_END_PATH_INVENTORY_COMPLETE = YES`

`REENTRY_ELIGIBILITY_OWNER_UNCHANGED = YES`

`REENTRY_ELIGIBILITY_DIRECTLY_ALLOCATES_CAPITAL = NO`

`REENTRY_USES_STANDARD_BUY_NEW_OPPORTUNITY_QUALITY = YES`

`REENTRY_USES_G43_BINDING_MATRIX = YES`

`REENTRY_AUTOMATIC_PRIORITY = NO`

`REENTRY_PERMANENT_PENALTY = NO`

`REENTRY_SPECIAL_CASH_RULE = NO`

`REENTRY_MARKET_SENSITIVITY_PROVEN = YES`

`POSITION_SIZING_REMAINS_QUANTITY_OWNER = YES`

`PC_RECOMPUTES_QUANTITY = NO`

`RISK_PACING_DIRECTLY_SETS_QUANTITY = NO`

`ZERO_QUANTITY_CANONICAL_REASON_REQUIRED = YES`

`UNEXPLAINED_ZERO_QUANTITY_FAIL_CLOSED = YES`

`PC_OWNS_LOT_RECONSIDERATION = YES`

`POSITION_SIZING_OWNS_RECONSIDERATION = NO`

`LOT_RECONSIDERATION_REUSES_G43_BINDING_MATRIX = YES`

`LEGACY_RESIDUAL_REALLOCATION_BYPASSES_BINDING_MATRIX = NO`

`CASH_PRESENT_DURING_LOT_RECONSIDERATION = YES`

`LOT_RECONSIDERATION_FORCES_SECURITY_DEPLOYMENT = NO`

`RECONSIDERATION_USES_ONLY_CURRENT_PIT_EVIDENCE = YES`

`RECONSIDERATION_WINNER_OWNER = PORTFOLIO_CONSTRUCTION`

`SECOND_RECONSIDERATION_AUTHORITY_COUNT = 0`

`SECOND_DISCRETE_QUANTITY_ENGINE_CREATED = NO`

`FINAL_NO_DEPLOYABLE_OWNER = PORTFOLIO_CONSTRUCTION`

`FINAL_NO_DEPLOYABLE_PREMATURE_DECLARATION = NO`

`CASH_WIN_REASON_LINEAGE_COMPLETE = YES`

`G44_FORCES_EXISTING_POSITION_EXIT = NO`

`SELL_REDUCE_EXIT_SEMANTICS_CHANGED = NO`

`BUY_SELL_INDEPENDENCE_PRESERVED = YES`

`SAFETY_AUTHORITY_CHANGED = NO`

`MARKET_QUALITY_RECOMPUTED_OUTSIDE_OWNER = NO`

`RISK_PACING_RECOMPUTED_OUTSIDE_OWNER = NO`

`OPPORTUNITY_QUALITY_RECOMPUTED_OUTSIDE_MCV_AUTHORITY = NO`

`FUTURE_INPUT_COUNT = 0`

`HISTORICAL_OUTCOME_INPUT_COUNT = 0`

`PAPER_LEDGER_INPUT_COUNT = 0`

`AUDIT_RESULT_INPUT_COUNT = 0`

`MFE_MAE_INPUT_COUNT = 0`

`G44_ADD_BINDING_TESTS = PASS`

`G44_REENTRY_BINDING_TESTS = PASS`

`G44_LOT_RECONSIDERATION_TESTS = PASS`

`PHASE28_29_LOT_REPAIR_REGRESSION = NO`

`G26_REENTRY_SEMANTIC_REGRESSION = NO`

`G27_ADD_CAPITAL_COMPETITION_REGRESSION = NO`

`G43_BINDING_MATRIX_BYPASS_COUNT = 0`

`ADD_BINDING_INTEGRATION_COMPLETE = YES`

`REENTRY_BINDING_INTEGRATION_COMPLETE = YES`

`LOT_RECONSIDERATION_BINDING_INTEGRATION_COMPLETE = YES`

`RESIDUAL_CAPITAL_BINDING_BYPASS_COUNT = 0`

`G44_PRODUCTION_BEHAVIOR_CHANGE_CLASS = AUTHORITATIVE_DECISION_CHANGE`

`G44_FOCUSED_REGRESSION = PASS`

`PY_COMPILE = PASS`

`GIT_DIFF_CHECK = PASS`

`CONFIG_CHANGE_EXECUTED = NO`

`THRESHOLD_CHANGE_EXECUTED = NO`

`PARAMETER_TUNING_EXECUTED = NO`

`FIXTURE_CHANGE_EXECUTED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`REPLAY_EXECUTED = NO`

`HISTORICAL_RERUN_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`
