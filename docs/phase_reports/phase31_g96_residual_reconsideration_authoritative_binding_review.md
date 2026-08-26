# Phase31-G96 -- Residual Reconsideration Authoritative Binding Review

## PRIMARY_JUDGMENT

READY_FOR_G97_AUTHORITATIVE_BINDING

## Scope

READ-ONLY / design-review task.

Evidence basis:

```text
G93 connectivity defect
G94 pre-implementation risk / benefit audit
G95 residual reconsideration shadow implementation and results
current Architecture SoT
existing PC / PS / Runtime code
```

No authoritative Strategy code, config, threshold, weight, Market Quality, Risk Pacing, Candidate ranking, PS, Runtime, Submit, Execution, ledger/current, pending state, fresh-run, resume, replay, or long Historical was changed or executed for G96.

## Required Final Judgments

```text
AUTHORITATIVE_BINDING_OWNER = PORTFOLIO_CONSTRUCTION

RECONSIDERATION_AUTO_AUTHORIZATION = NO
G90_REUSED_UNCHANGED = YES
SAFETY_BINDING_CHANGED = NO
PS_PRIORITY_REDECISION = NO
PS_RECONSIDERATION_AUTHORITY = NO
ADD_REMAINS_CANONICAL_COMPETITOR = YES

EXISTING_POSITIVE_ALLOCATION_STABILITY = PASS
EXISTING_BREADTH_CONTROLS_SUFFICIENT = YES

G80_REGRESSION_RISK_AFTER_BINDING = LOW
OPTIONAL_CASH_PRESERVED = YES
CAPITAL_BUDGET_REMAINS_MAXIMUM = YES

SHADOW_TO_AUTHORITATIVE_SEMANTIC_EQUIVALENCE_DEFINED = YES

AUTHORITATIVE_BINDING_ARCHITECTURALLY_SAFE = YES
AUTHORITATIVE_BINDING_IMPLEMENTATION_READY = YES

DECISION = READY_FOR_G97_AUTHORITATIVE_BINDING
```

## Binding Boundary

The authoritative boundary is Portfolio Construction only:

```text
REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION
-> PC-owned reconsideration
-> existing canonical capital competition
-> existing G90 participation-vs-deferral
-> final canonical_multi_allocation_deployment_set
-> PS
-> Runtime
```

Binding must not occur in Position Sizing or Runtime. PS remains quantity owner, and Runtime remains a consumer of already-bound PS output.

```text
AUTHORITATIVE_BINDING_OWNER = PORTFOLIO_CONSTRUCTION
```

## No Automatic Promotion

Permanent contract:

```text
REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION != positive security authorization
```

The row may only re-enter the candidate set for PC competition. It must then resolve through the same existing decision path as any other PC candidate:

```text
candidate re-entry only
-> security / Cash / dominated / terminal outcome
```

G95 proves this distinction: 2023-04-05 and 2023-04-06 representative rows were reconsidered but still resolved to Cash defer with zero security authorization.

```text
RECONSIDERATION_AUTO_AUTHORIZATION = NO
```

## G90 Preservation

Authoritative binding can and must reuse G90 unchanged.

G95 already reused the existing participation-vs-deferral resolver and confirmed:

```text
CASH_PREFERRED_PARTICIPATION_VALID can survive when same-date evidence supports it.
CASH_PREFERRED_DEFER remains available.
optional Cash remains first-class.
aggregate pressure remains active.
weak-tail deferral remains active.
frontier is a priority signal, not an exclusive admission gate.
```

If G97 requires weakening G90 to bind reconsideration, G97 should stop. The accepted boundary is to feed reconsidered rows into the existing resolver, not to add a second resolver.

```text
G90_REUSED_UNCHANGED = YES
```

## Existing Allocation Stability

Required authoritative competition set:

```text
existing canonical positive allocations
+ credible reconsideration candidates
+ credible ADD candidates
+ optional Cash
+ terminal Safety exclusion
```

G95 shadow consumed existing selected allocations before reconsidered candidates and only used remaining shadow budget for reconsidered rows. Rows can also resolve to:

```text
SHADOW_DOMINATED_BY_STRONGER_SECURITY
```

This preserves existing stronger allocations by design. G97 must preserve that ordering: reconsideration expands the input surface but does not invalidate already-authorized stronger allocations unless existing canonical competition semantics explicitly re-rank all PC candidates in one shared pass.

```text
EXISTING_POSITIVE_ALLOCATION_STABILITY = PASS
```

## Safety Preservation

Safety remains terminal:

```text
VALID_SAFETY_RESERVE
SAFETY_CAP_BOUND
minimum_lot_exceeds_safety_hard_cap
malformed Safety evidence
```

G95 regression anchor:

```text
2023-04-06 67310
-> VALID_SAFETY_RESERVE / SAFETY_CAP_BOUND
-> SHADOW_SAFETY_TERMINAL
-> authorized_shadow_weight = 0
```

G97 must exclude Safety-terminal rows before reconsideration.

```text
SAFETY_TERMINAL_REENTRY_ALLOWED = NO
SAFETY_BINDING_CHANGED = NO
```

## Lot / PS Contract

Authoritative binding should produce PC-authorized target weights only. It must not produce share quantity, synthetic fills, or Runtime orders.

PS remains responsible for:

```text
discrete quantity
lot feasibility
quantity_delta
no priority redecision
```

If an authoritative reconsidered allocation cannot form an executable lot, it must return through existing PC/lot residual semantics before PS binding. PS must not resurrect it.

```text
PS_PRIORITY_REDECISION = NO
PS_RECONSIDERATION_AUTHORITY = NO
```

## ADD Competition

Reconsidered NEW_BUY rows receive no special priority bonus.

G95 target-run positive shadow rows were `NEW_BUY`; no ADD-positive row was observed in that run. This is not a waiver. G97 must include a focused ADD regression proving:

```text
ADD remains in the same capital competition set.
ADD evidence / G74 intent remains authoritative for ADD eligibility.
reconsidered NEW_BUY does not crowd out ADD by special privilege.
```

```text
RECONSIDERED_NEW_BUY_PRIORITY_BONUS = NO
ADD_REMAINS_CANONICAL_COMPETITOR = YES
```

## Position Breadth Risk

G95 found:

```text
max extra theoretical security count per date = 6
EXCESS_POSITION_BREADTH_RISK = MEDIUM
```

Existing controls are sufficient for G97 binding review:

```text
capital budget envelope
strategy position / concentration policy
safety hard max
single-name caps
G90 Cash competition
lot feasibility
stronger-security domination
PS lot conversion
Runtime no priority redecision
```

No new fixed count specifically for reconsideration should be added.

```text
EXISTING_BREADTH_CONTROLS_SUFFICIENT = YES
```

## Overdeployment Risk

G95 safety facts:

```text
known weak-tail resurrection = 0
Safety resurrection = 0
median theoretical exposure delta = 0
SHADOW_CASH_DEFER = 414
SHADOW_SECURITY_PARTICIPATION_VALID = 53
SHADOW_DOMINATED_BY_STRONGER_SECURITY = 96
```

Binding can preserve G80 protection if it uses the same G95 resolver/helper path and keeps Cash as an explicit competitor.

```text
G80_REGRESSION_RISK_AFTER_BINDING = LOW
OPTIONAL_CASH_PRESERVED = YES
CAPITAL_BUDGET_REMAINS_MAXIMUM = YES
```

## Shadow-to-Authoritative Equivalence

G97 should reuse the G95 helper/semantic path and only change the publication target:

```text
G95:
canonical_residual_reconsideration_shadow.v1
-> non-authoritative terminal shadow outcome

G97:
same reconsideration classification
-> authoritative final PC allocation / deferral surface
-> canonical_multi_allocation_deployment_set
```

Before PS discretization, the authoritative decision must match G95 shadow semantics for G95-covered cases:

```text
SHADOW_SECURITY_PARTICIPATION_VALID -> positive PC allocation candidate
SHADOW_CASH_DEFER -> zero security allocation / explicit Cash or deferral
SHADOW_DOMINATED_BY_STRONGER_SECURITY -> zero security allocation
SHADOW_SAFETY_TERMINAL -> terminal zero
SHADOW_LOT_CAP_INFEASIBLE -> terminal/residual zero through existing lot semantics
SHADOW_EVIDENCE_INSUFFICIENT -> fail-closed zero
```

```text
SHADOW_TO_AUTHORITATIVE_SEMANTIC_EQUIVALENCE_DEFINED = YES
```

## Representative Cases

### 2023-04-05 Cash Defer

Rows:

```text
83060
59350
77760
44440
```

Expected authoritative semantic after binding:

```text
reconsidered = YES
security authorization = 0
Cash still wins
```

### 2023-04-06 Cash Defer

Rows:

```text
83060
59350
43880
94340
77760
```

Expected authoritative semantic after binding:

```text
reconsidered = YES
security authorization = 0
Cash still wins
```

### 2023-04-06 Safety Terminal

Row:

```text
67310
```

Expected authoritative semantic:

```text
Safety terminal = YES
security authorization = 0
```

### Positive NEW_BUY Case

Representative G95-compatible shadow-positive rows from target run:

| Date | Symbol | Type | Class | G90 result | Requested | Authorized |
| --- | --- | --- | --- | --- | ---: | ---: |
| 2023-03-22 | 94320 | NEW_BUY | COMPARABLE_HIGH | CASH_PREFERRED with participation-valid shadow path | 0.030303 | 0.030303 |
| 2023-04-14 | 94320 | NEW_BUY | COMPARABLE_MARGINAL | DEPLOY_ELIGIBLE | 0.040000 | 0.010185 |
| 2023-04-18 | 59350 | NEW_BUY | COMPARABLE_MARGINAL | DEPLOY_ELIGIBLE | 0.050000 | 0.050000 |

These rows show that authoritative binding can safely materialize reconsidered NEW_BUY candidates through PC final allocation before PS, while still preserving budget limits and G90 classification.

### Multi-Security Same-Day Case

Representative:

```text
2023-04-07
83060, 77760, 44440
```

All three were G95-compatible shadow-positive NEW_BUY rows, with requested/authorized shadow weight `0.035238` each. G97 must prove the same semantic can flow into PC final allocation without PS or Runtime redecision.

### ADD Case

No ADD-positive shadow row was observed in the target run. G97 must therefore include a synthetic or focused existing-fixture ADD regression proving ADD remains a canonical competitor and receives no worse treatment than NEW_BUY under identical existing ADD authority evidence.

## Regression Matrix for G97

Mandatory tests:

```text
1. reconsiderable -> authoritative Cash defer
2. reconsiderable -> authoritative positive security
3. reconsiderable -> dominated by stronger security
4. Safety terminal remains terminal
5. weak-tail known cases remain Cash
6. multiple reconsidered rows same day
7. existing positive allocations preserved
8. ADD competition preserved
9. lot infeasible case
10. no Runtime/PS priority redecision
11. no synthetic quantity
12. capital reconciliation exact
13. no unresolved reconsideration
14. shadow-authoritative equivalence
```

Regression anchors:

```text
2023-04-05: 83060, 59350, 77760, 44440 -> Cash defer
2023-04-06: 83060, 59350, 43880, 94340, 77760 -> Cash defer
2023-04-06: 67310 -> Safety terminal
Known G80 weak-tail rows: 14390, 69320, 37600, 87500 -> no security resurrection
2023-04-07: multi-security positive shadow case
At least one ADD-focused fixture
```

## SoT Update Plan

If G97 proceeds, update design documentation under:

```text
docs/02_architecture/portfolio_construction_and_position_sizing_contract.md
docs/02_architecture/dual_path_market_quality_and_capital_competition_contract.md
docs/02_architecture/strategy_architecture_v1.md
```

Permanent text must state:

```text
REALLOCATABLE_RESIDUAL_PENDING_RECONSIDERATION is non-terminal.
It must re-enter PC-owned canonical capital competition.
Reconsideration is not authorization.
Cash, ADD, stronger security, lot feasibility, and Safety remain authoritative competitors/boundaries.
```

G96 does not update SoT because this task is review-only and not authoritative binding.

## Binding Readiness

```text
AUTHORITATIVE_BINDING_ARCHITECTURALLY_SAFE = YES
AUTHORITATIVE_BINDING_IMPLEMENTATION_READY = YES
```

Readiness is conditional on G97 preserving the exact boundary above. In particular, G97 must not bind shadow directly to orders and must not interpret reconsideration as buy permission.

## Integrity

```text
CODE_CHANGED = NO
CONFIG_CHANGED = NO
AUTHORITATIVE_STRATEGY_CHANGED = NO
SHADOW_BOUND_TO_PRODUCTION = NO
FRESH_RUN_EXECUTED = NO
RESUME_EXECUTED = NO
REPLAY_EXECUTED = NO
LONG_HISTORICAL_EXECUTED = NO
PARAMETER_TUNING_FROM_PERFORMANCE = NO
FUTURE_INFORMATION_USED = NO
HISTORICAL_OUTCOME_PARAMETER_SELECTION_COUNT = 0
```

## Next

Proceed to:

```text
PHASE31_G97_RESIDUAL_RECONSIDERATION_AUTHORITATIVE_BINDING
```

No additional research task is required before G97.
