# Phase29-L20H - Mixed-Outcome Item-Level Order Lifecycle Authority Repair

Task ID: Phase29-L20H

Mode:

```text
IMPLEMENTATION + SHORT REGRESSION
NO CURRENT HALTED RUN MUTATION
NO RESUME / FRESH-RUN / RUN / PENDING_LIFECYCLE ON CURRENT RUN / REPAIR
NO LONG HISTORICAL EXECUTION
```

## Primary Judgment

```text
PHASE29_L20H_MIXED_ITEM_LIFECYCLE_AUTHORITY_IMPLEMENTED_SHORT_REGRESSION_PASS
```

L20H implements the L20G target model:

```text
ITEM-LEVEL TERMINAL STATE AUTHORITY
+
DERIVED PLAN STATE
```

The repair is Production-common in shape but Historical CA terminalization
remains guarded by Historical-only evidence. Production/Demo unresolved
Corporate Action remains fail-closed.

## Implemented Design

Execution now detects mixed lifecycle work even when submitted orders exist:

```text
submitted order exists
+ active Pending has sibling Corporate Action NOT_SUBMITTED item
+ filled sibling is proven by orderlist/ledger evidence
+ no broker uncertainty
-> pending_terminalization_status = PENDING_LIFECYCLE_REQUIRED
```

Pending lifecycle now revalidates the same authority before mutation:

```text
FILLED item
+ QUARANTINED_NOT_SUBMITTED item
+ all items terminal
+ no POST_SEND_UNKNOWN / broker uncertainty
-> derived plan terminal state = CONSUMED
-> history retains item_lifecycle_authority
-> current Pending slot becomes EMPTY
```

The previous L20D all-items CA quarantine path is unchanged:

```text
all items CA quarantine
+ submitted_count == 0
-> EXPIRED history
-> EMPTY current slot
```

## Changed Files

```text
src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py
src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py
src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py
scripts/runtime_test.py
tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py
tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py
tests/runtime_v2/test_phase17_k_runtime_test_runner.py
docs/phase_reports/phase29_l20h_mixed_outcome_item_level_order_lifecycle_authority_repair.md
```

## Item Outcomes

Implemented item outcomes for this repair:

```text
FILLED
QUARANTINED_NOT_SUBMITTED
REVIEW_REQUIRED
```

`POST_SEND_UNKNOWN` is not terminalized. Generic blocked/rejected or unresolved
review conditions remain REVIEW_REQUIRED unless a future task defines a safe
terminal classification.

## BUY / SELL Independence

Preserved:

```text
BUY quarantine / REVIEW does not block valid SELL execution.
SELL quarantine / REVIEW does not invalidate valid BUY fill.
```

The filled sibling is not rolled back or reinterpreted. Ledger/current behavior
remains owned by Execution/current projection.

## Safety

Fail-closed behavior preserved:

```text
POST_SEND_UNKNOWN -> REVIEW_REQUIRED
broker uncertainty -> REVIEW_REQUIRED
generic unresolved REVIEW_REQUIRED -> REVIEW_REQUIRED
Production/Demo unresolved CA -> REVIEW_REQUIRED
```

Data Readiness and Safety were not weakened.

## Runner / Day Completion

Runner still invokes `pending_lifecycle` only from formal Execution evidence:

```text
execution/pending_terminalization_evidence.json
status = PENDING_LIFECYCLE_REQUIRED
```

Day Completion now treats `CONSUMED` as a valid lifecycle completion status,
alongside the L20F terminal statuses.

## Test Results

Focused lifecycle + L20D/L20H:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py -k 'phase29_l20h or phase29_l20d_mixed or phase29_l20d_historical_ca_quarantine'
9 passed, 12 deselected
```

Execution L20B/L20H:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py -k 'phase29_l20h or phase29_l20b'
5 passed, 9 deselected
```

Runner L20F/L20H:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase17_k_runtime_test_runner.py -k 'phase29_l20f or phase29_l20h'
3 passed, 28 deselected
```

Full focused files:

```text
tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py
21 passed

tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py
14 passed

tests/runtime_v2/test_phase17_k_runtime_test_runner.py
31 passed
```

CA quarantine + historical submit/fill regression:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase29_l9_historical_ca_quarantine_continuation.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py
18 passed
```

Combined Runtime v2 focused regression:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py tests/runtime_v2/test_phase17_k_runtime_test_runner.py tests/runtime_v2/test_phase29_l9_historical_ca_quarantine_continuation.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py
84 passed
```

Data Readiness / Safety focused:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2 -k 'data_readiness or safety_authority or pending_safety or stale_approved_pending'
58 passed, 1419 deselected
```

SELL independence focused:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2 -k 'sell_continuation or BUY_REVIEW or buy_review or sell_independence or BUY_SELL'
11 passed, 1466 deselected
```

L19 Strategy focused:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/strategy/test_phase22_e_portfolio_construction.py tests/strategy/test_phase22_j_position_sizing.py -k 'phase29_l19'
6 passed, 143 deselected
```

Compile and whitespace:

```text
PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m py_compile scripts/runtime_test.py src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py src/ai_fund_lab_v2/runtime_v2/pending/lifecycle_runner.py src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py tests/runtime_v2/test_phase15ar_pending_lifecycle_stale_handling.py tests/runtime_v2/test_phase17_bg_empty_no_action_execution_contract.py tests/runtime_v2/test_phase17_k_runtime_test_runner.py
PASS

git diff --check
PASS
```

## Current Run Mutation

```text
NO
```

The current halted run was not resumed, repaired, reset, abandoned, rolled
back, or mutated.

## Long Historical Executed

```text
NO
```

No fresh-run, resume, 20BD, 100BD, 1-year, or 4-year Historical run was
executed.

## Recommended Next Step

After review, run a new fresh Historical validation from a clean operator
entrypoint. Do not resume the pre-L20H halted run.
