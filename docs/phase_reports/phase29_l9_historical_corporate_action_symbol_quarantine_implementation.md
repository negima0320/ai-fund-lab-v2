# Phase29-L9 Historical Corporate Action Symbol Quarantine Implementation

Status:

```text
COMPLETE
PRODUCTION CODE CHANGED
CONFIG CHANGE: NO
RUNTIME / PENDING / LEDGER MUTATION: NO
HISTORICAL EXECUTION: NO
RESUME ALLOWED: NO
FRESH RUN REQUIRED: YES
```

Primary Judgment:

```text
PHASE29_L9_HISTORICAL_SYMBOL_SCOPED_CORPORATE_ACTION_QUARANTINE_IMPLEMENTED_SHORT_REGRESSION_PASS_FRESH_977BD_RETRY_READY
```

Summary:

```text
Implemented HISTORICAL_SYMBOL_SCOPED_CORPORATE_ACTION_QUARANTINE as a
Runtime Test continuation contract, not as a Corporate Action PASS downgrade.
Runtime CLI submit still exits non-zero with REVIEW_REQUIRED for unresolved
Corporate Action authority. scripts/runtime_test.py now classifies only the
strict historical submit pattern as COMPLETED_WITH_SYMBOL_QUARANTINE:
historical replay, historical_simulated broker, no actual broker write,
submit item REVIEW_REQUIRED / NOT_SUBMITTED, guard reason
corporate_action_event_not_resolved, event_status IMPACT_DETECTED, and
adjustment authority REVIEW_REQUIRED.

The classifier persists a historical-only symbol quarantine registry under
runtime_state/corporate_action_quarantine/historical_symbol_registry.json.
The submit guard reads that registry in historical mode only and blocks the
same unresolved symbol on later days with REVIEW_REQUIRED / NOT_SUBMITTED,
while unrelated symbols continue through their normal guards.

No split/reverse-split mechanics were added. No quantity conversion,
average-cost adjustment, valuation correction, pending conversion, lot
conversion, PnL restatement, or AdjFactor-only inference is performed.
```

Implementation Files:

```text
src/ai_fund_lab_v2/runtime_v2/historical_support/corporate_action_quarantine.py
src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py
scripts/runtime_test.py
tests/runtime_v2/test_phase29_l9_historical_ca_quarantine_continuation.py
```

Quarantine Contract:

```text
corporate_action_quarantine_status: QUARANTINED
corporate_action_quarantined_symbol: impacted symbol, e.g. 76920
corporate_action_quarantine_reason: corporate_action_event_not_resolved
corporate_action_quarantine_scope: SYMBOL_ONLY
corporate_action_run_continuation_eligibility: ALLOWED_FOR_HISTORICAL_REPLAY_ONLY
production_applicability: NEVER
portfolio_performance_limitation_status: REVIEW_REQUIRED
portfolio_performance_limitation_reason: unresolved_corporate_action_without_historical_broker_state_transition
portfolio_performance_limitation_code: CORPORATE_ACTION_UNRESOLVED_LIMITATION
```

Non-Regression:

```text
Production unresolved Corporate Action fail-closed: preserved
Demo unresolved Corporate Action fail-closed: preserved
Historical generic REVIEW_REQUIRED HALT: preserved
BUY / ADD semantics: unchanged
SELL quantity contract materialization: unchanged
Corporate Action authority semantics: unchanged; unresolved remains REVIEW_REQUIRED
```

Regression Evidence:

```text
PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase29_l9_historical_ca_quarantine_continuation.py
4 passed

PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase17_bv8_historical_submit_pit_universe_authority.py tests/runtime_v2/test_phase17_g_historical_submit_guard_and_fill.py
21 passed

PYTHONPATH=src:. python3 -m pytest -q tests/runtime_v2/test_phase29_l7_sell_quantity_contract_materialization.py
10 passed

PYTHONPATH=src:. PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-pycache python3 -m py_compile scripts/runtime_test.py src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py src/ai_fund_lab_v2/runtime_v2/historical_support/corporate_action_quarantine.py
PASS
```

Operator Handoff:

```text
Do not resume runtime-test-historical-smoke-20260810T210535954893Z after this
source change. Abandon the halted run, verify idle state, then start a fresh
977BD historical-smoke run for 2022-08-10 through 2026-08-09.
```

