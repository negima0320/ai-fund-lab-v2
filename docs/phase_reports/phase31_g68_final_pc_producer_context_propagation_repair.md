# Phase31-G68 — Final PC Producer Context Propagation Repair

## PRIMARY_JUDGMENT

PHASE31_G68_FINAL_PC_PRODUCER_CONTEXT_PROPAGATION_REPAIRED_ACCEPTED

G68 repaired the G67-confirmed actual CLI defect at the single intended
boundary:

```text
shadow_runtime._produce_lot_aware_final_portfolio_construction()
-> portfolio_construction.apply_lot_aware_final_reallocation()
-> final capital_competition build
```

No fresh-run, resume, replay, or Historical execution was performed.

## Repair Summary

Changed:

- `src/ai_fund_lab_v2/strategy/shadow_runtime.py`
- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `tests/strategy/test_phase31_g66_publication_path_integration.py`

Actual final PC producer now propagates existing decision-time context:

```text
business_date
incremental_budget_reconciliation
portfolio_policy_allocation_authority.risk_pacing_evidence
portfolio_policy_allocation_authority.risk_pacing_evidence.incremental_capital_budget_envelope
existing PS preflight lot context
```

No new authority, fallback, bridge, threshold, weight, allocation tuning, or
Market Quality / Risk Pacing semantic change was added.

Important implementation detail:

`apply_lot_aware_final_reallocation()` now accepts a separate
`final_capital_competition_risk_pacing_evidence` argument. This keeps the
lot-aware reallocation procedure itself on its previous semantics while binding
the final capital competition / G61 publication to the authoritative Portfolio
Policy risk pacing and capital budget envelope evidence.

## Regression Update

Permanent regression:

```text
tests/strategy/test_phase31_g66_publication_path_integration.py
```

The regression no longer manually rebuilds and injects a date/budget-bound
competition. It now exercises the actual producer path:

```text
portfolio_construction_draft
-> position_sizing_preflight
-> shadow_runtime._produce_lot_aware_final_portfolio_construction()
-> portfolio_construction.apply_lot_aware_final_reallocation()
-> promote_final_portfolio_construction_for_production()
-> Position Sizing
-> Runtime Planning
```

This closes the G67 regression coverage gap.

## Actual Producer Path Evidence

Using existing 2022-10-03 PIT artifacts from:

```text
runtime-test-historical-extended-smoke-20260823T135454942984Z
```

Focused producer-path evidence:

```text
PC_MULTI_DATE = 2022-10-03
G61_DATE = 2022-10-03
BUDGET_SCHEMA = incremental_capital_budget_envelope.v1
CAPITAL_BUDGET_ENVELOPE_MISSING = False
SECURITY_ALLOCATIONS = 9
G61_LOT_EXECUTABLE = 9
PS_STATUS = PASS
PS_POSITIVE_QTY = 9
RP_STATUS = PASS
RP_BUY_ADD_POSITIVE = 9
LOWER_PRIORITY_IMPLICIT_PROMOTION = False
```

## Validation

G68 actual-producer-equivalent regression:

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase31_g66_publication_path_integration.py
```

Result:

```text
1 passed
```

Focused G61/G62/G68 regression:

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase31_g66_publication_path_integration.py tests/strategy/test_phase31_g61_lot_aware_allocation_to_sizing_compatibility.py tests/strategy/test_phase31_g62_position_sizing_g61_binding.py
```

Result:

```text
10 passed
```

Python compile:

```bash
PYTHONPYCACHEPREFIX=/private/tmp/pycache-g68 PYTHONPATH=src python3 -m py_compile src/ai_fund_lab_v2/strategy/portfolio_construction.py src/ai_fund_lab_v2/strategy/shadow_runtime.py tests/strategy/test_phase31_g66_publication_path_integration.py
```

Result:

```text
PASS
```

Diff whitespace check:

```bash
git diff --check -- src/ai_fund_lab_v2/strategy/portfolio_construction.py src/ai_fund_lab_v2/strategy/shadow_runtime.py tests/strategy/test_phase31_g66_publication_path_integration.py
```

Result:

```text
PASS
```

## Acceptance Fields

ACTUAL_FINAL_PC_PRODUCER_CONTEXT_PROPAGATION = PASS

CAPITAL_BUDGET_ENVELOPE_MISSING = NO

TOP_LEVEL_PC_DATE_BOUND = YES

G61_DATE_BOUND = YES

G61_SECURITY_ALLOCATIONS_GT_0 = YES

G61_LOT_EXECUTABLE_GT_0 = YES

PS_POSITIVE_QUANTITY_GT_0 = YES

RUNTIME_BUY_PLAN_GT_0 = YES

REGRESSION_ACTUAL_CLI_PRODUCER_EQUIVALENT = YES

NEW_AUTHORITY_OR_FALLBACK_ADDED = NO

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_INPUT_COUNT = 0

FRESH_RUN_EXECUTED = NO

RESUME_EXECUTED = NO

REPLAY_EXECUTED = NO

LONG_HISTORICAL_EXECUTED = NO

## Preserved Semantics

Market Quality / Risk Pacing semantics changed: NO

Candidate ranking / eligibility changed: NO

Threshold / weight / allocation tuning introduced: NO

PC remains capital allocation owner: YES

PS remains discrete quantity owner: YES

Runtime capital priority redecision introduced: NO

BUY / SELL independence changed: NO

Safety semantics changed: NO

## NEXT_TASK_RECOMMENDATION

G68 PASS.

Do not add research tasks or redesign Market Quality / Risk Pacing here. The
next step is user-operated long Historical execution.
