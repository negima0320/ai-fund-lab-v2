# Phase29-L21T-O - 2023-06-08 Execution Negative-Cash Root-Cause Audit

## Primary Judgment

`PHASE29_L21T_O_EXECUTION_NEGATIVE_CASH_ROOT_CAUSE_CONFIRMED_REPAIR_REQUIRED_RESUME_BLOCKED`

## Scope

READ-ONLY audit only. No Strategy, Runtime, config, schema, threshold, model, Accepted Generation, Pending writer, Ledger, fresh-run, resume-run, 20BD, 100BD, or long Historical execution was changed or started by Codex.

Target:

- run id: `runtime-test-historical-smoke-20260812T083943290963Z`
- business date: `2023-06-08`
- halt stage: `execution`
- observed failure: `runtime owned current projection failed: runtime owned cash projection negative: -46930.0`

## Required Judgment

```text
DIRECT_HALT_CAUSE = EXECUTION_PRICE_DRIFT_EXCEEDED_PLANNING_SUBMIT_CASH_RESERVATION_BUFFER
PLANNING_EXECUTION_CASH_FEASIBILITY_DIVERGENCE = YES
AGGREGATE_RESERVATION_GAP = NO
SELL_PROCEEDS_CONTRACT_GAP = NO
EXECUTION_ORDERING_GAP = NO
PRICE_DRIFT_GAP = YES
STALE_CASH_AUTHORITY = NO
LEDGER_CURRENT_DIVERGENCE = YES
PARTIAL_MUTATION_RISK = YES
SAFETY_AUTHORITY_GAP = PARTIAL_OBSERVABILITY_GAP_NOT_DIRECT_CAUSE
REGRESSION_CONFIRMED = NO
RUNTIME_DEFECT_CONFIRMED = YES
EXPECTED_FAIL_CLOSED = YES_AT_EXECUTION_PROJECTION_TOO_LATE_FOR_LEDGER_ATOMICITY
RESUME_SAFE_NOW = NO
IMPLEMENTATION_REPAIR_REQUIRED = YES
```

## Executive Summary

Planning and Submit approved three BUY orders and one SELL order using canonical current cash `437,870 JPY` from the 2023-06-07 Runtime Current / persistent ledger state.

Submit Guard's aggregate BUY reservation passed at Planning/Submit prices:

```text
Starting cash        437,870
- 30410 BUY         120,300
- 59550 BUY         111,100
- 67310 BUY         200,000
= reserved cash       6,470
```

This confirms aggregate reservation existed and did not rely on same-day SELL proceeds. The reservation buffer was only `6,470 JPY`.

Execution then filled the same four orders. The 67310 BUY filled at `3,000 JPY` instead of the Planning/Submit reference `2,000 JPY`, increasing BUY outflow by `100,000 JPY`. 30410 also worsened by `7,200 JPY`, while the 24350 SELL improved cash by `4,200 JPY`. Net execution-price drift versus the planned four-order cash equation was `-103,000 JPY`.

Execution cash equation exactly reproduces the halt:

```text
Starting cash          437,870
+ 24350 SELL proceeds   53,800
- 67310 BUY            300,000
- 30410 BUY            127,500
- 59550 BUY            111,100
= Projected cash       -46,930
```

Runtime-owned current projection correctly failed closed and did not clamp negative cash. However, the Execution pipeline appended Ledger records before current projection failed. Persistent `state.json` remains at 2023-06-07, while `executions.jsonl`, `orders.jsonl`, `positions.jsonl`, `cash.jsonl`, and `events.jsonl` contain 2023-06-08 partial simulation/review records. Therefore resume is not safe now.

## Materials Reviewed

- `docs/01_requirements/phase_roadmap.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/phase_reports/phase24_id_aggregate_portfolio_constraint_and_execution_reconciliation_contract.md`
- `docs/phase_reports/phase24_ie_aggregate_feasibility_buy_item_review_sell_continuation_contract.md`
- `docs/phase_reports/phase29_l21t_n_runtime_e2e_authority_consolidation_and_regression_audit.md`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T083943290963Z/daily/2023-06-07/current_valuation_refresh/*`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T083943290963Z/daily/2023-06-08/strategy/*`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T083943290963Z/daily/2023-06-08/morning/*`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T083943290963Z/daily/2023-06-08/sell_planning/*`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T083943290963Z/daily/2023-06-08/submit/*`
- `reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T083943290963Z/daily/2023-06-08/execution/*`
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py`

## Run State

`run_state.json`:

| Field | Value |
| --- | --- |
| `status` | `HALT` |
| `next_job` | `2023-06-08:execution` |
| completed business days | `45` |
| last completed business day | `2023-06-07` |

`execution/subprocess_trace.json`:

| Field | Value |
| --- | --- |
| job | `execution` |
| business date | `2023-06-08` |
| process status | `COMPLETED` |
| return code | `20` |

## Starting Current State

2023-06-07 valuation/current evidence:

| Field | Value |
| --- | ---: |
| cash | 437,870 |
| buying power | 437,870 |
| total equity | 950,630 |
| market value | 512,760 |
| position count | 5 |

This matches 2023-06-08 Submit Guard current authority:

- `current_authority_winner = persistent_ledger_state`
- `selected_cash_source = persistent_ledger/state.json:cash`
- `selected_current_source = persistent_ledger/state.json`
- `current_cash = 437870.0`
- `current_total_equity = 950630.0`

No stale cash authority was found.

## Four Orders

| Item | Symbol | Side | Decision Type | Pending Item ID | Planned Qty | Submitted Qty | Fill Qty | Planning Price | Submit Reference Price | Execution Price | Planned Notional | Execution Notional | Cash Effect |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 24350 | SELL | SELL_EXIT / EXIT | `strategy-d2825eebf7c04286885b` / fill `opi-sell-exit-pm-24350-001` | 200 | 200 | 200 | 248 | 248 | 269 | 49,600 | 53,800 | +53,800 |
| 2 | 30410 | BUY | BUY_NEW | `strategy-a6b6078330771c35ed8c` | 100 | 100 | 100 | 1,203 | 1,203 | 1,275 | 120,300 | 127,500 | -127,500 |
| 3 | 59550 | BUY | BUY_NEW | `strategy-d3fa60bc9fc3ccc7b3d6` | 1,100 | 1,100 | 1,100 | 101 | 101 | 101 | 111,100 | 111,100 | -111,100 |
| 4 | 67310 | BUY | BUY_NEW | `strategy-41ed66908c5c1dd4e695` | 100 | 100 | 100 | 2,000 | 2,000 | 3,000 | 200,000 | 300,000 | -300,000 |

Notes:

- Submit manifest has the canonical `pending_item_id` for all four items.
- `fills.json` preserves `pending_item_id` only for the SELL; BUY fills have `pending_item_id = MISSING` and `order_plan_item_id = MISSING`.
- This identity loss is an observability/lineage gap for BUY fill evidence. It is not the direct cash-negative cause because symbol, side, quantity, price, order hash, and cash effect still reconcile exactly.

## Cash Equation

Execution equation:

```text
437,870
+ 53,800
- 300,000
- 127,500
- 111,100
= -46,930
```

This exactly matches:

- `execution/current_apply_evidence.json`: `runtime_owned_projection_reason = runtime owned cash projection negative: -46930.0`
- `execution/runtime_manifest.json`: `projected_cash = -46930.0`

Fees, tax, and slippage are `NOT_AVAILABLE` in `fills.json`; they are not needed to reproduce the observed failure.

## Planning / Submit Feasibility

Planning and Pending:

- `morning/planning_evidence.json`: `status = PASS`
- selected symbols: `24350`, `30410`, `59550`, `67310`
- `pending_item_count = 4`
- `pending_commit_status = COMMITTED_CURRENT`
- `pending_generation_evidence.json`: `status = PASS`

Submit:

- `submit/runtime_manifest.json`: `final_state = CURRENT_STATE_LOADED`, `exit_code = 0`
- `submit_action = SUBMIT`
- `submitted_count = 4`
- `pending_classification = VALID`
- `safety_status = PASS`
- `safety_decision = NEUTRAL`
- `data_readiness_safety_authority_type = HISTORICAL_PENDING_SAFETY_CONTEXT`
- `ignored_latest_safety_decision = .runtime/runtime_state/safety/latest_safety_decision.json`

Submit Guard aggregate evidence:

| Field | Value |
| --- | ---: |
| starting cash | 437,870 |
| starting buying power | 437,870 |
| starting exposure | 512,760 |
| 30410 estimated BUY | 120,300 |
| 59550 estimated BUY | 111,100 |
| 67310 estimated BUY | 200,000 |
| ending reserved cash | 6,470 |
| ending reserved buying power | 6,470 |
| ending reserved exposure | 944,160 |
| aggregate status | PASS |

The aggregate reservation did not pre-credit 24350 same-day SELL proceeds. The reservation passed because planned BUY notional was `431,400 JPY`, leaving `6,470 JPY`.

## Divergence Classification

### A. Price Drift / Execution Price Gap

YES.

| Symbol | Side | Planning Price | Execution Price | Qty | Cash Delta vs Planning |
| --- | --- | ---: | ---: | ---: | ---: |
| 24350 | SELL | 248 | 269 | 200 | +4,200 |
| 30410 | BUY | 1,203 | 1,275 | 100 | -7,200 |
| 59550 | BUY | 101 | 101 | 1,100 | 0 |
| 67310 | BUY | 2,000 | 3,000 | 100 | -100,000 |
| Total | mixed | | | | -103,000 |

The 67310 execution price gap is dominant and alone exceeds the `6,470 JPY` cash buffer.

### B. Aggregate Reservation Gap

NO for the narrow L21T-O definition. Submit Guard did run aggregate reservation over the approved BUY items and left `6,470 JPY`. This was not item-only approval accidentally bypassing a batch check.

There is still a Runtime design gap: the aggregate reservation had no sufficient execution-price buffer or historical execution-price reconciliation before the Submit boundary.

### C. SELL Proceeds Assumption Gap

NO.

Phase24-ID and Runtime architecture state that same-day SELL proceeds or exposure reductions are not pre-credited to BUY feasibility without an explicit later contract. Submit evidence is consistent with that contract:

```text
437,870 - 120,300 - 111,100 - 200,000 = 6,470
```

Execution did include SELL proceeds in the realized cash equation, which improved the final cash by `53,800 JPY`. Without SELL proceeds, projected cash would have been `-100,730 JPY`.

### D. Execution Ordering Gap

NO.

The final net cash after all four fills is negative. This is not merely a transient negative caused by applying BUY before SELL.

### E. Stale Cash / Buying Power Authority

NO.

Planning, Submit, and Execution all start from the same current cash authority: 2023-06-07 persistent ledger/current cash `437,870 JPY`.

### F. Duplicate / Missing Execution Application

NO as direct cash cause; YES as resume risk.

`fills.json` has exactly 4 fills and the cash equation matches those 4 fills exactly. No duplicate fill is needed to explain `-46,930`.

However, persistent ledger already contains the 4 execution hashes in `executions.jsonl` and `orders.jsonl`, plus 2023-06-08 position/cash/event records. This creates retry/resume risk until a repair or reconciliation plan is defined.

### G. Fee / Cost Difference

NO.

Fees/tax/slippage are `NOT_AVAILABLE`; gross notional alone exactly reproduces the failure.

### H. Position / Ledger State Divergence

YES.

After the halt:

- `.runtime/persistent_ledger/state.json` remains `business_date = 2023-06-07`, `cash = 437870.0`, `positions_count = 5`.
- `.runtime/runtime_state/current_state.json` has `business_date = 2023-06-08`, `safety_state = BUY_REVIEW_REQUIRED`, but no successful current apply.
- `.runtime/persistent_ledger/executions.jsonl` contains the 4 2023-06-08 executions.
- `.runtime/persistent_ledger/orders.jsonl` contains the 4 2023-06-08 orders.
- `.runtime/persistent_ledger/positions.jsonl` contains 8 2023-06-08 position rows with `review_required = true`.
- `.runtime/persistent_ledger/cash.jsonl` contains 2023-06-08 cash `-46930.0` with `review_required = true`.

This is Ledger-ahead-of-Current divergence.

## SELL Proceeds Contract

Existing contract:

- BUY feasibility reserves current cash / buying power / exposure across the approved Pending batch.
- Later BUY items must see earlier BUY reservations.
- SELL items remain liquidation actions.
- Same-day SELL proceeds or exposure reductions are not pre-credited to BUY capacity unless a later explicit contract approves that behavior.

Observed behavior matches the contract. The 24350 SELL proceeds were not used to approve the BUY batch. Therefore this halt is not caused by a SELL proceeds contract mismatch.

## Execution Price Contract

Execution price source:

- `fills.json` records exact execution prices.
- `execution/readonly_pipeline.py` uses source execution price in historical mode and labels it `historical_execution_authority`.
- `historical_fill_authority.json` reports `orderlist_status = READY`, `execution_action = EXECUTE`, and `fill_count = 4`.

Planning reference price source:

- `runtime_planning.json` / Pending quantity contracts use `planning_reference_close` from 2023-06-08 Market Evidence.

There is no evidence that Planning Submit Feasibility reserved a buffer for the 67310 execution price moving from `2,000` to `3,000`.

## Safety Authority Consistency

Submit safety:

- `safety_status = PASS`
- `safety_decision = NEUTRAL`
- `data_readiness_safety_authority_type = HISTORICAL_PENDING_SAFETY_CONTEXT`
- latest safety decision was explicitly ignored.

Execution safety preflight:

- `safety_status = SAFETY_MISSING`
- `safety_decision = REVIEW_REQUIRED`
- `safety_artifact_path = .runtime/runtime_state/safety/latest_safety_decision.json`

This is an observability/consumer consistency gap: Execution manifests stale/missing latest-safety preflight evidence while the Submit path correctly consumes Historical temporal safety authority. It is not the direct negative-cash cause because Execution proceeded to fill projection and the final reason is `runtime owned cash projection negative`.

## Mutation Ordering Audit

Implementation order in `execution/readonly_pipeline.py` appends ledger records before `project_runtime_owned_fills_to_current(...)` runs:

```text
append orders
append executions
append positions
append cash
append events
project runtime-owned fills to current
if projection PASS -> apply current projection
if projection REVIEW_REQUIRED -> current apply not executed
```

Observed evidence:

- `ledger_append_evidence.json`: `ledger_executions_appended = 4`, `ledger_orders_appended = 4`, `ledger_positions_appended = 8`, `ledger_cash_appended = 1`.
- `current_apply_evidence.json`: `status = NOT_EXECUTED`, `asset_current_written = false`.
- persistent state remains at 2023-06-07.
- ledger detail files contain 2023-06-08 review-required rows.

Answers:

1. Ledger append is persistently materialized in JSONL files.
2. Yes, partial mutation state remains after HALT.
3. Resume is not proven safe.
4. Ledger is ahead of Current for 2023-06-08.
5. Dedup keys are present, but retry behavior is not proven safe enough for resume because state, pending, ledger, and run_state are inconsistent.

## Regression Classification

Classification: `PRE_EXISTING_UNCOVERED_RUNTIME_INTEGRATION_GAP`.

This does not contradict L21T-N's static finding that no known Critical/High BUY/SELL independence or Pending-to-Submit authority gap remained. L21T-O exposes a different gap:

- Planning/Submit cash feasibility did not protect against execution-price variation large enough to break cash after fill.
- Execution fail-closed worked, but after partial ledger append.

This is Runtime correctness, not Strategy performance tuning.

## Resume Gate

`RESUME_SAFE_NOW = NO`

Reasons:

- Current apply failed and did not write a coherent 2023-06-08 current state.
- Ledger JSONL records for 2023-06-08 were already appended.
- Pending is now `CONSUMED`.
- run_state remains `HALT` with next job `2023-06-08:execution`.
- Duplicate/retry and Current/Ledger reconciliation semantics are not proven safe in this partial mutation state.

Do not resume this run until a repair or explicit recovery procedure handles the partial ledger/current divergence.

## Repair Direction, Not Implementation

No repair was implemented in this task. Evidence suggests the next repair should address both:

- pre-Submit or pre-adapter aggregate cash feasibility under execution-price authority / buffer semantics; and
- atomicity or rollback/transactional ordering between Ledger append and Current projection/apply.

Do not fix this by allowing negative cash, weakening Safety, using Historical-only logic, blindly reducing BUY quantity at Execution, or pre-crediting same-day SELL proceeds without an explicit Production-common contract.

## Phase Boundary

Phase30-A remains blocked. The current baseline run is halted at `2023-06-08 execution` and is not a completed canonical performance baseline.

## Validation

- fresh-run: NOT RUN
- resume: NOT RUN
- long Historical: NOT RUN
- Strategy mutation: NONE
- Runtime mutation: NONE
- `git diff --check`: PASS
