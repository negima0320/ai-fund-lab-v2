# Phase31-G43 - Risk Pacing Economic Binding Activation

## Scope

Task type: IMPLEMENTATION - AUTHORITATIVE DECISION CHANGE.

G43 activates the full economically binding Risk Pacing matrix over the
canonical pre-final Market x Candidate x Cash interaction path created in G42.
This slice may change final incremental capital winners by design.

Changed files:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `tests/strategy/test_phase31_g43_risk_pacing_economic_binding.py`
- `docs/phase_reports/phase31_g43_risk_pacing_economic_binding_activation.md`

No Position Sizing, PM / SELL, Safety, Runtime capital re-decision,
configuration, thresholds, parameters, fixtures, fresh-run, resume, replay,
Historical rerun, or long Historical was changed or executed.

No permanent architecture update beyond G38 was required. G43 implements the
G38/G39 matrix already defined in
`docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`.

## Inputs Read

- `docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md`
- `docs/phase_reports/phase31_g37_risk_pacing_binding_candidate_comparison_effectiveness_root_cause_audit.md`
- `docs/phase_reports/phase31_g38_economically_binding_risk_pacing_market_candidate_cash_interaction_architecture_refinement.md`
- `docs/phase_reports/phase31_g39_opportunity_quality_true_cash_competition_implementation_planning.md`
- `docs/phase_reports/phase31_g40_opportunity_quality_producer_reachable_continuum_implementation.md`
- `docs/phase_reports/phase31_g41_true_cash_competitor_evidence_framework_implementation.md`
- `docs/phase_reports/phase31_g42_pre_final_market_candidate_cash_interaction_implementation.md`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/portfolio_policy.py`
- `src/ai_fund_lab_v2/strategy/marginal_capital_value.py`
- `src/ai_fund_lab_v2/strategy/market_context.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`

## Primary Judgment

`PHASE31_G43_RISK_PACING_ECONOMIC_BINDING_ACTIVATED_ACCEPTED`

The G43 binding matrix is now authoritative inside
`market_candidate_cash_interaction.v1`. Risk Pacing no longer acts as a late
target mutation. It changes final semantic capital winner through the
Portfolio Construction-owned pre-final interaction stage.

## Implemented Binding Matrix

| Risk Pacing | STRONG | COMPARABLE_HIGH | COMPARABLE_MARGINAL | WEAK_VALID | INSUFFICIENT | BLOCKED |
| --- | --- | --- | --- | --- | --- | --- |
| NORMAL | DEPLOY_ELIGIBLE | DEPLOY_ELIGIBLE | DEPLOY_ELIGIBLE | SELECTIVE_COMPETITION | FAIL_CLOSED | BLOCKED |
| GRADUAL | DEPLOY_ELIGIBLE | SELECTIVE_COMPETITION | CASH_PREFERRED | CASH_PREFERRED | FAIL_CLOSED | BLOCKED |
| CAUTIOUS | SELECTIVE_COMPETITION | SELECTIVE_COMPETITION only with caution-sufficient PIT evidence, otherwise CASH_PREFERRED | CASH_PREFERRED | CASH_PREFERRED | FAIL_CLOSED | BLOCKED |
| PRESERVE | SELECTIVE_COMPETITION only for complete explicit STRONG exception evidence, otherwise CASH_PREFERRED | CASH_PREFERRED | CASH_PREFERRED | CASH_PREFERRED | FAIL_CLOSED | BLOCKED |

No outcome-derived numeric threshold was introduced. Caution sufficiency and
preserve exception are read from existing PIT opportunity-quality evidence,
reason codes, and source evidence completeness.

## Decision Evidence

Every security competitor interaction record now materializes:

- `risk_pacing_intent`
- `canonical_opportunity_quality_class`
- `opportunity_quality_class`
- `cash_preference_semantic`
- `interaction_result`
- `binding_reason_codes`
- `winner_loser`
- `as_of_business_date`
- `lineage`

The interaction payload records:

- `full_risk_pacing_binding_matrix_implemented = True`
- `canonical_binding_decision_evidence_complete = True`
- `binding_reason_codes_implemented = True`
- no fixed exposure target, fixed BUY count, daily deployment quota, direct
  quantity setting, or rank mutation.

## Acceptance Results

| Requirement | Result |
| --- | --- |
| `FULL_RISK_PACING_BINDING_MATRIX_IMPLEMENTED` | YES |
| `NORMAL_STRONG_DEPLOY` | YES |
| `NORMAL_COMPARABLE_HIGH_DEPLOY` | YES |
| `NORMAL_COMPARABLE_MARGINAL_DEPLOY` | YES |
| `NORMAL_WEAK_VALID_SELECTIVE` | YES |
| `GRADUAL_STRONG_DEPLOY` | YES |
| `GRADUAL_COMPARABLE_HIGH_SELECTIVE` | YES |
| `GRADUAL_COMPARABLE_MARGINAL_CASH_PREFERRED` | YES |
| `GRADUAL_WEAK_VALID_CASH_PREFERRED` | YES |
| `CAUTIOUS_STRONG_SELECTIVE` | YES |
| `CAUTIOUS_COMPARABLE_HIGH_REQUIRES_CAUTION_SUFFICIENT_EVIDENCE` | YES |
| `CAUTIOUS_COMPARABLE_MARGINAL_CASH_PREFERRED` | YES |
| `CAUTIOUS_WEAK_VALID_CASH_PREFERRED` | YES |
| `PRESERVE_STRONG_EXCEPTION_PATH_EXISTS` | YES |
| `PRESERVE_COMPARABLE_HIGH_CASH_PREFERRED` | YES |
| `PRESERVE_COMPARABLE_MARGINAL_CASH_PREFERRED` | YES |
| `PRESERVE_WEAK_VALID_CASH_PREFERRED` | YES |
| `STRONG_CAN_OVERRIDE_CAUTION` | YES |
| `BLANKET_MARKET_BUY_BAN` | NO |
| `COMPARABLE_HIGH_NO_LONGER_AUTOMATIC_CAUTION_BYPASS` | YES |
| `MARGINAL_VALID_OPPORTUNITY_CAN_LOSE_TO_CASH` | YES |
| `WEAK_VALID_CAN_LOSE_TO_CASH` | YES |
| `CASH_CAN_WIN_AGAINST_VALID_SECURITY` | YES |
| `FIXED_EXPOSURE_TARGET_CREATED` | NO |
| `RISK_PACING_DIRECT_EXPOSURE_PERCENT_SETTER` | NO |
| `FIXED_BUY_COUNT_CREATED` | NO |
| `FIXED_DAILY_DEPLOYMENT_QUOTA_CREATED` | NO |
| `SAME_CANDIDATE_DIFFERENT_MARKET_CHANGES_ECONOMIC_DECISION` | YES |
| `SAME_MARKET_DIFFERENT_CANDIDATE_CHANGES_ECONOMIC_DECISION` | YES |
| `GRADUAL_CAUTION_ECONOMIC_DIFFERENCE_PROVEN` | YES |
| `PRESERVE_CAUTION_ECONOMIC_DIFFERENCE_PROVEN` | YES |
| `RECOVERY_REDEPLOYMENT_PATH_EXISTS` | YES |
| `FIXED_COOLDOWN_FOR_MARKET_RECOVERY_CREATED` | NO |
| `RISK_PACING_DECISION_REEVALUATED_EACH_BUSINESS_DATE` | YES |
| `PERMANENT_CAUTION_LATCH_CREATED` | NO |
| `RISK_PACING_FORCES_EXISTING_EXIT` | NO |
| `ADD_CAN_LOSE_TO_CASH_UNDER_CAUTION` | YES |
| `STRONG_ADD_CAN_WIN_UNDER_CAUTION` | YES |
| `ADD_AUTOMATIC_PRIORITY` | NO |
| `REENTRY_USES_SAME_BINDING_MATRIX` | YES |
| `REENTRY_SPECIAL_MARKET_PENALTY_CREATED` | NO |
| `INSUFFICIENT_ALWAYS_FAIL_CLOSED` | YES |
| `MISSING_MARKET_QUALITY_FAIL_CLOSED` | YES |
| `MISSING_RISK_PACING_FAIL_CLOSED` | YES |
| `BLOCKED_NEVER_RESCUED_BY_STRONG_MARKET` | YES |
| `BLOCKED_NEVER_RESCUED_BY_RISK_PACING` | YES |
| `FINAL_CAPITAL_WINNER_OWNER` | PORTFOLIO_CONSTRUCTION |
| `SECOND_CAPITAL_WINNER_AUTHORITY_COUNT` | 0 |
| `POSITION_SIZING_REMAINS_QUANTITY_OWNER` | YES |
| `RISK_PACING_DIRECTLY_SETS_QUANTITY` | NO |
| `PC_DIRECTLY_SETS_SHARE_QUANTITY` | NO |
| `LOT_RECONSIDERATION_PRESERVES_BINDING_MATRIX` | YES |
| `LEGACY_LATE_RISK_PACING_DECISION_AUTHORITY_COUNT` | 0 |
| `LEGACY_ELIGIBLE_CLASS_USED_FOR_BINDING_DECISION` | NO |
| `LEGACY_RESIDUAL_CASH_OVERRIDES_CANONICAL_WINNER` | NO |
| `MARKET_QUALITY_RECOMPUTED_IN_PC` | NO |
| `RISK_PACING_RECOMPUTED_IN_PC` | NO |
| `OPPORTUNITY_QUALITY_RECOMPUTED_IN_PC` | NO |
| `NEW_ALPHA_FEATURE_CREATED` | NO |
| `CANDIDATE_RANK_MUTATED_BY_RISK_PACING` | NO |
| `FUTURE_INPUT_COUNT` | 0 |
| `HISTORICAL_OUTCOME_INPUT_COUNT` | 0 |
| `PAPER_LEDGER_INPUT_COUNT` | 0 |
| `AUDIT_RESULT_INPUT_COUNT` | 0 |
| `MFE_MAE_INPUT_COUNT` | 0 |
| `OUTCOME_DERIVED_DECISION_RULE_COUNT` | 0 |
| `CANONICAL_BINDING_DECISION_EVIDENCE_COMPLETE` | YES |
| `BINDING_REASON_CODES_IMPLEMENTED` | YES |
| `G43_SYNTHETIC_BINDING_ACCEPTANCE` | PASS |
| `CURRENT_RISK_PACING_ECONOMIC_SENSITIVITY_PROVEN` | YES |
| `UNREACHABLE_WEAK_CLASS_DEFECT_REPAIRED` | YES_FROM_G40 |
| `TRUE_CASH_COMPETITOR_EVIDENCE_DEFECT_REPAIRED` | YES_FROM_G41 |
| `PRE_FINAL_INTERACTION_DEFECT_REPAIRED` | YES_FROM_G42 |
| `CAUTIOUS_GRADUAL_BINDING_DEFECT_REPAIRED` | YES |
| `TRUE_CASH_COMPETITOR_ECONOMIC_BINDING_DEFECT_REPAIRED` | YES |
| `RISK_PACING_EFFECTIVELY_NON_BINDING_DEFECT_REPAIRED` | YES |
| `G43_PRODUCTION_BEHAVIOR_CHANGE_CLASS` | AUTHORITATIVE_DECISION_CHANGE |

## Synthetic Binding Acceptance

Implemented in
`tests/strategy/test_phase31_g43_risk_pacing_economic_binding.py`.

Covered cases:

1. same COMPARABLE_MARGINAL candidate: NORMAL security wins, CAUTIOUS Cash wins.
2. same CAUTIOUS market: STRONG security wins, COMPARABLE_MARGINAL Cash wins.
3. same COMPARABLE_HIGH evidence: GRADUAL security wins, CAUTIOUS Cash wins
   without caution-sufficient evidence.
4. CAUTIOUS COMPARABLE_HIGH wins only when caution-sufficient PIT evidence is
   present.
5. STRONG + CAUTIOUS can win.
6. STRONG + PRESERVE can win only through complete explicit exception evidence.
7. WEAK_VALID + NORMAL is selective; WEAK_VALID + CAUTIOUS loses to Cash.
8. INSUFFICIENT fails closed.
9. BLOCKED remains blocked and is not rescued.
10. ADD STRONG can win under CAUTIOUS; ADD marginal can lose to Cash.
11. CAUTIOUS to NORMAL redeployment path exists without a sticky latch.

`G43_SYNTHETIC_BINDING_ACCEPTANCE = PASS`

## Validation

Focused G43 tests:

```text
python3 -m pytest tests/strategy/test_phase31_g43_risk_pacing_economic_binding.py
```

Result:

```text
10 passed
```

Focused regression:

```text
python3 -m pytest tests/strategy/test_phase31_g43_risk_pacing_economic_binding.py tests/strategy/test_phase31_g42_market_candidate_cash_interaction.py tests/strategy/test_phase31_g41_cash_competitor_evidence.py tests/strategy/test_phase31_g40_opportunity_quality_continuum.py tests/strategy/test_phase31_b4_marginal_capital_value_shadow.py tests/strategy/test_phase31_b6_marginal_capital_shadow_bridge.py tests/strategy/test_phase31_b8_pending_cash_causality_bridge.py tests/strategy/test_phase31_b10_alternative_c_marginal_capital_priority.py tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_c_portfolio_policy.py tests/strategy/test_phase22_l_market_context_resolution.py tests/strategy/test_phase30_j_strategy_intelligence.py tests/strategy/test_phase31_g4_pm_severity_persistence.py tests/strategy/test_phase31_g8_pm_severity_action_mapping.py tests/strategy/test_phase22_j_position_sizing.py -k 'not real'
```

Result:

```text
316 passed, 9 deselected
```

Python compile:

```text
PYTHONPYCACHEPREFIX=/private/tmp/ai_fund_lab_v2_pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py tests/strategy/test_phase31_g43_risk_pacing_economic_binding.py
```

Result:

```text
PASS
```

Diff hygiene:

```text
git diff --check -- src/ai_fund_lab_v2/strategy/portfolio_construction.py tests/strategy/test_phase31_g43_risk_pacing_economic_binding.py
```

Result:

```text
PASS
```

## Required Summary Output

`PRIMARY_JUDGMENT = PHASE31_G43_RISK_PACING_ECONOMIC_BINDING_ACTIVATED_ACCEPTED`

`FULL_RISK_PACING_BINDING_MATRIX_IMPLEMENTED = YES`

`NORMAL_STRONG_DEPLOY = YES`

`NORMAL_COMPARABLE_HIGH_DEPLOY = YES`

`NORMAL_COMPARABLE_MARGINAL_DEPLOY = YES`

`NORMAL_WEAK_VALID_SELECTIVE = YES`

`GRADUAL_STRONG_DEPLOY = YES`

`GRADUAL_COMPARABLE_HIGH_SELECTIVE = YES`

`GRADUAL_COMPARABLE_MARGINAL_CASH_PREFERRED = YES`

`GRADUAL_WEAK_VALID_CASH_PREFERRED = YES`

`CAUTIOUS_STRONG_SELECTIVE = YES`

`CAUTIOUS_COMPARABLE_HIGH_REQUIRES_CAUTION_SUFFICIENT_EVIDENCE = YES`

`CAUTIOUS_COMPARABLE_MARGINAL_CASH_PREFERRED = YES`

`CAUTIOUS_WEAK_VALID_CASH_PREFERRED = YES`

`PRESERVE_STRONG_EXCEPTION_PATH_EXISTS = YES`

`PRESERVE_COMPARABLE_HIGH_CASH_PREFERRED = YES`

`PRESERVE_COMPARABLE_MARGINAL_CASH_PREFERRED = YES`

`PRESERVE_WEAK_VALID_CASH_PREFERRED = YES`

`STRONG_CAN_OVERRIDE_CAUTION = YES`

`BLANKET_MARKET_BUY_BAN = NO`

`COMPARABLE_HIGH_NO_LONGER_AUTOMATIC_CAUTION_BYPASS = YES`

`MARGINAL_VALID_OPPORTUNITY_CAN_LOSE_TO_CASH = YES`

`WEAK_VALID_CAN_LOSE_TO_CASH = YES`

`CASH_CAN_WIN_AGAINST_VALID_SECURITY = YES`

`FIXED_EXPOSURE_TARGET_CREATED = NO`

`RISK_PACING_DIRECT_EXPOSURE_PERCENT_SETTER = NO`

`FIXED_BUY_COUNT_CREATED = NO`

`FIXED_DAILY_DEPLOYMENT_QUOTA_CREATED = NO`

`SAME_CANDIDATE_DIFFERENT_MARKET_CHANGES_ECONOMIC_DECISION = YES`

`SAME_MARKET_DIFFERENT_CANDIDATE_CHANGES_ECONOMIC_DECISION = YES`

`GRADUAL_CAUTION_ECONOMIC_DIFFERENCE_PROVEN = YES`

`PRESERVE_CAUTION_ECONOMIC_DIFFERENCE_PROVEN = YES`

`RECOVERY_REDEPLOYMENT_PATH_EXISTS = YES`

`FIXED_COOLDOWN_FOR_MARKET_RECOVERY_CREATED = NO`

`RISK_PACING_DECISION_REEVALUATED_EACH_BUSINESS_DATE = YES`

`PERMANENT_CAUTION_LATCH_CREATED = NO`

`RISK_PACING_FORCES_EXISTING_EXIT = NO`

`ADD_CAN_LOSE_TO_CASH_UNDER_CAUTION = YES`

`STRONG_ADD_CAN_WIN_UNDER_CAUTION = YES`

`ADD_AUTOMATIC_PRIORITY = NO`

`REENTRY_USES_SAME_BINDING_MATRIX = YES`

`REENTRY_SPECIAL_MARKET_PENALTY_CREATED = NO`

`INSUFFICIENT_ALWAYS_FAIL_CLOSED = YES`

`MISSING_MARKET_QUALITY_FAIL_CLOSED = YES`

`MISSING_RISK_PACING_FAIL_CLOSED = YES`

`BLOCKED_NEVER_RESCUED_BY_STRONG_MARKET = YES`

`BLOCKED_NEVER_RESCUED_BY_RISK_PACING = YES`

`FINAL_CAPITAL_WINNER_OWNER = PORTFOLIO_CONSTRUCTION`

`SECOND_CAPITAL_WINNER_AUTHORITY_COUNT = 0`

`POSITION_SIZING_REMAINS_QUANTITY_OWNER = YES`

`RISK_PACING_DIRECTLY_SETS_QUANTITY = NO`

`PC_DIRECTLY_SETS_SHARE_QUANTITY = NO`

`LOT_RECONSIDERATION_PRESERVES_BINDING_MATRIX = YES`

`LEGACY_LATE_RISK_PACING_DECISION_AUTHORITY_COUNT = 0`

`LEGACY_ELIGIBLE_CLASS_USED_FOR_BINDING_DECISION = NO`

`LEGACY_RESIDUAL_CASH_OVERRIDES_CANONICAL_WINNER = NO`

`MARKET_QUALITY_RECOMPUTED_IN_PC = NO`

`RISK_PACING_RECOMPUTED_IN_PC = NO`

`OPPORTUNITY_QUALITY_RECOMPUTED_IN_PC = NO`

`NEW_ALPHA_FEATURE_CREATED = NO`

`CANDIDATE_RANK_MUTATED_BY_RISK_PACING = NO`

`FUTURE_INPUT_COUNT = 0`

`HISTORICAL_OUTCOME_INPUT_COUNT = 0`

`PAPER_LEDGER_INPUT_COUNT = 0`

`AUDIT_RESULT_INPUT_COUNT = 0`

`MFE_MAE_INPUT_COUNT = 0`

`OUTCOME_DERIVED_DECISION_RULE_COUNT = 0`

`CANONICAL_BINDING_DECISION_EVIDENCE_COMPLETE = YES`

`BINDING_REASON_CODES_IMPLEMENTED = YES`

`G43_SYNTHETIC_BINDING_ACCEPTANCE = PASS`

`CURRENT_RISK_PACING_ECONOMIC_SENSITIVITY_PROVEN = YES`

`UNREACHABLE_WEAK_CLASS_DEFECT_REPAIRED = YES_FROM_G40`

`TRUE_CASH_COMPETITOR_EVIDENCE_DEFECT_REPAIRED = YES_FROM_G41`

`PRE_FINAL_INTERACTION_DEFECT_REPAIRED = YES_FROM_G42`

`CAUTIOUS_GRADUAL_BINDING_DEFECT_REPAIRED = YES`

`TRUE_CASH_COMPETITOR_ECONOMIC_BINDING_DEFECT_REPAIRED = YES`

`RISK_PACING_EFFECTIVELY_NON_BINDING_DEFECT_REPAIRED = YES`

`G43_PRODUCTION_BEHAVIOR_CHANGE_CLASS = AUTHORITATIVE_DECISION_CHANGE`

`G43_FOCUSED_REGRESSION = PASS`

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

`NEXT_TASK_RECOMMENDATION = PHASE31_G44_ADD_REENTRY_LOT_RECONSIDERATION_BINDING_INTEGRATION`
