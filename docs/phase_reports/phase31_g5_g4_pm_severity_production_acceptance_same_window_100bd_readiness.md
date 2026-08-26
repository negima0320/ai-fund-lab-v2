# Phase31-G5 — G4 PM Severity / Persistence Production Acceptance + Clean 100BD Readiness

## Scope

Task type: READ-ONLY production acceptance / validation readiness.

No implementation, Strategy mutation, PM mutation, SELL rule mutation, threshold tuning, config change, feature addition, Runtime mutation, fresh-run, resume, replay, or long Historical execution was performed in G5.

Read:

- `docs/phase_reports/phase31_g4_pm_severity_persistence_contract_focused_implementation.md`
- `docs/phase_reports/phase31_g3_pit_safe_pm_severity_persistence_contract_design.md`
- `docs/phase_reports/phase31_g2_pit_safe_pm_severity_persistence_hold_regret_audit.md`
- `src/ai_fund_lab_v2/strategy/sell_semantic_state.py`
- `src/ai_fund_lab_v2/strategy/position_management.py`
- `tests/strategy/test_phase31_g4_pm_severity_persistence.py`
- `tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py`
- `tests/strategy/test_phase31_f1i_prior_unrepresentable_reduce_bridge.py`
- `tests/strategy/test_phase31_f1d_canonical_sell_semantic_shadow.py`

## Primary Judgment

`PRIMARY_JUDGMENT = PHASE31_G5_G4_PM_SEVERITY_ACCEPTED_READY_FOR_CLEAN_SAME_WINDOW_100BD`

G4 conforms to the G3 contract. PM severity is attached as production-visible PM evidence, consumes the existing canonical SELL state, preserves F1F/F1I PM-owned EXIT authority, and does not introduce a second SELL classifier or performance-window-derived tuning.

## Scope Acceptance

`G4_SCOPE_CONFORMANCE = PASS`

Changed production behavior is limited to PM severity / persistence evidence projection from the existing PM semantic path:

- `sell_semantic_state.evaluate_position_sell_semantic`
- `position_management._apply_canonical_sell_semantics`

No changed G4 implementation path was found for BUY, Candidate, ranking, ADD selection, model, technical feature generation, Market Context authority, PS quantity authority, Runtime SELL authority, Pending, Submit, execution, valuation, or Safety.

## Canonical SELL Ownership

`CANONICAL_SELL_STATE_OWNER_PRESERVED = YES`

`SECOND_SELL_CLASSIFIER_COUNT = 0`

`canonical_sell_state` remains produced by `strategy.sell_semantic_state`. PM severity is derived from that state and exposes `second_sell_classifier_created = False`.

## PM Severity Authority

`PM_SEVERITY_AUTHORITY_ACCEPTANCE = PASS`

Production severity states are exactly:

- `PM_SEVERITY_NORMAL`
- `PM_SEVERITY_CAUTION`
- `PM_SEVERITY_DEFENSIVE`
- `PM_SEVERITY_EXIT_CANDIDATE`
- `PM_SEVERITY_UNRESOLVED`

Severity does not independently classify market deterioration. It consumes canonical SELL state plus PM evidence modifiers.

## Strict-Prior Persistence

`STRICT_PRIOR_PERSISTENCE_ACCEPTANCE = PASS`

`SAME_DAY_SELF_COUNT = 0`

`CROSS_CAMPAIGN_HISTORY_LEAK = 0`

G4 uses prior unrepresentable-reduce / campaign history summaries surfaced through Strategy Intelligence and F1I. The F1I regression proves same-day current REDUCE is not counted, prior closed / other-campaign evidence does not leak, and recovery reset clears old unrepresentable pressure.

## Winner Preservation

`STATE_ALONE_AUTO_EXIT = NO`

`REGIME_ALONE_AUTO_EXIT = NO`

`REDUCE_COUNT_ALONE_AUTO_EXIT = NO`

`NEGATIVE_RETURN_ALONE_AUTO_EXIT = NO`

`PROFITABLE_WEAKENING_OPTIONALITY_PRESERVED = YES`

G4 tests prove profitable temporary weakening remains `PM_SEVERITY_CAUTION` without full EXIT, regime-only adversity cannot force EXIT, and repeated REDUCE count alone does not force EXIT for a profitable representable winner. Negative campaign return only contributes to `PM_SEVERITY_DEFENSIVE` when paired with canonical non-healthy state; it is not an EXIT rule.

## Loser Escalation

`PERSISTENT_FAILING_CAMPAIGN_CAN_ESCALATE = YES`

`PM_EXIT_AUTHORITY_PRESERVED = YES`

`PS_RUNTIME_EXIT_INVENTION = NO`

Persistent discrete-lot deterioration with complete campaign identity, PIT proof, no recovery, and strict-prior evidence still reaches the existing F1F PM-owned escalation gate. PS and Runtime do not receive new EXIT authority.

## Recovery Acceptance

`RECOVERY_DEESCALATION = PASS`

`PERMANENT_DETERIORATION_DEBT = NO`

G4 exposes recovery de-escalation evidence and maps recovered/healthy PM evidence to `PM_SEVERITY_NORMAL` / `RECOVERED`. F1I recovery reset regression confirms prior pressure is cleared after recovery boundary evidence.

## Missing Evidence Safety

`MISSING_EVIDENCE_AUTO_EXIT = NO`

`UNRESOLVED_FAIL_SAFE = PASS`

Missing or ambiguous PIT proof, campaign identity, canonical state, return modifier, or state evidence does not create severity-based EXIT. Ambiguous canonical state maps to `PM_SEVERITY_UNRESOLVED`.

## Future-Information Audit

`FUTURE_INFORMATION_USED_AS_PRODUCTION_INPUT = NO`

G4 severity inputs are current canonical SELL state, current campaign return, strict-prior same-campaign history, current recovery evidence, optional current regime modifier, and PIT proof. The code records `future_information_used = False`, `final_campaign_outcome_used = False`, and `outcome_used_for_parameter_selection = False`.

## Numeric Threshold Audit

`G0_G2_DERIVED_NUMERIC_THRESHOLD_COUNT = 0`

No G0/G1/G2-derived numeric threshold was introduced. G4 uses sign semantics for current campaign return and pre-existing canonical state / representability gates. No hidden rule equivalent to return < X%, exactly N days, giveback > X%, regime score > X, or REDUCE count >= N was added from the 100BD diagnostics.

## F1F / F1I Compatibility

`F1F_F1I_COMPATIBILITY = PASS`

Focused regression command:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/strategy/test_phase31_g4_pm_severity_persistence.py tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py tests/strategy/test_phase31_f1i_prior_unrepresentable_reduce_bridge.py tests/strategy/test_phase31_f1d_canonical_sell_semantic_shadow.py -q
```

Result:

```text
32 passed in 1.53s
```

Covered:

- G4 severity / persistence winner preservation
- F1F canonical SELL PM escalation
- F1I strict-prior bridge
- same-day self-count protection
- recovery reset
- discrete-lot unrepresentable REDUCE semantics
- minimum-notional isolation
- no fake execution event
- PIT/future-information canonical shadow guard

## Observability

`PM_SEVERITY_OBSERVABILITY_ACCEPTANCE = PASS`

PM rows now expose:

- `canonical_sell_state`
- `canonical_sell_semantic_evidence`
- `pm_severity`
- `pm_severity_reasons`
- `pm_severity_evidence`
- `persistence_state`
- campaign economics modifier
- recovery modifier
- regime modifier
- final PM action
- canonical and severity contract versions

This is sufficient for later old-vs-new 100BD campaign-level comparison.

## Baseline Comparison Contract

`CONTROLLED_COMPARISON_CONTRACT = LOCKED`

Old baseline run:

`runtime-test-historical-extended-smoke-20260821T095536206137Z`

Locked comparison inputs:

- `profile = historical-extended-smoke`
- `start-date = 2022-08-15`
- `business-days = 100`
- `initial-cash = 1000000`

Baseline result:

- final equity = 1,171,580
- return = +17.158%

## Validation Interpretation Contract

`PERFORMANCE_ONLY_ACCEPTANCE_PROHIBITED = YES`

The next 100BD result must be interpreted through causal comparison, not final return alone. Required comparison includes final equity, gross profit/loss, MDD, 2-5BD loss, 11BD+ winner profit, winner giveback, retention, false early EXIT damage, HOLD regret, REDUCE/EXIT counts, churn, regime PnL, exposure/cash, every changed PM campaign, severity distribution, escalation/de-escalation, recovery events, and long winner preservation.

`POST_100BD_IMMEDIATE_PARAMETER_TUNING = PROHIBITED`

If the new run is better or worse, the next step is old-vs-new causal audit before any tuning.

## Compile / Diff Checks

Py compile command:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/sell_semantic_state.py src/ai_fund_lab_v2/strategy/position_management.py tests/strategy/test_phase31_g4_pm_severity_persistence.py tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py tests/strategy/test_phase31_f1i_prior_unrepresentable_reduce_bridge.py tests/strategy/test_phase31_f1d_canonical_sell_semantic_shadow.py
```

`PY_COMPILE = PASS`

Diff check command:

```bash
git diff --check
```

`GIT_DIFF_CHECK = PASS`

## Required Summary Output

`G4_SCOPE_CONFORMANCE = PASS`

`CANONICAL_SELL_STATE_OWNER_PRESERVED = YES`

`SECOND_SELL_CLASSIFIER_COUNT = 0`

`PM_SEVERITY_AUTHORITY_ACCEPTANCE = PASS`

`STRICT_PRIOR_PERSISTENCE_ACCEPTANCE = PASS`

`SAME_DAY_SELF_COUNT = 0`

`CROSS_CAMPAIGN_HISTORY_LEAK = 0`

`STATE_ALONE_AUTO_EXIT = NO`

`REGIME_ALONE_AUTO_EXIT = NO`

`REDUCE_COUNT_ALONE_AUTO_EXIT = NO`

`NEGATIVE_RETURN_ALONE_AUTO_EXIT = NO`

`PROFITABLE_WEAKENING_OPTIONALITY_PRESERVED = YES`

`PERSISTENT_FAILING_CAMPAIGN_CAN_ESCALATE = YES`

`PM_EXIT_AUTHORITY_PRESERVED = YES`

`PS_RUNTIME_EXIT_INVENTION = NO`

`RECOVERY_DEESCALATION = PASS`

`PERMANENT_DETERIORATION_DEBT = NO`

`MISSING_EVIDENCE_AUTO_EXIT = NO`

`UNRESOLVED_FAIL_SAFE = PASS`

`FUTURE_INFORMATION_USED_AS_PRODUCTION_INPUT = NO`

`G0_G2_DERIVED_NUMERIC_THRESHOLD_COUNT = 0`

`F1F_F1I_COMPATIBILITY = PASS`

`PM_SEVERITY_OBSERVABILITY_ACCEPTANCE = PASS`

`CONTROLLED_COMPARISON_CONTRACT = LOCKED`

`PERFORMANCE_ONLY_ACCEPTANCE_PROHIBITED = YES`

`POST_100BD_IMMEDIATE_PARAMETER_TUNING = PROHIBITED`

`IMPLEMENTATION_CHANGED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`FOCUSED_TEST_RESULTS = PASS`

`PY_COMPILE = PASS`

`GIT_DIFF_CHECK = PASS`

`VALIDATION_READINESS = READY_FOR_CLEAN_SAME_WINDOW_100BD`

## User-Operated Next Command

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-extended-smoke --start-date 2022-08-15 --business-days 100 --initial-cash 1000000 --confirm --yes-i-understand-this-mutates-trading-state
```
