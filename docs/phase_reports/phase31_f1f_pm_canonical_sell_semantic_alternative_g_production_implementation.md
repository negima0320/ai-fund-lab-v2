# Phase31-F1F — PM Canonical SELL Semantic / Alternative G Production Implementation

## PRIMARY_JUDGMENT

PHASE31_F1F_PM_CANONICAL_SELL_SEMANTIC_PRODUCTION_IMPLEMENTED_WITH_REGRESSION_PASS

## IMPLEMENTATION_STATUS

IMPLEMENTED

## Scope

This phase implements the Phase31-F1E authorized scope only:

- Production canonical SELL semantic state evaluation.
- PM-owned discrete-lot persistent-deterioration REDUCE -> EXIT escalation.
- No Strategy/Runtime/PS authority expansion outside PM.
- No fresh-run, resume, replay, or long Historical execution.

## Implementation

Implemented:

- `src/ai_fund_lab_v2/strategy/sell_semantic_state.py`
- `src/ai_fund_lab_v2/strategy/position_management.py`
- `tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py`

The production semantic evidence is embedded per PM position row as:

- `canonical_sell_semantic_evidence`
- `canonical_sell_state`
- `canonical_sell_semantic_contract_version`

The PM row action is mutated from `REDUCE` to `EXIT` only when the full F1E/F1F gate passes.

## Required Fields

PRODUCTION_SELL_SEMANTIC_OWNER = PM

ESCALATION_OWNER = PM

CANONICAL_SELL_SEMANTIC_IMPLEMENTED = YES

PM_DISCRETE_CONTROL_ESCALATION_IMPLEMENTED = YES

ESCALATION_REASON_CODE = pm_discrete_control_persistent_deterioration_exit

ONE_LOT_AUTOMATIC_EXIT = NO

REDUCE_COUNT_ONLY_EXIT = NO

EXISTING_EXIT_AUTHORITY_PRESERVED = YES

MINIMUM_NOTIONAL_MUTATION_AUTHORIZED = NO

MARKET_CONTEXT_LOGIC_CHANGED = NO

PRODUCTION_SHADOW_CONSUMER_COUNT = 0

STRUCTURAL_ESCALATION_ELIGIBLE_COUNT = 95

RECOVERY_BLOCKED_COUNT = 26

MINIMUM_NOTIONAL_EXCLUDED_COUNT = 15

61750_REGRESSION_JUDGMENT = PASS; 2022-09-13 remains WEAKENING_BUT_INTACT / no EXIT, and 2022-09-14 onward is PERSISTENT_DETERIORATION eligible under the F1F PM gate.

FAIL_CLOSED_REGRESSION = PASS

EXISTING_SELL_REGRESSION = PASS

FUTURE_INFORMATION_USED = NO

OUTCOME_USED_FOR_PARAMETER_SELECTION = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

## Canonical States

Implemented canonical SELL states:

- HEALTHY_OR_RECOVERING
- WEAKENING_BUT_INTACT
- PERSISTENT_DETERIORATION
- EXIT_GRADE
- UNRESOLVED

Aggregate PASS semantics:

EVIDENCE_AVAILABLE_NOT_HEALTH_SIGNAL

`PASS` from continuation/downside evidence is not interpreted as a health signal by itself. It remains evidence availability / compatibility, consistent with F1B/F1C/F1E.

## Escalation Gate

PM materializes final `EXIT` only when all conditions are true:

- Baseline PM action is `REDUCE`.
- Representability family is `DISCRETE_LOT`.
- Final partial REDUCE quantity is `0`.
- No valid intermediate lot exposure exists.
- Canonical state is `PERSISTENT_DETERIORATION`.
- Recovery guard is absent.
- PIT proof passes.
- Campaign identity is complete.
- Minimum-notional flag is false.
- PM is the materializing authority.

Otherwise PM preserves the baseline action.

## Protection Cases

Protected by tests:

- First one-lot weakening REDUCE stays `REDUCE`.
- Persistent discrete-lot deterioration escalates inside PM.
- Recovery reset blocks escalation.
- Existing PM `EXIT` remains unchanged.
- Minimum-notional REDUCE remains unresolved/preserved and does not escalate.
- Future-dated PIT evidence fails closed.
- Ambiguous campaign identity fails closed.

## Current-Run Structural Evidence

READ-ONLY source:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260820T120909096218Z/daily/*/diagnostic_shadow/canonical_sell_semantic_shadow.json`

No new Historical run was executed.

Artifact count = 42

TOTAL_POSITION_DAY_ROWS = 458

Canonical state counts:

- HEALTHY_OR_RECOVERING = 244
- WEAKENING_BUT_INTACT = 44
- PERSISTENT_DETERIORATION = 95
- EXIT_GRADE = 60
- UNRESOLVED = 15

STRUCTURAL_ESCALATION_ELIGIBLE_COUNT = 95

RECOVERY_BLOCKED_COUNT = 26

MINIMUM_NOTIONAL_EXCLUDED_COUNT = 15

61750 evidence:

- 2022-09-13 = REDUCE / WEAKENING_BUT_INTACT / no Alternative G candidate
- 2022-09-14 onward = REDUCE / PERSISTENT_DETERIORATION / Alternative G candidate

Under F1F production PM logic, the 2022-09-14 persistent discrete-lot condition is the first date eligible for PM-owned `EXIT` materialization.

## Regression Results

TEST_RESULTS = PASS

Commands:

```bash
python3 -m pytest tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py -q
python3 -m pytest tests/strategy/test_phase31_f1d_canonical_sell_semantic_shadow.py -q
python3 -m pytest tests/strategy/test_phase22_d_position_management.py -q
python3 -m pytest tests/strategy/test_phase22_g_runtime_planning.py -q
python3 -m pytest tests/strategy/test_phase31_c0d_unrepresentable_reduce_exit_shadow.py -q
PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache python3 -m py_compile src/ai_fund_lab_v2/strategy/sell_semantic_state.py src/ai_fund_lab_v2/strategy/position_management.py tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py
```

Results:

- F1F PM canonical SELL semantic integration: 7 passed
- F1D canonical SELL semantic shadow: 10 passed
- Phase22 position management: 22 passed
- Phase22 runtime planning: 48 passed
- C0D unrepresentable REDUCE shadow: 9 passed

Total focused tests = 96 passed

PY_COMPILE = PASS

## Git Diff Check

GIT_DIFF_CHECK = PASS

F1F touched only:

- `src/ai_fund_lab_v2/strategy/sell_semantic_state.py`
- `src/ai_fund_lab_v2/strategy/position_management.py`
- `tests/strategy/test_phase31_f1f_pm_canonical_sell_semantic_integration.py`
- `docs/phase_reports/phase31_f1f_pm_canonical_sell_semantic_alternative_g_production_implementation.md`

Existing unrelated working-tree changes from prior phases were not reverted.

## Authority Boundary

PS / Runtime do not invent `EXIT`.

Runtime planning continues to consume PM `REDUCE` as sell-reduce intent and PM `EXIT` as sell-exit intent. The F1F mutation point is PM only.

Minimum-notional remains excluded from mutation authority.

Market Context logic is unchanged.

## NEXT_TASK_RECOMMENDATION

Run the next clean validation on a fresh branch or explicitly scoped working tree, using normal Historical validation only after this production semantic change is accepted.
