# Runtime Submit Order Condition Authority Contract

## Purpose

Runtime Submit must not invent order conditions. This contract defines who decides and who verifies order conditions before Runtime v2 can reach Submit preflight or Submit.

## Authority Split

| Field | Authority | Runtime Rule |
| --- | --- | --- |
| `order_type` | Human Approval within Policy allowance | Submit Runtime must send unchanged. |
| `price_condition` | Human Approval within Policy allowance | Submit Runtime must send unchanged. |
| `limit_price` | Human Approval when `order_type=LIMIT` | `MARKET` must carry `limit_price=null`. |
| `target_session` | Submit Pending Producer from approved target session | Submit Runtime must require exact session match. |
| `time_in_force` | Human Approval within Policy allowance | Missing value blocks Submit. |
| Broker capability | Broker Capability Evidence | Submit preflight must verify supported side/order/session/cash/demo constraints. |

## Producer / Consumer

Policy defines allowed order methods and constraints.

Human Approval approves concrete order conditions for each item:

```text
order_type
price_condition
limit_price
target_session
time_in_force
quantity
side
issue_code
broker_issue_code
approved_at
expires_at
policy_hash
broker_capability_hash
```

Submit Pending Producer freezes approved conditions into Authoritative Pending. Broker Capability Evidence confirms the broker can accept the selected side, order type, session, quantity unit, trading unit, price tick, cash-equity constraint, and demo/production environment.

Submit Runtime is a consumer. It must not choose Market vs Limit and must not fill missing fields with defaults.

## Market Order

Market order conditions must explicitly include:

```text
order_type=MARKET
price_condition=MARKET
limit_price=null
time_in_force=DAY
```

## Blocking Rules

Submit preflight must block before the Broker client boundary when:

- `order_type` is missing or outside the supported contract.
- `price_condition` is missing.
- `time_in_force` is missing.
- `limit_price` is missing for `LIMIT`.
- `limit_price` is not `null` for `MARKET`.
- Pending item conditions do not match approved order conditions.
- Broker capability evidence does not support the side/order/session.
- Approval is expired for the target session.

## Phase15-BN Status

Phase15-BN resolves `ORDER_CONDITION_AUTHORITY_CONTRACT_REQUIRED` for the isolated normal SELL submit scenario.

The selected isolated scenario uses:

```text
side=SELL
issue_code=6522
order_type=MARKET
price_condition=MARKET
limit_price=null
target_session=2026-07-09
time_in_force=DAY
```

This is an Acceptance fixture, not an investment decision.
