# Phase12-G SELL / Exit Integration Fix

## Summary

Phase12 Operations daily runtime now carries SELL / Exit decisions from runtime positions through Order Plan, Approval, Demo Submit dry-run guard, Fill Monitor, Reconciliation, and Daily Report.

Demo Order Wire Execution remains locked. No demo order, production order, LINE send, AI retraining, or backtest was executed.

Final status:

```text
PHASE12G_SELL_EXIT_INTEGRATION_FIX_COMPLETE
DEMO_ORDER_WIRE_EXECUTION_REMAINS_BLOCKED
PRODUCTION_ORDER_EXECUTION_REMAINS_BLOCKED
```

## Changed Files

- `src/ai_fund_lab_v2/operations/exit_adapter.py`
- `src/ai_fund_lab_v2/operations/io.py`
- `src/ai_fund_lab_v2/operations/operations.py`
- `tests/phase12/test_operations_exit_adapter.py`
- `tests/phase12/test_operations_sell_integration.py`
- `docs/phase_reports/phase12g_sell_exit_integration_fix.md`
- `reports/phase_reports/phase12g_sell_exit_integration_fix.json`

Phase9 artifacts, launchd files, CLI scripts, and paper trading modules were not changed.

## SELL Order Plan Schema

SELL items are now normalized in the Operations Order Plan with the required SELL-specific fields:

- `side = SELL`
- `code` / `issue_code`
- `quantity`
- `position_id`
- `lot_reference`
- `exit_source`
- `exit_reason`
- `sell_reason`
- `position_entry_price`
- `current_price`
- `unrealized_return`
- `expected_notional`
- `approval_required = true`
- `production_order_allowed = false`
- `demo_order_allowed = false`

BUY and SELL items share the same top-level order plan `items` list. SELL-only fields are preserved instead of being dropped during normalization.

## Exit Adapter

Added `src/ai_fund_lab_v2/operations/exit_adapter.py`.

Responsibilities:

- Accept current runtime positions.
- Classify `EXIT`, `REDUCE`, or `HOLD`.
- Normalize `EXIT` / `REDUCE` decisions into SELL Order Plan items.
- Mark fallback exit decisions with `exit_source = fallback`.
- Treat positions as runtime input only.
- Explicitly mark AI training contamination flags as false.

The adapter does not train models and does not use Broker Snapshot, Paper Ledger, Safety Result, Audit Result, cash, portfolio state, PnL, selected, bought, or affordable data as AI training input.

## Daily Plan Integration

`run_daily_plan` now:

- Validates market refresh and feature refresh gates.
- Reads `.runtime/operations/positions/<business_date>/positions.json` when present.
- Calls the Operations Exit Adapter.
- Combines BUY items and generated SELL items into one Order Plan.
- Blocks the daily plan if SELL generation fails, so BUY-only execution does not continue while exit logic is broken.

When no position artifact exists, the adapter returns PASS with an empty SELL list.

## Approval SELL Scope

Approval artifacts now include SELL-specific approval scope:

- `approved_side = SELL`
- `approved_position_id`
- `approved_lot_reference`
- `approved_max_quantity`
- `sell_reason`
- `exit_source`
- `approval_required = true`

Approval is not granted when SELL position reference, lot reference, quantity, reason, or exit source is missing. SELL quantity above approved position quantity is rejected.

## Submit Guard

`run_demo_submit` still performs dry-run only and does not call broker order wire execution.

Before a SELL item can reach dry-run ready state, it now checks:

- Approval exists and includes the SELL item.
- `position_id` and `lot_reference` are present.
- Runtime broker position artifact contains the matching position.
- SELL quantity does not exceed broker position quantity.
- SELL quantity does not exceed approval scope.
- Production order flags remain false.

If broker position information is missing or inconsistent, submit fails closed.

## Fill / Reconcile / Report

Fill Monitor now carries SELL semantics through each event:

- side
- quantity
- position id
- exit source
- sell reason
- remaining quantity
- position closed marker
- realized result placeholder

Reconciliation now includes `sell_reconciliation`, including SELL event counts, full close / partial sell checks, realized result placeholder, and Broker Source of Truth requirement.

Daily Report references and generated report payloads now include `sell_summary`, including SELL candidates, approval/submission/fill counts, exit source, sell reason, position id, expected notional, fill status, and realized result placeholder. LINE payload is generated as an artifact only; LINE send remains false.

## Safety Policy

The Phase11 safety policy remains intact:

- SELL / exposure-reducing orders are not blocked by MAX_EXPOSURE.
- SELL still requires Approval.
- SELL still fails closed on position mismatch, missing broker position, unknown severe state, or broker divergence.
- Production order execution remains forbidden.

## Verification

Commands executed:

```bash
python3 -m pytest tests/phase12
```

Result:

```text
25 passed
```

```bash
env PYTHONPYCACHEPREFIX=/private/tmp/aifundlab_pycache python3 -m py_compile src/ai_fund_lab_v2/operations/exit_adapter.py src/ai_fund_lab_v2/operations/io.py src/ai_fund_lab_v2/operations/operations.py scripts/run_market_refresh.py scripts/run_daily_plan.py scripts/run_approval_prepare.py scripts/run_demo_submit.py scripts/run_fill_monitor.py scripts/run_reconcile.py scripts/run_daily_report.py scripts/run_operation_audit.py
```

Result:

```text
PASS
```

Mock / dry-run SELL smoke:

```text
submit_status=PASS
demo_order_submitted=false
production_order_submitted=false
fill_status=PASS
reconcile_status=REVIEW_REQUIRED
sell_candidates=1
line_send_executed=false
```

The smoke reconciliation was `REVIEW_REQUIRED` because ledger and other full-day artifacts were intentionally not generated in the minimal smoke. SELL still flowed from positions through report artifacts.

JSON validation:

```text
PASS
```

## Prohibited Actions Audit

- Demo Order Wire Execution: not executed
- Demo order: not executed
- Production order: not executed
- Production Unlock: not executed
- LINE send: not executed
- AI retraining: not executed
- Backtest rerun: not executed
- Secrets plaintext save: not executed
- Raw broker response save: not executed
- Phase9 artifact change: not executed
- Phase9 launchd change: not executed
- Phase9 CLI change: not executed
- Phase9 module destructive change: not executed

## Remaining Gaps

None for Phase12-G scope.

Demo order wire execution remains intentionally blocked until a later explicit unlock phase.
