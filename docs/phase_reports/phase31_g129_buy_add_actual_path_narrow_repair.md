# Phase31-G129 — BUY_ADD Actual-Path Narrow Repair

## Final Decision

`G129_BUY_ADD_ACTUAL_PATH_NARROW_REPAIR_ACCEPTED`

## Scope

Task type: focused implementation repair.

G129 repaired only the three root-cause boundaries confirmed by G128:

1. BUY_ADD PC/PS -> Submit quantity authority scope.
2. Actual BUY_ADD fill -> canonical campaign ADD history materialization.
3. G115 Market-Candidate-Cash interaction consumer erasing positive ADD marginal evidence.

No Strategy threshold, Market Quality, Risk Pacing, BUY_NEW ranking, Safety, Position Sizing quantity ownership, or Runtime capital priority semantics were changed. No fresh-run, resume, replay, or long Historical was executed.

## Source Changes

### A. BUY_ADD Submit order-increment authority

Changed:

`src/ai_fund_lab_v2/runtime_v2/planning_submit_feasibility.py`

For `semantic_type = BUY_ADD`, Submit now validates the pending item quantity against the canonical ADD order increment:

```text
pc_positive_executable_quantity_authority.final_allocated_quantity
```

The repair distinguishes:

| Field | G129 contract |
| --- | --- |
| `pc_positive_executable_quantity_authority.final_allocated_quantity` | BUY_ADD order-increment authority |
| `final_allocated_quantity` on BUY_ADD authority | accepted as canonical order increment when emitted by PC discrete quantity authority |
| `executable_quantity_delta` | position-scope / cumulative delta evidence; not an independent Submit order-increment equality requirement for BUY_ADD |
| `preflight_executable_quantity_delta` | preflight position-scope / cumulative evidence; not an independent Submit order-increment equality requirement for BUY_ADD |
| Pending item quantity | actual submitted order increment |
| Submit authorized quantity | actual submitted order increment |

True mismatch between pending item quantity and canonical ADD order increment remains `REVIEW_REQUIRED`.

BUY_NEW / REENTRY quantity validation remains unchanged.

### B. BUY_ADD campaign identity materialization

Changed:

`src/ai_fund_lab_v2/strategy/shadow_runtime.py`

Execution-derived campaign events now preserve canonical bridge fields:

- `position_campaign_id`
- `canonical_position_campaign_id`
- `open_position_campaign_id`
- `source_position_campaign_id`
- `source_decision_type`

Strict-prior ledger history merges into an open campaign only when the ledger event proves the canonical open campaign identity. Same-symbol quantity movement alone still cannot synthesize ADD history.

This preserves:

- actual BUY fill required
- no synthetic ADD from current quantity delta
- flat / closed campaign re-entry starts a new campaign
- conflicting runtime-owned campaign id without canonical bridge does not merge

### C. ADD marginal MCC consumer

Changed:

`src/ai_fund_lab_v2/strategy/portfolio_construction.py`

When Market-Candidate-Cash interaction returns `FAIL_CLOSED` / `BLOCKED`, PC no longer uses that result as a blanket ADD evidence eraser. If the ADD competitor has canonical positive/PASS incremental investment evidence and PASS opportunity-cost evidence, the ADD evidence remains visible to the ADD-vs-Cash frontier. Missing, malformed, or non-PASS ADD evidence remains fail-closed.

## SoT Update

Updated:

`docs/02_architecture/strategy_intelligence_architecture_v1.md`

Added the Phase31-G129 BUY_ADD actual-path amendment covering:

- BUY_ADD order-increment Submit authority.
- position-scope quantity fields are not Submit order-increment gates for BUY_ADD.
- BUY_ADD fill materialization requires canonical campaign identity proof.
- MCC is not a blanket positive ADD evidence eraser.

`ARCHITECTURE_SOT_UPDATED = YES`

## G128 Contract Reconciliation

BUY_ADD_ORDER_INCREMENT_AUTHORITY =
`pc_positive_executable_quantity_authority.final_allocated_quantity`

BUY_ADD_QUANTITY_SCOPE_DEFECT_REPAIRED = `YES`

G128_QUANTITY_ROWS_CONTRACT_RECONCILED = `67/67`

The 67 G128 direct `pc_discrete_quantity_authority_quantity_mismatch` ADD rows are reconciled by order-increment scoped validation. A broader local scan over the available post-G128 artifact set found the same contract shape also resolves the additional quantity-mismatch shaped row observed outside the strict G128 direct count.

SUBMIT_SAFETY_PRESERVATION_GATE = `PASS`

Reserved-cash, corporate-action, malformed authority, true order-increment mismatch, unknown/ambiguous authority, and Safety/Data Readiness fail-closed paths remain preserved.

BUY_NEW_BEHAVIOR_UNCHANGED = `YES`

The BUY_ADD-specific Submit path is gated by `semantic_type = BUY_ADD`; BUY_NEW and REENTRY keep the prior quantity contract.

BUY_ADD_CAMPAIGN_IDENTITY_REPAIRED = `YES`

ACTUAL_SHAPED_ADD_HISTORY_PASS = `5/5`

The five G128 actual filled ADD shapes are covered by actual-shaped regression anchors:

| Date | Symbol | Canonical open campaign | Runtime fill campaign |
| --- | --- | --- | --- |
| 2022-10-12 | 94320 | `pc-e62b56d6967476ec-94320-0001` | `pc-f9cfb6b5498e35e5-94320-0001` |
| 2022-10-12 | 94340 | `pc-1018b460441d595a-94340-0001` | `pc-f9cfb6b5498e35e5-94340-0001` |
| 2022-10-13 | 94340 | `pc-1018b460441d595a-94340-0001` | `pc-f9cfb6b5498e35e5-94340-0001` |
| 2023-02-15 | 54010 | `pc-ace730ca2278c71f-54010-0001` | `pc-f9cfb6b5498e35e5-54010-0001` |
| 2023-05-31 | 30410 | `pc-9357311690cdfb6c-30410-0001` | `pc-f9cfb6b5498e35e5-30410-0001` |

Existing immutable run artifacts are not mutated by G129; the 5/5 result is producer-equivalent focused regression evidence for the repaired materializer contract.

FLAT_REENTRY_NEW_CAMPAIGN_GATE = `PASS`

MCC_CONSUMER_DEFECT_REPAIRED = `YES`

G128_MCC_ROWS_CONTRACT_RECONCILED = `8/8`

G115_ONE_INCREMENT_STAGING_GATE = `PASS`

PC_TO_PS_ADD_LEAK_COUNT = `0`

PS_TO_RUNTIME_ADD_LEAK_COUNT = `0`

CAMPAIGN_LIFECYCLE_REGRESSION_GATE = `PASS`

MANDATORY_BUY_ADD_REPAIR_COMPLETE = `YES`

## Regression Results

New G129 focused tests:

```text
11 passed in 2.11s
```

Focused G129 / G115 / G117 / G119 / G122 / Submit / Pending bundle:

```text
101 passed in 2.46s
```

Additional nearby suite result:

```text
72 passed, 3 failed
```

The three failures are artifact-availability failures for pre-existing actual-run fixture paths, not G129 semantic regressions:

- missing `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260825T072702567342Z/daily/2022-12-06/strategy/portfolio_construction.json`
- missing `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260824T203644021876Z/daily/2023-03-22/strategy/portfolio_construction.json`
- missing `reports/runtime_tests/runs/runtime-test-historical-extended-smoke-20260824T055234719725Z/daily/2023-04-07/strategy/portfolio_construction.json`

PY_COMPILE = `PASS`

`py_compile` was run with `PYTHONPYCACHEPREFIX=/private/tmp/pycache-g129` to avoid macOS user cache permission issues.

GIT_DIFF_CHECK = `PASS`

## Required Flags

BUY_ADD_ORDER_INCREMENT_AUTHORITY =
`pc_positive_executable_quantity_authority.final_allocated_quantity`

BUY_ADD_QUANTITY_SCOPE_DEFECT_REPAIRED = `YES`

G128_QUANTITY_ROWS_CONTRACT_RECONCILED = `67/67`

SUBMIT_SAFETY_PRESERVATION_GATE = `PASS`

BUY_NEW_BEHAVIOR_UNCHANGED = `YES`

BUY_ADD_CAMPAIGN_IDENTITY_REPAIRED = `YES`

ACTUAL_SHAPED_ADD_HISTORY_PASS = `5/5`

FLAT_REENTRY_NEW_CAMPAIGN_GATE = `PASS`

MCC_CONSUMER_DEFECT_REPAIRED = `YES`

G128_MCC_ROWS_CONTRACT_RECONCILED = `8/8`

G115_ONE_INCREMENT_STAGING_GATE = `PASS`

PC_TO_PS_ADD_LEAK_COUNT = `0`

PS_TO_RUNTIME_ADD_LEAK_COUNT = `0`

CAMPAIGN_LIFECYCLE_REGRESSION_GATE = `PASS`

ARCHITECTURE_SOT_UPDATED = `YES`

MANDATORY_BUY_ADD_REPAIR_COMPLETE = `YES`

FUTURE_INFORMATION_USED_FOR_PRODUCTION_DECISION = `NO`

PERFORMANCE_USED_TO_SELECT_PRODUCTION_PARAMETER = `NO`

FRESH_RUN_EXECUTED = `NO`

RESUME_EXECUTED = `NO`

REPLAY_EXECUTED = `NO`

LONG_HISTORICAL_EXECUTED = `NO`

## Next

G129 is accepted for user-operated fresh long Historical validation. Do not apply G129 to any already-running Historical mid-run.

User-operated command:

```bash
PYTHONPATH=src python3 scripts/runtime_test.py fresh-run \
  --profile historical-extended-smoke \
  --start-date 2022-10-03 \
  --business-days 650 \
  --initial-cash 1000000 \
  --confirm \
  --yes-i-understand-this-mutates-trading-state
```
