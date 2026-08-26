# Phase31-F1Z6 — Generic NOT_EXECUTABLE Terminal Consumer Compatibility Repair

## PRIMARY_JUDGMENT

PHASE31_F1Z6_GENERIC_NOT_EXECUTABLE_TERMINAL_CONSUMER_REPAIR_ACCEPTED

## Scope

This phase implemented a focused Production-common consumer repair. It did not change Strategy, PM SELL semantics, BUY logic, valuation policy, broker behavior, execution fill logic, or Historical runtime orchestration.

No fresh-run, resume, replay, or long Historical execution was performed.

## Root Cause Addressed

F1Z2 correctly terminalized execution-authority-unavailable item submission as item state `NOT_EXECUTABLE`, with no order/fill/cash/position mutation. Downstream consumer compatibility was incomplete: `PendingReviewScopeAuthority` did not classify `NOT_EXECUTABLE` as a terminal item, so current valuation pre-gate and Historical Safety temporal authority treated an otherwise terminal residual Pending plan as active `REVIEW_REQUIRED`.

## Implementation Summary

Changed:

- `src/ai_fund_lab_v2/runtime_v2/pending/review_scope_authority.py`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/safety_temporal_authority.py`
- `tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py`

Added a generic terminal item state set:

- `CONSUMED`
- `EXPIRED`
- `CANCELLED`
- `SUPERSEDED`
- `NOT_EXECUTABLE`

`NOT_EXECUTABLE` is terminal only when canonical item evidence is safety-qualified:

- item state is `NOT_EXECUTABLE`
- `approved` is false
- explicit `feasibility_status` exists
- same-day retry is not true when `retry_eligible_same_day` exists
- no submitted/accepted/order/ledger/fill side-effect id is present
- no submit/order/fill/cash/position mutation flag is true
- contradictory submit status is absent

Malformed or contradictory `NOT_EXECUTABLE` evidence remains fail-closed via `not_executable_terminal_evidence_invalid:<pending_item_id>`.

## Canonical Consumer Behavior

`PendingReviewScopeAuthority` now includes safely-qualified `NOT_EXECUTABLE` items in `terminal_item_ids` and exposes `non_terminal_item_ids`.

`pending_scope_allows_current_valuation_residual()` now supports two safe residual forms:

- existing `BUY_ITEM_SCOPED_REVIEW` residual BUY review contract
- terminal-only `REVIEW_REQUIRED` Pending where every item is terminal and there are no executable, reviewed, retryable, or ambiguous residual items

Historical Safety uses the same current valuation Pending scope adapter, avoiding a second local classification.

## Production-Shaped Regression

Added a 2022-12-09-shaped fixture:

- `75590 BUY CONSUMED`
- `34940 SELL NOT_EXECUTABLE`
- `56100 SELL CONSUMED`

Expected result:

- Pending readiness = READY
- Historical pending safety authority = READY
- Historical daily neutral safety compatibility = READY
- current valuation pre-gate can reach producer

This proves only pre-gate compatibility. It does not assert valuation price availability or valuation output for 34940.

## Fail-Closed Regressions Preserved

Verified:

- malformed `NOT_EXECUTABLE` without explicit feasibility fails closed
- `NOT_EXECUTABLE` with unknown ledger/order side effect fails closed
- reviewed SELL remains fail-closed
- retryable approved item remains fail-closed
- existing residual BUY review behavior remains valid
- Pending lifecycle regressions remain valid
- Data Readiness regressions remain valid
- Historical Safety temporal authority regressions remain valid

## Tests Executed

All commands were local focused tests only:

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py -q
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase30_ak9r27_pending_review_scope_authority.py -q
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase30_ak9r28_historical_safety_temporal_authority.py -q
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py -q
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase15aq_runtime_data_readiness_gate.py -q
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase15as_data_readiness_semantic_consistency.py -q
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m pytest tests/runtime_v2/test_phase31_f1w_item_scoped_partial_submit.py -q
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m py_compile src/ai_fund_lab_v2/runtime_v2/pending/review_scope_authority.py src/ai_fund_lab_v2/runtime_v2/historical_support/safety_temporal_authority.py tests/runtime_v2/test_phase17_ab_current_valuation_pre_gate_authority.py
git diff --check
```

Results:

- `test_phase17_ab_current_valuation_pre_gate_authority.py`: 21 passed
- `test_phase30_ak9r27_pending_review_scope_authority.py`: 8 passed
- `test_phase30_ak9r28_historical_safety_temporal_authority.py`: 12 passed
- `test_phase15ar_pending_lifecycle_stale_handling.py`: 41 passed
- `test_phase15aq_runtime_data_readiness_gate.py`: 9 passed
- `test_phase15as_data_readiness_semantic_consistency.py`: 9 passed
- `test_phase31_f1w_item_scoped_partial_submit.py`: 4 passed
- `py_compile`: PASS
- `git diff --check`: PASS

## Required Output

PRIMARY_JUDGMENT = PHASE31_F1Z6_GENERIC_NOT_EXECUTABLE_TERMINAL_CONSUMER_REPAIR_ACCEPTED

PENDING_REVIEW_SCOPE_AUTHORITY_UPDATED = YES

NOT_EXECUTABLE_INCLUDED_IN_TERMINAL_ITEM_IDS = YES

NOT_EXECUTABLE_REASON_SPECIFIC_BRANCHING_USED = NO

SYMBOL_SPECIFIC_BRANCHING_USED = NO

DATE_SPECIFIC_BRANCHING_USED = NO

CURRENT_VALUATION_ADAPTER_READY_FOR_TERMINAL_ONLY_PENDING = YES

HISTORICAL_SAFETY_CONSUMES_CANONICAL_PENDING_SCOPE = YES

MALFORMED_NOT_EXECUTABLE_FAILS_CLOSED = YES

UNKNOWN_SIDE_EFFECT_FAILS_CLOSED = YES

REVIEWED_SELL_FAILS_CLOSED = YES

RETRYABLE_APPROVED_ITEM_FAILS_CLOSED = YES

STRATEGY_CHANGED = NO

PM_SELL_SEMANTICS_CHANGED = NO

BUY_LOGIC_CHANGED = NO

VALUATION_POLICY_CHANGED = NO

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED_BY_CODEX = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

NEXT_ACTION_RECOMMENDATION = Operator may run the scoped resume/readiness validation after reviewing this repair. Treat any later 34940 valuation price availability failure as a separate valuation evidence issue, not as Pending terminal consumer incompatibility.
