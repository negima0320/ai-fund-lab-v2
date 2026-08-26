# Phase31-G9 - G8 PM Severity Action-Mapping Production Acceptance / Same-Window 100BD Readiness

## Scope

Task type: READ-ONLY PRODUCTION ACCEPTANCE + CONTROLLED VALIDATION READINESS.

No implementation, Strategy mutation, PM mutation, SELL rule mutation, threshold tuning, config change, feature addition, Runtime mutation, fresh-run, resume, replay, or Historical rerun was performed in G9.

Authority read:

- `docs/phase_reports/phase31_g8_pm_severity_action_mapping_focused_implementation.md`
- `docs/phase_reports/phase31_g7_pm_severity_action_mapping_design.md`
- `docs/phase_reports/phase31_g6_g4_same_window_100bd_behavioral_activation_no_delta_audit.md`
- `docs/phase_reports/phase31_g5_g4_pm_severity_production_acceptance_same_window_100bd_readiness.md`
- `docs/phase_reports/phase31_g4_pm_severity_persistence_contract_focused_implementation.md`
- `docs/phase_reports/phase31_g3_pit_safe_pm_severity_persistence_contract_design.md`
- `docs/phase_reports/phase31_g2_pit_safe_pm_severity_persistence_hold_regret_audit.md`
- `src/ai_fund_lab_v2/strategy/position_management.py`
- `src/ai_fund_lab_v2/strategy/sell_semantic_state.py`
- focused G8/G4/F1F/F1I/F1D tests

## Primary Judgment

`PRIMARY_JUDGMENT = PHASE31_G9_G8_PM_SEVERITY_ACTION_MAPPING_ACCEPTED_READY_FOR_CLEAN_SAME_WINDOW_100BD`

G8 is production-accepted for one controlled same-window 100BD validation. The implementation connects PM severity to PM-owned final action selection without moving canonical SELL state ownership, creating a second SELL classifier, adding numeric production thresholds, or giving PS/Runtime new action authority.

## Architecture Acceptance

`G8_SCOPE_CONFORMANCE = PASS`

G8 production behavior is limited to PM-owned severity action mapping in `position_management.py`. No evidence was found that G8 changed BUY, Candidate, ranking, ADD logic, model, feature generation, Market Context authority, PS quantity authority, Runtime SELL authority, Pending, Submit, execution, valuation, or Safety.

`PM_SEVERITY_ACTION_MUTATION_CONNECTED = YES`

`ACTION_MAPPING_EXECUTION_ORDER = PASS`

The production flow is:

1. `strategy.sell_semantic_state.evaluate_position_sell_semantic(...)` produces canonical SELL state, PM severity, campaign economics, persistence, recovery, regime modifier evidence, and PIT proof.
2. `position_management._apply_pm_severity_action_mapping(...)` consumes that evidence.
3. The mapped `final_pm_action` is materialized into the PM row action by `_apply_canonical_sell_semantics(...)`.
4. Downstream feasibility / Pending / Submit / execution consume the already-materialized PM action.

This places G8 action mapping before final PM action is frozen for downstream planning.

`CANONICAL_SELL_STATE_OWNER_PRESERVED = YES`

`SECOND_SELL_CLASSIFIER_COUNT = 0`

Canonical SELL state remains produced by `strategy.sell_semantic_state`. G8 does not independently classify deterioration; it maps severity evidence into PM-owned action deltas.

`PM_ACTION_MAPPING_OWNER = POSITION_MANAGEMENT_PM`

`PS_RUNTIME_ACTION_INVENTION = NO`

Only PM / `position_management` mutates `HOLD -> REDUCE` and `REDUCE -> EXIT` under G8. PS and Runtime remain quantity, lot representability, feasibility, Pending, Submit, and execution consumers.

## Behavioral Delta Acceptance

`HOLD_TO_REDUCE_ACTION_DELTA_ACCEPTED = PASS`

Focused regression proves baseline `HOLD` plus `PM_SEVERITY_DEFENSIVE`, canonical weakening/deterioration, failing campaign economics, valid PIT/campaign identity, and no recovery can become `REDUCE`.

`REDUCE_TO_EXIT_ACTION_DELTA_ACCEPTED = PASS`

Focused regression proves baseline `REDUCE` plus defensive/exit-candidate severity, persistent/worsening state, failing campaign economics, no recovery, and canonical PM/F1F EXIT gate can become `EXIT`.

`FIRST_OBSERVATION_FULL_EXIT = NO`

Focused regression preserves first-observation protection: defensive first observation can preserve or reduce where allowed, but cannot create `REDUCE -> EXIT` solely from first observation.

## Winner / Recovery / Persistence Guards

`WINNER_PRESERVATION_ACTION_GATE = PASS`

The G8 focused cases preserve the prohibited deltas:

- CAUTION does not become full EXIT solely from severity.
- positive-return weakening does not become full EXIT solely from severity.
- regime-only deterioration does not become full EXIT.
- REDUCE-count-only does not become full EXIT.
- negative-return-only does not become full EXIT.
- state-only `WEAKENING_BUT_INTACT` does not become full EXIT.

`PROFITABLE_REDUCE_CHAIN_PRESERVED = YES`

Profitable weakening/reduce chains remain preservable and do not receive severity-only full EXIT.

`RECOVERY_PRE_ACTION_DEESCALATION = PASS`

Recovery evidence is included in canonical severity evidence before G8 action mapping. The common action gate rejects recovery-present / de-escalated evidence before mutating action.

`STALE_EXIT_AFTER_RECOVERY = NO`

`PERMANENT_DETERIORATION_DEBT = NO`

Recovery can block stale severity escalation and does not leave hidden permanent deterioration debt in G8 action mapping.

`STRICT_PRIOR_PERSISTENCE_ACCEPTANCE = PASS`

`SAME_DAY_SELF_COUNT = 0`

`CROSS_CAMPAIGN_HISTORY_LEAK = 0`

G4/G8 evidence keeps strict-prior same-campaign persistence semantics. Same-day self-count remains zero, and cross-campaign history leak remains zero.

`MISSING_EVIDENCE_AUTO_EXIT = NO`

`AMBIGUOUS_EVIDENCE_FAIL_SAFE = PASS`

Missing or ambiguous canonical state, campaign identity, campaign economics, persistence, recovery, or PIT proof does not create new severity-based EXIT. The common gate fail-closes to preserve baseline action rather than inventing EXIT.

## F1F / F1I Preservation

`F1F_F1I_COMPATIBILITY = PASS`

Focused regressions covering canonical SELL, discrete-lot unrepresentable REDUCE escalation, minimum-notional isolation, same-day self-count guard, strict-prior campaign evidence, recovery reset, no fake execution, and no PS/Runtime EXIT invention all passed.

G8 does not replace or bypass existing PM-owned escalation. It requires canonical EXIT-grade or existing PM escalation gate for `REDUCE -> EXIT`.

## Threshold / PIT / Observability Acceptance

`DIAGNOSTIC_DERIVED_NUMERIC_THRESHOLD_COUNT = 0`

No G0-G8-derived numeric production threshold was introduced. G8 uses semantic distinctions: campaign basis profitable/failing, first observation versus strict-prior persistence, worsening, canonical gate, and recovery.

`FUTURE_INFORMATION_USED_AS_PRODUCTION_INPUT = NO`

G8 production mapping consumes current canonical SELL / PM severity evidence with PIT proof and explicit `future_information_used = False`. It does not consume future MFE, final campaign PnL, future return, later winner/loser classification, future regime, or later EXIT date.

`ACTION_MAPPING_OBSERVABILITY_ACCEPTANCE = PASS`

G8 PM rows expose the required audit fields:

- `baseline_final_pm_action`
- `final_pm_action`
- `final_pm_intensity`
- `pm_severity`
- `canonical_sell_state`
- `persistence_state`
- campaign economics modifier
- recovery evidence
- regime modifier evidence
- PIT proof
- `pm_severity_action_mapping_decision`
- `pm_severity_action_mapping_reason_code`
- `pm_severity_action_mapping_contract_version`

## Controlled Validation Contract

`CONTROLLED_100BD_COMPARISON_CONTRACT = LOCKED`

Next validation must use:

- profile: `historical-extended-smoke`
- start: `2022-08-15`
- business days: `100`
- initial cash: `1,000,000`

No performance-related config changes are allowed.

`PERFORMANCE_ONLY_ACCEPTANCE_PROHIBITED = YES`

The next audit must compare portfolio, campaign economics, PM behavioral deltas, winner safety, loser improvement, and exact changed campaigns. Final return alone is not an acceptance criterion.

`POST_VALIDATION_IMMEDIATE_TUNING = PROHIBITED`

After the same-window 100BD validation, do not tune immediately whether performance improves or worsens. First perform causal OLD-vs-NEW audit.

## Focused Acceptance Evidence

Command:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/strategy/test_phase31_g8_pm_severity_action_mapping.py tests/strategy/test_phase31_g4_pm_severity_persistence.py tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py tests/strategy/test_phase31_f1i_prior_unrepresentable_reduce_bridge.py tests/strategy/test_phase31_f1d_canonical_sell_semantic_shadow.py -q
```

Result:

```text
42 passed in 1.46s
```

`FOCUSED_TEST_RESULTS = PASS`

Command:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/position_management.py src/ai_fund_lab_v2/strategy/sell_semantic_state.py tests/strategy/test_phase31_g8_pm_severity_action_mapping.py tests/strategy/test_phase31_g4_pm_severity_persistence.py tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py tests/strategy/test_phase31_f1i_prior_unrepresentable_reduce_bridge.py tests/strategy/test_phase31_f1d_canonical_sell_semantic_shadow.py
```

Result:

`PY_COMPILE = PASS`

Command:

```bash
git diff --check
```

Result:

`GIT_DIFF_CHECK = PASS`

## Required Summary

`PRIMARY_JUDGMENT = PHASE31_G9_G8_PM_SEVERITY_ACTION_MAPPING_ACCEPTED_READY_FOR_CLEAN_SAME_WINDOW_100BD`

`G8_SCOPE_CONFORMANCE = PASS`

`PM_SEVERITY_ACTION_MUTATION_CONNECTED = YES`

`ACTION_MAPPING_EXECUTION_ORDER = PASS`

`CANONICAL_SELL_STATE_OWNER_PRESERVED = YES`

`SECOND_SELL_CLASSIFIER_COUNT = 0`

`PM_ACTION_MAPPING_OWNER = POSITION_MANAGEMENT_PM`

`PS_RUNTIME_ACTION_INVENTION = NO`

`HOLD_TO_REDUCE_ACTION_DELTA_ACCEPTED = PASS`

`REDUCE_TO_EXIT_ACTION_DELTA_ACCEPTED = PASS`

`FIRST_OBSERVATION_FULL_EXIT = NO`

`WINNER_PRESERVATION_ACTION_GATE = PASS`

`PROFITABLE_REDUCE_CHAIN_PRESERVED = YES`

`RECOVERY_PRE_ACTION_DEESCALATION = PASS`

`STALE_EXIT_AFTER_RECOVERY = NO`

`PERMANENT_DETERIORATION_DEBT = NO`

`STRICT_PRIOR_PERSISTENCE_ACCEPTANCE = PASS`

`SAME_DAY_SELF_COUNT = 0`

`CROSS_CAMPAIGN_HISTORY_LEAK = 0`

`MISSING_EVIDENCE_AUTO_EXIT = NO`

`AMBIGUOUS_EVIDENCE_FAIL_SAFE = PASS`

`F1F_F1I_COMPATIBILITY = PASS`

`DIAGNOSTIC_DERIVED_NUMERIC_THRESHOLD_COUNT = 0`

`FUTURE_INFORMATION_USED_AS_PRODUCTION_INPUT = NO`

`ACTION_MAPPING_OBSERVABILITY_ACCEPTANCE = PASS`

`CONTROLLED_100BD_COMPARISON_CONTRACT = LOCKED`

`PERFORMANCE_ONLY_ACCEPTANCE_PROHIBITED = YES`

`POST_VALIDATION_IMMEDIATE_TUNING = PROHIBITED`

`IMPLEMENTATION_CHANGED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

`FOCUSED_TEST_RESULTS = PASS; 42 passed in 1.46s`

`PY_COMPILE = PASS`

`GIT_DIFF_CHECK = PASS`

`VALIDATION_READINESS = READY_FOR_CLEAN_SAME_WINDOW_100BD`

`USER_OPERATED_NEXT_COMMAND = PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-extended-smoke --start-date 2022-08-15 --business-days 100 --initial-cash 1000000 --confirm --yes-i-understand-this-mutates-trading-state`

## User-Operated Next Command

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --start-date 2022-08-15 \
  --business-days 100 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```
