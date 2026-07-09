# Phase14-E55 Runtime Architecture v2 Design Contract Amendment

## Summary

Phase14-E55 amended `docs/02_architecture/runtime_architecture_v2.md` to reflect the Runtime v2 contract gaps and regression lessons found during Phase14.

This updated E55 amendment additionally clarifies that Runtime v2 is not the AI that directly achieves the annual 50% operating target, but it must not block the aggressive capital deployment selected by Capital Allocation / Risk Policy through hidden fixed values.

Final judgment: **PHASE14E55_RUNTIME_ARCHITECTURE_CONTRACT_UPDATED**

This phase was documentation-only.

No implementation code was changed. No Submit, Broker Write, Production order, Notification real send, launchd change, Current direct edit, or test-only Runtime path was performed.

## References

- `docs/phase_reports/phase14_e53_buy_sell_submit_guard_regression_audit.md`
- `docs/phase_reports/phase14_e54_instruction_regression_failure_postmortem.md`
- `docs/phase_reports/phase14_final_summary_and_phase15_handoff.md`

## Architecture Document Updated

Updated:

```text
docs/02_architecture/runtime_architecture_v2.md
```

The amendment adds a Phase14 contract section under Submit non-idempotency:

```text
12.2 Phase14 追補: Submit Guard / Capital Allocation / SELL Liquidation Contract
```

It also updates:

- Architecture Acceptance Criteria
- Future Implementation / Test Criteria
- Prohibited actions

## Contract Amendments

### 1. Submit Guard Must Not Override Capital Allocation With Hidden Fixed Values

The architecture now states that Submit Guard may verify operational safety but must not silently override Planning / Capital Allocation intent with an undocumented fixed value.

`max_order_amount=100000` style caps are only valid when their meaning, source, runtime mode behavior, manifest output, and regression tests are explicit.

### 2. Runtime Must Not Block the Annual Target Through Hidden Conservatism

The architecture now states:

- Runtime is not the AI that directly achieves the annual 50% goal.
- Candidate AI / Opportunity AI / Position Management AI / Capital Allocation / Risk Policy decide risk-taking and capital deployment.
- Runtime is the control layer that safely puts explicitly approved capital into the market.
- Runtime must not introduce hidden conservative caps that prevent the designed capital deployment.

### 3. Capital Deployment Contract Was Added

A new section was added:

```text
3.1 Capital Deployment Contract
```

It requires the following to be explicit policy, not Runtime hidden defaults:

- target investment ratio
- cash buffer
- max single-position weight
- max positions
- minimum order amount
- maximum order amount
- BUY notional guard
- SELL liquidation guard
- Safety stop conditions

The architecture also requires active capital deployment policy to appear in manifest / report / audit.

### 4. Order Amount Guard Must Be Explicit

The architecture now requires amount guard policy to be visible in:

- design contract
- submit manifest
- report
- audit/report evidence
- regression tests

Hidden amount caps are not accepted as Runtime v2 Submit Guard behavior.

### 5. BUY Notional Guard and SELL Liquidation Guard Are Separated

The architecture now distinguishes:

- BUY: exposure-increasing order, controlled by Capital Allocation, cash/buying power, exposure, price, lot size, Broker constraints, and Safety.
- SELL liquidation: exposure-reducing order, controlled by Runtime-owned Current position, Broker available quantity, and quantity/ownership checks.

If BUY and SELL share the same notional guard, that must be explicitly designed, manifested, and tested.

SELL liquidation must not be mechanically stopped only because it exceeds a BUY order amount limit. If large SELL liquidation should stop, the SELL-specific liquidation policy must define whether the result is review, split, quantity reduction, or block.

### 6. SELL Liquidation Source Is Runtime-owned Current Only

The architecture now states that SELL liquidation can only use Runtime-owned positions from:

```text
persistent_ledger/state.json
```

Broker-only positions are evidence for Reconcile / Review and must not become automatic SELL targets.

### 7. Max Positions Is Not a Runtime Hidden Default

The architecture now states that Runtime has no hidden `max_positions` default.

If a maximum holding count is used, it must be part of Capital Deployment Contract / Risk Policy and must be emitted to manifest:

- `active_max_positions`
- `max_positions_source`
- `current_position_count`
- `planned_position_count`
- `max_positions_decision`
- `max_positions_reason`

This prevents old "5 positions fixed" Runtime behavior from returning implicitly.

### 8. Submit Guard Active Policy Must Be Emitted

Submit Runtime must emit active guard policy in manifest / audit, including:

- `guard_policy_version`
- `active_amount_policy`
- `side`
- `estimated_amount`
- `capital_allocation_amount`
- `max_buy_order_amount`
- `max_sell_liquidation_amount`
- `target_investment_ratio`
- `cash_buffer`
- `max_position_weight`
- `max_positions`
- `notional_guard_source`
- `quantity_guard_source`
- `current_position_source`
- `broker_available_quantity_checked`
- `guard_decision`
- `guard_reason`
- `manual_review_required`

### 9. Tests Pass Is Not Sufficient Acceptance

The architecture now states that `tests pass` is necessary but insufficient.

Runtime v2 acceptance must also prove:

- design contract match
- Input / Output / Consumer schema and unit match
- regular CLI path verification
- Manifest / Current / Ledger / Report / Audit evidence
- no fake adapter or test-only path being reported as Runtime mainline success

### 10. Review Levels Are Explicit

The architecture now separates:

| Level | Meaning |
| --- | --- |
| Level 1 | Component PASS |
| Level 2 | Flow PASS |
| Level 3 | Full Runtime PASS |

Component PASS must not be reported as Flow PASS or Full Runtime PASS.

### 11. Regression Requirements Added

The architecture now requires regression coverage for:

- BUY over 100,000 JPY through regular CLI submit path
- SELL liquidation over 100,000 JPY through regular CLI submit path
- Capital Allocation -> Pending -> Submit Guard contract alignment
- Capital Deployment Contract -> Capital Allocation -> Pending -> Submit Guard alignment
- max_positions policy manifest and enforcement
- regular CLI submit path amount policy
- Submit Guard active policy manifest
- Broker-only position exclusion from SELL source
- Runtime-owned Current position as the only SELL liquidation source

### 12. Legacy / Existing Code Reuse Warning Strengthened

The architecture now prohibits uncritical reuse of existing Runtime / legacy code / helpers without confirming design contract and Input / Output / Consumer semantics.

It also requires that when old code is referenced, the design must state which old contracts are not inherited. Old Runtime safety guards, amount caps, position-count caps, filters, or stop conditions cannot be brought into Runtime v2 without explicit design-contract review.

## Phase15 Handoff

Phase15 should treat prior Phase14 PASS labels as evidence candidates, not as final acceptance.

Phase15 Runtime Contract Full Re-Review must re-check:

- Submit Guard / Capital Allocation contract
- BUY vs SELL guard contract
- SELL liquidation regular CLI flow
- Report / Blog / Notification readiness level
- Regression coverage against regular Runtime paths

Phase15 review must also follow the Runtime Review Rules added to `phase14_final_summary_and_phase15_handoff.md`:

- Runtime Evidence First Rule: prefer Runtime artifacts, Broker state, Current SoT, manifest, ledger, report, and other available evidence over inference.
- Evidence Request Rule: when evidence is missing, ask the Operator for one or two minimal confirmation commands, inspect the result, then decide the next check.
- PASS Rule: do not say PASS until design contract, regular CLI path, manifest, Current, Broker evidence when required, Report, Notification, and Regression evidence are present for the review scope.
- No Guess Rule: do not infer Runtime state when it can be checked.

## Prohibited Actions Check

| Action | Performed |
| --- | --- |
| Implementation change | No |
| Submit | No |
| Broker Write | No |
| Production order | No |
| Notification real send | No |
| launchd/plist change | No |
| Current direct edit | No |
| Test-only Runtime path | No |

## Final Judgment

**PHASE14E55_RUNTIME_ARCHITECTURE_CONTRACT_UPDATED**
