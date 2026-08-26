# Phase31-G65 — G61 Lot Context Propagation Repair

## PRIMARY_JUDGMENT

PHASE31_G65_G61_LOT_CONTEXT_PROPAGATION_PARTIAL_REPAIR_ACTUAL_BOOTSTRAP_MATERIALIZATION_BLOCKED

G65 repaired part of the PC -> G61 lot context propagation path, but the
required actual bootstrap BUY materialization gate is not accepted yet.

The focused function-level actual-equivalent check for 2022-10-03 passes after
the repair:

- PC multi-allocation remains non-zero.
- G61 no longer converts all rows to `INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED`.
- G61 produces lot-executable rows.
- PS can produce positive quantities when the repaired PC multi-allocation is
  supplied to PS.
- Runtime can produce BUY_NEW plans from the repaired PS artifact.

However, the short production-equivalent 3BD fresh smoke still produced actual
runtime artifacts where top-level PC G61 compatibility remained all
`INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED` for 2022-10-03, 2022-10-04, and
2022-10-05. Therefore actual bootstrap BUY materialization was not demonstrated.

## Implementation Summary

Changed:

- `src/ai_fund_lab_v2/strategy/portfolio_construction.py`
- `src/ai_fund_lab_v2/strategy/position_sizing.py`
- `tests/strategy/test_phase31_g61_lot_aware_allocation_to_sizing_compatibility.py`
- `tests/strategy/test_phase31_g62_position_sizing_g61_binding.py`

Repair intent:

1. Extend G61 lot context propagation to reuse existing member / target weight /
   Phase29 lot resolution evidence.
2. Preserve fail-closed behavior when required lot context is genuinely missing.
3. Let PS preserve executable multi-allocation rows instead of having legacy
   SINGLE/CASH deployment-set zero them before sizing.

No Market Quality / Risk Pacing semantic change was made. No candidate ranking,
eligibility, threshold, weight, or allocation tuning was introduced.

## Focused Actual-Equivalent Check

Source evidence:

`reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260823T131305201581Z/daily/2022-10-03/strategy/portfolio_construction.json`

Method:

Existing 2022-10-03 PC members were read and the patched PC capital competition
builder was applied in-process. Temporary PS / Runtime artifacts were built
under `/tmp`; the original run artifact was not mutated.

Result:

| Check | Result |
|---|---:|
| PC_MULTI_ALLOCATION_NONZERO | YES |
| PC_SECURITY_ALLOCATIONS | 10 |
| G61_INSUFFICIENT_LOT_CONTEXT_ALL_ROWS | NO |
| G61_LOT_EXECUTABLE_ROWS | 9 |
| G61 states | `LOT_EXECUTABLE_COMPATIBLE=9`, `LOT_INFEASIBLE_RESIDUAL_REQUIRED=1` |
| PS_POSITIVE_QUANTITY_EXISTS | YES |
| PS_POSITIVE_QUANTITY_ROWS | 9 |
| PS quantity statuses | `RESOLVED_CANDIDATE=9`, `RESOLVED_ZERO_DELTA=41` |
| RUNTIME_BUY_OR_ADD_PLAN_COUNT | 7 |
| FINAL_PLANNED_BUY_COUNT | 7 |
| Runtime intents | `BUY_NEW=7`, `NO_ORDER=15` |
| Runtime NO_ORDER reasons | `zero_quantity_delta=13`, `G61_EXPLICIT_RESIDUAL_RESOLUTION_REQUIRED=2` |
| LOWER_PRIORITY_IMPLICIT_PROMOTION | NO |
| PS_QUANTITY_AUTHORITY_PRESERVED | YES |
| MARKET_QUALITY_SEMANTICS_CHANGED | NO |
| FUTURE_INPUT_COUNT | 0 |
| HISTORICAL_OUTCOME_INPUT_COUNT | 0 |

This confirms the code path can produce bootstrap BUY materialization when the
repaired PC multi-allocation/G61 evidence is what PS consumes.

## Focused Regression

Command:

```bash
PYTHONPATH=src python3 -m pytest tests/strategy/test_phase31_g61_lot_aware_allocation_to_sizing_compatibility.py tests/strategy/test_phase31_g62_position_sizing_g61_binding.py tests/strategy/test_phase31_g63_runtime_executable_binding.py tests/strategy/test_phase31_g59_within_class_allocation_evidence.py tests/strategy/test_phase31_g57_multi_allocation_shadow.py tests/strategy/test_phase22_j_position_sizing.py tests/strategy/test_phase22_g_runtime_planning.py
```

Result:

```text
173 passed
```

## Short Production-Equivalent Smoke

Command executed:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run --profile historical-extended-smoke --date-from 2022-10-03 --date-to 2022-10-05 --business-days 3 --initial-cash 1000000 --confirm --yes-i-understand-this-mutates-trading-state --auto-abandon-on-error --auto-abandon-reason phase31_g65_short_smoke
```

This was a short 3BD smoke, not a long Historical run.

Result:

- RUN_ID: `runtime-test-historical-extended-smoke-20260823T133244574859Z`
- STATUS: `PASS`
- FINAL_JUDGMENT: `PASS`
- EXIT_CODE: `0`
- COMPLETED_DAYS: `2022-10-03`, `2022-10-04`, `2022-10-05`

But actual BUY materialization did not occur.

| Date | PC Security Allocations | G61 States | G61 Lot Executable | PS Positive Quantity | Runtime BUY/ADD Plans | Submitted Orders | Fills |
|---|---:|---|---:|---:|---:|---:|---:|
| 2022-10-03 | 22 | `INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED=22` | 0 | 0 | 0 | 0 | 0 |
| 2022-10-04 | 29 | `INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED=29` | 0 | 0 | 0 | 0 | 0 |
| 2022-10-05 | 30 | `INSUFFICIENT_LOT_CONTEXT_FAIL_CLOSED=30` | 0 | 0 | 0 | 0 | 0 |

## Root Cause Of Remaining Blocker

The remaining blocker is not the G61 row calculator itself. The patched
function can resolve existing lot context from PC member evidence.

The remaining actual-path gap is that the top-level production PC artifact still
publishes a `capital_competition.canonical_multi_allocation_deployment_set` whose
G61 compatibility is built from pre-lot / insufficient context. The later
lot-aware final reallocation evidence contains the canonical executable lot
context, but that repaired/evaluable multi-allocation evidence is not the
top-level PC evidence consumed by PS in the actual fresh path.

In short:

```text
patched function-level PC member evidence -> G61 works
actual fresh top-level PC artifact -> still pre-lot G61 all fail-closed
```

## Acceptance Status

| Requirement | Status |
|---|---|
| PC_MULTI_ALLOCATION_NONZERO | PASS |
| G61_INSUFFICIENT_LOT_CONTEXT_ALL_ROWS = NO | PASS in actual-equivalent, FAIL in short smoke |
| G61_LOT_EXECUTABLE_ROWS > 0 | PASS in actual-equivalent, FAIL in short smoke |
| PS_POSITIVE_QUANTITY_EXISTS = YES | PASS in actual-equivalent, FAIL in short smoke |
| RUNTIME_BUY_OR_ADD_PLAN_COUNT > 0 | PASS in actual-equivalent, FAIL in short smoke |
| FINAL_PLANNED_BUY_COUNT > 0 | PASS in actual-equivalent, FAIL in short smoke |
| LOWER_PRIORITY_IMPLICIT_PROMOTION = NO | PASS |
| PS_QUANTITY_AUTHORITY_PRESERVED = YES | PASS |
| MARKET_QUALITY_SEMANTICS_CHANGED = NO | PASS |
| FUTURE_INPUT_COUNT = 0 | PASS |
| HISTORICAL_OUTCOME_INPUT_COUNT = 0 | PASS |
| Actual bootstrap BUY materialization demonstrated | FAIL |

## Required Output

PC_MULTI_ALLOCATION_NONZERO = YES

G61_INSUFFICIENT_LOT_CONTEXT_ALL_ROWS = PARTIAL

G61_LOT_EXECUTABLE_ROWS = PARTIAL

PS_POSITIVE_QUANTITY_EXISTS = PARTIAL

RUNTIME_BUY_OR_ADD_PLAN_COUNT = PARTIAL

FINAL_PLANNED_BUY_COUNT = PARTIAL

LOWER_PRIORITY_IMPLICIT_PROMOTION = NO

PS_QUANTITY_AUTHORITY_PRESERVED = YES

MARKET_QUALITY_SEMANTICS_CHANGED = NO

FUTURE_INPUT_COUNT = 0

HISTORICAL_OUTCOME_INPUT_COUNT = 0

FOCUSED_REGRESSION = PASS

SHORT_PRODUCTION_EQUIVALENT_SMOKE = FAIL_FOR_BUY_MATERIALIZATION

ACTUAL_BOOTSTRAP_BUY_MATERIALIZATION = NO

FRESH_LONG_HISTORICAL_EXECUTED = NO

## Recommendation

Do not proceed to long Historical.

Next task should repair the actual top-level PC artifact publication path so
that the PC multi-allocation/G61 evidence consumed by PS is built after, or
otherwise enriched with, the canonical lot-aware final reallocation context.
This should remain a connectivity repair only:

- no Market Quality redesign
- no threshold / weight tuning
- no candidate ranking or eligibility change
- no Runtime capital priority redecision
- no PS quantity authority transfer to PC

Recommended next task:

PHASE31_G66_TOP_LEVEL_PC_MULTI_ALLOCATION_LOT_CONTEXT_PUBLICATION_REPAIR
