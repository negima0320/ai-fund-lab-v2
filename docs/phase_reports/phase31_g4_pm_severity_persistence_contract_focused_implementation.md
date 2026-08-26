# Phase31-G4 — PM Severity / Persistence Contract Focused Production Implementation

## Scope

Task type: focused production implementation + regression.

Implemented the Phase31-G3 PM severity / persistence contract as a PM-owned evidence layer attached to the existing canonical SELL semantic authority.

No BUY logic, Candidate generation, ranking, retraining, indicators, Market Context authority, execution feasibility, Pending, Submit, Runtime, fresh-run, resume, replay, or long Historical execution was changed.

## Primary Judgment

`PRIMARY_JUDGMENT = PHASE31_G4_PM_SEVERITY_PERSISTENCE_IMPLEMENTED_ACCEPTED`

The implementation adds production-visible PM severity and persistence evidence without creating a second SELL classifier or moving canonical SELL state ownership away from `strategy.sell_semantic_state`.

## Implementation Summary

Touched production files:

- `src/ai_fund_lab_v2/strategy/sell_semantic_state.py`
- `src/ai_fund_lab_v2/strategy/position_management.py`

Added focused regression:

- `tests/strategy/test_phase31_g4_pm_severity_persistence.py`

The new PM evidence fields are:

- `pm_severity`
- `pm_severity_reasons`
- `pm_severity_evidence`
- `persistence_state`
- `pm_severity_contract_version`

PM severity is derived from canonical SELL state, strict-prior same-campaign persistence evidence, campaign-basis return sign, recovery evidence, and optional regime modifier evidence. It does not calculate new indicators and does not add numeric thresholds.

## Contract Results

`PM_SEVERITY_IMPLEMENTED = YES`

`CANONICAL_SELL_STATE_OWNER_CHANGED = NO`

`SECOND_SELL_CLASSIFIER_CREATED = NO`

`PM_SEVERITY_STATES = PM_SEVERITY_NORMAL; PM_SEVERITY_CAUTION; PM_SEVERITY_DEFENSIVE; PM_SEVERITY_EXIT_CANDIDATE; PM_SEVERITY_UNRESOLVED`

`STRICT_PRIOR_PERSISTENCE = YES`

`SAME_DAY_SELF_COUNT = 0`

`CROSS_CAMPAIGN_HISTORY_LEAK = 0`

`RECOVERY_DEESCALATION_IMPLEMENTED = YES`

`PROFITABLE_WEAKENING_AUTO_EXIT = NO`

`HEALTHY_PULLBACK_OPTIONALITY_PRESERVED = YES`

`LOSER_SEVERITY_ESCALATION_IMPLEMENTED = YES`

`PM_EXIT_AUTHORITY_PRESERVED = YES`

`REDUCE_COUNT_DIRECT_EXIT_RULE = NO`

`REGIME_DIRECT_EXIT_RULE = NO`

`FUTURE_MFE_USED = NO`

`FINAL_CAMPAIGN_OUTCOME_USED = NO`

`NEW_NUMERIC_THRESHOLD_ADDED = NO`

`MISSING_EVIDENCE_AUTO_EXIT = NO`

`F1F_F1I_REGRESSION = PASS`

`PM_SEVERITY_OBSERVABILITY = PASS`

`WINNER_PRESERVATION_REGRESSIONS = PASS`

`FUTURE_INFORMATION_USED_AS_PRODUCTION_INPUT = NO`

`PERFORMANCE_WINDOW_USED_FOR_PARAMETER_SELECTION = NO`

`STRATEGY_SCOPE_CHANGED = PM_SEVERITY_ONLY`

`BUY_LOGIC_CHANGED = NO`

`NEW_FEATURE_ADDED = NO`

`FRESH_RUN_EXECUTED = NO`

`RESUME_EXECUTED = NO`

`LONG_HISTORICAL_EXECUTED = NO`

## Focused Regression Evidence

Command:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/strategy/test_phase31_g4_pm_severity_persistence.py tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py tests/strategy/test_phase31_f1i_prior_unrepresentable_reduce_bridge.py -q
```

Result:

```text
22 passed in 1.58s
```

Covered cases:

- profitable temporary weakening remains `PM_SEVERITY_CAUTION` and does not become full EXIT
- recovery de-escalates to `PM_SEVERITY_NORMAL` / `RECOVERED`
- persistent discrete-lot loser reaches `PM_SEVERITY_EXIT_CANDIDATE` through existing PM authority
- repeated REDUCE count alone does not force EXIT for a profitable representable winner
- regime-only adversity does not create EXIT authority
- same-day current observation remains `FIRST_OBSERVATION`
- cross-campaign prior evidence does not leak into a new campaign
- missing/ambiguous evidence becomes `PM_SEVERITY_UNRESOLVED` without auto-EXIT
- F1F and F1I focused regressions still pass

## Compile / Diff Checks

Command:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/sell_semantic_state.py src/ai_fund_lab_v2/strategy/position_management.py tests/strategy/test_phase31_g4_pm_severity_persistence.py
```

Result:

`PY_COMPILE = PASS`

Command:

```bash
git diff --check
```

Result:

`GIT_DIFF_CHECK = PASS`

## Acceptance

`FOCUSED_TEST_RESULTS = PASS`

`PY_COMPILE = PASS`

`GIT_DIFF_CHECK = PASS`

`IMPLEMENTATION_ACCEPTANCE_ASSESSMENT = ACCEPTED`

## Next Task Recommendation

`NEXT_TASK_RECOMMENDATION = run user-operated clean validation or resume decision task; if performance behavior changes, audit PM severity observability before tuning`
