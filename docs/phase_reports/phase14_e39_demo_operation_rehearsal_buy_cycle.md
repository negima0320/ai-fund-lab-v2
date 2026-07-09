# Phase14-E39 Runtime v2 Demo Operation Rehearsal BUY Cycle

## Summary

Phase14-E39 attempted the Level 3 Runtime v2 Demo Operation Rehearsal BUY cycle using only existing Runtime v2 paths and CLI.

The cycle did not reach BUY Submit. It stopped safely at Market Refresh because the requested feature date `2026-07-09` could not be satisfied and the only available carryover feature date was `2026-07-07`, which exceeded the freshness limit.

Final judgment: `LEVEL3_DEMO_OPERATION_BUY_REVIEW_REQUIRED`

## Review Level

- Level: 3
- Scope: Demo Operation BUY cycle
- Runtime core change: none
- New Runtime module: none
- New CLI: none
- New Runtime path: none
- Fake adapter: none
- Submit bypass: none
- SELL execution: none
- Notification actual send: none

## Pre-Run Backup / Reset

E38-style backup and reset were executed before the rehearsal.

Backup root:

- `/private/tmp/phase14e39_backup_20260709T062231`

Backup targets:

- `.runtime/`
- `reports/runtime_v2/`
- `reports/public/runtime_v2/`

Backup signature:

- file count: `20347`
- total bytes: `5180470135`
- sha256: `e87ae1c8756833da27afe5d326613e4d084b6157127d670e19f4273818d34fa5`

Reset state:

| Field | Value |
| --- | ---: |
| cash | 1000000.0 |
| buying_power | 1000000.0 |
| market_value | 0 |
| total_equity | 1000000.0 |
| positions_count | 0 |
| pending_state | PENDING_APPROVAL |
| pending_items | 0 |

Reset report:

- `reports/public/runtime_v2/latest.md`
- redaction scan: PASS

## Runtime Execution

### Step 1: Market Refresh

Command:

```bash
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation \
  --mode demo \
  --job market_refresh \
  --business-date 2026-07-09 \
  --submit-enabled false \
  --notification-mode payload-only \
  --stop-on-review-required \
  --stop-on-blocked \
  --market-refresh-allow-api-fetch true
```

Manifest:

- `.runtime/runtime_state/run_manifest/2026-07-09/runtime-v2-market_refresh-2026-07-09-20260708T212253.147270+0000.json`

Result:

- `exit_code=10`
- `final_state=BLOCKED`
- `runtime_v2_market_refresh_pipeline=BLOCKED`
- reason: `market_refresh_blocked`

Market refresh details:

- `.runtime/operations/market_refresh/2026-07-09/market_data_refresh_detail.json`
- status: `API_PARAM_ERROR`
- blocked reasons:
  - `api_fetch_failed:JQuantsClientError`
  - `data_until_before_decision_for`
- data_until: `2026-07-07`
- not_yet_available_dates:
  - `2026-07-09`

Feature-date contract:

- `.runtime/operations/feature_date_contract/2026-07-09.json`
- requested_feature_date: `2026-07-09`
- selected_feature_date: `2026-07-07`
- latest_available_market_date: `2026-07-07`
- carryover_used: `true`
- carryover_reason: `requested_feature_date_missing_but_latest_available_is_stale`
- freshness_lag_business_days: `2`
- freshness_limit_business_days: `1`
- status: `REVIEW_REQUIRED`
- reason: `carryover_stale`

This means the E36 carryover policy worked as intended: stale carryover was not silently accepted.

### Step 2: Morning

Not executed.

Reason:

- Market Refresh blocked before Morning.

### Step 3: Submit

Not executed.

Reason:

- Market Refresh blocked before Morning/Pending.
- No submit-capable Pending was generated.

### Step 4: Broker Accepted

Not reached.

### Step 5: Execution / Current / Report / Blog / Notification Payload

BUY Execution was not reached.

The reset report remains available and shows:

- cash: `1000000.0`
- buying_power: `1000000.0`
- positions: `0`
- source: `phase14e8_demo_operation_initial_state`

## Post-Stop State

Current after stop:

- cash: `1000000.0`
- buying_power: `1000000.0`
- positions: `0`
- source: `phase14e8_demo_operation_initial_state`

Pending after stop:

- state: `PENDING_APPROVAL`
- items: `0`

Ledger after stop:

- `orders.jsonl`: empty
- `executions.jsonl`: empty
- `positions.jsonl`: empty

No BUY Submit occurred.

## Acceptance Mapping

| Item | Result | Evidence |
| --- | --- | --- |
| Backup | PASS | `/private/tmp/phase14e39_backup_20260709T062231` |
| Reset | PASS | Current 100万円 / 保有0 / Pending 0 |
| Market Refresh | BLOCKED | stale carryover + J-Quants error |
| Morning | NOT_EXECUTED | blocked before Morning |
| Pending | NOT_EXECUTED | no Morning after blocked Market Refresh |
| Submit | NOT_EXECUTED | no submit-capable Pending |
| Broker Accepted | NOT_REACHED | Submit not executed |
| Execution | NOT_REACHED | Submit not executed |
| Execution-equivalent | NOT_REACHED | Submit not executed |
| Ledger | PASS_NO_ORDER | no orders/executions/positions records written |
| Current | PASS_SAFE_INITIAL | remained 100万円 / 保有0 |
| Report | PASS_RESET_REPORT | latest report generated from reset Current |
| Blog/Public Report | PASS_RESET_REPORT | latest public report generated |
| Notification Payload | PAYLOAD_ONLY_RESET_CONTEXT | no actual send |

## Prohibited Actions Check

- SELL: not executed.
- Production order: not executed.
- Notification actual send: not executed.
- launchd change: not executed.
- Current direct edit: not performed.
- Runtime bypass: not performed.
- fake adapter: not used.
- Runtime core change: not performed.
- new Runtime module/CLI/path: not created.

## Review Required Reason

The BUY cycle cannot proceed until Market Refresh can provide a valid selected feature date under the E36 feature-date contract.

Current blocker:

- requested feature date: `2026-07-09`
- latest available market date: `2026-07-07`
- freshness lag: `2`
- allowed lag: `1`
- status: `carryover_stale`

Next attempt should start from the same E38 backup/reset procedure and re-run Market Refresh after market data freshness is resolved or an explicit policy decision changes the freshness limit.

## Final Judgment

`LEVEL3_DEMO_OPERATION_BUY_REVIEW_REQUIRED`

