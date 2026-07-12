# Phase15-BP Explicit Demo Broker Write Review

## Summary

Phase15-BP reviewed the final boundary before any real Tachibana Demo Broker Write.

Final judgment:

```text
DEMO_BROKER_WRITE_REVIEW_REQUIRED
```

Broker Write was not performed. Submit was not executed. Broker client send was not called.

Phase15-BO proved the isolated simulation path, but the same isolated root is not directly eligible for a real Demo Broker Write because the BO accepted simulation consumed the Pending, the target session is in the past, approval/safety evidence is stale, fresh broker read-only evidence is missing, and user explicit authorization is absent.

## Read Documents

- `docs/02_architecture/runtime_architecture_v2.md`
- `docs/02_architecture/runtime_temporal_freshness_contract.md`
- `docs/02_architecture/runtime_submit_order_condition_authority_contract.md`
- `docs/phase_reports/phase15_bn_isolated_normal_submit_scenario_preparation.md`
- `docs/phase_reports/phase15_bo_isolated_normal_submit_acceptance_simulation.md`
- `docs/phase_reports/phase15_bm_safety_blocked_submit_path_closure.md`
- `docs/phase_reports/phase15_bl_authoritative_submit_pending_apply_review.md`
- `docs/phase_reports/phase14_e51_sell_submit_execution_cleanup_cycle.md`
- `docs/phase_reports/phase14_e52_sell_submit_guard_contract_audit.md`
- `docs/phase_reports/phase14_e53_buy_sell_submit_guard_regression_audit.md`
- `docs/phase_reports/phase14_e47_execution_current_projection_runtime_connection_fix.md`
- `docs/phase_reports/phase14_e46_execution_current_projection_audit.md`
- `src/ai_fund_lab_v2/runtime_v2/submit/`
- `src/ai_fund_lab_v2/runtime_v2/execution/`
- `src/ai_fund_lab_v2/runtime_v2/pending/`
- `src/ai_fund_lab_v2/broker/tachibana*`
- `src/ai_fund_lab_v2/broker/runtime_v2_readonly_adapter.py`

## Safety Boundary

| Boundary | Result |
| --- | --- |
| Demo Broker API order send | Not called |
| Broker Write | Not performed |
| Submit | Not executed |
| Execution processing | Not performed |
| Current Apply | Not performed |
| Pending consume | Not performed in BP |
| Notification Send | Not performed |
| Production Write | Not performed |
| Existing `.runtime` mutation | Not performed |
| 4591 Safety解除 | Not performed |

## Runtime Roots

Existing Runtime Root:

```text
.runtime
```

This root remains the 4591 Safety-blocked evidence root and was not used for Demo Broker Write.

Isolated Runtime Root:

```text
.runtime_acceptance_phase15_submit
```

This root was used only for review evidence. Its current Pending state is:

```text
CONSUMED
```

That state is a blocker for real Demo Broker Write. A consumed Pending cannot be resent or promoted into real Broker Write.

## Scenario Candidate

The reviewed candidate is the Phase15-BN/BO SELL-first scenario.

| Field | Value |
| --- | --- |
| Side | `SELL` |
| Issue Code | `6522` |
| Quantity | `100` |
| Order Type | `MARKET` |
| Price Condition | `MARKET` |
| Limit Price | `null` |
| Time In Force | `DAY` |
| Environment | `demo` |
| Target Session | `2026-07-09` |

Assessment:

```text
NOT READY FOR REAL SEND
```

The order conditions match the fixture contract, but the target session is a past session and must not be reused for real Demo Broker Write.

## Broker Account Evidence

Fixture broker snapshot:

```text
.runtime_acceptance_phase15_submit/broker/snapshots/positions/positions-phase15bn.json
```

Observed fixture values:

| Field | Value |
| --- | --- |
| issue_code | `6522` |
| quantity | `100` |
| available_quantity | `100` |
| account_type | `cash` |
| as_of | `2026-07-09T08:30:00+09:00` |
| source | `broker_readonly` |

Classification:

```text
FIXTURE_PRESENT_STALE_READONLY_REFRESH_REQUIRED
```

The fixture demonstrates the required evidence shape, but it is not sufficient for real Demo Broker Write on a later date. Before any send, a fresh Tachibana Demo ReadOnly snapshot must confirm:

- target issue code exists in the demo account
- available quantity is at least `100`
- account type is compatible with cash equity SELL
- existing open orders do not conflict
- snapshot freshness is within policy

If 6522 is a Demo preloaded position rather than Runtime-owned position, it must be classified as:

```text
DEMO_PRELOADED_POSITION
NOT_RUNTIME_OWNED
ACCEPTANCE_ONLY
PRODUCTION_EQUIVALENT=false
```

That exception is Demo-only and must not be applied to Production.

## Safety Permissions

Fixture safety artifact:

```text
.runtime_acceptance_phase15_submit/runtime_state/safety/latest_safety_decision.json
```

Observed fixture permissions:

| Field | Value |
| --- | --- |
| `sell_submit` | `ALLOWED` |
| `broker_write` | `ALLOWED_FOR_ACCEPTANCE` |
| `business_date` | `2026-07-09` |
| `expires_at` | `2026-07-09T15:00:00+09:00` |

Classification:

```text
STALE_REGENERATION_REQUIRED
```

For real Demo Broker Write, Safety must be regenerated for the actual target session with explicit `sell_submit` and `broker_write` permission.

## Request Review

Request Review Artifact:

```text
.runtime_acceptance_phase15_submit/runtime_state/demo_broker_write_review/phase15bp_request_review.json
```

Redacted request evidence:

```text
reports/phase_reports/phase15_bp/request_review_redacted.json
```

Request hash:

```text
sha256:8e7f03c217ea1860554e76896721f82d9b5f0749c2f48cd276d82512662b9d60
```

The request hash covers redacted non-secret submit intent fields:

- environment
- issue_code / broker_issue_code
- side
- quantity
- order type / price condition / limit price
- target session
- pending identifiers
- approval hash

The artifact does not store credentials, raw token, secret key, plain account ID, or a complete raw request.

## Send Authority

Real Demo Broker Write requires all of the following:

| Authority | BP Status |
| --- | --- |
| Human Approval | Expired fixture; regeneration required |
| Authoritative Pending APPROVED | Not present; current pending is `CONSUMED` |
| Safety submit permission ALLOWED | Stale fixture; regeneration required |
| Safety broker_write permission ALLOWED | Stale fixture; regeneration required |
| Policy READY | Fixture policy exists; must be revalidated |
| Broker Snapshot fresh | Missing for actual send |
| Broker capability READY | Fixture capability exists; must be revalidated for target session |
| Order conditions approved | Fixture order conditions exist; target session expired |
| User explicit authorization | Not present |

No Broker adapter send may be called until every authority is present and current.

## User Authorization Artifact Contract

Codex did not create an approved authorization artifact.

The real send prefix must create it only after explicit user approval. Minimum fields:

```text
authorization_id
authorized_by=human_operator
environment=demo
pending_plan_id
pending_item_ids
issue_code
side
quantity
order_conditions
authorized_at
expires_at
request_hash
broker_write_authorized=true
production_write_authorized=false
```

## Send Preconditions

Current status:

```text
BLOCKED_UNTIL_REGENERATED_AND_AUTHORIZED
```

Required immediately before real send:

- User Authorization exists and is unexpired.
- Approval is unexpired and not revoked.
- Safety allows `sell_submit` and `broker_write`.
- Pending is `APPROVED`, not `CONSUMED`.
- Broker available quantity for `6522` is at least `100`.
- Open order list has no conflicting order.
- Target session is the actual trading session.
- Market hours/session rule permits the order.
- Broker capability is READY.
- Final request hash matches the authorization artifact.

If any state changes between preflight and send, send is forbidden.

## Send Follow-up Plan

If a future prefix receives explicit user authorization and performs Demo Broker Write, the follow-up plan is:

Accepted:

```text
APPROVED
-> SUBMITTING
-> SUBMITTED / ACCEPTED
-> Broker ReadOnly confirmation
-> MONITORING_FILL
```

Rejected:

```text
REJECTED
-> REVIEW_REQUIRED
```

Unknown:

```text
POST_SEND_UNKNOWN
-> automatic resend forbidden
-> Broker ReadOnly reconciliation
-> Human Review
```

Submit success must not be treated as Execution success.

## Cancel Policy Review

Cancel was not executed and is not accepted in BP.

Before real Demo Broker Write, the operator must decide:

- whether cancellation will be attempted for remaining open orders
- when cancellation should be attempted
- whether the order type/session allows cancellation
- what to do if already filled
- what to do on partial fill
- whether Cancel API is a separate Acceptance scope

Automatic cancellation is not allowed by this BP.

## Execution / Fill Confirmation Plan

Execution confirmation must be read-only first:

- Order List
- Execution List
- Position List
- Available Quantity
- Cash / Buying Power
- Order Status
- Execution Quantity
- Execution Price

Execution evidence must be normalized before any ledger/current update.

## Current Apply Boundary

Current Apply is outside BP.

Required future boundary:

```text
Broker Execution Evidence
-> Execution Normalization
-> Ledger append
-> Current projection
-> Current apply
```

BP does not mutate Current.

## Demo Account Impact

Potential impact if later authorized and sent:

- 6522 demo account position may decrease by 100 shares.
- An open order may remain if not filled.
- Buying power may change after sell acceptance/fill.
- Demo preloaded position handling may affect interpretation of ownership.
- Future Acceptance may be affected by residual orders or fills.
- Cancel inability or partial fill may require separate review.

Because fresh broker account state was not acquired in BP, impact remains:

```text
REVIEW_REQUIRED
```

## Regression

BP-specific regression:

```text
PYTHONPATH=src python3 -m pytest -q tests/runtime_v2/test_phase15bp_explicit_demo_broker_write_review.py
```

Additional existing coverage reviewed:

- User Authorizationなしではsend不可: BP artifact blocks send and existing submit path requires explicit live order enablement / approved pending.
- Authorization期限切れでsend不可: BP marks existing approval expired/stale.
- Authorization request hash不一致でsend不可: BP defines request hash as required authority field.
- Safety blockedでsend不可: Phase15-BM regression remains the Safety-blocked submit closure.
- Broker quantity不足でSELL不可: Phase15-M / Phase15-BN regression covers SELL available quantity guard.
- Target Session過去日でsend不可: BP marks `2026-07-09` as past-session blocker.
- Pending non-APPROVEDでsend不可: Current isolated pending is `CONSUMED` and blocked.
- No-send reviewでBroker client未呼出: BP did not call broker client.
- 既存 `.runtime` 不変: BP did not write `.runtime`.
- 隔離Rootのみ参照: BP request review artifact is under `.runtime_acceptance_phase15_submit`.

## Remaining Blockers

- Isolated pending is `CONSUMED` after BO and cannot be reused.
- Target session `2026-07-09` is stale for real send.
- Human Approval and Safety Decision are stale fixture evidence.
- Fresh Tachibana Demo ReadOnly broker snapshot is required.
- Fresh open order evidence is required.
- User explicit authorization artifact is absent.

## Final Judgment

```text
DEMO_BROKER_WRITE_REVIEW_REQUIRED
```

## Recommended Next Prefix

```text
Phase15-BQ Runtime Acceptance Step2 Demo Broker Write Preconditions Regeneration
```

BQ Execution should only be used after the user explicitly authorizes the exact issue code, side, quantity, order conditions, target session, and Demo Broker Write.
