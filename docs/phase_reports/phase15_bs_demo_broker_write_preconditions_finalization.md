# Phase15-BS Demo Broker Write Preconditions Finalization

## Summary

Phase15-BS finalized the no-send preconditions for the selected Fresh Demo scenario:

```text
demo / SELL / 6501 / 100 shares / MARKET / DAY / target_session=2026-07-13
```

Final judgment:

```text
DEMO_WRITE_READY_FOR_USER_AUTHORIZATION
```

Broker Write, Submit send, Execution processing, Current Apply, Notification Send, Production Write, and User Authorization artifact generation were not performed.

## Read Documents

- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/02_architecture/runtime_submit_order_condition_authority_contract.md`
- `docs/phase_reports/phase15_bq_r2_demo_environment_reinitialization.md`
- `docs/phase_reports/phase15_br2_demo_scenario_selection.md`
- `docs/phase_reports/phase15_bo_isolated_normal_submit_acceptance_simulation.md`
- `docs/phase_reports/phase15_bp_explicit_demo_broker_write_review.md`
- `docs/phase_reports/phase15_bq_demo_broker_write_preconditions_regeneration.md`
- `docs/phase_reports/phase14_e46_execution_current_projection_audit.md`
- `docs/phase_reports/phase14_e47_execution_current_projection_runtime_connection_fix.md`
- `docs/phase_reports/phase14_e51_sell_submit_execution_cleanup_cycle.md`
- `docs/phase_reports/phase14_e52_sell_submit_guard_contract_audit.md`
- `docs/phase_reports/phase14_e53_buy_sell_submit_guard_regression_audit.md`
- `src/ai_fund_lab_v2/runtime_v2/broker_readonly/`
- `src/ai_fund_lab_v2/runtime_v2/broker_adapter/`
- `src/ai_fund_lab_v2/runtime_v2/safety/`
- `src/ai_fund_lab_v2/runtime_v2/approval/`
- `src/ai_fund_lab_v2/runtime_v2/pending/`
- `src/ai_fund_lab_v2/runtime_v2/submit/`

## Runtime Root

BS used only the isolated root:

```text
.runtime_acceptance_phase15_demo_reinit
```

Existing `.runtime` was not changed.

| Existing Runtime Artifact | SHA-256 |
| --- | --- |
| `.runtime/pending_order_plan/pending_order_plan.json` | `84075f23cc6d1c5ae227de1bfe4a213221aefd131fdadb395058755601ac2c77` |
| `.runtime/runtime_state/safety/latest_safety_decision.json` | `c4c1019497fc47b245ad92f21b0b06d59abe32e449f026eb0f9b0aed112faeb7` |
| `.runtime/persistent_ledger/state.json` | `add4f37373c6f7331b6894b29322ffd39a6a0c911086150427d57a2ddb442b0f` |

Result:

```text
existing_runtime_mutated=false
```

## Fresh Broker Snapshot

Fresh ReadOnly command:

```text
PYTHONPATH=src python3 -m ai_fund_lab_v2.runtime_v2.cli.run_daily_operation --mode demo --job broker_readonly_refresh --business-date 2026-07-13 --submit-enabled false --notification-mode payload-only --runtime-root .runtime_acceptance_phase15_demo_reinit --reports-root reports/phase_reports/phase15_bs/runtime_v2 --public-reports-root reports/phase_reports/phase15_bs/public_runtime_v2 --manifest-root .runtime_acceptance_phase15_demo_reinit/runtime_state/run_manifest --log-root .runtime_acceptance_phase15_demo_reinit/runtime_state/logs
```

The first sandboxed attempt returned `FAILED_LOGIN_SESSION`; the approved network/session retry succeeded.

Successful manifest:

```text
.runtime_acceptance_phase15_demo_reinit/runtime_state/run_manifest/2026-07-13/runtime-v2-broker_readonly_refresh-2026-07-13-20260712T000204.142389+0000.json
```

| Field | Value |
| --- | --- |
| Snapshot status | `PASS_WITH_WARNINGS` |
| Refresh status | `READY` |
| Data origin | `BROKER_API` |
| Fixture used | `false` |
| Mock used | `false` |
| Snapshot generated_at | `2026-07-12T00:02:05.935570+00:00` |
| Open orders | `0` |
| Executions | `0` |
| Cash available | `18,070,600 JPY` |
| Buying power | `20,000,000 JPY` |
| Broker write executed | `false` |
| Pending mutation by refresh | `false` |
| Current apply by refresh | `false` |

## 6501 Evidence

| Field | Value |
| --- | --- |
| Issue Code | `6501` |
| Account type | `cash` |
| Quantity | `200` |
| Available quantity | `200` |
| Market price | `4,700 JPY` |
| Market value | `940,000 JPY` |
| Open SELL conflict | `false` |
| Open opposite-side conflict | `false` |
| Position origin | `DEMO_PRELOADED_POSITION` |
| Runtime-owned | `false` |
| Acceptance-only | `true` |
| Production equivalent | `false` |

The selected quantity `100` is within the fresh available quantity.

## Session Evidence

| Field | Value |
| --- | --- |
| Business date | `2026-07-13` |
| Target session | `2026-07-13` |
| Market open status | `true` |
| Order validity | `DAY` |
| Session expiration | `2026-07-13T15:00:00+09:00` |
| Broker send window | `READY_FOR_USER_AUTHORIZATION_PRE_SEND_RECHECK_REQUIRED` |

The target session is not stale or expired. Actual broker send window must be rechecked in Phase15-BT immediately before any Broker adapter send.

## Broker Capability

Artifact:

```text
.runtime_acceptance_phase15_demo_reinit/runtime_state/demo_broker_write_preconditions/2026-07-13/broker_capability_evidence.json
```

Status:

```text
READY
```

The artifact records `demo`, `SELL`, `cash_equity`, `6501`, `MARKET`, `MARKET`, `limit_price=null`, `DAY`, `quantity=100`, trading unit validity, static config version, and config hash.

## Policy

Artifacts:

```text
.runtime_acceptance_phase15_demo_reinit/runtime_state/policy/phase15bs_capital_deployment_policy.json
.runtime_acceptance_phase15_demo_reinit/runtime_state/demo_broker_write_preconditions/2026-07-13/policy_evidence.json
```

Status:

```text
READY
```

Policy explicitly allows only the Phase15-BS acceptance scenario: Demo preloaded `6501`, `SELL`, quantity `100`, `MARKET`, `DAY`, `production_equivalent=false`, `acceptance_only=true`.

## Safety

Safety source:

```text
.runtime_acceptance_phase15_demo_reinit/reports/safety/phase11/2026-07-13_safety_report.json
```

Runtime Safety Decision:

```text
.runtime_acceptance_phase15_demo_reinit/runtime_state/safety/latest_safety_decision.json
```

| Field | Value |
| --- | --- |
| Decision | `ALLOW` |
| Safety status | `PASS` |
| `sell_submit` | `ALLOWED` |
| `broker_write` | `ALLOWED_FOR_ACCEPTANCE` |
| `buy_submit` | `BLOCKED` |
| `auto_sell` | `BLOCKED` |
| `expires_at` | `2026-07-13T15:00:00+09:00` |

Safety was generated through the Runtime Safety producer. Producer support was tightened so `broker_write_acceptance_scope=ALLOWED_FOR_ACCEPTANCE` is produced by the Safety route, and `block_buy=true` keeps `buy_submit=BLOCKED`.

## Human Approval Candidate

Artifact:

```text
.runtime_acceptance_phase15_demo_reinit/runtime_state/human_approval/2026-07-13/phase15bs_human_approval_candidate.json
```

| Field | Value |
| --- | --- |
| Status | `APPROVED_FOR_PENDING_PROMOTION` |
| Issue | `6501` |
| Side | `SELL` |
| Quantity | `100` |
| Order conditions | `MARKET / MARKET / null / DAY` |
| `automatic_trade_authorized` | `false` |
| `broker_write_authorized` | `false` |
| `authoritative_pending_promotion_authorized` | `true` |

This is not User Broker Write Authorization.

## Promotion / Apply / Pending

| Artifact | Status |
| --- | --- |
| Promotion Candidate | `READY` |
| Apply Candidate | `READY` |
| Authoritative Submit Pending | `APPROVED` |

Authoritative Pending:

```text
.runtime_acceptance_phase15_demo_reinit/pending_order_plan/pending_order_plan.json
```

The Pending item is unconsumed, linked to the fresh Approval / Policy / Safety / Broker evidence, and scoped to `6501 SELL 100 MARKET DAY target_session=2026-07-13`.

## No-Send Submit Preflight

Artifact:

```text
.runtime_acceptance_phase15_demo_reinit/runtime_state/demo_broker_write_preconditions/2026-07-13/no_send_submit_preflight.json
```

| Field | Value |
| --- | --- |
| Pending state | `APPROVED` |
| Submit preflight status | `READY` |
| Preflight allowed | `true` |
| Request payload ready | `true` |
| Request hash generated | `true` |
| Submit attempted | `false` |
| Broker client called | `false` |
| Broker write performed | `false` |

Final Request Hash:

```text
sha256:56ebea4e14ffe7369f133260645720c49303711b74c21960973e833016b37f70
```

## Final Request Review

Artifact:

```text
reports/phase_reports/phase15_bs/final_request_review_redacted.json
```

The review artifact contains only redacted, non-secret request fields. It records:

- Demo environment.
- `6501`.
- `SELL`.
- `100`.
- `MARKET`.
- `DAY`.
- Fresh available quantity `200`.
- Open order conflict `NONE`.
- Safety `sell_submit=ALLOWED`.
- Safety `broker_write=ALLOWED_FOR_ACCEPTANCE`.
- Estimated impact: `6501 position 200 -> 100` if fully filled.
- Submit attempted `false`.
- Broker Write performed `false`.
- User Authorization present `false`.

## Cancel / Follow-up Plan

Artifact:

```text
.runtime_acceptance_phase15_demo_reinit/runtime_state/demo_broker_write_preconditions/2026-07-13/cancel_followup_plan.json
```

| Case | Plan |
| --- | --- |
| Unfilled | Broker ReadOnly order check; no automatic resend; no automatic cancel. |
| Partial fill | Confirm execution quantity and residual quantity; Human Review. |
| Immediate fill | Confirm Execution List, Position List, Cash, and Buying Power. |
| POST_SEND_UNKNOWN | No automatic resend; reconcile Order List and Execution List; Human Review. |
| Cancel | Separate explicit Acceptance Scope required. |

## Current Apply Boundary

Current Apply was not performed. Submit acceptance alone must not update Current.

Future flow remains:

```text
Broker Write
↓
Order ReadOnly確認
↓
Execution / Fill Evidence
↓
Execution Normalization
↓
Ledger Append
↓
Current Projection
↓
Current Apply
```

## Regression

| Check | Result |
| --- | --- |
| Fresh Broker Snapshotなしでblock | `PASS` |
| Available Quantity不足でblock | `PASS` |
| Open Order conflictでblock | `PASS` |
| Target Session staleでblock | `PASS` |
| Broker Capability不一致でblock | `PASS` |
| Policy不一致でblock | `PASS` |
| Safety blockedでblock | `PASS` |
| Approval期限切れでblock | `PASS` |
| Approval hash不一致でblock | `PASS` |
| Pending non-EMPTY before applyでblock | `PASS` |
| 注文条件欠損でblock | `PASS` |
| No-send Preflight READY | `PASS` |
| Broker client未呼出 | `PASS` |
| Broker Writeなし | `PASS` |
| User Authorizationなしでsend不可 | `PASS` |
| 既存`.runtime`不変 | `PASS` |
| 隔離Rootのみ使用 | `PASS` |

Regression command:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase15bs_demo_broker_write_preconditions_finalization.py tests/runtime_v2/test_phase15ac_runtime_safety_decision_producer.py tests/runtime_v2/test_phase15bm_safety_blocked_submit_path.py
```

## Remaining Blockers

These are intentional next-phase gates:

- `USER_AUTHORIZATION_NOT_PRESENT`
- `BROKER_SEND_WINDOW_RECHECK_REQUIRED`

## Final Judgment

```text
DEMO_WRITE_READY_FOR_USER_AUTHORIZATION
```

## Next Prefix

```text
Phase15-BT Explicit Demo Broker Write User Authorization and Execution
```

BT may proceed only if the user explicitly approves the Final Request Review for Demo / 6501 / SELL / 100 shares / MARKET / DAY / target session / Demo account impact / Broker Write.
