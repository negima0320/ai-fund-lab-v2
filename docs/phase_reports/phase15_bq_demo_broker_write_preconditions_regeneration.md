# Phase15-BQ Demo Broker Write Preconditions Regeneration

## Summary

Phase15-BQ attempted to regenerate the fresh preconditions required before an explicit Tachibana Demo Broker Write.

Final judgment:

```text
DEMO_WRITE_PRECONDITIONS_BLOCKED
```

Broker Write was not performed. Submit was not executed. Execution processing, Current Apply, Notification Send, Production Write, and User Authorization artifact generation were not performed.

The blocker is the first required dependency: Tachibana Demo ReadOnly snapshot refresh failed with `FAILED_LOGIN_SESSION`, so no fresh Broker positions, available quantity, open orders, executions, cash, or buying power evidence exists for the real-send candidate selection.

## Read Documents

- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/02_architecture/runtime_submit_order_condition_authority_contract.md`
- `docs/phase_reports/phase15_bn_isolated_normal_submit_scenario_preparation.md`
- `docs/phase_reports/phase15_bo_isolated_normal_submit_acceptance_simulation.md`
- `docs/phase_reports/phase15_bp_explicit_demo_broker_write_review.md`
- `docs/phase_reports/phase14_e46_execution_current_projection_audit.md`
- `docs/phase_reports/phase14_e47_execution_current_projection_runtime_connection_fix.md`
- `docs/phase_reports/phase14_e51_sell_submit_execution_cleanup_cycle.md`
- `docs/phase_reports/phase14_e52_sell_submit_guard_contract_audit.md`
- `docs/phase_reports/phase14_e53_buy_sell_submit_guard_regression_audit.md`
- `src/ai_fund_lab_v2/runtime_v2/broker_readonly/`
- `src/ai_fund_lab_v2/runtime_v2/submit/`
- `src/ai_fund_lab_v2/runtime_v2/pending/`
- `src/ai_fund_lab_v2/runtime_v2/approval/`
- `src/ai_fund_lab_v2/runtime_v2/safety/`
- `src/ai_fund_lab_v2/broker/tachibana*`

## Existing Runtime Preservation

Existing Runtime Root:

```text
.runtime
```

Hash evidence after BQ:

| Artifact | SHA-256 |
| --- | --- |
| `.runtime/pending_order_plan/pending_order_plan.json` | `84075f23cc6d1c5ae227de1bfe4a213221aefd131fdadb395058755601ac2c77` |
| `.runtime/runtime_state/safety/latest_safety_decision.json` | `c4c1019497fc47b245ad92f21b0b06d59abe32e449f026eb0f9b0aed112faeb7` |
| `.runtime/persistent_ledger/state.json` | `add4f37373c6f7331b6894b29322ffd39a6a0c911086150427d57a2ddb442b0f` |

Result:

```text
existing_runtime_mutated=false
```

## Isolated Runtime Root

New isolated root:

```text
.runtime_acceptance_phase15_demo_write
```

Reason:

- `.runtime_acceptance_phase15_submit` was consumed by Phase15-BO simulation.
- The old approval/safety/target_session evidence was expired.
- Simulation evidence and real Demo Write preparation evidence must be separated.

## Fresh Business Date / Target Session

Review time:

```text
2026-07-12 07:18 JST
```

Selected fresh session:

| Field | Value |
| --- | --- |
| Current date | `2026-07-12` |
| Business date | `2026-07-13` |
| Target session | `2026-07-13` |
| Calendar source | `fallback` |
| Session status | `NEXT_TRADING_SESSION_SELECTED` |
| Send window status | `NOT_OPEN_AT_REVIEW_TIME` |

Past target session `2026-07-09` was not reused.

## Fresh Broker ReadOnly Snapshot

Command:

```text
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --mode demo --job broker_readonly_refresh --business-date 2026-07-13 --submit-enabled false --notification-mode payload-only --runtime-root .runtime_acceptance_phase15_demo_write --reports-root reports/phase_reports/phase15_bq/runtime_v2 --public-reports-root reports/phase_reports/phase15_bq/public_runtime_v2 --manifest-root .runtime_acceptance_phase15_demo_write/runtime_state/run_manifest --log-root .runtime_acceptance_phase15_demo_write/runtime_state/logs
```

Result:

| Field | Value |
| --- | --- |
| CLI exit code | `20` |
| Final state | `REVIEW_REQUIRED` |
| Snapshot status | `FAILED_LOGIN_SESSION` |
| Snapshot created | `false` |
| Data origin | `UNKNOWN` |
| Retry attempts | `3` |
| Safe error class | `BrokerConfigurationError` |
| Broker write executed | `false` |
| Ledger appended | `false` |
| Current position apply executed | `false` |
| Pending mutation executed | `false` |
| Secret saved | `false` |
| Raw response saved | `false` |

Evidence:

```text
.runtime_acceptance_phase15_demo_write/runtime_state/broker_readonly/2026-07-13/snapshot_report.json
.runtime_acceptance_phase15_demo_write/runtime_state/run_manifest/2026-07-13/runtime-v2-broker_readonly_refresh-2026-07-13-20260711T221839.983572+0000.json
```

Because the snapshot was not created, the following are missing:

- Cash Position List
- Margin Position List
- Available Quantity
- Open Order List
- Execution List
- Cash / Buying Power
- Broker data `as_of`
- Account identity hash
- `data_origin=BROKER_API`

## Scenario Candidate Selection

SELL-first selection was required, but it could not proceed.

Status:

```text
BLOCKED
```

Reason:

```text
fresh Broker ReadOnly evidence missing
```

Candidate count:

```text
0
```

No Demo preloaded position was selected. No position was classified as `DEMO_PRELOADED_POSITION` because fresh account evidence was unavailable.

## Quantity

No quantity was selected.

Reason:

- available_quantity is unknown
- open order conflict is unknown
- lot/unit suitability cannot be confirmed
- user approval target cannot be formed

## BUY Fallback

BUY fallback was not selected.

Reason:

- BUY is a different acceptance scope.
- Fresh cash/buying power evidence is also missing.
- Safety BUY permission was not regenerated.

## Fresh Safety Evidence

Status:

```text
NOT_GENERATED
```

Reason:

Fresh Safety for broker_write acceptance requires fresh Broker Snapshot, open order evidence, policy readiness, and selected scenario. The upstream Broker ReadOnly dependency failed.

## Human Approval Candidate

Status:

```text
NOT_GENERATED
```

Reason:

No fresh scenario candidate exists. BQ did not synthesize approval or user authorization.

## Fresh Pending Chain

| Artifact | Status |
| --- | --- |
| Review / Scenario Evidence | `BLOCKED` |
| Human Approval Candidate | `NOT_GENERATED` |
| Promotion Candidate | `NOT_GENERATED` |
| Apply Candidate | `NOT_GENERATED` |
| Authoritative Submit Pending | `NOT_GENERATED` |

No unconsumed `APPROVED` Pending was created.

## No-Send Submit Preflight

Status:

```text
NOT_RUN
```

Reason:

No fresh scenario and no Authoritative Pending exist.

## Final Request Review

Artifact:

```text
reports/phase_reports/phase15_bq/final_request_review_redacted.json
```

Status:

```text
BLOCKED
```

No request hash was generated because no request payload is ready.

The artifact confirms that no credentials, plain account ID, raw token, secret key, or full raw request were saved.

## User Authorization Contract

User Authorization is absent and was not generated.

Before any future real Demo Broker Write, the user must explicitly confirm:

- Demo environment
- target issue code
- side
- quantity
- order conditions
- target session
- expected account impact
- unfilled/partial-fill policy
- explicit Broker Write permission

## Cancel / Follow-up Plan

Cancel plan status:

```text
NOT_APPLICABLE_UNTIL_REQUEST_SELECTED
```

Future send follow-up remains:

- automatic resend forbidden
- Broker ReadOnly order list confirmation
- Broker ReadOnly execution list confirmation
- no Current Apply until execution evidence is normalized and accepted
- Cancel API remains a separate explicit scope

## Regression

BQ-specific regression:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase15bq_demo_broker_write_preconditions_regeneration.py
```

Result:

```text
5 passed
```

Regression intent:

- consumed Pending is not reused
- stale session is not reused
- fresh Broker Snapshot is mandatory
- open order evidence is mandatory
- no user authorization is synthesized
- no broker client send or Broker Write occurs
- existing `.runtime` is preserved
- only `.runtime_acceptance_phase15_demo_write` is used

## Remaining Blockers

- Tachibana Demo ReadOnly snapshot failed with `FAILED_LOGIN_SESSION`.
- Fresh Broker positions / available quantity are missing.
- Fresh open order evidence is missing.
- Fresh cash / buying power evidence is missing.
- No SELL scenario candidate can be selected.
- Fresh Safety Decision cannot be generated.
- Human Approval Candidate cannot be generated.
- Authoritative Pending cannot be built.
- No-send Submit Preflight cannot run.
- User explicit authorization is absent.

## Final Judgment

```text
DEMO_WRITE_PRECONDITIONS_BLOCKED
```

## Recommended Next Prefix

```text
Phase15-BQ-Retry Tachibana Demo ReadOnly Login Session Recovery
```
