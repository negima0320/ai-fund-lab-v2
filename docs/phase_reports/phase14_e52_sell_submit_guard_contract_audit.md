# Phase14-E52 SELL Submit Guard Contract Audit

## Summary

Phase14-E52 audited why the Phase14-E51 SELL cleanup cycle stopped at Submit preflight.

Final judgment: **PHASE14E52_SELL_GUARD_CONTRACT_IDENTIFIED**

This phase was audit-only.

No code was changed. No Runtime behavior was changed. No Broker Submit, Production order, Notification send, launchd change, or Current direct edit was performed.

## E51 Stop Point

E51 stopped at:

```text
SELL Pending -> Runtime v2 submit preflight guard
```

Submit manifest:

```text
.runtime/runtime_state/run_manifest/2026-07-09/runtime-v2-submit-2026-07-09-20260709T025724.778276+0000.json
```

Submit result:

| Field | Value |
|---|---:|
| exit_code | `10` |
| final_state | `BLOCKED` |
| demo_submit_executed | `false` |
| submitted_count | `0` |
| accepted_count | `0` |
| rejected_count | `0` |
| unknown_count | `0` |
| blocked_count | `5` |
| pending_consumed | `false` |

All 5 items were blocked before Broker write:

| Symbol | Side | Estimated amount | Current max_order_amount | Result |
|---|---:|---:|---:|---|
| 6897 | SELL | 338000 | 100000 | BLOCKED |
| 4591 | SELL | 410000 | 100000 | BLOCKED |
| 3926 | SELL | 351000 | 100000 | BLOCKED |
| 4446 | SELL | 435500 | 100000 | BLOCKED |
| 4935 | SELL | 513000 | 100000 | BLOCKED |

Guard reason:

```text
estimated amount exceeds max order amount
```

## Current Implementation Contract

### Source

`src/ai_fund_lab_v2/runtime_v2/submit/pipeline.py`

`run_submit_pipeline(...)` has:

```python
max_order_amount: float | None = 100_000.0
```

The Runtime v2 CLI calls `run_submit_pipeline(...)` without overriding `max_order_amount`, so the regular CLI path uses:

```text
max_order_amount = 100000
```

### Guard Logic

`src/ai_fund_lab_v2/runtime_v2/submit/guards.py`

The guard is side-agnostic:

```python
if max_order_amount is not None and item.estimated_amount > max_order_amount:
    return "estimated amount exceeds max order amount"
```

Therefore, in the current implementation:

- BUY and SELL use the same max_order_amount guard.
- SELL liquidation notional is blocked when `estimated_amount > 100000`.
- The max notional check runs after SELL quantity / position / available quantity checks.

### CLI Exposure

The regular Runtime v2 CLI does not currently expose a `--max-order-amount` argument for Submit.

Therefore, E51 could not raise this limit via the normal operation entry. It used the default `100000`.

## Design Evidence

### Phase14-B Preflight Design

`docs/phase_reports/phase14_b_demo_broker_buy_sell_preflight.md`

Phase14-B separates:

- `max order amount guard` under BUY checks.
- `sell quantity guard` under SELL checks.

SELL design focuses on:

- Broker ReadOnly position exists.
- SELL quantity does not exceed broker position quantity.
- SELL quantity does not exceed available quantity.
- Current Asset State and Broker Position do not materially diverge.
- Unknown position quantity blocks Submit.

This document does not clearly state that SELL liquidation must be blocked by the same notional cap as BUY.

### Phase14-D3 Pure Submit Path Design

`docs/phase_reports/phase14_d3_runtime_v2_pure_demo_submit_path_redesign.md`

Phase14-D3 lists Runtime v2 submit guard requirements and includes:

```text
estimated amount does not exceed max order amount
```

This text is side-agnostic and matches the current implementation.

### Phase14-D14 SELL Preflight

`docs/phase_reports/phase14_d14_demo_sell_guarded_preflight.md`

Phase14-D14 defines SELL-specific guards around:

- position quantity
- available quantity
- Pending-only Submit
- Approval
- duplicate submit

Its D14 test used:

```text
max_order_amount = 500000
```

for a `7203 SELL 100` with estimated amount `294100`, so that single-order SELL preflight could pass.

This proves the SELL submit path can pass when the max notional limit is above the liquidation amount, but it does not settle the general daily-operation contract for SELL liquidation.

### Phase14-D23 Production Readiness Audit

`docs/phase_reports/phase14_d23_phase13_runtime_v2_contract_full_compliance_audit.md`

Production readiness explicitly leaves these items for production review:

```text
max order amount / position / cash / buying power / kill switch / halt conditions
```

This indicates max_order_amount is not fully finalized as a production contract.

### Phase11 Safety Context

`docs/phase_reports/phase11_completion_audit.md`

Safety max exposure rules are documented as BUY/new exposure oriented, with SELL/exposure-reducing orders passing that specific max exposure guard.

That is a Safety guard concept, not the Runtime v2 Submit max_order_amount guard, but it supports the idea that exposure-reducing SELLs may need a different contract than BUYs.

## Classification

Current implementation behavior:

```text
BUY and SELL share the same max_order_amount Submit preflight guard.
```

Current configured/default value:

```text
100000 JPY
```

E51 SELL item notionals:

```text
338000, 410000, 351000, 435500, 513000
```

Therefore E51 was correctly blocked by the current implementation.

However, the design contract is not fully settled:

- Phase14-B and D14 describe SELL primarily through position/available-quantity safety.
- Phase14-D3 describes max order amount as side-agnostic.
- Phase14-D23 says max order amount requires further review before Production.
- No document explicitly defines how a Runtime-owned multi-position liquidation should behave when the liquidation notional exceeds a BUY-sized max order amount.

Judgment:

```text
Implementation behavior: SPEC_CURRENT_IMPLEMENTATION
Design status: CONTRACT_GAP_FOR_SELL_LIQUIDATION
E51 stop: EXPECTED_UNDER_CURRENT_DEFAULT
Production readiness: REVIEW_REQUIRED
```

## Operator Explanation

E51 did not fail because of Tachibana Demo, issue code conversion, Broker reject, or Execution evidence.

The Runtime stopped before Broker write because every SELL order had an estimated notional above the current default max order amount of `100000`.

This prevented accidental large orders, but it also prevents normal liquidation of Runtime-owned positions whose market value is greater than the BUY sizing cap.

## Design Options For Next Phase

No implementation was performed in E52. The following are candidate fixes for a later phase.

### Option A: Keep One Shared Max Notional Guard

Meaning:
- BUY and SELL both use the same notional cap.
- SELL cleanup must split orders or reduce quantities until each order is within cap.

Pros:
- Conservative and simple.
- Prevents large accidental SELL orders.

Cons:
- SELL liquidation may require partial lots.
- Japanese lot size and current position quantity may prevent exact cap-respecting liquidation.
- Multi-day cleanup logic may be required.

### Option B: Separate BUY Max Order Amount and SELL Liquidation Max Amount

Meaning:
- BUY keeps `max_buy_order_amount`.
- SELL uses `max_sell_order_amount` or `max_liquidation_order_amount`.

Pros:
- Preserves BUY risk cap.
- Allows intended exposure reduction.

Cons:
- Requires an explicit Runtime contract and tests.
- Needs Production readiness review.

### Option C: SELL Liquidation Exempt From Notional Cap If It Reduces Runtime-owned Exposure

Meaning:
- SELL can exceed BUY notional cap only when:
  - source is Current SoT Runtime-owned position,
  - quantity <= Current position,
  - Broker available quantity confirms the same,
  - Pending/Approval/Duplicate/Production guards pass.

Pros:
- Matches exposure-reducing semantics.
- Avoids unnecessary partial liquidation mechanics.

Cons:
- Must be very carefully scoped to avoid accidental all-holdings sell or broker-only position sell.

### Option D: Human Review For SELL Above BUY Cap

Meaning:
- Large SELL is not auto-blocked permanently.
- Runtime stops in REVIEW_REQUIRED with a manual approval/unlock path.

Pros:
- Conservative and operator-visible.

Cons:
- Requires manual intervention contract and unlock artifact before Demo/Production operation.

## Recommended Direction

Recommended next contract:

```text
Split BUY and SELL notional guards.
```

Suggested contract:

- BUY:
  - keep `max_buy_order_amount`
  - default can remain conservative
  - applies to new exposure
- SELL:
  - enforce Current position quantity guard
  - enforce Broker available quantity guard
  - enforce Runtime-owned source guard
  - do not sell broker-only positions
  - use either:
    - higher `max_sell_liquidation_amount`, or
    - explicit review-required threshold
- Any SELL exceeding the configured SELL liquidation policy should become `REVIEW_REQUIRED`, not silent success.

This should be implemented only as a regular Runtime submit guard contract, not as a Phase14/Demo-only bypass.

## Acceptance

| Acceptance | Result |
|---|---|
| SELL Guard reason is operator-explainable | PASS |
| max_order_amount current value identified | PASS |
| max_order_amount source identified | PASS |
| BUY/SELL same current implementation identified | PASS |
| E51 BLOCK condition explained | PASS |
| Existing design documents checked | PASS |
| Specification vs implementation classified | PASS |
| Code unchanged | PASS |
| Runtime unchanged | PASS |
| Broker Submit not executed | PASS |
| Production order not executed | PASS |

## Final Judgment

**PHASE14E52_SELL_GUARD_CONTRACT_IDENTIFIED**

