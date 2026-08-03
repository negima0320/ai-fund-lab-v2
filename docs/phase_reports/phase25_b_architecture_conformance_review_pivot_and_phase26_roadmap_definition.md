# Phase25-B Architecture Conformance Review Pivot and Phase26 Roadmap Definition

## 1. Executive Summary

Phase25-B formally pivots Phase25 away from immediate Performance Improvement. Phase25 is now an Architecture Conformance and Gap Inventory phase.

Reason: Phase25-A3R confirmed that the Strategy/Sizing layer and the Planning/Submit feasibility layer can still consume different capital authorities. This is not only a fixed 850,000 JPY issue. It is evidence that new Architecture artifacts can exist while old Production consumers remain active.

No Production code, Runtime code, Strategy code, schema implementation, CLI, capital policy, config, or legacy deletion was changed in this task. The only persistent project update outside reports is the required roadmap update.

## 2. Primary Judgment

```text
PHASE25_B_ARCHITECTURE_CONFORMANCE_PIVOT_COMPLETE_PHASE26_ROADMAP_DEFINED
```

Phase25 is not ready for Strategy improvement or long performance acceptance testing. It is ready for architecture conformance inventory work.

## 3. Reason for Phase25 Pivot

Phase25-A3R found:

```text
Position Sizing:
current_total_equity based

Planning / Submit Feasibility:
fixed evaluation_capital = 1,000,000
fixed max_exposure = 850,000
```

Additional A3R judgments:

```text
Compound Reinvestment Design: PARTIAL
runtime_evaluation_capital: MISNAMED
capital_deployment_evaluation_capital: AMBIGUOUS_ACTIVE_LEGACY_POLICY
max_exposure: LEGACY_CAP
```

The broader concern is migration/closure conformance:

- new Strategy artifacts may be present but not fully connected;
- old consumers may remain active;
- Closure gates may verify new artifact existence without verifying old consumer absence;
- Runtime PASS may not prove Architecture Conformance PASS.

## 4. Revised Phase25 Definition

Revised name:

```text
Phase25 - Architecture Conformance Review, Implementation Gap Inventory and Performance Evaluation Foundation
```

Revised purpose:

```text
Identify architecture, contract, implementation, config, schema, runtime consumer,
evidence, test, documentation, migration, and closure-gate gaps before any
Strategy performance tuning.
```

Phase25 outputs:

- Architecture Conformance Inventory.
- Confirmed Gap Inventory.
- Legacy Retirement Inventory.
- Authority Conflict Inventory.
- Observability Gap Inventory.
- Phase26 Repair Plan.
- Updated Phase Roadmap.

## 5. Phase25 Completed Work Reclassification

| Task | Original Role | Revised Classification | Result |
|---|---|---|---|
| Phase25-AA | Baseline investigation | Entry-gate gap discovery | Capital authority evidence required. |
| Phase25-A1 | Evaluation design | Performance evidence foundation | Daily evidence and capital trace contracts defined. |
| Phase25-A2 | Daily evidence producer | Observability foundation | Implemented read-only evidence, not a performance improvement. |
| Phase25-A3 | Capital trace | Authority conflict detection | Confirmed fixed-cap coexistence. |
| Phase25-A3R | Capital authority review | First architecture conformance finding | Design repair required. |
| Phase25-B | Pivot | Roadmap and audit foundation | Defines B1-B7 and Phase26. |

## 6. Architecture Conformance Review Scope

Phase25-B1 will compare design SoT to implementation and active consumers for:

- Market Context.
- Portfolio Policy.
- Position Management.
- Portfolio Construction.
- Capital Deployment.
- Dynamic Position Count.
- Dynamic Cash / Exposure.
- Position Sizing.
- Runtime Planning.
- Planning Authority.
- Safety Hard Maximum.
- Submit Guard.
- Current.
- Ledger.
- Pending.
- Resume.
- Corporate Action Authority.
- Historical Safety.
- Accepted Generation.
- Performance Observability.

Judgments:

```text
CONFORMANT
PARTIAL
DESIGN_ONLY
IMPLEMENTED_NOT_CONNECTED
SHADOW_ONLY
LEGACY_CONSUMER_REMAINS
AUTHORITY_CONFLICT
OBSERVABILITY_INSUFFICIENT
NOT_IMPLEMENTED
AMBIGUOUS
```

## 7. Legacy Authority Review Scope

Phase25-B2 will inventory:

- Legacy Runtime Authority.
- Legacy Config.
- Legacy Schema.
- Legacy Field.
- Legacy Fallback.
- Legacy Producer.
- Legacy Consumer.
- Legacy Fixture.
- Legacy Test Expectation.
- Legacy CLI.
- Legacy Documentation.
- Dead Code.
- Compatibility Alias.
- Implicit Default.

Initial examples are fixed `evaluation_capital=1,000,000`, fixed `max_exposure=850,000`, legacy `max_positions`, `target_investment_ratio`, `runtime_evaluation_capital`, legacy Current fallback, legacy Planning budget, legacy ADD capacity, accepted-generation fallback, latest-path fallback, and direct model path fallback.

## 8. Authority Conflict Review Scope

Phase25-B3 will inventory conflicts including:

- `initial_capital` vs `runtime_evaluation_capital` vs `current_total_equity`.
- dynamic target exposure vs fixed max exposure.
- Strategy position count vs legacy max_positions.
- Current vs Broker snapshot.
- Planning Authority vs recomputed Submit Authority.
- Accepted Generation vs latest artifact.
- run-scoped evidence vs shared latest state.

Each conflict must name owning layer, producer, consumer, runtime consequence, performance consequence, safety consequence, recommended Phase26 repair, and evidence.

## 9. Migration Completion Audit Contract

Phase25-B4 will verify, for each claimed migration:

```text
New producer exists
New artifact exists
New consumer connection exists
All intended consumers switched
Old producer retired
Old consumers zero
Old config zero
Old schema zero
Old fallback zero
Regression test covers new authority
Negative assertion covers old authority absence
```

Judgments:

```text
MIGRATION_COMPLETE
MIGRATION_PARTIAL
NEW_PATH_EXISTS_OLD_PATH_ACTIVE
SHADOW_ONLY
NOT_MIGRATED
UNKNOWN
```

## 10. Closure Gate Failure Review

Phase25-B5 will determine why Phase22-24 closure did not detect the A3R-style issue. Failure classes:

```text
Design Gap
Implementation Gap
Review Gap
Test Gap
Evidence Gap
Closure Criteria Gap
Negative Assertion Gap
Documentation Gap
Runtime Switch Gap
Legacy Retirement Gap
```

The review must distinguish Runtime PASS from Architecture Conformance PASS.

## 11. Observability Gap Review

Phase25-B6 will inventory missing authority observability, including:

- `submit_capital_limit`.
- `aggregate_feasibility_capital_base`.
- `pending_reserved_cash`.
- same-day reservation.
- binding constraint.
- authority selected at runtime.
- fallback selected at runtime.
- policy source hash.
- active config source.
- legacy path activation.

## 12. Gap Severity and Prioritization

Severity:

```text
CRITICAL
HIGH
MEDIUM
LOW
INFORMATIONAL
```

Type:

```text
RUNTIME_DEFECT
ARCHITECTURE_CONFORMANCE_GAP
LEGACY_RETIREMENT_GAP
AUTHORITY_CONFLICT
OBSERVABILITY_GAP
TEST_GAP
DOCUMENTATION_GAP
PERFORMANCE_EVALUATION_GAP
```

Repair order:

1. Safety / Submit / Corporate Action integrity.
2. Authority conflict.
3. Active Legacy Runtime constraint.
4. Production / Demo / Historical divergence.
5. Runtime state correctness.
6. Performance evaluation contamination.
7. Observability.
8. Documentation / cleanup.

## 13. Revised Phase25 Workstreams

| Workstream | Name | Output |
|---|---|---|
| Phase25-B1 | Architecture-to-Implementation Conformance Matrix | Component matrix and Gap IDs. |
| Phase25-B2 | Legacy Authority and Consumer Inventory | Legacy retirement inventory. |
| Phase25-B3 | Authority Conflict Inventory | Conflict list with owners and repairs. |
| Phase25-B4 | Migration Completion Audit | Migration completeness judgments. |
| Phase25-B5 | Closure Gate Failure Review | Closure criteria and negative assertion gaps. |
| Phase25-B6 | Observability Gap Inventory | Missing runtime authority evidence list. |
| Phase25-B7 | Gap Severity and Phase26 Prioritization | Confirmed repair order and regression scope. |

## 14. Phase25 Exit Gate

Phase25 may close only when:

```text
Architecture components reviewed = 100% of declared scope
Confirmed Gap Inventory complete
Suspected gaps separated from confirmed gaps
Legacy Consumer Inventory complete
Authority Conflict Inventory complete
Migration Completion Audit complete
Closure Gate Failure Review complete
Observability Gap Inventory complete
Phase26 Repair Tasks defined
Repair dependency order defined
Required regression matrix defined
Required user-run tests defined
Roadmap updated
No Strategy tuning performed
```

Candidate closure judgments:

```text
PHASE25_ARCHITECTURE_CONFORMANCE_REVIEW_COMPLETE_PHASE26_REPAIR_READY
PHASE25_ARCHITECTURE_CONFORMANCE_REVIEW_PARTIAL_ADDITIONAL_AUDIT_REQUIRED
PHASE25_ARCHITECTURE_CONFORMANCE_REVIEW_BLOCKED_BY_EVIDENCE_GAPS
```

## 15. Phase26 Definition

Name:

```text
Phase26 - Production Architecture Repair, Legacy Retirement and Evaluation Readiness Restoration
```

Purpose:

```text
Repair Phase25-confirmed gaps as Production / Demo / Historical common Runtime
changes and restore performance evaluation readiness.
```

Non-scope:

- Strategy tuning.
- Performance optimization for returns.
- Guard weakening.
- Historical-only Strategy.
- Unapproved repair bundling.
- Repairs not mapped to confirmed Phase25 Gap IDs.

## 16. Phase26 Workstreams

| Workstream | Name | Scope |
|---|---|---|
| Phase26-A | Capital Authority Repair and Legacy Fixed Capital Retirement | `runtime_evaluation_capital`, fixed `evaluation_capital`, fixed `max_exposure`, active deployment capital, independent Safety cap, Morning Planning, ADD, Planning Submit Feasibility, Current/fill projection. |
| Phase26-B | Legacy Runtime Authority and Consumer Retirement | Old consumers, configs, schemas, fallbacks, fixtures, tests, docs, aliases, dead code. |
| Phase26-C | Cross-Architecture Conformance Repairs | Non-capital gaps from Phase25. |
| Phase26-D | Observability and Runtime Authority Materialization | Selected authority, binding reason, fallback use, active config source, policy hash. |
| Phase26-E | Negative Assertion and Closure Gate Strengthening | Old consumer/config/schema/fallback/test/docs absence checks. |
| Phase26-F | Performance Evaluation Readiness Revalidation | Rematerialize A2/A3-style evidence after repairs. |
| Phase26-G | User-run Historical Regression | User/operator executes short, 20BD, 60BD, and later 200/252BD gates. |

## 17. Phase26 Entry Gate

Every Phase26 repair must satisfy:

```text
Confirmed Phase25 Gap ID exists
Design SoT identified
Current consumer inventory known
Migration target known
Regression scope known
Safety preservation contract known
Production / Demo / Historical impact known
Long test owner assigned to user/operator
No combined unrelated repair bundle
```

## 18. Phase26 Exit Gate

Phase26 may close only when:

- all accepted Phase26 repair tasks are complete or explicitly deferred with user approval;
- old Production/Demo/Historical consumer counts are zero for retired items;
- Safety / Submit / Corporate Action Guards are not weakened;
- Production / Demo / Historical common Runtime is preserved;
- A2/A3 evaluation evidence rematerializes without unresolved legacy conflicts for repaired areas;
- regression matrix passes;
- user/operator run gates are completed or explicitly deferred.

## 19. Phase27 Recommendation

Recommended separation:

```text
Phase26 = Repair / Retirement / Revalidation
Phase27 = Performance Evaluation and Strategy Improvement
```

Architecture repair and Strategy performance tuning should not be bundled. Phase27 should begin only after Phase26 restores evaluation readiness and eliminates confirmed architecture contamination.

## 20. New Closure Negative Assertions

For every replaced or retired item:

```text
Old Production Consumer Count = 0
Old Demo Consumer Count = 0
Old Historical Consumer Count = 0
Old Config Authority Count = 0
Old Schema Authority Count = 0
Old Implicit Fallback Count = 0
Old Runtime Activation Count = 0
Old Fixture Dependency Count = 0
Old Test Expectation Count = 0
Old Documentation Presented as Current = 0
```

Allowed document exceptions must be labeled:

```text
HISTORICAL_REFERENCE_ONLY
NON_RUNTIME
NON_AUTHORITY
```

## 21. Roadmap Changes

`docs/01_requirements/phase_roadmap.md` was updated by appending the Phase25-B pivot, revised Phase25, Phase26 definition, Phase27 recommendation, and closure negative assertion contract.

## 22. Required Follow-up Tasks

1. `Phase25-B1 Architecture-to-Implementation Conformance Matrix`
2. `Phase25-B2 Legacy Authority and Consumer Inventory`
3. `Phase25-B3 Authority Conflict Inventory`
4. `Phase25-B4 Migration Completion Audit`
5. `Phase25-B5 Closure Gate Failure Review`
6. `Phase25-B6 Observability Gap Inventory`
7. `Phase25-B7 Gap Severity and Phase26 Prioritization`
8. `Phase26-A Capital Authority Repair and Legacy Fixed Capital Retirement`

## 23. Blocking Gaps

No blocking gap for this roadmap definition task.

## 24. Non-Blocking Gaps

- Phase25-B does not complete the full B1-B7 audit.
- Confirmed gaps beyond A3R remain to be established by B1-B7.
- Phase26 repair task details are intentionally not implementation-ready until Gap IDs are confirmed.

## 25. Recommended Next Task

```text
Phase25-B1 Architecture-to-Implementation Conformance Matrix
```

