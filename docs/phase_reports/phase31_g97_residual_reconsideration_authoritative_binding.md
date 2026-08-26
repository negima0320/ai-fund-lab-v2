# Phase31-G97 -- Residual Reconsideration Authoritative Binding

## PRIMARY_JUDGMENT

PHASE31_G97_RESIDUAL_RECONSIDERATION_AUTHORITATIVE_BINDING_ACCEPTED

## Scope

Implementation task.

G97 repairs only the PC residual reconsideration connectivity defect:

```text
REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION
-> PC-owned reconsideration
-> existing canonical capital competition
-> existing G90 participation-vs-deferral
-> canonical_multi_allocation_deployment_set
-> PS
-> Runtime
```

No fresh-run, resume, replay, or long Historical was executed.

## Changed Files

```text
src/ai_fund_lab_v2/strategy/portfolio_construction.py
tests/strategy/test_phase31_g97_residual_reconsideration_authoritative_binding.py
tests/strategy/test_phase31_g95_residual_reconsideration_shadow.py
docs/02_architecture/portfolio_construction_and_position_sizing_contract.md
docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md
docs/02_architecture/strategy_architecture_v1.md
```

## Implementation Summary

G97 adds authoritative PC binding evidence:

```text
canonical_residual_reconsideration_authoritative_binding.v1
```

The implementation reuses the G95 semantic path. G95 continues to produce the non-authoritative shadow artifact, and G97 maps equivalent shadow terminal outcomes into authoritative PC allocation/deferral results.

Mapping:

```text
SHADOW_SECURITY_PARTICIPATION_VALID
-> positive PC security allocation, bounded by remaining budget

SHADOW_CASH_DEFER
-> zero security allocation, explicit cash_preferred_security_deferrals[] row

SHADOW_DOMINATED_BY_STRONGER_SECURITY
-> zero security allocation, terminal binding evidence

SHADOW_SAFETY_TERMINAL
-> zero security allocation, terminal Safety preservation

SHADOW_LOT_CAP_INFEASIBLE
-> zero security allocation through existing terminal/residual semantics

SHADOW_EVIDENCE_INSUFFICIENT
-> fail-closed zero
```

Existing positive canonical allocations are consumed first. Reconsidered rows receive no special priority bonus. G90 remains the security/Cash resolver. Cash remains first-class. PS and Runtime do not receive reconsideration authority.

## Required Final Judgments

```text
RESIDUAL_RECONSIDERATION_AUTHORITATIVE_BINDING = YES

AUTHORITATIVE_BINDING_OWNER = PORTFOLIO_CONSTRUCTION

G90_CODE_CHANGED = NO
RECONSIDERATION_BYPASSES_G90 = NO
RECONSIDERATION_AUTO_AUTHORIZATION = NO

EXISTING_POSITIVE_ALLOCATION_STABILITY = PASS
ADD_REMAINS_CANONICAL_COMPETITOR = YES

OPTIONAL_CASH_FIRST_CLASS = YES
CAPITAL_BUDGET_REMAINS_MAXIMUM = YES
FORCED_BUDGET_EXHAUSTION = NO

SAFETY_TERMINAL_RESURRECTION_COUNT = 0
KNOWN_G80_WEAK_TAIL_AUTHORITATIVE_RESURRECTION_COUNT = 0

PS_RECONSIDERATION_AUTHORITY = NO
PS_PRIORITY_REDECISION = NO
RUNTIME_RECONSIDERATION_AUTHORITY = NO
RUNTIME_PRIORITY_REDECISION = NO

AUTHORITATIVE_CAPITAL_RECONCILIATION = PASS

SHADOW_TO_AUTHORITATIVE_SEMANTIC_EQUIVALENCE = PASS
SHADOW_DOUBLE_BINDING = NO

NEW_THRESHOLD_CREATED = NO
NEW_SCORE_CREATED = NO
NEW_FIXED_EXPOSURE_CREATED = NO
NEW_RECONSIDERATION_POSITION_CAP_CREATED = NO

FUTURE_INFORMATION_USED = NO
HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0

G97_ACCEPTED = YES
```

## Representative Acceptance

### 2023-04-05 Cash Preservation

Rows:

```text
83060
59350
77760
44440
```

Result:

```text
reconsidered = YES
positive authoritative security allocation = NO
cash_preferred_security_deferrals[] = YES
Cash remains available = YES
capital reconciliation = PASS
```

### 2023-04-06 Cash Preservation

Rows:

```text
83060
59350
43880
94340
77760
```

Result:

```text
reconsidered = YES
positive authoritative security allocation = NO
cash_preferred_security_deferrals[] = YES
Cash remains available = YES
capital reconciliation = PASS
```

### 2023-04-06 Safety Anchor

Row:

```text
67310
```

Result:

```text
source shadow outcome = SHADOW_SAFETY_TERMINAL
authoritative security allocation = 0
SAFETY_TERMINAL_RESURRECTION_COUNT = 0
```

### Positive Authoritative Anchors

| Date | Symbol | Type | Result |
| --- | --- | --- | --- |
| 2023-03-22 | 94320 | NEW_BUY | positive authoritative PC allocation |
| 2023-04-14 | 94320 | NEW_BUY | positive authoritative PC allocation |
| 2023-04-18 | 59350 | NEW_BUY | positive authoritative PC allocation |

These prove G97 is not only a Cash-defer bridge; when same-date G95-equivalent evidence supports participation, the row can enter authoritative PC allocation before PS discretization.

### Multi-Security Reconsideration

Anchor:

```text
2023-04-07
83060
77760
44440
```

Result:

```text
multiple reconsidered securities coexist = YES
single-winner behavior restored = NO
Cash remains available = YES
capital reconciliation = PASS
```

### ADD Preservation

Focused fixture result:

```text
legitimate ADD competitor = preserved
reconsidered NEW_BUY = no priority bonus
ADD remains canonical competitor = YES
capital reconciliation = PASS
```

## Existing Artifact Characterization

Existing target run artifacts were re-evaluated read-only through the G97 code path:

```text
binding_dates = 180
positive_authoritative_dates = 64

positive_authoritative_rows = 120
cash_defer_authoritative_rows = 408
terminal_authoritative_rows = 358
unresolved_rows = 0
safety_terminal_resurrection_count = 0

median extra authoritative security count per date = 0
max extra authoritative security count per date = 6
aggregate authoritative reconsideration security weight = 4.038634
max authoritative reconsideration security weight on a date = 0.250000

KNOWN_G80_WEAK_TAIL_AUTHORITATIVE_RESURRECTION_COUNT = 0
```

This is not a performance forecast and uses no future PnL. It characterizes the repaired decision path only.

## Regression Matrix

Covered:

```text
1. reconsiderable -> authoritative Cash defer = PASS
2. reconsiderable -> authoritative positive security = PASS
3. reconsiderable -> dominated by stronger security = PASS
4. Safety terminal remains terminal = PASS
5. G80 weak-tail remains Cash / non-security = PASS
6. multiple reconsidered rows same day = PASS
7. existing positive allocations preserved = PASS
8. ADD competition preserved = PASS
9. lot / terminal infeasible semantics preserved = PASS
10. no PS priority redecision = PASS
11. no Runtime priority redecision = PASS
12. no synthetic quantity = PASS
13. exact capital reconciliation = PASS
14. no unresolved reconsideration = PASS
15. shadow-authoritative semantic equivalence = PASS
16. 4/5 Cash preservation = PASS
17. 4/6 Cash preservation = PASS
18. positive G95 anchor cases = PASS
```

## Focused Test Results

```text
tests/strategy/test_phase31_g97_residual_reconsideration_authoritative_binding.py = 6 passed
tests/strategy/test_phase31_g95_residual_reconsideration_shadow.py = 4 passed
```

Full focused matrix:

```text
tests/strategy/test_phase31_g97_residual_reconsideration_authoritative_binding.py
tests/strategy/test_phase31_g95_residual_reconsideration_shadow.py
tests/strategy/test_phase31_g90_cash_preferred_aggregate_resolver.py
tests/strategy/test_phase31_g86_cash_preferred_participation_deferral.py
tests/strategy/test_phase31_g83_bootstrap_cash_preference_partition.py
tests/strategy/test_phase31_g81_opportunity_aware_security_cash_partition.py
tests/strategy/test_phase31_g57_multi_allocation_shadow.py
tests/strategy/test_phase31_g59_within_class_allocation_evidence.py
tests/strategy/test_phase31_g61_lot_aware_allocation_to_sizing_compatibility.py
tests/strategy/test_phase31_g62_position_sizing_g61_binding.py
tests/strategy/test_phase31_g63_runtime_executable_binding.py
tests/strategy/test_phase31_g44_add_reentry_lot_binding_integration.py
tests/strategy/test_phase31_b10_alternative_c_marginal_capital_priority.py
tests/strategy/test_phase22_e_portfolio_construction.py
```

Result:

```text
181 passed
```

Additional checks:

```text
py_compile = PASS
git diff --check = PASS
```

## SoT Updates

Updated:

```text
docs/02_architecture/portfolio_construction_and_position_sizing_contract.md
docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md
docs/02_architecture/strategy_architecture_v1.md
```

Permanent semantics added:

```text
REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION is non-terminal.
It must re-enter PC-owned canonical capital competition.
Reconsideration is candidate re-entry, not security authorization.
Reconsidered rows remain subject to G90, stronger-security competition, ADD, optional Cash, capital budget, lot feasibility, concentration/caps, and Safety terminal boundaries.
PS owns quantity.
Runtime does not redecide capital priority.
```

## Integrity

```text
FRESH_RUN_EXECUTED = NO
RESUME_EXECUTED = NO
REPLAY_EXECUTED = NO
LONG_HISTORICAL_EXECUTED = NO
FUTURE_INFORMATION_USED = NO
HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0
```

## Next

Do not automatically start Historical validation. Return G97 implementation and focused regression results first.
