# Phase15-BQ-R2 Demo Environment Reinitialization and Fresh Preconditions

## Summary

Phase15-BQ-R2 reinitialized the Tachibana Demo environment evidence after the demo account reset.

Final judgment:

```text
DEMO_ENVIRONMENT_READY
```

The previous 6522 SELL scenario and all derived artifacts were not reused. No Broker Write, Submit, Execution processing, Pending generation, Human Approval, Promotion, Apply, Request Hash, or scenario fixation was performed.

## Runtime Root

New isolated root:

```text
.runtime_acceptance_phase15_demo_reinit
```

Previous roots and scenarios were not reused:

- `.runtime_acceptance_phase15_submit`
- `.runtime_acceptance_phase15_demo_write`
- previous `6522 SELL` scenario
- previous Human Approval / Pending / Request Review

Existing `.runtime` hash remained unchanged:

| Artifact | SHA-256 |
| --- | --- |
| `.runtime/pending_order_plan/pending_order_plan.json` | `84075f23cc6d1c5ae227de1bfe4a213221aefd131fdadb395058755601ac2c77` |
| `.runtime/runtime_state/safety/latest_safety_decision.json` | `c4c1019497fc47b245ad92f21b0b06d59abe32e449f026eb0f9b0aed112faeb7` |
| `.runtime/persistent_ledger/state.json` | `add4f37373c6f7331b6894b29322ffd39a6a0c911086150427d57a2ddb442b0f` |

## Executed ReadOnly Flow

Executed order:

```text
Demo Login
↓
Session取得
↓
Broker ReadOnly Snapshot
↓
Open Orders
↓
Execution List
↓
Cash / Buying Power
↓
Position Inventory
↓
Broker Evidence更新
↓
Scenario候補調査
```

Command:

```text
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --mode demo --job broker_readonly_refresh --business-date 2026-07-13 --submit-enabled false --notification-mode payload-only --runtime-root .runtime_acceptance_phase15_demo_reinit --reports-root reports/phase_reports/phase15_bq_r2/runtime_v2 --public-reports-root reports/phase_reports/phase15_bq_r2/public_runtime_v2 --manifest-root .runtime_acceptance_phase15_demo_reinit/runtime_state/run_manifest --log-root .runtime_acceptance_phase15_demo_reinit/runtime_state/logs
```

Result:

| Field | Value |
| --- | --- |
| CLI exit code | `0` |
| Broker refresh status | `READY` |
| Snapshot status | `PASS_WITH_WARNINGS` |
| Session status | `PASS` |
| Data origin | `BROKER_API` |
| Fixture used | `false` |
| Mock used | `false` |
| Broker write executed | `false` |
| Ledger appended | `false` |
| Current apply executed | `false` |
| Pending mutation executed | `false` |
| Secret saved | `false` |
| Raw response saved | `false` |

Evidence:

```text
.runtime_acceptance_phase15_demo_reinit/runtime_state/broker_readonly/2026-07-13/tachibana_snapshot.json
.runtime_acceptance_phase15_demo_reinit/runtime_state/broker_readonly/2026-07-13/snapshot_report.json
.runtime_acceptance_phase15_demo_reinit/runtime_state/broker_readonly/latest.json
.runtime_acceptance_phase15_demo_reinit/runtime_state/run_manifest/2026-07-13/runtime-v2-broker_readonly_refresh-2026-07-13-20260711T234421.772078+0000.json
reports/phase_reports/phase15_bq_r2/broker_environment_inventory.json
```

## Broker Evidence

| Item | Evidence |
| --- | --- |
| Snapshot generated_at | `2026-07-11T23:44:24.193132+00:00` |
| Snapshot as_of | `2026-07-11T23:44:24.193132+00:00` |
| Runtime business date | `2026-07-13` |
| Account identity | `REFERENCE_HASHED` |
| Account id | redacted |
| Open orders | `0` |
| Executions | `0` |
| Position records | `7` |
| Cash available | `18,070,600 JPY` |
| Buying power | `20,000,000 JPY` |

## Position Inventory Classification

Classification rules:

- Runtime-owned: source submit / execution linkage exists in this fresh Runtime root.
- Demo preloaded: Demo account initial cash position, not Runtime-owned, acceptance-only.
- Unknown: no Runtime-owned link and not a positive cash preloaded position.

| Issue Code | Account | Quantity | Available | Classification | Runtime-owned | Acceptance-only | Production equivalent |
| --- | --- | ---: | ---: | --- | --- | --- | --- |
| `6501` | cash | `200` | `200` | `DEMO_PRELOADED_POSITION` | `false` | `true` | `false` |
| `6502` | cash | `2000` | `2000` | `DEMO_PRELOADED_POSITION` | `false` | `true` | `false` |
| `9984` | cash | `400` | `400` | `DEMO_PRELOADED_POSITION` | `false` | `true` | `false` |
| `6504` | margin | `0` | `0` | `UNKNOWN_ZERO_QUANTITY_MARGIN_RECORD` | `false` | `false` | `false` |
| `6504` | margin | `0` | `0` | `UNKNOWN_ZERO_QUANTITY_MARGIN_RECORD` | `false` | `false` | `false` |
| `6505` | margin | `0` | `0` | `UNKNOWN_ZERO_QUANTITY_MARGIN_RECORD` | `false` | `false` | `false` |
| `9001` | margin | `0` | `0` | `UNKNOWN_ZERO_QUANTITY_MARGIN_RECORD` | `false` | `false` | `false` |

No Broker position was classified as Runtime-owned because this is a fresh reinitialization root and no submit/execution linkage exists.

## Scenario Candidate Investigation

Scenario was not fixed.

Potential SELL candidates for the next review are only inventory candidates:

| Issue Code | Available Quantity | Classification |
| --- | ---: | --- |
| `6501` | `200` | `DEMO_PRELOADED_POSITION` |
| `6502` | `2000` | `DEMO_PRELOADED_POSITION` |
| `9984` | `400` | `DEMO_PRELOADED_POSITION` |

These are not investment decisions and not approved orders. They are only acceptance candidates for Phase15-BR2.

BUY scenario was not evaluated in BQ-R2 because the instruction was environment reinitialization, not scenario selection.

## Prohibited Actions Result

| Action | Result |
| --- | --- |
| Broker Write | Not performed |
| Submit | Not performed |
| Execution processing | Not performed |
| Pending generation | Not performed |
| Human Approval | Not generated |
| Promotion | Not generated |
| Apply | Not generated |
| Request Hash | Not generated |
| Scenario fixed | Not performed |

## Remaining Review Items

- Select scenario in Phase15-BR2 from fresh Broker Evidence only.
- Decide whether SELL or BUY is appropriate for Acceptance.
- If using Demo preloaded positions, keep `production_equivalent=false`.
- Generate Safety / Policy / Approval / Pending only after scenario selection.

## Final Judgment

```text
DEMO_ENVIRONMENT_READY
```

## Next Prefix

```text
Phase15-BR2 Demo Scenario Selection
```
