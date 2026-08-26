# Phase31-F1Z9 — Generic Terminal-Only Pending Cross-Day Lifecycle Closure Repair

## PRIMARY_JUDGMENT

PHASE31_F1Z9_GENERIC_TERMINAL_ONLY_PENDING_CROSS_DAY_LIFECYCLE_CLOSURE_REPAIRED

## Scope

This phase implemented a focused Production-common Pending lifecycle repair. It did not change Strategy, PM SELL semantics, BUY logic, Data Readiness semantics, Historical Safety semantics, valuation policy, or Runtime execution semantics.

No fresh-run, resume, replay, or long Historical execution was performed.

Changed for F1Z9:

- `src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py`
- `tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py`
- this report

## Architecture Direction

```text
ARCHITECTURE_DIRECTION = GENERALIZED_TERMINAL_STATE_MACHINE
```

The lifecycle runner now consumes `PendingReviewScopeAuthority` for terminal-only prior-day Pending closure. It does not duplicate terminal item classification and does not branch on symbol, date, or `EXECUTION_AUTHORITY_UNAVAILABLE`.

## Repair Summary

Added a generic closure authority:

```text
_terminal_only_cross_day_closure_authority
```

Predicate:

```text
target_session_date < business_date
state = REVIEW_REQUIRED
PendingReviewScopeAuthority.structural_validity = PASS
terminal_item_ids present
non_terminal_item_ids = []
reviewed_item_ids = []
executable_item_ids = []
batch_blocked = false
post_send_unknown_detected = false
```

When the predicate passes:

```text
new_state = EXPIRED
reason = GENERIC_TERMINAL_ONLY_PRIOR_DAY_PENDING_EXPIRED
empty_slot = true
```

The old Pending remains archived in lifecycle history, but no longer participates in next-day authority or decisions.

## Closure State

```text
CANONICAL_PLAN_CLOSURE_STATE = EXPIRED
```

This reuses existing lifecycle semantics for prior-day residual Pending that should no longer be active authority. It avoids inventing a competing plan-state model.

## Actual Run Static Trace

Target run:

```text
runtime-test-historical-extended-smoke-20260821T050423121340Z
```

Active Pending:

```text
pending_plan_id = pending-strategy-plan-historical-2022-12-09-055b6551b8aef624
state = REVIEW_REQUIRED
target_session_date = 2022-12-09
business_date = 2022-12-12
items = 75590 BUY CONSUMED; 34940 SELL NOT_EXECUTABLE; 56100 SELL CONSUMED
```

Repaired static predicate result:

```text
AUTH_STATUS = PASS
terminal_item_count = 3
non_terminal_item_count = 0
true_review_count = 0
retryable_count = 0
post_send_unknown_detected = false
closure_state = EXPIRED
```

Note: legacy `_submit_attempt_evidence.unknown_submit_risk` remains true when a submit attempt occurred, for compatibility with existing lifecycle callers. F1Z9 distinguishes unresolved post-send unknown from known submitted terminal side effects by using `post_send_unknown_detected`. The actual 12/09 submit had a known pass state, not `POST_SEND_UNKNOWN`.

## Regression Coverage

Added focused tests for:

- actual 12/09 terminal-only shape closing on 12/12
- CONSUMED-only prior-day closure
- CONSUMED + safely-qualified `NOT_EXECUTABLE` mixed closure
- reviewed SELL fail-closed
- true reviewed BUY fail-closed
- retryable approved item fail-closed
- malformed `NOT_EXECUTABLE` fail-closed
- unknown side-effect `NOT_EXECUTABLE` fail-closed
- same-day terminal-only Pending evidence preserved

## Focused Test Results

Executed local focused regression only:

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py -q
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase30_ak9r27_pending_review_scope_authority.py -q
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py -q
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase30_ak9r28_historical_safety_temporal_authority.py -q
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py tests/runtime_v2/test_phase15as_data_readiness_semantic_consistency.py -q
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py -q
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase31_f1l_same_day_sell_pending_idempotency.py -q
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py
git diff --check
```

Results:

- Pending lifecycle stale handling: 50 passed
- PendingReviewScopeAuthority regressions: 8 passed
- current valuation pre-gate / F1Z6 regressions: 21 passed
- Historical Safety temporal authority regressions: 12 passed
- Data Readiness regressions: 18 passed
- F1W/F1Z2 Submit terminal regressions: 4 passed
- F1L/F1Y same-day SELL Pending idempotency regressions: 20 passed
- `py_compile`: PASS
- `git diff --check`: PASS

## Resume Assessment

Static post-repair resume path:

```text
resume
-> 2022-12-12:data_readiness
-> pre-data-readiness Pending lifecycle
-> detect prior-day terminal-only REVIEW_REQUIRED Pending
-> close old plan as EXPIRED and empty active slot
-> Data Readiness evaluates without stale 2022-12-09 Pending authority
-> next-day authority must come from fresh 2022-12-12 PIT/PM/Planning/Pending evidence
```

```text
RESUME_ASSESSMENT = NORMAL_RESUME_SAFE
```

## Required Output

PRIMARY_JUDGMENT = PHASE31_F1Z9_GENERIC_TERMINAL_ONLY_PENDING_CROSS_DAY_LIFECYCLE_CLOSURE_REPAIRED

ARCHITECTURE_DIRECTION = GENERALIZED_TERMINAL_STATE_MACHINE

SHARED_PENDING_SCOPE_AUTHORITY = YES

CANONICAL_PLAN_CLOSURE_STATE = EXPIRED

20221212_TERMINAL_ONLY_CROSS_DAY_CLOSURE_REGRESSION = PASS

STALE_INTENT_CARRY_FORWARD = NO

NEXT_DAY_FRESH_DECISION_REQUIRED = YES

TRUE_REVIEW_FAIL_CLOSED = PASS

RETRYABLE_ITEM_FAIL_CLOSED = PASS

UNKNOWN_SIDE_EFFECT_FAIL_CLOSED = PASS

SAME_DAY_PENDING_EVIDENCE_PRESERVED = PASS

REASON_SPECIFIC_BRANCHING_USED = NO

SYMBOL_SPECIFIC_BRANCHING_USED = NO

DATE_SPECIFIC_BRANCHING_USED = NO

DATA_READINESS_CODE_CHANGED = NO

HISTORICAL_SAFETY_CODE_CHANGED = NO

STRATEGY_CHANGED = NO

PM_SELL_SEMANTICS_CHANGED = NO

BUY_LOGIC_CHANGED = NO

VALUATION_POLICY_CHANGED = NO

FUTURE_INFORMATION_USED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

FOCUSED_TEST_RESULTS = PASS

PY_COMPILE = PASS

GIT_DIFF_CHECK = PASS

RESUME_ASSESSMENT = NORMAL_RESUME_SAFE

NEXT_TASK_RECOMMENDATION = Run focused acceptance, then operator resume of the clean 100BD run. If a later stage halts, audit that new actual artifact independently rather than changing F1Z9.
