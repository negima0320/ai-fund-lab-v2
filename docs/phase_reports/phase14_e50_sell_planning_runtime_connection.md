# Phase14-E50 Runtime v2 SELL Planning Runtime Connection

## Summary

Phase14-E50 connected SELL Planning to the regular Runtime v2 CLI as a mainline operation entry.

Final judgment: **PHASE14E50_SELL_PLANNING_RUNTIME_CONNECTED**

Review level:
- Level 1/2 connection validation for SELL Planning entry
- Broker SELL Submit / Execution was not executed in this phase because the validation time was 2026-07-09 11:48 JST, within the 11:30-12:30 interval where Tachibana Demo execution may not complete.

## Scope

This phase implemented the missing regular Runtime v2 entry for SELL Planning.

Implemented:
- Added `--job sell_planning` to Runtime v2 CLI allowed jobs.
- Connected `sell_planning` job to existing `run_sell_planning_pending_pipeline(...)`.
- SELL source is fixed to Current SoT positions from `.runtime/persistent_ledger/state.json`.
- SELL Pending is written to `.runtime/pending_order_plan/pending_order_plan.json`.
- Existing `submit` job remains the only submit path.
- Existing `execution` job remains the only execution/read-only sync path.
- Existing E47 Execution -> Current projection remains the Current update path after execution.

Not implemented:
- No SELL-specific Submit path.
- No SELL-specific Execution path.
- No Phase14-specific branch.
- No Demo-specific branch.
- No fake adapter or bypass.

## Runtime CLI Contract

New job:

```bash
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job sell_planning \
  --submit-enabled false \
  --notification-mode payload-only
```

The job performs:

1. Current SoT read
2. SELL source selection from Current positions only
3. SELL Planning
4. Approval artifact creation
5. Pending generation
6. Stop before Submit

Submit remains:

```bash
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job submit \
  --submit-enabled true \
  --notification-mode payload-only
```

Execution remains:

```bash
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job execution \
  --submit-enabled false \
  --notification-mode payload-only
```

## Validation Run

Executed command:

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache \
python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job sell_planning \
  --business-date 2026-07-09 \
  --submit-enabled false \
  --notification-mode payload-only \
  --stop-on-review-required \
  --stop-on-blocked
```

Result:

- exit_code: `0`
- manifest: `.runtime/runtime_state/run_manifest/2026-07-09/runtime-v2-sell_planning-2026-07-09-20260709T024852.974006+0000.json`
- submit_enabled: `false`
- demo_submit_executed: `false`
- production_order_executed: `false`
- notification_sent: `false`
- phase9_runtime_called: `false`
- phase9_writer_called: `false`

Generated Pending:

- path: `.runtime/pending_order_plan/pending_order_plan.json`
- state: `APPROVED`
- target_session_date: `2026-07-09`
- consumed: `false`
- approval_status: `APPROVED`
- item_count: `5`

SELL Pending items:

| Symbol | Side | Quantity | Estimated price | Estimated amount |
|---|---:|---:|---:|---:|
| 6897 | SELL | 500 | 676 | 338000 |
| 4591 | SELL | 5000 | 82 | 410000 |
| 3926 | SELL | 1000 | 351 | 351000 |
| 4446 | SELL | 500 | 871 | 435500 |
| 4935 | SELL | 1500 | 342 | 513000 |

## Acceptance Matrix

| Requirement | Result | Evidence |
|---|---|---|
| SELL Planning CLI exists | PASS | `--job sell_planning` accepted by Runtime v2 CLI |
| Current positions generate SELL Pending | PASS | 5 Current positions generated 5 SELL Pending items |
| BUY candidates are not SELL source | PASS | job reads Current SoT positions only, not feature/candidate artifacts |
| Current quantity guard | PASS | existing planner blocks quantity above Current position; regression test retained |
| 9000-series / target-excluded broker positions are not sold | PASS | E50 test places broker-only `9001` in position ledger evidence; Pending excludes it because source is Current only |
| Pending side is SELL | PASS | all Pending items have `side=SELL` |
| Submit not executed by sell_planning | PASS | manifest `demo_submit_executed=false`, `submit_enabled=false` |
| Existing submit pipeline remains submit authority | PASS | no SELL-specific submit path added |
| Existing execution pipeline remains execution authority | PASS | no SELL-specific execution path added |
| tests/runtime_v2 PASS | PASS | `351 passed` |

## Time Window Decision

At validation time:

- local time: `2026-07-09 11:48:46 JST`
- Tachibana Demo note: 11:30-12:30 may not execute.

Therefore E50 stopped after SELL Planning/Pending connection validation. SELL Submit/Execution should be run after 12:30 JST in a following phase using the regular `submit` and `execution` jobs.

## Files Changed

- `src/ai_fund_lab_v2/runtime_v2/cli/run_daily_operation.py`
- `tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py`

## Tests

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache \
python3 -m pytest \
  tests/runtime_v2/test_phase14e50_sell_planning_runtime_connection.py \
  tests/runtime_v2/test_phase14e32_sell_runtime_io_contract.py
```

Result: `5 passed`

```bash
PYTHONPATH=src PYTHONPYCACHEPREFIX=/private/tmp/ai-fund-lab-v2-pycache \
python3 -m pytest tests/runtime_v2
```

Result: `351 passed`

## Prohibited Actions Check

- Production order: not executed
- Notification real send: not executed
- launchd/plist change: not executed
- Current direct edit: not executed
- Broker all-holdings sell: not executed
- Demo-excluded / non-target broker position sell: not executed
- raw request / raw response / secret save: not executed
- Phase9 Runtime / Phase9 writer: not used

## Next Step

Run the already-generated SELL Pending through the existing Runtime v2 `submit` job and then the existing `execution` job after the 12:30 JST execution-risk window, if the operation goal is to complete the cleanup sell cycle.

