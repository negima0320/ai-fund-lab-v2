# Phase29-L21T-P Execution Price Authority and Transactional Repair Design

## Scope

READ-ONLY DESIGN / VERIFICATION ONLY.

No Runtime implementation, Strategy implementation, config, schema, threshold,
model, Accepted Generation, Pending writer, Ledger, Current, fresh-run, resume,
or long Historical execution was changed or started by Codex.

Target run:
`reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T083943290963Z`

Target halt:
`2023-06-08 execution`

Upstream L21T-O judgment:
`PHASE29_L21T_O_EXECUTION_NEGATIVE_CASH_ROOT_CAUSE_CONFIRMED_REPAIR_REQUIRED_RESUME_BLOCKED`

## Primary Judgment

`PHASE29_L21T_P_EXECUTION_PRICE_AUTHORITY_VERIFIED_TRANSACTIONAL_RUNTIME_REPAIR_DESIGN_READY`

67310's `3,000 JPY` execution price is valid under the current
Production-common Historical execution semantics: Historical MARKET orders fill
at the target session Canonical OHLCV `Open`.  The price is also inside the
same-day PIT market range.

The confirmed Runtime defect is not the 67310 execution price authority.  The
defect is that Planning/Submit cash feasibility reserved MARKET BUY cash at the
planning reference close (`2,000 JPY`) while the accepted execution authority
could fill at the target-session open (`3,000 JPY`), and the execution pipeline
committed Ledger rows before the runtime-owned Current projection validated the
filled cash state.

## Required Classification

```text
67310_EXECUTION_PRICE_3000_VALID = YES
PRICE_AUTHORITY_DEFECT = NO
CORPORATE_ACTION_BASIS_MISMATCH = NO
PLANNING_RESERVATION_SEMANTICS_DEFECT = YES
PRE_COMMIT_EXECUTION_FEASIBILITY_REQUIRED = YES
LEDGER_CURRENT_TRANSACTIONALITY_DEFECT = YES
RECOVERY_REQUIRED_BEFORE_RESUME = YES
SAFETY_AUTHORITY_REPAIR_REQUIRED = SEPARATE
PRODUCTION_COMMON_REPAIR_DESIGN_READY = YES
RESUME_SAFE_NOW = NO
```

## Mandatory Reading

Reviewed:

- `docs/01_requirements/phase_roadmap.md`
- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/phase_reports/phase24_id_aggregate_portfolio_constraint_and_execution_reconciliation_contract.md`
- `docs/phase_reports/phase24_ie_aggregate_feasibility_buy_item_review_sell_continuation_contract.md`
- `docs/phase_reports/phase29_l21t_n_runtime_e2e_authority_consolidation_and_regression_audit.md`
- `docs/phase_reports/phase29_l21t_o_execution_negative_cash_projection_root_cause_audit.md`
- `src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py`
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`
- `src/ai_fund_lab_v2/runtime_v2/asset/runtime_owned_fill_projection.py`

## 67310 Price Lineage

| Stage | Source | Date / temporal status | Price | Adjustment state | Authority |
| --- | --- | --- | ---: | --- | --- |
| Raw PIT market source | `market_refresh/inputs/historical_asof/2023-06-08/raw/jquants/equities_bars_daily/data.parquet` | `target_date=2023-06-08`, PIT materialized under target run | raw `O=3`, `H=3`, `L=2`, `C=2`; adjusted `AdjO=3000`, `AdjH=3000`, `AdjL=2000`, `AdjC=2000` | `AdjFactor=1.0`; adjusted columns present | J-Quants equities bars daily |
| Market Refresh | `market_refresh/market_refresh/market_data_refresh_detail.json` | `existing_latest_date=2023-06-08`, dry-run historical source copy | normalized source path resolved | normalized adjusted OHLCV | Historical market refresh |
| Historical As-Of View | `market_refresh/historical_asof_view.json` | `status=PASS`, `logical_cutoff=2023-06-08`, `logical_max_date=2023-06-08`, future rows excluded | normalized OHLCV through 2023-06-08 | same normalized basis | `normalized_ohlcv` historical as-of authority |
| Feature / Market Evidence | `strategy/technical_features.json`, `strategy/price_volatility.json` | `reference_price_date=2023-06-08`, `PIT_status=PASS` | `reference_price=2000` | adjusted close | `MARKET_EVIDENCE_AUTHORITY`, source field `close` |
| Strategy Reference Price | `strategy/runtime_planning.json` | `business_date=2023-06-08` | `reference_price=2000` | adjusted close | `planning_reference_close` |
| Planning Reference Price | `strategy/runtime_planning.json` | same-day Planning | `planned_quantity=100`, `planned_notional=200000` | adjusted close | Strategy Planning Authority |
| Pending / Submit Reference Price | `submit/runtime_manifest.json` | Submit guard revalidation PASS | `estimated_price=2000`, `estimated_amount=200000` | adjusted close | `strategy_planning_approval_order_conditions`; `order_type=MARKET`, `price_condition=MARKET` |
| Historical Execution Price | `.runtime/runtime_state/historical_broker/2023-06-08/8d77773f7a54ec13711c23d586e1f9ddecb82c50e1ecc05ffb2fad24e0cb374b.json` | `fill_datetime=2023-06-08T09:00:00+09:00` | `fill_price=3000` | adjusted open | Historical execution submission evidence |
| Fill Price | `execution/fills.json` | Execution job `2023-06-08` | `execution_price=3000`, `quantity=100`, `cash_effect=-300000` | adjusted open | `historical_execution_authority` via `readonly_pipeline.py` |

## Market Price Sanity Check

67310 same-day OHLCV from the raw and normalized historical as-of inputs:

| Field | Raw | Adjusted / normalized |
| --- | ---: | ---: |
| Previous close, 2023-06-07 | `C=3` | `Close=3000` |
| Planning reference, 2023-06-08 | `C=2` | `Close=2000` |
| Open, 2023-06-08 | `O=3` | `Open=3000` |
| High, 2023-06-08 | `H=3` | `High=3000` |
| Low, 2023-06-08 | `L=2` | `Low=2000` |
| Close, 2023-06-08 | `C=2` | `Close=2000` |
| Execution authority price | `Open=3` | `fill_price=3000` |

`3,000 JPY` is inside the target session PIT market range
`2,000..3,000 JPY` and equals the same-day adjusted Open.  Therefore it is not
classified as `HISTORICAL_EXECUTION_PRICE_AUTHORITY_DEFECT`.

## Corporate Action / Price Adjustment Check

Evidence:

- `strategy/corporate_event.json` has the 67310 same-day symbol event fact:
  `coverage_status=AVAILABLE`, `event_status=KNOWN_NO_EVENT`, `event_dates=[]`,
  `event_types=[]`.
- Raw OHLCV for 2023-06-08 has `AdjFactor=1.0`.
- Raw adjusted values and normalized values agree: `AdjO/Open=3000`,
  `AdjH/High=3000`, `AdjL/Low=2000`, `AdjC/Close=2000`.
- Planning reference price and Historical execution price both resolve from
  the same normalized OHLCV file:
  `reports/runtime_tests/runs/runtime-test-historical-smoke-20260812T083943290963Z/daily/2023-06-08/market_refresh/inputs/historical_asof/2023-06-08/raw_normalized/jquants/equities_bars_daily/data.parquet`.

The repository also records that a broader J-Quants corporate actions source is
not fully implemented in this run's Strategy input authority.  That is a
coverage limitation to keep visible, but it does not explain the `2,000 ->
3,000` difference here because the symbol-specific event fact is no-event and
the OHLCV adjustment basis is consistent.

Conclusion:

```text
CORPORATE_ACTION_BASIS_MISMATCH = NO
```

## Execution Semantics

`docs/02_architecture/runtime_architecture_v2.md` states that Historical is a
formal Runtime v2 environment and connects `HistoricalSubmitAdapter` and
`HistoricalExecutionSnapshotProvider` into the same Submit Guard, Execution
Processor, Ledger, and Current Apply chain.  It also freezes the Phase17-G
minimum Historical Fill Model:

```text
Market order = target business day's Canonical OHLCV Open fill price
```

The implementation matches that contract:

- `src/ai_fund_lab_v2/runtime_v2/historical_support/environment.py` resolves
  `fill_price` from the target session normalized OHLCV `Open`.
- `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py` uses
  `source_execution.price` in historical mode and labels it
  `historical_execution_authority`.

For 67310, Submit accepted a `MARKET` BUY with `estimated_price=2000`; the
Historical execution authority then filled the order at target-session Open
`3000`.  This is semantically valid under the existing Historical fill model.

## Cash Feasibility Finding

L21T-O confirmed:

```text
Starting cash = 437,870
Submit aggregate BUY reservation = 431,400
Submit residual cash = 6,470
SELL proceeds pre-credit = NO
```

Actual execution:

| Symbol | Side | Planning / Submit price | Execution price | Quantity | Drift |
| --- | --- | ---: | ---: | ---: | ---: |
| 24350 | SELL | 248 | 269 | 200 | +4,200 cash |
| 30410 | BUY | 1203 | 1275 | 100 | -7,200 cash |
| 59550 | BUY | 101 | 101 | 1100 | 0 |
| 67310 | BUY | 2000 | 3000 | 100 | -100,000 cash |

Net drift versus the planned four-order cash equation was `-103,000 JPY`, and
67310 alone exceeded the residual cash buffer.

The defect is therefore:

```text
PLANNING_RESERVATION_SEMANTICS_DEFECT = YES
```

The reservation price for a `MARKET` BUY must be derived from the order's
actual economic execution semantics, not from an arbitrary Historical-only
buffer.  For the current Historical model, the accepted execution price
authority is target-session Open.  For Production, the equivalent must be
broker/order-condition driven: market order cash hold, explicit limit price,
price-protection limit, broker estimated required amount, or exchange/broker
upper price constraint where available.

## Candidate Cash Feasibility Designs

| Option | Description | Production correctness | Historical parity | Safety | Opportunity / utilization | Risk |
| --- | --- | --- | --- | --- | --- | --- |
| A | Conservative pre-Submit reservation price | Strong if derived from broker/order-condition authority | Strong if Historical MARKET reserves target Open or accepted simulated execution price | Prevents unaffordable orders before Submit | May reduce deployed capital when protection price is conservative | Needs explicit authority source; arbitrary percentages are banned |
| B | Explicit execution price protection | Strong for limit/protected orders; weak for pure market orders unless broker supports max cash/protection | Strong if Historical rejects fills above protected price | Prevents accepting fills beyond authorized economics | May miss fills or require repricing | Requires schema/contract for max execution price and rejection semantics |
| C | Pre-commit execution feasibility recheck | Essential last gate after actual broker/historical execution authority is known | Strong; would block 6/8 before Ledger mutation | Prevents negative cash from committing | Does not prevent market opportunity loss after broker execution in Production, but prevents Runtime SoT corruption | Must handle real broker fills that already occurred outside Runtime |
| D | Combination | Best | Best | Best | Balanced | More implementation work |

Recommended design:

```text
Option D = A/B + C
```

Use A/B before Submit to ensure each BUY's reserved amount reflects the
approved order condition and broker/historical execution semantics.  Always use
C before committing Ledger/Current so actual fills cannot create a partially
mutated Runtime state.  This is Production-common and avoids a Historical-only
cash buffer.

## Transactional Mutation Finding

Current execution order in `src/ai_fund_lab_v2/runtime_v2/execution/readonly_pipeline.py`:

```text
resolve/normalize broker or historical fills
append orders
append executions
append positions
append cash
append events
project Runtime-owned Current
apply Current
```

On 2023-06-08:

- `execution/ledger_append_evidence.json` reports orders, executions,
  positions, and cash appended.
- `execution/current_apply_evidence.json` reports
  `status=NOT_EXECUTED`,
  `runtime_owned_projection_status=REVIEW_REQUIRED`,
  `runtime_owned_projection_reason=runtime owned cash projection negative: -46930.0`.
- `.runtime/persistent_ledger/state.json` remains authoritative at
  `2023-06-07`.
- JSONL Ledger files contain 2023-06-08 partial rows.

This is a transactional defect:

```text
LEDGER_CURRENT_TRANSACTIONALITY_DEFECT = YES
```

Phase24-ID correctly requires negative cash projection to fail closed and
materialize raw projected values.  The missing contract is that this validation
must occur before persistent execution mutation is committed, or inside a
prepare/validate/commit boundary with recoverable staged rows.

## Transactional Repair Design

Preferred design:

```text
Resolve fills
Normalize candidate orders/executions/positions/cash/events in memory
Project candidate Runtime Current in memory from current SoT + candidate fills
Validate cash, buying_power, quantity, dedup, date, and reconciliation
If PASS:
  Commit Ledger rows and Current together as one logical transaction
  Terminalize Pending consistently
If REVIEW_REQUIRED / HALT:
  Write review evidence only
  Do not append committed execution Ledger rows
  Do not consume or terminalize Pending as executed
```

Implementation shape for a later task:

- Add an execution commit coordinator with `prepare -> validate -> commit`.
- Keep `_append_ledger_records` behind the commit step.
- Provide a candidate projection path that does not write
  `asset/current_projection` or `Current` until validation passes.
- Preserve existing dedup keys, but evaluate duplicates against committed rows
  plus staged candidate rows before commit.
- Commit Ledger and Current in a deterministic order with a transaction marker
  or manifest that lets retry detect `prepared`, `committed`, or `aborted`
  state.
- If true filesystem atomicity is not available across files, use logical
  atomicity: staged files under an execution transaction id, validation
  evidence, then final append/current apply plus a commit marker.

Required guarantees:

- Current projection failure leaves no committed execution mutation.
- Retry creates no duplicate fills.
- Ledger and Current business date match after commit.
- Cash and buying power match after commit.
- Position quantity matches after commit.
- Pending terminalization is consistent with commit status.
- Crash during prepare is recoverable or quarantinable.
- Crash after commit marker is idempotently resumable.
- Behavior is common for Production, Demo, and Historical.

## Existing 2023-06-08 Partial State Recovery Design

Recovery is required before resume.

Authoritative recovery point:

```text
Current SoT = .runtime/persistent_ledger/state.json at 2023-06-07
run_state next_job = 2023-06-08:execution
2023-06-08 execution JSONL rows = partial, not authoritative current-applied state
Pending = consumed after failed execution path
```

Do not manually delete JSONL rows as the primary plan.

Recommended recovery task:

1. Build a read-only recovery detector that classifies
   `LEDGER_AHEAD_OF_CURRENT_PARTIAL_EXECUTION` when committed JSONL rows exist
   for a business date newer than Current and the execution manifest ended
   `REVIEW_REQUIRED` before Current apply.
2. Add a recovery operation that writes a quarantine/supersession manifest for
   the partial 2023-06-08 rows, preserving hashes and original records.
3. Restore or re-materialize the approved Pending from its authoritative
   pre-execution source only if the recovery operation proves the prior submit
   authority and pending item ids are unchanged.
4. Mark the consumed Pending terminalization as superseded by recovery, not
   silently erased.
5. Ensure execution dedup ignores quarantined partial rows for retry while
   preserving an audit trail that those rows were never Current-applied.
6. Reconcile Current and Ledger back to the 2023-06-07 checkpoint before any
   resume.

Resume remains unsafe until this is implemented and validated.

## Safety Authority Side Gap

Submit consumed same-day Historical Pending Safety Context:

```text
safety_status = PASS
safety_decision = NEUTRAL
data_readiness_safety_authority_type = HISTORICAL_PENDING_SAFETY_CONTEXT
```

Execution manifest records:

```text
safety_status = SAFETY_MISSING
safety_decision = REVIEW_REQUIRED
safety_reason = safety decision evidence missing
```

This did not directly cause the negative cash projection, because execution
continued to fill projection and halted on `runtime owned cash projection
negative`.  It is still an authority-consumer consistency gap: Execution should
consume or explicitly bind the same Historical temporal safety authority as the
submitted Pending/Submit path, or fail closed before execution authority
resolution if safety is truly missing.

Recommended classification:

```text
SAFETY_AUTHORITY_REPAIR_REQUIRED = SEPARATE
```

Handle separately unless Q1/Q2 naturally touches the execution preflight
authority binding.

## Regression Risk Review

The repair must preserve:

- BUY_NEW, BUY_ADD, and REENTRY authority semantics.
- SELL, REDUCE, and EXIT continuation semantics.
- BUY/SELL independence and item-scoped authority.
- Aggregate BUY reservation and same-day SELL proceeds non-pre-credit.
- One-lot authority and Strategy soft cap / Safety hard cap contracts.
- Pending composition and approved item id preservation.
- Submit Guard as final hard pre-broker guard.
- Execution dedup and retry idempotency.
- Current as SoT.
- Ledger continuity and append-only audit.
- Historical external-effect isolation.
- Production broker behavior and real-fill reconciliation.

The repair must not:

- Add arbitrary `+5%` or `+10%` buffers.
- Add Historical-only relief.
- Pre-credit same-day SELL proceeds.
- Clamp negative cash to PASS.
- Rewrite BUY quantities from SELL/Execution side.
- Restore missing BUY at Submit/Execution.

## Recommended Next Tasks

### Phase29-L21T-Q1

Execution Price / Cash Feasibility repair.

Define and implement order-condition-derived BUY reservation price:

- MARKET: broker/historical economic reserve authority.
- LIMIT: limit price times quantity plus required fees/taxes where available.
- Protected market / price-protection order: explicit protection price.
- Historical MARKET: target-session Open, matching the accepted fill model, or
  a pre-submit known execution simulation authority if that is the explicit
  Historical contract.

Add pre-commit execution feasibility recheck after execution authority is known.

### Phase29-L21T-Q2

Ledger / Current transactional commit repair.

Move Ledger append behind candidate Current projection validation or introduce a
staged transaction with prepare/validate/commit markers.

### Phase29-L21T-Q3

Existing 2023-06-08 partial-state recovery.

Quarantine/supersede partial 2023-06-08 rows, restore a coherent 2023-06-07
Current/Ledger resume point, and re-materialize Pending only under authoritative
recovery evidence.

### Phase29-L21T-Q4

Historical Execution Safety authority consistency.

Make Execution consume same-date Historical temporal safety authority
consistently with Submit, or fail closed before execution authority resolution
when that authority is unavailable.

## Phase Boundary

Phase30 remains blocked.  The Phase29 baseline must not resume until Q1/Q2/Q3
have repaired price-reservation/execution-feasibility, transactionality, and the
existing 2023-06-08 partial state.

## Verification

- Fresh-run/resume/long Historical: NOT RUN.
- Runtime/Strategy/config/schema mutation: NONE.
- `git diff --check`: PASS.
