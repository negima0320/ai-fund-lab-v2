# Phase31-G8 — PM Severity Action-Mapping Focused Production Implementation

## Scope

Task type: focused production implementation + regression.

Implemented only the G7-defined PM-owned action mapping. No BUY, Candidate, ranking, ADD logic, model, indicator, Market Context, PS/Runtime EXIT invention, Pending, Submit, fresh-run, resume, replay, or long Historical change was made.

Read:

- `docs/phase_reports/phase31_g7_pm_severity_action_mapping_design.md`
- `docs/phase_reports/phase31_g6_g4_same_window_100bd_behavioral_activation_no_delta_audit.md`
- `docs/phase_reports/phase31_g4_pm_severity_persistence_contract_focused_implementation.md`
- `docs/phase_reports/phase31_g3_pit_safe_pm_severity_persistence_contract_design.md`
- `docs/phase_reports/phase31_g2_pit_safe_pm_severity_persistence_hold_regret_audit.md`
- `src/ai_fund_lab_v2/strategy/sell_semantic_state.py`
- `src/ai_fund_lab_v2/strategy/position_management.py`

## Primary Judgment

`PRIMARY_JUDGMENT = PHASE31_G8_PM_SEVERITY_ACTION_MAPPING_IMPLEMENTED_READY_FOR_G9_ACCEPTANCE`

G8 connects production-visible `pm_severity` to PM-owned final action mapping in `position_management`, after canonical SELL state and severity evidence exist. Canonical SELL state ownership remains unchanged.

## Implementation Summary

Production change:

- `src/ai_fund_lab_v2/strategy/position_management.py`

Focused test added:

- `tests/strategy/test_phase31_g8_pm_severity_action_mapping.py`

The mapping now records:

- `baseline_final_pm_action`
- `final_pm_action`
- `final_pm_intensity`
- `pm_severity_action_mapping_connected`
- `pm_severity_action_mapping_contract_version`
- `pm_severity_action_mapping_decision`
- `pm_severity_action_mapping_reason_code`
- `pm_severity_action_mapping_evidence`

## Action Mapping

`PM_SEVERITY_ACTION_MUTATION_CONNECTED = YES`

`PM_ACTION_MAPPING_OWNER = POSITION_MANAGEMENT_PM`

`CANONICAL_SELL_STATE_OWNER_CHANGED = NO`

`SECOND_SELL_CLASSIFIER_CREATED = NO`

`PS_RUNTIME_ACTION_INVENTION = NO`

Implemented rules:

- `NORMAL`: preserve baseline action.
- `CAUTION`: preserve HOLD/REDUCE optionality; no auto-EXIT.
- `DEFENSIVE`: may mutate HOLD -> REDUCE only when canonical non-healthy state, failing campaign economics, PIT pass, complete campaign identity, no recovery, no conflict, and no unresolved evidence all hold.
- `DEFENSIVE FIRST_OBSERVATION`: REDUCE remains REDUCE; no full EXIT.
- `DEFENSIVE / EXIT_CANDIDATE` with `PERSISTENT / WORSENING`: REDUCE may become EXIT only when campaign economics remain failing, recovery is absent, PIT/campaign validity pass, canonical state is `PERSISTENT_DETERIORATION` or `EXIT_GRADE`, and a PM-owned canonical/F1F gate authorizes EXIT.
- `EXIT_GRADE`: existing EXIT remains preserved.
- `UNRESOLVED` / missing evidence: no severity-based EXIT.

## Safety Results

`DEFENSIVE_HOLD_TO_REDUCE_IMPLEMENTED = YES`

`FIRST_OBSERVATION_FULL_EXIT = NO`

`PERSISTENT_REDUCE_TO_EXIT_IMPLEMENTED = YES`

`EXIT_GRADE_EXISTING_EXIT_PRESERVED = YES`

`PROFITABLE_WEAKENING_AUTO_EXIT = NO`

`PROFITABLE_REDUCE_CHAIN_PRESERVED = YES`

`REDUCE_COUNT_DIRECT_EXIT_RULE = NO`

`NEGATIVE_RETURN_DIRECT_EXIT = NO`

`RECOVERY_PRE_ACTION_DEESCALATION = YES`

`STALE_EXIT_AFTER_RECOVERY = NO`

`REGIME_ACTION_AUTHORITY = NONE`

`REGIME_DIRECT_EXIT_RULE = NO`

`MISSING_EVIDENCE_AUTO_EXIT = NO`

`AMBIGUOUS_EVIDENCE_FAIL_SAFE = PASS`

`ACTION_MAPPING_OBSERVABILITY = PASS`

`FUTURE_INFORMATION_USED_AS_PRODUCTION_INPUT = NO`

`PERFORMANCE_WINDOW_USED_FOR_PARAMETER_SELECTION = NO`

`PRODUCTION_NUMERIC_THRESHOLD_SELECTED = NO`

`BUY_LOGIC_CHANGED = NO`

`NEW_FEATURE_ADDED = NO`

## Behavioral Delta Proof

`FOCUSED_HOLD_TO_REDUCE_DELTA_PROVEN = YES`

Focused test proves:

```text
OLD HOLD
+ PM_SEVERITY_DEFENSIVE
+ WEAKENING_BUT_INTACT
+ failing campaign economics
+ PIT/campaign valid
+ no recovery
-> NEW REDUCE
```

`FOCUSED_REDUCE_TO_EXIT_DELTA_PROVEN = YES`

Focused test proves:

```text
OLD REDUCE
+ PM_SEVERITY_EXIT_CANDIDATE
+ WORSENING
+ EXIT_GRADE canonical gate
+ failing campaign economics
+ PIT/campaign valid
+ no recovery
-> NEW EXIT
```

`PROHIBITED_ACTION_DELTA_REGRESSIONS = PASS`

Prohibited deltas covered:

- CAUTION -> EXIT
- regime-only -> EXIT
- REDUCE-count-only -> EXIT
- negative-return-only -> EXIT
- missing-history / ambiguous evidence -> EXIT
- recovery -> stale EXIT
- state-only WEAKENING -> EXIT

## Regression Evidence

Command:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/strategy/test_phase31_g8_pm_severity_action_mapping.py tests/strategy/test_phase31_g4_pm_severity_persistence.py tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py tests/strategy/test_phase31_f1i_prior_unrepresentable_reduce_bridge.py tests/strategy/test_phase31_f1d_canonical_sell_semantic_shadow.py -q
```

Result:

```text
42 passed in 1.66s
```

`F1F_F1I_REGRESSION = PASS`

Coverage includes:

- G8 action mapping
- G4 severity evidence
- F1F canonical SELL PM escalation
- F1I strict-prior campaign bridge
- same-day self-count protection
- cross-campaign isolation
- recovery reset
- minimum-notional isolation
- no fake execution event
- PIT future-information guards

## Compile / Diff Checks

Command:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/position_management.py src/ai_fund_lab_v2/strategy/sell_semantic_state.py tests/strategy/test_phase31_g8_pm_severity_action_mapping.py tests/strategy/test_phase31_g4_pm_severity_persistence.py tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py tests/strategy/test_phase31_f1i_prior_unrepresentable_reduce_bridge.py tests/strategy/test_phase31_f1d_canonical_sell_semantic_shadow.py
```

`PY_COMPILE = PASS`

Command:

```bash
git diff --check
```

`GIT_DIFF_CHECK = PASS`

## Runtime Execution

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

No 100BD or long Historical was executed.

## Acceptance

`FOCUSED_TEST_RESULTS = PASS`

`IMPLEMENTATION_ACCEPTANCE_ASSESSMENT = READY_FOR_G9_PRODUCTION_ACCEPTANCE`

## Required Summary Output

`PM_SEVERITY_ACTION_MUTATION_CONNECTED = YES`

`CANONICAL_SELL_STATE_OWNER_CHANGED = NO`

`SECOND_SELL_CLASSIFIER_CREATED = NO`

`PM_ACTION_MAPPING_OWNER = POSITION_MANAGEMENT_PM`

`DEFENSIVE_HOLD_TO_REDUCE_IMPLEMENTED = YES`

`FIRST_OBSERVATION_FULL_EXIT = NO`

`PERSISTENT_REDUCE_TO_EXIT_IMPLEMENTED = YES`

`EXIT_GRADE_EXISTING_EXIT_PRESERVED = YES`

`PROFITABLE_WEAKENING_AUTO_EXIT = NO`

`PROFITABLE_REDUCE_CHAIN_PRESERVED = YES`

`NEGATIVE_RETURN_DIRECT_EXIT = NO`

`RECOVERY_PRE_ACTION_DEESCALATION = YES`

`STALE_EXIT_AFTER_RECOVERY = NO`

`REGIME_ACTION_AUTHORITY = NONE`

`MISSING_EVIDENCE_AUTO_EXIT = NO`

`F1F_F1I_REGRESSION = PASS`

`FOCUSED_HOLD_TO_REDUCE_DELTA_PROVEN = YES`

`FOCUSED_REDUCE_TO_EXIT_DELTA_PROVEN = YES`

`PROHIBITED_ACTION_DELTA_REGRESSIONS = PASS`

`ACTION_MAPPING_OBSERVABILITY = PASS`

`FUTURE_INFORMATION_USED_AS_PRODUCTION_INPUT = NO`

`PERFORMANCE_WINDOW_USED_FOR_PARAMETER_SELECTION = NO`

`PRODUCTION_NUMERIC_THRESHOLD_SELECTED = NO`

`BUY_LOGIC_CHANGED = NO`

`NEW_FEATURE_ADDED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`FOCUSED_TEST_RESULTS = PASS`

`PY_COMPILE = PASS`

`GIT_DIFF_CHECK = PASS`

`IMPLEMENTATION_ACCEPTANCE_ASSESSMENT = READY_FOR_G9_PRODUCTION_ACCEPTANCE`

`NEXT_TASK_RECOMMENDATION = run READ-ONLY G9 production acceptance, then same-window 100BD controlled validation`
